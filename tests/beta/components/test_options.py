"""Tests for beta ``Options`` and fuzzy filtering."""

from __future__ import annotations

from typing import Any

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.options import (
    Option,
    Options,
    Select,
    get_fuzzy_match,
)
from xnano.beta.core.content import Items, Stack
from xnano.beta.types import Area, is_focusable_component


def _ctx() -> ComponentRenderContext[Any]:
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
    options = Options(items=_ITEMS)
    assert options.visible_items == _ITEMS


def test_query_filters_and_ranks() -> None:
    options = Options(items=_ITEMS, query="dark")
    assert set(options.visible_items) == {"dark", "solarized dark"}
    assert options.visible_items[0] == "dark"


def test_filter_false_ignores_query() -> None:
    options = Options(items=_ITEMS, query="dark", filter=False)
    assert options.visible_items == _ITEMS


def test_value_reads_selected_filtered_item() -> None:
    options = Options(items=_ITEMS, query="sol")
    assert options.value == "solarized dark"
    options.selected = 1
    assert options.value == "solarized light"


def test_value_none_when_nothing_matches() -> None:
    options = Options(items=_ITEMS, query="zzz")
    assert options.value is None
    assert options.selected_item is None


def test_option_value_label_separation() -> None:
    options = Options(
        items=(
            Option(label="Dark Mode", value="dark"),
            Option(label="Light Mode", value="light"),
        ),
    )
    assert options.value == "dark"
    assert options.selected_item is not None
    assert isinstance(options.selected_item, Option)
    options.select(1)
    assert options.value == "light"


def test_option_value_defaults_to_label() -> None:
    options = Options(items=(Option(label="only"),))
    assert options.value == "only"


def test_bottom_to_top_reverses_display_order() -> None:
    options = Options(
        items=("a", "b", "c"),
        direction="bottom_to_top",
    )
    assert options.visible_items == ("c", "b", "a")
    assert options.filtered == (2, 1, 0)


# ---------------------------------------------------------------------------
# Movement / select / disabled
# ---------------------------------------------------------------------------


def test_move_advances_and_retreats_selection() -> None:
    options = Options(items=_ITEMS, searchable=False)
    options.move(1)
    assert options.selected == 1
    options.move(-1)
    assert options.selected == 0


def test_move_clamps_to_filtered_bounds() -> None:
    options = Options(items=_ITEMS, searchable=False)
    options.move(1000)
    assert options.selected == len(_ITEMS) - 1
    options.move(-1000)
    assert options.selected == 0


def test_move_on_empty_filtered_view_resets_to_zero() -> None:
    options = Options(items=_ITEMS, query="zzz-no-match")
    options.selected = 3
    options.move(1)
    assert options.selected == 0


def test_move_skips_disabled_entries() -> None:
    options = Options(
        items=(
            Option("a"),
            Option("b", disabled=True),
            Option("c"),
        ),
        searchable=False,
    )
    options.move(1)
    assert options.selected == 2
    assert options.value == "c"
    options.move(-1)
    assert options.selected == 0
    assert options.value == "a"


def test_select_rejects_disabled_index() -> None:
    options = Options(
        items=(
            Option("a"),
            Option("b", disabled=True),
            Option("c"),
        ),
        searchable=False,
    )
    options.select(1)
    assert options.selected == 0
    options.select(2)
    assert options.selected == 2


def test_clear_query_resets_filter_and_selection() -> None:
    options = Options(items=_ITEMS, query="dark", selected=1)
    options.clear_query()
    assert options.query == ""
    assert options.selected == 0
    assert options.visible_items == _ITEMS


def test_filtered_returns_visible_indices() -> None:
    options = Options(items=_ITEMS, searchable=False)
    assert options.filtered == tuple(range(len(_ITEMS)))


def test_filtered_narrows_with_query() -> None:
    options = Options(items=_ITEMS, query="dark")
    assert set(options.filtered) <= set(range(len(_ITEMS)))
    assert 0 in options.filtered  # "dark" itself


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------


def test_up_down_move_selection() -> None:
    options = Options(items=_ITEMS)
    assert options.handle_keyboard(_kbd(matches={"down"})) is True
    assert options.selected == 1
    assert options.handle_keyboard(_kbd(matches={"up"})) is True
    assert options.selected == 0
    assert options.handle_keyboard(_kbd(matches={"up"})) is True
    assert options.selected == 0


