"""xnano.beta.components.dropdown

---

Choose an item from a collapsible, searchable list.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Sequence

from xnano.beta.components.options import Options, _item_text

if TYPE_CHECKING:
    from xnano.beta.components.component import ComponentRenderContext
    from xnano.beta.components.options import OptionItem
    from xnano.beta.events import KeyboardEventData


@dataclasses.dataclass
class Dropdown(Options):
    """Collapsible choice list.

    When closed, the dropdown shows the selected label or placeholder.
    When open, users can search and move through the available options.

        class Form(BaseGrid):
            theme: Dropdown = Field(
                default=Dropdown(
                    items=("dark", "light", "system"),
                    placeholder="pick a theme",
                ),
            )

            @on_keyboard("enter")
        def _choose(self, ctx: Context) -> None:
            if not self.theme.open:
                apply_theme(self.theme.value)

    Example:
        ``Dropdown(items=("dark", "light"), placeholder="Choose a theme")``

    Attributes:
        open: Whether the options list is expanded.
        placeholder: Closed-row text when nothing is selected.
        max_visible: Cap on open-list rows around the selection.
        close_on_select: Close after enter accepts the selection.
        open_keys: Bindings that open a closed dropdown.
        close_keys: Bindings that close an open dropdown (enter also
            accepts the current selection first).
    """

    open: bool = False
    """Whether the options list is expanded."""
    placeholder: str | Any | None = None
    """Closed-row text when nothing is selected (string or ``Text``)."""
    max_visible: int | None = None
    """Cap on open-list rows around the selection; ``None`` shows all."""
    close_on_select: bool = True
    """Close after enter accepts the current selection."""
    open_keys: Sequence[str] = ("enter", "space", "down")
    """Bindings that open a closed dropdown."""
    close_keys: Sequence[str] = ("enter", "escape")
    """Bindings that close an open dropdown."""

    def _placeholder_text(self) -> str:
        """Return plain placeholder text, or an empty string."""
        if self.placeholder is None:
            return ""
        if isinstance(self.placeholder, str):
            return self.placeholder
        value = getattr(self.placeholder, "value", None)
        if isinstance(value, str):
            return value
        content = getattr(self.placeholder, "content", None)
        if isinstance(content, str):
            return content
        return str(self.placeholder)

    def _closed_label(self) -> str:
        """Return the text shown on the closed control row."""
        item: OptionItem | None = self.selected_item
        if item is not None:
            return _item_text(item)
        return self._placeholder_text()

    def _windowed_visible(
        self,
    ) -> list[tuple[int, tuple[int, ...]]]:
        """Return the filtered view, optionally windowed by max_visible."""
        pairs = self._filtered()
        if self.max_visible is None or self.max_visible <= 0:
            return pairs
        if len(pairs) <= self.max_visible:
            return pairs
        # Keep the selection roughly centered in the window.
        selected = max(0, min(self.selected, len(pairs) - 1)) if pairs else 0
        half = self.max_visible // 2
        start = max(0, selected - half)
        end = start + self.max_visible
        if end > len(pairs):
            end = len(pairs)
            start = max(0, end - self.max_visible)
        # Adjust ``selected`` so Items highlights the correct row
        # inside the windowed slice. Callers must remap after compose.
        return pairs[start:end]

    def _window_selected_offset(
        self,
        window: list[tuple[int, tuple[int, ...]]],
    ) -> int | None:
        """Map global ``selected`` into a window-local index."""
        if not window:
            return None
        pairs = self._filtered()
        if not pairs:
            return None
        global_selected = max(0, min(self.selected, len(pairs) - 1))
        target = pairs[global_selected][0]
        for offset, (item_index, _) in enumerate(window):
            if item_index == target:
                return offset
        return 0

    def handle_keyboard(self, keyboard: "KeyboardEventData") -> bool:
        """Open, close, search, or move through the dropdown.

        Opening keys expand a closed dropdown. Escape closes it without
        changing the selection. Enter accepts the selected value and closes
        it when ``close_on_select`` is enabled.

        Args:
            keyboard: The keyboard event payload.

        Returns:
            ``True`` when the event was consumed.
        """
        kind = keyboard.kind
        if kind is not None and kind not in ("press", "repeat"):
            return False
        if self.passthrough and keyboard.matches(*self.passthrough):
            return False

        if not self.open:
            if self.open_keys and keyboard.matches(*self.open_keys):
                self.open = True
                self._ensure_enabled_selection()
                return True
            return False

        # Open: escape always dismisses without changing selection.
        if keyboard.matches("escape", "esc"):
            self.open = False
            return True

        if keyboard.matches("enter"):
            # Accept current selection; close only when configured.
            self._ensure_enabled_selection()
            if self.close_on_select:
                self.open = False
            # Bubble so application hooks can read ``value``.
            return False

        if self.close_keys and keyboard.matches(*self.close_keys):
            # Non-enter close keys (e.g. a custom binding) dismiss.
            if not keyboard.matches("enter"):
                self.open = False
                return True

        # While open, reuse Options movement / filter handling.
        return super().handle_keyboard(keyboard)

    def _compose_closed_row(self) -> Any:
        """Compose the single closed control row."""
        from xnano.beta.core.content import Run, TextBlock

        label = self._closed_label()
        if not label:
            return TextBlock(
                lines=(
                    (
                        Run(
                            text="select…",
                            color="gray",
                            modifiers=("dim",),
                        ),
                    ),
                ),
            )
        color = self.highlight_color if self._input_focused else self.color
        background = (
            self.highlight_background
            if self._input_focused
            else self.background
        )
        return TextBlock(
            lines=((Run(text=label, color=color, background=background),),),
            color=color,
            background=background,
        )

    def compose(self, ctx: "ComponentRenderContext") -> Any:
        """Compose closed label or open options content.

        Args:
            ctx: Render-time scope for this paint.

        Returns:
            Closed: a single ``TextBlock`` row. Open: the same content
            tree ``Options`` would produce, optionally windowed.
        """
        from xnano.beta.core.content import Stack

        if not self.open:
            return self._compose_closed_row()

        window = self._windowed_visible()
        # Remap selected into the window for Items highlight, then
        # restore — selection state stays global on the component.
        global_selected = self.selected
        local = self._window_selected_offset(window)
        if local is not None:
            self.selected = local
        try:
            items_content = self._compose_items(ctx, visible=window)
        finally:
            self.selected = global_selected

        if not self.searchable:
            return items_content
        return Stack(
            children=(self._compose_query_row(), items_content),
            direction="vertical",
            z=self.z,
            visible=self.visible,
        )


__all__ = ("Dropdown",)
