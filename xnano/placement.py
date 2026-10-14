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

    from xnano._customize import (
        BitCrushAudioCustomization,
        CoalesceEffectCustomization,
        DarkenEffectCustomization,
        DelayAudioCustomization,
        DissolveEffectCustomization,
        DistortionAudioCustomization,
        EvolveEffectCustomization,
        EvolveFromEffectCustomization,
        EvolveIntoEffectCustomization,
        ExpandEffectCustomization,
        ExplodeEffectCustomization,
        FadeFromEffectCustomization,
        FadeToEffectCustomization,
        FillCustomization,
        FuzzCustomization,
        GlitchEffectCustomization,
        HighPassAudioCustomization,
        HslShiftEffectCustomization,
        LayoutCustomization,
        LightenEffectCustomization,
        LowPassAudioCustomization,
        PaintEffectCustomization,
        PixelsCustomization,
        RasterCustomization,
        ReverbAudioCustomization,
        SaturateEffectCustomization,
        SleepEffectCustomization,
        SlideInEffectCustomization,
        SlideOutEffectCustomization,
        StretchEffectCustomization,
        SweepInEffectCustomization,
        SweepOutEffectCustomization,
        TremoloAudioCustomization,
        WriteCustomization,
    )
    from xnano.terminal import Terminal

