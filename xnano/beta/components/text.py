"""xnano.beta.components.text"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from xnano.beta.components.abstract import AbstractComponent
from xnano.beta.types import Alignment, CharacterModifier

if TYPE_CHECKING:
    from xnano.beta.color import ColorLike
    from xnano.beta.components.abstract import ComponentRenderContext
    from xnano.beta.core.nodes import AbstractRenderNode, LineNode
    from xnano.beta.events import KeyboardEventData


@dataclasses.dataclass
class Text(AbstractComponent):
    """Unified text component that adapts its render node based on structure.

    Three usage modes, all through one class:

    **Leaf** — a single styled string (renders as ``SpanNode`` when nested,
    ``ParagraphNode`` at top level):

        Text("hello world", color="red", modifiers=("bold",))

    **Line** — inline spans composed via a list of ``Text`` children where
    every child is itself a leaf (renders as ``LineNode``):

        Text([Text("Hello ", color="cyan"), Text("world", color="red")])

    **Paragraph** — multiple lines composed via a list of ``Text`` children
    where at least one child is itself a line (renders as ``ParagraphNode``
    wrapping a ``TextNode``):

        Text([
            Text([Text("Hello ", color="cyan"), Text("world")]),
            Text("Second line", color="blue"),
        ])

    **Input** — set ``input=True`` on a leaf ``Text`` placed in a grid field
    to make it focusable and editable (tab order, caret, placeholder):

        class Form(Grid):
            name: Text = Field(
                default=Text("", input=True, placeholder="your name"),
            )

    All modes share the same styling params: ``color``, ``background``,
    ``modifiers``.  ``align`` and ``wrap`` apply at the paragraph level.
    """

    content: str | Text | list[str | Text] = dataclasses.field(default="")
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: tuple[CharacterModifier, ...] = ()
    align: Alignment | None = None
    wrap: bool = True
    input: bool = False
    """When ``True`` on a leaf ``Text``, the component is an editable field
    that participates in field focus (tab order) and receives keyboard input
    while focused."""
    placeholder: str | Text | None = None
    """Shown when ``input`` is enabled, the content is empty, and the field
    is not focused.  A string is rendered dim; a ``Text`` keeps its styling."""
    cursor: int | None = None
    """Caret index into ``content`` when ``input`` is enabled; ``None`` means
    the end of the string."""
    _input_focused: bool = dataclasses.field(
        default=False, init=False, repr=False, compare=False
    )

    def _is_leaf(self) -> bool:
        """True when this node holds a plain string (no nested Text children)."""
        return isinstance(self.content, str)

    @property
    def value(self) -> str:
        """Plain-string content for leaf ``Text``; empty string otherwise."""
        if isinstance(self.content, str):
            return self.content
        return ""

    @value.setter
    def value(self, text: str) -> None:
        self.content = text
        if self.cursor is not None:
            self.cursor = max(0, min(self.cursor, len(text)))

    def handle_keyboard(self, keyboard: KeyboardEventData) -> bool:
        """Apply a keyboard event when this is an editable input.

        Args:
            keyboard: The keyboard sub-event to apply.

        Returns:
            ``True`` when the event was consumed by this input.
        """
        from xnano.beta.focus import apply_text_keyboard

        return apply_text_keyboard(self, keyboard)

    def _placeholder_string(self) -> str | None:
        if self.placeholder is None:
            return None
        if isinstance(self.placeholder, str):
            return self.placeholder
        if isinstance(self.placeholder, Text) and isinstance(
            self.placeholder.content, str
        ):
            return self.placeholder.content
        return None

    def _input_display_content(self) -> tuple[str, ColorLike | None, bool]:
        """Return ``(text, color_override, is_placeholder)`` for input mode."""
        if not isinstance(self.content, str):
            return ("", None, False)
        if (
            self.content == ""
            and not self._input_focused
            and self.placeholder is not None
        ):
            if isinstance(self.placeholder, Text):
                if isinstance(self.placeholder.content, str):
                    return (
                        self.placeholder.content,
                        self.placeholder.color or "gray",
                        True,
                    )
            else:
                return (self.placeholder, "gray", True)
        if self._input_focused and self.input:
            position = (
                self.cursor if self.cursor is not None else len(self.content)
            )
            position = max(0, min(position, len(self.content)))
            # Visible caret between characters (hardware cursor is also moved).
            return (
                self.content[:position] + "▌" + self.content[position:],
                None,
                False,
            )
        return (self.content, None, False)

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

    def _leaf_children_have_embedded_newlines(
        self,
        children: list[Text],
    ) -> bool:
        """Return whether any leaf child contains embedded newlines."""
        for child in children:
            if isinstance(child.content, str) and "\n" in child.content:
                return True
        return False

    def _build_line_nodes_from_leaf_children(
        self,
        children: list[Text],
    ) -> list[LineNode]:
        """Expand leaf children into one line node per text row."""
        from xnano.beta.core.nodes import LineNode

        line_nodes: list[LineNode] = []
        for child in children:
            if not isinstance(child.content, str):
                continue
            for segment in child.content.split("\n"):
                line_nodes.append(
                    LineNode(
                        content=segment,
                        color=child.color,
                        background=child.background,
                        modifiers=list(child.modifiers),
                    )
                )
        return line_nodes

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
            text_str = self.content
            color = self.color
            modifiers = self.modifiers
            if self.input:
                text_str, color_override, is_placeholder = (
                    self._input_display_content()
                )
                if color_override is not None:
                    color = color_override
                if is_placeholder and not modifiers:
                    modifiers = ("dim",)
            return ParagraphNode(
                text=text_str,
                color=color,
                background=self.background,
                modifiers=modifiers,
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
            if self._leaf_children_have_embedded_newlines(children):
                text_node = TextNode(
                    lines=self._build_line_nodes_from_leaf_children(children),
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

            # All children are plain strings on one row → inline spans
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
