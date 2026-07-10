"""xnano.beta.web

---

Web host for xnano grids — the browser analogue of ``Terminal``.

Renders a grid to HTML via flexbox + htmx, owns per-visitor or shared
sessions, and dispatches browser events into the same ``@on_*`` hook
paths the terminal loop uses. Custom HTTP routes are declared with
``@on_get`` / ``@on_post`` from ``xnano.beta.requests``.
"""

from __future__ import annotations

import html
from typing import Any, cast

from xnano.beta.controllers.web import WebController
from xnano.beta.requests import (
    HttpMethod,
    _OnRequestHookEntry,
    _RequestHooksRegistry,
)
from xnano.hooks import _EventHooksRegistry


_SESSION_COOKIE = "xnano-session"

_WEB_KEY_ALIASES: dict[str, str] = {
    "escape": "esc",
    "return": "enter",
    " ": "space",
}


def _normalize_web_binding(
    binding: str,
) -> tuple[frozenset[str], str] | None:
    """Normalize a ``ctrl+shift+k`` style binding for comparison.

    Args:
        binding: The binding string to normalize.

    Returns:
        A ``(modifiers, key)`` pair, or ``None`` for an empty binding.
    """
    parts = [part.strip().lower() for part in binding.split("+")]
    parts = [part for part in parts if part]
    if not parts:
        return None
    key = parts[-1]
    key = _WEB_KEY_ALIASES.get(key, key)
    modifiers = frozenset(
        part for part in parts[:-1] if part in ("ctrl", "alt", "shift")
    )
    return (modifiers, key)


class _WebKeyboardEventData:
    """Duck-typed keyboard payload for hooks dispatched from the browser.

    Mirrors the surface hooks read from the terminal's
    ``KeyboardEventData``: ``kind``, ``key``, ``modifiers``,
    ``character``, and ``matches``.
    """

    type = "keyboard"
    kind = "press"

    def __init__(self, binding: str) -> None:
        normalized = _normalize_web_binding(binding) or (frozenset(), "")
        self._modifiers, self._key = normalized
        self.key = self._key
        self.modifiers = sorted(self._modifiers)
        if len(self._key) == 1:
            self.character: str | None = self._key
        elif self._key == "space":
            self.character = " "
        else:
            self.character = None

    def matches(self, *bindings: str) -> bool:
        """Return whether this event matches any of ``bindings``."""
        for binding in bindings:
            if binding is None:
                return True
            if _normalize_web_binding(str(binding)) == (
                self._modifiers,
                self._key,
            ):
                return True
        return False


class _WebEvent:
    """Duck-typed ``Event`` shell carrying one browser sub-event."""

    def __init__(
        self, *, keyboard: Any = None, mouse: Any = None
    ) -> None:
        self._keyboard = keyboard
        self._mouse = mouse

    def is_keyboard_event(self) -> bool:
        return self._keyboard is not None

    def is_mouse_event(self) -> bool:
        return self._mouse is not None

    def is_resize_event(self) -> bool:
        return False

    def is_clipboard_event(self) -> bool:
        return False

    def is_focus_event(self) -> bool:
        return False

    @property
    def keyboard_event(self) -> Any:
        return self._keyboard

    @property
    def mouse_event(self) -> Any:
        return self._mouse


