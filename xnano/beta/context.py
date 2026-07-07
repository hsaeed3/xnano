"""xnano.beta.context"""

from __future__ import annotations

import dataclasses
from typing import Any, Generic, TypeVar, TYPE_CHECKING

from xnano.beta.events import (
    Event,
    KeyboardEventData,
    MouseEventData,
)

if TYPE_CHECKING:
    from xnano.beta.terminal import Terminal


StateT = TypeVar("StateT")


@dataclasses.dataclass(slots=True, frozen=True)
class Context(Generic[StateT]):
    """Event hook execution context passed to every ``@on_<event>`` handler."""

    event: Event | None
    terminal: "Terminal[StateT] | None"
    state: StateT | None

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
    def cursor(self) -> Any:
        """Live cursor controller, forwarded from the active terminal."""
        return None if self.terminal is None else self.terminal.cursor

    @property
    def device(self) -> Any:
        """Live device controller, forwarded from the active terminal."""
        return None if self.terminal is None else self.terminal.device

    def with_scope(self, **kwargs: Any) -> "Context[StateT]":
        """Return a shallow copy with the given fields replaced."""
        return dataclasses.replace(self, **kwargs)
