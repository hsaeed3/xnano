"""Web lowering for the text-update features (input, markdown, Select)."""

from __future__ import annotations

from xnano._types import Area
from xnano.components.abstract import ComponentRenderContext
from xnano.components.select import Select
from xnano.components.text import Text
from xnano.web.nodes import (
    WebContainerNode,
    WebInputNode,
    WebParagraphNode,
    WebRawHtmlNode,
)


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=60, height=20))


def test_input_text_lowers_to_input_element() -> None:
    text = Text("hi", input=True, placeholder="name")
    node = text.get_web_node(_ctx())
    assert isinstance(node, WebInputNode)
    html = node.to_html()
    assert html.startswith("<input")
    assert 'value="hi"' in html
    assert 'placeholder="name"' in html


def test_multiline_input_lowers_to_textarea() -> None:
    text = Text("a\nb", input=True, multiline=True, rows=3)
    node = text.get_web_node(_ctx())
    assert isinstance(node, WebInputNode)
    html = node.to_html()
    assert html.startswith('<textarea rows="3"')
    assert ">a\nb</textarea>" in html


def test_input_value_is_escaped() -> None:
    text = Text('x"><script>', input=True)
    node = text.get_web_node(_ctx())
    assert isinstance(node, WebInputNode)
    assert "<script>" not in node.to_html()


def test_markdown_lowers_to_raw_semantic_html() -> None:
    node = Text("# Title\n\n**bold**", markdown=True).get_web_node(_ctx())
    assert isinstance(node, WebRawHtmlNode)
    html = node.to_html()
    assert "<h1>Title</h1>" in html
    assert "<strong>bold</strong>" in html


def test_select_searchable_lowers_to_input_plus_list() -> None:
    select = Select(items=("dark", "light"), query="d")
    node = select.get_web_node(_ctx())
    assert isinstance(node, WebContainerNode)
    input_node, items_node = node.children
    assert isinstance(input_node, WebInputNode)
    assert input_node.value == "d"
    assert isinstance(items_node, WebParagraphNode)
    assert len(items_node.lines) == 1


def test_select_selected_row_is_highlighted() -> None:
    select = Select(items=("one", "two"), searchable=False)
    node = select.get_web_node(_ctx())
    assert isinstance(node, WebParagraphNode)
    first_row = node.lines[0]
    assert first_row[0].content == "> "
    assert first_row[1].background is not None
    second_row = node.lines[1]
    assert second_row[1].background is None
