"""Audio capture abstraction layer."""

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from omr.backends.wasapi import WasapiBackend
from omr.config.settings import RecordingMode, Settings
from omr.core.device_manager import AudioDevice, DeviceManager


@dataclass
class RecordingState:
    """Current state of a recording session."""

    is_recording: bool = False
    start_time: datetime | None = None
    output_file: Path | None = None
    bytes_recorded: int = 0
    error: str | None = None


@dataclass
class RecordingSession:
    """Manages a recording session."""

    mode: RecordingMode
    output_path: Path
    mic_device: AudioDevice | None = None
    loopback_device: AudioDevice | None = None
    stereo_split: bool = True  # For BOTH mode: True=left:mic/right:system
    state: RecordingState = field(default_factory=RecordingState)
    _stop_event: threading.Event = field(default_factory=threading.Event)
    _recording_thread: threading.Thread | None = None

    def request_stop(self) -> None:
        """Request the recording to stop."""
        self._stop_event.set()

    @property
    def stop_event(self) -> threading.Event:
        """Get the stop event."""
        return self._stop_event


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
    ) -> RecordingSession:
        """Create a new recording session.

        Args:
            mode: Recording mode (LOOPBACK, MIC, or BOTH)
            output_path: Output file path (auto-generated if None)
            mic_device_index: Specific mic device index (default device if None)
            loopback_device_index: Specific loopback device index (default if None)
            stereo_split: For BOTH mode - True: left=mic, right=system. False: mixed.
        """
        # Generate output filename if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
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
            try:
                if session.mode == RecordingMode.LOOPBACK and session.loopback_device:
                    self._backend.record_to_file(
                        device=session.loopback_device,
                        output_path=session.output_path,
                        stop_event=session.stop_event,
                        on_chunk=on_chunk,
                    )
                elif session.mode == RecordingMode.MIC and session.mic_device:
                    self._backend.record_to_file(
                        device=session.mic_device,
                        output_path=session.output_path,
                        stop_event=session.stop_event,
                        on_chunk=on_chunk,
                    )
                elif session.mode == RecordingMode.BOTH:
                    if session.mic_device and session.loopback_device:
                        self._backend.record_dual_to_file(
                            mic_device=session.mic_device,
                            loopback_device=session.loopback_device,
                            output_path=session.output_path,
                            stop_event=session.stop_event,
                            stereo_split=session.stereo_split,
                            on_chunk=on_chunk,
                        )
                    else:
                        raise RuntimeError(
                            "Both mic and loopback devices are required for BOTH mode"
                        )
            except Exception as e:
                session.state.error = str(e)
            finally:
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
