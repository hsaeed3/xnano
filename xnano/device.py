"""xnano.device"""

from __future__ import annotations

from typing import Literal, TypeAlias

from xnano import _core
from xnano.layout import Size


ClearTypeName: TypeAlias = Literal[
    "all",
    "purge",
    "from_cursor_down",
    "from_cursor_up",
    "current_line",
    "until_new_line",
]
"""Terminal clear mode names."""


_CLEAR_TYPE: dict[ClearTypeName, _core.ClearType] = {
    "all": _core.ClearType.All,
    "purge": _core.ClearType.Purge,
    "from_cursor_down": _core.ClearType.FromCursorDown,
    "from_cursor_up": _core.ClearType.FromCursorUp,
    "current_line": _core.ClearType.CurrentLine,
    "until_new_line": _core.ClearType.UntilNewLine,
}


def _core_clear_type(value: ClearTypeName) -> _core.ClearType:
    return _CLEAR_TYPE[value]


def enable_raw_mode() -> None:
    """Enable terminal raw mode."""
    _core.enable_raw_mode()


def disable_raw_mode() -> None:
    """Disable terminal raw mode."""
    _core.disable_raw_mode()


def is_raw_mode_enabled() -> bool:
    """Return whether raw mode is currently enabled."""
    return _core.is_raw_mode_enabled()


def get_terminal_size() -> Size:
    """Return the terminal size in columns and rows."""
    native_size = _core.terminal_size()
    return Size(width=native_size.width, height=native_size.height)


def get_terminal_window_size() -> Size:
    """Return the terminal window size in columns and rows."""
    native_size = _core.terminal_window_size()
    return Size(width=native_size.width, height=native_size.height)


def scroll_up(count: int = 1) -> None:
    """Scroll the terminal buffer up."""
    _core.scroll_up(count)


def scroll_down(count: int = 1) -> None:
    """Scroll the terminal buffer down."""
    _core.scroll_down(count)


def clear_terminal(clear_type: ClearTypeName = "all") -> None:
    """Clear the terminal using the given clear mode."""
    _core.clear_terminal(_core_clear_type(clear_type))


def enter_alternate_screen() -> None:
    """Switch to the alternate screen buffer."""
    _core.enter_alternate_screen()


def leave_alternate_screen() -> None:
    """Leave the alternate screen buffer."""
    _core.leave_alternate_screen()


def set_terminal_title(title: str) -> None:
    """Set the terminal window title."""
    _core.set_terminal_title(title)


def enable_line_wrap() -> None:
    """Enable terminal line wrapping."""
    _core.enable_line_wrap()


def disable_line_wrap() -> None:
    """Disable terminal line wrapping."""
    _core.disable_line_wrap()


def begin_synchronized_update() -> None:
    """Begin a synchronized terminal update."""
    _core.begin_synchronized_update()


def end_synchronized_update() -> None:
    """End a synchronized terminal update."""
    _core.end_synchronized_update()


def supports_keyboard_enhancement() -> bool:
    """Return whether the terminal supports keyboard enhancement."""
    return _core.supports_keyboard_enhancement()


__all__ = (
    "ClearTypeName",
    "begin_synchronized_update",
    "clear_terminal",
    "disable_line_wrap",
    "disable_raw_mode",
    "enable_line_wrap",
    "enable_raw_mode",
    "end_synchronized_update",
    "enter_alternate_screen",
    "get_terminal_size",
    "get_terminal_window_size",
    "is_raw_mode_enabled",
    "leave_alternate_screen",
    "scroll_down",
    "scroll_up",
    "set_terminal_title",
    "supports_keyboard_enhancement",
)
