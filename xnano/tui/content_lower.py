"""xnano.tui.content_lower

---

Lowers interface-neutral ``xnano.core.content`` trees to terminal nodes.
Preserves the existing node ``to_ir`` / ``lower`` fast path: the tui
controller walks Content once, then paints nodes as before.
"""

from __future__ import annotations

from typing import Any

from xnano._types import Frame
from xnano.core.content import (
    AbstractContent,
    CellCanvas,
    CellSpan,
    Clear,
    Items,
    Native,
    Panel,
    Run,
    Stack,
    TextBlock,
)
from xnano.tui.nodes import (
    AbstractTerminalNode,
    ClearNode,
    ContainerNode,
    FrameNode,
    LineNode,
    ListNode,
    ParagraphNode,
    SpanNode,
    TextNode,
)


def lower_content(
    content: AbstractContent | Any,
) -> AbstractTerminalNode | None:
    """Lower a Content tree (or passthrough node) to a terminal node.

    Args:
        content: A Content primitive, or an already-built terminal node.

    Returns:
        An ``AbstractTerminalNode``, or ``None`` when nothing paints.
    """
    if content is None:
        return None
    if isinstance(content, AbstractTerminalNode):
        return content
    if not isinstance(content, AbstractContent):
        return ParagraphNode(text=str(content))

    if not content.visible:
        return None

    if isinstance(content, Native):
        if content.interface_kind not in (None, "tui"):
            return None
        payload = content.payload
        if isinstance(payload, AbstractTerminalNode):
            return payload
        if isinstance(payload, AbstractContent):
            return lower_content(payload)
        return ParagraphNode(text=str(payload))

    if isinstance(content, Run):
        return SpanNode(
            content=content.text,
            color=content.color,
            background=content.background,
            modifiers=list(content.modifiers),
            z=content.z,
            visible=content.visible,
        )

    if isinstance(content, TextBlock):
        return _lower_text_block(content)

    if isinstance(content, CellCanvas):
        return _lower_cell_canvas(content)

    if isinstance(content, Items):
        return _lower_items(content)

    if isinstance(content, Clear):
        return ClearNode(z=content.z, visible=content.visible)

    if isinstance(content, Stack):
        children: list[AbstractTerminalNode] = []
        for child in content.children:
            node = lower_content(child)
            if node is not None:
                children.append(node)
        return ContainerNode(
            children=children,
            direction=content.direction or "vertical",
            gap=content.gap or 0,
            z=content.z,
            visible=content.visible,
        )

    if isinstance(content, Panel):
        child_node = lower_content(content.child)
        if child_node is None:
            child_node = ClearNode()
        style = content.style
        frame = Frame(
            background=(
                content.background
                if content.background is not None
                else (style.background if style else None)
            ),
            border=(
                content.border
                if content.border is not None
                else (style.border if style else None)
            ),
            border_color=(
                content.border_color
                if content.border_color is not None
                else (style.border_color if style else None)
            ),
            border_sides=(
                list(content.border_sides)
                if content.border_sides is not None
                else (
                    list(style.border_sides)
                    if style and style.border_sides is not None
                    else None
                )
            ),
            title=(
                content.title
                if content.title is not None
                else (style.title if style else None)
            ),
            title_position=(
                content.title_position
                if content.title_position is not None
                else (style.title_position if style else None)
            ),
            padding=(
                content.padding
                if content.padding is not None
                else (style.padding if style else None)
            ),
        )
        return FrameNode(
            frame=frame,
            child=child_node,
            z=content.z,
            visible=content.visible,
        )

    # Unsupported Content kinds: string fallback for visibility in tests.
    return ParagraphNode(text=repr(type(content).__name__))


def _lower_text_block(block: TextBlock) -> AbstractTerminalNode:
    if block.lines:
        line_nodes: list[LineNode] = []
        for line in block.lines:
            spans: list[SpanNode] = []
            for run in line:
                if isinstance(run, Run):
                    spans.append(
                        SpanNode(
                            content=run.text,
                            color=run.color,
                            background=run.background,
                            modifiers=list(run.modifiers),
                        )
                    )
                else:
                    spans.append(SpanNode(content=str(run)))
            line_nodes.append(
                LineNode(
                    content=spans,
                    color=block.color,
                    background=block.background,
                    modifiers=list(block.modifiers),
                )
            )
        # One visual line → Paragraph wrapping a LineNode (matches the
        # historical Text leaf-list shape tests and demos expect).
        if len(line_nodes) == 1:
            return ParagraphNode(
                text=line_nodes[0],
                color=block.color,
                background=block.background,
                modifiers=block.modifiers,
                align=block.align,
                wrap=block.wrap,
                z=block.z,
                visible=block.visible,
            )
        text_node = TextNode(
            lines=line_nodes,
            color=block.color,
            background=block.background,
            modifiers=block.modifiers,
            align=block.align,
        )
        return ParagraphNode(
            text=text_node,
            color=block.color,
            background=block.background,
            modifiers=block.modifiers,
            align=block.align,
            wrap=block.wrap,
            z=block.z,
            visible=block.visible,
        )

    return ParagraphNode(
        text=block.text or "",
        color=block.color,
        background=block.background,
        modifiers=block.modifiers,
        align=block.align,
        wrap=block.wrap,
        z=block.z,
        visible=block.visible,
    )


