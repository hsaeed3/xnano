"""
xnano.deprecated.server

---

Serve browser applications and standalone grid request hooks.
"""

from xnano.deprecated.server.native import NativeWebServer, serve_native
from xnano.deprecated.server.requests import (
    RequestServer,
    serve_requests,
    start_request_server,
)

__all__ = (
    'NativeWebServer',
    'RequestServer',
    'serve_native',
    'serve_requests',
    'start_request_server',
)
