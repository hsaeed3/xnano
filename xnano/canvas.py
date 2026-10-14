"""
xnano.canvas

Compose a buffer with [`new`][xnano.canvas.new] (or [`make`][xnano.canvas.make]),
then build it with [`Canvas.build`][xnano.canvas.Canvas.build] or open it live with
[`Canvas.open`][xnano.canvas.Canvas.open] or [`open`][xnano.open].

[`Canvas`][xnano.canvas.Canvas] records widgets, attributes, styles, operations and
children without opening a terminal or drawing until asked.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict, cast, overload

import xnano_core as _core
from xnano._appearance import APPEARANCE_NAMES, Appearance
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
from xnano._hooks import Trigger
from xnano._media import content_buffer
from xnano._optional import is_image
from xnano._values import (
    AttributeValue,
    Axis,
    AxisName,
    Content,
    Number,
    NumericExpression,
    StateT,
)
from xnano.context import Context
from xnano.expressions import (
    Parent,
    ParentExpressionScope,
    Root,
    RootExpressionScope,
)
from xnano.operations import (
    ContextualOperation,
    OperationResult,
    OperationTrigger,
)
from xnano.operations import (
    hook as _hook_decorator,
)
from xnano_core import TextContent

if TYPE_CHECKING:
    from typing_extensions import Unpack
    from xnano_image import TerminalImage

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
    from xnano.placement import Placement
    from xnano.terminal import Terminal

__all__ = [
    'BufferArguments',
    'Canvas',
    'Composition',
    'CompositionContent',
    'make',
    'new',
]

_AXES: tuple[AxisName, ...] = ('x', 'y', 'width', 'height')


class BufferArguments(TypedDict, total=False):
    """
    The arguments a buffer can be constructed with before it is placed.

    Attributes:
        content: Text the buffer starts with.
        width: The width in cells.
        height: The height in cells.
        x: The column.
        y: The row.
        style: The style of the buffer.
    """

    content: TextContent
    """Text the buffer starts with."""
    width: int
    """The width in cells."""
    height: int
    """The height in cells."""
    x: int
    """The column."""
    y: int
    """The row."""
    style: _core.Style
    """The style of the buffer."""


CompositionContent: TypeAlias = (
    'type[_core.Buffer] | _core.Buffer | _core.Operation | TerminalImage | str | None'
)
"""What [`new`][xnano.new] starts from: a widget class, a buffer, text, an operation or nothing."""


class Canvas:
    """
    A composable buffer specification created by [`new`][xnano.new] (or [`make`][xnano.make]).

    Set any attribute the buffer or widget understands. Position and size keep their usual
    operators, so ``canvas.x += 1`` and ``canvas.x = canvas.parent.width // 2`` are
    ordinary assignments. ``canvas | operation`` records an operation, including a
    [`Style`][xnano.styles.Style], [`Border`][xnano.operations.Border],
    [`Effect`][xnano.effects.Effect], [`draggable`][xnano.operations.draggable],
    [`shade`][xnano.operations.shade], [`fx`][xnano.operations.fx] or
    [`ContextualOperation`][xnano.operations.ContextualOperation].
    [`write`][xnano.canvas.Canvas.write] attaches a child canvas or applies an operation.

    Nothing here draws until asked. Call [`build`][xnano.canvas.Canvas.build] to get a
    standalone [`Buffer`][xnano_core.Buffer], pass the canvas to
    [`Terminal.write`][xnano.terminal.Terminal.write], or open it directly in a terminal with
    [`open`][xnano.canvas.Canvas.open] or ``xnano.open(canvas)``.

    Attributes:
        x: The column of the left edge, as an [`Axis`][xnano.types.Axis].
        y: The row of the top edge, as an [`Axis`][xnano.types.Axis].
        width: The width, as an [`Axis`][xnano.types.Axis].
        height: The height, as an [`Axis`][xnano.types.Axis].
        parent: Symbolic expressions for the parent container's ``width``, ``height`` and ``size``.
        root: Symbolic expressions for the root terminal's ``width``, ``height``, ``size`` and ``time``.
        time: Symbolic expression for elapsed seconds on the terminal clock.

    Examples:
        ```python
        import xnano
        from xnano_core import Border, Buffer

        card = xnano.new(width=12, height=3) | Border('rounded')
        buffer = card.build()
        assert isinstance(buffer, Buffer)
        assert '╭' in buffer.render(format='text')
        ```
    """

    _content: CompositionContent
    _attributes: dict[str, AttributeValue]
    _operations: list[_core.Operation]
    _contextual_operations: list[ContextualOperation[object]]
    _children: list[Canvas]
    _buffer: _core.Buffer | None
    _pending: list[_core.Operation]

    @property
    def x(self) -> Number | NumericExpression:
        """The column of the left edge, as an [`Axis`][xnano.types.Axis]."""
        return self._read_axis('x')

    @x.setter
    def x(self, value: Axis) -> None:
        self._attributes['x'] = value
        if (
            self._buffer is not None
            and isinstance(value, int)
            and not isinstance(value, bool)
        ):
            self._buffer.x = value

    @property
    def y(self) -> Number | NumericExpression:
        """The row of the top edge, as an [`Axis`][xnano.types.Axis]."""
        return self._read_axis('y')

    @y.setter
    def y(self, value: Axis) -> None:
        self._attributes['y'] = value
        if (
            self._buffer is not None
            and isinstance(value, int)
            and not isinstance(value, bool)
        ):
            self._buffer.y = value

    @property
    def width(self) -> Number | NumericExpression:
        """The width, as an [`Axis`][xnano.types.Axis]."""
        return self._read_axis('width')

    @width.setter
    def width(self, value: Axis) -> None:
        self._attributes['width'] = value
        if (
            self._buffer is not None
            and isinstance(value, int)
            and not isinstance(value, bool)
        ):
            self._buffer.width = value

    @property
    def height(self) -> Number | NumericExpression:
        """The height, as an [`Axis`][xnano.types.Axis]."""
        return self._read_axis('height')

    @height.setter
    def height(self, value: Axis) -> None:
        self._attributes['height'] = value
        if (
            self._buffer is not None
            and isinstance(value, int)
            and not isinstance(value, bool)
        ):
            self._buffer.height = value

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

    def _read_axis(self, name: AxisName) -> Number | NumericExpression:
        buffer = self._buffer
        value: object = (
            getattr(buffer, name) if buffer is not None else self._attributes.get(name)
        )
        if isinstance(value, (int, float, _core.NumericValue)):
            return value
        if (
            isinstance(value, tuple)
            and len(value) == 2
            and isinstance(value[0], (int, float, _core.NumericValue))
        ):
            return value[0]
        if name in ('width', 'height'):
            if isinstance(self._content, _core.Buffer):
                return cast('int', getattr(self._content, name))
            if isinstance(self._content, str):
                measured = _core.Buffer(self._content)
                return cast('int', getattr(measured, name))
        raise AttributeError(
            f'{name} is not set on this canvas. Assign canvas.{name} before '
            f'reading it, or call build() and read the attribute on the buffer it returns.'
        )

    def __init__(
        self, content: CompositionContent, attributes: dict[str, AttributeValue]
    ) -> None:
        """
        Record a buffer to build. Use [`new`][xnano.new] instead of calling this directly.

        Args:
            content: What the buffer is: a widget class, a buffer, text, an image or nothing.
            attributes: Attributes to set on the buffer, such as ``x`` or ``ratio``.
        """
        object.__setattr__(self, '_content', content)
        object.__setattr__(self, '_attributes', dict(attributes))
        object.__setattr__(self, '_operations', [])
        object.__setattr__(self, '_contextual_operations', [])
        object.__setattr__(self, '_children', [])
        object.__setattr__(self, '_buffer', None)
        object.__setattr__(self, '_pending', [])
        if isinstance(content, ContextualOperation):
            self._contextual_operations.append(content)

    def __setattr__(self, name: str, value: AttributeValue) -> None:
        if name in ('x', 'y', 'width', 'height'):
            prop = getattr(type(self), name)
            prop.fset(self, value)
            return
        if name in APPEARANCE_NAMES:
            self._attributes[name] = value
            if self._buffer is not None:
                self._show_appearance()
            return
        buffer = self._buffer
        if buffer is not None:
            setattr(buffer, name, value)
            return
        self._attributes[name] = value

    def __getattr__(self, name: str) -> AttributeValue:
        if name in APPEARANCE_NAMES:
            return getattr(_appearance_of(self._content, self._attributes), name)
        buffer = self._buffer
        if buffer is not None:
            return getattr(buffer, name)
        try:
            return self._attributes[name]
        except KeyError:
            raise AttributeError(
                f'{name} is not set on this canvas. Assign canvas.{name} before '
                f'reading it, or call build() and read the attribute on the buffer it returns.'
            ) from None

    def __or__(self, operation: _core.Operation | _core.Style) -> Canvas:
        self._record_operation(operation)
        return self

    def __ior__(self, operation: _core.Operation | _core.Style) -> Canvas:
        self._record_operation(operation)
        return self

    def update(self, *operations: _core.Operation | _core.Style) -> Canvas:
        """
        Record operations or styles to apply when the buffer is built or mounted.

        Args:
            operations: Any core or contextual operation, effect or style.
        """
        for item in operations:
            self._record_operation(item)
        return self

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
        Add an effect or other typed customization to this canvas and return it.

        The returned customization stays attached: assigning one of its fields afterwards
        changes the canvas, and a running effect is stopped and started again with the new
        values. Use the keyword parameters of ``write`` and ``new`` for how text looks
        (colors, border, title, padding, margin).

        Args:
            kind: Which customization to add, such as ``'fill'``, ``'effect.dissolve'`` or
                ``'pixels'``.
            parameters: Keyword arguments for the chosen customization kind.

        Examples:
            ```python
            import xnano

            canvas = xnano.new('hello', width=5, height=1)
            dots = canvas.fx('fill', cell='.')
            dots.cell = '#'
            assert '#' in canvas.build().render(format='text')
            ```
        """
        compiled = cast('Callable[..., Customization]', _customize_operation)(
            kind, **parameters
        )
        self._record_operation(compiled)
        return compiled

    @overload
    def hook(
        self, function: Callable[[Context[StateT]], OperationResult], /
    ) -> ContextualOperation[StateT]: ...
    @overload
    def hook(
        self,
        /,
        *,
        on: OperationTrigger = 'frame',
        every: float | None = None,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
        when: Trigger[StateT] | None = None,
    ) -> Callable[
        [Callable[[Context[StateT]], OperationResult]], ContextualOperation[StateT]
    ]: ...
    def hook(
        self,
        function: Callable[[Context[StateT]], OperationResult] | None = None,
        /,
        *,
        on: OperationTrigger = 'frame',
        every: float | None = None,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
        when: Trigger[StateT] | None = None,
    ) -> (
        ContextualOperation[StateT]
        | Callable[
            [Callable[[Context[StateT]], OperationResult]], ContextualOperation[StateT]
        ]
    ):
        """
        Register a [`ContextualOperation`][xnano.operations.ContextualOperation] on this canvas.

        Args:
            function: The function to wrap when ``@canvas.hook`` is used without parentheses.
            on: When the operation runs.
            every: Optional interval in seconds.
            after: Optional one-shot delay in seconds.
            keys: Key names to match when ``on='key'``.
            when: Custom trigger function or generator.
        """

        def register(
            callback: Callable[[Context[StateT]], OperationResult],
        ) -> ContextualOperation[StateT]:
            wrapped = _hook_decorator(
                on=on,
                every=every,
                after=after,
                keys=keys,
                when=when,
            )(callback)
            self._record_operation(wrapped)
            return wrapped

        if function is not None:
            return register(function)
        return register

    def write(
        self,
        child: Content | Canvas | _core.Operation | _core.Style | None = None,
        /,
        **attributes: AttributeValue,
    ) -> Canvas:
        """
        Attach a child canvas or apply an operation to this canvas.

        When ``child`` is an [`Operation`][xnano.operations.Operation] or
        [`Style`][xnano.styles.Style] and no placement attributes are given, it is applied to
        this canvas and ``self`` is returned. Otherwise ``child`` is recorded as a nested
        child [`Canvas`][xnano.canvas.Canvas] and that child canvas is returned so you can
        further customize or pipe operations onto it.

        Args:
            child: A child buffer, widget, string, canvas, operation or style.
            attributes: Attributes set on the child before it is attached, such as ``x`` and ``y``.
        """
        if isinstance(child, (_core.Operation, _core.Style)) and not attributes:
            self._record_operation(child)
            return self
        if isinstance(child, Canvas):
            for name, value in attributes.items():
                setattr(child, name, value)
            child_canvas = child
        else:
            child_canvas = Canvas(cast('CompositionContent', child), attributes)
        self._children.append(child_canvas)
        buffer = self._buffer
        if buffer is not None:
            _attach(buffer, child_canvas)
        return child_canvas

    def _show_appearance(self) -> None:
        """Draw the text again with its current look, resizing the buffer to fit."""
        buffer = self._buffer
        if buffer is None:
            return
        if not isinstance(self._content, str):
            raise TypeError(
                'Colors, text modifiers, title, border, padding and margin decorate text, '
                'but this canvas does not hold text. Set them on a canvas made from a '
                'string, or give the widget its own style and block.'
            )
        drawn = _appearance_of(self._content, self._attributes).snapshot()
        buffer.resize(drawn.width, drawn.height)
        buffer.update(_core.Fill(' '), _core.Paste(drawn, mode='replace'))

    def build(self) -> _core.Buffer:
        """
        Build the buffer this canvas describes.

        The returned buffer is a core [`Buffer`][xnano_core.Buffer] (or a widget, which is a
        buffer). Render it with ``buffer.render()``, or place it on a terminal yourself.
        ``build`` does neither: calling it draws nothing and opens nothing.

        Calling ``build`` again returns the same buffer.

        Examples:
            ```python
            import xnano

            thumb = xnano.new('#')
            thumb.x = 1
            thumb.x += 2
            buffer = thumb.build()
            assert buffer.x == 3
            assert buffer.render(format='text') == '#'
            ```
        """
        buffer = self._buffer
        if buffer is not None:
            return buffer
        built = _create(self._content, self._attributes)
        pending = [item for item in self._operations if not _apply_now(built, item)]
        for child_canvas in self._children:
            _attach(built, child_canvas)
        object.__setattr__(self, '_buffer', built)
        object.__setattr__(self, '_pending', pending)
        return built

    @overload
    def open(
        self,
        *,
        offscreen: bool = False,
        title: str | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: float = 60.0,
        realtime: bool = False,
        clear: bool = True,
        alternate_screen: bool = True,
        mouse: bool | Literal['buttons', 'motion'] = False,
        keyboard: bool | Literal['disambiguated', 'release_events'] = True,
        paste: bool = True,
        focus: bool = True,
        interrupt: bool = True,
        capture: bool = True,
        state: None = None,
    ) -> Terminal[None]: ...
    @overload
    def open(
        self,
        *,
        offscreen: bool = False,
        title: str | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: float = 60.0,
        realtime: bool = False,
        clear: bool = True,
        alternate_screen: bool = True,
        mouse: bool | Literal['buttons', 'motion'] = False,
        keyboard: bool | Literal['disambiguated', 'release_events'] = True,
        paste: bool = True,
        focus: bool = True,
        interrupt: bool = True,
        capture: bool = True,
        state: StateT,
    ) -> Terminal[StateT]: ...
    def open(
        self,
        *,
        offscreen: bool = False,
        title: str | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: float = 60.0,
        realtime: bool = False,
        clear: bool = True,
        alternate_screen: bool = True,
        mouse: bool | Literal['buttons', 'motion'] = False,
        keyboard: bool | Literal['disambiguated', 'release_events'] = True,
        paste: bool = True,
        focus: bool = True,
        interrupt: bool = True,
        capture: bool = True,
        state: StateT | None = None,
    ) -> Terminal[StateT] | Terminal[None]:
        """
        Open a terminal with this canvas mounted on it.

        When ``width`` or ``height`` is omitted on an offscreen terminal and this canvas has
        an integer ``width`` or ``height``, the terminal uses the canvas's dimensions.

        Args:
            offscreen: Draw into memory instead of onto the screen.
            title: Window title; ``None`` leaves the existing title untouched.
            width: The width in cells.
            height: The height in cells.
            fps: The rate frames are drawn at, at most.
            realtime: Whether an offscreen terminal runs by itself on the wall clock.
            clear: Whether what the terminal drew is erased when it closes.
            alternate_screen: Whether a full-window live terminal uses the alternate screen.
            mouse: ``True`` for clicks and drags, ``'motion'`` for all movement as well.
            keyboard: ``True``, ``'disambiguated'``, ``'release_events'``, or ``False`` to ignore keys.
            paste: Whether pasted text arrives as one paste event.
            focus: Whether the terminal reports focus changes.
            interrupt: Whether ``Ctrl-C`` ends the loop on a live terminal.
            capture: Whether text printed during a live session is held back.
            state: A dataclass instance the terminal keeps and validates.
        """
        from xnano.terminal import open as open_terminal

        return cast(
            'Terminal[StateT] | Terminal[None]',
            open_terminal(
                self,
                offscreen=offscreen,
                title=title,
                width=width,
                height=height,
                fps=fps,
                realtime=realtime,
                clear=clear,
                alternate_screen=alternate_screen,
                mouse=mouse,
                keyboard=keyboard,
                paste=paste,
                focus=focus,
                interrupt=interrupt,
                capture=capture,
                state=state,
            ),
        )

    def axes(self) -> dict[AxisName, Axis]:
        """Position and size recorded on the canvas, including expressions and ranges."""
        axes: dict[AxisName, Axis] = {}
        for name in _AXES:
            value = self._attributes.get(name)
            if isinstance(value, (int, float, str, tuple, _core.NumericValue)):
                axes[name] = value
        return axes

    def apply_mounted(self, placement: Placement[object] | None = None) -> None:
        """
        Apply operations and nested children that need a mounted placement or terminal.

        Args:
            placement: The [`Placement`][xnano.placement.Placement] created when this canvas was added
                to a terminal or parent placement.
        """
        buffer = self._buffer
        pending = self._pending
        if buffer is not None and pending:
            for item in pending:
                if isinstance(item, Customization):
                    item.apply_to_surface(buffer)
                else:
                    buffer.update(item)
            object.__setattr__(self, '_pending', [])
        if placement is not None:
            for contextual in self._contextual_operations:
                contextual.apply_to(placement)
            for child_canvas in self._children:
                child_buffer = child_canvas.build()
                if buffer is not None:
                    buffer.detach(child_buffer)
                placement.write(child_canvas)

    def __xnano_buffer__(self) -> _core.Buffer:
        """Return the built buffer, for a terminal that is asked to show this canvas."""
        return self.build()

    def _record_operation(self, item: _core.Operation | _core.Style) -> None:
        if isinstance(item, _core.Style):
            item = _core.ApplyStyle(item)
        if not isinstance(item, _core.Operation):
            raise TypeError(
                f'{item!r} is not an operation, so it cannot be composed onto a buffer. '
                f'Pass an Operation such as a Border or an Effect. To nest a buffer or a '
                f'widget, use canvas.write(...).'
            )
        if isinstance(item, Customization):
            item._attach(self)
            self._operations.append(item)
            if self._buffer is not None:
                try:
                    item.apply_to_surface(self._buffer)
                except _core.RuntimeRequiredError:
                    self._pending.append(item)
            return
        if isinstance(item, ContextualOperation):
            if (
                item.on == 'immediate'
                and item._placement_runner is None
                and item._callback is None
            ):
                self._operations.append(item)
                if self._buffer is not None:
                    try:
                        item.apply_to_surface(self._buffer)
                    except _core.RuntimeRequiredError:
                        self._pending.append(item)
            else:
                self._contextual_operations.append(
                    cast('ContextualOperation[object]', item)
                )
            return
        self._operations.append(item)
        buffer = self._buffer
        if buffer is not None:
            try:
                buffer.update(item)
            except _core.RuntimeRequiredError:
                self._pending.append(item)

    def __repr__(self) -> str:
        if self._buffer is not None:
            return (
                f'Canvas(made, width={self._buffer.width}, height={self._buffer.height})'
            )
        name = getattr(self._content, '__name__', None)
        content = (
            name if isinstance(self._content, type) else type(self._content).__name__
        )
        return f'Canvas({content}, pending)'


