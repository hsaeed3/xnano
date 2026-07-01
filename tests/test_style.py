"""Tests for xnano.style module - comprehensive style functionality."""

import pytest
from xnano import _core
from xnano.style import (
    Modifier,
    Borders,
    Padding,
    Style,
    Wrap,
    ModifierName,
    BorderSide,
    BorderTypeName,
    TitlePositionName,
    HighlightSpacingName,
)
from xnano.color import Color


class TestModifier:
    """Tests for Modifier class."""

    def test_empty_modifier(self):
        m = Modifier()
        assert m.names == frozenset()
        assert repr(m) == "Modifier()"

    def test_single_modifier(self):
        m = Modifier("bold")
        assert m.names == frozenset(["bold"])
        assert "bold" in repr(m)

    def test_multiple_modifiers(self):
        m = Modifier("bold", "italic", "underlined")
        assert "bold" in m.names
        assert "italic" in m.names
        assert "underlined" in m.names

    def test_modifier_or(self):
        m1 = Modifier("bold")
        m2 = Modifier("italic")
        m3 = m1 | m2
        assert "bold" in m3.names
        assert "italic" in m3.names

    def test_modifier_or_chaining(self):
        m1 = Modifier("bold")
        m2 = Modifier("italic")
        m3 = Modifier("underlined")
        m4 = m1 | m2 | m3
        assert "bold" in m4.names
        assert "italic" in m4.names
        assert "underlined" in m4.names

    def test_modifier_empty_method(self):
        m = Modifier.empty()
        assert m.names == frozenset()

    def test_modifier_of_method(self):
        m = Modifier.of("bold", "italic")
        assert m.names == frozenset(["bold", "italic"])

    def test_all_modifier_names(self):
        for name in ModifierName.__args__:
            m = Modifier(name)
            assert name in m.names


class TestBorders:
    """Tests for Borders class."""

    def test_none_borders(self):
        b = Borders.none()
        assert b.sides == frozenset()

    def test_all_borders(self):
        b = Borders.all()
        assert "top" in b.sides
        assert "right" in b.sides
        assert "bottom" in b.sides
        assert "left" in b.sides

    def test_single_border(self):
        b = Borders("top")
        assert b.sides == frozenset(["top"])

    def test_multiple_borders(self):
        b = Borders("top", "bottom")
        assert "top" in b.sides
        assert "bottom" in b.sides

    def test_borders_or(self):
        b1 = Borders("top")
        b2 = Borders("bottom")
        b3 = b1 | b2
        assert "top" in b3.sides
        assert "bottom" in b3.sides

    def test_borders_of_method(self):
        b = Borders.of("top", "right")
        assert b.sides == frozenset(["top", "right"])

    def test_all_border_sides(self):
        for side in BorderSide.__args__:
            b = Borders(side)
            assert side in b.sides


class TestPadding:
    """Tests for Padding class."""

    def test_zero_padding(self):
        p = Padding.zero()
        assert repr(p) is not None

    def test_uniform_padding(self):
        p = Padding.uniform(5)
        assert repr(p) is not None

    def test_horizontal_padding(self):
        p = Padding.horizontal(10)
        assert repr(p) is not None

    def test_vertical_padding(self):
        p = Padding.vertical(5)
        assert repr(p) is not None

    def test_symmetric_padding(self):
        p = Padding.symmetric(3, 2)
        assert repr(p) is not None

    def test_new_padding(self):
        p = Padding.new(1, 2, 3, 4)
        assert repr(p) is not None

    def test_padding_immutability(self):
        p = Padding(1, 2, 3, 4)
        with pytest.raises(AttributeError, match="Padding is immutable"):
            p.left = 10


class TestStyle:
    """Tests for Style class."""

    def test_default_style(self):
        s = Style.default()
        assert s is not None

    def test_reset_style(self):
        s = Style.reset()
        assert s is not None

    def test_style_with_foreground(self):
        s = Style(foreground="red")
        assert s is not None

    def test_style_with_background(self):
        s = Style(background="blue")
        assert s is not None

    def test_style_with_modifiers(self):
        s = Style(modifiers="bold")
        assert s is not None

    def test_style_with_all_options(self):
        s = Style(foreground="red", background="blue", modifiers=["bold", "italic"])
        assert s is not None

    def test_style_from_parts(self):
        s = Style.from_parts(fg=Color(r=255, g=0, b=0, a=255), bg=Color(r=0, g=0, b=255, a=255), modifiers=Modifier("bold"))
        assert s is not None

    def test_style_patch(self):
        s1 = Style(foreground="red")
        s2 = Style(background="blue")
        patched = s1.patch(s2)
        assert patched is not None

    def test_style_immutability(self):
        s = Style(foreground="red")
        with pytest.raises(AttributeError, match="Style is immutable"):
            s.foreground = "blue"
        with pytest.raises(AttributeError, match="Style is immutable"):
            s._inner = _core.Style.default()


class TestWrap:
    """Tests for Wrap class."""

    def test_wrap_default(self):
        w = Wrap()
        assert w.trim is False

    def test_wrap_trim_true(self):
        w = Wrap(trim=True)
        assert w.trim is True

    def test_wrap_trim_false(self):
        w = Wrap(trim=False)
        assert w.trim is False

    def test_wrap_repr(self):
        w = Wrap(trim=True)
        assert "trim=True" in repr(w)