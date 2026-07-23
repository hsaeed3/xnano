"""tests.beta.test_web"""

from __future__ import annotations

import http.client
import json
import threading


def test_browser_events_use_public_beta_events() -> None:
    from xnano.beta.server.native import _browser_event

    keyboard = _browser_event(
        {
            "type": "keyboard",
            "binding": "ctrl+s",
            "kind": "press",
            "character": None,
        }
    )
    mouse = _browser_event(
        {
            "type": "mouse",
            "kind": "press",
            "button": "left",
            "x": 3,
            "y": 2,
        }
    )

    assert keyboard.keyboard_event is not None
    assert keyboard.keyboard_event.matches("ctrl+s")
    assert mouse.mouse_position == (3, 2)


from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid
from xnano.beta.web import Web, grid_factory


class _Counter(BaseGrid):
    label: str = Field(default="ok")


def test_web_construction() -> None:
    web = Web(title="demo", width=60, height=20)
    assert web.title == "demo"
    assert web.width == 60
    assert web.surface == "web"
    web.close()


def test_grid_factory_shared_instance() -> None:
    instance = _Counter()
    factory, shared, grid_class = grid_factory(instance)
    assert shared is True
    assert factory() is instance


def test_grid_factory_class() -> None:
    factory, shared, grid_class = grid_factory(_Counter)
    assert shared is False
    assert grid_class is _Counter
    first = factory()
    second = factory()
    assert isinstance(first, _Counter)
    assert first is not second


def test_native_web_http_event_changes_subsequent_frame() -> None:
    from xnano.beta import hooks
    from xnano.beta.server.native import NativeWebServer

    class App(BaseGrid):
        label: str = Field(default="initial")

        @hooks.on_keyboard("x")
        def change(self) -> None:
            self.label = "changed by browser"

    server = NativeWebServer(
        ("127.0.0.1", 0),
        App,
        width=30,
        height=6,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection(
        "127.0.0.1",
        server.server_address[1],
        timeout=2,
    )
    try:
        connection.request("GET", "/xnano/frame")
        response = connection.getresponse()
        initial = json.loads(response.read())
        assert response.status == 200
        assert "initial" in initial["text"]

        payload = json.dumps(
            {
                "type": "keyboard",
                "binding": "x",
                "kind": "press",
                "character": "x",
            }
        )
        connection.request(
            "POST",
            "/xnano/event",
            body=payload,
            headers={"content-type": "application/json"},
        )
        response = connection.getresponse()
        response.read()
        assert response.status == 204

        connection.request("GET", "/xnano/frame")
        response = connection.getresponse()
        changed = json.loads(response.read())
        assert response.status == 200
        assert changed["revision"] > initial["revision"]
        assert "changed by browser" in changed["text"]
        assert "initial" not in changed["text"]
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
