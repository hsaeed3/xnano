"""xnano.beta.terminal"""

from __future__ import annotations

import contextvars
from typing import Any, Callable, Generic, TypeVar

from xnano_core.core import CoreSession

from xnano.beta.context import Context
from xnano.beta.exceptions import Exit
from xnano.beta.utils.native_types import get_area_from_native_rect
from xnano.beta.hooks import (
    _EventHooksRegistry,
    _OnKeyboardHookFunctionEntry,
    _OnMouseHookFunctionEntry,
    _OnStateHookFunctionEntry,
    _OnTickHookFunctionEntry,
)
from xnano.beta.core.session import Session
from xnano.beta.core import dispatch as _dispatch
from xnano.beta.events import Event
from xnano.beta.grid import Grid, _GridSlideCapture
from xnano.beta.types import Area, Coordinate


StateT = TypeVar("StateT")


_ACTIVE_TERMINAL: contextvars.ContextVar["Terminal[Any] | None"] = (
    contextvars.ContextVar("_ACTIVE_TERMINAL", default=None)
)


def exit_terminal() -> None:
    """Request an exit to the current terminal session.

    Raises:
        Exit: If the terminal session is not live.
    """
    if _ACTIVE_TERMINAL.get() is None:
        raise Exit("Terminal is not live.")


