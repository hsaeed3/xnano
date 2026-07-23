"""xnano.terminal.cursor

---

Terminal cursor controls (visibility, style, position) for a live
``Terminal`` session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypeAlias

import xnano_core.rust.native as native

from xnano import _core_bindings as native_types
from xnano._types import Coordinate
from xnano.core.device import AbstractCursor

if TYPE_CHECKING:
    from xnano.terminal.terminal import Terminal


CursorStyle: TypeAlias = Literal[
    "default",
    "blinking_block",
    "steady_block",
    "blinking_underline",
    "steady_underline",
    "blinking_bar",
    "steady_bar",
]
"""The style of the cursor in the terminal.

Values:
    ``"default"``: The default cursor style (usually a blinking block on most terminals).
        Example: The cursor blinks as a solid block at the current text position.

    ``"blinking_block"``: A blinking block cursor.
        Example: █ (block shape), blinks at a regular interval.

    ``"steady_block"``: A steady (non-blinking) block cursor.
        Example: █ (block shape), remains visible and does not blink.

    ``"blinking_underline"``: A blinking underline cursor.
        Example: _ (underline shape), blinks beneath the active character.

    ``"steady_underline"``: A steady (non-blinking) underline cursor.
        Example: _ (underline shape), remains visible and does not blink.

    ``"blinking_bar"``: A blinking vertical bar cursor.
        Example: | (vertical bar shape), blinks at the current position.

    ``"steady_bar"``: A steady (non-blinking) vertical bar cursor.
        Example: | (vertical bar shape), remains visible and does not blink.
"""


class TerminalCursor(AbstractCursor):
    """Show, hide, style, and move the terminal cursor.

    Obtained from a live ``Terminal`` (``terminal.cursor`` or
    ``ctx.cursor`` in hooks). Do not construct this class yourself.
    """

    __slots__ = (
        "_terminal",
        "_style",
        "_visible",
    )

    def __init__(
        self,
        _terminal: "Terminal[Any]",
        *,
        _visible: bool = True,
        _style: CursorStyle = "default",
    ) -> None:
        from xnano.terminal.terminal import Terminal

        if not isinstance(_terminal, Terminal):
            raise TypeError("`_terminal` must be a live `Terminal` session.")
        self._terminal = _terminal
        self._visible = _visible
        self._style = _style

    @property
    def visible(self) -> bool:
        """Whether the cursor is currently visible on the terminal
        screen.
        """
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError("`visible` must be a boolean.")
        self._visible = value
        if value:
            native.show_cursor()
        else:
            native.hide_cursor()

    @property
    def style(self) -> CursorStyle:
        """The style of the cursor in the terminal."""
        return self._style

    @style.setter
    def style(self, value: CursorStyle) -> None:
        if not value in CursorStyle.__args__:
            raise ValueError(
                "`style` must be one of the following: "
                + ", ".join(CursorStyle.__args__)
            )
        self._style = value
        native.set_cursor_style(native_types._NATIVE_CURSOR_STYLE_TYPES[value])

    def get_position(self) -> Coordinate:
        """Get the current cursor position."""
        position = native.get_cursor_position()
        return (position.x, position.y)

    def save_position(self) -> None:
        """Save the current cursor position."""
        native.save_cursor_position()

    def restore_position(self) -> None:
        """Restore the saved cursor position."""
        native.restore_cursor_position()

    def move_to(self, x: int, y: int) -> None:
        """Move the cursor to the given position."""
        native.move_cursor_to(x, y)

    def move_to_column(self, x: int) -> None:
        """Move the cursor to the given column."""
        native.move_cursor_to_column(x)

    def move_to_row(self, y: int) -> None:
        """Move the cursor to the given row."""
        native.move_cursor_to_row(y)

    def move_up(self, count: int = 1) -> None:
        """Move the cursor up by the given count."""
        native.move_cursor_up(count)

    def move_down(self, count: int = 1) -> None:
        """Move the cursor down by the given count."""
        native.move_cursor_down(count)

    def move_left(self, count: int = 1) -> None:
        """Move the cursor left by the given count."""
        native.move_cursor_left(count)

    def move_right(self, count: int = 1) -> None:
        """Move the cursor right by the given count."""
        native.move_cursor_right(count)

    def move_to_next_line(self, count: int = 1) -> None:
        """Move the cursor to the next line by the given count."""
        native.move_cursor_to_next_line(count)

    def move_to_previous_line(self, count: int = 1) -> None:
        """Move the cursor to the previous line by the given count."""
        native.move_cursor_to_previous_line(count)

    def enable_blinking(self) -> None:
        """Enable cursor blinking."""
        native.enable_cursor_blinking()

    def disable_blinking(self) -> None:
        """Disable cursor blinking."""
        native.disable_cursor_blinking()


__all__ = ("TerminalCursor", "CursorStyle")
