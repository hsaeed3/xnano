"""Tests for BaseGrid.grid_post_init lifecycle hook."""

from __future__ import annotations

from xnano.context import Context
from xnano.fields import Field
from xnano.grid import BaseGrid

from helpers import close_offscreen_app, open_offscreen_app


def test_grid_post_init_fires_zero_arg_form() -> None:
    calls: list[str] = []

    class G(BaseGrid):
        a: str = Field(default="hi")

        def grid_post_init(self) -> None:
            calls.append("called")

    grid = G()
    terminal = open_offscreen_app(grid)
    try:
        assert calls == ["called"]
    finally:
        close_offscreen_app(terminal)


def test_grid_post_init_receives_ctx_and_state() -> None:
    seen: list[object] = []

    class G(BaseGrid):
        a: str = Field(default="hi")

        def grid_post_init(  # ty: ignore[invalid-method-override]
            self, ctx: Context
        ) -> None:
            seen.append(ctx.state)
            self.a = "post-init-ran"

    grid = G()
    state = {"workspace": "demo"}
    terminal = open_offscreen_app(grid, state=state)
    try:
        assert seen == [state]
        assert grid.a == "post-init-ran"
    finally:
        close_offscreen_app(terminal)


def test_grid_post_init_fires_exactly_once_per_instance() -> None:
    calls: list[str] = []

    class G(BaseGrid):
        a: str = Field(default="hi")

        def grid_post_init(self) -> None:
            calls.append("called")

    grid = G()
    terminal = open_offscreen_app(grid)
    try:
        # A second frame paints the same instance again.
        terminal._render_frame(grid)
        assert calls == ["called"]
    finally:
        close_offscreen_app(terminal)


def test_grid_post_init_default_is_noop() -> None:
    class G(BaseGrid):
        a: str = Field(default="hi")

    grid = G()
    terminal = open_offscreen_app(grid)
    try:
        assert grid.a == "hi"
    finally:
        close_offscreen_app(terminal)
