"""xnano.web.request_server

---

A tiny stdlib HTTP server that exposes a grid's ``@on_*_request`` routes
(every registered HTTP method) alongside a running ``Terminal``. This is
what makes requests a cross-host capability: the same decorators that do
nothing extra on their own become live HTTP endpoints when the grid is
run with a host/port.

Request handlers mutate grid state directly; the terminal's continuous
render loop reflects the change on its next frame (no signaling needed).
Handlers should only mutate state — driving rendering or terminal I/O
from the server thread is out of scope.
"""

from __future__ import annotations

import functools
import http.server
import threading
import urllib.parse
from typing import Any

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000


class _RequestServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, address: tuple[str, int], *, grid: Any, routes: set
    ) -> None:
        super().__init__(address, _RequestHandler)
        self.grid = grid
        self.routes = routes


class _RequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # silence log
        pass

    def _handle(self, method: str) -> None:
        from xnano.web.requests import dispatch_request

        server: Any = self.server
        path = urllib.parse.urlparse(self.path).path
        # Drain any request body so keep-alive connections stay in sync.
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)
        if (method, path) not in server.routes:
            self.send_error(404)
            return
        matched = dispatch_request(server.grid, method, path)
        self.send_response(200 if matched else 404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_GET = functools.partialmethod(_handle, "GET")
    do_HEAD = functools.partialmethod(_handle, "HEAD")
    do_POST = functools.partialmethod(_handle, "POST")
    do_PUT = functools.partialmethod(_handle, "PUT")
    do_DELETE = functools.partialmethod(_handle, "DELETE")
    do_CONNECT = functools.partialmethod(_handle, "CONNECT")
    do_OPTIONS = functools.partialmethod(_handle, "OPTIONS")
    do_TRACE = functools.partialmethod(_handle, "TRACE")
    do_PATCH = functools.partialmethod(_handle, "PATCH")
    do_QUERY = functools.partialmethod(_handle, "QUERY")


def start_request_server(
    grid: Any,
    *,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
) -> _RequestServer | None:
    """Serve ``grid``'s request routes in a background thread.

    Returns the server (call ``.shutdown()`` to stop) or ``None`` when
    the grid declares no request hooks.
    """
    from xnano.web.requests import collect_request_routes

    routes = {
        (entry["method"], entry["path"])
        for entry in collect_request_routes(type(grid))
    }
    if not routes:
        return None
    server = _RequestServer((host, port), grid=grid, routes=routes)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


__all__ = ("start_request_server",)
