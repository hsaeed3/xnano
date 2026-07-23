"""xnano.beta.web

---

Serve beta grids and components through an offscreen native cell runtime.
"""

from __future__ import annotations

from typing import Any, Callable


def grid_factory(source: Any) -> tuple[Callable[[], Any], bool, type | None]:
    """Normalize a grid instance, class, or callable into a factory.

    Args:
        source: Root grid instance, grid class, or factory.

    Returns:
        Factory, whether the source is shared, and its grid class.

    Raises:
        TypeError: If ``source`` cannot produce a beta grid or component.
    """
    from xnano.beta.grids import BaseGrid

    if isinstance(source, type) and issubclass(source, BaseGrid):
        return source, False, source
    if isinstance(source, BaseGrid):
        return (lambda: source), True, type(source)
    if callable(source):
        return source, False, None
    if getattr(type(source), "_xnano_component_base", False):
        return (lambda: source), True, None
    raise TypeError(
        "Web.run() expects a grid/component instance, class, or factory"
    )


class Web:
    """Serve an application in a browser from an offscreen runtime.

    Attributes:
        state: Application state shared with event and request hooks.
        title: Browser document title.
        width: Offscreen viewport width in cells.
        height: Offscreen viewport height in cells.
        surface: Presentation surface name.

    Example:
        >>> from xnano.beta.components import Text
        >>> web = Web(title="Status")
        >>> # web.run(Text("Ready"), host="127.0.0.1", port=8000)
    """

    def __init__(
        self,
        *,
        state: Any = None,
        title: str | None = None,
        width: int = 80,
        height: int = 24,
    ) -> None:
        self.state = state
        """Application state passed to the offscreen runtime."""
        self.title = title or "xnano"
        """Browser document title."""
        self.width = width
        """Offscreen viewport width in cells."""
        self.height = height
        """Offscreen viewport height in cells."""
        self.surface = "web"
        """Presentation surface name."""
        self._server: Any | None = None

    def run(
        self,
        source: Any,
        *,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        """Serve an application until interrupted.

        Args:
            source: Grid/component instance, class, or factory.
            host: Bind address.
            port: Bind port.
        """
        from xnano.beta.server.native import serve_native

        factory, _, _ = grid_factory(source)
        serve_native(
            factory,
            state=self.state,
            title=self.title,
            host=host,
            port=port,
            width=self.width,
            height=self.height,
        )

    def close(self) -> None:
        """Stop a managed server when one has been attached."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


__all__ = ("Web", "grid_factory")
