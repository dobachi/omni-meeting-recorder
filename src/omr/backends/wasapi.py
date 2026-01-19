"""WASAPI backend for Windows audio capture using PyAudioWPatch."""

from __future__ import annotations

import contextlib
import threading
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from omr.config.settings import AudioSettings
from omr.core.device_manager import AudioDevice, DeviceType

if TYPE_CHECKING:
    from omr.core.aec_processor import AECProcessor


class AudioWriter(Protocol):
    """音声書き込みインターフェース（WAVとMP3で共通）."""

    def write(self, data: bytes) -> None:
        """音声データを書き込む."""
        ...

    def close(self) -> None:
        """ライターを閉じる."""
        ...


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
        data: bytes = self._stream.read(self._config.chunk_size, exception_on_overflow=False)
        return data

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
        actual_sample_rate = (
            sample_rate or int(device.default_sample_rate) or self._settings.sample_rate
        )

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
        writer: AudioWriter | None = None,
    ) -> None:
        """Record audio from a device to a file.

        Args:
            device: Audio device to record from
            output_path: Output file path (used for WAV if writer is None)
            stop_event: Event to signal recording stop
            on_chunk: Optional callback for each audio chunk
            writer: Optional AudioWriter for direct output (e.g., StreamingMP3Encoder).
                    If None, records to WAV file at output_path.
        """
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
            if writer is not None:
                # Use provided writer (e.g., StreamingMP3Encoder)
                while not stop_event.is_set():
                    try:
                        data = stream.read()
                        writer.write(data)
                        if on_chunk:
                            on_chunk(data)
                    except Exception:
                        if stop_event.is_set():
                            break
                        raise
                writer.close()
            else:
                # Default: write to WAV file
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
        aec_enabled: bool = False,
        mic_gain: float = 1.0,
        loopback_gain: float = 1.0,
        mix_ratio: float = 0.5,
        on_chunk: Callable[[bytes], None] | None = None,
        writer: AudioWriter | None = None,
    ) -> None:
        """Record audio from both mic and loopback devices to a single file.

        Uses parallel thread reading for proper timing synchronization.

        Args:
            mic_device: Microphone device
            loopback_device: Loopback device for system audio
            output_path: Output file path (used for WAV if writer is None)
            stop_event: Event to signal recording stop
            stereo_split: If True, left=mic, right=system. If False, mix both.
            aec_enabled: If True, apply acoustic echo cancellation to mic signal.
            mic_gain: Microphone gain multiplier (applied after AGC).
            loopback_gain: System audio gain multiplier (applied after AGC).
            mix_ratio: Mic/system mix ratio (0.0-1.0). Higher = more mic.
            on_chunk: Callback for each output chunk
            writer: Optional AudioWriter for direct output (e.g., StreamingMP3Encoder).
                    If None, records to WAV file at output_path.
        """
        import struct
        from queue import Empty, Queue

        import pyaudiowpatch as pyaudio

        if self._pyaudio is None:
            self.initialize()

        # Use each device's native sample rate
        mic_sample_rate = int(mic_device.default_sample_rate)
        loopback_sample_rate = int(loopback_device.default_sample_rate)

        # Output uses loopback's sample rate as master
        output_sample_rate = loopback_sample_rate

        # Create streams with their native sample rates
        mic_stream = self.create_stream(mic_device)
        loopback_stream = self.create_stream(loopback_device)

        mic_channels = mic_stream._config.channels
        loopback_channels = loopback_stream._config.channels

        sample_width = self._pyaudio.get_sample_size(pyaudio.paInt16)

        # Initialize AEC processor if enabled
        aec_processor: AECProcessor | None = None
        if aec_enabled:
            from omr.core.aec_processor import AECProcessor as AECProcessorClass
            from omr.core.aec_processor import is_aec_available

            if is_aec_available():
                # Use 160 samples frame size (10ms at 16kHz, common for AEC)
                # Scale frame size based on sample rate
                aec_frame_size = max(160, output_sample_rate // 100)
                aec_processor = AECProcessorClass(
                    sample_rate=output_sample_rate,
                    frame_size=aec_frame_size,
                )

        # Thread-safe queues for audio data
        mic_queue: Queue[list[int]] = Queue(maxsize=100)
        loopback_queue: Queue[list[int]] = Queue(maxsize=100)

        def to_mono(samples: list[int], channels: int, use_left_only: bool = False) -> list[int]:
            """Convert to mono.

            Args:
                samples: Interleaved samples
                channels: Number of channels
                use_left_only: If True, use only left channel (avoids phase issues)
            """
            if channels == 1:
                return samples
            mono = []
            for i in range(0, len(samples) - channels + 1, channels):
                if use_left_only:
                    # Use only left channel to avoid phase-related echo
                    mono.append(samples[i])
                else:
                    # Average all channels
                    mono.append(sum(samples[i:i+channels]) // channels)
            return mono

        def resample_simple(samples: list[int], from_rate: int, to_rate: int) -> list[int]:
            """Simple resampling using linear interpolation."""
            if from_rate == to_rate or not samples:
                return samples
            ratio = to_rate / from_rate
            new_length = int(len(samples) * ratio)
            if new_length == 0:
                return []
            resampled = []
            for i in range(new_length):
                pos = i / ratio
                idx = int(pos)
                frac = pos - idx
                if idx + 1 < len(samples):
                    val = samples[idx] * (1 - frac) + samples[idx + 1] * frac
                else:
                    val = samples[idx] if idx < len(samples) else 0
                resampled.append(int(val))
            return resampled

        def calc_rms(samples: list[int]) -> float:
            """Calculate RMS (Root Mean Square) of samples."""
            if not samples:
                return 0.0
            sum_sq = sum(s * s for s in samples)
            return float((sum_sq / len(samples)) ** 0.5)

        def apply_gain(samples: list[int], gain: float) -> list[int]:
            """Apply gain to samples with soft clipping."""
            result = []
            for s in samples:
                val = s * gain
                # Soft clipping to prevent harsh distortion
                if val > 32767:
                    val = 32767
                elif val < -32768:
                    val = -32768
                result.append(int(val))
            return result

        # Automatic gain control state
        mic_rms_history: list[float] = []
        loopback_rms_history: list[float] = []
        agc_window = 50  # Number of chunks to average for stable gain
        loopback_target_rms = 8000.0  # Target RMS level (~25% of 16-bit peak)
        mic_target_rms = 16000.0  # Higher target for mic (~49% of 16-bit peak)

        def mic_reader_thread() -> None:
            """Thread to read from microphone."""
            while not stop_event.is_set():
                try:
                    data = mic_stream.read()
                    samples = list(struct.unpack(f"<{len(data) // 2}h", data))
                    mono = to_mono(samples, mic_channels)
                    # Resample to output rate
                    resampled = resample_simple(mono, mic_sample_rate, output_sample_rate)
                    with contextlib.suppress(Exception):
                        mic_queue.put_nowait(resampled)  # Drop if queue full
                except Exception:
                    if stop_event.is_set():
                        break

        def loopback_reader_thread() -> None:
            """Thread to read from loopback."""
            while not stop_event.is_set():
                try:
                    data = loopback_stream.read()
                    samples = list(struct.unpack(f"<{len(data) // 2}h", data))
                    # Use left channel only to avoid phase-related echo
                    mono = to_mono(samples, loopback_channels, use_left_only=True)
                    with contextlib.suppress(Exception):
                        loopback_queue.put_nowait(mono)  # Drop if queue full
                except Exception:
                    if stop_event.is_set():
                        break

        # Buffers for accumulating samples
        mic_buffer: list[int] = []
        loopback_buffer: list[int] = []

        try:
            mic_stream.open()
            loopback_stream.open()

            # Start reader threads
            mic_thread = threading.Thread(target=mic_reader_thread, daemon=True)
            loopback_thread = threading.Thread(target=loopback_reader_thread, daemon=True)
            mic_thread.start()
            loopback_thread.start()

            # Helper function for the main recording loop
            def recording_loop(write_func: Callable[[bytes], None]) -> None:
                """Main recording loop that processes audio data."""
                nonlocal mic_buffer, loopback_buffer
                nonlocal mic_rms_history, loopback_rms_history

                while not stop_event.is_set():
                    # Drain queues into buffers
                    while True:
                        try:
                            mic_buffer.extend(mic_queue.get_nowait())
                        except Empty:
                            break

                    while True:
                        try:
                            loopback_buffer.extend(loopback_queue.get_nowait())
                        except Empty:
                            break

                    # Output based on loopback buffer (master clock)
                    if loopback_buffer:
                        chunk_size = len(loopback_buffer)
                        loopback_chunk = loopback_buffer[:]
                        loopback_buffer.clear()

                        # Take matching amount from mic buffer
                        if len(mic_buffer) >= chunk_size:
                            mic_chunk = mic_buffer[:chunk_size]
                            mic_buffer[:] = mic_buffer[chunk_size:]
                        else:
                            mic_chunk = mic_buffer[:] + [0] * (chunk_size - len(mic_buffer))
                            mic_buffer.clear()

                        # Apply AEC if enabled
                        if aec_processor is not None:
                            # process_samples returns same length as input
                            mic_chunk = aec_processor.process_samples(
                                mic_chunk, loopback_chunk
                            )

                        # Automatic gain control: normalize both channels to target level
                        mic_rms = calc_rms(mic_chunk)
                        loopback_rms = calc_rms(loopback_chunk)

                        # Track RMS history for stable gain calculation
                        if mic_rms > 50:  # Lower threshold for quiet mics
                            mic_rms_history.append(mic_rms)
                            if len(mic_rms_history) > agc_window:
                                mic_rms_history.pop(0)
                        if loopback_rms > 100:
                            loopback_rms_history.append(loopback_rms)
                            if len(loopback_rms_history) > agc_window:
                                loopback_rms_history.pop(0)

                        # Normalize mic to target level (higher target for mic)
                        if mic_rms_history:
                            avg_mic_rms = sum(mic_rms_history) / len(mic_rms_history)
                            if avg_mic_rms > 50:
                                auto_mic_gain = mic_target_rms / avg_mic_rms
                                auto_mic_gain = max(0.5, min(12.0, auto_mic_gain))
                                # Apply user gain multiplier
                                total_mic_gain = auto_mic_gain * mic_gain
                                mic_chunk = apply_gain(mic_chunk, total_mic_gain)

                        # Normalize loopback to target level
                        if loopback_rms_history:
                            avg_loopback_rms = sum(loopback_rms_history) / len(loopback_rms_history)
                            if avg_loopback_rms > 50:
                                auto_loopback_gain = loopback_target_rms / avg_loopback_rms
                                auto_loopback_gain = max(0.5, min(6.0, auto_loopback_gain))
                                # Apply user gain multiplier
                                total_loopback_gain = auto_loopback_gain * loopback_gain
                                loopback_chunk = apply_gain(loopback_chunk, total_loopback_gain)

                        # Create stereo output
                        output_samples = []
                        for i in range(chunk_size):
                            mic_val = mic_chunk[i] if i < len(mic_chunk) else 0
                            loop_val = loopback_chunk[i] if i < len(loopback_chunk) else 0

                            if stereo_split:
                                output_samples.extend([mic_val, loop_val])
                            else:
                                mixed = int(mic_val * mix_ratio + loop_val * (1.0 - mix_ratio))
                                output_samples.extend([mixed, mixed])

                        clamped = [max(-32768, min(32767, s)) for s in output_samples]
                        output_data = struct.pack(f"<{len(clamped)}h", *clamped)
                        write_func(output_data)

                        if on_chunk:
                            on_chunk(output_data)
                    else:
                        # No loopback data yet, small sleep to avoid busy loop
                        import time
                        time.sleep(0.001)

            # Execute recording loop with appropriate writer
            if writer is not None:
                # Use provided writer (e.g., StreamingMP3Encoder)
                recording_loop(writer.write)
                writer.close()
            else:
                # Default: write to WAV file
                with wave.open(str(output_path), "wb") as wf:
                    wf.setnchannels(2)  # Stereo output
                    wf.setsampwidth(sample_width)
                    wf.setframerate(output_sample_rate)
                    recording_loop(wf.writeframes)

            # Wait for threads to finish
            mic_thread.join(timeout=1.0)
            loopback_thread.join(timeout=1.0)

        finally:
            mic_stream.close()
            loopback_stream.close()

    def __enter__(self) -> WasapiBackend:
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.terminate()
