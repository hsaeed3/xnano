"""xnano.web.render

---

Shared "render a grid to cells" seam for the web host.

A ``WebRenderer`` drives a buffer-backed offscreen ``Terminal`` — the
same layout/render engine the live TUI uses — and reads its cells back
as wire frames for the browser painter. Because it is the real engine,
every component renders on web identically to the terminal.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from xnano.web.frame import Row, build_frame, serialize_rows

StateT = TypeVar("StateT")


class WebRenderer(Generic[StateT]):
    """Owns an offscreen ``Terminal`` and produces cell frames for a grid.

    The grid, hooks, and event dispatch are identical to the terminal
    host; only the destination differs (an offscreen buffer whose cells
    are streamed to the browser instead of a live terminal).
    """

    def __init__(
        self,
        grid: Any,
        *,
        cols: int = 80,
        rows: int = 24,
        state: StateT | None = None,
        title: str | None = None,
    ) -> None:
        from xnano.terminal.terminal import Terminal

        self._grid = grid
        self._cols = cols
        self._rows = rows
        self._previous: tuple[Row, ...] | None = None
        self._previous_title: str | None = None
        self._terminal: Any = Terminal.offscreen(
            cols=cols, rows=rows, state=state, title=title
        )

    @property
    def terminal(self) -> Any:
        """The underlying offscreen terminal (for event dispatch)."""
        return self._terminal

    @property
    def grid(self) -> Any:
        """The grid being rendered (for request-hook dispatch)."""
        return self._grid

    @property
    def size(self) -> tuple[int, int]:
        return (self._cols, self._rows)

    def resize(self, cols: int, rows: int) -> None:
        """Resize the offscreen viewport; forces a full next frame."""
        if (cols, rows) == (self._cols, self._rows):
            return
        from xnano.terminal.terminal import Terminal

        state = getattr(self._terminal, "state", None)
        title = getattr(self._terminal, "title", None)
        self.close()
        self._cols = max(1, cols)
        self._rows = max(1, rows)
        self._previous = None
        self._previous_title = None
        self._terminal = Terminal.offscreen(
            cols=self._cols, rows=self._rows, state=state, title=title
        )

    def _render_rows(self) -> tuple[Row, ...]:
        from xnano.grid import BaseGrid

        root = self._grid if isinstance(self._grid, BaseGrid) else None
        renderables = None if root is not None else (self._grid,)
        self._terminal._render_frame(root, renderables=renderables)
        buffer = self._terminal.session._core_session.buffer_snapshot()
        return serialize_rows(buffer)

    def frame(self) -> dict[str, Any]:
        """Render one frame and return the wire dict (row-diffed).

        ``ctx.cursor``/``ctx.device`` work identically to the terminal
        host (see ``TerminalCursor``/``TerminalDevice``) — a hook that
        moves or shows/hides the cursor here is reflected in the browser
        canvas exactly as it would move the real terminal caret.
        """
        rows = self._render_rows()
        cursor_state = self._terminal.cursor
        cursor = cursor_state.get_position() if cursor_state.visible else None
        frame = build_frame(
            rows,
            width=self._cols,
            height=self._rows,
            cursor=cursor,
            previous=self._previous,
        )
        title = self._terminal.device.title
        if title is not None and title != self._previous_title:
            frame["title"] = title
            self._previous_title = title
        self._previous = rows
        return frame

    def close(self) -> None:
        """Tear down the offscreen terminal."""
        terminal = getattr(self, "_terminal", None)
        if terminal is not None:
            try:
                terminal.__exit__(None, None, None)
            except Exception:
                pass


__all__ = ("WebRenderer",)
