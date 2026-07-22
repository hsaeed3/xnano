"""xnano.terminal.terminal

---

``Terminal`` host: session lifecycle, run loop, viewport sizing, and
hook dispatch for interactive TUI apps.
"""

from __future__ import annotations

import atexit
import contextvars
import dataclasses
import signal
import sys
import warnings
from typing import IO, TYPE_CHECKING, Any, Generic, Sequence, TextIO, TypeVar

if TYPE_CHECKING:
    from xnano._types import (
        Alignment,
        Border,
        CharacterModifier,
        Direction,
        FrameTitlePosition,
        PaddingLike,
        Side,
        Sizing,
        SizingLike,
    )
    from xnano.color import ColorLike

from xnano import _dispatch
from xnano._function_hooks import (
    _EventHooksRegistry,
    _OnKeyboardHookFunctionEntry,
    _OnMouseHookFunctionEntry,
)
from xnano.context import Context
from xnano.core.exceptions import Exit
from xnano.core.hosts import AbstractHost
from xnano.grid import BaseGrid

if TYPE_CHECKING:
    from xnano.core.controllers.tui import TerminalController


StateT = TypeVar("StateT")


@dataclasses.dataclass(frozen=True, slots=True)
class _ResolvedRun:
    """The viewport/root sizing resolved for a single ``run`` / ``render``.

    Returned by ``Terminal._resolve_run`` so the resolution is an explicit
    value rather than a hidden mutation. The terminal stores its fields where
    frame-time consumers read them (the inline height for session creation, the
    root width sizing for per-frame area resolution).
    """

    inline_height: int | None
    root_width_sizing: "Sizing"


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


def _atexit_restore_active_terminal() -> None:
    """Restore any still-live terminal if the process exits without ``__exit__``.

    Incomplete private-mode teardown leaves subsequent TUI apps in the same
    host terminal painting with sticky colors until cells are force-redrawn.
    """
    terminal = _ACTIVE_TERMINAL.get()
    if terminal is None or not getattr(terminal, "_is_live", False):
        return
    try:
        terminal.__exit__(None, None, None)
    except Exception:
        pass


atexit.register(_atexit_restore_active_terminal)


