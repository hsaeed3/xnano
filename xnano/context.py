"""xnano.context"""

from __future__ import annotations

import dataclasses
from typing import Any, Generic, TypeVar, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from xnano.component import Component
    from xnano.keyboard import KeyboardEvent
    from xnano.mouse import MouseEvent

StateT = TypeVar("StateT")


@dataclasses.dataclass
class Context(Generic[StateT]):
    """Execution context for component hooks, state access, and updates.

    Attributes:
        component: The component instance associated with this context.
        event: The event that triggered this hook, if any.
    """

    component: Component[StateT]
    """The component instance associated with this context."""

    event: KeyboardEvent | MouseEvent | None = None
    """The event that triggered this hook, if any."""

    @property
    def state(self) -> StateT:
        """The current state of the component."""
        return self.component.state

    @property
    def keyboard(self) -> KeyboardEvent | None:
        """The keyboard event, or None if not triggered by keyboard."""
        from xnano.keyboard import KeyboardEvent

        return self.event if isinstance(self.event, KeyboardEvent) else None

    @property
    def mouse(self) -> MouseEvent | None:
        """The mouse event, or None if not triggered by mouse."""
        from xnano.mouse import MouseEvent

        return self.event if isinstance(self.event, MouseEvent) else None

    def update(self, *arguments: StateT, **changes: Any) -> None:
        """Update the component's state.

        If a single positional argument is provided, it replaces the state.
        If keyword changes are provided, it performs a partial update on the
        state (supporting dataclasses, Pydantic models, and dicts).
        """
        current_state = self.component.state

        if arguments:
            new_state = arguments[0]
        elif changes:
            state_any: Any = current_state
            if hasattr(state_any, "model_copy"):
                new_state = state_any.model_copy(update=changes)
            elif hasattr(state_any, "copy"):
                new_state = state_any.copy(update=changes)
            elif dataclasses.is_dataclass(state_any):
                new_state = dataclasses.replace(state_any, **changes)
            elif isinstance(state_any, dict):
                new_state = {**state_any, **changes}
            else:
                raise TypeError(
                    f"Cannot perform partial update on state of type "
                    f"{type(current_state).__name__!r}. "
                    f"Expected dataclass, Pydantic model, or dict."
                )
        else:
            return

        self.component.update_state(cast(StateT, new_state))
