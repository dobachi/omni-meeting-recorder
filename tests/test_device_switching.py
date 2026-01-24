"""Tests for device switching functionality."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from omr.config.settings import RecordingMode
from omr.core.device_manager import AudioDevice, DeviceType


class TestRecordingSessionDeviceSwitching:
    """Tests for device switching in RecordingSession."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock recording session with device switching support."""
        from omr.core.audio_capture import RecordingSession

        mic_device = AudioDevice(
            index=0,
            name="Test Microphone",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=1,
            default_sample_rate=44100.0,
            is_default=True,
        )

        loopback_device = AudioDevice(
            index=1,
            name="Test Loopback",
            device_type=DeviceType.LOOPBACK,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=48000.0,
            is_default=True,
        )

        session = RecordingSession(
            mode=RecordingMode.BOTH,
            output_path=Path("/tmp/test.mp3"),
            mic_device=mic_device,
            loopback_device=loopback_device,
        )
        return session

    def test_device_switch_event_initial_state(self, mock_session):
        """Test device switch event is initially not set."""
        assert not mock_session.device_switch_event.is_set()

    def test_request_device_switch_mic(self, mock_session):
        """Test requesting mic device switch."""
        new_mic = AudioDevice(
            index=2,
            name="New Microphone",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=1,
            default_sample_rate=44100.0,
            is_default=False,
        )

        mock_session.request_device_switch(mic_device=new_mic)

        assert mock_session.device_switch_event.is_set()

    def test_request_device_switch_loopback(self, mock_session):
        """Test requesting loopback device switch."""
        new_loopback = AudioDevice(
            index=3,
            name="New Loopback",
            device_type=DeviceType.LOOPBACK,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=48000.0,
            is_default=False,
        )

        mock_session.request_device_switch(loopback_device=new_loopback)

        assert mock_session.device_switch_event.is_set()

    def test_request_device_switch_both(self, mock_session):
        """Test requesting both device switch."""
        new_mic = AudioDevice(
            index=2,
            name="New Microphone",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=1,
            default_sample_rate=44100.0,
            is_default=False,
        )
        new_loopback = AudioDevice(
            index=3,
            name="New Loopback",
            device_type=DeviceType.LOOPBACK,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=48000.0,
            is_default=False,
        )

        mock_session.request_device_switch(mic_device=new_mic, loopback_device=new_loopback)

        assert mock_session.device_switch_event.is_set()

    def test_get_pending_switch(self, mock_session):
        """Test getting and clearing pending switch."""
        new_mic = AudioDevice(
            index=2,
            name="New Microphone",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=1,
            default_sample_rate=44100.0,
            is_default=False,
        )

        mock_session.request_device_switch(mic_device=new_mic)

        # Get pending switch
        mic, loopback = mock_session.get_pending_switch()

        assert mic is not None
        assert mic.name == "New Microphone"
        assert loopback is None

        # Event should be cleared
        assert not mock_session.device_switch_event.is_set()

        # Second call should return None, None
        mic2, loopback2 = mock_session.get_pending_switch()
        assert mic2 is None
        assert loopback2 is None

    def test_update_devices(self, mock_session):
        """Test updating session devices after switch."""
        original_mic = mock_session.mic_device
        new_mic = AudioDevice(
            index=2,
            name="New Microphone",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=1,
            default_sample_rate=44100.0,
            is_default=False,
        )

        mock_session.update_devices(mic_device=new_mic)

        assert mock_session.mic_device is new_mic
        assert mock_session.mic_device is not original_mic

    def test_update_devices_none_keeps_current(self, mock_session):
        """Test updating with None keeps current device."""
        original_mic = mock_session.mic_device
        original_loopback = mock_session.loopback_device

        mock_session.update_devices(mic_device=None, loopback_device=None)

        assert mock_session.mic_device is original_mic
        assert mock_session.loopback_device is original_loopback

    def test_thread_safety(self, mock_session):
        """Test device switching is thread-safe."""
        new_devices = []
        for i in range(10):
            new_devices.append(
                AudioDevice(
                    index=i + 10,
                    name=f"Device {i}",
                    device_type=DeviceType.INPUT,
                    host_api="WASAPI",
                    channels=1,
                    default_sample_rate=44100.0,
                    is_default=False,
                )
            )

        errors = []

        def request_switch(device):
            try:
                mock_session.request_device_switch(mic_device=device)
                mock_session.get_pending_switch()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=request_switch, args=(d,))
            for d in new_devices
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestDeviceSwitchingIntegration:
    """Integration tests for device switching."""

    @pytest.fixture
    def mock_audio_devices(self):
        """Create mock audio devices."""
        mic1 = AudioDevice(
            index=0,
            name="Mic 1",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=1,
            default_sample_rate=44100.0,
            is_default=True,
        )
        mic2 = AudioDevice(
            index=1,
            name="Mic 2",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=1,
            default_sample_rate=48000.0,
            is_default=False,
        )
        loopback1 = AudioDevice(
            index=2,
            name="Loopback 1",
            device_type=DeviceType.LOOPBACK,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=48000.0,
            is_default=True,
        )
        loopback2 = AudioDevice(
            index=3,
            name="Loopback 2",
            device_type=DeviceType.LOOPBACK,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=44100.0,
            is_default=False,
        )
        return {
            "mic1": mic1,
            "mic2": mic2,
            "loopback1": loopback1,
            "loopback2": loopback2,
        }

    def test_device_switch_callback_pattern(self, mock_audio_devices):
        """Test the callback pattern used for device switching."""
        from omr.core.audio_capture import RecordingSession

        session = RecordingSession(
            mode=RecordingMode.BOTH,
            output_path=Path("/tmp/test.mp3"),
            mic_device=mock_audio_devices["mic1"],
            loopback_device=mock_audio_devices["loopback1"],
        )

        # Simulate what the CLI does
        session.request_device_switch(mic_device=mock_audio_devices["mic2"])

        # Simulate what the backend callback does
        def on_device_switch():
            mic, loopback = session.get_pending_switch()
            if mic:
                session.update_devices(mic_device=mic)
            if loopback:
                session.update_devices(loopback_device=loopback)
            return mic, loopback

        # Check event is set
        assert session.device_switch_event.is_set()

        # Call the callback
        new_mic, new_loopback = on_device_switch()

        # Verify results
        assert new_mic is mock_audio_devices["mic2"]
        assert new_loopback is None
        assert session.mic_device is mock_audio_devices["mic2"]
        assert not session.device_switch_event.is_set()

    def test_multiple_rapid_switches(self, mock_audio_devices):
        """Test handling multiple rapid switch requests."""
        from omr.core.audio_capture import RecordingSession

        session = RecordingSession(
            mode=RecordingMode.BOTH,
            output_path=Path("/tmp/test.mp3"),
            mic_device=mock_audio_devices["mic1"],
            loopback_device=mock_audio_devices["loopback1"],
        )

        # Request multiple switches rapidly
        session.request_device_switch(mic_device=mock_audio_devices["mic2"])
        session.request_device_switch(loopback_device=mock_audio_devices["loopback2"])

        # Only the last request should be pending
        mic, loopback = session.get_pending_switch()

        # The loopback should be set (last request)
        assert loopback is mock_audio_devices["loopback2"]
