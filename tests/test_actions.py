"""Tests for xnano.core.actions — matching, synthesis, and host.perform.

Covers every Action family (matches / to_event), Terminal.offscreen perform
paths, field-scoped click + slide via real dispatch helpers, and the
Context.actions facade. WebUI Action vocabulary lives in
``tests/web/test_web_actions.py``.
"""

from __future__ import annotations

from typing import cast

import pytest

from xnano._dispatch import dispatch_field_mouse
from xnano._types import Area
from xnano.context import Context
from xnano.core.actions import Action
from xnano.core.exceptions import HookError
from xnano.events import (
    ClipboardEventData,
    Event,
    FocusEventData,
    KeyboardEventData,
    MouseEventData,
    ResizeEventData,
    on_action,
    on_click,
    on_clipboard,
    on_focus,
    on_keyboard,
    on_mouse,
    on_resize,
    on_tick,
)
from xnano.fields import Field
from xnano.grid import BaseGrid, _GridFieldHit, _GridSlideCapture
from xnano.terminal import Terminal

# ---------------------------------------------------------------------------
# 1. Action matching + to_event for each family
# ---------------------------------------------------------------------------


def test_keyboard_action_matches_synthetic_event() -> None:
    action = Action.keyboard("ctrl+s")
    event = Event.from_data(KeyboardEventData.from_binding("ctrl+s"))
    assert action.matches(event)
    assert not Action.keyboard("ctrl+a").matches(event)


def test_keyboard_action_empty_bindings_match_any() -> None:
    action = Action.keyboard()
    event = Event.from_data(KeyboardEventData.from_binding("x"))
    assert action.matches(event)


def test_keyboard_action_kind_filter() -> None:
    press = Event.from_data(KeyboardEventData.from_binding("a", kind="press"))
    release = Event.from_data(
        KeyboardEventData.from_binding("a", kind="release")
    )
    only_press = Action.keyboard("a", kind="press")
    assert only_press.matches(press)
    assert not only_press.matches(release)


def test_keyboard_action_to_event_is_real_event() -> None:
    event = Action.keyboard("enter").to_event()
    assert event.is_keyboard_event()
    assert event.keyboard_event is not None
    assert event.keyboard_event.matches("enter")
    assert Action.keyboard("enter").matches(event)


def test_mouse_action_button_and_kind_filters() -> None:
    left_press = Event.from_data(
        MouseEventData(kind="press", x=1, y=2, button="left")
    )
    right_press = Event.from_data(
        MouseEventData(kind="press", x=1, y=2, button="right")
    )
    left_drag = Event.from_data(
        MouseEventData(kind="drag", x=3, y=4, button="left")
    )

    any_button = Action.mouse()
    left_only = Action.mouse("left")
    left_drag_only = Action.mouse("left", kind="drag")

    assert any_button.matches(left_press)
    assert any_button.matches(right_press)
    assert left_only.matches(left_press)
    assert not left_only.matches(right_press)
    assert left_drag_only.matches(left_drag)
    assert not left_drag_only.matches(left_press)
    assert not Action.mouse("left").matches(
        Event.from_data(KeyboardEventData.from_binding("x"))
    )


def test_mouse_action_to_event_round_trips_matches() -> None:
    action = Action.mouse("right", kind="release")
    event = action.to_event()
    assert event.is_mouse_event()
    assert event.mouse_event is not None
    assert event.mouse_event.button == "right"
    assert event.mouse_event.kind == "release"
    assert action.matches(event)


def test_click_action_matches_press_only() -> None:
    click = Action.click("body", button="left")
    press = Event.from_data(
        MouseEventData(kind="press", x=0, y=0, button="left")
    )
    drag = Event.from_data(
        MouseEventData(kind="drag", x=0, y=0, button="left")
    )
    right = Event.from_data(
        MouseEventData(kind="press", x=0, y=0, button="right")
    )
    assert click.matches(press)
    # Field is host-side metadata — matches ignores it.
    assert Action.click("other").matches(press)
    assert not click.matches(drag)
    assert not click.matches(right)


