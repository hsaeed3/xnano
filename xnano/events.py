"""xnano.events"""

from __future__ import annotations

import abc
import dataclasses
from typing import (
    Any,
    ClassVar,
    Generic,
    Literal,
    TypeAlias,
    TypeVar,
    TypedDict,
    Union,
    TYPE_CHECKING,
)

from xnano_core.core import (
    CoreEvent,
    CoreKeyBinding,
    CoreTickEvent,
)

_BINDING_CACHE: dict[str, CoreKeyBinding] = {}

from xnano.utils.events import (
    get_keyboard_binding_tuple_from_native_event,
    get_keyboard_event_kind_from_native_event,
    get_mouse_event_kind_from_native_event,
    get_event_data_from_core_event,
)
from xnano.keyboard import (
    KnownKeyboardBinding,
    KeyboardBinding,
    KeyboardKey,
    KeyboardModifier,
)
from xnano.mouse import MouseButton

if TYPE_CHECKING:
    from xnano_core.rust import native


StateT = TypeVar("StateT")


EventData: TypeAlias = Union[
    "KeyboardEventData",
    "MouseEventData",
    "ResizeEventData",
    "ClipboardEventData",
    "FocusEventData",
]
"""The data / sub-event content available within an ``Event``.

Values:
    ``KeyboardEventData``: A keyboard event (a main keypress + optional modifiers)
    ``MouseEventData``: A mouse event (a button press or movement)
    ``ResizeEventData``: A terminal resize event
    ``ClipboardEventData``: A clipboard (paste) event
    ``FocusEventData``: A focus change event
"""


EventDataType: TypeAlias = Literal[
    "keyboard", "mouse", "resize", "clipboard", "focus", "other"
]
"""The general classification of the type of event data that has been
received within an ``Event``.

Values:
    "keyboard": A keyboard event (a main keypress + optional modifiers)
    "mouse": A mouse event (a button press or movement)
    "resize": A terminal resize event
    "clipboard": A clipboard event
    "focus": A focus event
    "other": A miscellaneous event
"""


_CORE_EVENT_TYPES: dict[str, EventDataType] = {
    "key": "keyboard",
    "mouse": "mouse",
    "resize": "resize",
    "paste": "clipboard",
    "focus_gained": "focus",
    "focus_lost": "focus",
}


KeyboardEventKind: TypeAlias = Literal["press", "release", "repeat"]
"""The kind of keyboard event data available within the ``KeyboardEventData``
of an ``Event``.

Values:
    "press": A key was pressed down.
    "release": A key was released.
    "repeat": A key was held down and is repeating.
"""


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
"""The kind of mouse event data available within the ``MouseEventData``
of an ``Event``.

Values:
    "press": A mouse button was pressed down.
    "release": A mouse button was released.
    "drag": A mouse button was held down and is dragging.
    "move": A mouse was moved.
    "scroll_up": The mouse wheel was scrolled up.
    "scroll_down": The mouse wheel was scrolled down.
    "scroll_left": The mouse wheel was scrolled left.
    "scroll_right": The mouse wheel was scrolled right.
"""


@dataclasses.dataclass(slots=True, frozen=True)
class AbstractEventData(abc.ABC):
    """Abstract base class for the data available within an ``Event``."""

    type: ClassVar[EventDataType]
    """The type / kind of this event data."""


@dataclasses.dataclass(slots=True, frozen=True)
class ClipboardEventData(AbstractEventData):
    """A clipboard paste event.

    Attributes:
        type: The type of this event (always "clipboard")
        text: The text that was pasted.
    """

    type: ClassVar[Literal["clipboard"]] = "clipboard"
    """The type of event this sub-event represents. Always "clipboard" for
    ``ClipboardEvent``.
    """
    text: str | None = None
    """The text that was pasted."""


FocusEventKind: TypeAlias = Literal[
    "gained",
    "lost",
    "field_gained",
    "field_lost",
]
"""How a focus change was triggered.

Values:
    ``"gained"`` / ``"lost"``: The terminal window gained or lost OS focus.
    ``"field_gained"`` / ``"field_lost"``: A grid field gained or lost
        application focus (editable ``Text`` input).
"""


@dataclasses.dataclass(slots=True, frozen=True)
class FocusEventData(AbstractEventData):
    """Focus change event — terminal window or grid field.

    Attributes:
        kind: Terminal gained/lost, or field gained/lost.
        field: Layout field name when ``kind`` is a field focus change.
    """

    type: ClassVar[Literal["focus"]] = "focus"
    """The type of event this sub-event represents. Always "focus" for
    ``FocusEvent``.
    """
    kind: FocusEventKind | None = None
    """Terminal or field focus transition kind."""
    field: str | None = None
    """Layout field name for field-level focus changes."""


