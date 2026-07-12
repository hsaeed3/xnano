"""xnano._event_processing

---

Parse and normalize native terminal events into framework events.
"""

from __future__ import annotations

import dataclasses
import re
from typing import (
    Any,
    Generic,
    Literal,
    Tuple,
    TypeAlias,
    TypeVar,
    TypedDict,
    TYPE_CHECKING,
)

from xnano_core import core
from xnano_core.rust import native

if TYPE_CHECKING:
    import xnano.events as xnano_events
    from xnano.events import KeyboardEventKind, MouseEventKind
    from xnano._types import KeyboardModifier


StateT = TypeVar("StateT")


_F_KEY_RE = re.compile(r"^f(\d{1,2})$", re.IGNORECASE)
_SPECIAL_KEYBOARD_KEYS_DICT: dict[str, native.KeyCode] = {
    "enter": native.KeyCode.Enter,
    "esc": native.KeyCode.Esc,
    "backspace": native.KeyCode.Backspace,
    "tab": native.KeyCode.Tab,
    "backtab": native.KeyCode.BackTab,
    "up": native.KeyCode.Up,
    "down": native.KeyCode.Down,
    "left": native.KeyCode.Left,
    "right": native.KeyCode.Right,
    "home": native.KeyCode.Home,
    "end": native.KeyCode.End,
    "pageup": native.KeyCode.PageUp,
    "pagedown": native.KeyCode.PageDown,
    "insert": native.KeyCode.Insert,
    "delete": native.KeyCode.Delete,
    "space": native.KeyCode.Char,
}
_KEY_RESOLUTION_CACHE: dict[
    tuple[int, str | None, int | None, int],
    tuple[list[KeyboardModifier], str | None],
] = {}


class ParsedKeyboardBinding(TypedDict):
    """Parsed representation of a user provided `<modifiers>+<key>` keyboard
    binding into ``xnano_core`` native focused properties.

    Attributes:
        ctrl: Whether the control key was held down.
        shift: Whether the shift key was held down.
        alt: Whether the alt key was held down.
        key_code: The key code of the key that was pressed.
        char: The character that was pressed.
        f_number: The number of the function key that was pressed.
    """

    ctrl: bool
    shift: bool
    alt: bool
    key_code: native.KeyCode
    char: str | None
    f_number: int | None


def parse_keyboard_binding_from_string(binding: str) -> ParsedKeyboardBinding:
    """Parses a user provided ``<modifiers>+<key>`` keyboard binding string
    into a ``ParsedKeyboardBinding`` tuple.

    Args:
        binding: The user provided keyboard binding string to parse.

    Returns:
        A ``ParsedKeyboardBinding`` tuple containing the parsed keyboard binding.
    """
    parts = [part.strip().lower() for part in binding.split("+")]
    if not parts:
        raise ValueError(f"empty key binding: {binding!r}")

    ctrl = False
    shift = False
    alt = False

    key_part = parts[-1]
    for modifier in parts[:-1]:
        if modifier == "ctrl":
            ctrl = True
        elif modifier in ("shift", "shft"):
            shift = True
        elif modifier == "alt":
            alt = True
        else:
            raise ValueError(
                f"unknown modifier {modifier!r} in binding {binding!r}. "
                f"Valid modifiers: ctrl, shift, alt"
            )

    if key_part in _SPECIAL_KEYBOARD_KEYS_DICT:
        code = _SPECIAL_KEYBOARD_KEYS_DICT[key_part]
        character = " " if key_part == "space" else None
        return {
            "ctrl": ctrl,
            "shift": shift,
            "alt": alt,
            "key_code": code,
            "char": character,
            "f_number": None,
        }

    function_match = _F_KEY_RE.match(key_part)
    if function_match:
        function_number = int(function_match.group(1))
        if 1 <= function_number <= 12:
            return {
                "ctrl": ctrl,
                "shift": shift,
                "alt": alt,
                "key_code": native.KeyCode.F,
                "char": None,
                "f_number": function_number,
            }
        raise ValueError(f"invalid function key: {key_part!r}")

    if len(key_part) == 1:
        return {
            "ctrl": ctrl,
            "shift": shift,
            "alt": alt,
            "key_code": native.KeyCode.Char,
            "char": key_part,
            "f_number": None,
        }

    raise ValueError(f"unknown key in binding: {key_part!r}")