class _WebSession:
    """One live grid plus its hooks — the web analogue of a terminal.

    Duck-types the small surface the shared dispatch helpers read from a
    ``Terminal`` (``_hooks``, ``_attached_grids``,
    ``_attached_frame_grids``, ``state``), so hook registration and the
    tick pump are the exact same code paths the terminal loop uses.
    """

    def __init__(self, grid: Any, state: Any) -> None:
        self.grid = grid
        self.state = state
        self.controller = WebController()
        self.controller.grid_observer = self._observe_grid
        self._hooks = _EventHooksRegistry()
        self._attached_grids: dict[int, Any] = {}
        self._attached_frame_grids: list[Any] = []
        self._request_hooks: list[_OnRequestHookEntry] = []
        self._request_hook_grids: dict[int, Any] = {}

    def _observe_grid(self, grid: Any) -> None:
        from xnano.core.dispatch import track_frame_grid

        track_frame_grid(cast(Any, self), grid)
        self._collect_request_hooks(grid)

    def _collect_request_hooks(self, grid: Any) -> None:
        """Register ``@on_get`` / ``@on_post`` handlers for ``grid``.

        Bound once per grid instance so nested grids can contribute
        routes without double-binding on every paint.
        """
        grid_id = id(grid)
        if grid_id in self._request_hook_grids:
            return
        self._request_hook_grids[grid_id] = grid
        collected = _RequestHooksRegistry.from_component_class(type(grid))
        from xnano.core.dispatch import rebind_hook_handler

        for entry in collected.all_hooks():
            self._request_hooks.append(
                _OnRequestHookEntry(
                    method=entry["method"],
                    path=entry["path"],
                    handler=rebind_hook_handler(entry["handler"], grid),
                )
            )

    def render(self) -> str:
        """Render the session's grid to an HTML fragment."""
        self._attached_frame_grids.clear()
        return self.controller.render_grid_html(self.grid)

    def pump(self) -> None:
        """Run tick/state/field hooks, exactly like the terminal loop."""
        from xnano.core.dispatch import pump_tick

        pump_tick(cast(Any, self))

    def _make_context(self, event: Any = None) -> Any:
        from xnano.context import Context

        return Context(
            event=event,
            terminal=cast(Any, self),
            state=self.state,
        )

    def dispatch_click(self, target_id: str) -> str:
        """Fire the ``@on_click`` handler for ``target_id``, re-render.

        Unknown or stale ids degrade to an idempotent refresh.
        """
        info = self.controller.click_targets.get(target_id)
        if info is not None:
            from xnano.events import MouseEventData
            from xnano.grid import _resolve_grid_mouse_handler
            from xnano.core.dispatch import invoke_hook

            grid, field_name = info
            handler = _resolve_grid_mouse_handler(grid, field_name)
            if handler is not None:
                mouse = MouseEventData(
                    kind="press", x=0, y=0, button="left"
                )
                ctx = self._make_context(_WebEvent(mouse=mouse))
                invoke_hook(handler, grid, ctx)
        self.pump()
        return self.render()

    def dispatch_keyboard(self, binding: str) -> str:
        """Fire ``@on_event`` / ``@on_keyboard`` hooks for a keypress."""
        from xnano.core.dispatch import (
            invoke_hook,
            keyboard_matches,
            resolve_hook_grid,
        )

        keyboard = _WebKeyboardEventData(binding)
        ctx = self._make_context(_WebEvent(keyboard=keyboard))
        for handler in self._hooks.on_event_hooks:
            grid = resolve_hook_grid(cast(Any, self), handler)
            invoke_hook(handler, grid, ctx)
        for entry in self._hooks.on_keyboard_hooks:
            if not keyboard_matches(keyboard, entry):
                continue
            handler = entry["handler"]
            grid = getattr(handler, "__self__", None)
            if grid is None:
                grid = resolve_hook_grid(cast(Any, self), handler)
            invoke_hook(handler, grid, ctx)
        self.pump()
        return self.render()

    def dispatch_input(self, target_id: str, value: str) -> None:
        """Sync an edited ``<input>`` value back onto its ``Text``."""
        info = self.controller.input_targets.get(target_id)
        if info is None:
            return
        from xnano.focus import get_input_text

        grid, field_name = info
        text = get_input_text(grid, field_name)
        if text is not None:
            text.content = value
            text.cursor = len(value)
        self.pump()

    def dispatch_tick(self) -> str:
        """Run one poll tick (interval-gated hooks), re-render."""
        self.pump()
        return self.render()

    def dispatch_request(
        self,
        method: HttpMethod,
        path: str,
    ) -> str:
        """Fire matching ``@on_get`` / ``@on_post`` hooks, then re-render.

        Args:
            method: HTTP method of the request.
            path: Normalized request path (leading slash).

        Returns:
            A fresh HTML fragment for the session grid.
        """
        # Ensure request hooks from the root grid are registered even
        # before the first paint (e.g. pure API-style POSTs).
        self._collect_request_hooks(self.grid)

        from xnano.core.dispatch import invoke_hook

        ctx = self._make_context()
        for entry in self._request_hooks:
            if entry["method"] != method or entry["path"] != path:
                continue
            handler = entry["handler"]
            grid = getattr(handler, "__self__", None)
            if grid is None:
                grid = self.grid
            invoke_hook(handler, grid, ctx)
        self.pump()
        return self.render()

    def poll_interval_ms(self) -> int | None:
        """Return the htmx poll interval, or ``None`` when not needed.

        Polling is only wired when tick/state/field hooks exist; the
        interval is the smallest positive ``@on_tick`` interval
        (defaulting to one second) clamped to at least 100ms.
        """
        hooks = self._hooks
        if not (
            hooks.on_tick_hooks
            or hooks.on_state_hooks
            or hooks.on_field_hooks
        ):
            return None
        intervals = [
            entry["interval"]
            for entry in hooks.on_tick_hooks
            if entry["interval"] > 0
        ]
        interval = min(intervals) if intervals else 1000
        return max(100, interval)

    def wants_keyboard(self) -> bool:
        """Whether the page should capture browser keydown events."""
        return bool(
            self._hooks.on_keyboard_hooks or self._hooks.on_event_hooks
        )


