"""
xnano.placement

A buffer placed on a canvas, with a position and size that are formulas.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core
from xnano_core import EvaluationContext

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.components import _ComponentDriver
    from xnano.types import RenderableEffectSpecification

from xnano._internal._attributes import refuse_unknown_keywords
from xnano._internal._axes import (
    axis_expression,
    axis_limits,
    check_cells,
    check_count,
    check_edges,
    check_layer,
    check_point,
    check_size,
    inspect_number,
    is_static_formula,
)
from xnano._internal._dynamic_operations import DynamicOperation
from xnano._schema._appearance import ColorValue, Spacing
from xnano._schema._axes import Axis, AxisName, Bound, NumericExpression
from xnano._schema._content import Content
from xnano._schema._generics import DepsT, StateT, WrittenDepsT, WrittenStateT
from xnano._schema._layout import EdgeBehavior
from xnano.appearance._decoration import Decorated, insets_for
from xnano.appearance._look import MOST_CELLS, Appearance
from xnano.appearance._owners import _TextModifiers
from xnano.effects._properties import RenderableEffectProperties
from xnano.effects._registry import apply_effects
from xnano.errors import TerminalClosedError
from xnano.expressions import (
    Parent,
    ParentExpressionScope,
    Root,
    RootExpressionScope,
)
from xnano.hooks._handles import _Hooked
from xnano.operations import (
    ContextualOperation,
)
from xnano.region import Region
from xnano.state import StateNamespace

__all__ = ['Placement']


class Placement(_Hooked[DepsT, StateT], _TextModifiers):
    """
    A buffer placed on a canvas, with a position and size that are formulas.

    Assign any of ``x``, ``y``, ``width`` and ``height`` an [`Axis`][xnano.types.Axis]:
    a number, a percentage of the parent, or an expression. Numbers apply at once;
    everything else is evaluated again before every frame, so a placement can follow the
    clock, the canvas's size or another buffer without a callback.

    Assigning a range instead (``(0, 20)``) limits the axis rather than setting it.
    For ``x`` and ``y`` the range is how far the placement may travel, so a slider's thumb
    is a placement whose ``x`` is limited to its track; whatever is assigned to it later,
    by a drag hook, is held inside the track.
    For ``width`` and ``height`` it is the smallest and largest size.

    Percentages and ranges only change when something about the canvas does, so they
    cost nothing while it is still. An expression is assumed to change with time, so a
    canvas with one keeps drawing every frame; use a percentage for a layout that only
    follows the size of the canvas.

    Get one from [`Canvas.write`][xnano.canvas.Canvas.write] or nest a child placement inside
    another with [`Placement.write`][xnano.placement.Placement.write].

    Attributes:
        core_buffer: The core buffer that is placed.
        canvas: The canvas the buffer is placed on.
        parent: Symbolic expressions for the parent container's ``width``, ``height`` and ``size``.
        root: Symbolic expressions for the root canvas's ``width``, ``height``, ``size`` and ``time``.
        time: Symbolic expression for elapsed seconds on the canvas clock.
        x: The column of the left edge, relative to the parent.
        y: The row of the top edge, relative to the parent.
        width: The width in cells.
        height: The height in cells.
        layer: Placements with a higher layer are drawn over those with a lower one.
        is_visible: Whether the buffer is drawn.
        text: The text shown, line by line.

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=3) as canvas:
            label = canvas.write('hi')
            label.x = (label.parent.width - label.width) // 2
            assert label.x == 9

            thumb = canvas.write('#', x=(2, 10))
            thumb.x = 40
            assert thumb.x == 10
            thumb.x = 0
            assert thumb.x == 2
        ```
    """

    def __init__(
        self,
        canvas: Canvas[DepsT, StateT],
        buffer: _core.Buffer,
        parent_buffer: _core.Buffer | None = None,
        parent_owner: Canvas[object, object] | Placement[object, object] | None = None,
    ) -> None:
        """
        Place a buffer on a canvas. Get one from ``canvas.write`` instead of calling this.

        Args:
            canvas: The canvas the buffer is placed on.
            buffer: The buffer that is placed.
            parent_buffer: The parent buffer ``buffer`` is attached to (defaults to
                ``canvas.core_buffer``).
            parent_owner: The placement or canvas that owns ``parent_buffer`` (defaults to
                ``canvas``).
        """
        super().__init__()
        self._canvas = canvas
        self._buffer = buffer
        self._parent_buffer: _core.Buffer = (
            canvas._root if parent_buffer is None else parent_buffer
        )
        self._parent_owner: Canvas[object, object] | Placement[object, object] = cast(
            'Canvas[object, object] | Placement[object, object]',
            canvas if parent_owner is None else parent_owner,
        )
        self._bindings: dict[AxisName, tuple[NumericExpression, bool]] = {}
        self._limits: dict[AxisName, tuple[Bound | None, Bound | None, bool]] = {}
        self._removed = False
        self._is_text = False
        # Whether the placement draws the look of a box from xnano.box(), whose size
        # includes its border and padding.
        self._is_box = False
        self._edges: EdgeBehavior | None = None
        # An area that terminal.write uses inside a canvas's block follows that canvas.
        self._edges_owner: Canvas[object, object] | None = None
        self._wrapped_text: str | None = None
        self._wrapped_width: int | None = None
        self._appearance: Appearance | None = None
        self._decorated: Decorated | None = None
        self._has_nested = False
        self._state_namespace: StateNamespace | None = None
        self._driver: _ComponentDriver | None = None
        self._renderable_effects = RenderableEffectProperties(
            cast('Placement[object, object]', self)
        )
        self._seal()

    @property
    def core_buffer(self) -> _core.Buffer:
        """
        The core buffer of the content, which core operations and widgets draw into.

        A placement with a border, padding or margin around content that is not plain text
        draws that decoration in a buffer of its own; this is the buffer inside it.
        """
        self._flush_look()
        decorated = self._decorated
        return self._buffer if decorated is None else decorated.inner

    @property
    def _content(self) -> _core.Buffer:
        """The buffer that the content and nested placements live in."""
        decorated = self._decorated
        return self._buffer if decorated is None else decorated.inner

    def local(self, point: _core.Point) -> _core.Point:
        """
        Convert a cell of the screen into a cell of this placement.

        Args:
            point: A cell in screen coordinates, such as ``context.mouse.position``.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.new(width=20, height=4) as canvas:
                placement = canvas.write('hi', x=10, y=1)
                assert placement.local(Point(11, 1)) == Point(1, 0)
            ```
        """
        point = check_point(point)
        bounds = self._buffer._absolute_bounds
        return _core.Point(point.x - bounds.x, point.y - bounds.y)

    @property
    def canvas(self) -> Canvas[DepsT, StateT]:
        """The canvas the buffer is placed on."""
        return self._canvas

    @property
    def state(self) -> StateNamespace:
        """
        State that belongs to this placement, read with ``get`` and written with ``push``.

        It is the state of one placement, separate from the canvas's own
        ([`Canvas.state`][xnano.canvas.Canvas.state]) and from that of other placements, and
        it is deleted when the placement is removed. Asking a removed placement for its state
        raises a [`TerminalClosedError`][xnano.errors.TerminalClosedError], so finish with the
        state before calling ``remove``. See [`StateNamespace`][xnano.state.StateNamespace] for the
        path rules.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                first = canvas.write('a')
                second = canvas.write('b')
                first.state.push('clicks', 2)
                assert first.state.get('clicks') == 2
                assert second.state.get('clicks', default=0) == 0
            ```
        """
        if self._removed:
            raise TerminalClosedError(
                'This placement was removed from its canvas, so it no longer has state. Read '
                'state from canvas.state, or from a placement that is still on the canvas.'
            )
        namespace = self._state_namespace
        if namespace is None:
            namespace = self._state_namespace = self._canvas._new_state_namespace(
                'buffers'
            )
        return namespace

    @property
    def parent(self) -> ParentExpressionScope:
        """Symbolic expressions for the parent container's ``width``, ``height`` and ``size``."""
        return Parent

    @property
    def root(self) -> RootExpressionScope:
        """Symbolic expressions for the root canvas's ``width``, ``height``, ``size`` and ``time``."""
        return Root

    @property
    def time(self) -> _core.NumericValue:
        """Symbolic expression for elapsed seconds on the canvas clock."""
        return _core.TimeElapsed

    def _require_attached(self) -> None:
        """Raise when the canvas is closed or this placement was removed from it."""
        self._canvas._require_open()
        if self._removed:
            raise TerminalClosedError(
                'This placement was removed from its canvas, so it can no longer change or '
                'hold anything. Write to the canvas again with canvas.write(...) to put '
                'something on it.'
            )

    def _set_axis(self, axis: AxisName, value: Axis) -> None:
        self._require_attached()
        if isinstance(value, tuple):
            low, high = axis_limits(value, axis)
            is_time_dependent = any(not is_static_formula(bound) for bound in value)
            with self._canvas._lock:
                previous = self._limits.get(axis)
                if low is None and high is None:
                    self._limits.pop(axis, None)
                else:
                    self._limits[axis] = (low, high, is_time_dependent)
            try:
                self._enforce(axis)
            except ValueError:
                with self._canvas._lock:
                    if previous is None:
                        self._limits.pop(axis, None)
                    else:
                        self._limits[axis] = previous
                raise
            self._canvas._bindings_changed(self)
            return
        converted = axis_expression(value, axis)
        if isinstance(converted, (int, float)):
            check_size(converted, axis, value)
            with self._canvas._lock:
                self._bindings.pop(axis, None)
            self._assign_within_limits(axis, converted)
            return
        is_time_dependent = not is_static_formula(value)
        binding = (converted, is_time_dependent)
        with self._canvas._lock:
            previous = self._bindings.get(axis)
            self._bindings[axis] = binding

        def evaluate() -> None:
            try:
                self._assign_within_limits(axis, inspect_number(self._buffer, converted))
            except _core.RuntimeRequiredError:
                pass

        try:
            # The first value is worked out now, on the canvas's loop, so that a formula that
            # cannot be evaluated is reported to the caller instead of stopping the canvas.
            self._canvas._host.call(evaluate)
        except BaseException:
            # A formula that cannot be evaluated is not kept.
            with self._canvas._lock:
                if self._bindings.get(axis) is binding:
                    if previous is None:
                        del self._bindings[axis]
                    else:
                        self._bindings[axis] = previous
            raise
        self._canvas._bindings_changed(self)

    def _assign(self, axis: AxisName, value: int) -> None:
        if getattr(self._buffer, axis) != value:
            try:
                setattr(self._buffer, axis, value)
            except OverflowError:
                raise ValueError(
                    f'{axis} is {value}, which is too far from the canvas to be a cell. '
                    f'Pass a number of cells near the canvas, such as {axis}=0.'
                ) from None
            except ValueError:
                if axis not in ('width', 'height'):
                    raise
                raise ValueError(
                    f'{axis} must be a whole number of cells from 0 to {MOST_CELLS}, but the '
                    f'{axis} given works out to {value} cells on this canvas. Pass a size '
                    f"such as {axis}=4 or a share such as {axis}='50%', or leave {axis} out "
                    f'to use the size of the content.'
                ) from None
            driver = self._driver
            if (
                driver is not None
                and axis in ('width', 'height')
                and driver.is_size_followed
            ):
                driver.refresh()
            decorated = self._decorated
            if decorated is not None and axis in ('width', 'height'):
                self._refit_decoration(decorated)
            elif (
                axis in ('width', 'height')
                and self._is_box
                and self._appearance is not None
            ):
                # The cells a resize added take the colors of the box.
                self._apply_content_colors(self._appearance, self._buffer)
                self._canvas._request_frame()

    def _clamp(
        self, axis: AxisName, value: float, resolve: Callable[[Bound], float | None]
    ) -> float:
        """Hold a value inside the axis's range, or inside its area with ``edges='stop'``."""
        edge_range = self._edge_range(axis)
        if edge_range is not None:
            return min(max(value, edge_range[0]), edge_range[1])
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
        if not self._canvas._host.is_on_loop():
            raise _core.RuntimeRequiredError(
                'a bound that is a formula is evaluated by the canvas on its next frame'
            )
        return inspect_number(self._buffer, bound)

    def _assign_within_limits(self, axis: AxisName, value: float) -> None:
        """Assign a value now, held inside the range when the range is known now."""
        try:
            value = self._clamp(axis, value, self._resolve_offline)
        except _core.RuntimeRequiredError:
            pass
        self._assign(axis, _round_half_away(value))

    def _enforce(self, axis: AxisName) -> None:
        """Hold the current value of an axis inside its range."""
        self._assign_within_limits(axis, getattr(self._buffer, axis))

    def _apply_bindings(self, runtime: _core.Runtime) -> bool:
        """Evaluate every formula on the canvas's loop; return whether any follows time."""
        with self._canvas._lock:
            bindings = dict(self._bindings)
            limits = dict(self._limits)

        def resolve(bound: Bound) -> float | None:
            if isinstance(bound, (int, float)):
                return bound
            return bound.evaluate(EvaluationContext(buffer=self._buffer, runtime=runtime))

        axes: set[AxisName] = {*bindings, *limits}
        if self.edges == 'stop':
            axes.update(('x', 'y'))
        for axis in axes:
            if axis in bindings:
                expression, _ = bindings[axis]
                value = expression.evaluate(
                    EvaluationContext(buffer=self._buffer, runtime=runtime)
                )
                if value is None:
                    # Input or state the formula reads has no value at this moment, so the
                    # axis keeps what it had until the formula has one again.
                    continue
            else:
                value = getattr(self._buffer, axis)
            self._assign(axis, _round_half_away(self._clamp(axis, value, resolve)))
        self._refresh_wrap()
        return any(flag for _, flag in bindings.values()) or any(
            flag for _, _, flag in limits.values()
        )

    @property
    def x(self) -> int:
        """The column of the left edge, relative to the parent."""
        self._flush_look()
        return self._buffer.x

    @x.setter
    def x(self, value: Axis) -> None:
        """Set the column from an [`Axis`][xnano.types.Axis]; a range limits how far it may travel."""
        self._set_axis('x', value)

    @property
    def y(self) -> int:
        """The row of the top edge, relative to the parent."""
        self._flush_look()
        return self._buffer.y

    @y.setter
    def y(self, value: Axis) -> None:
        """Set the row from an [`Axis`][xnano.types.Axis]; a range limits how far it may travel."""
        self._set_axis('y', value)

    @property
    def width(self) -> int:
        """The width in cells."""
        self._flush_look()
        return self._buffer.width

    @width.setter
    def width(self, value: Axis) -> None:
        """Set the width from an [`Axis`][xnano.types.Axis]; a range limits the smallest and largest size."""
        self._set_axis('width', value)

    @property
    def height(self) -> int:
        """The height in cells."""
        self._flush_look()
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
        self._buffer.layer = check_layer(value)

    @property
    def is_visible(self) -> bool:
        """Whether the buffer is drawn."""
        return self._buffer.is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._buffer.is_visible = value

    @property
    def edges(self) -> EdgeBehavior:
        """
        What this content does at the edges of its area: ``'clip'``, ``'stop'`` or ``'wrap'``.

        Its area is what it is written on: the canvas, the placement around it, or its slot
        on a canvas with a ``'column'`` or ``'row'`` layout. Content written on the outer
        canvas inside the ``with`` block of a canvas created in it lives in that canvas's
        area, and follows that canvas's ``edges``. ``'clip'`` lets it move past an
        edge, where it is not drawn. ``'stop'`` holds it inside the area whenever it moves
        or is assigned a position, so a moved piece stops at the edge; a range given for
        ``x`` or ``y`` takes the place of the area's edges on that axis. ``'wrap'`` continues
        text on the next rows of the area, wrapped again whenever the area's width changes;
        on content that is not text it is the same as ``'clip'``. Assign ``None`` to follow
        what it is written on again: the setting of the placement around it, or the canvas's
        ``edges``.

        Raises:
            ValueError: The value is not ``'clip'``, ``'stop'``, ``'wrap'`` or ``None``.

        Examples:
            ```python
            import xnano

            with xnano.new(width=10, height=3) as canvas:
                ball = canvas.write('o', edges='stop')
                ball.right(50).down(50)
                assert (ball.x, ball.y) == (9, 2)
                note = canvas.write('one two three', edges='wrap')
                assert note.text == 'one two three'
                assert canvas.render().splitlines()[:2] == ['one two', 'three']
            ```
        """
        if self._edges is not None:
            return self._edges
        owner = self._edges_owner or self._parent_owner
        return owner.edges

    @edges.setter
    def edges(self, value: EdgeBehavior | None) -> None:
        self._require_attached()
        self._edges = None if value is None else check_edges(value)
        self._follow_edges()

    def _take_edges(self, edges: EdgeBehavior | None, content: object) -> None:
        """Keep the edges a write was given, and the text it wrote for wrapping."""
        self._edges = edges
        behavior = self.edges
        if behavior == 'clip':
            return
        if behavior == 'wrap' and self._is_text:
            if isinstance(content, str):
                self._wrapped_text = content
            elif isinstance(content, (list, tuple)):
                self._wrapped_text = '\n'.join(cast('Sequence[str]', content))
        self._follow_edges()

    def _follow_edges(self) -> None:
        """Apply the edges setting now, and look at the placement before each frame."""
        self._refresh_wrap()
        for axis in ('x', 'y'):
            self._enforce(cast('AxisName', axis))
        if self._needs_frames():
            self._canvas._bindings_changed(self)

    def _needs_frames(self) -> bool:
        """Whether a formula, a range or the edges setting is looked at before each frame."""
        return bool(self._bindings or self._limits) or self.edges in ('stop', 'wrap')

    def _edge_range(self, axis: AxisName) -> tuple[int, int] | None:
        """The positions ``'stop'`` holds ``x`` or ``y`` within, or ``None`` when it does not."""
        if axis not in ('x', 'y') or axis in self._limits or self.edges != 'stop':
            return None
        parent = self._parent_buffer
        if axis == 'x':
            room = parent.width - self._buffer.width
        else:
            room = parent.height - self._buffer.height
        return (0, max(0, room))

    def _refresh_wrap(self) -> None:
        """Wrap text at its area's width, or show the text as written once it no longer wraps."""
        if not self._is_text:
            return
        written = self._wrapped_text
        if self.edges != 'wrap':
            if written is not None:
                self._wrapped_text = None
                self._wrapped_width = None
                self._show_text(written)
            return
        if written is None:
            written = self.text
            self._wrapped_text = written
        width = self._parent_buffer.width
        if width == self._wrapped_width or width <= 0:
            return
        self._wrapped_width = width
        lines = _core.layout_text(written, width=width).lines
        self._show_text('\n'.join(line.text.rstrip() for line in lines))

    def move(self, x: int = 0, y: int = 0) -> Placement[DepsT, StateT]:
        """
        Move the placement by a number of cells along each axis.

        The move is held inside a range on the axis
        (``x=(0, 39)``), so a slider's thumb stops at the ends of its track. A position that
        is a formula keeps its formula and shifts it. Piping ``xnano.operations.Move`` onto
        the placement is also held inside its ranges.

        Args:
            x: Columns to move right; a negative number moves left.
            y: Rows to move down; a negative number moves up.

        Returns:
            The placement, so calls can chain.

        Raises:
            TypeError: An amount is not a whole number.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=3) as canvas:
                thumb = canvas.write('#', x=(0, 10), y=1)
                thumb.move(x=4, y=-1)
                assert (thumb.x, thumb.y) == (4, 0)
                thumb.right(99)
                assert thumb.x == 10
            ```
        """
        horizontal = check_cells(x, 'x')
        vertical = check_cells(y, 'y')
        self._require_attached()
        steps: tuple[tuple[AxisName, int], ...] = (('x', horizontal), ('y', vertical))
        for axis, step in steps:
            if step == 0:
                continue
            with self._canvas._lock:
                binding = self._bindings.get(axis)
            if binding is None:
                self._set_axis(axis, getattr(self._buffer, axis) + step)
                continue
            # A formula moves only as far as its range or edges let it, so moves past an
            # edge do not pile up and have to be undone before the opposite move shows.
            current = getattr(self._buffer, axis)
            try:
                target = self._clamp(axis, current + step, self._resolve_offline)
            except _core.RuntimeRequiredError:
                target = current + step
            self._set_axis(axis, binding[0] + _round_half_away(target - current))
        return self

    def up(self, count: int = 1) -> Placement[DepsT, StateT]:
        """
        Move the placement up by ``count`` rows; see [`move`][xnano.placement.Placement.move].

        Args:
            count: How many rows to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(y=-check_count(count, verb='up', opposite='down'))

    def down(self, count: int = 1) -> Placement[DepsT, StateT]:
        """
        Move the placement down by ``count`` rows; see [`move`][xnano.placement.Placement.move].

        Args:
            count: How many rows to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(y=check_count(count, verb='down', opposite='up'))

    def left(self, count: int = 1) -> Placement[DepsT, StateT]:
        """
        Move the placement left by ``count`` columns; see [`move`][xnano.placement.Placement.move].

        Args:
            count: How many columns to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(x=-check_count(count, verb='left', opposite='right'))

    def right(self, count: int = 1) -> Placement[DepsT, StateT]:
        """
        Move the placement right by ``count`` columns; see [`move`][xnano.placement.Placement.move].

        Args:
            count: How many columns to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(x=check_count(count, verb='right', opposite='left'))

    @property
    def fx(self) -> RenderableEffectProperties:
        """
        The visual effects of this placement, one method for each effect.

        ``placement.fx.fade_to(foreground='red')`` starts a fade on the placement at once, from
        a hook or from anywhere else, and ``placement.fx.clear()`` stops what was started here.
        See [`RenderableEffectProperties`][xnano.effects.RenderableEffectProperties].

        Examples:
            ```python
            import xnano
            from xnano.events import Event

            with xnano.new(width=20, height=1) as canvas:
                content = canvas.write('Press e')

                @canvas.hook(on='key')
                def flash(context: xnano.Context) -> None:
                    if context.keyboard.key == 'e':
                        content.fx.fade_to(foreground='red', duration_milliseconds=200)

                canvas.push(Event.key_press('e'))
                canvas.step()
                assert len(content.fx.active) == 1
            ```
        """
        return self._renderable_effects

    @property
    def region(self) -> Region[int]:
        """
        The cells of the content as a [`Region`][xnano.region.Region]: read and write
        ``placement.region[x, y]``.

        Around text with a border, padding or margin, the region is the area inside them. The
        same holds for a box from [`box`][xnano.box] whose look the placement draws: a box
        with a relative size, a box written with a ``width`` or a ``height``, and a box
        written with a look. A box written as it is, with no size and no look, is a snapshot
        whose border is part of its cells, so the region includes the border.

        Examples:
            ```python
            import xnano

            with xnano.new(width=10, height=3) as canvas:
                label = canvas.write('abc')
                label.region[0, 0] = xnano.Pixel('star')
                assert label.region[0, 0].character == '★'
            ```
        """
        buffer, inset = self._region_buffer()
        return Region(buffer, owner=cast('Placement[object, object]', self), inset=inset)

    def _region_buffer(self) -> tuple[_core.Buffer, tuple[int, int, int, int]]:
        """The buffer that ``region`` addresses, drawn up to date, and the cells left out of it."""
        self._flush_look()
        decorated = self._decorated
        if decorated is not None:
            return decorated.inner, (0, 0, 0, 0)
        return self._buffer, self._single_buffer_inset()

    def _region_cell_size(self) -> tuple[int, int]:
        """The width and height of ``region`` in cells, without making the region."""
        buffer, (left, top, right, bottom) = self._region_buffer()
        return (
            max(0, buffer.width - left - right),
            max(0, buffer.height - top - bottom),
        )

    def render(self, *, format: Literal['text', 'ansi'] = 'text') -> str:
        """
        Draw the placement, with its border, padding and nested placements, to a string.

        Args:
            format: ``'text'`` for the characters only, ``'ansi'`` with colors and styles.

        Examples:
            ```python
            import xnano

            with xnano.new(width=10, height=3) as canvas:
                card = canvas.write('hi', border='rounded')
                assert card.render().splitlines() == ['╭──╮', '│hi│', '╰──╯']
            ```
        """
        self._flush_look()
        return self._buffer.render(format=format)

    def _single_buffer_inset(self) -> tuple[int, int, int, int]:
        """The cells of border, padding and margin around the text of a one-buffer placement."""
        look = self._appearance
        if look is None or not self._is_text:
            return (0, 0, 0, 0)
        text = look.text.split('\n')
        insets = insets_for(look, max((len(line) for line in text), default=0), len(text))
        return insets.as_tuple()

    def refresh(self) -> None:
        """
        Draw a placement made from a component again, at the next frame.

        A component is evaluated once, and again only when it read something that changes. When
        something it does not track changes, such as a field of a class-based component or a
        value in ``context.deps``, call this to evaluate it again. A placement that was not made
        from a component has nothing to evaluate, so this does nothing.

        Examples:
            ```python
            import xnano

            @xnano.renderable
            def counter(context: xnano.Context) -> str:
                return str(context.deps['count'])

            dependencies = {'count': 0}
            with xnano.new(width=4, height=1, deps=dependencies) as canvas:
                placement = canvas.write(counter)
                dependencies['count'] = 7
                placement.refresh()
                canvas.step()
                assert canvas.render().strip() == '7'
            ```
        """
        driver = self._driver
        if driver is not None:
            driver.refresh()

    @property
    def text(self) -> str:
        """
        The text shown, line by line.

        Assign new text to change what a text placement says; the placement grows or shrinks
        to fit it, unless its size was set.
        """
        if self._wrapped_text is not None:
            return self._wrapped_text
        self._flush_look()
        if self._appearance is not None and self._is_text:
            return self._appearance.text
        return self._content.text

    @text.setter
    def text(self, value: str) -> None:
        self._require_attached()
        if not isinstance(value, str):
            raise TypeError(
                f'text must be a string, but got {value!r}. Pass text such as "hello", and '
                f'join lines with newlines.'
            )
        if self._wrapped_text is not None:
            self._wrapped_text = value
            self._wrapped_width = None
            self._refresh_wrap()
            return
        self._show_text(value)

    def _show_text(self, value: str) -> None:
        """Draw text in the placement, which grows or shrinks to fit it."""
        if self._appearance is not None:
            self._flush_look()
            self._appearance.text = value
            self._look_changed()
            self._flush_look()
            return
        lines = value.split('\n')
        self.width = max(len(line) for line in lines)
        self.height = len(lines)
        self._buffer.update(_core.Fill(' '), _core.Write(value))

    # -- the look ------------------------------------------------------------------------

    @property
    def style(self) -> _core.Style | None:
        """A ready-made style that the colors and modifiers are applied over."""
        look = self._appearance
        return None if look is None else look.style

    @style.setter
    def style(self, value: _core.Style | None) -> None:
        self._ensure_look().style = value
        self._look_changed()

    def _look_text(self) -> str:
        return self._content.text.rstrip('\n')

    def _look_canvas(self) -> Canvas[object, object] | None:
        return cast('Canvas[object, object]', self._canvas)

    def _look_size(self) -> tuple[int, int]:
        look = self._appearance
        if look is not None and self._is_text:
            text = look.text.split('\n')
            return (max((len(line) for line in text), default=0), len(text))
        content = self._content
        return (content.width, content.height)

    def _ensure_look(self) -> Appearance:
        self._require_attached()
        return super()._ensure_look()

    def _is_decoration_wanted(self, look: Appearance) -> bool:
        """Whether text needs the two-buffer layout: per-side settings or nested content."""
        if look.sides:
            return True
        has_children = self._has_nested or (
            self._decorated is None and bool(self._buffer.children)
        )
        return has_children and self._has_frame(look)

    def _has_frame(self, look: Appearance) -> bool:
        width, height = self._look_size()
        insets = insets_for(look, width, height)
        return bool(insets.horizontal or insets.vertical)

    def _redraw_look(self) -> None:
        """Draw the current look: one buffer for text with a uniform border, else two."""
        look = self._appearance
        if look is None or self._removed:
            return
        self._canvas._require_open()
        if self._is_text:
            if not self._is_decoration_wanted(look):
                if self._decorated is not None:
                    self._decorated.demote(copy_cells=False)
                    self._decorated = None
                self._show_appearance()
                return
        elif self._decorated is None and not self._has_frame(look):
            self._apply_content_colors(look, self._buffer)
            self._canvas._request_frame()
            return
        is_wrapped_now = False
        if self._decorated is None:
            if self._is_self_drawn():
                self._wrap_self_drawn_content()
                is_wrapped_now = True
            else:
                self._decorated = Decorated.promote(
                    self._buffer, copy_cells=not self._is_text
                )
        decorated = self._decorated
        assert decorated is not None
        if self._is_text:
            content = look.text_buffer()
            decorated.inner.width = content.width
            decorated.inner.height = content.height
            decorated.inner.update(
                _core.Fill(_core.Cell(' ')), _core.Paste(content, mode='replace')
            )
            insets = insets_for(look, content.width, content.height)
            self._buffer.width = content.width + insets.horizontal
            self._buffer.height = content.height + insets.vertical
        else:
            inner = decorated.inner
            if self._is_box:
                # The size of a box includes its border and padding, so they take room
                # inside it instead of growing it.
                insets = insets_for(look, self._buffer.width, self._buffer.height)
            else:
                insets = insets_for(look, inner.width, inner.height)
                previous = decorated.insets
                self._buffer.width = max(
                    1, self._buffer.width + insets.horizontal - previous.horizontal
                )
                self._buffer.height = max(
                    1, self._buffer.height + insets.vertical - previous.vertical
                )
                if is_wrapped_now:
                    # The box around a widget must fit in the parent, so the border is not
                    # cut off.
                    parent = self._parent_buffer
                    if 0 < parent.width < self._buffer.width:
                        self._buffer.width = max(insets.horizontal + 1, parent.width)
                    if 0 < parent.height < self._buffer.height:
                        self._buffer.height = max(insets.vertical + 1, parent.height)
            decorated.insets = insets
            decorated.fit_inner()
            self._apply_content_colors(look, inner)
        decorated.repaint(look, insets)
        if (
            not self._is_text
            and not insets.horizontal
            and not insets.vertical
            and not self._is_self_drawn()
        ):
            decorated.demote(copy_cells=True)
            self._decorated = None
        self._canvas._request_frame()

    def _is_self_drawn(self) -> bool:
        """Whether the content is a widget or an image, which draws its own cells."""
        content = self._content
        return isinstance(content, _core.Widget) or id(content) in self._canvas._images

    def _wrap_self_drawn_content(self) -> None:
        """
        Put a widget or an image inside a new outer buffer that takes its place.

        The content keeps drawing its own cells as the child of the outer buffer, which
        carries the position, the layer, the visibility and the hooks of the placement.
        """
        content = self._buffer
        parent = self._parent_buffer
        siblings = list(parent.children)
        later = siblings[siblings.index(content) + 1 :] if content in siblings else []
        outer = _core.Buffer(width=content.width, height=content.height)
        outer.x = content.x
        outer.y = content.y
        outer.layer = content.layer
        outer.is_visible = content.is_visible
        for buffer in (content, *later):
            parent.detach(buffer)
        content.x = 0
        content.y = 0
        content.layer = 0
        content.is_visible = True
        outer.attach(content, mode='transparent')
        parent.attach(outer, mode='transparent')
        for buffer in later:
            parent.attach(buffer, mode='transparent')
        self._buffer = outer
        self._decorated = Decorated(outer, content)
        for handle in list(self._registrations):
            handle._move_to_buffer(outer)

    def _refit_decoration(self, decorated: Decorated) -> None:
        """The outer size changed: make the content follow and draw the decoration again."""
        look = self._appearance
        if look is None:
            return
        if self._is_box:
            decorated.insets = insets_for(look, self._buffer.width, self._buffer.height)
        if not self._is_text:
            decorated.fit_inner()
            if self._is_box:
                self._apply_content_colors(look, decorated.inner)
        decorated.repaint(look, decorated.insets)

    def _show_appearance(self) -> None:
        """Draw text with a uniform look into the one buffer, resizing the placement to fit."""
        appearance = self._appearance
        if appearance is None:
            return
        self._canvas._require_open()
        drawn = appearance.snapshot()
        self.width = drawn.width
        self.height = drawn.height
        self._buffer.update(_core.Fill(' '), _core.Paste(drawn, mode='replace'))
        self._canvas._request_frame()

    @refuse_unknown_keywords
    def write(
        self,
        content: Content | Canvas[WrittenDepsT, WrittenStateT] | None = None,
        /,
        *,
        x: Axis | None = None,
        y: Axis | None = None,
        width: Axis | None = None,
        height: Axis | None = None,
        layer: int = 0,
        lock: bool = False,
        edges: EdgeBehavior | None = None,
        effects: Sequence[RenderableEffectSpecification] = (),
        style: _core.Style | None = None,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        bold: bool = False,
        dim: bool = False,
        italic: bool = False,
        underline: bool = False,
        blink: bool = False,
        reverse: bool = False,
        hidden: bool = False,
        crossed_out: bool = False,
        title: str | None = None,
        border: _core.BorderKind | bool | None = None,
        border_style: _core.Style | None = None,
        padding: Spacing | None = None,
        margin: Spacing | None = None,
    ) -> Placement[DepsT, StateT]:
        """
        Add a child placement inside this placement.

        A child placement's ``x``, ``y``, ``width`` and ``height`` are measured relative to
        this placement's buffer, so ``track.write('█', x=(0, track.width - 1), y=0)`` moves
        inside ``track``. To change this placement with an operation, a style or an effect, use
        [`update`][xnano.placement.Placement.update].

        A box from [`box`][xnano.box] with a percentage, formula or state reference size is
        measured against this placement and drawn again when it changes size; see
        [`Canvas.write`][xnano.canvas.Canvas.write] for how the look given here applies over
        the look of the box.

        Args:
            content: Child content to place inside this buffer.
            x: Column of the child's left edge, relative to this placement.
            y: Row of the child's top edge, relative to this placement.
            width: Width of the child in cells.
            height: Height of the child in cells.
            layer: Layer ordering among siblings.
            lock: Lock dynamic axes to their initial values.
            edges: What the content does at the edges of its area: ``'clip'``, ``'stop'`` or
                ``'wrap'``; see [`Placement.edges`][xnano.placement.Placement.edges]. Left
                out, it follows what it is written on.
            effects: Effects to start on the child, as dictionaries with a ``kind`` key.
            style: Ready-made [`Style`][xnano.styles.Style] for text.
            foreground: Text foreground color.
            background: Text background color.
            bold: Whether text is bold.
            dim: Whether text is dimmed.
            italic: Whether text is italic.
            underline: Whether text is underlined.
            blink: Whether text blinks.
            reverse: Whether foreground and background are swapped.
            hidden: Whether text is hidden.
            crossed_out: Whether text is struck through.
            title: Title for a box around text.
            border: The kind of border for a box around the content, a
                [`BorderKind`][xnano.types.BorderKind] such as ``'plain'``, ``'rounded'``,
                ``'double'`` or ``'thick'``; ``True`` for ``'plain'`` and ``False`` for none.
            border_style: Style for the box's border.
            padding: Space between the border and the text; see
                [`Canvas.write`][xnano.canvas.Canvas.write].
            margin: Space outside the box, in the same forms.
        """
        self._require_attached()
        if isinstance(content, Region):
            content._require_drawable('placement.write()')
            width, height = content._written_size(width, height)
        if edges is not None:
            edges = check_edges(edges)
        look = self._appearance
        if look is not None and self._decorated is None and self._has_frame(look):
            self._has_nested = True
            self._look_changed()
            self._flush_look()
        placement = self._canvas._place_on(
            self._content,
            content,
            parent_owner=cast('Placement[object, object]', self),
            x=x,
            y=y,
            width=width,
            height=height,
            layer=layer,
            lock=lock,
            style=style,
            foreground=foreground,
            background=background,
            bold=bold,
            dim=dim,
            italic=italic,
            underline=underline,
            blink=blink,
            reverse=reverse,
            hidden=hidden,
            crossed_out=crossed_out,
            title=title,
            border=border,
            border_style=border_style,
            padding=padding,
            margin=margin,
        )
        if effects:
            apply_effects(cast('Placement[object, object]', placement), effects)
        placement._take_edges(edges, content)
        return placement

    def update(
        self, *operations: _core.Operation | _core.Style
    ) -> Placement[DepsT, StateT]:
        """
        Change this placement's content with operations, styles or effects.

        Args:
            operations: What to apply, in order: an operation, a contextual operation, a style,
                or an effect such as ``Effect.dissolve(duration_milliseconds=500)``.

        Examples:
            ```python
            import xnano
            from xnano.operations import Effect

            with xnano.new(width=20, height=3) as canvas:
                title = canvas.write('Welcome')
                title.update(Effect.dissolve(duration_milliseconds=500))
            ```
        """
        self._require_attached()
        for item in operations:
            if isinstance(item, ContextualOperation):
                cast('ContextualOperation[DepsT, StateT]', item).apply_to(self)
            elif isinstance(item, DynamicOperation):
                item.apply_to(cast('Placement[object, object]', self))
            elif isinstance(item, _core.Style):
                self._buffer.update(_core.ApplyStyle(item))
            else:
                self._buffer.update(item)
                if isinstance(item, (_core.Move, _core.Place)):
                    for axis in ('x', 'y'):
                        if axis in self._limits:
                            self._enforce(axis)
        return self

    def __or__(
        self, operation: _core.Operation | _core.Style
    ) -> Placement[DepsT, StateT]:
        """Apply ``operation`` to this placement and return ``self``."""
        return self.update(operation)

    def __ior__(
        self, operation: _core.Operation | _core.Style
    ) -> Placement[DepsT, StateT]:
        """Apply ``operation`` to this placement in place and return ``self``."""
        return self.update(operation)

    def remove(self) -> None:
        """Take the buffer off the canvas. Removing twice is harmless."""
        if self._removed:
            return
        self._removed = True
        # A look that was waiting to be drawn is dropped with the placement.
        self._look_is_dirty = False
        canvas = self._canvas
        if not canvas._is_closed:
            canvas._look_was_drawn(self)
        with canvas._lock:
            nested = [
                other
                for other in canvas._placements
                if other._parent_owner is self
                or getattr(other._parent_owner, '_parent_placement', None) is self
            ]
        for other in nested:
            other.remove()
        follow = canvas._cursor_follow
        if (
            follow is not None
            and not canvas._is_closed
            and any(follow[0] is buffer for buffer in (self._buffer, self._content))
        ):
            # A cursor that followed this placement has nowhere to be once it is gone.
            canvas._cursor_view.position = None
        driver = self._driver
        if driver is not None:
            self._driver = None
            driver.close()
        self._cancel_hooks()
        self._renderable_effects.clear()
        namespace = self._state_namespace
        if namespace is not None:
            self._state_namespace = None
            namespace._remove()
        with self._canvas._lock:
            self._bindings.clear()
            self._limits.clear()
        try:
            self._parent_buffer.detach(self._buffer)
        except ValueError:
            pass
        self._canvas._release(self)
        with canvas._lock:
            children = [
                child
                for child in canvas._children
                if child._parent_placement is self and not child._is_closed
            ]
        for child in children:
            # A canvas written into this placement is closed with it.
            child.close()

    def __repr__(self) -> str:
        state = 'removed' if self._removed else f'x={self.x}, y={self.y}'
        return f'Placement({state}, width={self.width}, height={self.height})'


def _round_half_away(value: float) -> int:
    """Round to the nearest whole number, halves away from zero."""
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)