Composition = Canvas


def new(content: CompositionContent = None, /, **attributes: AttributeValue) -> Canvas:
    """
    Create a composable [`Canvas`][xnano.canvas.Canvas] without opening a terminal.

    ``content`` is a widget class, a buffer, text, an image, an operation, or nothing for an
    empty buffer. Keyword arguments are attributes of that buffer, such as ``width``,
    ``ratio`` or ``x``. Call [`Canvas.build`][xnano.canvas.Canvas.build] for a standalone
    buffer, pass the canvas to [`Terminal.write`][xnano.terminal.Terminal.write], or open it directly with
    [`Canvas.open`][xnano.canvas.Canvas.open] or [`open`][xnano.open].

    Args:
        content: What the buffer is. A widget class such as ``Gauge`` is constructed from the
            attributes. A buffer is used as it is. A string becomes text. An image (from
            [`img`][xnano.img] or [`TerminalImage`][xnano_image.TerminalImage]) becomes cells
            at the ``width`` and ``height`` given, or at its own size. Omit it for an empty
            buffer.
        attributes: Attributes applied to the buffer. Any attribute the buffer accepts,
            including expressions and ranges.

    Examples:
        ```python
        import xnano
        from xnano_core import Gauge

        gauge = xnano.new(Gauge, ratio=0.5, width=10, height=1)
        gauge.ratio = 0.75
        assert gauge.build().render(format='text')
        ```
    """
    return Canvas(content, attributes)


