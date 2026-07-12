"""xnano.webui.web

---

``Web`` host: Starlette/uvicorn orchestration for browser sessions of
xnano grids.
"""

from __future__ import annotations

import html
from importlib.util import find_spec
from typing import Any, TYPE_CHECKING

from xnano.core.exceptions import ExtraNotInstalledError
from xnano.core.controllers.webui import WebController
from xnano.webui.requests import HttpMethod
from xnano.webui.session import WebSession
from xnano._function_hooks import (
    _OnRequestHookEntry,
    _RequestHooksRegistry,
)

if TYPE_CHECKING:
    if find_spec("starlette") is None:
        Starlette = Any
    else:
        from starlette.applications import Starlette


_SESSION_COOKIE = "xnano-session"


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
        source: A ``BaseGrid`` instance or callable factory (often the class).

    Returns:
        The class to scan for ``@on_get_request`` / ``@on_post_request``, or ``None``.
    """
    if source is None:
        return None
    from xnano.grid import BaseGrid

    if isinstance(source, type) and issubclass(source, BaseGrid):
        return source
    if isinstance(source, BaseGrid):
        return type(source)
    if callable(source):
        # Factory: best-effort peek at annotations / return type is not
        # reliable; callers should pass the BaseGrid class itself.
        return None
    return None


class Web:
    """Web host for xnano grids — the browser analogue of ``Terminal``.

    Pass a ``BaseGrid`` instance for one shared grid across all visitors,
    or a callable factory (e.g. the ``BaseGrid`` subclass itself) for a
    fresh grid per browser session:

        Web(title="dashboard").run(Dashboard())     # shared
        Web(title="per-user app").run(Dashboard)    # session-per-visitor

    Supported hooks per event: ``@on_click`` / field ``@on_mouse``
    (element clicks), ``@on_keyboard`` / ``@on_event`` (browser keydown),
    ``@on_tick`` / ``@on_state`` / ``@on_field`` (htmx polling),
    ``@on_get_request`` / ``@on_post_request`` (custom HTTP routes via htmx or navigation),
    and editable ``Text(input=True)`` fields sync through real ``<input>``
    elements. Effects, focus cycling, and slide are terminal-only.
    """

    def __init__(self, *, state: Any = None, title: str | None = None) -> None:
        self.state = state
        self.title = title
        self._source: Any = None
        self._sessions: dict[str, WebSession] = {}
        self._default_session: WebSession | None = None

    def _is_factory(self) -> bool:
        from xnano.grid import BaseGrid

        return callable(self._source) and not isinstance(
            self._source, BaseGrid
        )

    def _make_session(self) -> WebSession:
        grid = self._source() if self._is_factory() else self._source
        return WebSession(grid, self.state)

    def _ensure_default_session(self, grid: Any = None) -> WebSession:
        if grid is not None and (
            self._default_session is None
            or self._default_session.grid is not grid
        ):
            self._default_session = WebSession(grid, self.state)
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
    ) -> tuple[WebSession, str | None]:
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

    @property
    def _controller(self) -> WebController:
        """The default session's controller (programmatic access)."""
        return self._ensure_default_session().controller

    def render_html(self, grid: Any = None) -> str:
        """Render a grid to HTML body content.

        Args:
            grid: The BaseGrid instance to render (or None to use the
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

    def dispatch_request(self, method: HttpMethod, path: str) -> str:
        """Fire an ``@on_get_request`` / ``@on_post_request`` hook on the default session.

        Args:
            method: ``"GET"`` or ``"POST"``.
            path: Request path (leading slash optional).

        Returns:
            A re-rendered HTML fragment.
        """
        from xnano.webui.requests import _normalize_request_path

        return self._ensure_default_session().dispatch_request(
            method, _normalize_request_path(path)
        )

    def build_page(
        self,
        body_html: str,
        *,
        session: WebSession | None = None,
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
        session: WebSession,
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
        content = self.build_page(body, session=session) if full_page else body
        response = HTMLResponse(content)
        if cookie is not None:
            response.set_cookie(_SESSION_COOKIE, cookie, httponly=True)
        return response

    def build_app(self, grid: Any) -> Starlette:
        """Build and return a Starlette ASGI app.

        Args:
            grid: A BaseGrid instance (shared across visitors) or a callable
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
            raise ExtraNotInstalledError("web") from error

        def _with_cookie(response: Any, cookie: str | None) -> Any:
            if cookie is not None:
                response.set_cookie(_SESSION_COOKIE, cookie, httponly=True)
            return response

        async def index(request: Any) -> Any:
            session, cookie = self._session_for_request(request)
            # Fire root ``@on_get_request("/")`` hooks before the first paint.
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
            return _with_cookie(HTMLResponse(session.dispatch_tick()), cookie)

        async def input_endpoint(request: Any) -> Any:
            session, cookie = self._session_for_request(request)
            target_id = request.path_params["target_id"]
            form = await request.form()
            session.dispatch_input(target_id, str(form.get("value", "")))
            return _with_cookie(Response(status_code=204), cookie)

        routes: list[Any] = [
            Route("/", endpoint=index),
            Route(
                "/xnano/click/{target_id}",
                endpoint=click_endpoint,
                methods=["POST"],
            ),
            Route("/xnano/key", endpoint=key_endpoint, methods=["POST"]),
            Route("/xnano/tick", endpoint=tick_endpoint, methods=["POST"]),
            Route(
                "/xnano/input/{target_id}",
                endpoint=input_endpoint,
                methods=["POST"],
            ),
        ]

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
                    session, cookie = self._session_for_request(request)
                    body = session.dispatch_request(http_method, request_path)
                    return self._response_for_session(
                        session,
                        body,
                        request=request,
                        cookie=cookie,
                        HTMLResponse=HTMLResponse,
                        # POST is almost always an htmx swap target.
                        full_page=(None if http_method == "GET" else False),
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
            grid: A BaseGrid instance (shared) or callable factory
                (per-visitor sessions).
            host: The host to bind to.
            port: The port to bind to.
        """
        app = self.build_app(grid)

        try:
            import uvicorn
        except ImportError as error:
            raise ExtraNotInstalledError("web") from error

        uvicorn.run(app, host=host, port=port)


__all__ = ("Web",)
