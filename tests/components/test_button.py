"""Tests for ``Button`` focus states and keyboard bubbling."""

from __future__ import annotations

from typing import Any

from xnano.actions import Action
from xnano.components.button import Button
from xnano.components.component import ComponentRenderContext
from xnano.components.dropdown import Dropdown
from xnano.components.input import Input
from xnano.core.content import Panel, TextBlock
from xnano.core.runtime import Runtime
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.hooks import on_click
from xnano.types import Area, is_focusable_component


def _ctx() -> ComponentRenderContext[Any]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=30, height=5))


def _kbd(**kwargs: Any) -> Any:
    character = kwargs.get("character")
    matches = set(kwargs.get("matches", ()))

    class _K:
        def __init__(self) -> None:
            self.kind = kwargs.get("kind", "press")
            self.character = character

        def matches(self, *bindings: str) -> bool:
            return any(binding in matches for binding in bindings)

    return _K()


def _block_text(content: Any) -> str:
    if isinstance(content, Panel):
        content = content.child
    assert isinstance(content, TextBlock)
    if content.lines:
        return "".join(run.text for run in content.lines[0])
    return content.text


def test_default_chrome_wraps_label() -> None:
    button = Button(label="Submit")
    content = button.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert _block_text(content) == "[ Submit ]"


def test_custom_left_right_chrome() -> None:
    button = Button(label="Go", left="<", right=">")
    assert _block_text(button.compose(_ctx())) == "<Go>"


def test_compose_idle_uses_base_colors() -> None:
    button = Button(
        label="Ok",
        foreground="green",
        background="black",
    )
    content = button.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.color == "green"
    assert content.background == "black"
    run = content.lines[0][0]
    assert run.color == "green"
    assert run.background == "black"


def test_compose_focused_uses_focused_colors_and_panel() -> None:
    button = Button(
        label="Ok",
        foreground="green",
        focused_color="black",
        focused_background="yellow",
    )
    button._input_focused = True
    assert button.focused is True
    content = button.compose(_ctx())
    assert isinstance(content, Panel)
    assert isinstance(content.child, TextBlock)
    assert content.child.color == "black"
    assert content.child.background == "yellow"
    assert _block_text(content) == "[ Ok ]"


def test_compose_disabled_uses_disabled_colors() -> None:
    button = Button(
        label="Ok",
        disabled=True,
        disabled_color="gray",
        disabled_background="black",
        focused_color="white",
        focused_background="blue",
    )
    button._input_focused = True
    content = button.compose(_ctx())
    # Disabled wins over focused — no panel chrome.
    assert isinstance(content, TextBlock)
    assert content.color == "gray"
    assert content.background == "black"


def test_activation_keys_always_bubble() -> None:
    button = Button(label="Go")
    for key in ("enter", "space"):
        assert button.handle_keyboard(_kbd(matches={key})) is False


def test_activation_keys_bubble_when_disabled() -> None:
    button = Button(label="Go", disabled=True)
    assert button.handle_keyboard(_kbd(matches={"enter"})) is False
    assert button.handle_keyboard(_kbd(matches={"space"})) is False


def test_other_keys_also_unhandled() -> None:
    button = Button(label="Go")
    assert button.handle_keyboard(_kbd(matches={"tab"})) is False
    assert button.handle_keyboard(_kbd(character="x")) is False


def test_button_is_focusable_component() -> None:
    assert is_focusable_component(Button(label="Go"))
    assert not is_focusable_component(Button(label="Go", focusable=False))


def test_get_label_text_from_string() -> None:
    assert Button(label="Hello").get_label_text() == "Hello"


def test_get_label_text_from_text_like() -> None:
    class _TextLike:
        value = "FromValue"

    assert Button(label=_TextLike()).get_label_text() == "FromValue"

    class _ContentLike:
        content = "FromContent"

    class _StringLike:
        def __str__(self) -> str:
            return "FromString"

    assert Button(label=_ContentLike()).get_label_text() == "FromContent"
    assert Button(label=_StringLike()).get_label_text() == "FromString"


def test_button_submits_composed_form_state() -> None:
    class Form(BaseGrid, direction="vertical"):
        name: Input = Field(
            default_factory=lambda: Input(placeholder="name"),
            group="name",
            height=1,
        )
        environment: Dropdown = Field(
            default_factory=lambda: Dropdown(
                items=("staging", "production"),
                searchable=False,
            ),
            group="environment",
            height=2,
        )
        submit: Button = Field(
            default_factory=lambda: Button(label="Deploy"),
            group="submit",
            height=1,
        )
        status: str = Field(default="Not deployed", height=1)

        @on_click("submit")
        def submit_form(self) -> None:
            self.status = f"{self.name.value} → {self.environment.value}"

    runtime = Runtime.offscreen(width=40, height=8)
    try:
        form = Form()
        runtime.set_root(form)
        assert "Deploy" in runtime.render().text

        assert runtime.focus("name")
        for character in "api":
            runtime.perform(Action.keyboard(character))

        assert runtime.focus("environment")
        runtime.perform(Action.keyboard("down"))
        runtime.perform(Action.keyboard("down"))
        runtime.perform(Action.keyboard("enter"))

        runtime.perform(Action.click("submit"))
        assert form.name.value == "api"
        assert form.environment.value == "production"
        assert "api → production" in runtime.render().text
    finally:
        runtime.close()
