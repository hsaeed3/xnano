"""xnano.beta.components.options

---

Display and search a list of choices with keyboard selection.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Literal, Sequence, TypeAlias

from xnano.beta.components.component import Component
from xnano.beta.types import CharacterModifier

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.components.component import ComponentRenderContext
    from xnano.beta.components.text import Text
    from xnano.beta.events import KeyboardEventData

_WORD_BOUNDARIES = " _-./:"

OptionsDirection: TypeAlias = Literal["top_to_bottom", "bottom_to_top"]
"""Visual order of option rows in the list."""

OptionItem: TypeAlias = "str | Text | Option"
"""A single entry accepted by ``Options.items``."""


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


@dataclasses.dataclass(frozen=True, slots=True)
class Option:
    """A labeled choice with optional distinct value and disabled flag.

    Pass plain strings or ``Text`` values for simple choices. Use ``Option``
    when the stored value differs from its label or the choice is disabled.

    Attributes:
        label: Display text (plain string or styled ``Text`` leaf).
        value: Stored value; defaults to the plain label text when
            ``None``.
        disabled: When ``True``, movement skips this entry and it
            cannot become the active selection via ``select``.
    """

    label: str | Any
    """Display text (plain string or styled ``Text`` leaf)."""
    value: Any = None
    """Stored value; defaults to the plain label text when ``None``."""
    disabled: bool = False
    """When ``True``, movement skips this entry."""

    def get_label_text(self) -> str:
        """Return the plain-text form of ``label``."""
        label = self.label
        if isinstance(label, str):
            return label
        value = getattr(label, "value", None)
        if isinstance(value, str):
            return value
        content = getattr(label, "content", None)
        if isinstance(content, str):
            return content
        return str(label)

    def get_value(self) -> Any:
        """Return the stored value, falling back to the plain label."""
        if self.value is not None:
            return self.value
        return self.get_label_text()


def _item_text(item: OptionItem) -> str:
    """Return plain display text for a list item."""
    if isinstance(item, Option):
        return item.get_label_text()
    if isinstance(item, str):
        return item
    value = getattr(item, "value", None)
    if isinstance(value, str):
        return value
    content = getattr(item, "content", None)
    if isinstance(content, str):
        return content
    return str(item)


def _item_value(item: OptionItem) -> Any:
    """Return the stored value for a list item."""
    if isinstance(item, Option):
        return item.get_value()
    return _item_text(item)


def _item_disabled(item: OptionItem) -> bool:
    """Return whether a list item is disabled."""
    if isinstance(item, Option):
        return bool(item.disabled)
    return False


@dataclasses.dataclass
class Options(Component):
    """Always-visible, filterable choice list.

    Typing while focused edits ``query`` (when ``searchable``); the
    visible list narrows to fuzzy matches with matched characters
    emphasized in ``match_color``. Up/down move the selection (skipping
    disabled entries) and ``value`` reads the selected item:

        class Picker(BaseGrid):
            themes: Options = Field(
                default=Options(items=THEME_NAMES),
            )

            @on_keyboard("enter")
            def _choose(self, ctx: Context) -> None:
                apply_theme(self.themes.value)

    Set ``searchable=False`` to drive ``query`` reactively from another
    field instead of direct typing.

    Example:
        ``Options(items=("small", "medium", "large"), selected=1)``

    Attributes:
        items: Entries to pick from (strings, ``Text``, or ``Option``).
        query: Filter text edited by typing when ``searchable``.
        filter: Whether ``query`` fuzzy-filters the visible items.
        searchable: Whether typing while focused edits ``query``.
        selected: Selection index within the *filtered* view.
        direction: Visual order of option rows.
        color: Default foreground color for unselected rows.
        background: Default background color for unselected rows.
        highlight_color: Foreground of the selected row.
        highlight_background: Background of the selected row.
        highlight_symbol: Symbol prepended to the selected row.
        match_color: Emphasis color for characters matched by ``query``.
        repeat_highlight_symbol: When ``True``, every row shows the
            highlight symbol (selected row still uses highlight style).
        focusable: Whether this Options participates in field focus.
        passthrough: Key bindings never captured while focused.
    """

    items: Sequence[OptionItem] = ()
    """Entries to pick from (plain strings, ``Text``, or ``Option``)."""
    query: str = ""
    """Filter text. Edited by typing while focused when ``searchable``;
    assign it from a hook to filter reactively.
    """
    filter: bool = True
    """Whether ``query`` fuzzy-filters the visible items. When
    ``False`` the query is ignored and all items stay visible.
    """
    searchable: bool = True
    """Whether typing while focused edits ``query`` directly."""
    selected: int = 0
    """Selection index within the *filtered* view."""
    direction: OptionsDirection = "top_to_bottom"
    """Visual order of option rows in the list."""
    color: ColorLike | None = None
    """Default foreground color for unselected rows."""
    background: ColorLike | None = None
    """Default background color for unselected rows."""
    highlight_color: ColorLike = "black"
    """Foreground of the selected row."""
    highlight_background: ColorLike = "white"
    """Background of the selected row."""
    highlight_symbol: str = "> "
    """Symbol prepended to the selected row."""
    match_color: ColorLike | None = "cyan"
    """Emphasis color for characters matched by ``query``."""
    repeat_highlight_symbol: bool = False
    """When ``True``, every row shows the highlight symbol."""
    focusable: bool = True
    """Whether this Options participates in field focus (tab order)."""
    passthrough: Sequence[str] = ()
    """Key bindings this list never captures while focused."""

    # The component paints its own selection highlight; the hardware
    # cursor stays hidden while focused.
    owns_cursor: bool = dataclasses.field(default=True, init=False)
    """Whether selection replaces the hardware caret."""

    def _filtered(self) -> list[tuple[int, tuple[int, ...]]]:
        """Return ``(item_index, matched_indices)`` in display order."""
        pairs: list[tuple[int, tuple[int, ...]]]
        if not self.filter or not self.query:
            pairs = [(index, ()) for index in range(len(self.items))]
        else:
            scored: list[tuple[int, int, tuple[int, ...]]] = []
            for index, item in enumerate(self.items):
                match = get_fuzzy_match(self.query, _item_text(item))
                if match is not None:
                    scored.append((match[0], index, match[1]))
            scored.sort(key=lambda entry: -entry[0])
            pairs = [(index, indices) for _, index, indices in scored]
        if self.direction == "bottom_to_top":
            pairs = list(reversed(pairs))
        return pairs

    @property
    def filtered(self) -> tuple[int, ...]:
        """Indices into ``items`` currently visible, in display order.

        Use this with ``visible_items`` to inspect the current filtered view.
        """
        return tuple(index for index, _ in self._filtered())

    @property
    def visible_items(self) -> tuple[str, ...]:
        """Plain text of the currently visible items, in display order."""
        return tuple(
            _item_text(self.items[index]) for index, _ in self._filtered()
        )

    @property
    def value(self) -> Any | None:
        """Stored value of the selected item, or ``None`` when empty."""
        item = self.selected_item
        if item is None:
            return None
        return _item_value(item)

    @property
    def selected_item(self) -> OptionItem | None:
        """The selected item object, or ``None`` when the view is empty."""
        visible = self._filtered()
        if not visible:
            return None
        selected = max(0, min(self.selected, len(visible) - 1))
        return self.items[visible[selected][0]]

    def move(self, delta: int) -> None:
        """Move ``selected`` by ``delta``, skipping disabled entries.

        Movement stays within the currently filtered choices.

        Args:
            delta: Steps to move; negative moves toward the start.
        """
        visible = self._filtered()
        visible_count = len(visible)
        if visible_count == 0:
            self.selected = 0
            return
        current = max(0, min(self.selected, visible_count - 1))
        if delta == 0:
            self.selected = current
            return
        step = 1 if delta > 0 else -1
        remaining = abs(delta)
        index = current
        while remaining > 0:
            next_index = index + step
            if next_index < 0 or next_index >= visible_count:
                break
            index = next_index
            item_index = visible[index][0]
            if not _item_disabled(self.items[item_index]):
                remaining -= 1
        self.selected = index
        # If we landed on a disabled entry (all remaining disabled),
        # snap back to the nearest enabled neighbor.
        self._ensure_enabled_selection()

    def select(self, index: int) -> None:
        """Set ``selected`` to ``index`` within the filtered view.

        Disabled entries are rejected; the selection is left unchanged
        when ``index`` points at a disabled item. Out-of-range indices
        are clamped.

        Args:
            index: Target index in the filtered view.
        """
        visible = self._filtered()
        if not visible:
            self.selected = 0
            return
        clamped = max(0, min(index, len(visible) - 1))
        item_index = visible[clamped][0]
        if _item_disabled(self.items[item_index]):
            return
        self.selected = clamped

    def clear_query(self) -> None:
        """Clear the filter query and reset selection to the first row."""
        self.query = ""
        self.selected = 0
        self._ensure_enabled_selection()

    def _ensure_enabled_selection(self) -> None:
        """Snap ``selected`` onto an enabled filtered entry when possible."""
        visible = self._filtered()
        if not visible:
            self.selected = 0
            return
        current = max(0, min(self.selected, len(visible) - 1))
        if not _item_disabled(self.items[visible[current][0]]):
            self.selected = current
            return
        # Prefer scanning forward, then backward.
        for index in range(current + 1, len(visible)):
            if not _item_disabled(self.items[visible[index][0]]):
                self.selected = index
                return
        for index in range(current - 1, -1, -1):
            if not _item_disabled(self.items[visible[index][0]]):
                self.selected = index
                return
        self.selected = current

    def _first_enabled_index(self) -> int:
        """Return the first enabled filtered index, or ``0``."""
        visible = self._filtered()
        for index, (item_index, _) in enumerate(visible):
            if not _item_disabled(self.items[item_index]):
                return index
        return 0

    def _last_enabled_index(self) -> int:
        """Return the last enabled filtered index, or ``0``."""
        visible = self._filtered()
        for index in range(len(visible) - 1, -1, -1):
            item_index = visible[index][0]
            if not _item_disabled(self.items[item_index]):
                return index
        return 0

    def handle_keyboard(self, keyboard: "KeyboardEventData") -> bool:
        """Apply a keyboard event while this Options is focused.

        Up/down move the selection (skipping disabled); Home/End jump
        to the first/last enabled entry. Printable characters and
        backspace edit ``query`` when ``searchable``. Enter, tab,
        escape, and ``passthrough`` bindings are never consumed so hooks
        and focus navigation see them.

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
        if keyboard.matches("enter", "tab", "escape", "esc"):
            return False

        visible_count = len(self._filtered())
        if keyboard.matches("up"):
            self.move(-1)
            return True
        if keyboard.matches("down"):
            self.move(1)
            return True
        if keyboard.matches("home"):
            self.selected = self._first_enabled_index()
            return True
        if keyboard.matches("end"):
            self.selected = self._last_enabled_index() if visible_count else 0
            return True
        if not self.searchable:
            return False
        if keyboard.matches("backspace"):
            self.query = self.query[:-1]
            self.selected = 0
            self._ensure_enabled_selection()
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
            self._ensure_enabled_selection()
            return True
        return False

    def _entry_block(
        self,
        text: str,
        matched: tuple[int, ...],
    ) -> Any:
        """Build a ``TextBlock`` row, emphasizing fuzzy-matched chars."""
        from xnano.beta.core.content import Run, TextBlock

        # When repeating the symbol, bake it into every row and clear
        # Items' own highlight_symbol so columns stay aligned.
        prefix = self.highlight_symbol if self.repeat_highlight_symbol else ""
        display = prefix + text if prefix else text
        # Matched indices refer to the original item text — offset by
        # the baked-in prefix length.
        offset = len(prefix)
        adjusted = tuple(index + offset for index in matched)

        if not adjusted or self.match_color is None:
            return TextBlock.from_plain(display)

        def make_run(segment: str, emphasized: bool) -> Run:
            return Run(
                text=segment,
                color=self.match_color if emphasized else None,
                modifiers=("bold",) if emphasized else (),
            )

        matched_set = set(adjusted)
        runs: list[Run] = []
        segment = ""
        segment_emphasized = False
        for index, character in enumerate(display):
            emphasized = index in matched_set
            if segment and emphasized != segment_emphasized:
                runs.append(make_run(segment, segment_emphasized))
                segment = ""
            segment += character
            segment_emphasized = emphasized
        if segment:
            runs.append(make_run(segment, segment_emphasized))
        return TextBlock(lines=(tuple(runs),))

    def _compose_items(
        self,
        ctx: "ComponentRenderContext",
        *,
        visible: list[tuple[int, tuple[int, ...]]] | None = None,
    ) -> Any:
        """Compose the ``Items`` content for the current filtered view."""
        from xnano.beta.core.content import Items

        del ctx  # available for subclasses / future sizing
        pairs = self._filtered() if visible is None else visible
        selected: int | None
        if pairs:
            selected = max(0, min(self.selected, len(pairs) - 1))
        else:
            selected = None

        entries = tuple(
            self._entry_block(
                _item_text(self.items[index]),
                matched,
            )
            for index, matched in pairs
        )
        # When repeating the symbol, Items should not also prepend one
        # on the selected row (already baked into each entry).
        symbol = "" if self.repeat_highlight_symbol else self.highlight_symbol
        return Items(
            items=entries,
            selected=selected,
            color=self.color,
            background=self.background,
            highlight_color=self.highlight_color,
            highlight_background=self.highlight_background,
            highlight_symbol=symbol,
            z=self.z,
            visible=self.visible,
        )

    def _compose_query_row(self) -> Any:
        """Compose the optional filter query row above the list."""
        from xnano.beta.core.content import Run, TextBlock

        caret = "▌" if self._input_focused else ""
        if self.query or caret:
            return TextBlock(
                lines=((Run(text=self.query + caret),),),
            )
        query_modifiers: tuple[CharacterModifier, ...] = ("dim",)
        return TextBlock(
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

    def compose(self, ctx: "ComponentRenderContext") -> Any:
        """Compose interface-neutral Content for this Options.

        Args:
            ctx: Render-time scope for this paint.

        Returns:
            An ``Items`` list, or a vertical ``Stack`` with a query row
            above the list when ``searchable``.
        """
        from xnano.beta.core.content import Stack

        items_content = self._compose_items(ctx)
        if not self.searchable:
            return items_content
        return Stack(
            children=(self._compose_query_row(), items_content),
            direction="vertical",
            z=self.z,
            visible=self.visible,
        )


# Migration alias — ``Select`` remains importable during the beta cutover.
Select = Options


__all__ = (
    "Option",
    "OptionItem",
    "Options",
    "OptionsDirection",
    "Select",
    "get_fuzzy_match",
)
