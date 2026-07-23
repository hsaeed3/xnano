"""xnano.core.content

---

Interface-neutral content primitives. Components compose ``Content`` trees
instead of terminal or web nodes; each interface controller lowers those
trees into its own node/IR/HTML representation.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any, Literal, Sequence, TypeAlias

from xnano._styles import Style
from xnano._types import (
    Alignment,
    Border,
    CanvasMarkerLike,
    CharacterModifier,
    Direction,
    FrameTitlePosition,
    GraphTypeLike,
    LegendPositionLike,
    PaddingLike,
    ScrollbarOrientationLike,
    Side,
)
from xnano.color import ColorLike

InterfaceKind: TypeAlias = Literal["tui"]
"""The interface kind a ``Native`` escape hatch targets."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AbstractContent(abc.ABC):
    """Base for every interface-neutral content primitive.

    Attributes:
        style: Optional shared style applied when lowering this content.
        z: Stacking order among sibling content.
        visible: Whether this content paints at all.
    """

    style: Style | None = None
    """Optional shared style applied when lowering this content."""
    z: int = 0
    """Stacking order among sibling content."""
    visible: bool = True
    """Whether this content paints at all."""


# ── text ──────────────────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Run(AbstractContent):
    """A single styled text span.

    Attributes:
        text: The characters in this span.
        color: Foreground color for this span.
        background: Background color for this span.
        modifiers: Character modifiers applied to ``text``.
    """

    text: str
    """The characters in this span."""
    color: ColorLike | None = None
    """Foreground color for this span."""
    background: ColorLike | None = None
    """Background color for this span."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Character modifiers applied to ``text``."""

    @classmethod
    def plain(
        cls,
        text: str,
        *,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: Sequence[CharacterModifier] | None = None,
        style: Style | None = None,
        z: int = 0,
        visible: bool = True,
    ) -> Run:
        """Build a run from plain text and optional leaf styling.

        Args:
            text: The characters in this span.
            color: Foreground color for this span.
            background: Background color for this span.
            modifiers: Character modifiers applied to ``text``.
            style: Optional shared style.
            z: Stacking order.
            visible: Whether this run paints.

        Returns:
            A ``Run`` with ``modifiers`` normalized to a tuple.
        """
        return cls(
            text=text,
            color=color,
            background=background,
            modifiers=tuple(modifiers or ()),
            style=style,
            z=z,
            visible=visible,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TextBlock(AbstractContent):
    """Lines of styled runs with wrap and alignment.

    Covers plain paragraphs, multi-line text, and inline run composition.
    When ``lines`` is empty, ``text`` is used as plain content.

    Attributes:
        text: Plain text used when ``lines`` is empty.
        lines: Rows of ``Run`` spans; each inner tuple is one visual line.
        color: Default foreground color for the block.
        background: Default background color for the block.
        modifiers: Default character modifiers for the block.
        align: Horizontal alignment of the block.
        wrap: Whether long lines may wrap.
    """

    text: str = ""
    """Plain text used when ``lines`` is empty."""
    lines: tuple[tuple[Run, ...], ...] = ()
    """Rows of ``Run`` spans; each inner tuple is one visual line."""
    color: ColorLike | None = None
    """Default foreground color for the block."""
    background: ColorLike | None = None
    """Default background color for the block."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Default character modifiers for the block."""
    align: Alignment | None = None
    """Horizontal alignment of the block."""
    wrap: bool = True
    """Whether long lines may wrap."""

    @classmethod
    def from_plain(
        cls,
        text: str,
        *,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: Sequence[CharacterModifier] | None = None,
        align: Alignment | None = None,
        wrap: bool = True,
        style: Style | None = None,
        z: int = 0,
        visible: bool = True,
    ) -> TextBlock:
        """Build a text block from a single plain string.

        Args:
            text: The plain text content.
            color: Optional foreground color.
            background: Optional background color.
            modifiers: Character modifiers for the text.
            align: Horizontal alignment.
            wrap: Whether text should wrap.
            style: Optional shared style.
            z: Stacking order.
            visible: Whether this block paints.

        Returns:
            A ``TextBlock`` holding ``text``.
        """
        return cls(
            text=text,
            color=color,
            background=background,
            modifiers=tuple(modifiers or ()),
            align=align,
            wrap=wrap,
            style=style,
            z=z,
            visible=visible,
        )

    @classmethod
    def from_lines(
        cls,
        lines: Sequence[Sequence[Run] | Run | str],
        *,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: Sequence[CharacterModifier] | None = None,
        align: Alignment | None = None,
        wrap: bool = True,
        style: Style | None = None,
        z: int = 0,
        visible: bool = True,
    ) -> TextBlock:
        """Build a text block from a sequence of line values.

        Each entry may be a plain string, a single ``Run``, or a sequence
        of ``Run`` instances.

        Args:
            lines: Line values to normalize into run rows.
            color: Optional foreground color.
            background: Optional background color.
            modifiers: Character modifiers for the block.
            align: Horizontal alignment.
            wrap: Whether text should wrap.
            style: Optional shared style.
            z: Stacking order.
            visible: Whether this block paints.

        Returns:
            A ``TextBlock`` with normalized ``lines``.
        """
        normalized: list[tuple[Run, ...]] = []
        for line in lines:
            if isinstance(line, str):
                normalized.append((Run(text=line),))
            elif isinstance(line, Run):
                normalized.append((line,))
            else:
                normalized.append(tuple(line))
        return cls(
            lines=tuple(normalized),
            color=color,
            background=background,
            modifiers=tuple(modifiers or ()),
            align=align,
            wrap=wrap,
            style=style,
            z=z,
            visible=visible,
        )


# ── layout / chrome ───────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Stack(AbstractContent):
    """Directional stack of child content.

    Attributes:
        children: Content laid out along ``direction``.
        direction: Axis along which children are placed.
        gap: Space between children in interface units.
    """

    children: tuple[AbstractContent, ...] = ()
    """Content laid out along ``direction``."""
    direction: Direction = "vertical"
    """Axis along which children are placed."""
    gap: int = 0
    """Space between children in interface units."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Panel(AbstractContent):
    """Chrome (border / title / fill) around a single child.

    Leaf chrome fields are convenience mirrors of ``Style`` attributes;
    controllers merge them with ``style`` when lowering.

    Attributes:
        child: Content drawn inside the panel chrome.
        title: Optional title painted on the border.
        title_position: Edge that carries ``title``.
        border: Border style around the panel.
        border_color: Color of the border.
        border_sides: Which sides draw a border.
        background: Fill behind the child area.
        padding: Inset between border and child, if expressed here.
    """

    child: AbstractContent
    """Content drawn inside the panel chrome."""
    title: str | None = None
    """Optional title painted on the border."""
    title_position: FrameTitlePosition | None = None
    """Edge that carries ``title``."""
    border: Border | None = None
    """Border style around the panel."""
    border_color: ColorLike | None = None
    """Color of the border."""
    border_sides: tuple[Side, ...] | None = None
    """Which sides draw a border."""
    background: ColorLike | None = None
    """Fill behind the child area."""
    padding: PaddingLike | None = None
    """Inset between border and child, if expressed here."""


# ── progress / charts ─────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Gauge(AbstractContent):
    """Block progress gauge (ratio 0.0–1.0).

    Attributes:
        progress: Completion ratio, typically clamped when lowered.
        label: Optional text drawn on the gauge.
        color: Filled-portion foreground color.
        background: Widget background color.
    """

    progress: float = 0.0
    """Completion ratio, typically clamped when lowered."""
    label: str | None = None
    """Optional text drawn on the gauge."""
    color: ColorLike = "green"
    """Filled-portion foreground color."""
    background: ColorLike | None = None
    """Widget background color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class LineGauge(AbstractContent):
    """Thin line progress gauge (ratio 0.0–1.0).

    Attributes:
        progress: Completion ratio, typically clamped when lowered.
        label: Optional text drawn on the gauge.
        color: Overall widget foreground style.
        filled_color: Filled-portion foreground color.
        unfilled_color: Unfilled-portion foreground color.
        background: Widget background color.
    """

    progress: float = 0.0
    """Completion ratio, typically clamped when lowered."""
    label: str | None = None
    """Optional text drawn on the gauge."""
    color: ColorLike | None = None
    """Overall widget foreground style."""
    filled_color: ColorLike | None = None
    """Filled-portion foreground color."""
    unfilled_color: ColorLike | None = None
    """Unfilled-portion foreground color."""
    background: ColorLike | None = None
    """Widget background color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Bar:
    """A single bar in a ``BarGroup``.

    Attributes:
        value: Numeric height of the bar.
        label: Label shown with the bar.
        text_value: Explicit override for the value label text.
        color: Per-bar fill color.
        value_color: Per-bar value-label color.
    """

    value: int
    """Numeric height of the bar."""
    label: str = ""
    """Label shown with the bar."""
    text_value: str | None = None
    """Explicit override for the value label text."""
    color: ColorLike | None = None
    """Per-bar fill color."""
    value_color: ColorLike | None = None
    """Per-bar value-label color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BarGroup:
    """A group of bars in a ``Bars`` chart.

    Attributes:
        bars: The bars in this group.
        label: Optional group label.
    """

    bars: tuple[Bar, ...] = ()
    """The bars in this group."""
    label: str | None = None
    """Optional group label."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Bars(AbstractContent):
    """Grouped bar chart content.

    Attributes:
        groups: Bar groups to display.
        bar_width: Width of each bar in interface units.
        bar_gap: Gap between bars in the same group.
        group_gap: Gap between groups.
        max_value: Explicit y-axis ceiling; ``None`` auto-scales.
        direction: Whether bars grow vertically or horizontally.
        color: Default bar fill style.
        value_color: Default value-label color.
        label_color: Bar-label color.
    """

    groups: tuple[BarGroup, ...] = ()
    """Bar groups to display."""
    bar_width: int = 1
    """Width of each bar in interface units."""
    bar_gap: int = 1
    """Gap between bars in the same group."""
    group_gap: int = 0
    """Gap between groups."""
    max_value: int | None = None
    """Explicit y-axis ceiling; ``None`` auto-scales."""
    direction: Direction = "vertical"
    """Whether bars grow vertically or horizontally."""
    color: ColorLike | None = None
    """Default bar fill style."""
    value_color: ColorLike | None = None
    """Default value-label color."""
    label_color: ColorLike | None = None
    """Bar-label color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PlotDataset:
    """A single plotted series in a ``Plot``.

    Attributes:
        data: ``(x, y)`` sample points in logical coordinates.
        name: Legend label for the series.
        color: Series line/point color.
        marker: Glyph set used to paint the series.
        graph_type: How the series is plotted.
    """

    data: tuple[tuple[float, float], ...] = ()
    """``(x, y)`` sample points in logical coordinates."""
    name: str | None = None
    """Legend label for the series."""
    color: ColorLike | None = None
    """Series line/point color."""
    marker: CanvasMarkerLike | None = None
    """Glyph set used to paint the series."""
    graph_type: GraphTypeLike = "line"
    """How the series is plotted."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PlotAxis:
    """An axis specification for a ``Plot``.

    Attributes:
        title: Axis title text.
        bounds: Logical ``(min, max)`` range of the axis.
        labels: Tick labels drawn along the axis.
        color: Axis line and label color.
    """

    title: str | None = None
    """Axis title text."""
    bounds: tuple[float, float] | None = None
    """Logical ``(min, max)`` range of the axis."""
    labels: tuple[str, ...] | None = None
    """Tick labels drawn along the axis."""
    color: ColorLike | None = None
    """Axis line and label color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Plot(AbstractContent):
    """Multi-series plot with axes and an optional legend.

    Attributes:
        datasets: The plotted series.
        x_axis: Optional x-axis specification.
        y_axis: Optional y-axis specification.
        color: Overall plot foreground style.
        legend: Whether to show the legend.
        legend_position: Where the legend is drawn when enabled.
    """

    datasets: tuple[PlotDataset, ...] = ()
    """The plotted series."""
    x_axis: PlotAxis | None = None
    """Optional x-axis specification."""
    y_axis: PlotAxis | None = None
    """Optional y-axis specification."""
    color: ColorLike | None = None
    """Overall plot foreground style."""
    legend: bool = True
    """Whether to show the legend."""
    legend_position: LegendPositionLike | None = "top_right"
    """Where the legend is drawn when enabled."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SparklineBar:
    """A single bar in a ``Sparkline`` with an optional color.

    Attributes:
        value: Numeric height of the bar.
        color: Per-bar foreground color; ``None`` uses the sparkline default.
    """

    value: int
    """Numeric height of the bar."""
    color: ColorLike | None = None
    """Per-bar foreground color; ``None`` uses the sparkline default."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Sparkline(AbstractContent):
    """Sparkline (mini bar chart) data.

    Attributes:
        data: Sequence of non-negative sample values.
        bars: Optional per-bar items with individual colors.
        max_value: Explicit y-axis ceiling; ``None`` auto-scales.
        color: Default bar foreground color.
        background: Widget background color.
        absent_value_color: Color applied to zero or absent samples.
        absent_value_symbol: Glyph drawn for absent samples.
    """

    data: tuple[int, ...] = ()
    """Sequence of non-negative sample values."""
    bars: tuple[SparklineBar, ...] | None = None
    """Optional per-bar items with individual colors."""
    max_value: int | None = None
    """Explicit y-axis ceiling; ``None`` auto-scales."""
    color: ColorLike | None = None
    """Default bar foreground color."""
    background: ColorLike | None = None
    """Widget background color."""
    absent_value_color: ColorLike | None = None
    """Color applied to zero or absent samples."""
    absent_value_symbol: str | None = None
    """Glyph drawn for absent samples."""


# ── table / list ──────────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableCell:
    """A single cell in a ``TableRow``.

    Attributes:
        content: Cell body — plain string or a styled run / text block.
        color: Cell foreground color.
        background: Cell background color.
        modifiers: Text modifiers applied to cell content.
    """

    content: str | Run | TextBlock = ""
    """Cell body — plain string or a styled run / text block."""
    color: ColorLike | None = None
    """Cell foreground color."""
    background: ColorLike | None = None
    """Cell background color."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Text modifiers applied to cell content."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableRow:
    """A row in a ``TableGrid``.

    Attributes:
        cells: The cells in this row.
        color: Row foreground color.
        background: Row background color.
        height: Row height in interface units.
    """

    cells: tuple[TableCell | str, ...] = ()
    """The cells in this row."""
    color: ColorLike | None = None
    """Row foreground color."""
    background: ColorLike | None = None
    """Row background color."""
    height: int = 1
    """Row height in interface units."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableGrid(AbstractContent):
    """Tabular grid with optional header, footer, and selection.

    Attributes:
        rows: Body rows.
        header: Optional header row.
        footer: Optional footer row.
        column_widths: Per-column width constraints. ``int`` is fixed
            width; ``float`` 0.0–1.0 is a fraction of available space;
            ``None`` means equal fill.
        column_spacing: Space between columns in interface units.
        selected_row: Highlighted row index.
        selected_column: Highlighted column index.
        highlight_color: Selection foreground color.
        highlight_background: Selection background color.
        highlight_symbol: Glyph prepended to the selected row.
    """

    rows: tuple[TableRow, ...] = ()
    """Body rows."""
    header: TableRow | None = None
    """Optional header row."""
    footer: TableRow | None = None
    """Optional footer row."""
    column_widths: tuple[int | float, ...] | None = None
    """Per-column width constraints."""
    column_spacing: int = 1
    """Space between columns in interface units."""
    selected_row: int | None = None
    """Highlighted row index."""
    selected_column: int | None = None
    """Highlighted column index."""
    highlight_color: ColorLike | None = None
    """Selection foreground color."""
    highlight_background: ColorLike | None = None
    """Selection background color."""
    highlight_symbol: str | None = None
    """Glyph prepended to the selected row."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Items(AbstractContent):
    """Selectable list of items.

    Attributes:
        items: Entries in the list (plain strings or styled text).
        selected: Selected item index; ``None`` means no selection.
        color: Default foreground color.
        background: Default background color.
        highlight_color: Selected item foreground color.
        highlight_background: Selected item background color.
        highlight_symbol: Symbol prepended to the selected item.
    """

    items: tuple[str | Run | TextBlock, ...] = ()
    """Entries in the list (plain strings or styled text)."""
    selected: int | None = None
    """Selected item index; ``None`` means no selection."""
    color: ColorLike | None = None
    """Default foreground color."""
    background: ColorLike | None = None
    """Default background color."""
    highlight_color: ColorLike = "black"
    """Selected item foreground color."""
    highlight_background: ColorLike = "white"
    """Selected item background color."""
    highlight_symbol: str = "> "
    """Symbol prepended to the selected item."""


# ── canvas / shapes ───────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasLine:
    """A straight line drawn on a ``Canvas``.

    Attributes:
        x1: Start x in logical coordinates.
        y1: Start y in logical coordinates.
        x2: End x in logical coordinates.
        y2: End y in logical coordinates.
        color: Stroke color.
    """

    x1: float
    """Start x in logical coordinates."""
    y1: float
    """Start y in logical coordinates."""
    x2: float
    """End x in logical coordinates."""
    y2: float
    """End y in logical coordinates."""
    color: ColorLike = "white"
    """Stroke color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPoints:
    """A scatter of points drawn on a ``Canvas``.

    Attributes:
        coords: Point coordinates in logical space.
        color: Point color.
    """

    coords: tuple[tuple[float, float], ...] = ()
    """Point coordinates in logical space."""
    color: ColorLike = "white"
    """Point color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasRectangle:
    """An axis-aligned rectangle drawn on a ``Canvas``.

    Attributes:
        x: Origin x in logical coordinates.
        y: Origin y in logical coordinates.
        width: Rectangle width in logical units.
        height: Rectangle height in logical units.
        color: Stroke or fill color.
    """

    x: float
    """Origin x in logical coordinates."""
    y: float
    """Origin y in logical coordinates."""
    width: float
    """Rectangle width in logical units."""
    height: float
    """Rectangle height in logical units."""
    color: ColorLike = "white"
    """Stroke or fill color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasCircle:
    """A circle drawn on a ``Canvas``.

    Attributes:
        x: Center x in logical coordinates.
        y: Center y in logical coordinates.
        radius: Circle radius in logical units.
        color: Stroke color.
    """

    x: float
    """Center x in logical coordinates."""
    y: float
    """Center y in logical coordinates."""
    radius: float
    """Circle radius in logical units."""
    color: ColorLike = "white"
    """Stroke color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPrint:
    """Text printed at a canvas coordinate.

    Attributes:
        x: Print origin x in logical coordinates.
        y: Print origin y in logical coordinates.
        content: Text body as a string, run, or text block.
    """

    x: float
    """Print origin x in logical coordinates."""
    y: float
    """Print origin y in logical coordinates."""
    content: str | Run | TextBlock = ""
    """Text body as a string, run, or text block."""


CanvasShape: TypeAlias = (
    CanvasLine | CanvasPoints | CanvasRectangle | CanvasCircle | CanvasPrint
)
"""Union of shape types accepted by ``Canvas``."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Canvas(AbstractContent):
    """Free-draw canvas of shapes in logical coordinates.

    Attributes:
        shapes: Drawing commands replayed in order when lowered.
        x_bounds: Logical x-axis range ``(min, max)``.
        y_bounds: Logical y-axis range ``(min, max)``.
        background: Canvas background color.
        marker: Glyph set used to paint canvas cells.
    """

    shapes: tuple[CanvasShape, ...] = ()
    """Drawing commands replayed in order when lowered."""
    x_bounds: tuple[float, float] = (0.0, 1.0)
    """Logical x-axis range ``(min, max)``."""
    y_bounds: tuple[float, float] = (0.0, 1.0)
    """Logical y-axis range ``(min, max)``."""
    background: ColorLike | None = None
    """Canvas background color."""
    marker: CanvasMarkerLike | None = None
    """Glyph set used to paint canvas cells."""


# ── chrome widgets / clear ────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Scrollbar(AbstractContent):
    """Scrollbar state and styling.

    Attributes:
        content_length: Total scrollable content size.
        position: Current scroll offset within ``content_length``.
        viewport_length: Visible window size; drives thumb proportion.
        orientation: Which edge the scrollbar is drawn on.
        color: Overall track and thumb style.
        thumb_color: Thumb foreground color.
        track_color: Track foreground color.
        begin_symbol: Arrow symbol at the start; ``None`` omits it.
        end_symbol: Arrow symbol at the end; ``None`` omits it.
    """

    content_length: int = 0
    """Total scrollable content size."""
    position: int = 0
    """Current scroll offset within ``content_length``."""
    viewport_length: int | None = None
    """Visible window size; drives thumb proportion."""
    orientation: ScrollbarOrientationLike = "vertical_right"
    """Which edge the scrollbar is drawn on."""
    color: ColorLike | None = None
    """Overall track and thumb style."""
    thumb_color: ColorLike | None = None
    """Thumb foreground color."""
    track_color: ColorLike | None = None
    """Track foreground color."""
    begin_symbol: str | None = None
    """Arrow symbol at the start; ``None`` omits it."""
    end_symbol: str | None = None
    """Arrow symbol at the end; ``None`` omits it."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Clear(AbstractContent):
    """Clear the target area before painting siblings or later content."""


# ── cell canvas (A9) ──────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True, slots=True)
class CellSpan:
    """A run-length styled span within a ``CellCanvas`` row.

    Attributes:
        text: Characters covering one or more consecutive cells.
        color: Foreground color for this span.
        background: Background color for this span.
        modifiers: Character modifiers for this span.
    """

    text: str
    """Characters covering one or more consecutive cells."""
    color: ColorLike | None = None
    """Foreground color for this span."""
    background: ColorLike | None = None
    """Background color for this span."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Character modifiers for this span."""


@dataclasses.dataclass(frozen=True, slots=True)
class CellCanvas(AbstractContent):
    """Rectangular grid of styled cell runs (run-length spans per row).

    Controllers lower this to span-run IR (tui) or positioned
    ``ch``/``lh`` spans (webui). ``rows`` must contain ``height`` rows;
    each row's spans together should cover ``width`` cells when painted.

    Attributes:
        width: BaseGrid width in cells.
        height: BaseGrid height in cells.
        rows: ``height`` rows of run-length ``CellSpan`` sequences.
    """

    width: int
    """BaseGrid width in cells."""
    height: int
    """BaseGrid height in cells."""
    rows: tuple[tuple[CellSpan, ...], ...] = ()
    """``height`` rows of run-length ``CellSpan`` sequences."""

    @classmethod
    def from_rows(
        cls,
        rows: Sequence[Sequence[CellSpan | str]],
        *,
        width: int | None = None,
        style: Style | None = None,
        z: int = 0,
        visible: bool = True,
    ) -> CellCanvas:
        """Build a cell canvas from row sequences.

        Args:
            rows: Each entry is a sequence of ``CellSpan`` or plain
                strings (converted to unstyled spans).
            width: Explicit width; when ``None``, the maximum row text
                length is used.
            style: Optional shared style.
            z: Stacking order.
            visible: Whether this canvas paints.

        Returns:
            A ``CellCanvas`` with normalized span rows.
        """
        normalized: list[tuple[CellSpan, ...]] = []
        measured_width = 0
        for row in rows:
            spans: list[CellSpan] = []
            row_width = 0
            for item in row:
                if isinstance(item, str):
                    span = CellSpan(item)
                else:
                    span = item
                spans.append(span)
                row_width += len(span.text)
            measured_width = max(measured_width, row_width)
            normalized.append(tuple(spans))
        return cls(
            width if width is not None else measured_width,
            len(normalized),
            rows=tuple(normalized),
            style=style,
            z=z,
            visible=visible,
        )


# ── escape hatch ──────────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Native(AbstractContent):
    """Interface-specific escape hatch payload.

    Controllers only consume a ``Native`` whose ``interface_kind`` matches
    their own kind; other kinds ignore it.

    Attributes:
        interface_kind: Target interface (``"tui"`` or ``"webui"``).
        payload: Opaque value understood by that interface's controller.
    """

    interface_kind: InterfaceKind | str
    """Target interface (``"tui"`` or ``"webui"``)."""
    payload: Any = None
    """Opaque value understood by that interface's controller."""


Content: TypeAlias = (
    Run
    | TextBlock
    | Stack
    | Panel
    | Gauge
    | LineGauge
    | Bars
    | Plot
    | Sparkline
    | TableGrid
    | Items
    | Canvas
    | Scrollbar
    | Clear
    | CellCanvas
    | Native
)
"""Closed union of every concrete content primitive."""


__all__ = (
    "AbstractContent",
    "Bar",
    "BarGroup",
    "Bars",
    "Canvas",
    "CanvasCircle",
    "CanvasLine",
    "CanvasPoints",
    "CanvasPrint",
    "CanvasRectangle",
    "CanvasShape",
    "CellCanvas",
    "CellSpan",
    "Clear",
    "Content",
    "Gauge",
    "InterfaceKind",
    "Items",
    "LineGauge",
    "Native",
    "Panel",
    "Plot",
    "PlotAxis",
    "PlotDataset",
    "Run",
    "Scrollbar",
    "Sparkline",
    "SparklineBar",
    "Stack",
    "TableCell",
    "TableGrid",
    "TableRow",
    "TextBlock",
)
