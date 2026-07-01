import pytest
from xnano.scroll import Scrollbar, ScrollbarState
from xnano.style import Style
from xnano import _core

def test_scrollbar():
    style = Style(foreground="red")
    sb = Scrollbar(
        "vertical_right",
        style=style,
        thumb_style=style,
        track_style=style,
        begin_style=style,
        end_style=style,
        begin_symbol="^",
        end_symbol="v"
    )
    
    assert sb._to_core() is not None
    assert repr(sb) is not None
    
    sb2 = Scrollbar._from_core(sb._to_core())
    assert repr(sb2) == repr(sb)
    
    with pytest.raises(AttributeError):
        sb.style = style
    with pytest.raises(AttributeError):
        del sb._inner


def test_scrollbar_state():
    state = ScrollbarState(100)
    assert state._to_core() is not None
    assert repr(state) is not None
    
    # State mutation methods
    state.set_position(10)
    state.set_content_length(200)
    
    # viewport_content_length (returns a new state)
    state2 = state.viewport_content_length(20)
    assert isinstance(state2, ScrollbarState)
    
    # Navigation
    state.prev()
    state.next()
    state.first()
    state.last()
    
    # scroll direction
    state.scroll("forward")
    state.scroll("backward")
    
    # Constructor from native
    state3 = ScrollbarState._from_core(state._to_core())
    assert repr(state3) == repr(state)
