"""xnano.core.nodes.terminal

The terminal's node types: text, panels, charts, tables, and everything
else a `Grid` can paint into a region of the screen. Every concrete node
here (`SpanNode`, `ParagraphNode`, `FrameNode`, ...) implements its own
drawing behavior directly, instead of being matched from the outside by a
central dispatcher that checks "is this a paragraph? a table? a chart?"
one type at a time.

Most nodes only need to implement `to_ir`, returning a `CoreRenderIR` —
a lightweight, mostly-Rust description that a controller can paint
directly. A handful of nodes have no such representation, either always
(a chart) or only in a particular case (a sparkline with per-bar colors,
where the shared color of a whole bar can't be expressed in the IR); those
override `lower` directly and build native content themselves.

A container node (`FrameNode`, `ContainerNode`, `StackNode`) never needs
to know what kind of node its children are — it measures and lowers them
by calling `child.measure()` / `child.lower(...)`, the same two methods
every node defines. That's the whole point of putting this behavior on
the node: nothing outside this module has to change when a new node type
is added.
"""

from __future__ import annotations

import dataclasses
from typing import Any, ClassVar, TypeAlias, TYPE_CHECKING

from xnano.color import ColorLike
from xnano.core.nodes.abstract import AbstractNode, NodeKind
from xnano.types import (
    Alignment,
    Area,
    CanvasMarkerLike,
    CharacterModifier,
    Direction,
    GraphTypeLike,
    LegendPositionLike,
    ScrollbarOrientationLike,
    Size,
)
from xnano.utils.native_types import (
    frame_length_overhead,
    get_native_color_from_color_like,
    get_native_style_from_kwargs,
)
from xnano_core.core import CoreRenderIR, IrLine
from xnano_core.rust import native

if TYPE_CHECKING:
    from xnano.core.controllers.abstract import (
        AbstractController,
        AbstractLayoutConstraint,
    )
    from xnano.frame import Frame


# Color resolution, style building, and frame-overhead measurement are
# shared with the terminal controller — they live in `xnano.utils.native_types`
# rather than being duplicated here.
_native_color = get_native_color_from_color_like
_native_style = get_native_style_from_kwargs
_frame_length_overhead = frame_length_overhead

# Modifiers are the one exception: `CoreRenderIR.*` calls take a *list* of
# individual `native.Modifier` flags, while `native_types.get_native_modifier_from_modifiers`
# returns them pre-combined into a single flag (what building a `native.Style`
# needs instead) — the two aren't interchangeable, so this stays local.
_NATIVE_MODIFIERS: dict[CharacterModifier, native.Modifier] = {
    "bold": native.Modifier.BOLD,
    "dim": native.Modifier.DIM,
    "italic": native.Modifier.ITALIC,
    "underline": native.Modifier.UNDERLINED,
    "slow_blink": native.Modifier.SLOW_BLINK,
    "rapid_blink": native.Modifier.RAPID_BLINK,
    "reversed": native.Modifier.REVERSED,
}


def _native_modifiers(
    modifiers: list[CharacterModifier] | None,
) -> list[native.Modifier]:
    if not modifiers:
        return []
    return [_NATIVE_MODIFIERS[modifier] for modifier in modifiers]


_ALIGNMENT_INDEX: dict[Alignment, int] = {"left": 0, "center": 1, "right": 2}


def _align_index(align: Alignment | None) -> int | None:
    if align is None:
        return None
    return _ALIGNMENT_INDEX[align]


_SCROLLBAR_ORIENTATION_INDEX: dict[ScrollbarOrientationLike, int] = {
    "vertical_right": 0,
    "vertical_left": 1,
    "horizontal_bottom": 2,
    "horizontal_top": 3,
}

_MARKER_INDEX: dict[CanvasMarkerLike, int] = {
    "dot": 0,
    "block": 1,
    "bar": 2,
    "braille": 3,
    "half_block": 4,
}

_NATIVE_GRAPH_TYPES: dict[GraphTypeLike, Any] = {
    "scatter": native.GraphType.Scatter,
    "line": native.GraphType.Line,
    "bar": native.GraphType.Bar,
}

_NATIVE_MARKERS: dict[CanvasMarkerLike, Any] = {
    "dot": native.Marker.Dot,
    "block": native.Marker.Block,
    "bar": native.Marker.Bar,
    "braille": native.Marker.Braille,
    "half_block": native.Marker.HalfBlock,
}

