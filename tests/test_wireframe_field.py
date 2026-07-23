"""Tests for Field(wireframe=...) — per-field debug cell-grid overlay."""

from __future__ import annotations

from xnano._types import Area
from xnano.core.controllers.tui import TerminalController
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.terminal import Terminal
from xnano_core.core import CoreSession


def _render(grid: BaseGrid, *, width: int = 10, height: int = 5) -> str:
    core = CoreSession.offscreen(width=width, height=height)
    session = TerminalController(
        core, terminal_width=width, terminal_height=height, is_offscreen=True
    )
    grid._grid_build_frame(Area(x=0, y=0, width=width, height=height), session)
    session.commit_requests()
    return session.get_core_session_output_text()


def test_wireframe_field_paints_dot_overlay() -> None:
    class App(BaseGrid, direction="vertical"):
        body: str = Field(default="hi", wireframe=True, height=3)

    grid = App()
    output = _render(grid)
    assert "·" in output


def test_field_without_wireframe_has_no_dots() -> None:
    class App(BaseGrid, direction="vertical"):
        body: str = Field(default="hi", height=3)

    grid = App()
    output = _render(grid)
    assert "·" not in output


def test_wireframe_can_be_toggled_live() -> None:
    class App(BaseGrid, direction="vertical"):
        body: str = Field(default="hi", height=3)

    grid = App()
    assert "·" not in _render(grid)
    grid.grid_update_field("body", wireframe=True)
    assert "·" in _render(grid)
    grid.grid_update_field("body", wireframe=False)
    assert "·" not in _render(grid)


def test_terminal_no_longer_accepts_debug_wireframe() -> None:
    import inspect

    params = inspect.signature(Terminal.__init__).parameters
    assert "debug_wireframe" not in params
    offscreen_params = inspect.signature(Terminal.offscreen).parameters
    assert "debug_wireframe" not in offscreen_params
