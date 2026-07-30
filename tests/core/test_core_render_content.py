"""CoreRenderContent constructor and predicate tests."""

from __future__ import annotations

import pytest
from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderIR,
    CoreRenderNode,
    CoreSession,
    IrLine,
)
from xnano_core.rust.native import (
    Buffer,
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
    assert any(
        line.strip()
        for line in offscreen_session.buffer_snapshot().to_string_lines()
    )


def test_widget_ir_stateful_and_drawable_render_in_one_layout(
    offscreen_session: CoreSession,
) -> None:
    table = RatTable.new(
        [Row.new(["Ada", "active"])],
        [Constraint.percentage(50), Constraint.percentage(50)],
    )

    def draw_status(buffer: Buffer, rect: Rect) -> None:
        buffer.set_string(rect.x, rect.y, "READY", Style.default())

    tree = CoreRenderNode.column(
        constraints=[
            Constraint.length(2),
            Constraint.length(3),
            Constraint.min(1),
        ],
        children=[
            CoreRenderNode.leaf(
                CoreRenderContent.widget(Paragraph.new("Deployments"))
            ),
            CoreRenderNode.row(
                constraints=[
                    Constraint.percentage(50),
                    Constraint.percentage(50),
                ],
                children=[
                    CoreRenderNode.leaf(
                        CoreRenderContent.ir(
                            CoreRenderIR.list(
                                [
                                    IrLine.raw("api"),
                                    IrLine.raw("worker"),
                                ],
                                None,
                                None,
                                None,
                                None,
                                None,
                                "• ",
                            )
                        )
                    ),
                    CoreRenderNode.leaf(
                        CoreRenderContent.stateful(table, TableState())
                    ),
                ],
            ),
            CoreRenderNode.leaf(CoreRenderContent.drawable(draw_status)),
        ],
    )

    offscreen_session.render(tree)
    text = "\n".join(offscreen_session.buffer_snapshot().to_string_lines())
    assert all(
        value in text
        for value in ("Deployments", "api", "worker", "Ada", "active", "READY")
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
