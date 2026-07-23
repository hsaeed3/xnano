"""Tests for Text(passthrough=...) — declarative key release, no subclass."""

from __future__ import annotations

from xnano.components.text import Text
from xnano.events import on_keyboard
from xnano.fields import Field
from xnano.grid import BaseGrid

from helpers import close_offscreen_app, open_offscreen_app, press, type_text


def test_passthrough_key_is_not_consumed_by_input() -> None:
    events: list[str] = []

    class App(BaseGrid):
        field: Text = Field(
            default_factory=lambda: Text(
                "", input=True, passthrough=("ctrl+s",)
            )
        )

        @on_keyboard("ctrl+s")
        def _quit(self) -> None:
            events.append("quit")

    grid = App()
    terminal = open_offscreen_app(grid)
    try:
        press(terminal, "ctrl+s")
        assert events == ["quit"]
        assert grid.field.value == ""
    finally:
        close_offscreen_app(terminal)


def test_non_passthrough_keys_still_edit_normally() -> None:
    class App(BaseGrid):
        field: Text = Field(
            default_factory=lambda: Text(
                "", input=True, passthrough=("ctrl+s",)
            )
        )

    grid = App()
    terminal = open_offscreen_app(grid)
    try:
        type_text(terminal, "hi")
        assert grid.field.value == "hi"
    finally:
        close_offscreen_app(terminal)


def test_up_down_passthrough_reaches_app_hooks() -> None:
    events: list[str] = []

    class App(BaseGrid):
        field: Text = Field(
            default_factory=lambda: Text(
                "", input=True, passthrough=("up", "down")
            )
        )

        @on_keyboard("up")
        def _up(self) -> None:
            events.append("up")

        @on_keyboard("down")
        def _down(self) -> None:
            events.append("down")

    grid = App()
    terminal = open_offscreen_app(grid)
    try:
        press(terminal, "up")
        press(terminal, "down")
        assert events == ["up", "down"]
    finally:
        close_offscreen_app(terminal)


def test_passthrough_intercepts_a_key_the_input_would_otherwise_consume() -> (
    None
):
    """``left`` moves the caret by default (apply_text_keyboard consumes
    it) — declaring it as passthrough releases it to app hooks instead."""
    events: list[str] = []

    class App(BaseGrid):
        field: Text = Field(
            default_factory=lambda: Text(
                "ab", input=True, cursor=2, passthrough=("left",)
            )
        )

        @on_keyboard("left")
        def _moved(self) -> None:
            events.append("moved")

    grid = App()
    terminal = open_offscreen_app(grid)
    try:
        press(terminal, "left")
        assert events == ["moved"]
        assert grid.field.cursor == 2  # untouched — input never saw the key
    finally:
        close_offscreen_app(terminal)


def test_without_passthrough_left_is_consumed_by_the_input() -> None:
    """Same key, no passthrough — the input's own caret movement wins and
    the app-level hook never fires."""
    events: list[str] = []

    class App(BaseGrid):
        field: Text = Field(
            default_factory=lambda: Text("ab", input=True, cursor=2)
        )

        @on_keyboard("left")
        def _moved(self) -> None:
            events.append("moved")

    grid = App()
    terminal = open_offscreen_app(grid)
    try:
        press(terminal, "left")
        assert events == []
        assert grid.field.cursor == 1  # the input moved its own caret
    finally:
        close_offscreen_app(terminal)
