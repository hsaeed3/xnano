"""Tests for editable Text(input=True) and display helpers."""

from __future__ import annotations

from typing import Any

from xnano._types import Area, apply_text_keyboard
from xnano.components.abstract import ComponentRenderContext
from xnano.components.text import Text
from xnano.tui.nodes import ParagraphNode


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=3))


def _kbd(**kwargs: Any) -> Any:
    """Build a duck-typed keyboard event for apply_text_keyboard."""
    character = kwargs.get("character")
    matches = set(kwargs.get("matches", ()))
    kind = kwargs.get("kind", "press")

    class _K:
        def __init__(self) -> None:
            self.kind = kind
            self.character = character

        def matches(self, *bindings: str) -> bool:
            return any(binding in matches for binding in bindings)

    return _K()


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_input_defaults() -> None:
    text = Text("hi", input=True, placeholder="name")
    assert text.input is True
    assert text.placeholder == "name"
    assert text.cursor is None
    assert text._input_focused is False


def test_value_property() -> None:
    text = Text("abc", input=True)
    assert text.value == "abc"
    text.value = "xyz"
    assert text.content == "xyz"


# ---------------------------------------------------------------------------
# Keyboard editing
# ---------------------------------------------------------------------------


def test_insert_character_at_end() -> None:
    text = Text("ab", input=True)
    assert apply_text_keyboard(text, _kbd(character="c")) is True
    assert text.content == "abc"
    assert text.cursor == 3


def test_insert_character_in_middle() -> None:
    text = Text("ac", input=True, cursor=1)
    assert apply_text_keyboard(text, _kbd(character="b")) is True
    assert text.content == "abc"
    assert text.cursor == 2


def test_backspace() -> None:
    text = Text("abc", input=True)
    assert apply_text_keyboard(text, _kbd(matches={"backspace"})) is True
    assert text.content == "ab"


def test_delete_forward() -> None:
    text = Text("abc", input=True, cursor=1)
    assert apply_text_keyboard(text, _kbd(matches={"delete"})) is True
    assert text.content == "ac"
    assert text.cursor == 1


def test_left_right_home_end() -> None:
    text = Text("abc", input=True, cursor=1)
    assert apply_text_keyboard(text, _kbd(matches={"left"})) is True
    assert text.cursor == 0
    assert apply_text_keyboard(text, _kbd(matches={"right"})) is True
    assert text.cursor == 1
    assert apply_text_keyboard(text, _kbd(matches={"end"})) is True
    assert text.cursor == 3
    assert apply_text_keyboard(text, _kbd(matches={"home"})) is True
    assert text.cursor == 0


def test_enter_and_tab_not_consumed() -> None:
    text = Text("x", input=True)
    assert apply_text_keyboard(text, _kbd(matches={"enter"})) is False
    assert apply_text_keyboard(text, _kbd(matches={"tab"})) is False
    assert text.content == "x"


def test_non_input_ignores_keys() -> None:
    text = Text("x", input=False)
    assert apply_text_keyboard(text, _kbd(character="a")) is False
    assert text.content == "x"


def test_handle_keyboard_delegates() -> None:
    text = Text("", input=True)
    assert text.handle_keyboard(_kbd(character="z")) is True
    assert text.content == "z"


# ---------------------------------------------------------------------------
# Display / get_node
# ---------------------------------------------------------------------------


def test_placeholder_when_empty_unfocused() -> None:
    text = Text("", input=True, placeholder="type here")
    node = text.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.text == "type here"
    assert node.color == "gray"


def test_placeholder_hidden_when_focused() -> None:
    text = Text("", input=True, placeholder="type here")
    text._input_focused = True
    node = text.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert "▌" in str(node.text)


def test_caret_inserted_when_focused() -> None:
    text = Text("hi", input=True, cursor=1)
    text._input_focused = True
    node = text.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.text == "h▌i"


def test_content_shown_when_unfocused_nonempty() -> None:
    text = Text("hello", input=True, placeholder="x")
    node = text.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.text == "hello"
