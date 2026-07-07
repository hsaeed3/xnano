"""Tests for xnano.beta.core.nodes — render IR nodes and NodeAssembler."""

from __future__ import annotations

import pytest

from xnano.beta.core.nodes import (
    ClearNode,
    ContainerNode,
    FrameNode,
    LineNode,
    ListNode,
    NodeAssembler,
    ParagraphNode,
    ProgressBarNode,
    SpanNode,
    StackNode,
    TextNode,
)
from xnano.beta.frame import Frame
from xnano.beta.types import Size


assembler = NodeAssembler()


# ---------------------------------------------------------------------------
# SpanNode
# ---------------------------------------------------------------------------


def test_span_node_defaults() -> None:
    s = SpanNode(content="hi")
    assert s.content == "hi"
    assert s.color is None
    assert s.background is None
    assert s.modifiers == []


def test_span_node_frozen() -> None:
    s = SpanNode(content="x")
    with pytest.raises((AttributeError, TypeError)):
        s.content = "y"  # type: ignore[misc]


def test_span_node_measure() -> None:
    size = assembler.measure_node(SpanNode(content="hello"))
    assert size == Size(width=5, height=1)


def test_span_node_measure_empty() -> None:
    size = assembler.measure_node(SpanNode(content=""))
    assert size == Size(width=0, height=1)


# ---------------------------------------------------------------------------
# LineNode
# ---------------------------------------------------------------------------


def test_line_node_string_width() -> None:
    node = LineNode(content="hello")
    assert node.get_width() == 5


def test_line_node_span_width() -> None:
    node = LineNode(content=[SpanNode(content="ab"), SpanNode(content="cde")])
    assert node.get_width() == 5


def test_line_node_none_width() -> None:
    node = LineNode(content=None)
    assert node.get_width() == 0


def test_line_node_measure_string() -> None:
    size = assembler.measure_node(LineNode(content="hello world"))
    assert size == Size(width=11, height=1)


def test_line_node_measure_spans() -> None:
    node = LineNode(content=[SpanNode(content="abc"), SpanNode(content="de")])
    size = assembler.measure_node(node)
    assert size == Size(width=5, height=1)


# ---------------------------------------------------------------------------
# TextNode
# ---------------------------------------------------------------------------


def test_text_node_get_size_from_lines() -> None:
    node = TextNode(
        lines=[LineNode(content="hello"), LineNode(content="world!")]
    )
    size = node.get_size()
    assert size == Size(width=6, height=2)


def test_text_node_get_size_from_content() -> None:
    node = TextNode(content="abc\nde\nf")
    size = node.get_size()
    assert size == Size(width=3, height=3)


def test_text_node_get_size_empty() -> None:
    size = TextNode().get_size()
    assert size == Size(width=0, height=1)


def test_text_node_invisible_measures_zero() -> None:
    node = TextNode(content="hello", visible=False)
    size = assembler.measure_node(node)
    assert size == Size(width=0, height=0)


# ---------------------------------------------------------------------------
# ParagraphNode
# ---------------------------------------------------------------------------


def test_paragraph_node_measure_string() -> None:
    node = ParagraphNode(text="hello")
    size = assembler.measure_node(node)
    assert size == Size(width=5, height=1)


def test_paragraph_node_measure_multiline_string() -> None:
    node = ParagraphNode(text="hello\nworld!")
    size = assembler.measure_node(node)
    assert size == Size(width=6, height=2)


def test_paragraph_node_measure_empty() -> None:
    node = ParagraphNode(text="")
    size = assembler.measure_node(node)
    assert size == Size(width=0, height=1)


def test_paragraph_node_measure_text_node() -> None:
    text_node = TextNode(
        lines=[LineNode(content="hi"), LineNode(content="there!")]
    )
    node = ParagraphNode(text=text_node)
    size = assembler.measure_node(node)
    assert size == Size(width=6, height=2)


def test_paragraph_node_measure_line_node() -> None:
    line = LineNode(content="line content")
    node = ParagraphNode(text=line)
    size = assembler.measure_node(node)
    assert size == Size(width=12, height=1)


def test_paragraph_node_invisible_measures_zero() -> None:
    node = ParagraphNode(text="hello", visible=False)
    size = assembler.measure_node(node)
    assert size == Size(width=0, height=0)


# ---------------------------------------------------------------------------
# ListNode
# ---------------------------------------------------------------------------


def test_list_node_measure_strings() -> None:
    node = ListNode(items=["alpha", "beta"])
    size = assembler.measure_node(node)
    symbol_w = len(node.highlight_symbol)
    assert size.height == 2
    assert size.width == 5 + symbol_w


def test_list_node_measure_empty() -> None:
    size = assembler.measure_node(ListNode(items=[]))
    assert size == Size(width=0, height=1)


