"""
xnano.placement

A buffer placed on a canvas, with a position and size that are formulas.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core
from xnano_core import EvaluationContext

if TYPE_CHECKING:
    from xnano.canvas import Canvas

from xnano._appearance import Appearance, Spacing
from xnano._axes import (
    axis_expression,
    axis_limits,
    check_cells,
    check_count,
    inspect_number,
)
from xnano._customize import Customization, apply_effects
from xnano._decoration import Decorated, insets_for
from xnano._hooks import _Hooked
from xnano._values import (
    Axis,
    AxisName,
    Bound,
    ColorValue,
    Content,
    DepsT,
    NumericExpression,
    StateT,
)
from xnano.appearance import _Looked
from xnano.expressions import (
    Parent,
    ParentExpressionScope,
    Root,
    RootExpressionScope,
)
from xnano.operations import (
    ContextualOperation,
)
from xnano.region import Region
from xnano.scene import Scene


class Placement(_Hooked[DepsT, StateT], _Looked):
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
        self._appearance: Appearance | None = None
        self._decorated: Decorated | None = None
        self._has_nested = False

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
        bounds = self._buffer._absolute_bounds
        return _core.Point(point.x - bounds.x, point.y - bounds.y)

    @property
    def canvas(self) -> Canvas[DepsT, StateT]:
        """The canvas the buffer is placed on."""
        return self._canvas

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

    def _set_axis(self, axis: AxisName, value: Axis) -> None:
        self._canvas._require_open()
        if isinstance(value, tuple):
            low, high = axis_limits(value, axis)
            is_time_dependent = any(
                isinstance(bound, _core.NumericValue) for bound in value
            )
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
            with self._canvas._lock:
                self._bindings.pop(axis, None)
            self._assign_within_limits(axis, converted)
            return
        is_time_dependent = isinstance(value, _core.NumericValue)
        with self._canvas._lock:
            self._bindings[axis] = (converted, is_time_dependent)

        def evaluate() -> None:
            try:
                self._assign_within_limits(axis, inspect_number(self._buffer, converted))
            except _core.RuntimeRequiredError:
                pass

        if self._canvas._host.is_on_loop():
            evaluate()
        else:
            self._canvas._host.post(evaluate)
        self._canvas._bindings_changed(self)

    def _assign(self, axis: AxisName, value: int) -> None:
        if getattr(self._buffer, axis) != value:
            setattr(self._buffer, axis, value)
            decorated = self._decorated
            if decorated is not None and axis in ('width', 'height'):
                self._refit_decoration(decorated)

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
        self._buffer.layer = value

    @property
    def is_visible(self) -> bool:
        """Whether the buffer is drawn."""
        return self._buffer.is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._buffer.is_visible = value

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
        self._canvas._require_open()
        steps: tuple[tuple[AxisName, int], ...] = (('x', horizontal), ('y', vertical))
        for axis, step in steps:
            if step == 0:
                continue
            with self._canvas._lock:
                binding = self._bindings.get(axis)
            if binding is None:
                self._set_axis(axis, getattr(self._buffer, axis) + step)
            else:
                self._set_axis(axis, binding[0] + step)
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
        return self.move(y=-check_count(count))

    def down(self, count: int = 1) -> Placement[DepsT, StateT]:
        """
        Move the placement down by ``count`` rows; see [`move`][xnano.placement.Placement.move].

        Args:
            count: How many rows to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(y=check_count(count))

    def left(self, count: int = 1) -> Placement[DepsT, StateT]:
        """
        Move the placement left by ``count`` columns; see [`move`][xnano.placement.Placement.move].

        Args:
            count: How many columns to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(x=-check_count(count))

    def right(self, count: int = 1) -> Placement[DepsT, StateT]:
        """
        Move the placement right by ``count`` columns; see [`move`][xnano.placement.Placement.move].

        Args:
            count: How many columns to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(x=check_count(count))

    @property
    def region(self) -> Region:
        """
        The cells of the content as a [`Region`][xnano.region.Region]: read and write
        ``placement.region[x, y]``.

        Around text with a border, padding or margin, the region is the area inside them.

        Examples:
            ```python
            import xnano

            with xnano.new(width=10, height=3) as canvas:
                label = canvas.write('abc')
                label.region[0, 0] = xnano.Pixel('star')
                assert label.region[0, 0].character == '★'
            ```
        """
        self._flush_look()
        decorated = self._decorated
        if decorated is not None:
            return Region(decorated.inner, owner=cast('Placement[object, object]', self))
        inset = self._single_buffer_inset()
        return Region(
            self._buffer, owner=cast('Placement[object, object]', self), inset=inset
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
            cast('Placement[object, object]', self), world_width, world_height, background
        )

    @property
    def text(self) -> str:
        """
        The text shown, line by line.

        Assign new text to change what a text placement says; the placement grows or shrinks
        to fit it, unless its size was set.
        """
        self._flush_look()
        if self._appearance is not None and self._is_text:
            return self._appearance.text
        return self._content.text

    @text.setter
    def text(self, value: str) -> None:
        self._canvas._require_open()
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

    @property
    def is_bold(self) -> bool:
        """Whether the text is bold."""
        look = self._appearance
        return False if look is None else look.is_bold

    @is_bold.setter
    def is_bold(self, value: bool) -> None:
        self._ensure_look().is_bold = value
        self._look_changed()

    @property
    def is_dim(self) -> bool:
        """Whether the text is dimmed."""
        look = self._appearance
        return False if look is None else look.is_dim

    @is_dim.setter
    def is_dim(self, value: bool) -> None:
        self._ensure_look().is_dim = value
        self._look_changed()

    @property
    def is_italic(self) -> bool:
        """Whether the text is italic."""
        look = self._appearance
        return False if look is None else look.is_italic

    @is_italic.setter
    def is_italic(self, value: bool) -> None:
        self._ensure_look().is_italic = value
        self._look_changed()

    @property
    def is_underlined(self) -> bool:
        """Whether the text is underlined."""
        look = self._appearance
        return False if look is None else look.is_underlined

    @is_underlined.setter
    def is_underlined(self, value: bool) -> None:
        self._ensure_look().is_underlined = value
        self._look_changed()

    @property
    def is_blinking(self) -> bool:
        """Whether the text blinks."""
        look = self._appearance
        return False if look is None else look.is_blinking

    @is_blinking.setter
    def is_blinking(self, value: bool) -> None:
        self._ensure_look().is_blinking = value
        self._look_changed()

    @property
    def is_reversed(self) -> bool:
        """Whether foreground and background are swapped."""
        look = self._appearance
        return False if look is None else look.is_reversed

    @is_reversed.setter
    def is_reversed(self, value: bool) -> None:
        self._ensure_look().is_reversed = value
        self._look_changed()

    @property
    def is_hidden(self) -> bool:
        """Whether the text is hidden."""
        look = self._appearance
        return False if look is None else look.is_hidden

    @is_hidden.setter
    def is_hidden(self, value: bool) -> None:
        self._ensure_look().is_hidden = value
        self._look_changed()

    @property
    def is_crossed_out(self) -> bool:
        """Whether the text is struck through."""
        look = self._appearance
        return False if look is None else look.is_crossed_out

    @is_crossed_out.setter
    def is_crossed_out(self, value: bool) -> None:
        self._ensure_look().is_crossed_out = value
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
        self._canvas._require_open()
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
        if look is None:
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
            insets = insets_for(look, inner.width, inner.height)
            previous = decorated.insets
            self._buffer.width = max(
                1, self._buffer.width + insets.horizontal - previous.horizontal
            )
            self._buffer.height = max(
                1, self._buffer.height + insets.vertical - previous.vertical
            )
            if is_wrapped_now:
                # The box around a widget must fit in the parent, so the border is not cut off.
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
        if not self._is_text:
            decorated.fit_inner()
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

    def write(
        self,
        content: Content
        | Canvas[object, object]
        | _core.Operation
        | _core.Style
        | None = None,
        /,
        *,
        x: Axis | None = None,
        y: Axis | None = None,
        width: Axis | None = None,
        height: Axis | None = None,
        layer: int = 0,
        lock: bool = False,
        effects: Sequence[Mapping[str, object]] = (),
        style: _core.Style | None = None,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        is_bold: bool = False,
        is_dim: bool = False,
        is_italic: bool = False,
        is_underlined: bool = False,
        is_blinking: bool = False,
        is_reversed: bool = False,
        is_hidden: bool = False,
        is_crossed_out: bool = False,
        title: str | None = None,
        border: _core.BorderKind | None = None,
        border_style: _core.Style | None = None,
        padding: Spacing | None = None,
        margin: Spacing | None = None,
    ) -> Placement[DepsT, StateT]:
        """
        Add a child placement inside this placement, or apply an operation or style to it.

        A child placement's ``x``, ``y``, ``width`` and ``height`` are measured relative to
        this placement's buffer, so ``track.write('█', x=(0, track.width - 1), y=0)`` moves
        inside ``track``. When ``content`` is an [`Operation`][xnano.operations.Operation] or
        [`Style`][xnano.styles.Style] and no placement arguments are given, it is applied to
        this placement and ``self`` is returned.

        Args:
            content: Child content to place inside this buffer, or an operation/style to apply.
            x: Column of the child's left edge, relative to this placement.
            y: Row of the child's top edge, relative to this placement.
            width: Width of the child in cells.
            height: Height of the child in cells.
            layer: Layer ordering among siblings.
            lock: Lock dynamic axes to their initial values.
            effects: Effects to start on the child, as dictionaries with a ``kind`` key.
            style: Ready-made [`Style`][xnano.styles.Style] for text.
            foreground: Text foreground color.
            background: Text background color.
            is_bold: Whether text is bold.
            is_dim: Whether text is dimmed.
            is_italic: Whether text is italic.
            is_underlined: Whether text is underlined.
            is_blinking: Whether text blinks.
            is_reversed: Whether foreground and background are swapped.
            is_hidden: Whether text is hidden.
            is_crossed_out: Whether text is struck through.
            title: Title for a box around text.
            border: Border kind for a box around text.
            border_style: Style for the box's border.
            padding: Space between the border and the text; see
                [`Canvas.write`][xnano.canvas.Canvas.write].
            margin: Space outside the box, in the same forms.
        """
        self._canvas._require_open()
        has_placement_options = any(
            value is not None
            for value in (
                x,
                y,
                width,
                height,
                style,
                foreground,
                background,
                title,
                border,
                border_style,
                padding,
                margin,
            )
        ) or any(
            (
                layer != 0,
                lock,
                bool(effects),
                is_bold,
                is_dim,
                is_italic,
                is_underlined,
                is_blinking,
                is_reversed,
                is_hidden,
                is_crossed_out,
            )
        )
        if (
            isinstance(content, (_core.Operation, _core.Style))
            and not has_placement_options
        ):
            self.update(content)
            return self
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
            is_bold=is_bold,
            is_dim=is_dim,
            is_italic=is_italic,
            is_underlined=is_underlined,
            is_blinking=is_blinking,
            is_reversed=is_reversed,
            is_hidden=is_hidden,
            is_crossed_out=is_crossed_out,
            title=title,
            border=border,
            border_style=border_style,
            padding=padding,
            margin=margin,
        )
        if effects:
            apply_effects(cast('Placement[object, object]', placement), effects)
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
            from xnano.effects import Effect

            with xnano.new(width=20, height=3) as canvas:
                title = canvas.write('Welcome')
                title.update(Effect.dissolve(duration_milliseconds=500))
            ```
        """
        self._canvas._require_open()
        for item in operations:
            if isinstance(item, ContextualOperation):
                cast('ContextualOperation[DepsT, StateT]', item).apply_to(self)
            elif isinstance(item, Customization):
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
        self._cancel_hooks()
        with self._canvas._lock:
            self._bindings.clear()
            self._limits.clear()
        try:
            self._parent_buffer.detach(self._buffer)
        except ValueError:
            pass
        self._canvas._release(self)

    def __repr__(self) -> str:
        state = 'removed' if self._removed else f'x={self.x}, y={self.y}'
        return f'Placement({state}, width={self.width}, height={self.height})'


def _round_half_away(value: float) -> int:
    """Round to the nearest whole number, halves away from zero."""
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)
