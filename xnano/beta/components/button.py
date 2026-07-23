"""xnano.beta.components.button

---

Display a focusable button and handle activation with normal keyboard or
click hooks.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Sequence

from xnano.beta.components.component import Component

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.components.component import ComponentRenderContext
    from xnano.beta.events import KeyboardEventData


@dataclasses.dataclass
class Button(Component):
    """Focusable styled text button.

    Buttons use the same hooks as every other field. Assign a group and
    handle clicks or activation keys on the grid:

        class Form(BaseGrid):
            submit: Button = Field(
                default=Button("Submit"),
                group="submit",
            )

            @on_click(group="submit")
        @on_keyboard("enter", group="submit")
        def submit_form(self, ctx: Context) -> None: ...

    Example:
        ``Button(label="Save", focused_background="blue")``

    Attributes:
        label: Button caption (plain string or styled ``Text``).
        disabled: When ``True``, paints disabled colors and ignores
            activation.
        focusable: Whether this button participates in field focus.
        color: Idle foreground color.
        background: Idle background color.
        focused_color: Foreground while focused.
        focused_background: Background while focused.
        disabled_color: Foreground while disabled.
        disabled_background: Background while disabled.
        left: Prefix chrome around the label.
        right: Suffix chrome around the label.
        activation_keys: Bindings that should bubble to hooks (never
            consumed by the button itself).
    """

    label: str | Any = ""
    """Button caption (plain string or styled ``Text``)."""
    disabled: bool = False
    """When ``True``, paints disabled colors and ignores activation."""
    focusable: bool = True
    """Whether this button participates in field focus (tab order)."""
    color: ColorLike | None = None
    """Idle foreground color."""
    background: ColorLike | None = None
    """Idle background color."""
    focused_color: ColorLike | None = "black"
    """Foreground while focused."""
    focused_background: ColorLike | None = "white"
    """Background while focused."""
    disabled_color: ColorLike | None = "gray"
    """Foreground while disabled."""
    disabled_background: ColorLike | None = None
    """Background while disabled."""
    left: str = "[ "
    """Prefix chrome around the label."""
    right: str = " ]"
    """Suffix chrome around the label."""
    activation_keys: Sequence[str] = ("enter", "space")
    """Bindings that bubble to hooks (never consumed here)."""

    def get_label_text(self) -> str:
        """Return the plain-text form of ``label``."""
        if isinstance(self.label, str):
            return self.label
        value = getattr(self.label, "value", None)
        if isinstance(value, str):
            return value
        content = getattr(self.label, "content", None)
        if isinstance(content, str):
            return content
        return str(self.label)

    def _resolved_colors(
        self,
    ) -> tuple[ColorLike | None, ColorLike | None]:
        """Return ``(foreground, background)`` for the current state."""
        if self.disabled:
            return (self.disabled_color, self.disabled_background)
        if self.focused:
            return (self.focused_color, self.focused_background)
        return (self.color, self.background)

    def handle_keyboard(self, keyboard: "KeyboardEventData") -> bool:
        """Leave keyboard activation to the grid's event hooks.

        Args:
            keyboard: The keyboard event payload.

        Returns:
            ``False`` so the event continues to hooks.
        """
        del keyboard
        return False

    def compose(self, ctx: "ComponentRenderContext") -> Any:
        """Compose a styled label, wrapped in a panel when focused.

        Args:
            ctx: Render-time scope for this paint.

        Returns:
            A ``TextBlock``, or a ``Panel`` around it while focused and
            not disabled.
        """
        from xnano.beta.core.content import Panel, Run, TextBlock

        del ctx
        foreground, background = self._resolved_colors()
        caption = f"{self.left}{self.get_label_text()}{self.right}"
        block = TextBlock(
            lines=(
                (
                    Run(
                        text=caption,
                        color=foreground,
                        background=background,
                    ),
                ),
            ),
            color=foreground,
            background=background,
            z=self.z,
            visible=self.visible,
        )
        if self.focused and not self.disabled:
            return Panel(
                child=block,
                background=background,
                border_color=foreground,
                z=self.z,
                visible=self.visible,
            )
        return block


__all__ = ("Button",)
