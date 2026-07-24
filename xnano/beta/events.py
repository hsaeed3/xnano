"""xnano.beta.events

---

Inspect keyboard, mouse, resize, focus, and clipboard events.
"""

from __future__ import annotations

import dataclasses
from typing import Any, ClassVar, Literal, TypeAlias, cast

from xnano_core.core import CoreEvent, CoreKeyBinding

from xnano.beta.types import (
    KeyboardBinding,
    KeyboardKey,
    KeyboardModifier,
    MouseButton,
)

EventDataType: TypeAlias = Literal[
    "keyboard", "mouse", "resize", "clipboard", "focus", "tick", "other"
]
"""Public event payload category."""


KeyboardEventKind: TypeAlias = Literal["press", "release", "repeat"]
"""Keyboard transition reported by a runtime."""


MouseEventKind: TypeAlias = Literal[
    "press",
    "release",
    "drag",
    "move",
    "scroll_up",
    "scroll_down",
    "scroll_left",
    "scroll_right",
]
"""Mouse movement, button, or wheel transition."""


FocusEventKind: TypeAlias = Literal[
    "gained", "lost", "field_gained", "field_lost"
]
"""Terminal or field focus transition."""

_KEY_ALIASES = {"esc": "escape", "return": "enter", " ": "space"}


def normalize_keyboard_binding(
    binding: str,
) -> tuple[frozenset[str], str]:
    """Normalize a keyboard binding for comparison.

    Args:
        binding: Binding such as ``"ctrl+s"``.

    Returns:
        Normalized modifiers and primary key.
    """
    parts = [
        part.strip().lower() for part in binding.split("+") if part.strip()
    ]
    if not parts:
        return (frozenset(), "")
    return (
        frozenset(
            part for part in parts[:-1] if part in ("ctrl", "alt", "shift")
        ),
        _KEY_ALIASES.get(parts[-1], parts[-1]),
    )


def parse_binding_tuple(
    binding: str,
) -> tuple[list[KeyboardModifier], str]:
    """Split a binding into modifiers and its primary key.

    Args:
        binding: Binding such as ``"shift+tab"``.

    Returns:
        Modifier names and primary key.
    """
    modifiers, key = normalize_keyboard_binding(binding)
    return (
        [cast(KeyboardModifier, modifier) for modifier in modifiers],
        "esc" if key == "escape" else key,
    )


@dataclasses.dataclass(slots=True, frozen=True)
class AbstractEventData:
    """Base for event payloads.

    Attributes:
        type: Payload category.
    """

    type: ClassVar[EventDataType] = "other"
    """Payload category."""


