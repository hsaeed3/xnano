"""xnano.beta.core.nodes"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any, TypeAlias, Union, TYPE_CHECKING

from xnano.beta.types import (
    Area,
    Alignment,
    Direction,
    CharacterModifier,
    Size,
    Padding,
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

        if isinstance(node, TextNode):
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
)
"""Collective alias for all render node types."""
