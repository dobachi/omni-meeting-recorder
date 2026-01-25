"""Recording commands for Omni Meeting Recorder."""

import time
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from omr.config.settings import AudioFormat, RecordingMode
from omr.core.aec_processor import is_aec_available
from omr.core.audio_capture import AudioCapture, RecordingSession
from omr.core.device_errors import DeviceError, DeviceErrorType
from omr.core.device_manager import AudioDevice
from omr.core.encoder import encode_to_mp3, is_mp3_available
from omr.core.input_handler import (
    InputCommand,
    InputEvent,
    KeyInputHandler,
    SelectionMode,
    is_input_available,
)

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
    size: float = bytes_count
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _create_status_panel(
    session: RecordingSession,
    selection_mode: SelectionMode = SelectionMode.NONE,
    available_devices: list[AudioDevice] | None = None,
    status_message: str | None = None,
    device_error: DeviceError | None = None,
) -> Panel:
    """Create a status panel for the recording.

    Args:
        session: The recording session.
        selection_mode: Current device selection mode.
        available_devices: List of devices to show in selection mode.
        status_message: Optional status message to display.
        device_error: Optional device error to display.
    """
    state = session.state
    elapsed = 0.0
    if state.start_time:
        elapsed = (datetime.now() - state.start_time).total_seconds()

    if session.mode == RecordingMode.BOTH:
        aec_status = " + AEC" if session.aec_enabled else ""
        if session.stereo_split:
            mode_text = f"Mic + System (Stereo: L=Mic, R=System){aec_status}"
        else:
            mode_text = f"Mic + System (Mixed){aec_status}"
    else:
        mode_text = {
            RecordingMode.LOOPBACK: "System Audio (Loopback)",
            RecordingMode.MIC: "Microphone",
        }.get(session.mode, "Unknown")

    # Determine recording status indicator based on device error
    if device_error:
        status_indicator = "[bold yellow]● Recording (Device Error)[/bold yellow]"
        border_style = "yellow"
    else:
        status_indicator = "[bold green]● Recording[/bold green]"
        border_style = "green"

    status_lines = [
        status_indicator,
        "",
        f"[cyan]Mode:[/cyan] {mode_text}",
        f"[cyan]Duration:[/cyan] {_format_duration(elapsed)}",
        f"[cyan]Size:[/cyan] {_format_size(state.bytes_recorded)}",
    ]

    # Show device error if any
    if device_error:
        error_type_str = {
            DeviceErrorType.DISCONNECTED: "disconnected",
            DeviceErrorType.ACCESS_DENIED: "access denied",
            DeviceErrorType.UNKNOWN: "error",
        }.get(device_error.error_type, "error")
        status_lines.append("")
        status_lines.append(
            f"[bold red]Warning:[/bold red] {device_error.source} device {error_type_str}"
        )
        if device_error.can_recover:
            status_lines.append("[dim]Recording continues with available device(s)[/dim]")
        else:
            status_lines.append("[dim]Recording will stop[/dim]")

    # Show current devices
    if session.mic_device:
        status_lines.append(f"[cyan]Microphone:[/cyan] {session.mic_device.name}")
    if session.loopback_device:
        status_lines.append(f"[cyan]Loopback:[/cyan] {session.loopback_device.name}")

    status_lines.append(f"[cyan]Output:[/cyan] {state.output_file}")

    # Show status message if any
    if status_message:
        status_lines.append("")
        status_lines.append(f"[yellow]{status_message}[/yellow]")

    # Show device selection or keyboard shortcuts
    if selection_mode != SelectionMode.NONE and available_devices:
        mode_name = "Microphone" if selection_mode == SelectionMode.MIC else "Loopback"
        status_lines.append("")
        status_lines.append(f"[bold yellow]Select {mode_name} Device:[/bold yellow]")
        for i, device in enumerate(available_devices[:10]):  # Max 10 devices
            default_marker = " [default]" if device.is_default else ""
            status_lines.append(f"  [cyan]{i}[/cyan]: {device.name}{default_marker}")
        status_lines.append("")
        status_lines.append("[dim]Press 0-9 to select, Esc to cancel[/dim]")
    else:
        # Show keyboard shortcuts
        status_lines.append("")
        status_lines.append("[dim]─────────── Keyboard Shortcuts ───────────[/dim]")
        shortcuts = []
        if session.mode in (RecordingMode.MIC, RecordingMode.BOTH):
            shortcuts.append("\\[m] Switch Mic")
        if session.mode in (RecordingMode.LOOPBACK, RecordingMode.BOTH):
            shortcuts.append("\\[l] Switch Loopback")
        shortcuts.append("\\[q] Stop")
        status_lines.append("[dim]" + "  ".join(shortcuts) + "[/dim]")

    text = Text.from_markup("\n".join(status_lines))
    return Panel(text, title="Omni Meeting Recorder", border_style=border_style)


