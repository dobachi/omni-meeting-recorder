"""Recording commands for Omni Meeting Recorder."""

import time
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from omr.config.settings import RecordingMode
from omr.core.audio_capture import AudioCapture, RecordingSession

app = typer.Typer(help="Recording commands")
console = Console()


def _format_duration(seconds: float) -> str:
    """Format duration in HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_size(bytes_count: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"


def _create_status_panel(session: RecordingSession) -> Panel:
    """Create a status panel for the recording."""
    state = session.state
    elapsed = 0.0
    if state.start_time:
        elapsed = (datetime.now() - state.start_time).total_seconds()

    mode_text = {
        RecordingMode.LOOPBACK: "System Audio (Loopback)",
        RecordingMode.MIC: "Microphone",
        RecordingMode.BOTH: "Mic + System Audio",
    }.get(session.mode, "Unknown")

    status_lines = [
        f"[bold green]● Recording[/bold green]",
        "",
        f"[cyan]Mode:[/cyan] {mode_text}",
        f"[cyan]Duration:[/cyan] {_format_duration(elapsed)}",
        f"[cyan]Size:[/cyan] {_format_size(state.bytes_recorded)}",
        f"[cyan]Output:[/cyan] {state.output_file}",
        "",
        "[dim]Press Ctrl+C to stop[/dim]",
    ]

    text = Text.from_markup("\n".join(status_lines))
    return Panel(text, title="Omni Meeting Recorder", border_style="green")


@app.command("start")
def start(
    loopback: bool = typer.Option(False, "--loopback", "-l", help="Record system audio"),
    mic: bool = typer.Option(False, "--mic", "-m", help="Record microphone"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    mic_device: int | None = typer.Option(None, "--mic-device", help="Microphone device index"),
    loopback_device: int | None = typer.Option(
        None, "--loopback-device", help="Loopback device index"
    ),
) -> None:
    """Start recording audio."""
    # Determine recording mode
    if loopback and mic:
        mode = RecordingMode.BOTH
    elif mic:
        mode = RecordingMode.MIC
    elif loopback:
        mode = RecordingMode.LOOPBACK
    else:
        # Default to loopback
        mode = RecordingMode.LOOPBACK
        console.print("[dim]No mode specified, defaulting to system audio (loopback)[/dim]")

    # Parse output path
    output_path = Path(output) if output else None

    audio_capture: AudioCapture | None = None
    session: RecordingSession | None = None

    try:
        audio_capture = AudioCapture()
        audio_capture.initialize()

        # Create session
        session = audio_capture.create_session(
            mode=mode,
            output_path=output_path,
            mic_device_index=mic_device,
            loopback_device_index=loopback_device,
        )

        # Show device info
        if session.mic_device:
            console.print(f"[cyan]Microphone:[/cyan] {session.mic_device.name}")
        if session.loopback_device:
            console.print(f"[cyan]Loopback:[/cyan] {session.loopback_device.name}")
        console.print(f"[cyan]Output:[/cyan] {session.output_path}")
        console.print()

        # Start recording
        audio_capture.start_recording(session)
        console.print("[green]Recording started![/green]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        console.print()

        # Show live status - use try/except for KeyboardInterrupt (works better on Windows)
        try:
            with Live(_create_status_panel(session), refresh_per_second=2, transient=True) as live:
                while session.state.is_recording:
                    live.update(_create_status_panel(session))
                    # Use shorter sleep for more responsive Ctrl+C handling
                    time.sleep(0.1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping recording...[/yellow]")
            session.request_stop()
            # Wait for recording thread to finish
            audio_capture.stop_recording(session)

        # Recording stopped
        state = session.state
        if state.error:
            console.print(f"\n[red]Recording error:[/red] {state.error}")
            raise typer.Exit(1)

        elapsed = 0.0
        if state.start_time:
            elapsed = (datetime.now() - state.start_time).total_seconds()

        console.print()
        console.print("[green]Recording complete![/green]")
        console.print(f"[cyan]Duration:[/cyan] {_format_duration(elapsed)}")
        console.print(f"[cyan]Size:[/cyan] {_format_size(state.bytes_recorded)}")
        console.print(f"[cyan]Saved to:[/cyan] {state.output_file}")

    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except NotImplementedError as e:
        console.print(f"[yellow]Not implemented:[/yellow] {e}")
        raise typer.Exit(1)
    finally:
        if audio_capture:
            audio_capture.terminate()


@app.command("stop")
def stop() -> None:
    """Stop the current recording (sends signal to running process)."""
    console.print("[yellow]Note:[/yellow] Use Ctrl+C in the recording terminal to stop.")
    console.print("[dim]Background recording management will be added in a future version.[/dim]")
