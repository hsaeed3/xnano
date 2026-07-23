"""Cross-host request hooks: the background stdlib request server that
exposes @on_*_request routes alongside a terminal app."""

from __future__ import annotations

import urllib.error
import urllib.request

from xnano import BaseGrid, Field
from xnano.hooks import on_get_request, on_post_request
from xnano.web.request_server import start_request_server


class Api(BaseGrid):
    count: int = Field(default=0, state=True)
    label: str = Field(default="idle")

    @on_post_request("/increment")
    def _inc(self) -> None:
        self.count += 1
        self.label = f"count={self.count}"

    @on_get_request("/status")
    def _status(self) -> None:
        self.label = f"status:{self.count}"


class Plain(BaseGrid):
    text: str = Field(default="x")


def _post(url: str) -> int:
    request = urllib.request.Request(url, method="POST", data=b"")
    return urllib.request.urlopen(request).status


def test_no_hooks_starts_no_server() -> None:
    assert start_request_server(Plain()) is None


def test_post_route_mutates_grid_over_http() -> None:
    grid = Api()
    server = start_request_server(grid, host="127.0.0.1", port=0)
    assert server is not None
    port = server.server_address[1]
    try:
        assert _post(f"http://127.0.0.1:{port}/increment") == 200
        assert _post(f"http://127.0.0.1:{port}/increment") == 200
        assert grid.count == 2
        assert grid.label == "count=2"
    finally:
        server.shutdown()


def test_get_route_reads_state_over_http() -> None:
    grid = Api()
    grid.count = 5
    server = start_request_server(grid, host="127.0.0.1", port=0)
    assert server is not None
    port = server.server_address[1]
    try:
        assert urllib.request.urlopen(
            f"http://127.0.0.1:{port}/status"
        ).status == 200
        assert grid.label == "status:5"
    finally:
        server.shutdown()


def test_unknown_path_is_404() -> None:
    grid = Api()
    server = start_request_server(grid, host="127.0.0.1", port=0)
    assert server is not None
    port = server.server_address[1]
    try:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nope")
        except urllib.error.HTTPError as error:
            assert error.code == 404
        else:
            raise AssertionError("expected 404")
    finally:
        server.shutdown()


def test_terminal_run_accepts_host_port() -> None:
    """host/port are accepted by Terminal.run's signature (no request
    hooks → server never starts, params ignored)."""
    import inspect

    from xnano.terminal.terminal import Terminal

    params = inspect.signature(Terminal.run).parameters
    assert "host" in params
    assert "port" in params
