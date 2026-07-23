"""xnano.beta.components.link

---

Display a focusable link whose destination is available to event hooks.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.text import Text
from xnano.beta.core.content import TextBlock

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.events import KeyboardEventData


@dataclasses.dataclass
class Link(Text):
    """Focusable hyperlink label.

    Links are underlined and blue by default. Handle an activation key in a
    grid hook to open, copy, or otherwise use ``url``.

    Example:
        ``Link(content="Documentation", url="https://example.com/docs")``

    Attributes:
        url: Destination address exposed to hooks.
        underline: When ``True``, paint with the underline modifier.
        focused_color: Foreground override while focused.
        visited: Whether the link has been activated by the app.
    """

    url: str = ""
    """Destination address exposed to hooks; never auto-opened."""
    underline: bool = True
    """When ``True``, compose with the underline modifier."""
    color: ColorLike | None = "blue"
    """Default link foreground color."""
    focused_color: ColorLike | None = None
    """Foreground override while this link holds focus."""
    visited: bool = False
    """Application-maintained visited flag."""
    focusable: bool = True
    """Links participate in field focus by default."""

    def component_post_init(self) -> None:
        """Validate modes without forcing ``input=True``."""
        super().component_post_init()

    @property
    def value(self) -> str:
        """Plain label text, falling back to ``url`` when empty."""
        label = super().value
        if label:
            return label
        return self.url

    @value.setter
    def value(self, text: str) -> None:
        if self.max_length is not None:
            text = text[: self.max_length]
        if self._editor is not None:
            self._editor.set_text(text)
        object.__setattr__(self, "content", text)
        if self.cursor is not None:
            self.cursor = max(0, min(self.cursor, len(text)))

    def compose(self, ctx: ComponentRenderContext[Any]) -> TextBlock | Any:
        """Compose underlined, focus-aware link content.

        Args:
            ctx: Render-time scope for this paint.

        Returns:
            Styled ``TextBlock`` (or nested content) for this link.
        """
        modifiers = tuple(self.modifiers)
        if self.underline and "underline" not in modifiers:
            modifiers = modifiers + ("underline",)

        color = self.color
        if self.focused and self.focused_color is not None:
            color = self.focused_color
        elif self.visited and self.focused_color is None:
            # Mild visited cue when no focused override is set.
            if color == "blue":
                color = "magenta"

        # Temporarily apply compose styles without mutating live state
        # beyond the frame: build a plain block from the label.
        if isinstance(self.content, str):
            label = self.content if self.content else self.url
            return TextBlock.from_plain(
                label,
                color=color,
                background=self.background,
                modifiers=modifiers,
                align=self.align,
                wrap=self.wrap,
                z=self.z,
                visible=self.visible,
            )

        # Nested content: style via a short-lived attribute swap.
        previous_modifiers = self.modifiers
        previous_color = self.color
        object.__setattr__(self, "modifiers", modifiers)
        object.__setattr__(self, "color", color)
        try:
            return Text.compose(self, ctx)
        finally:
            object.__setattr__(self, "modifiers", previous_modifiers)
            object.__setattr__(self, "color", previous_color)

    def handle_keyboard(self, keyboard: "KeyboardEventData") -> bool:
        """Leave activation keys for application hooks.

        Args:
            keyboard: The keyboard event payload.

        Returns:
            Always ``False`` so enter/space and other keys bubble.
        """
        if self.passthrough and keyboard.matches(*self.passthrough):
            return False
        # Never consume activation or editing keys on a link.
        return False


__all__ = ("Link",)
