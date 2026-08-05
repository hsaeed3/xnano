"""Tests for ``Dropdown`` open/close and selection."""

from __future__ import annotations

from typing import Any

from xnano.area import Area
from xnano.components.component import ComponentRenderContext
from xnano.components.dropdown import Dropdown
from xnano.components.options import Option
from xnano.components.text import Text
from xnano.core.content import Items, Stack, TextBlock


def _ctx() -> ComponentRenderContext[Any]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=30, height=10))


def _kbd(**kwargs: Any) -> Any:
    character = kwargs.get("character")
    matches = set(kwargs.get("matches", ()))

    class _K:
        def __init__(self) -> None:
            self.kind = kwargs.get("kind", "press")
            self.character = character
            self.modifiers = list(kwargs.get("modifiers", ()))

        def matches(self, *bindings: str) -> bool:
            return any(binding in matches for binding in bindings)

    return _K()


_ITEMS = ("alpha", "beta", "gamma", "delta", "epsilon")


def test_starts_closed() -> None:
    dropdown = Dropdown(items=_ITEMS)
    assert dropdown.open is False


def test_closed_compose_shows_selected_label() -> None:
    dropdown = Dropdown(items=_ITEMS, selected=2)
    content = dropdown.compose(_ctx())
    assert isinstance(content, TextBlock)
    text = "".join(run.text for run in content.lines[0])
    assert text == "gamma"


def test_closed_compose_shows_placeholder_when_empty() -> None:
    dropdown = Dropdown(items=(), placeholder="pick one")
    content = dropdown.compose(_ctx())
    assert isinstance(content, TextBlock)
    text = "".join(run.text for run in content.lines[0])
    assert text == "pick one"


def test_closed_empty_dropdown_has_accessible_default_prompt() -> None:
    dropdown = Dropdown(items=())
    assert dropdown._placeholder_text() == ""
    assert _entry_text(dropdown.compose(_ctx())) == "select…"

    class Prompt:
        content = "choose service"

    dropdown.placeholder = Prompt()
    assert _entry_text(dropdown.compose(_ctx())) == "choose service"

    class StringPrompt:
        def __str__(self) -> str:
            return "choose region"

    dropdown.placeholder = StringPrompt()
    assert _entry_text(dropdown.compose(_ctx())) == "choose region"


def test_open_keys_expand_list() -> None:
    dropdown = Dropdown(items=_ITEMS)
    assert dropdown.handle_keyboard(_kbd(matches={"down"})) is True
    assert dropdown.open is True
    dropdown.open = False
    assert dropdown.handle_keyboard(_kbd(matches={"space"})) is True
    assert dropdown.open is True
    dropdown.open = False
    assert dropdown.handle_keyboard(_kbd(matches={"enter"})) is True
    assert dropdown.open is True


def test_open_compose_is_options_content() -> None:
    dropdown = Dropdown(items=_ITEMS, open=True, searchable=False)
    content = dropdown.compose(_ctx())
    assert isinstance(content, Items)
    assert content.selected == 0
    assert len(content.items) == len(_ITEMS)


def test_open_searchable_stacks_query_row() -> None:
    dropdown = Dropdown(items=_ITEMS, open=True, query="a")
    content = dropdown.compose(_ctx())
    assert isinstance(content, Stack)
    assert isinstance(content.children[1], Items)


def test_escape_closes_without_changing_selection() -> None:
    dropdown = Dropdown(items=_ITEMS, open=True, selected=2, searchable=False)
    assert dropdown.handle_keyboard(_kbd(matches={"escape"})) is True
    assert dropdown.open is False
    assert dropdown.selected == 2
    assert dropdown.value == "gamma"


def test_enter_accepts_and_closes() -> None:
    dropdown = Dropdown(items=_ITEMS, open=True, selected=1, searchable=False)
    # enter bubbles so hooks can read value
    assert dropdown.handle_keyboard(_kbd(matches={"enter"})) is False
    assert dropdown.open is False
    assert dropdown.value == "beta"


def test_enter_keeps_open_when_close_on_select_false() -> None:
    dropdown = Dropdown(
        items=_ITEMS,
        open=True,
        selected=1,
        searchable=False,
        close_on_select=False,
    )
    # enter remains in default close_keys, but close_on_select wins.
    assert dropdown.handle_keyboard(_kbd(matches={"enter"})) is False
    assert dropdown.open is True
    assert dropdown.value == "beta"


def test_open_movement_reuses_options() -> None:
    dropdown = Dropdown(items=_ITEMS, open=True, searchable=False)
    assert dropdown.handle_keyboard(_kbd(matches={"down"})) is True
    assert dropdown.selected == 1
    assert dropdown.open is True