def _set_keyboard_event_data_binding_tuple(
    event_data: KeyboardEventData,
) -> None:
    if not hasattr(event_data, "type") or not event_data.type == "keyboard":
        raise ValueError("Expected a KeyboardEventData instance.")
    try:
        binding_tuple = get_keyboard_binding_tuple_from_native_event(
            event=event_data._native_event
        )
    except Exception as e:
        raise ValueError(
            f"Error resolving the associated keyboard binding for event: {event_data!r}.\n"
            f"Error: {e!r}"
        ) from e

    object.__setattr__(event_data, "_binding_tuple", binding_tuple)


@dataclasses.dataclass(slots=True, frozen=True)
class KeyboardEventData(AbstractEventData):
    """A keyboard input event.

    Properties:
        type: The type of this event (always "keyboard")
        key: The keyboard key that was pressed or released on this event.
        modifiers: The modifiers that were held down in combination with the primary
            action key to create this keyboard binding.
        kind: The kind of event that was triggered on the keyboard. This can be one of:
            - "press": A keyboard key was pressed.
            - "release": A keyboard key was released.
            - "repeat": A keyboard key was held down and repeated.
    """

    type: ClassVar[Literal["keyboard"]] = "keyboard"
    """The type of event this sub-event represents. Always "keyboard" for
    ``KeyboardEvent``.
    """

    _native_event: native.KeyEvent
    _kind: str | None = dataclasses.field(
        default=None,
    )
    _binding_tuple: tuple[list[KeyboardModifier | None], str] | None = (
        dataclasses.field(default=None)
    )

    @property
    def key(self) -> KeyboardKey | str | None:
        """The keyboard key that was pressed or released on this
        event.
        """
        if self._binding_tuple is None:
            _set_keyboard_event_data_binding_tuple(self)

        if self._binding_tuple is None or self._binding_tuple[1] is None:
            return None
        return self._binding_tuple[1]

    @property
    def binding(self) -> KeyboardBinding:
        """The ``xnano`` style keyboard binding that this event matches."""
        if self._binding_tuple is None:
            _set_keyboard_event_data_binding_tuple(self)

        if self._binding_tuple is not None:
            modifiers = [m for m in self._binding_tuple[0] if m is not None]
            if len(modifiers) > 0:
                return f"{'+'.join(str(m) for m in modifiers)}+{self._binding_tuple[1]}"
            else:
                return self._binding_tuple[1]

        raise ValueError(
            f"Error resolving the associated keyboard binding for event: {self!r}.\n"
            "Could not resolve the binding tuple from the native event."
        )

    @property
    def kind(self) -> KeyboardEventKind:
        """The kind of event that was triggered on the keyboard."""
        if self._kind is None:
            object.__setattr__(
                self,
                "_kind",
                get_keyboard_event_kind_from_native_event(
                    event=self._native_event
                ),
            )
        return self._kind  # ty: ignore[invalid-return-type]

    @property
    def modifiers(self) -> list[KeyboardModifier | None]:
        """The modifiers that were held down in combination with the primary
        action key to create this keyboard binding.
        """
        if not self._binding_tuple:
            _set_keyboard_event_data_binding_tuple(self)

        # this would have raised an error on the parsing step of
        # retrieving the binding tuple, so this will always have a value
        # when hit
        return self._binding_tuple[0]  # ty: ignore[not-subscriptable]

    @property
    def character(self) -> str | None:
        """The printable character emitted by this key press, if any."""
        character = self._native_event.char()
        if character is None:
            character = self._native_event.char_value()
        if character is None:
            return None
        return str(character)

    def matches(self, *bindings: KeyboardBinding) -> bool:
        """Checks if this keyboard event matches any of the provided keyboard
        bindings.

        Args:
            *bindings: The keyboard bindings to check against.

        Returns:
            True if the keyboard event matches the binding, False otherwise.
        """
        for binding in bindings:
            b = _BINDING_CACHE.get(binding)
            if b is None:
                try:
                    b = CoreKeyBinding.parse(binding)
                except Exception:
                    continue
                _BINDING_CACHE[binding] = b
            if b.matches(self._native_event):
                return True
        return False


@dataclasses.dataclass(slots=True, frozen=True)
class MouseEventData(AbstractEventData):
    """A mouse input event.

    Attributes:
        type: The type of this event (always "mouse")
        kind: The kind of mouse event that was triggered.
        x: The x-coordinate of the mouse event.
        y: The y-coordinate of the mouse event.
        button: The button that was pressed or released on the mouse event.
    """

    type: ClassVar[Literal["mouse"]] = "mouse"
    """The type of event this sub-event represents. Always "mouse" for
    ``MouseEvent``.
    """

    kind: MouseEventKind
    """The kind of mouse event that was triggered."""
    x: int
    """The x-coordinate of the mouse event."""
    y: int
    """The y-coordinate of the mouse event."""
    button: MouseButton
    """The button that was pressed or released on the mouse event."""


