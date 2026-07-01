"""Tests for xnano.text module - comprehensive text functionality."""

import pytest
from xnano.text import Span, Line, Text
from xnano.color import Color
from xnano.style import Style, Modifier


class TestSpan:
    """Tests for Span class."""

    def test_span_raw(self):
        s = Span("Hello")
        assert s.text == "Hello"

    def test_span_with_foreground(self):
        s = Span("Hello", foreground="red")
        assert s.text == "Hello"

    def test_span_with_background(self):
        s = Span("Hello", background="blue")
        assert s.text == "Hello"

    def test_span_with_modifiers_string(self):
        s = Span("Hello", modifiers="bold")
        assert s.text == "Hello"

    def test_span_with_modifiers_list(self):
        s = Span("Hello", modifiers=["bold", "italic"])
        assert s.text == "Hello"

    def test_span_style_method(self):
        s = Span("Hello")
        styled = s.style(Style(foreground="red"))
        assert styled.text == "Hello"

    def test_span_patch_style(self):
        s = Span("Hello")
        patched = s.patch_style(Style(foreground="red"))
        assert patched.text == "Hello"

    def test_span_reset_style(self):
        s = Span("Hello", foreground="red")
        reset = s.reset_style()
        assert reset.text == "Hello"

    def test_span_width(self):
        s = Span("Hello")
        assert s.width() == 5

    def test_span_empty_width(self):
        s = Span("")
        assert s.width() == 0

    def test_span_immutability(self):
        s = Span("Hello")
        with pytest.raises(AttributeError, match="Span is immutable"):
            s._text = "World"
        with pytest.raises(AttributeError, match="Span is immutable"):
            s._inner = s._inner  # Try assigning the same value to trigger immutability error without changing type

    def test_span_to_core(self):
        s = Span("Hello")
        core_s = s._to_core()
        assert core_s is not None


class TestLine:
    """Tests for Line class."""

    def test_line_raw(self):
        l = Line("Hello")
        assert l.text == "Hello"

    def test_line_from_spans(self):
        spans = [Span("Hello"), Span(" "), Span("World")]
        l = Line(spans)
        assert l.text == "Hello World"

    def test_line_empty(self):
        l = Line(None)
        assert l.text == ""

    def test_line_from_spans_empty(self):
        l = Line([])
        assert l.text == ""

    def test_line_with_style(self):
        l = Line("Hello", style=Style(foreground="red"))
        assert l.text == "Hello"

    def test_line_with_alignment(self):
        l = Line("Hello", alignment="center")
        assert l.text == "Hello"

    def test_line_width(self):
        l = Line("Hello")
        assert l.width() == 5

    def test_line_left_aligned(self):
        l = Line("Hello")
        aligned = l.left_aligned()
        assert aligned.text == "Hello"

    def test_line_centered(self):
        l = Line("Hello")
        aligned = l.centered()
        assert aligned.text == "Hello"

    def test_line_right_aligned(self):
        l = Line("Hello")
        aligned = l.right_aligned()
        assert aligned.text == "Hello"

    def test_line_spans_method(self):
        l = Line("Hello")
        new_spans = [Span("New")]
        new_line = l.spans(new_spans)
        assert new_line.text == "New"

    def test_line_style_method(self):
        l = Line("Hello")
        styled = l.style(Style(foreground="red"))
        assert styled.text == "Hello"

    def test_line_patch_style(self):
        l = Line("Hello")
        patched = l.patch_style(Style(foreground="red"))
        assert patched.text == "Hello"

    def test_line_reset_style(self):
        l = Line("Hello", style=Style(foreground="red"))
        reset = l.reset_style()
        assert reset.text == "Hello"

    def test_line_immutability(self):
        l = Line("Hello")
        with pytest.raises(AttributeError, match="Line is immutable"):
            l._text = "World"
        with pytest.raises(AttributeError, match="Line is immutable"):
            l._inner = l._inner  # Try assigning the same value to trigger immutability error without changing type

    def test_line_to_core(self):
        l = Line("Hello")
        core_l = l._to_core()
        assert core_l is not None


class TestText:
    """Tests for Text class."""

    def test_text_raw(self):
        t = Text("Hello\nWorld")
        assert t.width() > 0
        assert t.height() == 2

    def test_text_from_lines(self):
        lines = [Line("Hello"), Line("World")]
        t = Text(lines)
        assert t.height() == 2
        assert len(t.lines()) == 2

    def test_text_empty(self):
        t = Text(None)
        assert t.height() == 1
        assert t.width() == 0

    def test_text_with_style(self):
        t = Text("Hello", style=Style(foreground="red"))
        assert t.height() == 1

    def test_text_with_alignment(self):
        t = Text("Hello", alignment="center")
        assert t.height() == 1

    def test_text_lines(self):
        t = Text("Line 1\nLine 2\nLine 3")
        lines = t.lines()
        assert len(lines) == 3
        assert "Line 1" in lines[0]
        assert "Line 2" in lines[1]
        assert "Line 3" in lines[2]

    def test_text_left_aligned(self):
        t = Text("Hello")
        aligned = t.left_aligned()
        assert aligned.text == "Hello"

    def test_text_centered(self):
        t = Text("Hello")
        aligned = t.centered()
        assert aligned.text == "Hello"

    def test_text_right_aligned(self):
        t = Text("Hello")
        aligned = t.right_aligned()
        assert aligned.text == "Hello"

    def test_text_style_method(self):
        t = Text("Hello")
        styled = t.style(Style(foreground="red"))
        assert styled.text == "Hello"

    def test_text_patch_style(self):
        t = Text("Hello")
        patched = t.patch_style(Style(foreground="red"))
        assert patched.text == "Hello"

    def test_text_reset_style(self):
        t = Text("Hello")
        reset = t.reset_style()
        assert reset.text == "Hello"

    def test_text_immutability(self):
        t = Text("Hello")
        with pytest.raises(AttributeError, match="Text is immutable"):
            t._text = "World"

    def test_text_to_core(self):
        t = Text("Hello")
        core_t = t._to_core()
        assert core_t is not None


class TestTextIntegration:
    """Integration tests for text primitives."""

    def test_spans_to_line_to_text(self):
        spans = [Span("A"), Span("B"), Span("C")]
        line = Line(spans)
        text = Text([line])
        assert len(text.lines()) == 1

    def test_multiline_text(self):
        text = Text("Line 1\nLine 2\nLine 3")
        assert text.height() == 3