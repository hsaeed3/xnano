"""Tests for beta ``Button`` focus states and keyboard bubbling."""

from __future__ import annotations

from typing import Any

from xnano.beta.components.button import Button
from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.core.content import Panel, TextBlock
from xnano.beta.types import Area, is_focusable_component


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
        color="green",
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
        color="green",
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


def test_button_offscreen_smoke_render() -> None:
    from xnano.beta.core.runtime import Runtime

    button = Button(label="Submit", color="cyan")
    runtime = Runtime.offscreen(width=40, height=6)
    try:
        frame = runtime.render(button)
        assert frame is not None
        output = runtime.get_output()
        assert "Submit" in output
    finally:
        runtime.close()


def test_button_focused_offscreen_smoke_render() -> None:
    from xnano.beta.core.runtime import Runtime

    button = Button(label="Save")
    button._input_focused = True
    runtime = Runtime.offscreen(width=40, height=6)
    try:
        frame = runtime.render(button)
        assert frame is not None
        output = runtime.get_output()
        assert "Save" in output
    finally:
        runtime.close()
