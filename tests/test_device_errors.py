"""Tests for device error handling."""


from omr.core.device_errors import DeviceError, DeviceErrorType


class TestDeviceErrorType:
    """Tests for DeviceErrorType enum."""

    def test_enum_values_exist(self) -> None:
        """Test that all expected error types exist."""
        assert DeviceErrorType.DISCONNECTED is not None
        assert DeviceErrorType.ACCESS_DENIED is not None
        assert DeviceErrorType.UNKNOWN is not None


class TestDeviceError:
    """Tests for DeviceError class."""

    def test_create_device_error(self) -> None:
        """Test basic DeviceError creation."""
        error = DeviceError(
            source="mic",
            error_type=DeviceErrorType.DISCONNECTED,
            message="Device was disconnected",
            can_recover=True,
        )
        assert error.source == "mic"
        assert error.error_type == DeviceErrorType.DISCONNECTED
        assert error.message == "Device was disconnected"
        assert error.can_recover is True

    def test_default_values(self) -> None:
        """Test default values for DeviceError."""
        error = DeviceError(source="loopback", error_type=DeviceErrorType.UNKNOWN)
        assert error.message == ""
        assert error.can_recover is True

    def test_is_disconnection_property(self) -> None:
        """Test is_disconnection property."""
        disconnected = DeviceError(
            source="mic", error_type=DeviceErrorType.DISCONNECTED
        )
        assert disconnected.is_disconnection is True

        access_denied = DeviceError(
            source="mic", error_type=DeviceErrorType.ACCESS_DENIED
        )
        assert access_denied.is_disconnection is False

        unknown = DeviceError(source="mic", error_type=DeviceErrorType.UNKNOWN)
        assert unknown.is_disconnection is False

    def test_str_representation(self) -> None:
        """Test string representation."""
        error = DeviceError(
            source="mic",
            error_type=DeviceErrorType.DISCONNECTED,
            message="USB device removed",
        )
        result = str(error)
        assert "mic" in result
        assert "disconnected" in result
        assert "USB device removed" in result


class TestDeviceErrorFromException:
    """Tests for DeviceError.from_exception class method."""

    def test_from_oserror_disconnected(self) -> None:
        """Test creating DeviceError from OSError with disconnect errno."""
        # PyAudio error code for paNotInitialized (device removed)
        exc = OSError(-9996, "Device unavailable")
        exc.errno = -9996

        error = DeviceError.from_exception("mic", exc)
        assert error.source == "mic"
        assert error.error_type == DeviceErrorType.DISCONNECTED
        assert error.can_recover is True

    def test_from_oserror_internal_error(self) -> None:
        """Test creating DeviceError from OSError with internal error."""
        exc = OSError(-9999, "Internal error")
        exc.errno = -9999

        error = DeviceError.from_exception("loopback", exc)
        assert error.error_type == DeviceErrorType.DISCONNECTED
        assert error.can_recover is True

    def test_from_oserror_host_error(self) -> None:
        """Test creating DeviceError from OSError with host error."""
        exc = OSError(-9988, "Unanticipated host error")
        exc.errno = -9988

        error = DeviceError.from_exception("mic", exc)
        assert error.error_type == DeviceErrorType.DISCONNECTED

    def test_from_oserror_invalid_device(self) -> None:
        """Test creating DeviceError from OSError with invalid device."""
        exc = OSError(-9997, "Invalid device")
        exc.errno = -9997

        error = DeviceError.from_exception("mic", exc)
        assert error.error_type == DeviceErrorType.ACCESS_DENIED
        assert error.can_recover is True

    def test_from_generic_exception(self) -> None:
        """Test creating DeviceError from generic exception."""
        exc = Exception("Some error occurred")

        error = DeviceError.from_exception("loopback", exc)
        assert error.error_type == DeviceErrorType.UNKNOWN
        assert error.can_recover is False
        assert "Some error occurred" in error.message

    def test_from_exception_with_disconnect_message(self) -> None:
        """Test DeviceError detection from exception message patterns."""
        exc = Exception("Audio device was disconnected")

        error = DeviceError.from_exception("mic", exc)
        assert error.error_type == DeviceErrorType.DISCONNECTED
        assert error.can_recover is True

    def test_from_exception_with_removed_message(self) -> None:
        """Test DeviceError detection from removed device message."""
        exc = RuntimeError("Device removed unexpectedly")

        error = DeviceError.from_exception("mic", exc)
        assert error.error_type == DeviceErrorType.DISCONNECTED

    def test_from_exception_preserves_source(self) -> None:
        """Test that source is preserved correctly."""
        exc = Exception("Error")

        mic_error = DeviceError.from_exception("mic", exc)
        assert mic_error.source == "mic"

        loopback_error = DeviceError.from_exception("loopback", exc)
        assert loopback_error.source == "loopback"


class TestDeviceErrorRecovery:
    """Tests for error recovery scenarios."""

    def test_disconnected_error_is_recoverable(self) -> None:
        """Test that disconnected errors are marked as recoverable."""
        error = DeviceError.from_exception(
            "mic", OSError(-9996, "Device disconnected")
        )
        # Set errno manually for the test
        error.can_recover = True
        assert error.can_recover is True

    def test_unknown_error_not_recoverable(self) -> None:
        """Test that unknown errors are not recoverable by default."""
        error = DeviceError.from_exception("mic", ValueError("Unexpected error"))
        assert error.error_type == DeviceErrorType.UNKNOWN
        assert error.can_recover is False
