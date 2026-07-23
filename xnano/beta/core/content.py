"""xnano.beta.core.content

---

Compose interface-neutral text, layout, chart, table, canvas, and native data.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Sequence, TypeAlias

from xnano.beta.colors import ColorLike
from xnano.beta.tailwind import Style
from xnano.beta.types import (
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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ContentBase:
    """Shared visibility and stacking state for composed content.

    Attributes:
        style: Optional shared style.
        z: Sibling-local paint order.
        visible: Whether this content paints.
    """

    style: Style | None = None
    """Optional shared style."""
    z: int = 0
    """Sibling-local paint order."""
    visible: bool = True
    """Whether this content paints."""


AbstractContent = ContentBase


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Run(ContentBase):
    """One styled text run.

    Example:
        ``Run(text="Ready", color="green", modifiers=("bold",))``

    Attributes:
        text: Text displayed by the run.
        color: Foreground color.
        background: Background color.
        modifiers: Character modifiers.
    """

    text: str
    """Text displayed by the run."""
    color: ColorLike | None = None
    """Foreground color."""
    background: ColorLike | None = None
    """Background color."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Character modifiers."""

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
    ) -> "Run":
        """Create a plain styled run.

        Args:
            text: Text displayed by the run.
            color: Foreground color.
            background: Background color.
            modifiers: Character modifiers.
            style: Optional shared style.
            z: Sibling-local paint order.
            visible: Whether the run paints.

        Returns:
            A run containing ``text``.
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
class TextBlock(ContentBase):
    """Wrapped plain text or lines of styled runs.

    Example:
        ``TextBlock(text="Hello", align="center")``

    Attributes:
        text: Plain text content.
        lines: Styled text lines.
        color: Default foreground color.
        background: Default background color.
        modifiers: Default character modifiers.
        align: Horizontal alignment.
        wrap: Whether long lines wrap.
    """

    text: str = ""
    """Plain text content."""
    lines: tuple[tuple[Run, ...], ...] = ()
    """Styled text lines."""
    color: ColorLike | None = None
    """Default foreground color."""
    background: ColorLike | None = None
    """Default background color."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Default character modifiers."""
    align: Alignment | None = None
    """Horizontal alignment."""
    wrap: bool = True
    """Whether long lines wrap."""

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
    ) -> "TextBlock":
        """Create a block from plain text and explicit style values."""
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
    ) -> "TextBlock":
        """Create a block from styled line sequences."""
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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Stack(ContentBase):
    """Lay out child content in one direction.

    Example:
        ``Stack(children=(TextBlock(text="One"), TextBlock(text="Two")))``

    Attributes:
        children: Child content.
        direction: Layout direction.
        gap: Cells between children.
    """

    children: tuple[ContentBase, ...] = ()
    """Child content."""
    direction: Direction = "vertical"
    """Layout direction."""
    gap: int = 0
    """Cells between children."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Panel(ContentBase):
    """Decorate child content with a frame and padding.

    Example:
        ``Panel(child=TextBlock(text="Status"), title="Service")``

    Attributes:
        child: Content inside the panel.
        title: Optional frame title.
        title_position: Frame title alignment.
        border: Border style.
        border_color: Border foreground color.
        border_sides: Visible border sides.
        background: Panel background color.
        padding: Space between border and child.
    """

    child: ContentBase
    """Content inside the panel."""
    title: str | None = None
    """Optional frame title."""
    title_position: FrameTitlePosition | None = None
    """Frame title alignment."""
    border: Border | None = None
    """Border style."""
    border_color: ColorLike | None = None
    """Border foreground color."""
    border_sides: tuple[Side, ...] | None = None
    """Visible border sides."""
    background: ColorLike | None = None
    """Panel background color."""
    padding: PaddingLike | None = None
    """Space between border and child."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Gauge(ContentBase):
    """Render a filled progress gauge.

    Example:
        ``Gauge(progress=0.75, label="75%")``

    Attributes:
        progress: Completion ratio from zero to one.
        label: Text displayed inside the gauge.
        color: Filled-region color.
        background: Gauge background color.
    """

    progress: float = 0.0
    """Completion ratio from zero to one."""
    label: str | None = None
    """Text displayed inside the gauge."""
    color: ColorLike = "green"
    """Filled-region color."""
    background: ColorLike | None = None
    """Gauge background color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class LineGauge(ContentBase):
    """Render progress as a single horizontal line.

    Attributes:
        progress: Completion ratio from zero to one.
        label: Text displayed with the line.
        color: Default foreground color.
        filled_color: Completed-region color.
        unfilled_color: Remaining-region color.
        background: Line background color.
    """

    progress: float = 0.0
    """Completion ratio from zero to one."""
    label: str | None = None
    """Text displayed with the line."""
    color: ColorLike | None = None
    """Default foreground color."""
    filled_color: ColorLike | None = None
    """Completed-region color."""
    unfilled_color: ColorLike | None = None
    """Remaining-region color."""
    background: ColorLike | None = None
    """Line background color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Bar:
    """One value in a bar chart.

    Attributes:
        value: Numeric bar value.
        label: Label beneath the bar.
        text_value: Displayed value override.
        color: Bar color.
        value_color: Value-label color.
    """

    value: int
    """Numeric bar value."""
    label: str = ""
    """Label beneath the bar."""
    text_value: str | None = None
    """Displayed value override."""
    color: ColorLike | None = None
    """Bar color."""
    value_color: ColorLike | None = None
    """Value-label color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BarGroup:
    """A labeled group of chart bars.

    Attributes:
        bars: Bars in this group.
        label: Group label.
    """

    bars: tuple[Bar, ...] = ()
    """Bars in this group."""
    label: str | None = None
    """Group label."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Bars(ContentBase):
    """Render grouped bars.

    Example:
        ``Bars(groups=(BarGroup(bars=(Bar(value=8, label="A"),)),))``

    Attributes:
        groups: Bar groups.
        bar_width: Width of each bar in cells.
        bar_gap: Cells between bars.
        group_gap: Cells between groups.
        max_value: Explicit value ceiling.
        direction: Bar growth direction.
        color: Default bar color.
        value_color: Default value-label color.
        label_color: Bar-label color.
    """

    groups: tuple[BarGroup, ...] = ()
    """Bar groups."""
    bar_width: int = 1
    """Width of each bar in cells."""
    bar_gap: int = 1
    """Cells between bars."""
    group_gap: int = 0
    """Cells between groups."""
    max_value: int | None = None
    """Explicit value ceiling."""
    direction: Direction = "vertical"
    """Bar growth direction."""
    color: ColorLike | None = None
    """Default bar color."""
    value_color: ColorLike | None = None
    """Default value-label color."""
    label_color: ColorLike | None = None
    """Bar-label color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PlotDataset:
    """One named data series in a plot.

    Attributes:
        data: Plot coordinates.
        name: Legend label.
        color: Series color.
        marker: Point marker.
        graph_type: Line, bar, or scatter representation.
    """

    data: tuple[tuple[float, float], ...] = ()
    """Plot coordinates."""
    name: str | None = None
    """Legend label."""
    color: ColorLike | None = None
    """Series color."""
    marker: CanvasMarkerLike | None = None
    """Point marker."""
    graph_type: GraphTypeLike = "line"
    """Line, bar, or scatter representation."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PlotAxis:
    """Labels and bounds for one plot axis.

    Attributes:
        title: Axis title.
        bounds: Minimum and maximum values.
        labels: Tick labels.
        color: Axis color.
    """

    title: str | None = None
    """Axis title."""
    bounds: tuple[float, float] | None = None
    """Minimum and maximum values."""
    labels: tuple[str, ...] | None = None
    """Tick labels."""
    color: ColorLike | None = None
    """Axis color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Plot(ContentBase):
    """Render one or more numeric data series.

    Example:
        ``Plot(datasets=(PlotDataset(data=((0, 1), (1, 3))),))``

    Attributes:
        datasets: Data series.
        x_axis: Horizontal axis.
        y_axis: Vertical axis.
        color: Default plot color.
        legend: Whether to show the legend.
        legend_position: Legend placement.
    """

    datasets: tuple[PlotDataset, ...] = ()
    """Data series."""
    x_axis: PlotAxis | None = None
    """Horizontal axis."""
    y_axis: PlotAxis | None = None
    """Vertical axis."""
    color: ColorLike | None = None
    """Default plot color."""
    legend: bool = True
    """Whether to show the legend."""
    legend_position: LegendPositionLike | None = "top_right"
    """Legend placement."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SparklineBar:
    """One individually styled sparkline sample.

    Attributes:
        value: Sample value.
        color: Sample color.
    """

    value: int
    """Sample value."""
    color: ColorLike | None = None
    """Sample color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Sparkline(ContentBase):
    """Render a compact sequence of vertical samples.

    Example:
        ``Sparkline(data=(2, 5, 3, 8), color="cyan")``

    Attributes:
        data: Sample values.
        bars: Individually styled samples.
        max_value: Explicit sample ceiling.
        color: Default sample color.
        background: Sparkline background.
        absent_value_color: Color for missing or zero samples.
        absent_value_symbol: Symbol for missing or zero samples.
    """

    data: tuple[int, ...] = ()
    """Sample values."""
    bars: tuple[SparklineBar, ...] | None = None
    """Individually styled samples."""
    max_value: int | None = None
    """Explicit sample ceiling."""
    color: ColorLike | None = None
    """Default sample color."""
    background: ColorLike | None = None
    """Sparkline background."""
    absent_value_color: ColorLike | None = None
    """Color for missing or zero samples."""
    absent_value_symbol: str | None = None
    """Symbol for missing or zero samples."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableCell:
    """Styled content in one table column.

    Attributes:
        content: Cell content.
        color: Foreground color.
        background: Background color.
        modifiers: Character modifiers.
    """

    content: str | Run | TextBlock = ""
    """Cell content."""
    color: ColorLike | None = None
    """Foreground color."""
    background: ColorLike | None = None
    """Background color."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Character modifiers."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableRow:
    """One styled table row.

    Attributes:
        cells: Cells in column order.
        color: Default row foreground.
        background: Default row background.
        height: Row height in cells.
    """

    cells: tuple[TableCell | str, ...] = ()
    """Cells in column order."""
    color: ColorLike | None = None
    """Default row foreground."""
    background: ColorLike | None = None
    """Default row background."""
    height: int = 1
    """Row height in cells."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableGrid(ContentBase):
    """Render tabular rows with optional selection.

    Example:
        ``TableGrid(rows=(TableRow(cells=("Ada", "Engineer")),))``

    Attributes:
        rows: Body rows.
        header: Optional header row.
        footer: Optional footer row.
        column_widths: Fixed cell widths or fractional widths.
        column_spacing: Cells between columns.
        selected_row: Selected body row.
        selected_column: Selected column.
        highlight_color: Selection foreground.
        highlight_background: Selection background.
        highlight_symbol: Symbol prefixed to the selected row.
    """

    rows: tuple[TableRow, ...] = ()
    """Body rows."""
    header: TableRow | None = None
    """Optional header row."""
    footer: TableRow | None = None
    """Optional footer row."""
    column_widths: tuple[int | float, ...] | None = None
    """Fixed cell widths or fractional widths."""
    column_spacing: int = 1
    """Cells between columns."""
    selected_row: int | None = None
    """Selected body row."""
    selected_column: int | None = None
    """Selected column."""
    highlight_color: ColorLike | None = None
    """Selection foreground."""
    highlight_background: ColorLike | None = None
    """Selection background."""
    highlight_symbol: str | None = None
    """Symbol prefixed to the selected row."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Items(ContentBase):
    """Render a selectable list of text items.

    Example:
        ``Items(items=("One", "Two"), selected=0)``

    Attributes:
        items: List entries.
        selected: Selected entry index.
        color: Default foreground.
        background: Default background.
        highlight_color: Selected-entry foreground.
        highlight_background: Selected-entry background.
        highlight_symbol: Symbol prefixed to the selected entry.
    """

    items: tuple[str | Run | TextBlock, ...] = ()
    """List entries."""
    selected: int | None = None
    """Selected entry index."""
    color: ColorLike | None = None
    """Default foreground."""
    background: ColorLike | None = None
    """Default background."""
    highlight_color: ColorLike = "black"
    """Selected-entry foreground."""
    highlight_background: ColorLike = "white"
    """Selected-entry background."""
    highlight_symbol: str = "> "
    """Symbol prefixed to the selected entry."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasLine:
    """A straight line on a numeric canvas.

    Attributes:
        x1: Starting x-coordinate.
        y1: Starting y-coordinate.
        x2: Ending x-coordinate.
        y2: Ending y-coordinate.
        color: Line color.
    """

    x1: float
    """Starting x-coordinate."""
    y1: float
    """Starting y-coordinate."""
    x2: float
    """Ending x-coordinate."""
    y2: float
    """Ending y-coordinate."""
    color: ColorLike = "white"
    """Line color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPoints:
    """A set of points on a numeric canvas.

    Attributes:
        coords: Point coordinates.
        color: Point color.
    """

    coords: tuple[tuple[float, float], ...] = ()
    """Point coordinates."""
    color: ColorLike = "white"
    """Point color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasRectangle:
    """A rectangle on a numeric canvas.

    Attributes:
        x: Left coordinate.
        y: Top coordinate.
        width: Rectangle width.
        height: Rectangle height.
        color: Rectangle color.
    """

    x: float
    """Left coordinate."""
    y: float
    """Top coordinate."""
    width: float
    """Rectangle width."""
    height: float
    """Rectangle height."""
    color: ColorLike = "white"
    """Rectangle color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasCircle:
    """A circle on a numeric canvas.

    Attributes:
        x: Center x-coordinate.
        y: Center y-coordinate.
        radius: Circle radius.
        color: Circle color.
    """

    x: float
    """Center x-coordinate."""
    y: float
    """Center y-coordinate."""
    radius: float
    """Circle radius."""
    color: ColorLike = "white"
    """Circle color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPrint:
    """Text positioned on a numeric canvas.

    Attributes:
        x: Text x-coordinate.
        y: Text y-coordinate.
        content: Displayed text.
    """

    x: float
    """Text x-coordinate."""
    y: float
    """Text y-coordinate."""
    content: str | Run | TextBlock = ""
    """Displayed text."""


