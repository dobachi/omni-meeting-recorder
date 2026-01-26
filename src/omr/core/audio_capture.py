"""Audio capture abstraction layer."""

import contextlib
import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from omr.backends.wasapi import WasapiBackend
from omr.config.settings import RecordingMode, Settings
from omr.core.device_errors import DeviceError
from omr.core.device_manager import AudioDevice, DeviceManager

logger = logging.getLogger(__name__)


@dataclass
class RecordingState:
    """Current state of a recording session."""

    is_recording: bool = False
    start_time: datetime | None = None
    output_file: Path | None = None
    bytes_recorded: int = 0
    error: str | None = None
    device_error: DeviceError | None = None
    is_partial_save: bool = False


@dataclass
class RecordingSession:
    """Manages a recording session."""

    mode: RecordingMode
    output_path: Path
    mic_device: AudioDevice | None = None
    loopback_device: AudioDevice | None = None
    stereo_split: bool = True  # For BOTH mode: True=left:mic/right:system
    aec_enabled: bool = False  # For BOTH mode: Enable acoustic echo cancellation
    aec_filter_multiplier: int = 30  # AEC filter strength (5-100, higher = stronger)
    mic_gain: float = 1.5  # Microphone gain multiplier
    loopback_gain: float = 1.0  # System audio gain multiplier
    mix_ratio: float = 0.5  # Mic/system mix ratio (0.0-1.0, higher = more mic)
    direct_mp3: bool = True  # Enable direct MP3 output (default for MP3 format)
    mp3_bitrate: int = 128  # MP3 bitrate in kbps
    state: RecordingState = field(default_factory=RecordingState)
    _stop_event: threading.Event = field(default_factory=threading.Event)
    _recording_thread: threading.Thread | None = None
    # Device switching support
    _device_switch_event: threading.Event = field(default_factory=threading.Event)
    _pending_mic_device: AudioDevice | None = field(default=None)
    _pending_loopback_device: AudioDevice | None = field(default=None)
    _device_switch_lock: threading.Lock = field(default_factory=threading.Lock)
    # Device error callback
    _device_error_callback: Callable[[DeviceError], None] | None = field(default=None)

    def request_stop(self) -> None:
        """Request the recording to stop."""
        self._stop_event.set()

    @property
    def stop_event(self) -> threading.Event:
        """Get the stop event."""
        return self._stop_event

    @property
    def device_switch_event(self) -> threading.Event:
        """Get the device switch event."""
        return self._device_switch_event

    def request_device_switch(
        self,
        mic_device: AudioDevice | None = None,
        loopback_device: AudioDevice | None = None,
    ) -> None:
        """Request a device switch during recording.

        Args:
            mic_device: New microphone device (None to keep current).
            loopback_device: New loopback device (None to keep current).
        """
        with self._device_switch_lock:
            self._pending_mic_device = mic_device
            self._pending_loopback_device = loopback_device
            self._device_switch_event.set()

    def get_pending_switch(self) -> tuple[AudioDevice | None, AudioDevice | None]:
        """Get and clear the pending device switch request.

        Returns:
            Tuple of (mic_device, loopback_device) that were requested.
            Either may be None if not changing.
        """
        with self._device_switch_lock:
            mic = self._pending_mic_device
            loopback = self._pending_loopback_device
            self._pending_mic_device = None
            self._pending_loopback_device = None
            self._device_switch_event.clear()
            return mic, loopback

    def update_devices(
        self,
        mic_device: AudioDevice | None = None,
        loopback_device: AudioDevice | None = None,
    ) -> None:
        """Update the current devices after a successful switch.

        Args:
            mic_device: New microphone device (None to keep current).
            loopback_device: New loopback device (None to keep current).
        """
        if mic_device is not None:
            self.mic_device = mic_device
        if loopback_device is not None:
            self.loopback_device = loopback_device

    def set_device_error_callback(
        self, callback: Callable[[DeviceError], None] | None
    ) -> None:
        """Set the callback to be invoked when a device error occurs.

        Args:
            callback: Function to call with DeviceError when an error occurs.
                      Set to None to disable callback.
        """
        self._device_error_callback = callback

    def handle_device_error(self, error: DeviceError) -> None:
        """Handle a device error by updating state and calling callback.

        Args:
            error: The device error that occurred.
        """
        self.state.device_error = error
        self.state.is_partial_save = True
        if self._device_error_callback:
            self._device_error_callback(error)


