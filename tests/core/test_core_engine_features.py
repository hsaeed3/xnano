"""Core engine feature tests for z-order, visibility, and rename surface."""

from __future__ import annotations

import xnano_core.rust.engine as engine
import xnano_core.rust.native as rust
from conftest import draw_glyph_content, glyph_at
from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderNode,
    CoreSession,
)
from xnano_core.rust.native import Constraint, Paragraph


OLD_ENGINE_PUBLIC_NAMES = (
    "Event",
    "RenderContent",
    "RenderNode",
    "Session",
    "TerminalEventKind",
    "TerminalRef",
    "TickEvent",
)


def test_render_node_constructor_defaults() -> None:
    node = CoreRenderNode()
    assert node.get_z() == 0
    assert node.is_visible()


def test_leaf_factory_defaults_z_and_visible() -> None:
    node = CoreRenderNode.leaf(CoreRenderContent.empty())
    assert node.get_z() == 0
    assert node.is_visible()


def test_row_factory_defaults_z_and_visible() -> None:
    child = CoreRenderNode.leaf(CoreRenderContent.empty())
    node = CoreRenderNode.row(children=[child])
    assert node.get_z() == 0
    assert node.is_visible()


def test_column_factory_defaults_z_and_visible() -> None:
    child = CoreRenderNode.leaf(CoreRenderContent.empty())
    node = CoreRenderNode.column(children=[child])
    assert node.get_z() == 0
    assert node.is_visible()


def test_stack_factory_defaults_z_and_visible() -> None:
    child = CoreRenderNode.leaf(CoreRenderContent.empty())
    node = CoreRenderNode.stack(0, 0, 4, 2, [child])
    assert node.get_z() == 0
    assert node.is_visible()


def test_negative_z_paints_before_positive() -> None:
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
                z=5,
            ),
            CoreRenderNode(
                x=0,
                y=0,
                width=2,
                height=1,
                content=draw_glyph_content("B"),
                z=-1,
            ),
        ],
    )
    session.render(tree)
    assert glyph_at(session, 0, 0) == "A"


def test_z_does_not_change_layout_slots() -> None:
    session = CoreSession.offscreen(20, 1)
    tree = CoreRenderNode.row(
        children=[
            CoreRenderNode(
                content=CoreRenderContent.widget(Paragraph.new("L")),
                z=100,
            ),
            CoreRenderNode(
                content=CoreRenderContent.widget(Paragraph.new("R")),
                z=0,
            ),
        ],
        constraints=[Constraint.percentage(50), Constraint.percentage(50)],
    )
    session.render(tree)
    line = session.buffer_snapshot().to_string_lines()[0]
    left_index = line.index("L")
    right_index = line.index("R")
    assert left_index < right_index
    assert left_index < len(line) // 2
    assert right_index >= len(line) // 2


def test_invisible_leaf_does_not_paint_content() -> None:
    session = CoreSession.offscreen(4, 1)
    node = CoreRenderNode(
        content=draw_glyph_content("X"),
        visible=False,
    )
    session.render(node)
    for line in session.buffer_snapshot().to_string_lines():
        assert "X" not in line


def test_root_visible_false_leaves_buffer_empty() -> None:
    session = CoreSession.offscreen(6, 2)
    tree = CoreRenderNode(
        visible=False,
        children=[
            CoreRenderNode.leaf(draw_glyph_content("visible-child")),
        ],
    )
    session.render(tree)
    for line in session.buffer_snapshot().to_string_lines():
        assert line.strip() == ""


def test_old_engine_public_names_removed() -> None:
    for name in OLD_ENGINE_PUBLIC_NAMES:
        assert not hasattr(engine, name), name


def test_native_root_reexports_core_event_types() -> None:
    assert rust.CoreEvent is engine.CoreEvent
    assert rust.CoreTickEvent is engine.CoreTickEvent
    assert rust.CoreTerminalEventKind is engine.CoreTerminalEventKind


def test_core_terminal_ref_exported() -> None:
    assert hasattr(engine, "CoreTerminalRef")


def test_row_gap_inserts_spacing_between_children() -> None:
    session = CoreSession.offscreen(11, 1)
    tree = CoreRenderNode.row(
        gap=2,
        children=[
            CoreRenderNode(
                content=CoreRenderContent.widget(Paragraph.new("A"))
            ),
            CoreRenderNode(
                content=CoreRenderContent.widget(Paragraph.new("B"))
            ),
        ],
        constraints=[Constraint.length(3), Constraint.length(3)],
    )
    session.render(tree)
    line = session.buffer_snapshot().to_string_lines()[0]
    assert line.index("A") == 0
    assert line.index("B") == 5


def test_invisible_child_reserves_layout_slot() -> None:
    session = CoreSession.offscreen(20, 1)
    tree = CoreRenderNode.row(
        children=[
            CoreRenderNode(
                content=CoreRenderContent.widget(Paragraph.new("L")),
                visible=False,
            ),
            CoreRenderNode(
                content=CoreRenderContent.widget(Paragraph.new("R")),
            ),
        ],
        constraints=[Constraint.percentage(50), Constraint.percentage(50)],
    )
    session.render(tree)
    line = session.buffer_snapshot().to_string_lines()[0]
    assert "L" not in line
    assert line.index("R") >= len(line) // 2
