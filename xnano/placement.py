"""
xnano.placement

A buffer placed on a terminal, with a position and size that are formulas.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core
from xnano_core import (
    EvaluationContext,
    EventContext,
)

if TYPE_CHECKING:
    from xnano.terminal import Terminal

from xnano._axes import axis_expression, axis_limits, inspect_number
from xnano._hooks import _Hooked
from xnano._values import (
    Axis,
    AxisName,
    Bound,
    ColorValue,
    NumericExpression,
    PixelEncoding,
    StateT,
)
from xnano.context import Context
from xnano.pixels import Pixels
from xnano.scene import Scene


class Placement(_Hooked[StateT]):
    """
    A buffer placed on a terminal, with a position and size that are formulas.

    Assign any of ``x``, ``y``, ``width`` and ``height`` an [`Axis`][xnano.types.Axis]:
    a number, a percentage of the parent, or an expression. Numbers apply at once;
    everything else is evaluated again before every frame, so a placement can follow the
    clock, the terminal's size or another buffer without a callback.

    Assigning a range instead (``(0, 20)``) limits the axis rather than setting it.
    For ``x`` and ``y`` the range is how far the placement may travel, so a slider's thumb
    is a placement whose ``x`` is limited to its track; whatever is assigned to it later,
    by a mouse hook for example, is held inside the track. For ``width`` and ``height`` it
    is the smallest and largest size.

    Percentages and ranges only change when something about the terminal does, so they
    cost nothing while it is still. An expression is assumed to change with time, so a
    terminal with one keeps drawing every frame; use a percentage for a layout that only
    follows the size of the terminal.

    Get one from [`Terminal.add`][xnano.Terminal.add].

    Attributes:
        buffer: The buffer that is placed.
        terminal: The terminal the buffer is placed on.
        x: The column of the left edge, relative to the terminal.
        y: The row of the top edge, relative to the terminal.
        width: The width in cells.
        height: The height in cells.
        layer: Placements with a higher layer are drawn over those with a lower one.
        is_visible: Whether the buffer is drawn.

    Examples:
        ```python
        import xnano
        from xnano_core import Buffer, ParentWidth, Width

        with xnano.open(offscreen=True, width=20, height=3) as terminal:
            label = terminal.add(Buffer.with_text('hi'))
            label.x = (ParentWidth - Width) // 2
            assert label.x == 9

            thumb = terminal.add(Buffer.with_text('#'))
            thumb.x = (2, 10)   # may travel from column 2 to column 10
            thumb.x = 40
            assert thumb.x == 10
            thumb.x = 0
            assert thumb.x == 2
        ```
    """

    def __init__(self, terminal: Terminal[StateT], buffer: _core.Buffer) -> None:
        # Created by ``Terminal.add``; not constructed directly.
        """
        Place a buffer on a terminal. Get one from ``terminal.add`` instead of calling this.

        Args:
            terminal: The terminal the buffer is placed on.
            buffer: The buffer that is placed.
        """
        super().__init__()
        self._terminal = terminal
        self._buffer = buffer
        # axis -> (expression, whether it is assumed to change with time)
        self._bindings: dict[AxisName, tuple[NumericExpression, bool]] = {}
        # axis -> (lowest bound, highest bound, whether a bound is assumed to change with time)
        self._limits: dict[AxisName, tuple[Bound | None, Bound | None, bool]] = {}
        self._removed = False

    @property
    def buffer(self) -> _core.Buffer:
        """The buffer that is placed."""
        return self._buffer

    @property
    def terminal(self) -> Terminal[StateT]:
        """The terminal the buffer is placed on."""
        return self._terminal

    def _set_axis(self, axis: AxisName, value: Axis) -> None:
        self._terminal._require_open()
        if isinstance(value, tuple):
            low, high = axis_limits(value, axis)
            is_time_dependent = any(
                isinstance(bound, _core.NumericValue) for bound in value
            )
            with self._terminal._lock:
                previous = self._limits.get(axis)
                if low is None and high is None:
                    self._limits.pop(axis, None)
                else:
                    self._limits[axis] = (low, high, is_time_dependent)
            try:
                self._enforce(axis)
            except ValueError:
                # A range that cannot hold anything is refused, and the old one stays.
                with self._terminal._lock:
                    if previous is None:
                        self._limits.pop(axis, None)
                    else:
                        self._limits[axis] = previous
                raise
            self._terminal._bindings_changed(self)
            return
        converted = axis_expression(value, axis)
        if isinstance(converted, (int, float)):
            with self._terminal._lock:
                self._bindings.pop(axis, None)
            self._assign_within_limits(axis, converted)
            return
        is_time_dependent = isinstance(value, _core.NumericValue)
        with self._terminal._lock:
            self._bindings[axis] = (converted, is_time_dependent)
        # Formulas that only read geometry are known at once. A formula may read something
        # only the terminal's own loop can read (the clock, the microphone), so from another
        # thread the loop evaluates it, and the caller never waits.

        def evaluate() -> None:
            try:
                self._assign_within_limits(axis, inspect_number(self._buffer, converted))
            except _core.RuntimeRequiredError:
                pass

        if self._terminal._host.is_on_loop():
            evaluate()
        else:
            self._terminal._host.post(evaluate)
        self._terminal._bindings_changed(self)

    def _assign(self, axis: AxisName, value: int) -> None:
        if getattr(self._buffer, axis) != value:
            setattr(self._buffer, axis, value)

    def _clamp(
        self, axis: AxisName, value: float, resolve: Callable[[Bound], float]
    ) -> float:
        """Hold a value inside the axis's range, if it has one."""
        limits = self._limits.get(axis)
        if limits is None:
            return value
        low_bound, high_bound, _ = limits
        low = None if low_bound is None else resolve(low_bound)
        high = None if high_bound is None else resolve(high_bound)
        if low is not None and high is not None and low > high:
            raise ValueError(
                f'The range for {axis} starts at {low:g} but ends at {high:g}. Its bounds '
                f'are expressions, so check that the first never exceeds the second.'
            )
        if low is not None:
            value = max(value, low)
        if high is not None:
            value = min(value, high)
        return value

    def _resolve_offline(self, bound: Bound) -> float:
        if isinstance(bound, (int, float)):
            return bound
        if not self._terminal._host.is_on_loop():
            raise _core.RuntimeRequiredError(
                'a bound that is a formula is evaluated by the terminal on its next frame'
            )
        return inspect_number(self._buffer, bound)

    def _assign_within_limits(self, axis: AxisName, value: float) -> None:
        """Assign a value now, held inside the range when the range is known now."""
        try:
            value = self._clamp(axis, value, self._resolve_offline)
        except _core.RuntimeRequiredError:
            pass  # a bound follows time; the next frame holds the value in the range
        self._assign(axis, _round_half_away(value))

    def _enforce(self, axis: AxisName) -> None:
        """Hold the current value of an axis inside its range."""
        self._assign_within_limits(axis, getattr(self._buffer, axis))

    def _apply_bindings(self, runtime: _core.Runtime) -> bool:
        """Evaluate every formula on the terminal's loop; return whether any follows time."""
        with self._terminal._lock:
            bindings = dict(self._bindings)
            limits = dict(self._limits)

        def resolve(bound: Bound) -> float:
            if isinstance(bound, (int, float)):
                return bound
            return bound.evaluate(EvaluationContext(buffer=self._buffer, runtime=runtime))

        axes: set[AxisName] = {*bindings, *limits}
        for axis in axes:
            if axis in bindings:
                expression, _ = bindings[axis]
                value = expression.evaluate(
                    EvaluationContext(buffer=self._buffer, runtime=runtime)
                )
            else:
                value = getattr(self._buffer, axis)
            self._assign(axis, _round_half_away(self._clamp(axis, value, resolve)))
        return any(flag for _, flag in bindings.values()) or any(
            flag for _, _, flag in limits.values()
        )

    @property
    def x(self) -> int:
        """The column of the left edge, relative to the terminal."""
        return self._buffer.x

    @x.setter
    def x(self, value: Axis) -> None:
        """Set the column from an [`Axis`][xnano.types.Axis]; a range limits how far it may travel."""
        self._set_axis('x', value)

    @property
    def y(self) -> int:
        """The row of the top edge, relative to the terminal."""
        return self._buffer.y

    @y.setter
    def y(self, value: Axis) -> None:
        """Set the row from an [`Axis`][xnano.types.Axis]; a range limits how far it may travel."""
        self._set_axis('y', value)

    @property
    def width(self) -> int:
        """The width in cells."""
        return self._buffer.width

    @width.setter
    def width(self, value: Axis) -> None:
        """Set the width from an [`Axis`][xnano.types.Axis]; a range limits the smallest and largest size."""
        self._set_axis('width', value)

    @property
    def height(self) -> int:
        """The height in cells."""
        return self._buffer.height

    @height.setter
    def height(self, value: Axis) -> None:
        """Set the height from an [`Axis`][xnano.types.Axis]; a range limits the smallest and largest size."""
        self._set_axis('height', value)

    @property
    def layer(self) -> int:
        """Placements with a higher layer are drawn over those with a lower one."""
        return self._buffer.layer

    @layer.setter
    def layer(self, value: int) -> None:
        self._buffer.layer = value

    @property
    def is_visible(self) -> bool:
        """Whether the buffer is drawn."""
        return self._buffer.is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._buffer.is_visible = value

    def pixels(self, *, encoding: PixelEncoding = 'half_blocks') -> Pixels:
        """
        Return a [`Pixels`][xnano.Pixels] view of the placed buffer.

        Args:
            encoding: How pixels are packed into cells.
        """
        return Pixels(self._buffer.pixels(encoding=encoding))

    def scene(
        self,
        world_width: int,
        world_height: int,
        *,
        background: ColorValue = (0, 0, 0),
    ) -> Scene:
        """
        Make a pixel world drawn on this placement, seen through a camera.

        Put sprites in it with [`Scene.add`][xnano.scene.Scene.add]; the scene redraws only when
        something changed. See [`Scene`][xnano.scene.Scene].

        Args:
            world_width: The width of the world in pixels.
            world_height: The height of the world in pixels.
            background: The color shown where no sprite is drawn.
        """
        return Scene(
            cast('Placement[object]', self), world_width, world_height, background
        )

    @property
    def text(self) -> str:
        """
        The text shown, line by line.

        Assign new text to change what a text placement says; the placement grows or shrinks
        to fit it, unless its size was set.
        """
        return self._buffer.text

    @text.setter
    def text(self, value: str) -> None:
        self._terminal._require_open()
        lines = value.split('\n')
        self.width = max(len(line) for line in lines)
        self.height = len(lines)
        self._buffer.update(_core.Fill(' '), _core.Write(value))

    def update(self, *operations: _core.Operation) -> None:
        """
        Change this placement's content with operations, such as an effect.

        Args:
            operations: What to apply, in order: text to write, a style, or an effect such
                as ``Effect.dissolve(duration_milliseconds=500)``.

        Examples:
            ```python
            import xnano
            from xnano.effects import Effect

            with xnano.open(offscreen=True, width=20, height=3) as terminal:
                title = terminal.add('Welcome')
                title.update(Effect.dissolve(duration_milliseconds=500))
            ```
        """
        self._terminal._require_open()
        self._buffer.update(*operations)

    def make_draggable(self, axis: Literal['x', 'y'] = 'x') -> None:
        """
        Let the pointer move this placement along one axis by dragging it.

        Pressing the placement grabs the pointer, so the drag keeps going when the pointer
        leaves it. The placement follows the pointer's position on the terminal. Give the
        axis a range first, such as ``placement.x = (0, 19)``, and the drag stays inside it.
        Open the terminal with ``mouse='buttons'`` to receive drags.

        Args:
            axis: ``'x'`` or ``'y'``.

        Raises:
            ValueError: ``axis`` is neither ``'x'`` nor ``'y'``.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=20, height=3) as terminal:
                thumb = terminal.add('#', x=(0, 10), y=0)
                thumb.make_draggable()
                assert thumb.x == 0
            ```
        """
        if axis not in ('x', 'y'):
            raise ValueError(
                f'{axis!r} is not an axis make_draggable can move. Use "x" or "y".'
            )

        @self.on_click
        def grab(context: Context[StateT]) -> None:
            # Keep hearing the drag after the pointer leaves the placement.
            if isinstance(context.core, EventContext):
                context.core.capture_pointer()

        @self.on_drag
        def move(context: Context[StateT]) -> None:
            mouse = context.mouse
            if mouse is None:
                return
            setattr(self, axis, mouse.position.x if axis == 'x' else mouse.position.y)

    def remove(self) -> None:
        """Take the buffer off the terminal. Removing twice is harmless."""
        if self._removed:
            return
        self._removed = True
        self._cancel_hooks()
        with self._terminal._lock:
            self._bindings.clear()
            self._limits.clear()
        self._terminal._release(self)

    def __repr__(self) -> str:
        state = 'removed' if self._removed else f'x={self.x}, y={self.y}'
        return f'Placement({state}, width={self.width}, height={self.height})'


def _round_half_away(value: float) -> int:
    """Round to the nearest whole number, halves away from zero."""
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)
