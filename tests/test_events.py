import pytest
from unittest import mock
from xnano.events import Event, EventHandler, on_key, on_mouse, poll_event, read_event
from xnano.keyboard import KeyEvent, _parse_binding, _event_matches_binding
from xnano.mouse import MouseEvent
from xnano import _core

def test_event_cannot_be_instantiated_directly():
    with pytest.raises(TypeError, match="Event instances are created internally"):
        Event()

def test_key_event_cannot_be_instantiated_directly():
    with pytest.raises(TypeError, match="KeyEvent instances are created internally"):
        KeyEvent()

def test_event_from_core_key():
    # Mock core.KeyEvent
    mock_key = mock.Mock(spec=_core.KeyEvent)
    mock_key.code_name = _core.KeyCode.Char
    mock_key.char.return_value = "q"
    mock_key.kind = _core.KeyEventKind.Press
    mock_key.modifiers = mock.Mock(spec=_core.KeyModifiers)
    mock_key.modifiers.control.return_value = False
    mock_key.modifiers.shift.return_value = False
    mock_key.modifiers.alt.return_value = False
    
    # Mock core.Event
    mock_core_event = mock.Mock(spec=_core.Event)
    mock_core_event.kind = "key"
    mock_core_event.key = mock_key
    mock_core_event.mouse = None
    mock_core_event.width = None
    mock_core_event.height = None
    mock_core_event.paste = None
    
    event = Event._from_core(mock_core_event)
    assert event.kind == "key"
    assert event.key is not None
    assert event.key.code == _core.KeyCode.Char
    assert event.key.char == "q"
    assert event.key.is_press is True
    assert event.key.is_repeat is False
    assert event.key.is_release is False
    assert event.key.ctrl is False
    assert event.key.shift is False
    assert event.key.alt is False
    assert event.width is None
    assert event.height is None
    assert event.paste is None
    assert event.mouse is None
    assert repr(event) == repr(mock_core_event)
    assert event._to_core() is mock_core_event
    assert event.key._to_core() is mock_key
    assert repr(event.key) == repr(mock_key)

def test_key_event_kinds():
    # Repeat
    mock_key = mock.Mock(spec=_core.KeyEvent)
    mock_key.code_name = _core.KeyCode.Char
    mock_key.char.return_value = "q"
    mock_key.kind = _core.KeyEventKind.Repeat
    mock_key.modifiers = mock.Mock(spec=_core.KeyModifiers)
    key_event = KeyEvent._from_core(mock_key)
    assert key_event.is_press is False
    assert key_event.is_repeat is True
    assert key_event.is_release is False

    # Release
    mock_key.kind = _core.KeyEventKind.Release
    key_event2 = KeyEvent._from_core(mock_key)
    assert key_event2.is_press is False
    assert key_event2.is_repeat is False
    assert key_event2.is_release is True

def test_event_from_core_mouse():
    mock_mouse = mock.Mock(spec=_core.MouseEvent)
    mock_mouse.kind = "down"
    mock_mouse.x = 10
    mock_mouse.y = 20
    mock_mouse.button = "left"
    
    mock_core_event = mock.Mock(spec=_core.Event)
    mock_core_event.kind = "mouse"
    mock_core_event.key = None
    mock_core_event.mouse = mock_mouse
    
    event = Event._from_core(mock_core_event)
    assert event.kind == "mouse"
    assert event.key is None
    assert event.mouse is not None
    assert event.mouse.kind == "down"
    assert event.mouse.x == 10
    assert event.mouse.y == 20
    assert event.mouse.button == "left"

def test_event_from_core_resize():
    mock_core_event = mock.Mock(spec=_core.Event)
    mock_core_event.kind = "resize"
    mock_core_event.key = None
    mock_core_event.mouse = None
    mock_core_event.width = 80
    mock_core_event.height = 24
    
    event = Event._from_core(mock_core_event)
    assert event.kind == "resize"
    assert event.key is None
    assert event.width == 80
    assert event.height == 24

def test_event_from_core_paste():
    mock_core_event = mock.Mock(spec=_core.Event)
    mock_core_event.kind = "paste"
    mock_core_event.key = None
    mock_core_event.mouse = None
    mock_core_event.paste = "pasted text"
    
    event = Event._from_core(mock_core_event)
    assert event.kind == "paste"
    assert event.paste == "pasted text"

def test_mouse_event_direct_creation():
    me = MouseEvent("up", 5, 5, "right")
    assert me.kind == "up"
    assert me.x == 5
    assert me.y == 5
    assert me.button == "right"
    assert repr(me) == "MouseEvent(kind='up', x=5, y=5, button='right')"
    
    with pytest.raises(AttributeError):
        me.kind = "down"
    with pytest.raises(AttributeError):
        del me.kind

def test_mouse_event_from_core():
    mock_mouse = mock.Mock(spec=_core.MouseEvent)
    mock_mouse.kind = "moved"
    mock_mouse.x = 1
    mock_mouse.y = 2
    mock_mouse.button = "unknown"
    
    me = MouseEvent._from_core(mock_mouse)
    assert me.kind == "moved"
    assert me.x == 1
    assert me.y == 2
    assert me.button == "unknown"

