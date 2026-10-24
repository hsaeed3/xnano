"""
xnano._schema._hooks

The aliases that describe a hook: when it runs, its condition, the function itself, and the
key and mouse button names that hooks and inputs use.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Generator, Sequence
from typing import TYPE_CHECKING, Literal, TypeAlias

import xnano_core as _core
from xnano._schema._generics import DepsT, StateT

if sys.version_info >= (3, 13):
    from typing import TypeAliasType
else:
    from typing_extensions import TypeAliasType

if TYPE_CHECKING:
    # `Context` is written as a string in the aliases below: `xnano.hooks` imports this module,
    # so it cannot be imported here while the module runs.
    from xnano.hooks._context import Context

HookKind: TypeAlias = Literal[
    'frame',
    'tick',
    'beat',
    'key',
    'mouse',
    'scroll',
    'drag',
    'paste',
    'focus',
    'resize',
    'state',
    'custom',
]
"""
When a hook runs.

``'frame'`` before each frame, ``'tick'`` at each simulation step, ``'beat'`` on the canvas's
musical beat, ``'key'``, ``'mouse'``, ``'scroll'``, ``'drag'``, ``'paste'``, ``'focus'`` and
``'resize'`` when that input arrives, ``'state'`` when state the hook read changes, and
``'custom'`` for events you push yourself. A hook without ``on`` hears every input event.
"""

When = TypeAliasType(
    'When',
    str | Callable[['Context[DepsT, StateT]'], bool] | _core.Expression[bool],
    type_params=(DepsT, StateT),
)
"""
The condition of a hook: an expression, a function of the context, or a string.

* An expression built from the scopes in [`xnano.expressions`][xnano.expressions], such as
  ``keyboard.key == 'q'``, is checked by the runtime before Python is called.
* A function takes the context and returns ``True`` when the hook should run.
* A string such as ``"keyboard.key == 'q' and not mouse.is_down"`` is parsed once. It uses the
  names ``keyboard``, ``mouse``, ``scroll``, ``buffer``, ``parent``, ``root``, ``time`` and
  ``deps``, and the operators ``==``, ``!=``, ``<``, ``<=``, ``>``, ``>=``, ``in``, ``and``,
  ``or`` and ``not``.

A value the event did not carry, such as ``keyboard.key`` while a mouse event arrives, is
neither equal to nor different from anything, so every comparison with it is false.
"""

HookTrigger = TypeAliasType(
    'HookTrigger',
    'HookKind | str | When[DepsT, StateT]',
    type_params=(DepsT, StateT),
)
"""
When a hook runs, given as its ``on``: a kind of event, the name of a custom event, or a
condition.

* A kind from [`HookKind`][xnano.hooks.HookKind], such as ``'key'``, ``'tick'`` or
  ``'resize'``.
* The name of an event pushed with ``Event.custom(name)``, such as ``'volume_changed'`` or
  ``'game.over'``: any name that is not a kind and does not start with a name a condition
  reads (``keyboard``, ``mouse``, ``scroll``, ``buffer``, ``parent``, ``root``, ``time`` or
  ``deps``).
* A condition, see [`When`][xnano.hooks.When]: a string such as
  ``"mouse.kind == 'press'"``, an expression such as ``keyboard.key == 'q'``, or a function of
  the context. A string that reads one input hears only that input, so
  ``on="mouse.kind == 'press'"`` is a mouse hook and hears the pointer inside a placement; a
  string that reads no input is checked on every tick. An expression or a function hears every
  input event. With ``every=`` or ``after=`` a condition is checked on those ticks, and with
  ``keys=`` on those keys.
"""

IfRunning: TypeAlias = Literal['replace', 'ignore', 'queue', 'overlap']
"""
What an ``async def`` hook does when it is called again while its previous run has not
finished.

``'replace'`` cancels the earlier run and starts the new one, so the latest input wins.
``'ignore'`` keeps the earlier run and drops the new call. ``'queue'`` starts the new run when
the earlier one has finished, so the runs happen one at a time in order. ``'overlap'`` starts
the new run at once, next to the earlier one.
"""

HookResult = TypeAliasType(
    'HookResult',
    Generator[None, 'Context[DepsT, StateT]', None],
    type_params=(DepsT, StateT),
)
"""
What a hook that spans several events returns: a generator that receives the next context at
each bare ``yield``.
"""

Hook = TypeAliasType(
    'Hook',
    Callable[['Context[DepsT, StateT]'], 'object | HookResult[DepsT, StateT]']
    | Callable[[], 'object | HookResult[DepsT, StateT]'],
    type_params=(DepsT, StateT),
)
"""
What a canvas or placement calls when an event counts: a function of the
[`Context`][xnano.hooks.Context], or a function with no parameters when it needs none.
"""

KeyName: TypeAlias = Literal[
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'space', 'enter', 'escape', 'tab', 'backspace', 'delete', 'insert',
    'home', 'end', 'page_up', 'page_down', 'up', 'down', 'left', 'right',
    'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
    'f13', 'f14', 'f15', 'f16', 'f17', 'f18', 'f19', 'f20', 'f21', 'f22', 'f23', 'f24',
    'caps_lock', 'scroll_lock', 'num_lock', 'print_screen', 'pause', 'menu',
] | str  # fmt: skip
"""
The name of a key such as ``'q'``, ``'enter'`` or ``'page_up'``.

A key with modifiers is written as a key binding joined with ``+``, such as ``'ctrl+s'`` or
``'shift+tab'``; the trailing ``str`` lets a key binding and punctuation keys type-check while editors
still suggest the names listed here. A key that types a character, such as ``'é'`` or ``'?'``,
is named by that character in lowercase.
"""

KeyNames: TypeAlias = KeyName | Sequence[KeyName]
"""One key name, or several that count the same, such as ``('a', 'left')``."""
