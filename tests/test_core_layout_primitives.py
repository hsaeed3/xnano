"""Layout and geometry primitive tests."""

from __future__ import annotations

from xnano_core.rust.native import (
    Constraint,
    Direction,
    Layout,
    Margin,
    Rect,
)


def test_rect_geometry() -> None:
    rect = Rect(2, 3, 10, 4)
    assert rect.x == 2
    assert rect.y == 3
    assert rect.width == 10
    assert rect.height == 4
    assert rect.area() == 40
    assert not rect.is_empty()


def test_rect_inner_margin() -> None:
    outer = Rect(0, 0, 20, 10)
    inner = outer.inner(Margin(2, 1))
    assert inner.width == 16
    assert inner.height == 8


def test_layout_split_vertical() -> None:
    area = Rect(0, 0, 10, 10)
    chunks = (
        Layout.vertical([Constraint.length(3), Constraint.min(0)])
        .split(area)
    )
    assert len(chunks) == 2
    assert chunks[0].height == 3
    assert chunks[1].height == 7


def test_layout_split_horizontal() -> None:
    area = Rect(0, 0, 12, 4)
    chunks = (
        Layout.horizontal([Constraint.percentage(25), Constraint.percentage(75)])
        .split(area)
    )
    assert chunks[0].width == 3
    assert chunks[1].width == 9


def test_constraint_factories() -> None:
    assert Constraint.min(1) is not None
    assert Constraint.max(5) is not None
    assert Constraint.length(3) is not None
    assert Constraint.percentage(50) is not None
    assert Constraint.ratio(1, 2) is not None


def test_layout_direction_and_spacing() -> None:
    layout = (
        Layout.default()
        .direction(Direction.Horizontal)
        .spacing(1)
        .constraints([Constraint.min(0), Constraint.min(0)])
    )
    chunks = layout.split(Rect(0, 0, 11, 3))
    assert len(chunks) == 2
    assert chunks[0].width + chunks[1].width <= 11