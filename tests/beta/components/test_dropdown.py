"""Tests for beta ``Dropdown`` open/close and selection."""

from __future__ import annotations

from typing import Any

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.dropdown import Dropdown
from xnano.beta.components.options import Option
from xnano.beta.core.content import Items, Stack, TextBlock
from xnano.beta.types import Area


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


def test_dropdown_offscreen_smoke_render() -> None:
    from xnano.beta.core.runtime import Runtime

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
    from xnano.beta.core.runtime import Runtime

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
