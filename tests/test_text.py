"""Tests for xnano.components.text — unified Text component."""

from __future__ import annotations

from xnano._types import Area
from xnano.components.abstract import ComponentRenderContext
from xnano.components.text import Text
from xnano.tui.nodes import (
    LineNode,
    ParagraphNode,
    SpanNode,
    TextNode,
)


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=80, height=24))


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_text_default_construction() -> None:
    t = Text()
    assert t.content == ""
    assert t.color is None
    assert t.background is None
    assert t.modifiers == ()
    assert t.align is None
    assert t.wrap is True


def test_text_leaf_string() -> None:
    t = Text("hello")
    assert t.content == "hello"


def test_text_with_all_style_params() -> None:
    t = Text(
        "x",
        color="red",
        background="black",
        modifiers=("bold",),
        align="center",
        wrap=False,
    )
    assert t.color == "red"
    assert t.background == "black"
    assert t.modifiers == ("bold",)
    assert t.align == "center"
    assert t.wrap is False


def test_text_list_of_strings() -> None:
    t = Text(["hello", "world"])
    assert isinstance(t.content, list)
    assert len(t.content) == 2


def test_text_nested_text_child() -> None:
    child = Text("child")
    t = Text(child)
    assert t.content is child


def test_text_is_mutable_component() -> None:
    t = Text("hi")
    t.content = "bye"
    assert t.content == "bye"


# ---------------------------------------------------------------------------
# _is_leaf
# ---------------------------------------------------------------------------


def test_is_leaf_with_string_content() -> None:
    assert Text("hello")._is_leaf()


def test_is_leaf_false_with_list() -> None:
    assert not Text([Text("a"), Text("b")])._is_leaf()


def test_is_leaf_false_with_nested_text() -> None:
    assert not Text(Text("inner"))._is_leaf()


# ---------------------------------------------------------------------------
# get_node — leaf mode → ParagraphNode with string
# ---------------------------------------------------------------------------


def test_leaf_get_node_returns_paragraph() -> None:
    node = Text("hello world").get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.text == "hello world"


def test_leaf_get_node_propagates_color() -> None:
    node = Text("hi", color="red").get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.color == "red"


def test_leaf_get_node_propagates_align() -> None:
    node = Text("hi", align="center").get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.align == "center"


def test_leaf_get_node_propagates_wrap() -> None:
    node = Text("hi", wrap=False).get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.wrap is False


def test_leaf_get_node_propagates_modifiers() -> None:
    node = Text("hi", modifiers=("bold", "italic")).get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert "bold" in node.modifiers


def test_empty_leaf_returns_paragraph() -> None:
    node = Text("").get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.text == ""


# ---------------------------------------------------------------------------
# get_node — single nested Text child delegates
# ---------------------------------------------------------------------------


def test_single_nested_text_delegates() -> None:
    inner = Text("inner", color="blue")
    node = Text(inner).get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.text == "inner"


# ---------------------------------------------------------------------------
# get_node — list of all-leaf strings → LineNode of SpanNodes in ParagraphNode
# ---------------------------------------------------------------------------


def test_list_of_strings_produces_paragraph_with_line() -> None:
    t = Text(["hello ", "world"])
    node = t.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert isinstance(node.text, LineNode)


def test_list_of_leaf_texts_produces_spans() -> None:
    t = Text([Text("hello ", color="red"), Text("world", color="blue")])
    node = t.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    line = node.text
    assert isinstance(line, LineNode)
    assert isinstance(line.content, list)
    assert all(isinstance(s, SpanNode) for s in line.content)


def test_list_of_leaf_texts_span_content() -> None:
    t = Text([Text("A"), Text("B")])
    node = t.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    line = node.text
    assert isinstance(line, LineNode)
    assert isinstance(line.content, list)
    contents = [s.content for s in line.content]
    assert "A" in contents
    assert "B" in contents


def test_mixed_string_and_text_list() -> None:
    t = Text(["plain", Text("styled", color="cyan")])
    node = t.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert isinstance(node.text, LineNode)


