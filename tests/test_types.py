"""Tests for xnano.beta.types — Padding, Size, Area."""

from __future__ import annotations

import pytest
from typing import Any

from xnano.beta.types import Area, Flex, Padding, Size, resolve_flex_weight


# ---------------------------------------------------------------------------
# Padding.parse
# ---------------------------------------------------------------------------


def test_padding_parse_int_applies_all_sides() -> None:
    p = Padding.parse(3)
    assert (p.top, p.right, p.bottom, p.left) == (3, 3, 3, 3)


def test_padding_parse_two_tuple_vertical_horizontal() -> None:
    p = Padding.parse((2, 4))
    assert (p.top, p.right, p.bottom, p.left) == (2, 4, 2, 4)


def test_padding_parse_four_tuple() -> None:
    p = Padding.parse((1, 2, 3, 4))
    assert (p.top, p.right, p.bottom, p.left) == (1, 2, 3, 4)


def test_padding_parse_instance_is_identity() -> None:
    original = Padding(top=1, right=2, bottom=3, left=4)
    assert Padding.parse(original) is original


def test_padding_parse_none_returns_zero() -> None:
    p = Padding.parse(None)
    assert (p.top, p.right, p.bottom, p.left) == (0, 0, 0, 0)


def test_padding_parse_zero() -> None:
    p = Padding.parse(0)
    assert (p.top, p.right, p.bottom, p.left) == (0, 0, 0, 0)


# ---------------------------------------------------------------------------
# Padding.horizontal / vertical properties
# ---------------------------------------------------------------------------


def test_padding_horizontal() -> None:
    p = Padding(top=1, right=3, bottom=1, left=5)
    assert p.horizontal == 8


def test_padding_vertical() -> None:
    p = Padding(top=2, right=0, bottom=4, left=0)
    assert p.vertical == 6


# ---------------------------------------------------------------------------
# Padding is frozen
# ---------------------------------------------------------------------------


def test_padding_is_frozen() -> None:
    p = Padding(top=1, right=2, bottom=3, left=4)
    with pytest.raises((AttributeError, TypeError)):
        p.top = 99  # ty: ignore[invalid-assignment]


# ---------------------------------------------------------------------------
# Size
# ---------------------------------------------------------------------------


def test_size_from_tuple() -> None:
    s = Size.from_tuple((10, 20))
    assert s.width == 10
    assert s.height == 20


def test_size_from_int() -> None:
    s = Size.from_int(5)
    assert s.width == 5
    assert s.height == 5


def test_size_equality() -> None:
    assert Size(width=4, height=8) == Size(width=4, height=8)


def test_size_is_frozen() -> None:
    s = Size(width=1, height=2)
    with pytest.raises((AttributeError, TypeError)):
        s.width = 99  # ty: ignore[invalid-assignment]


# ---------------------------------------------------------------------------
# Area.size property
# ---------------------------------------------------------------------------


def test_area_size_property() -> None:
    a = Area(x=0, y=0, width=10, height=5)
    assert a.size == Size(width=10, height=5)


# ---------------------------------------------------------------------------
# Area.contains
# ---------------------------------------------------------------------------


def test_area_contains_interior_point() -> None:
    a = Area(x=5, y=5, width=10, height=10)
    assert a.contains((7, 8))


def test_area_contains_top_left_corner() -> None:
    a = Area(x=5, y=5, width=10, height=10)
    assert a.contains((5, 5))


def test_area_contains_excludes_right_edge() -> None:
    a = Area(x=5, y=5, width=10, height=10)
    assert not a.contains((15, 7))


def test_area_contains_excludes_bottom_edge() -> None:
    a = Area(x=5, y=5, width=10, height=10)
    assert not a.contains((7, 15))


def test_area_contains_outside_left() -> None:
    a = Area(x=5, y=5, width=10, height=10)
    assert not a.contains((4, 7))


def test_area_contains_outside_top() -> None:
    a = Area(x=5, y=5, width=10, height=10)
    assert not a.contains((7, 4))


# ---------------------------------------------------------------------------
# Area.fit_content — alignment variants
# ---------------------------------------------------------------------------


def test_fit_content_left_align() -> None:
    a = Area(x=0, y=0, width=80, height=24)
    fitted = a.fit_content(Size(width=20, height=5), align="left")
    assert fitted.x == 0
    assert fitted.width == 20
    assert fitted.height == 5


def test_fit_content_right_align() -> None:
    a = Area(x=0, y=0, width=80, height=24)
    fitted = a.fit_content(Size(width=20, height=5), align="right")
    assert fitted.x == 60


def test_fit_content_center_align() -> None:
    a = Area(x=0, y=0, width=80, height=24)
    fitted = a.fit_content(Size(width=20, height=4), align="center")
    assert fitted.x == 30


def test_fit_content_centers_vertically() -> None:
    a = Area(x=0, y=0, width=80, height=20)
    fitted = a.fit_content(Size(width=10, height=4))
    assert fitted.y == (20 - 4) // 2


def test_fit_content_clamped_to_area() -> None:
    a = Area(x=0, y=0, width=10, height=5)
    fitted = a.fit_content(Size(width=200, height=200))
    assert fitted.width == 10
    assert fitted.height == 5


def test_fit_content_minimum_one() -> None:
    a = Area(x=0, y=0, width=80, height=24)
    fitted = a.fit_content(Size(width=0, height=0))
    assert fitted.width >= 1
    assert fitted.height >= 1


# ---------------------------------------------------------------------------
# Area is frozen
# ---------------------------------------------------------------------------


def test_area_is_frozen() -> None:
    a = Area(x=0, y=0, width=10, height=5)
    with pytest.raises((AttributeError, TypeError)):
        a.x = 99  # ty: ignore[invalid-assignment]


# ---------------------------------------------------------------------------
# Flex / resolve_flex_weight
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("flex", "expected"),
    [
        (None, None),
        (1, 1),
        (3, 3),
        ("flex-1", 1),
        ("flex-auto", 1),
        ("grow", 1),
        ("shrink", 1),
        ("flex-initial", 0),
        ("flex-none", 0),
        ("grow-0", 0),
        ("shrink-0", 0),
    ],
)
def test_resolve_flex_weight(flex: Flex | None, expected: int | None) -> None:
    assert resolve_flex_weight(flex) == expected


def test_resolve_flex_weight_rejects_unknown_class() -> None:
    invalid_flex: Any = "flex-2"
    with pytest.raises(ValueError, match="flex must be an int"):
        resolve_flex_weight(invalid_flex)


def test_resolve_flex_weight_rejects_invalid_type() -> None:
    invalid_flex: Any = 1.5
    with pytest.raises(TypeError, match="flex must be an int"):
        resolve_flex_weight(invalid_flex)
