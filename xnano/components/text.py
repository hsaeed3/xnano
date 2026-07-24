"""xnano.components.text

---

``Text`` component for styled strings, inline spans, paragraphs, and
editable input fields.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Sequence

from xnano._types import Alignment, CharacterModifier
from xnano.components.abstract import AbstractComponent

if TYPE_CHECKING:
    from xnano.color import ColorLike
    from xnano.components.abstract import ComponentRenderContext
    from xnano.events import KeyboardEventData
    from xnano.terminal.nodes import AbstractTerminalNode, LineNode


@dataclasses.dataclass
class Text(AbstractComponent):
    """Unified text component that adapts its render node based on structure.

    Structural modes, all through one class:

    **Leaf** — a single styled string (renders as
    [`SpanNode`](../terminal/nodes.md#xnano.terminal.nodes.SpanNode){data-preview}
    when nested,
    [`ParagraphNode`](../terminal/nodes.md#xnano.terminal.nodes.ParagraphNode){data-preview}
    at top level):

        Text("hello world", color="red", modifiers=("bold",))

    **Line** — inline spans composed via a list of ``Text`` children where
    every child is itself a leaf (renders as
    [`LineNode`](../terminal/nodes.md#xnano.terminal.nodes.LineNode){data-preview}):

        Text([Text("Hello ", color="cyan"), Text("world", color="red")])

    **Paragraph** — multiple lines composed via a list of ``Text`` children
    where at least one child is itself a line (renders as
    [`ParagraphNode`](../terminal/nodes.md#xnano.terminal.nodes.ParagraphNode){data-preview}
    wrapping a
    [`TextNode`](../terminal/nodes.md#xnano.terminal.nodes.TextNode){data-preview}):

        Text([
            Text([Text("Hello ", color="cyan"), Text("world")]),
            Text("Second line", color="blue"),
        ])

    **Input** — set ``input=True`` on a leaf ``Text`` placed in a grid field
    to make it focusable and editable (tab order, caret, placeholder).
    Add ``multiline=True`` (and optional ``rows``) for multi-line editing
    backed by ``CoreTextEditor``:

        class Form(BaseGrid):
            name: Text = Field(
                default=Text("", input=True, placeholder="your name"),
            )
            notes: Text = Field(
                default=Text("", input=True, multiline=True, rows=5),
            )

    **Display modes** (mutually exclusive with each other and with
    ``input``) parse a leaf string before styling:

    - ``ansi=True`` — SGR sequences (subprocess/Rich/pytest output)
    - ``markdown=True`` — headings, emphasis, lists, fenced code
    - ``language="python"`` — Pygments syntax highlighting only

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
    multiline: bool = False
    """When ``True`` together with ``input``, editing is backed by the
    native ``CoreTextEditor`` engine: multi-line content, undo/redo, and
    an in-buffer caret. Single-line inputs keep the lightweight path."""
    rows: int | None = None
    """Preferred visible height (in lines) for a ``multiline`` input;
    ``None`` sizes to the content."""
    ansi: bool = False
    """When ``True`` on a leaf ``Text``, ANSI escape sequences in
    ``content`` (subprocess output, Rich/pytest colors, …) are parsed
    into styled runs instead of rendering as raw escapes."""
    markdown: bool = False
    """When ``True`` on a leaf ``Text``, ``content`` is parsed as
    markdown: headings, emphasis, lists, blockquotes, and fenced code
    blocks (highlighted by their fence language tag)."""
    language: str | None = None
    """Syntax-highlight ``content`` as this language (a Pygments lexer
    name such as ``"python"``); no markdown parsing."""
    passthrough: Sequence[str] = ()
    """Key bindings this input never captures, even while focused (e.g.
    ``("ctrl+c", "up", "down")``) — ``handle_keyboard`` returns ``False``
    for them immediately, so they bubble to ``@on_keyboard`` app hooks
    instead of being consumed as text editing."""
    _input_focused: bool = dataclasses.field(
        default=False, init=False, repr=False, compare=False
    )
    _editor: Any = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        display_modes = [
            name
            for name, enabled in (
                ("ansi", self.ansi),
                ("markdown", self.markdown),
                ("language", self.language is not None),
            )
            if enabled
        ]
        if len(display_modes) > 1 or (display_modes and self.input):
            conflict = " + ".join(
                display_modes + (["input"] if self.input else [])
            )
            raise ValueError(
                f"Text({conflict}) is invalid: ansi, markdown, language, "
                "and input are mutually exclusive."
            )
        if self.multiline and self.input and isinstance(self.content, str):
            from xnano_core.core import CoreTextEditor

            self._editor = CoreTextEditor(self.content)
            placeholder = self._placeholder_string()
            if placeholder:
                self._editor.set_placeholder_text(placeholder)

    def _is_leaf(self) -> bool:
        """True when this node holds a plain string (no nested Text children)."""
        return isinstance(self.content, str)

    @property
    def focusable(self) -> bool:
        """Whether this Text participates in field focus (tab order)."""
        return bool(self.input)

    @property
    def owns_cursor(self) -> bool:
        """Whether this Text paints its own caret (multi-line editor)."""
        return self._editor is not None

    @property
    def value(self) -> str:
        """Plain-string content for leaf ``Text``; empty string otherwise."""
        if self._editor is not None:
            return self._editor.text()
        if isinstance(self.content, str):
            return self.content
        return ""

    @value.setter
    def value(self, text: str) -> None:
        if self._editor is not None:
            self._editor.set_text(text)
        self.content = text
        if self.cursor is not None:
            self.cursor = max(0, min(self.cursor, len(text)))

    def handle_paste(self, text: str) -> bool:
        """Insert pasted text at the caret of a multi-line editor.

        Args:
            text: The pasted clipboard text.

        Returns:
            ``True`` when the paste was consumed by the native editor.
        """
        if self._editor is None:
            return False
        self._editor.insert_text(text)
        self.content = self._editor.text()
        return True

    def _markup_lines(self) -> tuple[tuple[Any, ...], ...] | None:
        """Run lines for ansi/markdown/language modes; None otherwise."""
        if not isinstance(self.content, str):
            return None
        if self.ansi:
            from xnano._markup import parse_ansi_lines

            return parse_ansi_lines(self.content)
        if self.markdown:
            from xnano._markup import markdown_lines

            return markdown_lines(self.content)
        if self.language is not None:
            from xnano._markup import highlight_lines

            return highlight_lines(self.content, self.language)
        return None

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

    def _to_span_node(self) -> AbstractTerminalNode:
        from xnano.terminal.nodes import SpanNode

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
        from xnano.terminal.nodes import LineNode

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

    def _to_line_node(
        self, ctx: ComponentRenderContext
    ) -> AbstractTerminalNode:
        from xnano.terminal.nodes import LineNode, SpanNode

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

    def compose(self, ctx: ComponentRenderContext):
        """Compose interface-neutral
        [`Content`](../core/content.md#xnano.core.content.Content){data-preview}
        for this Text.

        Controllers lower the result; ``get_terminal_node`` remains a
        thin adapter that lowers the same
        [`Content`](../core/content.md#xnano.core.content.Content){data-preview}
        for older call sites.
        """
        from xnano.core.content import Native, Run, TextBlock

        # Native multi-line editor: the engine owns content and caret.
        if self._editor is not None:
            from xnano.terminal.nodes import EditorNode

            return Native(
                interface_kind="tui",
                payload=EditorNode(editor=self._editor, rows=self.rows),
                z=self.z,
                visible=self.visible,
            )

        # Pre-styled content (ANSI, markdown, highlighted code): parse
        # into run lines once, render as a plain TextBlock.
        markup_lines = self._markup_lines()
        if markup_lines is not None:
            return TextBlock(
                lines=markup_lines,
                color=self.color,
                background=self.background,
                modifiers=self.modifiers,
                align=self.align,
                wrap=self.wrap,
                z=self.z,
                visible=self.visible,
            )

        # Leaf: single string
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
            return TextBlock.from_plain(
                text_str,
                color=color,
                background=self.background,
                modifiers=modifiers,
                align=self.align,
                wrap=self.wrap,
                z=self.z,
                visible=self.visible,
            )

        if isinstance(self.content, Text):
            return self.content.compose(ctx)

        children = self._as_children()
        all_leaves = all(child._is_leaf() for child in children)

        # Simple one-line leaf spans → Content TextBlock. Nested lines,
        # embedded newlines, and mixed trees keep full fidelity through
        # Native wrapping of the existing node assembly path.
        if all_leaves and not self._leaf_children_have_embedded_newlines(
            children
        ):
            runs: list[Run] = []
            for child in children:
                if isinstance(child.content, str):
                    runs.append(
                        Run(
                            text=child.content,
                            color=child.color,
                            background=child.background,
                            modifiers=tuple(child.modifiers),
                        )
                    )
            return TextBlock(
                lines=(tuple(runs),),
                color=self.color,
                background=self.background,
                modifiers=tuple(self.modifiers),
                align=self.align,
                wrap=self.wrap,
                z=self.z,
                visible=self.visible,
            )

        return Native(
            interface_kind="tui",
            payload=self._compose_terminal_node(ctx),
            z=self.z,
            visible=self.visible,
        )

    def handle_keyboard(self, keyboard: "KeyboardEventData") -> bool:
        """Apply a keyboard event while this Text is a focused input.

        Component-owned input path; hosts call this through the shared
        focus dispatch. Multi-line inputs forward the native key event
        into the ``CoreTextEditor`` engine; single-line inputs use the
        lightweight pure-Python path.

        Args:
            keyboard: The keyboard event payload.

        Returns:
            ``True`` when the key was consumed as text editing.
        """
        if self.passthrough and keyboard.matches(*self.passthrough):
            return False
        if self._editor is not None:
            native = getattr(keyboard, "_native_event", None)
            if native is None:
                return False
            consumed = bool(self._editor.input(native))
            if consumed:
                self.content = self._editor.text()
            return consumed
        from xnano._types import apply_text_keyboard

        return apply_text_keyboard(self, keyboard)

    def get_terminal_node(
        self, ctx: ComponentRenderContext
    ) -> AbstractTerminalNode:
        """Lower ``compose()`` output to a terminal render node."""
        from xnano.core.content import Native
        from xnano.terminal.content_lower import lower_content
        from xnano.terminal.nodes import AbstractTerminalNode as TerminalNode

        content = self.compose(ctx)
        if content is not None:
            if isinstance(content, Native) and isinstance(
                content.payload, TerminalNode
            ):
                return content.payload
            node = lower_content(content)
            if node is not None:
                return node
        return self._compose_terminal_node(ctx)

    def _compose_terminal_node(
        self, ctx: ComponentRenderContext
    ) -> AbstractTerminalNode:
        from xnano.terminal.nodes import (
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
            return self.content.get_terminal_node(ctx)

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
