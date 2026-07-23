"""Tests for Field(scroll=...) — windowed container fields."""

from __future__ import annotations

from xnano_core.core import CoreSession

from xnano._dispatch import dispatch_field_mouse
from xnano._types import Area
from xnano.context import Context
from xnano.core.controllers.tui import (
    TerminalController,
    compute_scroll_window,
)
from xnano.events import Event, MouseEventData
from xnano.fields import Field
from xnano.grid import BaseGrid, _GridFieldHit

# ---------------------------------------------------------------------------
# compute_scroll_window — pure function
# ---------------------------------------------------------------------------


def test_window_anchors_at_bottom_by_default() -> None:
    assert compute_scroll_window([1, 1, 1, 1, 1], 0, 3, 0) == (2, 5)


def test_window_shifts_with_offset() -> None:
    assert compute_scroll_window([1, 1, 1, 1, 1], 0, 3, 1) == (1, 4)


def test_window_always_includes_at_least_one_item() -> None:
    assert compute_scroll_window([10, 10], 0, 1, 0) == (1, 2)


def test_window_empty_input() -> None:
    assert compute_scroll_window([], 0, 5, 0) == (0, 0)


def test_window_respects_gap() -> None:
    # 3 items of length 1, gap 1: item+gap+item+gap+item = 5 > available=3
    start, end = compute_scroll_window([1, 1, 1], 1, 3, 0)
    assert end == 3
    assert start >= 1


# ---------------------------------------------------------------------------
# Rendered windowing
# ---------------------------------------------------------------------------


def _render(grid: BaseGrid, *, width: int = 20, height: int = 4) -> str:
    core = CoreSession.offscreen(width=width, height=height)
    session = TerminalController(
        core, terminal_width=width, terminal_height=height, is_offscreen=True
    )
    grid._grid_build_frame(Area(x=0, y=0, width=width, height=height), session)
    session.commit_requests()
    return session.get_core_session_output_text()


def test_scroll_field_shows_only_the_tail_by_default() -> None:
    class App(BaseGrid, direction="vertical"):
        items: list = Field(
            default_factory=list, direction="vertical", scroll=True
        )

    grid = App()
    grid.items = [f"line{i}" for i in range(10)]
    output = _render(grid, height=4)
    assert "line9" in output
    assert "line0" not in output


def test_scroll_offset_shifts_the_window() -> None:
    class App(BaseGrid, direction="vertical"):
        items: list = Field(
            default_factory=list, direction="vertical", scroll=True
        )

    grid = App()
    grid.items = [f"line{i}" for i in range(10)]
    grid._grid_set_field_scroll_offset("items", 9)
    output = _render(grid, height=4)
    assert "line0" in output
    assert "line9" not in output


def test_content_that_fits_ignores_offset() -> None:
    class App(BaseGrid, direction="vertical"):
        items: list = Field(
            default_factory=list, direction="vertical", scroll=True
        )

    grid = App()
    grid.items = ["a", "b"]
    output = _render(grid, height=10)
    assert "a" in output
    assert "b" in output


# ---------------------------------------------------------------------------
# ScrollHandle / ctx.scroll(group)
# ---------------------------------------------------------------------------


def test_ctx_scroll_resolves_by_group() -> None:
    class App(BaseGrid, direction="vertical"):
        items: list = Field(
            default_factory=list,
            direction="vertical",
            scroll=True,
            group="transcript",
        )

    grid = App()
    terminal = _attach(grid)
    ctx = Context(event=None, terminal=terminal, state=terminal.state)
    handle = ctx.scroll("transcript")
    assert handle is not None
    assert handle.offset == 0
    handle.offset = 5
    assert grid._grid_field_scroll_offset("items") == 5


def test_ctx_scroll_unknown_group_returns_none() -> None:
    class App(BaseGrid, direction="vertical"):
        items: list = Field(default_factory=list, group="transcript")

    grid = App()
    terminal = _attach(grid)
    ctx = Context(event=None, terminal=terminal, state=terminal.state)
    assert ctx.scroll("does-not-exist") is None


def test_scroll_handle_to_bottom_and_scroll_by() -> None:
    class App(BaseGrid, direction="vertical"):
        items: list = Field(
            default_factory=list, scroll=True, group="transcript"
        )

    grid = App()
    terminal = _attach(grid)
    ctx = Context(event=None, terminal=terminal, state=terminal.state)
    handle = ctx.scroll("transcript")
    assert handle is not None
    handle.scroll_by(3)
    assert handle.offset == 3
    handle.to_bottom()
    assert handle.offset == 0


def test_scroll_handle_follow_persists_across_lookups() -> None:
    class App(BaseGrid, direction="vertical"):
        items: list = Field(
            default_factory=list, scroll=True, group="transcript"
        )

    grid = App()
    terminal = _attach(grid)
    ctx = Context(event=None, terminal=terminal, state=terminal.state)
    first = ctx.scroll("transcript")
    assert first is not None
    first.follow = True
    second = ctx.scroll("transcript")
    assert second is not None
    assert second.follow is True


# ---------------------------------------------------------------------------
# Mouse wheel dispatch
# ---------------------------------------------------------------------------


def _attach(grid: BaseGrid):
    from xnano.terminal import Terminal

    terminal = Terminal.offscreen()
    terminal.attach_grid(grid)
    return terminal


def test_wheel_up_increases_offset_on_scrollable_field() -> None:
    class App(BaseGrid, direction="vertical"):
        items: list = Field(
            default_factory=list, direction="vertical", scroll=True
        )

    grid = App()
    terminal = _attach(grid)
    terminal._mouse_geometry_active = True
    paint = Area(x=0, y=0, width=20, height=4)
    terminal._field_hits.append(
        _GridFieldHit(
            grid=grid,
            field_name="items",
            area=paint,
            slot_area=paint,
            parent_area=Area(x=0, y=0, width=20, height=4),
            slide_axes=[],
        )
    )
    event = Event.from_data(
        MouseEventData(kind="scroll_up", x=1, y=1, button="unknown")
    )
    dispatch_field_mouse(
        terminal, Context(event=event, terminal=terminal, state=None)
    )
    assert grid._grid_field_scroll_offset("items") == 1

    down_event = Event.from_data(
        MouseEventData(kind="scroll_down", x=1, y=1, button="unknown")
    )
    dispatch_field_mouse(
        terminal, Context(event=down_event, terminal=terminal, state=None)
    )
    assert grid._grid_field_scroll_offset("items") == 0


def test_wheel_ignores_non_scroll_fields() -> None:
    class App(BaseGrid, direction="vertical"):
        body: str = Field(default="hi")

    grid = App()
    terminal = _attach(grid)
    terminal._mouse_geometry_active = True
    paint = Area(x=0, y=0, width=20, height=4)
    terminal._field_hits.append(
        _GridFieldHit(
            grid=grid,
            field_name="body",
            area=paint,
            slot_area=paint,
            parent_area=Area(x=0, y=0, width=20, height=4),
            slide_axes=[],
        )
    )
    event = Event.from_data(
        MouseEventData(kind="scroll_up", x=1, y=1, button="unknown")
    )
    # Should not raise even though "body" isn't scrollable.
    dispatch_field_mouse(
        terminal, Context(event=event, terminal=terminal, state=None)
    )
