"""
xnano.operations

Operations that change or animate a buffer, placement or canvas.

Pass operations to ``update``, pipe them with ``|``, or write them with ``write``. Create
contextual operations from functions with [`hook`][xnano.operations.hook], shade
pixels with [`shade`][xnano.operations.shade], make placements draggable with
[`draggable`][xnano.operations.draggable], or build typed style, border, block and effect
customizations with [`fx`][xnano.operations.fx].
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Generic, Literal, TypeAlias, TypeVar, cast, overload

import xnano_core as _core
from xnano._axes import to_rgb
from xnano._customize import (
    Customization as Customization,
)
from xnano._customize import (
    CustomizationKind as CustomizationKind,
)
from xnano._customize import (
    fx as fx,
)
from xnano._hooks import HookHandle, Trigger
from xnano._values import RGB, ColorValue, DepsT, PixelEncoding, Renderable, StateT
from xnano.context import Context, Frame, Update
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
    EventContext,
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

OperationTrigger: TypeAlias = Literal[
    'immediate',
    'frame',
    'tick',
    'key',
    'click',
    'drag',
    'mouse',
    'paste',
    'resize',
    'state_change',
]
"""When a [`ContextualOperation`][xnano.operations.ContextualOperation] runs."""

OperationResult: TypeAlias = (
    '_core.Operation | _core.Style | _core.Buffer | Renderable | str | None'
)
"""What a function decorated with [`hook`][xnano.operations.hook] may return."""


def _shade_surface(
    surface: _core.Surface,
    function: Callable[[int, int], ColorValue | None],
    encoding: PixelEncoding,
) -> None:
    view = surface.pixels(encoding=encoding)
    colored: list[tuple[int, int, RGB]] = []
    for row in range(view.height):
        for column in range(view.width):
            color = function(column, row)
            if color is not None:
                colored.append((column, row, to_rgb(color)))
    view.write(colored)


def _apply_result_to_surface(
    surface: _core.Surface,
    result: OperationResult,
    target: Canvas[object, object] | Placement[object, object] | None = None,
) -> None:
    if result is None:
        return
    if isinstance(result, (ContextualOperation, Customization)):
        if target is not None:
            result.apply_to(target)
        else:
            result.apply_to_surface(surface)
        return
    if isinstance(result, _core.Operation):
        surface.update(result)
        return
    if isinstance(result, _core.Style):
        surface.update(_core.ApplyStyle(result))
        return
    if isinstance(result, str):
        from xnano.placement import Placement

        if isinstance(target, Placement):
            target.text = result
        else:
            surface.update(_core.Fill(' '), _core.Write(result))
        return
    if isinstance(result, _core.Buffer):
        surface.update(_core.Paste(result, mode='replace'))
        return
    if isinstance(result, Renderable):
        surface.update(_core.Paste(result.__xnano_buffer__(), mode='replace'))


class ContextualOperation(Operation, Generic[DepsT, StateT]):
    """
    A composable operation that customizes or animates a buffer, placement or canvas.

    Build one with [`hook`][xnano.operations.hook], [`shade`][xnano.operations.shade],
    [`draggable`][xnano.operations.draggable] or [`fx`][xnano.operations.fx].
    Apply it with ``|``, ``|=``, ``write`` or ``update``.

    Attributes:
        on: When the operation runs (``'immediate'``, ``'frame'``, ``'drag'``, ``'click'``, ``'key'``, etc.).
        every: Steady interval in seconds between calls, or ``None``.
        after: One-shot delay in seconds before the call, or ``None``.
        keys: Key names that trigger a ``'key'`` operation.

    Examples:
        ```python
        import xnano

        @xnano.hook(on='frame')
        def banner(context: xnano.context.Context) -> str:
            return f'width={context.width}'

        with xnano.new(width=16, height=1) as canvas:
            placed = canvas.write(banner)
            assert placed.text == 'width=16'
        ```
    """

    __xnano_operation__ = True

    def __init__(
        self,
        callback: Callable[[Context[DepsT, StateT]], OperationResult] | None = None,
        *,
        on: OperationTrigger = 'frame',
        every: float | None = None,
        after: float | None = None,
        keys: tuple[str, ...] = (),
        when: Trigger[DepsT, StateT] | None = None,
        surface_runner: Callable[[_core.Surface], None] | None = None,
        placement_runner: Callable[[Placement[DepsT, StateT]], None] | None = None,
        steps: Sequence[_core.Operation] = (),
    ) -> None:
        """
        Create a contextual operation.

        Args:
            callback: Function called with a [`Context`][xnano.context.Context] when triggered.
            on: Trigger kind that runs ``callback``.
            every: Optional interval in seconds for periodic execution.
            after: Optional delay in seconds for one-shot execution.
            keys: Key names to match when ``on='key'``.
            when: Custom trigger function or generator.
            surface_runner: Direct action on a [`Surface`][xnano_core.Surface] when ``on='immediate'``.
            placement_runner: Direct action on a [`Placement`][xnano.placement.Placement] when attached.
            steps: Chained operations to apply in sequence.
        """
        super().__init__()
        self._callback = callback
        self._is_tick = on == 'tick'
        if every is not None:
            self._trigger = _core.Trigger.every(every)
        elif after is not None:
            self._trigger = _core.Trigger.after(after)
        else:
            # A tick is the core's simulation update.
            self._trigger = _core.Trigger.named(
                'update' if on == 'tick' else on, keys=keys
            )
        self._when = when
        self._surface_runner = surface_runner
        self._placement_runner = placement_runner
        self._steps: tuple[_core.Operation, ...] = tuple(steps)

    @property
    def trigger(self) -> _core.Trigger:
        """The native [`Trigger`][xnano_core.Trigger] that says when the operation runs."""
        return self._trigger

    @property
    def on(self) -> OperationTrigger:
        """When the operation runs."""
        if self._is_tick:
            return 'tick'
        return cast('OperationTrigger', self._trigger.kind)

    @property
    def every(self) -> float | None:
        """Steady interval in seconds between calls, or ``None``."""
        return self._trigger.seconds if self._trigger.kind == 'every' else None

    @property
    def after(self) -> float | None:
        """One-shot delay in seconds before the call, or ``None``."""
        return self._trigger.seconds if self._trigger.kind == 'after' else None

    @property
    def keys(self) -> tuple[str, ...]:
        """Key names that trigger a ``'key'`` operation."""
        return tuple(self._trigger.keys)

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
        return ContextualOperation(on='immediate', steps=combined)

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
            return cast(
                'TargetT', ContextualOperation(on='immediate', steps=(target, self))
            )
        self.apply_to(
            cast(
                'Canvas[DepsT, StateT] | Placement[DepsT, StateT] | _core.Surface',
                target,
            )
        )
        return target

    def apply_to_surface(self, surface: _core.Surface) -> None:
        """
        Apply immediate steps of this operation to a core [`Surface`][xnano_core.Surface].

        Args:
            surface: The buffer or region to modify.
        """
        if self._steps:
            for step in self._steps:
                if isinstance(step, (ContextualOperation, Customization)):
                    step.apply_to_surface(surface)
                else:
                    surface.update(step)
            return
        if self._surface_runner is not None:
            self._surface_runner(surface)

    def apply_to(
        self,
        target: Canvas[DepsT, StateT] | Placement[DepsT, StateT] | _core.Surface,
    ) -> None:
        """
        Attach or execute this operation on ``target``.

        Args:
            target: A [`Canvas`][xnano.canvas.Canvas], a
                [`Placement`][xnano.placement.Placement] or a [`Surface`][xnano_core.Surface].
        """
        from xnano.canvas import Canvas
        from xnano.placement import Placement

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
        if self._placement_runner is not None and isinstance(target, Placement):
            self._placement_runner(target)
            return
        if self._surface_runner is not None and self._trigger.kind == 'immediate':
            self._surface_runner(target._buffer)
            return
        callback = self._callback
        if callback is None:
            return
        canvas: Canvas[DepsT, StateT] = (
            target if isinstance(target, Canvas) else target.canvas
        )
        surface = target._buffer

        def run_with_context(context: Context[DepsT, StateT]) -> None:
            result = callback(context)
            _apply_result_to_surface(
                surface,
                result,
                cast('Canvas[object, object] | Placement[object, object]', target),
            )

        # Errors name the function the user wrote, not this wrapper.
        run_with_context.__name__ = getattr(callback, '__name__', 'hook')
        dummy_handle: HookHandle[DepsT, StateT] = HookHandle(
            target, run_with_context, None
        )

        def build_adhoc_context(
            event: Frame | Update | None = None,
        ) -> Context[DepsT, StateT]:
            return target._context_for(None, dummy_handle, event=event)

        trigger = self._trigger
        if self._is_tick:

            def on_tick(update: Update) -> None:
                if isinstance(target, Placement) and target._removed:
                    canvas._unregister(tick_registration)
                    return
                run_with_context(build_adhoc_context(update))

            tick_registration = canvas._on_update(on_tick, fixed_step_seconds=self.every)
            return
        if self._when is not None:
            target.hook(run_with_context, when=self._when)
            return
        if trigger.kind == 'every':
            target.every(cast('float', trigger.seconds))(run_with_context)
            return
        if trigger.kind == 'after':
            target.after(cast('float', trigger.seconds))(run_with_context)
            return
        if trigger.kind == 'immediate':
            run_with_context(build_adhoc_context())
            return
        if trigger.kind == 'frame':
            run_with_context(build_adhoc_context())

            def on_frame(frame: Frame) -> None:
                if isinstance(target, Placement) and target._removed:
                    stop_frames()
                    return
                run_with_context(build_adhoc_context(frame))

            stop_frames = canvas._on_frame(on_frame)
            return
        target.hook(run_with_context, when=trigger)


@overload
def hook(
    function: Callable[[Context[DepsT, StateT]], OperationResult], /
) -> ContextualOperation[DepsT, StateT]: ...
@overload
def hook(
    *,
    on: OperationTrigger = 'frame',
    every: float | None = None,
    after: float | None = None,
    keys: str | Sequence[str] | None = None,
    when: Trigger[DepsT, StateT] | None = None,
) -> Callable[
    [Callable[[Context[DepsT, StateT]], OperationResult]],
    ContextualOperation[DepsT, StateT],
]: ...
def hook(
    function: Callable[[Context[DepsT, StateT]], OperationResult] | None = None,
    /,
    *,
    on: OperationTrigger = 'frame',
    every: float | None = None,
    after: float | None = None,
    keys: str | Sequence[str] | None = None,
    when: Trigger[DepsT, StateT] | None = None,
) -> (
    ContextualOperation[DepsT, StateT]
    | Callable[
        [Callable[[Context[DepsT, StateT]], OperationResult]],
        ContextualOperation[DepsT, StateT],
    ]
):
    """
    Turn a function of [`Context`][xnano.context.Context] into a reusable [`ContextualOperation`][xnano.operations.ContextualOperation].

    The decorated function receives a [`Context`][xnano.context.Context] and may either mutate state
    and placements directly or return text, a buffer, a style or another operation (such as
    [`shade`][xnano.operations.shade] or [`fx`][xnano.operations.fx]) to update
    the target.

    Args:
        function: The function to wrap when ``@xnano.hook`` is used without parentheses.
        on: When the operation runs: ``'frame'`` (default), ``'drag'``, ``'click'``,
            ``'key'``, ``'tick'``, ``'mouse'``, ``'paste'``, ``'resize'``,
            ``'state_change'`` or ``'immediate'``. ``'tick'`` with ``every`` runs once for
            every step of ``every`` seconds.
        every: Run at a steady interval in seconds on the canvas's clock.
        after: Run once after this many seconds on the canvas's clock.
        keys: Key name or sequence of key names when ``on='key'``.
        when: Custom trigger function or generator.

    Examples:
        ```python
        import xnano

        @xnano.hook(on='frame')
        def clock_readout(context: xnano.context.Context) -> str:
            return f'{context.time.elapsed:.1f}s'

        with xnano.new(width=12, height=1) as canvas:
            readout = canvas.write(clock_readout)
            canvas.step(delta_seconds=0.5)
            assert readout.text == '0.5s'
        ```
    """
    normalized_keys: tuple[str, ...] = (
        () if keys is None else (keys,) if isinstance(keys, str) else tuple(keys)
    )

    def wrap(
        callback: Callable[[Context[DepsT, StateT]], OperationResult],
    ) -> ContextualOperation[DepsT, StateT]:
        return ContextualOperation(
            callback,
            on=on,
            every=every,
            after=after,
            keys=normalized_keys,
            when=when,
        )

    if function is not None:
        return wrap(function)
    return wrap


def shade(
    function: Callable[[int, int], ColorValue | None],
    *,
    encoding: PixelEncoding = 'half_blocks',
) -> ContextualOperation[object, object]:
    """
    Create an operation that colors every pixel of its target from ``function(column, row)``.

    Pipe it onto a buffer, canvas or placement with ``|``, pass it to ``write``, or
    return it from an [`hook`][xnano.operations.hook] that runs on every frame.

    Args:
        function: Called with ``(column, row)`` in pixels; return a color or ``None``.
        encoding: ``'half_blocks'`` (two vertical pixels per cell) or ``'braille'``.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=2) as canvas:
            canvas | xnano.operations.shade(lambda column, row: (column * 20, row * 40, 120))
            assert canvas.core_buffer[0, 0].symbol == '▀'
        ```
    """
    return ContextualOperation(
        on='immediate',
        surface_runner=lambda surface: _shade_surface(surface, function, encoding),
    )


def draggable(axis: Literal['x', 'y'] = 'x') -> ContextualOperation[object, object]:
    """
    Create an operation that lets the pointer drag a placement along ``axis``.

    Give the placement a range on that axis first (such as ``x=(0, 39)``) and pipe
    ``| xnano.operations.draggable()`` onto the placement or canvas. When the placement lives inside a
    parent placement (added with ``parent.write(...)``), dragging moves it in the parent's
    coordinate space.

    Args:
        axis: ``'x'`` or ``'y'``.

    Raises:
        ValueError: ``axis`` is neither ``'x'`` nor ``'y'``.

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=3) as canvas:
            thumb = canvas.write('█', x=(0, 10), y=1) | xnano.operations.draggable()
            assert thumb.x == 0
        ```
    """
    if axis not in ('x', 'y'):
        raise ValueError(f'{axis!r} is not an axis draggable can move. Use "x" or "y".')

    def attach(placement: Placement[object, object]) -> None:
        @placement.on_click
        def grab(context: Context[object, object]) -> None:
            if isinstance(context.core, EventContext):
                context.core.capture_pointer()

        @placement.on_drag
        def move(context: Context[object, object]) -> None:
            mouse = context.mouse
            if mouse is None:
                return
            local_point = context.parent.local(mouse.position)
            setattr(
                placement,
                axis,
                local_point.x if axis == 'x' else local_point.y,
            )

    return ContextualOperation(on='immediate', placement_runner=attach)


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
    'OperationTrigger',
    'Paste',
    'Place',
    'Resize',
    'Write',
    'fx',
    'draggable',
    'hook',
    'shade',
]
