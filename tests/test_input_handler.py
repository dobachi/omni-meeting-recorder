"""Tests for the keyboard input handler module."""

import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from omr.core.input_handler import (
    InputCommand,
    InputEvent,
    KeyInputHandler,
    SelectionMode,
    is_input_available,
)


class TestInputCommand:
    """Tests for InputCommand enum."""

    def test_all_commands_defined(self):
        """Verify all expected commands are defined."""
        assert InputCommand.STOP is not None
        assert InputCommand.SWITCH_MIC is not None
        assert InputCommand.SWITCH_LOOPBACK is not None
        assert InputCommand.SELECT_DEVICE is not None
        assert InputCommand.CANCEL is not None
        assert InputCommand.REFRESH_DEVICES is not None


class TestSelectionMode:
    """Tests for SelectionMode enum."""

    def test_all_modes_defined(self):
        """Verify all expected modes are defined."""
        assert SelectionMode.NONE is not None
        assert SelectionMode.MIC is not None
        assert SelectionMode.LOOPBACK is not None


class TestInputEvent:
    """Tests for InputEvent dataclass."""

    def test_create_event_without_value(self):
        """Test creating an event without a value."""
        event = InputEvent(InputCommand.STOP)
        assert event.command == InputCommand.STOP
        assert event.value is None

    def test_create_event_with_value(self):
        """Test creating an event with a value."""
        event = InputEvent(InputCommand.SELECT_DEVICE, value=5)
        assert event.command == InputCommand.SELECT_DEVICE
        assert event.value == 5

    def test_repr_without_value(self):
        """Test string representation without value."""
        event = InputEvent(InputCommand.STOP)
        assert "STOP" in repr(event)
        assert "value" not in repr(event)

    def test_repr_with_value(self):
        """Test string representation with value."""
        event = InputEvent(InputCommand.SELECT_DEVICE, value=3)
        assert "SELECT_DEVICE" in repr(event)
        assert "value=3" in repr(event)


class TestKeyInputHandler:
    """Tests for KeyInputHandler class."""

    def test_initial_state(self):
        """Test initial state of handler."""
        handler = KeyInputHandler()
        assert handler.selection_mode == SelectionMode.NONE

    def test_enter_selection_mode(self):
        """Test entering selection mode."""
        handler = KeyInputHandler()
        handler.enter_selection_mode(SelectionMode.MIC)
        assert handler.selection_mode == SelectionMode.MIC

        handler.enter_selection_mode(SelectionMode.LOOPBACK)
        assert handler.selection_mode == SelectionMode.LOOPBACK

    def test_exit_selection_mode(self):
        """Test exiting selection mode."""
        handler = KeyInputHandler()
        handler.enter_selection_mode(SelectionMode.MIC)
        handler.exit_selection_mode()
        assert handler.selection_mode == SelectionMode.NONE

    def test_start_stop(self):
        """Test starting and stopping the handler."""
        handler = KeyInputHandler()
        handler.start()
        assert handler._thread is not None
        assert handler._thread.is_alive()

        handler.stop()
        # Thread should stop within timeout
        time.sleep(0.2)
        assert not handler._thread.is_alive() if handler._thread else True

    def test_context_manager(self):
        """Test using handler as context manager."""
        with KeyInputHandler() as handler:
            assert handler._thread is not None
            assert handler._thread.is_alive()
        # After exit, thread should be stopped
        time.sleep(0.2)

    def test_get_event_timeout(self):
        """Test get_event returns None on timeout."""
        handler = KeyInputHandler()
        event = handler.get_event(timeout=0.01)
        assert event is None

    def test_process_key_q_in_normal_mode(self):
        """Test 'q' key generates STOP command in normal mode."""
        handler = KeyInputHandler()
        handler._process_key(b"q")
        event = handler.get_event(timeout=0.1)
        assert event is not None
        assert event.command == InputCommand.STOP

    def test_process_key_m_in_normal_mode(self):
        """Test 'm' key generates SWITCH_MIC command in normal mode."""
        handler = KeyInputHandler()
        handler._process_key(b"m")
        event = handler.get_event(timeout=0.1)
        assert event is not None
        assert event.command == InputCommand.SWITCH_MIC

    def test_process_key_l_in_normal_mode(self):
        """Test 'l' key generates SWITCH_LOOPBACK command in normal mode."""
        handler = KeyInputHandler()
        handler._process_key(b"l")
        event = handler.get_event(timeout=0.1)
        assert event is not None
        assert event.command == InputCommand.SWITCH_LOOPBACK

    def test_process_key_r_in_normal_mode(self):
        """Test 'r' key generates REFRESH_DEVICES command in normal mode."""
        handler = KeyInputHandler()
        handler._process_key(b"r")
        event = handler.get_event(timeout=0.1)
        assert event is not None
        assert event.command == InputCommand.REFRESH_DEVICES

    def test_process_number_in_selection_mode(self):
        """Test number keys generate SELECT_DEVICE in selection mode."""
        handler = KeyInputHandler()
        handler.enter_selection_mode(SelectionMode.MIC)

        handler._process_key(b"5")
        event = handler.get_event(timeout=0.1)
        assert event is not None
        assert event.command == InputCommand.SELECT_DEVICE
        assert event.value == 5

    def test_process_escape_in_selection_mode(self):
        """Test Escape key generates CANCEL in selection mode."""
        handler = KeyInputHandler()
        handler.enter_selection_mode(SelectionMode.MIC)

        handler._process_key(b"\x1b")  # Escape key
        event = handler.get_event(timeout=0.1)
        assert event is not None
        assert event.command == InputCommand.CANCEL

    def test_process_q_in_selection_mode(self):
        """Test 'q' key still generates STOP in selection mode."""
        handler = KeyInputHandler()
        handler.enter_selection_mode(SelectionMode.MIC)

        handler._process_key(b"q")
        event = handler.get_event(timeout=0.1)
        assert event is not None
        assert event.command == InputCommand.STOP

    def test_unknown_key_ignored_in_normal_mode(self):
        """Test unknown keys are ignored in normal mode."""
        handler = KeyInputHandler()
        handler._process_key(b"x")
        event = handler.get_event(timeout=0.01)
        assert event is None

    def test_case_insensitive_keys(self):
        """Test keys are case insensitive."""
        handler = KeyInputHandler()

        handler._process_key(b"Q")
        event = handler.get_event(timeout=0.1)
        assert event is not None
        assert event.command == InputCommand.STOP

        handler._process_key(b"M")
        event = handler.get_event(timeout=0.1)
        assert event is not None
        assert event.command == InputCommand.SWITCH_MIC

    def test_double_start(self):
        """Test calling start twice doesn't create multiple threads."""
        handler = KeyInputHandler()
        handler.start()
        thread1 = handler._thread

        handler.start()  # Second call
        thread2 = handler._thread

        assert thread1 is thread2
        handler.stop()


class TestIsInputAvailable:
    """Tests for is_input_available function."""

    def test_returns_boolean(self):
        """Test function returns a boolean."""
        result = is_input_available()
        assert isinstance(result, bool)

    @patch.object(sys, "platform", "win32")
    def test_windows_platform(self):
        """Test on Windows platform."""
        # Just verify it doesn't crash
        result = is_input_available()
        assert isinstance(result, bool)

    @patch.object(sys, "platform", "linux")
    def test_linux_platform(self):
        """Test on Linux platform."""
        result = is_input_available()
        assert result is True
