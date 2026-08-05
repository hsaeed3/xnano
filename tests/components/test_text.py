"""Tests for Text component."""

from __future__ import annotations

from typing import Any

import pytest

from xnano.actions import Action
from xnano.area import Area
from xnano.components.component import ComponentRenderContext
from xnano.components.text import Text
from xnano.core import Runtime
from xnano.core.content import Panel, TextBlock
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.hooks import on_keyboard


def _ctx() -> ComponentRenderContext[Any]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=3))


def _kbd(**kwargs: Any) -> Any:
    """Build a duck-typed keyboard event."""
    character = kwargs.get("character")
    matches = set(kwargs.get("matches", ()))
    kind = kwargs.get("kind", "press")
    modifiers = list(kwargs.get("modifiers", ()))

    class _K:
        def __init__(self) -> None:
            self.kind = kind
            self.character = character
            self.modifiers = modifiers

        def matches(self, *bindings: str) -> bool:
            return any(binding in matches for binding in bindings)

    return _K()


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_plain_construction() -> None:
    text = Text("hello", foreground="cyan")
    assert text.content == "hello"
    assert text.foreground == "cyan"
    assert text.input is False
    assert text.focusable is False
    assert text.mask is None
    assert text.max_length is None
    assert text.read_only is False
    assert text.tab_size == 4


def test_nested_spans() -> None:
    text = Text([Text("ok", foreground="green"), Text(" ready")])
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


def test_editor_mode_transition_preserves_native_text() -> None:
    text = Text("draft", input=True, multiline=True)
    assert text._editor is not None
    text._editor.set_text("native edit")
    object.__setattr__(text, "content", "")
    text._sync_editor_state()
    assert text.content == "native edit"

    text.multiline = False
    text._sync_editor_state()
    assert text.content == "native edit"
    assert text._editor is None

    replaced = Text("old", input=True, multiline=True)
    object.__setattr__(replaced, "content", "new")
    replaced._sync_editor_state()
    assert replaced._editor is not None
    assert replaced._editor.text() == "new"


def test_value_clamps_max_length() -> None:
    text = Text("", input=True, max_length=3)
    text.value = "abcdef"
    assert text.value == "abc"
    assert Text([Text("nested")]).value == ""


def test_multiline_value_assignment_updates_editor_and_clamps_cursor() -> None:
    text = Text("old", input=True, multiline=True, cursor=99)
    text.value = "new"
    assert text._editor is not None
    assert text._editor.text() == "new"
    assert text.cursor == 3


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


def test_paste_contract_without_editor_and_at_capacity() -> None:
    assert Text("", input=True).handle_paste("ignored") is False
    full = Text("abc", input=True, multiline=True, max_length=3)
    assert full.handle_paste("ignored") is True
    assert full.value == "abc"


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
    assert content.foreground == "gray"


def test_styled_placeholder_keeps_component_color() -> None:
    text = Text(
        "",
        input=True,
        placeholder=Text("search logs", foreground="yellow"),
    )
    content = text.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.text == "search logs"
    assert content.foreground == "yellow"
    assert "dim" in content.modifiers


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


@pytest.mark.parametrize(
    ("text", "mode"),
    (
        ("\x1b[31mred\x1b[0m", "ansi"),
        ("value = 1", "language"),
    ),
)
def test_markup_modes_render_styled_lines(text: str, mode: str) -> None:
    component = (
        Text(text, ansi=True)
        if mode == "ansi"
        else Text(text, language="python")
    )
    content = component.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.lines
    assert "".join(run.text for line in content.lines for run in line)


def test_compose_plain() -> None:
    text = Text("hello", foreground="cyan")
    content = text.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.text == "hello"
    assert content.foreground == "cyan"


def test_nested_text_shapes_preserve_rows_and_styles() -> None:
    single = Text(Text("nested", foreground="green")).compose(_ctx())
    assert isinstance(single, TextBlock)
    assert single.text == "nested"

    lines = Text(
        [
            Text("first\nsecond", foreground="cyan"),
            "third",
        ]
    ).compose(_ctx())
    assert isinstance(lines, TextBlock)
    assert ["".join(run.text for run in line) for line in lines.lines] == [
        "first",
        "second",
        "third",
    ]
    assert lines.lines[0][0].foreground == "cyan"

    leaf = Text("leaf", foreground="green")
    assert leaf._as_children() == [leaf]
    assert leaf._to_span_node().text == "leaf"
    nested = Text(leaf)
    assert nested._as_children() == [leaf]
    assert nested._to_span_node().text == "leaf"
    assert isinstance(Text(["a", "b"])._to_line_node(_ctx()), TextBlock)
    assert Text([leaf])._to_span_node().text == ""
    assert Text("line")._to_line_node(_ctx()).text == "line"

    nested_lines = Text([Text([Text("ignored")]), Text("shown\nnext")])
    content = nested_lines.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert ["".join(run.text for run in line) for line in content.lines] == [
        "shown",
        "next",
    ]
    assert (
        nested_lines._build_line_nodes_from_leaf_children(
            [Text([Text("ignored")])]
        )
        == []
    )


