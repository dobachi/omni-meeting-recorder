"""CLI entry point for Omni Meeting Recorder."""

from typing import Annotated

import typer
from rich.console import Console

from omr import __version__
from omr.cli.commands import config, devices, record
from omr.config.settings import AudioFormat, load_user_config

app = typer.Typer(
    name="omr",
    help="Omni Meeting Recorder - Record online meeting audio (mic + system sound)",
    add_completion=False,
)

console = Console()

# Add subcommands
app.add_typer(devices.app, name="devices")
app.add_typer(record.app, name="record")
app.add_typer(config.app, name="config")


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"Omni Meeting Recorder v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Omni Meeting Recorder - CLI tool for recording online meeting audio."""
    pass


# Shortcut commands for convenience
@app.command("start")
def start_recording(
    loopback_only: bool = typer.Option(
        False, "--loopback-only", "-L", help="Record system audio only"
    ),
    mic_only: bool = typer.Option(
        False, "--mic-only", "-M", help="Record microphone only"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    mic_device: str | None = typer.Option(
        None, "--mic-device", help="Microphone device (index or name)"
    ),
    loopback_device: str | None = typer.Option(
        None, "--loopback-device", help="Loopback device (index or name)"
    ),
    stereo_split: bool | None = typer.Option(
        None,
        "--stereo-split/--mix",
        help="Stereo split (left=mic, right=system) or mix both channels",
    ),
    aec: bool | None = typer.Option(
        None,
        "--aec/--no-aec",
        help="Enable acoustic echo cancellation (requires pyaec)",
    ),
    mic_gain: Annotated[
        float | None, typer.Option("--mic-gain", help="Microphone gain multiplier")
    ] = None,
    loopback_gain: Annotated[
        float | None, typer.Option("--loopback-gain", help="System audio gain multiplier")
    ] = None,
    mix_ratio: Annotated[
        float | None,
        typer.Option(
            "--mix-ratio",
            help="Mic/system audio mix ratio (0.0-1.0). Higher = more mic."
        )
    ] = None,
    output_format: Annotated[
        AudioFormat | None, typer.Option("--format", "-f", help="Output format (wav/mp3)")
    ] = None,
    bitrate: Annotated[
        int | None, typer.Option("--bitrate", "-b", help="MP3 bitrate in kbps")
    ] = None,
    keep_wav: Annotated[
        bool, typer.Option("--keep-wav", help="Keep WAV file after MP3 conversion (only with --post-convert)")
    ] = False,
    post_convert: Annotated[
        bool, typer.Option("--post-convert", help="WAV録音後にMP3変換（旧動作）")
    ] = False,
    # Deprecated option - kept for backward compatibility
    direct_mp3: Annotated[
        bool, typer.Option("--direct-mp3", help="[非推奨] 直接MP3出力（現在はデフォルト動作）", hidden=True)
    ] = False,
) -> None:
    """Start recording audio (mic + system by default). Shortcut for 'omr record start'.

    Configuration values from ~/.config/omr/config.toml (or %APPDATA%/omr/config.toml)
    are used as defaults when CLI options are not specified.
    """
    # Load user configuration
    user_config = load_user_config()

    # Apply config defaults for unspecified options
    effective_mic_gain = mic_gain if mic_gain is not None else user_config.audio.mic_gain
    effective_loopback_gain = (
        loopback_gain if loopback_gain is not None else user_config.audio.loopback_gain
    )
    effective_aec = aec if aec is not None else user_config.audio.aec_enabled
    effective_stereo_split = (
        stereo_split if stereo_split is not None else user_config.audio.stereo_split
    )
    effective_mix_ratio = mix_ratio if mix_ratio is not None else user_config.audio.mix_ratio
    effective_format = output_format if output_format is not None else user_config.output.format
    effective_bitrate = bitrate if bitrate is not None else user_config.output.bitrate

    # Handle device options - can be index (int) or name (str)
    effective_mic_device: int | None = None
    if mic_device is not None:
        # CLI option specified - try to parse as int, otherwise treat as name
        try:
            effective_mic_device = int(mic_device)
        except ValueError:
            # It's a device name - will be resolved later
            # For now, pass None and let record.start handle by name
            effective_mic_device = None
    elif user_config.device.mic is not None:
        # Try config value
        try:
            effective_mic_device = int(user_config.device.mic)
        except ValueError:
            effective_mic_device = None

    effective_loopback_device: int | None = None
    if loopback_device is not None:
        try:
            effective_loopback_device = int(loopback_device)
        except ValueError:
            effective_loopback_device = None
    elif user_config.device.loopback is not None:
        try:
            effective_loopback_device = int(user_config.device.loopback)
        except ValueError:
            effective_loopback_device = None

    # Handle output directory from config
    effective_output = output
    if effective_output is None and user_config.output.directory is not None:
        # Use config directory with default filename pattern
        from datetime import datetime
        from pathlib import Path

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = effective_format.value
        output_dir = Path(user_config.output.directory).expanduser()
        effective_output = str(output_dir / f"recording_{timestamp}.{ext}")

    record.start(
        loopback=False,
        mic=False,
        loopback_only=loopback_only,
        mic_only=mic_only,
        output=effective_output,
        mic_device=effective_mic_device,
        loopback_device=effective_loopback_device,
        stereo_split=effective_stereo_split,
        aec=effective_aec,
        mic_gain=effective_mic_gain,
        loopback_gain=effective_loopback_gain,
        mix_ratio=effective_mix_ratio,
        output_format=effective_format,
        bitrate=effective_bitrate,
        keep_wav=keep_wav,
        post_convert=post_convert,
        direct_mp3=direct_mp3,
    )


if __name__ == "__main__":
    app()
