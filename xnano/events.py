"""xnano.events

---

Unified terminal and application events, plus the public ``@on_*`` hook
decorators used to annotate ``BaseGrid`` methods for event handling.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Literal,
    TypeAlias,
    TypeVar,
    Union,
    overload,
)

from xnano_core.core import (
    CoreEvent,
    CoreKeyBinding,
)

_BINDING_CACHE: dict[str, CoreKeyBinding] = {}

from xnano._event_processing import (
    get_event_data_from_core_event,
    get_keyboard_binding_tuple_from_native_event,
    get_keyboard_event_kind_from_native_event,
)
from xnano._types import (
    KeyboardBinding,
    KeyboardKey,
    KeyboardModifier,
    MouseButton,
)

if TYPE_CHECKING:
    import xnano_core.rust.native as native


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


_KEY_ALIASES: dict[str, str] = {
    " ": "space",
    "esc": "escape",
    "return": "enter",
}


def normalize_keyboard_binding(
    binding: str,
) -> tuple[frozenset[str], str] | None:
    """Normalize a ``ctrl+shift+k`` style binding for comparison.

    Args:
        binding: The binding string to normalize.

    Returns:
        A ``(modifiers, key)`` pair, or ``None`` for an empty binding.
    """
    parts = [part.strip().lower() for part in binding.split("+")]
    parts = [part for part in parts if part]
    if not parts:
        return None
    key = parts[-1]
    key = _KEY_ALIASES.get(key, key)
    modifiers = frozenset(
        part for part in parts[:-1] if part in ("ctrl", "alt", "shift")
    )
    return (modifiers, key)


def parse_binding_tuple(
    binding: str,
) -> tuple[list[KeyboardModifier | None], str]:
    """Parse a binding string into a ``(modifiers, key)`` tuple.

    Args:
        binding: A ``ctrl+s`` style binding.

    Returns:
        Modifiers list and primary key.
    """
    normalized = normalize_keyboard_binding(binding)
    if normalized is None:
        return ([], "")
    modifiers_set, key = normalized
    modifiers: list[KeyboardModifier | None] = [
        m
        for m in ("ctrl", "alt", "shift")
        if m in modifiers_set  # type: ignore[misc]
    ]
    return (modifiers, key)


def _set_keyboard_event_data_binding_tuple(
    event_data: KeyboardEventData,
) -> None:
    if not hasattr(event_data, "type") or not event_data.type == "keyboard":
        raise ValueError("Expected a KeyboardEventData instance.")
    if event_data._native_event is None:
        raise ValueError(
            f"Error resolving the associated keyboard binding for event: "
            f"{event_data!r}.\nSynthetic events must pre-fill "
            f"``_binding_tuple``."
        )
    try:
        binding_tuple = get_keyboard_binding_tuple_from_native_event(
            event=event_data._native_event
        )
    except Exception as e:
        raise ValueError(
            f"Error resolving the associated keyboard binding for event: "
            f"{event_data!r}.\n"
            f"Error: {e!r}"
        ) from e

    object.__setattr__(event_data, "_binding_tuple", binding_tuple)


@dataclasses.dataclass(slots=True, frozen=True)
class KeyboardEventData(AbstractEventData):
    """A keyboard input event.

    May be produced from a native terminal ``KeyEvent`` or synthesized
    from a binding string (``from_binding``) for Actions / web input.

    Properties:
        type: The type of this event (always "keyboard")
        key: The keyboard key that was pressed or released on this event.
        modifiers: The modifiers that were held down in combination with the
            primary action key to create this keyboard binding.
        kind: The kind of event that was triggered on the keyboard.
    """

    type: ClassVar[Literal["keyboard"]] = "keyboard"
    """The type of event this sub-event represents. Always "keyboard" for
    ``KeyboardEvent``.
    """

    _native_event: "native.KeyEvent | None" = None
    _kind: str | None = dataclasses.field(
        default=None,
    )
    _binding_tuple: tuple[list[KeyboardModifier | None], str] | None = (
        dataclasses.field(default=None)
    )
    _character: str | None = dataclasses.field(default=None)

    @classmethod
    def from_binding(
        cls,
        binding: str,
        *,
        kind: KeyboardEventKind = "press",
        character: str | None = None,
    ) -> "KeyboardEventData":
        """Synthesize keyboard data from a binding string.

        Args:
            binding: A ``ctrl+s`` style binding.
            kind: Press / release / repeat.
            character: Optional printable character override.

        Returns:
            A ``KeyboardEventData`` with no native event underneath.
        """
        modifiers, key = parse_binding_tuple(binding)
        resolved_character = character
        if resolved_character is None:
            if len(key) == 1:
                resolved_character = key
            elif key == "space":
                resolved_character = " "
        return cls(
            _native_event=None,
            _kind=kind,
            _binding_tuple=(modifiers, key),
            _character=resolved_character,
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
                return (
                    f"{'+'.join(str(m) for m in modifiers)}"
                    f"+{self._binding_tuple[1]}"
                )
            else:
                return self._binding_tuple[1]

        raise ValueError(
            f"Error resolving the associated keyboard binding for event: "
            f"{self!r}.\n"
            "Could not resolve the binding tuple from the native event."
        )

    @property
    def kind(self) -> KeyboardEventKind:
        """The kind of event that was triggered on the keyboard."""
        if self._kind is None:
            if self._native_event is None:
                return "press"
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
        if self._character is not None:
            return self._character
        if self._native_event is None:
            key = self.key
            if isinstance(key, str) and len(key) == 1:
                return key
            if key == "space":
                return " "
            return None
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
        if self._native_event is not None:
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

        # Synthetic path: compare normalized binding strings.
        own = normalize_keyboard_binding(str(self.binding))
        for binding in bindings:
            if binding is None:
                return True
            if normalize_keyboard_binding(str(binding)) == own:
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
    """A unified input event from a host adapter or synthesized Action.

    Terminal adapters construct from a ``CoreEvent``; Actions and the web
    host construct from typed ``*EventData`` via ``Event.from_data``.
    """

    _core_event: CoreEvent | None = None
    """The ``xnano_core.core.CoreEvent`` received from a terminal session,
    or ``None`` for synthesized events.
    """
    _event_data: AbstractEventData | None = dataclasses.field(
        default=None, repr=False
    )
    _event_type: EventDataType | None = dataclasses.field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        if self._core_event is None and self._event_data is None:
            raise ValueError(
                "Event requires either a CoreEvent or synthetic event data"
            )

    @classmethod
    def from_data(cls, data: AbstractEventData) -> "Event":
        """Build an event from typed sub-event data (no native core event).

        Args:
            data: Keyboard, mouse, resize, clipboard, or focus payload.

        Returns:
            An ``Event`` handlers cannot distinguish from device input.
        """
        type_map: dict[str, EventDataType] = {
            "keyboard": "keyboard",
            "mouse": "mouse",
            "resize": "resize",
            "clipboard": "clipboard",
            "focus": "focus",
        }
        event_type = type_map.get(getattr(data, "type", "other"), "other")
        return cls(
            _core_event=None,
            _event_data=data,
            _event_type=event_type,
        )

    @property
    def data(self) -> EventData:
        """The event data / sub-event content available within this event."""
        if self._event_data is not None:
            return self._event_data  # ty: ignore[invalid-return-type]
        if self._core_event is None:
            raise ValueError("Event has neither core event nor data")
        object.__setattr__(
            self,
            "_event_data",
            get_event_data_from_core_event(event=self._core_event),
        )
        return self._event_data  # ty: ignore[invalid-return-type]

    @property
    def type(self) -> EventDataType:
        """The type of this event's data."""
        if self._event_type is not None:
            return self._event_type
        if self._core_event is None:
            return "other"
        kind = self._core_event.kind_str()
        event_type = _CORE_EVENT_TYPES.get(kind, "other")
        object.__setattr__(self, "_event_type", event_type)
        return event_type

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