class Terminal(AbstractHost, Generic[StateT]):
    """The active terminal screen / session.

    ``Terminal`` owns the ``CoreSession`` lifecycle, binds the context variable,
    drains events, and dispatches hooks.  Use as a context manager or call
    the function ``Terminal.run`` directly with a root ``BaseGrid`` instance.

    The terminal is the *root box*: its own ``width`` / ``height`` sizing
    decides how the root area attaches to the physical screen.  A fill height
    (the default for a ``BaseGrid``) claims the full alternate screen, while any
    finite height (the default ``fit`` for other content) reserves an inline
    viewport in the main screen buffer.  A fixed ``width`` / ``height`` (e.g.
    ``Terminal(width=80, height=24)``) constrains the render area to that box.

    Example:
        >>> with Terminal() as terminal:
        ...     terminal.run(BaseGrid.new([
        ...         Text.new("Hello, world!"),
        ...     ]))

        **Inline, content-sized output:**

        >>> Terminal().run("Hello, world!")

        **Fixed-size box:**

        >>> Terminal(width=40, height=10).run(App())

        **With State:**

        >>> with Terminal(state=State(name="John")) as terminal:
        ...     terminal.run(BaseGrid.new([
        ...         Text.new("Hello, {terminal.state.name}!"),
        ...     ]))

    Attributes:
        title: Optional window title set on session entry.
        width: Root-box horizontal sizing (any ``Sizing`` or shorthand). When
            unset, defaults to fill for a ``BaseGrid`` and fit for other content.
        height: Root-box vertical sizing (any ``Sizing`` or shorthand). A fill
            height renders full-screen; a finite height renders inline.
        mouse_events: Enable mouse event delivery.
        bracketed_paste: Enable bracketed paste sequences.
        synchronized_updates: Enable synchronized output on supported hosts.
        tick_interval: Minimum time between ticks, in milliseconds.
        state: User state threaded into every ``Context``.
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
        "_attached_frame_grids",
        "_field_hits",
        "_mouse_geometry_active",
        "_slide_capture",
        "_default_hooks_registered",
        "_exit_requested",
        "_tick_last_ms",
        "_cursor",
        "_device",
        "_run_renderables",
        "_run_field",
        "_inline_height",
        "_pending_enter",
        "_width_sizing",
        "_height_sizing",
        "_root_width_sizing",
        "_prev_sigterm",
        "_prev_sighup",
        "_prev_sigint",
        "_field_focus",
        "_field_focus_announced",
        "_last_field_focus_event",
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
        width: SizingLike | None = None,
        height: SizingLike | None = None,
        mouse_events: bool = False,
        bracketed_paste: bool = False,
        synchronized_updates: bool = False,
        tick_interval: int = 16,
        debug_wireframe: bool = False,
    ) -> None:
        from xnano._types import Sizing

        # Host perform-queue / routes first; terminal then owns the duck
        # surface dispatch expects (``_hooks``, attached grids, state).
        AbstractHost.__init__(self)

        self.state: StateT | None = state
        self.title = title
        self.mouse_events = mouse_events
        self.bracketed_paste = bracketed_paste
        self.synchronized_updates = synchronized_updates
        self.tick_interval = tick_interval

        # The terminal is the root box: its own width/height sizing decides how
        # the root area attaches to the physical screen (see ``_resolve_run``).
        self._width_sizing: Sizing | None = Sizing.parse(width)
        self._height_sizing: Sizing | None = Sizing.parse(height)
        self._root_width_sizing: Sizing | None = None

        self._session: TerminalController[StateT] | None = None
        self._terminal_token: Any = None
        self._context_token: Any = None
        self._hooks: _EventHooksRegistry = _EventHooksRegistry()
        self._renderable_overlays: list[tuple[Any, int]] = []
        self._is_live: bool = False
        self._has_context: bool = False
        # Grids whose hooks are registered, keyed by ``id`` — the value is a
        # strong reference so the id stays unique for the terminal's life.
        self._attached_grids: dict[int, Any] = {}
        self._attached_frame_grids: list[Any] = []
        self._field_hits: list[Any] = []
        self._mouse_geometry_active: bool = False
        self._slide_capture: Any = None
        self._default_hooks_registered: bool = False
        self._exit_requested: bool = False
        self._tick_last_ms: float = 0.0
        self._cursor: Any = None
        self._device: Any = None
        self._run_renderables: tuple[Any, ...] | None = None
        if debug_wireframe:
            self.stage.wireframe(True)
        self._run_field: Any = None
        self._inline_height: int | None = None
        self._pending_enter: bool = False
        self._prev_sigterm: Any = None
        self._prev_sighup: Any = None
        self._prev_sigint: Any = None
        self._field_focus: Any = None
        self._field_focus_announced: bool = False
        self._last_field_focus_event: Any = None

    def _on_exit_signal(
        self,
        signum: int,  # noqa: ARG002
        frame: Any,  # noqa: ARG002
    ) -> None:
        # Soft-exit only: never raise from the handler. Raising KeyboardInterrupt
        # mid-restore can leave private modes / SGR half-cleared for the next
        # process sharing this terminal.
        self._exit_requested = True

    def __enter__(self) -> "Terminal[StateT]":
        if self._is_live:
            return self
        # The underlying ``CoreSession`` is created lazily on first access (see
        # ``_ensure_session``) so that ``run`` / ``render`` can decide between a
        # full-screen and an inline viewport based on the content given, even
        # when entered via the context manager.
        self._terminal_token = _ACTIVE_TERMINAL.set(self)
        self.enter_host()
        self._is_live = True
        self._pending_enter = True
        self._drain_pending_hooks()
        self._register_default_hooks()
        # Install signal handlers so SIGINT / SIGTERM / SIGHUP flow through the
        # normal exit path instead of killing the process (or raising
        # KeyboardInterrupt mid-restore) before terminal restore can finish.
        # signal.signal() is only valid on the main thread; silently skip if
        # called elsewhere.
        try:
            self._prev_sigint = signal.signal(
                signal.SIGINT, self._on_exit_signal
            )
            self._prev_sigterm = signal.signal(
                signal.SIGTERM, self._on_exit_signal
            )
            self._prev_sighup = signal.signal(
                signal.SIGHUP, self._on_exit_signal
            )
        except (OSError, ValueError):
            pass
        return self

    @staticmethod
    def _supports_live_terminal() -> bool:
        """Return whether ``xnano-core`` can claim a real terminal.

        Wasm / Pyodide wheels build without the ``terminal`` cargo feature
        and only expose buffer-backed :meth:`CoreSession.offscreen` sessions.
        Import errors propagate — a broken ``xnano_core`` install must
        surface as itself, not masquerade as a wasm build.
        """
        from xnano_core.core import CoreSession

        return bool(CoreSession.supports_live_terminal())

    def _ensure_session(self) -> None:
        """Create the deferred ``CoreSession`` if entry is still pending.

        On builds without a live terminal (wasm), opens a buffer-backed
        offscreen session sized to the resolved inline height so single-frame
        :meth:`render` still uses the real layout engine.
        """
        if not self._pending_enter:
            return
        from xnano_core.core import CoreSession

        from xnano.core.controllers.tui import TerminalController

        self._pending_enter = False

        if not CoreSession.supports_live_terminal():
            # Buffer-backed path: no crossterm, full layout solver.
            cols = 80
            rows = self._inline_height or 24
            try:
                if (
                    self._width_sizing is not None
                    and self._width_sizing.kind == "cells"
                ):
                    cols = max(1, int(self._width_sizing.value))
            except Exception:
                pass
            try:
                if (
                    self._height_sizing is not None
                    and self._height_sizing.kind == "cells"
                ):
                    rows = max(1, int(self._height_sizing.value))
            except Exception:
                pass
            core = CoreSession.offscreen(width=cols, height=rows)
            if self.title is not None:
                core.set_title(self.title)
            self._session = TerminalController(
                core,
                terminal_width=cols,
                terminal_height=rows,
                is_offscreen=True,
            )
            return

        core = CoreSession.init(
            tick_rate_ms=None, inline_height=self._inline_height
        )
        if self.title is not None:
            core.set_title(self.title)
        if self.mouse_events:
            core.enable_mouse_capture()
        if self.bracketed_paste:
            core.enable_bracketed_paste()
        if self.synchronized_updates:
            core.begin_synchronized_update()

        self._session = TerminalController(core)

    def __exit__(self, *exc: Any) -> None:
        if not self._is_live:
            return
        try:
            if self._session is not None:
                # CoreSession.restore always clears mouse / paste / sync / SGR
                # regardless of which flags this Terminal instance enabled.
                self._session.leave()
        finally:
            if self._terminal_token is not None:
                _ACTIVE_TERMINAL.reset(self._terminal_token)
                self._terminal_token = None
            self.leave_host()
            self._session = None
            self._is_live = False
            self._pending_enter = False
            self._exit_requested = False
            self._inline_height = None
            self._root_width_sizing = None
            try:
                if self._prev_sigint is not None:
                    signal.signal(signal.SIGINT, self._prev_sigint)
                    self._prev_sigint = None
                if self._prev_sigterm is not None:
                    signal.signal(signal.SIGTERM, self._prev_sigterm)
                    self._prev_sigterm = None
                if self._prev_sighup is not None:
                    signal.signal(signal.SIGHUP, self._prev_sighup)
                    self._prev_sighup = None
            except (OSError, ValueError):
                pass

    def _render_frame(
        self,
        root: Any = None,
        *,
        renderables: tuple[Any, ...] | None = None,
        field: Any = None,
    ) -> None:
        _dispatch.render_frame(
            self, root, renderables=renderables, field=field
        )

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

    def _track_frame_grid(self, grid: BaseGrid[StateT]) -> None:
        _dispatch.track_frame_grid(self, grid)

    def _merge_hooks(
        self, other: _EventHooksRegistry, grid: BaseGrid | None = None
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
        debug_wireframe: bool = False,
    ) -> "Terminal[StateT]":
        """Return a terminal backed by an offscreen (test) buffer."""
        from xnano_core.core import CoreSession

        from xnano.core.controllers.tui import TerminalController

        terminal: Terminal[StateT] = cls(
            title=title, state=state, debug_wireframe=debug_wireframe
        )
        terminal._session = TerminalController(
            CoreSession.offscreen(width=cols, height=rows),
            terminal_width=cols,
            terminal_height=rows,
            is_offscreen=True,
        )
        terminal._terminal_token = _ACTIVE_TERMINAL.set(terminal)
        terminal.enter_host()
        terminal._is_live = True
        terminal._drain_pending_hooks()
        terminal._register_default_hooks()
        return terminal

    def attach_grid(self, grid: Any) -> None:
        """Register a grid's method-level hooks against this terminal."""
        self._track_frame_grid(grid)

    def request_exit(self) -> None:
        self._exit_requested = True

    @property
    def field_focus(self) -> Any:
        """The currently focused layout field (``FieldFocus``), if any."""
        return self._field_focus

    def focus_field(self, grid: Any, field_name: str) -> bool:
        """Focus an editable ``Text`` layout field on ``grid``."""
        from xnano._types import set_field_focus

        return set_field_focus(self, grid, field_name)

    def blur_field(self) -> None:
        """Clear application field focus."""
        from xnano._types import clear_field_focus

        clear_field_focus(self)

    def focus_next(self) -> bool:
        """Move field focus to the next editable input (tab order)."""
        from xnano._types import cycle_field_focus

        return cycle_field_focus(self, reverse=False)

    def focus_previous(self) -> bool:
        """Move field focus to the previous editable input."""
        from xnano._types import cycle_field_focus

        return cycle_field_focus(self, reverse=True)

    def get_output(self) -> str:
        """Return the offscreen buffer text (only valid for offscreen sessions)."""
        return self.session.get_core_session_output_text()

    def get_output_as_ansi(self) -> str:
        """Return offscreen buffer text with ANSI cell styles preserved."""
        return self.session.get_core_session_output_as_ansi()

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy ``text`` to the system clipboard via an OSC 52 escape.

        Works over SSH and in most modern terminal emulators (iTerm2,
        Kitty, WezTerm, Windows Terminal, VS Code's integrated terminal)
        without a subprocess or platform-specific clipboard tool. Not
        forwarded by tmux/screen unless clipboard passthrough is enabled
        there, and silently does nothing on unsupported terminals.

        Args:
            text: The text to place on the system clipboard.

        Returns:
            ``True`` when the escape sequence was written, ``False`` when
                this is an offscreen session (no real terminal to write to).
        """
        if self._session is None or self._session._is_offscreen:
            return False
        import base64

        import xnano_core.rust.native as native

        payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
        native.print_text(f"\x1b]52;c;{payload}\x07")
        native.flush_stdout_buffer()
        return True

    def _build_render_field(
        self,
        *,
        color: ColorLike | None,
        background: ColorLike | None,
        modifiers: Sequence[CharacterModifier] | None,
        align: Alignment | None,
        border: Border | None,
        border_sides: Sequence[Side] | None,
        border_color: ColorLike | None,
        title: str | None,
        title_position: FrameTitlePosition | None,
        padding: PaddingLike | None,
        gap: int | None,
    ) -> Any:
        """Build a ``GridFieldInfo`` describing style for non-BaseGrid content."""
        from xnano.fields import GridFieldInfo

        return GridFieldInfo(
            color=color,
            background=background,
            modifiers=list(modifiers) if modifiers else None,
            align=align,
            border=border,
            border_sides=list(border_sides) if border_sides else None,
            border_color=border_color,
            title=title,
            title_position=title_position,
            padding=padding,
            gap=gap,
        )

    def _query_terminal_rows(self) -> int:
        """Return the terminal's row count, or ``0`` when unavailable."""
        try:
            import xnano_core.rust.native as native

            return native.terminal_size().height
        except Exception:
            return 0

    def _resolve_inline_height(
        self,
        height_sizing: "Sizing",
        renderables: Sequence[Any],
        field: Any,
    ) -> int:
        """Resolve a non-fill height ``Sizing`` to an inline viewport height.

        ``fit`` uses the summed content height (including any field
        border/padding overhead); ``percent`` / ``ratio`` resolve against the
        terminal's row count; ``cells`` is taken literally. The result is
        clamped to at least one row and to the available terminal rows.
        """
        term_rows = self._query_terminal_rows()
        # Only ``fit`` consults content, so avoid measuring otherwise.
        content = (
            _dispatch.measure_renderables_height(renderables, field)
            if height_sizing.is_fit
            else 0
        )
        available = term_rows if term_rows > 0 else max(content, 1)
        height = max(1, height_sizing.resolve(available, content))
        if term_rows > 0:
            height = min(height, term_rows)
        return height

    def _resolve_run(
        self,
        renderables: Sequence[Any],
        is_grid: bool,
        field: Any,
    ) -> _ResolvedRun:
        """Resolve the viewport and root width sizing for a run/render.

        The terminal's own height sizing selects the viewport: ``fill`` (the
        default for a ``BaseGrid``) claims the full alternate screen, while any
        finite height (the default ``fit`` for other content) reserves an
        inline viewport. The width sizing constrains the root box within that
        viewport.

        Returns a ``_ResolvedRun``; the caller is responsible for wiring
        its fields onto the terminal so the resolution is explicit rather than
        a side effect.
        """
        from xnano._types import Sizing

        height_sizing = self._height_sizing or (
            Sizing.fraction(1) if is_grid else Sizing.fit()
        )
        width_sizing = self._width_sizing or (
            Sizing.fraction(1) if is_grid else Sizing.fit()
        )
        # A ``BaseGrid`` has no measurable intrinsic height, so a ``fit`` height for
        # one can't reserve an inline viewport — fall back to full-screen. This
        # only arises from an explicit ``Terminal(height="fit")``, so surface it
        # rather than silently overriding the request.
        fit_grid = is_grid and height_sizing.is_fit
        if fit_grid:
            warnings.warn(
                "Terminal(height='fit') has no effect for a BaseGrid: a BaseGrid has "
                "no measurable intrinsic height, so it renders full-screen. "
                "Use a fixed height (e.g. Terminal(height=24)) to reserve an "
                "inline viewport.",
                UserWarning,
                stacklevel=3,
            )
        if height_sizing.is_fill or fit_grid:
            inline_height = None
        else:
            inline_height = self._resolve_inline_height(
                height_sizing, renderables, field
            )
        return _ResolvedRun(
            inline_height=inline_height, root_width_sizing=width_sizing
        )

    def _apply_resolved_run(self, resolved: _ResolvedRun) -> None:
        """Store a ``_ResolvedRun`` where frame-time consumers read it.

        ``_inline_height`` is consumed once when the deferred session is created
        (``_ensure_session``); ``_root_width_sizing`` is consumed every
        frame when resolving the root area.
        """
        self._inline_height = resolved.inline_height
        self._root_width_sizing = resolved.root_width_sizing

    def _recreate_session(self, resolved: _ResolvedRun) -> None:
        """Tear down the live session so the next access recreates it.

        Used when a one-shot ``render`` needs a different inline viewport
        height than the session that is already open.
        """
        if self._session is not None:
            self._session.leave()
            self._session = None
        self._apply_resolved_run(resolved)
        self._pending_enter = True

    def _prepare_render_session(
        self,
        renderables: Sequence[Any],
        field: Any,
        *,
        is_grid: bool = False,
    ) -> None:
        """Resolve viewport sizing for a one-shot render and prepare the session.

        Each ``render`` call is content-sized. When an inline session is
        already open but the new content needs a different inline viewport
        height, the existing session is torn down and recreated on the next
        paint. Pass ``is_grid=True`` when the single root is a ``BaseGrid`` so
        height/width defaults match the interactive ``run`` path.
        """
        resolved = self._resolve_run(renderables, is_grid=is_grid, field=field)
        if self._session is None:
            self._apply_resolved_run(resolved)
            return
        if self._session._is_offscreen:
            self._root_width_sizing = resolved.root_width_sizing
            return
        current_inline = self._session._core_session.get_inline_height()
        if resolved.inline_height != current_inline:
            self._recreate_session(resolved)
        else:
            self._root_width_sizing = resolved.root_width_sizing

    def _render_stream_items(
        self,
        renderables: Sequence[Any],
        *,
        field: Any,
        flush: bool = False,
    ) -> None:
        """Paint ``renderables`` into the live session (stream-friendly).

        Used by ``xnano._renderable.render`` when an active host is present so
        full-content stream updates re-paint without leaving the session.
        """
        items = tuple(renderables)
        self._prepare_render_session(items, field)
        self._render_frame(renderables=items, field=field)
        if flush:
            self._flush_session_output()

    def _flush_session_output(self) -> None:
        """Best-effort flush of the live session's output buffers."""
        session = self._session
        if session is None:
            return
        flush = getattr(session, "flush", None)
        if callable(flush):
            try:
                flush()
            except Exception:
                pass

    def render(
        self,
        *renderables: Any,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: Sequence[CharacterModifier] | None = None,
        align: Alignment | None = None,
        border: Border | None = None,
        border_sides: Sequence[Side] | None = None,
        border_color: ColorLike | None = None,
        title: str | None = None,
        title_position: FrameTitlePosition | None = None,
        padding: PaddingLike | None = None,
        gap: int | None = None,
        direction: Direction = "vertical",
        # builtins.print-compatible parameters
        sep: str | None = " ",
        end: str | None = "\n",
        file: IO[str] | TextIO | None = None,
        flush: bool = False,
        # stream / live-update parameters
        stream: str | bool | None = None,
        update: bool = False,
    ) -> None:
        """Render renderables to the terminal once (no event loop).

        Each renderable is auto-sized to its content dimensions and painted
        sequentially from the top of the render area.  When called standalone
        the session auto-enters an inline viewport sized to the content, paints
        one frame, and exits — leaving the output inline with prior terminal
        output.  When called inside an already-live session the content is
        painted into the current viewport instead.

        Style params (``color``, ``border``, ``padding``, etc.) apply to the
        content and mirror the options available on ``Field``.

        Also accepts builtins.print-compatible ``sep`` / ``end`` / ``file`` /
        ``flush``, plus ``stream`` / ``update`` for append-or-replace stream
        regions (shared with ``xnano._renderable.render``).
        """
        # Text targets, stream regions, and in-place updates share the
        # module-level renderer (stdout ANSI and live-session paint).
        if file is not None or stream is not None or update:
            from xnano._renderable import render as module_render

            module_render(
                *renderables,
                direction=direction,
                color=color,
                background=background,
                modifiers=modifiers,
                align=align,
                border=border,
                border_sides=border_sides,
                border_color=border_color,
                title=title,
                title_position=title_position,
                padding=padding,
                sep=sep,
                end=end,
                file=file,
                flush=flush,
                stream=stream,
                update=update,
            )
            return

        from xnano.grid import BaseGrid

        items = tuple(renderables)
        # Mirror ``run``: a lone BaseGrid is the layout root, not an inline
        # renderable. Painting it through the inline path only draws field
        # chrome tops (a single border row) and drops the rest of the grid.
        is_grid = len(items) == 1 and isinstance(items[0], BaseGrid)
        field = (
            None
            if is_grid
            else self._build_render_field(
                color=color,
                background=background,
                modifiers=modifiers,
                align=align,
                border=border,
                border_sides=border_sides,
                border_color=border_color,
                title=title,
                title_position=title_position,
                padding=padding,
                gap=gap,
            )
        )

        # Wasm / headless builds: paint through a buffer-backed session and
        # write the resulting cell text to stdout (no interactive terminal).
        if not self._is_live and not self._supports_live_terminal():
            self._render_buffer_backed(
                items,
                field=field,
                file=file,
                end=end if end is not None else "\n",
                flush=flush,
            )
            return

        auto_entered = not self._is_live
        if auto_entered:
            self.__enter__()
        self._prepare_render_session(items, field, is_grid=is_grid)
        try:
            if is_grid:
                self._render_frame(items[0])
            else:
                self._render_frame(renderables=items, field=field)
            if flush:
                self._flush_session_output()
        finally:
            if auto_entered:
                self.__exit__()

    def _render_buffer_backed(
        self,
        renderables: Sequence[Any],
        *,
        field: Any,
        file: IO[str] | TextIO | None,
        end: str,
        flush: bool,
    ) -> None:
        """Single-frame render via ``CoreSession.offscreen`` (wasm path).

        Uses the real layout/constraint engine, then dumps the buffer text
        to ``file`` (default stdout). There is no interactive event loop.
        """
        from xnano import _dispatch
        from xnano.grid import BaseGrid

        # A lone ``BaseGrid`` root drives the full layout engine and sizes
        # itself to the (default or explicitly set) viewport, the same as a
        # live terminal — its content isn't measurable in isolation the way
        # plain renderables are, since fields can fill/fraction-size against
        # whatever area they're given.
        root: Any = None
        if len(renderables) == 1 and isinstance(renderables[0], BaseGrid):
            root = renderables[0]

        # Prefer measured content size so the buffer matches the grid/layout.
        width = 80
        height = 24
        try:
            if root is not None:
                pass
            elif field is not None and len(renderables) == 1:
                w, h = _dispatch.measure_renderable_in_field(
                    renderables[0], field
                )
                width = max(1, w)
                height = max(1, h)
            elif renderables:
                max_w = 1
                for item in renderables:
                    w, _ = _dispatch.measure_renderable_in_field(item, field)
                    max_w = max(max_w, w)
                width = max_w
                height = max(
                    1,
                    _dispatch.measure_renderables_height(renderables, field),
                )
        except Exception:
            pass

        if (
            self._width_sizing is not None
            and self._width_sizing.kind == "cells"
        ):
            try:
                width = max(1, int(self._width_sizing.value))
            except Exception:
                pass
        if (
            self._height_sizing is not None
            and self._height_sizing.kind == "cells"
        ):
            try:
                height = max(1, int(self._height_sizing.value))
            except Exception:
                pass
        if self._inline_height is not None:
            height = max(1, self._inline_height)

        terminal = type(self).offscreen(
            cols=width,
            rows=height,
            state=self.state,
            title=self.title,
        )
        try:
            terminal._root_width_sizing = self._root_width_sizing
            terminal._render_frame(
                root,
                renderables=None if root is not None else tuple(renderables),
                field=field,
            )
            text = terminal.get_output_as_ansi().rstrip("\n")
            out = sys.stdout if file is None else file
            out.write(text)
            out.write(end)
            if flush:
                try:
                    out.flush()
                except Exception:
                    pass
        finally:
            terminal.__exit__(None, None, None)

    def run(
        self,
        *renderables: Any,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: Sequence[CharacterModifier] | None = None,
        align: Alignment | None = None,
        border: Border | None = None,
        border_sides: Sequence[Side] | None = None,
        border_color: ColorLike | None = None,
        title: str | None = None,
        title_position: FrameTitlePosition | None = None,
        padding: PaddingLike | None = None,
        gap: int | None = None,
        auto_resize: bool = True,
    ) -> None:
        """Enter the terminal, render content each frame, and loop until exit.

        Accepts any renderable value — a ``BaseGrid`` instance, strings, numbers,
        components, render nodes, or any mix.  A single ``BaseGrid`` fills the full
        alternate screen (existing behaviour); all other renderables are
        rendered inline: the session reserves a viewport sized to the measured
        content and paints directly through native types (no ``BaseGrid`` is
        created) rather than taking over the whole screen.

        Style params (``color``, ``border``, ``padding``, etc.) apply to
        non-BaseGrid content and mirror the options available on ``Field``.

        When ``auto_resize`` is ``True`` (default), terminal resize events
        trigger an immediate re-render so content stays correctly sized.

        Can be called without the context manager — it auto-enters and exits.
        """
        from xnano.grid import BaseGrid

        is_grid = len(renderables) == 1 and isinstance(
            renderables[0], BaseGrid
        )

        # Non-BaseGrid content renders inline; build its style field up front so
        # the inline viewport can be sized to include any border/padding.
        field = (
            None
            if is_grid
            else self._build_render_field(
                color=color,
                background=background,
                modifiers=modifiers,
                align=align,
                border=border,
                border_sides=border_sides,
                border_color=border_color,
                title=title,
                title_position=title_position,
                padding=padding,
                gap=gap,
            )
        )

        if not self._supports_live_terminal():
            raise RuntimeError(
                "Terminal.run() requires a live OS terminal and is not "
                "available on Emscripten/WebAssembly builds. Use "
                "Terminal.render(...) or Terminal.offscreen(...) for "
                "single-frame buffer-backed rendering with the real layout "
                "engine."
            )

        auto_entered = not self._is_live
        if auto_entered:
            self.__enter__()
        # Resolve the viewport/root sizing when the underlying session has not
        # been created yet — either from the auto-enter above or a deferred
        # context-manager entry.
        if self._session is None:
            self._apply_resolved_run(
                self._resolve_run(renderables, is_grid=is_grid, field=field)
            )
        self._exit_requested = False

        _resize_hook: Any = None

        # Single BaseGrid → full-screen path (unchanged behaviour). Non-BaseGrid content
        # renders inline: the renderables and their shared style field are kept
        # on the terminal so the render loop and the resize hook can repaint.
        grid_root: Any = None
        if is_grid:
            grid_root = renderables[0]
            self._track_frame_grid(grid_root)
            self._run_renderables = None
            self._run_field = None
        else:
            self._run_renderables = tuple(renderables)
            self._run_field = field

            if auto_resize:
                _terminal = self

                def _resize_hook(ctx: Any) -> None:  # type: ignore[misc]
                    if _terminal._run_renderables is not None:
                        _terminal._render_frame(
                            renderables=_terminal._run_renderables,
                            field=_terminal._run_field,
                        )

                self._hooks.on_resize_hooks.append(_resize_hook)

        try:
            if is_grid:
                # Load the focus helpers before CoreSession claims the terminal.
                # This keeps one-time Python import work out of the interval
                # between entering the alternate screen and painting frame one.
                from xnano import _types as _focus  # noqa: F401

            while not self._exit_requested:
                self._render_frame(
                    grid_root,
                    renderables=self._run_renderables,
                    field=self._run_field,
                )
                self._pump_events()
                self._pump_tick()
                # Frame polls fire once per loop iteration, after events/ticks.
                _dispatch.pump_poll(self, when="frame")
        except (KeyboardInterrupt, Exit):
            pass
        except Exception:
            # Fail-fast: log and re-raise.  ``finally`` (and the caller's
            # ``with Terminal()`` if any) still restores the host terminal so
            # raw mode / alt-screen cannot stick after a hook crash.
            import logging

            logging.getLogger("xnano").exception(
                "Uncaught exception in Terminal.run(); restoring terminal"
            )
            raise
        finally:
            self._run_renderables = None
            self._run_field = None
            if _resize_hook is not None:
                try:
                    self._hooks.on_resize_hooks.remove(_resize_hook)
                except ValueError:
                    pass
            if auto_entered:
                self.__exit__()
                self._inline_height = None

    @property
    def session(self) -> "TerminalController[StateT]":
        if self._pending_enter:
            self._ensure_session()
        if self._session is None:
            from xnano.core.exceptions import TerminalNotActiveError

            raise TerminalNotActiveError()
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
            from xnano.terminal.cursor import TerminalCursor

            self._cursor = TerminalCursor(self)
        return self._cursor

    @property
    def device(self) -> Any:
        """Live device controller for this terminal session."""
        if self._device is None:
            from xnano.terminal.device import TerminalDevice

            self._device = TerminalDevice(self)
        return self._device


__all__ = ("Terminal", "_ACTIVE_TERMINAL", "exit_terminal")
