"""Tests for grid field slide and lazy mouse geometry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from xnano.beta import Context, on_mouse, Field, Grid, Terminal
from xnano.beta.events import Event
from xnano.beta.hooks import _EventHooksRegistry
from xnano.beta.grid import _GridSlideCapture, _grid_slide_paint_area
from xnano.beta.terminal import _ACTIVE_TERMINAL
from xnano.beta.types import Area


class SlideGrid(Grid):
    body: str = Field(default="hello", slide=["x", "y"])


class ClickGrid(Grid):
    body: str = Field(default="hello")

    @on_mouse(field="body")
    def on_body(self, ctx: Context) -> None:
        self.body = "clicked"


class DragHookGrid(Grid):
    body: str = Field(default="hello", slide=["x"])

    @on_mouse(field="body", kind="drag")
    def on_drag(self, ctx: Context) -> None:
        self.body = f"x={self.field_position('body')[0]}"


def test_slide_paint_area_offsets_within_parent() -> None:
    parent = Area(x=0, y=0, width=20, height=10)
    slot = Area(x=0, y=0, width=8, height=4)
    paint = _grid_slide_paint_area(parent, slot, ["x", "y"], (5, 3))
    assert paint == Area(x=5, y=3, width=8, height=4)


def test_slide_paint_area_clamps_to_parent() -> None:
    parent = Area(x=0, y=0, width=10, height=10)
    slot = Area(x=0, y=0, width=4, height=4)
    paint = _grid_slide_paint_area(parent, slot, ["x", "y"], (99, 99))
    assert paint == Area(x=6, y=6, width=4, height=4)


def test_on_mouse_defaults_to_left_press() -> None:
    @on_mouse
    def handler(ctx: Context) -> None:
        pass

    buttons, kind = getattr(handler, _EventHooksRegistry.ON_MOUSE_FILTER_ATTR)
    assert buttons == ("left",)
    assert kind == "press"


def test_field_hits_skipped_without_mouse_geometry() -> None:
    grid = ClickGrid()
    terminal = Terminal(mouse_events=False)
    terminal._mouse_geometry_active = False
    terminal._field_hits.clear()

    token = _ACTIVE_TERMINAL.set(terminal)
    try:
        grid._grid_register_field_hit(
            "body",
            Area(x=0, y=0, width=5, height=3),
            slot_area=Area(x=0, y=0, width=5, height=3),
            parent_area=Area(x=0, y=0, width=10, height=10),
        )
    finally:
        _ACTIVE_TERMINAL.reset(token)
    assert terminal._field_hits == []


@dataclass(frozen=True, slots=True)
class _Mouse:
    kind: str
    x: int
    y: int
    button: str = "left"


@dataclass(frozen=True, slots=True)
class _MouseEvent:
    _mouse: _Mouse

    def is_mouse_event(self) -> bool:
        return True

    @property
    def mouse_event(self) -> _Mouse:
        return self._mouse


def test_slide_capture_updates_position_on_drag() -> None:
    grid = SlideGrid()
    grid._grid_last_parent_area = Area(x=0, y=0, width=20, height=10)
    grid._grid_last_slot_areas = {"body": Area(x=0, y=0, width=6, height=3)}

    terminal = Terminal(mouse_events=True)
    terminal._mouse_geometry_active = True
    terminal._slide_capture = _GridSlideCapture(
        grid=grid,
        field_name="body",
        parent_area=Area(x=0, y=0, width=20, height=10),
        slot_area=Area(x=0, y=0, width=6, height=3),
        grab_x=1,
        grab_y=1,
        slide_axes=["x", "y"],
    )

    terminal._dispatch_field_mouse(
        Context(
            event=cast(
                Event | None,
                _MouseEvent(_Mouse(kind="drag", x=6, y=4)),
            ),
            terminal=terminal,
            state=None,
        )
    )
    assert grid.field_position("body") == (5, 3)


def test_set_field_slide_and_position() -> None:
    grid = ClickGrid()
    grid._grid_last_parent_area = Area(x=0, y=0, width=20, height=10)
    grid._grid_last_slot_areas = {"body": Area(x=0, y=0, width=6, height=3)}
    grid.grid_set_field("body", slide=["x"], position=(4, 0))
    assert grid._grid_field_info("body").slide == ["x"]
    assert grid.field_position("body") == (4, 0)


def test_drag_hook_fires_while_sliding() -> None:
    grid = DragHookGrid()
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
    terminal._dispatch_field_mouse(
        Context(
            event=cast(
                Event | None,
                _MouseEvent(_Mouse(kind="drag", x=7, y=0)),
            ),
            terminal=terminal,
            state=None,
        )
    )
    assert grid.body == "x=7"
