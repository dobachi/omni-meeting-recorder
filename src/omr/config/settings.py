"""Configuration settings for Omni Meeting Recorder."""

from enum import Enum
from pathlib import Path
from typing import Annotated

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
    def default(cls) -> "Settings":
        """Create default settings."""
        return cls()
