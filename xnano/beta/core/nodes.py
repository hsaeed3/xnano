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
class SparklineNode(AbstractRenderNode):
    """A sparkline (mini bar chart) widget.

    Attributes:
        data: Sequence of non-negative sample values.
        max_value: Explicit y-axis ceiling; ``None`` = auto-scale.
        color: Bar foreground color.
        background: Widget background color.
        absent_value_color: Color applied to zero/absent samples.
        absent_value_symbol: Glyph for absent samples (default ``""``).
    """

    data: list[int] = dataclasses.field(default_factory=list)
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
    """A single bar in a :class:`BarChartNode` group.

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
    """A group of bars in a :class:`BarChartNode`.

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
    """A single cell in a :class:`TableRowItem`.

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
    """A row in a :class:`TableNode`.

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
    """A straight line drawn on a :class:`CanvasNode`."""

    x1: float
    y1: float
    x2: float
    y2: float
    color: ColorLike = "white"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPoints:
    """A scatter of points drawn on a :class:`CanvasNode`."""

    coords: list[tuple[float, float]] = dataclasses.field(default_factory=list)
    color: ColorLike = "white"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasRectangle:
    """An axis-aligned rectangle drawn on a :class:`CanvasNode`."""

    x: float
    y: float
    width: float
    height: float
    color: ColorLike = "white"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasCircle:
    """A circle drawn on a :class:`CanvasNode`."""

    x: float
    y: float
    radius: float
    color: ColorLike = "white"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPrint:
    """Text printed at a canvas coordinate on a :class:`CanvasNode`."""

    x: float
    y: float
    content: str | LineNode | SpanNode = ""


