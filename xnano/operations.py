"""
xnano.operations

Operations that change or animate a buffer, placement or canvas.

Pass operations to ``update`` or pipe them with ``|``. Create a reusable hook from a function
with [`hook`][xnano.hooks.hook]. Animated effects such as [`Effect`][xnano.operations.Effect]
(``Effect.fade_to(...)``, ``Effect.dissolve(...)``) and
[`CancelEffect`][xnano.operations.CancelEffect] are operations as well and apply the same way.

The Dynamic operations ([`DynamicFill`][xnano.operations.DynamicFill],
[`DynamicWrite`][xnano.operations.DynamicWrite],
[`DynamicLayout`][xnano.operations.DynamicLayout],
[`DynamicFuzz`][xnano.operations.DynamicFuzz],
[`DynamicPixels`][xnano.operations.DynamicPixels] and
[`DynamicRaster`][xnano.operations.DynamicRaster]) are operations whose settings are dataclass
fields holding plain values: numbers, text, cells and styles. The fields are read every time the
operation is applied, and assigning a field of an applied operation applies it again with the
new value. A field does not follow an expression over time. To make a position or size follow
an expression, give the expression to the placement itself (``placement.x = ...``) or change the
field from a hook. The parameters of an effect, which can follow an expression while it runs,
are built with [`effect`][xnano.effects.effect].
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Generic, Literal, cast

import xnano_core as _core
from xnano._internal._axes import to_rgb
from xnano._internal._dynamic_operations import DynamicOperation
from xnano._schema._appearance import RGB, ColorValue
from xnano._schema._generics import DepsT, StateT, TargetT
from xnano._schema._hooks import HookTrigger, IfRunning
from xnano._schema._layout import PixelEncoding
from xnano._schema._operations import DynamicFillSchema as DynamicFillSchema
from xnano._schema._operations import DynamicFuzzSchema as DynamicFuzzSchema
from xnano._schema._operations import DynamicLayoutSchema as DynamicLayoutSchema
from xnano._schema._operations import DynamicPixelsSchema as DynamicPixelsSchema
from xnano._schema._operations import DynamicRasterSchema as DynamicRasterSchema
from xnano._schema._operations import DynamicWriteSchema as DynamicWriteSchema
from xnano._schema._operations import OperationResult as OperationResult
from xnano.hooks._context import Context

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.layout._placement import Placement
    from xnano_core import ApplyStyle as _CoreApplyStyle
    from xnano_core import Background as _CoreBackground
    from xnano_core import Border as _CoreBorder
    from xnano_core import CancelEffect as _CoreCancelEffect
    from xnano_core import Clear as _CoreClear
    from xnano_core import Dissolve as _CoreDissolve
    from xnano_core import Effect as _CoreEffect
    from xnano_core import Fade as _CoreFade
    from xnano_core import Fill as _CoreFill
    from xnano_core import Foreground as _CoreForeground
    from xnano_core import Fuzz as _CoreFuzz
    from xnano_core import Glitch as _CoreGlitch
    from xnano_core import Layout as _CoreLayout
    from xnano_core import Margin as _CoreMargin
    from xnano_core import Move as _CoreMove
    from xnano_core import Operation as _CoreOperation
    from xnano_core import Paste as _CorePaste
    from xnano_core import Place as _CorePlace
    from xnano_core import Resize as _CoreResize
    from xnano_core import Write as _CoreWrite

    ApplyStyle = _CoreApplyStyle
    """
    An operation that patches a style onto every cell of its target.

    Colors and modifiers that the [`Style`][xnano.styles.Style] leaves unset stay as they
    are, so it adds to the look of the target instead of replacing it.

    ```python
    import xnano
    from xnano.operations import ApplyStyle
    from xnano.styles import Style

    with xnano.new(width=8, height=1) as canvas:
        text = canvas.screen.write('hi')
        text | ApplyStyle(Style('green', bold=True))
        assert 'bold' in text.core_buffer[0, 0].style.modifiers
    ```
    """

    Background = _CoreBackground
    """
    An operation that sets the background color of every cell of its target.

    The color is a name, a hex string, a ``(red, green, blue)`` tuple or a
    [`Color`][xnano.styles.Color].

    ```python
    import xnano
    from xnano.operations import Background

    with xnano.new(width=8, height=1) as canvas:
        text = canvas.screen.write('hi')
        text | Background((0, 0, 255))
        assert text.core_buffer[0, 0].background.to_rgb() == (0, 0, 255)
    ```
    """

    Border = _CoreBorder
    """
    An operation that draws a border around the edge of its target.

    The kind is ``'plain'``, ``'rounded'``, ``'double'`` or ``'thick'``, and a
    [`Style`][xnano.styles.Style] colors the border cells.

    Maps to [`ratatui::widgets::Block`](https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Block.html)
    with [`BorderType`](https://docs.rs/ratatui/0.30.0/ratatui/widgets/enum.BorderType.html).

    ```python
    import xnano
    from xnano.operations import Border

    with xnano.new(width=6, height=3) as canvas:
        canvas.screen | Border('rounded')
        assert canvas.screen.render().splitlines()[0] == '╭────╮'
    ```
    """

    CancelEffect = _CoreCancelEffect
    """
    An operation that stops the running effect that was started with a key.

    Give an effect a ``key`` when it is created, then apply ``CancelEffect(key)`` to stop it
    before it ends. The target looks as it did before the effect.

    ```python
    import xnano
    from xnano.operations import CancelEffect, Dissolve

    with xnano.new(width=10, height=1) as canvas:
        text = canvas.screen.write('hello')
        text | Dissolve(duration_milliseconds=100, seed=1, key='fade-out')
        text | CancelEffect('fade-out')
        canvas.clock.step(delta_seconds=0.05)
        canvas.clock.step(delta_seconds=0.05)
        assert canvas.screen.render() == 'hello'
    ```
    """

    Clear = _CoreClear
    """
    A widget of blank cells that hide whatever is behind them.

    Write one onto a canvas to erase the area it covers. Its ``symbol`` is the one-column
    character every cell shows, a space by default.

    Maps to [`ratatui::widgets::Clear`](https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Clear.html).

    ```python
    import xnano
    from xnano.operations import Clear, Fill

    with xnano.new(width=8, height=3) as canvas:
        canvas.screen | Fill('#')
        canvas.screen.write(Clear(width=4, height=1), x=1, y=1)
        assert canvas.screen.render().splitlines()[1] == '#    ###'
    ```
    """

    Dissolve = _CoreDissolve
    """
    An effect that dissolves the glyphs of its target away, cell by cell.

    With ``should_reverse=True`` the glyphs appear instead. A ``seed`` makes the order of the
    cells repeatable, and a ``key`` lets [`CancelEffect`][xnano.operations.CancelEffect] stop
    it. It is the class form of ``Effect.dissolve(...)``.

    Maps to [`tachyonfx::fx::dissolve`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/fn.dissolve.html)
    and [`tachyonfx::fx::coalesce`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/fn.coalesce.html).

    ```python
    import xnano
    from xnano.operations import Dissolve

    with xnano.new(width=10, height=1) as canvas:
        text = canvas.screen.write('hello')
        text | Dissolve(duration_milliseconds=100, seed=1)
        canvas.clock.step(delta_seconds=0.05)
        canvas.clock.step(delta_seconds=0.05)
        assert canvas.screen.render() != 'hello'
    ```
    """

    Effect = _CoreEffect
    """
    A composable animation of colors or glyphs, applied like any other operation.

    The method constructors ``Effect.fade_to(...)``, ``Effect.dissolve(...)`` and the other
    named effects are the operation form of [`effect`][xnano.effects.effect]. The settings of
    an effect, such as ``foreground`` and ``duration_milliseconds``, can be read and assigned,
    and effects combine with ``then`` and ``repeat``.

    ```python
    import xnano
    from xnano.operations import Effect

    with xnano.new(width=10, height=1) as canvas:
        text = canvas.screen.write('hello')
        before = canvas.screen.render(format='ansi')
        fade = Effect.fade_to('red', duration_milliseconds=100)
        fade.duration_milliseconds = 200
        text | fade
        canvas.clock.step(delta_seconds=0.05)
        canvas.clock.step(delta_seconds=0.05)
        assert canvas.screen.render(format='ansi') != before
    ```
    """

    Fade = _CoreFade
    """
    An effect that fades the colors of its target toward a foreground and a background color.

    Leave a color out to keep it as it is. It is the class form of ``Effect.fade_to(...)``.

    Maps to [`tachyonfx::fx::fade_to`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/fn.fade_to.html).

    ```python
    import xnano
    from xnano.operations import Fade

    with xnano.new(width=10, height=1) as canvas:
        text = canvas.screen.write('hello')
        before = canvas.screen.render(format='ansi')
        text | Fade(foreground='red', duration_milliseconds=100)
        canvas.clock.step(delta_seconds=0.05)
        canvas.clock.step(delta_seconds=0.05)
        assert canvas.screen.render(format='ansi') != before
    ```
    """

    Fill = _CoreFill
    """
    An operation that fills every cell of its target with one character or
    [`Cell`][xnano.buffers.Cell].

    Use [`DynamicFill`][xnano.operations.DynamicFill] for the form whose cell can be changed
    after it is applied.

    ```python
    import xnano
    from xnano.operations import Fill

    with xnano.new(width=3, height=2) as canvas:
        canvas.screen | Fill('#')
        assert canvas.screen.render().splitlines() == ['###', '###']
    ```
    """

    Foreground = _CoreForeground
    """
    An operation that sets the foreground color of every cell of its target.

    The color is a name, a hex string, a ``(red, green, blue)`` tuple or a
    [`Color`][xnano.styles.Color].

    ```python
    import xnano
    from xnano.operations import Foreground
    from xnano.styles import Color

    with xnano.new(width=8, height=1) as canvas:
        text = canvas.screen.write('hi')
        text | Foreground('red')
        assert text.core_buffer[0, 0].foreground == Color('red')
    ```
    """

    Fuzz = _CoreFuzz
    """
    An operation that replaces a percentage of the visible glyphs of its target with noise.

    It changes the cells once, when it is applied, and does not need a running canvas. Blank
    and wide cells are left alone. A ``seed`` makes the noise repeatable. Use
    [`DynamicFuzz`][xnano.operations.DynamicFuzz] for the form whose settings can be changed
    after it is applied.

    ```python
    import xnano
    from xnano.operations import Fuzz, Write

    with xnano.new(width=5, height=1) as canvas:
        canvas.screen | Write('hello') | Fuzz(100, seed=1)
        assert canvas.screen.render() != 'hello'
    ```
    """

    Glitch = _CoreGlitch
    """
    An effect that randomly corrupts and displaces glyphs of its target.

    The ``intensity`` is the fraction of cells affected, from ``0.0`` to ``1.0``, and a ``seed``
    makes the result repeatable. It is the class form of ``Effect.glitch(...)``.

    Maps to [`tachyonfx::fx::Glitch`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/struct.Glitch.html).

    ```python
    import xnano
    from xnano.operations import Glitch

    with xnano.new(width=10, height=1) as canvas:
        text = canvas.screen.write('hello')
        text | Glitch(intensity=1.0, duration_milliseconds=100, seed=1)
        canvas.clock.step(delta_seconds=0.05)
        canvas.clock.step(delta_seconds=0.05)
        assert canvas.screen.render() != 'hello'
    ```
    """

    Layout = _CoreLayout
    """
    An operation that arranges the children attached to a buffer in a row, a column or an
    overlay.

    The ``sizes`` are one [`SizeRule`][xnano.layout.SizeRule] per child along the main axis,
    ``spacing`` is the number of cells between children and ``padding`` the number of cells
    between the edge of the parent and its children. Use
    [`DynamicLayout`][xnano.operations.DynamicLayout] for the form whose settings can be
    changed after it is applied.

    Maps to [`ratatui::layout::Layout`](https://docs.rs/ratatui/0.30.0/ratatui/layout/struct.Layout.html)
    for ``'row'`` and ``'column'``.

    ```python
    from xnano.buffers import Buffer
    from xnano.layout import SizeRule
    from xnano.operations import Layout

    parent = Buffer(width=12, height=3)
    left, right = Buffer(), Buffer()
    parent.attach(left, geometry='inherit')
    parent.attach(right, geometry='inherit')
    parent.update(Layout('row', sizes=[SizeRule.cells(4), SizeRule.fill()], spacing=1))
    assert (left.width, right.x, right.width) == (4, 5, 7)
    ```
    """

    Margin = _CoreMargin
    """
    Horizontal and vertical inset distances, in cells.

    Reach for it to shrink or grow a [`Rectangle`][xnano.layout.Rectangle]. To give a
    placement a margin, set its ``margin`` instead, as in ``canvas.screen.write('hi', margin=1)``.

    ```python
    from xnano.layout import Rectangle
    from xnano.operations import Margin

    area = Rectangle(2, 3, 10, 4)
    assert area.inner_area(Margin(1, 1)) == Rectangle(3, 4, 8, 2)
    assert area.outer(Margin(1, 1)) == Rectangle(1, 2, 12, 6)
    ```
    """

    Move = _CoreMove
    """
    An operation that moves its target relative to its current position in its parent.

    ``x`` moves it right and ``y`` moves it down; negative numbers move it left and up. Use
    [`Place`][xnano.operations.Place] to move it to an absolute position instead.

    ```python
    import xnano
    from xnano.operations import Move

    with xnano.new(width=10, height=3) as canvas:
        label = canvas.screen.write('hi')
        label | Move(2, 1)
        assert (label.x, label.y) == (2, 1)
        label | Move(x=-1)
        assert (label.x, label.y) == (1, 1)
    ```
    """

    Operation = _CoreOperation
    """
    The base every operation shares: an action that changes a buffer, a placement or a canvas.

    Apply an operation with ``|`` or ``update``. Combine operations with ``|`` or ``then`` and
    they run in order; the combination is an operation as well.

    ```python
    import xnano
    from xnano.operations import Fill, Operation, Write

    with xnano.new(width=4, height=1) as canvas:
        both = Fill('.') | Write('hi', x=1)
        assert isinstance(both, Operation)
        canvas.screen | both
        assert canvas.screen.render() == '.hi.'
    ```
    """

    Paste = _CorePaste
    """
    An operation that copies the cells of another buffer into its target.

    The source is copied when the operation is created, so applying it again copies the same
    cells. ``x`` and ``y`` are where the top-left cell of the source lands, and ``mode`` is
    ``'replace'`` or ``'preserve_background'``.

    ```python
    import xnano
    from xnano.buffers import Buffer
    from xnano.operations import Fill, Paste

    source = Buffer('ab', width=2, height=1)
    with xnano.new(width=4, height=1) as canvas:
        canvas.screen | Fill('.') | Paste(source, x=1)
        assert canvas.screen.render() == '.ab.'
    ```
    """

    Place = _CorePlace
    """
    An operation that moves its target to an absolute position in its parent.

    Use [`Move`][xnano.operations.Move] to move it relative to where it is instead.

    ```python
    import xnano
    from xnano.operations import Place

    with xnano.new(width=10, height=3) as canvas:
        label = canvas.screen.write('hi')
        label | Place(5, 2)
        assert (label.x, label.y) == (5, 2)
    ```
    """

    Resize = _CoreResize
    """
    An operation that resizes its target to a width and a height in cells.

    Content is kept where it still fits.

    ```python
    import xnano
    from xnano.operations import Resize

    with xnano.new(width=10, height=3) as canvas:
        label = canvas.screen.write('hi')
        label | Resize(6, 2)
        assert (label.width, label.height) == (6, 2)
    ```
    """

    Write = _CoreWrite
    """
    An operation that writes text into its target at a cell position.

    Text is clipped by display columns, and ``mode`` is ``'replace'`` or
    ``'preserve_background'``. Use [`DynamicWrite`][xnano.operations.DynamicWrite] for the
    form whose text and position can be changed after it is applied.

    ```python
    import xnano
    from xnano.operations import Write

    with xnano.new(width=4, height=2) as canvas:
        canvas.screen | Write('hi', x=1, y=1)
        assert canvas.screen.render().splitlines()[1] == ' hi'
    ```
    """

_CORE_NAMES: Final[dict[str, str]] = {
    'ApplyStyle': 'ApplyStyle',
    'Background': 'Background',
    'Border': 'Border',
    'CancelEffect': 'CancelEffect',
    'Clear': 'Clear',
    'Dissolve': 'Dissolve',
    'Effect': 'Effect',
    'Fade': 'Fade',
    'Fill': 'Fill',
    'Foreground': 'Foreground',
    'Fuzz': 'Fuzz',
    'Glitch': 'Glitch',
    'Layout': 'Layout',
    'Margin': 'Margin',
    'Move': 'Move',
    'Operation': 'Operation',
    'Paste': 'Paste',
    'Place': 'Place',
    'Resize': 'Resize',
    'Write': 'Write',
}
"""The name each operations object has in ``xnano_core``, by the name it has here."""


class ContextualOperation(_core.Operation, Generic[DepsT, StateT]):
    """
    A reusable hook that can be piped onto any canvas or placement.

    Build one with [`hook`][xnano.hooks.hook]. Apply it with ``|``, ``|=`` or ``update``,
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
        def count(context: xnano.Context) -> None:
            counted.append(context.clock.elapsed_seconds)

        with xnano.new(width=16, height=1) as canvas:
            canvas.screen | count
            canvas.clock.step(delta_seconds=1.0)
        assert len(counted) == 2
        ```
    """

    __xnano_operation__ = True

    def __init__(
        self,
        callback: Callable[[Context[DepsT, StateT]], object] | None = None,
        *,
        on: HookTrigger[DepsT, StateT] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: tuple[str, ...] = (),
        requires_deps: bool = False,
        if_running: IfRunning = 'replace',
        steps: Sequence[_core.Operation] = (),
    ) -> None:
        """
        Create a reusable hook. Use [`hook`][xnano.hooks.hook] instead of calling this.

        Args:
            callback: Function called with a [`Context`][xnano.hooks.Context] when the hook
                runs.
            on: When the hook runs: a kind of event, the name of a custom event, or a
                condition.
            every: Interval between runs.
            after: Delay before the one run.
            keys: Key names to react to when ``on='key'``.
            requires_deps: Whether the hook needs the canvas's dependencies.
            if_running: What an ``async def`` hook does when it runs again before its
                previous run has finished.
            steps: Chained operations to apply in sequence.
        """
        super().__init__()
        self._callback = callback
        self._hook_on = on
        self._every = every
        self._after = after
        self._keys = tuple(keys)
        self._requires_deps = requires_deps
        self._if_running: IfRunning = if_running
        self._steps: tuple[_core.Operation, ...] = tuple(steps)

    @property
    def on(self) -> HookTrigger[DepsT, StateT] | None:
        """When the hook runs, as it was given, or ``None`` for every input event."""
        return self._hook_on

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
            if isinstance(step, (ContextualOperation, DynamicOperation)):
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
                [`Placement`][xnano.layout.Placement] or a [`Surface`][xnano_core.Surface].
        """
        if isinstance(target, _core.Surface):
            self.apply_to_surface(target)
            return
        if self._steps:
            from xnano.canvas import Canvas

            # What draws goes on a canvas's screen; what listens attaches to the canvas.
            surface = target.screen if isinstance(target, Canvas) else target
            for step in self._steps:
                if isinstance(step, (ContextualOperation, DynamicOperation)):
                    step.apply_to(
                        cast('Canvas[object, object] | Placement[object, object]', target)
                    )
                else:
                    surface.update(step)
            return
        callback = self._callback
        if callback is None:
            return
        target.hook(
            callback,
            on=self._hook_on,
            every=self._every,
            after=self._after,
            keys=self._keys or None,
            requires_deps=self._requires_deps,
            if_running=self._if_running,
        )


@dataclass
class DynamicFill(DynamicOperation):
    """
    An operation that fills every cell of its target with a character or a
    [`Cell`][xnano_core.Cell].

    The ``cell`` setting is a plain value. It is read every time the operation is applied, and
    assigning it on an applied operation applies the operation again with the new value.

    Attributes:
        cell: The character or cell used to fill the target.

    Examples:
        ```python
        import xnano
        from xnano.operations import DynamicFill

        dots = DynamicFill(cell='.')
        with xnano.new('hi', width=4, height=1) as canvas:
            canvas.screen | dots
            dots.cell = '#'
            assert '#' in canvas.screen.render()
        ```
    """

    customization_kind = 'fill'

    cell: _core.Cell | str = ' '
    """The character or cell used to fill the target."""


@dataclass
class DynamicWrite(DynamicOperation):
    """
    An operation that writes text into the cells of its target.

    Its settings are plain values: text, a position, a style and a blending mode. They are read
    every time the operation is applied, and assigning one on an applied operation applies the
    operation again with the new value. A position does not follow an expression over time: to
    make the text move with an expression, give the expression to a placement
    (``placement.x = ...``) or change ``x`` and ``y`` from a hook.

    Attributes:
        text: Text or styled text to write.
        x: Starting column.
        y: Starting row.
        style: Optional style applied to the written text.
        mode: Write blending mode (``'replace'``, ``'preserve_background'``).

    Examples:
        ```python
        import xnano
        from xnano.operations import DynamicWrite

        label = DynamicWrite(text='ab')
        with xnano.new(width=4, height=1) as canvas:
            canvas.screen | label
            label.text = 'cd'
            assert 'cd' in canvas.screen.render()
        ```
    """

    customization_kind = 'write'

    text: _core.TextContent = ''
    """Text or styled text to write."""

    x: int = 0
    """Starting column."""

    y: int = 0
    """Starting row."""

    style: _core.Style | None = None
    """Optional style applied to the written text."""

    mode: _core.WriteMode = 'replace'
    """Write blending mode (``'replace'``, ``'preserve_background'``)."""


@dataclass
class DynamicLayout(DynamicOperation):
    """
    An operation that arranges the children attached to its target in a row, a column or an
    overlay.

    Its settings are plain values: the arrangement, the size rules, the spacing and the padding.
    They are read every time the operation is applied, and assigning one on an applied operation
    applies the operation again with the new value.

    Attributes:
        arrangement: ``'row'``, ``'column'`` or ``'overlay'``.
        sizes: Size rules for each child along the main axis.
        spacing: Cells between adjacent children.
        padding: Cells inset from the parent's edges.
    """

    customization_kind = 'layout'

    arrangement: Literal['row', 'column', 'overlay'] = 'column'
    """``'row'``, ``'column'`` or ``'overlay'``."""

    sizes: Sequence[_core.SizeRule] = ()
    """Size rules for each child along the main axis."""

    spacing: int = 0
    """Cells between adjacent children."""

    padding: int = 0
    """Cells inset from the parent's edges."""


@dataclass
class DynamicFuzz(DynamicOperation):
    """
    An operation that replaces a percentage of the visible glyphs of its target with noise.

    Its settings are plain values: an intensity and an optional seed. They are read every time
    the operation is applied, and assigning one on an applied operation applies the operation
    again with the new value.

    Attributes:
        intensity: Percentage of glyphs to replace (``0`` to ``100``).
        seed: Optional random seed for repeatable noise.
    """

    customization_kind = 'fuzz'

    intensity: int = 10
    """Percentage of glyphs to replace (``0`` to ``100``)."""

    seed: int | None = None
    """Optional random seed for repeatable noise."""


@dataclass
class DynamicPixels(DynamicOperation):
    """
    An operation that colors pixels from a shader function or from an explicit iterable of
    pixels.

    The shader is called with the column and row of every pixel of the target's pixel grid
    and returns a color, or ``None`` to leave the pixel as it is. The settings are plain values
    and functions. They are read every time the operation is applied, and assigning one on an
    applied operation applies the operation again with the new value.

    Attributes:
        shader: Optional function ``(x, y) -> color`` evaluated across the target's pixel grid.
        pixels: Optional explicit iterable of ``(x, y, (red, green, blue))`` pixels.
        encoding: ``'half_blocks'`` or ``'braille'``.
        clip: Whether out-of-bounds pixels are clipped instead of raising ``IndexError``.
        x: Column offset of the explicit pixels, or ``None``.
        y: Row offset of the explicit pixels, or ``None``.
    """

    customization_kind = 'pixels'

    shader: Callable[[int, int], ColorValue | None] | None = None
    """Optional function ``(x, y) -> color`` evaluated across the target's pixel grid."""

    pixels: Iterable[_core.PixelEntry] | None = None
    """Optional explicit iterable of ``(x, y, (red, green, blue))`` pixels."""

    encoding: PixelEncoding = 'half_blocks'
    """``'half_blocks'`` or ``'braille'``."""

    clip: bool = True
    """Whether out-of-bounds pixels are clipped instead of raising ``IndexError``."""

    x: int | None = None
    """Column offset of the explicit pixels, or ``None``."""

    y: int | None = None
    """Row offset of the explicit pixels, or ``None``."""

    def apply_to_surface(self, surface: _core.Surface) -> None:
        """
        Shade or write the pixels into a core [`Surface`][xnano_core.Surface].

        Args:
            surface: The buffer or region to modify.
        """
        if self.pixels is not None:
            surface.update(
                _core.Pixels(
                    self.pixels,
                    encoding=self.encoding,
                    clip=self.clip,
                    x=self.x,
                    y=self.y,
                )
            )
        if self.shader is not None:
            view = surface.pixels(encoding=self.encoding)
            colored: list[tuple[int, int, RGB]] = []
            for row in range(view.height):
                for column in range(view.width):
                    color = self.shader(column, row)
                    if color is not None:
                        colored.append((column, row, to_rgb(color)))
            view.write(colored)


@dataclass
class DynamicRaster(DynamicOperation):
    """
    An operation that draws a row-major RGBA8 buffer as pixels.

    Its settings are plain values: the bytes, the size of the image, its position, the encoding
    and the mode. They are read every time the operation is applied, and assigning one on an
    applied operation applies the operation again with the new value.

    Attributes:
        rgba: ``width * height * 4`` bytes of RGBA8 pixel data.
        width: Image width in pixels.
        height: Image height in pixels.
        x: Top-left pixel column.
        y: Top-left pixel row.
        encoding: ``'half_blocks'`` or ``'braille'``.
        mode: ``'over'`` or ``'replace'``.
    """

    customization_kind = 'raster'

    rgba: bytes = b''
    """``width * height * 4`` bytes of RGBA8 pixel data."""

    width: int = 0
    """Image width in pixels."""

    height: int = 0
    """Image height in pixels."""

    x: int = 0
    """Top-left pixel column."""

    y: int = 0
    """Top-left pixel row."""

    encoding: PixelEncoding = 'half_blocks'
    """``'half_blocks'`` or ``'braille'``."""

    mode: _core.RasterMode = 'over'
    """``'over'`` or ``'replace'``."""


__all__ = [
    'ApplyStyle',
    'Background',
    'Border',
    'CancelEffect',
    'Clear',
    'ContextualOperation',
    'Dissolve',
    'DynamicFill',
    'DynamicFillSchema',
    'DynamicFuzz',
    'DynamicFuzzSchema',
    'DynamicLayout',
    'DynamicLayoutSchema',
    'DynamicPixels',
    'DynamicPixelsSchema',
    'DynamicRaster',
    'DynamicRasterSchema',
    'DynamicWrite',
    'DynamicWriteSchema',
    'Effect',
    'Fade',
    'Fill',
    'Foreground',
    'Fuzz',
    'Glitch',
    'Layout',
    'Margin',
    'Move',
    'Operation',
    'OperationResult',
    'Paste',
    'Place',
    'Resize',
    'Write',
]


def __getattr__(name: str) -> object:
    """Import an object from ``xnano_core`` the first time it is read, then keep it."""
    core_name = _CORE_NAMES.get(name)
    if core_name is None:
        raise AttributeError(
            f'xnano.operations has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    value = getattr(_core, core_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