_KEYBOARD_SCRIPT = """
<script>
document.addEventListener("keydown", function (event) {
  var tag = event.target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") { return; }
  var named = {
    " ": "space", "Escape": "esc", "Enter": "enter",
    "Backspace": "backspace", "Tab": "tab", "Delete": "delete",
    "ArrowUp": "up", "ArrowDown": "down",
    "ArrowLeft": "left", "ArrowRight": "right",
    "Home": "home", "End": "end",
    "PageUp": "pageup", "PageDown": "pagedown", "Insert": "insert"
  };
  var key = named[event.key];
  if (!key) {
    if (event.key.length === 1) { key = event.key.toLowerCase(); }
    else { return; }
  }
  var mods = [];
  if (event.ctrlKey) { mods.push("ctrl"); }
  if (event.altKey) { mods.push("alt"); }
  if (event.shiftKey) { mods.push("shift"); }
  var binding = mods.concat([key]).join("+");
  htmx.ajax(
    "POST",
    "/xnano/key?binding=" + encodeURIComponent(binding),
    {target: "#xnano-app", swap: "innerHTML"}
  );
});
</script>
"""


def _source_grid_class(source: Any) -> type | None:
    """Return the grid class used to discover request routes.

    Args:
        source: A ``Grid`` instance or callable factory (often the class).

    Returns:
        The class to scan for ``@on_get`` / ``@on_post``, or ``None``.
    """
    if source is None:
        return None
    from xnano.grid import Grid

    if isinstance(source, type) and issubclass(source, Grid):
        return source
    if isinstance(source, Grid):
        return type(source)
    if callable(source):
        # Factory: best-effort peek at annotations / return type is not
        # reliable; callers should pass the Grid class itself.
        return None
    return None