class AudioCaptureBase(ABC):
    """Base class for audio capture implementations."""

    @abstractmethod
    def start_recording(self, session: RecordingSession) -> None:
        """Start recording audio."""
        ...

    @abstractmethod
    def stop_recording(self, session: RecordingSession) -> None:
        """Stop recording audio."""
        ...


class AudioCapture(AudioCaptureBase):
    """Main audio capture implementation using WASAPI backend."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings.default()
        self._backend = WasapiBackend(self._settings.audio)
        self._device_manager = DeviceManager()

    def initialize(self) -> None:
        """Initialize the audio capture system."""
        self._device_manager.initialize()
        self._backend.initialize()

    def terminate(self) -> None:
        """Cleanup resources."""
        self._backend.terminate()

    @property
    def device_manager(self) -> DeviceManager:
        """Get the device manager."""
        return self._device_manager

    def create_session(
        self,
        mode: RecordingMode,
        output_path: Path | None = None,
        mic_device_index: int | None = None,
        loopback_device_index: int | None = None,
        stereo_split: bool = True,
        aec_enabled: bool = False,
        aec_filter_multiplier: int = 30,
        mic_gain: float = 1.5,
        loopback_gain: float = 1.0,
        mix_ratio: float = 0.5,
        direct_mp3: bool = True,
        mp3_bitrate: int = 128,
    ) -> RecordingSession:
        """Create a new recording session.

        Args:
            mode: Recording mode (LOOPBACK, MIC, or BOTH)
            output_path: Output file path (auto-generated if None)
            mic_device_index: Specific mic device index (default device if None)
            loopback_device_index: Specific loopback device index (default if None)
            stereo_split: For BOTH mode - True: left=mic, right=system. False: mixed.
            aec_enabled: For BOTH mode - Enable acoustic echo cancellation.
            aec_filter_multiplier: AEC filter strength multiplier (5-100, default: 30).
            mic_gain: Microphone gain multiplier.
            loopback_gain: System audio gain multiplier.
            mix_ratio: Mic/system mix ratio (0.0-1.0, higher = more mic).
            direct_mp3: Enable direct MP3 output (default: True for MP3 format).
            mp3_bitrate: MP3 bitrate in kbps (default: 128).
        """
        # Generate output filename if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".mp3" if direct_mp3 else ".wav"
            filename = f"recording_{timestamp}{ext}"
            output_path = self._settings.output.output_dir / filename

        # Get devices based on mode
        mic_device = None
        loopback_device = None

        if mode in (RecordingMode.MIC, RecordingMode.BOTH):
            if mic_device_index is not None:
                mic_device = self._device_manager.get_device_by_index(mic_device_index)
            else:
                mic_device = self._device_manager.get_default_input_device()

            if mic_device is None:
                raise RuntimeError("No microphone device found")

        if mode in (RecordingMode.LOOPBACK, RecordingMode.BOTH):
            if loopback_device_index is not None:
                loopback_device = self._device_manager.get_device_by_index(
                    loopback_device_index
                )
            else:
                loopback_device = self._device_manager.get_default_loopback_device()

            if loopback_device is None:
                raise RuntimeError("No loopback device found")

        return RecordingSession(
            mode=mode,
            output_path=output_path,
            mic_device=mic_device,
            loopback_device=loopback_device,
            stereo_split=stereo_split,
            aec_enabled=aec_enabled,
            aec_filter_multiplier=aec_filter_multiplier,
            mic_gain=mic_gain,
            loopback_gain=loopback_gain,
            mix_ratio=mix_ratio,
            direct_mp3=direct_mp3,
            mp3_bitrate=mp3_bitrate,
        )

    def start_recording(self, session: RecordingSession) -> None:
        """Start recording in a background thread."""
        if session.state.is_recording:
            raise RuntimeError("Recording is already in progress")

        session.state.is_recording = True
        session.state.start_time = datetime.now()
        session.state.output_file = session.output_path
        session.state.bytes_recorded = 0
        session.state.error = None

        def on_chunk(data: bytes) -> None:
            session.state.bytes_recorded += len(data)

        def record_worker() -> None:
            from omr.core.encoder import StreamingMP3Encoder

            writer = None
            try:
                # Create MP3 encoder if direct_mp3 is enabled
                if session.direct_mp3:
                    # Determine sample rate and channels based on mode
                    if session.mode == RecordingMode.BOTH:
                        # BOTH mode outputs stereo (2 channels) at loopback's sample rate
                        if session.loopback_device:
                            sample_rate = int(session.loopback_device.default_sample_rate)
                        else:
                            sample_rate = 48000
                        channels = 2
                    elif session.mode == RecordingMode.LOOPBACK and session.loopback_device:
                        sample_rate = int(session.loopback_device.default_sample_rate)
                        channels = session.loopback_device.channels or 2
                    elif session.mode == RecordingMode.MIC and session.mic_device:
                        sample_rate = int(session.mic_device.default_sample_rate)
                        channels = session.mic_device.channels or 1
                    else:
                        sample_rate = 48000
                        channels = 2

                    writer = StreamingMP3Encoder(
                        output_path=session.output_path,
                        sample_rate=sample_rate,
                        channels=channels,
                        bitrate=session.mp3_bitrate,
                    )

                def on_single_device_switch() -> AudioDevice | None:
                    """Callback for single device switching."""
                    mic, loopback = session.get_pending_switch()
                    new_device = None
                    if session.mode == RecordingMode.LOOPBACK and loopback:
                        new_device = loopback
                        session.update_devices(loopback_device=loopback)
                    elif session.mode == RecordingMode.MIC and mic:
                        new_device = mic
                        session.update_devices(mic_device=mic)
                    return new_device

                if session.mode == RecordingMode.LOOPBACK and session.loopback_device:
                    self._backend.record_to_file(
                        device=session.loopback_device,
                        output_path=session.output_path,
                        stop_event=session.stop_event,
                        on_chunk=on_chunk,
                        writer=writer,
                        device_switch_event=session.device_switch_event,
                        on_device_switch=on_single_device_switch,
                        on_device_error=session.handle_device_error,
                    )
                elif session.mode == RecordingMode.MIC and session.mic_device:
                    self._backend.record_to_file(
                        device=session.mic_device,
                        output_path=session.output_path,
                        stop_event=session.stop_event,
                        on_chunk=on_chunk,
                        writer=writer,
                        device_switch_event=session.device_switch_event,
                        on_device_switch=on_single_device_switch,
                        on_device_error=session.handle_device_error,
                    )
                elif session.mode == RecordingMode.BOTH:
                    if session.mic_device and session.loopback_device:

                        def on_dual_device_switch() -> (
                            tuple[AudioDevice | None, AudioDevice | None]
                        ):
                            """Callback for dual device switching."""
                            mic, loopback = session.get_pending_switch()
                            if mic:
                                session.update_devices(mic_device=mic)
                            if loopback:
                                session.update_devices(loopback_device=loopback)
                            return mic, loopback

                        def on_find_alternative(
                            source: str, current_device: AudioDevice
                        ) -> AudioDevice | None:
                            """Find alternative device when error occurs."""
                            self._device_manager.refresh_devices()
                            alternative = self._device_manager.get_alternative_device(
                                current_device
                            )
                            if alternative:
                                # Update session with new device
                                if source == "mic":
                                    session.update_devices(mic_device=alternative)
                                else:
                                    session.update_devices(loopback_device=alternative)
                            return alternative

                        self._backend.record_dual_to_file(
                            mic_device=session.mic_device,
                            loopback_device=session.loopback_device,
                            output_path=session.output_path,
                            stop_event=session.stop_event,
                            stereo_split=session.stereo_split,
                            aec_enabled=session.aec_enabled,
                            aec_filter_multiplier=session.aec_filter_multiplier,
                            mic_gain=session.mic_gain,
                            loopback_gain=session.loopback_gain,
                            mix_ratio=session.mix_ratio,
                            on_chunk=on_chunk,
                            writer=writer,
                            device_switch_event=session.device_switch_event,
                            on_device_switch=on_dual_device_switch,
                            on_device_error=session.handle_device_error,
                            on_find_alternative=on_find_alternative,
                        )
                    else:
                        raise RuntimeError(
                            "Both mic and loopback devices are required for BOTH mode"
                        )
            except Exception as e:
                session.state.error = str(e)
            finally:
                # Ensure writer is closed to prevent resource leaks
                if writer is not None:
                    with contextlib.suppress(Exception):
                        writer.close()
                session.state.is_recording = False

        session._recording_thread = threading.Thread(target=record_worker, daemon=True)
        session._recording_thread.start()

    def stop_recording(self, session: RecordingSession) -> None:
        """Stop the recording."""
        session.request_stop()
        if session._recording_thread is not None:
            session._recording_thread.join(timeout=5.0)

    def __enter__(self) -> "AudioCapture":
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        self.terminate()
