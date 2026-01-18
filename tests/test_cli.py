"""Tests for CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from omr.cli.main import app
from omr.core.device_manager import AudioDevice, DeviceType

runner = CliRunner()


class TestMainCLI:
    """Tests for main CLI commands."""

    def test_version_flag(self):
        """Test --version flag shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "Omni Meeting Recorder" in result.stdout
        assert "0.1.0" in result.stdout

    def test_help(self):
        """Test --help flag shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Omni Meeting Recorder" in result.stdout
        assert "devices" in result.stdout
        assert "record" in result.stdout


class TestDevicesCommand:
    """Tests for devices command."""

    @patch("omr.cli.commands.devices.DeviceManager")
    def test_devices_list_empty(self, mock_manager_class):
        """Test devices command when no devices found."""
        mock_manager = MagicMock()
        mock_manager.get_input_devices.return_value = []
        mock_manager.get_loopback_devices.return_value = []
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(app, ["devices"])
        assert result.exit_code == 1
        assert "No devices found" in result.stdout

    @patch("omr.cli.commands.devices.DeviceManager")
    def test_devices_list_with_devices(self, mock_manager_class):
        """Test devices command with available devices."""
        mock_manager = MagicMock()
        test_devices = [
            AudioDevice(
                index=0,
                name="Test Microphone",
                device_type=DeviceType.INPUT,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=44100.0,
                is_default=True,
            ),
            AudioDevice(
                index=1,
                name="Test Loopback",
                device_type=DeviceType.LOOPBACK,
                host_api="WASAPI",
                channels=2,
                default_sample_rate=48000.0,
                is_default=False,
            ),
        ]
        mock_manager.get_input_devices.return_value = [test_devices[0]]
        mock_manager.get_loopback_devices.return_value = [test_devices[1]]
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(app, ["devices"])
        assert result.exit_code == 0
        assert "Test Microphone" in result.stdout
        assert "Test Loopback" in result.stdout

    @patch("omr.cli.commands.devices.DeviceManager")
    def test_devices_mic_only(self, mock_manager_class):
        """Test devices command with --mic flag."""
        mock_manager = MagicMock()
        test_mic = AudioDevice(
            index=0,
            name="Test Microphone",
            device_type=DeviceType.INPUT,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=44100.0,
            is_default=True,
        )
        mock_manager.get_input_devices.return_value = [test_mic]
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(app, ["devices", "--mic"])
        assert result.exit_code == 0
        assert "Test Microphone" in result.stdout
        assert "Microphone Devices" in result.stdout

    @patch("omr.cli.commands.devices.DeviceManager")
    def test_devices_loopback_only(self, mock_manager_class):
        """Test devices command with --loopback flag."""
        mock_manager = MagicMock()
        test_loopback = AudioDevice(
            index=1,
            name="Test Loopback",
            device_type=DeviceType.LOOPBACK,
            host_api="WASAPI",
            channels=2,
            default_sample_rate=48000.0,
        )
        mock_manager.get_loopback_devices.return_value = [test_loopback]
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(app, ["devices", "--loopback"])
        assert result.exit_code == 0
        assert "Test Loopback" in result.stdout
        assert "Loopback Devices" in result.stdout


class TestRecordCommand:
    """Tests for record command."""

    @patch("omr.cli.commands.record.AudioCapture")
    def test_record_start_no_loopback_device(self, mock_capture_class):
        """Test record start when no loopback device available."""
        mock_capture = MagicMock()
        mock_capture.create_session.side_effect = RuntimeError("No loopback device found")
        mock_capture_class.return_value = mock_capture

        result = runner.invoke(app, ["start", "--loopback", "--format", "wav"])
        assert result.exit_code == 1
        assert "No loopback device found" in result.stdout

    @patch("omr.cli.commands.record.AudioCapture")
    def test_record_start_no_mic_device(self, mock_capture_class):
        """Test record start when no mic device available."""
        mock_capture = MagicMock()
        mock_capture.create_session.side_effect = RuntimeError("No microphone device found")
        mock_capture_class.return_value = mock_capture

        result = runner.invoke(app, ["start", "--mic", "--format", "wav"])
        assert result.exit_code == 1
        assert "No microphone device found" in result.stdout

    def test_record_stop_info(self):
        """Test record stop command shows info message."""
        result = runner.invoke(app, ["record", "stop"])
        assert result.exit_code == 0
        assert "Ctrl+C" in result.stdout
