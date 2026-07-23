"""Tests for Field(autofocus=True)."""

from __future__ import annotations

from xnano.components.text import Text
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.terminal import Terminal

from helpers import close_offscreen_app, open_offscreen_app


def test_autofocus_wins_over_declaration_order() -> None:
    class App(BaseGrid, direction="vertical"):
        first: Text = Field(default_factory=lambda: Text("", input=True))
        second: Text = Field(
            default_factory=lambda: Text("", input=True), autofocus=True
        )

    grid = App()
    terminal = open_offscreen_app(grid)
    try:
        assert terminal.field_focus.field_name == "second"
        assert grid.second._input_focused is True
        assert grid.first._input_focused is False
    finally:
        close_offscreen_app(terminal)


def test_no_autofocus_falls_back_to_first_field() -> None:
    class App(BaseGrid, direction="vertical"):
        first: Text = Field(default_factory=lambda: Text("", input=True))
        second: Text = Field(default_factory=lambda: Text("", input=True))

    grid = App()
    terminal = open_offscreen_app(grid)
    try:
        assert terminal.field_focus.field_name == "first"
    finally:
        close_offscreen_app(terminal)


def test_autofocus_does_not_override_explicit_focus() -> None:
    class App(BaseGrid, direction="vertical"):
        first: Text = Field(default_factory=lambda: Text("", input=True))
        second: Text = Field(
            default_factory=lambda: Text("", input=True), autofocus=True
        )

    grid = App()
    terminal = Terminal.offscreen()
    terminal.attach_grid(grid)
    terminal.focus_field(grid, "first")
    terminal._render_frame(grid)
    try:
        assert terminal.field_focus.field_name == "first"
    finally:
        close_offscreen_app(terminal)