@dataclasses.dataclass(slots=True, frozen=True)
class KeyboardEventData(AbstractEventData):
    """Keyboard input and its normalized binding.

    Attributes:
        type: Payload category, always ``"keyboard"``.
        binding: Normalized binding such as ``"ctrl+s"``.
        key: Primary key.
        kind: Keyboard transition.
        modifiers: Modifier keys held during the event.
        character: Typed character, when available.

    Examples:
        ```python
        event = KeyboardEventData.from_binding("ctrl+s")
        if event.matches("ctrl+s"):
            save()
        ```
    """

    type: ClassVar[Literal["keyboard"]] = "keyboard"
    """Payload category."""
    _native_event: object | None = None
    _kind: KeyboardEventKind = "press"
    _binding: str | None = None
    _character: str | None = None

    @classmethod
    def from_binding(
        cls,
        binding: str,
        *,
        kind: KeyboardEventKind = "press",
        character: str | None = None,
    ) -> "KeyboardEventData":
        """Create keyboard data from a binding string.

        Args:
            binding: Keyboard binding to synthesize.
            kind: Keyboard transition.
            character: Text character, when the binding represents one.

        Returns:
            Synthetic keyboard event data.
        """
        _, key = parse_binding_tuple(binding)
        if character is None:
            character = (
                key if len(key) == 1 else (" " if key == "space" else None)
            )
        return cls(_kind=kind, _binding=binding, _character=character)

    @property
    def binding(self) -> KeyboardBinding:
        """Normalized binding represented by this event."""
        if self._binding is not None:
            return self._binding
        if self._native_event is None:
            return ""
        modifiers: list[str] = []
        native: Any = self._native_event
        native_modifiers = getattr(native, "modifiers", None)
        if native_modifiers is not None:
            if native_modifiers.control():
                modifiers.append("ctrl")
            if native_modifiers.alt():
                modifiers.append("alt")
            if native_modifiers.shift():
                modifiers.append("shift")
        key = str(getattr(native, "code_name", "")).lower()
        character = getattr(native, "char", lambda: None)()
        if character:
            key = str(character)
        return "+".join((*modifiers, key))

    @property
    def key(self) -> KeyboardKey | str | None:
        """Primary key represented by this event."""
        _, key = parse_binding_tuple(str(self.binding))
        return key or None

    @property
    def kind(self) -> KeyboardEventKind:
        """Keyboard transition represented by this event."""
        if self._native_event is None:
            return self._kind
        native: Any = self._native_event
        return cast(KeyboardEventKind, native.keyboard_kind_str())

    @property
    def modifiers(self) -> list[KeyboardModifier]:
        """Modifier keys held during this event."""
        modifiers, _ = parse_binding_tuple(str(self.binding))
        return modifiers

    @property
    def character(self) -> str | None:
        """Typed character, when the key produces text."""
        if self._character is not None:
            return self._character
        if self._native_event is not None:
            native: Any = self._native_event
            value = native.char() or native.char_value()
            return None if value is None else str(value)
        key = self.key
        return key if isinstance(key, str) and len(key) == 1 else None

    def matches(self, *bindings: KeyboardBinding) -> bool:
        """Return whether this event matches any binding.

        Args:
            *bindings: Candidate keyboard bindings.

        Returns:
            Whether at least one binding matches.
        """
        if self._native_event is not None:
            native_event: Any = self._native_event
            for binding in bindings:
                try:
                    if CoreKeyBinding.parse(str(binding)).matches(
                        native_event
                    ):
                        return True
                except Exception:
                    continue
            return False
        own = normalize_keyboard_binding(str(self.binding))
        return any(
            normalize_keyboard_binding(str(binding)) == own
            for binding in bindings
        )


@dataclasses.dataclass(slots=True, frozen=True)
class MouseEventData(AbstractEventData):
    """Mouse input at a cell coordinate.

    Attributes:
        kind: Mouse transition.
        x: Zero-based cell column.
        y: Zero-based cell row.
        button: Button involved in the transition.
        field: Field under the pointer for synthetic or web input.
        group: Field group under the pointer.

    Examples:
        ```python
        event = MouseEventData(kind="press", x=12, y=4, button="left")
        ```
    """

    type: ClassVar[Literal["mouse"]] = "mouse"
    """Payload category."""
    kind: MouseEventKind
    """Mouse transition."""
    x: int
    """Zero-based cell column."""
    y: int
    """Zero-based cell row."""
    button: MouseButton = "unknown"
    """Button involved in the transition."""
    field: str | None = None
    """Field under the pointer."""
    group: str | None = None
    """Field group under the pointer."""


@dataclasses.dataclass(slots=True, frozen=True)
class ResizeEventData(AbstractEventData):
    """New viewport dimensions.

    Attributes:
        width: Viewport width in cells.
        height: Viewport height in cells.
    """

    type: ClassVar[Literal["resize"]] = "resize"
    """Payload category."""
    width: int
    """Viewport width in cells."""
    height: int
    """Viewport height in cells."""


@dataclasses.dataclass(slots=True, frozen=True)
class ClipboardEventData(AbstractEventData):
    """Text received from paste or clipboard input.

    Attributes:
        text: Pasted text, when available.
    """

    type: ClassVar[Literal["clipboard"]] = "clipboard"
    """Payload category."""
    text: str | None = None
    """Pasted text."""