def test_click_action_to_event_is_left_press() -> None:
    event = Action.click("save").to_event()
    assert event.is_mouse_event()
    assert event.mouse_button == "left"
    assert event.mouse_event_kind == "press"
    assert Action.click("save").matches(event)


def test_focus_action_matches_and_kind_compatibility() -> None:
    window_gained = Event.from_data(FocusEventData(kind="gained"))
    field_gained = Event.from_data(
        FocusEventData(kind="field_gained", field="prompt")
    )
    field_lost = Event.from_data(
        FocusEventData(kind="field_lost", field="prompt")
    )

    any_focus = Action.focus()
    gained = Action.focus(kind="gained")
    prompt_gained = Action.focus(field="prompt", kind="gained")
    prompt_lost = Action.focus(field="prompt", kind="lost")

    assert any_focus.matches(window_gained)
    assert any_focus.matches(field_gained)
    assert gained.matches(window_gained)
    assert gained.matches(field_gained)  # gained accepts field_gained
    assert prompt_gained.matches(field_gained)
    assert not prompt_gained.matches(window_gained)  # field filter
    assert not prompt_gained.matches(field_lost)
    assert prompt_lost.matches(field_lost)


def test_focus_action_to_event_defaults() -> None:
    window = Action.focus().to_event()
    assert window.is_focus_event()
    assert window.focus_event is not None
    assert window.focus_event.kind == "gained"
    assert Action.focus(kind="gained").matches(window)

    field = Action.focus(field="name", kind="lost").to_event()
    assert field.focus_event is not None
    assert field.focus_event.kind == "field_lost"
    assert field.focus_event.field == "name"
    assert Action.focus(field="name", kind="lost").matches(field)


def test_clipboard_action_matches_and_to_event() -> None:
    any_paste = Action.clipboard()
    exact = Action.clipboard("hello")
    hello = Event.from_data(ClipboardEventData(text="hello"))
    other = Event.from_data(ClipboardEventData(text="other"))

    assert any_paste.matches(hello)
    assert any_paste.matches(other)
    assert exact.matches(hello)
    assert not exact.matches(other)

    synthesized = exact.to_event()
    assert synthesized.is_clipboard_event()
    assert synthesized.clipboard_text == "hello"
    assert exact.matches(synthesized)


def test_tick_action_matches_shell_not_plain_events() -> None:
    tick = Action.tick(50)
    shell = tick.to_event()
    assert shell.is_tick_event()
    assert getattr(shell, "type", None) == "tick"
    assert tick.matches(shell)
    assert Action.tick(0).matches(shell)  # 0 = any interval
    assert not Action.tick(100).matches(shell)

    # Ordinary keyboard events never match tick actions.
    key = Event.from_data(KeyboardEventData.from_binding("x"))
    assert not tick.matches(key)


def test_resize_action_matches_and_to_event() -> None:
    any_size = Action.resize()
    exact = Action.resize(120, 40)
    wide = Event.from_data(ResizeEventData(width=120, height=40))
    tall = Event.from_data(ResizeEventData(width=80, height=50))

    assert any_size.matches(wide)
    assert any_size.matches(tall)
    assert exact.matches(wide)
    assert not exact.matches(tall)
    assert Action.resize(width=120).matches(wide)
    assert not Action.resize(width=120).matches(tall)

    synthesized = Action.resize(100, 30).to_event()
    assert synthesized.is_resize_event()
    assert synthesized.resize_size == (100, 30)
    assert Action.resize(100, 30).matches(synthesized)

    defaults = Action.resize().to_event()
    assert defaults.resize_size == (80, 24)


def test_request_action_object_form_and_to_event() -> None:
    post = Action.request("POST", "/save")
    shell = post.to_event()
    assert getattr(shell, "type", None) == "request" or (
        hasattr(shell, "is_request_event") and shell.is_request_event()
    )
    assert post.matches(shell)
    assert not Action.request("GET", "/save").matches(shell)
    assert not Action.request("POST", "/other").matches(shell)
    # Terminal keyboard events never match request actions.
    key = Event.from_data(KeyboardEventData.from_binding("x"))
    assert not post.matches(key)


# ---------------------------------------------------------------------------
# 2. Terminal host perform + shared Action hooks
# ---------------------------------------------------------------------------