def _lower_items(items: Items) -> AbstractTerminalNode:
    """Lower an Items list to a selectable ``ListNode``."""
    node_items: list[str | LineNode | SpanNode] = []
    for entry in items.items:
        if isinstance(entry, str):
            node_items.append(entry)
        elif isinstance(entry, Run):
            node_items.append(
                SpanNode(
                    content=entry.text,
                    color=entry.color,
                    background=entry.background,
                    modifiers=list(entry.modifiers),
                )
            )
        elif entry.lines:
            # TextBlock entry: first run line becomes the list row.
            node_items.append(
                LineNode(
                    content=[
                        SpanNode(
                            content=run.text,
                            color=run.color,
                            background=run.background,
                            modifiers=list(run.modifiers),
                        )
                        for run in entry.lines[0]
                    ]
                )
            )
        else:
            node_items.append(entry.text)
    return ListNode(
        items=node_items,
        selected=items.selected,
        color=items.color,
        background=items.background,
        highlight_color=items.highlight_color,
        highlight_background=items.highlight_background,
        highlight_symbol=items.highlight_symbol,
        z=items.z,
        visible=items.visible,
    )


def _lower_cell_canvas(canvas: Any) -> AbstractTerminalNode:
    """Lower a CellCanvas to a non-wrapping paragraph of run-length spans."""
    rows = getattr(canvas, "rows", None)
    as_span_rows = getattr(canvas, "as_span_rows", None)
    if rows is None and callable(as_span_rows):
        rows = as_span_rows()
    if not rows:
        # Per-cell storage fallback (Stage paint lattice).
        get_cell = getattr(canvas, "get_cell", None)
        if callable(get_cell):
            lines: list[LineNode] = []
            for y in range(int(getattr(canvas, "height", 0) or 0)):
                spans: list[SpanNode] = []
                current = ""
                current_style: Any = None
                for x in range(int(getattr(canvas, "width", 0) or 0)):
                    glyph, style = get_cell(x, y)
                    if current and style != current_style:
                        spans.append(
                            _span_from_cell_run(current, current_style)
                        )
                        current = ""
                    current += glyph
                    current_style = style
                if current:
                    spans.append(_span_from_cell_run(current, current_style))
                lines.append(LineNode(content=spans or [SpanNode(content="")]))
            return ParagraphNode(
                text=TextNode(lines=lines),
                wrap=False,
                z=getattr(canvas, "z", 0),
                visible=getattr(canvas, "visible", True),
            )
        return ParagraphNode(text="", wrap=False)

    line_nodes: list[LineNode] = []
    for row in rows:
        spans: list[SpanNode] = []
        for span in row:
            if isinstance(span, CellSpan):
                spans.append(
                    SpanNode(
                        content=span.text,
                        color=getattr(span, "color", None),
                        background=getattr(span, "background", None),
                        modifiers=list(getattr(span, "modifiers", ()) or ()),
                    )
                )
            else:
                spans.append(SpanNode(content=str(span)))
        line_nodes.append(LineNode(content=spans or [SpanNode(content="")]))
    return ParagraphNode(
        text=TextNode(lines=line_nodes),
        wrap=False,
        z=canvas.z,
        visible=canvas.visible,
    )


def _span_from_cell_run(text: str, style: Any) -> SpanNode:
    if style is None:
        return SpanNode(content=text)
    if isinstance(style, dict):
        return SpanNode(
            content=text,
            color=style.get("color"),
            background=style.get("background"),
            modifiers=list(style.get("modifiers") or ()),
        )
    return SpanNode(
        content=text,
        color=getattr(style, "color", None),
        background=getattr(style, "background", None),
        modifiers=list(getattr(style, "modifiers", ()) or ()),
    )


__all__ = ("lower_content",)
