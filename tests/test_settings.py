"""Tests for configuration settings."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from omr.config.settings import (
    AudioFormat,
    AudioSettings,
    OutputSettings,
    RecordingMode,
    RecordingSettings,
    Settings,
)


class TestAudioSettings:
    """Tests for AudioSettings."""

    def test_default_values(self):
        """Test default audio settings."""
        settings = AudioSettings()
        assert settings.sample_rate == 44100
        assert settings.channels == 2
        assert settings.bit_depth == 16
        assert settings.chunk_size == 1024

    def test_custom_values(self):
        """Test custom audio settings."""
        settings = AudioSettings(
            sample_rate=48000,
            channels=1,
            bit_depth=24,
            chunk_size=2048,
        )
        assert settings.sample_rate == 48000
        assert settings.channels == 1
        assert settings.bit_depth == 24
        assert settings.chunk_size == 2048

    def test_sample_rate_validation(self):
        """Test sample rate validation bounds."""
        # Valid bounds
        AudioSettings(sample_rate=8000)
        AudioSettings(sample_rate=192000)

        # Invalid: too low
        with pytest.raises(ValidationError):
            AudioSettings(sample_rate=7999)

        # Invalid: too high
        with pytest.raises(ValidationError):
            AudioSettings(sample_rate=192001)

    def test_channels_validation(self):
        """Test channels validation bounds."""
        AudioSettings(channels=1)
        AudioSettings(channels=2)

        with pytest.raises(ValidationError):
            AudioSettings(channels=0)

        with pytest.raises(ValidationError):
            AudioSettings(channels=3)


class TestOutputSettings:
    """Tests for OutputSettings."""

    def test_default_values(self):
        """Test default output settings."""
        settings = OutputSettings()
        assert settings.format == AudioFormat.WAV
        assert settings.output_dir == Path(".")
        assert settings.filename_template == "recording_{timestamp}"

    def test_custom_output_dir(self):
        """Test custom output directory."""
        settings = OutputSettings(output_dir=Path("/tmp/recordings"))
        assert settings.output_dir == Path("/tmp/recordings")

    def test_audio_formats(self):
        """Test all audio format options."""
        for fmt in AudioFormat:
            settings = OutputSettings(format=fmt)
            assert settings.format == fmt


class TestRecordingSettings:
    """Tests for RecordingSettings."""

    def test_default_values(self):
        """Test default recording settings."""
        settings = RecordingSettings()
        assert settings.mode == RecordingMode.LOOPBACK
        assert settings.mic_device_index is None
        assert settings.loopback_device_index is None
        assert settings.stereo_split is False

    def test_mic_mode(self):
        """Test microphone recording mode."""
        settings = RecordingSettings(mode=RecordingMode.MIC, mic_device_index=0)
        assert settings.mode == RecordingMode.MIC
        assert settings.mic_device_index == 0

    def test_both_mode(self):
        """Test dual recording mode."""
        settings = RecordingSettings(
            mode=RecordingMode.BOTH,
            mic_device_index=0,
            loopback_device_index=1,
            stereo_split=True,
        )
        assert settings.mode == RecordingMode.BOTH
        assert settings.stereo_split is True


class TestSettings:
    """Tests for main Settings class."""

    def test_default_factory(self):
        """Test default settings factory method."""
        settings = Settings.default()
        assert isinstance(settings.audio, AudioSettings)
        assert isinstance(settings.output, OutputSettings)
        assert isinstance(settings.recording, RecordingSettings)

    def test_nested_settings(self):
        """Test nested settings modification."""
        settings = Settings(
            audio=AudioSettings(sample_rate=48000),
            output=OutputSettings(format=AudioFormat.FLAC),
            recording=RecordingSettings(mode=RecordingMode.MIC),
        )
        assert settings.audio.sample_rate == 48000
        assert settings.output.format == AudioFormat.FLAC
        assert settings.recording.mode == RecordingMode.MIC
