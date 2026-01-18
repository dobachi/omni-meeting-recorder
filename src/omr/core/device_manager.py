"""Device detection and management for audio capture."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DeviceType(Enum):
    """Type of audio device."""

    INPUT = "input"  # Microphone
    OUTPUT = "output"  # Speaker/headphone
    LOOPBACK = "loopback"  # System audio capture


@dataclass
class AudioDevice:
    """Represents an audio device."""

    index: int
    name: str
    device_type: DeviceType
    host_api: str
    channels: int
    default_sample_rate: float
    is_default: bool = False

    @property
    def display_name(self) -> str:
        """Get formatted display name for the device."""
        type_label = {
            DeviceType.INPUT: "[MIC]",
            DeviceType.OUTPUT: "[SPK]",
            DeviceType.LOOPBACK: "[LOOP]",
        }
        default_marker = " (default)" if self.is_default else ""
        return f"{type_label[self.device_type]} {self.name}{default_marker}"


class DeviceManager:
    """Manages audio device detection and selection."""

    def __init__(self) -> None:
        self._devices: list[AudioDevice] = []
        self._initialized = False

    def initialize(self) -> None:
        """Initialize and scan for available audio devices."""
        try:
            import pyaudiowpatch as pyaudio

            p = pyaudio.PyAudio()
            self._scan_devices(p)
            p.terminate()
            self._initialized = True
        except ImportError:
            raise RuntimeError(
                "PyAudioWPatch is required but not installed. "
                "Install with: pip install PyAudioWPatch"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize audio system: {e}")

    def _scan_devices(self, p: Any) -> None:
        """Scan and categorize all available audio devices."""
        self._devices.clear()

        # Get default device indices
        try:
            default_input = p.get_default_input_device_info()["index"]
        except OSError:
            default_input = -1

        try:
            default_output_info = p.get_default_output_device_info()
            default_output = default_output_info["index"]
            default_output_name = default_output_info.get("name", "")
        except OSError:
            default_output = -1
            default_output_name = ""

        # Get WASAPI host API index
        wasapi_index = self._get_wasapi_host_api_index(p)

        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
            except OSError:
                continue

            # Only process WASAPI devices for loopback support
            if info.get("hostApi") != wasapi_index:
                continue

            name = info.get("name", f"Device {i}")
            channels_in = int(info.get("maxInputChannels", 0))
            channels_out = int(info.get("maxOutputChannels", 0))
            sample_rate = float(info.get("defaultSampleRate", 44100))

            # Check if this is a loopback device
            # PyAudioWPatch marks loopback devices with isLoopbackDevice flag
            is_loopback = info.get("isLoopbackDevice", False)

            if is_loopback:
                # Check if this loopback corresponds to the default output device
                # by matching the device name (without [Loopback] suffix)
                base_name = name.replace(" [Loopback]", "")
                is_default_loopback = (
                    default_output_name and base_name in default_output_name
                ) or (default_output_name and default_output_name in base_name)

                device = AudioDevice(
                    index=i,
                    name=name,
                    device_type=DeviceType.LOOPBACK,
                    host_api="WASAPI",
                    channels=channels_in if channels_in > 0 else (channels_out if channels_out > 0 else 2),
                    default_sample_rate=sample_rate,
                    is_default=is_default_loopback,
                )
                self._devices.append(device)
            elif channels_in > 0:
                device = AudioDevice(
                    index=i,
                    name=name,
                    device_type=DeviceType.INPUT,
                    host_api="WASAPI",
                    channels=channels_in,
                    default_sample_rate=sample_rate,
                    is_default=(i == default_input),
                )
                self._devices.append(device)
            elif channels_out > 0:
                device = AudioDevice(
                    index=i,
                    name=name,
                    device_type=DeviceType.OUTPUT,
                    host_api="WASAPI",
                    channels=channels_out,
                    default_sample_rate=sample_rate,
                    is_default=(i == default_output),
                )
                self._devices.append(device)

    def _get_wasapi_host_api_index(self, p: Any) -> int:
        """Get the index of WASAPI host API."""
        for i in range(p.get_host_api_count()):
            info = p.get_host_api_info_by_index(i)
            if "WASAPI" in info.get("name", ""):
                return i
        return -1

    @property
    def devices(self) -> list[AudioDevice]:
        """Get all detected devices."""
        if not self._initialized:
            self.initialize()
        return self._devices

    def get_input_devices(self) -> list[AudioDevice]:
        """Get all input (microphone) devices."""
        return [d for d in self.devices if d.device_type == DeviceType.INPUT]

    def get_loopback_devices(self) -> list[AudioDevice]:
        """Get all loopback (system audio) devices."""
        return [d for d in self.devices if d.device_type == DeviceType.LOOPBACK]

    def get_output_devices(self) -> list[AudioDevice]:
        """Get all output (speaker) devices."""
        return [d for d in self.devices if d.device_type == DeviceType.OUTPUT]

    def get_default_input_device(self) -> AudioDevice | None:
        """Get the default input device."""
        for d in self.get_input_devices():
            if d.is_default:
                return d
        inputs = self.get_input_devices()
        return inputs[0] if inputs else None

    def get_default_loopback_device(self) -> AudioDevice | None:
        """Get the default loopback device (corresponds to default output)."""
        loopbacks = self.get_loopback_devices()
        # Prefer the loopback device marked as default
        for d in loopbacks:
            if d.is_default:
                return d
        # Fall back to first loopback device
        return loopbacks[0] if loopbacks else None

    def get_device_by_index(self, index: int) -> AudioDevice | None:
        """Get a device by its index."""
        for d in self.devices:
            if d.index == index:
                return d
        return None