from xnano._appearance import Appearance, Spacing
from xnano._axes import axis_expression, axis_limits, inspect_number
from xnano._customize import (
    BitCrushAudioArguments,
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
    FuzzArguments,
    GlitchEffectArguments,
    HighPassAudioArguments,
    HslShiftEffectArguments,
    LayoutArguments,
    LightenEffectArguments,
    LowPassAudioArguments,
    PaintEffectArguments,
    PixelsArguments,
    RasterArguments,
    ReverbAudioArguments,
    SaturateEffectArguments,
    SleepEffectArguments,
    SlideInEffectArguments,
    SlideOutEffectArguments,
    StretchEffectArguments,
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
        self._is_text = False
        self._appearance: Appearance | None = None

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

    @property
    def pixels(self) -> Pixels:
        """
        The pixels of the placed buffer: ``placement.pixels[column, row] = color``.

        See [`Pixels`][xnano.pixels.Pixels].
        """
        return Pixels(self._buffer.pixels())

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
        if self._appearance is not None:
            self._appearance.text = value
            self._show_appearance()
            return
        lines = value.split('\n')
        self.width = max(len(line) for line in lines)
        self.height = len(lines)
        self._buffer.update(_core.Fill(' '), _core.Write(value))

    @property
    def foreground(self) -> ColorValue | None:
        """The text color. Assigning it draws the text again."""
        return self._appearance_of_text().foreground

    @foreground.setter
    def foreground(self, value: ColorValue | None) -> None:
        self._appearance_of_text().foreground = value
        self._show_appearance()

    @property
    def background(self) -> ColorValue | None:
        """The color behind the text. Assigning it draws the text again."""
        return self._appearance_of_text().background

    @background.setter
    def background(self, value: ColorValue | None) -> None:
        self._appearance_of_text().background = value
        self._show_appearance()

    @property
    def style(self) -> _core.Style | None:
        """A ready-made style that the colors and modifiers are applied over."""
        return self._appearance_of_text().style

    @style.setter
    def style(self, value: _core.Style | None) -> None:
        self._appearance_of_text().style = value
        self._show_appearance()

    @property
    def is_bold(self) -> bool:
        """Whether the text is bold."""
        return self._appearance_of_text().is_bold

    @is_bold.setter
    def is_bold(self, value: bool) -> None:
        self._appearance_of_text().is_bold = value
        self._show_appearance()

    @property
    def is_dim(self) -> bool:
        """Whether the text is dimmed."""
        return self._appearance_of_text().is_dim

    @is_dim.setter
    def is_dim(self, value: bool) -> None:
        self._appearance_of_text().is_dim = value
        self._show_appearance()

    @property
    def is_italic(self) -> bool:
        """Whether the text is italic."""
        return self._appearance_of_text().is_italic

    @is_italic.setter
    def is_italic(self, value: bool) -> None:
        self._appearance_of_text().is_italic = value
        self._show_appearance()

    @property
    def is_underlined(self) -> bool:
        """Whether the text is underlined."""
        return self._appearance_of_text().is_underlined

    @is_underlined.setter
    def is_underlined(self, value: bool) -> None:
        self._appearance_of_text().is_underlined = value
        self._show_appearance()

    @property
    def is_blinking(self) -> bool:
        """Whether the text blinks."""
        return self._appearance_of_text().is_blinking

    @is_blinking.setter
    def is_blinking(self, value: bool) -> None:
        self._appearance_of_text().is_blinking = value
        self._show_appearance()

    @property
    def is_reversed(self) -> bool:
        """Whether foreground and background are swapped."""
        return self._appearance_of_text().is_reversed

    @is_reversed.setter
    def is_reversed(self, value: bool) -> None:
        self._appearance_of_text().is_reversed = value
        self._show_appearance()

    @property
    def is_hidden(self) -> bool:
        """Whether the text is hidden."""
        return self._appearance_of_text().is_hidden

    @is_hidden.setter
    def is_hidden(self, value: bool) -> None:
        self._appearance_of_text().is_hidden = value
        self._show_appearance()

    @property
    def is_crossed_out(self) -> bool:
        """Whether the text is struck through."""
        return self._appearance_of_text().is_crossed_out

    @is_crossed_out.setter
    def is_crossed_out(self, value: bool) -> None:
        self._appearance_of_text().is_crossed_out = value
        self._show_appearance()

    @property
    def title(self) -> str | None:
        """The title on the border."""
        return self._appearance_of_text().title

    @title.setter
    def title(self, value: str | None) -> None:
        self._appearance_of_text().title = value
        self._show_appearance()

    @property
    def border(self) -> _core.BorderKind | None:
        """The kind of border: ``'plain'``, ``'rounded'``, ``'double'`` or ``'thick'``."""
        return self._appearance_of_text().border

    @border.setter
    def border(self, value: _core.BorderKind | None) -> None:
        self._appearance_of_text().border = value
        self._show_appearance()

    @property
    def border_style(self) -> _core.Style | None:
        """The style of the border."""
        return self._appearance_of_text().border_style

    @border_style.setter
    def border_style(self, value: _core.Style | None) -> None:
        self._appearance_of_text().border_style = value
        self._show_appearance()

    @property
    def padding(self) -> Spacing | None:
        """Space between the border and the text; see [`Spacing`][xnano.types.Spacing]."""
        return self._appearance_of_text().padding

    @padding.setter
    def padding(self, value: Spacing | None) -> None:
        self._appearance_of_text().padding = value
        self._show_appearance()

    @property
    def margin(self) -> Spacing | None:
        """Space outside the border, in the same forms as ``padding``."""
        return self._appearance_of_text().margin

    @margin.setter
    def margin(self, value: Spacing | None) -> None:
        self._appearance_of_text().margin = value
        self._show_appearance()

    def _appearance_of_text(self) -> Appearance:
        """The look of this text placement, created from the text it shows when it has none."""
        if self._appearance is None:
            if not self._is_text:
                raise TypeError(
                    'Colors, text modifiers, title, border, padding and margin decorate text, '
                    'but this placement does not show text. Set them on a placement made '
                    'from a string, or give the widget its own style and block.'
                )
            self._appearance = Appearance(text=self._buffer.text.rstrip('\n'))
        return self._appearance

    def _show_appearance(self) -> None:
        """Draw the text again with its current look, resizing the placement to fit."""
        appearance = self._appearance
        if appearance is None:
            return
        self._terminal._require_open()
        drawn = appearance.snapshot()
        self.width = drawn.width
        self.height = drawn.height
        self._buffer.update(_core.Fill(' '), _core.Paste(drawn, mode='replace'))
        self._terminal._request_frame()

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
        padding: Spacing | None = None,
        margin: Spacing | None = None,
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
            padding: Space between the border and the text; see
                [`Terminal.write`][xnano.terminal.Terminal.write].
            margin: Space outside the box, in the same forms.
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
                padding,
                margin,
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
            padding=padding,
            margin=margin,
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
        self, kind: Literal['fill'], /, **parameters: Unpack[FillArguments]
    ) -> FillCustomization: ...
    @overload
    def fx(
        self, kind: Literal['write'], /, **parameters: Unpack[WriteArguments]
    ) -> WriteCustomization: ...
    @overload
    def fx(
        self, kind: Literal['layout'], /, **parameters: Unpack[LayoutArguments]
    ) -> LayoutCustomization: ...
    @overload
    def fx(
        self, kind: Literal['fuzz'], /, **parameters: Unpack[FuzzArguments]
    ) -> FuzzCustomization: ...
    @overload
    def fx(
        self, kind: Literal['pixels'], /, **parameters: Unpack[PixelsArguments]
    ) -> PixelsCustomization: ...
    @overload
    def fx(
        self, kind: Literal['raster'], /, **parameters: Unpack[RasterArguments]
    ) -> RasterCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.fade_to'],
        /,
        **parameters: Unpack[FadeToEffectArguments],
    ) -> FadeToEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.fade_from'],
        /,
        **parameters: Unpack[FadeFromEffectArguments],
    ) -> FadeFromEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.paint'],
        /,
        **parameters: Unpack[PaintEffectArguments],
    ) -> PaintEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.saturate'],
        /,
        **parameters: Unpack[SaturateEffectArguments],
    ) -> SaturateEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.lighten'],
        /,
        **parameters: Unpack[LightenEffectArguments],
    ) -> LightenEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.darken'],
        /,
        **parameters: Unpack[DarkenEffectArguments],
    ) -> DarkenEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.sweep_in'],
        /,
        **parameters: Unpack[SweepInEffectArguments],
    ) -> SweepInEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.sweep_out'],
        /,
        **parameters: Unpack[SweepOutEffectArguments],
    ) -> SweepOutEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.slide_in'],
        /,
        **parameters: Unpack[SlideInEffectArguments],
    ) -> SlideInEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.slide_out'],
        /,
        **parameters: Unpack[SlideOutEffectArguments],
    ) -> SlideOutEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.hsl_shift'],
        /,
        **parameters: Unpack[HslShiftEffectArguments],
    ) -> HslShiftEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.dissolve'],
        /,
        **parameters: Unpack[DissolveEffectArguments],
    ) -> DissolveEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.coalesce'],
        /,
        **parameters: Unpack[CoalesceEffectArguments],
    ) -> CoalesceEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.glitch'],
        /,
        **parameters: Unpack[GlitchEffectArguments],
    ) -> GlitchEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.sleep'],
        /,
        **parameters: Unpack[SleepEffectArguments],
    ) -> SleepEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.evolve'],
        /,
        **parameters: Unpack[EvolveEffectArguments],
    ) -> EvolveEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.evolve_into'],
        /,
        **parameters: Unpack[EvolveIntoEffectArguments],
    ) -> EvolveIntoEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.evolve_from'],
        /,
        **parameters: Unpack[EvolveFromEffectArguments],
    ) -> EvolveFromEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.expand'],
        /,
        **parameters: Unpack[ExpandEffectArguments],
    ) -> ExpandEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.stretch'],
        /,
        **parameters: Unpack[StretchEffectArguments],
    ) -> StretchEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['effect.explode'],
        /,
        **parameters: Unpack[ExplodeEffectArguments],
    ) -> ExplodeEffectCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.bit_crush'],
        /,
        **parameters: Unpack[BitCrushAudioArguments],
    ) -> BitCrushAudioCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.distortion'],
        /,
        **parameters: Unpack[DistortionAudioArguments],
    ) -> DistortionAudioCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.low_pass'],
        /,
        **parameters: Unpack[LowPassAudioArguments],
    ) -> LowPassAudioCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.high_pass'],
        /,
        **parameters: Unpack[HighPassAudioArguments],
    ) -> HighPassAudioCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.delay'],
        /,
        **parameters: Unpack[DelayAudioArguments],
    ) -> DelayAudioCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.reverb'],
        /,
        **parameters: Unpack[ReverbAudioArguments],
    ) -> ReverbAudioCustomization: ...
    @overload
    def fx(
        self,
        kind: Literal['audio.tremolo'],
        /,
        **parameters: Unpack[TremoloAudioArguments],
    ) -> TremoloAudioCustomization: ...
    def fx(self, kind: CustomizationKind, /, **parameters: object) -> Customization:
        """
        Apply an effect or other typed customization to this placement and return it.

        The returned customization stays attached: assigning one of its fields afterwards
        changes the placement, and a running effect is stopped and started again with the
        new values. Use the properties of the placement for how text looks (colors, border,
        title, padding, margin).

        Args:
            kind: Which customization to apply, such as ``'fill'``, ``'effect.dissolve'`` or
                ``'pixels'``.
            parameters: Keyword arguments for the chosen customization kind.
        """
        compiled = cast('Callable[..., Customization]', _customize_operation)(
            kind, **parameters
        )
        compiled.apply_to(cast('Placement[object]', self))
        return compiled

    def make_draggable(self, axis: Literal['x', 'y'] = 'x') -> Placement[StateT]:
        """
        Let the pointer move this placement along one axis by dragging it.

        Pressing the placement grabs the pointer, so the drag keeps going when the pointer
        leaves it. The placement follows the pointer's position inside its parent. Give the
        axis a range first, such as ``placement.x = (0, 19)``, and the drag stays inside it.
        Open the terminal with ``mouse=True`` to receive drags.

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
