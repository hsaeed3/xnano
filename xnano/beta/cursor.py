"""xnano.beta.cursor

---

Show, hide, style, and move the cursor in live or offscreen sessions.

Position, visibility, and style are always tracked locally, so the caret
state a ``Frame`` snapshot reports is correct for a live or an offscreen
runtime (tests, and every web visitor's session). Only a *live* runtime
issues the real terminal escape codes; an offscreen runtime must not, or
it would write control sequences to whatever process owns stdout.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias, cast

import xnano_core.rust.native as native

from xnano.beta.types import Coordinate

if TYPE_CHECKING:
    from xnano.beta.core.runtime import Runtime


CursorStyle: TypeAlias = Literal[
    "default",
    "blinking_block",
    "steady_block",
    "blinking_underline",
    "steady_underline",
    "blinking_bar",
    "steady_bar",
]
"""The caret rendering style.

Values:
    ``"default"``: The terminal's default caret style.
    ``"blinking_block"``: A blinking block. (``█``)
    ``"steady_block"``: A steady (non-blinking) block. (``█``)
    ``"blinking_underline"``: A blinking underline. (``_``)
    ``"steady_underline"``: A steady (non-blinking) underline. (``_``)
    ``"blinking_bar"``: A blinking vertical bar. (``|``)
    ``"steady_bar"``: A steady (non-blinking) vertical bar. (``|``)
"""


class Cursor:
    """Show, hide, style, and move the caret for a ``Runtime`` session.

    Obtained from ``runtime.cursor`` — do not construct this class
    yourself.

    Attributes:
        visible: Whether the caret is shown.
        style: Caret rendering style.
        position: Current ``(x, y)`` position in cells.

    Example:
        >>> from xnano.beta.core.runtime import Runtime
        >>> runtime = Runtime.offscreen(20, 4)
        >>> runtime.cursor.position = (3, 1)
        >>> runtime.cursor.position
        (3, 1)
        >>> runtime.close()
    """

    __slots__ = (
        "_runtime",
        "_visible",
        "_style",
        "_x",
        "_y",
        "_saved_position",
        "_blinking",
    )

    def __init__(self, runtime: "Runtime") -> None:
        self._runtime = runtime
        self._visible = True
        self._style: CursorStyle = "default"
        self._x = 0
        self._y = 0
        self._saved_position: Coordinate | None = None
        self._blinking = True

    def _is_live(self) -> bool:
        """Whether the owning runtime drives a real terminal session."""
        return self._runtime.is_live

    @property
    def _session(self):
        """Native session controlled by this cursor."""
        return self._runtime.session

    @property
    def visible(self) -> bool:
        """Whether the caret is currently shown."""
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._visible = value
        if self._is_live():
            if value:
                self._session.show_cursor()
            else:
                self._session.hide_cursor()

    @property
    def style(self) -> CursorStyle:
        """The caret's rendering style."""
        return self._style

    @style.setter
    def style(self, value: CursorStyle) -> None:
        self._set_style(value)

    def _set_style(self, value: CursorStyle) -> None:
        """Validate and apply a native cursor style."""
        if value not in CursorStyle.__args__:
            raise ValueError(
                "`style` must be one of the following: "
                + ", ".join(CursorStyle.__args__)
            )
        self._style = value
        if not self._is_live():
            return
        styles = {
            "default": native.CursorStyle.DefaultUserShape,
            "blinking_block": native.CursorStyle.BlinkingBlock,
            "steady_block": native.CursorStyle.SteadyBlock,
            "blinking_underline": native.CursorStyle.BlinkingUnderline,
            "steady_underline": native.CursorStyle.SteadyUnderline,
            "blinking_bar": native.CursorStyle.BlinkingBar,
            "steady_bar": native.CursorStyle.SteadyBar,
        }
        self._session.set_cursor_style(styles[value])

    def get_position(self) -> Coordinate:
        """The locally tracked ``(x, y)`` caret position."""
        return (self._x, self._y)

    @property
    def position(self) -> Coordinate:
        """The current ``(x, y)`` caret position."""
        return (self._x, self._y)

    @position.setter
    def position(self, value: Coordinate) -> None:
        self.move(*value)

    def move(self, x: int, y: int) -> None:
        """Move the caret to ``(x, y)``."""
        self._x, self._y = x, y
        if self._is_live():
            self._session.move_cursor_to(x, y)

    def move_up(self, count: int = 1) -> None:
        """Move the caret up by ``count`` rows."""
        self._y = max(0, self._y - count)
        self.move(self._x, self._y)

    def move_down(self, count: int = 1) -> None:
        """Move the caret down by ``count`` rows."""
        self._y += count
        self.move(self._x, self._y)

    def move_left(self, count: int = 1) -> None:
        """Move the caret left by ``count`` columns."""
        self._x = max(0, self._x - count)
        self.move(self._x, self._y)

    def move_right(self, count: int = 1) -> None:
        """Move the caret right by ``count`` columns."""
        self._x += count
        self.move(self._x, self._y)

    def save(self) -> None:
        """Save the current caret position."""
        self._saved_position = (self._x, self._y)
        if self._is_live():
            self._session.save_cursor_position()

    def restore(self) -> None:
        """Restore the previously saved caret position."""
        if self._saved_position is not None:
            self._x, self._y = self._saved_position
        if self._is_live():
            self._session.restore_cursor_position()

    def enable_blinking(self) -> None:
        """Enable caret blinking."""
        self._blinking = True
        if self._style in {"steady_block", "steady_underline", "steady_bar"}:
            self._set_style(
                cast(
                    CursorStyle,
                    {
                        "steady_block": "blinking_block",
                        "steady_underline": "blinking_underline",
                        "steady_bar": "blinking_bar",
                    }[self._style],
                )
            )

    def disable_blinking(self) -> None:
        """Disable caret blinking."""
        self._blinking = False
        if self._style.startswith("blinking_"):
            self._set_style(
                cast(
                    CursorStyle,
                    {
                        "blinking_block": "steady_block",
                        "blinking_underline": "steady_underline",
                        "blinking_bar": "steady_bar",
                    }[self._style],
                )
            )


__all__ = ("Cursor", "CursorStyle")