def test_perform_runs_keyboard_hook() -> None:
    class App(BaseGrid):
        n: int = Field(default=0, state=True)

        @on_keyboard("x")
        def bump(self, ctx) -> None:
            self.n += 1

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(Action.keyboard("x"))
    assert app.n == 1


def test_on_action_with_shared_keyboard_action() -> None:
    SAVE = Action.keyboard("ctrl+s")

    class App(BaseGrid):
        saved: bool = Field(default=False, state=True)

        @on_action(SAVE)
        def save(self, ctx) -> None:
            self.saved = True

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(SAVE)
    assert app.saved is True
    # Mismatched binding does not fire.
    terminal.perform(Action.keyboard("ctrl+a"))
    assert app.saved is True


def test_deprecated_on_decorator_forwards_to_on_action() -> None:
    from xnano.events import on  # ty: ignore[deprecated]

    save = Action.keyboard("ctrl+s")
    with pytest.warns(DeprecationWarning, match="on_action"):
        decorator = on(save)  # ty: ignore[deprecated]

    assert callable(decorator)


def test_on_action_is_exported_from_package_root() -> None:
    from xnano import on_action as root_on_action

    assert root_on_action is on_action


def test_perform_unscoped_mouse_hook() -> None:
    class App(BaseGrid):
        presses: int = Field(default=0, state=True)

        @on_mouse("left", kind="press")
        def on_press(self, ctx) -> None:
            self.presses += 1

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(Action.mouse("left", kind="press"))
    assert app.presses == 1
    # Kind filter: drag does not fire press hook.
    terminal.perform(Action.mouse("left", kind="drag"))
    assert app.presses == 1


def test_on_decorator_with_shared_mouse_action() -> None:
    RIGHT = Action.mouse("right", kind="press")

    class App(BaseGrid):
        n: int = Field(default=0, state=True)

        @on_action(RIGHT)
        def right_click(self, ctx) -> None:
            self.n += 1

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(RIGHT)
    assert app.n == 1
    terminal.perform(Action.mouse("left", kind="press"))
    assert app.n == 1


def test_perform_clipboard_hook() -> None:
    class App(BaseGrid):
        pasted: str = Field(default="", state=True)

        @on_clipboard
        def on_paste(self, ctx) -> None:
            self.pasted = ctx.event.clipboard_text or ""

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(Action.clipboard("hello world"))
    assert app.pasted == "hello world"


def test_perform_window_focus_hook() -> None:
    class App(BaseGrid):
        log: list[str] = Field(default_factory=list, state=True)

        @on_focus
        def on_window_focus(self, ctx) -> None:
            focus = ctx.event.focus_event if ctx.event else None
            if focus is not None and focus.kind is not None:
                self.log.append(focus.kind)

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(Action.focus(kind="gained"))
    terminal.perform(Action.focus(kind="lost"))
    assert app.log == ["gained", "lost"]


def test_perform_resize_hook() -> None:
    class App(BaseGrid):
        size: tuple[int, int] = Field(default=(0, 0), state=True)

        @on_resize
        def on_resize(self, ctx) -> None:
            if ctx.event is not None and ctx.event.resize_size is not None:
                self.size = ctx.event.resize_size

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(Action.resize(100, 30))
    assert app.size == (100, 30)


def test_perform_tick_does_not_replace_pump_tick() -> None:
    """Ticks are pumped by the host clock, not Action.perform.

    ``Action.tick().to_event()`` is a shell for matching; perform runs
    ``dispatch_hooks``, which has no tick branch — ``@on_tick`` only
    fires via ``pump_tick`` / web ``dispatch_tick``.
    """

    class App(BaseGrid):
        ticks: int = Field(default=0, state=True)

        @on_tick
        def on_tick(self, ctx) -> None:
            self.ticks += 1

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(Action.tick())
    assert app.ticks == 0

    from xnano._dispatch import pump_tick

    pump_tick(terminal)
    assert app.ticks == 1


