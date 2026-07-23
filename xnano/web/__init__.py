"""xnano.web

---

Web host for xnano grids — the browser analogue of ``Terminal``.

Runs a grid on a dependency-free native server that streams the real
render engine's terminal cells to a ``<canvas>`` client and routes
browser events back through the same ``@on_*`` hook paths the terminal
loop uses, so every component renders on web identically to the
terminal. Custom HTTP routes are declared with ``@on_*_request``
decorators from ``xnano.web.requests`` (every HTTP method).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.web.web import Web

__all__ = ("Web",)


def __getattr__(name: str):
    if name == "Web":
        from xnano.web.web import Web

        return Web
    raise AttributeError(f"module 'xnano.web' has no attribute {name!r}")
