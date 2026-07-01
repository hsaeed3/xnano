"""xnano.keyboard"""

from __future__ import annotations

import re
from typing import Any, Literal, TypeAlias, TypeVar, Union

from xnano import _core


T = TypeVar("T")


SpecialKey: TypeAlias = Literal[
    "enter",
    "esc",
    "backspace",
    "tab",
    "backtab",
    "up",
    "down",
    "left",
    "right",
    "home",
    "end",
    "pageup",
    "pagedown",
    "insert",
    "delete",
    "space",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
]
"""Special key names for bindings."""


KeyModifierPrefix: TypeAlias = Literal["ctrl+", "shift+", "alt+"]
"""Modifiers prefixes for combinations."""


KeyBinding: TypeAlias = Union[
    str,
    SpecialKey,
    Literal[
        "ctrl+c",
        "ctrl+d",
        "ctrl+z",
        "ctrl+x",
        "ctrl+v",
        "ctrl+a",
        "ctrl+s",
        "ctrl+w",
        "ctrl+r",
        "ctrl+f",
        "ctrl+up",
        "ctrl+down",
        "ctrl+left",
        "ctrl+right",
        "shift+tab",
        "shift+up",
        "shift+down",
        "shift+left",
        "shift+right",
        "alt+enter",
        "alt+backspace",
        "alt+up",
        "alt+down",
        "alt+left",
        "alt+right",
    ],
]
"""A key binding string representation."""


KeyEventKindName: TypeAlias = Literal["press", "repeat", "release"]
"""The phase of a key event."""


_SPECIAL_KEYS: dict[str, _core.KeyCode] = {
    "enter": _core.KeyCode.Enter,
    "return": _core.KeyCode.Enter,
    "esc": _core.KeyCode.Esc,
    "escape": _core.KeyCode.Esc,
    "backspace": _core.KeyCode.Backspace,
    "tab": _core.KeyCode.Tab,
    "backtab": _core.KeyCode.BackTab,
    "up": _core.KeyCode.Up,
    "down": _core.KeyCode.Down,
    "left": _core.KeyCode.Left,
    "right": _core.KeyCode.Right,
    "home": _core.KeyCode.Home,
    "end": _core.KeyCode.End,
    "pageup": _core.KeyCode.PageUp,
    "pagedown": _core.KeyCode.PageDown,
    "insert": _core.KeyCode.Insert,
    "delete": _core.KeyCode.Delete,
    "space": _core.KeyCode.Char,
}


_MODIFIER_NAMES = {"ctrl", "shift", "alt"}


_F_KEY_RE = re.compile(r"^f(\d{1,2})$", re.IGNORECASE)


def _parse_binding(
    binding: str,
) -> tuple[bool, bool, bool, _core.KeyCode, str | None, int | None]:
    """Parse a key binding string into its components.

    Returns:
        A tuple of (ctrl, shift, alt, key_code, char_or_none, f_number_or_none).

    Raises:
        ValueError: If the binding string is malformed.
    """
    parts = [p.strip().lower() for p in binding.split("+")]
    if not parts:
        raise ValueError(f"empty key binding: {binding!r}")

    ctrl = False
    shift = False
    alt = False

    # All parts except the last are modifiers
    key_part = parts[-1]
    for mod in parts[:-1]:
        if mod == "ctrl":
            ctrl = True
        elif mod in ("shift", "shft"):
            shift = True
        elif mod == "alt":
            alt = True
        else:
            raise ValueError(
                f"unknown modifier {mod!r} in binding {binding!r}. "
                f"Valid modifiers: ctrl, shift, alt"
            )

    # Parse the key part
    if key_part in _SPECIAL_KEYS:
        code = _SPECIAL_KEYS[key_part]
        char = " " if key_part == "space" else None
        return ctrl, shift, alt, code, char, None

    # Check function keys (f1 - f12)
    f_match = _F_KEY_RE.match(key_part)
    if f_match:
        f_num = int(f_match.group(1))
        if 1 <= f_num <= 12:
            return ctrl, shift, alt, _core.KeyCode.F, None, f_num
        raise ValueError(f"invalid function key: {key_part!r}")

    # Check single character
    if len(key_part) == 1:
        return ctrl, shift, alt, _core.KeyCode.Char, key_part, None

    raise ValueError(f"unknown key in binding: {key_part!r}")