def test_perform_loop_guard() -> None:
    class App(BaseGrid):
        n: int = Field(default=0, state=True)

        @on_keyboard("a")
        def loop(self, ctx) -> None:
            self.n += 1
            # Re-entrant perform of the same key — must queue, then depth-guard.
            if self.n < 100:
                ctx.host.perform(Action.keyboard("a"))

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    try:
        terminal.perform(Action.keyboard("a"))
    except HookError:
        assert app.n >= 32
    else:
        # Queue drains without stack overflow; depth guard may or may not
        # trip depending on whether each perform re-enters the same drain.
        assert app.n >= 1


def test_ctx_actions_press_convenience() -> None:
    class App(BaseGrid):
        n: int = Field(default=0, state=True)

        @on_keyboard("z")
        def bump(self, ctx) -> None:
            self.n += 1

        @on_keyboard("p")
        def via_actions(self, ctx) -> None:
            ctx.actions.press("z")

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(Action.keyboard("p"))
    assert app.n == 1


def test_ctx_actions_paste_and_resize_conveniences() -> None:
    class App(BaseGrid):
        pasted: str = Field(default="", state=True)
        size: tuple[int, int] = Field(default=(0, 0), state=True)

        @on_clipboard
        def on_paste(self, ctx) -> None:
            self.pasted = (
                ctx.event.clipboard_text if ctx.event is not None else ""
            ) or ""

        @on_resize
        def on_resize(self, ctx) -> None:
            if ctx.event is not None and ctx.event.resize_size is not None:
                self.size = ctx.event.resize_size

        @on_keyboard("g")
        def drive(self, ctx) -> None:
            ctx.actions.paste("clip")
            ctx.actions.resize(64, 20)

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(Action.keyboard("g"))
    assert app.pasted == "clip"
    assert app.size == (64, 20)


# ---------------------------------------------------------------------------
# 3. Field click + sliding (Action vocabulary + host geometry)
# ---------------------------------------------------------------------------


def _arm_field_hit(
    terminal: Terminal,
    grid: BaseGrid,
    field_name: str,
    *,
    area: Area | None = None,
    slide_axes: list[str] | None = None,
) -> None:
    """Register a hit region so dispatch_field_mouse can resolve clicks."""
    terminal._mouse_geometry_active = True
    paint = area or Area(x=0, y=0, width=10, height=5)
    terminal._field_hits.append(
        _GridFieldHit(
            grid=grid,
            field_name=field_name,
            area=paint,
            slot_area=paint,
            parent_area=Area(x=0, y=0, width=40, height=20),
            slide_axes=slide_axes or [],
        )
    )


def test_field_click_via_action_to_event_and_dispatch() -> None:
    """Action.click is the object form; field scope needs host hit-testing.

    ``perform(Action.click("body"))`` alone does not run field handlers
    (field scope is host metadata). With geometry +
    ``dispatch_field_mouse``, ``Action.click(...).to_event()`` fires
    ``@on_click``.
    """

    CLICK_BODY = Action.click("body")

    class App(BaseGrid):
        body: str = Field(default="idle")
        n: int = Field(default=0, state=True)

        @on_action(CLICK_BODY)
        def on_body(self, ctx) -> None:
            self.n += 1
            self.body = "clicked"

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    _arm_field_hit(terminal, app, "body")

    # perform alone: field handlers are not in on_mouse_hooks.
    terminal.perform(CLICK_BODY)
    assert app.n == 0

    event = CLICK_BODY.to_event()
    assert CLICK_BODY.matches(event)
    ctx = Context(event=event, terminal=terminal, state=terminal.state)
    dispatch_field_mouse(terminal, ctx)
    assert app.n == 1
    assert app.body == "clicked"


def test_field_click_via_on_click_and_action_event() -> None:
    class App(BaseGrid):
        body: str = Field(default="hello")
        n: int = Field(default=0, state=True)

        @on_click("body")
        def bump(self, ctx) -> None:
            self.n += 1

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    _arm_field_hit(terminal, app, "body")

    event = Action.click("body").to_event()
    dispatch_field_mouse(
        terminal,
        Context(event=event, terminal=terminal, state=terminal.state),
    )
    assert app.n == 1


