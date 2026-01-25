"""Tests for user configuration file functionality."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from omr.config.settings import (
    AudioConfig,
    AudioFormat,
    DeviceConfig,
    OutputConfig,
    UserConfig,
    get_config_dir,
    get_config_path,
    get_config_value,
    load_user_config,
    reset_user_config,
    save_user_config,
    update_user_config,
)


class TestDeviceConfig:
    """Tests for DeviceConfig."""

    def test_default_values(self) -> None:
        """Test default device config values."""
        config = DeviceConfig()
        assert config.mic is None
        assert config.loopback is None

    def test_custom_values(self) -> None:
        """Test custom device config values."""
        config = DeviceConfig(mic="Microphone (Realtek)", loopback="Speakers (Realtek)")
        assert config.mic == "Microphone (Realtek)"
        assert config.loopback == "Speakers (Realtek)"


class TestAudioConfig:
    """Tests for AudioConfig."""

    def test_default_values(self) -> None:
        """Test default audio config values."""
        config = AudioConfig()
        assert config.mic_gain == 1.5
        assert config.loopback_gain == 1.0
        assert config.aec_enabled is True
        assert config.stereo_split is False
        assert config.mix_ratio == 0.5

    def test_gain_validation(self) -> None:
        """Test gain value validation."""
        # Valid bounds
        AudioConfig(mic_gain=0.1)
        AudioConfig(mic_gain=10.0)

        # Invalid: too low
        with pytest.raises(ValidationError):
            AudioConfig(mic_gain=0.09)

        # Invalid: too high
        with pytest.raises(ValidationError):
            AudioConfig(mic_gain=10.1)

    def test_mix_ratio_validation(self) -> None:
        """Test mix ratio validation."""
        AudioConfig(mix_ratio=0.0)
        AudioConfig(mix_ratio=1.0)

        with pytest.raises(ValidationError):
            AudioConfig(mix_ratio=-0.1)

        with pytest.raises(ValidationError):
            AudioConfig(mix_ratio=1.1)


class TestOutputConfig:
    """Tests for OutputConfig."""

    def test_default_values(self) -> None:
        """Test default output config values."""
        config = OutputConfig()
        assert config.format == AudioFormat.MP3
        assert config.bitrate == 128
        assert config.directory is None

    def test_custom_values(self) -> None:
        """Test custom output config values."""
        config = OutputConfig(
            format=AudioFormat.WAV, bitrate=192, directory="~/Recordings"
        )
        assert config.format == AudioFormat.WAV
        assert config.bitrate == 192
        assert config.directory == "~/Recordings"

    def test_bitrate_validation(self) -> None:
        """Test bitrate validation."""
        OutputConfig(bitrate=64)
        OutputConfig(bitrate=320)

        with pytest.raises(ValidationError):
            OutputConfig(bitrate=63)

        with pytest.raises(ValidationError):
            OutputConfig(bitrate=321)


class TestUserConfig:
    """Tests for UserConfig."""

    def test_default_factory(self) -> None:
        """Test default user config factory."""
        config = UserConfig.default()
        assert isinstance(config.device, DeviceConfig)
        assert isinstance(config.audio, AudioConfig)
        assert isinstance(config.output, OutputConfig)

    def test_nested_config(self) -> None:
        """Test nested config modification."""
        config = UserConfig(
            device=DeviceConfig(mic="Test Mic"),
            audio=AudioConfig(mic_gain=2.0),
            output=OutputConfig(format=AudioFormat.WAV),
        )
        assert config.device.mic == "Test Mic"
        assert config.audio.mic_gain == 2.0
        assert config.output.format == AudioFormat.WAV


class TestConfigPath:
    """Tests for config path functions."""

    def test_get_config_dir_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config dir can be overridden by environment variable."""
        monkeypatch.setenv("OMR_CONFIG_DIR", "/custom/config/dir")
        assert get_config_dir() == Path("/custom/config/dir")

    def test_get_config_path_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config path can be overridden by environment variable."""
        monkeypatch.setenv("OMR_CONFIG", "/custom/config.toml")
        assert get_config_path() == Path("/custom/config.toml")

    def test_get_config_path_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test default config path ends with config.toml."""
        monkeypatch.delenv("OMR_CONFIG", raising=False)
        monkeypatch.delenv("OMR_CONFIG_DIR", raising=False)
        path = get_config_path()
        assert path.name == "config.toml"
        assert "omr" in str(path)


