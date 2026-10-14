"""
xnano.placement

A buffer placed on a terminal, with a position and size that are formulas.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, cast, overload

import xnano_core as _core
from xnano_core import EvaluationContext

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from xnano.terminal import Terminal

from xnano._axes import axis_expression, axis_limits, inspect_number
from xnano._customize import (
    BackgroundArguments,
    BitCrushAudioArguments,
    BlockArguments,
    BorderArguments,
    CoalesceEffectArguments,
    Customization,
    CustomizationKind,
    DarkenEffectArguments,
    DelayAudioArguments,
    DissolveEffectArguments,
    DistortionAudioArguments,
    EvolveEffectArguments,
    EvolveFromEffectArguments,
    EvolveIntoEffectArguments,
    ExpandEffectArguments,
    ExplodeEffectArguments,
    FadeFromEffectArguments,
    FadeToEffectArguments,
    FillArguments,
    ForegroundArguments,
    FuzzArguments,
    GlitchEffectArguments,
    HighPassAudioArguments,
    HslShiftEffectArguments,
    LayoutArguments,
    LightenEffectArguments,
    LowPassAudioArguments,
    MarginArguments,
    PaddingArguments,
    PaintEffectArguments,
    PixelsArguments,
    RasterArguments,
    ReverbAudioArguments,
    SaturateEffectArguments,
    SleepEffectArguments,
    SlideInEffectArguments,
    SlideOutEffectArguments,
    StretchEffectArguments,
    StyleArguments,
    SweepInEffectArguments,
    SweepOutEffectArguments,
    TremoloAudioArguments,
    WriteArguments,
)
from xnano._customize import (
    fx as _customize_operation,
)
from xnano._hooks import _Hooked
from xnano._values import (
    Axis,
    AxisName,
    Bound,
    ColorValue,
    Content,
    NumericExpression,
    PixelEncoding,
    StateT,
)
from xnano.expressions import (
    Parent,
    ParentExpressionScope,
    Root,
    RootExpressionScope,
)
from xnano.operations import (
    ContextualOperation,
)
from xnano.operations import (
    draggable as _draggable_operation,
)
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
    by a mouse hook or [`draggable`][xnano.operations.draggable], is held inside the track.
    For ``width`` and ``height`` it is the smallest and largest size.

    Percentages and ranges only change when something about the terminal does, so they
    cost nothing while it is still. An expression is assumed to change with time, so a
    terminal with one keeps drawing every frame; use a percentage for a layout that only
    follows the size of the terminal.

    Get one from [`Terminal.write`][xnano.terminal.Terminal.write] or nest a child placement inside
    another with [`Placement.write`][xnano.placement.Placement.write].

    Attributes:
        buffer: The buffer that is placed.
        terminal: The terminal the buffer is placed on.
        parent: Symbolic expressions for the parent container's ``width``, ``height`` and ``size``.
        root: Symbolic expressions for the root terminal's ``width``, ``height``, ``size`` and ``time``.
        time: Symbolic expression for elapsed seconds on the terminal clock.
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

        with xnano.open(offscreen=True, width=20, height=3) as terminal:
            label = terminal.write('hi')
            label.x = (label.parent.width - label.width) // 2
            assert label.x == 9

            thumb = terminal.write('#', x=(2, 10))
            thumb.x = 40
            assert thumb.x == 10
            thumb.x = 0
            assert thumb.x == 2
        ```
    """

    def __init__(
        self,
        terminal: Terminal[StateT],
        buffer: _core.Buffer,
        parent_buffer: _core.Buffer | None = None,
    ) -> None:
        """
        Place a buffer on a terminal. Get one from ``terminal.write`` instead of calling this.

        Args:
            terminal: The terminal the buffer is placed on.
            buffer: The buffer that is placed.
            parent_buffer: The parent buffer ``buffer`` is attached to (defaults to ``terminal.root``).
        """
        super().__init__()
        self._terminal = terminal
        self._buffer = buffer
        self._parent_buffer: _core.Buffer = (
            terminal._root if parent_buffer is None else parent_buffer
        )
        self._bindings: dict[AxisName, tuple[NumericExpression, bool]] = {}
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

    @property
    def parent(self) -> ParentExpressionScope:
        """Symbolic expressions for the parent container's ``width``, ``height`` and ``size``."""
        return Parent

    @property
    def root(self) -> RootExpressionScope:
        """Symbolic expressions for the root terminal's ``width``, ``height``, ``size`` and ``time``."""
        return Root

    @property
    def time(self) -> _core.NumericValue:
        """Symbolic expression for elapsed seconds on the terminal clock."""
        return _core.TimeElapsed

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
            pass
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
        """The column of the left edge, relative to the parent."""
        return self._buffer.x

    @x.setter
    def x(self, value: Axis) -> None:
        """Set the column from an [`Axis`][xnano.types.Axis]; a range limits how far it may travel."""
        self._set_axis('x', value)

    @property
    def y(self) -> int:
        """The row of the top edge, relative to the parent."""
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
        Return a [`Pixels`][xnano.pixels.Pixels] view of the placed buffer.

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

    def write(
        self,
        content: Content | _core.Operation | _core.Style,
        *,
        x: Axis | None = None,
        y: Axis | None = None,
        width: Axis | None = None,
        height: Axis | None = None,
        layer: int = 0,
        lock: bool = False,
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
    ) -> Placement[StateT]:
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
        """
        self._terminal._require_open()
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
            )
        ) or any(
            (
                layer != 0,
                lock,
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
        return self._terminal._place_on(
            self._buffer,
            cast('Content', content),
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
        )

    def update(self, *operations: _core.Operation | _core.Style) -> Placement[StateT]:
        """
        Change this placement's content with operations, styles or effects.

        Args:
            operations: What to apply, in order: an operation, a contextual operation, a style,
                or an effect such as ``Effect.dissolve(duration_milliseconds=500)``.

        Examples:
            ```python
            import xnano
            from xnano.effects import Effect

            with xnano.open(offscreen=True, width=20, height=3) as terminal:
                title = terminal.write('Welcome')
                title.update(Effect.dissolve(duration_milliseconds=500))
            ```
        """
        self._terminal._require_open()
        for item in operations:
            if isinstance(item, ContextualOperation):
                cast('ContextualOperation[StateT]', item).apply_to(self)
            elif isinstance(item, Customization):
                item.apply_to(cast('Placement[object]', self))
            elif isinstance(item, _core.Style):
                self._buffer.update(_core.ApplyStyle(item))
            else:
                self._buffer.update(item)
        return self

    def __or__(self, operation: _core.Operation | _core.Style) -> Placement[StateT]:
        """Apply ``operation`` to this placement and return ``self``."""
        return self.update(operation)

    def __ior__(self, operation: _core.Operation | _core.Style) -> Placement[StateT]:
        """Apply ``operation`` to this placement in place and return ``self``."""
        return self.update(operation)

    @overload
    def fx(
        self, kind: Literal['style'], /, **parameters: Unpack[StyleArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['border'], /, **parameters: Unpack[BorderArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['block'], /, **parameters: Unpack[BlockArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['padding'], /, **parameters: Unpack[PaddingArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['margin'], /, **parameters: Unpack[MarginArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['fill'], /, **parameters: Unpack[FillArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['foreground'], /, **parameters: Unpack[ForegroundArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['background'], /, **parameters: Unpack[BackgroundArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['write'], /, **parameters: Unpack[WriteArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['layout'], /, **parameters: Unpack[LayoutArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['fuzz'], /, **parameters: Unpack[FuzzArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['pixels'], /, **parameters: Unpack[PixelsArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self, kind: Literal['raster'], /, **parameters: Unpack[RasterArguments]
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.fade_to'],
        /,
        **parameters: Unpack[FadeToEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.fade_from'],
        /,
        **parameters: Unpack[FadeFromEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.paint'],
        /,
        **parameters: Unpack[PaintEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.saturate'],
        /,
        **parameters: Unpack[SaturateEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.lighten'],
        /,
        **parameters: Unpack[LightenEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.darken'],
        /,
        **parameters: Unpack[DarkenEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.sweep_in'],
        /,
        **parameters: Unpack[SweepInEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.sweep_out'],
        /,
        **parameters: Unpack[SweepOutEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.slide_in'],
        /,
        **parameters: Unpack[SlideInEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.slide_out'],
        /,
        **parameters: Unpack[SlideOutEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.hsl_shift'],
        /,
        **parameters: Unpack[HslShiftEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.dissolve'],
        /,
        **parameters: Unpack[DissolveEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.coalesce'],
        /,
        **parameters: Unpack[CoalesceEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.glitch'],
        /,
        **parameters: Unpack[GlitchEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.sleep'],
        /,
        **parameters: Unpack[SleepEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.evolve'],
        /,
        **parameters: Unpack[EvolveEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.evolve_into'],
        /,
        **parameters: Unpack[EvolveIntoEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.evolve_from'],
        /,
        **parameters: Unpack[EvolveFromEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.expand'],
        /,
        **parameters: Unpack[ExpandEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.stretch'],
        /,
        **parameters: Unpack[StretchEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.explode'],
        /,
        **parameters: Unpack[ExplodeEffectArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.bit_crush'],
        /,
        **parameters: Unpack[BitCrushAudioArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.distortion'],
        /,
        **parameters: Unpack[DistortionAudioArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.low_pass'],
        /,
        **parameters: Unpack[LowPassAudioArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.high_pass'],
        /,
        **parameters: Unpack[HighPassAudioArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.delay'],
        /,
        **parameters: Unpack[DelayAudioArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.reverb'],
        /,
        **parameters: Unpack[ReverbAudioArguments],
    ) -> Placement[StateT]: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.tremolo'],
        /,
        **parameters: Unpack[TremoloAudioArguments],
    ) -> Placement[StateT]: ...
    def fx(self, kind: CustomizationKind, /, **parameters: object) -> Placement[StateT]:
        """
        Apply a typed customization (``'style'``, ``'border'``, ``'block'``, ``'padding'``,
        ``'margin'``, ``'pixels'``, ``'effect.<name>'``, etc.) to this placement and return ``self``.

        Args:
            kind: Which customization to apply.
            parameters: Keyword arguments for the chosen customization kind.
        """
        compiled = cast('Callable[..., Customization]', _customize_operation)(
            kind, **parameters
        )
        compiled.apply_to(cast('Placement[object]', self))
        return self

    def make_draggable(self, axis: Literal['x', 'y'] = 'x') -> Placement[StateT]:
        """
        Let the pointer move this placement along one axis by dragging it.

        Pressing the placement grabs the pointer, so the drag keeps going when the pointer
        leaves it. The placement follows the pointer's position inside its parent. Give the
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
                thumb = terminal.write('#', x=(0, 10), y=0)
                thumb.make_draggable()
                assert thumb.x == 0
            ```
        """
        if axis not in ('x', 'y'):
            raise ValueError(
                f'{axis!r} is not an axis make_draggable can move. Use "x" or "y".'
            )
        _draggable_operation(axis).apply_to(cast('Placement[object]', self))
        return self

    def remove(self) -> None:
        """Take the buffer off the terminal. Removing twice is harmless."""
        if self._removed:
            return
        self._removed = True
        self._cancel_hooks()
        with self._terminal._lock:
            self._bindings.clear()
            self._limits.clear()
        try:
            self._parent_buffer.detach(self._buffer)
        except ValueError:
            pass
        self._terminal._release(self)

    def __repr__(self) -> str:
        state = 'removed' if self._removed else f'x={self.x}, y={self.y}'
        return f'Placement({state}, width={self.width}, height={self.height})'


def _round_half_away(value: float) -> int:
    """Round to the nearest whole number, halves away from zero."""
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)
