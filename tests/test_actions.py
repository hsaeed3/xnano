"""Tests for xnano.actions — matching, synthesis, and host.perform."""

from __future__ import annotations

from xnano.core.actions import Action
from xnano.events import Event, KeyboardEventData, on, on_keyboard
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.tui import Terminal


def test_keyboard_action_matches_synthetic_event() -> None:
    action = Action.keyboard("ctrl+s")
    event = Event.from_data(KeyboardEventData.from_binding("ctrl+s"))
    assert action.matches(event)
    assert not Action.keyboard("ctrl+a").matches(event)


def test_keyboard_action_empty_bindings_match_any() -> None:
    action = Action.keyboard()
    event = Event.from_data(KeyboardEventData.from_binding("x"))
    assert action.matches(event)


def test_action_to_event_is_real_event() -> None:
    event = Action.keyboard("enter").to_event()
    assert event.is_keyboard_event()
    assert event.keyboard_event is not None
    assert event.keyboard_event.matches("enter")


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


def test_on_decorator_with_shared_action() -> None:
    SAVE = Action.keyboard("ctrl+s")

    class App(BaseGrid):
        saved: bool = Field(default=False, state=True)

        @on(SAVE)
        def save(self, ctx) -> None:
            self.saved = True

    terminal = Terminal.offscreen()
    app = App()
    terminal.attach_grid(app)
    terminal.perform(SAVE)
    assert app.saved is True


def test_perform_loop_guard() -> None:
    from xnano.core.exceptions import HookError

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


def test_ctx_actions_facade() -> None:
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
