"""xnano.events"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeAlias, TypeVar, cast

import xnano._core as _core
from xnano.keyboard import KeyBinding, KeyEvent
from xnano.mouse import MouseEvent, MouseEventName


F = TypeVar("F", bound=Callable[..., Any])


EventKindName: TypeAlias = Literal["key", "resize", "paste", "mouse", "other"]
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
    def kind(self) -> EventKindName:
        """The event category: ``"key"``, ``"resize"``, ``"paste"``, ``"mouse"``, or ``"other"``."""
        return cast(EventKindName, self._inner.kind)

    @property
    def key(self) -> KeyEvent | None:
        """The key event data, or ``None`` if this is not a key event."""
        if self._inner.key is None:
            return None
        return KeyEvent._from_core(self._inner.key)

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


def poll_event(timeout_ms: int) -> Event | None:
    """Poll for a terminal event with a timeout."""
    event = _core.poll_event(timeout_ms)
    return Event._from_core(event) if event is not None else None


def read_event() -> Event:
    """Block until a terminal event is available and return it."""
    return Event._from_core(_core.read_event())


_KEY_BINDINGS_ATTR = "__xnano_key_bindings__"
_MOUSE_KINDS_ATTR = "__xnano_mouse_kinds__"


def on_key(*bindings: KeyBinding) -> Callable[[F], F]:
    """Decorator that marks a function as a key event handler."""

    def decorator(fn: F) -> F:
        existing = getattr(fn, _KEY_BINDINGS_ATTR, [])
        setattr(fn, _KEY_BINDINGS_ATTR, existing + list(bindings))
        return fn

    return decorator


def on_mouse(*kinds: MouseEventName) -> Callable[[F], F]:
    """Decorator that marks a function as a mouse event handler."""

    def decorator(fn: F) -> F:
        existing = getattr(fn, _MOUSE_KINDS_ATTR, [])
        setattr(fn, _MOUSE_KINDS_ATTR, existing + list(kinds))
        return fn

    return decorator


class EventHandler:
    """Collects key and mouse event handlers and dispatches events."""

    __slots__ = ("_key_handlers", "_mouse_handlers")

    def __init__(self) -> None:
        self._key_handlers: list[tuple[list[str], Callable[..., Any]]] = []
        self._mouse_handlers: list[tuple[list[str], Callable[..., Any]]] = []

    def on_key(self, *bindings: KeyBinding) -> Callable[[F], F]:
        """Register a key event handler on this dispatcher."""

        def decorator(fn: F) -> F:
            self._key_handlers.append((list(bindings), fn))
            return fn

        return decorator

    def on_mouse(self, *kinds: MouseEventName) -> Callable[[F], F]:
        """Register a mouse event handler on this dispatcher."""

        def decorator(fn: F) -> F:
            self._mouse_handlers.append((list(kinds), fn))
            return fn

        return decorator

    def register(self, fn: Callable[..., Any]) -> None:
        """Register a decorated handler function."""
        key_bindings = getattr(fn, _KEY_BINDINGS_ATTR, None)
        mouse_kinds = getattr(fn, _MOUSE_KINDS_ATTR, None)

        if key_bindings is None and mouse_kinds is None:
            raise ValueError(
                f"{fn!r} is not decorated with @on_key or @on_mouse"
            )

        if key_bindings:
            self._key_handlers.append((key_bindings, fn))
        if mouse_kinds:
            self._mouse_handlers.append((mouse_kinds, fn))

    def dispatch(self, event: Event) -> bool:
        """Dispatch an event to all matching registered handlers."""
        handled = False

        if event.kind == "key" and event.key is not None:
            key_event = event.key
            if key_event.is_press:
                for bindings, handler in self._key_handlers:
                    if key_event.matches_any(*bindings):
                        handler(key_event)
                        handled = True

        elif event.kind == "mouse" and event.mouse is not None:
            mouse_event = event.mouse
            for kinds, handler in self._mouse_handlers:
                if mouse_event.kind in kinds:
                    handler(mouse_event)
                    handled = True

        return handled

    def __repr__(self) -> str:
        return (
            f"EventHandler(key_handlers={len(self._key_handlers)}, "
            f"mouse_handlers={len(self._mouse_handlers)})"
        )


__all__ = (
    "Event",
    "EventHandler",
    "EventKindName",
    "on_key",
    "on_mouse",
    "poll_event",
    "read_event",
)