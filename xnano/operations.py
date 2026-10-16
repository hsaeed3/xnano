"""
xnano.operations

Operations that change or animate a buffer, placement or canvas.

Pass operations to ``update`` or pipe them with ``|``. Create a reusable hook from a function
with [`hook`][xnano.operations.hook], or build typed style, border, block and effect
customizations with [`fx`][xnano.operations.fx].
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Generic, TypeAlias, TypeVar, cast, overload

import xnano_core as _core
from xnano._customize import (
    Customization as Customization,
)
from xnano._customize import (
    CustomizationKind as CustomizationKind,
)
from xnano._customize import (
    fx as fx,
)
from xnano._hooks import HookKind, When
from xnano._values import DepsT, KeyName, StateT
from xnano.context import Context
from xnano_core import (
    ApplyStyle as ApplyStyle,
)
from xnano_core import (
    Background as Background,
)
from xnano_core import (
    Border as Border,
)
from xnano_core import (
    Clear as Clear,
)
from xnano_core import (
    Fill as Fill,
)
from xnano_core import (
    Foreground as Foreground,
)
from xnano_core import (
    Layout as Layout,
)
from xnano_core import (
    Margin as Margin,
)
from xnano_core import (
    Move as Move,
)
from xnano_core import (
    Operation as Operation,
)
from xnano_core import (
    Paste as Paste,
)
from xnano_core import (
    Place as Place,
)
from xnano_core import (
    Resize as Resize,
)
from xnano_core import (
    Write as Write,
)

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.placement import Placement

TargetT = TypeVar('TargetT')

OperationResult: TypeAlias = '_core.Operation | _core.Style | Customization | None'
"""What a function decorated with [`hook`][xnano.operations.hook] may return."""


class ContextualOperation(Operation, Generic[DepsT, StateT]):
    """
    A reusable hook that can be piped onto any canvas or placement.

    Build one with [`hook`][xnano.operations.hook]. Apply it with ``|``, ``|=`` or ``update``,
    and it attaches the same hook that ``target.hook(function, ...)`` would.

    Attributes:
        on: When the hook runs, or ``None`` for every input event.
        every: Seconds (``'tick'``) or beats (``'beat'``) between runs, or ``None``.
        after: Delay before the one run, or ``None``.
        keys: Key names an ``on='key'`` hook reacts to.

    Examples:
        ```python
        import xnano

        counted = []

        @xnano.hook(on='tick', every=0.5)
        def count(context: xnano.context.Context) -> None:
            counted.append(context.time.elapsed)

        with xnano.new(width=16, height=1) as canvas:
            canvas | count
            canvas.step(delta_seconds=1.0)
        assert len(counted) == 2
        ```
    """

    __xnano_operation__ = True

    def __init__(
        self,
        callback: Callable[[Context[DepsT, StateT]], object] | None = None,
        *,
        on: HookKind | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: tuple[str, ...] = (),
        when: When[DepsT, StateT] | None = None,
        requires_deps: bool = False,
        steps: Sequence[_core.Operation] = (),
    ) -> None:
        """
        Create a reusable hook. Use [`hook`][xnano.operations.hook] instead of calling this.

        Args:
            callback: Function called with a [`Context`][xnano.context.Context] when the hook
                runs.
            on: What the hook listens to.
            every: Interval between runs.
            after: Delay before the one run.
            keys: Key names to react to when ``on='key'``.
            when: A condition that must hold.
            requires_deps: Whether the hook needs the canvas's dependencies.
            steps: Chained operations to apply in sequence.
        """
        super().__init__()
        self._callback = callback
        self._hook_on = on
        self._every = every
        self._after = after
        self._keys = tuple(keys)
        self._when = when
        self._requires_deps = requires_deps
        self._steps: tuple[_core.Operation, ...] = tuple(steps)

    @property
    def on(self) -> HookKind | None:
        """What the hook listens to, or ``None`` for every input event."""
        return cast('HookKind | None', self._hook_on)

    @property
    def every(self) -> float | None:
        """Interval between runs, or ``None``."""
        return self._every

    @property
    def after(self) -> float | None:
        """Delay before the one run, or ``None``."""
        return self._after

    @property
    def keys(self) -> tuple[str, ...]:
        """Key names an ``on='key'`` hook reacts to."""
        return self._keys

    def then(self, other: _core.Operation) -> ContextualOperation[DepsT, StateT]:
        """
        Return a new operation that applies this operation and then ``other``.

        Args:
            other: The next operation to run.
        """
        combined: list[_core.Operation] = list(self._steps) if self._steps else [self]
        if isinstance(other, ContextualOperation) and other._steps:
            combined.extend(other._steps)
        else:
            combined.append(other)
        return ContextualOperation(steps=combined)

    def __or__(  # type: ignore[override]
        self, other: _core.Operation | _core.Style
    ) -> ContextualOperation[DepsT, StateT]:
        """Combine this operation with another operation or style."""
        if isinstance(other, _core.Style):
            return self.then(_core.ApplyStyle(other))
        return self.then(other)

    def __ror__(self, target: TargetT) -> TargetT:
        """Apply this operation to ``target`` when piped with ``target | operation``."""
        if isinstance(target, _core.Operation):
            return cast('TargetT', ContextualOperation(steps=(target, self)))
        self.apply_to(
            cast(
                'Canvas[DepsT, StateT] | Placement[DepsT, StateT] | _core.Surface',
                target,
            )
        )
        return target

    def apply_to_surface(self, surface: _core.Surface) -> None:
        """
        Apply the chained steps of this operation to a core [`Surface`][xnano_core.Surface].

        A hook has no surface to listen on, so only its chained steps apply.

        Args:
            surface: The buffer or region to modify.
        """
        for step in self._steps:
            if isinstance(step, (ContextualOperation, Customization)):
                step.apply_to_surface(surface)
            else:
                surface.update(step)

    def apply_to(
        self,
        target: Canvas[DepsT, StateT] | Placement[DepsT, StateT] | _core.Surface,
    ) -> None:
        """
        Attach this hook to ``target``, or apply its chained steps.

        Args:
            target: A [`Canvas`][xnano.canvas.Canvas], a
                [`Placement`][xnano.placement.Placement] or a [`Surface`][xnano_core.Surface].
        """
        if isinstance(target, _core.Surface):
            self.apply_to_surface(target)
            return
        if self._steps:
            for step in self._steps:
                if isinstance(step, (ContextualOperation, Customization)):
                    step.apply_to(
                        cast('Canvas[object, object] | Placement[object, object]', target)
                    )
                else:
                    target.update(step)
            return
        callback = self._callback
        if callback is None:
            return
        target.hook(
            callback,
            on=cast('HookKind | None', self._hook_on),
            when=self._when,
            every=self._every,
            after=self._after,
            keys=self._keys or None,
            requires_deps=self._requires_deps,
        )


@overload
def hook(
    function: Callable[[Context[DepsT, StateT]], object], /
) -> ContextualOperation[DepsT, StateT]: ...
@overload
def hook(
    *,
    on: HookKind | None = None,
    when: When[DepsT, StateT] | None = None,
    every: float | None = None,
    after: float | None = None,
    keys: KeyName | Sequence[KeyName] | None = None,
    requires_deps: bool = False,
) -> Callable[
    [Callable[[Context[DepsT, StateT]], object]],
    ContextualOperation[DepsT, StateT],
]: ...
def hook(
    function: Callable[[Context[DepsT, StateT]], object] | None = None,
    /,
    *,
    on: HookKind | None = None,
    when: When[DepsT, StateT] | None = None,
    every: float | None = None,
    after: float | None = None,
    keys: KeyName | Sequence[KeyName] | None = None,
    requires_deps: bool = False,
) -> (
    ContextualOperation[DepsT, StateT]
    | Callable[
        [Callable[[Context[DepsT, StateT]], object]],
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
        function: The function to wrap when ``@xnano.hook`` is used without parentheses.
        on: What the hook listens to; see [`HookKind`][xnano.types.HookKind].
        when: A condition that must hold; see [`When`][xnano.types.When].
        every: Repeat every this many seconds (``'tick'``) or beats (``'beat'``).
        after: Run once after this many seconds (``'tick'``) or beats (``'beat'``).
        keys: The key or keys an ``on='key'`` hook reacts to.
        requires_deps: Whether the hook needs the dependencies given to ``new(deps=...)``.

    Examples:
        ```python
        import xnano

        readings = []

        @xnano.hook(on='frame')
        def clock_readout(context: xnano.context.Context) -> None:
            readings.append(round(context.time.elapsed, 1))

        with xnano.new(width=12, height=1) as canvas:
            canvas | clock_readout
            canvas.step(delta_seconds=0.5)
        assert readings == [0.5]
        ```
    """
    normalized_keys: tuple[str, ...] = (
        () if keys is None else (keys,) if isinstance(keys, str) else tuple(keys)
    )

    def wrap(
        callback: Callable[[Context[DepsT, StateT]], object],
    ) -> ContextualOperation[DepsT, StateT]:
        return ContextualOperation(
            callback,
            on=on,
            every=every,
            after=after,
            keys=normalized_keys,
            when=when,
            requires_deps=requires_deps,
        )

    if function is not None:
        return wrap(function)
    return wrap


__all__ = [
    'ApplyStyle',
    'Background',
    'Border',
    'Clear',
    'ContextualOperation',
    'Customization',
    'CustomizationKind',
    'Fill',
    'Foreground',
    'Layout',
    'Margin',
    'Move',
    'Operation',
    'OperationResult',
    'Paste',
    'Place',
    'Resize',
    'Write',
    'fx',
    'hook',
]
