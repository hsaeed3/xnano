"""Tests for the Select component and fuzzy filtering."""

from __future__ import annotations

from typing import Any

from xnano._types import Area, is_focusable_component
from xnano.components.abstract import ComponentRenderContext
from xnano.components.select import Select, get_fuzzy_match
from xnano.core.content import Items, Stack
from xnano.terminal.content_lower import lower_content
from xnano.terminal.nodes import ListNode


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=30, height=10))


def _kbd(**kwargs: Any) -> Any:
    character = kwargs.get("character")
    matches = set(kwargs.get("matches", ()))

    class _K:
        def __init__(self) -> None:
            self.kind = kwargs.get("kind", "press")
            self.character = character

        def matches(self, *bindings: str) -> bool:
            return any(binding in matches for binding in bindings)

    return _K()


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------


def test_empty_query_matches_everything() -> None:
    assert get_fuzzy_match("", "anything") == (0, ())


def test_subsequence_match_returns_indices() -> None:
    match = get_fuzzy_match("tp", "theme_picker")
    assert match is not None
    assert match[1] == (0, 6)


def test_non_match_returns_none() -> None:
    assert get_fuzzy_match("xyz", "theme") is None


def test_consecutive_beats_scattered() -> None:
    scattered = get_fuzzy_match("abc", "a_b_c_long")
    consecutive = get_fuzzy_match("abc", "xxabcxxxxx")
    assert scattered is not None and consecutive is not None
    assert consecutive[0] > scattered[0]


# ---------------------------------------------------------------------------
# Filtering & selection
# ---------------------------------------------------------------------------

_ITEMS = ("dark", "light", "solarized dark", "solarized light", "dracula")


def test_no_query_keeps_original_order() -> None:
    select = Select(items=_ITEMS)
    assert select.visible_items == _ITEMS


def test_query_filters_and_ranks() -> None:
    select = Select(items=_ITEMS, query="dark")
    assert set(select.visible_items) == {"dark", "solarized dark"}
    assert select.visible_items[0] == "dark"


def test_filter_false_ignores_query() -> None:
    select = Select(items=_ITEMS, query="dark", filter=False)
    assert select.visible_items == _ITEMS


def test_value_reads_selected_filtered_item() -> None:
    select = Select(items=_ITEMS, query="sol")
    assert select.value == "solarized dark"
    select.selected = 1
    assert select.value == "solarized light"


def test_value_none_when_nothing_matches() -> None:
    select = Select(items=_ITEMS, query="zzz")
    assert select.value is None


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------


def test_up_down_move_selection() -> None:
    select = Select(items=_ITEMS)
    assert select.handle_keyboard(_kbd(matches={"down"})) is True
    assert select.selected == 1
    assert select.handle_keyboard(_kbd(matches={"up"})) is True
    assert select.selected == 0
    assert select.handle_keyboard(_kbd(matches={"up"})) is True
    assert select.selected == 0


def test_typing_edits_query_and_resets_selection() -> None:
    select = Select(items=_ITEMS, selected=3)
    assert select.handle_keyboard(_kbd(character="d")) is True
    assert select.query == "d"
    assert select.selected == 0
    assert select.handle_keyboard(_kbd(matches={"backspace"})) is True
    assert select.query == ""


def test_navigation_keys_fall_through() -> None:
    select = Select(items=_ITEMS)
    for key in ("enter", "esc", "tab"):
        assert select.handle_keyboard(_kbd(matches={key})) is False


def test_not_searchable_ignores_typing() -> None:
    select = Select(items=_ITEMS, searchable=False)
    assert select.handle_keyboard(_kbd(character="d")) is False
    assert select.query == ""
    assert select.handle_keyboard(_kbd(matches={"down"})) is True


def test_select_is_focusable_component() -> None:
    assert is_focusable_component(Select(items=_ITEMS))
    assert not is_focusable_component(Select(items=_ITEMS, focusable=False))


# ---------------------------------------------------------------------------
# Compose & lowering
# ---------------------------------------------------------------------------


def test_compose_searchable_stacks_query_row() -> None:
    select = Select(items=_ITEMS, query="da")
    content = select.compose(_ctx())
    assert isinstance(content, Stack)
    assert isinstance(content.children[1], Items)


def test_compose_not_searchable_is_items_only() -> None:
    select = Select(items=_ITEMS, searchable=False)
    content = select.compose(_ctx())
    assert isinstance(content, Items)
    assert content.selected == 0


def test_match_characters_are_emphasized() -> None:
    select = Select(items=("dark",), query="dr", searchable=False)
    content = select.compose(_ctx())
    assert isinstance(content, Items)
    (entry,) = content.items
    runs = entry.lines[0]
    emphasized = [run.text for run in runs if run.color == "cyan"]
    assert emphasized == ["d", "r"]


def test_items_content_lowers_to_list_node() -> None:
    select = Select(items=_ITEMS, searchable=False)
    node = lower_content(select.compose(_ctx()))
    assert isinstance(node, ListNode)
    assert node.selected == 0
    assert len(node.items) == len(_ITEMS)


def test_filtered_returns_visible_indices() -> None:
    select = Select(items=_ITEMS, searchable=False)
    assert select.filtered == tuple(range(len(_ITEMS)))


def test_filtered_narrows_with_query() -> None:
    select = Select(items=_ITEMS, query="dark")
    assert set(select.filtered) <= set(range(len(_ITEMS)))
    assert 0 in select.filtered  # "dark" itself


def test_move_advances_and_retreats_selection() -> None:
    select = Select(items=_ITEMS, searchable=False)
    select.move(1)
    assert select.selected == 1
    select.move(-1)
    assert select.selected == 0


def test_move_clamps_to_filtered_bounds() -> None:
    select = Select(items=_ITEMS, searchable=False)
    select.move(1000)
    assert select.selected == len(_ITEMS) - 1
    select.move(-1000)
    assert select.selected == 0


def test_move_on_empty_filtered_view_resets_to_zero() -> None:
    select = Select(items=_ITEMS, query="zzz-no-match")
    select.selected = 3
    select.move(1)
    assert select.selected == 0
