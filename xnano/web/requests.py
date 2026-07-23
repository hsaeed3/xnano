"""xnano.web.requests

---

HTTP request hooks for creating reactive grids.

Every standard HTTP method has a decorator — ``@on_get_request``,
``@on_head_request``, ``@on_post_request``, ``@on_put_request``,
``@on_delete_request``, ``@on_connect_request``, ``@on_options_request``,
``@on_trace_request``, ``@on_patch_request``, and ``@on_query_request``.
Annotate methods of a ``BaseGrid`` subclass; handlers mutate grid state
only — hosts repaint on their own schedule:

- Under ``Web``, routes are registered on the native stdlib server and the
  continuous cell-stream render loop reflects the mutation next frame.
- Under ``Terminal``, pass ``host``/``port`` to ``Terminal.run`` (or let the
  defaults apply) and a background request server exposes the same routes
  alongside the live TUI.

The same decorators are re-exported from ``xnano.hooks`` and
``xnano.requests``.

Example:

    ```python
    from xnano.grid import BaseGrid
    from xnano.fields import Field
    from xnano.web.requests import (
        on_delete_request,
        on_get_request,
        on_post_request,
        on_put_request,
    )
    from xnano.web import Web

    class Items(BaseGrid):
        label: str = Field(default="Count: 0")
        count: int = Field(default=0, state=True)

        @on_get_request("/items")
        def list_items(self) -> None:
            self.label = f"Count: {self.count}"

        @on_post_request("/items")
        def create_item(self) -> None:
            self.count += 1
            self.label = f"Count: {self.count}"

        @on_put_request("/items")
        def replace_items(self) -> None:
            self.count = 1
            self.label = "Count: 1"

        @on_delete_request("/items")
        def clear_items(self) -> None:
            self.count = 0
            self.label = "Count: 0"

    Web(title="items").run(Items)
    ```
"""

from __future__ import annotations

from typing import Any, Callable

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
    setattr(fn, _RequestHooksRegistry.ON_REQUEST_METHOD_ATTR, method)
    setattr(fn, _RequestHooksRegistry.ON_REQUEST_PATH_ATTR, normalized)
    return fn


def _create_request_hook(method: HttpMethod) -> Callable[..., Any]:
    """Create the public request decorator for one HTTP method."""

    def on_method_request(
        handler_or_path: EventHookFunction | str | None = None,
        /,
        *,
        path: str | None = None,
    ) -> EventHookFunction | Callable[[EventHookFunction], EventHookFunction]:
        """Register an HTTP request hook for a grid method."""
        if callable(handler_or_path):
            return _decorate_request_hook(
                handler_or_path,
                method=method,
                path=path if path is not None else "/",
            )

        resolved_path = (
            handler_or_path
            if isinstance(handler_or_path, str)
            else (path if path is not None else "/")
        )

        def decorator(fn: EventHookFunction) -> EventHookFunction:
            return _decorate_request_hook(
                fn, method=method, path=resolved_path
            )

        return decorator

    on_method_request.__name__ = f"on_{method.lower()}_request"
    return on_method_request


on_get_request = _create_request_hook("GET")
on_head_request = _create_request_hook("HEAD")
on_post_request = _create_request_hook("POST")
on_put_request = _create_request_hook("PUT")
on_delete_request = _create_request_hook("DELETE")
on_connect_request = _create_request_hook("CONNECT")
on_options_request = _create_request_hook("OPTIONS")
on_trace_request = _create_request_hook("TRACE")
on_patch_request = _create_request_hook("PATCH")
on_query_request = _create_request_hook("QUERY")


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

    method = method.upper()
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
    "on_connect_request",
    "on_delete_request",
    "on_get_request",
    "on_head_request",
    "on_options_request",
    "on_patch_request",
    "on_post_request",
    "on_put_request",
    "on_query_request",
    "on_trace_request",
)