def get_keyboard_binding_tuple_from_native_event(
    event: native.KeyEvent,
) -> tuple[list[KeyboardModifier], str | None]:
    """Parses a native ``KeyEvent`` from ``ratatui`` into the an ``xnano``
    style keyboard binding string.

    Args:
        event: The native ``KeyEvent`` from ``ratatui`` to parse.

    Returns:
        The corresponding ``xnano`` style keyboard binding string.
    """
    # The resolved tuple includes the held modifiers, so the cache key must
    # too — otherwise ``a`` and ``alt+a`` collide on the same entry and the
    # second press reports the first press's modifiers.
    modifier_bits = (
        (4 if event.modifiers.control() else 0)
        | (2 if event.modifiers.alt() else 0)
        | (1 if event.modifiers.shift() else 0)
    )
    cache_key = (
        int(event.code_name),
        event.char(),
        event.function_number(),
        modifier_bits,
    )
    if cache_key in _KEY_RESOLUTION_CACHE:
        return _KEY_RESOLUTION_CACHE[cache_key]

    modifiers: list[Literal["ctrl", "shift", "alt"]] = []
    key: str | None = None

    if event.is_enter():
        key = "enter"
    elif event.is_esc():
        key = "esc"
    elif event.is_backspace():
        key = "backspace"
    elif event.is_back_tab():
        key = "backtab"
    elif event.is_tab():
        key = "tab"
    elif event.is_up():
        key = "up"
    elif event.is_down():
        key = "down"
    elif event.is_left():
        key = "left"
    elif event.is_right():
        key = "right"
    elif event.is_home():
        key = "home"
    elif event.is_end():
        key = "end"
    elif event.is_page_up():
        key = "pageup"
    elif event.is_page_down():
        key = "pagedown"
    elif event.is_insert():
        key = "insert"
    elif event.is_delete():
        key = "delete"
    elif event.is_null():
        key = "null"
    elif event.is_caps_lock():
        key = "capslock"
    elif event.is_scroll_lock():
        key = "scrolllock"
    elif event.is_num_lock():
        key = "numlock"

    elif event.is_function_key():
        function_number = event.function_number()
        if function_number is not None and 1 <= function_number <= 12:
            key = f"f{function_number}"
        else:
            key = None

    else:
        character = event.char()
        if character is None:
            character = event.char_value()

        if character == " ":
            key = "space"
        elif character is not None and len(character) == 1:
            code = ord(character)
            if 1 <= code <= 26:
                key = chr(ord("a") + code - 1)
                if not event.modifiers.control():
                    modifiers.append("ctrl")
            else:
                key = character.lower()
        elif event.code_name == native.KeyCode.PrintScreen:
            key = "printscreen"
        elif event.code_name == native.KeyCode.Pause:
            key = "pause"
        elif event.code_name == native.KeyCode.Menu:
            key = "menu"
        elif event.code_name == native.KeyCode.KeypadBegin:
            key = "keypadbegin"
        elif event.code_name == native.KeyCode.Media:
            key = "media"
        elif event.code_name in (
            native.KeyCode.Modifier,
            native.KeyCode.Other,
        ):
            key = "other"
        else:
            key = None

    if key is None:
        raise ValueError(f"Could not resolve key from native event: {event!r}")

    if event.modifiers.alt():
        modifiers.append("alt")
    if event.modifiers.shift():
        modifiers.append("shift")
    if event.modifiers.control() and "ctrl" not in modifiers:
        modifiers.append("ctrl")

    _KEY_RESOLUTION_CACHE[cache_key] = (modifiers, key)
    return (modifiers, key)


def get_keyboard_event_kind_from_native_event(
    event: native.KeyEvent,
) -> KeyboardEventKind:
    """Maps a native ``KeyEvent`` kind string to an ``xnano`` keyboard event kind."""
    return event.keyboard_kind_str()  # type: ignore[return-value]


def get_mouse_event_kind_from_native_event(
    event: native.MouseEvent,
) -> MouseEventKind:
    """Maps a native ``MouseEvent`` kind string to an ``xnano`` mouse event kind."""
    return event.xnano_kind_str()  # type: ignore[return-value]


def get_event_data_from_core_event(
    event: core.CoreEvent,
) -> xnano_events.EventData | None:
    """Parses an ``xnano_core.core.CoreEvent`` into a corresponding
    ``xnano.events.EventData`` instance.

    Args:
        event: The ``xnano_core.core.CoreEvent`` to parse.

    Returns:
        The corresponding ``xnano.events.EventData`` instance.
    """
    # Imported at call time: ``xnano.events`` imports this module at its own
    # top level, so a module-level import here is circular whenever
    # ``xnano._event_processing`` happens to be imported first.
    import xnano.events as xnano_events

    kind = event.kind_str()

    if kind == "key":
        key = event.key
        assert key is not None
        return xnano_events.KeyboardEventData(_native_event=key)

    if kind == "mouse":
        m = event.mouse
        assert m is not None
        native_button = m.xnano_button_str()
        # Scroll/move events carry no pressed button; the native layer
        # reports "none", which isn't a ``MouseButton`` value.
        button = "unknown" if native_button == "none" else native_button
        return xnano_events.MouseEventData(
            kind=m.xnano_kind_str(),  # type: ignore[arg-type]
            x=m.x,
            y=m.y,
            button=button,  # type: ignore[arg-type]
        )

    if kind == "resize":
        if event.width is None or event.height is None:
            return None
        return xnano_events.ResizeEventData(
            width=event.width, height=event.height
        )

    if kind == "paste":
        return xnano_events.ClipboardEventData(text=event.paste)

    if kind == "focus_gained":
        return xnano_events.FocusEventData(kind="gained")
    if kind == "focus_lost":
        return xnano_events.FocusEventData(kind="lost")

    return None
