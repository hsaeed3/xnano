"""xnano.web.server

---

Dependency-free web host: a stdlib ``ThreadingHTTPServer`` that serves a
``<canvas>`` shell + painter, streams rendered terminal cells over
Server-Sent Events, and routes browser key/mouse/resize events back
through the same ``xnano._dispatch`` engine the live terminal uses.

No third-party dependency is required — request-hook routes are served
here too. ``xnano[requests]`` (Starlette + uvicorn) is an optional
production-serving upgrade (see ``xnano.web.web``).
"""

from __future__ import annotations

import concurrent.futures
import contextlib
import http.server
import json
import queue
import secrets
import threading
import urllib.parse
from typing import Any, Callable, Iterator

from xnano.web.render import WebRenderer

_PAINTER_JS_PATH = "static/painter.js"
_TICK_INTERVAL_SECONDS = 0.1

_MOUSE_KINDS = frozenset(
    {"press", "release", "drag", "move", "scroll_up", "scroll_down"}
)
_MOUSE_BUTTONS = frozenset({"left", "right", "middle"})


def _read_painter_js() -> bytes:
    import importlib.resources

    return (
        importlib.resources.files("xnano.web")
        .joinpath(_PAINTER_JS_PATH)
        .read_bytes()
    )


def _shell_html(title: str) -> bytes:
    import html

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>html,body{margin:0;padding:0;overflow:hidden;"
        "background:#101010}canvas{display:block}</style></head>"
        "<body><canvas id='xnano'></canvas>"
        "<script src='/xnano/painter.js'></script></body></html>"
    ).encode("utf-8")


@contextlib.contextmanager
def _bind_active(terminal: Any) -> Iterator[None]:
    """Bind the active-terminal/host contextvars for one operation.

    Sessions live across threads (an SSE thread renders; event POSTs
    arrive on other threads), so any code reading the active host/
    terminal contextvar must see this session's terminal.
    """
    from xnano.core.hosts import _ACTIVE_HOST
    from xnano.terminal.terminal import _ACTIVE_TERMINAL

    terminal_token = _ACTIVE_TERMINAL.set(terminal)
    host_token = _ACTIVE_HOST.set(terminal)
    try:
        yield
    finally:
        _ACTIVE_TERMINAL.reset(terminal_token)
        _ACTIVE_HOST.reset(host_token)


class _Session:
    """One visitor, pinned to a single worker thread.

    ``CoreSession`` is PyO3-``unsendable`` — it must only ever be
    touched from the thread that created it. Since a threading HTTP
    server serves each request on a different thread, all session work
    (create, render, event, tick, resize) is funneled onto one dedicated
    worker thread; I/O threads submit callables and await the result.
    """

    def __init__(self, grid: Any, cols: int, state: Any, title: str | None):
        self.dirty = threading.Event()
        self._grid = grid
        self._cols = cols
        self._state = state
        self._title = title
        self._tasks: queue.Queue[
            tuple[Callable[[], Any], concurrent.futures.Future] | None
        ] = queue.Queue()
        # Created and only ever touched on the worker thread; typed Any
        # because callers submit lambdas that run after it is set.
        self.renderer: Any = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self.renderer = WebRenderer(
            self._grid,
            cols=self._cols,
            rows=24,
            state=self._state,
            title=self._title,
        )
        # The worker thread exclusively owns this session, so bind the
        # active-terminal contextvars once for its whole lifetime.
        with _bind_active(self.renderer.terminal):
            while True:
                item = self._tasks.get()
                if item is None:
                    return
                fn, future = item
                if future.set_running_or_notify_cancel():
                    try:
                        future.set_result(fn())
                    except Exception as error:  # surface to caller
                        future.set_exception(error)

    def _submit(self, fn: Callable[[], Any]) -> Any:
        future: concurrent.futures.Future = concurrent.futures.Future()
        self._tasks.put((fn, future))
        return future.result()

    def frame(self) -> dict[str, Any]:
        return self._submit(lambda: self.renderer.frame())

    def tick(self) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            self.renderer.terminal._pump_tick()
            return self.renderer.frame()

        return self._submit(run)

    def apply_event(self, payload: dict[str, Any]) -> None:
        self._submit(
            lambda: _dispatch_browser_event(self.renderer.terminal, payload)
        )
        self.dirty.set()

    def resize(self, cols: int, rows: int) -> None:
        self._submit(lambda: self.renderer.resize(cols, rows))
        self.dirty.set()

    def request(self, method: str, path: str) -> bool:
        from xnano.web.requests import dispatch_request

        matched = self._submit(
            lambda: dispatch_request(self.renderer.grid, method, path)
        )
        self.dirty.set()
        return bool(matched)

    def close(self) -> None:
        self._submit(lambda: self.renderer.close())
        self._tasks.put(None)


