"""xnano.components.chart

---

``Chart`` component for multi-series line and scatter plots.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, ClassVar, Sequence, TypeAlias, cast

from typing_extensions import deprecated

from xnano._types import GraphTypeLike, LegendPositionLike
from xnano.components.abstract import AbstractComponent
from xnano.components.schema import (
    ComponentDescriptor,
    DeclarativeComponentMeta,
    Series,
)

if TYPE_CHECKING:
    from xnano.color import ColorLike
    from xnano.components.abstract import ComponentRenderContext
    from xnano.terminal.nodes import AbstractTerminalNode


_DEFAULT_PALETTE: tuple[str, ...] = (
    "cyan",
    "magenta",
    "green",
    "yellow",
    "blue",
    "red",
)

# A series' points: either ``(x, y)`` pairs or bare ``y`` values (x = index).
# ``Any`` sequence elements are accepted so callers can pass bare lists of
# numbers or pairs without fighting sequence invariance.
SeriesData: TypeAlias = Sequence[Any]
"""Points for one chart series: ``(x, y)`` pairs or bare ``y`` values."""


@deprecated(
    "'xnano.components.Chart' is deprecated and will be removed in v1.2; use "
    "'xnano.beta.components.Chart' instead.",
    category=DeprecationWarning,
    stacklevel=2,
)
@dataclasses.dataclass
class Chart(AbstractComponent, metaclass=DeclarativeComponentMeta):
    """Declarative multi-series chart.

    Hand it a mapping of series name → points and it derives the datasets,
    legend, axis bounds, and a cycled color per series. Points may be ``(x, y)``
    pairs or bare ``y`` values (the x-axis becomes the index). One component
    covers line, scatter, and bar plots.

        # data-driven — one line per key, legend + bounds inferred
        Chart(series={"cpu": [30, 42, 38, 55], "mem": [60, 61, 63, 62]})

        # explicit points and a bar plot
        Chart(series={"load": [(0, 3), (1, 5), (2, 4)]}, kind="bar")

        # declarative subclass — per-series styling as a schema
        class Latency(Chart):
            p50 = Series(color="green")
            p99 = Series(color="red")

        Latency(series={"p50": [...], "p99": [...]})
    """

    series: dict[str, SeriesData] = dataclasses.field(default_factory=dict)
    """Mapping of series name → points (``(x, y)`` pairs or bare ``y`` values)."""
    kind: GraphTypeLike = "line"
    """Default plot kind for series that do not override it."""
    colors: Sequence[ColorLike] | None = None
    """Palette cycled across series; ``None`` uses a built-in palette."""
    x_bounds: tuple[float, float] | None = None
    """x-axis ``(min, max)``; ``None`` auto-fits to the data."""
    y_bounds: tuple[float, float] | None = None
    """y-axis ``(min, max)``; ``None`` auto-fits to the data."""
    x_label: str | None = None
    """Optional x-axis title."""
    y_label: str | None = None
    """Optional y-axis title."""
    legend: bool = True
    """Whether to show the legend (labelled from series names)."""
    legend_position: LegendPositionLike = "top_right"
    """Legend placement when ``legend`` is enabled."""
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    _declared: ClassVar[dict[str, ComponentDescriptor]] = {}

    # ── series resolution ────────────────────────────────────────────────

    @staticmethod
    def _normalize_points(points: Any) -> list[tuple[float, float]]:
        result: list[tuple[float, float]] = []
        for index, point in enumerate(points):
            if isinstance(point, (tuple, list)) and len(point) == 2:
                result.append((float(point[0]), float(point[1])))
            else:
                result.append((float(index), float(point)))
        return result

    def _ordered_names(self) -> list[str]:
        # Declared series first (schema order), then any extra data keys.
        names = [name for name in self._declared if name in self.series]
        names.extend(name for name in self.series if name not in names)
        return names

    def _resolve_series(
        self,
    ) -> list[tuple[str, list[tuple[float, float]], Any, GraphTypeLike]]:
        palette = tuple(self.colors) if self.colors else _DEFAULT_PALETTE
        resolved: list[
            tuple[str, list[tuple[float, float]], Any, GraphTypeLike]
        ] = []
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
            label = (
                descriptor.resolve_label() if descriptor is not None else name
            )
            resolved.append((label, points, color, kind))
        return resolved

    @staticmethod
    def _auto_bounds(
        values: list[float], explicit: tuple[float, float] | None
    ) -> tuple[float, float]:
        if explicit is not None:
            return explicit
        if not values:
            return (0.0, 1.0)
        low, high = min(values), max(values)
        if low == high:
            return (low, high + 1.0)
        return (low, high)

    # ── rendering ────────────────────────────────────────────────────────

    def compose(self, ctx):
        """Compose
        [`Content`](../core/content.md#xnano.core.content.Content){data-preview}
        via Native tui payload of the existing node tree.
        """
        from xnano.core.content import Native

        return Native(
            interface_kind="tui",
            payload=self.get_terminal_node(ctx),
            z=self.z,
            visible=self.visible,
        )

    def get_terminal_node(
        self, ctx: ComponentRenderContext
    ) -> AbstractTerminalNode:
        from xnano.terminal.nodes import (
            ChartAxis,
            ChartDataset,
            ChartNode,
        )

        resolved = self._resolve_series()

        all_x: list[float] = []
        all_y: list[float] = []
        datasets: list[ChartDataset] = []
        for label, points, color, kind in resolved:
            for x, y in points:
                all_x.append(x)
                all_y.append(y)
            datasets.append(
                ChartDataset(
                    data=points,
                    name=label,
                    color=color,
                    graph_type=kind,
                )
            )

        x_bounds = self._auto_bounds(all_x, self.x_bounds)
        y_bounds = self._auto_bounds(all_y, self.y_bounds)

        return ChartNode(
            datasets=datasets,
            x_axis=ChartAxis(title=self.x_label, bounds=x_bounds),
            y_axis=ChartAxis(title=self.y_label, bounds=y_bounds),
            legend_position=self.legend_position if self.legend else None,
            z=self.z,
            visible=self.visible,
        )


__all__ = ("Chart", "SeriesData")
