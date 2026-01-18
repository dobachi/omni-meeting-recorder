"""WASAPI backend for Windows audio capture using PyAudioWPatch."""

import threading
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from omr.config.settings import AudioSettings
from omr.core.device_manager import AudioDevice, DeviceType


@dataclass
class StreamConfig:
    """Configuration for an audio stream."""

    device_index: int
    channels: int
    sample_rate: int
    chunk_size: int
    format: int  # PyAudio format constant


class WasapiStream:
    """Handles a single WASAPI audio stream."""

    def __init__(
        self,
        pyaudio_instance: Any,
        config: StreamConfig,
        is_loopback: bool = False,
    ) -> None:
        self._pyaudio = pyaudio_instance
        self._config = config
        self._is_loopback = is_loopback
        self._stream: Any = None
        self._is_running = False
        self._lock = threading.Lock()

    def open(self) -> None:
        """Open the audio stream.

        For loopback devices, PyAudioWPatch automatically handles WASAPI loopback
        capture when opening the loopback device as an input stream.
        """
        with self._lock:
            if self._stream is not None:
                return

            stream_kwargs: dict[str, Any] = {
                "format": self._config.format,
                "channels": self._config.channels,
                "rate": self._config.sample_rate,
                "input": True,
                "input_device_index": self._config.device_index,
                "frames_per_buffer": self._config.chunk_size,
            }

            self._stream = self._pyaudio.open(**stream_kwargs)
            self._is_running = True

    def close(self) -> None:
        """Close the audio stream."""
        with self._lock:
            if self._stream is not None:
                self._is_running = False
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None

    def read(self) -> bytes:
        """Read a chunk of audio data."""
        if self._stream is None:
            raise RuntimeError("Stream is not open")
        return self._stream.read(self._config.chunk_size, exception_on_overflow=False)

    @property
    def is_running(self) -> bool:
        """Check if the stream is currently running."""
        return self._is_running