@dataclasses.dataclass(slots=True, frozen=True)
class FocusEventData(AbstractEventData):
    """Terminal or field focus transition.

    Attributes:
        kind: Focus transition.
        field: Field name for field focus.
        group: Shared focus group for field focus.
    """

    type: ClassVar[Literal["focus"]] = "focus"
    """Payload category."""
    kind: FocusEventKind
    """Focus transition."""
    field: str | None = None
    """Focused field name."""
    group: str | None = None
    """Focused field group."""


@dataclasses.dataclass(slots=True, frozen=True)
class TickEventData(AbstractEventData):
    """Elapsed time reported by the runtime clock.

    Attributes:
        elapsed_ms: Milliseconds since the previous tick.
    """

    type: ClassVar[Literal["tick"]] = "tick"
    """Payload category."""
    elapsed_ms: int = 0
    """Milliseconds since the previous tick."""


EventData: TypeAlias = (
    KeyboardEventData
    | MouseEventData
    | ResizeEventData
    | ClipboardEventData
    | FocusEventData
    | TickEventData
)
"""Payload carried by a public ``Event``."""


def _data_from_core(event: CoreEvent) -> EventData | None:
    kind = event.kind_str()
    if kind == "key" and event.key is not None:
        return KeyboardEventData(_native_event=event.key)
    if kind == "mouse" and event.mouse is not None:
        mouse = event.mouse
        button = mouse.xnano_button_str()
        return MouseEventData(
            kind=mouse.xnano_kind_str(),
            x=mouse.x,
            y=mouse.y,
            button="unknown" if button == "none" else button,
        )
    if (
        kind == "resize"
        and event.width is not None
        and event.height is not None
    ):
        return ResizeEventData(width=event.width, height=event.height)
    if kind == "paste":
        return ClipboardEventData(text=event.paste)
    if kind == "focus_gained":
        return FocusEventData(kind="gained")
    if kind == "focus_lost":
        return FocusEventData(kind="lost")
    if kind == "tick" and event.tick is not None:
        return TickEventData(elapsed_ms=event.tick.elapsed_ms)
    return None


