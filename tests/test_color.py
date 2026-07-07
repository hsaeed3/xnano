"""Tests for xnano.beta.color — Color, tailwind."""

from __future__ import annotations

import pytest

from xnano.beta.color import Color, tailwind


# ---------------------------------------------------------------------------
# Color.from_name
# ---------------------------------------------------------------------------


def test_from_name_red() -> None:
    c = Color.from_name("red")
    assert c.r == 255
    assert c.g == 0
    assert c.b == 0
    assert c.a == 255.0


def test_from_name_black() -> None:
    c = Color.from_name("black")
    assert (c.r, c.g, c.b) == (0, 0, 0)


def test_from_name_white() -> None:
    c = Color.from_name("white")
    assert (c.r, c.g, c.b) == (255, 255, 255)


def test_from_name_custom_alpha() -> None:
    c = Color.from_name("blue", alpha=128.0)
    assert c.a == 128.0


def test_from_name_unknown_raises() -> None:
    with pytest.raises(KeyError):
        Color.from_name("notacolor")  # ty: ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# Color.from_rgba
# ---------------------------------------------------------------------------


def test_from_rgba_three_component() -> None:
    c = Color.from_rgba((10, 20, 30))
    assert (c.r, c.g, c.b, c.a) == (10, 20, 30, 255.0)


def test_from_rgba_four_component() -> None:
    c = Color.from_rgba((10, 20, 30, 0.5))
    assert (c.r, c.g, c.b, c.a) == (10, 20, 30, 0.5)


def test_from_rgba_wrong_length_raises() -> None:
    with pytest.raises(ValueError):
        Color.from_rgba((10, 20))  # ty: ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# Color.from_hex
# ---------------------------------------------------------------------------


def test_from_hex_six_digit() -> None:
    c = Color.from_hex("#ff0000")
    assert (c.r, c.g, c.b) == (255, 0, 0)


def test_from_hex_without_hash() -> None:
    c = Color.from_hex("00ff00")
    assert (c.r, c.g, c.b) == (0, 255, 0)


def test_from_hex_three_digit_shorthand() -> None:
    c = Color.from_hex("#f00")
    assert (c.r, c.g, c.b) == (255, 0, 0)


def test_from_hex_eight_digit_alpha() -> None:
    c = Color.from_hex("#ff000080")
    assert c.r == 255
    assert c.g == 0
    assert c.b == 0
    assert c.a == 0x80


def test_from_hex_uppercase() -> None:
    c = Color.from_hex("#FF0000")
    assert c.r == 255


def test_from_hex_invalid_raises() -> None:
    with pytest.raises(ValueError):
        Color.from_hex("notahex")


# ---------------------------------------------------------------------------
# Color.parse — dispatch router
# ---------------------------------------------------------------------------


def test_parse_color_name() -> None:
    c = Color.parse("cyan")
    assert (c.r, c.g, c.b) == (0, 255, 255)


def test_parse_hex_string() -> None:
    c = Color.parse("#0000ff")
    assert (c.r, c.g, c.b) == (0, 0, 255)


def test_parse_rgb_tuple() -> None:
    c = Color.parse((1, 2, 3))
    assert (c.r, c.g, c.b) == (1, 2, 3)


def test_parse_rgba_tuple() -> None:
    c = Color.parse((1, 2, 3, 0.5))
    assert c.a == 0.5


def test_parse_color_instance_is_identity() -> None:
    original = Color(r=1, g=2, b=3)
    assert Color.parse(original) is original


def test_parse_unknown_name_raises() -> None:
    with pytest.raises(ValueError, match="not a known color name"):
        Color.parse("banana")


def test_parse_invalid_hex_raises() -> None:
    with pytest.raises(ValueError):
        Color.parse("#zzzzzz")


def test_parse_invalid_type_raises() -> None:
    with pytest.raises((ValueError, TypeError)):
        Color.parse(42)  # ty: ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# Color frozen / equality
# ---------------------------------------------------------------------------


def test_color_equality() -> None:
    assert Color(r=1, g=2, b=3) == Color(r=1, g=2, b=3)


def test_color_inequality() -> None:
    assert Color(r=1, g=2, b=3) != Color(r=1, g=2, b=4)


def test_color_is_frozen() -> None:
    c = Color(r=1, g=2, b=3)
    with pytest.raises((AttributeError, TypeError)):
        c.r = 99  # ty: ignore[invalid-assignment]


# ---------------------------------------------------------------------------
# tailwind
# ---------------------------------------------------------------------------


def test_tailwind_returns_color() -> None:
    c = tailwind("blue", 500)
    assert isinstance(c, Color)
    assert 0 <= c.r <= 255
    assert 0 <= c.g <= 255
    assert 0 <= c.b <= 255


def test_tailwind_is_cached() -> None:
    c1 = tailwind("red", 500)
    c2 = tailwind("red", 500)
    assert c1 is c2


def test_tailwind_different_shades_differ() -> None:
    light = tailwind("blue", 100)
    dark = tailwind("blue", 900)
    assert (light.r, light.g, light.b) != (dark.r, dark.g, dark.b)