def test_placeholder_normalization_rejects_nested_content() -> None:
    assert Text("", placeholder="search")._placeholder_string() == "search"
    assert (
        Text("", placeholder=Text([Text("nested")]))._placeholder_string()
        is None
    )
    non_string = Text([Text("value")], input=True)
    assert non_string._input_display_content() == ("", None, False)


def test_fill_wraps_text_without_losing_content() -> None:
    content = Text("alert", background="red", fill=True).compose(_ctx())
    assert isinstance(content, Panel)
    assert content.background == "red"
    assert isinstance(content.child, TextBlock)
    assert content.child.text == "alert"


@pytest.mark.parametrize(
    ("binding", "start", "cursor", "expected", "expected_cursor"),
    (
        ("backspace", "abcd", 2, "acd", 1),
        ("delete", "abcd", 2, "abd", 2),
        ("left", "abcd", 2, "abcd", 1),
        ("right", "abcd", 2, "abcd", 3),
        ("home", "abcd", 2, "abcd", 0),
        ("end", "abcd", 2, "abcd", 4),
    ),
)
def test_single_line_editor_commands(
    binding: str,
    start: str,
    cursor: int,
    expected: str,
    expected_cursor: int,
) -> None:
    text = Text(start, input=True, cursor=cursor)
    assert text.handle_keyboard(_kbd(matches={binding})) is True
    assert text.value == expected
    assert text.cursor == expected_cursor


def test_non_input_and_navigation_keys_bubble() -> None:
    assert Text("label").handle_keyboard(_kbd(character="x")) is False
    text = Text("value", input=True)
    assert text.handle_keyboard(_kbd(matches={"enter"})) is False
    assert text.handle_keyboard(_kbd(character="x", kind="release")) is False
    assert (
        text.handle_keyboard(_kbd(character="x", modifiers=("ctrl",))) is False
    )
    assert text.value == "value"

    non_string = Text([Text("value")], input=True)
    assert non_string.handle_keyboard(_kbd(character="x")) is False

    read_only = Text("value", input=True, read_only=True)
    assert read_only.handle_keyboard(_kbd(matches={"backspace"})) is True
    assert read_only.handle_keyboard(_kbd(matches={"delete"})) is True
    assert read_only.value == "value"

    start = Text("value", input=True, cursor=0)
    assert start.handle_keyboard(_kbd(matches={"backspace"})) is True
    assert start.value == "value"
    end = Text("value", input=True, cursor=5)
    assert end.handle_keyboard(_kbd(matches={"delete"})) is True
    assert end.value == "value"


def test_terminal_node_matches_component_composition() -> None:
    text = Text("terminal", foreground="cyan")
    assert text.get_terminal_node(_ctx()) == text.compose(_ctx())


def test_multiline_editor_drives_composed_preview() -> None:
    class Editor(BaseGrid, direction="vertical"):
        notes: Text = Field(
            default_factory=lambda: Text(
                "",
                input=True,
                multiline=True,
                placeholder=Text("release notes", foreground="yellow"),
                max_length=12,
                tab_size=2,
            ),
            group="notes",
            height=3,
        )
        preview: str = Field(default="Nothing saved", height=2)

        @on_keyboard("ctrl+s")
        def save_notes(self) -> None:
            self.preview = self.notes.value

    runtime = Runtime.offscreen(40, 6)
    try:
        editor = Editor()
        runtime.set_root(editor)
        assert runtime.focus("notes")
        runtime.render()

        assert editor.notes.handle_paste("one\ttwo\nthree") is True
        runtime.perform(Action.keyboard("ctrl+s"))
        frame = runtime.render()

        assert editor.notes.value == "one two\nthre"
        assert "one two" in frame.text
        assert editor.notes.cursor_position is not None
    finally:
        runtime.close()


def test_wrapped_text_preserves_indentation_after_newline() -> None:
    """Leading whitespace after a newline survives wrapping (#128).

    ``Text`` wraps by default; the wrapping renderer used to trim leading
    whitespace from every line, dropping authored indentation.
    """
    runtime = Runtime.offscreen(24, 4)
    try:
        frame = runtime.render(Text("a\n    indented"))
        assert "    indented" in frame.text
    finally:
        runtime.close()
