"""xnano.beta.server.requests

---

Serve beta ``@on_*_request`` hooks with the standard library HTTP server.
"""

from __future__ import annotations

import http.server
import threading
import urllib.parse
from typing import Any

from xnano.beta.requests import Request, Response, dispatch_request

_MAX_REQUEST_BODY = 1_048_576


class RequestServer(http.server.ThreadingHTTPServer):
    """Serve request hooks declared by one grid.

    Attributes:
        grid: Grid instance whose request hooks are served.
        runtime: Runtime exposed to request hook contexts, if supplied.

    Example:
        >>> server = RequestServer(("127.0.0.1", 0), object())
        >>> server.server_address[1] > 0
        True
        >>> server.server_close()
    """

    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        grid: Any,
        *,
        runtime: Any | None = None,
    ) -> None:
        self.grid = grid() if isinstance(grid, type) else grid
        self.runtime = runtime if runtime is not None else self.grid
        super().__init__(address, _RequestHandler)


class _RequestHandler(http.server.BaseHTTPRequestHandler):
    """Translate HTTP requests into beta request-hook dispatch."""

    server: RequestServer

    def _dispatch_request(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if length > _MAX_REQUEST_BODY:
            self.send_error(413, "Request body too large")
            return
        body = self.rfile.read(length) if length else b""
        request = Request.from_parts(
            self.command,
            parsed.path,
            query_string=parsed.query,
            headers=dict(self.headers.items()),
            body=body,
        )
        response = dispatch_request(
            self.server.grid,
            self.command,
            parsed.path,
            request_obj=request,
            runtime=self.server.runtime,
        )
        if isinstance(response, bool):
            response = (
                Response()
                if response
                else Response(
                    status=404,
                    body="Not Found",
                )
            )
        payload = response.as_bytes()
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        if "content-type" not in {name.lower() for name in response.headers}:
            self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    do_CONNECT = _dispatch_request
    do_DELETE = _dispatch_request
    do_GET = _dispatch_request
    do_HEAD = _dispatch_request
    do_OPTIONS = _dispatch_request
    do_PATCH = _dispatch_request
    do_POST = _dispatch_request
    do_PUT = _dispatch_request
    do_QUERY = _dispatch_request
    do_TRACE = _dispatch_request

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stderr access logging."""


def start_request_server(
    grid: Any,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    runtime: Any | None = None,
) -> RequestServer:
    """Start request-hook serving on a daemon thread.

    Args:
        grid: Grid instance or class declaring request hooks.
        host: Bind address.
        port: Bind port. Use ``0`` to select a free port.
        runtime: Runtime exposed to request-hook contexts.

    Returns:
        Running server. Call ``shutdown`` and ``server_close`` to stop it.
    """
    server = RequestServer((host, port), grid, runtime=runtime)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


serve_requests = start_request_server

__all__ = ("RequestServer", "serve_requests", "start_request_server")
