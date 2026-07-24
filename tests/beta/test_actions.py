"""tests.beta.test_actions

---

Verify every public beta action against matching and nonmatching events.
"""

from __future__ import annotations

import pytest

from xnano.beta.actions import Action
from xnano.beta.events import (
    ClipboardEventData,
    Event,
    FocusEventData,
    KeyboardEventData,
    MouseEventData,
    ResizeEventData,
    TickEventData,
)
from xnano.beta.requests import Request


@pytest.mark.parametrize(
    ("action", "matching", "nonmatching"),
    (
        (
            Action.keyboard("ctrl+s", kind="press"),
            Event.from_data(KeyboardEventData.from_binding("ctrl+s")),
            Event.from_data(KeyboardEventData.from_binding("ctrl+x")),
        ),
        (
            Action.mouse("right", kind="release"),
            Event.from_data(
                MouseEventData(
                    kind="release",
                    x=1,
                    y=2,
                    button="right",
                )
            ),
            Event.from_data(
                MouseEventData(
                    kind="press",
                    x=1,
                    y=2,
                    button="left",
                )
            ),
        ),
        (
            Action.click("save"),
            Event.from_data(
                MouseEventData(
                    kind="press",
                    x=1,
                    y=2,
                    button="left",
                    field="save",
                )
            ),
            Event.from_data(
                MouseEventData(
                    kind="release",
                    x=1,
                    y=2,
                    button="left",
                    field="save",
                )
            ),
        ),
        (
            Action.focus("editor", kind="field_gained"),
            Event.from_data(
                FocusEventData(kind="field_gained", field="editor")
            ),
            Event.from_data(FocusEventData(kind="field_lost", field="editor")),
        ),
        (
            Action.clipboard("expected"),
            Event.from_data(ClipboardEventData(text="expected")),
            Event.from_data(ClipboardEventData(text="other")),
        ),
        (
            Action.tick(16),
            Event.from_data(TickEventData(elapsed_ms=16)),
            Event.from_data(KeyboardEventData.from_binding("x")),
        ),
        (
            Action.resize(80, 24),
            Event.from_data(ResizeEventData(width=80, height=24)),
            Event.from_data(ResizeEventData(width=40, height=12)),
        ),
        (
            Action.request("POST", "/save"),
            Request.from_parts("POST", "/save"),
            Request.from_parts("GET", "/save"),
        ),
    ),
    ids=(
        "keyboard",
        "mouse",
        "click",
        "focus",
        "clipboard",
        "tick",
        "resize",
        "request",
    ),
)
def test_action_matches_only_its_declared_event(
    action,
    matching,
    nonmatching,
) -> None:
    assert action.matches(matching) is True
    assert action.matches(nonmatching) is False


def test_action_wildcards_match_payloads_but_not_other_event_types() -> None:
    keyboard = Event.from_data(KeyboardEventData.from_binding("z"))
    mouse = Event.from_data(
        MouseEventData(kind="move", x=3, y=4, button="unknown")
    )
    focus = Event.from_data(FocusEventData(kind="gained"))
    clipboard = Event.from_data(ClipboardEventData(text="anything"))
    resize = Event.from_data(ResizeEventData(width=10, height=5))

    assert Action.keyboard().matches(keyboard)
    assert Action.mouse().matches(mouse)
    assert Action.click().matches(mouse) is False
    assert Action.focus().matches(focus)
    assert Action.clipboard().matches(clipboard)
    assert Action.resize().matches(resize)
    assert Action.keyboard().matches(mouse) is False


def test_actions_facade_dispatches_each_keyboard_binding() -> None:
    class Runtime:
        performed = []

        def perform(self, action) -> None:
            self.performed.append(action)

    from xnano.beta.actions import Actions

    runtime = Runtime()
    actions = Actions(runtime)
    actions.keyboard("a", "b", kind="repeat")
    assert [action.bindings for action in runtime.performed] == [
        ("a",),
        ("b",),
    ]
    assert all(action.kind == "repeat" for action in runtime.performed)
