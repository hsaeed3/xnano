"""xnano.beta.components.text

---

Display styled text, nested spans, ANSI, Markdown, or highlighted source code.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Sequence

from xnano.beta.components.component import Component, ComponentRenderContext
from xnano.beta.core.content import Native, Run, TextBlock
from xnano.beta.types import Alignment, CharacterModifier

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.events import KeyboardEventData


@dataclasses.dataclass
class Text(Component):
    """Display styled, marked-up, highlighted, or editable text.

    Nest ``Text`` values for independently styled spans. Enable ANSI,
    Markdown, or syntax highlighting for formatted content, or set ``input``
    to make a leaf editable.

    Example:
        ``Text(content="Ready", color="green", modifiers=("bold",))``

    Attributes:
        content: Plain string, nested ``Text``, or list of either.
        color: Foreground color.
        background: Background color.
        modifiers: Character modifiers such as bold or underline.
        align: Horizontal alignment at the paragraph level.
        wrap: Whether long lines may wrap.
        input: When ``True`` on a leaf, participates in field focus.
        placeholder: Shown when input is empty and unfocused.
        cursor: Caret index for single-line input; ``None`` means end.
        multiline: Use ``CoreTextEditor`` when combined with ``input``.
        rows: Preferred visible height for multiline input.
        ansi: Parse ANSI SGR sequences in leaf content.
        markdown: Parse markdown in leaf content.
        language: Pygments lexer name for syntax highlighting.
        passthrough: Key bindings never captured while focused.
        mask: Single-character display mask (password style).
        max_length: Optional clamp on the plain-string value.
        read_only: Reject edits while remaining focusable.
        tab_size: Tab width for multiline tab expansion.
        focusable: Whether this component takes field focus.
    """

    content: str | Text | list[str | Text] = dataclasses.field(default="")
    """Plain string, nested ``Text``, or a list of either."""
    color: ColorLike | None = None
    """Foreground color."""
    background: ColorLike | None = None
    """Background color."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Character modifiers such as bold or underline."""
    align: Alignment | None = None
    """Horizontal alignment at the paragraph level."""
    wrap: bool = True
    """Whether long lines may wrap."""
    input: bool = False
    """When ``True`` on a leaf, the component is an editable field."""
    placeholder: str | Text | None = None
    """Shown when input is empty and unfocused."""
    cursor: int | None = None
    """Caret index for single-line input; ``None`` means end of string."""
    multiline: bool = False
    """When ``True`` with ``input``, editing uses ``CoreTextEditor``."""
    rows: int | None = None
    """Preferred visible height (lines) for a multiline input."""
    ansi: bool = False
    """Parse ANSI SGR sequences in leaf content."""
    markdown: bool = False
    """Parse leaf content as markdown."""
    language: str | None = None
    """Pygments lexer name for syntax highlighting only."""
    passthrough: Sequence[str] = ()
    """Key bindings this input never captures while focused."""
    mask: str | None = None
    """Display-only mask character(s); real ``value`` is preserved."""
    max_length: int | None = None
    """Maximum plain-string length; longer input is clamped."""
    read_only: bool = False
    """Reject edits while remaining focusable."""
    tab_size: int = 4
    """Tab width applied to multiline tab insertion and paste."""
    focusable: bool = False
    """Whether this component participates in field focus."""

    _editor: Any = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _markup_cache_key: tuple[str, bool, bool, str | None] | None = (
        dataclasses.field(default=None, init=False, repr=False, compare=False)
    )
    _markup_cache_lines: tuple[tuple[Any, ...], ...] | None = (
        dataclasses.field(default=None, init=False, repr=False, compare=False)
    )

    def component_post_init(self) -> None:
        """Validate modes and initialize the native editor when needed."""
        self._validate_display_modes()
        if self.input:
            self.focusable = True
        self._sync_editor_state()

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)
        # Keep editor text aligned when content is assigned after init.
        if name == "content" and isinstance(value, str):
            editor = object.__getattribute__(self, "__dict__").get("_editor")
            if editor is not None and editor.text() != value:
                editor.set_text(value)

    def _validate_display_modes(self) -> None:
        """Raise when mutually exclusive display modes are combined."""
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

    def _sync_editor_state(self) -> None:
        """Create, update, or tear down the native editor as needed."""
        want_editor = (
            self.multiline and self.input and isinstance(self.content, str)
        )
        if want_editor:
            if self._editor is None:
                from xnano_core.core import CoreTextEditor

                self._editor = CoreTextEditor(self.content)
            else:
                current = self._editor.text()
                if current != self.content:
                    # Prefer editor text when it already diverged.
                    if self.content == "" and current:
                        object.__setattr__(self, "content", current)
                    elif self.content != current:
                        self._editor.set_text(self.content)
            placeholder = self._placeholder_string()
            if placeholder:
                self._editor.set_placeholder_text(placeholder)
        elif self._editor is not None:
            object.__setattr__(self, "content", self._editor.text())
            self._editor = None

    def _is_leaf(self) -> bool:
        """True when this node holds a plain string."""
        return isinstance(self.content, str)

    @property
    def owns_cursor(self) -> bool:
        """Whether this Text paints its own caret (multi-line editor)."""
        return self._editor is not None

    @property
    def value(self) -> str:
        """Canonical plain-string content for leaf and input modes."""
        if self._editor is not None:
            return self._editor.text()
        if isinstance(self.content, str):
            return self.content
        return ""

    @value.setter
    def value(self, text: str) -> None:
        if self.max_length is not None:
            text = text[: self.max_length]
        if self._editor is not None:
            self._editor.set_text(text)
        object.__setattr__(self, "content", text)
        if self.cursor is not None:
            self.cursor = max(0, min(self.cursor, len(text)))

    def _clamp_text(self, text: str) -> str:
        """Apply ``max_length`` and ``tab_size`` expansion to ``text``."""
        if self.tab_size > 0 and "\t" in text:
            text = text.expandtabs(self.tab_size)
        if self.max_length is not None:
            text = text[: self.max_length]
        return text

    def handle_paste(self, text: str) -> bool:
        """Insert pasted text at the caret of a multi-line editor.

        Args:
            text: The pasted clipboard text.

        Returns:
            ``True`` when the paste was consumed by the native editor.
        """
        if self._editor is None:
            return False
        if self.read_only:
            return True
        text = self._clamp_text(text)
        if self.max_length is not None:
            remaining = self.max_length - len(self._editor.text())
            if remaining <= 0:
                return True
            text = text[:remaining]
        self._editor.insert_text(text)
        object.__setattr__(self, "content", self._editor.text())
        return True

    def _markup_lines(self) -> tuple[tuple[Any, ...], ...] | None:
        """Run lines for ansi/markdown/language modes; None otherwise."""
        if not isinstance(self.content, str):
            return None
        if not (self.ansi or self.markdown or self.language is not None):
            return None
        key: tuple[str, bool, bool, str | None] = (
            self.content,
            self.ansi,
            self.markdown,
            self.language,
        )
        if (
            self._markup_cache_key == key
            and self._markup_cache_lines is not None
        ):
            return self._markup_cache_lines
        lines: tuple[tuple[Any, ...], ...] | None = None
        if self.ansi:
            from xnano.beta.utils.markup import parse_ansi_lines

            lines = parse_ansi_lines(self.content)
        elif self.markdown:
            from xnano.beta.utils.markup import markdown_lines

            lines = markdown_lines(self.content)
        elif self.language is not None:
            from xnano.beta.utils.markup import highlight_lines

            lines = highlight_lines(self.content, self.language)
        self._markup_cache_key = key
        self._markup_cache_lines = lines
        return lines

    def _placeholder_string(self) -> str | None:
        """Plain placeholder string when one is configured."""
        if self.placeholder is None:
            return None
        if isinstance(self.placeholder, str):
            return self.placeholder
        if isinstance(self.placeholder, Text) and isinstance(
            self.placeholder.content, str
        ):
            return self.placeholder.content
        return None

    def _mask_text(self, text: str) -> str:
        """Return ``text`` with each character replaced by the mask."""
        if not self.mask:
            return text
        glyph = self.mask[:1]
        return glyph * len(text)

    def _input_display_content(
        self,
    ) -> tuple[str, ColorLike | None, bool]:
        """Return ``(text, color_override, is_placeholder)`` for input."""
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
        display = self._mask_text(self.content)
        if self._input_focused and self.input:
            position = (
                self.cursor if self.cursor is not None else len(self.content)
            )
            position = max(0, min(position, len(self.content)))
            return (
                display[:position] + "▌" + display[position:],
                None,
                False,
            )
        return (display, None, False)

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

    def _to_span_node(self) -> Run:
        """Return this leaf as one styled text run."""
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
        return Run(
            text=text_str,
            color=self.color,
            background=self.background,
            modifiers=tuple(self.modifiers),
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
    ) -> list[tuple[Run, ...]]:
        """Expand leaf children into styled text rows."""
        lines: list[tuple[Run, ...]] = []
        for child in children:
            if not isinstance(child.content, str):
                continue
            for segment in child.content.split("\n"):
                lines.append(
                    (
                        Run(
                            text=segment,
                            color=child.color,
                            background=child.background,
                            modifiers=tuple(child.modifiers),
                        ),
                    )
                )
        return lines

    def _to_line_node(self, ctx: ComponentRenderContext[Any]) -> TextBlock:
        """Return this value as one interface-neutral text block."""
        if isinstance(self.content, str):
            return TextBlock(
                text=self.content,
                color=self.color,
                background=self.background,
                modifiers=tuple(self.modifiers),
            )
        children = self._as_children()
        spans = [child._to_span_node() for child in children]
        return TextBlock(
            lines=(tuple(spans),),
            color=self.color,
            background=self.background,
            modifiers=tuple(self.modifiers),
        )

    def compose(
        self, ctx: ComponentRenderContext[Any]
    ) -> TextBlock | Native | None:
        """Compose interface-neutral content for this Text.

        Args:
            ctx: Render-time scope for this paint.

        Returns:
            A ``TextBlock``, ``Native`` editor payload, or nested content.
        """
        self._sync_editor_state()

        if self._editor is not None:
            return TextBlock(
                text=self.value,
                color=self.color,
                background=self.background,
                modifiers=self.modifiers,
                align=self.align,
                wrap=self.wrap,
                z=self.z,
                visible=self.visible,
            )

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

        lines: list[tuple[Run, ...]] = []
        for child in children:
            if not isinstance(child.content, str):
                continue
            lines.extend(child._build_line_nodes_from_leaf_children([child]))
        return TextBlock(
            lines=tuple(lines),
            color=self.color,
            background=self.background,
            modifiers=self.modifiers,
            align=self.align,
            wrap=self.wrap,
            z=self.z,
            visible=self.visible,
        )

    def handle_keyboard(self, keyboard: "KeyboardEventData") -> bool:
        """Edit this text when it has focus.

        Passthrough bindings remain available to hooks. Read-only inputs reject
        edits, and ``max_length`` limits inserted content.

        Args:
            keyboard: The keyboard event payload.

        Returns:
            ``True`` when the key was consumed as text editing.
        """
        if self.passthrough and keyboard.matches(*self.passthrough):
            return False
        if not self.input:
            return False

        if self._editor is not None:
            return self._handle_editor_keyboard(keyboard)
        return self._handle_single_line_keyboard(keyboard)

    def _handle_editor_keyboard(self, keyboard: "KeyboardEventData") -> bool:
        """Forward a key into the native multi-line editor."""
        native = getattr(keyboard, "_native_event", None)
        if native is None:
            return False
        before = self._editor.text()
        if self.read_only:
            consumed = bool(self._editor.input(native))
            if self._editor.text() != before:
                self._editor.set_text(before)
                return True
            return consumed
        consumed = bool(self._editor.input(native))
        if not consumed:
            return False
        text = self._editor.text()
        if self.max_length is not None and len(text) > self.max_length:
            text = text[: self.max_length]
            self._editor.set_text(text)
        if self.tab_size > 0 and "\t" in text:
            expanded = text.expandtabs(self.tab_size)
            if expanded != text:
                if (
                    self.max_length is not None
                    and len(expanded) > self.max_length
                ):
                    expanded = expanded[: self.max_length]
                self._editor.set_text(expanded)
                text = expanded
        object.__setattr__(self, "content", text)
        return True

    def _handle_single_line_keyboard(
        self, keyboard: "KeyboardEventData"
    ) -> bool:
        """Lightweight single-line editing with mask/max_length/read_only."""
        if not isinstance(self.content, str):
            return False
        kind = keyboard.kind
        if kind is not None and kind not in ("press", "repeat"):
            return False

        content = self.content
        position = self.cursor if self.cursor is not None else len(content)
        position = max(0, min(position, len(content)))

        if keyboard.matches("backspace"):
            if self.read_only:
                return True
            if position > 0:
                object.__setattr__(
                    self,
                    "content",
                    content[: position - 1] + content[position:],
                )
                self.cursor = position - 1
            return True
        if keyboard.matches("delete"):
            if self.read_only:
                return True
            if position < len(content):
                object.__setattr__(
                    self,
                    "content",
                    content[:position] + content[position + 1 :],
                )
                self.cursor = position
            return True
        if keyboard.matches("left"):
            self.cursor = max(0, position - 1)
            return True
        if keyboard.matches("right"):
            self.cursor = min(len(content), position + 1)
            return True
        if keyboard.matches("home"):
            self.cursor = 0
            return True
        if keyboard.matches("end"):
            self.cursor = len(content)
            return True
        if keyboard.matches(
            "tab",
            "backtab",
            "enter",
            "esc",
            "up",
            "down",
            "pageup",
            "pagedown",
        ):
            return False

        character = keyboard.character
        if (
            character is not None
            and len(character) == 1
            and character.isprintable()
            and character not in ("\n", "\r", "\t")
        ):
            if self.read_only:
                return True
            if self.max_length is not None and len(content) >= self.max_length:
                return True
            object.__setattr__(
                self,
                "content",
                content[:position] + character + content[position:],
            )
            self.cursor = position + 1
            return True
        return False

    def get_terminal_node(
        self, ctx: ComponentRenderContext[Any]
    ) -> TextBlock | Native | None:
        """Return composed content for terminal compatibility.

        Args:
            ctx: Render-time scope for this paint.

        Returns:
            The same interface-neutral content as ``compose``.
        """
        return self.compose(ctx)


__all__ = ("Text",)
