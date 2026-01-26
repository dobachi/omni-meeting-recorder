"""Configuration settings for Omni Meeting Recorder."""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field


class AudioFormat(str, Enum):
    """Supported audio output formats."""

    WAV = "wav"
    FLAC = "flac"
    MP3 = "mp3"


class RecordingMode(str, Enum):
    """Recording mode selection."""

    LOOPBACK = "loopback"  # System audio only
    MIC = "mic"  # Microphone only
    BOTH = "both"  # Both mic and system audio


class AudioSettings(BaseModel):
    """Audio capture settings."""

    sample_rate: Annotated[int, Field(ge=8000, le=192000)] = 44100
    channels: Annotated[int, Field(ge=1, le=2)] = 2
    bit_depth: Annotated[int, Field(ge=8, le=32)] = 16
    chunk_size: Annotated[int, Field(ge=256, le=8192)] = 1024


class OutputSettings(BaseModel):
    """Output file settings."""

    format: AudioFormat = AudioFormat.MP3
    output_dir: Path = Path(".")
    filename_template: str = "recording_{timestamp}"
    bitrate: Annotated[int, Field(ge=64, le=320)] = 128


class RecordingSettings(BaseModel):
    """Recording configuration."""

    mode: RecordingMode = RecordingMode.LOOPBACK
    mic_device_index: int | None = None
    loopback_device_index: int | None = None
    stereo_split: bool = False  # If True, left=mic, right=system


class Settings(BaseModel):
    """Main application settings."""

    audio: AudioSettings = AudioSettings()
    output: OutputSettings = OutputSettings()
    recording: RecordingSettings = RecordingSettings()

    @classmethod
    def default(cls) -> Settings:
        """Create default settings."""
        return cls()


# =============================================================================
# User Configuration File Support
# =============================================================================


class DeviceConfig(BaseModel):
    """Device configuration for user config file."""

    mic: str | None = None  # Device name or index
    loopback: str | None = None  # Device name or index


class AudioConfig(BaseModel):
    """Audio settings for user config file."""

    mic_gain: Annotated[float, Field(ge=0.1, le=10.0)] = 1.5
    loopback_gain: Annotated[float, Field(ge=0.1, le=10.0)] = 1.0
    aec_enabled: bool = True
    aec_filter_multiplier: Annotated[int, Field(ge=5, le=100)] = 30
    stereo_split: bool = False
    mix_ratio: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5


class OutputConfig(BaseModel):
    """Output settings for user config file."""

    format: AudioFormat = AudioFormat.MP3
    bitrate: Annotated[int, Field(ge=64, le=320)] = 128
    directory: str | None = None  # Default output directory


class UserConfig(BaseModel):
    """User configuration file model.

    This represents the structure of the config.toml file.
    """

    device: DeviceConfig = DeviceConfig()
    audio: AudioConfig = AudioConfig()
    output: OutputConfig = OutputConfig()

    @classmethod
    def default(cls) -> UserConfig:
        """Create default user configuration."""
        return cls()


def get_config_dir() -> Path:
    """Get the configuration directory path.

    Returns:
        Path to the configuration directory.

    Priority:
        1. OMR_CONFIG_DIR environment variable
        2. Windows: %APPDATA%/omr
        3. Unix: ~/.config/omr
    """
    # Check environment variable first
    env_dir = os.environ.get("OMR_CONFIG_DIR")
    if env_dir:
        return Path(env_dir)

    # Platform-specific default
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "omr"
        # Fallback to user home
        return Path.home() / "AppData" / "Roaming" / "omr"
    else:
        # Unix-like systems (Linux, macOS)
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "omr"
        return Path.home() / ".config" / "omr"


def get_config_path() -> Path:
    """Get the configuration file path.

    Returns:
        Path to the config.toml file.

    Priority:
        1. OMR_CONFIG environment variable (full path to file)
        2. {config_dir}/config.toml
    """
    # Check environment variable for full path
    env_path = os.environ.get("OMR_CONFIG")
    if env_path:
        return Path(env_path)

    return get_config_dir() / "config.toml"


def load_user_config() -> UserConfig:
    """Load user configuration from file.

    Returns:
        UserConfig object. Returns default config if file doesn't exist.
    """
    config_path = get_config_path()

    if not config_path.exists():
        return UserConfig.default()

    try:
        import tomllib

        with config_path.open("rb") as f:
            data = tomllib.load(f)

        return UserConfig.model_validate(data)
    except Exception:
        # If config file is invalid, return default
        return UserConfig.default()


