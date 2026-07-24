"""xnano.beta.core.runtime

---

Own live and offscreen sessions, rendering, events, state, focus, and output.
"""

from __future__ import annotations

import atexit
import contextvars
import signal
import time
from typing import Any, Generic, Sequence, TypeVar

from xnano_core.core import CoreSession

from xnano.beta.actions import Actions
from xnano.beta.colors import ColorLike
from xnano.beta.core.content import Panel, Stack, TextBlock
from xnano.beta.core.frame import Frame
from xnano.beta.core.rendering import lower_content
from xnano.beta.core.stage import Stage
from xnano.beta.cursor import Cursor
from xnano.beta.device import Device
from xnano.beta.events import event_from_core
from xnano.beta.types import (
    Alignment,
    Border,
    CharacterModifier,
    Direction,
    FrameTitlePosition,
    PaddingLike,
    Side,
)

StateT = TypeVar("StateT")

_EXIT_SIGNALS: tuple[signal.Signals, ...] = tuple(
    resolved
    for resolved in (
        getattr(signal, name, None) for name in ("SIGINT", "SIGTERM", "SIGHUP")
    )
    if resolved is not None
)
"""Termination signals to route through terminal restore, resolved per
platform. ``SIGHUP`` (controlling-terminal hangup) is POSIX-only and
simply absent on Windows; individual signals a platform accepts to
``signal.signal`` but rejects at install time are skipped there too."""

_ACTIVE_RUNTIME: contextvars.ContextVar["Runtime[Any] | None"] = (
    contextvars.ContextVar("_ACTIVE_BETA_RUNTIME", default=None)
)


def get_active_runtime() -> "Runtime[Any] | None":
    """Return the runtime active in the current context."""
    return _ACTIVE_RUNTIME.get()


def _atexit_restore_active_runtime() -> None:
    """Restore a still-live runtime if the process exits without ``close``.

    Without this, an interpreter shutdown that skips the normal ``close``
    path (an unhandled exit, a closed terminal window) leaves the host
    terminal in raw mode with mouse tracking and alternate-screen state
    still enabled — so the next shell paints garbage glyphs until reset.
    """
    runtime = _ACTIVE_RUNTIME.get()
    if runtime is None or not runtime.is_live:
        return
    try:
        runtime.close()
    except Exception:
        pass


atexit.register(_atexit_restore_active_runtime)


