"""tests.beta.test_events"""

from __future__ import annotations

from xnano.beta.events import (
    Event,
    KeyboardEventData,
    MouseEventData,
    ResizeEventData,
    event_from_core,
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


def test_event_from_core_smoke() -> None:
    # Offscreen sessions can synthesize core events; just ensure the
    # helper is importable and rejects nothing obvious when unused.
    assert callable(event_from_core)