def make(content: CompositionContent = None, /, **attributes: AttributeValue) -> Canvas:
    """
    Create a composable [`Canvas`][xnano.canvas.Canvas] (alias for [`new`][xnano.canvas.new]).

    Args:
        content: What the buffer is: a widget class, a buffer, text, an image, an operation
            or nothing for an empty buffer.
        attributes: Attributes applied to the buffer, including expressions and ranges.

    Examples:
        ```python
        import xnano
        from xnano_core import Gauge

        gauge = xnano.make(Gauge, ratio=0.5, width=10, height=1)
        gauge.ratio = 0.75
        assert gauge.build().render(format='text')
        ```
    """
    return Canvas(content, attributes)


def _apply_now(buffer: _core.Buffer, item: _core.Operation) -> bool:
    """Apply an operation now. Return whether it could run without a runtime."""
    if isinstance(item, (ContextualOperation, Customization)):
        try:
            item.apply_to_surface(buffer)
        except _core.RuntimeRequiredError:
            return False
        return True
    try:
        buffer.update(item)
    except _core.RuntimeRequiredError:
        return False
    return True


def _create(
    content: CompositionContent, attributes: dict[str, AttributeValue]
) -> _core.Buffer:
    if isinstance(content, _core.Buffer):
        for name, value in attributes.items():
            if _is_buffer_value(name, value):
                setattr(content, name, value)
        return content
    if isinstance(content, type) and issubclass(content, _core.Buffer):
        return _construct(content, attributes)
    if is_image(content):
        width, height = attributes.get('width'), attributes.get('height')
        buffer, _ = content_buffer(
            cast('Content', content),
            columns=width if isinstance(width, int) else None,
            rows=height if isinstance(height, int) else None,
        )
        for name, value in attributes.items():
            if name not in ('width', 'height') and _is_buffer_value(name, value):
                setattr(buffer, name, value)
        return buffer
    if isinstance(content, str) or content is None:
        appearance = _appearance_of(content, attributes)
        if content is not None and (
            appearance.has_style or appearance.has_frame or appearance.margin is not None
        ):
            buffer = appearance.snapshot()
            for name, value in attributes.items():
                if name not in APPEARANCE_NAMES and _is_buffer_value(name, value):
                    setattr(buffer, name, value)
            return buffer
        return _build_plain(content, attributes)
    if isinstance(content, ContextualOperation):
        buffer = _build_plain(None, attributes)
        if content.on == 'immediate':
            content.apply_to_surface(buffer)
        return buffer
    if isinstance(content, _core.Operation):
        buffer = _build_plain(None, attributes)
        buffer.update(content)
        return buffer
    raise TypeError(
        f'{content!r} cannot be composed into a buffer. Pass a widget class, a buffer, '
        f'a string, an operation, or no content for an empty buffer.'
    )


