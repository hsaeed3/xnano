"""xnano.webui.device

---

Web implementations of ``AbstractDevice`` / ``AbstractCursor``. Thin
adapters: page title, logical size, scroll/clipboard intents that the
host can lower to browser APIs later.
"""

from __future__ import annotations

from typing import Any

from xnano.core.device import (
    AbstractCursor,
    AbstractDevice,
    ClearType,
    CursorStyle,
)
from xnano._types import Size


class WebDevice(AbstractDevice):
    """Browser-side device intents for a ``Web`` / session host."""

    def __init__(self, host: Any, *, title: str | None = None) -> None:
        self._host = host
        self._title = title
        self._size = Size(width=80, height=24)

    @property
    def title(self) -> str | None:
        return self._title

    @title.setter
    def title(self, value: str | None) -> None:
        self._title = value

    def clear(self, kind: ClearType = "all") -> None:
        return None

    @property
    def size(self) -> Size:
        return self._size

    def set_size(self, width: int, height: int) -> None:
        """Override logical lattice size used by Stage/LayoutMap."""
        self._size = Size(width=width, height=height)

    def scroll_up(self, n: int = 1) -> None:
        return None

    def scroll_down(self, n: int = 1) -> None:
        return None

    def copy_to_clipboard(self, text: str) -> None:
        return None


class WebCursor(AbstractCursor):
    """Browser caret / pointer style facade."""

    def __init__(self, host: Any) -> None:
        self._host = host
        self._visible = True
        self._style: CursorStyle = "default"

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._visible = bool(value)

    @property
    def style(self) -> CursorStyle:
        return self._style

    @style.setter
    def style(self, value: CursorStyle) -> None:
        self._style = value


__all__ = ("WebCursor", "WebDevice")