@app.command("start")
def start(
    loopback: bool = typer.Option(
        False, "--loopback", "-l", help="Include system audio", hidden=True
    ),
    mic: bool = typer.Option(
        False, "--mic", "-m", help="Include microphone", hidden=True
    ),
    loopback_only: bool = typer.Option(
        False, "--loopback-only", "-L", help="Record system audio only"
    ),
    mic_only: bool = typer.Option(
        False, "--mic-only", "-M", help="Record microphone only"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    mic_device: int | None = typer.Option(None, "--mic-device", help="Microphone device index"),
    loopback_device: int | None = typer.Option(
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
    mic_gain: Annotated[
        float, typer.Option("--mic-gain", help="Microphone gain multiplier (default: 1.5)")
    ] = 1.5,
    loopback_gain: Annotated[
        float, typer.Option("--loopback-gain", help="System audio gain multiplier (default: 1.0)")
    ] = 1.0,
    mix_ratio: Annotated[
        float,
        typer.Option(
            "--mix-ratio",
            help="Mic/system audio mix ratio (0.0-1.0). Higher = more mic."
        )
    ] = 0.5,
    output_format: Annotated[
        AudioFormat, typer.Option("--format", "-f", help="Output format (wav/mp3)")
    ] = AudioFormat.MP3,
    bitrate: Annotated[
        int, typer.Option("--bitrate", "-b", help="MP3 bitrate in kbps")
    ] = 128,
    keep_wav: Annotated[
        bool,
        typer.Option("--keep-wav", help="Keep WAV file after MP3 conversion"),
    ] = False,
    post_convert: Annotated[
        bool, typer.Option("--post-convert", help="WAV録音後にMP3変換（旧動作）")
    ] = False,
    # Deprecated option - kept for backward compatibility
    direct_mp3: Annotated[
        bool,
        typer.Option("--direct-mp3", help="[非推奨] 直接MP3出力", hidden=True),
    ] = False,
) -> None:
    """Start recording audio."""
    # Show deprecation warning for --direct-mp3
    if direct_mp3:
        console.print(
            "[yellow]Warning:[/yellow] --direct-mp3 is deprecated. "
            "Direct MP3 output is now the default behavior."
        )
        console.print()

    # Determine if we should use streaming MP3 (direct output)
    # Default: streaming MP3 for --format mp3
    # --post-convert: record to WAV first, then convert
    use_streaming_mp3 = output_format == AudioFormat.MP3 and not post_convert

    # Warn if --keep-wav used without --post-convert
    if keep_wav and not post_convert:
        console.print(
            "[yellow]Warning:[/yellow] --keep-wav has no effect without --post-convert."
        )
        console.print()

    # Check lameenc availability for MP3 format
    if output_format == AudioFormat.MP3 and not is_mp3_available():
        console.print("[red]Error:[/red] lameenc is required for MP3 output.")
        console.print("[dim]Install with: uv sync[/dim]")
        raise typer.Exit(1)

    # Check AEC availability
    aec_enabled = aec
    if aec and not is_aec_available():
        console.print(
            "[yellow]Warning:[/yellow] pyaec is not installed. AEC will be disabled."
        )
        console.print("[dim]Install with: uv sync[/dim]")
        console.print()
        aec_enabled = False

    # Determine recording mode
    # Priority: --loopback-only / --mic-only > -l -m > default (BOTH)
    if loopback_only and mic_only:
        console.print("[red]Error:[/red] Cannot use --loopback-only and --mic-only together.")
        raise typer.Exit(1)
    elif loopback_only:
        mode = RecordingMode.LOOPBACK
    elif mic_only:
        mode = RecordingMode.MIC
    elif loopback or mic:
        # Legacy -l -m options
        if loopback and mic:
            mode = RecordingMode.BOTH
        elif mic:
            mode = RecordingMode.MIC
        else:
            mode = RecordingMode.LOOPBACK
    else:
        # Default: BOTH mode (mic + loopback)
        mode = RecordingMode.BOTH

    # Show AEC status for BOTH mode
    if mode == RecordingMode.BOTH:
        if aec_enabled:
            console.print(
                "[cyan]Info:[/cyan] Acoustic Echo Cancellation (AEC) is enabled."
            )
            console.print()
        else:
            console.print(
                "[yellow]Warning:[/yellow] Using mic and loopback together may cause echo "
                "if speakers are used."
            )
            console.print(
                "[dim]Recommendation: Use --aec to enable echo cancellation, or use "
                "headphones to prevent microphone from picking up speaker audio.[/dim]"
            )
            console.print()

    # Parse output path - ensure correct extension based on format and mode
    output_path = Path(output) if output else None
    desired_mp3_path: Path | None = None
    if output_format == AudioFormat.MP3:
        if use_streaming_mp3:
            # Streaming MP3: output path should be .mp3
            if output_path and output_path.suffix.lower() != ".mp3":
                output_path = output_path.with_suffix(".mp3")
        else:
            # Post-conversion mode: record to WAV first
            if output_path and output_path.suffix.lower() == ".mp3":
                desired_mp3_path = output_path
                output_path = output_path.with_suffix(".wav")

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
            stereo_split=stereo_split,
            aec_enabled=aec_enabled,
            mic_gain=mic_gain,
            loopback_gain=loopback_gain,
            mix_ratio=mix_ratio,
            direct_mp3=use_streaming_mp3,
            mp3_bitrate=bitrate,
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
        if is_input_available():
            console.print("[dim]Press 'q' to stop, 'm' to switch mic, 'l' to switch loopback[/dim]")
        else:
            console.print("[dim]Press Ctrl+C to stop[/dim]")
        console.print()

        # State for device selection mode
        selection_mode = SelectionMode.NONE
        available_devices: list[AudioDevice] = []
        status_message: str | None = None
        input_handler: KeyInputHandler | None = None
        current_device_error: DeviceError | None = None

        # Set up device error callback
        def on_device_error(error: DeviceError) -> None:
            """Callback when device error is detected."""
            nonlocal current_device_error
            current_device_error = error

        session.set_device_error_callback(on_device_error)

        # Get device manager for device listing
        device_manager = audio_capture.device_manager

        def get_devices_for_mode(sel_mode: SelectionMode) -> list[AudioDevice]:
            """Get available devices for the selection mode."""
            if sel_mode == SelectionMode.MIC:
                return device_manager.get_input_devices()
            elif sel_mode == SelectionMode.LOOPBACK:
                return device_manager.get_loopback_devices()
            return []

        def handle_device_selection(device_index: int) -> str | None:
            """Handle device selection. Returns status message or None."""
            nonlocal selection_mode, available_devices
            if device_index >= len(available_devices):
                return f"Invalid device index: {device_index}"

            selected_device = available_devices[device_index]
            if selection_mode == SelectionMode.MIC:
                session.request_device_switch(mic_device=selected_device)
                msg = f"Switching mic to: {selected_device.name}"
            else:
                session.request_device_switch(loopback_device=selected_device)
                msg = f"Switching loopback to: {selected_device.name}"

            selection_mode = SelectionMode.NONE
            available_devices = []
            if input_handler:
                input_handler.exit_selection_mode()
            return msg

        def handle_input_event(event: InputEvent) -> bool:
            """Handle an input event. Returns True if should stop recording."""
            nonlocal selection_mode, available_devices, status_message

            if event.command == InputCommand.STOP:
                return True

            elif event.command == InputCommand.SWITCH_MIC:
                if session.mode in (RecordingMode.MIC, RecordingMode.BOTH):
                    selection_mode = SelectionMode.MIC
                    available_devices = get_devices_for_mode(selection_mode)
                    if input_handler:
                        input_handler.enter_selection_mode(selection_mode)
                    status_message = None

            elif event.command == InputCommand.SWITCH_LOOPBACK:
                if session.mode in (RecordingMode.LOOPBACK, RecordingMode.BOTH):
                    selection_mode = SelectionMode.LOOPBACK
                    available_devices = get_devices_for_mode(selection_mode)
                    if input_handler:
                        input_handler.enter_selection_mode(selection_mode)
                    status_message = None

            elif event.command == InputCommand.SELECT_DEVICE:
                if selection_mode != SelectionMode.NONE and event.value is not None:
                    status_message = handle_device_selection(event.value)

            elif event.command == InputCommand.CANCEL:
                selection_mode = SelectionMode.NONE
                available_devices = []
                if input_handler:
                    input_handler.exit_selection_mode()
                status_message = None

            elif event.command == InputCommand.REFRESH_DEVICES:
                device_manager.initialize()  # Re-scan devices
                status_message = "Device list refreshed"

            return False

        # Show live status with keyboard input handling
        try:
            if is_input_available():
                input_handler = KeyInputHandler()
                input_handler.start()

            with Live(
                _create_status_panel(
                    session, selection_mode, available_devices, status_message, current_device_error
                ),
                refresh_per_second=4,
                transient=True,
            ) as live:
                while session.state.is_recording:
                    # Check for keyboard input
                    if input_handler:
                        event = input_handler.get_event(timeout=0.05)
                        if event:
                            should_stop = handle_input_event(event)
                            if should_stop:
                                console.print("\n[yellow]Stopping recording...[/yellow]")
                                session.request_stop()
                                break
                            # Clear status message after a short delay
                            if status_message and "Switching" not in status_message:
                                time.sleep(0.5)
                                status_message = None

                    # Update device error from session state
                    if session.state.device_error and not current_device_error:
                        current_device_error = session.state.device_error

                    live.update(
                        _create_status_panel(
                            session,
                            selection_mode,
                            available_devices,
                            status_message,
                            current_device_error,
                        )
                    )
                    time.sleep(0.05)

        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping recording...[/yellow]")
            session.request_stop()
        finally:
            if input_handler:
                input_handler.stop()
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

        # Check if recording was interrupted by device error
        if state.is_partial_save and state.device_error:
            console.print("[yellow]Recording stopped due to device error![/yellow]")
            error_type_str = {
                DeviceErrorType.DISCONNECTED: "disconnected",
                DeviceErrorType.ACCESS_DENIED: "access denied",
                DeviceErrorType.UNKNOWN: "error",
            }.get(state.device_error.error_type, "error")
            console.print(
                f"[yellow]Device:[/yellow] {state.device_error.source} ({error_type_str})"
            )
            console.print("[cyan]Partial recording saved:[/cyan]")
        else:
            console.print("[green]Recording complete![/green]")

        console.print(f"[cyan]Duration:[/cyan] {_format_duration(elapsed)}")
        console.print(f"[cyan]Size:[/cyan] {_format_size(state.bytes_recorded)}")

        # Convert to MP3 if post-convert mode was used
        final_output: Path | str | None = state.output_file
        if output_format == AudioFormat.MP3 and state.output_file and not use_streaming_mp3:
            wav_path = state.output_file
            mp3_path = desired_mp3_path or wav_path.with_suffix(".mp3")
            console.print("[yellow]Converting to MP3...[/yellow]")

            if encode_to_mp3(wav_path, mp3_path, bitrate):
                final_output = mp3_path
                if not keep_wav:
                    wav_path.unlink()
                    console.print("[dim]Removed temporary WAV file[/dim]")
                console.print("[green]MP3 conversion complete![/green]")
            else:
                console.print("[red]MP3 conversion failed, keeping WAV file[/red]")

        console.print(f"[cyan]Saved to:[/cyan] {final_output}")

    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except NotImplementedError as e:
        console.print(f"[yellow]Not implemented:[/yellow] {e}")
        raise typer.Exit(1) from None
    finally:
        if audio_capture:
            audio_capture.terminate()


@app.command("stop")
def stop() -> None:
    """Stop the current recording (sends signal to running process)."""
    console.print("[yellow]Note:[/yellow] Use Ctrl+C in the recording terminal to stop.")
    console.print("[dim]Background recording management will be added in a future version.[/dim]")
