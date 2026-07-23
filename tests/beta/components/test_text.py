"""Tests for beta Text component."""

from __future__ import annotations

from typing import Any

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.text import Text
from xnano.beta.core import Runtime
from xnano.beta.core.content import TextBlock
from xnano.beta.types import Area


def _ctx() -> ComponentRenderContext[Any]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=3))


def _kbd(**kwargs: Any) -> Any:
    """Build a duck-typed keyboard event."""
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


def test_plain_construction() -> None:
    text = Text("hello", color="cyan")
    assert text.content == "hello"
    assert text.color == "cyan"
    assert text.input is False
    assert text.focusable is False
    assert text.mask is None
    assert text.max_length is None
    assert text.read_only is False
    assert text.tab_size == 4


def test_nested_spans() -> None:
    text = Text([Text("ok", color="green"), Text(" ready")])
    assert not text._is_leaf()
    children = text._as_children()
    assert len(children) == 2
    assert children[0].content == "ok"


def test_mutually_exclusive_modes() -> None:
    try:
        Text("x", ansi=True, markdown=True)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "invalid" in str(error)

    try:
        Text("x", input=True, language="python")
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "invalid" in str(error)


# ---------------------------------------------------------------------------
# Value sync
# ---------------------------------------------------------------------------


def test_value_property_sync() -> None:
    text = Text("abc", input=True)
    assert text.value == "abc"
    text.value = "xyz"
    assert text.content == "xyz"
    assert text.value == "xyz"


def test_content_assignment_syncs_editor() -> None:
    text = Text("start", input=True, multiline=True)
    assert text._editor is not None
    text.content = "replaced"
    assert text.value == "replaced"
    assert text._editor.text() == "replaced"


def test_value_clamps_max_length() -> None:
    text = Text("", input=True, max_length=3)
    text.value = "abcdef"
    assert text.value == "abc"


# ---------------------------------------------------------------------------
# mask / max_length / read_only
# ---------------------------------------------------------------------------


def test_mask_display_preserves_value() -> None:
    text = Text("secret", input=True, mask="*")
    assert text.value == "secret"
    display, _, _ = text._input_display_content()
    assert display == "******"
    assert text.value == "secret"


def test_mask_with_caret() -> None:
    text = Text("ab", input=True, mask="•", cursor=1)
    text._input_focused = True
    display, _, _ = text._input_display_content()
    assert display == "•▌•"


def test_max_length_rejects_extra_chars() -> None:
    text = Text("ab", input=True, max_length=2)
    assert text.handle_keyboard(_kbd(character="c")) is True
    assert text.value == "ab"


def test_read_only_rejects_edits_but_moves_cursor() -> None:
    text = Text("hi", input=True, read_only=True, cursor=1)
    assert text.focusable is True
    assert text.handle_keyboard(_kbd(character="x")) is True
    assert text.value == "hi"
    assert text.handle_keyboard(_kbd(matches={"left"})) is True
    assert text.cursor == 0


def test_read_only_paste_consumed() -> None:
    text = Text("ab", input=True, multiline=True, read_only=True)
    assert text.handle_paste("zz") is True
    assert text.value == "ab"


# ---------------------------------------------------------------------------
# Keyboard / placeholder
# ---------------------------------------------------------------------------


def test_single_line_insert() -> None:
    text = Text("ab", input=True)
    assert text.handle_keyboard(_kbd(character="c")) is True
    assert text.content == "abc"
    assert text.cursor == 3


def test_passthrough_before_input() -> None:
    text = Text("x", input=True, passthrough=("left",))
    text.cursor = 1
    assert text.handle_keyboard(_kbd(matches={"left"})) is False
    assert text.cursor == 1


def test_placeholder_when_empty_unfocused() -> None:
    text = Text("", input=True, placeholder="type here")
    content = text.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.text == "type here"
    assert content.color == "gray"


def test_multiline_creates_editor() -> None:
    text = Text("hello\nworld", input=True, multiline=True)
    assert text._editor is not None
    assert text.owns_cursor is True
    assert text.value == "hello\nworld"
    content = text.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.text == "hello\nworld"


# ---------------------------------------------------------------------------
# Markup cache + compose
# ---------------------------------------------------------------------------


def test_markup_cache_reuses_lines() -> None:
    text = Text("# Title", markdown=True)
    first = text._markup_lines()
    second = text._markup_lines()
    assert first is second
    assert first is not None


def test_compose_plain() -> None:
    text = Text("hello", color="cyan")
    content = text.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.text == "hello"
    assert content.color == "cyan"


def test_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(40, 10)
    try:
        frame = runtime.render(Text("hello", color="cyan"))
        assert "hello" in frame.text
    finally:
        runtime.close()
