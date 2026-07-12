"""CoreRenderContent constructor and predicate tests."""

from __future__ import annotations

import pytest
from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderNode,
    CoreSession,
)
from xnano_core.rust.native import (
    BufferMutView,
    Constraint,
    ListItem,
    ListState,
    Paragraph,
    RatList,
    RatTable,
    Rect,
    Row,
    Scrollbar,
    ScrollbarOrientation,
    ScrollbarState,
    Style,
    TableState,
)


def test_empty_content_predicates() -> None:
    content = CoreRenderContent.empty()
    assert content.is_empty()
    assert not content.is_stateful()
    assert not content.is_drawable()


def test_widget_content_predicates(sample_paragraph) -> None:
    content = CoreRenderContent.widget(sample_paragraph)
    assert not content.is_empty()
    assert not content.is_stateful()
    assert not content.is_drawable()


def test_stateful_content_predicates() -> None:
    widget = RatList.new([ListItem.new("alpha")])
    state = ListState()
    content = CoreRenderContent.stateful(widget, state)
    assert content.is_stateful()
    assert not content.is_empty()
    assert not content.is_drawable()


def test_drawable_writes_into_buffer(offscreen_session: CoreSession) -> None:
    def draw(buffer: BufferMutView, rect: Rect) -> None:
        buffer.set_string(2, 2, "X", Style.default())

    content = CoreRenderContent.drawable(draw)  # type: ignore
    assert content.is_drawable()

    offscreen_session.render(CoreRenderNode.leaf(content))
    lines = offscreen_session.buffer_snapshot().to_string_lines()
    assert "X" in "".join(lines)


def test_drawable_exception_propagates_from_render(
    offscreen_session: CoreSession,
) -> None:
    def draw(buffer: BufferMutView, rect: Rect) -> None:
        raise ValueError("drawable failure")

    with pytest.raises(ValueError, match="drawable failure"):
        offscreen_session.render(
            CoreRenderNode.leaf(CoreRenderContent.drawable(draw))  # type: ignore
        )


def test_widget_to_core_duck_type(offscreen_session: CoreSession) -> None:
    class WidgetToCore:
        def _to_core(self) -> Paragraph:
            return Paragraph.new("to-core")

    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.widget(WidgetToCore()))
    )
    text = "\n".join(offscreen_session.buffer_snapshot().to_string_lines())
    assert "to-core" in text


def test_widget_inner_duck_type(offscreen_session: CoreSession) -> None:
    class WidgetInner:
        _inner = Paragraph.new("inner")

    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.widget(WidgetInner()))
    )
    text = "\n".join(offscreen_session.buffer_snapshot().to_string_lines())
    assert "inner" in text


def test_widget_render_area_duck_type(offscreen_session: CoreSession) -> None:
    class WidgetRender:
        def render(self, area: Rect) -> Paragraph:
            return Paragraph.new("render-area")

    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.widget(WidgetRender()))
    )
    text = "\n".join(offscreen_session.buffer_snapshot().to_string_lines())
    assert "render-area" in text


def test_stateful_table_renders(offscreen_session: CoreSession) -> None:
    table = RatTable.new(
        [Row.new(["alpha", "beta"])],
        [Constraint.percentage(50), Constraint.percentage(50)],
    )
    state = TableState()
    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.stateful(table, state))
    )
    text = "\n".join(offscreen_session.buffer_snapshot().to_string_lines())
    assert "alpha" in text


def test_stateful_scrollbar_renders(offscreen_session: CoreSession) -> None:
    scrollbar = Scrollbar.new(ScrollbarOrientation.VerticalRight)
    state = ScrollbarState(20)
    state.set_position(10)
    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.stateful(scrollbar, state))
    )


def test_stateful_invalid_pairing_raises(
    offscreen_session: CoreSession,
) -> None:
    widget = RatList.new([ListItem.new("alpha")])
    state = TableState()
    with pytest.raises(TypeError, match="unsupported stateful"):
        offscreen_session.render(
            CoreRenderNode.leaf(CoreRenderContent.stateful(widget, state))
        )
