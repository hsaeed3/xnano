"""End-to-end tests for the dependency-free native web server."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any

import pytest

from xnano import BaseGrid, Field
from xnano.components.text import Text
from xnano.events import on_keyboard
from xnano.web.server import NativeWebServer


class Counter(BaseGrid):
    label: Text = Field(default=Text("count: 0"))
    count: int = Field(default=0, state=True)

    @on_keyboard("up")
    def _bump(self) -> None:
        self.count += 1
        self.label = Text(f"count: {self.count}")


def _row_text(frame: dict[str, Any], y: int) -> str:
    return "".join(
        str(span[0]) for span in frame["rows"].get(str(y), [])
    ).strip()


class _Client:
    def __init__(self, port: int) -> None:
        self._base = f"http://127.0.0.1:{port}"
        self._stream = urllib.request.urlopen(
            f"{self._base}/xnano/stream?cols=20&rows=3"
        )

    def read_frame(self) -> dict[str, Any]:
        buf = b""
        while b"\n\n" not in buf:
            buf += self._stream.read(1)
        data = buf.split(b"data: ", 1)[1].split(b"\n\n", 1)[0]
        return json.loads(data)

    def post_event(self, payload: dict[str, Any]) -> int:
        request = urllib.request.Request(
            f"{self._base}/xnano/event",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        return urllib.request.urlopen(request).status

    def get(self, path: str) -> tuple[int, bytes]:
        response = urllib.request.urlopen(f"{self._base}{path}")
        return response.status, response.read()


@pytest.fixture()
def server() -> Any:
    srv = NativeWebServer(
        ("127.0.0.1", 0),
        grid_factory=Counter,
        shared=True,
        state=None,
        title="test",
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    try:
        yield srv
    finally:
        srv.shutdown_all()
        srv.shutdown()
        srv.server_close()


def test_serves_shell_and_painter(server: Any) -> None:
    client = _Client(server.server_address[1])
    status, page = client.get("/")
    assert status == 200
    assert b"<canvas id='xnano'>" in page
    status, js = client.get("/xnano/painter.js")
    assert status == 200
    assert b"xnano web painter" in js


def test_first_frame_is_full_and_rendered(server: Any) -> None:
    client = _Client(server.server_address[1])
    frame = client.read_frame()
    assert frame["full"] is True
    assert _row_text(frame, 0) == "count: 0"


def test_key_event_round_trips_through_hooks(server: Any) -> None:
    client = _Client(server.server_address[1])
    client.read_frame()  # initial
    assert client.post_event({"type": "key", "binding": "up"}) == 204
    # The next non-empty frame should reflect the incremented count.
    for _ in range(20):
        frame = client.read_frame()
        if frame["rows"]:
            assert _row_text(frame, 0) == "count: 1"
            return
    raise AssertionError("no updated frame received")


def test_no_web_extra_needed() -> None:
    """The native server imports without starlette/uvicorn installed."""
    import importlib

    module = importlib.import_module("xnano.web.server")
    assert hasattr(module, "serve_native")