def _construct(
    kind: type[_core.Buffer], attributes: dict[str, AttributeValue]
) -> _core.Buffer:
    """Construct a widget, then set any attribute its constructor does not take."""
    geometry = _geometry(attributes)
    remaining = {
        name: value
        for name, value in attributes.items()
        if name not in geometry and _is_buffer_value(name, value)
    }
    factory = cast('Callable[..., _core.Buffer]', kind)
    try:
        return factory(**geometry, **remaining)
    except TypeError:
        pass
    try:
        buffer = factory(**geometry) if geometry else factory()
    except TypeError as error:
        raise TypeError(
            f'{kind.__name__} could not be constructed from {sorted(attributes)}. '
            f'Pass the attributes {kind.__name__} accepts, or construct it yourself and '
            f'pass the instance to new().'
        ) from error
    for name, value in remaining.items():
        _assign_attribute(buffer, kind, name, value)
    return buffer


def _assign_attribute(
    buffer: _core.Buffer, kind: type[_core.Buffer], name: str, value: AttributeValue
) -> None:
    try:
        setattr(buffer, name, value)
    except (AttributeError, TypeError) as error:
        raise TypeError(
            f'{kind.__name__} has no attribute {name} that can be set to {value!r}. '
            f'Check the name against the widget, or pass it to the constructor.'
        ) from error


