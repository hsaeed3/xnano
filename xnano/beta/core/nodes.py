"""xnano.beta.core.nodes"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any, TypeAlias, Union, TYPE_CHECKING

from xnano.beta.types import (
    Area,
    Alignment,
    CanvasMarkerLike,
    CharacterModifier,
    Direction,
    Padding,
    ScrollbarOrientationLike,
    Size,
)

if TYPE_CHECKING:
    from xnano.beta.core.session import Session
    from xnano.beta.color import ColorLike
    from xnano.beta.frame import Frame


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AbstractRenderNode(abc.ABC):
    """Abstract base class for a 'render node'.

    Render nodes are the framework's low-level intermediate representation:
    immutable, composable descriptions of *what* to draw in a terminal cell
    region (text, paragraphs, lists, frames, layout containers, etc.).
    The session lowers them through ``xnano-core`` into native widgets each
    frame.
    """


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SpanNode(AbstractRenderNode):
    """A single styled text span.

    Attributes:
        content: The text content of this span.
        color: The foreground color of this span.
        background: The background color of this span.
        modifiers: The modifiers to to apply to the characters
            within this span's content.
    """

    content: str
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: list[CharacterModifier] = dataclasses.field(
        default_factory=list
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class LineNode(AbstractRenderNode):
    """A single line of text or styled spans.

    Attributes:
        content: The text content of this line.
        color: The foreground color of this line.
        background: The background color of this line.
        modifiers: The modifiers to to apply to the characters
            within this line's content.
    """

    content: str | list[SpanNode] | None = None
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: list[CharacterModifier] = dataclasses.field(
        default_factory=list
    )

    def get_width(self) -> int:
        """Measures the width of the content within this
        line.

        Returns:
            The width of the content within this line.
        """
        if isinstance(self.content, str):
            return len(self.content)
        return sum(len(span.content) for span in self.content or [])


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TextNode(AbstractRenderNode):
    """ "Multi-line text render node.

    Attributes:
        content: The text content of this text node.
        lines: The lines of text in this text node.
        color: The foreground color of this text node.
        background: The background color of this text node.
        modifiers: The modifiers to to apply to the characters
            within this text node's content.
    """

    content: str = ""
    lines: list[LineNode] = dataclasses.field(default_factory=list)
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: tuple[CharacterModifier, ...] = ()
    align: Alignment | None = None
    z: int = 0
    visible: bool = True

    def get_size(self) -> Size:
        """Measures the size of the content within this text
        node.

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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ParagraphNode(AbstractRenderNode):
    """A single-or-multi-line text paragraph.

    Attributes:
        text: The text content of this paragraph.
        color: The foreground color of this paragraph.
        background: The background color of this paragraph.
        modifiers: The modifiers to to apply to the characters
            within this paragraph's content.
    """

    text: str | TextNode | LineNode = ""
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: tuple[CharacterModifier, ...] = ()
    align: Alignment | None = None
    wrap: bool = True
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ListNode(AbstractRenderNode):
    """A selectable list widget.

    Attributes:
        items: The items in this list.
        selected: The selected item in this list.
        color: The foreground color of this list.
        background: The background color of this list.
        modifiers: The modifiers to to apply to the characters
            within this list's content.
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
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ProgressBarNode(AbstractRenderNode):
    """A progress bar widget.

    Attributes:
        ratio: The current progress of the progress bar, as a value between
            0.0 and 1.0.
        color: The foreground color of this progress bar.
        background: The background color of this progress bar.
        modifiers: The modifiers to to apply to the characters
            within this progress bar's content.
    """

    progress: float = 0.0
    label: str | None = None
    color: ColorLike = "green"
    background: ColorLike | None = None
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ClearNode(AbstractRenderNode):
    """A clear-area render node.

    Attributes:
        z: The z-index of this clear-area render node.
        visible: Whether this clear-area render node is visible.
    """

    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FrameNode(AbstractRenderNode):
    """A frame render node.

    Attributes:
        frame: The frame of this frame render node.
        child: The child render node of this frame render node.
    """

    frame: Frame
    child: AbstractRenderNode
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ContainerNode(AbstractRenderNode):
    """A container render node.

    Attributes:
        direction: The direction in which the children of this container
            render node should be laid out.
        children: The children of this container render node.
        gap: The gap between the children of this container render node.
        z: The z-index of this container render node.
        visible: Whether this container render node is visible.
    """

    direction: Direction
    children: list[AbstractRenderNode]
    gap: int = 0
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class StackNode(AbstractRenderNode):
    """A render node that lays out it's children on top of each
    other.

    Attributes:
        children: The children of this stack render node.
        z: The z-index of this stack render node.
        visible: Whether this stack render node is visible.
    """

    children: list[AbstractRenderNode]
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SparklineBarItem:
    """A single bar in a ``SparklineNode``.

    Attributes:
        value: Numeric height of the bar.
        color: Per-bar foreground color; ``None`` uses the node default.
    """

    value: int
    color: ColorLike | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SparklineNode(AbstractRenderNode):
    """A sparkline (mini bar chart) widget.

    Attributes:
        data: Sequence of non-negative sample values.
        bars: Optional per-bar items with individual colors.
        max_value: Explicit y-axis ceiling; ``None`` = auto-scale.
        color: Default bar foreground color.
        background: Widget background color.
        absent_value_color: Color applied to zero/absent samples.
        absent_value_symbol: Glyph for absent samples (default ``""``).
    """

    data: list[int] = dataclasses.field(default_factory=list)
    bars: list[SparklineBarItem] | None = None
    max_value: int | None = None
    color: ColorLike | None = None
    background: ColorLike | None = None
    absent_value_color: ColorLike | None = None
    absent_value_symbol: str | None = None
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class LineGaugeNode(AbstractRenderNode):
    """A thin horizontal progress gauge.

    Attributes:
        progress: Completion ratio, ``0.0``–``1.0``; clamped at render time.
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
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BarItem:
    """A single bar in a ``BarChartNode`` group.

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
    """A group of bars in a ``BarChartNode``.

    Attributes:
        bars: The bars in this group.
        label: Optional group label (passed through but not yet exposed by the binding).
    """

    bars: list[BarItem] = dataclasses.field(default_factory=list)
    label: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BarChartNode(AbstractRenderNode):
    """A grouped bar chart widget.

    Attributes:
        groups: List of bar groups to display.
        bar_width: Width of each bar in terminal columns.
        bar_gap: Gap between bars in the same group.
        group_gap: Gap between groups.
        max_value: Explicit y-axis ceiling; ``None`` = auto-scale.
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
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableCellItem:
    """A single cell in a ``TableRowItem``.

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
    """A row in a ``TableNode``.

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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TableNode(AbstractRenderNode):
    """A table widget with optional header and footer rows.

    Attributes:
        rows: Body rows.
        header: Optional header row.
        footer: Optional footer row.
        column_widths: Per-column width constraints.  ``int`` = fixed character
            width; ``float`` ``0.0``–``1.0`` = percentage of available space;
            ``None`` = equal fill for all columns.
        column_spacing: Space between columns in terminal columns.
        selected_row: Highlighted row index; triggers stateful rendering.
        selected_column: Highlighted column index; triggers stateful rendering.
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
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ScrollbarNode(AbstractRenderNode):
    """A scrollbar widget.  Always rendered with state.

    Attributes:
        content_length: Total scrollable content size (rows or columns).
        position: Current scroll offset within ``content_length``.
        viewport_length: Visible window size; drives thumb proportion.
        orientation: Which edge the scrollbar is drawn on.
        color: Overall track + thumb style.
        thumb_color: Thumb foreground color.
        track_color: Track foreground color.
        begin_symbol: Arrow symbol at the start; ``None`` omits the arrow.
        end_symbol: Arrow symbol at the end; ``None`` omits the arrow.
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
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TabsNode(AbstractRenderNode):
    """A tab bar widget.

    Attributes:
        titles: One entry per tab — plain string, styled line, or span.
        selected: Active tab index; ``None`` = no selection.
        color: Unselected tab foreground color.
        background: Widget background color.
        highlight_color: Selected tab foreground color.
        highlight_background: Selected tab background color.
        divider: Glyph between tabs; ``None`` uses the ratatui default (``"|"``).
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
    z: int = 0
    visible: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasLine:
    """A straight line drawn on a ``CanvasNode``."""

    x1: float
    y1: float
    x2: float
    y2: float
    color: ColorLike = "white"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPoints:
    """A scatter of points drawn on a ``CanvasNode``."""

    coords: list[tuple[float, float]] = dataclasses.field(default_factory=list)
    color: ColorLike = "white"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasRectangle:
    """An axis-aligned rectangle drawn on a ``CanvasNode``."""

    x: float
    y: float
    width: float
    height: float
    color: ColorLike = "white"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasCircle:
    """A circle drawn on a ``CanvasNode``."""

    x: float
    y: float
    radius: float
    color: ColorLike = "white"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPrint:
    """Text printed at a canvas coordinate on a ``CanvasNode``."""

    x: float
    y: float
    content: str | LineNode | SpanNode = ""


CanvasShape: TypeAlias = (
    CanvasLine | CanvasPoints | CanvasRectangle | CanvasCircle | CanvasPrint
)
"""Union of all shape types accepted by ``CanvasNode``."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasNode(AbstractRenderNode):
    """A free-draw canvas widget.

    Attributes:
        shapes: Drawing commands replayed in order at render time.
        x_bounds: Logical x-axis range ``(min, max)``.
        y_bounds: Logical y-axis range ``(min, max)``.
        background: Canvas background color.
        marker: Glyph set used to paint canvas cells; ``None`` = ratatui default.
    """

    shapes: list[CanvasShape] = dataclasses.field(default_factory=list)
    x_bounds: tuple[float, float] = (0.0, 1.0)
    y_bounds: tuple[float, float] = (0.0, 1.0)
    background: ColorLike | None = None
    marker: CanvasMarkerLike | None = None
    z: int = 0
    visible: bool = True


