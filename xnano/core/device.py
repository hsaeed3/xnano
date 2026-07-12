"""xnano.core.device"""

from __future__ import annotations

import abc
from typing import Literal, TypeAlias

from xnano._types import Size


ClearType: TypeAlias = Literal[
    "all",
    "purge",
    "from_cursor_down",
    "from_cursor_up",
    "current_line",
    "until_new_line",
]
"""Display clear intents shared by terminal and web device adapters.

Values:
    ``"all"``: Clear the entire display area.
    ``"purge"``: Clear and purge scrollback where supported.
    ``"from_cursor_down"``: Clear from the cursor to the end of the
        display.
    ``"from_cursor_up"``: Clear from the cursor to the start of the
        display.
    ``"current_line"``: Clear only the current line.
    ``"until_new_line"``: Clear from the cursor to the end of the
        current line.
"""


CursorStyle: TypeAlias = Literal[
    "default",
    "blinking_block",
    "steady_block",
    "blinking_underline",
    "steady_underline",
    "blinking_bar",
    "steady_bar",
]
"""Cursor shape/blink intents shared by interface kinds.

Values:
    ``"default"``: Host default cursor style.
    ``"blinking_block"``: Blinking block cursor.
    ``"steady_block"``: Steady (non-blinking) block cursor.
    ``"blinking_underline"``: Blinking underline cursor.
    ``"steady_underline"``: Steady underline cursor.
    ``"blinking_bar"``: Blinking vertical bar cursor.
    ``"steady_bar"``: Steady vertical bar cursor.
"""


class AbstractDevice(abc.ABC):
    """Intent-level device contract shared by tui and webui.

    Interface kinds implement the mechanisms (crossterm escapes, DOM /
    browser APIs). The DSL only speaks these intents: title, clear,
    size, scroll, and clipboard.
    """

    @property
    @abc.abstractmethod
    def title(self) -> str | None:
        """Window or page title, if one has been set."""

    @title.setter
    @abc.abstractmethod
    def title(self, value: str | None) -> None:
        """Set the window or page title.

        Args:
            value: Title text, or ``None`` to clear/reset when
                supported.
        """

    @abc.abstractmethod
    def clear(self, kind: ClearType = "all") -> None:
        """Clear the active display surface.

        Args:
            kind: Which clear intent to apply.
        """

    @property
    @abc.abstractmethod
    def size(self) -> Size:
        """Current display size in interface units (cells/logical)."""

    @abc.abstractmethod
    def scroll_up(self, n: int = 1) -> None:
        """Scroll the display up by ``n`` units.

        Args:
            n: Number of lines (or equivalent units) to scroll.
        """

    @abc.abstractmethod
    def scroll_down(self, n: int = 1) -> None:
        """Scroll the display down by ``n`` units.

        Args:
            n: Number of lines (or equivalent units) to scroll.
        """

    @abc.abstractmethod
    def copy_to_clipboard(self, text: str) -> None:
        """Copy ``text`` to the system/browser clipboard.

        Args:
            text: Payload to place on the clipboard.
        """


class AbstractCursor(abc.ABC):
    """Intent-level cursor contract shared by tui and webui.

    Terminal adapters map these intents to crossterm cursor APIs.
    Web adapters map visibility/style to caret focus and pointer
    classes; position moves may be no-ops where unsupported.
    """

    @property
    @abc.abstractmethod
    def visible(self) -> bool:
        """Whether the cursor/caret is currently visible."""

    @visible.setter
    @abc.abstractmethod
    def visible(self, value: bool) -> None:
        """Show or hide the cursor/caret.

        Args:
            value: ``True`` to show, ``False`` to hide.
        """

    @property
    @abc.abstractmethod
    def style(self) -> CursorStyle:
        """Current cursor shape/blink style intent."""

    @style.setter
    @abc.abstractmethod
    def style(self, value: CursorStyle) -> None:
        """Set the cursor shape/blink style intent.

        Args:
            value: A :data:`CursorStyle` literal.
        """

    def move_to(self, x: int, y: int) -> None:
        """Move the cursor to cell ``(x, y)`` when supported.

        Default is a no-op so interface kinds without a free-moving
        caret (e.g. many web targets) need not override.

        Args:
            x: Column in interface units.
            y: Row in interface units.
        """
        return None


__all__ = (
    "AbstractCursor",
    "AbstractDevice",
    "ClearType",
    "CursorStyle",
)
