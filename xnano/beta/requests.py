"""xnano.beta.requests

---

Declare HTTP routes on grids and return text, bytes, or JSON responses.
"""

from __future__ import annotations

import dataclasses
import functools
import json
import urllib.parse
from typing import (
    Any,
    Callable,
    ClassVar,
    Literal,
    Mapping,
    Sequence,
    TypeAlias,
    TypedDict,
)

EventHookFunction: TypeAlias = Callable[..., Any]

HttpMethod: TypeAlias = Literal[
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "CONNECT",
    "OPTIONS",
    "TRACE",
    "PATCH",
    "QUERY",
]
"""A standard HTTP request method."""

ON_REQUEST_METHOD_ATTR = "__xnano_on_request_method__"
ON_REQUEST_PATH_ATTR = "__xnano_on_request_path__"


class _OnRequestHookEntry(TypedDict):
    method: HttpMethod
    path: str
    handler: EventHookFunction


@dataclasses.dataclass(slots=True)
class _RequestHooksRegistry:
    """Collects ``@on_*_request`` hooks declared on a grid class."""

    ON_REQUEST_METHOD_ATTR: ClassVar[str] = ON_REQUEST_METHOD_ATTR
    ON_REQUEST_PATH_ATTR: ClassVar[str] = ON_REQUEST_PATH_ATTR

    request_hooks: list[_OnRequestHookEntry] = dataclasses.field(
        default_factory=list, init=False
    )

    def all_hooks(self) -> list[_OnRequestHookEntry]:
        """Return all request hooks in registration order."""
        return self.request_hooks.copy()

    @classmethod
    def from_component_class(
        cls, component_class: type
    ) -> "_RequestHooksRegistry":
        """Collect ``@on_*_request`` hooks from a grid (or component) class.

        A name defined on a more-derived class shadows any base
        definition.
        """
        cached = cls._get_component_class_hooks(component_class)
        registry = cls()
        registry.request_hooks = [
            entry.copy() for entry in cached.request_hooks
        ]
        return registry

    @classmethod
    @functools.cache
    def _get_component_class_hooks(
        cls, component_class: type
    ) -> "_RequestHooksRegistry":
        """Collect and cache the immutable request-hook template for a class."""
        registry = cls()
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

                is_hook_method = hasattr(member, cls.ON_REQUEST_METHOD_ATTR)
                if name.startswith("_") and not is_hook_method:
                    continue

                path = getattr(member, cls.ON_REQUEST_PATH_ATTR, None)
                if path is None:
                    continue

                method = getattr(member, cls.ON_REQUEST_METHOD_ATTR, None)
                if method is not None:
                    registry.request_hooks.append(
                        _OnRequestHookEntry(
                            method=method, path=path, handler=member
                        )
                    )
        return registry


def _normalize_request_path(path: str) -> str:
    """Normalize a request path to a leading-slash form."""
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
    """Mark ``fn`` as an HTTP request hook for ``method`` at ``path``."""
    normalized = _normalize_request_path(path)
    setattr(fn, ON_REQUEST_METHOD_ATTR, method)
    setattr(fn, ON_REQUEST_PATH_ATTR, normalized)
    return fn


RequestDecorator: TypeAlias = (
    EventHookFunction | Callable[[EventHookFunction], EventHookFunction]
)
"""A request handler or a decorator that creates one."""


def _register_request_hook(
    method: HttpMethod,
    handler_or_path: EventHookFunction | str | None,
    path: str | None,
) -> RequestDecorator:
    """Register a request hook for one HTTP method."""
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
        return _decorate_request_hook(fn, method=method, path=resolved_path)

    return decorator


def on_get_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``GET`` request."""
    return _register_request_hook("GET", handler_or_path, path)


def on_head_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``HEAD`` request."""
    return _register_request_hook("HEAD", handler_or_path, path)


def on_post_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``POST`` request."""
    return _register_request_hook("POST", handler_or_path, path)


def on_put_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``PUT`` request."""
    return _register_request_hook("PUT", handler_or_path, path)


def on_delete_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``DELETE`` request."""
    return _register_request_hook("DELETE", handler_or_path, path)


def on_connect_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``CONNECT`` request."""
    return _register_request_hook("CONNECT", handler_or_path, path)


def on_options_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``OPTIONS`` request."""
    return _register_request_hook("OPTIONS", handler_or_path, path)


def on_trace_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``TRACE`` request."""
    return _register_request_hook("TRACE", handler_or_path, path)


