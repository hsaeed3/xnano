"""Native widget builder and render tests."""

from __future__ import annotations

from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderNode,
    CoreSession,
)
from xnano_core.rust.native import (
    Block,
    Borders,
    Line,
    ListItem,
    ListState,
    Paragraph,
    RatList,
    Span,
    Style,
    Text,
)


def test_paragraph_with_block_title(offscreen_session: CoreSession) -> None:
    widget = Paragraph.new("widget-body").block(
        Block.bordered()
        .borders(Borders.ALL)
        .title("title")
        .border_style(Style.default())
    )
    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.widget(widget))
    )
    text = "\n".join(offscreen_session.buffer_snapshot().to_string_lines())
    assert "widget-body" in text


def test_stateful_list_renders_selection(
    offscreen_session: CoreSession,
) -> None:
    items = [ListItem.new("alpha"), ListItem.new("beta")]
    widget = RatList.new(items)
    state = ListState()
    state.select(1)
    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.stateful(widget, state))
    )
    text = "\n".join(offscreen_session.buffer_snapshot().to_string_lines())
    assert "alpha" in text
    assert "beta" in text


def test_styled_text_spans(offscreen_session: CoreSession) -> None:
    line = Line.from_spans([Span.styled("styled-bit", Style.default())])
    text = Text.from_lines([line])
    widget = Paragraph.new(text)
    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.widget(widget))
    )
    assert "styled-bit" in "\n".join(
        offscreen_session.buffer_snapshot().to_string_lines()
    )
