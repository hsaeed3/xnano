"""Tests for native-editor-backed Text(input=True, multiline=True)."""

from __future__ import annotations

from typing import Any

from xnano._types import Area, is_input_text
from xnano.components.abstract import ComponentRenderContext
from xnano.components.text import Text
from xnano.core.content import Native
from xnano.terminal.nodes import EditorNode


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=6))


# ---------------------------------------------------------------------------
# Construction & focus protocol
# ---------------------------------------------------------------------------


def test_multiline_input_creates_editor() -> None:
    text = Text("hello\nworld", input=True, multiline=True)
    assert text._editor is not None
    assert text.value == "hello\nworld"


def test_display_text_has_no_editor() -> None:
    assert Text("hello")._editor is None


def test_focus_protocol_flags() -> None:
    multiline = Text("", input=True, multiline=True)
    single = Text("", input=True)
    display = Text("hi")
    assert multiline.focusable and multiline.owns_cursor
    assert single.focusable and not single.owns_cursor
    assert not display.focusable
    assert is_input_text(multiline)
    assert is_input_text(single)
    assert not is_input_text(display)


def test_multiline_without_input_is_display_only() -> None:
    text = Text("a\nb", multiline=True)
    assert text._editor is None
    assert not text.focusable


# ---------------------------------------------------------------------------
# Value round-trip & paste
# ---------------------------------------------------------------------------


def test_value_setter_round_trip() -> None:
    text = Text("start", input=True, multiline=True)
    text.value = "replaced\ncontent"
    assert text.value == "replaced\ncontent"
    assert text.content == "replaced\ncontent"


def test_handle_paste_inserts_at_cursor() -> None:
    text = Text("ab", input=True, multiline=True)
    assert text.handle_paste("cd") is True
    assert text.value == "abcd"
    assert text.content == "abcd"


def test_handle_paste_without_editor_is_unconsumed() -> None:
    text = Text("ab", input=True)
    assert text.handle_paste("cd") is False
    assert text.value == "ab"


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------


def test_duck_typed_keyboard_falls_through_for_editor() -> None:
    """Editor path needs a native key event; duck-typed events fall
    through unconsumed so hooks still see them."""

    class _K:
        kind = "press"
        character = "x"
        _native_event = None

        def matches(self, *bindings: str) -> bool:
            return False

    text = Text("", input=True, multiline=True)
    event: Any = _K()
    assert text.handle_keyboard(event) is False


# ---------------------------------------------------------------------------
# Compose / render node
# ---------------------------------------------------------------------------


def test_compose_returns_editor_node() -> None:
    text = Text("one\ntwo", input=True, multiline=True, rows=5)
    content = text.compose(_ctx())
    assert isinstance(content, Native)
    assert content.interface_kind == "tui"
    assert isinstance(content.payload, EditorNode)
    size = content.payload.measure()
    assert size.width == 3
    assert size.height == 5


def test_editor_node_measures_content_without_rows() -> None:
    text = Text("one\ntwo\nthree", input=True, multiline=True)
    content = text.compose(_ctx())
    assert isinstance(content, Native)
    size = content.payload.measure()
    assert size.width == 5
    assert size.height == 3
