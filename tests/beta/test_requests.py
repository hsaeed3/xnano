"""tests.beta.test_requests"""

from __future__ import annotations

from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid
from xnano.beta.requests import (
    Request,
    Response,
    dispatch_request,
    on_get_request,
    on_post_request,
    request,
)


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