def test_closed_ignores_typing() -> None:
    dropdown = Dropdown(items=_ITEMS, searchable=True)
    assert dropdown.handle_keyboard(_kbd(character="a")) is False
    assert dropdown.query == ""
    assert dropdown.open is False


def test_open_typing_filters() -> None:
    dropdown = Dropdown(items=_ITEMS, open=True, searchable=True)
    assert dropdown.handle_keyboard(_kbd(character="g")) is True
    assert dropdown.query == "g"
    assert "gamma" in dropdown.visible_items


def test_max_visible_windows_open_list() -> None:
    dropdown = Dropdown(
        items=_ITEMS,
        open=True,
        searchable=False,
        max_visible=2,
        selected=0,
    )
    content = dropdown.compose(_ctx())
    assert isinstance(content, Items)
    assert len(content.items) == 2


def test_window_selection_offsets_handle_short_and_empty_views() -> None:
    short = Dropdown(items=("a", "b"), max_visible=5)
    window = short._windowed_visible()
    assert len(window) == 2
    assert short._window_selected_offset(window) == 0

    empty = Dropdown(items=(), max_visible=2)
    assert empty._window_selected_offset([]) is None
    assert empty._window_selected_offset([(99, ())]) is None

    long = Dropdown(items=_ITEMS, selected=4, max_visible=2)
    window = long._windowed_visible()
    assert [index for index, _ in window] == [3, 4]
    assert long._window_selected_offset(window) == 1
    assert long._window_selected_offset(window[:1]) == 0

    centered = Dropdown(items=_ITEMS, selected=4, max_visible=3)
    assert [index for index, _ in centered._windowed_visible()] == [2, 3, 4]


def _entry_text(entry: Any) -> str:
    if getattr(entry, "lines", None):
        return "".join(run.text for run in entry.lines[0])
    return str(getattr(entry, "text", entry))


def test_max_visible_follows_selection() -> None:
    dropdown = Dropdown(
        items=_ITEMS,
        open=True,
        searchable=False,
        max_visible=2,
        selected=4,
    )
    content = dropdown.compose(_ctx())
    assert isinstance(content, Items)
    assert len(content.items) == 2
    # Window should include the last item.
    texts = [_entry_text(entry) for entry in content.items]
    assert "epsilon" in texts
    # Global selection is preserved.
    assert dropdown.selected == 4


def test_disabled_skipped_while_open() -> None:
    dropdown = Dropdown(
        items=(
            Option("a"),
            Option("b", disabled=True),
            Option("c"),
        ),
        open=True,
        searchable=False,
    )
    dropdown.move(1)
    assert dropdown.selected == 2
    assert dropdown.value == "c"


def test_value_available_when_closed() -> None:
    dropdown = Dropdown(items=_ITEMS, selected=3)
    assert dropdown.open is False
    assert dropdown.value == "delta"


def test_text_placeholder_and_custom_keyboard_policy() -> None:
    dropdown = Dropdown(
        items=(),
        placeholder=Text("choose target"),
        close_keys=("left",),
        passthrough=("ctrl+p",),
    )
    assert _entry_text(dropdown.compose(_ctx())) == "choose target"

    assert (
        dropdown.handle_keyboard(_kbd(matches={"down"}, kind="release"))
        is False
    )
    assert dropdown.open is False
    assert dropdown.handle_keyboard(_kbd(matches={"down"})) is True
    assert dropdown.open is True
    assert dropdown.handle_keyboard(_kbd(matches={"ctrl+p"})) is False
    assert dropdown.open is True
    assert dropdown.handle_keyboard(_kbd(matches={"left"})) is True
    assert dropdown.open is False


def test_dropdown_offscreen_smoke_render() -> None:
    from xnano.core.runtime import Runtime

    dropdown = Dropdown(items=_ITEMS, open=True, searchable=False)
    runtime = Runtime.offscreen(width=40, height=12)
    try:
        frame = runtime.render(dropdown)
        assert frame is not None
        output = runtime.get_output()
        assert "alpha" in output
        assert "epsilon" in output
    finally:
        runtime.close()


def test_dropdown_closed_offscreen_smoke_render() -> None:
    from xnano.core.runtime import Runtime

    dropdown = Dropdown(
        items=_ITEMS,
        selected=1,
        searchable=False,
    )
    runtime = Runtime.offscreen(width=40, height=6)
    try:
        frame = runtime.render(dropdown)
        assert frame is not None
        output = runtime.get_output()
        assert "beta" in output
    finally:
        runtime.close()
