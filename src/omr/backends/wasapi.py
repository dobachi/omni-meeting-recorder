"""WASAPI backend for Windows audio capture using PyAudioWPatch."""

from __future__ import annotations

import contextlib
import logging
import threading
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from omr.config.settings import AudioSettings
from omr.core.device_errors import DeviceError
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
                # Stream may already be closed due to device disconnection
                with contextlib.suppress(OSError):
                    self._stream.stop_stream()
                with contextlib.suppress(OSError):
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
        device_switch_event: threading.Event | None = None,
        on_device_switch: Callable[[], AudioDevice | None] | None = None,
        on_device_error: Callable[[DeviceError], None] | None = None,
    ) -> None:
        """Record audio from a device to a file.

        Args:
            device: Audio device to record from
            output_path: Output file path (used for WAV if writer is None)
            stop_event: Event to signal recording stop
            on_chunk: Optional callback for each audio chunk
            writer: Optional AudioWriter for direct output (e.g., StreamingMP3Encoder).
                    If None, records to WAV file at output_path.
            device_switch_event: Optional event to signal device switch request.
            on_device_switch: Callback to get new device when switch is requested.
                              Returns new AudioDevice or None to keep current.
            on_device_error: Callback when a device error is detected.
                             Called with DeviceError describing the error.
        """
        import pyaudiowpatch as pyaudio

        logger = logging.getLogger(__name__)

        if self._pyaudio is None:
            self.initialize()

        current_device = device
        stream = self.create_stream(current_device)
        stream.open()

        sample_width = self._pyaudio.get_sample_size(pyaudio.paInt16)

        # Use the actual stream config settings for WAV file
        channels = stream._config.channels
        sample_rate = stream._config.sample_rate

        # Error tracking for consecutive error detection
        consecutive_errors = 0
        max_consecutive_errors = 3

        # Determine source name for error reporting
        source = "loopback" if current_device.device_type == DeviceType.LOOPBACK else "mic"

        try:
            if writer is not None:
                # Use provided writer (e.g., StreamingMP3Encoder)
                while not stop_event.is_set():
                    # Check for device switch request
                    if (
                        device_switch_event is not None
                        and device_switch_event.is_set()
                        and on_device_switch is not None
                    ):
                        new_device = on_device_switch()
                        if new_device is not None:
                            try:
                                # Close current stream
                                stream.close()
                                # Create new stream with new device
                                current_device = new_device
                                stream = self.create_stream(current_device)
                                stream.open()
                                logger.info(f"Switched to device: {current_device.name}")
                            except Exception as e:
                                logger.error(f"Device switch failed: {e}")
                                # Try to reopen previous device
                                stream = self.create_stream(current_device)
                                stream.open()

                    try:
                        data = stream.read()
                        writer.write(data)
                        if on_chunk:
                            on_chunk(data)
                        consecutive_errors = 0  # Reset on success
                    except Exception as e:
                        if stop_event.is_set():
                            break
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            device_error = DeviceError.from_exception(source, e)
                            logger.warning(f"Device error detected: {device_error}")
                            if on_device_error:
                                on_device_error(device_error)
                            if not device_error.can_recover:
                                raise
                            break
                writer.close()
            else:
                # Default: write to WAV file
                with wave.open(str(output_path), "wb") as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(sample_width)
                    wf.setframerate(sample_rate)

                    while not stop_event.is_set():
                        # Check for device switch request
                        if (
                            device_switch_event is not None
                            and device_switch_event.is_set()
                            and on_device_switch is not None
                        ):
                            new_device = on_device_switch()
                            if new_device is not None:
                                try:
                                    stream.close()
                                    current_device = new_device
                                    stream = self.create_stream(current_device)
                                    stream.open()
                                    logger.info(f"Switched to device: {current_device.name}")
                                except Exception as e:
                                    logger.error(f"Device switch failed: {e}")
                                    stream = self.create_stream(current_device)
                                    stream.open()

                        try:
                            data = stream.read()
                            wf.writeframes(data)
                            if on_chunk:
                                on_chunk(data)
                            consecutive_errors = 0  # Reset on success
                        except Exception as e:
                            if stop_event.is_set():
                                break
                            consecutive_errors += 1
                            if consecutive_errors >= max_consecutive_errors:
                                device_error = DeviceError.from_exception(source, e)
                                logger.warning(f"Device error detected: {device_error}")
                                if on_device_error:
                                    on_device_error(device_error)
                                if not device_error.can_recover:
                                    raise
                                break
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
        mic_gain: float = 1.5,
        loopback_gain: float = 1.0,
        mix_ratio: float = 0.5,
        on_chunk: Callable[[bytes], None] | None = None,
        writer: AudioWriter | None = None,
        device_switch_event: threading.Event | None = None,
        on_device_switch: Callable[[], tuple[AudioDevice | None, AudioDevice | None]] | None = None,
        on_device_error: Callable[[DeviceError], None] | None = None,
        on_find_alternative: Callable[[str, AudioDevice], AudioDevice | None] | None = None,
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
            device_switch_event: Optional event to signal device switch request.
            on_device_switch: Callback to get new devices when switch is requested.
                              Returns tuple of (mic_device, loopback_device).
                              Either may be None to keep current device.
            on_device_error: Callback when a device error is detected.
                             Called with DeviceError describing the error.
            on_find_alternative: Callback to find alternative device on error.
                                 Takes (source, current_device) and returns alternative
                                 AudioDevice or None if no alternative available.
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

        # Error queue for device errors
        error_queue: Queue[DeviceError] = Queue(maxsize=10)

        # Error tracking for consecutive error detection
        max_consecutive_errors = 3

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
        agc_window = 100  # Number of chunks to average for stable gain
        loopback_target_rms = 8000.0  # Target RMS level (~25% of 16-bit peak)
        mic_target_rms = 16000.0  # Higher target for mic (~49% of 16-bit peak)

        # Buffers for accumulating samples
        mic_buffer: list[int] = []
        loopback_buffer: list[int] = []

        # Initialize thread references for cleanup in finally block
        mic_thread: threading.Thread | None = None
        loopback_thread: threading.Thread | None = None

        # Logger for this method
        logger = logging.getLogger(__name__)

        # Shared state for device switching
        reader_pause_event = threading.Event()
        reader_resume_event = threading.Event()
        reader_resume_event.set()  # Initially not paused

        # Mutable container for current devices/streams (for thread access)
        current_state = {
            "mic_device": mic_device,
            "loopback_device": loopback_device,
            "mic_stream": mic_stream,
            "loopback_stream": loopback_stream,
            "mic_sample_rate": mic_sample_rate,
            "loopback_sample_rate": loopback_sample_rate,
            "mic_channels": mic_channels,
            "loopback_channels": loopback_channels,
        }

        def mic_reader_thread_v2() -> None:
            """Thread to read from microphone with pause support and error detection."""
            consecutive_errors = 0
            while not stop_event.is_set():
                # Check for pause
                if reader_pause_event.is_set():
                    reader_resume_event.wait(timeout=0.1)
                    consecutive_errors = 0  # Reset on pause
                    continue
                try:
                    stream = current_state["mic_stream"]
                    if stream is None or not stream.is_running:
                        import time
                        time.sleep(0.01)
                        continue
                    data = stream.read()
                    samples = list(struct.unpack(f"<{len(data) // 2}h", data))
                    mono = to_mono(samples, current_state["mic_channels"])
                    resampled = resample_simple(
                        mono,
                        current_state["mic_sample_rate"],
                        output_sample_rate
                    )
                    with contextlib.suppress(Exception):
                        mic_queue.put_nowait(resampled)
                    consecutive_errors = 0  # Reset on success
                except Exception as e:
                    if stop_event.is_set() or reader_pause_event.is_set():
                        continue
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        # Device likely disconnected
                        device_error = DeviceError.from_exception("mic", e)
                        with contextlib.suppress(Exception):
                            error_queue.put_nowait(device_error)
                        logger.warning(f"Mic device error detected: {device_error}")
                        # Pause and wait for recovery or stop
                        reader_pause_event.set()
                        consecutive_errors = 0

        def loopback_reader_thread_v2() -> None:
            """Thread to read from loopback with pause support and error detection."""
            consecutive_errors = 0
            while not stop_event.is_set():
                # Check for pause
                if reader_pause_event.is_set():
                    reader_resume_event.wait(timeout=0.1)
                    consecutive_errors = 0  # Reset on pause
                    continue
                try:
                    stream = current_state["loopback_stream"]
                    if stream is None or not stream.is_running:
                        import time
                        time.sleep(0.01)
                        continue
                    data = stream.read()
                    samples = list(struct.unpack(f"<{len(data) // 2}h", data))
                    mono = to_mono(samples, current_state["loopback_channels"], use_left_only=True)
                    with contextlib.suppress(Exception):
                        loopback_queue.put_nowait(mono)
                    consecutive_errors = 0  # Reset on success
                except Exception as e:
                    if stop_event.is_set() or reader_pause_event.is_set():
                        continue
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        # Device likely disconnected
                        device_error = DeviceError.from_exception("loopback", e)
                        with contextlib.suppress(Exception):
                            error_queue.put_nowait(device_error)
                        logger.warning(f"Loopback device error detected: {device_error}")
                        # Pause and wait for recovery or stop
                        reader_pause_event.set()
                        consecutive_errors = 0

        def perform_device_switch() -> bool:
            """Perform device switch. Returns True if switch was successful."""
            nonlocal aec_processor

            if on_device_switch is None:
                return False

            new_mic, new_loopback = on_device_switch()
            if new_mic is None and new_loopback is None:
                return False

            # Pause reader threads
            reader_pause_event.set()
            reader_resume_event.clear()
            import time
            time.sleep(0.05)  # Give threads time to pause

            success = True
            try:
                # Switch mic device if requested
                if new_mic is not None:
                    try:
                        old_stream = current_state["mic_stream"]
                        if old_stream:
                            old_stream.close()
                        new_stream = self.create_stream(new_mic)
                        new_stream.open()
                        current_state["mic_device"] = new_mic
                        current_state["mic_stream"] = new_stream
                        current_state["mic_sample_rate"] = int(new_mic.default_sample_rate)
                        current_state["mic_channels"] = new_stream._config.channels
                        logger.info(f"Switched mic to: {new_mic.name}")
                    except Exception as e:
                        logger.error(f"Mic device switch failed: {e}")
                        success = False

                # Switch loopback device if requested
                if new_loopback is not None:
                    try:
                        old_stream = current_state["loopback_stream"]
                        if old_stream:
                            old_stream.close()
                        new_stream = self.create_stream(new_loopback)
                        new_stream.open()
                        current_state["loopback_device"] = new_loopback
                        current_state["loopback_stream"] = new_stream
                        current_state["loopback_sample_rate"] = int(
                            new_loopback.default_sample_rate
                        )
                        current_state["loopback_channels"] = new_stream._config.channels
                        logger.info(f"Switched loopback to: {new_loopback.name}")
                    except Exception as e:
                        logger.error(f"Loopback device switch failed: {e}")
                        success = False

                # Clear queues and buffers
                while not mic_queue.empty():
                    try:
                        mic_queue.get_nowait()
                    except Empty:
                        break
                while not loopback_queue.empty():
                    try:
                        loopback_queue.get_nowait()
                    except Empty:
                        break
                mic_buffer.clear()
                loopback_buffer.clear()

            finally:
                # Resume reader threads
                reader_pause_event.clear()
                reader_resume_event.set()

            return success

        def perform_device_switch_for_source(
            source: str, new_device: AudioDevice
        ) -> bool:
            """Perform device switch for a specific source (mic or loopback).

            Args:
                source: "mic" or "loopback"
                new_device: The new device to switch to

            Returns:
                True if switch was successful, False otherwise
            """
            # Threads are already paused from error detection
            import time
            time.sleep(0.05)  # Give threads time to fully pause

            success = True
            try:
                if source == "mic":
                    try:
                        old_stream = current_state["mic_stream"]
                        if old_stream:
                            old_stream.close()
                        new_stream = self.create_stream(new_device)
                        new_stream.open()
                        current_state["mic_device"] = new_device
                        current_state["mic_stream"] = new_stream
                        current_state["mic_sample_rate"] = int(
                            new_device.default_sample_rate
                        )
                        current_state["mic_channels"] = new_stream._config.channels
                        logger.info(f"Auto-switched mic to: {new_device.name}")
                    except Exception as e:
                        logger.error(f"Mic device auto-switch failed: {e}")
                        success = False
                else:  # loopback
                    try:
                        old_stream = current_state["loopback_stream"]
                        if old_stream:
                            old_stream.close()
                        new_stream = self.create_stream(new_device)
                        new_stream.open()
                        current_state["loopback_device"] = new_device
                        current_state["loopback_stream"] = new_stream
                        current_state["loopback_sample_rate"] = int(
                            new_device.default_sample_rate
                        )
                        current_state["loopback_channels"] = new_stream._config.channels
                        logger.info(f"Auto-switched loopback to: {new_device.name}")
                    except Exception as e:
                        logger.error(f"Loopback device auto-switch failed: {e}")
                        success = False

                # Clear queues and buffers
                while not mic_queue.empty():
                    try:
                        mic_queue.get_nowait()
                    except Empty:
                        break
                while not loopback_queue.empty():
                    try:
                        loopback_queue.get_nowait()
                    except Empty:
                        break
                mic_buffer.clear()
                loopback_buffer.clear()

            finally:
                # Resume reader threads
                reader_pause_event.clear()
                reader_resume_event.set()

            return success

        try:
            mic_stream.open()
            loopback_stream.open()

            # Start reader threads with pause support
            mic_thread = threading.Thread(
                target=mic_reader_thread_v2, daemon=True, name="mic_reader"
            )
            loopback_thread = threading.Thread(
                target=loopback_reader_thread_v2, daemon=True, name="loopback_reader"
            )
            mic_thread.start()
            loopback_thread.start()

            # Helper function for the main recording loop
            def recording_loop(write_func: Callable[[bytes], None]) -> None:
                """Main recording loop that processes audio data."""
                nonlocal mic_buffer, loopback_buffer
                nonlocal mic_rms_history, loopback_rms_history

                while not stop_event.is_set():
                    # Check for device errors and attempt recovery
                    while not error_queue.empty():
                        try:
                            device_error = error_queue.get_nowait()
                            if on_device_error:
                                on_device_error(device_error)

                            # Try to find alternative device
                            alternative = None
                            current_device = None
                            if on_find_alternative:
                                if device_error.source == "mic":
                                    current_device = current_state["mic_device"]
                                else:
                                    current_device = current_state["loopback_device"]
                                alternative = on_find_alternative(
                                    device_error.source, current_device
                                )

                            if alternative:
                                # Trigger device switch
                                logger.info(
                                    f"Auto-switching {device_error.source} to: "
                                    f"{alternative.name}"
                                )
                                if device_error.source == "mic":
                                    if on_device_switch:
                                        # Use existing switch mechanism
                                        current_state["mic_device"] = alternative
                                        perform_device_switch_for_source("mic", alternative)
                                else:
                                    if on_device_switch:
                                        current_state["loopback_device"] = alternative
                                        perform_device_switch_for_source(
                                            "loopback", alternative
                                        )
                            else:
                                # No alternative found, stop recording
                                logger.warning(
                                    f"No alternative device found for {device_error.source}, "
                                    "stopping recording"
                                )
                                stop_event.set()
                                return
                        except Empty:
                            break

                    # Check for device switch request
                    if (
                        device_switch_event is not None
                        and device_switch_event.is_set()
                    ):
                        perform_device_switch()

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
                                auto_mic_gain = max(0.8, min(4.0, auto_mic_gain))
                                # Apply user gain multiplier
                                total_mic_gain = auto_mic_gain * mic_gain
                                mic_chunk = apply_gain(mic_chunk, total_mic_gain)

                        # Normalize loopback to target level
                        if loopback_rms_history:
                            avg_loopback_rms = sum(loopback_rms_history) / len(loopback_rms_history)
                            if avg_loopback_rms > 50:
                                auto_loopback_gain = loopback_target_rms / avg_loopback_rms
                                auto_loopback_gain = max(0.8, min(3.0, auto_loopback_gain))
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

            # Wait for threads to finish (normal path)
            mic_thread.join(timeout=1.0)
            loopback_thread.join(timeout=1.0)

        finally:
            # Ensure stop_event is set to signal threads to exit
            stop_event.set()
            # Also clear pause to ensure threads can exit
            reader_pause_event.clear()
            reader_resume_event.set()

            # Wait for threads to terminate
            if mic_thread is not None and mic_thread.is_alive():
                mic_thread.join(timeout=2.0)
                if mic_thread.is_alive():
                    logger.warning("mic_reader thread did not terminate within timeout")

            if loopback_thread is not None and loopback_thread.is_alive():
                loopback_thread.join(timeout=2.0)
                if loopback_thread.is_alive():
                    logger.warning("loopback_reader thread did not terminate within timeout")

            # Clean up AEC processor
            if aec_processor is not None:
                aec_processor.close()

            # Close current streams (may have been switched)
            if current_state["mic_stream"] is not None:
                current_state["mic_stream"].close()
            if current_state["loopback_stream"] is not None:
                current_state["loopback_stream"].close()

    def __enter__(self) -> WasapiBackend:
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.terminate()