def test_list_node_measure_line_items() -> None:
    node = ListNode(items=[LineNode(content="hello"), LineNode(content="hi")])
    size = assembler.measure_node(node)
    symbol_w = len(node.highlight_symbol)
    assert size.height == 2
    assert size.width == 5 + symbol_w


def test_list_node_measure_span_items() -> None:
    node = ListNode(items=[SpanNode(content="ab"), SpanNode(content="cde")])
    size = assembler.measure_node(node)
    symbol_w = len(node.highlight_symbol)
    assert size.height == 2
    assert size.width == 3 + symbol_w


# ---------------------------------------------------------------------------
# ProgressBarNode
# ---------------------------------------------------------------------------


def test_progress_bar_node_defaults() -> None:
    p = ProgressBarNode()
    assert p.progress == 0.0
    assert p.label is None
    assert p.color == "green"


def test_progress_bar_measure() -> None:
    size = assembler.measure_node(ProgressBarNode(progress=0.5))
    assert size == Size(width=0, height=1)


# ---------------------------------------------------------------------------
# ClearNode
# ---------------------------------------------------------------------------


def test_clear_node_measures_zero() -> None:
    size = assembler.measure_node(ClearNode())
    assert size == Size(width=0, height=0)


# ---------------------------------------------------------------------------
# FrameNode
# ---------------------------------------------------------------------------


def test_frame_node_measure_adds_border_overhead() -> None:
    child = ParagraphNode(text="hello")
    node = FrameNode(frame=Frame(border="rounded"), child=child)
    size = assembler.measure_node(node)
    # border adds 2 on each axis
    assert size.width == 5 + 2
    assert size.height == 1 + 2


def test_frame_node_measure_no_border() -> None:
    child = ParagraphNode(text="hi")
    node = FrameNode(frame=Frame(), child=child)
    size = assembler.measure_node(node)
    assert size.width == 2
    assert size.height == 1


def test_frame_node_measure_with_padding() -> None:
    child = ParagraphNode(text="hi")
    node = FrameNode(frame=Frame(padding=1), child=child)
    size = assembler.measure_node(node)
    assert size.width == 2 + 2
    assert size.height == 1 + 2


# ---------------------------------------------------------------------------
# ContainerNode
# ---------------------------------------------------------------------------


def test_container_node_horizontal_measure() -> None:
    node = ContainerNode(
        direction="horizontal",
        children=[ParagraphNode(text="abc"), ParagraphNode(text="de")],
    )
    size = assembler.measure_node(node)
    assert size.width == 3 + 2
    assert size.height == 1


def test_container_node_vertical_measure() -> None:
    node = ContainerNode(
        direction="vertical",
        children=[ParagraphNode(text="abc"), ParagraphNode(text="de")],
    )
    size = assembler.measure_node(node)
    assert size.width == 3
    assert size.height == 1 + 1


def test_container_node_gap_added() -> None:
    node = ContainerNode(
        direction="horizontal",
        children=[ParagraphNode(text="a"), ParagraphNode(text="b")],
        gap=2,
    )
    size = assembler.measure_node(node)
    assert size.width == 1 + 1 + 2


def test_container_node_empty_measures_zero() -> None:
    node = ContainerNode(direction="vertical", children=[])
    size = assembler.measure_node(node)
    assert size == Size(width=0, height=0)


# ---------------------------------------------------------------------------
# StackNode
# ---------------------------------------------------------------------------


def test_stack_node_takes_max_of_children() -> None:
    node = StackNode(
        children=[
            ParagraphNode(text="hello"),
            ParagraphNode(text="hi"),
        ]
    )
    size = assembler.measure_node(node)
    assert size.width == 5
    assert size.height == 1


def test_stack_node_empty_measures_zero() -> None:
    size = assembler.measure_node(StackNode(children=[]))
    assert size == Size(width=0, height=0)


# ---------------------------------------------------------------------------
# Nested composition
# ---------------------------------------------------------------------------


def test_nested_frame_in_container() -> None:
    framed = FrameNode(
        frame=Frame(border="plain"), child=ParagraphNode(text="abc")
    )
    container = ContainerNode(
        direction="horizontal", children=[framed, ParagraphNode(text="x")]
    )
    size = assembler.measure_node(container)
    assert size.width == (3 + 2) + 1
    assert size.height == max(1 + 2, 1)


def test_stack_inside_container() -> None:
    stack = StackNode(
        children=[ParagraphNode(text="hello"), ParagraphNode(text="hi")]
    )
    container = ContainerNode(
        direction="vertical", children=[stack, ParagraphNode(text="!")]
    )
    size = assembler.measure_node(container)
    assert size.width == 5
    assert size.height == 1 + 1
