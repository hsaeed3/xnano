"""Tests for @on_get_request / @on_post_request via the host-agnostic
request dispatcher (xnano.web.requests.dispatch_request)."""

from __future__ import annotations

from tests.web.grids import RequestHookGrid
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.web.requests import (
    collect_request_routes,
    dispatch_request,
    has_request_hooks,
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
)


def test_post_hook_mutates_state() -> None:
    grid = RequestHookGrid()
    assert dispatch_request(grid, "POST", "/increment") is True
    dispatch_request(grid, "POST", "/increment")
    assert grid.count == 2
    assert grid.label == "Count: 2"


def test_path_without_leading_slash_matches() -> None:
    grid = RequestHookGrid()
    assert dispatch_request(grid, "POST", "increment") is True
    assert grid.count == 1


def test_wrong_method_is_noop() -> None:
    grid = RequestHookGrid()
    assert dispatch_request(grid, "GET", "/increment") is False
    assert grid.count == 0


def test_unknown_path_is_noop() -> None:
    grid = RequestHookGrid()
    assert dispatch_request(grid, "POST", "/nope") is False
    assert grid.count == 0


def test_get_reflects_prior_post_state() -> None:
    grid = RequestHookGrid()
    dispatch_request(grid, "POST", "/increment")
    dispatch_request(grid, "POST", "/increment")
    dispatch_request(grid, "GET", "/status")
    assert grid.count == 2
    assert grid.label == "status:2"


def test_has_request_hooks_detects_routes() -> None:
    assert has_request_hooks(RequestHookGrid) is True
    assert has_request_hooks(RequestHookGrid()) is True

    class Plain(BaseGrid):
        label: str = Field(default="x")

    assert has_request_hooks(Plain) is False


def test_collect_routes_lists_method_path_pairs() -> None:
    routes = {
        (entry["method"], entry["path"])
        for entry in collect_request_routes(RequestHookGrid)
    }
    assert ("POST", "/increment") in routes
    assert ("GET", "/status") in routes


def test_all_http_method_hooks_are_collected() -> None:
    decorators = {
        "GET": on_get_request,
        "HEAD": on_head_request,
        "POST": on_post_request,
        "PUT": on_put_request,
        "DELETE": on_delete_request,
        "CONNECT": on_connect_request,
        "OPTIONS": on_options_request,
        "TRACE": on_trace_request,
        "PATCH": on_patch_request,
        "QUERY": on_query_request,
    }
    namespace = {}
    for method, decorator in decorators.items():

        def handler(self) -> None:
            pass

        handler.__name__ = method.lower()
        namespace[handler.__name__] = decorator(f"/{method.lower()}")(handler)

    grid_class = type("AllRequestHooks", (), namespace)
    routes = {
        (entry["method"], entry["path"])
        for entry in collect_request_routes(grid_class)
    }
    assert routes == {(method, f"/{method.lower()}") for method in decorators}


def test_subclass_route_shadows_base() -> None:
    class BaseCounter(BaseGrid):
        label: str = Field(default="0")
        count: int = Field(default=0, state=True)

        @on_post_request("/bump")
        def _bump(self) -> None:
            self.count += 1
            self.label = f"base:{self.count}"

    class DerivedCounter(BaseCounter):
        @on_post_request("/bump")
        def _bump(self) -> None:
            self.count += 10
            self.label = f"derived:{self.count}"

    grid = DerivedCounter()
    dispatch_request(grid, "POST", "/bump")
    assert grid.count == 10
    assert grid.label == "derived:10"


def test_isolated_grids_keep_separate_state() -> None:
    first = RequestHookGrid()
    second = RequestHookGrid()
    dispatch_request(first, "POST", "/increment")
    dispatch_request(first, "POST", "/increment")
    assert first.count == 2
    assert second.count == 0
