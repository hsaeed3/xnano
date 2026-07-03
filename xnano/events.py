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


class KeyboardEnhancementFlags:
    """Keyboard enhancement protocol flags."""

    __slots__ = ("_inner",)
    _inner: _core.KeyboardEnhancementFlags

    def __init__(self) -> None:
        raise TypeError(
            "KeyboardEnhancementFlags instances are created via class methods."
        )

    @classmethod
    def disambiguate_escape_codes(cls) -> KeyboardEnhancementFlags:
        """Return the disambiguate escape codes flag."""
        return cls._from_core(
            _core.KeyboardEnhancementFlags.DISAMBIGUATE_ESCAPE_CODES
        )

    @classmethod
    def report_event_types(cls) -> KeyboardEnhancementFlags:
        """Return the report event types flag."""
        return cls._from_core(
            _core.KeyboardEnhancementFlags.REPORT_EVENT_TYPES
        )

    @classmethod
    def report_alternate_keys(cls) -> KeyboardEnhancementFlags:
        """Return the report alternate keys flag."""
        return cls._from_core(
            _core.KeyboardEnhancementFlags.REPORT_ALTERNATE_KEYS
        )

    @classmethod
    def report_all_keys_as_escape_codes(cls) -> KeyboardEnhancementFlags:
        """Return the report all keys as escape codes flag."""
        return cls._from_core(
            _core.KeyboardEnhancementFlags.REPORT_ALL_KEYS_AS_ESCAPE_CODES
        )

    @classmethod
    def _from_core(
        cls,
        flags: _core.KeyboardEnhancementFlags,
    ) -> KeyboardEnhancementFlags:
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", flags)
        return obj

    def _to_core(self) -> _core.KeyboardEnhancementFlags:
        return self._inner

    def __or__(
        self, other: KeyboardEnhancementFlags
    ) -> KeyboardEnhancementFlags:
        return self._from_core(self._inner | other._inner)

    def __repr__(self) -> str:
        return repr(self._inner)


def enable_mouse_capture() -> None:
    """Enable mouse event capture."""
    _core.enable_mouse_capture()


def disable_mouse_capture() -> None:
    """Disable mouse event capture."""
    _core.disable_mouse_capture()


def enable_bracketed_paste() -> None:
    """Enable bracketed paste mode."""
    _core.enable_bracketed_paste()


def disable_bracketed_paste() -> None:
    """Disable bracketed paste mode."""
    _core.disable_bracketed_paste()


def enable_focus_change() -> None:
    """Enable focus change events."""
    _core.enable_focus_change()


def disable_focus_change() -> None:
    """Disable focus change events."""
    _core.disable_focus_change()


def push_keyboard_enhancement_flags(
    flags: KeyboardEnhancementFlags,
) -> None:
    """Push keyboard enhancement flags to the terminal."""
    _core.push_keyboard_enhancement_flags(flags._to_core())


def pop_keyboard_enhancement_flags() -> None:
    """Pop keyboard enhancement flags from the terminal."""
    _core.pop_keyboard_enhancement_flags()


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
    "KeyboardEnhancementFlags",
    "disable_bracketed_paste",
    "disable_focus_change",
    "disable_mouse_capture",
    "dispatch",
    "enable_bracketed_paste",
    "enable_focus_change",
    "enable_mouse_capture",
    "poll_event",
    "pop_keyboard_enhancement_flags",
    "push_keyboard_enhancement_flags",
    "read_event",
)