from xnano._function_hooks import (
    _PENDING_HOOKS,
    EventHookFunction,
    FocusHookKind,
    PollWhen,
    _EventHooksRegistry,
)
from xnano._types import KeyboardBinding, MouseButton


def _auto_register_hook_function(fn: EventHookFunction) -> EventHookFunction:
    """Register a free-function hook with the active terminal, or queue it.

    Args:
        fn: The hook function to register.

    Returns:
        The hook function.
    """
    from xnano.tui.terminal import _ACTIVE_TERMINAL

    terminal = _ACTIVE_TERMINAL.get()
    if terminal is not None:
        terminal._hooks.register_hook(fn)
    else:
        _PENDING_HOOKS.append(fn)
    return fn


def _decorate_hook_function(fn: EventHookFunction) -> EventHookFunction:
    """Optionally auto-register ``fn`` when it is a module-level function.

    Args:
        fn: The hook function to decorate.

    Returns:
        The decorated hook function.
    """
    qualname = getattr(fn, "__qualname__", "")
    parts = qualname.split(".")
    is_method = len(parts) > 1 and "<locals>" not in parts[-2]
    if not is_method:
        _auto_register_hook_function(fn)
    return fn


def _decorate_on_tick_hook(
    fn: EventHookFunction, interval: int
) -> EventHookFunction:
    """Decorate a hook function with the ``@on_tick`` decorator.

    Args:
        fn: The hook function to decorate.
        interval: The interval in milliseconds to filter the hook function by.

    Returns:
        The decorated hook function.
    """
    setattr(fn, _EventHooksRegistry.ON_TICK_HOOK_ATTR, True)
    setattr(fn, _EventHooksRegistry.ON_TICK_INTERVAL_ATTR, interval)
    return _decorate_hook_function(fn)


