"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_pyaudio():
    """Mock PyAudioWPatch for testing without audio hardware."""
    with patch.dict("sys.modules", {"pyaudiowpatch": MagicMock()}):
        yield


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for output files."""
    output_dir = tmp_path / "recordings"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_device_info():
    """Sample device information for testing."""
    return {
        "index": 0,
        "name": "Test Microphone",
        "maxInputChannels": 2,
        "maxOutputChannels": 0,
        "defaultSampleRate": 44100.0,
        "hostApi": 0,
        "isLoopbackDevice": False,
    }


@pytest.fixture
def mock_loopback_device_info():
    """Sample loopback device information for testing."""
    return {
        "index": 1,
        "name": "Test Speaker [Loopback]",
        "maxInputChannels": 0,
        "maxOutputChannels": 2,
        "defaultSampleRate": 48000.0,
        "hostApi": 0,
        "isLoopbackDevice": True,
    }