def test_list_with_embedded_newlines_produces_textnode() -> None:
    logo = "line one\nline two\nline three"
    t = Text(
        [
            Text("\n"),
            Text(logo, color="teal"),
            Text("footer"),
        ]
    )
    node = t.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert isinstance(node.text, TextNode)
    assert len(node.text.lines) == 6


def test_list_with_embedded_newlines_preserves_line_content() -> None:
    t = Text([Text("alpha\nbeta", color="red")])
    node = t.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    text_node = node.text
    assert isinstance(text_node, TextNode)
    assert text_node.lines[0].content == "alpha"
    assert text_node.lines[1].content == "beta"
    assert text_node.lines[0].color == "red"


# ---------------------------------------------------------------------------
# get_node — multi-line (paragraph) mode → ParagraphNode wrapping TextNode
# ---------------------------------------------------------------------------


def test_multiline_produces_textnode() -> None:
    t = Text(
        [
            Text([Text("Hello "), Text("world")]),
            Text("Second line"),
        ]
    )
    node = t.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert isinstance(node.text, TextNode)


def test_multiline_textnode_has_lines() -> None:
    t = Text(
        [
            Text([Text("span1"), Text("span2")]),
            Text([Text("span3")]),
        ]
    )
    node = t.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    text_node = node.text
    assert isinstance(text_node, TextNode)
    assert len(text_node.lines) == 2


def test_deeply_nested_paragraph_color_propagated() -> None:
    t = Text(
        [Text([Text("A"), Text("B")]), Text("C")],
        color="green",
    )
    node = t.get_terminal_node(_ctx())
    assert isinstance(node, ParagraphNode)
    assert node.color == "green"


# ---------------------------------------------------------------------------
# _to_span_node helper
# ---------------------------------------------------------------------------


def test_to_span_node_from_leaf() -> None:
    span = Text("hello", color="red")._to_span_node()
    assert isinstance(span, SpanNode)
    assert span.content == "hello"
    assert span.color == "red"


def test_to_span_node_from_nested_leaf() -> None:
    inner = Text("inner")
    span = Text(inner)._to_span_node()
    assert isinstance(span, SpanNode)
    assert span.content == "inner"


def test_to_span_node_from_list_yields_empty() -> None:
    span = Text([Text("a"), Text("b")])._to_span_node()
    assert isinstance(span, SpanNode)
    assert span.content == ""


# ---------------------------------------------------------------------------
# _to_line_node helper
# ---------------------------------------------------------------------------


def test_to_line_node_from_string() -> None:
    line = Text("hello")._to_line_node(_ctx())
    assert isinstance(line, LineNode)
    assert line.content == "hello"


def test_to_line_node_from_list_of_leaves() -> None:
    t = Text([Text("a"), Text("b")])
    line = t._to_line_node(_ctx())
    assert isinstance(line, LineNode)
    assert isinstance(line.content, list)


# ---------------------------------------------------------------------------
# LineNode.get_width
# ---------------------------------------------------------------------------


def test_line_node_get_width_string() -> None:
    node = LineNode(content="hello")
    assert node.get_width() == 5


def test_line_node_get_width_spans() -> None:
    node = LineNode(
        content=[
            SpanNode(content="ab"),
            SpanNode(content="cde"),
        ]
    )
    assert node.get_width() == 5


def test_line_node_get_width_none() -> None:
    node = LineNode(content=None)
    assert node.get_width() == 0


# ---------------------------------------------------------------------------
# TextNode.get_size
# ---------------------------------------------------------------------------


def test_text_node_get_size_from_lines() -> None:
    node = TextNode(
        lines=[
            LineNode(content="hello"),
            LineNode(content="world!"),
        ]
    )
    size = node.get_size()
    assert size.height == 2
    assert size.width == 6


def test_text_node_get_size_from_content_string() -> None:
    node = TextNode(content="abc\nde")
    size = node.get_size()
    assert size.height == 2
    assert size.width == 3


def test_text_node_get_size_empty() -> None:
    node = TextNode()
    size = node.get_size()
    assert size.height == 1
    assert size.width == 0