def _build_plain(
    content: str | None, attributes: dict[str, AttributeValue]
) -> _core.Buffer:
    arguments = _geometry(attributes)
    if isinstance(content, str):
        arguments['content'] = content
    buffer = _core.Buffer(
        arguments.get('content'),
        width=arguments.get('width'),
        height=arguments.get('height'),
        x=arguments.get('x', 0),
        y=arguments.get('y', 0),
        style=arguments.get('style'),
    )
    for name, value in attributes.items():
        if name in arguments or not _is_buffer_value(name, value):
            continue
        setattr(buffer, name, value)
    return buffer


def _is_buffer_value(name: str, value: AttributeValue) -> bool:
    """
    Whether a buffer can take the attribute as it is.

    Position and size may be percentages, ranges or expressions, which are applied when the
    buffer is placed.
    """
    if name in APPEARANCE_NAMES:
        return False
    if name in _AXES:
        return isinstance(value, int) and not isinstance(value, bool)
    return not isinstance(value, _core.NumericValue)


def _appearance_of(
    content: CompositionContent, attributes: dict[str, AttributeValue]
) -> Appearance:
    """The look that a canvas's appearance attributes describe for its text."""
    return Appearance(
        text=content if isinstance(content, str) else '',
        **{name: attributes[name] for name in APPEARANCE_NAMES if name in attributes},  # type: ignore[arg-type]
    )


def _attach(buffer: _core.Buffer, child_canvas: Canvas) -> None:
    child_buffer = child_canvas.build()
    for name, value in child_canvas._attributes.items():
        if _is_buffer_value(name, value):
            setattr(child_buffer, name, value)
    buffer.attach(child_buffer)


def _geometry(attributes: dict[str, AttributeValue]) -> BufferArguments:
    """Constructor arguments a buffer can take before it is placed."""
    geometry: BufferArguments = {}
    for name in _AXES:
        value = attributes.get(name)
        if isinstance(value, int) and not isinstance(value, bool):
            geometry[name] = value
    style = attributes.get('style')
    if isinstance(style, _core.Style):
        geometry['style'] = style
    return geometry
