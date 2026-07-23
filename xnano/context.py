"""xnano.context

---

``Context`` passed into ``@on_*`` handlers: event, host, state, and
shortcuts for cursor, device, actions, and stage.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from typing_extensions import deprecated

if TYPE_CHECKING:
    from xnano._types import ScrollHandle
    from xnano.core.actions import Actions
    from xnano.core.hosts import AbstractHost
    from xnano.core.stage import Stage
    from xnano.events import (
        Event,
        KeyboardEventData,
        MouseEventData,
    )
    from xnano.terminal.cursor import TerminalCursor
    from xnano.terminal.device import TerminalDevice
    from xnano.terminal.terminal import Terminal


StateT = TypeVar("StateT")


@deprecated(
    "'xnano.Context' is deprecated and will be removed in v1.2; use "
    "'xnano.beta.Context' instead.",
    category=DeprecationWarning,
    stacklevel=2,
)
@dataclasses.dataclass(slots=True, frozen=True)
class Context(Generic[StateT]):
    """Runtime context passed into every ``@on_*`` hook handler.

    Carries the event, active host, and optional app state, plus shortcuts
    for cursor, device, actions, and stage. Built by the host — do not
    construct this yourself.
    """

    event: Event | None
    terminal: "Terminal[StateT]"
    state: StateT

    @property
    def host(self) -> "AbstractHost":
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
    def cursor(self) -> "TerminalCursor":
        """Cursor / caret controls for the active host (show, hide, style)."""
        return self.terminal.cursor

    @property
    def device(self) -> "TerminalDevice":
        """Device controls for the active host (title, clear, size, clipboard)."""
        return self.terminal.device

    @property
    def actions(self) -> "Actions":
        """Perform synthetic input and requests (``press``, ``click``, …)."""
        return self.terminal.actions

    @property
    def stage(self) -> "Stage":
        """Layout map and cell-level paint / wireframe for the active host."""
        return self.terminal.stage

    def focus(self, group: str) -> bool:
        """Focus the field labeled ``group``, on any attached grid.

        Terminal-global — no grid reference or nesting knowledge required.
        See ``Field(group=...)``.
        """
        return self.terminal.focus_group(group)

    @property
    def focused_group(self) -> str | None:
        """``group`` of the currently focused field, or ``None``."""
        return self.terminal.focused_group

    def is_focused(self, group: str) -> bool:
        """Return whether the field labeled ``group`` currently holds focus."""
        return self.focused_group == group

    def scroll(self, group: str) -> "ScrollHandle | None":
        """Return a scroll handle for the ``Field(scroll=...)`` field
        labeled ``group``, or ``None`` when no such field is attached.

            ctx.scroll("transcript").to_bottom()
            ctx.scroll("transcript").follow = True
        """
        from xnano._types import scroll_handle_for_group

        return scroll_handle_for_group(self.terminal, group)

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