def on_patch_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``PATCH`` request."""
    return _register_request_hook("PATCH", handler_or_path, path)


def on_query_request(
    handler_or_path: EventHookFunction | str | None = None,
    /,
    *,
    path: str | None = None,
) -> RequestDecorator:
    """Decorate a handler for an HTTP ``QUERY`` request."""
    return _register_request_hook("QUERY", handler_or_path, path)


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


def request(
    method: str,
    path: str = "/",
) -> Callable[[EventHookFunction], EventHookFunction]:
    """Register an HTTP request hook for an arbitrary method.

    Args:
        method: HTTP method name.
        path: URL path (normalized to a leading slash).

    Returns:
        A decorator that marks the function as a request hook.
    """
    method_upper = method.upper()
    factories: dict[str, Callable[..., Any]] = {
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
    factory = factories.get(method_upper)
    if factory is None:
        raise ValueError(f"Unsupported HTTP method: {method!r}")
    return factory(path)


@dataclasses.dataclass(frozen=True, slots=True)
class Request:
    """Immutable parsed HTTP request.

    Attributes:
        method: Uppercase HTTP method.
        path: Normalized path beginning with ``/``.
        query: Read-only multi-value query mapping.
        headers: Read-only header mapping (lowercase keys preferred).
        body: Raw request body bytes.

    Example:
        >>> request = Request.from_parts("GET", "/search", query_string="q=xnano")
        >>> request.method, request.query["q"]
        ('GET', ('xnano',))
    """

    method: str
    """Uppercase HTTP method."""
    path: str
    """Normalized path beginning with ``/``."""
    query: Mapping[str, tuple[str, ...]] = dataclasses.field(
        default_factory=dict
    )
    """Multi-value query parameters."""
    headers: Mapping[str, str] = dataclasses.field(default_factory=dict)
    """Request headers with lowercase names."""
    body: bytes = b""
    """Raw request body."""

    def text(self, encoding: str = "utf-8") -> str:
        """Decode ``body`` as text."""
        return self.body.decode(encoding)

    def json(self) -> Any:
        """Parse ``body`` as JSON via stdlib ``json``."""
        if not self.body:
            return None
        return json.loads(self.body.decode("utf-8"))

    @classmethod
    def from_parts(
        cls,
        method: str,
        path: str,
        *,
        query_string: str = "",
        headers: Mapping[str, str] | None = None,
        body: bytes = b"",
        max_body: int = 1_048_576,
    ) -> "Request":
        """Build a request from raw HTTP parts with body limits.

        Raises:
            ValueError: If ``body`` exceeds ``max_body``.
        """
        if len(body) > max_body:
            raise ValueError(f"Request body exceeds limit of {max_body} bytes")
        cleaned = _normalize_request_path(path)
        parsed = urllib.parse.parse_qs(query_string, keep_blank_values=True)
        query = {key: tuple(values) for key, values in parsed.items()}
        header_map = {
            str(key).lower(): str(value)
            for key, value in (headers or {}).items()
        }
        return cls(
            method=method.upper(),
            path=cleaned,
            query=query,
            headers=header_map,
            body=body,
        )


@dataclasses.dataclass(slots=True)
class Response:
    """HTTP response returned from a request hook.

    Attributes:
        body: Response body as bytes or text.
        status: HTTP status code.
        headers: Response headers.

    Example:
        >>> response = Response.json({"ready": True}, status=201)
        >>> response.status
        201
    """

    body: bytes | str = b""
    """Response body."""
    status: int = 200
    """HTTP status code."""
    headers: dict[str, str] = dataclasses.field(default_factory=dict)
    """Response headers."""

    def as_bytes(self) -> bytes:
        """Return the body as bytes."""
        if isinstance(self.body, bytes):
            return self.body
        return self.body.encode("utf-8")

    @classmethod
    def json(
        cls,
        data: Any,
        *,
        status: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> "Response":
        """Build a JSON response."""
        payload = json.dumps(data).encode("utf-8")
        merged = {"content-type": "application/json; charset=utf-8"}
        if headers:
            merged.update({str(k).lower(): str(v) for k, v in headers.items()})
        return cls(body=payload, status=status, headers=merged)


@dataclasses.dataclass(frozen=True, slots=True)
class RequestEvent:
    """Event payload carrying a parsed ``Request``.

    Attributes:
        request: Parsed HTTP request.
        type: Payload category.
    """

    request: Request
    """Parsed HTTP request."""
    type: str = "request"
    """Payload category."""


def dispatch_request(
    grid: Any,
    method: str,
    path: str,
    *,
    request_obj: Request | None = None,
    runtime: Any | None = None,
) -> Response | bool:
    """Run the request hook matching ``method`` and ``path``.

    Pass a runtime to make it available through the handler's ``Context``.
    A handler that returns ``None`` produces an empty successful response.

    Args:
        grid: Grid instance declaring request hooks.
        method: HTTP method.
        path: Request path.
        request_obj: Optional parsed request for ``ctx.request``.
        runtime: Optional runtime exposed through the hook context.

    Returns:
        The handler response, or whether a route matched when no runtime was
        supplied.
    """
    from xnano.beta.context import Context
    from xnano.beta.utils.dispatch import invoke_hook

    method = method.upper()
    cleaned = _normalize_request_path(path)
    routes: Sequence[_OnRequestHookEntry] = collect_request_routes(type(grid))
    matched = False
    last_response: Response | None = None

    facade = runtime if runtime is not None else grid
    # Stash the request on the facade so Context.request can read it
    # without inventing a parallel Event subclass during the beta window.
    if request_obj is not None:
        try:
            object.__setattr__(facade, "_beta_request", request_obj)
        except Exception:
            setattr(facade, "_beta_request", request_obj)

    ctx = Context(
        event=None,
        terminal=facade,
        state=getattr(runtime, "state", getattr(grid, "state", None)),
    )

    try:
        for entry in routes:
            if entry["method"] != method or entry["path"] != cleaned:
                continue
            name = getattr(entry["handler"], "__name__", "")
            handler = getattr(grid, name, None)
            if handler is None:
                continue
            result = invoke_hook(handler, grid, ctx)
            matched = True
            if isinstance(result, Response):
                last_response = result
            elif result is not None and not isinstance(result, bool):
                last_response = Response(body=str(result))
    finally:
        if request_obj is not None:
            try:
                object.__setattr__(facade, "_beta_request", None)
            except Exception:
                if hasattr(facade, "_beta_request"):
                    delattr(facade, "_beta_request")

    if runtime is not None:
        if last_response is not None:
            return last_response
        if matched:
            return Response()
        return Response(status=404, body=b"Not Found")
    return matched


__all__ = (
    "HttpMethod",
    "Request",
    "RequestEvent",
    "Response",
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
    "request",
)
