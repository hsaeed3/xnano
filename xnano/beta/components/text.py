"""xnano.beta.components.text"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from xnano.beta.components.abstract import AbstractComponent
from xnano.beta.types import Alignment, CharacterModifier

if TYPE_CHECKING:
    from xnano.beta.color import ColorLike
    from xnano.beta.components.abstract import ComponentRenderContext
    from xnano.beta.core.nodes import AbstractRenderNode


@dataclasses.dataclass
class Text(AbstractComponent):
    """Unified text component that adapts its render node based on structure.

    Three usage modes, all through one class:

    **Leaf** — a single styled string (renders as ``SpanNode`` when nested,
    ``ParagraphNode`` at top level)::

        Text("hello world", color="red", modifiers=("bold",))

    **Line** — inline spans composed via a list of ``Text`` children where
    every child is itself a leaf (renders as ``LineNode``)::

        Text([Text("Hello ", color="cyan"), Text("world", color="red")])

    **Paragraph** — multiple lines composed via a list of ``Text`` children
    where at least one child is itself a line (renders as ``ParagraphNode``
    wrapping a ``TextNode``)::

        Text([
            Text([Text("Hello ", color="cyan"), Text("world")]),
            Text("Second line", color="blue"),
        ])

    All modes share the same styling params: ``color``, ``background``,
    ``modifiers``.  ``align`` and ``wrap`` apply at the paragraph level.
    """

    content: str | Text | list[str | Text] = dataclasses.field(default="")
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: tuple[CharacterModifier, ...] = ()
    align: Alignment | None = None
    wrap: bool = True

    def _is_leaf(self) -> bool:
        """True when this node holds a plain string (no nested Text children)."""
        return isinstance(self.content, str)

    def _as_children(self) -> list[Text]:
        """Normalize content to a flat list of Text children."""
        if isinstance(self.content, str):
            return [self]
        if isinstance(self.content, Text):
            return [self.content]
        result: list[Text] = []
        for item in self.content:
            if isinstance(item, str):
                result.append(Text(item))
            else:
                result.append(item)
        return result

    def _to_span_node(self) -> AbstractRenderNode:
        from xnano.beta.core.nodes import SpanNode

        if isinstance(self.content, str):
            text_str = self.content
        elif isinstance(self.content, Text):
            text_str = (
                self.content.content
                if isinstance(self.content.content, str)
                else ""
            )
        else:
            text_str = ""
        return SpanNode(
            content=text_str,
            color=self.color,
            background=self.background,
            modifiers=list(self.modifiers),
        )

    def _to_line_node(self, ctx: ComponentRenderContext) -> AbstractRenderNode:
        from xnano.beta.core.nodes import LineNode, SpanNode

        if isinstance(self.content, str):
            return LineNode(
                content=self.content,
                color=self.color,
                background=self.background,
                modifiers=list(self.modifiers),
            )
        children = self._as_children()
        spans: list[SpanNode] = []
        for child in children:
            node = child._to_span_node()
            if isinstance(node, SpanNode):
                spans.append(node)
        return LineNode(
            content=spans,
            color=self.color,
            background=self.background,
            modifiers=list(self.modifiers),
        )

    def get_node(self, ctx: ComponentRenderContext) -> AbstractRenderNode:
        from xnano.beta.core.nodes import (
            LineNode,
            ParagraphNode,
            SpanNode,
            TextNode,
        )

        # Leaf: single string — paragraph wrapping plain text
        if isinstance(self.content, str):
            return ParagraphNode(
                text=self.content,
                color=self.color,
                background=self.background,
                modifiers=self.modifiers,
                align=self.align,
                wrap=self.wrap,
            )

        # Single nested Text — delegate
        if isinstance(self.content, Text):
            return self.content.get_node(ctx)

        # List variant: normalise to Text children
        children = self._as_children()
        all_leaves = all(child._is_leaf() for child in children)

        if all_leaves:
            # All children are plain strings → one line of spans
            spans: list[SpanNode] = []
            for child in children:
                node = child._to_span_node()
                if isinstance(node, SpanNode):
                    spans.append(node)
            line = LineNode(
                content=spans,
                color=self.color,
                background=self.background,
                modifiers=list(self.modifiers),
            )
            return ParagraphNode(
                text=line,
                color=self.color,
                background=self.background,
                modifiers=self.modifiers,
                align=self.align,
                wrap=self.wrap,
            )

        # Mixed or multi-line: each child is a line
        line_nodes: list[LineNode] = []
        for child in children:
            node = child._to_line_node(ctx)
            if isinstance(node, LineNode):
                line_nodes.append(node)
        text_node = TextNode(
            lines=line_nodes,
            color=self.color,
            background=self.background,
            modifiers=self.modifiers,
            align=self.align,
        )
        return ParagraphNode(
            text=text_node,
            color=self.color,
            background=self.background,
            modifiers=self.modifiers,
            align=self.align,
            wrap=self.wrap,
        )


__all__ = ("Text",)
