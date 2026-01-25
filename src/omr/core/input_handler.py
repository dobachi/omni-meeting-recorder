"""Keyboard input handler for recording control.

Provides non-blocking keyboard input handling for device switching
and recording control during active recording sessions.
"""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from enum import Enum, auto
from queue import Empty, Queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class InputCommand(Enum):
    """Commands triggered by keyboard input."""

    STOP = auto()  # Stop recording (q key)
    SWITCH_MIC = auto()  # Enter mic selection mode (m key)
    SWITCH_LOOPBACK = auto()  # Enter loopback selection mode (l key)
    SELECT_DEVICE = auto()  # Select device by number (0-9)
    CANCEL = auto()  # Cancel selection mode (Esc)
    REFRESH_DEVICES = auto()  # Refresh device list (r key)


class SelectionMode(Enum):
    """Current device selection mode."""

    NONE = auto()  # Normal recording mode
    MIC = auto()  # Selecting microphone
    LOOPBACK = auto()  # Selecting loopback device


@dataclass
class InputEvent:
    """Represents a keyboard input event."""

    command: InputCommand
    value: int | None = None  # Device number for SELECT_DEVICE

    def __repr__(self) -> str:
        if self.value is not None:
            return f"InputEvent({self.command.name}, value={self.value})"
        return f"InputEvent({self.command.name})"


class KeyInputHandler:
    """Handles keyboard input in a separate thread.

    Uses msvcrt on Windows for non-blocking keyboard input.
    On non-Windows platforms, provides a stub implementation.
    """

    def __init__(self) -> None:
        self._queue: Queue[InputEvent] = Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._selection_mode = SelectionMode.NONE
        self._lock = threading.Lock()
        self._is_windows = sys.platform == "win32"

    @property
    def selection_mode(self) -> SelectionMode:
        """Get the current selection mode."""
        with self._lock:
            return self._selection_mode

    def enter_selection_mode(self, mode: SelectionMode) -> None:
        """Enter device selection mode.

        Args:
            mode: The selection mode to enter (MIC or LOOPBACK)
        """
        with self._lock:
            self._selection_mode = mode

    def exit_selection_mode(self) -> None:
        """Exit device selection mode."""
        with self._lock:
            self._selection_mode = SelectionMode.NONE

    def start(self) -> None:
        """Start the keyboard input handler thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._input_loop,
            daemon=True,
            name="key_input_handler",
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the keyboard input handler thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def get_event(self, timeout: float = 0.1) -> InputEvent | None:
        """Get the next input event from the queue.

        Args:
            timeout: Maximum time to wait for an event in seconds.

        Returns:
            The next InputEvent, or None if no event is available.
        """
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def _input_loop(self) -> None:
        """Main input loop running in a separate thread."""
        if self._is_windows:
            self._windows_input_loop()
        else:
            self._unix_input_loop()

    def _windows_input_loop(self) -> None:
        """Windows-specific input loop using msvcrt."""
        import msvcrt

        while not self._stop_event.is_set():
            # Check if a key is available
            if msvcrt.kbhit():  # type: ignore[attr-defined]
                try:
                    # Get the key (bytes)
                    key = msvcrt.getch()  # type: ignore[attr-defined]
                    self._process_key(key)
                except Exception:
                    # Ignore any input errors
                    pass
            else:
                # Small sleep to prevent busy waiting
                self._stop_event.wait(0.05)

    def _unix_input_loop(self) -> None:
        """Unix-specific input loop (stub for cross-platform compatibility).

        Note: This is a basic implementation. For full Unix support,
        consider using termios/tty or a library like pynput.
        """
        import select

        while not self._stop_event.is_set():
            try:
                # Check if stdin has data available
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    if key:
                        self._process_key(key.encode())
            except Exception:
                # If select fails (not a terminal), just wait
                self._stop_event.wait(0.1)

    def _process_key(self, key: bytes) -> None:
        """Process a key press and generate appropriate event.

        Args:
            key: The key that was pressed (as bytes).
        """
        event: InputEvent | None = None

        with self._lock:
            mode = self._selection_mode

        # Handle key based on current mode
        if mode == SelectionMode.NONE:
            # Normal mode: handle control keys
            event = self._handle_normal_mode(key)
        else:
            # Selection mode: handle device selection
            event = self._handle_selection_mode(key)

        if event is not None:
            self._queue.put(event)

    def _handle_normal_mode(self, key: bytes) -> InputEvent | None:
        """Handle key press in normal (non-selection) mode.

        Args:
            key: The key that was pressed.

        Returns:
            An InputEvent if the key is recognized, None otherwise.
        """
        try:
            char = key.decode("utf-8").lower()
        except UnicodeDecodeError:
            return None

        if char == "q":
            return InputEvent(InputCommand.STOP)
        elif char == "m":
            return InputEvent(InputCommand.SWITCH_MIC)
        elif char == "l":
            return InputEvent(InputCommand.SWITCH_LOOPBACK)
        elif char == "r":
            return InputEvent(InputCommand.REFRESH_DEVICES)

        return None

    def _handle_selection_mode(self, key: bytes) -> InputEvent | None:
        """Handle key press in device selection mode.

        Args:
            key: The key that was pressed.

        Returns:
            An InputEvent if the key is recognized, None otherwise.
        """
        # Check for Escape key (0x1b)
        if key == b"\x1b":
            return InputEvent(InputCommand.CANCEL)

        try:
            char = key.decode("utf-8")
        except UnicodeDecodeError:
            return None

        # Check for number keys (0-9)
        if char.isdigit():
            device_num = int(char)
            return InputEvent(InputCommand.SELECT_DEVICE, value=device_num)

        # Also allow q to stop in selection mode
        if char.lower() == "q":
            return InputEvent(InputCommand.STOP)

        # Allow Escape via 'e' key as fallback
        if char.lower() == "e":
            return InputEvent(InputCommand.CANCEL)

        return None

    def __enter__(self) -> KeyInputHandler:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.stop()


def is_input_available() -> bool:
    """Check if keyboard input handling is available on this platform.

    Returns:
        True if keyboard input can be handled, False otherwise.
    """
    if sys.platform == "win32":
        try:
            import msvcrt  # noqa: F401

            return True
        except ImportError:
            return False
    else:
        # Unix platforms can use select with stdin
        return True
