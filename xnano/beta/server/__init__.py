"""xnano.beta.server

---

Serve browser applications and standalone grid request hooks.
"""

from xnano.beta.server.native import NativeWebServer, serve_native
from xnano.beta.server.requests import (
    RequestServer,
    serve_requests,
    start_request_server,
)

__all__ = (
    "NativeWebServer",
    "RequestServer",
    "serve_requests",
    "serve_native",
    "start_request_server",
)
