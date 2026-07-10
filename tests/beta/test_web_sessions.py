"""Web session model: shared grid instance vs per-visitor factory."""

from __future__ import annotations

import types

from tests.beta.grids import InteractiveGrid
from xnano.beta.web import Web


def test_factory_source_creates_isolated_sessions() -> None:
    """A callable source gives each session its own grid instance."""
    web = Web()
    web._source = InteractiveGrid
    first = web._make_session()
    second = web._make_session()
    assert first.grid is not second.grid
    first.render()
    first.dispatch_keyboard("up")
    assert first.grid.count == 10
    assert second.grid.count == 0


def test_grid_instance_source_shares_mutations() -> None:
    """A Grid instance source is one shared grid across sessions."""
    grid = InteractiveGrid()
    web = Web()
    web._source = grid
    first = web._make_session()
    second = web._make_session()
    assert first.grid is grid
    assert second.grid is grid
    first.render()
    first.dispatch_keyboard("up")
    assert grid.count == 10
    assert second.grid.count == 10


def test_session_for_request_sets_cookie_in_factory_mode() -> None:
    """Factory mode issues a session cookie and reuses it afterwards."""
    web = Web()
    web._source = InteractiveGrid
    request = types.SimpleNamespace(cookies={})
    session, cookie = web._session_for_request(request)
    assert cookie is not None
    request_two = types.SimpleNamespace(cookies={"xnano-session": cookie})
    session_two, cookie_two = web._session_for_request(request_two)
    assert session_two is session
    assert cookie_two is None