def test_home_end_jump_to_edges() -> None:
    options = Options(items=_ITEMS, searchable=False, selected=2)
    assert options.handle_keyboard(_kbd(matches={"home"})) is True
    assert options.selected == 0
    assert options.handle_keyboard(_kbd(matches={"end"})) is True
    assert options.selected == len(_ITEMS) - 1


def test_home_end_skip_disabled_edges() -> None:
    options = Options(
        items=(
            Option("a", disabled=True),
            Option("b"),
            Option("c"),
            Option("d", disabled=True),
        ),
        searchable=False,
        selected=2,
    )
    assert options.handle_keyboard(_kbd(matches={"home"})) is True
    assert options.selected == 1
    assert options.handle_keyboard(_kbd(matches={"end"})) is True
    assert options.selected == 2


def test_typing_edits_query_and_resets_selection() -> None:
    options = Options(items=_ITEMS, selected=3)
    assert options.handle_keyboard(_kbd(character="d")) is True
    assert options.query == "d"
    assert options.selected == 0
    assert options.handle_keyboard(_kbd(matches={"backspace"})) is True
    assert options.query == ""


def test_navigation_keys_fall_through() -> None:
    options = Options(items=_ITEMS)
    for key in ("enter", "esc", "escape", "tab"):
        assert options.handle_keyboard(_kbd(matches={key})) is False


def test_passthrough_keys_fall_through() -> None:
    options = Options(items=_ITEMS, passthrough=("ctrl+c", "up"))
    assert options.handle_keyboard(_kbd(matches={"ctrl+c"})) is False
    # up is passthrough — must not move selection
    assert options.handle_keyboard(_kbd(matches={"up"})) is False
    assert options.selected == 0


def test_not_searchable_ignores_typing() -> None:
    options = Options(items=_ITEMS, searchable=False)
    assert options.handle_keyboard(_kbd(character="d")) is False
    assert options.query == ""
    assert options.handle_keyboard(_kbd(matches={"down"})) is True


def test_options_is_focusable_component() -> None:
    assert is_focusable_component(Options(items=_ITEMS))
    assert not is_focusable_component(Options(items=_ITEMS, focusable=False))


def test_select_alias_is_options() -> None:
    assert Select is Options


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------


def test_compose_searchable_stacks_query_row() -> None:
    options = Options(items=_ITEMS, query="da")
    content = options.compose(_ctx())
    assert isinstance(content, Stack)
    assert isinstance(content.children[1], Items)


def test_compose_not_searchable_is_items_only() -> None:
    options = Options(items=_ITEMS, searchable=False)
    content = options.compose(_ctx())
    assert isinstance(content, Items)
    assert content.selected == 0


def test_match_characters_are_emphasized() -> None:
    options = Options(items=("dark",), query="dr", searchable=False)
    content = options.compose(_ctx())
    assert isinstance(content, Items)
    (entry,) = content.items
    runs = entry.lines[0]
    emphasized = [run.text for run in runs if run.color == "cyan"]
    assert emphasized == ["d", "r"]


def _entry_text(entry: Any) -> str:
    if getattr(entry, "lines", None):
        return "".join(run.text for run in entry.lines[0])
    return str(getattr(entry, "text", entry))


def test_repeat_highlight_symbol_bakes_prefix() -> None:
    options = Options(
        items=("a", "b"),
        searchable=False,
        repeat_highlight_symbol=True,
        highlight_symbol="* ",
    )
    content = options.compose(_ctx())
    assert isinstance(content, Items)
    assert content.highlight_symbol == ""
    texts = [_entry_text(entry) for entry in content.items]
    assert texts == ["* a", "* b"]


# ---------------------------------------------------------------------------
# Offscreen smoke
# ---------------------------------------------------------------------------


def test_options_offscreen_smoke_render() -> None:
    from xnano.beta.core.runtime import Runtime

    options = Options(items=_ITEMS, searchable=False)
    runtime = Runtime.offscreen(width=40, height=12)
    try:
        frame = runtime.render(options)
        assert frame is not None
        output = runtime.get_output()
        assert "dark" in output
        assert "dracula" in output
    finally:
        runtime.close()
