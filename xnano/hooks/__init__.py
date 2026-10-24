"""
xnano.hooks

A hook is a function xnano calls when an event counts: a key press, a click, a frame, a
timer or a change of state.

``canvas.hook(function, on='key', keys='q')`` attaches a hook to a canvas or placement right
away, also as a decorator, and returns a [`HookHandle`][xnano.hooks.HookHandle] whose
``remove()`` detaches it. [`hook`][xnano.hooks.hook] (``@xnano.hook(on='frame')``) describes a
hook once, to attach to any target later with ``target | operation``.

A hook's ``on`` says when it runs ([`HookTrigger`][xnano.hooks.HookTrigger]): a kind of event
from [`HookKind`][xnano.hooks.HookKind], the name of a custom event, or a condition
([`When`][xnano.hooks.When]). [`Hook`][xnano.hooks.Hook] is the function a hook runs and
[`HookResult`][xnano.hooks.HookResult] is what that function may return.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, cast, overload

from xnano._schema._generics import DepsT, StateT
from xnano._schema._hooks import (
    Hook as Hook,
)
from xnano._schema._hooks import (
    HookKind as HookKind,
)
from xnano._schema._hooks import (
    HookResult as HookResult,
)
from xnano._schema._hooks import (
    HookTrigger as HookTrigger,
)
from xnano._schema._hooks import (
    IfRunning as IfRunning,
)
from xnano._schema._hooks import KeyName
from xnano._schema._hooks import (
    When as When,
)
from xnano.hooks._context import Context as Context
from xnano.hooks._context import Frame as Frame
from xnano.hooks._context import Plugin as Plugin
from xnano.hooks._context import ReadLog as ReadLog
from xnano.hooks._context import Update as Update
from xnano.hooks._handles import (
    HookHandle as HookHandle,
)
from xnano.hooks._handles import (
    _check_hook_arguments,
    _check_hook_function,
    _check_if_running,
    _check_if_running_fits,
    resolve_trigger,
)
from xnano.hooks._triggers import compile_when
from xnano.operations import ContextualOperation

if TYPE_CHECKING:
    from xnano.hooks._handles import _Hooked

__all__ = [
    'Context',
    'Frame',
    'Hook',
    'HookHandle',
    'HookKind',
    'HookResult',
    'HookTrigger',
    'IfRunning',
    'Plugin',
    'ReadLog',
    'Update',
    'When',
    'hook',
]


@overload
def hook(function: Hook[DepsT, StateT], /) -> ContextualOperation[DepsT, StateT]: ...
@overload
def hook(
    *,
    on: HookTrigger[DepsT, StateT] | None = None,
    every: float | None = None,
    after: float | None = None,
    keys: KeyName | Sequence[KeyName] | None = None,
    requires_deps: bool = False,
    if_running: IfRunning = 'replace',
) -> Callable[
    [Hook[DepsT, StateT]],
    ContextualOperation[DepsT, StateT],
]: ...
def hook(
    function: Hook[DepsT, StateT] | None = None,
    /,
    *,
    on: HookTrigger[DepsT, StateT] | None = None,
    every: float | None = None,
    after: float | None = None,
    keys: KeyName | Sequence[KeyName] | None = None,
    requires_deps: bool = False,
    if_running: IfRunning = 'replace',
) -> (
    ContextualOperation[DepsT, StateT]
    | Callable[
        [Hook[DepsT, StateT]],
        ContextualOperation[DepsT, StateT],
    ]
):
    """
    Describe a hook once, to attach to any canvas or placement later.

    It takes the same arguments as ``target.hook(...)`` and returns an operation: pipe it onto
    a target with ``target | operation``, or pass it to ``update``. Each target gets its own
    hook. The function may return an operation, a style or an effect, which is applied to the
    target it runs on.

    Args:
        function: The function to wrap when ``@xnano.hook`` is used without parentheses: a
            function of the [`Context`][xnano.hooks.Context], or one with no parameters.
        on: When the hook runs: a kind of event, the name of a custom event, or a condition;
            see [`HookTrigger`][xnano.hooks.HookTrigger].
        every: Repeat every this many seconds (``'tick'``) or beats (``'beat'``).
        after: Run once after this many seconds (``'tick'``) or beats (``'beat'``).
        keys: The key or keys an ``on='key'`` hook reacts to.
        requires_deps: Whether the hook needs the dependencies given to ``new(deps=...)``.
        if_running: For an ``async def`` function, what happens when the hook runs again
            before its previous run has finished; see [`IfRunning`][xnano.hooks.IfRunning].

    Raises:
        TypeError: ``function`` cannot be called with a context, ``keys`` is not a key name
            or a list of them, or ``on`` is not a kind, a name or a condition.
        ValueError: ``on``, ``every``, ``after``, ``keys`` or ``if_running`` is not valid, or
            they do not fit together.

    Examples:
        ```python
        import xnano

        readings = []

        @xnano.hook(on='frame')
        def clock_readout(context: xnano.Context) -> None:
            readings.append(round(context.clock.elapsed, 1))

        with xnano.new(width=12, height=1) as canvas:
            canvas.screen | clock_readout
            canvas.clock.step(delta_seconds=0.5)
        assert readings == [0.5]
        ```
    """
    kind, condition = resolve_trigger(on, every=every, after=after, keys=keys)
    _check_hook_arguments(
        cast('_Hooked[object, object]', object()), kind, every, after, keys
    )
    compile_when(condition)
    _check_if_running(if_running)
    normalized_keys: tuple[str, ...] = (
        () if keys is None else (keys,) if isinstance(keys, str) else tuple(keys)
    )

    def wrap(
        callback: Hook[DepsT, StateT],
    ) -> ContextualOperation[DepsT, StateT]:
        checked = _check_hook_function(callback)
        _check_if_running_fits(checked, if_running)
        return ContextualOperation(
            cast('Callable[[Context[DepsT, StateT]], object]', checked),
            on=on,
            every=every,
            after=after,
            keys=normalized_keys,
            requires_deps=requires_deps,
            if_running=if_running,
        )

    if function is not None:
        return wrap(function)
    return wrap
