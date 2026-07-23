"""tests.beta.test_hooks"""

from __future__ import annotations

from xnano.beta import hooks
from xnano.beta.actions import Action
from xnano.beta.grids import BaseGrid


def test_beta_hooks_are_collected_by_grid_markers() -> None:
    class App(BaseGrid):
        @hooks.on_keyboard("ctrl+s", kind="press")
        def save(self) -> None:
            pass

        @hooks.on_click(group="actions")
        def click_action(self) -> None:
            pass

        @hooks.on_focus("editor", kind="gained")
        def focus_editor(self) -> None:
            pass

        @hooks.on_poll("frame")
        def poll_frame(self) -> None:
            pass

        @hooks.on_tick(25)
        def tick(self) -> None:
            pass

    assert getattr(App.save, hooks.ON_KEYBOARD_FILTER_ATTR) == (
        ("ctrl+s",),
        "press",
    )
    assert getattr(App.click_action, hooks.ON_MOUSE_GROUP_ATTR) == "actions"
    assert getattr(App.focus_editor, hooks.ON_FOCUS_FIELD_ATTR) == "editor"
    assert getattr(App.poll_frame, hooks.ON_POLL_WHEN_ATTR) == "frame"
    assert getattr(App.tick, hooks.ON_TICK_INTERVAL_ATTR) == 25


def test_beta_hook_markers_cover_unfiltered_decorators() -> None:
    @hooks.on_event
    def event() -> None:
        pass

    @hooks.on_resize
    def resize() -> None:
        pass

    @hooks.on_clipboard
    def clipboard() -> None:
        pass

    @hooks.on_state("ready")
    def state() -> None:
        pass

    @hooks.on_field("count > 0")
    def field() -> None:
        pass

    assert getattr(event, "__xnano_on_event__") is True
    assert getattr(resize, "__xnano_on_resize__") is True
    assert getattr(clipboard, "__xnano_on_clipboard__") is True
    assert getattr(state, "__xnano_on_state_expression__") == "ready"
    assert getattr(field, "__xnano_on_field_expression__") == "count > 0"


def test_on_action_uses_beta_hook_markers() -> None:
    @hooks.on_action(Action.keyboard("escape"))
    def close() -> None:
        pass

    assert getattr(close, "__xnano_on_keyboard_filter__") == (
        ("escape",),
        None,
    )