@dataclasses.dataclass(slots=True, frozen=True, repr=False)
class Event:
    """Unified event produced by native input, web input, or an action.

    Attributes:
        data: Public event payload.
        type: Payload category.
        keyboard_event: Keyboard payload, when present.
        mouse_event: Mouse payload, when present.
        resize_event: Resize payload, when present.
        clipboard_event: Clipboard payload, when present.
        focus_event: Focus payload, when present.
        tick_event: Tick payload, when present.

    Examples:
        ```python
        event = Event.from_data(KeyboardEventData.from_binding("enter"))
        if event.keyboard_event and event.keyboard_event.matches("enter"):
            submit()
        ```
    """

    _core_event: CoreEvent | None = None
    _event_data: EventData | None = None

    def __post_init__(self) -> None:
        if self._core_event is None and self._event_data is None:
            raise ValueError("Event requires native or synthetic data")

    @classmethod
    def from_data(cls, data: EventData) -> "Event":
        """Create an event from a synthetic payload.

        Args:
            data: Public event payload.

        Returns:
            Event wrapping the payload.
        """
        return cls(_event_data=data)

    @property
    def data(self) -> EventData:
        """Public payload, converted lazily from native input."""
        data = self._event_data
        if data is None and self._core_event is not None:
            data = _data_from_core(self._core_event)
            object.__setattr__(self, "_event_data", data)
        if data is None:
            raise ValueError("Core event has no public payload")
        return data

    @property
    def type(self) -> EventDataType:
        """Category of the event payload."""
        return self.data.type

    def is_clipboard_event(self) -> bool:
        """Return whether this is clipboard input."""
        return self.type == "clipboard"

    def is_focus_event(self) -> bool:
        """Return whether this is a focus transition."""
        return self.type == "focus"

    def is_keyboard_event(self) -> bool:
        """Return whether this is keyboard input."""
        return self.type == "keyboard"

    def is_mouse_event(self) -> bool:
        """Return whether this is mouse input."""
        return self.type == "mouse"

    def is_resize_event(self) -> bool:
        """Return whether this is a viewport resize."""
        return self.type == "resize"

    def is_tick_event(self) -> bool:
        """Return whether this is a runtime clock tick."""
        return self.type == "tick"

    @property
    def keyboard_event(self) -> KeyboardEventData | None:
        """Keyboard payload, or ``None``."""
        return self.data if isinstance(self.data, KeyboardEventData) else None

    @property
    def keyboard_key(self) -> KeyboardKey | str | None:
        """Primary keyboard key, or ``None``."""
        return None if self.keyboard_event is None else self.keyboard_event.key

    @property
    def keyboard_event_kind(self) -> KeyboardEventKind | None:
        """Keyboard event kind when this is a keyboard event."""
        keyboard = self.keyboard_event
        return None if keyboard is None else keyboard.kind

    @property
    def keyboard_modifiers(self) -> list[KeyboardModifier]:
        """Modifier keys when this is a keyboard event."""
        keyboard = self.keyboard_event
        return [] if keyboard is None else keyboard.modifiers

    @property
    def mouse_event(self) -> MouseEventData | None:
        """Mouse payload, or ``None``."""
        return self.data if isinstance(self.data, MouseEventData) else None

    @property
    def mouse_position(self) -> tuple[int, int] | None:
        """Mouse cell position, or ``None``."""
        mouse = self.mouse_event
        return None if mouse is None else (mouse.x, mouse.y)

    @property
    def mouse_event_kind(self) -> MouseEventKind | None:
        """Mouse event kind when this is a mouse event."""
        mouse = self.mouse_event
        return None if mouse is None else mouse.kind

    @property
    def mouse_button(self) -> MouseButton | None:
        """Mouse button when this is a mouse event."""
        mouse = self.mouse_event
        return None if mouse is None else mouse.button

    @property
    def resize_event(self) -> ResizeEventData | None:
        """Resize payload, or ``None``."""
        return self.data if isinstance(self.data, ResizeEventData) else None

    @property
    def resize_size(self) -> tuple[int, int] | None:
        """Viewport size from a resize event, or ``None``."""
        resize = self.resize_event
        return None if resize is None else (resize.width, resize.height)

    @property
    def clipboard_event(self) -> ClipboardEventData | None:
        """Clipboard payload, or ``None``."""
        return self.data if isinstance(self.data, ClipboardEventData) else None

    @property
    def clipboard_text(self) -> str | None:
        """Pasted text when this is a clipboard event."""
        clipboard = self.clipboard_event
        return None if clipboard is None else clipboard.text

    @property
    def focus_event(self) -> FocusEventData | None:
        """Focus payload, or ``None``."""
        return self.data if isinstance(self.data, FocusEventData) else None

    @property
    def tick_event(self) -> TickEventData | None:
        """Tick payload, or ``None``."""
        return self.data if isinstance(self.data, TickEventData) else None


def event_from_core(core_event: CoreEvent) -> Event:
    """Convert a native core event into the public ``Event`` shape.

    Browser input and synthetic actions should construct the same public
    classes; this is the single native conversion path.

    Args:
        core_event: Event polled from ``CoreSession``.

    Returns:
        A public ``Event`` handlers cannot distinguish from other sources.
    """
    return Event(_core_event=core_event)


__all__ = (
    "AbstractEventData",
    "ClipboardEventData",
    "Event",
    "EventData",
    "EventDataType",
    "FocusEventData",
    "FocusEventKind",
    "KeyboardEventData",
    "KeyboardEventKind",
    "MouseEventData",
    "MouseEventKind",
    "ResizeEventData",
    "TickEventData",
    "event_from_core",
    "normalize_keyboard_binding",
    "parse_binding_tuple",
)
