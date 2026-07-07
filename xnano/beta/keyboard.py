"""xnano.keyboard

Aliases for keyboard-specific (non-event) related types used by
``xnano.beta.events`` and ``xnano.beta.hooks``.
"""

from __future__ import annotations

from typing import Literal, TypeAlias, Union


KnownKeyboardBinding: TypeAlias = Literal[
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
]
"""Convenience alias providing a list of commonly used keybindings that
can be set within the ``on_keyboard`` event hook.
"""


KeyboardModifier: TypeAlias = Literal["ctrl", "shift", "alt"]
"""A modifier key that can be held along with the primary action
key for classifying keyboard events.
"""


KeyboardKey: TypeAlias = Literal[
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
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
    "null",
    "capslock",
    "scrolllock",
    "numlock",
    "printscreen",
    "pause",
    "menu",
    "keypadbegin",
    "media",
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
    "other",
]
"""Convenience alias representing the standard character keys that
can be set and/or recieved by ``on_keyboard`` event hooks.
"""


KeyboardBinding: TypeAlias = Union[KnownKeyboardBinding, KeyboardKey, str]
"""``"ctrl+e"`` | ``"enter"`` | ``"shift+f1"`` | ``"3"`` | ``"h"`` | ``"alt+home"``

A keyboard event binding representing a primary trigger key that is
optionally followed by one or more modifier keys held or released at the
same time.

A keyboard binding can be provided in the following formats:

## Without Modifiers

When defining a keyboard binding without modifiers, the primary trigger
key can be provided as one of the following types:

- 'a' - 'z'   : Letter keys.
- '0' - '9'   : Number keys.
- 'enter'     : Enter/Return key.
- 'esc'       : Escape key.
- 'backspace' : Backspace key.
- 'tab', 'backtab' : Tab and BackTab keys.
- 'up', 'down', 'left', 'right' : Arrow keys.
- 'home', 'end', 'pageup', 'pagedown', 'insert', 'delete', 'space', 'null'
- 'capslock', 'scrolllock', 'numlock', 'printscreen', 'pause', 'menu'
- 'keypadbegin', 'media', 'f1' - 'f12', 'other'

## With Modifiers

Bindings including modifier keys are expressed as a string using '+' notation.
Valid modifier keys are 'ctrl', 'shift', and 'alt'. Modifiers must precede
the base key, separated by '+'.

For example:
- 'ctrl+a'        : Control and 'a' key.
- 'shift+tab'     : Shift and Tab key.
- 'alt+enter'     : Alt and Enter key.
- 'ctrl+shift+z'  : Control, Shift, and 'z' key.
"""


__all__ = (
    "KnownKeyboardBinding",
    "KeyboardModifier",
    "KeyboardKey",
    "KeyboardBinding",
)
