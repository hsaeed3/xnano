"""xnano.web.web

---

``Web`` host: the browser analogue of ``Terminal``. Runs a grid on the
dependency-free native server (``xnano.web.server``), streaming rendered
terminal cells to a ``<canvas>`` client and routing browser events back
through the same ``@on_*`` hook engine the terminal loop uses.

Every component renders on web exactly as it does in the terminal —
there is no separate web renderer — because the server drives the real
offscreen render engine and streams its cells.

``@on_*_request`` routes (every HTTP method) are served by the same
server; host/port configure where it binds.
"""

from __future__ import annotations

from typing import Any, Callable

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000


def _grid_factory(source: Any) -> tuple[Callable[[], Any], bool, type | None]:
    """Return ``(factory, shared, grid_class)`` for a grid source.

    A ``BaseGrid`` *instance* is shared across visitors; a ``BaseGrid``
    *subclass* (or callable factory) makes a fresh grid per session.
    """
    from xnano.grid import BaseGrid

    if isinstance(source, type) and issubclass(source, BaseGrid):
        return source, False, source
    if isinstance(source, BaseGrid):
        return (lambda: source), True, type(source)
    if callable(source):
        return source, False, None
    raise TypeError(
        "Web.run() expects a BaseGrid instance, subclass, or factory"
    )


class Web:
    """Web host for xnano grids — the browser analogue of ``Terminal``.

    Pass a ``BaseGrid`` instance for one shared grid across all visitors,
    or the ``BaseGrid`` subclass itself for a fresh grid per session:

        Web(title="dashboard").run(Dashboard())     # shared
        Web(title="per-user app").run(Dashboard)    # session-per-visitor

    The same grid, fields, and ``@on_*`` hooks that run under
    ``Terminal`` run here — the browser shows the identical render.
    """

    def __init__(self, *, state: Any = None, title: str | None = None) -> None:
        self.state = state
        self.title = title or "xnano"

    def run(
        self,
        source: Any,
        *,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
    ) -> None:
        """Serve ``source`` in the browser until interrupted.

        Args:
            source: A ``BaseGrid`` instance (shared) or subclass/factory
                (per-session).
            host: Interface to bind.
            port: Port to bind.
        """
        from xnano.web.server import serve_native

        factory, shared, grid_class = _grid_factory(source)
        serve_native(
            factory,
            shared=shared,
            state=self.state,
            title=self.title,
            host=host,
            port=port,
            grid_class=grid_class,
        )


__all__ = ("Web",)