@dataclasses.dataclass(slots=True, frozen=True)
class ResizeEventData(AbstractEventData):
    """A terminal resize event.

    Attributes:
        type: The type of this event (always "resize")
        width: The width of the new terminal size.
        height: The height of the new terminal size.
    """

    type: ClassVar[Literal["resize"]] = "resize"
    """The type of event this sub-event represents. Always "resize" for
    ``ResizeEvent``.
    """

    width: int
    """The width of the new terminal size in character cells."""
    height: int
    """The height of the new terminal size in character cells."""


@dataclasses.dataclass(slots=True, frozen=True, repr=False)
class Event:
    """A terminal event that was received from the active terminal session
    due to a condition matching this event's ``type``.
    """

    _core_event: CoreEvent
    """The ``xnano_core.core.CoreEvent`` recieved from the terminal session
    used to initialize this ``Event``.
    """

    _event_data: AbstractEventData = dataclasses.field(init=False)
    _event_type: EventDataType = dataclasses.field(init=False)

    @property
    def data(self) -> EventData:
        """The event data / sub-event content available within this event."""
        if not hasattr(self, "_event_data") or self._event_data is None:
            object.__setattr__(
                self,
                "_event_data",
                get_event_data_from_core_event(event=self._core_event),
            )
        return self._event_data  # ty: ignore[invalid-return-type]

    @property
    def type(self) -> EventDataType:
        """The type of this event's data."""
        if not hasattr(self, "_event_type"):
            kind = self._core_event.kind_str()
            event_type = _CORE_EVENT_TYPES.get(kind, "other")
            object.__setattr__(self, "_event_type", event_type)
        return self._event_type

    def is_clipboard_event(self) -> bool:
        """Return whether this is a clipboard event."""
        return self.type == "clipboard"

    def is_focus_event(self) -> bool:
        """Return whether this is a focus event."""
        return self.type == "focus"

    def is_keyboard_event(self) -> bool:
        """Return whether this is a keyboard event."""
        return self.type == "keyboard"

    def is_mouse_event(self) -> bool:
        """Return whether this is a mouse event."""
        return self.type == "mouse"

    def is_resize_event(self) -> bool:
        """Return whether this is a resize event."""
        return self.type == "resize"

    @property
    def clipboard_event(self) -> ClipboardEventData | None:
        """Clipboard payload when ``kind`` is ``"clipboard"``."""
        if self.type != "clipboard":
            return None
        return self.data  # ty: ignore[invalid-return-type]

    @property
    def clipboard_text(self) -> str | None:
        """Pasted text when this is a clipboard event."""
        if self.clipboard_event is None:
            return None
        return self.clipboard_event.text

    @property
    def focus_event(self) -> FocusEventData | None:
        """Focus payload when ``kind`` is ``"focus"``."""
        if self.type != "focus":
            return None
        return self.data  # ty: ignore[invalid-return-type]

    @property
    def keyboard_event(self) -> KeyboardEventData | None:
        """Keyboard payload when ``kind`` is ``"keyboard"``."""
        if self.type != "keyboard":
            return None
        return self.data  # ty: ignore[invalid-return-type]

    @property
    def keyboard_event_kind(self) -> KeyboardEventKind | None:
        """Keyboard event kind when this is a keyboard event."""
        if self.keyboard_event is None:
            return None
        return self.keyboard_event.kind

    @property
    def keyboard_key(self) -> KeyboardKey | str | None:
        """Primary key when this is a keyboard event."""
        if self.keyboard_event is None:
            return None
        return self.keyboard_event.key

    @property
    def keyboard_modifiers(self) -> list[KeyboardModifier | None]:
        """Modifier keys when this is a keyboard event."""
        if self.keyboard_event is None:
            return []
        return self.keyboard_event.modifiers

    @property
    def mouse_event(self) -> MouseEventData | None:
        """Mouse payload when this is a mouse event."""
        if self.type != "mouse":
            return None
        return self.data  # ty: ignore[invalid-return-type]

    @property
    def mouse_event_kind(self) -> MouseEventKind | None:
        """Mouse event kind when this is a mouse event."""
        if self.mouse_event is None:
            return None
        return self.mouse_event.kind

    @property
    def mouse_position(self) -> tuple[int, int] | None:
        """Mouse coordinates when this is a mouse event."""
        if self.mouse_event is None:
            return None
        return (self.mouse_event.x, self.mouse_event.y)

    @property
    def mouse_button(self) -> MouseButton | None:
        """Mouse button when this is a mouse event."""
        if self.mouse_event is None:
            return None
        return self.mouse_event.button

    @property
    def resize_event(self) -> ResizeEventData | None:
        """Resize payload when ``kind`` is ``"resize"``."""
        if self.type != "resize":
            return None
        return self.data  # ty: ignore[invalid-return-type]

    @property
    def resize_size(self) -> tuple[int, int] | None:
        """New terminal size when this is a resize event."""
        if self.resize_event is None:
            return None
        return (self.resize_event.width, self.resize_event.height)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"type={self.type!r}, "
            f"data={self.data!r})"
        )