class TestConfigFileOperations:
    """Tests for config file read/write operations."""

    def test_load_missing_config_returns_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test loading missing config returns defaults."""
        monkeypatch.setenv("OMR_CONFIG", str(tmp_path / "nonexistent.toml"))
        config = load_user_config()
        assert config == UserConfig.default()

    def test_save_and_load_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test saving and loading config file."""
        config_path = tmp_path / "config.toml"
        monkeypatch.setenv("OMR_CONFIG", str(config_path))

        # Create custom config
        config = UserConfig(
            device=DeviceConfig(mic="Test Mic", loopback="Test Speaker"),
            audio=AudioConfig(mic_gain=2.5, aec_enabled=False),
            output=OutputConfig(format=AudioFormat.WAV, bitrate=256),
        )

        # Save
        save_user_config(config)
        assert config_path.exists()

        # Load
        loaded = load_user_config()
        assert loaded.device.mic == "Test Mic"
        assert loaded.device.loopback == "Test Speaker"
        assert loaded.audio.mic_gain == 2.5
        assert loaded.audio.aec_enabled is False
        assert loaded.output.format == AudioFormat.WAV
        assert loaded.output.bitrate == 256

    def test_reset_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test resetting config to defaults."""
        config_path = tmp_path / "config.toml"
        monkeypatch.setenv("OMR_CONFIG", str(config_path))

        # Save custom config
        custom = UserConfig(audio=AudioConfig(mic_gain=5.0))
        save_user_config(custom)

        # Reset
        reset_user_config()

        # Load and verify defaults
        config = load_user_config()
        assert config.audio.mic_gain == 1.5  # Default value


class TestUpdateConfig:
    """Tests for update_user_config function."""

    def test_update_device_mic(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test updating device.mic setting."""
        monkeypatch.setenv("OMR_CONFIG", str(tmp_path / "config.toml"))
        config = update_user_config("device.mic", "New Microphone")
        assert config.device.mic == "New Microphone"

    def test_update_audio_mic_gain(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test updating audio.mic_gain setting."""
        monkeypatch.setenv("OMR_CONFIG", str(tmp_path / "config.toml"))
        config = update_user_config("audio.mic_gain", "2.5")
        assert config.audio.mic_gain == 2.5

    def test_update_audio_aec_enabled(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test updating audio.aec_enabled setting."""
        monkeypatch.setenv("OMR_CONFIG", str(tmp_path / "config.toml"))
        config = update_user_config("audio.aec_enabled", "false")
        assert config.audio.aec_enabled is False

    def test_update_output_format(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test updating output.format setting."""
        monkeypatch.setenv("OMR_CONFIG", str(tmp_path / "config.toml"))
        config = update_user_config("output.format", "wav")
        assert config.output.format == AudioFormat.WAV

    def test_update_invalid_key_format(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test updating with invalid key format raises error."""
        monkeypatch.setenv("OMR_CONFIG", str(tmp_path / "config.toml"))
        with pytest.raises(ValueError, match="Invalid key format"):
            update_user_config("invalid_key", "value")

    def test_update_unknown_section(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test updating unknown section raises error."""
        monkeypatch.setenv("OMR_CONFIG", str(tmp_path / "config.toml"))
        with pytest.raises(ValueError, match="Unknown section"):
            update_user_config("unknown.field", "value")

    def test_update_unknown_field(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test updating unknown field raises error."""
        monkeypatch.setenv("OMR_CONFIG", str(tmp_path / "config.toml"))
        with pytest.raises(ValueError, match="Unknown"):
            update_user_config("audio.unknown_field", "value")


class TestGetConfigValue:
    """Tests for get_config_value function."""

    def test_get_device_value(self) -> None:
        """Test getting device config values."""
        config = UserConfig(device=DeviceConfig(mic="Test Mic"))
        assert get_config_value(config, "device.mic") == "Test Mic"
        assert get_config_value(config, "device.loopback") is None

    def test_get_audio_value(self) -> None:
        """Test getting audio config values."""
        config = UserConfig(audio=AudioConfig(mic_gain=2.0))
        assert get_config_value(config, "audio.mic_gain") == 2.0
        assert get_config_value(config, "audio.aec_enabled") is True

    def test_get_output_value(self) -> None:
        """Test getting output config values."""
        config = UserConfig(output=OutputConfig(format=AudioFormat.WAV))
        assert get_config_value(config, "output.format") == "wav"
        assert get_config_value(config, "output.bitrate") == 128

    def test_get_invalid_key(self) -> None:
        """Test getting invalid key raises error."""
        config = UserConfig()
        with pytest.raises(ValueError, match="Invalid key format"):
            get_config_value(config, "invalid")
