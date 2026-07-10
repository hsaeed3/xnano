"""Unit tests for @on_get / @on_post via Web.dispatch_request."""

from __future__ import annotations

from tests.beta.grids import RequestHookGrid
from tests.helpers import close_offscreen_app, open_offscreen_app
from xnano.beta.requests import on_post
from xnano.beta.web import Web
from xnano.fields import Field
from xnano.grid import Grid


def test_dispatch_request_post_mutates_state_and_html() -> None:
    """POST /increment increments state and the re-render reflects it."""
    grid = RequestHookGrid()
    web = Web()
    web.render_html(grid)

    first = web.dispatch_request("POST", "/increment")
    second = web.dispatch_request("POST", "/increment")

    assert grid.count == 2
    assert "Count: 1" in first
    assert "Count: 2" in second
    assert "Count: 1" not in second


def test_dispatch_request_normalizes_path_without_leading_slash() -> None:
    """Paths without a leading slash still match the registered route."""
    grid = RequestHookGrid()
    web = Web()
    web.render_html(grid)

    web.dispatch_request("POST", "increment")
    assert grid.count == 1


def test_dispatch_request_wrong_method_does_not_fire_hook() -> None:
    """GET on a POST-only path is a no-op for that handler."""
    grid = RequestHookGrid()
    web = Web()
    web.render_html(grid)

    html_out = web.dispatch_request("GET", "/increment")
    assert grid.count == 0
    assert "Count: 0" in html_out


def test_dispatch_request_unknown_path_leaves_state_alone() -> None:
    """Unknown paths re-render without mutating request-hook state."""
    grid = RequestHookGrid()
    web = Web()
    web.render_html(grid)
    web.dispatch_request("POST", "/increment")
    assert grid.count == 1

    html_out = web.dispatch_request("POST", "/nope")
    assert grid.count == 1
    assert "Count: 1" in html_out


def test_dispatch_request_get_reflects_prior_post_state() -> None:
    """GET /status reads the live count after a prior POST."""
    grid = RequestHookGrid()
    web = Web()
    web.render_html(grid)

    web.dispatch_request("POST", "/increment")
    web.dispatch_request("POST", "/increment")
    html_out = web.dispatch_request("GET", "/status")

    assert grid.count == 2
    assert grid.label == "status:2"
    assert "status:2" in html_out


def test_dispatch_request_pumps_on_field_hooks() -> None:
    """Request dispatch runs the same on_field pump as click/key paths."""
    grid = RequestHookGrid()
    web = Web()
    web.render_html(grid)

    web.dispatch_request("POST", "/increment")
    assert grid.note == ""
    web.dispatch_request("POST", "/increment")
    assert grid.note == "double"


def test_request_hooks_do_not_fire_on_terminal_frame() -> None:
    """Terminal frames ignore @on_get/@on_post — only paint and TUI hooks run."""
    grid = RequestHookGrid()
    terminal = open_offscreen_app(grid, cols=40, rows=12)
    try:
        assert grid.visits == 0
        assert grid.count == 0
        assert grid.label == "Count: 0"
        web = Web()
        web.render_html(grid)
        web.dispatch_request("POST", "/increment")
        assert grid.count == 1
    finally:
        close_offscreen_app(terminal)


def test_request_hook_subclass_shadows_base_handler() -> None:
    """A more-derived @on_post for the same path replaces the base one."""

    class BaseCounter(Grid):
        label: str = Field(default="0")
        count: int = Field(default=0, state=True)

        @on_post("/bump")
        def _bump(self) -> None:
            self.count += 1
            self.label = f"base:{self.count}"

    class DerivedCounter(BaseCounter):
        @on_post("/bump")
        def _bump(self) -> None:
            self.count += 10
            self.label = f"derived:{self.count}"

    grid = DerivedCounter()
    web = Web()
    web.render_html(grid)
    html_out = web.dispatch_request("POST", "/bump")

    assert grid.count == 10
    assert grid.label == "derived:10"
    assert "derived:10" in html_out
    assert "base:" not in html_out


def test_factory_sessions_isolate_request_hook_state() -> None:
    """Each factory session mutates only its own grid via request hooks."""
    web = Web()
    web._source = RequestHookGrid
    first = web._make_session()
    second = web._make_session()

    first.render()
    first.dispatch_request("POST", "/increment")
    first.dispatch_request("POST", "/increment")

    assert first.grid.count == 2
    assert second.grid.count == 0

    second.render()
    second.dispatch_request("POST", "/increment")
    assert first.grid.count == 2
    assert second.grid.count == 1
