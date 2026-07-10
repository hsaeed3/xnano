"""xnano.beta.components.text"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from xnano.components.text import Text as BaseText

if TYPE_CHECKING:
    from xnano.beta.nodes.web import AbstractWebNode
    from xnano.components.abstract import ComponentRenderContext


@dataclasses.dataclass
class Text(BaseText):
    """Beta ``Text`` component. This implements the ``get_web_node`` method and
    provides beta web-specific functionality.
    """

    def get_web_node(self, ctx: "ComponentRenderContext") -> (
        "AbstractWebNode | None"
    ):
        """Render this Text to a web node tree.

        Args:
            ctx: The render context.

        Returns:
            A web node representing this Text, or None.
        """
        from xnano.beta.nodes.web import (
            WebParagraphNode,
            WebSpanNode,
        )

        # Leaf: single string
        if isinstance(self.content, str):
            display_text = self.content
            display_color = self.color
            display_modifiers = self.modifiers

            if self.input and self.content == "":
                placeholder_str = self._placeholder_string()
                if placeholder_str is not None:
                    display_text = placeholder_str
                    if display_color is None:
                        display_color = "gray"
                    if not display_modifiers:
                        display_modifiers = ("dim",)

            return WebParagraphNode(
                text=display_text,
                color=display_color,
                background=self.background,
                modifiers=display_modifiers,
                align=self.align,
                wrap=self.wrap,
            )

        # Single nested Text child. The base component's ``get_web_node``
        # returns ``None``, so fall through to building a paragraph from a
        # plain terminal ``Text`` rather than dropping its content.
        if isinstance(self.content, BaseText):
            node = self.content.get_web_node(ctx)
            if node is not None:
                return node
            if isinstance(self.content.content, str):
                return WebParagraphNode(
                    text=self.content.content,
                    color=self.content.color,
                    background=self.content.background,
                    modifiers=self.content.modifiers,
                    align=self.content.align,
                    wrap=self.content.wrap,
                )
            return None

        # List content
        children = self._as_children()
        all_leaves = all(child._is_leaf() for child in children)

        if all_leaves:
            # All children are leaf Text instances: one line of spans
            spans: list[WebSpanNode] = []
            for child in children:
                if isinstance(child.content, str):
                    span = WebSpanNode(
                        content=child.content,
                        color=child.color,
                        background=child.background,
                        modifiers=child.modifiers,
                    )
                    spans.append(span)
            return WebParagraphNode(
                lines=(tuple(spans),),
                color=self.color,
                background=self.background,
                modifiers=self.modifiers,
                align=self.align,
                wrap=self.wrap,
            )

        # Mixed or multi-line: one line per child
        lines: list[tuple[WebSpanNode, ...]] = []
        for child in children:
            if child._is_leaf():
                # Leaf child: single-span line
                if isinstance(child.content, str):
                    span = WebSpanNode(
                        content=child.content,
                        color=child.color,
                        background=child.background,
                        modifiers=child.modifiers,
                    )
                    lines.append((span,))
            else:
                # Non-leaf child: extract leaf grandchildren into spans
                if isinstance(child.content, list):
                    grandchildren = child._as_children()
                    line_spans: list[WebSpanNode] = []
                    for grandchild in grandchildren:
                        if grandchild._is_leaf():
                            if isinstance(grandchild.content, str):
                                span = WebSpanNode(
                                    content=grandchild.content,
                                    color=grandchild.color,
                                    background=grandchild.background,
                                    modifiers=grandchild.modifiers,
                                )
                                line_spans.append(span)
                    if line_spans:
                        lines.append(tuple(line_spans))

        return WebParagraphNode(
            lines=tuple(lines),
            color=self.color,
            background=self.background,
            modifiers=self.modifiers,
            align=self.align,
            wrap=self.wrap,
        )


__all__ = ("Text",)