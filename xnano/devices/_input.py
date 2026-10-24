"""
xnano.devices._input

What the keyboard and the mouse share: checking key names, the cells a hook's target covers, and
pairs of cell numbers.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

import xnano_core as _core
from xnano._schema._hooks import KeyNames
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.layout._placement import Placement

# How long after the last key repeat a key still counts as held, on a terminal that does not
# report key releases. It has to outlast the operating system's pause before a held key repeats.
_ESTIMATED_HOLD_SECONDS = 0.45


# The range of a cell number or a number of wheel steps that an event can carry.
_MINIMUM_CELL_NUMBER = -(2**31)
_MAXIMUM_CELL_NUMBER = 2**31 - 1

_MOUSE_BUTTON_NAMES = ('mouse_left', 'mouse_right', 'mouse_middle')


_MODIFIER_NAMES = ('shift', 'ctrl', 'control', 'alt', 'super', 'meta', 'hyper')


def _names(keys: KeyNames) -> tuple[str, ...]:
    """The keys in ``keys`` as the runtime spells them, each checked to be one held key."""
    import difflib

    from xnano.hooks._triggers import _KEY_NAMES, normalize_binding

    if isinstance(keys, str):
        names: tuple[object, ...] = (keys,)
    elif isinstance(keys, Sequence):
        names = tuple(keys)
    else:
        names = (keys,)
    spelled: list[str] = []
    for name in names:
        if not isinstance(name, str):
            raise TypeError(
                f"The keyboard takes a key name such as 'space', or several such as "
                f"('a', 'left'), but got {keys!r}. Pass the names as text."
            )
        if name in _MOUSE_BUTTON_NAMES or name.lower().removeprefix('mouse_') in (
            'left_mouse',
            'right_mouse',
            'middle_mouse',
        ):
            raise ValueError(
                f'{name!r} is a mouse button, which the mouse holds: ask '
                f"canvas.mouse.held_buttons, such as 'left' in canvas.mouse.held_buttons."
            )
        if name.lower() in _MODIFIER_NAMES or (name != '+' and '+' in name):
            raise ValueError(
                f'{name!r} is a modifier or a key binding, but held keys are checked one key '
                f"at a time, such as is_down('s'). A key binding belongs in "
                f"hook(keys='ctrl+s')."
            )
        try:
            normalize_binding(name)
        except ValueError:
            close = difflib.get_close_matches(name.lower(), _KEY_NAMES, n=3)
            hint = (
                f' Did you mean {" or ".join(repr(match) for match in close)}?'
                if close
                else ''
            )
            raise ValueError(
                f'{name!r} is not a key.{hint} Use one key name from xnano.devices.KeyName such '
                f"as 'q', 'space' or 'page_up'."
            ) from None
        key = _core.Event.key_press(name).key
        assert key is not None
        spelled.append(key.key)
    return tuple(spelled)


def _modifier_text(key: _core.KeyEvent) -> _core.KeyBindingText:
    order = (
        ('control', 'ctrl'),
        ('alt', 'alt'),
        ('shift', 'shift'),
        ('super', 'super'),
        ('meta', 'meta'),
        ('hyper', 'hyper'),
    )
    parts = [text for name, text in order if name in key.modifiers]
    parts.append(key.key)
    return '+'.join(parts)


def _owner_cells(
    canvas: Canvas[object, object], owner: object | None
) -> tuple[int, int, int, int]:
    """
    The screen cells ``(left, top, right, bottom)`` that ``owner`` covers, right and bottom
    exclusive, cut to the screen. ``owner`` is a placement, a canvas, or ``None`` for the canvas.
    """
    from xnano.canvas import Canvas as CanvasType

    screen = canvas.screen.size
    if owner is None or owner is canvas:
        left, top, right, bottom = 0, 0, screen.width, screen.height
    else:
        if isinstance(owner, CanvasType):
            area = owner._root._absolute_bounds
        else:
            area = cast('Placement[object, object]', owner)._buffer._absolute_bounds
        left, top = area.x, area.y
        right, bottom = area.x + area.width, area.y + area.height
    left, top = max(left, 0), max(top, 0)
    right, bottom = min(right, screen.width), min(bottom, screen.height)
    if right <= left or bottom <= top:
        raise TerminalError(
            'random() needs a cell to push to, but the canvas or placement it belongs to '
            'covers no cell on the screen. Give it a size and a position on the screen first, '
            'or give the cell yourself, such as mouse.click(x=3, y=1).',
            code='canvas.state',
        )
    return left, top, right, bottom


def _random_cell(canvas: Canvas[object, object], owner: object | None) -> tuple[int, int]:
    """A random screen cell ``(x, y)`` inside the cells ``owner`` covers."""
    left, top, right, bottom = _owner_cells(canvas, owner)
    return random.randrange(left, right), random.randrange(top, bottom)


def _cell_pair(
    value: tuple[object, ...],
    name: str,
    *,
    description: str = 'a cell on the screen, such as (3, 1)',
) -> tuple[int, int]:
    """Return ``value`` when it is a pair of whole numbers in the supported range."""
    if len(value) != 2 or any(
        isinstance(item, bool) or not isinstance(item, int) for item in value
    ):
        raise TypeError(
            f'{name} takes a pair of whole numbers, {description}, but got {value!r}.'
        )
    pair = cast('tuple[int, int]', value)
    if any(not _MINIMUM_CELL_NUMBER <= item <= _MAXIMUM_CELL_NUMBER for item in pair):
        raise ValueError(
            f'{name} takes whole numbers from {_MINIMUM_CELL_NUMBER} to '
            f'{_MAXIMUM_CELL_NUMBER}, but got {value!r}. Pass {description}.'
        )
    return pair
