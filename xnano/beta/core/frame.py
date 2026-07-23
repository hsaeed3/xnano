"""xnano.beta.core.frame

---

Inspect immutable text, cursor, device, and revision data from a rendered
frame.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping, Sequence


@dataclasses.dataclass(frozen=True, slots=True)
class Frame:
    """Immutable snapshot of one painted native frame.

    Example:
        ``Frame(width=20, height=4, text="Ready")``

    Attributes:
        width: Frame width in cells.
        height: Frame height in cells.
        text: Plain-text rows joined by newlines.
        ansi: ANSI-styled serialization of the buffer.
        cursor_position: ``(x, y)`` caret cell, when known.
        cursor_visible: Whether the caret is shown.
        cursor_style: Caret style name when known.
        title: Terminal / document title when set.
        commands: Device commands queued with this frame.
        revision: Monotonic revision for diff consumers.
    """

    width: int
    """Frame width in cells."""
    height: int
    """Frame height in cells."""
    text: str = ""
    """Plain-text cell rows."""
    ansi: str = ""
    """ANSI-styled cell rows."""
    cursor_position: tuple[int, int] | None = None
    """Caret position in cells."""
    cursor_visible: bool = True
    """Whether the caret is visible."""
    cursor_style: str | None = None
    """Caret shape and blink style."""
    title: str | None = None
    """Window or document title."""
    commands: tuple[Mapping[str, Any], ...] = ()
    """Device commands emitted with the frame."""
    revision: int = 0
    """Monotonic frame revision."""

    @property
    def rows(self) -> tuple[str, ...]:
        """Plain-text rows of the frame."""
        if not self.text:
            return tuple("" for _ in range(self.height))
        lines = self.text.split("\n")
        if len(lines) < self.height:
            lines = lines + [""] * (self.height - len(lines))
        return tuple(lines[: self.height])

    def contains(self, needle: str) -> bool:
        """Return whether plain text contains ``needle``."""
        return needle in self.text


def frame_from_terminal(terminal: Any, *, revision: int = 0) -> Frame:
    """Build a ``Frame`` snapshot from a terminal or runtime.

    Args:
        terminal: Object exposing size/output/cursor/device.
        revision: Monotonic revision to stamp on the frame.

    Returns:
        An immutable ``Frame``.
    """
    size: Any = getattr(terminal, "size", (0, 0))
    if callable(size):
        size = size()
    if hasattr(size, "width") and hasattr(size, "height"):
        width, height = int(size.width), int(size.height)
    else:
        width, height = int(size[0]), int(size[1])
    text = ""
    ansi = ""
    get_output = getattr(terminal, "get_output", None)
    get_ansi = getattr(terminal, "get_output_as_ansi", None)
    if callable(get_output):
        text = str(get_output())
    if callable(get_ansi):
        ansi = str(get_ansi())
    cursor = getattr(terminal, "cursor", None)
    position = None
    visible = True
    style = None
    if cursor is not None:
        get_position = getattr(cursor, "get_position", None)
        pos = (
            get_position()
            if callable(get_position)
            else getattr(cursor, "position", None)
        )
        if callable(pos):
            pos = pos()
        if isinstance(pos, Sequence) and len(pos) >= 2:
            position = (int(pos[0]), int(pos[1]))
        visible = bool(getattr(cursor, "visible", True))
        style = getattr(cursor, "style", None)
        if callable(style):
            style = style()
    device = getattr(terminal, "device", None)
    title = None
    if device is not None:
        title = getattr(device, "title", None)
        if callable(title):
            title = title()
    commands = tuple(getattr(terminal, "_frame_commands", ()) or ())
    return Frame(
        width=width,
        height=height,
        text=text,
        ansi=ansi,
        cursor_position=position,
        cursor_visible=visible,
        cursor_style=str(style) if style is not None else None,
        title=str(title) if title is not None else None,
        commands=commands,
        revision=revision,
    )


__all__ = ("Frame", "frame_from_terminal")