def test_keyboard_parse_binding_errors():
    with pytest.raises(ValueError, match="unknown key in binding"):
        _parse_binding("")
    with pytest.raises(ValueError, match="unknown modifier"):
        _parse_binding("ctrl+invalid+c")
    with pytest.raises(ValueError, match="invalid function key"):
        _parse_binding("f13")
    with pytest.raises(ValueError, match="unknown key in binding"):
        _parse_binding("ctrl+alt+longkeyname")

def test_event_matches_binding():
    # Mock event that returns False for matches when parsing fails
    mock_key = mock.Mock(spec=_core.KeyEvent)
    assert _event_matches_binding(mock_key, "ctrl+invalid+c") is False

    # Mock Key code non-match
    mock_key.code_name = _core.KeyCode.Esc
    assert _event_matches_binding(mock_key, "enter") is False

    # Shift tab special case
    # binding: shift+tab (code Tab, shift True, ctrl False, alt False)
    # event: BackTab, shift True, ctrl False, alt False
    mock_key.code_name = _core.KeyCode.BackTab
    mock_key.modifiers = mock.Mock(spec=_core.KeyModifiers)
    mock_key.modifiers.control.return_value = False
    mock_key.modifiers.shift.return_value = True
    mock_key.modifiers.alt.return_value = False
    assert _event_matches_binding(mock_key, "shift+tab") is True

    # Character check
    mock_key.code_name = _core.KeyCode.Char
    mock_key.char.return_value = None
    assert _event_matches_binding(mock_key, "q") is False

    mock_key.char.return_value = "Q"
    mock_key.modifiers.control.return_value = False
    mock_key.modifiers.shift.return_value = False
    mock_key.modifiers.alt.return_value = False
    assert _event_matches_binding(mock_key, "q") is True
    assert _event_matches_binding(mock_key, "w") is False

    # Modifier mismatch
    mock_key.modifiers.control.return_value = True
    assert _event_matches_binding(mock_key, "q") is False
    
    mock_key.modifiers.control.return_value = False
    mock_key.modifiers.alt.return_value = True
    assert _event_matches_binding(mock_key, "q") is False

    # Shift modifier mismatch (on non-char key)
    mock_key.code_name = _core.KeyCode.Enter
    mock_key.modifiers.control.return_value = False
    mock_key.modifiers.shift.return_value = True
    mock_key.modifiers.alt.return_value = False
    assert _event_matches_binding(mock_key, "enter") is False

def test_key_event_immutability():
    mock_key = mock.Mock(spec=_core.KeyEvent)
    key_event = KeyEvent._from_core(mock_key)
    with pytest.raises(AttributeError):
        setattr(key_event, "kind", "press")
    with pytest.raises(AttributeError):
        del key_event._inner

def test_event_handler_and_decorators():
    handler = EventHandler()
    
    # Decorators on free functions (on_key, on_mouse)
    @on_key("ctrl+c")
    @on_mouse("down")
    def my_handler(event):
        pass
        
    handler.register(my_handler)
    assert len(handler._key_handlers) == 1
    assert len(handler._mouse_handlers) == 1

    # Registering non-decorated function
    def raw_func(event):
        pass
    with pytest.raises(ValueError, match="is not decorated"):
        handler.register(raw_func)

    # Dispatching key event
    mock_key = mock.Mock(spec=_core.KeyEvent)
    mock_key.code_name = _core.KeyCode.Char
    mock_key.char.return_value = "c"
    mock_key.kind = _core.KeyEventKind.Press
    mock_key.modifiers = mock.Mock(spec=_core.KeyModifiers)
    mock_key.modifiers.control.return_value = True
    mock_key.modifiers.shift.return_value = False
    mock_key.modifiers.alt.return_value = False
    
    mock_core_event = mock.Mock(spec=_core.Event)
    mock_core_event.kind = "key"
    mock_core_event.key = mock_key
    mock_core_event.mouse = None
    
    event = Event._from_core(mock_core_event)
    
    called = []
    @handler.on_key("ctrl+c")
    def ctrl_c_handler(evt):
        called.append(evt)
        
    res = handler.dispatch(event)
    assert res is True
    assert len(called) == 1

    # Dispatching mouse event
    mock_mouse = mock.Mock(spec=_core.MouseEvent)
    mock_mouse.kind = "down"
    mock_mouse.x = 0
    mock_mouse.y = 0
    mock_mouse.button = "left"
    mock_core_event.kind = "mouse"
    mock_core_event.key = None
    mock_core_event.mouse = mock_mouse
    event = Event._from_core(mock_core_event)
    
    called_mouse = []
    @handler.on_mouse("down")
    def down_handler(evt):
        called_mouse.append(evt)
        
    res = handler.dispatch(event)
    assert res is True
    assert len(called_mouse) == 1

    # Repr
    assert repr(handler) == f"EventHandler(key_handlers={len(handler._key_handlers)}, mouse_handlers={len(handler._mouse_handlers)})"

def test_poll_and_read_event():
    with mock.patch("xnano._core.poll_event") as mock_poll:
        mock_poll.return_value = None
        assert poll_event(100) is None
        
        mock_evt = mock.Mock(spec=_core.Event)
        mock_poll.return_value = mock_evt
        res = poll_event(100)
        assert isinstance(res, Event)
        assert res._to_core() is mock_evt

    with mock.patch("xnano._core.read_event") as mock_read:
        mock_evt = mock.Mock(spec=_core.Event)
        mock_read.return_value = mock_evt
        res = read_event()
        assert isinstance(res, Event)
        assert res._to_core() is mock_evt
