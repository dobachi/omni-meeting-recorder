"""Device error types for audio capture."""

from dataclasses import dataclass
from enum import Enum, auto


class DeviceErrorType(Enum):
    """Type of device error."""

    DISCONNECTED = auto()  # Device was disconnected
    ACCESS_DENIED = auto()  # Access to device was denied
    UNKNOWN = auto()  # Other/unknown error


@dataclass
class DeviceError:
    """Represents a device error during recording.

    Attributes:
        source: Source of the error ("mic" or "loopback")
        error_type: Type of error that occurred
        message: Human-readable error message
        can_recover: Whether recovery (e.g., device switch) is possible
    """

    source: str  # "mic" or "loopback"
    error_type: DeviceErrorType
    message: str = ""
    can_recover: bool = True

    @classmethod
    def from_exception(cls, source: str, exception: Exception) -> "DeviceError":
        """Create a DeviceError from an exception.

        Args:
            source: Source of the error ("mic" or "loopback")
            exception: The exception that was raised

        Returns:
            DeviceError instance with appropriate type and message
        """
        # OSError with specific errno values indicate device disconnection
        # -9996: paNotInitialized (device removed)
        # -9999: paInternalError (often device disconnection)
        # -9988: paUnanticipatedHostError (device failure)
        if isinstance(exception, OSError):
            errno = getattr(exception, "errno", None)
            # Check for device-specific error attributes from PyAudio
            if errno in (-9996, -9999, -9988):
                return cls(
                    source=source,
                    error_type=DeviceErrorType.DISCONNECTED,
                    message=str(exception),
                    can_recover=True,
                )
            # Permission/access errors
            if errno in (-9997,):  # paInvalidDevice
                return cls(
                    source=source,
                    error_type=DeviceErrorType.ACCESS_DENIED,
                    message=str(exception),
                    can_recover=True,
                )

        # Check exception message for common patterns
        error_msg = str(exception).lower()
        if any(
            pattern in error_msg
            for pattern in ["device", "disconnect", "removed", "unplugged", "not found"]
        ):
            return cls(
                source=source,
                error_type=DeviceErrorType.DISCONNECTED,
                message=str(exception),
                can_recover=True,
            )

        # Default to unknown error
        return cls(
            source=source,
            error_type=DeviceErrorType.UNKNOWN,
            message=str(exception),
            can_recover=False,
        )

    @property
    def is_disconnection(self) -> bool:
        """Check if this error represents a device disconnection."""
        return self.error_type == DeviceErrorType.DISCONNECTED

    def __str__(self) -> str:
        """Return human-readable string representation."""
        type_str = {
            DeviceErrorType.DISCONNECTED: "disconnected",
            DeviceErrorType.ACCESS_DENIED: "access denied",
            DeviceErrorType.UNKNOWN: "unknown error",
        }.get(self.error_type, "error")
        return f"{self.source} device {type_str}: {self.message}"
