"""xnano.beta.components.chart

---

Plot one or more line, scatter, or bar series.
"""

from __future__ import annotations

import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Sequence,
    TypeAlias,
    cast,
)

from xnano.beta.components.component import Component
from xnano.beta.components.schema import ComponentDescriptor
from xnano.beta.core.content import (
    Plot,
    PlotAxis,
    PlotDataset,
)
from xnano.beta.types import (
    CanvasMarkerLike,
    GraphTypeLike,
    LegendPositionLike,
)

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.components.component import ComponentRenderContext


_DEFAULT_PALETTE: tuple[str, ...] = (
    "cyan",
    "magenta",
    "green",
    "yellow",
    "blue",
    "red",
)

SeriesData: TypeAlias = Sequence[Any]
"""Points for one chart series: ``(x, y)`` pairs or bare ``y`` values."""

ResolvedDataset: TypeAlias = tuple[
    str,
    tuple[tuple[float, float], ...],
    Any,
    GraphTypeLike,
    "CanvasMarkerLike | None",
]
"""Resolved ``(label, points, color, kind, marker)`` dataset tuple."""


@dataclasses.dataclass
class Series(ComponentDescriptor):
    """Declares one series of a ``Chart``.

    Attributes:
        label: Legend label; ``None`` derives it from the attribute name.
        color: Series color.
        kind: Per-series plot kind, overriding the chart default.
        marker: Glyph set used to paint the series.
    """

    label: str | None = None
    """Legend label."""
    color: "ColorLike | None" = None
    """Series color."""
    kind: GraphTypeLike | None = None
    """Per-series graph representation."""
    marker: CanvasMarkerLike | None = None
    """Marker used to paint samples."""

    if TYPE_CHECKING:

        def __new__(cls, *args: Any, **kwargs: Any) -> Any: ...

    def resolve_label(self) -> str:
        """Return the legend label, deriving one from ``name`` when unset.

        Returns:
            The legend label for this series.
        """
        return self.label if self.label is not None else self.name


