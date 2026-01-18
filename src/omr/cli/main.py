"""CLI entry point for Omni Meeting Recorder."""

from typing import Annotated

import typer
from rich.console import Console

from omr import __version__
from omr.cli.commands import devices, record
from omr.config.settings import AudioFormat

app = typer.Typer(
    name="omr",
    help="Omni Meeting Recorder - Record online meeting audio (mic + system sound)",
    add_completion=False,
)

console = Console()

# Add subcommands
app.add_typer(devices.app, name="devices")
app.add_typer(record.app, name="record")


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
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
    mic_device: int = typer.Option(None, "--mic-device", help="Microphone device index"),
    loopback_device: int = typer.Option(
        None, "--loopback-device", help="Loopback device index"
    ),
    stereo_split: bool = typer.Option(
        False,
        "--stereo-split/--mix",
        help="Stereo split (left=mic, right=system) or mix both channels",
    ),
    aec: bool = typer.Option(
        True,
        "--aec/--no-aec",
        help="Enable acoustic echo cancellation (requires pyaec)",
    ),
    output_format: Annotated[
        AudioFormat, typer.Option("--format", "-f", help="Output format (wav/mp3)")
    ] = AudioFormat.MP3,
    bitrate: Annotated[
        int, typer.Option("--bitrate", "-b", help="MP3 bitrate in kbps")
    ] = 128,
    keep_wav: Annotated[
        bool, typer.Option("--keep-wav", help="Keep WAV file after MP3 conversion")
    ] = False,
) -> None:
    """Start recording audio (mic + system by default). Shortcut for 'omr record start'."""
    record.start(
        loopback=False,
        mic=False,
        loopback_only=loopback_only,
        mic_only=mic_only,
        output=output,
        mic_device=mic_device,
        loopback_device=loopback_device,
        stereo_split=stereo_split,
        aec=aec,
        output_format=output_format,
        bitrate=bitrate,
        keep_wav=keep_wav,
    )


if __name__ == "__main__":
    app()
