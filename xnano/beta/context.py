"""xnano.beta.context

---

Access the current event, application state, runtime, device, cursor, and
layout from an event hook.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

if TYPE_CHECKING:
    from xnano.beta.actions import Actions
    from xnano.beta.core.runtime import Runtime
    from xnano.beta.core.stage import Stage
    from xnano.beta.cursor import Cursor
    from xnano.beta.device import Device
    from xnano.beta.events import (
        Event,
        KeyboardEventData,
        MouseEventData,
        TickEventData,
    )
    from xnano.beta.requests import Request
    from xnano.beta.types import Area, ScrollHandle
    from xnano.beta.utils.responsive import Breakpoint


StateT = TypeVar("StateT")


@dataclasses.dataclass(slots=True, frozen=True)
class Context(Generic[StateT]):
    """Values and controls available inside an event hook.

    Use the event-specific shortcuts such as ``keyboard`` and ``mouse``,
    read or update application state, move focus, or access the current
    cursor, device, actions, and stage.

    Attributes:
        event: Event that triggered the hook.
        terminal: Terminal or runtime handling the event.
        state: Application state shared with the runtime.
        host: Session handling the event.
        runtime: Runtime handling the event.
        surface: Active presentation surface.
        request: HTTP request that triggered the hook, if any.
        tick: Tick payload that triggered the hook, if any.
        keyboard: Keyboard payload that triggered the hook, if any.
        mouse: Mouse payload that triggered the hook, if any.
        cursor: Cursor controls for the active runtime.
        device: Device controls for the active runtime.
        actions: Synthetic action performer.
        stage: Current layout stage.
        focused_group: Name of the focused field group.

    Example:
        >>> def handle_key(ctx: Context[dict[str, int]]) -> None:
        ...     if ctx.keyboard is not None:
        ...         ctx.state["keys"] += 1
    """

    event: "Event"
    """Event that triggered the hook."""
    terminal: "Runtime[StateT]"
    """Terminal or offscreen session handling the event."""
    state: StateT
    """Application state shared with the runtime."""

    @property
    def host(self) -> "Runtime[StateT]":
        """Session handling the event."""
        return self.terminal

    @property
    def runtime(self) -> "Runtime[StateT]":
        """Runtime handling the event."""
        return self.terminal

    @property
    def surface(self) -> str:
        """Presentation surface: ``"terminal"``, ``"web"``, or
        ``"offscreen"``.
        """
        surface = getattr(self.terminal, "surface", None)
        if isinstance(surface, str):
            return surface
        is_offscreen = getattr(self.terminal, "_session", None)
        session = getattr(self.terminal, "session", None)
        controller = session if session is not None else is_offscreen
        if controller is not None and getattr(
            controller, "is_offscreen", False
        ):
            return "offscreen"
        return "terminal"

    @property
    def request(self) -> "Request | None":
        """HTTP request that triggered the hook, if any."""
        return getattr(self.terminal, "_beta_request", None)

    @property
    def tick(self) -> "TickEventData | None":
        """Tick payload when this context was triggered by a tick."""
        return self.event.tick_event

    @property
    def keyboard(self) -> "KeyboardEventData | None":
        """Keyboard sub-event when triggered by a keyboard event."""
        return self.event.keyboard_event

    @property
    def mouse(self) -> "MouseEventData | None":
        """Mouse sub-event when triggered by a mouse event."""
        return self.event.mouse_event

    def get_state(self) -> StateT:
        """Return the shared application state.

        Raises:
            RuntimeError: If no state was attached to this context.
        """
        if self.state is None:
            raise RuntimeError("No state attached to this context.")
        return self.state

    @property
    def cursor(self) -> "Cursor":
        """Cursor / caret controls for the active runtime."""
        return self.terminal.cursor

    @property
    def device(self) -> "Device":
        """Device controls for the active runtime."""
        return self.terminal.device

    @property
    def actions(self) -> "Actions":
        """Perform synthetic input and requests."""
        return self.terminal.actions

    @property
    def stage(self) -> "Stage":
        """Layout map and cell-level paint helpers."""
        return self.terminal.stage

    def focus(self, group: str) -> bool:
        """Focus the field labeled ``group`` on any attached grid."""
        focus_group = getattr(self.terminal, "focus_group", None)
        if callable(focus_group):
            return bool(focus_group(group))
        return bool(self.terminal.focus(group))

    def blur(self) -> None:
        """Clear field focus on the active runtime."""
        blur_field = getattr(self.terminal, "blur_field", None)
        if callable(blur_field):
            blur_field()
            return
        blur = getattr(self.terminal, "blur", None)
        if callable(blur):
            blur()

    @property
    def render_size(self) -> "Breakpoint":
        """Current viewport breakpoint tier.

        The same value ``grid_render_<size>`` / ``compose_<size>`` dispatch
        on — one of ``"extra_small"``, ``"small"``, ``"medium"``,
        ``"large"``, ``"extra_large"`` — derived from the live window
        width. Read it from any hook to branch on size without declaring a
        per-tier render method.
        """
        from xnano.beta.utils.responsive import breakpoint_for_width

        return breakpoint_for_width(self.terminal.size[0])

    @property
    def focused_group(self) -> str | None:
        """``group`` of the currently focused field, or ``None``."""
        return self.terminal.focused_group

    def is_focused(self, group: str) -> bool:
        """Return whether the field labeled ``group`` currently holds focus."""
        return self.focused_group == group

    def call_soon(self, callback: "Callable[..., Any]", *args: Any) -> None:
        """Schedule ``callback`` to run on the UI thread before the next pump.

        The thread-safe bridge for updating grid state from a worker thread:
        the callback runs on the runtime's own thread, so it can freely mutate
        components/fields without racing the renderer.
        """
        self.terminal.call_soon(callback, *args)

    def field_area(self, name: str) -> "Area | None":
        """Return the last painted area for field ``name``, if known.

        Reads the always-on layout map so viewports and chrome math can use
        measured slot sizes instead of guessing.
        """
        return self.stage.get_area(name)

    def scroll(self, group: str) -> "ScrollHandle | None":
        """Return a scroll handle for ``Field(scroll=...)`` labeled ``group``."""
        from xnano.beta.utils.focus import scroll_handle_for_group

        return scroll_handle_for_group(self.terminal, group)

    def get_scroll(self, group: str) -> "ScrollHandle | None":
        """Return scroll state for ``group``, or ``None`` if it is unavailable."""
        return self.scroll(group)

    def with_event(self, event: "Event") -> "Context[StateT]":
        """Return a copy carrying a different event."""
        return dataclasses.replace(self, event=event)

    def with_scope(self, **kwargs: Any) -> "Context[StateT]":
        """Return a shallow copy with the given fields replaced."""
        return dataclasses.replace(self, **kwargs)

    def has_clipboard_event(self) -> bool:
        """Return whether this context contains a clipboard event."""
        return self.event.is_clipboard_event()

    def has_focus_event(self) -> bool:
        """Return whether this is a focus event."""
        return self.event.is_focus_event()

    def has_keyboard_event(self) -> bool:
        """Return whether this is a keyboard event."""
        return self.event.is_keyboard_event()

    def has_mouse_event(self) -> bool:
        """Return whether this is a mouse event."""
        return self.event.is_mouse_event()

    def has_resize_event(self) -> bool:
        """Return whether this is a resize event."""
        return self.event.is_resize_event()


__all__ = ("Context",)
