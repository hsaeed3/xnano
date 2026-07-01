"""xnano.scroll"""

from __future__ import annotations

import dataclasses
from typing import Literal, TypeAlias

from xnano import _core
from xnano.style import Style


ScrollbarOrientationName: TypeAlias = Literal[
    "vertical_right",
    "vertical_left",
    "horizontal_bottom",
    "horizontal_top",
]
"""The layout edge placement and flow direction of a scrollbar."""


ScrollDirectionName: TypeAlias = Literal["forward", "backward"]
"""The scrolling direction."""


_SCROLLBAR_ORIENTATION: dict[
    ScrollbarOrientationName, _core.ScrollbarOrientation
] = {
    "vertical_right": _core.ScrollbarOrientation.VerticalRight,
    "vertical_left": _core.ScrollbarOrientation.VerticalLeft,
    "horizontal_bottom": _core.ScrollbarOrientation.HorizontalBottom,
    "horizontal_top": _core.ScrollbarOrientation.HorizontalTop,
}


_SCROLL_DIRECTION: dict[ScrollDirectionName, _core.ScrollDirection] = {
    "forward": _core.ScrollDirection.Forward,
    "backward": _core.ScrollDirection.Backward,
}


def _core_scrollbar_orientation(
    value: ScrollbarOrientationName,
) -> _core.ScrollbarOrientation:
    return _SCROLLBAR_ORIENTATION[value]


def _core_scroll_direction(
    value: ScrollDirectionName,
) -> _core.ScrollDirection:
    return _SCROLL_DIRECTION[value]


class Scrollbar:
    """A scrollbar widget for indicating scroll progress and position in viewports.

    Example::

        scrollbar = Scrollbar(
            "vertical_right",
            style=Style(foreground="gray"),
            thumb_style=Style(foreground="yellow")
        )
    """

    __slots__ = ("_inner",)
    _inner: _core.Scrollbar

    def __init__(
        self,
        orientation: ScrollbarOrientationName,
        *,
        style: Style | None = None,
        thumb_style: Style | None = None,
        track_style: Style | None = None,
        begin_style: Style | None = None,
        end_style: Style | None = None,
        begin_symbol: str | None = None,
        end_symbol: str | None = None,
    ) -> None:
        """Create a Scrollbar.

        Args:
            orientation: Placement edge (e.g. ``"vertical_right"``, ``"horizontal_bottom"``).
            style: Overall default style.
            thumb_style: Style applied to the scroll slider thumb.
            track_style: Style applied to the scrollbar background track.
            begin_style: Style applied to the begin arrow symbol.
            end_style: Style applied to the end arrow symbol.
            begin_symbol: Arrow symbol character used at the beginning of the track.
            end_symbol: Arrow symbol character used at the end of the track.
        """
        inner = _core.Scrollbar.new(_core_scrollbar_orientation(orientation))

        if style is not None:
            inner = inner.style(style._to_core())
        if thumb_style is not None:
            inner = inner.thumb_style(thumb_style._to_core())
        if track_style is not None:
            inner = inner.track_style(track_style._to_core())
        if begin_style is not None:
            inner = inner.begin_style(begin_style._to_core())
        if end_style is not None:
            inner = inner.end_style(end_style._to_core())
        if begin_symbol is not None:
            inner = inner.begin_symbol(begin_symbol)
        if end_symbol is not None:
            inner = inner.end_symbol(end_symbol)

        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.Scrollbar) -> Scrollbar:
        """Construct from a native ``_core.Scrollbar``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Scrollbar:
        """Return the native scrollbar."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Scrollbar is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Scrollbar is immutable")


class ScrollbarState:
    """Mutable scrolling position tracking state for a ``Scrollbar`` widget.

    Example::

        state = ScrollbarState(content_length=100)
        state.set_position(10)
    """

    __slots__ = ("_inner",)
    _inner: _core.ScrollbarState

    def __init__(self, content_length: int) -> None:
        """Create a new mutable ScrollbarState.

        Args:
            content_length: The total scrollable content length.
        """
        object.__setattr__(
            self, "_inner", _core.ScrollbarState(content_length)
        )

    @classmethod
    def _from_core(cls, inner: _core.ScrollbarState) -> ScrollbarState:
        """Construct from a native ``_core.ScrollbarState``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.ScrollbarState:
        """Return the native scrollbar state."""
        return self._inner

    def set_position(self, value: int) -> None:
        """Set the current viewport scroll position."""
        self._inner.set_position(value)

    def set_content_length(self, value: int) -> None:
        """Set the total scrollable content length."""
        self._inner.set_content_length(value)

    def viewport_content_length(self, value: int) -> ScrollbarState:
        """Return a new ScrollbarState with the viewport visible height/width size set."""
        return ScrollbarState._from_core(
            self._inner.viewport_content_length(value)
        )

    def prev(self) -> None:
        """Scroll backwards by one item."""
        self._inner.prev()

    def next(self) -> None:
        """Scroll forwards by one item."""
        self._inner.next()

    def first(self) -> None:
        """Scroll to the absolute beginning position."""
        self._inner.first()

    def last(self) -> None:
        """Scroll to the absolute end position."""
        self._inner.last()

    def scroll(self, direction: ScrollDirectionName) -> None:
        """Scroll in the specified direction."""
        self._inner.scroll(_core_scroll_direction(direction))

    def __repr__(self) -> str:
        return repr(self._inner)


__all__ = (
    "ScrollDirectionName",
    "Scrollbar",
    "ScrollbarOrientationName",
    "ScrollbarState",
)
