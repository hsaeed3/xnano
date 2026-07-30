"""tests.test_context"""

from __future__ import annotations

from typing import cast

from xnano.context import Context
from xnano.core.runtime import Runtime
from xnano.events import AbstractEventData, Event, KeyboardEventData
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.hooks import on_keyboard


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
    ctx = Context(
        event=event,
        terminal=cast(Runtime[dict[str, bool]], facade),
        state={"ok": True},
    )

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
    ctx = Context(
        event=Event.from_data(AbstractEventData()),
        terminal=cast(Runtime[None], facade),
        state=None,
    )
    event = Event.from_data(KeyboardEventData.from_binding("q"))
    next_ctx = ctx.with_event(event)
    assert next_ctx.event is event
    assert next_ctx.terminal is facade


def test_ctx_cursor_and_device_are_runtime_objects() -> None:
    """Context exposes the same controls as its runtime."""
    from xnano.core.runtime import Runtime
    from xnano.cursor import Cursor
    from xnano.device import Device

    runtime = Runtime.offscreen(20, 6)
    try:
        ctx = Context(
            event=Event.from_data(AbstractEventData()),
            terminal=runtime.terminal,
            state=None,
        )
        assert isinstance(ctx.cursor, Cursor)
        assert isinstance(ctx.device, Device)
        assert hasattr(ctx.cursor, "get_position")
        assert ctx.runtime is runtime.terminal
        runtime.cursor.move(3, 3)
        assert runtime.cursor.position == (3, 3)
        assert ctx.cursor.get_position() == (3, 3)
    finally:
        runtime.close()


def test_real_hook_context_combines_state_runtime_and_rendering() -> None:
    class App(BaseGrid):
        message: str = Field(default="waiting")

        @on_keyboard("enter")
        def submit(self, ctx: Context[dict[str, str]]) -> None:
            state = ctx.get_state()
            self.message = f"{state['name']}:{ctx.surface}:{ctx.render_size}"

    runtime = Runtime.offscreen(45, 6, state={"name": "Ada"})
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        runtime.dispatch(
            Event.from_data(KeyboardEventData.from_binding("enter"))
        )

        frame = runtime.render()
        assert frame.contains("Ada:offscreen:small")
    finally:
        runtime.close()