CanvasShape: TypeAlias = (
    CanvasLine | CanvasPoints | CanvasRectangle | CanvasCircle | CanvasPrint
)
"""Shape accepted by ``Canvas``."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Canvas(ContentBase):
    """Render geometric shapes in numeric coordinate space.

    Example:
        ``Canvas(shapes=(CanvasCircle(x=0.5, y=0.5, radius=0.25),))``

    Attributes:
        shapes: Shapes painted in declaration order.
        x_bounds: Horizontal coordinate bounds.
        y_bounds: Vertical coordinate bounds.
        marker: Canvas point marker.
        background: Canvas background.
    """

    shapes: tuple[CanvasShape, ...] = ()
    """Shapes painted in declaration order."""
    x_bounds: tuple[float, float] = (0.0, 1.0)
    """Horizontal coordinate bounds."""
    y_bounds: tuple[float, float] = (0.0, 1.0)
    """Vertical coordinate bounds."""
    marker: CanvasMarkerLike = "braille"
    """Canvas point marker."""
    background: ColorLike | None = None
    """Canvas background."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Scrollbar(ContentBase):
    """Render scroll position and viewport proportion.

    Example:
        ``Scrollbar(content_length=100, viewport_length=20, position=10)``

    Attributes:
        content_length: Total scrollable length.
        position: Current scroll offset.
        viewport_length: Visible length.
        orientation: Scrollbar edge and direction.
        thumb_symbol: Custom thumb symbol.
        track_symbol: Custom track symbol.
        begin_symbol: Symbol at the beginning.
        end_symbol: Symbol at the end.
        color: Default scrollbar color.
        thumb_color: Thumb color.
        track_color: Track color.
    """

    content_length: int = 0
    """Total scrollable length."""
    position: int = 0
    """Current scroll offset."""
    viewport_length: int = 0
    """Visible length."""
    orientation: ScrollbarOrientationLike = "vertical_right"
    """Scrollbar edge and direction."""
    thumb_symbol: str | None = None
    """Custom thumb symbol."""
    track_symbol: str | None = None
    """Custom track symbol."""
    begin_symbol: str | None = None
    """Symbol at the beginning."""
    end_symbol: str | None = None
    """Symbol at the end."""
    color: ColorLike | None = None
    """Default scrollbar color."""
    thumb_color: ColorLike | None = None
    """Thumb color."""
    track_color: ColorLike | None = None
    """Track color."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Clear(ContentBase):
    """Clear the assigned render area.

    Attributes:
        style: Optional shared style.
        z: Sibling-local paint order.
        visible: Whether this content paints.
    """


@dataclasses.dataclass(frozen=True, slots=True)
class CellSpan:
    """A styled run inside a cell canvas row.

    Attributes:
        text: Characters covered by the span.
        color: Foreground color.
        background: Background color.
        modifiers: Character modifiers.
    """

    text: str = " "
    """Characters covered by the span."""
    color: ColorLike | None = None
    """Foreground color."""
    background: ColorLike | None = None
    """Background color."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Character modifiers."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CellCanvas(ContentBase):
    """A rectangular sequence of styled cell rows.

    Example:
        ``CellCanvas.from_rows(((CellSpan("OK", color="green"),),))``

    Attributes:
        rows: Rows of styled spans.
        width: Canvas width in cells.
        height: Canvas height in cells.
    """

    rows: tuple[tuple[CellSpan, ...], ...] = ()
    """Rows of styled spans."""
    width: int = 0
    """Canvas width in cells."""
    height: int = 0
    """Canvas height in cells."""

    @classmethod
    def from_rows(
        cls,
        rows: Sequence[Sequence[CellSpan | str]],
        *,
        width: int | None = None,
        style: Style | None = None,
        z: int = 0,
        visible: bool = True,
    ) -> "CellCanvas":
        """Create a cell canvas from styled span rows."""
        normalized = tuple(
            tuple(
                span if isinstance(span, CellSpan) else CellSpan(text=span)
                for span in row
            )
            for row in rows
        )
        measured_width = max(
            (sum(len(span.text) for span in row) for row in normalized),
            default=0,
        )
        return cls(
            rows=normalized,
            width=measured_width if width is None else width,
            height=len(normalized),
            style=style,
            z=z,
            visible=visible,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Native(ContentBase):
    """Content already lowered for a named interface.

    Example:
        ``Native(interface_kind="terminal", payload=widget)``

    Attributes:
        interface_kind: Target interface name.
        payload: Interface-specific payload.
    """

    interface_kind: str
    """Target interface name."""
    payload: Any = None
    """Interface-specific payload."""


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
"""Any beta content primitive."""


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
