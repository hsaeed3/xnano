"""xnano.requests

---

Barrel re-export of every HTTP request hook decorator from
``xnano.web.requests`` (``@on_get_request``, ``@on_post_request``,
``@on_put_request``, ``@on_delete_request``, …) plus a ``Requests``
convenience class mirroring the ``Hooks`` pattern.
"""

from __future__ import annotations

from xnano.web.requests import (
    on_connect_request,
    on_delete_request,
    on_get_request,
    on_head_request,
    on_options_request,
    on_patch_request,
    on_post_request,
    on_put_request,
    on_query_request,
    on_trace_request,
)


class Requests:
    """Convenience class for accessing HTTP request handler decorators."""

    on_connect_request = on_connect_request
    on_delete_request = on_delete_request
    on_get_request = on_get_request
    on_head_request = on_head_request
    on_options_request = on_options_request
    on_patch_request = on_patch_request
    on_post_request = on_post_request
    on_put_request = on_put_request
    on_query_request = on_query_request
    on_trace_request = on_trace_request


__all__ = (
    "Requests",
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