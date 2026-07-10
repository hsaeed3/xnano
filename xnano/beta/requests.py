"""xnano.beta.requests

HTTP request hooks for creating reactive grids within web applications.

This module provides ``@on_get`` and ``@on_post`` decorators which can be
annotated onto methods of a ``Grid`` subclass to handle HTTP requests when
the grid is served by ``Web``. Under a terminal session the decorators are
harmless no-ops for dispatch — the methods remain on the class and never
fire.

Example:

    ```python
    from xnano.grid import Grid
    from xnano.fields import Field
    from xnano.beta.requests import on_get, on_post
    from xnano.beta.web import Web

    class Counter(Grid):
        label: str = Field(default="Count: 0")
        count: int = Field(default=0, state=True)

        @on_post("/increment")
        def increment(self) -> None:
            self.count += 1
            self.label = f"Count: {self.count}"

        @on_get("/reset")
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

import dataclasses
from typing import (
    Callable,
    ClassVar,
    Literal,
    TypeAlias,
    TypedDict,
    overload,
)

from xnano.hooks import EventHookFunction


HttpMethod: TypeAlias = Literal["GET", "POST"]
"""HTTP methods supported by request hooks."""


class _OnRequestHookEntry(TypedDict):
    method: HttpMethod
    path: str
    handler: EventHookFunction


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


@dataclasses.dataclass(slots=True)
class _RequestHooksRegistry:
    """Internal utility class for managing HTTP request hook registration
    within grids.
    """

    ON_GET_HOOK_ATTR: ClassVar[str] = "__xnano_on_get__"
    ON_POST_HOOK_ATTR: ClassVar[str] = "__xnano_on_post__"
    ON_REQUEST_PATH_ATTR: ClassVar[str] = "__xnano_on_request_path__"

    on_get_hooks: list[_OnRequestHookEntry] = dataclasses.field(
        default_factory=list, init=False
    )
    on_post_hooks: list[_OnRequestHookEntry] = dataclasses.field(
        default_factory=list, init=False
    )

    def all_hooks(self) -> list[_OnRequestHookEntry]:
        """Return GET and POST hooks in registration order.

        Returns:
            Combined list of request hook entries.
        """
        return [*self.on_get_hooks, *self.on_post_hooks]

    @classmethod
    def from_component_class(
        cls, component_class: type
    ) -> _RequestHooksRegistry:
        """Collect ``@on_get`` / ``@on_post`` hooks from a component class.

        A name defined on a more-derived class shadows any base definition,
        matching ``_EventHooksRegistry.from_component_class``.

        Args:
            component_class: The grid (or component) class to scan.

        Returns:
            A registry of collected request hooks.
        """
        registry = cls()
        hook_attributes = (
            cls.ON_GET_HOOK_ATTR,
            cls.ON_POST_HOOK_ATTR,
        )

        seen_names: set[str] = set()
        for base in component_class.__mro__:
            if base is object:
                continue
            for name, member in base.__dict__.items():
                if not callable(member):
                    continue
                if name in seen_names:
                    continue
                seen_names.add(name)

                is_hook_method = any(
                    hasattr(member, attribute)
                    for attribute in hook_attributes
                )
                if name.startswith("_") and not is_hook_method:
                    continue

                path = getattr(member, cls.ON_REQUEST_PATH_ATTR, None)
                if path is None:
                    continue

                if hasattr(member, cls.ON_GET_HOOK_ATTR):
                    registry.on_get_hooks.append(
                        _OnRequestHookEntry(
                            method="GET",
                            path=path,
                            handler=member,
                        )
                    )
                if hasattr(member, cls.ON_POST_HOOK_ATTR):
                    registry.on_post_hooks.append(
                        _OnRequestHookEntry(
                            method="POST",
                            path=path,
                            handler=member,
                        )
                    )
        return registry


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
def on_get(
    path: str,
    /,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_get(
    handler: EventHookFunction,
    /,
    *,
    path: str = "/",
) -> EventHookFunction: ...
def on_get(
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
            handler when used as ``@on_get`` / ``@on_get(path=...)``.
        path: Explicit path when decorating a handler directly.

    Returns:
        The decorated hook function, or a decorator awaiting a function.

    Example:
        @on_get("/status")
        def show_status(self) -> None:
            self.label = "ok"

        @on_get
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
        return _decorate_request_hook(
            fn, method="GET", path=resolved_path
        )

    return decorator


@overload
def on_post(
    path: str,
    /,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_post(
    handler: EventHookFunction,
    /,
    *,
    path: str = "/",
) -> EventHookFunction: ...
def on_post(
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
            handler when used as ``@on_post`` / ``@on_post(path=...)``.
        path: Explicit path when decorating a handler directly.

    Returns:
        The decorated hook function, or a decorator awaiting a function.

    Example:
        @on_post("/increment")
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
        return _decorate_request_hook(
            fn, method="POST", path=resolved_path
        )

    return decorator


__all__ = (
    "HttpMethod",
    "on_get",
    "on_post",
)
