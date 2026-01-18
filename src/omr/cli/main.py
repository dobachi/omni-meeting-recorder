"""CLI entry point for Omni Meeting Recorder."""

import typer
from rich.console import Console

from omr import __version__
from omr.cli.commands import devices, record

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
    loopback: bool = typer.Option(False, "--loopback", "-l", help="Record system audio"),
    mic: bool = typer.Option(False, "--mic", "-m", help="Record microphone"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
    mic_device: int = typer.Option(None, "--mic-device", help="Microphone device index"),
    loopback_device: int = typer.Option(
        None, "--loopback-device", help="Loopback device index"
    ),
) -> None:
    """Start recording audio. Shortcut for 'omr record start'."""
    record.start(
        loopback=loopback,
        mic=mic,
        output=output,
        mic_device=mic_device,
        loopback_device=loopback_device,
    )


if __name__ == "__main__":
    app()
