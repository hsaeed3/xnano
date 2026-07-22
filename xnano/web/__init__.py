"""xnano.web

---

Web host for xnano grids — the browser analogue of ``Terminal``.

Renders a grid to HTML via flexbox + htmx, owns per-visitor or shared
sessions, and dispatches browser events into the same ``@on_*`` hook
paths the terminal loop uses. Custom HTTP routes are declared with
``@on_get_request`` / ``@on_post_request`` from ``xnano.web.requests``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.core.controllers.webui import WebController
    from xnano.web.session import WebSession
    from xnano.web.web import Web

__all__ = (
    "Web",
    "WebController",
    "WebSession",
)


def __getattr__(name: str):
    if name == "Web":
        from xnano.web.web import Web

        return Web
    if name == "WebSession":
        from xnano.web.session import WebSession

        return WebSession
    if name == "WebController":
        from xnano.core.controllers.webui import WebController

        return WebController
    raise AttributeError(f"module 'xnano.web' has no attribute {name!r}")
