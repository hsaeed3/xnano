"""xnano.web.requests

---

HTTP request hooks for creating reactive grids within web applications.

This module provides ``@on_get_request`` and ``@on_post_request`` decorators which can be
annotated onto methods of a ``BaseGrid`` subclass to handle HTTP requests when
the grid is served by ``Web``. Under a terminal session the decorators are
harmless no-ops for dispatch — the methods remain on the class and never
fire.

Example:

    ```python
    from xnano.grid import BaseGrid
    from xnano.fields import Field
    from xnano.web.requests import on_get_request, on_post_request
    from xnano.web import Web

    class Counter(BaseGrid):
        label: str = Field(default="Count: 0")
        count: int = Field(default=0, state=True)

        @on_post_request("/increment")
        def increment(self) -> None:
            self.count += 1
            self.label = f"Count: {self.count}"

        @on_get_request("/reset")
        def reset(self) -> None:
            self.count = 0
            self.label = "Count: 0"

    Web(title="counter").run(Counter)
    ```

    ``Web`` registers each path as a Starlette route. Responses are full
    HTML pages for ordinary browser navigation and ``#xnano-app`` fragments
    for htmx requests (``HX-Request``), so buttons can wire themselves with
    ``hx-post="/increment" hx-target="#xnano-app" hx-swap="innerHTML"``.
"""

from __future__ import annotations

from typing import Any, Callable, overload

from xnano._function_hooks import (
    EventHookFunction,
    HttpMethod,
    _OnRequestHookEntry,
    _RequestHooksRegistry,
)


def _normalize_request_path(path: str) -> str:
    """Normalize a request path to a leading-slash form.

    Args:
        path: The raw path string (may be empty or omit the leading slash).

    Returns:
        A path beginning with ``/``. Empty input becomes ``"/"``.
    """
    cleaned = path.strip()
    if not cleaned:
        return "/"
    if not cleaned.startswith("/"):
        return f"/{cleaned}"
    return cleaned


def _decorate_request_hook(
    fn: EventHookFunction,
    *,
    method: HttpMethod,
    path: str,
) -> EventHookFunction:
    """Mark ``fn`` as an HTTP request hook for ``method`` at ``path``.

    Unlike terminal event hooks, request hooks are never auto-registered
    with an active terminal — they only participate when ``Web`` scans
    the grid class for routes.

    Args:
        fn: The hook function to decorate.
        method: The HTTP method this hook handles.
        path: The URL path (normalized to a leading slash).

    Returns:
        The decorated hook function.
    """
    normalized = _normalize_request_path(path)
    if method == "GET":
        setattr(fn, _RequestHooksRegistry.ON_GET_HOOK_ATTR, True)
    else:
        setattr(fn, _RequestHooksRegistry.ON_POST_HOOK_ATTR, True)
    setattr(fn, _RequestHooksRegistry.ON_REQUEST_PATH_ATTR, normalized)
    return fn


@overload
def on_get_request(
    path: str,
    /,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_get_request(
    handler: EventHookFunction,
    /,
    *,
    path: str = "/",
) -> EventHookFunction: ...
def on_get_request(
    handler_or_path: "EventHookFunction | str | None" = None,
    /,
    *,
    path: str | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a GET request hook for a grid method.

    When the grid is hosted by ``Web``, the path is registered as a
    Starlette ``GET`` route. The handler runs against the live session
    grid, then the page (or htmx fragment) is re-rendered.

    Under ``Terminal`` the decorator only marks the method — nothing is
    dispatched and no error is raised.

    Args:
        handler_or_path: The path string (decorator factory form) or the
            handler when used as ``@on_get_request`` / ``@on_get_request(path=...)``.
        path: Explicit path when decorating a handler directly.

    Returns:
        The decorated hook function, or a decorator awaiting a function.

    Example:
        @on_get_request("/status")
        def show_status(self) -> None:
            self.label = "ok"

        @on_get_request
        def index(self) -> None:
            ...  # path defaults to "/"
    """
    if callable(handler_or_path):
        resolved = path if path is not None else "/"
        return _decorate_request_hook(
            handler_or_path, method="GET", path=resolved
        )

    resolved_path = (
        handler_or_path
        if isinstance(handler_or_path, str)
        else (path if path is not None else "/")
    )

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        return _decorate_request_hook(fn, method="GET", path=resolved_path)

    return decorator


@overload
def on_post_request(
    path: str,
    /,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_post_request(
    handler: EventHookFunction,
    /,
    *,
    path: str = "/",
) -> EventHookFunction: ...
def on_post_request(
    handler_or_path: "EventHookFunction | str | None" = None,
    /,
    *,
    path: str | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a POST request hook for a grid method.

    When the grid is hosted by ``Web``, the path is registered as a
    Starlette ``POST`` route and is the natural target for htmx
    ``hx-post`` attributes that swap ``#xnano-app``.

    Under ``Terminal`` the decorator only marks the method — nothing is
    dispatched and no error is raised.

    Args:
        handler_or_path: The path string (decorator factory form) or the
            handler when used as ``@on_post_request`` / ``@on_post_request(path=...)``.
        path: Explicit path when decorating a handler directly.

    Returns:
        The decorated hook function, or a decorator awaiting a function.

    Example:
        @on_post_request("/increment")
        def increment(self) -> None:
            self.count += 1
    """
    if callable(handler_or_path):
        resolved = path if path is not None else "/"
        return _decorate_request_hook(
            handler_or_path, method="POST", path=resolved
        )

    resolved_path = (
        handler_or_path
        if isinstance(handler_or_path, str)
        else (path if path is not None else "/")
    )

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        return _decorate_request_hook(fn, method="POST", path=resolved_path)

    return decorator


def has_request_hooks(grid_or_class: Any) -> bool:
    """Return whether a grid (instance or class) declares any request hook."""
    grid_class = (
        grid_or_class
        if isinstance(grid_or_class, type)
        else type(grid_or_class)
    )
    return bool(
        _RequestHooksRegistry.from_component_class(grid_class).all_hooks()
    )


def collect_request_routes(grid_class: type) -> list[_OnRequestHookEntry]:
    """Collect ``@on_*_request`` route entries declared on a grid class."""
    return _RequestHooksRegistry.from_component_class(grid_class).all_hooks()


def dispatch_request(grid: Any, method: str, path: str) -> bool:
    """Invoke matching request hooks on a live ``grid``; return matched.

    Host-agnostic: the handler mutates grid state, and the host's own
    render loop (terminal frame loop or web SSE loop) repaints. No HTML
    is produced here.
    """
    from typing import cast

    from xnano._dispatch import invoke_hook
    from xnano.context import Context

    normalized = _normalize_request_path(path)
    routes = collect_request_routes(type(grid))
    matched = False
    # Request handlers are zero-arg methods that mutate grid state; they
    # never read ctx.terminal, so a null host context is sufficient.
    ctx = Context(event=None, terminal=cast(Any, None), state=None)
    for entry in routes:
        if entry["method"] != method or entry["path"] != normalized:
            continue
        name = getattr(entry["handler"], "__name__", "")
        handler = getattr(grid, name, None)
        if handler is None:
            continue
        invoke_hook(handler, grid, ctx)
        matched = True
    return matched


__all__ = (
    "HttpMethod",
    "collect_request_routes",
    "dispatch_request",
    "has_request_hooks",
    "on_get_request",
    "on_post_request",
)
