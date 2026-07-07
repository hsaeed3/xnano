"""CoreRenderNode layout and accessor tests."""

from __future__ import annotations

from xnano_core.rust.native import Constraint, Margin, Paragraph
from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderNode,
    CoreSession,
)

from conftest import draw_glyph_content, glyph_at


def _flattened_text(session: CoreSession) -> str:
    return "\n".join(session.buffer_snapshot().to_string_lines())


def test_leaf_renders_widget_text(
    offscreen_session: CoreSession, sample_paragraph: Paragraph
) -> None:
    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.widget(sample_paragraph))
    )
    assert "hello, xnano-core" in _flattened_text(offscreen_session)


def test_column_splits_with_constraints(
    offscreen_session: CoreSession, column_tree: CoreRenderNode
) -> None:
    offscreen_session.render(column_tree)
    text = _flattened_text(offscreen_session)
    assert "hello, xnano-core" in text


def test_row_layout(offscreen_session: CoreSession) -> None:
    left = Paragraph.new("left")
    right = Paragraph.new("right")
    tree = CoreRenderNode.row(
        children=[
            CoreRenderNode.leaf(CoreRenderContent.widget(left)),
            CoreRenderNode.leaf(CoreRenderContent.widget(right)),
        ],
        constraints=[Constraint.percentage(50), Constraint.percentage(50)],
    )
    offscreen_session.render(tree)
    text = _flattened_text(offscreen_session)
    assert "left" in text
    assert "right" in text


def test_absolute_geometry_overlay(offscreen_session: CoreSession) -> None:
    overlay = CoreRenderNode(
        x=4,
        y=2,
        width=12,
        height=3,
        content=CoreRenderContent.widget(Paragraph.new("popup")),
    )
    tree = CoreRenderNode(
        content=CoreRenderContent.widget(Paragraph.new("background")),
        children=[overlay],
    )
    offscreen_session.render(tree)
    text = _flattened_text(offscreen_session)
    assert "background" in text
    assert "popup" in text


def test_stack_factory_sets_absolute_geometry() -> None:
    node = CoreRenderNode.stack(
        1,
        2,
        10,
        4,
        [CoreRenderNode.leaf(CoreRenderContent.empty())],
    )
    assert node.has_absolute_geometry()


def test_effect_key_recorded_area(
    offscreen_session: CoreSession, sample_paragraph
) -> None:
    node = CoreRenderNode(
        content=CoreRenderContent.widget(sample_paragraph),
        effect_key="hero",
    )
    offscreen_session.render(node)
    area = offscreen_session.effect_area_for("hero")
    assert area is not None
    assert area.width == 40
    assert area.height == 12
    assert offscreen_session.effect_area_for("missing") is None


def test_render_node_accessors(sample_paragraph) -> None:
    child = CoreRenderNode.leaf(CoreRenderContent.empty())
    node = CoreRenderNode(
        content=CoreRenderContent.widget(sample_paragraph),
        effect_key="panel",
        children=[child],
        margin=Margin(1, 1),
    )
    assert node.get_effect_key() == "panel"
    assert len(node.get_children()) == 1
    assert not node.get_content().is_empty()
    assert not node.has_absolute_geometry()


def test_absolute_geometry_flag() -> None:
    node = CoreRenderNode(x=1, y=2, width=10, height=5, children=[])
    assert node.has_absolute_geometry()


def test_z_order_higher_paints_last() -> None:
    session = CoreSession.offscreen(2, 1)

    tree = CoreRenderNode.stack(
        0,
        0,
        2,
        1,
        [
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("A"),
                z=0,
            ),
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("B"),
                z=10,
            ),
        ],
    )
    session.render(tree)
    assert glyph_at(session, 0, 0) == "B"

    tree = CoreRenderNode.stack(
        0,
        0,
        2,
        1,
        [
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("A"),
                z=10,
            ),
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("B"),
                z=0,
            ),
        ],
    )
    session.render(tree)
    assert glyph_at(session, 0, 0) == "A"

    tree = CoreRenderNode.stack(
        0,
        0,
        2,
        1,
        [
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("A"),
                z=0,
            ),
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("B"),
                z=0,
            ),
        ],
    )
    session.render(tree)
    assert glyph_at(session, 0, 0) == "B"


def test_visible_false_skips_child_paint() -> None:
    session = CoreSession.offscreen(2, 1)
    tree = CoreRenderNode.stack(
        0,
        0,
        2,
        1,
        [
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("A"),
                z=0,
            ),
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("B"),
                z=10,
                visible=False,
            ),
        ],
    )
    session.render(tree)
    assert glyph_at(session, 0, 0) == "A"


def test_visible_false_on_parent_clears_buffer() -> None:
    session = CoreSession.offscreen(2, 1)
    tree = CoreRenderNode(
        x=0,
        y=0,
        width=2,
        height=1,
        visible=False,
        children=[
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("A"),
            ),
        ],
    )
    session.render(tree)
    for line in session.buffer_snapshot().to_string_lines():
        assert line.strip() == ""


def test_effect_area_skipped_when_invisible() -> None:
    session = CoreSession.offscreen(10, 5)
    node = CoreRenderNode(
        visible=False,
        effect_key="hidden_target",
        children=[
            CoreRenderNode(
                effect_key="nested_hidden",
                content=CoreRenderContent.empty(),
            ),
        ],
    )
    session.render(node)
    assert session.effect_area_for("hidden_target") is None
    assert session.effect_area_for("nested_hidden") is None


def test_z_and_visible_accessors() -> None:
    node = CoreRenderNode(z=5, visible=False)
    assert node.get_z() == 5
    assert not node.is_visible()