def save_user_config(config: UserConfig) -> Path:
    """Save user configuration to file.

    Args:
        config: UserConfig object to save.

    Returns:
        Path to the saved config file.
    """
    config_path = get_config_path()

    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to TOML format
    toml_content = _config_to_toml(config)

    with config_path.open("w", encoding="utf-8") as f:
        f.write(toml_content)

    return config_path


def _config_to_toml(config: UserConfig) -> str:
    """Convert UserConfig to TOML string.

    Args:
        config: UserConfig object.

    Returns:
        TOML formatted string.
    """
    lines: list[str] = []

    # [device] section
    lines.append("[device]")
    if config.device.mic is not None:
        lines.append(f'mic = "{config.device.mic}"')
    if config.device.loopback is not None:
        lines.append(f'loopback = "{config.device.loopback}"')
    lines.append("")

    # [audio] section
    lines.append("[audio]")
    lines.append(f"mic_gain = {config.audio.mic_gain}")
    lines.append(f"loopback_gain = {config.audio.loopback_gain}")
    lines.append(f"aec_enabled = {str(config.audio.aec_enabled).lower()}")
    lines.append(f"aec_filter_multiplier = {config.audio.aec_filter_multiplier}")
    lines.append(f"stereo_split = {str(config.audio.stereo_split).lower()}")
    lines.append(f"mix_ratio = {config.audio.mix_ratio}")
    lines.append("")

    # [output] section
    lines.append("[output]")
    lines.append(f'format = "{config.output.format.value}"')
    lines.append(f"bitrate = {config.output.bitrate}")
    if config.output.directory is not None:
        lines.append(f'directory = "{config.output.directory}"')
    lines.append("")

    return "\n".join(lines)


def reset_user_config() -> Path:
    """Reset user configuration to defaults.

    Returns:
        Path to the config file.
    """
    return save_user_config(UserConfig.default())


def update_user_config(key: str, value: str) -> UserConfig:
    """Update a single configuration value.

    Args:
        key: Configuration key in format "section.key" (e.g., "audio.mic_gain")
        value: String value to set (will be converted to appropriate type)

    Returns:
        Updated UserConfig object.

    Raises:
        ValueError: If key is invalid or value cannot be converted.
    """
    config = load_user_config()

    parts = key.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid key format: {key}. Use 'section.key' format.")

    section, field = parts

    if section == "device":
        if field == "mic":
            config.device.mic = value if value.lower() != "none" else None
        elif field == "loopback":
            config.device.loopback = value if value.lower() != "none" else None
        else:
            raise ValueError(f"Unknown device field: {field}")

    elif section == "audio":
        if field == "mic_gain":
            config.audio.mic_gain = float(value)
        elif field == "loopback_gain":
            config.audio.loopback_gain = float(value)
        elif field == "aec_enabled":
            config.audio.aec_enabled = value.lower() in ("true", "1", "yes", "on")
        elif field == "aec_filter_multiplier":
            config.audio.aec_filter_multiplier = int(value)
        elif field == "stereo_split":
            config.audio.stereo_split = value.lower() in ("true", "1", "yes", "on")
        elif field == "mix_ratio":
            config.audio.mix_ratio = float(value)
        else:
            raise ValueError(f"Unknown audio field: {field}")

    elif section == "output":
        if field == "format":
            config.output.format = AudioFormat(value.lower())
        elif field == "bitrate":
            config.output.bitrate = int(value)
        elif field == "directory":
            config.output.directory = value if value.lower() != "none" else None
        else:
            raise ValueError(f"Unknown output field: {field}")

    else:
        raise ValueError(f"Unknown section: {section}")

    save_user_config(config)
    return config


def get_config_value(config: UserConfig, key: str) -> Any:
    """Get a configuration value by key.

    Args:
        config: UserConfig object.
        key: Configuration key in format "section.key" (e.g., "audio.mic_gain")

    Returns:
        The configuration value.

    Raises:
        ValueError: If key is invalid.
    """
    parts = key.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid key format: {key}. Use 'section.key' format.")

    section, field = parts

    if section == "device":
        return getattr(config.device, field, None)
    elif section == "audio":
        return getattr(config.audio, field, None)
    elif section == "output":
        val = getattr(config.output, field, None)
        if isinstance(val, AudioFormat):
            return val.value
        return val
    else:
        raise ValueError(f"Unknown section: {section}")
