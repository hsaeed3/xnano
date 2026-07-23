"""tests.beta.test_requests"""

from __future__ import annotations

import http.client

import pytest

from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid
from xnano.beta.requests import (
    Request,
    Response,
    dispatch_request,
    on_connect_request,
    on_delete_request,
    on_get_request,
    on_head_request,
    on_options_request,
    on_patch_request,
    on_post_request,
    on_put_request,
    on_query_request,
    on_trace_request,
    request,
)
from xnano.beta.server.requests import start_request_server


def test_request_parsing_and_json() -> None:
    req = Request.from_parts(
        "POST",
        "/items",
        query_string="a=1&a=2&b=x",
        headers={"Content-Type": "application/json"},
        body=b'{"ok": true}',
    )
    assert req.method == "POST"
    assert req.path == "/items"
    assert req.query["a"] == ("1", "2")
    assert req.json() == {"ok": True}
    assert req.headers["content-type"] == "application/json"


def test_request_body_limit() -> None:
    try:
        Request.from_parts("POST", "/", body=b"x" * 10, max_body=5)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_response_json() -> None:
    response = Response.json({"ok": True}, status=201)
    assert response.status == 201
    assert b"ok" in response.as_bytes()
    assert response.headers["content-type"].startswith("application/json")


def test_dispatch_request_with_runtime_context() -> None:
    class Items(BaseGrid):
        count: int = Field(default=0, state=True)

        @on_post_request("/items")
        def create(self, ctx) -> Response:
            self.count += 1
            assert ctx.request is not None
            return Response.json({"count": self.count}, status=201)

        @on_get_request("/items")
        def list_items(self) -> None:
            pass

    grid = Items()
    req = Request.from_parts("POST", "/items", body=b"{}")
    result = dispatch_request(
        grid,
        "POST",
        "/items",
        request_obj=req,
        runtime=grid,
    )
    assert isinstance(result, Response)
    assert result.status == 201
    assert grid.count == 1


def test_request_decorator_factory() -> None:
    decorator = request("PATCH", "/thing")
    assert callable(decorator)


@pytest.mark.parametrize(
    ("method", "decorator"),
    (
        ("GET", on_get_request),
        ("HEAD", on_head_request),
        ("POST", on_post_request),
        ("PUT", on_put_request),
        ("DELETE", on_delete_request),
        ("CONNECT", on_connect_request),
        ("OPTIONS", on_options_request),
        ("TRACE", on_trace_request),
        ("PATCH", on_patch_request),
        ("QUERY", on_query_request),
    ),
)
def test_every_request_hook_dispatches_with_context(
    method: str,
    decorator,
) -> None:
    def handle(self, ctx) -> Response:
        self.called = method
        assert ctx.request.method == method
        return Response(body=method)

    class App(BaseGrid):
        called: str = Field(default="", state=True)

    setattr(App, "handle", decorator("/route")(handle))
    app = App()
    request_obj = Request.from_parts(method, "/route")
    response = dispatch_request(
        app,
        method,
        "/route",
        request_obj=request_obj,
        runtime=app,
    )
    assert isinstance(response, Response)
    assert response.as_bytes() == method.encode()
    assert app.called == method


def test_request_server_preserves_http_body_query_status_and_404() -> None:
    class App(BaseGrid):
        @on_post_request("/submit")
        def submit(self, ctx) -> Response:
            assert ctx.request.query["mode"] == ("test",)
            assert ctx.request.json() == {"value": 3}
            return Response.json({"accepted": True}, status=202)

    server = start_request_server(App, host="127.0.0.1", port=0)
    connection = http.client.HTTPConnection(
        "127.0.0.1",
        server.server_address[1],
        timeout=2,
    )
    try:
        connection.request(
            "POST",
            "/submit?mode=test",
            body=b'{"value": 3}',
            headers={"content-type": "application/json"},
        )
        response = connection.getresponse()
        assert response.status == 202
        assert response.getheader("content-type", "").startswith(
            "application/json"
        )
        assert response.read() == b'{"accepted": true}'

        connection.request("GET", "/missing")
        response = connection.getresponse()
        assert response.status == 404
        assert response.read() == b"Not Found"
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
