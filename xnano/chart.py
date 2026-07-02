"""xnano.chart"""

from __future__ import annotations

import dataclasses
from typing import Any, Sequence

from xnano import _core
from xnano._convert import Content, as_line, as_text
from xnano.layout import Direction, _core_direction
from xnano.style import Style
from xnano.widgets import Block


class Sparkline:
    """A miniature chart widget that displays a single line of data trends.

    Example::

        sparkline = Sparkline([1, 2, 4, 3, 5, 2, 7])
    """

    __slots__ = ("_inner",)
    _inner: _core.Sparkline

    def __init__(
        self,
        data: Sequence[int],
        *,
        block: Block | None = None,
        style: Style | None = None,
        max_value: int | None = None,
        absent_value_style: Style | None = None,
        absent_value_symbol: str | None = None,
    ) -> None:
        """Create a new Sparkline chart.

        Args:
            data: List of data points to plot.
            block: Optional decorative ``Block`` container.
            style: Default style for the sparkline blocks.
            max_value: Maximum data value boundary scale.
            absent_value_style: Style for absent/zero data cells.
            absent_value_symbol: Character printed for absent/zero data cells.
        """
        inner = _core.Sparkline.new(data)

        if block is not None:
            inner = inner.block(block._to_core())
        if style is not None:
            inner = inner.style(style._to_core())
        if max_value is not None:
            inner = inner.max(max_value)
        if absent_value_style is not None:
            inner = inner.absent_value_style(absent_value_style._to_core())
        if absent_value_symbol is not None:
            inner = inner.absent_value_symbol(absent_value_symbol)

        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.Sparkline) -> Sparkline:
        """Construct from a native ``core.Sparkline``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Sparkline:
        """Return the native sparkline."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Sparkline is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Sparkline is immutable")


class LineGauge:
    """A compact horizontal bar gauge showing completion ratio.

    Example::

        progress = LineGauge(ratio=0.75, label="Extracting...")
    """

    __slots__ = ("_inner",)
    _inner: _core.LineGauge

    def __init__(
        self,
        *,
        ratio: float = 0.0,
        label: Content | None = None,
        block: Block | None = None,
        style: Style | None = None,
        filled_style: Style | None = None,
        unfilled_style: Style | None = None,
    ) -> None:
        """Create a new LineGauge.

        Args:
            ratio: Progress completion ratio (0.0 to 1.0).
            label: Text label printed inside the gauge.
            block: Optional background/border Block.
            style: Overall default style.
            filled_style: Style applied to progress filled portion.
            unfilled_style: Style applied to progress unfilled portion.
        """
        inner = _core.LineGauge.new()

        inner = inner.ratio(ratio)
        if label is not None:
            inner = inner.label(as_line(label))
        if block is not None:
            inner = inner.block(block._to_core())
        if style is not None:
            inner = inner.style(style._to_core())
        if filled_style is not None:
            inner = inner.filled_style(filled_style._to_core())
        if unfilled_style is not None:
            inner = inner.unfilled_style(unfilled_style._to_core())

        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.LineGauge) -> LineGauge:
        """Construct from a native ``core.LineGauge``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.LineGauge:
        """Return the native line gauge."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("LineGauge is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("LineGauge is immutable")


class Bar:
    """A single bar within a BarChart widget."""

    __slots__ = ("_inner",)
    _inner: _core.Bar

    def __init__(
        self,
        value: int = 0,
        label: str = "",
        *,
        style: Style | None = None,
        value_style: Style | None = None,
        text_value: str | None = None,
    ) -> None:
        """Create a new Chart Bar.

        Args:
            value: Height value of the bar.
            label: Text label printed under the bar.
            style: Style for the bar column.
            value_style: Style for the printed value text.
            text_value: Alternative text representation of the value.
        """
        inner = _core.Bar.new(value, label)

        if style is not None:
            inner = inner.style(style._to_core())
        if value_style is not None:
            inner = inner.value_style(value_style._to_core())
        if text_value is not None:
            inner = inner.text_value(text_value)

        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.Bar) -> Bar:
        """Construct from a native ``core.Bar``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Bar:
        """Return the native bar."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Bar is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Bar is immutable")


class BarGroup:
    """A logical grouping of Bars inside a BarChart."""

    __slots__ = ("_inner",)
    _inner: _core.BarGroup

    def __init__(self, bars: Sequence[Bar]) -> None:
        """Create a new BarGroup.

        Args:
            bars: The list of bars to group together.
        """
        inner = _core.BarGroup.new([bar._to_core() for bar in bars])
        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.BarGroup) -> BarGroup:
        """Construct from a native ``core.BarGroup``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.BarGroup:
        """Return the native bar group."""
        return self._inner

    def __repr__(self) -> str:
        return "BarGroup()"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("BarGroup is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("BarGroup is immutable")


class BarChart:
    """A bar chart widget that displays grouped data vertically or horizontally."""

    __slots__ = ("_inner", "width", "height")
    _inner: _core.BarChart

    def __init__(
        self,
        groups: Sequence[BarGroup],
        *,
        block: Block | None = None,
        style: Style | None = None,
        bar_width: int | None = None,
        max_value: int | None = None,
        bar_gap: int | None = None,
        group_gap: int | None = None,
        bar_style: Style | None = None,
        value_style: Style | None = None,
        label_style: Style | None = None,
        direction: Direction | None = None,
        width: int | None = None,
        height: int | None = None,
        class_name: str | None = None,
    ) -> None:
        """Create a BarChart.

        Args:
            groups: The grouped bars to plot.
            block: Optional background/border Block around the chart.
            style: Overall default base style.
            bar_width: Width of each individual bar column.
            max_value: Maximum value boundary scale.
            bar_gap: Space gap between individual bars.
            group_gap: Space gap between different groups of bars.
            bar_style: Visual style applied to the bar columns.
            value_style: Visual style applied to the printed values.
            label_style: Visual style applied to the labels under the bars.
            direction: Direction of bar stack flow (``"vertical"`` or ``"horizontal"``).
            width: Optional fixed width constraint.
            height: Optional fixed height constraint.
            class_name: Optional space-separated Tailwind utility classes.
        """
        from xnano.widgets import _merge_tailwind

        style, width, height, block = _merge_tailwind(
            class_name, style, width, height, block
        )
        inner = _core.BarChart.new([g._to_core() for g in groups])

        if block is not None:
            inner = inner.block(block._to_core())
        if style is not None:
            inner = inner.style(style._to_core())
        if bar_width is not None:
            inner = inner.bar_width(bar_width)
        if max_value is not None:
            inner = inner.max(max_value)
        if bar_gap is not None:
            inner = inner.bar_gap(bar_gap)
        if group_gap is not None:
            inner = inner.group_gap(group_gap)
        if bar_style is not None:
            inner = inner.bar_style(bar_style._to_core())
        if value_style is not None:
            inner = inner.value_style(value_style._to_core())
        if label_style is not None:
            inner = inner.label_style(label_style._to_core())
        if direction is not None:
            inner = inner.direction(_core_direction(direction))

        if width is None and block is not None:
            width = getattr(block, "width", None)
        if height is None and block is not None:
            height = getattr(block, "height", None)

        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)

    @classmethod
    def _from_core(cls, inner: _core.BarChart) -> BarChart:
        """Construct from a native ``core.BarChart``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.BarChart:
        """Return the native bar chart."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("BarChart is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("BarChart is immutable")


__all__ = ("Bar", "BarChart", "BarGroup", "LineGauge", "Sparkline")