class Terminal(Generic[StateT]):
    """The active terminal screen / session.

    ``Terminal`` owns the ``CoreSession`` lifecycle, binds the context variable,
    drains events, and dispatches hooks.  Use as a context manager or call
    :meth:`run` directly with a root :class:`~xnano.grid.abstract.Grid`.

    Attributes:
        title: Optional window title set on session entry.
        mouse_events: Enable mouse event delivery.
        bracketed_paste: Enable bracketed paste sequences.
        synchronized_updates: Enable synchronized output on supported hosts.
        tick_interval: Minimum time between ticks, in milliseconds.
        state: User state threaded into every :class:`~xnano.context.Context`.
    """

    __slots__ = (
        "_session",
        "_terminal_token",
        "_context_token",
        "_hooks",
        "_renderable_overlays",
        "_is_live",
        "_has_context",
        "_attached_grids",
        "_attached_grid_classes",
        "_attached_frame_grids",
        "_field_hits",
        "_mouse_geometry_active",
        "_slide_capture",
        "_default_hooks_registered",
        "_exit_requested",
        "_tick_last_ms",
        "_cursor",
        "_device",
        "title",
        "mouse_events",
        "bracketed_paste",
        "synchronized_updates",
        "tick_interval",
        "state",
    )

    def __init__(
        self,
        *,
        state: StateT | None = None,
        title: str | None = None,
        mouse_events: bool = False,
        bracketed_paste: bool = False,
        synchronized_updates: bool = False,
        tick_interval: int = 16,
    ) -> None:
        self.state: StateT | None = state
        self.title = title
        self.mouse_events = mouse_events
        self.bracketed_paste = bracketed_paste
        self.synchronized_updates = synchronized_updates
        self.tick_interval = tick_interval

        self._session: Session[StateT] | None = None
        self._terminal_token: Any = None
        self._context_token: Any = None
        self._hooks: _EventHooksRegistry = _EventHooksRegistry()
        self._renderable_overlays: list[tuple[Any, int]] = []
        self._is_live: bool = False
        self._has_context: bool = False
        self._attached_grids: set[int] = set()
        self._attached_grid_classes: set[type] = set()
        self._attached_frame_grids: list[Any] = []
        self._field_hits: list[Any] = []
        self._mouse_geometry_active: bool = False
        self._slide_capture: Any = None
        self._default_hooks_registered: bool = False
        self._exit_requested: bool = False
        self._tick_last_ms: float = 0.0
        self._cursor: Any = None
        self._device: Any = None

    def __enter__(self) -> "Terminal[StateT]":
        if self._is_live:
            return self
        core = CoreSession.init(tick_rate_ms=None)
        if self.title is not None:
            core.set_title(self.title)
        if self.mouse_events:
            core.enable_mouse_capture()
        if self.bracketed_paste:
            core.enable_bracketed_paste()
        if self.synchronized_updates:
            core.begin_synchronized_update()
        self._session = Session(core)
        self._terminal_token = _ACTIVE_TERMINAL.set(self)
        self._is_live = True
        self._drain_pending_hooks()
        self._register_default_hooks()
        return self

    def __exit__(self, *exc: Any) -> None:
        if not self._is_live:
            return
        try:
            if self._session is not None:
                if self.mouse_events:
                    try:
                        self._session._core_session.disable_mouse_capture()
                    except OSError:
                        pass
                if self.bracketed_paste:
                    try:
                        self._session._core_session.disable_bracketed_paste()
                    except OSError:
                        pass
                self._session.leave()
        finally:
            if self._terminal_token is not None:
                _ACTIVE_TERMINAL.reset(self._terminal_token)
                self._terminal_token = None
            self._session = None
            self._is_live = False
            self._exit_requested = False

    def _render_frame(self, root: Any) -> None:
        _dispatch.render_frame(self, root)

    def _pump_events(self) -> None:
        _dispatch.pump_events(self)

    def _pump_tick(self) -> None:
        _dispatch.pump_tick(self)

    def _dispatch_hooks(self, ctx: "Context[Any]") -> None:
        _dispatch.dispatch_hooks(self, ctx)

    def _dispatch_field_mouse(self, ctx: "Context[Any]") -> None:
        _dispatch.dispatch_field_mouse(self, ctx)

    def _update_slide_capture(self, capture: Any, mouse: Any) -> None:
        _dispatch.update_slide_capture(self, capture, mouse)

    @staticmethod
    def _field_mouse_handler_matches(handler: Any, mouse: Any) -> bool:
        return _dispatch.field_mouse_handler_matches(handler, mouse)

    @staticmethod
    def _keyboard_matches(
        kbd: Any, entry: "_OnKeyboardHookFunctionEntry"
    ) -> bool:
        return _dispatch.keyboard_matches(kbd, entry)

    @staticmethod
    def _mouse_matches(mouse: Any, entry: "_OnMouseHookFunctionEntry") -> bool:
        return _dispatch.mouse_matches(mouse, entry)

    def _resolve_hook_grid(self, handler: Any) -> Any | None:
        return _dispatch.resolve_hook_grid(self, handler)

    def _track_frame_grid(self, grid: Grid[StateT]) -> None:
        _dispatch.track_frame_grid(self, grid)

    def _merge_hooks(
        self, other: _EventHooksRegistry, grid: Grid | None = None
    ) -> None:
        _dispatch.merge_hooks(self, other, grid=grid)

    def _drain_pending_hooks(self) -> None:
        _dispatch.drain_pending_hooks(self)

    def _register_default_hooks(self) -> None:
        _dispatch.register_default_hooks(self)

    @classmethod
    def offscreen(
        cls,
        *,
        cols: int = 40,
        rows: int = 12,
        state: StateT | None = None,
        title: str | None = None,
    ) -> "Terminal[StateT]":
        """Return a terminal backed by an offscreen (test) buffer."""
        terminal: Terminal[StateT] = cls(title=title, state=state)
        terminal._session = Session(
            CoreSession.offscreen(width=cols, height=rows),
            terminal_width=cols,
            terminal_height=rows,
            is_offscreen=True,
        )
        terminal._terminal_token = _ACTIVE_TERMINAL.set(terminal)
        terminal._is_live = True
        terminal._drain_pending_hooks()
        terminal._register_default_hooks()
        return terminal

    def attach_grid(self, grid: Any) -> None:
        """Register a grid's method-level hooks against this terminal."""
        self._track_frame_grid(grid)

    def request_exit(self) -> None:
        self._exit_requested = True

    def get_output(self) -> str:
        """Return the offscreen buffer text (only valid for offscreen sessions)."""
        return self.session.get_core_session_output_text()

    def run(self, grid: Any) -> None:
        """Enter the terminal, render ``grid`` each frame, and loop until exit.

        Can be called without using the context manager — it auto-enters and
        auto-exits.
        """
        auto_entered = not self._is_live
        if auto_entered:
            self.__enter__()
        self._exit_requested = False
        self._track_frame_grid(grid)
        try:
            while not self._exit_requested:
                self._render_frame(grid)
                self._pump_events()
                self._pump_tick()
        except (KeyboardInterrupt, Exit):
            pass
        finally:
            if auto_entered:
                self.__exit__()

    @property
    def session(self) -> "Session[StateT]":
        if self._session is None:
            raise RuntimeError(
                "Terminal is not entered — call __enter__ or run() first."
            )
        return self._session

    @property
    def size(self) -> tuple[int, int]:
        """Return ``(width, height)`` of the current terminal viewport."""
        rect = self.session.get_native_viewport_area()
        return (rect.width, rect.height)

    @property
    def cursor(self) -> Any:
        """Live cursor controller for this terminal session."""
        if self._cursor is None:
            from xnano.beta.cursor import Cursor

            self._cursor = Cursor(self)
        return self._cursor

    @property
    def device(self) -> Any:
        """Live device controller for this terminal session."""
        if self._device is None:
            from xnano.beta.device import Device

            self._device = Device(self)
        return self._device


__all__ = ("exit", "Terminal")
