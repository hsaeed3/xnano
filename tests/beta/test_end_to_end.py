"""tests.beta.test_end_to_end

---

Exercise beta's public hooks and browser event path through a real runtime,
including the repaint that makes mutations visible to users.
"""

from __future__ import annotations

import dataclasses

import pytest

from xnano.beta import hooks
from xnano.beta.actions import Action
from xnano.beta.core import Runtime
from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid


@pytest.mark.parametrize(
    ("action", "decorator"),
    (
        (Action.keyboard("ctrl+s"), hooks.on_keyboard("ctrl+s")),
        (
            Action.mouse("right", kind="release"),
            hooks.on_mouse("right", kind="release"),
        ),
        (Action.click("content"), hooks.on_click("content")),
        (Action.clipboard("pasted"), hooks.on_clipboard),
        (Action.resize(30, 6), hooks.on_resize),
        (
            Action.focus("content", kind="gained"),
            hooks.on_focus("content", kind="gained"),
        ),
        (Action.tick(10), hooks.on_tick(10)),
    ),
    ids=(
        "keyboard",
        "mouse",
        "click",
        "clipboard",
        "resize",
        "focus",
        "tick",
    ),
)
def test_event_hook_mutation_is_visible_after_repaint(
    action,
    decorator,
) -> None:
    def handle_event(self) -> None:
        self.content = "changed"

    class App(BaseGrid):
        content: str = Field(default="initial", group="content")

    setattr(App, "handle_event", decorator(handle_event))
    runtime = Runtime.offscreen(30, 6)
    try:
        app = App()
        runtime.set_root(app)
        assert "initial" in runtime.render().text
        runtime.perform(action)
        assert app.content == "changed"
        assert "changed" in runtime.render().text
    finally:
        runtime.close()


def test_frame_idle_state_field_and_event_hooks_repaint() -> None:
    @dataclasses.dataclass
    class State:
        ready: bool = True

    class App(BaseGrid):
        count: int = Field(default=1, state=True)
        content: str = Field(default="initial")
        calls: list[str] = Field(default_factory=list, state=True)

        @hooks.on_poll("frame")
        def frame_hook(self) -> None:
            if "frame" not in self.calls:
                self.calls.append("frame")

        @hooks.on_poll("idle")
        def idle_hook(self) -> None:
            self.calls.append("idle")

        @hooks.on_state("ready == True")
        def state_hook(self) -> None:
            if "state" not in self.calls:
                self.calls.append("state")

        @hooks.on_field("count > 0")
        def field_hook(self) -> None:
            if "field" not in self.calls:
                self.calls.append("field")
                self.content = "field changed"

        @hooks.on_event
        def event_hook(self) -> None:
            self.calls.append("event")

    runtime = Runtime.offscreen(30, 6, state=State())
    try:
        app = App()
        runtime.set_root(app)
        frame = runtime.render()
        assert "field changed" in frame.text
        assert {"frame", "state", "field"} <= set(app.calls)
        runtime.pump()
        assert "idle" in app.calls
        assert "event" in app.calls
    finally:
        runtime.close()


def test_on_action_mutates_and_repaints() -> None:
    class App(BaseGrid):
        content: str = Field(default="initial")

        @hooks.on_action(Action.keyboard("enter"))
        def submit(self) -> None:
            self.content = "submitted"

    runtime = Runtime.offscreen(30, 6)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        runtime.perform(Action.keyboard("enter"))
        assert "submitted" in runtime.render().text
    finally:
        runtime.close()


def test_hook_filters_reject_nonmatching_events() -> None:
    class App(BaseGrid):
        content: str = Field(default="unchanged", group="target")

        @hooks.on_keyboard("ctrl+s", kind="press")
        def keyboard(self) -> None:
            self.content = "keyboard"

        @hooks.on_mouse("right", kind="release")
        def mouse(self) -> None:
            self.content = "mouse"

        @hooks.on_focus("content", kind="gained")
        def focus(self) -> None:
            self.content = "focus"

    runtime = Runtime.offscreen(30, 6)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        runtime.perform(Action.keyboard("ctrl+x"))
        runtime.perform(Action.mouse("left", kind="press"))
        runtime.perform(Action.focus("other", kind="lost"))
        assert app.content == "unchanged"
        assert "unchanged" in runtime.render().text
    finally:
        runtime.close()