class Web:
    """Web host for xnano grids — the browser analogue of ``Terminal``.

    Pass a ``Grid`` instance for one shared grid across all visitors,
    or a callable factory (e.g. the ``Grid`` subclass itself) for a
    fresh grid per browser session:

        Web(title="dashboard").run(Dashboard())     # shared
        Web(title="per-user app").run(Dashboard)    # session-per-visitor

    Supported hooks per event: ``@on_click`` / field ``@on_mouse``
    (element clicks), ``@on_keyboard`` / ``@on_event`` (browser keydown),
    ``@on_tick`` / ``@on_state`` / ``@on_field`` (htmx polling),
    ``@on_get`` / ``@on_post`` (custom HTTP routes via htmx or navigation),
    and editable ``Text(input=True)`` fields sync through real ``<input>``
    elements. Effects, focus cycling, and slide are terminal-only.
    """

    def __init__(
        self, *, state: Any = None, title: str | None = None
    ) -> None:
        self.state = state
        self.title = title
        self._source: Any = None
        self._sessions: dict[str, _WebSession] = {}
        self._default_session: _WebSession | None = None

    # ── session management ────────────────────────────────────────────

    def _is_factory(self) -> bool:
        from xnano.grid import Grid

        return callable(self._source) and not isinstance(
            self._source, Grid
        )

    def _make_session(self) -> _WebSession:
        grid = self._source() if self._is_factory() else self._source
        return _WebSession(grid, self.state)

    def _ensure_default_session(self, grid: Any = None) -> _WebSession:
        if grid is not None and (
            self._default_session is None
            or self._default_session.grid is not grid
        ):
            self._default_session = _WebSession(grid, self.state)
        if self._default_session is None:
            if self._source is None:
                raise RuntimeError(
                    "no grid attached; call run()/build_app() or pass a "
                    "grid to render_html() first"
                )
            self._default_session = self._make_session()
        return self._default_session

    def _session_for_request(
        self, request: Any
    ) -> tuple[_WebSession, str | None]:
        """Resolve the session for a request.

        Returns:
            ``(session, new_cookie_value)`` — the cookie value is set
            only when a new per-visitor session was just created.
        """
        if not self._is_factory():
            return self._ensure_default_session(), None
        session_id = request.cookies.get(_SESSION_COOKIE)
        if session_id and session_id in self._sessions:
            return self._sessions[session_id], None
        import secrets

        session_id = secrets.token_hex(16)
        session = self._make_session()
        self._sessions[session_id] = session
        return session, session_id

    def _discover_request_routes(self) -> list[_OnRequestHookEntry]:
        """Collect request routes from the attached grid source class.

        Returns:
            Request hook entries (handlers unbound; rebound per session).
        """
        grid_class = _source_grid_class(self._source)
        if grid_class is None and self._default_session is not None:
            grid_class = type(self._default_session.grid)
        if grid_class is None:
            return []
        return _RequestHooksRegistry.from_component_class(
            grid_class
        ).all_hooks()

    # ── programmatic surface (used directly and by tests) ─────────────

    @property
    def _controller(self) -> WebController:
        """The default session's controller (programmatic access)."""
        return self._ensure_default_session().controller

    def render_html(self, grid: Any = None) -> str:
        """Render a grid to HTML body content.

        Args:
            grid: The Grid instance to render (or None to use the
                default session's grid).

        Returns:
            The HTML body content (not a full page).
        """
        return self._ensure_default_session(grid).render()

    def dispatch_click(self, target_id: str) -> str:
        """Handle a click event on the default session and re-render."""
        return self._ensure_default_session().dispatch_click(target_id)

    def dispatch_keyboard(self, binding: str) -> str:
        """Handle a keypress on the default session and re-render."""
        return self._ensure_default_session().dispatch_keyboard(binding)

    def dispatch_input(self, target_id: str, value: str) -> None:
        """Sync an input edit into the default session."""
        self._ensure_default_session().dispatch_input(target_id, value)

    def dispatch_tick(self) -> str:
        """Run one poll tick on the default session and re-render."""
        return self._ensure_default_session().dispatch_tick()

    def dispatch_request(
        self, method: HttpMethod, path: str
    ) -> str:
        """Fire an ``@on_get`` / ``@on_post`` hook on the default session.

        Args:
            method: ``"GET"`` or ``"POST"``.
            path: Request path (leading slash optional).

        Returns:
            A re-rendered HTML fragment.
        """
        from xnano.beta.requests import _normalize_request_path

        return self._ensure_default_session().dispatch_request(
            method, _normalize_request_path(path)
        )

    # ── page assembly ─────────────────────────────────────────────────

    def build_page(
        self,
        body_html: str,
        *,
        session: _WebSession | None = None,
    ) -> str:
        """Build a complete HTML page around a rendered fragment.

        Args:
            body_html: The inner body HTML.
            session: The session whose hooks decide whether keyboard
                capture and tick polling are wired in. Defaults to the
                default session when one exists.

        Returns:
            A full HTML document string.
        """
        if session is None:
            session = self._default_session
        title = html.escape(self.title) if self.title else "xnano"

        extras: list[str] = []
        if session is not None:
            if session.wants_keyboard():
                extras.append(_KEYBOARD_SCRIPT)
            interval = session.poll_interval_ms()
            if interval is not None:
                # The poller lives outside #xnano-app so swaps never
                # tear down the polling trigger.
                extras.append(
                    f'<div hx-post="/xnano/tick" '
                    f'hx-trigger="every {interval}ms" '
                    f'hx-target="#xnano-app" hx-swap="innerHTML">'
                    f"</div>"
                )

        return (
            "<!doctype html>\n"
            "<html><head>\n"
            '<meta charset="utf-8"/>\n'
            f"<title>{title}</title>\n"
            '<script src="https://cdn.tailwindcss.com"></script>\n'
            '<script src="'
            'https://unpkg.com/htmx.org@1.9.12"></script>\n'
            "</head>\n"
            '<body class="bg-zinc-900 text-zinc-100 font-mono '
            'min-h-screen p-4">\n'
            f'<div id="xnano-app" class="h-full">{body_html}</div>\n'
            f"{''.join(extras)}\n"
            "</body></html>\n"
        )

    def _response_for_session(
        self,
        session: _WebSession,
        body: str,
        *,
        request: Any,
        cookie: str | None,
        HTMLResponse: Any,
        full_page: bool | None = None,
    ) -> Any:
        """Build an HTML response, full page or htmx fragment.

        Args:
            session: The live session.
            body: Rendered fragment HTML.
            request: The incoming Starlette request.
            cookie: Optional new session cookie value.
            HTMLResponse: Starlette response class.
            full_page: Force full page (``True``) or fragment (``False``).
                When ``None``, full page unless ``HX-Request`` is set.

        Returns:
            An HTML response, with session cookie applied when needed.
        """
        if full_page is None:
            hx = request.headers.get("hx-request", "").lower()
            full_page = hx not in ("true", "1")
        content = (
            self.build_page(body, session=session)
            if full_page
            else body
        )
        response = HTMLResponse(content)
        if cookie is not None:
            response.set_cookie(
                _SESSION_COOKIE, cookie, httponly=True
            )
        return response

    # ── server ────────────────────────────────────────────────────────

    def build_app(self, grid: Any) -> Any:
        """Build and return a Starlette ASGI app.

        Args:
            grid: A Grid instance (shared across visitors) or a callable
                factory producing one grid per browser session.

        Returns:
            A Starlette application instance.
        """
        self._source = grid

        try:
            from starlette.applications import Starlette
            from starlette.responses import HTMLResponse, Response
            from starlette.routing import Route
        except ImportError as error:
            raise ImportError(
                'the web interface requires the "web" extra: '
                'pip install "xnano[web]"'
            ) from error

        def _with_cookie(response: Any, cookie: str | None) -> Any:
            if cookie is not None:
                response.set_cookie(
                    _SESSION_COOKIE, cookie, httponly=True
                )
            return response

        async def index(request: Any) -> Any:
            session, cookie = self._session_for_request(request)
            # Fire root ``@on_get("/")`` hooks before the first paint.
            body = session.dispatch_request("GET", "/")
            page = self.build_page(body, session=session)
            return _with_cookie(HTMLResponse(page), cookie)

        async def click_endpoint(request: Any) -> Any:
            session, cookie = self._session_for_request(request)
            target_id = request.path_params["target_id"]
            return _with_cookie(
                HTMLResponse(session.dispatch_click(target_id)), cookie
            )

        async def key_endpoint(request: Any) -> Any:
            session, cookie = self._session_for_request(request)
            binding = request.query_params.get("binding", "")
            return _with_cookie(
                HTMLResponse(session.dispatch_keyboard(binding)), cookie
            )

        async def tick_endpoint(request: Any) -> Any:
            session, cookie = self._session_for_request(request)
            return _with_cookie(
                HTMLResponse(session.dispatch_tick()), cookie
            )

        async def input_endpoint(request: Any) -> Any:
            session, cookie = self._session_for_request(request)
            target_id = request.path_params["target_id"]
            form = await request.form()
            session.dispatch_input(
                target_id, str(form.get("value", ""))
            )
            return _with_cookie(Response(status_code=204), cookie)

        routes: list[Any] = [
            Route("/", endpoint=index),
            Route(
                "/xnano/click/{target_id}",
                endpoint=click_endpoint,
                methods=["POST"],
            ),
            Route("/xnano/key", endpoint=key_endpoint, methods=["POST"]),
            Route(
                "/xnano/tick", endpoint=tick_endpoint, methods=["POST"]
            ),
            Route(
                "/xnano/input/{target_id}",
                endpoint=input_endpoint,
                methods=["POST"],
            ),
        ]

        # Custom ``@on_get`` / ``@on_post`` routes (skip ``/`` GET — that
        # is already the index endpoint, which fires those hooks).
        seen_routes: set[tuple[str, str]] = {("GET", "/")}
        for entry in self._discover_request_routes():
            method = entry["method"]
            path = entry["path"]
            key = (method, path)
            if key in seen_routes:
                continue
            if path.startswith("/xnano/"):
                continue
            seen_routes.add(key)

            def _make_request_endpoint(
                http_method: HttpMethod = method,
                request_path: str = path,
            ) -> Any:
                async def request_endpoint(request: Any) -> Any:
                    session, cookie = self._session_for_request(
                        request
                    )
                    body = session.dispatch_request(
                        http_method, request_path
                    )
                    return self._response_for_session(
                        session,
                        body,
                        request=request,
                        cookie=cookie,
                        HTMLResponse=HTMLResponse,
                        # POST is almost always an htmx swap target.
                        full_page=(
                            None if http_method == "GET" else False
                        ),
                    )

                return request_endpoint

            routes.append(
                Route(
                    path,
                    endpoint=_make_request_endpoint(),
                    methods=[method],
                )
            )

        return Starlette(routes=routes)

    def run(
        self,
        grid: Any,
        *,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        """Run the web server.

        Args:
            grid: A Grid instance (shared) or callable factory
                (per-visitor sessions).
            host: The host to bind to.
            port: The port to bind to.
        """
        app = self.build_app(grid)

        try:
            import uvicorn
        except ImportError as error:
            raise ImportError(
                'the web interface requires the "web" extra: '
                'pip install "xnano[web]"'
            ) from error

        uvicorn.run(app, host=host, port=port)


__all__ = ("Web", "WebController")