_NATIVE_LEGEND_POSITIONS: dict[LegendPositionLike, Any] = {
    "top": native.LegendPosition.Top,
    "top_right": native.LegendPosition.TopRight,
    "top_left": native.LegendPosition.TopLeft,
    "left": native.LegendPosition.Left,
    "right": native.LegendPosition.Right,
    "bottom": native.LegendPosition.Bottom,
    "bottom_right": native.LegendPosition.BottomRight,
    "bottom_left": native.LegendPosition.BottomLeft,
}


def _table_widths(
    column_widths: list[int | float] | None,
    col_count: int,
) -> list[tuple[int, float]]:
    if column_widths is None:
        return [(2, 1.0)] * max(col_count, 1)
    result: list[tuple[int, float]] = []
    for width in column_widths:
        if isinstance(width, float):
            result.append((1, width * 100.0))
        else:
            result.append((0, float(width)))
    return result


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AbstractTerminalNode(AbstractNode):
    """Base for every terminal render node.

    Two methods carry a node's drawing behavior:

        `to_ir`: returns this node's `CoreRenderIR` representation, or
            `None` if it doesn't have one. Most nodes only implement this.
        `lower`: paints this node into an area through a controller. The
            default implementation calls `to_ir` and enqueues the result
            through `controller.render_ir`; nodes with no IR
            representation (containers, and native-only widgets like a
            chart) override `lower` directly instead.

    A controller never inspects which concrete node it has — it calls
    `node.measure()` / `node.lower(...)` and lets the node decide how.
    """

    kind: ClassVar[NodeKind] = "terminal"

    def _effective_z(self, parent_z: int) -> int:
        return self.z or parent_z

    def to_ir(self) -> CoreRenderIR | None:
        """Return this node's `CoreRenderIR` representation, if it has one.

        Returns `None` for nodes that must be lowered through `lower`
        instead — containers, and native-only widgets.
        """
        return None

    def measure(self) -> Size:
        """Measure this node's content size in terminal cells."""
        if not self.visible:
            return Size(width=0, height=0)
        ir = self.to_ir()
        if ir is None:
            return Size(width=0, height=0)
        width, height = ir.measure()
        return Size(width=width, height=height)

    def lower(
        self,
        area: Area,
        controller: "AbstractController",
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Paint this node into `area` through `controller`.

        Args:
            area: The area to paint this node into.
            controller: The controller to paint this node through.
            z: The z-index this node inherits when it doesn't set its own.
            effect_key: The key of the effect targeting this node's area,
                if any.
        """
        if not self.visible:
            return
        ir = self.to_ir()
        if ir is None:
            raise NotImplementedError(
                f"{type(self).__name__} has no 'to_ir' representation and "
                "must override 'lower' directly."
            )
        controller.render_ir(
            area, ir, z=self._effective_z(z), effect_key=effect_key
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SpanNode(AbstractTerminalNode):
    """A single styled text span.

    Attributes:
        content: The text content of this span.
        color: The foreground color of this span.
        background: The background color of this span.
        modifiers: The modifiers to apply to the characters within this
            span's content.
    """

    content: str
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: list[CharacterModifier] = dataclasses.field(
        default_factory=list
    )

    def to_ir(self) -> CoreRenderIR:
        return CoreRenderIR.span(
            self.content,
            _native_color(self.color),
            _native_color(self.background),
            _native_modifiers(self.modifiers),
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class LineNode(AbstractTerminalNode):
    """A single line of text or styled spans.

    Attributes:
        content: The text content of this line.
        color: The foreground color of this line.
        background: The background color of this line.
        modifiers: The modifiers to apply to the characters within this
            line's content.
    """

    content: str | list[SpanNode] | None = None
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: list[CharacterModifier] = dataclasses.field(
        default_factory=list
    )

    def get_width(self) -> int:
        """Measures the width of the content within this line.

        Returns:
            The width of the content within this line.
        """
        if isinstance(self.content, str):
            return len(self.content)
        return sum(len(span.content) for span in self.content or [])

    def to_ir(self) -> CoreRenderIR:
        return CoreRenderIR.line(_ir_line(self))


def _ir_line(value: "str | SpanNode | LineNode") -> IrLine:
    """Convert a `str` / `SpanNode` / `LineNode` into a single `IrLine`."""
    if isinstance(value, str):
        return IrLine.raw(value)
    if isinstance(value, SpanNode):
        return IrLine.from_spans(
            [
                (
                    value.content,
                    _native_color(value.color),
                    _native_color(value.background),
                    _native_modifiers(value.modifiers),
                )
            ]
        )
    # LineNode
    if isinstance(value.content, str) or value.content is None:
        return IrLine.styled(
            value.content or "",
            _native_color(value.color),
            _native_color(value.background),
            _native_modifiers(value.modifiers),
        )
    spans = [
        (
            span.content,
            _native_color(span.color),
            _native_color(span.background),
            _native_modifiers(span.modifiers),
        )
        for span in value.content
    ]
    return IrLine.from_spans(spans)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TextNode(AbstractTerminalNode):
    """Multi-line text render node.

    Attributes:
        content: The text content of this text node.
        lines: The lines of text in this text node.
        color: The foreground color of this text node.
        background: The background color of this text node.
        modifiers: The modifiers to apply to the characters within this
            text node's content.
    """

    content: str = ""
    lines: list[LineNode] = dataclasses.field(default_factory=list)
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: tuple[CharacterModifier, ...] = ()
    align: Alignment | None = None

    def get_size(self) -> Size:
        """Measures the size of the content within this text node.

        Returns:
            The size of the content within this text node.
        """
        if self.lines:
            return Size(
                width=max(line.get_width() for line in self.lines),
                height=len(self.lines),
            )
        if not self.content:
            return Size(width=0, height=1)
        lines = self.content.split("\n")
        return Size(
            width=max(len(line) for line in lines),
            height=len(lines),
        )

    def to_ir(self) -> CoreRenderIR:
        fg = _native_color(self.color)
        bg = _native_color(self.background)
        mods = _native_modifiers(list(self.modifiers))
        align = _align_index(self.align)
        if self.lines:
            lines = [_ir_line(line) for line in self.lines]
            return CoreRenderIR.text_lines(lines, fg, bg, mods, align)
        return CoreRenderIR.text_raw(self.content, fg, bg, mods, align)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ParagraphNode(AbstractTerminalNode):
    """A single-or-multi-line text paragraph.

    Attributes:
        text: The text content of this paragraph.
        color: The foreground color of this paragraph.
        background: The background color of this paragraph.
        modifiers: The modifiers to apply to the characters within this
            paragraph's content.
    """

    text: str | TextNode | LineNode = ""
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: tuple[CharacterModifier, ...] = ()
    align: Alignment | None = None
    wrap: bool = True

    def to_ir(self) -> CoreRenderIR:
        fg = _native_color(self.color)
        bg = _native_color(self.background)
        mods = _native_modifiers(list(self.modifiers))
        align = _align_index(self.align)
        text = self.text
        if isinstance(text, str):
            return CoreRenderIR.paragraph_raw(
                text, fg, bg, mods, align, self.wrap
            )
        if isinstance(text, TextNode):
            if text.lines:
                lines = [_ir_line(line) for line in text.lines]
                return CoreRenderIR.paragraph_lines(
                    lines, fg, bg, mods, align, self.wrap
                )
            return CoreRenderIR.paragraph_raw(
                text.content, fg, bg, mods, align, self.wrap
            )
        # LineNode body
        return CoreRenderIR.paragraph_lines(
            [_ir_line(text)], fg, bg, mods, align, self.wrap
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ListNode(AbstractTerminalNode):
    """A selectable list widget.

    Attributes:
        items: The items in this list.
        selected: The selected item in this list.
        color: The foreground color of this list.
        background: The background color of this list.
        highlight_color: The foreground color of the selected item.
        highlight_background: The background color of the selected item.
        highlight_symbol: The symbol prepended to the selected item.
    """

    items: list[str | LineNode | SpanNode] = dataclasses.field(
        default_factory=list
    )
    selected: int | None = None
    color: ColorLike | None = None
    background: ColorLike | None = None
    highlight_color: ColorLike = "black"
    highlight_background: ColorLike = "white"
    highlight_symbol: str = "> "

    def to_ir(self) -> CoreRenderIR:
        ir_items = [_ir_line(item) for item in self.items]
        return CoreRenderIR.list(
            ir_items,
            self.selected,
            _native_color(self.color),
            _native_color(self.background),
            _native_color(self.highlight_color),
            _native_color(self.highlight_background),
            self.highlight_symbol,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ProgressBarNode(AbstractTerminalNode):
    """A progress bar widget.

    Attributes:
        progress: The current progress of the progress bar, as a value
            between 0.0 and 1.0.
        label: An optional label rendered within the progress bar.
        color: The foreground color of this progress bar.
        background: The background color of this progress bar.
    """

    progress: float = 0.0
    label: str | None = None
    color: ColorLike = "green"
    background: ColorLike | None = None

    def to_ir(self) -> CoreRenderIR:
        return CoreRenderIR.progress_bar(
            self.progress,
            self.label,
            _native_color(self.color),
            _native_color(self.background),
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ClearNode(AbstractTerminalNode):
    """A clear-area render node."""

    def to_ir(self) -> CoreRenderIR:
        return CoreRenderIR.clear()


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FrameNode(AbstractTerminalNode):
    """A frame render node.

    Attributes:
        frame: The frame of this frame render node.
        child: The child render node of this frame render node.
    """

    frame: "Frame"
    child: AbstractTerminalNode

    def measure(self) -> Size:
        if not self.visible:
            return Size(width=0, height=0)
        child_size = self.child.measure()
        return Size(
            width=child_size.width
            + _frame_length_overhead(self.frame, "horizontal"),
            height=child_size.height
            + _frame_length_overhead(self.frame, "vertical"),
        )

    def lower(
        self,
        area: Area,
        controller: "AbstractController",
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        if not self.visible:
            return
        effective_z = self._effective_z(z)
        inner_area = controller.paint_frame(area, self.frame, z=effective_z)
        self.child.lower(inner_area, controller, z=effective_z)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ContainerNode(AbstractTerminalNode):
    """A container render node.

    Attributes:
        direction: The direction in which the children of this container
            render node should be laid out.
        children: The children of this container render node.
        gap: The gap between the children of this container render node.
    """

    direction: Direction
    children: list[AbstractTerminalNode]
    gap: int = 0

    def measure(self) -> Size:
        if not self.visible or not self.children:
            return Size(width=0, height=0)
        sizes = [child.measure() for child in self.children]
        if self.direction == "horizontal":
            return Size(
                width=sum(size.width for size in sizes)
                + self.gap * (len(sizes) - 1),
                height=max(size.height for size in sizes),
            )
        return Size(
            width=max(size.width for size in sizes),
            height=sum(size.height for size in sizes)
            + self.gap * (len(sizes) - 1),
        )

    def lower(
        self,
        area: Area,
        controller: "AbstractController",
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        if not self.visible or not self.children:
            return
        effective_z = self._effective_z(z)
        from xnano.core.controllers.abstract import AbstractLayoutConstraint

        # Equal fill weight per child — `AbstractLayoutConstraint` carries
        # no weight field yet, so this relies on a controller treating a
        # bare "fill" constraint as equal-share among siblings.
        constraints: list[AbstractLayoutConstraint] = [
            AbstractLayoutConstraint(kind="fill") for _ in self.children
        ]
        child_areas = controller.split_layout(
            area, self.direction, self.gap, constraints
        )
        for child, child_area in zip(self.children, child_areas):
            child.lower(child_area, controller, z=effective_z)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class StackNode(AbstractTerminalNode):
    """A render node that lays out its children on top of each other.

    Attributes:
        children: The children of this stack render node.
    """

    children: list[AbstractTerminalNode]

    def measure(self) -> Size:
        if not self.visible or not self.children:
            return Size(width=0, height=0)
        sizes = [child.measure() for child in self.children]
        return Size(
            width=max(size.width for size in sizes),
            height=max(size.height for size in sizes),
        )

    def lower(
        self,
        area: Area,
        controller: "AbstractController",
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        if not self.visible:
            return
        effective_z = self._effective_z(z)
        for child in self.children:
            child.lower(area, controller, z=effective_z)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SparklineBarItem:
    """A single bar in a `SparklineNode`.

    Attributes:
        value: Numeric height of the bar.
        color: Per-bar foreground color; `None` uses the node default.
    """

    value: int
    color: ColorLike | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SparklineNode(AbstractTerminalNode):
    """A sparkline (mini bar chart) widget.

    Attributes:
        data: Sequence of non-negative sample values.
        bars: Optional per-bar items with individual colors. When set,
            this node has no `to_ir` representation — per-bar colors can't
            be expressed in the IR — and `lower` builds a native widget
            instead.
        max_value: Explicit y-axis ceiling; `None` = auto-scale.
        color: Default bar foreground color.
        background: Widget background color.
        absent_value_color: Color applied to zero/absent samples.
        absent_value_symbol: Glyph for absent samples (default `""`).
    """

    data: list[int] = dataclasses.field(default_factory=list)
    bars: list[SparklineBarItem] | None = None
    max_value: int | None = None
    color: ColorLike | None = None
    background: ColorLike | None = None
    absent_value_color: ColorLike | None = None
    absent_value_symbol: str | None = None

    def to_ir(self) -> CoreRenderIR | None:
        if self.bars is not None:
            return None
        return CoreRenderIR.sparkline(
            self.data,
            self.max_value,
            _native_color(self.color),
            _native_color(self.background),
            _native_color(self.absent_value_color),
            self.absent_value_symbol,
        )

    def lower(
        self,
        area: Area,
        controller: "AbstractController",
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        if not self.visible:
            return
        if self.bars is None:
            return super().lower(area, controller, z=z, effect_key=effect_key)

        native_bars: list[Any] = []
        for bar in self.bars:
            native_bar = native.SparklineBar.new(bar.value)
            if bar.color is not None:
                bar_style = _native_style(color=bar.color)
                if bar_style is not None:
                    native_bar = native_bar.style(bar_style)
            native_bars.append(native_bar)

        spark = native.Sparkline.from_bars(native_bars)
        if self.max_value is not None:
            spark = spark.max(self.max_value)
        if self.color is not None:
            style = _native_style(color=self.color)
            if style is not None:
                spark = spark.style(style)
        controller.render_native(
            area, spark, z=self._effective_z(z), effect_key=effect_key
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class LineGaugeNode(AbstractTerminalNode):
    """A thin horizontal progress gauge.

    Attributes:
        progress: Completion ratio, 0.0-1.0; clamped at render time.
        label: Optional text label rendered inside the gauge.
        color: Overall widget foreground style.
        filled_color: Filled-portion foreground color.
        unfilled_color: Unfilled-portion foreground color.
        background: Widget background color.
    """

    progress: float = 0.0
    label: str | None = None
    color: ColorLike | None = None
    filled_color: ColorLike | None = None
    unfilled_color: ColorLike | None = None
    background: ColorLike | None = None

    def to_ir(self) -> CoreRenderIR:
        return CoreRenderIR.line_gauge(
            self.progress,
            self.label,
            _native_color(self.color),
            _native_color(self.background),
            _native_color(self.filled_color),
            _native_color(self.unfilled_color),
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BarItem:
    """A single bar in a `BarChartNode` group.

    Attributes:
        value: Numeric height of the bar.
        label: Label shown beneath the bar.
        text_value: Explicit override for the value label text.
        color: Per-bar fill color.
        value_color: Per-bar value-label color.
    """

    value: int
    label: str = ""
    text_value: str | None = None
    color: ColorLike | None = None
    value_color: ColorLike | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BarGroupItem:
    """A group of bars in a `BarChartNode`.

    Attributes:
        bars: The bars in this group.
        label: Optional group label (passed through but not yet exposed by
            the binding).
    """

    bars: list[BarItem] = dataclasses.field(default_factory=list)
    label: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BarChartNode(AbstractTerminalNode):
    """A grouped bar chart widget.

    Attributes:
        groups: List of bar groups to display.
        bar_width: Width of each bar in terminal columns.
        bar_gap: Gap between bars in the same group.
        group_gap: Gap between groups.
        max_value: Explicit y-axis ceiling; `None` = auto-scale.
        direction: Whether bars grow vertically or horizontally.
        color: Default bar fill style.
        value_color: Default value-label color.
        label_color: Bar-label color.
    """

    groups: list[BarGroupItem] = dataclasses.field(default_factory=list)
    bar_width: int = 1
    bar_gap: int = 1
    group_gap: int = 0
    max_value: int | None = None
    direction: Direction = "vertical"
    color: ColorLike | None = None
    value_color: ColorLike | None = None
    label_color: ColorLike | None = None

    def to_ir(self) -> CoreRenderIR:
        groups: list[Any] = []
        for group in self.groups:
            bars = [
                (
                    bar.value,
                    bar.label,
                    bar.text_value,
                    _native_color(bar.color),
                    None,
                    _native_color(bar.value_color),
                    None,
                )
                for bar in group.bars
            ]
            groups.append((group.label, bars))
        return CoreRenderIR.bar_chart(
            groups,
            self.bar_width,
            self.bar_gap,
            self.group_gap,
            self.max_value,
            self.direction == "horizontal",
            _native_color(self.color),
            _native_color(self.value_color),
            _native_color(self.label_color),
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableCellItem:
    """A single cell in a `TableRowItem`.

    Attributes:
        content: Cell content — plain string, a styled line, or a span.
        color: Cell foreground color.
        background: Cell background color.
        modifiers: Text modifiers applied to cell content.
    """

    content: str | LineNode | SpanNode = ""
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: list[CharacterModifier] = dataclasses.field(
        default_factory=list
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableRowItem:
    """A row in a `TableNode`.

    Attributes:
        cells: The cells in this row.
        color: Row foreground color.
        background: Row background color.
        height: Row height in terminal lines.
    """

    cells: list[TableCellItem | str] = dataclasses.field(default_factory=list)
    color: ColorLike | None = None
    background: ColorLike | None = None
    height: int = 1


def _ir_table_cell(
    cell: "TableCellItem | str",
) -> tuple[IrLine, native.Color | None, native.Color | None, list[Any]]:
    if isinstance(cell, str):
        return (IrLine.raw(cell), None, None, [])
    return (
        _ir_line(cell.content),
        _native_color(cell.color),
        _native_color(cell.background),
        _native_modifiers(cell.modifiers),
    )


def _ir_table_row(
    row: "TableRowItem",
) -> tuple[list[Any], native.Color | None, native.Color | None, int]:
    return (
        [_ir_table_cell(cell) for cell in row.cells],
        _native_color(row.color),
        _native_color(row.background),
        row.height,
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableNode(AbstractTerminalNode):
    """A table widget with optional header and footer rows.

    Attributes:
        rows: Body rows.
        header: Optional header row.
        footer: Optional footer row.
        column_widths: Per-column width constraints. `int` = fixed
            character width; `float` 0.0-1.0 = percentage of available
            space; `None` = equal fill for all columns.
        column_spacing: Space between columns in terminal columns.
        selected_row: Highlighted row index; triggers stateful rendering.
        selected_column: Highlighted column index; triggers stateful
            rendering.
        highlight_color: Highlight foreground color.
        highlight_background: Highlight background color.
        highlight_symbol: Symbol prepended to the selected row.
    """

    rows: list[TableRowItem] = dataclasses.field(default_factory=list)
    header: TableRowItem | None = None
    footer: TableRowItem | None = None
    column_widths: list[int | float] | None = None
    column_spacing: int = 1
    selected_row: int | None = None
    selected_column: int | None = None
    highlight_color: ColorLike | None = None
    highlight_background: ColorLike | None = None
    highlight_symbol: str | None = None

    def to_ir(self) -> CoreRenderIR:
        col_count = max((len(row.cells) for row in self.rows), default=1)
        return CoreRenderIR.table(
            [_ir_table_row(row) for row in self.rows],
            _ir_table_row(self.header) if self.header is not None else None,
            _ir_table_row(self.footer) if self.footer is not None else None,
            _table_widths(self.column_widths, col_count),
            self.column_spacing,
            self.selected_row,
            self.selected_column,
            _native_color(self.highlight_color),
            _native_color(self.highlight_background),
            self.highlight_symbol,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ScrollbarNode(AbstractTerminalNode):
    """A scrollbar widget. Always rendered with state.

    Attributes:
        content_length: Total scrollable content size (rows or columns).
        position: Current scroll offset within `content_length`.
        viewport_length: Visible window size; drives thumb proportion.
        orientation: Which edge the scrollbar is drawn on.
        color: Overall track + thumb style.
        thumb_color: Thumb foreground color.
        track_color: Track foreground color.
        begin_symbol: Arrow symbol at the start; `None` omits the arrow.
        end_symbol: Arrow symbol at the end; `None` omits the arrow.
    """

    content_length: int = 0
    position: int = 0
    viewport_length: int | None = None
    orientation: ScrollbarOrientationLike = "vertical_right"
    color: ColorLike | None = None
    thumb_color: ColorLike | None = None
    track_color: ColorLike | None = None
    begin_symbol: str | None = None
    end_symbol: str | None = None

    def to_ir(self) -> CoreRenderIR:
        return CoreRenderIR.scrollbar(
            _SCROLLBAR_ORIENTATION_INDEX.get(self.orientation, 0),
            self.content_length,
            self.position,
            self.viewport_length,
            _native_color(self.color),
            _native_color(self.thumb_color),
            _native_color(self.track_color),
            self.begin_symbol,
            self.end_symbol,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TabsNode(AbstractTerminalNode):
    """A tab bar widget.

    Attributes:
        titles: One entry per tab — plain string, styled line, or span.
        selected: Active tab index; `None` = no selection.
        color: Unselected tab foreground color.
        background: Widget background color.
        highlight_color: Selected tab foreground color.
        highlight_background: Selected tab background color.
        divider: Glyph between tabs; `None` uses the ratatui default (`"|"`).
        padding_left: Padding inserted left of each tab title.
        padding_right: Padding inserted right of each tab title.
    """

    titles: list[str | LineNode | SpanNode] = dataclasses.field(
        default_factory=list
    )
    selected: int | None = None
    color: ColorLike | None = None
    background: ColorLike | None = None
    highlight_color: ColorLike | None = None
    highlight_background: ColorLike | None = None
    divider: str | None = None
    padding_left: str = " "
    padding_right: str = " "

    def to_ir(self) -> CoreRenderIR:
        titles = [_ir_line(title) for title in self.titles]
        return CoreRenderIR.tabs(
            titles,
            self.selected or 0,
            _native_color(self.color),
            _native_color(self.background),
            _native_color(self.highlight_color),
            _native_color(self.highlight_background),
            self.divider,
            self.padding_left,
            self.padding_right,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasLine:
    """A straight line drawn on a `CanvasNode`."""

    x1: float
    y1: float
    x2: float
    y2: float
    color: ColorLike = "white"

    def to_native_shape(self) -> tuple[Any, ...]:
        return (
            "line",
            self.x1,
            self.y1,
            self.x2,
            self.y2,
            _native_color(self.color) or native.Color.WHITE,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPoints:
    """A scatter of points drawn on a `CanvasNode`."""

    coords: list[tuple[float, float]] = dataclasses.field(default_factory=list)
    color: ColorLike = "white"

    def to_native_shape(self) -> tuple[Any, ...]:
        return (
            "points",
            list(self.coords),
            _native_color(self.color) or native.Color.WHITE,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasRectangle:
    """An axis-aligned rectangle drawn on a `CanvasNode`."""

    x: float
    y: float
    width: float
    height: float
    color: ColorLike = "white"

    def to_native_shape(self) -> tuple[Any, ...]:
        return (
            "rect",
            self.x,
            self.y,
            self.width,
            self.height,
            _native_color(self.color) or native.Color.WHITE,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasCircle:
    """A circle drawn on a `CanvasNode`."""

    x: float
    y: float
    radius: float
    color: ColorLike = "white"

    def to_native_shape(self) -> tuple[Any, ...]:
        return (
            "circle",
            self.x,
            self.y,
            self.radius,
            _native_color(self.color) or native.Color.WHITE,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPrint:
    """Text printed at a canvas coordinate on a `CanvasNode`."""

    x: float
    y: float
    content: str | LineNode | SpanNode = ""

    def to_native_shape(self) -> tuple[Any, ...]:
        content = self.content
        if isinstance(content, str):
            spans: list[Any] = [(content, None, None, [])]
        elif isinstance(content, LineNode):
            if isinstance(content.content, list):
                spans = [
                    (
                        span.content,
                        _native_color(span.color),
                        _native_color(span.background),
                        _native_modifiers(span.modifiers),
                    )
                    for span in content.content
                ]
            else:
                spans = [
                    (
                        content.content or "",
                        _native_color(content.color),
                        _native_color(content.background),
                        _native_modifiers(content.modifiers),
                    )
                ]
        else:  # SpanNode
            spans = [
                (
                    content.content,
                    _native_color(content.color),
                    _native_color(content.background),
                    _native_modifiers(content.modifiers),
                )
            ]
        return ("print", self.x, self.y, spans)


CanvasShape: TypeAlias = (
    CanvasLine | CanvasPoints | CanvasRectangle | CanvasCircle | CanvasPrint
)
"""Union of all shape types accepted by `CanvasNode`."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasNode(AbstractTerminalNode):
    """A free-draw canvas widget.

    Attributes:
        shapes: Drawing commands replayed in order at render time.
        x_bounds: Logical x-axis range `(min, max)`.
        y_bounds: Logical y-axis range `(min, max)`.
        background: Canvas background color.
        marker: Glyph set used to paint canvas cells; `None` = ratatui
            default.
    """

    shapes: list[CanvasShape] = dataclasses.field(default_factory=list)
    x_bounds: tuple[float, float] = (0.0, 1.0)
    y_bounds: tuple[float, float] = (0.0, 1.0)
    background: ColorLike | None = None
    marker: CanvasMarkerLike | None = None

    def to_ir(self) -> CoreRenderIR:
        return CoreRenderIR.canvas(
            [shape.to_native_shape() for shape in self.shapes],
            self.x_bounds,
            self.y_bounds,
            _native_color(self.background),
            _MARKER_INDEX.get(self.marker) if self.marker else None,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ChartDataset:
    """A single plotted series in a `ChartNode`.

    Attributes:
        data: `(x, y)` sample points in logical coordinates.
        name: Legend label for the series.
        color: Series line/point color.
        marker: Glyph set used to paint the series; `None` = ratatui
            default.
        graph_type: How the series is plotted (line, scatter, or bar).
    """

    data: list[tuple[float, float]] = dataclasses.field(default_factory=list)
    name: str | None = None
    color: ColorLike | None = None
    marker: CanvasMarkerLike | None = None
    graph_type: GraphTypeLike = "line"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ChartAxis:
    """An axis specification for a `ChartNode`.

    Attributes:
        title: Axis title text.
        bounds: Logical `(min, max)` range of the axis.
        labels: Tick labels drawn along the axis.
        color: Axis line + label color.
    """

    title: str | None = None
    bounds: tuple[float, float] | None = None
    labels: list[str] | None = None
    color: ColorLike | None = None

    def to_native_axis(self) -> Any:
        axis = native.Axis.default()
        if self.title is not None:
            axis = axis.title(self.title)
        if self.bounds is not None:
            axis = axis.bounds(self.bounds)
        if self.labels is not None:
            axis = axis.labels(self.labels)
        if self.color is not None:
            style = _native_style(color=self.color)
            if style is not None:
                axis = axis.style(style)
        return axis


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ChartNode(AbstractTerminalNode):
    """A line/scatter/bar chart with axes and an optional legend.

    Rendered through the native ratatui `Chart` widget — it has no
    `CoreRenderIR` representation at all, so `lower` is overridden
    directly rather than `to_ir`.

    Attributes:
        datasets: The plotted series.
        x_axis: Optional x-axis specification.
        y_axis: Optional y-axis specification.
        color: Overall widget foreground style.
        legend_position: Where the legend is drawn; `None` hides it.
    """

    datasets: list[ChartDataset] = dataclasses.field(default_factory=list)
    x_axis: ChartAxis | None = None
    y_axis: ChartAxis | None = None
    color: ColorLike | None = None
    legend_position: LegendPositionLike | None = "top_right"

    def lower(
        self,
        area: Area,
        controller: "AbstractController",
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        if not self.visible:
            return

        native_datasets: list[Any] = []
        for dataset in self.datasets:
            native_dataset = native.Dataset.default().data(dataset.data)
            if dataset.name is not None:
                native_dataset = native_dataset.name(dataset.name)
            native_dataset = native_dataset.graph_type(
                _NATIVE_GRAPH_TYPES.get(
                    dataset.graph_type, native.GraphType.Line
                )
            )
            if dataset.marker is not None:
                native_dataset = native_dataset.marker(
                    _NATIVE_MARKERS.get(dataset.marker, native.Marker.Braille)
                )
            series_color = (
                dataset.color if dataset.color is not None else self.color
            )
            if series_color is not None:
                style = _native_style(color=series_color)
                if style is not None:
                    native_dataset = native_dataset.style(style)
            native_datasets.append(native_dataset)

        chart = native.Chart.new(native_datasets)
        if self.x_axis is not None:
            chart = chart.x_axis(self.x_axis.to_native_axis())
        if self.y_axis is not None:
            chart = chart.y_axis(self.y_axis.to_native_axis())
        if self.color is not None:
            style = _native_style(color=self.color)
            if style is not None:
                chart = chart.style(style)
        if self.legend_position is None:
            chart = chart.legend_position(None)
        else:
            chart = chart.legend_position(
                _NATIVE_LEGEND_POSITIONS.get(
                    self.legend_position, native.LegendPosition.TopRight
                )
            )
        controller.render_native(
            area, chart, z=self._effective_z(z), effect_key=effect_key
        )


TerminalNode: TypeAlias = AbstractTerminalNode
"""Alias for the general terminal node type, for import convenience."""


__all__ = (
    "AbstractTerminalNode",
    "BarChartNode",
    "BarGroupItem",
    "BarItem",
    "CanvasCircle",
    "CanvasLine",
    "CanvasNode",
    "CanvasPoints",
    "CanvasPrint",
    "CanvasRectangle",
    "CanvasShape",
    "ChartAxis",
    "ChartDataset",
    "ChartNode",
    "ClearNode",
    "ContainerNode",
    "FrameNode",
    "LineGaugeNode",
    "LineNode",
    "ListNode",
    "ParagraphNode",
    "ProgressBarNode",
    "ScrollbarNode",
    "SparklineBarItem",
    "SparklineNode",
    "SpanNode",
    "StackNode",
    "TableCellItem",
    "TableNode",
    "TableRowItem",
    "TabsNode",
    "TerminalNode",
    "TextNode",
)
