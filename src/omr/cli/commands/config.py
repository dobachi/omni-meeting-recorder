"""Configuration management commands for Omni Meeting Recorder."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from omr.config.settings import (
    UserConfig,
    get_config_path,
    get_config_value,
    load_user_config,
    reset_user_config,
    save_user_config,
    update_user_config,
)

app = typer.Typer(help="Configuration management commands")
console = Console()


# All valid configuration keys
CONFIG_KEYS = {
    "device.mic": "Default microphone device (name or index)",
    "device.loopback": "Default loopback device (name or index)",
    "audio.mic_gain": "Microphone gain multiplier (0.1-10.0)",
    "audio.loopback_gain": "System audio gain multiplier (0.1-10.0)",
    "audio.aec_enabled": "Acoustic Echo Cancellation (true/false)",
    "audio.stereo_split": "Stereo split mode (true/false)",
    "audio.mix_ratio": "Mic/system mix ratio (0.0-1.0)",
    "output.format": "Output format (mp3/wav/flac)",
    "output.bitrate": "MP3 bitrate in kbps (64-320)",
    "output.directory": "Default output directory",
}


@app.command("show")
def show(
    key: Annotated[
        str | None,
        typer.Argument(help="Specific key to show (e.g., 'audio.mic_gain')"),
    ] = None,
) -> None:
    """Show current configuration.

    If no key is specified, shows all configuration values.
    """
    config = load_user_config()
    config_path = get_config_path()

    if key:
        # Show specific key
        try:
            value = get_config_value(config, key)
            console.print(f"[cyan]{key}[/cyan] = {value}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
    else:
        # Show all configuration
        console.print(f"[dim]Config file: {config_path}[/dim]")
        if not config_path.exists():
            console.print("[dim](Using default values - no config file exists)[/dim]")
        console.print()

        table = Table(title="Current Configuration", show_header=True)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")

        for cfg_key, description in CONFIG_KEYS.items():
            try:
                value = get_config_value(config, cfg_key)
                value_str = str(value) if value is not None else "[dim]not set[/dim]"
            except ValueError:
                value_str = "[red]error[/red]"
            table.add_row(cfg_key, value_str, description)

        console.print(table)


@app.command("set")
def set_config(
    key: Annotated[str, typer.Argument(help="Configuration key (e.g., 'audio.mic_gain')")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a configuration value.

    Examples:
        omr config set audio.mic_gain 2.0
        omr config set output.format wav
        omr config set device.mic "Microphone (Realtek)"
    """
    if key not in CONFIG_KEYS:
        console.print(f"[red]Error:[/red] Unknown key: {key}")
        console.print()
        console.print("[cyan]Valid keys:[/cyan]")
        for k in CONFIG_KEYS:
            console.print(f"  {k}")
        raise typer.Exit(1)

    try:
        config = update_user_config(key, value)
        new_value = get_config_value(config, key)
        console.print(f"[green]Set[/green] [cyan]{key}[/cyan] = {new_value}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command("reset")
def reset(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Reset configuration to default values."""
    config_path = get_config_path()

    if not force and config_path.exists():
        confirm = typer.confirm(
            f"This will overwrite {config_path}. Continue?",
            default=False,
        )
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    path = reset_user_config()
    console.print("[green]Configuration reset to defaults[/green]")
    console.print(f"[dim]Config file: {path}[/dim]")


@app.command("path")
def show_path() -> None:
    """Show the configuration file path."""
    config_path = get_config_path()
    console.print(f"[cyan]Config file:[/cyan] {config_path}")
    if config_path.exists():
        console.print("[green]File exists[/green]")
    else:
        console.print("[dim]File does not exist (using defaults)[/dim]")


@app.command("init")
def init(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing config file"),
    ] = False,
) -> None:
    """Create a new configuration file with default values."""
    config_path = get_config_path()

    if config_path.exists() and not force:
        console.print(f"[yellow]Config file already exists:[/yellow] {config_path}")
        console.print("[dim]Use --force to overwrite[/dim]")
        raise typer.Exit(1)

    path = save_user_config(UserConfig.default())
    console.print(f"[green]Created configuration file:[/green] {path}")
    console.print()
    console.print("[dim]Edit this file or use 'omr config set <key> <value>'[/dim]")


@app.command("edit")
def edit() -> None:
    """Open the configuration file in the default editor."""
    import os
    import subprocess

    config_path = get_config_path()

    # Create config file if it doesn't exist
    if not config_path.exists():
        save_user_config(UserConfig.default())
        console.print(f"[dim]Created default config file: {config_path}[/dim]")

    # Try to open with default editor
    try:
        if os.name == "nt":  # Windows
            os.startfile(str(config_path))  # type: ignore[attr-defined]
        elif os.name == "posix":  # Linux/macOS
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(config_path)], check=True)
    except Exception as e:
        console.print(f"[yellow]Could not open editor:[/yellow] {e}")
        console.print(f"[cyan]Config file path:[/cyan] {config_path}")