def _event_matches_binding(event: _core.KeyEvent, binding: KeyBinding) -> bool:
    """Internal matching function comparing a native key event to a binding."""
    try:
        ctrl, shift, alt, code, char, _f_num = _parse_binding(binding)
    except ValueError:
        return False

    # Check key code matches
    if event.code_name != code:
        # Special case: shift+tab should match BackTab
        if (
            shift
            and not ctrl
            and not alt
            and code == _core.KeyCode.Tab
            and event.code_name == _core.KeyCode.BackTab
        ):
            return True
        return False

    # Check character (for Char keys)
    if code == _core.KeyCode.Char and char is not None:
        event_char = event.char()
        if event_char is None:
            return False
        if event_char.lower() != char.lower():
            return False

    # Check modifiers
    if ctrl != event.modifiers.control():
        return False
    if alt != event.modifiers.alt():
        return False
    # Shift is implicit for uppercase characters, so only check
    # explicitly when the binding specifies shift with a non-char key
    if code != _core.KeyCode.Char and shift != event.modifiers.shift():
        return False

    return True


class KeyEvent:
    """A keyboard input event with modifier-aware matching."""

    __slots__ = ("_inner",)
    _inner: _core.KeyEvent

    def __init__(self) -> None:
        raise TypeError(
            "KeyEvent instances are created internally by the event system."
        )

    @classmethod
    def _from_core(cls, event: _core.KeyEvent) -> KeyEvent:
        """Construct from a native key event."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", event)
        return obj

    def _to_core(self) -> _core.KeyEvent:
        """Return the native key event."""
        return self._inner

    @property
    def code(self) -> _core.KeyCode:
        """The key code enum category."""
        return self._inner.code_name

    @property
    def kind(self) -> KeyEventKindName:
        """The key action type: ``"press"``, ``"repeat"``, or ``"release"``."""
        kind_val = self._inner.kind
        if kind_val == _core.KeyEventKind.Press:
            return "press"
        elif kind_val == _core.KeyEventKind.Repeat:
            return "repeat"
        else:
            return "release"

    @property
    def is_press(self) -> bool:
        """True if the key was pressed down."""
        return self.kind == "press"

    @property
    def is_repeat(self) -> bool:
        """True if the key is auto-repeating."""
        return self.kind == "repeat"

    @property
    def is_release(self) -> bool:
        """True if the key was released."""
        return self.kind == "release"

    @property
    def ctrl(self) -> bool:
        """True if the Ctrl key was held."""
        return self._inner.modifiers.control()

    @property
    def shift(self) -> bool:
        """True if the Shift key was held."""
        return self._inner.modifiers.shift()

    @property
    def alt(self) -> bool:
        """True if the Alt key was held."""
        return self._inner.modifiers.alt()

    @property
    def char(self) -> str | None:
        """The character representation of the key if printable, else ``None``."""
        return self._inner.char()

    def matches(self, binding: KeyBinding) -> bool:
        """Check if this key event matches a Textual-style binding string."""
        return _event_matches_binding(self._inner, binding)

    def matches_any(self, *bindings: KeyBinding) -> bool:
        """Check if this key event matches any of the given binding strings."""
        return any(self.matches(b) for b in bindings)

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("KeyEvent is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("KeyEvent is immutable")


__all__ = (
    "SpecialKey",
    "KeyModifierPrefix",
    "KeyBinding",
    "KeyEventKindName",
    "KeyEvent",
)