def test_request_action_dispatches_route_and_repaints() -> None:
    from xnano.beta.requests import on_post_request

    class App(BaseGrid):
        content: str = Field(default="waiting")

        @on_post_request("/run")
        def run_request(self) -> None:
            self.content = "request handled"

    runtime = Runtime.offscreen(30, 6)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        runtime.perform(Action.request("POST", "/run"))
        assert "request handled" in runtime.render().text
    finally:
        runtime.close()


def test_interactive_components_receive_runtime_keyboard_and_repaint() -> None:
    from xnano.beta.components import Dropdown, Input, Options, Table

    class App(BaseGrid, direction="vertical"):
        input: Input = Field(
            default_factory=Input,
            group="input",
            autofocus=True,
            height=1,
        )
        dropdown: Dropdown = Field(
            default_factory=lambda: Dropdown(items=("one", "two")),
            group="dropdown",
            height=1,
        )
        options: Options = Field(
            default_factory=lambda: Options(
                items=("alpha", "beta"),
                searchable=False,
            ),
            group="options",
            height=3,
        )
        table: Table = Field(
            default_factory=lambda: Table(
                data=[{"name": "first"}, {"name": "second"}],
                focusable=True,
            ),
            group="table",
            height=3,
        )

    runtime = Runtime.offscreen(40, 10)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()

        runtime.perform(Action.keyboard("a"))
        assert app.input.value == "a"
        assert "a" in runtime.render().text

        assert runtime.focus("dropdown")
        runtime.perform(Action.keyboard("down"))
        assert app.dropdown.open is True
        runtime.perform(Action.keyboard("down"))
        assert app.dropdown.value == "two"
        runtime.perform(Action.keyboard("enter"))
        assert app.dropdown.open is False
        assert "two" in runtime.render().text

        assert runtime.focus("options")
        runtime.perform(Action.keyboard("down"))
        assert app.options.value == "beta"
        assert "beta" in runtime.render().text

        assert runtime.focus("table")
        runtime.perform(Action.keyboard("down"))
        assert app.table.value == {"name": "second"}
        assert "second" in runtime.render().text
    finally:
        runtime.close()


def test_button_and_link_activation_bubble_to_hooks_and_repaint() -> None:
    from xnano.beta.components import Button, Link

    class App(BaseGrid, direction="vertical"):
        button: Button = Field(
            default_factory=lambda: Button(label="Submit"),
            group="button",
            autofocus=True,
        )
        link: Link = Field(
            default_factory=lambda: Link(
                "Documentation",
                url="https://example.com",
            ),
            group="link",
        )
        status: str = Field(default="waiting")

        @hooks.on_keyboard("enter")
        def activate(self, ctx) -> None:
            self.status = ctx.focused_group or "none"

    runtime = Runtime.offscreen(40, 8)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        runtime.perform(Action.keyboard("enter"))
        assert app.status == "button"
        assert "button" in runtime.render().text

        assert runtime.focus("link")
        runtime.perform(Action.keyboard("enter"))
        assert app.status == "link"
        assert "link" in runtime.render().text
    finally:
        runtime.close()


def test_browser_event_dispatch_mutates_and_repaints() -> None:
    from xnano.beta.server.native import _browser_event

    class App(BaseGrid):
        content: str = Field(default="initial")

        @hooks.on_keyboard("x")
        def edit(self) -> None:
            self.content = "browser changed"

    runtime = Runtime.offscreen(30, 6)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        runtime.dispatch(
            _browser_event(
                {
                    "type": "keyboard",
                    "binding": "x",
                    "kind": "press",
                    "character": "x",
                }
            )
        )
        assert "browser changed" in runtime.render().text
    finally:
        runtime.close()
