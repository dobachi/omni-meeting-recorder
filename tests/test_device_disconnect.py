"""Integration tests for device disconnect handling."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from omr.core.audio_capture import RecordingSession, RecordingState
from omr.core.device_errors import DeviceError, DeviceErrorType
from omr.core.device_manager import AudioDevice, DeviceManager, DeviceType


class TestRecordingStateWithError:
    """Tests for RecordingState with device error fields."""

    def test_initial_state_no_error(self) -> None:
        """Test that initial state has no device error."""
        state = RecordingState()
        assert state.device_error is None
        assert state.is_partial_save is False

    def test_state_with_device_error(self) -> None:
        """Test setting device error on state."""
        state = RecordingState()
        error = DeviceError(
            source="mic",
            error_type=DeviceErrorType.DISCONNECTED,
            message="Device removed",
        )
        state.device_error = error
        state.is_partial_save = True

        assert state.device_error is not None
        assert state.device_error.source == "mic"
        assert state.is_partial_save is True


class TestRecordingSessionDeviceError:
    """Tests for RecordingSession device error handling."""

    def test_set_device_error_callback(self) -> None:
        """Test setting device error callback."""
        from pathlib import Path
        from omr.config.settings import RecordingMode

        session = RecordingSession(
            mode=RecordingMode.BOTH,
            output_path=Path("/tmp/test.mp3"),
        )

        callback_called = False
        received_error: DeviceError | None = None

        def error_callback(error: DeviceError) -> None:
            nonlocal callback_called, received_error
            callback_called = True
            received_error = error

        session.set_device_error_callback(error_callback)

        # Simulate device error
        test_error = DeviceError(
            source="mic",
            error_type=DeviceErrorType.DISCONNECTED,
            message="USB device removed",
        )
        session.handle_device_error(test_error)

        assert callback_called is True
        assert received_error is not None
        assert received_error.source == "mic"
        assert session.state.device_error is test_error
        assert session.state.is_partial_save is True

    def test_handle_device_error_without_callback(self) -> None:
        """Test handling device error without a callback set."""
        from pathlib import Path
        from omr.config.settings import RecordingMode

        session = RecordingSession(
            mode=RecordingMode.MIC,
            output_path=Path("/tmp/test.mp3"),
        )

        test_error = DeviceError(
            source="mic",
            error_type=DeviceErrorType.DISCONNECTED,
            message="Device removed",
        )

        # Should not raise even without callback
        session.handle_device_error(test_error)

        assert session.state.device_error is test_error
        assert session.state.is_partial_save is True


class TestDeviceManagerAlternativeDevice:
    """Tests for DeviceManager alternative device search."""

    def test_get_alternative_device_none_available(self) -> None:
        """Test when no alternative device is available."""
        manager = DeviceManager()
        manager._devices = [
            AudioDevice(
                index=1,
                name="Test Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=48000.0,
                is_default=True,
            )
        ]
        manager._initialized = True

        current = manager._devices[0]
        alternative = manager.get_alternative_device(current)

        assert alternative is None

    def test_get_alternative_device_found(self) -> None:
        """Test finding an alternative device."""
        manager = DeviceManager()
        manager._devices = [
            AudioDevice(
                index=1,
                name="Primary Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=48000.0,
                is_default=True,
            ),
            AudioDevice(
                index=2,
                name="Secondary Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=44100.0,
                is_default=False,
            ),
        ]
        manager._initialized = True

        current = manager._devices[0]
        alternative = manager.get_alternative_device(current)

        assert alternative is not None
        assert alternative.index == 2
        assert alternative.name == "Secondary Mic"

    def test_get_alternative_device_prefers_default(self) -> None:
        """Test that default device is preferred."""
        manager = DeviceManager()
        manager._devices = [
            AudioDevice(
                index=1,
                name="Old Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=48000.0,
                is_default=False,
            ),
            AudioDevice(
                index=2,
                name="Default Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=48000.0,
                is_default=True,
            ),
            AudioDevice(
                index=3,
                name="Another Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=44100.0,
                is_default=False,
            ),
        ]
        manager._initialized = True

        current = manager._devices[0]  # Old Mic
        alternative = manager.get_alternative_device(current)

        assert alternative is not None
        assert alternative.index == 2
        assert alternative.is_default is True

    def test_get_alternative_device_with_exclusions(self) -> None:
        """Test excluding specific devices."""
        manager = DeviceManager()
        manager._devices = [
            AudioDevice(
                index=1,
                name="Mic 1",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=48000.0,
                is_default=False,
            ),
            AudioDevice(
                index=2,
                name="Mic 2 (broken)",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=48000.0,
                is_default=False,
            ),
            AudioDevice(
                index=3,
                name="Mic 3",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=44100.0,
                is_default=False,
            ),
        ]
        manager._initialized = True

        current = manager._devices[0]  # Mic 1
        # Exclude both Mic 1 (current) and Mic 2 (index 2)
        alternative = manager.get_alternative_device(current, exclude_indices=[2])

        assert alternative is not None
        assert alternative.index == 3
        assert alternative.name == "Mic 3"

    def test_get_alternative_device_loopback(self) -> None:
        """Test finding alternative loopback device."""
        manager = DeviceManager()
        manager._devices = [
            AudioDevice(
                index=1,
                name="Speaker [Loopback]",
                device_type=DeviceType.LOOPBACK,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=48000.0,
                is_default=True,
            ),
            AudioDevice(
                index=2,
                name="Headphones [Loopback]",
                device_type=DeviceType.LOOPBACK,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=48000.0,
                is_default=False,
            ),
            AudioDevice(
                index=3,
                name="Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=48000.0,
                is_default=True,
            ),
        ]
        manager._initialized = True

        current = manager._devices[0]  # Speaker [Loopback]
        alternative = manager.get_alternative_device(current)

        assert alternative is not None
        assert alternative.device_type == DeviceType.LOOPBACK
        assert alternative.index == 2


class TestDeviceDisconnectSimulation:
    """Tests simulating device disconnect scenarios."""

    def test_error_callback_invocation(self) -> None:
        """Test that error callback is invoked on device disconnect."""
        from pathlib import Path
        from omr.config.settings import RecordingMode

        session = RecordingSession(
            mode=RecordingMode.BOTH,
            output_path=Path("/tmp/test.mp3"),
        )

        errors_received: list[DeviceError] = []

        def error_callback(error: DeviceError) -> None:
            errors_received.append(error)

        session.set_device_error_callback(error_callback)

        # Simulate mic disconnect
        mic_error = DeviceError(
            source="mic",
            error_type=DeviceErrorType.DISCONNECTED,
            message="USB device removed",
            can_recover=True,
        )
        session.handle_device_error(mic_error)

        assert len(errors_received) == 1
        assert errors_received[0].source == "mic"
        assert errors_received[0].is_disconnection is True

    def test_partial_save_flag_set(self) -> None:
        """Test that partial save flag is set after device error."""
        from pathlib import Path
        from omr.config.settings import RecordingMode

        session = RecordingSession(
            mode=RecordingMode.LOOPBACK,
            output_path=Path("/tmp/test.mp3"),
        )

        assert session.state.is_partial_save is False

        error = DeviceError(
            source="loopback",
            error_type=DeviceErrorType.DISCONNECTED,
            message="HDMI audio device removed",
        )
        session.handle_device_error(error)

        assert session.state.is_partial_save is True
        assert session.state.device_error is error
