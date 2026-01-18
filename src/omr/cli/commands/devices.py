"""Device listing commands for Omni Meeting Recorder."""

import typer
from rich.console import Console
from rich.table import Table

from omr.core.device_manager import DeviceManager, DeviceType

app = typer.Typer(help="List and manage audio devices")
console = Console()


@app.callback(invoke_without_command=True)
def list_devices(
    ctx: typer.Context,
    all_devices: bool = typer.Option(
        False, "--all", "-a", help="Show all devices including outputs"
    ),
    mic_only: bool = typer.Option(False, "--mic", "-m", help="Show only microphones"),
    loopback_only: bool = typer.Option(
        False, "--loopback", "-l", help="Show only loopback devices"
    ),
) -> None:
    """List available audio devices."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        manager = DeviceManager()
        manager.initialize()
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    # Filter devices based on options
    if mic_only:
        devices = manager.get_input_devices()
        title = "Microphone Devices"
    elif loopback_only:
        devices = manager.get_loopback_devices()
        title = "Loopback Devices (System Audio)"
    elif all_devices:
        devices = manager.devices
        title = "All Audio Devices"
    else:
        # Default: show mic and loopback devices
        devices = manager.get_input_devices() + manager.get_loopback_devices()
        title = "Recording Devices"

    if not devices:
        console.print("[yellow]No devices found.[/yellow]")
        console.print("\nMake sure:")
        console.print("  1. Audio devices are connected and enabled")
        console.print("  2. Windows audio service is running")
        console.print("  3. PyAudioWPatch is properly installed")
        raise typer.Exit(1)

    # Create table
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Index", style="dim", width=6)
    table.add_column("Type", width=8)
    table.add_column("Name", min_width=30)
    table.add_column("Channels", justify="center", width=10)
    table.add_column("Sample Rate", justify="right", width=12)
    table.add_column("Default", justify="center", width=8)

    type_styles = {
        DeviceType.INPUT: ("MIC", "green"),
        DeviceType.OUTPUT: ("SPK", "blue"),
        DeviceType.LOOPBACK: ("LOOP", "magenta"),
    }

    for device in devices:
        type_label, type_style = type_styles.get(device.device_type, ("???", "white"))
        default_mark = "[green]*[/green]" if device.is_default else ""

        table.add_row(
            str(device.index),
            f"[{type_style}]{type_label}[/{type_style}]",
            device.name,
            str(device.channels),
            f"{int(device.default_sample_rate)} Hz",
            default_mark,
        )

    console.print()
    console.print(table)
    console.print()
    console.print("[dim]* = default device[/dim]")
    console.print()
    console.print("Usage examples:")
    console.print("  [cyan]omr start --loopback[/cyan]          # Record system audio")
    console.print("  [cyan]omr start --mic[/cyan]               # Record microphone")
    console.print(
        "  [cyan]omr start --loopback --loopback-device 5[/cyan]  # Use specific device"
    )


@app.command("test")
def test_device(
    device_index: int = typer.Argument(..., help="Device index to test"),
    duration: float = typer.Option(3.0, "--duration", "-d", help="Test duration in seconds"),
) -> None:
    """Test an audio device by recording briefly."""
    console.print(f"[yellow]Testing device {device_index} for {duration} seconds...[/yellow]")
    console.print("[dim]This feature will be implemented in a future version.[/dim]")
