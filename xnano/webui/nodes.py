"""xnano.webui.nodes

---

Web render nodes that lower component content to HTML fragments.
"""

from __future__ import annotations

import abc
import dataclasses
import html
from typing import ClassVar

from xnano._types import Alignment, CharacterModifier, Direction
from xnano.color import Color, ColorLike
from xnano.tui._node_base_tmp import AbstractNode, NodeKind


def build_style_attrs(
    *,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    modifiers: tuple[CharacterModifier, ...] | None = None,
    align: Alignment | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Build Tailwind classes and inline styles from text styling.

    Args:
        color: Text color to apply.
        background: Background color to apply.
        modifiers: Text modifiers (bold, dim, etc.).
        align: Text alignment.

    Returns:
        A tuple of (tailwind_classes, inline_styles_dict).
    """
    classes: list[str] = []
    styles: dict[str, str] = {}

    # Process color
    if color is not None:
        try:
            parsed_color = Color.parse(color)
            styles["color"] = (
                f"rgb({parsed_color.r}, {parsed_color.g}, {parsed_color.b})"
            )
        except Exception:
            pass

    # Process background
    if background is not None:
        try:
            parsed_bg = Color.parse(background)
            styles["background-color"] = (
                f"rgb({parsed_bg.r}, {parsed_bg.g}, {parsed_bg.b})"
            )
        except Exception:
            pass

    # Process modifiers
    if modifiers:
        for mod in modifiers:
            if mod == "bold":
                classes.append("font-bold")
            elif mod == "dim":
                classes.append("opacity-60")
            elif mod == "italic":
                classes.append("italic")
            elif mod == "underline":
                classes.append("underline")
            elif mod in ("slow_blink", "rapid_blink"):
                classes.append("animate-pulse")
            elif mod == "reversed":
                # Handle reversed: swap color and background-color
                if "color" in styles and "background-color" in styles:
                    styles["color"], styles["background-color"] = (
                        styles["background-color"],
                        styles["color"],
                    )
                elif "color" in styles:
                    styles["background-color"] = styles.pop("color")
                elif "background-color" in styles:
                    styles["color"] = styles.pop("background-color")

    # Process alignment
    if align is not None:
        if align == "left":
            classes.append("text-left")
        elif align == "center":
            classes.append("text-center")
        elif align == "right":
            classes.append("text-right")

    return classes, styles


def _format_attributes(classes: list[str], styles: dict[str, str]) -> str:
    """Format Tailwind classes and inline styles as HTML attributes.

    Args:
        classes: List of Tailwind CSS classes.
        styles: Dictionary of inline style key-value pairs.

    Returns:
        A space-separated string of HTML attributes, or empty string.
    """
    attrs = ""
    if classes:
        class_str = " ".join(classes)
        attrs += f' class="{html.escape(class_str, quote=True)}"'
    if styles:
        style_parts = [
            f"{key}: {html.escape(value, quote=True)}"
            for key, value in styles.items()
        ]
        style_str = "; ".join(style_parts)
        attrs += f' style="{html.escape(style_str, quote=True)}"'
    return attrs


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AbstractWebNode(AbstractNode, abc.ABC):
    """Abstract base for web render nodes.

    A web node renders itself to an HTML string. Layout is handled by
    the browser, unlike terminal nodes which must measure themselves.
    """

    kind: ClassVar[NodeKind] = "web"

    @abc.abstractmethod
    def to_html(self) -> str:
        """Render this node to an HTML string.

        Returns:
            HTML representation of this node.
        """
        ...


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WebSpanNode(AbstractWebNode):
    """A span of styled text.

    Attributes:
        content: The text content of the span.
        color: Optional text color.
        background: Optional background color.
        modifiers: Text modifiers (bold, dim, etc.).
    """

    content: str = ""
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: tuple[CharacterModifier, ...] = ()

    def to_html(self) -> str:
        """Render to an HTML span element."""
        if not self.visible:
            return ""
        classes, styles = build_style_attrs(
            color=self.color,
            background=self.background,
            modifiers=self.modifiers,
        )
        attrs = _format_attributes(classes, styles)
        escaped_content = html.escape(self.content)
        if attrs:
            return f"<span{attrs}>{escaped_content}</span>"
        return escaped_content


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WebParagraphNode(AbstractWebNode):
    """A paragraph of text, optionally with multiple lines.

    Attributes:
        text: Plain text content (used when lines is empty).
        lines: Tuple of lines, each containing tuples of WebSpanNode.
        color: Optional text color.
        background: Optional background color.
        modifiers: Text modifiers.
        align: Horizontal alignment.
        wrap: Whether text should wrap.
    """

    text: str = ""
    lines: tuple[tuple[WebSpanNode, ...], ...] = ()
    color: ColorLike | None = None
    background: ColorLike | None = None
    modifiers: tuple[CharacterModifier, ...] = ()
    align: Alignment | None = None
    wrap: bool = True

    def to_html(self) -> str:
        """Render to an HTML div element."""
        if not self.visible:
            return ""
        classes, styles = build_style_attrs(
            color=self.color,
            background=self.background,
            modifiers=self.modifiers,
            align=self.align,
        )
        wrap_class = "whitespace-pre-wrap" if self.wrap else "whitespace-pre"
        classes.append(wrap_class)
        attrs = _format_attributes(classes, styles)

        inner_html = ""
        if self.lines:
            # Multiple lines: one inner div per line
            line_divs = []
            for line_spans in self.lines:
                if not line_spans:
                    line_divs.append("<div>&nbsp;</div>")
                else:
                    spans_html = "".join(span.to_html() for span in line_spans)
                    line_divs.append(f"<div>{spans_html}</div>")
            inner_html = "\n".join(line_divs)
        else:
            # Plain text: split on newlines
            text_lines = self.text.split("\n")
            if len(text_lines) == 1:
                # Single line: put escaped text directly in outer div
                inner_html = html.escape(text_lines[0]) or "&nbsp;"
            else:
                # Multiple lines: one inner div per line
                line_divs = []
                for line in text_lines:
                    escaped = html.escape(line) or "&nbsp;"
                    line_divs.append(f"<div>{escaped}</div>")
                inner_html = "\n".join(line_divs)

        return f"<div{attrs}>{inner_html}</div>"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WebContainerNode(AbstractWebNode):
    """A flex container for laying out child nodes.

    Attributes:
        direction: Layout direction (vertical or horizontal).
        children: Child nodes.
        gap: Gap between children in quarter-rem units.
    """

    direction: Direction = "vertical"
    children: tuple[AbstractWebNode, ...] = ()
    gap: int = 0

    def to_html(self) -> str:
        """Render to an HTML flex container div."""
        if not self.visible:
            return ""
        classes = [
            "flex",
            "flex-col" if self.direction == "vertical" else "flex-row",
        ]
        styles: dict[str, str] = {}
        if self.gap > 0:
            styles["gap"] = f"{self.gap * 0.25}rem"
        attrs = _format_attributes(classes, styles)
        children_html = "".join(child.to_html() for child in self.children)
        return f"<div{attrs}>{children_html}</div>"


__all__ = (
    "AbstractWebNode",
    "WebSpanNode",
    "WebParagraphNode",
    "WebContainerNode",
    "build_style_attrs",
)