CanvasShape: TypeAlias = (
    CanvasLine | CanvasPoints | CanvasRectangle | CanvasCircle | CanvasPrint
)
"""Union of all shape types accepted by :class:`CanvasNode`."""


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

    @staticmethod
    def _measure_paragraph_body(text: "str | TextNode | LineNode") -> Size:
        if isinstance(text, str):
            if not text:
                return Size(width=0, height=1)
            lines = text.split("\n")
            return Size(
                width=max(len(line) for line in lines),
                height=len(lines),
            )
        if isinstance(text, TextNode):
            return text.get_size()
        return Size(width=text.get_width(), height=1)

    @classmethod
    def measure_node(cls, node: AbstractRenderNode) -> Size:
        """Measures the size of the content within this node.

        Returns:
            The size of the content within this node.
        """
        if hasattr(node, "visible") and not node.visible:
            return Size(width=0, height=0)

        if isinstance(node, SpanNode):
            return Size(width=len(node.content), height=1)
        elif isinstance(node, LineNode):
            return Size(width=node.get_width(), height=1)
        elif isinstance(node, TextNode):
            return node.get_size()
        elif isinstance(node, ParagraphNode):
            return cls._measure_paragraph_body(node.text)
        elif isinstance(node, ListNode):
            if not node.items:
                return Size(width=0, height=1)
            symbol_width = len(node.highlight_symbol)
            widths: list[int] = []
            for item in node.items:
                if isinstance(item, LineNode):
                    widths.append(item.get_width())
                elif isinstance(item, SpanNode):
                    widths.append(len(item.content))
                else:
                    widths.append(len(item))
            return Size(
                width=max(widths) + symbol_width,
                height=len(node.items),
            )
        elif isinstance(node, ProgressBarNode):
            return Size(width=0, height=1)
        elif isinstance(node, ClearNode):
            return Size(width=0, height=0)
        elif isinstance(node, FrameNode):
            child_size = cls.measure_node(node.child)
            overhead = cls._frame_length_overhead(node.frame, "vertical")
            return Size(
                width=child_size.width + overhead,
                height=child_size.height + overhead,
            )
        elif isinstance(node, ContainerNode):
            if not node.children:
                return Size(width=0, height=0)
            sizes = [cls.measure_node(child) for child in node.children]
            if node.direction == "horizontal":
                return Size(
                    width=sum(size.width for size in sizes)
                    + node.gap * (len(sizes) - 1),
                    height=max(size.height for size in sizes),
                )
            else:
                return Size(
                    width=max(size.width for size in sizes),
                    height=sum(size.height for size in sizes)
                    + node.gap * (len(sizes) - 1),
                )
        elif isinstance(node, StackNode):
            if not node.children:
                return Size(width=0, height=0)
            sizes = [cls.measure_node(child) for child in node.children]
            return Size(
                width=max(size.width for size in sizes),
                height=max(size.height for size in sizes),
            )

        elif isinstance(node, SparklineNode):
            return Size(width=0, height=1)

        elif isinstance(node, LineGaugeNode):
            return Size(width=0, height=1)

        elif isinstance(node, BarChartNode):
            return Size(width=0, height=0)

        elif isinstance(node, TableNode):
            row_count = len(node.rows)
            if node.header is not None:
                row_count += 1
            if node.footer is not None:
                row_count += 1
            return Size(width=0, height=row_count)

        elif isinstance(node, ScrollbarNode):
            if node.orientation in ("horizontal_bottom", "horizontal_top"):
                return Size(width=0, height=1)
            return Size(width=1, height=0)

        elif isinstance(node, TabsNode):
            return Size(width=0, height=1)

        elif isinstance(node, CanvasNode):
            return Size(width=0, height=0)

        else:
            return Size(width=0, height=0)

    @classmethod
    def lower_node_to_native(
        cls,
        node: AbstractRenderNode,
        area: Area,
        session: "Session[Any]",
        z: int,
    ) -> None:
        from xnano_core.rust import native
        from xnano.beta.utils import native_types

        if hasattr(node, "visible") and not node.visible:
            return
        effective_z: int = node.z if (hasattr(node, "z") and node.z) else z  # type: ignore

        native_rect = native_types.get_native_rect_from_area(area)

        if isinstance(node, ClearNode):
            session.render_native(native_rect, native.Clear(), z=effective_z)
            return

        if isinstance(node, SpanNode):
            native_span = native_types.get_native_span_from_span_node(node)
            native_line = native.Line.from_spans([native_span])
            native_text = native.Text.from_lines([native_line])
            paragraph = native.Paragraph.new(native_text)
            session.render_native(native_rect, paragraph, z=effective_z)
            return

        if isinstance(node, LineNode):
            native_line = native_types.get_native_line_from_line_node(node)
            native_text = native.Text.from_lines([native_line])
            paragraph = native.Paragraph.new(native_text)
            session.render_native(native_rect, paragraph, z=effective_z)
            return

        if isinstance(node, TextNode):
            native_text = native_types.get_native_text_from_text_node(node)
            paragraph = native.Paragraph.new(native_text)
            style = native_types.get_native_style_from_kwargs(
                color=node.color,
                background=node.background,
                modifiers=list(node.modifiers),
            )
            if style is not None:
                paragraph = paragraph.style(style)
            session.render_native(native_rect, paragraph, z=effective_z)
            return

        if isinstance(node, ParagraphNode):
            text = node.text
            if isinstance(text, str):
                native_text = native.Text.raw(text)
            elif isinstance(text, TextNode):
                native_text = native_types.get_native_text_from_text_node(text)
            else:
                native_line = native_types.get_native_line_from_line_node(text)
                native_text = native.Text.from_lines([native_line])
            paragraph = native.Paragraph.new(native_text)
            if node.wrap:
                paragraph = paragraph.wrap(native.Wrap(True))
            if node.align is not None:
                paragraph = paragraph.alignment(
                    native_types._NATIVE_ALIGNMENT_TYPES[node.align]
                )
            style = native_types.get_native_style_from_kwargs(
                color=node.color,
                background=node.background,
                modifiers=list(node.modifiers),
            )
            if style is not None:
                paragraph = paragraph.style(style)
            session.render_native(native_rect, paragraph, z=effective_z)
            return

        if isinstance(node, ListNode):
            items: list[Any] = []
            for item in node.items:
                if isinstance(item, LineNode):
                    native_line = native_types.get_native_line_from_line_node(
                        item
                    )
                    items.append(
                        native.ListItem.new(
                            native.Text.from_lines([native_line])
                        )
                    )
                elif isinstance(item, SpanNode):
                    native_span = native_types.get_native_span_from_span_node(
                        item
                    )
                    items.append(
                        native.ListItem.new(
                            native.Text.from_lines(
                                [native.Line.from_spans([native_span])]
                            )
                        )
                    )
                else:
                    items.append(
                        native.ListItem.new(native.Text.raw(str(item)))
                    )
            rat_list = native.RatList.new(items)
            highlight_style = native_types.get_native_style_from_kwargs(
                color=node.highlight_color,
                background=node.highlight_background,
            )
            if highlight_style is not None:
                rat_list = rat_list.highlight_style(highlight_style)
            rat_list = rat_list.highlight_symbol(node.highlight_symbol)
            if node.selected is not None:
                list_state = native.ListState()
                list_state.select(node.selected)
                session.render_native_with_state(
                    native_rect, rat_list, list_state, z=effective_z
                )
            else:
                session.render_native(native_rect, rat_list, z=effective_z)
            return

        if isinstance(node, ProgressBarNode):
            gauge = native.Gauge.default()
            clamped = max(0.0, min(1.0, node.progress))
            gauge = gauge.ratio(clamped)
            if node.label is not None:
                gauge = gauge.label(node.label)
            style = native_types.get_native_style_from_kwargs(
                color=node.color, background=node.background
            )
            if style is not None:
                gauge = gauge.style(style)
            session.render_native(native_rect, gauge, z=effective_z)
            return

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
            from xnano.beta.utils.native_types import _NATIVE_DIRECTION_TYPES

            constraints: list[Any] = []
            for child in node.children:
                child_size = cls.measure_node(child)
                from xnano.beta.grid import _GridLayoutConstraint

                constraints.append(_GridLayoutConstraint(kind="fill", value=1))
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

        if isinstance(node, SparklineNode):
            spark = native.Sparkline.new(node.data)
            if node.max_value is not None:
                spark = spark.max(node.max_value)
            style = native_types.get_native_style_from_kwargs(
                color=node.color, background=node.background
            )
            if style is not None:
                spark = spark.style(style)
            if node.absent_value_color is not None:
                av_style = native_types.get_native_style_from_kwargs(
                    color=node.absent_value_color
                )
                if av_style is not None:
                    spark = spark.absent_value_style(av_style)
            if node.absent_value_symbol is not None:
                spark = spark.absent_value_symbol(node.absent_value_symbol)
            session.render_native(native_rect, spark, z=effective_z)
            return

        if isinstance(node, LineGaugeNode):
            lg = native.LineGauge.new().ratio(
                max(0.0, min(1.0, node.progress))
            )
            if node.label is not None:
                lg = lg.label(node.label)
            style = native_types.get_native_style_from_kwargs(
                color=node.color, background=node.background
            )
            if style is not None:
                lg = lg.style(style)
            if node.filled_color is not None:
                fs = native_types.get_native_style_from_kwargs(
                    color=node.filled_color
                )
                if fs is not None:
                    lg = lg.filled_style(fs)
            if node.unfilled_color is not None:
                us = native_types.get_native_style_from_kwargs(
                    color=node.unfilled_color
                )
                if us is not None:
                    lg = lg.unfilled_style(us)
            session.render_native(native_rect, lg, z=effective_z)
            return

        if isinstance(node, BarChartNode):
            native_groups: list[Any] = []
            for g in node.groups:
                native_bars: list[Any] = []
                for b in g.bars:
                    nb = native.Bar.new(b.value, b.label)
                    if b.text_value is not None:
                        nb = nb.text_value(b.text_value)
                    if b.color is not None:
                        s = native_types.get_native_style_from_kwargs(
                            color=b.color
                        )
                        if s is not None:
                            nb = nb.style(s)
                    if b.value_color is not None:
                        vs = native_types.get_native_style_from_kwargs(
                            color=b.value_color
                        )
                        if vs is not None:
                            nb = nb.value_style(vs)
                    native_bars.append(nb)
                native_groups.append(native.BarGroup.new(native_bars))
            chart = native.BarChart.new(native_groups)
            chart = (
                chart.bar_width(node.bar_width)
                .bar_gap(node.bar_gap)
                .group_gap(node.group_gap)
            )
            if node.max_value is not None:
                chart = chart.max(node.max_value)
            from xnano.beta.utils.native_types import (
                _NATIVE_DIRECTION_TYPES as _DIR,
            )

            chart = chart.direction(_DIR[node.direction])
            if node.color is not None:
                s = native_types.get_native_style_from_kwargs(color=node.color)
                if s is not None:
                    chart = chart.bar_style(s)
            if node.value_color is not None:
                vs = native_types.get_native_style_from_kwargs(
                    color=node.value_color
                )
                if vs is not None:
                    chart = chart.value_style(vs)
            if node.label_color is not None:
                ls = native_types.get_native_style_from_kwargs(
                    color=node.label_color
                )
                if ls is not None:
                    chart = chart.label_style(ls)
            session.render_native(native_rect, chart, z=effective_z)
            return

        if isinstance(node, TableNode):
            from xnano.beta.utils.native_types import (
                get_native_table_constraints,
            )

            def _cell_to_native(c: "TableCellItem | str") -> Any:
                if isinstance(c, str):
                    return native.Cell.new(native.Text.raw(c))
                content = c.content
                if isinstance(content, str):
                    cell_text: Any = native.Text.raw(content)
                elif isinstance(content, LineNode):
                    cell_text = native.Text.from_lines(
                        [native_types.get_native_line_from_line_node(content)]
                    )
                else:
                    cell_text = native.Text.from_lines(
                        [
                            native.Line.from_spans(
                                [
                                    native_types.get_native_span_from_span_node(
                                        content
                                    )
                                ]
                            )
                        ]
                    )
                cell = native.Cell.new(cell_text)
                style = native_types.get_native_style_from_kwargs(
                    color=c.color,
                    background=c.background,
                    modifiers=c.modifiers,
                )
                if style is not None:
                    cell = cell.style(style)
                return cell

            def _row_to_native(r: "TableRowItem") -> Any:
                native_cells = [_cell_to_native(c) for c in r.cells]
                row = native.Row.new(native_cells)
                if r.height != 1:
                    row = row.height(r.height)
                style = native_types.get_native_style_from_kwargs(
                    color=r.color, background=r.background
                )
                if style is not None:
                    row = row.style(style)
                return row

            native_rows = [_row_to_native(r) for r in node.rows]
            col_count = max((len(r.cells) for r in node.rows), default=1)
            constraints = get_native_table_constraints(
                node.column_widths, col_count
            )
            rat_table = native.RatTable.new(native_rows, constraints)
            rat_table = rat_table.column_spacing(node.column_spacing)
            if node.header is not None:
                rat_table = rat_table.header(_row_to_native(node.header))
            if node.footer is not None:
                rat_table = rat_table.footer(_row_to_native(node.footer))
            if node.highlight_symbol is not None:
                rat_table = rat_table.highlight_symbol(node.highlight_symbol)
            if (
                node.highlight_color is not None
                or node.highlight_background is not None
            ):
                hl = native_types.get_native_style_from_kwargs(
                    color=node.highlight_color,
                    background=node.highlight_background,
                )
                if hl is not None:
                    rat_table = rat_table.row_highlight_style(hl)

            if (
                node.selected_row is not None
                or node.selected_column is not None
            ):
                table_state = native.TableState()
                if node.selected_row is not None:
                    table_state.select(node.selected_row)
                if node.selected_column is not None:
                    table_state.select_column(node.selected_column)
                session.render_native_with_state(
                    native_rect, rat_table, table_state, z=effective_z
                )
            else:
                session.render_native(native_rect, rat_table, z=effective_z)
            return

        if isinstance(node, ScrollbarNode):
            from xnano.beta.utils.native_types import (
                _NATIVE_SCROLLBAR_ORIENTATION_TYPES,
            )

            sb = native.Scrollbar.new(
                _NATIVE_SCROLLBAR_ORIENTATION_TYPES[node.orientation]
            )
            sb = sb.begin_symbol(node.begin_symbol)
            sb = sb.end_symbol(node.end_symbol)
            if node.color is not None:
                s = native_types.get_native_style_from_kwargs(color=node.color)
                if s is not None:
                    sb = sb.style(s)
            if node.thumb_color is not None:
                ts = native_types.get_native_style_from_kwargs(
                    color=node.thumb_color
                )
                if ts is not None:
                    sb = sb.thumb_style(ts)
            if node.track_color is not None:
                trs = native_types.get_native_style_from_kwargs(
                    color=node.track_color
                )
                if trs is not None:
                    sb = sb.track_style(trs)
            state = native.ScrollbarState(node.content_length)
            state.set_position(node.position)
            if node.viewport_length is not None:
                state = state.viewport_content_length(node.viewport_length)
            session.render_native_with_state(
                native_rect, sb, state, z=effective_z
            )
            return

        if isinstance(node, TabsNode):
            from xnano.beta.utils.native_types import (
                get_native_line_from_line_node,
                get_native_span_from_span_node,
            )

            def _title_to_native_line(t: "str | LineNode | SpanNode") -> Any:
                if isinstance(t, str):
                    return native.Line.raw(t)
                if isinstance(t, LineNode):
                    return get_native_line_from_line_node(t)
                return native.Line.from_spans(
                    [get_native_span_from_span_node(t)]
                )

            native_titles = [_title_to_native_line(t) for t in node.titles]
            tabs = native.Tabs.new(native_titles)
            if node.selected is not None:
                tabs = tabs.select(node.selected)
            if node.divider is not None:
                tabs = tabs.divider(node.divider)
            tabs = tabs.padding_left(node.padding_left).padding_right(
                node.padding_right
            )
            style = native_types.get_native_style_from_kwargs(
                color=node.color, background=node.background
            )
            if style is not None:
                tabs = tabs.style(style)
            hl = native_types.get_native_style_from_kwargs(
                color=node.highlight_color,
                background=node.highlight_background,
            )
            if hl is not None:
                tabs = tabs.highlight_style(hl)
            session.render_native(native_rect, tabs, z=effective_z)
            return

        if isinstance(node, CanvasNode):
            from xnano.beta.utils.native_types import (
                _NATIVE_MARKER_TYPES,
                get_native_color_from_color_like,
                get_native_line_from_line_node,
                get_native_span_from_span_node,
            )

            canvas = native.Canvas.default()
            canvas = canvas.x_bounds(node.x_bounds).y_bounds(node.y_bounds)
            if node.background is not None:
                bg = get_native_color_from_color_like(node.background)
                if bg is not None:
                    canvas = canvas.background_color(bg)
            if node.marker is not None:
                canvas = canvas.marker(_NATIVE_MARKER_TYPES[node.marker])
            for shape in node.shapes:
                if isinstance(shape, CanvasLine):
                    c = (
                        get_native_color_from_color_like(shape.color)
                        or native.Color.WHITE
                    )
                    canvas = canvas.line(
                        shape.x1, shape.y1, shape.x2, shape.y2, c
                    )
                elif isinstance(shape, CanvasPoints):
                    c = (
                        get_native_color_from_color_like(shape.color)
                        or native.Color.WHITE
                    )
                    canvas = canvas.points(shape.coords, c)
                elif isinstance(shape, CanvasRectangle):
                    c = (
                        get_native_color_from_color_like(shape.color)
                        or native.Color.WHITE
                    )
                    canvas = canvas.rectangle(
                        shape.x, shape.y, shape.width, shape.height, c
                    )
                elif isinstance(shape, CanvasCircle):
                    c = (
                        get_native_color_from_color_like(shape.color)
                        or native.Color.WHITE
                    )
                    canvas = canvas.circle(shape.x, shape.y, shape.radius, c)
                elif isinstance(shape, CanvasPrint):
                    content = shape.content
                    if isinstance(content, str):
                        print_text: Any = native.Text.raw(content)
                    elif isinstance(content, LineNode):
                        print_text = native.Text.from_lines(
                            [get_native_line_from_line_node(content)]
                        )
                    else:
                        print_text = native.Text.from_lines(
                            [
                                native.Line.from_spans(
                                    [get_native_span_from_span_node(content)]
                                )
                            ]
                        )
                    canvas = canvas.print(shape.x, shape.y, print_text)
            session.render_native(native_rect, canvas, z=effective_z)
            return


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
