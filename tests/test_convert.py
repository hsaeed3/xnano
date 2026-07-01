import pytest
from xnano._convert import (
    _resolve_color,
    _resolve_modifier,
    as_span,
    as_line,
    as_text,
    as_lines,
    unwrap,
)
from xnano.color import Color
from xnano.style import Modifier
from xnano.text import Span, Line, Text
from xnano import _core

def test_resolve_color():
    # Test Color instance
    c = Color.from_name("red")
    assert isinstance(_resolve_color(c), _core.Color)
    
    # Test valid color name string
    assert isinstance(_resolve_color("blue"), _core.Color)
    
    # Test hex string
    assert isinstance(_resolve_color("#ff0000"), _core.Color)
    
    # Test invalid type
    with pytest.raises(TypeError):
        _resolve_color(123)  # type: ignore

def test_resolve_modifier():
    # Test Modifier instance
    m = Modifier("bold")
    assert isinstance(_resolve_modifier(m), _core.Modifier)
    
    # Test single modifier name string
    assert isinstance(_resolve_modifier("italic"), _core.Modifier)
    
    # Test sequence of modifier names
    assert isinstance(_resolve_modifier(["bold", "italic"]), _core.Modifier)
    
    # Test invalid type
    with pytest.raises(TypeError):
        _resolve_modifier(123)  # type: ignore

def test_as_span():
    # Test string
    assert isinstance(as_span("hello"), _core.Span)
    
    # Test Span
    span = Span("hello")
    assert isinstance(as_span(span), _core.Span)
    
    # Test Line
    line = Line("hello")
    assert isinstance(as_span(line), _core.Span)
    
    # Test Text
    text = Text("hello\nworld")
    assert isinstance(as_span(text), _core.Span)
    
    # Test empty text
    empty_text = Text([])
    assert isinstance(as_span(empty_text), _core.Span)
    
    # Test invalid type
    with pytest.raises(TypeError):
        as_span(123)  # type: ignore

def test_as_line():
    # Test string
    assert isinstance(as_line("hello"), _core.Line)
    
    # Test Span
    span = Span("hello")
    assert isinstance(as_line(span), _core.Line)
    
    # Test Line
    line = Line("hello")
    assert isinstance(as_line(line), _core.Line)
    
    # Test Text
    text = Text("hello\nworld")
    assert isinstance(as_line(text), _core.Line)
    
    # Test invalid type
    with pytest.raises(TypeError):
        as_line(123)  # type: ignore

def test_as_text():
    # Test string
    assert isinstance(as_text("hello"), _core.Text)
    
    # Test Span
    span = Span("hello")
    assert isinstance(as_text(span), _core.Text)
    
    # Test Line
    line = Line("hello")
    assert isinstance(as_text(line), _core.Text)
    
    # Test Text
    text = Text("hello\nworld")
    assert isinstance(as_text(text), _core.Text)
    
    # Test invalid type
    with pytest.raises(TypeError):
        as_text(123)  # type: ignore

def test_as_lines():
    # Test single Content
    lines = as_lines("hello")
    assert len(lines) == 1
    assert isinstance(lines[0], _core.Line)
    
    # Test list of Content
    lines_list = as_lines(["hello", Span("world")])
    assert len(lines_list) == 2
    assert isinstance(lines_list[0], _core.Line)
    assert isinstance(lines_list[1], _core.Line)

def test_unwrap():
    # Test object with _to_core
    c = Color.from_name("red")
    assert isinstance(unwrap(c), _core.Color)
    
    # Test object with _inner but no _to_core
    class MockWrapper:
        def __init__(self):
            self._inner = "mock_inner"
    assert unwrap(MockWrapper()) == "mock_inner"
    
    # Test plain value
    assert unwrap("plain") == "plain"
