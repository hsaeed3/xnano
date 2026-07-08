"""xnano.beta.terminal"""

from __future__ import annotations

import contextvars
import dataclasses
import warnings
from typing import Any, Callable, Generic, Sequence, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.beta.color import ColorLike
    from xnano.beta.frame import FrameTitlePosition
    from xnano.beta.sizing import Sizing, SizingLike
    from xnano.beta.types import (
        Alignment,
        Border,
        CharacterModifier,
        Direction,
        PaddingLike,
        Side,
    )

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


@dataclasses.dataclass(frozen=True, slots=True)
class _ResolvedRun:
    """The viewport/root sizing resolved for a single ``run`` / ``render``.

    Returned by :meth:`Terminal._resolve_run` so the resolution is an explicit
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


class Terminal(Generic[StateT]):
    """The active terminal screen / session.

    ``Terminal`` owns the ``CoreSession`` lifecycle, binds the context variable,
    drains events, and dispatches hooks.  Use as a context manager or call
    the function ``Terminal.run`` directly with a root ``Grid`` instance.

    The terminal is the *root box*: its own ``width`` / ``height`` sizing
    decides how the root area attaches to the physical screen.  A fill height
    (the default for a ``Grid``) claims the full alternate screen, while any
    finite height (the default ``fit`` for other content) reserves an inline
    viewport in the main screen buffer.  A fixed ``width`` / ``height`` (e.g.
    ``Terminal(width=80, height=24)``) constrains the render area to that box.

    Example:
        >>> with Terminal() as terminal:
        ...     terminal.run(Grid.new([
        ...         Text.new("Hello, world!"),
        ...     ]))

        **Inline, content-sized output:**

        >>> Terminal().run("Hello, world!")

        **Fixed-size box:**

        >>> Terminal(width=40, height=10).run(App())

        **With State:**

        >>> with Terminal(state=State(name="John")) as terminal:
        ...     terminal.run(Grid.new([
        ...         Text.new("Hello, {terminal.state.name}!"),
        ...     ]))

    Attributes:
        title: Optional window title set on session entry.
        width: Root-box horizontal sizing (any ``Sizing`` or shorthand). When
            unset, defaults to fill for a ``Grid`` and fit for other content.
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
        "_run_renderables",
        "_run_field",
        "_inline_height",
        "_pending_enter",
        "_width_sizing",
        "_height_sizing",
        "_root_width_sizing",
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
    ) -> None:
        from xnano.beta.sizing import Sizing

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
        self._run_renderables: tuple[Any, ...] | None = None
        self._run_field: Any = None
        self._inline_height: int | None = None
        self._pending_enter: bool = False

    def __enter__(self) -> "Terminal[StateT]":
        if self._is_live:
            return self
        # The underlying ``CoreSession`` is created lazily on first access (see
        # ``_ensure_session``) so that ``run`` / ``render`` can decide between a
        # full-screen and an inline viewport based on the content given, even
        # when entered via the context manager.
        self._terminal_token = _ACTIVE_TERMINAL.set(self)
        self._is_live = True
        self._pending_enter = True
        self._drain_pending_hooks()
        self._register_default_hooks()
        return self

    def _ensure_session(self) -> None:
        """Create the deferred ``CoreSession`` if entry is still pending."""
        if not self._pending_enter:
            return
        self._pending_enter = False
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
        self._session = Session(core)

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
            self._pending_enter = False
            self._exit_requested = False
            self._inline_height = None
            self._root_width_sizing = None

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
        """Build a ``GridFieldInfo`` describing style for non-Grid content."""
        from xnano.beta.fields import GridFieldInfo

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
            from xnano_core.rust import native

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
        default for a ``Grid``) claims the full alternate screen, while any
        finite height (the default ``fit`` for other content) reserves an
        inline viewport. The width sizing constrains the root box within that
        viewport.

        Returns a :class:`_ResolvedRun`; the caller is responsible for wiring
        its fields onto the terminal so the resolution is explicit rather than
        a side effect.
        """
        from xnano.beta.sizing import Sizing

        height_sizing = self._height_sizing or (
            Sizing.fraction(1) if is_grid else Sizing.fit()
        )
        width_sizing = self._width_sizing or (
            Sizing.fraction(1) if is_grid else Sizing.fit()
        )
        # A ``Grid`` has no measurable intrinsic height, so a ``fit`` height for
        # one can't reserve an inline viewport — fall back to full-screen. This
        # only arises from an explicit ``Terminal(height="fit")``, so surface it
        # rather than silently overriding the request.
        fit_grid = is_grid and height_sizing.is_fit
        if fit_grid:
            warnings.warn(
                "Terminal(height='fit') has no effect for a Grid: a Grid has "
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
        (:meth:`_ensure_session`); ``_root_width_sizing`` is consumed every
        frame when resolving the root area.
        """
        self._inline_height = resolved.inline_height
        self._root_width_sizing = resolved.root_width_sizing

    def _recreate_session(self, resolved: _ResolvedRun) -> None:
        """Tear down the live session so the next access recreates it.

        Used when a one-shot :meth:`render` needs a different inline viewport
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
    ) -> None:
        """Resolve viewport sizing for a one-shot render and prepare the session.

        Each :meth:`render` call is content-sized. When an inline session is
        already open but the new content needs a different inline viewport
        height, the existing session is torn down and recreated on the next
        paint.
        """
        resolved = self._resolve_run(renderables, is_grid=False, field=field)
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
    ) -> None:
        """Render renderables to the terminal once (no event loop).

        Each renderable is auto-sized to its content dimensions and painted
        sequentially from the top of the render area.  When called standalone
        the session auto-enters an inline viewport sized to the content, prints
        one frame, and exits — leaving the output inline with prior terminal
        output.  When called inside an already-live session the content is
        painted into the current viewport instead.

        Style params (``color``, ``border``, ``padding``, etc.) apply to the
        content and mirror the options available on ``Field``.
        """
        field = self._build_render_field(
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
        items = tuple(renderables)

        auto_entered = not self._is_live
        if auto_entered:
            self.__enter__()
        self._prepare_render_session(items, field)
        try:
            self._render_frame(renderables=items, field=field)
        finally:
            if auto_entered:
                self.__exit__()

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

        Accepts any renderable value — a ``Grid`` instance, strings, numbers,
        components, render nodes, or any mix.  A single ``Grid`` fills the full
        alternate screen (existing behaviour); all other renderables are
        rendered inline: the session reserves a viewport sized to the measured
        content and paints directly through native types (no ``Grid`` is
        created) rather than taking over the whole screen.

        Style params (``color``, ``border``, ``padding``, etc.) apply to
        non-Grid content and mirror the options available on ``Field``.

        When ``auto_resize`` is ``True`` (default), terminal resize events
        trigger an immediate re-render so content stays correctly sized.

        Can be called without the context manager — it auto-enters and exits.
        """
        from xnano.beta.grid import Grid

        is_grid = len(renderables) == 1 and isinstance(renderables[0], Grid)

        # Non-Grid content renders inline; build its style field up front so
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

        # Single Grid → full-screen path (unchanged behaviour). Non-Grid content
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
            while not self._exit_requested:
                self._render_frame(
                    grid_root,
                    renderables=self._run_renderables,
                    field=self._run_field,
                )
                self._pump_events()
                self._pump_tick()
        except (KeyboardInterrupt, Exit):
            pass
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
    def session(self) -> "Session[StateT]":
        if self._pending_enter:
            self._ensure_session()
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
