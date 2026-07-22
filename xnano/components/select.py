"""xnano.components.select

---

``Select`` component: a selectable, fuzzy-filterable list of items.

Typing while focused edits the filter query; matched characters are
emphasized, up/down move the selection, and enter/tab/esc stay
available to application hooks and focus navigation.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Sequence

from xnano._types import CharacterModifier
from xnano.components.abstract import AbstractComponent
from xnano.components.text import Text

if TYPE_CHECKING:
    from xnano.color import ColorLike
    from xnano.components.abstract import ComponentRenderContext
    from xnano.events import KeyboardEventData

_WORD_BOUNDARIES = " _-./:"


def get_fuzzy_match(
    query: str,
    candidate: str,
) -> tuple[int, tuple[int, ...]] | None:
    """Score ``candidate`` against ``query`` as a fuzzy subsequence.

    Case-insensitive. Consecutive matches and word-start matches score
    higher; shorter candidates win ties.

    Args:
        query: The needle typed by the user.
        candidate: The haystack item text.

    Returns:
        ``(score, matched_indices)`` when every query character appears
        in order, otherwise ``None``. An empty query matches with score
        zero.
    """
    # ponytail: naive O(n*m) scan; nucleo-matcher binding if item
    # counts ever hit five digits.
    if not query:
        return (0, ())
    lowered_query = query.lower()
    lowered_candidate = candidate.lower()
    indices: list[int] = []
    score = 0
    search_from = 0
    previous = -2
    for character in lowered_query:
        found = lowered_candidate.find(character, search_from)
        if found < 0:
            return None
        score += 1
        if found == previous + 1:
            score += 4
        if found == 0 or lowered_candidate[found - 1] in _WORD_BOUNDARIES:
            score += 2
        indices.append(found)
        previous = found
        search_from = found + 1
    score -= max(0, len(candidate) - len(query)) // 4
    return (score, tuple(indices))


@dataclasses.dataclass
class Select(AbstractComponent):
    """Selectable, filterable list of items.

    Typing while focused edits ``query`` (when ``searchable``); the
    visible list narrows to fuzzy matches with matched characters
    emphasized in ``match_color``. Up/down move the selection and
    ``value`` reads the selected item:

        class Picker(BaseGrid):
            themes: Select = Field(default=Select(items=THEME_NAMES))

            @on_keyboard("enter")
            def _choose(self, ctx: Context) -> None:
                apply_theme(self.themes.value)

    Set ``searchable=False`` to drive ``query`` reactively from another
    field (a ``Text(input=True)`` search box) instead of direct typing.
    """

    items: Sequence[str | Text] = ()
    """Entries to pick from (plain strings or styled ``Text`` leaves)."""
    query: str = ""
    """Filter text. Edited by typing while focused when ``searchable``;
    assign it from a hook to filter reactively."""
    filter: bool = True
    """Whether ``query`` fuzzy-filters the visible items. When
    ``False`` the query is ignored and all items stay visible."""
    searchable: bool = True
    """Whether typing while focused edits ``query`` directly."""
    selected: int = 0
    """Selection index within the *filtered* view."""
    color: ColorLike | None = None
    background: ColorLike | None = None
    highlight_color: ColorLike = "black"
    """Foreground of the selected row."""
    highlight_background: ColorLike = "white"
    """Background of the selected row."""
    highlight_symbol: str = "> "
    """Symbol prepended to the selected row."""
    match_color: ColorLike | None = "cyan"
    """Emphasis color for characters matched by ``query``."""
    focusable: bool = True
    """Whether this Select participates in field focus (tab order)."""
    _input_focused: bool = dataclasses.field(
        default=False, init=False, repr=False, compare=False
    )

    # The component paints its own selection highlight; the hardware
    # cursor stays hidden while focused.
    owns_cursor: bool = dataclasses.field(default=True, init=False)

    def _item_text(self, item: str | Text) -> str:
        if isinstance(item, Text):
            return item.value
        return item

    def _filtered(self) -> list[tuple[int, tuple[int, ...]]]:
        """Return ``(item_index, matched_indices)`` in display order."""
        if not self.filter or not self.query:
            return [(index, ()) for index in range(len(self.items))]
        scored: list[tuple[int, int, tuple[int, ...]]] = []
        for index, item in enumerate(self.items):
            match = get_fuzzy_match(self.query, self._item_text(item))
            if match is not None:
                scored.append((match[0], index, match[1]))
        scored.sort(key=lambda entry: -entry[0])
        return [(index, indices) for _, index, indices in scored]

    @property
    def visible_items(self) -> tuple[str, ...]:
        """Plain text of the currently visible items, in display order."""
        return tuple(
            self._item_text(self.items[index]) for index, _ in self._filtered()
        )

    @property
    def value(self) -> str | None:
        """Plain text of the selected item, or ``None`` when the
        filtered view is empty."""
        visible = self._filtered()
        if not visible:
            return None
        selected = max(0, min(self.selected, len(visible) - 1))
        return self._item_text(self.items[visible[selected][0]])

    def handle_keyboard(self, keyboard: KeyboardEventData) -> bool:
        """Apply a keyboard event while this Select is focused.

        Up/down move the selection; printable characters and backspace
        edit ``query`` when ``searchable``. Enter, tab, and escape are
        never consumed so hooks and focus navigation see them.

        Args:
            keyboard: The keyboard event payload.

        Returns:
            ``True`` when the event was consumed.
        """
        kind = keyboard.kind
        if kind is not None and kind not in ("press", "repeat"):
            return False
        visible_count = len(self._filtered())
        if keyboard.matches("up"):
            self.selected = max(0, min(self.selected, visible_count - 1) - 1)
            return True
        if keyboard.matches("down"):
            self.selected = min(max(0, visible_count - 1), self.selected + 1)
            return True
        if not self.searchable:
            return False
        if keyboard.matches("backspace"):
            self.query = self.query[:-1]
            self.selected = 0
            return True
        character = keyboard.character
        if (
            character is not None
            and len(character) == 1
            and character.isprintable()
            and character not in ("\n", "\r", "\t")
        ):
            self.query = self.query + character
            self.selected = 0
            return True
        return False

    def _entry_block(
        self,
        text: str,
        matched: tuple[int, ...],
    ) -> Any:
        from xnano.core.content import Run, TextBlock

        if not matched or self.match_color is None:
            return TextBlock.from_plain(text)

        def make_run(segment: str, emphasized: bool) -> Run:
            return Run(
                text=segment,
                color=self.match_color if emphasized else None,
                modifiers=("bold",) if emphasized else (),
            )

        matched_set = set(matched)
        runs: list[Run] = []
        segment = ""
        segment_emphasized = False
        for index, character in enumerate(text):
            emphasized = index in matched_set
            if segment and emphasized != segment_emphasized:
                runs.append(make_run(segment, segment_emphasized))
                segment = ""
            segment += character
            segment_emphasized = emphasized
        if segment:
            runs.append(make_run(segment, segment_emphasized))
        return TextBlock(lines=(tuple(runs),))

    def compose(self, ctx: ComponentRenderContext) -> Any:
        """Compose interface-neutral Content for this Select."""
        from xnano.core.content import Items, Run, Stack, TextBlock

        visible = self._filtered()
        selected = (
            max(0, min(self.selected, len(visible) - 1)) if visible else None
        )
        entries = tuple(
            self._entry_block(self._item_text(self.items[index]), matched)
            for index, matched in visible
        )
        items_content = Items(
            items=entries,
            selected=selected,
            color=self.color,
            background=self.background,
            highlight_color=self.highlight_color,
            highlight_background=self.highlight_background,
            highlight_symbol=self.highlight_symbol,
            z=self.z,
            visible=self.visible,
        )
        if not self.searchable:
            return items_content

        caret = "▌" if self._input_focused else ""
        if self.query or caret:
            query_row: Any = TextBlock(
                lines=((Run(text=self.query + caret),),),
            )
        else:
            query_modifiers: tuple[CharacterModifier, ...] = ("dim",)
            query_row = TextBlock(
                lines=(
                    (
                        Run(
                            text="type to filter",
                            color="gray",
                            modifiers=query_modifiers,
                        ),
                    ),
                ),
            )
        return Stack(
            children=(query_row, items_content),
            direction="vertical",
            z=self.z,
            visible=self.visible,
        )

    def _web_row_spans(
        self,
        index: int,
        matched: tuple[int, ...],
        *,
        is_selected: bool,
    ) -> tuple[Any, ...]:
        """Build the styled ``WebSpanNode`` row for one visible item."""
        from xnano.core.content import Run
        from xnano.web.nodes import WebSpanNode

        block = self._entry_block(self._item_text(self.items[index]), matched)
        runs = block.lines[0] if block.lines else (Run(text=block.text),)
        prefix = (
            self.highlight_symbol
            if is_selected
            else " " * len(self.highlight_symbol)
        )
        spans = [WebSpanNode(content=prefix)]
        for run in runs:
            spans.append(
                WebSpanNode(
                    content=run.text,
                    color=self.highlight_color if is_selected else run.color,
                    background=(
                        self.highlight_background if is_selected else None
                    ),
                    modifiers=run.modifiers,
                )
            )
        return tuple(spans)

    def get_web_node(self, ctx: ComponentRenderContext) -> Any:
        """Render this Select as a search field plus a filtered list.

        Args:
            ctx: The render context.

        Returns:
            A web node tree for this Select.
        """
        from xnano.web.nodes import (
            WebContainerNode,
            WebInputNode,
            WebParagraphNode,
        )

        visible = self._filtered()
        selected = (
            max(0, min(self.selected, len(visible) - 1)) if visible else None
        )
        lines = tuple(
            self._web_row_spans(
                index, matched, is_selected=display_index == selected
            )
            for display_index, (index, matched) in enumerate(visible)
        )
        items_node = WebParagraphNode(
            lines=lines,
            color=self.color,
            background=self.background,
            wrap=False,
            z=self.z,
            visible=self.visible,
        )
        if not self.searchable:
            return items_node
        return WebContainerNode(
            children=(
                WebInputNode(value=self.query, placeholder="type to filter"),
                items_node,
            ),
            direction="vertical",
            z=self.z,
            visible=self.visible,
        )


__all__ = (
    "Select",
    "get_fuzzy_match",
)