class Runtime(Generic[StateT]):
    """Drive one application through an ``xnano_core`` session.

    Most applications use :class:`xnano.beta.terminal.Terminal`; use
    ``Runtime`` directly when you need explicit session ownership.

    Attributes:
        session: Native session owned by the runtime.
        terminal: Compatibility name for this runtime.
        surface: Presentation surface name.
        is_live: Whether the runtime owns the user's terminal.
        state: Application state shared with hooks.
        device: Display controls for the session.
        cursor: Cursor controls for the session.
        actions: Synthetic action performer.
        stage: Current layout stage, when available.
        size: Viewport width and height in cells.
        focused_group: Name of the focused field group.

    Example:
        >>> runtime = Runtime.offscreen(24, 3)
        >>> frame = runtime.render("Hello")
        >>> frame.width, frame.height
        (24, 3)
        >>> runtime.close()
    """

    def __init__(
        self,
        session: CoreSession,
        *,
        live: bool,
        state: StateT | None = None,
        title: str | None = None,
        surface: str = "terminal",
        tick_interval: int = 16,
    ) -> None:
        self._session = session
        self._live = live
        self._state = state
        self._surface = surface
        self._root: Any = None
        self._revision = 0
        self._closed = False
        self._should_exit = False
        self._focused_group: str | None = None
        self._token: contextvars.Token[Runtime[Any] | None] | None = None
        self._frame_commands: list[dict[str, Any]] = []
        self._stage = Stage()
        self._elapsed_ms = 0
        self._tick_hook_times: dict[tuple[int, str], int] = {}
        self._post_init_grids: set[int] = set()
        self._watch_values: dict[tuple[int, str, str], Any] = {}
        self._grid_breakpoints: dict[int, str] = {}
        self._tick_interval = max(1, tick_interval)
        self._last_tick_ms = time.monotonic() * 1000
        self._signals_installed = False
        self._prev_signal_handlers: dict[signal.Signals, Any] = {}
        self._cursor = Cursor(self)
        self._device = Device(self)
        self._actions = Actions(self)
        if title is not None:
            self._device.title = title

    @classmethod
    def live(
        cls,
        *,
        state: StateT | None = None,
        title: str | None = None,
        tick_interval: int = 16,
    ) -> "Runtime[StateT]":
        """Create a runtime backed by the active terminal."""
        session = CoreSession.init(tick_rate_ms=None)
        return cls(
            session,
            live=True,
            state=state,
            title=title,
            tick_interval=tick_interval,
        )

    @classmethod
    def offscreen(
        cls,
        width: int = 80,
        height: int = 24,
        *,
        state: StateT | None = None,
        title: str | None = None,
    ) -> "Runtime[StateT]":
        """Create an active in-memory runtime."""
        runtime = cls(
            CoreSession.offscreen(width, height),
            live=False,
            state=state,
            title=title,
            surface="offscreen",
        )
        return runtime.enter()

    @staticmethod
    def supports_live_terminal() -> bool:
        """Return whether this build can claim a live terminal."""
        return CoreSession.supports_live_terminal()

    def _on_exit_signal(self, signum: int, frame: Any) -> None:
        """Route a termination signal through the normal exit path.

        Marks the run loop for exit and raises ``SystemExit`` so the
        session is restored via ``close`` before the process ends —
        rather than the default action terminating mid-frame and leaving
        the host terminal in raw mode with mouse tracking still on.
        """
        self._should_exit = True
        raise SystemExit(128 + signum)

    def _install_signal_handlers(self) -> None:
        """Install termination handlers for a live session.

        Each supported signal is installed independently: a platform
        that resolves the name but rejects it at install time (Windows
        only accepts a small set) is skipped without losing the others.
        ``signal.signal`` is also only valid on the main thread, so
        installation is a no-op anywhere else (e.g. a web request
        thread).
        """
        if self._signals_installed:
            return
        installed: dict[signal.Signals, Any] = {}
        for exit_signal in _EXIT_SIGNALS:
            try:
                installed[exit_signal] = signal.signal(
                    exit_signal, self._on_exit_signal
                )
            except (OSError, ValueError, RuntimeError):
                continue
        self._prev_signal_handlers = installed
        self._signals_installed = bool(installed)

    def _restore_signal_handlers(self) -> None:
        """Restore the handlers replaced by ``_install_signal_handlers``."""
        if not self._signals_installed:
            return
        for exit_signal, previous in self._prev_signal_handlers.items():
            try:
                signal.signal(exit_signal, previous)
            except (OSError, ValueError, RuntimeError):
                pass
        self._prev_signal_handlers = {}
        self._signals_installed = False

    def enter(self) -> "Runtime[StateT]":
        """Bind this runtime to the current context."""
        if self._token is None:
            self._token = _ACTIVE_RUNTIME.set(self)
        if self._live:
            self._install_signal_handlers()
        return self

    def close(self) -> None:
        """Restore the native session and release the active binding."""
        if self._closed:
            return
        self._closed = True
        if self._token is not None:
            _ACTIVE_RUNTIME.reset(self._token)
            self._token = None
        # Restore the host terminal first (raw mode, mouse tracking,
        # alternate screen, SGR) so a failure restoring signal handlers
        # never leaves the screen corrupted.
        try:
            self._session.restore()
        finally:
            # Runtime owns cursor/device/action proxies that point back to it,
            # so the Python object can remain in a reference cycle after
            # close. Release the unsendable PyO3 session now, on its owner
            # thread, instead of leaving its destructor to a later GC pass.
            del self._session
            self._restore_signal_handlers()

    def __enter__(self) -> "Runtime[StateT]":
        return self.enter()

    def __exit__(self, *exception: Any) -> None:
        self.close()

    @property
    def session(self) -> CoreSession:
        """Native session owned by this runtime."""
        return self._session

    @property
    def terminal(self) -> "Runtime[StateT]":
        """Compatibility name for the runtime's terminal surface."""
        return self

    @property
    def surface(self) -> str:
        """Presentation surface name."""
        return self._surface

    @property
    def is_live(self) -> bool:
        """Whether the runtime owns the user's terminal."""
        return self._live

    @property
    def state(self) -> StateT | None:
        """Application state shared with hooks."""
        return self._state

    @state.setter
    def state(self, value: StateT | None) -> None:
        self._state = value

    @property
    def device(self) -> Device:
        """Display controls for this session."""
        return self._device

    @property
    def cursor(self) -> Cursor:
        """Caret controls for this session."""
        return self._cursor

    @property
    def actions(self) -> Actions:
        """Synthetic action performer for this session."""
        return self._actions

    @property
    def stage(self) -> Any:
        """Current layout stage when a grid has rendered."""
        return self._stage

    @property
    def size(self) -> tuple[int, int]:
        """Viewport width and height in cells."""
        size = self._session.get_size()
        return (int(size.width), int(size.height))

    @property
    def focused_group(self) -> str | None:
        """Name of the focused field group."""
        return self._focused_group

    def set_root(self, root: Any) -> None:
        """Set the renderable used by subsequent empty renders."""
        self._root = root

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
        gap: int = 0,
        direction: Direction = "vertical",
    ) -> Frame:
        """Render one frame and return its immutable snapshot.

        Args:
            *renderables: Grids, components, content primitives, or plain
                values to paint.
            color: Foreground color applied to plain values.
            background: Background color for the rendered area.
            modifiers: Character modifiers applied to plain values.
            align: Horizontal alignment applied to plain values.
            border: Border style around the rendered area.
            border_sides: Border sides to draw.
            border_color: Border foreground color.
            title: Optional border title.
            title_position: Border edge that holds the title.
            padding: Space between the border and content.
            gap: Cells between multiple renderables.
            direction: Direction used to lay out multiple renderables.

        Returns:
            A snapshot of the rendered terminal frame.
        """
        items = renderables or (
            (self._root,) if self._root is not None else ()
        )
        if self._root is not None:
            from xnano.beta.core.dispatch import (
                dispatch_frame,
                dispatch_post_init,
            )
            from xnano.beta.utils.focus import ensure_default_field_focus

            dispatch_post_init(self._root, self)
            ensure_default_field_focus(self)
            dispatch_frame(self._root, self)
        if len(items) == 1 and isinstance(
            getattr(type(items[0]), "_grid_fields", None), dict
        ):
            from xnano.beta.core.controller import TerminalController
            from xnano.beta.types import Area

            self._stage.areas.clear()
            controller = TerminalController(self)
            items[0]._grid_build_frame(
                Area(x=0, y=0, width=self.size[0], height=self.size[1]),
                controller,
            )
            controller.paint_stage()
            controller.commit()
            return self._snapshot_frame()
        styled_items = tuple(
            TextBlock(
                text=item,
                color=color,
                background=background,
                modifiers=tuple(modifiers or ()),
                align=align,
            )
            if isinstance(item, str)
            else item
            for item in items
        )
        content = (
            styled_items[0]
            if len(styled_items) == 1
            else Stack(
                children=styled_items,
                direction=direction,
                gap=gap,
            )
        )
        if (
            border is not None
            or border_sides is not None
            or border_color is not None
            or title is not None
            or padding is not None
            or background is not None
        ):
            content = Panel(
                child=content,
                title=title,
                title_position=title_position,
                border=border,
                border_color=border_color,
                border_sides=(
                    tuple(border_sides) if border_sides is not None else None
                ),
                background=background,
                padding=padding,
            )
        node = lower_content(content)
        self._session.render(node)
        return self._snapshot_frame()

    def _snapshot_frame(self) -> Frame:
        """Return the rendered native buffer as one public frame."""
        self._revision += 1
        buffer = self._session.buffer_snapshot()
        text = "\n".join(buffer.to_string_lines())
        ansi = "\n".join(buffer.to_ansi_lines())
        frame = Frame(
            width=self.size[0],
            height=self.size[1],
            text=text,
            ansi=ansi,
            cursor_position=self.cursor.position,
            cursor_visible=self.cursor.visible,
            cursor_style=self.cursor.style,
            title=self.device.title,
            commands=tuple(self._frame_commands),
            revision=self._revision,
        )
        self._frame_commands.clear()
        return frame

    def pump(self, timeout: float = 0.0) -> bool:
        """Poll and dispatch at most one event."""
        if self._should_exit:
            return False
        timeout_ms = max(0, int(timeout * 1000))
        if self._live and timeout_ms == 0:
            timeout_ms = self._tick_interval
        native_event = self._session.poll_event(timeout_ms)
        if native_event is not None:
            self.dispatch(event_from_core(native_event))
        elif self._root is not None:
            from xnano.beta.core.dispatch import dispatch_idle

            dispatch_idle(self._root, self)
        if self._root is not None:
            from xnano.beta.events import Event, TickEventData

            now = time.monotonic() * 1000
            elapsed_ms = max(0, int(now - self._last_tick_ms))
            self._last_tick_ms = now
            self.dispatch(
                Event.from_data(TickEventData(elapsed_ms=elapsed_ms))
            )
        return not self._should_exit

    def dispatch(self, event: Any) -> None:
        """Dispatch one event to the root grid or component."""
        from xnano.beta.core.dispatch import dispatch_event
        from xnano.beta.utils.focus import (
            apply_text_keyboard,
            cycle_field_focus,
            focused_component,
        )

        consumed = False
        mouse = getattr(event, "mouse_event", None)
        if mouse is not None and mouse.field is None:
            from xnano.beta.core.dispatch import iter_grids
            from xnano.beta.events import Event, MouseEventData

            for grid in iter_grids(self._root):
                for hit in reversed(getattr(grid, "_grid_field_hits", ())):
                    if hit.area.contains((mouse.x, mouse.y)):
                        field = hit.grid._grid_field_info(hit.field_name)
                        event = Event.from_data(
                            MouseEventData(
                                kind=mouse.kind,
                                x=mouse.x,
                                y=mouse.y,
                                button=mouse.button,
                                field=hit.field_name,
                                group=field.group,
                            )
                        )
                        break
        keyboard = getattr(event, "keyboard_event", None)
        if keyboard is not None:
            if keyboard.matches("ctrl+c"):
                self.request_exit()
                return
            if keyboard.matches("tab"):
                consumed = cycle_field_focus(self)
            elif keyboard.matches("shift+tab"):
                consumed = cycle_field_focus(self, -1)
            else:
                consumed = apply_text_keyboard(
                    focused_component(self),
                    keyboard,
                )
        clipboard = getattr(event, "clipboard_event", None)
        tick = getattr(event, "tick_event", None)
        if tick is not None:
            self._elapsed_ms += tick.elapsed_ms
        component = focused_component(self)
        if clipboard is not None and component is not None:
            paste_handler = getattr(component, "handle_paste", None)
            if callable(paste_handler):
                consumed = (
                    bool(paste_handler(clipboard.text or "")) or consumed
                )
        if self._root is not None and not consumed:
            dispatch_event(self._root, self, event)
        root_dispatch = getattr(self._root, "dispatch_event", None)
        if callable(root_dispatch):
            root_dispatch(event, self)

    def play_effect(
        self,
        effect: Any,
        *,
        fields: list[str] | None = None,
    ) -> bool:
        """Play an effect over fields recorded by the latest render.

        Args:
            effect: Beta effect description.
            fields: Field names whose rendered areas receive the effect.

        Returns:
            Whether at least one named field had a rendered area.
        """
        from xnano.beta.core.effects import resolve_native_effect

        played = False
        for field in fields or ():
            area = self._session.effect_area_for(field)
            if area is None:
                continue
            native_effect = resolve_native_effect(effect).with_area(area)
            key = f"{getattr(effect, 'key', None) or field}:{field}"
            self._session.add_unique_effect(key, native_effect)
            played = True
        return played

    def perform(self, action: Any) -> None:
        """Perform a synthetic action through its event representation."""
        from xnano.beta.actions import (
            ClickAction,
            ClipboardAction,
            FocusAction,
            KeyboardAction,
            MouseAction,
            RequestAction,
            ResizeAction,
            TickAction,
        )
        from xnano.beta.events import (
            ClipboardEventData,
            Event,
            FocusEventData,
            KeyboardEventData,
            MouseEventData,
            ResizeEventData,
            TickEventData,
        )

        if isinstance(action, KeyboardAction):
            for binding in action.bindings:
                self.dispatch(
                    Event.from_data(
                        KeyboardEventData.from_binding(
                            str(binding),
                            kind=action.kind or "press",
                        )
                    )
                )
            return
        if isinstance(action, MouseAction):
            self.dispatch(
                Event.from_data(
                    MouseEventData(
                        kind=action.kind or "press",
                        x=0,
                        y=0,
                        button=action.buttons[0]
                        if action.buttons
                        else "unknown",
                    )
                )
            )
            return
        if isinstance(action, ClickAction):
            event = Event.from_data(
                MouseEventData(
                    kind="press",
                    x=0,
                    y=0,
                    button=action.button,
                    field=action.field,
                )
            )
            self.dispatch(event)
            return
        if isinstance(action, FocusAction):
            self.dispatch(
                Event.from_data(
                    FocusEventData(
                        kind=action.kind or "gained",
                        field=action.field,
                    )
                )
            )
            return
        if isinstance(action, ClipboardAction):
            self.dispatch(
                Event.from_data(ClipboardEventData(text=action.text))
            )
            return
        if isinstance(action, ResizeAction):
            self.dispatch(
                Event.from_data(
                    ResizeEventData(
                        width=action.width or self.size[0],
                        height=action.height or self.size[1],
                    )
                )
            )
            return
        if isinstance(action, TickAction):
            self.dispatch(
                Event.from_data(
                    TickEventData(elapsed_ms=action.interval_ms),
                )
            )
            return
        if isinstance(action, RequestAction) and self._root is not None:
            from xnano.beta.requests import dispatch_request

            dispatch_request(
                self._root,
                action.method,
                action.path,
                runtime=self,
            )
            return
        self.dispatch(action)

    def resize(self, width: int, height: int) -> None:
        """Resize support is fixed at offscreen-session construction."""
        if self.size != (width, height):
            raise RuntimeError("Create a new offscreen runtime to resize it.")

    def request_exit(self) -> None:
        """Stop the run loop after the current dispatch."""
        self._should_exit = True

    def focus(self, group: str) -> bool:
        """Focus a named field group."""
        from xnano.beta.utils.focus import (
            resolve_group_target,
            set_field_focus,
        )

        target = resolve_group_target(self, group)
        if target is None:
            return False
        set_field_focus(self, target)
        return True

    focus_group = focus

    def blur(self) -> None:
        """Clear field focus."""
        from xnano.beta.utils.focus import clear_field_focus

        clear_field_focus(self)
        self._focused_group = None

    blur_field = blur

    def focus_next(self) -> bool:
        """Move focus through the root grid when supported."""
        from xnano.beta.utils.focus import cycle_field_focus

        return cycle_field_focus(self)

    def focus_previous(self) -> bool:
        """Move focus backward through the root grid when supported."""
        from xnano.beta.utils.focus import cycle_field_focus

        return cycle_field_focus(self, -1)

    def get_output(self) -> str:
        """Return the current buffer as plain text."""
        return "\n".join(self._session.buffer_snapshot().to_string_lines())

    def get_output_as_ansi(self) -> str:
        """Return the current buffer with ANSI styling."""
        return "\n".join(self._session.buffer_snapshot().to_ansi_lines())


__all__ = ("Runtime", "get_active_runtime")
