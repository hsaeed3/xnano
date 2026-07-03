"""xnano.cursor"""

from __future__ import annotations

from typing import Literal, TypeAlias

from xnano import _core
from xnano.layout import Position


CursorStyleName: TypeAlias = Literal[
    "default",
    "blinking_block",
    "steady_block",
    "blinking_underline",
    "steady_underline",
    "blinking_bar",
    "steady_bar",
]
"""Terminal cursor shape names."""


_CURSOR_STYLE: dict[CursorStyleName, _core.CursorStyle] = {
    "default": _core.CursorStyle.DefaultUserShape,
    "blinking_block": _core.CursorStyle.BlinkingBlock,
    "steady_block": _core.CursorStyle.SteadyBlock,
    "blinking_underline": _core.CursorStyle.BlinkingUnderline,
    "steady_underline": _core.CursorStyle.SteadyUnderline,
    "blinking_bar": _core.CursorStyle.BlinkingBar,
    "steady_bar": _core.CursorStyle.SteadyBar,
}


def _core_cursor_style(value: CursorStyleName) -> _core.CursorStyle:
    return _CURSOR_STYLE[value]


def show_cursor() -> None:
    """Show the terminal cursor."""
    _core.show_cursor()


def hide_cursor() -> None:
    """Hide the terminal cursor."""
    _core.hide_cursor()


def save_cursor_position() -> None:
    """Save the current cursor position."""
    _core.save_cursor_position()


def restore_cursor_position() -> None:
    """Restore the previously saved cursor position."""
    _core.restore_cursor_position()


def move_cursor_to(x: int, y: int) -> None:
    """Move the cursor to the given coordinates."""
    _core.move_cursor_to(x, y)


def move_cursor_to_column(x: int) -> None:
    """Move the cursor to column ``x`` on the current row."""
    _core.move_cursor_to_column(x)


def move_cursor_to_row(y: int) -> None:
    """Move the cursor to row ``y`` on the current column."""
    _core.move_cursor_to_row(y)


def move_cursor_up(count: int = 1) -> None:
    """Move the cursor up by ``count`` cells."""
    _core.move_cursor_up(count)


def move_cursor_down(count: int = 1) -> None:
    """Move the cursor down by ``count`` cells."""
    _core.move_cursor_down(count)


def move_cursor_left(count: int = 1) -> None:
    """Move the cursor left by ``count`` cells."""
    _core.move_cursor_left(count)


def move_cursor_right(count: int = 1) -> None:
    """Move the cursor right by ``count`` cells."""
    _core.move_cursor_right(count)


def move_cursor_to_next_line(count: int = 1) -> None:
    """Move the cursor to the next line."""
    _core.move_cursor_to_next_line(count)


def move_cursor_to_previous_line(count: int = 1) -> None:
    """Move the cursor to the previous line."""
    _core.move_cursor_to_previous_line(count)


def enable_cursor_blinking() -> None:
    """Enable cursor blinking."""
    _core.enable_cursor_blinking()


def disable_cursor_blinking() -> None:
    """Disable cursor blinking."""
    _core.disable_cursor_blinking()


def set_cursor_style(style: CursorStyleName) -> None:
    """Set the terminal cursor style."""
    _core.set_cursor_style(_core_cursor_style(style))


def get_cursor_position() -> Position:
    """Query the current cursor position."""
    native_position = _core.get_cursor_position()
    return Position(x=native_position.x, y=native_position.y)


__all__ = (
    "CursorStyleName",
    "disable_cursor_blinking",
    "enable_cursor_blinking",
    "get_cursor_position",
    "hide_cursor",
    "move_cursor_down",
    "move_cursor_left",
    "move_cursor_right",
    "move_cursor_to",
    "move_cursor_to_column",
    "move_cursor_to_next_line",
    "move_cursor_to_previous_line",
    "move_cursor_to_row",
    "move_cursor_up",
    "restore_cursor_position",
    "save_cursor_position",
    "set_cursor_style",
    "show_cursor",
)
