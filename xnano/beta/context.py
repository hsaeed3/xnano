"""xnano.beta.context

---

Access the current event, application state, runtime, device, cursor, and
layout from an event hook.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from xnano.beta.actions import Actions
    from xnano.beta.core.stage import Stage
    from xnano.beta.cursor import Cursor
    from xnano.beta.device import Device
    from xnano.beta.events import (
        Event,
        KeyboardEventData,
        MouseEventData,
    )
    from xnano.beta.types import ScrollHandle


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

    event: "Event | None"
    """Event that triggered the hook."""
    terminal: Any
    """Terminal or offscreen session handling the event."""
    state: StateT
    """Application state shared with the runtime."""

    @property
    def host(self) -> Any:
        """Session handling the event."""
        return self.terminal

    @property
    def runtime(self) -> Any:
        """Runtime handling the event."""
        runtime = getattr(self.terminal, "runtime", None)
        return self.terminal if runtime is None else runtime

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
    def request(self) -> Any | None:
        """HTTP request that triggered the hook, if any."""
        return getattr(self.terminal, "_beta_request", None)

    @property
    def tick(self) -> Any | None:
        """Tick payload when this context was triggered by a tick."""
        event = self.event
        if event is None:
            return None
        # Tick hooks currently receive a context with no specialized
        # payload; expose interval metadata when present.
        return getattr(event, "tick_event", None)

    @property
    def keyboard(self) -> "KeyboardEventData | None":
        """Keyboard sub-event when triggered by a keyboard event."""
        return None if self.event is None else self.event.keyboard_event

    @property
    def mouse(self) -> "MouseEventData | None":
        """Mouse sub-event when triggered by a mouse event."""
        return None if self.event is None else self.event.mouse_event

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
    def focused_group(self) -> str | None:
        """``group`` of the currently focused field, or ``None``."""
        return self.terminal.focused_group

    def is_focused(self, group: str) -> bool:
        """Return whether the field labeled ``group`` currently holds focus."""
        return self.focused_group == group

    def scroll(self, group: str) -> "ScrollHandle | None":
        """Return a scroll handle for ``Field(scroll=...)`` labeled ``group``."""
        from xnano.beta.utils.focus import scroll_handle_for_group

        return scroll_handle_for_group(self.terminal, group)

    def get_scroll(self, group: str) -> "ScrollHandle | None":
        """Return scroll state for ``group``, or ``None`` if it is unavailable."""
        return self.scroll(group)

    def with_event(self, event: "Event | None") -> "Context[StateT]":
        """Return a copy carrying a different event."""
        return dataclasses.replace(self, event=event)

    def has_clipboard_event(self) -> bool:
        """Return whether this context contains a clipboard event."""
        return self.event is not None and self.event.is_clipboard_event()

    def has_focus_event(self) -> bool:
        """Return whether this is a focus event."""
        return self.event is not None and self.event.is_focus_event()

    def has_keyboard_event(self) -> bool:
        """Return whether this is a keyboard event."""
        return self.event is not None and self.event.is_keyboard_event()

    def has_mouse_event(self) -> bool:
        """Return whether this is a mouse event."""
        return self.event is not None and self.event.is_mouse_event()

    def has_resize_event(self) -> bool:
        """Return whether this is a resize event."""
        return self.event is not None and self.event.is_resize_event()


__all__ = ("Context",)
