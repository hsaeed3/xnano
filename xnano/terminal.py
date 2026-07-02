"""xnano.terminal"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar, cast

from xnano import _core
from xnano._convert import unwrap
from xnano.layout import (
    Position,
    Rectangle,
    RectangleLike,
    Size,
    _resolve_rectangle,
)


T = TypeVar("T")


class Frame:
    """A single-frame render context provided to the draw callback."""

    __slots__ = ("_inner",)
    _inner: _core.Frame

    def __init__(self) -> None:
        raise TypeError(
            "Frame instances are created internally during draw cycles."
        )

    @classmethod
    def _from_core(cls, frame: _core.Frame) -> Frame:
        """Construct from a native frame."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", frame)
        return obj

    def _to_core(self) -> _core.Frame:
        """Return the native frame."""
        return self._inner

    def area(self) -> Rectangle:
        """Return the total renderable area of this frame."""
        return Rectangle._from_core(self._inner.area())

    def render_widget(self, widget: Any, area: RectangleLike) -> None:
        """Render a widget into the given area."""
        resolved_area = _resolve_rectangle(area)
        if isinstance(widget, str):
            from xnano.widgets import Paragraph

            widget = Paragraph(widget)
        self._inner.render_widget(unwrap(widget), resolved_area._to_core())

    def render_stateful_widget(
        self, widget: Any, area: RectangleLike, state: Any
    ) -> None:
        """Render a stateful widget with its mutable state."""
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
        """Render a widget or sequence of widgets into this frame.

        Args:
            renderable: A single widget to render, or a sequence of widgets
                or layout tuples ``(widget, area)`` or ``(widget, area, state)``.
            area: Default area to render into if rendering a single widget.
                If not specified, defaults to the entire frame area.
        """
        if isinstance(renderable, Sequence) and not isinstance(
            renderable, (str, bytes)
        ):
            for item in renderable:
                if isinstance(item, tuple):
                    if len(item) == 2:
                        widget, item_area = item
                        self.render_widget(widget, item_area)
                    elif len(item) == 3:
                        widget, item_area, state = item
                        self.render_stateful_widget(widget, item_area, state)
                    else:
                        raise ValueError(
                            f"Invalid draw tuple: {item!r}. "
                            f"Expected 2 or 3 elements."
                        )
                else:
                    self.render_widget(
                        item,
                        area if area is not None else self.area(),
                    )
        else:
            self.render_widget(
                renderable,
                area if area is not None else self.area(),
            )

    def set_cursor_position(self, position: Position) -> None:
        """Set the terminal cursor position for this frame."""
        self._inner.set_cursor_position(position._to_core())

    def hide_cursor(self) -> None:
        """Hide the terminal cursor for this frame."""
        self._inner.hide_cursor()

    def process_effects(
        self,
        manager: Any,
        duration_ms: int,
        area: Rectangle,
    ) -> None:
        """Process visual effects through the effect manager."""
        self._inner.process_effects(
            unwrap(manager), duration_ms, area._to_core()
        )

    def count(self) -> int:
        """Return the frame counter (number of draws so far)."""
        return self._inner.count()


class Terminal:
    """The main terminal handle for drawing to the screen."""

    __slots__ = ("_inner",)
    _inner: _core.Terminal

    def __init__(self) -> None:
        """Initialize the terminal in raw mode with alternate screen.

        Raises:
            RuntimeError: If terminal initialization fails.
        """
        object.__setattr__(self, "_inner", _core.Terminal.init())

    def _to_core(self) -> _core.Terminal:
        """Return the native terminal."""
        return self._inner

    def draw(
        self,
        renderable: Callable[[Frame], Any]
        | Sequence[
            Any | tuple[Any, RectangleLike] | tuple[Any, RectangleLike, Any]
        ]
        | Any,
    ) -> None:
        """Execute a single draw cycle.

        Args:
            renderable: Either a callback function that accepts a ``Frame``, or a
                sequence of widgets or layout tuples ``(widget, area)`` or
                ``(widget, area, state)`` to render, or a single widget to render.
        """
        if callable(renderable):
            cb = cast(Callable[[Frame], Any], renderable)

            def _bridge(native_frame: _core.Frame) -> Any:
                frame = Frame._from_core(native_frame)
                res = cb(frame)
                if isinstance(res, Sequence) and not isinstance(
                    res, (str, bytes)
                ):
                    for item in res:
                        if isinstance(item, tuple):
                            if len(item) == 2:
                                widget, area = item
                                frame.render_widget(
                                    widget, _resolve_rectangle(area)
                                )
                            elif len(item) == 3:
                                widget, area, state = item
                                frame.render_stateful_widget(
                                    widget, _resolve_rectangle(area), state
                                )
                            else:
                                raise ValueError(
                                    f"Invalid draw tuple: {item!r}. "
                                    f"Expected 2 or 3 elements."
                                )
                        else:
                            frame.render_widget(item, frame.area())
                elif res is not None:
                    frame.render_widget(res, frame.area())
                return res

            self._inner.draw(_bridge)
        elif isinstance(renderable, Sequence) and not isinstance(
            renderable, (str, bytes)
        ):

            def _draw_widgets(frame: Frame) -> None:
                for item in renderable:
                    if isinstance(item, tuple):
                        if len(item) == 2:
                            widget, area = item
                            frame.render_widget(
                                widget, _resolve_rectangle(area)
                            )
                        elif len(item) == 3:
                            widget, area, state = item
                            frame.render_stateful_widget(
                                widget, _resolve_rectangle(area), state
                            )
                        else:
                            raise ValueError(
                                f"Invalid draw tuple: {item!r}. "
                                f"Expected 2 or 3 elements."
                            )
                    else:
                        frame.render_widget(item, frame.area())

            def _bridge_seq(native_frame: _core.Frame) -> Any:
                return _draw_widgets(Frame._from_core(native_frame))

            self._inner.draw(_bridge_seq)
        else:

            def _bridge_single(native_frame: _core.Frame) -> Any:
                frame = Frame._from_core(native_frame)
                return frame.render_widget(renderable, frame.area())

            self._inner.draw(_bridge_single)

    def clear(self) -> None:
        """Clear the terminal screen."""
        self._inner.clear()

    def size(self) -> Size:
        """Return the current terminal size."""
        inner = self._inner.size()
        return Size(width=inner.width, height=inner.height)

    def __enter__(self) -> Terminal:
        self._inner.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self._inner.__exit__(exc_type, exc_value, traceback)

    def __repr__(self) -> str:
        return "Terminal()"


def restore_terminal() -> None:
    """Restore the terminal to its pre-xnano state."""
    _core.restore_terminal()


__all__ = (
    "Frame",
    "Terminal",
    "restore_terminal",
)