@dataclasses.dataclass
class Chart(Component):
    """Declarative multi-series chart.

    Hand it a mapping of series name → points and it derives the datasets,
    legend, axis bounds, and a cycled color per series. Points may be
    ``(x, y)`` pairs or bare ``y`` values (the x-axis becomes the index).

    Example:
        ``Chart(series={"requests": (3, 5, 4, 8)})``

    Attributes:
        series: Mapping of series name → points.
        kind: Default plot kind for series that do not override it.
        colors: Palette cycled across series.
        x_bounds: Explicit x-axis ``(min, max)``.
        y_bounds: Explicit y-axis ``(min, max)``.
        x_label: Optional x-axis title.
        y_label: Optional y-axis title.
        x_labels: Optional x-axis tick labels.
        y_labels: Optional y-axis tick labels.
        legend: Whether to show the legend.
        legend_position: Legend placement when enabled.
        marker: Default marker glyph set for series.
        hidden_series: Series names omitted from paint.
    """

    series: dict[str, SeriesData] = dataclasses.field(default_factory=dict)
    """Mapping of series name → points."""
    kind: GraphTypeLike = "line"
    """Default plot kind for series that do not override it."""
    colors: Sequence["ColorLike"] | None = None
    """Palette cycled across series; ``None`` uses a built-in palette."""
    x_bounds: tuple[float, float] | None = None
    """x-axis ``(min, max)``; ``None`` auto-fits to the data."""
    y_bounds: tuple[float, float] | None = None
    """y-axis ``(min, max)``; ``None`` auto-fits to the data."""
    x_label: str | None = None
    """Optional x-axis title."""
    y_label: str | None = None
    """Optional y-axis title."""
    x_labels: Sequence[str] | None = None
    """Optional x-axis tick labels."""
    y_labels: Sequence[str] | None = None
    """Optional y-axis tick labels."""
    legend: bool = True
    """Whether to show the legend (labelled from series names)."""
    legend_position: LegendPositionLike = "top_right"
    """Legend placement when ``legend`` is enabled."""
    marker: CanvasMarkerLike | None = None
    """Default marker glyph set for series that do not override it."""
    hidden_series: Sequence[str] = ()
    """Series names omitted from paint and bounds."""
    fit_content: bool = dataclasses.field(default=False, kw_only=True)
    """Whether layout should use the plot's natural size."""

    _declared: ClassVar[dict[str, ComponentDescriptor]] = {}

    @staticmethod
    def _normalize_points(points: Any) -> tuple[tuple[float, float], ...]:
        result: list[tuple[float, float]] = []
        for index, point in enumerate(points):
            if isinstance(point, (tuple, list)) and len(point) == 2:
                result.append((float(point[0]), float(point[1])))
            else:
                result.append((float(index), float(point)))
        return tuple(result)

    def _ordered_names(self) -> list[str]:
        hidden = set(self.hidden_series)
        names = [
            name
            for name in self._declared
            if name in self.series and name not in hidden
        ]
        names.extend(
            name
            for name in self.series
            if name not in names and name not in hidden
        )
        return names

    def _resolve_series(self) -> list[ResolvedDataset]:
        palette = tuple(self.colors) if self.colors else _DEFAULT_PALETTE
        resolved: list[ResolvedDataset] = []
        for index, name in enumerate(self._ordered_names()):
            raw = self._declared.get(name)
            descriptor = cast(Series | None, raw)
            points = self._normalize_points(self.series[name])
            color: Any = (
                descriptor.color
                if descriptor is not None and descriptor.color is not None
                else palette[index % len(palette)]
            )
            kind: GraphTypeLike = (
                descriptor.kind
                if descriptor is not None and descriptor.kind is not None
                else self.kind
            )
            marker: CanvasMarkerLike | None = (
                descriptor.marker
                if descriptor is not None and descriptor.marker is not None
                else self.marker
            )
            label = (
                descriptor.resolve_label() if descriptor is not None else name
            )
            resolved.append((label, points, color, kind, marker))
        return resolved

    @property
    def datasets(self) -> tuple[ResolvedDataset, ...]:
        """Read-only resolved view of plotted datasets."""
        return tuple(self._resolve_series())

    @staticmethod
    def _auto_bounds(
        values: list[float],
        explicit: tuple[float, float] | None,
    ) -> tuple[float, float]:
        if explicit is not None:
            low, high = float(explicit[0]), float(explicit[1])
            if low == high:
                return (low, high + 1.0) if high >= 0 else (low - 1.0, high)
            if low > high:
                return (high, low)
            return (low, high)
        if not values:
            return (0.0, 1.0)
        low, high = min(values), max(values)
        if low == high:
            # Single-value / flat series: expand away from the point so
            # axes remain drawable for negative, zero, and positive data.
            if low == 0.0:
                return (0.0, 1.0)
            if low > 0.0:
                return (low, high + max(1.0, abs(high) * 0.1))
            return (low - max(1.0, abs(low) * 0.1), high)
        # Small pad keeps extremes off the plot edge.
        span = high - low
        pad = span * 0.02
        return (low - pad, high + pad)

    def _compose_plot(self) -> Plot:
        resolved = self._resolve_series()
        all_x: list[float] = []
        all_y: list[float] = []
        datasets: list[PlotDataset] = []
        for label, points, color, kind, marker in resolved:
            for x_value, y_value in points:
                all_x.append(x_value)
                all_y.append(y_value)
            datasets.append(
                PlotDataset(
                    data=points,
                    name=label,
                    color=color,
                    marker=marker,
                    graph_type=kind,
                )
            )
        x_bounds = self._auto_bounds(all_x, self.x_bounds)
        y_bounds = self._auto_bounds(all_y, self.y_bounds)
        x_labels = tuple(self.x_labels) if self.x_labels is not None else None
        y_labels = tuple(self.y_labels) if self.y_labels is not None else None
        return Plot(
            datasets=tuple(datasets),
            x_axis=PlotAxis(
                title=self.x_label,
                bounds=x_bounds,
                labels=x_labels,
            ),
            y_axis=PlotAxis(
                title=self.y_label,
                bounds=y_bounds,
                labels=y_labels,
            ),
            legend=self.legend,
            legend_position=(self.legend_position if self.legend else None),
            z=self.z,
            visible=self.visible,
        )

    def compose(self, ctx: "ComponentRenderContext"):
        """Compose Plot content with a native ChartNode paint fallback.

        Returns:
            Interface-neutral content for this chart.
        """
        return self._compose_plot()


__all__ = (
    "Chart",
    "ResolvedDataset",
    "Series",
    "SeriesData",
)
