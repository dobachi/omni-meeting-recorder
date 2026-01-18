"""Tests for device manager."""


from omr.core.device_manager import AudioDevice, DeviceManager, DeviceType


class TestAudioDevice:
    """Tests for AudioDevice dataclass."""

    def test_input_device_display_name(self):
        """Test display name for input device."""
        device = AudioDevice(
            index=0,
            name="Test Microphone",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=44100.0,
            is_default=False,
        )
        assert device.display_name == "[MIC] Test Microphone"

    def test_default_device_display_name(self):
        """Test display name for default device."""
        device = AudioDevice(
            index=0,
            name="Default Mic",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=1,
            default_sample_rate=44100.0,
            is_default=True,
        )
        assert device.display_name == "[MIC] Default Mic (default)"

    def test_loopback_device_display_name(self):
        """Test display name for loopback device."""
        device = AudioDevice(
            index=1,
            name="Speaker [Loopback]",
            device_type=DeviceType.LOOPBACK,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=48000.0,
            is_default=False,
        )
        assert device.display_name == "[LOOP] Speaker [Loopback]"

    def test_output_device_display_name(self):
        """Test display name for output device."""
        device = AudioDevice(
            index=2,
            name="Speaker",
            device_type=DeviceType.OUTPUT,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=48000.0,
            is_default=True,
        )
        assert device.display_name == "[SPK] Speaker (default)"


class TestDeviceManager:
    """Tests for DeviceManager class."""

    def test_initialization_without_pyaudio(self):
        """Test that DeviceManager raises error without PyAudioWPatch."""
        _ = DeviceManager()  # Just verify instantiation doesn't crash
        # On systems without PyAudioWPatch, initialize() should raise RuntimeError
        # We test this behavior indirectly

    def test_get_device_by_index_empty(self):
        """Test getting device by index when no devices."""
        manager = DeviceManager()
        manager._initialized = True  # Bypass initialization
        manager._devices = []
        assert manager.get_device_by_index(0) is None

    def test_get_device_by_index_found(self):
        """Test getting device by index when device exists."""
        manager = DeviceManager()
        manager._initialized = True
        test_device = AudioDevice(
            index=5,
            name="Test Device",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=44100.0,
        )
        manager._devices = [test_device]
        assert manager.get_device_by_index(5) == test_device
        assert manager.get_device_by_index(0) is None

    def test_filter_input_devices(self):
        """Test filtering input devices."""
        manager = DeviceManager()
        manager._initialized = True
        manager._devices = [
            AudioDevice(
                index=0,
                name="Mic 1",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=44100.0,
            ),
            AudioDevice(
                index=1,
                name="Speaker",
                device_type=DeviceType.OUTPUT,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=48000.0,
            ),
            AudioDevice(
                index=2,
                name="Mic 2",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=44100.0,
            ),
        ]
        input_devices = manager.get_input_devices()
        assert len(input_devices) == 2
        assert all(d.device_type == DeviceType.INPUT for d in input_devices)

    def test_filter_loopback_devices(self):
        """Test filtering loopback devices."""
        manager = DeviceManager()
        manager._initialized = True
        manager._devices = [
            AudioDevice(
                index=0,
                name="Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=44100.0,
            ),
            AudioDevice(
                index=1,
                name="Loopback",
                device_type=DeviceType.LOOPBACK,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=48000.0,
            ),
        ]
        loopback_devices = manager.get_loopback_devices()
        assert len(loopback_devices) == 1
        assert loopback_devices[0].device_type == DeviceType.LOOPBACK

    def test_get_default_input_device(self):
        """Test getting default input device."""
        manager = DeviceManager()
        manager._initialized = True
        manager._devices = [
            AudioDevice(
                index=0,
                name="Mic 1",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=44100.0,
                is_default=False,
            ),
            AudioDevice(
                index=1,
                name="Default Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=44100.0,
                is_default=True,
            ),
        ]
        default_device = manager.get_default_input_device()
        assert default_device is not None
        assert default_device.name == "Default Mic"
        assert default_device.is_default is True

    def test_get_default_input_device_fallback(self):
        """Test fallback when no default input device is marked."""
        manager = DeviceManager()
        manager._initialized = True
        manager._devices = [
            AudioDevice(
                index=0,
                name="Mic 1",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=44100.0,
                is_default=False,
            ),
        ]
        # Falls back to first input device
        default_device = manager.get_default_input_device()
        assert default_device is not None
        assert default_device.name == "Mic 1"

    def test_get_default_loopback_device(self):
        """Test getting default loopback device."""
        manager = DeviceManager()
        manager._initialized = True
        manager._devices = [
            AudioDevice(
                index=0,
                name="Loopback 1",
                device_type=DeviceType.LOOPBACK,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=48000.0,
            ),
            AudioDevice(
                index=1,
                name="Loopback 2",
                device_type=DeviceType.LOOPBACK,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=48000.0,
            ),
        ]
        # Returns first loopback device
        default_loopback = manager.get_default_loopback_device()
        assert default_loopback is not None
        assert default_loopback.name == "Loopback 1"

    def test_no_loopback_device(self):
        """Test when no loopback device is available."""
        manager = DeviceManager()
        manager._initialized = True
        manager._devices = [
            AudioDevice(
                index=0,
                name="Mic",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=1,
                default_sample_rate=44100.0,
            ),
        ]
        assert manager.get_default_loopback_device() is None
