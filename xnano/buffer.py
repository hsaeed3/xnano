"""xnano.buffer"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

from xnano import _core
from xnano._convert import unwrap
from xnano.color import Color
from xnano.layout import Rectangle, RectangleLike
from xnano.style import Modifier, Style


class Buffer:
    """An off-screen pixel/character grid representing a terminal render buffer.

    ``Buffer`` is primarily used to represent intermediate visual states
    for effects processing, testing layouts, or compositing complex frames.
    """

    __slots__ = ("_inner",)
    _inner: _core.Buffer

    def __init__(self) -> None:
        raise TypeError(
            "Buffer instances must be created using factory methods: "
            "Buffer.empty(area)"
        )

    @classmethod
    def _from_core(cls, inner: _core.Buffer) -> Buffer:
        """Construct from a native ``_core.Buffer``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Buffer:
        """Return the native buffer."""
        return self._inner

    @classmethod
    def empty(cls, area: RectangleLike) -> Buffer:
        """Create an empty Buffer of the specified size.

        Args:
            area: The Rectangle area of the buffer.
        """
        from xnano.layout import _resolve_rectangle

        resolved_area = _resolve_rectangle(area)
        return cls._from_core(_core.Buffer.empty(resolved_area._to_core()))

    @property
    def area(self) -> Rectangle:
        """The bounding rectangle layout area of the buffer."""
        inner_rect = self._inner.area
        return Rectangle(
            x=inner_rect.x,
            y=inner_rect.y,
            width=inner_rect.width,
            height=inner_rect.height,
        )

    def render_widget(self, widget: Any, area: RectangleLike) -> None:
        """Render a widget into the specified area of this buffer.

        Args:
            widget: The widget to render.
            area: The rectangle area of the buffer to draw into.
        """
        from xnano.layout import _resolve_rectangle

        resolved_area = _resolve_rectangle(area)
        if isinstance(widget, str):
            from xnano.widgets import Paragraph

            widget = Paragraph(widget)
        self._inner.render_widget(unwrap(widget), resolved_area._to_core())

    def render_stateful_widget(
        self, widget: Any, area: RectangleLike, state: Any
    ) -> None:
        """Render a stateful widget using its mutable state into this buffer.

        Args:
            widget: The stateful widget.
            area: The rectangle area to draw into.
            state: The mutable widget state.
        """
        from xnano.layout import _resolve_rectangle

        resolved_area = _resolve_rectangle(area)
        self._inner.render_stateful_widget(
            unwrap(widget), resolved_area._to_core(), unwrap(state)
        )

    def render(
        self,
        renderable: Sequence[
            Any | tuple[Any, RectangleLike] | tuple[Any, RectangleLike, Any]
        ]
        | Any,
        area: RectangleLike | None = None,
    ) -> None:
        """Render a widget or sequence of widgets into this buffer.

        Args:
            renderable: A single widget to render, or a sequence of widgets
                or layout tuples ``(widget, area)`` or ``(widget, area, state)``.
            area: Default area to render into if rendering a single widget.
                If not specified, defaults to the entire buffer area.
        """
        from collections.abc import Sequence
        from xnano.layout import _resolve_rectangle

        if isinstance(renderable, Sequence) and not isinstance(
            renderable, (str, bytes)
        ):
            for item in renderable:
                if isinstance(item, tuple):
                    if len(item) == 2:
                        widget, item_area = item
                        self.render_widget(
                            widget, _resolve_rectangle(item_area)
                        )
                    elif len(item) == 3:
                        widget, item_area, state = item
                        self.render_stateful_widget(
                            widget, _resolve_rectangle(item_area), state
                        )
                    else:
                        raise ValueError(
                            f"Invalid draw tuple: {item!r}. "
                            f"Expected 2 or 3 elements."
                        )
                else:
                    self.render_widget(
                        item,
                        _resolve_rectangle(area)
                        if area is not None
                        else self.area,
                    )
        else:
            self.render_widget(
                renderable,
                _resolve_rectangle(area) if area is not None else self.area,
            )

    def cell_symbol(self, x: int, y: int) -> str:
        """Return the character symbol printed at the given coordinates."""
        return self._inner.cell_symbol(x, y)

    def cell_foreground(self, x: int, y: int) -> Color:
        """Return the Color of the text at the given coordinates."""
        return Color.from_native(self._inner.cell_fg(x, y))

    def cell_background(self, x: int, y: int) -> Color:
        """Return the Color of the cell background at the given coordinates."""
        return Color.from_native(self._inner.cell_bg(x, y))

    # Backward compatibility aliases
    cell_fg = cell_foreground
    cell_bg = cell_background

    def cell_modifier(self, x: int, y: int) -> Modifier:
        """Return the text style Modifiers of the cell at the given coordinates."""
        return Modifier._from_core(self._inner.cell_modifier(x, y))

    def set_string(self, x: int, y: int, string: str, style: Style) -> None:
        """Write a string of characters starting at the given coordinates
        using the specified style.
        """
        self._inner.set_string(x, y, string, style._to_core())

    def lines(self) -> list[str]:
        """Return the text content of the buffer as a list of strings,
        one per line.
        """
        return self._inner.to_string_lines()

    def to_ansi_lines(self, *, clip_bottom: bool = False) -> list[str]:
        """Return the styled ANSI text content of the buffer as a list of strings.

        Args:
            clip_bottom: If True, trailing empty lines at the bottom of the buffer
                will be stripped.
        """
        return self._inner.to_ansi_lines(clip_bottom)

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Buffer is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Buffer is immutable")


def render_widget(widget: Any, area: RectangleLike, buffer: Buffer) -> None:
    """Render a widget into the specified buffer area.

    Args:
        widget: The widget to render.
        area: The layout area.
        buffer: The destination buffer.
    """
    from xnano.layout import _resolve_rectangle

    if isinstance(widget, str):
        from xnano.widgets import Paragraph

        widget = Paragraph(widget)

    rect = _resolve_rectangle(area)
    width = getattr(widget, "width", None)
    height = getattr(widget, "height", None)
    if width is not None or height is not None:
        from xnano.layout import Rectangle

        w = min(rect.width, width) if width is not None else rect.width
        h = min(rect.height, height) if height is not None else rect.height
        rect = Rectangle(rect.x, rect.y, w, h)

    _core.render_widget(unwrap(widget), rect._to_core(), buffer._to_core())


def render_stateful_widget(
    widget: Any, area: RectangleLike, state: Any, buffer: Buffer
) -> None:
    """Render a stateful widget using its mutable state into the specified buffer area.

    Args:
        widget: The stateful widget.
        area: The layout area.
        state: The widget state.
        buffer: The destination buffer.
    """
    from xnano.layout import _resolve_rectangle

    rect = _resolve_rectangle(area)
    width = getattr(widget, "width", None)
    height = getattr(widget, "height", None)
    if width is not None or height is not None:
        from xnano.layout import Rectangle

        w = min(rect.width, width) if width is not None else rect.width
        h = min(rect.height, height) if height is not None else rect.height
        rect = Rectangle(rect.x, rect.y, w, h)

    _core.render_stateful_widget(
        unwrap(widget),
        rect._to_core(),
        unwrap(state),
        buffer._to_core(),
    )


__all__ = ("Buffer", "render_stateful_widget", "render_widget")