_MOUSE_KINDS_WITH_BUTTON = frozenset({"press", "release", "drag"})
"""``MouseEventKind`` values that carry a real pressed button.

``move`` and the ``scroll_*`` kinds always report no button on the native
side, so a button filter would never match them.
"""


def _decorate_on_mouse_hook(
    fn: EventHookFunction,
    *,
    buttons: tuple[str, ...] = (),
    kind: MouseEventKind | None = None,
    field: str | None = None,
) -> EventHookFunction:
    """Decorate a hook function with the ``@on_mouse`` decorator.

    Args:
        fn: The hook function to decorate.
        buttons: The buttons to filter the hook function by.
        kind: The kind of mouse event to filter the hook function by.
        field: The field to filter the hook function by.

    Returns:
        The decorated hook function.
    """
    selected_kind: MouseEventKind | None = (
        kind if kind is not None else "press"
    )
    if buttons:
        selected_buttons = buttons
    elif selected_kind in _MOUSE_KINDS_WITH_BUTTON:
        selected_buttons = ("left",)
    else:
        selected_buttons = ()
    setattr(fn, _EventHooksRegistry.ON_MOUSE_HOOK_ATTR, True)
    setattr(
        fn,
        _EventHooksRegistry.ON_MOUSE_FILTER_ATTR,
        (selected_buttons, selected_kind),
    )
    if field is not None:
        setattr(fn, _EventHooksRegistry.ON_MOUSE_FIELD_ATTR, field)
    return _decorate_hook_function(fn)


