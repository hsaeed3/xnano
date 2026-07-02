"""xnano.component

---

Component base class and lifecycle system.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any, Callable, Generic, TypeVar

from xnano.context import Context
from xnano.layout import Rectangle

StateT = TypeVar("StateT")


@dataclasses.dataclass
class Component(abc.ABC, Generic[StateT]):
    """Base class for all declarative, stateful terminal components.

    Attributes:
        state: The internal state of the component.
        visible: Whether the component is rendered on the screen.
        focused: Whether the component currently accepts keyboard focus.
    """

    state: StateT
    """The internal state of the component."""

    visible: bool = dataclasses.field(default=True, init=False)
    """Whether the component is rendered on the screen."""

    focused: bool = dataclasses.field(default=False, init=False)
    """Whether the component currently accepts keyboard focus."""

    _keyboard_handlers: list[
        tuple[list[Any], Callable[[Context[StateT]], Any]]
    ] = dataclasses.field(default_factory=list, init=False, repr=False)
    _mouse_handlers: list[
        tuple[list[Any], Callable[[Context[StateT]], Any]]
    ] = dataclasses.field(default_factory=list, init=False, repr=False)
    _on_update_callbacks: list[Callable[[Component[StateT]], None]] = (
        dataclasses.field(default_factory=list, init=False, repr=False)
    )

    def __post_init__(self) -> None:
        keyboard_handlers = []
        mouse_handlers = []

        for name in dir(self):
            if name.startswith("__"):
                continue
            member = getattr(self, name, None)
            if member is None:
                continue

            if hasattr(member, "__xnano_keyboard_bindings__"):
                bindings = getattr(member, "__xnano_keyboard_bindings__")
                keyboard_handlers.append((bindings, member))

            if hasattr(member, "__xnano_mouse_kinds__"):
                kinds = getattr(member, "__xnano_mouse_kinds__")
                mouse_handlers.append((kinds, member))

        object.__setattr__(self, "_keyboard_handlers", keyboard_handlers)
        object.__setattr__(self, "_mouse_handlers", mouse_handlers)

    @abc.abstractmethod
    def render(self, area: Rectangle) -> Any:
        """Render the component into the specified layout region.

        Args:
            area: The rectangular screen region available for this component.

        Returns:
            A renderable widget or another component instance.
        """
        pass

    def update(self, **changes: Any) -> None:
        """Update component properties dynamically and notify listeners.

        Args:
            **changes: The field values to update on the component.
        """
        for key, value in changes.items():
            if not hasattr(self, key):
                raise AttributeError(
                    f"Component {self.__class__.__name__} has no attribute {key}"
                )
            object.__setattr__(self, key, value)

        for callback in self._on_update_callbacks:
            callback(self)

    def update_state(self, new_state: StateT) -> None:
        """Update the component state and notify listeners.

        Args:
            new_state: The new state value.
        """
        object.__setattr__(self, "state", new_state)
        for callback in self._on_update_callbacks:
            callback(self)

    def register_on_update(self, callback: Callable[[Any], None]) -> None:
        """Register a callback to be invoked when the component state changes.

        Args:
            callback: The callback function.
        """
        self._on_update_callbacks.append(callback)

    def dispatch(self, context: Context[StateT]) -> bool:
        """Dispatch the event inside the context to matching hooks on this component.

        Args:
            context: The context containing the event and state.

        Returns:
            True if the event was handled by one of the hooks, False otherwise.
        """
        handled = False
        event = context.event
        if event is None:
            return False

        from xnano.keyboard import KeyboardEvent
        from xnano.mouse import MouseEvent

        if isinstance(event, KeyboardEvent):
            if event.is_press:
                for bindings, handler in self._keyboard_handlers:
                    if event.matches_any(*bindings):
                        handler(context)
                        handled = True

        elif isinstance(event, MouseEvent):
            for kinds, handler in self._mouse_handlers:
                if event.kind in kinds:
                    handler(context)
                    handled = True

        return handled
