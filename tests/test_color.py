"""Tests for xnano.color module - comprehensive color functionality."""

import pytest
from xnano.color import Color, COLORS_BY_NAME, ColorName


class TestColorCreation:
    """Tests for Color class factory methods."""

    def test_rgb_color(self):
        c = Color(r=255, g=128, b=64, a=255)
        assert c.r == 255
        assert c.g == 128
        assert c.b == 64
        assert c.a == 255

    def test_rgb_color_alpha(self):
        c = Color(r=100, g=100, b=100, a=128)
        assert c.r == 100
        assert c.g == 100
        assert c.b == 100
        assert c.a == 128

    def test_from_hex_with_hash(self):
        c = Color.from_hex("#ff00ff")
        assert c.r == 255
        assert c.g == 0
        assert c.b == 255
        assert c.a == 255

    def test_from_hex_without_hash(self):
        c = Color.from_hex("00ff00")
        assert c.r == 0
        assert c.g == 255
        assert c.b == 0
        assert c.a == 255

    def test_from_hex_with_alpha(self):
        c = Color.from_hex("#ff0000ff")
        assert c.r == 255
        assert c.g == 0
        assert c.b == 0
        assert c.a == 255

    def test_from_hex_3_digit(self):
        c = Color.from_hex("#fff")
        assert c.r == 255
        assert c.g == 255
        assert c.b == 255

    def test_from_hex_4_digit(self):
        c = Color.from_hex("#ffff")
        assert c.r == 255
        assert c.g == 255
        assert c.b == 255
        assert c.a == 255

    def test_from_hex_4_digit_alpha(self):
        c = Color.from_hex("#fff8")
        assert c.r == 255
        assert c.g == 255
        assert c.b == 255
        assert c.a == 136

    def test_from_hex_uppercase(self):
        c = Color.from_hex("#FF00FF")
        assert c.r == 255
        assert c.g == 0
        assert c.b == 255

    def test_from_hex_lowercase(self):
        c = Color.from_hex("#ff00ff")
        assert c.r == 255
        assert c.g == 0
        assert c.b == 255

    def test_from_hex_invalid(self):
        with pytest.raises(ValueError, match="Invalid hex color string"):
            Color.from_hex("invalid")

    def test_from_hex_empty(self):
        with pytest.raises(ValueError, match="Invalid hex color string"):
            Color.from_hex("")

    def test_from_name_basic(self):
        c = Color.from_name("red")
        assert c.r == 255
        assert c.g == 0
        assert c.b == 0

    def test_from_name_multiple(self):
        for name in ["blue", "green", "yellow", "white", "black"]:
            c = Color.from_name(name)
            assert isinstance(c, Color)
            assert 0 <= c.r <= 255
            assert 0 <= c.g <= 255
            assert 0 <= c.b <= 255

    def test_from_hsl(self):
        c = Color.from_hsl(0.0, 1.0, 0.5)
        assert isinstance(c, Color)

    def test_from_hsl_edge_cases(self):
        # Black
        c = Color.from_hsl(0.0, 0.0, 0.0)
        assert c.r == 0
        assert c.g == 0
        assert c.b == 0

        # White
        c = Color.from_hsl(0.0, 0.0, 1.0)
        assert c.r == 255
        assert c.g == 255
        assert c.b == 255

    def test_from_hsl_invalid(self):
        # We can trigger ValueError by mocking the native call to raise an exception
        from unittest import mock
        from xnano import _core
        with mock.patch("xnano._core.color_from_hsl", side_effect=Exception("HSL error")):
            with pytest.raises(ValueError, match="Invalid HSL components"):
                Color.from_hsl(999.0, 999.0, 999.0)

    def test_from_native_mappings(self):
        from unittest import mock
        from xnano import _core
        # Test named color mapping (e.g. "Black")
        mock_color = mock.Mock(spec=_core.Color)
        mock_color.__repr__ = mock.Mock(return_value="Black")
        c = Color.from_native(mock_color)
        assert c == Color.from_name("black")

        # Test "Reset"
        mock_color.__repr__ = mock.Mock(return_value="Reset")
        c = Color.from_native(mock_color)
        assert c == Color(0, 0, 0, 0)

        # Test Unsupported native color representation
        mock_color.__repr__ = mock.Mock(return_value="InvalidColorRepr")
        with pytest.raises(ValueError, match="unsupported native color"):
            Color.from_native(mock_color)

    def test_color_repr(self):
        c = Color(1, 2, 3, 4)
        assert repr(c) == "Color(r=1, g=2, b=3, a=4)"