@overload
def on_keyboard(
    key: KeyboardBinding,
    /,
    *keys: KeyboardBinding,
    kind: KeyboardEventKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_keyboard(
    *,
    key: KeyboardBinding,
    kind: KeyboardEventKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_keyboard(
    handler: EventHookFunction,
    /,
    *,
    key: KeyboardBinding | None = None,
    kind: KeyboardEventKind | None = None,
) -> EventHookFunction: ...
def on_keyboard(
    handler_or_key: "EventHookFunction | KeyboardBinding | None" = None,
    /,
    *keys: KeyboardBinding,
    key: KeyboardBinding | None = None,
    kind: KeyboardEventKind | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Decorate a keyboard event hook.

    Args:
        handler_or_key: The handler or key to decorate.
        keys: The keys to filter the hook function by.
        key: The key to filter the hook function by.
        kind: The kind of keyboard event to filter the hook function by.

    Returns:
        The decorated hook function.
    """
    if callable(handler_or_key):
        bindings: tuple[KeyboardBinding, ...] = (
            (key,) if key is not None else keys
        )
        setattr(
            handler_or_key, _EventHooksRegistry.ON_KEYBOARD_HOOK_ATTR, True
        )
        setattr(
            handler_or_key,
            _EventHooksRegistry.ON_KEYBOARD_FILTER_ATTR,
            (bindings, kind),
        )
        return _decorate_hook_function(handler_or_key)

    if handler_or_key is not None:
        keys = (handler_or_key, *keys)  # type: ignore[assignment]
    elif key is not None:
        keys = (key, *keys)
    filter_spec = (keys, kind)

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        setattr(fn, _EventHooksRegistry.ON_KEYBOARD_HOOK_ATTR, True)
        setattr(fn, _EventHooksRegistry.ON_KEYBOARD_FILTER_ATTR, filter_spec)
        return _decorate_hook_function(fn)

    return decorator


@overload
def on_mouse(
    button: MouseButton,
    /,
    *,
    field: str | None = None,
    kind: MouseEventKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_mouse(
    *,
    button: MouseButton | None = None,
    field: str | None = None,
    kind: MouseEventKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_mouse(
    handler: EventHookFunction,
    /,
    *,
    button: MouseButton | None = None,
    field: str | None = None,
    kind: MouseEventKind | None = None,
) -> EventHookFunction: ...
def on_mouse(
    handler_or_button: "EventHookFunction | MouseButton | None" = None,
    /,
    *buttons: MouseButton,
    button: MouseButton | None = None,
    field: str | None = None,
    kind: MouseEventKind | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a mouse event hook.

    Defaults to left-button press when ``button`` and ``kind`` are omitted.
    Pass ``field`` to bind the hook to a grid layout field's interactive region.
    """
    if callable(handler_or_button):
        selected: tuple[MouseButton, ...] = (
            (button,) if button is not None else buttons
        )
        return _decorate_on_mouse_hook(
            handler_or_button,
            buttons=selected,
            kind=kind,
            field=field,
        )

    if handler_or_button is not None:
        buttons = (handler_or_button, *buttons)  # type: ignore[assignment]
    elif button is not None:
        buttons = (button, *buttons)

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        return _decorate_on_mouse_hook(
            fn, buttons=buttons, kind=kind, field=field
        )

    return decorator


@overload
def on_click(
    field: str, /
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_click(
    handler: EventHookFunction,
    /,
    *,
    field: str,
    button: MouseButton = "left",
    kind: MouseEventKind = "press",
) -> EventHookFunction: ...
def on_click(
    field_or_handler: "str | EventHookFunction",
    /,
    *,
    field: str | None = None,
    button: MouseButton = "left",
    kind: MouseEventKind = "press",
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a click handler for a grid layout field.

    Example:
        @on_click("body")
        def highlight_body(self, ctx: Context) -> None:
            self.body = Paragraph("clicked", color="red")
    """
    if isinstance(field_or_handler, str):
        field_name = field_or_handler

        def decorator(fn: EventHookFunction) -> EventHookFunction:
            return _decorate_on_mouse_hook(
                fn,
                buttons=(button,),
                kind=kind,
                field=field_name,
            )

        return decorator

    if field is None:
        raise TypeError("on_click requires a field name")
    return _decorate_on_mouse_hook(
        field_or_handler,
        buttons=(button,),
        kind=kind,
        field=field,
    )


@overload
def on_tick(handler: EventHookFunction, /) -> EventHookFunction: ...
@overload
def on_tick(
    interval: int,
    /,
    *,
    interval_milliseconds: int | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_tick(
    *,
    interval_milliseconds: int,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
def on_tick(
    handler_or_interval: "EventHookFunction | int | None" = None,
    /,
    *,
    interval_milliseconds: int | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a tick hook, optionally at a fixed interval.

    Args:
        handler_or_interval: The handler or interval to decorate.
        interval_milliseconds: The interval in milliseconds to filter the hook function by.

    Returns:
        The decorated hook function.
    """
    if callable(handler_or_interval):
        return _decorate_on_tick_hook(handler_or_interval, 0)
    resolved = (
        int(handler_or_interval)
        if isinstance(handler_or_interval, int)
        else interval_milliseconds
    )
    if isinstance(resolved, int):
        return lambda fn: _decorate_on_tick_hook(fn, resolved)
    raise TypeError(
        "on_tick expects a callable or an interval in milliseconds"
    )


def on_event(fn: EventHookFunction) -> EventHookFunction:
    """Register an event hook that triggers on every detected terminal
    event.

    Args:
        fn: The hook function to decorate.

    Returns:
        The decorated hook function.
    """
    setattr(fn, _EventHooksRegistry.ON_EVENT_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


def on_resize(fn: EventHookFunction) -> EventHookFunction:
    """Register a hook fired on terminal resize events."""
    setattr(fn, _EventHooksRegistry.ON_RESIZE_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


@overload
def on_focus(handler: EventHookFunction, /) -> EventHookFunction: ...
@overload
def on_focus(
    field: str,
    /,
    *,
    kind: FocusHookKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_focus(
    *,
    field: str | None = None,
    kind: FocusHookKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
def on_focus(
    handler_or_field: "EventHookFunction | str | None" = None,
    /,
    *,
    field: str | None = None,
    kind: FocusHookKind | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a focus hook for the terminal window or a grid field.

    Bare ``@on_focus`` fires on OS-level terminal focus gained/lost events.
    Pass a field name to listen for application field focus instead — the
    caret moving onto/off an editable ``Text(input=True)`` field:

        @on_focus
        def _window(self, ctx: Context) -> None:
            ...  # terminal focus

        @on_focus("prompt")
        def _prompt_focused(self) -> None:
            self.status = "editing prompt"

        @on_focus("prompt", kind="lost")
        def _prompt_blurred(self) -> None:
            self.status = "left prompt"
    """

    def _decorate(
        fn: EventHookFunction,
        *,
        field_name: str | None,
        focus_kind: FocusHookKind | None,
    ) -> EventHookFunction:
        setattr(fn, _EventHooksRegistry.ON_FOCUS_HOOK_ATTR, True)
        if field_name is not None:
            setattr(fn, _EventHooksRegistry.ON_FOCUS_FIELD_ATTR, field_name)
        if focus_kind is not None:
            setattr(fn, _EventHooksRegistry.ON_FOCUS_KIND_ATTR, focus_kind)
        return _decorate_hook_function(fn)

    if callable(handler_or_field):
        return _decorate(
            handler_or_field,
            field_name=field,
            focus_kind=kind,
        )

    resolved_field = (
        handler_or_field if isinstance(handler_or_field, str) else field
    )

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        return _decorate(fn, field_name=resolved_field, focus_kind=kind)

    return decorator


def on_clipboard(fn: EventHookFunction) -> EventHookFunction:
    """Register a hook fired on clipboard paste events."""
    setattr(fn, _EventHooksRegistry.ON_CLIPBOARD_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


def on_state(
    expression: str,
) -> Callable[[EventHookFunction], EventHookFunction]:
    """Fire the decorated handler each tick when ``expression`` is truthy
    against the current application state's attributes.

    The expression is evaluated with the state object's ``__dict__`` as local
    variables, plus ``state`` bound to the full state object. Only state field
    attributes should be referenced; the evaluation namespace is intentionally
    restricted to safe built-ins.

    Example:
        @on_state("count > 0")
        def _on_positive_count(self, ctx: Context[AppState]) -> None:
            self.counter_label = f"Count: {ctx.get_state().count}"

        @on_state("is_loading")
        def _show_spinner(self, ctx: Context[AppState]) -> None:
            self.status = "Loading…"
    """

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        setattr(fn, _EventHooksRegistry.ON_STATE_HOOK_ATTR, True)
        setattr(fn, _EventHooksRegistry.ON_STATE_EXPRESSION_ATTR, expression)
        return _decorate_hook_function(fn)

    return decorator


def on_field(
    expression: str,
) -> Callable[[EventHookFunction], EventHookFunction]:
    """Fire the decorated handler each tick when ``expression`` is truthy
    against the grid's own field values.

    Unlike ``on_state``, which evaluates against the terminal's shared
    ``State`` object, ``on_field`` evaluates against the grid instance
    itself — its layout and state fields are available by name.

    Example:
        @on_field("config['name'] == 'john'")
        def _on_john(self) -> None:
            self.current_text = "Hello, John!"

        @on_field("count > 0")
        def _show_count(self) -> None:
            self.label = f"Count: {self.count}"
    """

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        setattr(fn, _EventHooksRegistry.ON_FIELD_HOOK_ATTR, True)
        setattr(fn, _EventHooksRegistry.ON_FIELD_EXPRESSION_ATTR, expression)
        return _decorate_hook_function(fn)

    return decorator


@overload
def on_poll(handler: EventHookFunction, /) -> EventHookFunction: ...
@overload
def on_poll(
    when: PollWhen = "idle",
    /,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_poll(
    *,
    when: PollWhen,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
def on_poll(
    handler_or_when: "EventHookFunction | PollWhen | None" = None,
    /,
    *,
    when: PollWhen | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a poll hook that fires on idle event waits or every frame.

    Args:
        handler_or_when: A handler (``@on_poll`` bare form, defaults to
            ``"idle"``) or a ``PollWhen`` value (``@on_poll("frame")``).
        when: Keyword form of the poll mode.

    Returns:
        The decorated hook function, or a decorator.

    Example:
        @on_poll
        def _idle_work(self) -> None:
            self.status = "waiting…"

        @on_poll("frame")
        def _each_frame(self) -> None:
            self.frame_count += 1

        @on_poll(when="idle")
        def _also_idle(self, ctx: Context) -> None:
            ...
    """

    def _validate_when(resolved_when: PollWhen) -> None:
        if resolved_when not in ("idle", "frame"):
            raise TypeError(
                "on_poll expects when='idle' or when='frame', got "
                f"{resolved_when!r}"
            )

    def _decorate(
        fn: EventHookFunction, resolved_when: PollWhen
    ) -> EventHookFunction:
        _validate_when(resolved_when)
        setattr(fn, _EventHooksRegistry.ON_POLL_HOOK_ATTR, True)
        setattr(fn, _EventHooksRegistry.ON_POLL_WHEN_ATTR, resolved_when)
        return _decorate_hook_function(fn)

    if callable(handler_or_when):
        return _decorate(handler_or_when, when if when is not None else "idle")

    resolved: PollWhen
    if handler_or_when is not None:
        resolved = handler_or_when
    elif when is not None:
        resolved = when
    else:
        resolved = "idle"

    _validate_when(resolved)

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        return _decorate(fn, resolved)

    return decorator


def on(
    action: Any,
    /,
) -> Callable[[EventHookFunction], EventHookFunction]:
    """Bind a prebuilt ``Action`` as a hook trigger.

    User-facing sugar for storing an Action on a handler. The concrete
    ``@on_keyboard`` / ``@on_click`` decorators remain preferred for
    simple cases; ``@on`` is for shared Action constants:

        SAVE = Action.keyboard("ctrl+s")

        @on(SAVE)
        def save(self, ctx): ...

    Args:
        action: An ``Action`` instance (keyboard, mouse, click, …).

    Returns:
        A decorator that marks ``fn`` with the matching ``@on_*``
        attributes derived from ``action``.
    """
    from xnano.core.actions import (
        ClickAction,
        ClipboardAction,
        FocusAction,
        KeyboardAction,
        MouseAction,
        ResizeAction,
        TickAction,
    )

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        if isinstance(action, KeyboardAction):
            setattr(fn, _EventHooksRegistry.ON_KEYBOARD_HOOK_ATTR, True)
            setattr(
                fn,
                _EventHooksRegistry.ON_KEYBOARD_FILTER_ATTR,
                (action.bindings, action.kind),
            )
        elif isinstance(action, ClickAction):
            return _decorate_on_mouse_hook(
                fn,
                buttons=(action.button,),
                kind="press",
                field=action.field,
            )
        elif isinstance(action, MouseAction):
            return _decorate_on_mouse_hook(
                fn,
                buttons=tuple(action.buttons),
                kind=action.kind,  # type: ignore[arg-type]
            )
        elif isinstance(action, FocusAction):
            setattr(fn, _EventHooksRegistry.ON_FOCUS_HOOK_ATTR, True)
            setattr(fn, _EventHooksRegistry.ON_FOCUS_FIELD_ATTR, action.field)
            setattr(fn, _EventHooksRegistry.ON_FOCUS_KIND_ATTR, action.kind)
        elif isinstance(action, ClipboardAction):
            setattr(fn, _EventHooksRegistry.ON_CLIPBOARD_HOOK_ATTR, True)
        elif isinstance(action, ResizeAction):
            setattr(fn, _EventHooksRegistry.ON_RESIZE_HOOK_ATTR, True)
        elif isinstance(action, TickAction):
            return _decorate_on_tick_hook(fn, action.interval_ms)
        else:
            raise TypeError(
                f"@on expects an Action instance, got {type(action)!r}"
            )
        return _decorate_hook_function(fn)

    return decorator


__all__ = (
    "PollWhen",
    "FocusHookKind",
    "on",
    "on_event",
    "on_resize",
    "on_focus",
    "on_clipboard",
    "on_state",
    "on_field",
    "on_poll",
    "on_keyboard",
    "on_mouse",
    "on_click",
    "on_tick",
    "normalize_keyboard_binding",
    "parse_binding_tuple",
)
