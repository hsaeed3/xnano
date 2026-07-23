"""tests.beta.test_context"""

from __future__ import annotations

from xnano.beta.context import Context
from xnano.beta.events import Event, KeyboardEventData


class _Facade:
    def __init__(self) -> None:
        self.focused_group = None
        self._focused = None
        self.cursor = object()
        self.device = object()
        self.actions = object()
        self.stage = object()
        self.surface = "offscreen"
        self.runtime = self

    def focus_group(self, group: str) -> bool:
        self.focused_group = group
        return True

    def blur_field(self) -> None:
        self.focused_group = None


def test_context_keyboard_and_focus_helpers() -> None:
    facade = _Facade()
    event = Event.from_data(KeyboardEventData.from_binding("enter"))
    ctx = Context(event=event, terminal=facade, state={"ok": True})

    assert ctx.has_keyboard_event()
    assert ctx.keyboard is not None
    assert ctx.keyboard.matches("enter")
    assert ctx.get_state() == {"ok": True}
    assert ctx.runtime is facade
    assert ctx.surface == "offscreen"
    assert ctx.focus("main") is True
    assert ctx.is_focused("main")
    ctx.blur()
    assert ctx.focused_group is None


def test_context_with_event() -> None:
    facade = _Facade()
    ctx = Context(event=None, terminal=facade, state=None)
    event = Event.from_data(KeyboardEventData.from_binding("q"))
    next_ctx = ctx.with_event(event)
    assert next_ctx.event is event
    assert next_ctx.terminal is facade


def test_ctx_cursor_and_device_are_beta_runtime_objects() -> None:
    """Context exposes the same beta-owned controls as its runtime."""
    from xnano.beta.core.runtime import Runtime
    from xnano.beta.cursor import Cursor
    from xnano.beta.device import Device

    runtime = Runtime.offscreen(20, 6)
    try:
        ctx = Context(event=None, terminal=runtime.terminal, state=None)
        assert isinstance(ctx.cursor, Cursor)
        assert isinstance(ctx.device, Device)
        assert hasattr(ctx.cursor, "get_position")
        assert ctx.runtime is runtime.terminal
        runtime.cursor.move(3, 3)
        assert runtime.cursor.position == (3, 3)
        assert ctx.cursor.get_position() == (3, 3)
    finally:
        runtime.close()