class TestColorLerp:
    """Tests for color interpolation."""

    def test_lerp_start(self):
        c1 = Color(r=0, g=0, b=0, a=255)
        c2 = Color(r=100, g=100, b=100, a=255)
        result = Color.lerp(c1, c2, 0.0)
        assert result.r == 0
        assert result.g == 0
        assert result.b == 0

    def test_lerp_end(self):
        c1 = Color(r=0, g=0, b=0, a=255)
        c2 = Color(r=100, g=100, b=100, a=255)
        result = Color.lerp(c1, c2, 1.0)
        assert result.r == 100
        assert result.g == 100
        assert result.b == 100

    def test_lerp_middle(self):
        c1 = Color(r=0, g=0, b=0, a=255)
        c2 = Color(r=100, g=100, b=100, a=255)
        result = Color.lerp(c1, c2, 0.5)
        assert result.r == 50
        assert result.g == 50
        assert result.b == 50

    def test_lerp_clamp_low(self):
        c1 = Color(r=0, g=0, b=0, a=255)
        c2 = Color(r=100, g=100, b=100, a=255)
        result = Color.lerp(c1, c2, -0.5)
        assert result.r == 0  # Clamped to 0

    def test_lerp_clamp_high(self):
        c1 = Color(r=0, g=0, b=0, a=255)
        c2 = Color(r=100, g=100, b=100, a=255)
        result = Color.lerp(c1, c2, 1.5)
        assert result.r == 100  # Clamped to end value

    def test_lerp_alpha(self):
        c1 = Color(r=0, g=0, b=0, a=0)
        c2 = Color(r=100, g=100, b=100, a=255)
        result = Color.lerp(c1, c2, 0.5)
        assert result.a == 128


class TestColorEquality:
    """Tests for Color equality and hashing."""

    def test_equal_colors(self):
        c1 = Color(r=255, g=0, b=0, a=255)
        c2 = Color(r=255, g=0, b=0, a=255)
        assert c1 == c2

    def test_unequal_colors(self):
        c1 = Color(r=255, g=0, b=0, a=255)
        c2 = Color(r=0, g=255, b=0, a=255)
        assert c1 != c2

    def test_different_types(self):
        c = Color(r=255, g=0, b=0, a=255)
        assert c != "red"
        assert c != 100

    def test_hashable(self):
        c1 = Color(r=255, g=0, b=0, a=255)
        c2 = Color(r=255, g=0, b=0, a=255)
        assert hash(c1) == hash(c2)

    def test_hashable_in_set(self):
        colors = {Color(r=255, g=0, b=0, a=255), Color(r=0, g=255, b=0, a=255)}
        assert len(colors) == 2


class TestCOLORS_BY_NAME:
    """Tests for the COLORS_BY_NAME dictionary."""

    def test_colors_dict_not_empty(self):
        assert len(COLORS_BY_NAME) > 100

    def test_known_colors(self):
        assert "red" in COLORS_BY_NAME
        assert "blue" in COLORS_BY_NAME
        assert "green" in COLORS_BY_NAME

    def test_color_values_are_tuples(self):
        for name, value in COLORS_BY_NAME.items():
            assert isinstance(value, tuple)
            assert len(value) == 3

    def test_color_values_in_range(self):
        for name, (r, g, b) in COLORS_BY_NAME.items():
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255