"""xnano.events"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, TypeAlias, cast

import xnano._core as _core
from xnano.keyboard import KeyboardEvent
from xnano.mouse import MouseEvent


EventKind: TypeAlias = Literal["keyboard", "resize", "paste", "mouse", "other"]
"""The category of a terminal event."""


class Event:
    """A terminal input event."""

    __slots__ = ("_inner",)
    _inner: _core.Event

    def __init__(self) -> None:
        raise TypeError(
            "Event instances are created internally by the event system."
        )

    @classmethod
    def _from_core(cls, event: _core.Event) -> Event:
        """Construct from a native event."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", event)
        return obj

    def _to_core(self) -> _core.Event:
        """Return the native event."""
        return self._inner

    @property
    def kind(self) -> EventKind:
        """The event category: ``"keyboard"``, ``"resize"``, ``"paste"``, ``"mouse"``, or ``"other"``."""
        kind_val = self._inner.kind
        return "keyboard" if kind_val == "key" else cast(EventKind, kind_val)

    @property
    def keyboard(self) -> KeyboardEvent | None:
        """The keyboard event data, or ``None`` if this is not a keyboard event."""
        if self._inner.key is None:
            return None
        return KeyboardEvent._from_core(self._inner.key)

    @property
    def width(self) -> int | None:
        """Terminal width after a resize event, or ``None``."""
        return self._inner.width

    @property
    def height(self) -> int | None:
        """Terminal height after a resize event, or ``None``."""
        return self._inner.height

    @property
    def paste(self) -> str | None:
        """Pasted text content, or ``None``."""
        return self._inner.paste

    @property
    def mouse(self) -> MouseEvent | None:
        """The mouse event data, or ``None`` if this is not a mouse event."""
        if self._inner.mouse is None:
            return None
        return MouseEvent._from_core(self._inner.mouse)

    def __repr__(self) -> str:
        return repr(self._inner)


def poll_event(timeout_milliseconds: int) -> Event | None:
    """Poll for a terminal event with a timeout.

    Args:
        timeout_milliseconds: The timeout duration in milliseconds.
    """
    event = _core.poll_event(timeout_milliseconds)
    return Event._from_core(event) if event is not None else None


def read_event() -> Event:
    """Block until a terminal event is available and return it."""
    return Event._from_core(_core.read_event())


def dispatch(
    event: Event,
    target: Any | Sequence[Any],
) -> bool:
    """Dispatch an event to a component or sequence of components.

    Creates a Context and calls target.dispatch(context) on each target component
    until the event is handled.

    Args:
        event: The event to dispatch.
        target: A component or sequence of components to dispatch to.

    Returns:
        True if the event was handled by one of the components, False otherwise.
    """
    from xnano.context import Context

    inner_event = event.keyboard or event.mouse
    if inner_event is None:
        return False

    if isinstance(target, Sequence) and not isinstance(target, (str, bytes)):
        for component in target:
            if hasattr(component, "dispatch"):
                comp_any: Any = component
                context = Context(component=comp_any, event=inner_event)
                if comp_any.dispatch(context):
                    return True
        return False

    if hasattr(target, "dispatch"):
        target_any: Any = target
        context = Context(component=target_any, event=inner_event)
        return bool(target_any.dispatch(context))

    return False


__all__ = (
    "Event",
    "EventKind",
    "poll_event",
    "read_event",
    "dispatch",
)
