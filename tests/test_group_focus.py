"""Tests for Field(group=...) — terminal-global focus & click addressing."""

from __future__ import annotations

from xnano._dispatch import dispatch_field_mouse
from xnano._types import Area
from xnano.components.text import Text
from xnano.context import Context
from xnano.core.actions import Action
from xnano.events import on_click, on_focus
from xnano.fields import Field
from xnano.grid import BaseGrid, _GridFieldHit
from xnano.terminal import Terminal


class InputRow(BaseGrid, direction="horizontal"):
    field: Text = Field(
        default_factory=lambda: Text("", input=True), group="composer"
    )


class Sidebar(BaseGrid):
    history: str = Field(default="log", group="transcript")


def _terminal_with(*grids: BaseGrid) -> Terminal:
    terminal = Terminal.offscreen()
    for grid in grids:
        terminal.attach_grid(grid)
    return terminal


def test_focus_group_resolves_nested_field() -> None:
    row = InputRow()
    terminal = _terminal_with(row)
    assert terminal.focus_group("composer") is True
    assert terminal.focused_group == "composer"


def test_focus_group_unknown_returns_false() -> None:
    row = InputRow()
    terminal = _terminal_with(row)
    assert terminal.focus_group("does-not-exist") is False
    assert terminal.focused_group is None


def test_ctx_focus_and_is_focused() -> None:
    row = InputRow()
    terminal = _terminal_with(row)
    ctx = Context(event=None, terminal=terminal, state=terminal.state)
    assert ctx.focus("composer") is True
    assert ctx.is_focused("composer") is True
    assert ctx.focused_group == "composer"


def test_group_spans_multiple_grids_first_wins() -> None:
    row = InputRow()
    sidebar = Sidebar()
    terminal = _terminal_with(row, sidebar)
    assert terminal.focus_group("composer") is True
    assert terminal.field_focus.grid is row


def test_on_focus_group_fires_on_gain_and_lost() -> None:
    events: list[str] = []

    class App(BaseGrid):
        field: Text = Field(
            default_factory=lambda: Text("", input=True), group="composer"
        )

        @on_focus(group="composer", kind="gained")
        def _gained(self) -> None:
            events.append("gained")

        @on_focus(group="composer", kind="lost")
        def _lost(self) -> None:
            events.append("lost")

    app = App()
    terminal = _terminal_with(app)
    assert terminal.focus_group("composer") is True
    assert events == ["gained"]
    terminal.blur_field()
    assert events == ["gained", "lost"]


def test_on_click_group_fires_regardless_of_grid() -> None:
    hits: list[str] = []

    class App(BaseGrid):
        field: Text = Field(
            default_factory=lambda: Text("", input=True), group="composer"
        )

        @on_click(group="composer")
        def _clicked(self) -> None:
            hits.append("clicked")

    app = App()
    terminal = _terminal_with(app)
    terminal._mouse_geometry_active = True
    paint = Area(x=0, y=0, width=10, height=1)
    terminal._field_hits.append(
        _GridFieldHit(
            grid=app,
            field_name="field",
            area=paint,
            slot_area=paint,
            parent_area=Area(x=0, y=0, width=40, height=20),
            slide_axes=[],
        )
    )
    event = Action.click("field").to_event()
    dispatch_field_mouse(
        terminal,
        Context(event=event, terminal=terminal, state=terminal.state),
    )
    assert hits == ["clicked"]