def _dispatch_browser_event(terminal: Any, payload: dict[str, Any]) -> None:
    """Turn a browser event payload into an xnano event + dispatch it."""
    from xnano._dispatch import dispatch_hooks
    from xnano.context import Context
    from xnano.events import Event, KeyboardEventData, MouseEventData

    kind = payload.get("type")
    if kind == "key":
        keyboard = KeyboardEventData.from_binding(
            str(payload.get("binding", "")),
            character=payload.get("char"),
        )
        event = Event.from_data(keyboard)
    elif kind == "mouse":
        mouse_kind = payload.get("kind", "press")
        button = payload.get("button", "left")
        mouse = MouseEventData(
            kind=mouse_kind if mouse_kind in _MOUSE_KINDS else "press",
            x=int(payload.get("x", 0)),
            y=int(payload.get("y", 0)),
            button=button if button in _MOUSE_BUTTONS else "left",
        )
        event = Event.from_data(mouse)
    else:
        return
    ctx = Context(event=event, terminal=terminal, state=terminal.state)
    dispatch_hooks(terminal, ctx)


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # silence log
        pass

    @property
    def _server(self) -> "NativeWebServer":
        from typing import cast

        return cast("NativeWebServer", self.server)

    def _session_id(self) -> str:
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "xnano-session" and value:
                return value
        return ""

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._serve_shell()
        elif parsed.path == "/xnano/painter.js":
            self._serve_bytes(_read_painter_js(), "application/javascript")
        elif parsed.path == "/xnano/stream":
            self._serve_stream(urllib.parse.parse_qs(parsed.query))
        elif ("GET", parsed.path) in self._server.request_routes:
            self._serve_request("GET", parsed.path)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/xnano/event":
            self._serve_event()
        elif ("POST", parsed.path) in self._server.request_routes:
            self._serve_request("POST", parsed.path)
        else:
            self.send_error(404)

    def _serve_event(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self.send_error(400)
            return
        session = self._server.session_for(self._session_id())
        if payload.get("type") == "resize":
            session.resize(
                int(payload.get("cols", 80)), int(payload.get("rows", 24))
            )
        else:
            session.apply_event(payload)
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _serve_request(self, method: str, path: str) -> None:
        session = self._server.session_for(self._session_id())
        session.request(method, path)
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _serve_shell(self) -> None:
        body = _shell_html(self._server.title)
        session_id = self._session_id() or secrets.token_hex(16)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Set-Cookie", f"xnano-session={session_id}; Path=/; HttpOnly"
        )
        self.end_headers()
        self.wfile.write(body)

    def _serve_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_stream(self, query: dict[str, list[str]]) -> None:
        session = self._server.session_for(self._session_id())
        cols = int(query.get("cols", ["80"])[0])
        rows = int(query.get("rows", ["24"])[0])
        session.resize(cols, rows)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            self._send_frame(session.frame())
            while not self._server.stopped:
                fired = session.dirty.wait(_TICK_INTERVAL_SECONDS)
                session.dirty.clear()
                frame = session.frame() if fired else session.tick()
                if frame["full"] or frame["rows"]:
                    self._send_frame(frame)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_frame(self, frame: dict[str, Any]) -> None:
        data = json.dumps(frame, separators=(",", ":"))
        self.wfile.write(b"data: " + data.encode("utf-8") + b"\n\n")
        self.wfile.flush()


class NativeWebServer(http.server.ThreadingHTTPServer):
    """Threading HTTP server holding the session registry + grid factory."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        grid_factory: Callable[[], Any],
        shared: bool,
        state: Any,
        title: str,
        grid_class: type | None = None,
    ) -> None:
        super().__init__(address, _Handler)
        self._grid_factory = grid_factory
        self._shared = shared
        self._state = state
        self.title = title
        self._sessions: dict[str, _Session] = {}
        self._sessions_lock = threading.Lock()
        self.stopped = False
        self.request_routes: set[tuple[str, str]] = set()
        if grid_class is not None:
            from xnano.web.requests import collect_request_routes

            self.request_routes = {
                (entry["method"], entry["path"])
                for entry in collect_request_routes(grid_class)
            }

    def session_for(self, session_id: str) -> _Session:
        key = "shared" if self._shared else (session_id or "default")
        with self._sessions_lock:
            session = self._sessions.get(key)
            if session is None:
                session = _Session(
                    self._grid_factory(),
                    cols=80,
                    state=self._state,
                    title=self.title,
                )
                self._sessions[key] = session
            return session

    def shutdown_all(self) -> None:
        self.stopped = True
        with self._sessions_lock:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()


def serve_native(
    grid_factory: Callable[[], Any],
    *,
    shared: bool,
    state: Any,
    title: str,
    host: str,
    port: int,
    grid_class: type | None = None,
) -> None:
    """Run the native stdlib web host until interrupted."""
    server = NativeWebServer(
        (host, port),
        grid_factory=grid_factory,
        shared=shared,
        state=state,
        title=title,
        grid_class=grid_class,
    )
    print(f"xnano web → http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown_all()
        server.server_close()


__all__ = ("NativeWebServer", "serve_native")
