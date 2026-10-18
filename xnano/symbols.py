"""
xnano.symbols

Names for values: register a picture, a note, a pixel or a sound once and use it by name.

A symbol is a name, not a class. ``symbol='wall'`` on a value registers it here, and a
function that takes a ``str`` where such a value fits looks the name up, so ``Pixel('wall')``
or ``play('kick')`` uses what was registered. The registry is shared by the whole program.
"""

from __future__ import annotations

import difflib
import re
import threading
from typing import Final, overload

from xnano._schema._generics import ValueT

__all__ = ['lookup', 'names', 'register', 'remove']

_registry: dict[str, object] = {}
"""Every registered value by its name."""

_lock: Final = threading.Lock()

# The names of the built-in pixel presets: a symbol may not take one, so a preset always
# means the same thing.
_PRESET_NAMES: Final = frozenset(
    {
        'block',
        'half_top',
        'half_bottom',
        'shade_light',
        'shade_medium',
        'shade_dark',
        'braille',
        'circle',
        'circle_outline',
        'dot',
        'diamond',
        'star',
        'line_horizontal',
        'line_vertical',
        'corner_top_left_rounded',
        'corner_top_right_rounded',
        'corner_bottom_left_rounded',
        'corner_bottom_right_rounded',
        'corner_top_left_square',
        'corner_top_right_square',
        'corner_bottom_left_square',
        'corner_bottom_right_square',
        'arrow_up',
        'arrow_down',
        'arrow_left',
        'arrow_right',
        'check',
        'cross',
    }
)

# A note name such as ``C4``, ``c#4`` or ``Bb-1``, which ``play`` reads as a pitch.
_NOTE_NAME: Final = re.compile(r'^[A-Ga-g](#|b|s)?-?\d+$')


def _kind_name(value: object) -> str:
    return type(value).__name__


def _article(word: str) -> str:
    """``word`` with ``a`` or ``an`` in front of it."""
    return f'an {word}' if word[:1].lower() in 'aeiou' else f'a {word}'


def _check_name(name: str) -> None:
    if not isinstance(name, str):
        raise TypeError(
            f'A symbol name is a string, but got {type(name).__name__}. Name it with text, '
            f"such as symbol='wall'."
        )
    if len(name) < 2:
        raise ValueError(
            f'The symbol name {name!r} is too short: a single character is always drawn as '
            f'that character. Use a name of two characters or more, such as {name * 2!r}.'
        )
    if any(character.isspace() for character in name):
        raise ValueError(
            f'The symbol name {name!r} has a space in it, so it would read as melody text. '
            f'Use a name without spaces, such as {name.replace(" ", "_")!r}.'
        )
    if name in _PRESET_NAMES:
        raise ValueError(
            f'{name!r} is the name of a built-in pixel preset, so it cannot be a symbol. '
            f'Pick another name, such as {name + "_symbol"!r}.'
        )
    lowered = name.lower()
    if lowered in ('rest', '-') or _NOTE_NAME.match(name) or name.isdigit():
        raise ValueError(
            f'{name!r} reads as a note, a rest or a MIDI number, so play() would never look '
            f'it up as a symbol. Pick another name, such as {"sound_" + name!r}.'
        )


def register(name: str, value: object, /) -> None:
    """
    Register ``value`` under ``name``, so that functions that take a name can use it.

    Registering a name again with a value of the same kind keeps the newer value, so code
    that builds the same symbol twice (a function called again, a notebook
    cell run again) keeps working. A name already taken by another kind of value is
    refused, so a lookup that worked before can never silently change.

    Args:
        name: The name, two characters or more, without spaces. It may not be the name of a
            pixel preset, a note name such as ``'C4'``, ``'rest'`` or a number.
        value: The value to register.

    Raises:
        ValueError: The name cannot be a symbol, or another kind of value already has it.
        TypeError: The name is not a string.

    Examples:
        ```python
        import xnano

        xnano.symbols.register('logo', xnano.Color('#336699'))
        assert xnano.symbols.lookup('logo') == xnano.Color('#336699')
        xnano.symbols.remove('logo')
        ```
    """
    _check_name(name)
    with _lock:
        existing = _registry.get(name)
        if existing is not None and type(existing) is not type(value):
            raise ValueError(
                f'The symbol {name!r} is already {_article(_kind_name(existing))}, so it '
                f'cannot also name {_article(_kind_name(value))}. Call '
                f'xnano.symbols.remove({name!r}) first, or pick another name.'
            )
        _registry[name] = value


@overload
def lookup(name: str, /) -> object: ...
@overload
def lookup(name: str, /, *, kind: type[ValueT]) -> ValueT: ...
def lookup(name: str, /, *, kind: type[ValueT] | None = None) -> ValueT | object:
    """
    Return the value registered under ``name``.

    Args:
        name: The registered name.
        kind: The class the value must be an instance of, such as ``xnano.Image``; ``None``
            accepts any kind.

    Raises:
        ValueError: Nothing of that kind is registered under the name. The message names the
            closest registered names first, then every known one.

    Examples:
        ```python
        import xnano

        xnano.symbols.register('accent', xnano.Color('#ff8800'))
        assert xnano.symbols.lookup('accent', kind=xnano.Color).to_rgb() == (255, 136, 0)
        xnano.symbols.remove('accent')
        ```
    """
    with _lock:
        value = _registry.get(name)
        known = sorted(
            registered
            for registered, item in _registry.items()
            if kind is None or isinstance(item, kind)
        )
    if value is not None and (kind is None or isinstance(value, kind)):
        return value
    what = 'symbol' if kind is None else f'{kind.__name__} symbol'
    if value is not None and kind is not None:
        raise ValueError(
            f'{name!r} is {_article(_kind_name(value))} symbol, not {_article(what)}. Use a '
            f'name registered for {_article(kind.__name__)}, or register one with '
            f'symbol={name!r} when you create it.'
        )
    close = difflib.get_close_matches(name, known, n=3)
    hint = f' Did you mean {" or ".join(repr(item) for item in close)}?' if close else ''
    listed = ', '.join(repr(item) for item in known) if known else 'none yet'
    raise ValueError(
        f'{name!r} is not a known {what}.{hint} Known {what}s: {listed}. Register one with '
        f'symbol={name!r} when you create it.'
    )


def names(*, kind: type | None = None) -> tuple[str, ...]:
    """
    Return the registered names, in alphabetical order.

    Args:
        kind: Only the names of values that are instances of this class; ``None`` for all.

    Examples:
        ```python
        import xnano

        xnano.symbols.register('sky', xnano.Color('#88ccff'))
        assert 'sky' in xnano.symbols.names(kind=xnano.Color)
        xnano.symbols.remove('sky')
        ```
    """
    with _lock:
        return tuple(
            sorted(
                registered
                for registered, item in _registry.items()
                if kind is None or isinstance(item, kind)
            )
        )


def remove(name: str, /) -> None:
    """
    Forget the value registered under ``name``. Removing a name that is not there does nothing.

    Args:
        name: The registered name.
    """
    with _lock:
        _registry.pop(name, None)