class NodeAssembler:
    """Assembles ``xnano.beta.core.nodes.AbstractRenderNode`` trees into ratatui
    native widgets through ``xnano-core``.
    """

    @staticmethod
    def _frame_length_overhead(frame: Frame, direction: str) -> int:
        extra = 0
        if frame.border is not None or frame.border_sides is not None:
            extra += 2
        padding = frame.padding
        if padding is not None:
            if isinstance(padding, Padding):
                if direction == "vertical":
                    extra += padding.vertical
                else:
                    extra += padding.horizontal
            elif isinstance(padding, int):
                extra += padding * 2
            elif isinstance(padding, tuple) and len(padding) == 2:
                v, h = padding
                extra += (v * 2) if direction == "vertical" else (h * 2)
            elif isinstance(padding, tuple) and len(padding) == 4:
                top, right, bottom, left = padding  # type: ignore[misc]
                extra += (
                    (int(top or 0) + int(bottom or 0))
                    if direction == "vertical"
                    else (int(left or 0) + int(right or 0))
                )
        return extra

    @classmethod
    def measure_node(cls, node: AbstractRenderNode) -> Size:
        """Measures the size of the content within this node.

        Returns:
            The size of the content within this node.
        """
        if hasattr(node, "visible") and not node.visible:
            return Size(width=0, height=0)

        # Container nodes that recurse must stay in Python.
        if isinstance(node, FrameNode):
            child_size = cls.measure_node(node.child)
            overhead = cls._frame_length_overhead(node.frame, "vertical")
            return Size(
                width=child_size.width + overhead,
                height=child_size.height + overhead,
            )
        if isinstance(node, ContainerNode):
            if not node.children:
                return Size(width=0, height=0)
            sizes = [cls.measure_node(child) for child in node.children]
            if node.direction == "horizontal":
                return Size(
                    width=sum(s.width for s in sizes)
                    + node.gap * (len(sizes) - 1),
                    height=max(s.height for s in sizes),
                )
            return Size(
                width=max(s.width for s in sizes),
                height=sum(s.height for s in sizes)
                + node.gap * (len(sizes) - 1),
            )
        if isinstance(node, StackNode):
            if not node.children:
                return Size(width=0, height=0)
            sizes = [cls.measure_node(child) for child in node.children]
            return Size(
                width=max(s.width for s in sizes),
                height=max(s.height for s in sizes),
            )

        # All leaf nodes: delegate to CoreRenderIR.measure() (pure Rust, no widget build).
        ir = cls._build_leaf_ir(node)
        if ir is not None:
            w, h = ir.measure()
            return Size(width=w, height=h)
        return Size(width=0, height=0)

    # ── IR helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _c(color: "Any") -> "Any":
        from xnano.beta.utils.native_types import (
            get_native_color_from_color_like,
        )

        return get_native_color_from_color_like(color, role="foreground")

    @staticmethod
    def _bg(color: "Any") -> "Any":
        from xnano.beta.utils.native_types import (
            get_native_color_from_color_like,
        )

        return get_native_color_from_color_like(color, role="background")

    @staticmethod
    def _mods(modifiers: "list[Any]") -> "list[Any]":
        from xnano.beta.utils.native_types import _NATIVE_MODIFIER_TYPES

        return (
            [_NATIVE_MODIFIER_TYPES[m] for m in modifiers] if modifiers else []
        )

    @staticmethod
    def _align(alignment: "str | None") -> "int | None":
        if alignment == "left":
            return 0
        if alignment == "center":
            return 1
        if alignment == "right":
            return 2
        return None

    _SCROLLBAR_ORIENT: "dict[str, int]" = {
        "vertical_right": 0,
        "vertical_left": 1,
        "horizontal_bottom": 2,
        "horizontal_top": 3,
    }
    _MARKER_INT: "dict[str, int]" = {
        "dot": 0,
        "block": 1,
        "bar": 2,
        "braille": 3,
        "half_block": 4,
    }

    @classmethod
    def _ir_line(cls, node: "Any") -> "Any":
        """Convert str / SpanNode / LineNode → IrLine (single Rust call)."""
        from xnano_core.core import IrLine

        if isinstance(node, str):
            return IrLine.raw(node)
        if isinstance(node, SpanNode):
            return IrLine.from_spans(
                [
                    (
                        node.content,
                        cls._c(node.color),
                        cls._bg(node.background),
                        cls._mods(node.modifiers),
                    )
                ]
            )
        # LineNode
        fg = cls._c(node.color)
        bg = cls._bg(node.background)
        mods = cls._mods(node.modifiers)
        if isinstance(node.content, str) or node.content is None:
            return IrLine.styled(node.content or "", fg, bg, mods)
        spans = [
            (
                s.content,
                cls._c(s.color),
                cls._bg(s.background),
                cls._mods(s.modifiers),
            )
            for s in node.content
        ]
        return IrLine.from_spans(spans)

    @classmethod
    def _table_widths(
        cls, column_widths: "Any", col_count: int
    ) -> "list[tuple[int, float]]":
        if column_widths is None:
            return [(2, 1.0)] * col_count  # Fill(1) for each column
        result = []
        for w in column_widths:
            if isinstance(w, float):
                result.append((1, w * 100.0))  # Percentage
            else:
                result.append((0, float(w)))  # Length
        return result

    @classmethod
    def _build_leaf_ir(cls, node: "AbstractRenderNode") -> "Any | None":
        """Build a CoreRenderIR for a leaf node; return None for containers."""
        from xnano_core.core import CoreRenderIR, IrLine

        if isinstance(node, ClearNode):
            return CoreRenderIR.clear()

        if isinstance(node, SpanNode):
            return CoreRenderIR.span(
                node.content,
                cls._c(node.color),
                cls._bg(node.background),
                cls._mods(node.modifiers),
            )

        if isinstance(node, LineNode):
            return CoreRenderIR.line(cls._ir_line(node))

        if isinstance(node, TextNode):
            fg = cls._c(node.color)
            bg = cls._bg(node.background)
            mods = cls._mods(list(node.modifiers))
            align = cls._align(node.align)
            if node.lines:
                lines = [cls._ir_line(ln) for ln in node.lines]
                return CoreRenderIR.text_lines(lines, fg, bg, mods, align)
            return CoreRenderIR.text_raw(node.content, fg, bg, mods, align)

        if isinstance(node, ParagraphNode):
            fg = cls._c(node.color)
            bg = cls._bg(node.background)
            mods = cls._mods(list(node.modifiers))
            align = cls._align(node.align)
            text = node.text
            if isinstance(text, str):
                return CoreRenderIR.paragraph_raw(
                    text, fg, bg, mods, align, node.wrap
                )
            if isinstance(text, TextNode):
                if text.lines:
                    lines = [cls._ir_line(ln) for ln in text.lines]
                    return CoreRenderIR.paragraph_lines(
                        lines, fg, bg, mods, align, node.wrap
                    )
                return CoreRenderIR.paragraph_raw(
                    text.content, fg, bg, mods, align, node.wrap
                )
            # LineNode body
            return CoreRenderIR.paragraph_lines(
                [cls._ir_line(text)], fg, bg, mods, align, node.wrap
            )

        if isinstance(node, ListNode):
            ir_items = [cls._ir_line(item) for item in node.items]
            return CoreRenderIR.list(
                ir_items,
                node.selected,
                cls._c(node.color),
                cls._bg(node.background),
                cls._c(node.highlight_color),
                cls._bg(node.highlight_background),
                node.highlight_symbol,
            )

        if isinstance(node, ProgressBarNode):
            return CoreRenderIR.progress_bar(
                node.progress,
                node.label,
                cls._c(node.color),
                cls._bg(node.background),
            )

        if isinstance(node, SparklineNode):
            # Per-bar colors can't be expressed in CoreRenderIR; fall back to native.
            if node.bars is not None:
                return None
            return CoreRenderIR.sparkline(
                node.data,
                node.max_value,
                cls._c(node.color),
                cls._bg(node.background),
                cls._c(node.absent_value_color),
                node.absent_value_symbol,
            )

        if isinstance(node, LineGaugeNode):
            return CoreRenderIR.line_gauge(
                node.progress,
                node.label,
                cls._c(node.color),
                cls._bg(node.background),
                cls._c(node.filled_color),
                cls._c(node.unfilled_color),
            )

        if isinstance(node, BarChartNode):
            groups = []
            for g in node.groups:
                bars = []
                for b in g.bars:
                    bars.append(
                        (
                            b.value,
                            b.label,
                            b.text_value,
                            cls._c(b.color),
                            None,
                            cls._c(b.value_color),
                            None,
                        )
                    )
                groups.append((g.label, bars))
            return CoreRenderIR.bar_chart(
                groups,
                node.bar_width,
                node.bar_gap,
                node.group_gap,
                node.max_value,
                node.direction == "horizontal",
                cls._c(node.color),
                cls._c(node.value_color),
                cls._c(node.label_color),
            )

        if isinstance(node, TableNode):

            def _ir_cell(c: "TableCellItem | str"):
                if isinstance(c, str):
                    return (IrLine.raw(c), None, None, [])
                return (
                    cls._ir_line(
                        c.content
                        if not isinstance(c.content, str)
                        else c.content
                    ),
                    cls._c(c.color),
                    cls._bg(c.background),
                    cls._mods(c.modifiers),
                )

            def _ir_row(r: "TableRowItem"):
                return (
                    [_ir_cell(c) for c in r.cells],
                    cls._c(r.color),
                    cls._bg(r.background),
                    r.height,
                )

            col_count = max((len(r.cells) for r in node.rows), default=1)
            return CoreRenderIR.table(
                [_ir_row(r) for r in node.rows],
                _ir_row(node.header) if node.header is not None else None,
                _ir_row(node.footer) if node.footer is not None else None,
                cls._table_widths(node.column_widths, col_count),
                node.column_spacing,
                node.selected_row,
                node.selected_column,
                cls._c(node.highlight_color),
                cls._bg(node.highlight_background),
                node.highlight_symbol,
            )

        if isinstance(node, ScrollbarNode):
            return CoreRenderIR.scrollbar(
                cls._SCROLLBAR_ORIENT.get(node.orientation, 0),
                node.content_length,
                node.position,
                node.viewport_length,
                cls._c(node.color),
                cls._c(node.thumb_color),
                cls._c(node.track_color),
                node.begin_symbol,
                node.end_symbol,
            )

        if isinstance(node, TabsNode):
            titles = [cls._ir_line(t) for t in node.titles]
            return CoreRenderIR.tabs(
                titles,
                node.selected or 0,
                cls._c(node.color),
                cls._bg(node.background),
                cls._c(node.highlight_color),
                cls._bg(node.highlight_background),
                node.divider,
                node.padding_left,
                node.padding_right,
            )

        if isinstance(node, CanvasNode):
            from xnano.beta.utils.native_types import (
                get_native_color_from_color_like,
            )
            from xnano_core.rust import native as _native

            shapes = []
            for shape in node.shapes:
                if isinstance(shape, CanvasLine):
                    c = (
                        get_native_color_from_color_like(shape.color)
                        or _native.Color.WHITE
                    )
                    shapes.append(
                        ("line", shape.x1, shape.y1, shape.x2, shape.y2, c)
                    )
                elif isinstance(shape, CanvasPoints):
                    c = (
                        get_native_color_from_color_like(shape.color)
                        or _native.Color.WHITE
                    )
                    shapes.append(("points", list(shape.coords), c))
                elif isinstance(shape, CanvasRectangle):
                    c = (
                        get_native_color_from_color_like(shape.color)
                        or _native.Color.WHITE
                    )
                    shapes.append(
                        (
                            "rect",
                            shape.x,
                            shape.y,
                            shape.width,
                            shape.height,
                            c,
                        )
                    )
                elif isinstance(shape, CanvasCircle):
                    c = (
                        get_native_color_from_color_like(shape.color)
                        or _native.Color.WHITE
                    )
                    shapes.append(
                        ("circle", shape.x, shape.y, shape.radius, c)
                    )
                elif isinstance(shape, CanvasPrint):
                    content = shape.content
                    if isinstance(content, str):
                        spans = [(content, None, None, [])]
                    elif isinstance(content, LineNode):
                        if isinstance(content.content, list):
                            spans = [
                                (
                                    s.content,
                                    cls._c(s.color),
                                    cls._bg(s.background),
                                    cls._mods(s.modifiers),
                                )
                                for s in content.content
                            ]
                        else:
                            spans = [
                                (
                                    content.content or "",
                                    cls._c(content.color),
                                    cls._bg(content.background),
                                    cls._mods(content.modifiers),
                                )
                            ]
                    else:  # SpanNode
                        spans = [
                            (
                                content.content,
                                cls._c(content.color),
                                cls._bg(content.background),
                                cls._mods(content.modifiers),
                            )
                        ]
                    shapes.append(("print", shape.x, shape.y, spans))
            return CoreRenderIR.canvas(
                shapes,
                node.x_bounds,
                node.y_bounds,
                cls._bg(node.background),
                cls._MARKER_INT.get(node.marker) if node.marker else None,
            )

        return None

    @classmethod
    def lower_node_to_native(
        cls,
        node: AbstractRenderNode,
        area: Area,
        session: "Session[Any]",
        z: int,
        *,
        effect_key: str | None = None,
    ) -> None:
        from xnano.beta.utils import native_types

        if hasattr(node, "visible") and not node.visible:
            return
        effective_z: int = node.z if (hasattr(node, "z") and node.z) else z  # type: ignore

        native_rect = native_types.get_native_rect_from_area(area)

        # Container nodes must stay Python-side (they call session layout methods).
        if isinstance(node, FrameNode):
            inner_area = session.grid_paint_frame(
                area, node.frame, z=effective_z
            )
            cls.lower_node_to_native(
                node.child, inner_area, session, effective_z
            )
            return

        if isinstance(node, ContainerNode):
            if not node.children:
                return
            from xnano.beta.grid import _GridLayoutConstraint

            constraints = [
                _GridLayoutConstraint(kind="fill", value=1)
                for _ in node.children
            ]
            child_areas = session.grid_split_layout(
                area, node.direction, node.gap, constraints
            )
            for child, child_area in zip(node.children, child_areas):
                cls.lower_node_to_native(
                    child, child_area, session, effective_z
                )
            return

        if isinstance(node, StackNode):
            for child in node.children:
                cls.lower_node_to_native(child, area, session, effective_z)
            return

        # Sparkline with per-bar colors: native path (CoreRenderIR can't express per-bar styles).
        if isinstance(node, SparklineNode) and node.bars is not None:
            from xnano_core.rust import native

            native_bars: list[Any] = []
            for bar in node.bars:
                native_bar = native.SparklineBar.new(bar.value)
                if bar.color is not None:
                    bar_style = native_types.get_native_style_from_kwargs(
                        color=bar.color
                    )
                    if bar_style is not None:
                        native_bar = native_bar.style(bar_style)
                native_bars.append(native_bar)
            spark = native.Sparkline.from_bars(native_bars)
            if node.max_value is not None:
                spark = spark.max(node.max_value)
            if node.color is not None:
                s = native_types.get_native_style_from_kwargs(color=node.color)
                if s is not None:
                    spark = spark.style(s)
            session.render_native(native_rect, spark, z=effective_z)
            return

        # Leaf nodes → single CoreRenderIR construction + enqueue.
        ir = cls._build_leaf_ir(node)
        if ir is not None:
            session.render_ir(
                native_rect, ir, z=effective_z, effect_key=effect_key
            )


RenderNode: TypeAlias = (
    AbstractRenderNode
    | SpanNode
    | LineNode
    | TextNode
    | ParagraphNode
    | ListNode
    | ProgressBarNode
    | ClearNode
    | FrameNode
    | ContainerNode
    | StackNode
    | SparklineNode
    | LineGaugeNode
    | BarChartNode
    | TableNode
    | ScrollbarNode
    | TabsNode
    | CanvasNode
)
"""Collective alias for all render node types."""


__all__ = (
    "AbstractRenderNode",
    "SpanNode",
    "LineNode",
    "TextNode",
    "ParagraphNode",
    "ListNode",
    "ProgressBarNode",
    "ClearNode",
    "FrameNode",
    "ContainerNode",
    "StackNode",
    "SparklineBarItem",
    "SparklineNode",
    "LineGaugeNode",
    "BarChartNode",
    "TableNode",
    "ScrollbarNode",
    "TabsNode",
    "CanvasNode",
    "RenderNode",
    "NodeAssembler",
)
