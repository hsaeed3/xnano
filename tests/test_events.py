"""tests.test_events"""

from __future__ import annotations

from xnano.events import (
    ClipboardEventData,
    Event,
    FocusEventData,
    KeyboardEventData,
    MouseEventData,
    ResizeEventData,
    TickEventData,
    normalize_keyboard_binding,
)


def test_keyboard_from_binding_and_matches() -> None:
    data = KeyboardEventData.from_binding("ctrl+s")
    event = Event.from_data(data)
    assert event.is_keyboard_event()
    assert event.keyboard_key == "s"
    assert data.matches("ctrl+s")
    assert not data.matches("ctrl+c")


def test_mouse_and_resize_payloads() -> None:
    mouse = Event.from_data(
        MouseEventData(kind="press", x=2, y=3, button="left")
    )
    assert mouse.mouse_position == (2, 3)
    resize = Event.from_data(ResizeEventData(width=80, height=24))
    assert resize.resize_size == (80, 24)


def test_normalize_binding_aliases() -> None:
    assert normalize_keyboard_binding("esc") == (frozenset(), "escape")
    assert normalize_keyboard_binding("return") == (frozenset(), "enter")


def test_uniform_event_accessors_across_user_input_types() -> None:
    keyboard = Event.from_data(
        KeyboardEventData.from_binding(
            "ctrl+s",
            kind="repeat",
            character="s",
        )
    )
    mouse = Event.from_data(
        MouseEventData(kind="drag", x=4, y=5, button="left")
    )
    clipboard = Event.from_data(ClipboardEventData("pasted"))
    focus = Event.from_data(FocusEventData(kind="field_gained", field="name"))
    tick = Event.from_data(TickEventData(elapsed_ms=16))

    assert keyboard.keyboard_event is not None
    assert keyboard.keyboard_event_kind == "repeat"
    assert keyboard.keyboard_modifiers == ["ctrl"]
    assert keyboard.keyboard_event.character == "s"
    assert mouse.mouse_event_kind == "drag"
    assert mouse.mouse_button == "left"
    assert clipboard.is_clipboard_event()
    assert clipboard.clipboard_text == "pasted"
    assert focus.is_focus_event()
    assert focus.focus_event is not None
    assert focus.focus_event.field == "name"
    assert tick.is_tick_event()
    assert tick.tick_event is not None
    assert tick.tick_event.elapsed_ms == 16
    assert tick.keyboard_event is None
    assert tick.keyboard_modifiers == []
