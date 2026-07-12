"""xnano.context"""

from __future__ import annotations

import dataclasses
from typing import Any, Generic, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.core.actions import Actions
    from xnano.events import (
        Event,
        KeyboardEventData,
        MouseEventData,
    )
    from xnano.core.hosts import AbstractHost
    from xnano.core.stage import Stage
    from xnano.tui import Terminal
    from xnano.tui.cursor import TerminalCursor
    from xnano.tui.device import TerminalDevice


StateT = TypeVar("StateT")


@dataclasses.dataclass(slots=True, frozen=True)
class Context(Generic[StateT]):
    """Event hook execution context passed to every ``@on_<event>`` handler.

    This class should never be initialized directly, rather it is passed
    automatically by the live host session to all active & condition-fulfilling
    hooks.
    """

    event: Event | None
    terminal: "Terminal[StateT]"
    state: StateT | None

    @property
    def host(self) -> "Terminal[StateT] | AbstractHost":
        """Active host for this context (alias of ``terminal``).

        Named ``host`` so code that is interface-kind-agnostic can avoid
        the terminal-specific attribute name. Same object as ``terminal``.
        """
        return self.terminal

    @property
    def keyboard(self) -> KeyboardEventData | None:
        """Keyboard sub-event when this context was triggered by a keyboard event."""
        return None if self.event is None else self.event.keyboard_event

    @property
    def mouse(self) -> MouseEventData | None:
        """Mouse sub-event when this context was triggered by a mouse event."""
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
    def cursor(self) -> "TerminalCursor | None":
        """Live cursor controller, forwarded from the active host."""
        return None if self.terminal is None else self.terminal.cursor

    @property
    def device(self) -> "TerminalDevice | None":
        """Live device controller, forwarded from the active host."""
        return None if self.terminal is None else self.terminal.device

    @property
    def actions(self) -> "Actions | None":
        """Actions facade bound to the active host (perform / press / click)."""
        if self.terminal is None:
            return None
        getter = getattr(self.terminal, "actions", None)
        if getter is None:
            return None
        return getter if not callable(getter) else self.terminal.actions  # type: ignore[return-value]

    @property
    def stage(self) -> "Stage | None":
        """Stage facade for layout map / overlay paint / wireframe."""
        if self.terminal is None:
            return None
        if not hasattr(self.terminal, "stage"):
            return None
        return self.terminal.stage  # type: ignore[return-value]

    def with_scope(self, **kwargs: Any) -> "Context[StateT]":
        """Return a shallow copy with the given fields replaced."""
        return dataclasses.replace(self, **kwargs)

    def has_clipboard_event(self) -> bool:
        """Return whether this context contains a clipboard event.

        Returns:
            True if this context contains a clipboard event, False otherwise.
        """
        return self.event is not None and self.event.is_clipboard_event()

    def has_focus_event(self) -> bool:
        """Return whether this is a focus event.

        Returns:
            True if this context contains a focus event, False otherwise.
        """
        return self.event is not None and self.event.is_focus_event()

    def has_keyboard_event(self) -> bool:
        """Return whether this is a keyboard event.

        Returns:
            True if this context contains a keyboard event, False otherwise.
        """
        return self.event is not None and self.event.is_keyboard_event()

    def has_mouse_event(self) -> bool:
        """Return whether this is a mouse event.

        Returns:
            True if this context contains a mouse event, False otherwise.
        """
        return self.event is not None and self.event.is_mouse_event()

    def has_resize_event(self) -> bool:
        """Return whether this is a resize event.

        Returns:
            True if this context contains a resize event, False otherwise.
        """
        return self.event is not None and self.event.is_resize_event()


__all__ = ("Context",)