class WasapiBackend:
    """WASAPI backend for audio capture."""

    def __init__(self, audio_settings: AudioSettings | None = None) -> None:
        self._settings = audio_settings or AudioSettings()
        self._pyaudio: Any = None
        self._streams: list[WasapiStream] = []
        self._recording = False
        self._lock = threading.Lock()

    def initialize(self) -> None:
        """Initialize PyAudio."""
        import pyaudiowpatch as pyaudio

        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()

    def terminate(self) -> None:
        """Terminate PyAudio and cleanup resources."""
        self.stop_all_streams()
        if self._pyaudio is not None:
            self._pyaudio.terminate()
            self._pyaudio = None

    def create_stream(
        self,
        device: AudioDevice,
        channels: int | None = None,
        sample_rate: int | None = None,
    ) -> WasapiStream:
        """Create an audio stream for the given device.

        Uses device's native sample rate and channels if not specified,
        which is important for loopback devices to work correctly.
        """
        import pyaudiowpatch as pyaudio

        if self._pyaudio is None:
            self.initialize()

        # Use device's native settings for best compatibility
        actual_channels = channels or device.channels or self._settings.channels
        actual_sample_rate = sample_rate or int(device.default_sample_rate) or self._settings.sample_rate

        config = StreamConfig(
            device_index=device.index,
            channels=actual_channels,
            sample_rate=actual_sample_rate,
            chunk_size=self._settings.chunk_size,
            format=pyaudio.paInt16,  # 16-bit audio
        )

        is_loopback = device.device_type == DeviceType.LOOPBACK
        stream = WasapiStream(self._pyaudio, config, is_loopback)
        self._streams.append(stream)
        return stream

    def stop_all_streams(self) -> None:
        """Stop and close all active streams."""
        for stream in self._streams:
            stream.close()
        self._streams.clear()

    def record_to_file(
        self,
        device: AudioDevice,
        output_path: Path,
        stop_event: threading.Event,
        on_chunk: Callable[[bytes], None] | None = None,
    ) -> None:
        """Record audio from a device to a WAV file."""
        import pyaudiowpatch as pyaudio

        if self._pyaudio is None:
            self.initialize()

        stream = self.create_stream(device)
        stream.open()

        sample_width = self._pyaudio.get_sample_size(pyaudio.paInt16)

        # Use the actual stream config settings for WAV file
        channels = stream._config.channels
        sample_rate = stream._config.sample_rate

        try:
            with wave.open(str(output_path), "wb") as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sample_width)
                wf.setframerate(sample_rate)

                while not stop_event.is_set():
                    try:
                        data = stream.read()
                        wf.writeframes(data)
                        if on_chunk:
                            on_chunk(data)
                    except Exception:
                        if stop_event.is_set():
                            break
                        raise
        finally:
            stream.close()

    def record_dual_to_file(
        self,
        mic_device: AudioDevice,
        loopback_device: AudioDevice,
        output_path: Path,
        stop_event: threading.Event,
        stereo_split: bool = True,
        on_chunk: Callable[[bytes], None] | None = None,
    ) -> None:
        """Record audio from both mic and loopback devices to a single WAV file.

        Args:
            mic_device: Microphone device
            loopback_device: Loopback device for system audio
            output_path: Output WAV file path
            stop_event: Event to signal recording stop
            stereo_split: If True, left=mic, right=system. If False, mix both.
            on_chunk: Callback for each output chunk
        """
        import pyaudiowpatch as pyaudio

        from omr.core.mixer import AudioMixer, MixerConfig

        if self._pyaudio is None:
            self.initialize()

        # Use each device's native sample rate for best compatibility
        mic_sample_rate = int(mic_device.default_sample_rate)
        loopback_sample_rate = int(loopback_device.default_sample_rate)

        # Output sample rate is the higher of the two
        output_sample_rate = max(mic_sample_rate, loopback_sample_rate)

        # Create streams with their native sample rates
        mic_stream = self.create_stream(mic_device)
        loopback_stream = self.create_stream(loopback_device)

        # Create mixer with sample rate info for resampling
        mixer_config = MixerConfig(
            sample_rate=output_sample_rate,
            mic_sample_rate=mic_sample_rate,
            loopback_sample_rate=loopback_sample_rate,
            channels=2,  # Stereo output
            chunk_size=self._settings.chunk_size,
            stereo_split=stereo_split,
        )
        mixer = AudioMixer(mixer_config)

        sample_width = self._pyaudio.get_sample_size(pyaudio.paInt16)

        # Reader threads
        def mic_reader() -> None:
            while not stop_event.is_set():
                try:
                    data = mic_stream.read()
                    mixer.add_mic_data(data)
                except Exception:
                    if stop_event.is_set():
                        break

        def loopback_reader() -> None:
            while not stop_event.is_set():
                try:
                    data = loopback_stream.read()
                    mixer.add_loopback_data(data)
                except Exception:
                    if stop_event.is_set():
                        break

        try:
            # Open streams
            mic_stream.open()
            loopback_stream.open()

            # Start mixer
            mixer.start()

            # Start reader threads
            mic_thread = threading.Thread(target=mic_reader, daemon=True)
            loopback_thread = threading.Thread(target=loopback_reader, daemon=True)
            mic_thread.start()
            loopback_thread.start()

            # Write mixed output to file
            with wave.open(str(output_path), "wb") as wf:
                wf.setnchannels(2)  # Stereo
                wf.setsampwidth(sample_width)
                wf.setframerate(output_sample_rate)

                while not stop_event.is_set():
                    mixed_data = mixer.get_output(timeout=0.1)
                    if mixed_data:
                        wf.writeframes(mixed_data)
                        if on_chunk:
                            on_chunk(mixed_data)

            # Wait for reader threads to finish
            stop_event.set()
            mic_thread.join(timeout=1.0)
            loopback_thread.join(timeout=1.0)

        finally:
            mixer.stop()
            mic_stream.close()
            loopback_stream.close()

    def __enter__(self) -> "WasapiBackend":
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.terminate()