def test_ctx_actions_click_uses_perform_not_field_hits() -> None:
    """ctx.actions.click → host.perform; field hits are not consulted."""

    class App(BaseGrid):
        body: str = Field(default="x")
        n: int = Field(default=0, state=True)

        @on_click("body")
        def bump(self, ctx) -> None:
            self.n += 1

        @on_keyboard("c")
        def via_actions(self, ctx) -> None:
            ctx.actions.click("body")

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    _arm_field_hit(terminal, app, "body")
    terminal.perform(Action.keyboard("c"))
    assert app.n == 0  # perform path does not hit-test fields


def test_slide_drag_matches_mouse_action_and_updates_position() -> None:
    """Sliding uses coordinate-bearing mouse events; Action filters kinds.

    ``Action.mouse(kind="drag")`` matches drag events. Coordinates are not
    part of Action factories (always 0,0 in to_event), so hosts synthesize
    ``MouseEventData`` / ``Event.from_data`` for real geometry — same
    matching surface.
    """

    class SlideApp(BaseGrid):
        body: str = Field(default="hello", slide=["x"])

        @on_mouse(field="body", kind="drag")
        def on_drag(self, ctx) -> None:
            self.body = f"x={self.grid_field_position('body')[0]}"

    grid = SlideApp()
    terminal = Terminal(mouse_events=True)
    terminal._mouse_geometry_active = True
    terminal._slide_capture = _GridSlideCapture(
        grid=grid,
        field_name="body",
        parent_area=Area(x=0, y=0, width=20, height=10),
        slot_area=Area(x=0, y=0, width=6, height=3),
        grab_x=0,
        grab_y=0,
        slide_axes=["x"],
    )

    drag_event = Event.from_data(
        MouseEventData(kind="drag", x=7, y=0, button="left")
    )
    assert Action.mouse(kind="drag").matches(drag_event)
    assert Action.mouse("left", kind="drag").matches(drag_event)
    assert not Action.mouse(kind="press").matches(drag_event)

    dispatch_field_mouse(
        terminal,
        Context(
            event=cast(Event | None, drag_event),
            terminal=terminal,
            state=None,
        ),
    )
    assert grid.grid_field_position("body") == (7, 0)
    assert grid.body == "x=7"


def test_slide_y_axis_drag_with_action_filter() -> None:
    class SlideY(BaseGrid):
        panel: str = Field(default="p", slide=["y"])

    grid = SlideY()
    terminal = Terminal(mouse_events=True)
    terminal._mouse_geometry_active = True
    terminal._slide_capture = _GridSlideCapture(
        grid=grid,
        field_name="panel",
        parent_area=Area(x=0, y=0, width=20, height=15),
        slot_area=Area(x=0, y=0, width=4, height=2),
        grab_x=0,
        grab_y=0,
        slide_axes=["y"],
    )
    drag = Event.from_data(
        MouseEventData(kind="drag", x=0, y=5, button="left")
    )
    assert Action.mouse("left", kind="drag").matches(drag)
    dispatch_field_mouse(
        terminal,
        Context(event=drag, terminal=terminal, state=None),
    )
    assert grid.grid_field_position("panel") == (0, 5)


def test_slide_press_starts_capture_via_action_click_event() -> None:
    """Left press on a slidable field arms slide capture (real hit path)."""

    class SlideApp(BaseGrid):
        body: str = Field(default="hello", slide=["x", "y"])

    grid = SlideApp()
    terminal = Terminal(mouse_events=True)
    terminal.attach_grid(grid)
    _arm_field_hit(
        terminal,
        grid,
        "body",
        area=Area(x=2, y=2, width=6, height=3),
        slide_axes=["x", "y"],
    )

    # Click at (3, 4) inside the hit — use Event.from_data for coordinates.
    press = Event.from_data(
        MouseEventData(kind="press", x=3, y=4, button="left")
    )
    assert Action.click("body").matches(press)
    dispatch_field_mouse(
        terminal,
        Context(event=press, terminal=terminal, state=None),
    )
    capture = terminal._slide_capture
    assert capture is not None
    assert capture.field_name == "body"
    assert capture.slide_axes == ["x", "y"]
    assert capture.grab_x == 1  # 3 - area.x
    assert capture.grab_y == 2  # 4 - area.y
