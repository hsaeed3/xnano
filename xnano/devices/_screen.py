"""
xnano.devices._screen

The screen of a terminal: what is written and drawn on it, its look, its size, its cursor and
its title.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Generic, Literal, cast

# The module, not the class: the canvas module imports this one while it loads.
import xnano.canvas as _canvas_module
import xnano_core as _core
from xnano._internal._attributes import refuse_unknown_keywords
from xnano._internal._axes import check_edges
from xnano._runtime._slots import close_slot, open_slot
from xnano._schema._generics import DepsT, StateT
from xnano.effects._registry import apply_effects
from xnano.layout._region import Region
from xnano.styles._owners import _TextModifiers

if TYPE_CHECKING:
    from typing_extensions import Self, Unpack

    from xnano._schema._appearance import ColorValue, Spacing
    from xnano._schema._axes import Axis, Percentage
    from xnano._schema._content import Content
    from xnano._schema._effects import WritableEffectSpecification
    from xnano._schema._generics import WrittenDepsT, WrittenStateT
    from xnano._schema._layout import CanvasLayout, EdgeBehavior
    from xnano._schema._terminal import CanvasSettings
    from xnano.canvas import Canvas
    from xnano.devices._cursor import Cursor
    from xnano.devices._output import Output
    from xnano.effects._properties import WritableEffectProperties
    from xnano.expressions import ParentExpressionScope, RootExpressionScope
    from xnano.layout._placement import Placement
    from xnano.styles._look import Appearance

__all__ = ['Screen']


class Screen(_TextModifiers, Generic[DepsT, StateT]):
    """
    The screen of a terminal: what is written and drawn on it, and how it looks.

    Get it from [`Canvas.screen`][xnano.canvas.Canvas.screen], or from ``context.screen``
    inside a hook. ``write`` puts content on it and returns the
    [`Placement`][xnano.layout.Placement] that holds it; ``region`` reads and writes its
    cells; ``render`` gives the frame as text. Its look (``color``, ``border``, ``padding``,
    ``margin`` and the text modifiers) is the look of the whole canvas. A canvas from ``new()``
    has a screen in memory: everything works the same, and ``render`` shows what it would draw.

    A canvas written into another one has a screen of its own, its area of the outer canvas;
    ``x`` and ``y`` say where that area is, and ``move`` moves it.

    Attributes:
        size: The size of the screen in cells.
        width: The width of the screen in cells.
        height: The height of the screen in cells.
        x: The column of the screen: ``0``, unless its canvas was written into another one.
        y: The row of the screen: ``0``, unless its canvas was written into another one.
        region: The cells of the screen as a [`Region`][xnano.layout.Region].
        cursor: The terminal's [`Cursor`][xnano.devices.Cursor].
        title: The window title last set on this screen.
        window: The size of the whole terminal window in cells, for a canvas on the screen;
            the size of the screen otherwise.
        output: The last frame drawn, and the text printed while the canvas was on the screen.
        core_buffer: The core buffer the screen draws, as large as the screen.
        fx: The visual effects of the whole screen, one method for each effect.
        layout: How the screen places what is written on it.
        edges: What content written on the screen does at the edges of its area.
        parent: Symbolic expressions for the parent container's ``width``, ``height`` and
            ``size``.
        root: Symbolic expressions for the root canvas's ``width``, ``height``, ``size`` and
            ``time``.

    Examples:
        ```python
        import xnano

        with xnano.new(width=12, height=3) as canvas:
            canvas.screen.write('hello', x='center', y='center', bold=True)
            canvas.screen.border = 'rounded'
            assert canvas.screen.render().splitlines()[1].strip() == '│ hello │'
        ```
    """

    _canvas: Canvas[DepsT, StateT]

    def __init__(self, canvas: Canvas[DepsT, StateT]) -> None:
        """
        Create the screen of a canvas. Use ``canvas.screen`` instead of calling this.

        Args:
            canvas: The canvas whose screen this is.
        """
        object.__setattr__(self, '_canvas', canvas)
        self._seal()

    def __repr__(self) -> str:
        size = self._canvas._screen_size
        return f'Screen(width={size.width}, height={size.height})'

    # -- the look, kept by the canvas ----------------------------------------------------

    @property
    def _appearance(self) -> Appearance | None:  # type: ignore[override]
        return self._canvas._appearance

    @_appearance.setter
    def _appearance(self, value: Appearance | None) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        self._canvas._appearance = value

    @property
    def _look_is_dirty(self) -> bool:  # type: ignore[override]
        return self._canvas._look_is_dirty

    @_look_is_dirty.setter
    def _look_is_dirty(self, value: bool) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        self._canvas._look_is_dirty = value

    def _ensure_look(self) -> Appearance:
        return self._canvas._ensure_look()

    def _look_text(self) -> str:
        return self._canvas._look_text()

    def _look_canvas(self) -> Canvas[object, object] | None:
        return self._canvas._look_canvas()

    def _look_size(self) -> tuple[int, int]:
        return self._canvas._look_size()

    def _redraw_look(self) -> None:
        self._canvas._redraw_look()

    def _look_changed(self) -> None:
        self._canvas._look_changed()

    def _flush_look(self) -> None:
        self._canvas._flush_look()

    # -- what is on the screen -----------------------------------------------------------

    @refuse_unknown_keywords
    def write(
        self,
        content: Content | Canvas[WrittenDepsT, WrittenStateT] | None = None,
        /,
        *,
        x: Axis = 'next',
        y: Axis = 'next',
        width: Axis | None = None,
        height: Axis | None = None,
        layer: int = 0,
        lock: bool = False,
        edges: EdgeBehavior | None = None,
        effects: Sequence[WritableEffectSpecification] = (),
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
        Put something on the canvas: text, a widget, a buffer, another canvas or an image.

        On a canvas that runs by itself it appears at once: this only declares it, and the
        canvas's own loop draws it. ``width`` and ``height`` you leave out are taken from the
        content, so ``canvas.screen.write('hello')`` shows five cells of text.

        Content given no position goes on the next line, the way a terminal prints: the first
        write starts at the top-left corner and each one after it starts a new line below the
        lines written before it (``x`` and ``y`` default to ``'next'``). The lines keep up with
        each other, so when a line grows, shrinks or is removed, the lines after it follow. A
        ``y`` you give places the content there instead, outside the lines, so a status line
        at ``y='bottom'`` never moves them; ``x='next'`` (the default) then continues right
        after the content written just before it when that content is on the same row and
        there is room. Change the text later by assigning the placement's
        [`text`][xnano.layout.Placement.text].

        Inside the ``with`` block of a canvas created in this one's block, what is written here
        is placed and clipped within that canvas's area of this one: where it is written, or
        the top-left corner while it is not. Positions such as ``y='center'`` are measured in
        that area, and that canvas's ``edges`` applies there.

        A canvas from [`new`][xnano.new] that is written here becomes part of this one: it
        draws inside the placement, its own clock is set aside and it runs on this canvas's
        time. It may not have been given ``state`` or ``deps``, which belong to the outermost
        canvas. Its audio is not carried over: a musical clock it started and a note it was
        playing stop, and a formula that reads its ``audio.beat`` follows the outer canvas's
        musical clock, which starts at the first beat.

        An image is added as an [`Image`][xnano.Image] (never a file path or a bare
        [`TerminalImage`][xnano_image.TerminalImage]; load one with
        [`load_image`][xnano.load_image]). With neither ``width`` nor ``height`` it keeps
        its own proportions at its own size, shrunk to fit the canvas. With one of them the
        other follows the image's proportions, and with both the image fits inside that box. An
        image sized by a percentage, or by the canvas because you gave no size, is converted
        again when the canvas is resized, unless it is locked. An animated image plays on the
        canvas's clock.

        A box from [`box`][xnano.box] with a relative size (a percentage, a formula or a state
        reference), written with a ``width`` or a ``height``, or written with a look, is drawn
        at the size of its placement, and its look becomes the placement's look, so it is
        drawn again when the canvas is resized. The size given to ``write`` wins over the
        box's own. The look keywords given to ``write`` win over the box's look and the rest
        of the box's look stays, and ``border=False`` leaves out the box's own border, title,
        border style and sides. A box written with a look and no size keeps its own size,
        border included, so the look of the write replaces the look of the box instead of
        surrounding it, and a ``margin`` given to ``write`` surrounds it outside that size,
        a percentage margin being a share of the box. The border of such a box is part of its
        placement, so ``placement.region`` starts inside it. A box written as it is, with no
        size and no look, and any other region, is written as a snapshot of its cells. The
        look given to ``write`` surrounds a region that is not a box, and ``placement.region``
        of a snapshot includes the cells of its border.

        Args:
            content: Text (or a list of lines), a [`Buffer`][xnano_core.Buffer] or widget, a
                canvas from ``new()``, an image, or any
                [`Writable`][xnano.components.Writable]; ``None`` for an empty placement.
            x: The column of the left edge: a number of cells, a percentage string, a word
                (``'left'``, ``'center'``, ``'right'`` or ``'next'``), an expression, or a
                range (``(0, 20)``) that limits how far it may travel. See
                [`Axis`][xnano.layout.Axis].
            y: The row of the top edge, in the same forms (``'top'``, ``'center'``,
                ``'bottom'``, ``'next'``). ``'next'``, the default, is the first row below
                what was written before; see [`FlowPosition`][xnano.layout.FlowPosition].
            width: The width, in the same forms; the content's own width when ``None``.
            height: The height, in the same forms; the content's own height when ``None``.
            layer: Content with a higher layer is drawn over content with a lower one.
            lock: Keep the position and size the content has now, whatever the canvas's
                size does afterwards: percentages, words and formulas are read once.
            edges: What the content does at the edges of its area: ``'clip'``, ``'stop'`` or
                ``'wrap'``; see [`Placement.edges`][xnano.layout.Placement.edges]. Left
                out, it follows what it is written on.
            effects: Effects to start on the placement, as dictionaries with a ``kind``
                key, such as ``[{'kind': 'effect.fade_to', 'foreground': 'red'}]``.
            style: A ready-made [`Style`][xnano.styles.Style] for text. The parameters below
                are applied over it.
            foreground: The text color.
            background: The color behind the text.
            bold: Whether the text is bold.
            dim: Whether the text is dimmed.
            italic: Whether the text is italic.
            underline: Whether the text is underlined.
            blink: Whether the text blinks.
            reverse: Whether foreground and background are swapped.
            hidden: Whether the text is hidden.
            crossed_out: Whether the text is struck through.
            title: A title on the border of a box around the text.
            border: The kind of border for a box around the content, a
                [`BorderKind`][xnano.styles.BorderKind] such as ``'plain'``, ``'rounded'``,
                ``'double'`` or ``'thick'``; ``True`` for ``'plain'`` and ``False`` for none.
                Giving a ``title`` alone draws a plain one.
            border_style: The style of the box's border.
            padding: Space between the border and the text: a number of cells, a float or a
                percentage of the text's size, or a dictionary with ``top``, ``right``,
                ``bottom``, ``left``, ``vertical`` and ``horizontal``. Giving it draws the
                text in a box without a border unless ``border`` or ``title`` is also given.
            margin: Space outside the box, in the same forms.

        Returns:
            A [`Placement`][xnano.layout.Placement] to move, resize, listen on or remove.

        Raises:
            TypeError: The content is a file path, raw bytes, or an operation, style or effect
                (apply those with ``canvas.screen.update(...)`` instead).
            TerminalError: The content is a canvas that cannot be written here.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=4) as canvas:
                box = canvas.screen.write('hello', x='50%', y=1)
                assert box.x == 10
                assert (box.width, box.height) == (5, 1)
                canvas.screen.write(
                    'Ready',
                    x='center',
                    y='bottom',
                    foreground='green',
                    bold=True,
                    border='rounded',
                    title='Status',
                )

            with xnano.new(width=20, height=4) as canvas:
                title = canvas.screen.write('Build 142')
                status = canvas.screen.write('passed', x='center')
                assert (title.y, status.y) == (0, 1)
                title.height = 2
                assert status.y == 2
            ```
        """
        canvas = self._canvas
        canvas._require_open()
        if isinstance(content, Region):
            content._require_drawable('canvas.screen.write()')
            width, height = content._written_size(width, height)
        if edges is not None:
            edges = check_edges(edges)
        area = canvas._area_for_write(content)
        if area is not None:
            placement = area.write(
                content,
                x=x,
                y=y,
                width=width,
                height=height,
                layer=layer,
                lock=lock,
                edges=edges,
                effects=effects,
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
            written = canvas._rendering_writes
            if written is not None:
                written.append(placement)
            return placement  # type: ignore[return-value]
        parent_buffer = canvas._content
        slot: _core.Buffer | None = None
        if canvas._layout != 'overlay':
            slot, width, height = open_slot(
                cast('Canvas[object, object]', canvas),
                content if isinstance(content, _canvas_module.Canvas) else None,
                width,
                height,
            )
            parent_buffer = slot
        try:
            placement = canvas._canvas._place_on(
                parent_buffer,
                content,
                parent_owner=cast('Canvas[object, object]', canvas),
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
        except BaseException:
            if slot is not None:
                close_slot(cast('Canvas[object, object]', canvas), slot)
            raise
        if slot is not None:
            canvas._slots[-1] = (
                cast('Placement[object, object]', placement),
                *canvas._slots[-1][1:],
            )
        if effects:
            apply_effects(cast('Placement[object, object]', placement), effects)
        placement._take_edges(edges, content)
        written = canvas._rendering_writes
        if written is not None:
            written.append(cast('Placement[object, object]', placement))
        return placement

    def new(
        self,
        content: Content | None = None,
        /,
        *,
        width: int | Percentage | str | None = None,
        height: int | Percentage | str | None = None,
        effects: Sequence[WritableEffectSpecification] = (),
        **settings: Unpack[CanvasSettings],
    ) -> Canvas[DepsT, StateT]:
        """
        Create a canvas inside this one and draw it here at once, at the top-left corner.

        This is [`new`][xnano.new] followed by ``canvas.screen.write(child)``: the child's size is
        measured in this canvas (``'50%'`` is half of it, and no size fills it), it runs on
        this canvas's time and hears its input, and it closes with this canvas. Move it with
        [`move`][xnano.devices.Screen.move] and its relatives, or create it with
        [`new`][xnano.new] and write it with ``x`` and ``y`` to place it elsewhere.

        Args:
            content: Something to write into the new canvas at once, such as text.
            width: The width in cells, or a percentage of this canvas such as ``'50%'``.
            height: The height in cells, or a percentage of this canvas.
            effects: Effects to apply to the new canvas, as dictionaries with a ``kind`` key.
            settings: The terminal settings and the new canvas's own look; see
                [`CanvasSettings`][xnano.canvas.CanvasSettings].

        Returns:
            The new [`Canvas`][xnano.canvas.Canvas], already drawn in this one.

        Raises:
            TypeError: An appearance keyword was given with content, or a keyword is unknown.
            ValueError: A size, terminal setting or border kind is out of range.
            TerminalError: This canvas is closed.

        Examples:
            ```python
            import xnano

            with xnano.new(width=12, height=6) as outer:
                panel = outer.screen.new(height='50%', border='plain')
                panel.screen.write('inside')
                assert (panel.screen.width, panel.screen.height) == (10, 1)
                assert outer.screen.render().splitlines()[:3] == [
                    '┌──────────┐',
                    '│inside    │',
                    '└──────────┘',
                ]
            ```
        """
        return self._canvas._new(
            content, width=width, height=height, effects=effects, **settings
        )

    def clear(self) -> None:
        """Erase everything written or drawn directly on the canvas's cells."""
        return self._canvas._clear()

    def update(self, *operations: _core.Operation | _core.Style) -> Self:
        """
        Change the canvas's own cells with operations, styles or effects.

        ``canvas.screen | operation`` does the same. To put content on the canvas, use
        [`write`][xnano.devices.Screen.write] instead.

        Args:
            operations: What to apply, in order: a core operation such as ``Fill`` or
                ``Write``, a style, or an xnano effect or dynamic operation.

        Returns:
            The canvas, so calls chain.

        Examples:
            ```python
            import xnano
            from xnano_core import Fill

            with xnano.new(width=4, height=1) as canvas:
                canvas.screen.update(Fill('.'))
                assert canvas.screen.render() == '....'
                canvas.screen | Fill('#')
                assert canvas.screen.render() == '####'
            ```
        """
        self._canvas._update(*operations)
        return self

    def render(self, *, format: Literal['text', 'ansi'] = 'text') -> str:
        """
        Draw the current frame and return it, without a screen.

        A canvas that was written into another one returns its own cells alone, at its own
        size, as they stand in the outer canvas's current frame.

        Args:
            format: ``'text'`` for the characters alone, ``'ansi'`` for the characters with
                their colors and styles as escape codes.

        Raises:
            ValueError: ``format`` is neither ``'text'`` nor ``'ansi'``.

        Examples:
            ```python
            import xnano

            with xnano.new(width=6, height=2) as canvas:
                canvas.screen.write('hello', y=1)
                assert canvas.screen.render().splitlines() == ['', 'hello']
                assert 'hello' in canvas.screen.render(format='ansi')
            ```
        """
        return self._canvas._render(format=format)

    def local(self, point: _core.Point) -> _core.Point:
        """
        Convert a cell of the screen into a cell of this canvas.

        Args:
            point: A cell in screen coordinates, such as ``context.mouse.position``.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.new(width=10, height=3) as canvas:
                assert canvas.screen.local(Point(4, 1)) == Point(4, 1)
            ```
        """
        return self._canvas._local(point)

    def move(self, x: int = 0, y: int = 0) -> Self:
        """
        Move a canvas that is written into another one by a number of cells along each axis.

        This moves the placement the canvas is drawn in; see
        [`Placement.move`][xnano.layout.Placement.move].

        Args:
            x: Columns to move right; a negative number moves left.
            y: Rows to move down; a negative number moves up.

        Returns:
            The canvas, so calls can chain.

        Raises:
            TerminalError: The canvas is not written into another canvas, so it sits at the
                origin and cannot move.
            TypeError: An amount is not a whole number.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=3) as outer:
                inner = outer.screen.new('box', width=4, height=1)
                inner.screen.move(x=2, y=1)
                assert (inner.screen.x, inner.screen.y) == (2, 1)
                assert outer.screen.render().splitlines()[1] == '  box'
            ```
        """
        self._canvas._move(x, y)
        return self

    def up(self, count: int = 1) -> Self:
        """
        Move a written canvas up by ``count`` rows; see [`move`][xnano.devices.Screen.move].

        Args:
            count: How many rows to move.

        Raises:
            TerminalError: The canvas is not written into another canvas.
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        self._canvas._up(count)
        return self

    def down(self, count: int = 1) -> Self:
        """
        Move a written canvas down by ``count`` rows; see [`move`][xnano.devices.Screen.move].

        Args:
            count: How many rows to move.

        Raises:
            TerminalError: The canvas is not written into another canvas.
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        self._canvas._down(count)
        return self

    def left(self, count: int = 1) -> Self:
        """
        Move a written canvas left by ``count`` columns; see [`move`][xnano.devices.Screen.move].

        Args:
            count: How many columns to move.

        Raises:
            TerminalError: The canvas is not written into another canvas.
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        self._canvas._left(count)
        return self

    def right(self, count: int = 1) -> Self:
        """
        Move a written canvas right by ``count`` columns; see [`move`][xnano.devices.Screen.move].

        Args:
            count: How many columns to move.

        Raises:
            TerminalError: The canvas is not written into another canvas.
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        self._canvas._right(count)
        return self

    @property
    def size(self) -> _core.Size:
        """
        The size of the canvas in cells.

        An axis given no size when the canvas was created follows the content: the canvas is
        as wide as the farthest right edge of what is written on it and as tall as its lowest
        bottom edge.
        """
        return self._canvas._screen_size

    @property
    def width(self) -> int:
        """The width of the canvas in cells."""
        return self._canvas._screen_width

    @property
    def height(self) -> int:
        """The height of the canvas in cells."""
        return self._canvas._screen_height

    @property
    def x(self) -> int:
        """The column of the canvas: ``0``, unless it was written into another canvas."""
        return self._canvas._screen_x

    @property
    def y(self) -> int:
        """The row of the canvas: ``0``, unless it was written into another canvas."""
        return self._canvas._screen_y

    @property
    def region(self) -> Region[int]:
        """
        The cells of the canvas as a [`Region`][xnano.layout.Region]: read and write
        ``canvas.screen.region[x, y]``.

        The default resolution is one cell. ``canvas.screen.region.half_blocks`` addresses two
        pixels per cell and ``canvas.screen.region.braille`` eight dots.

        Examples:
            ```python
            import xnano

            with xnano.new(width=4, height=2) as canvas:
                canvas.screen.region[0, 0] = xnano.Pixel('diamond')
                canvas.screen.region.half_blocks[1, 0] = (255, 0, 0)
                assert canvas.screen.region[0, 0].character == '◆'
                assert canvas.screen.region.half_blocks.height == 4
            ```
        """
        return self._canvas._screen_region

    @property
    def cursor(self) -> Cursor:
        """
        The canvas's [`Cursor`][xnano.devices.Cursor].

        A canvas has exactly one cursor. Set its ``position`` (a cell, or ``None`` to hide
        it), ``shape``, ``is_blinking`` and ``is_visible``, move it with ``up``, ``down``,
        ``left``, ``right`` and ``move``, or ``follow`` a placement. It can be changed from
        any thread, and on the screen the cursor you had before is restored when the canvas
        closes.

        Examples:
            ```python
            import xnano

            with xnano.new(width=10, height=2) as canvas:
                canvas.screen.cursor.position = (3, 0)
                canvas.screen.cursor.shape = 'bar'
                assert canvas.screen.cursor.position.x == 3
            ```
        """
        return self._canvas._screen_cursor

    @property
    def title(self) -> str | None:
        """
        The window title last set on this canvas.

        Assign a single line of printable text to set the title of the window a canvas on the
        screen draws in, or ``None`` to clear it. A canvas without a screen keeps the value
        and shows it when it is opened.
        """
        return self._canvas._screen_title

    @title.setter
    def title(self, value: str | None) -> None:
        self._canvas._screen_title = value

    @property
    def core_buffer(self) -> _core.Buffer:
        """
        The core buffer the canvas draws, as large as the canvas.

        Everything you write is a child of this buffer, and everything drawn directly on the
        canvas is stored in it. A canvas with a border, padding or margin draws them around
        a buffer of its own; this is the buffer inside them.
        """
        return self._canvas._screen_core_buffer

    @property
    def fx(self) -> WritableEffectProperties:
        """
        The visual effects of the canvas itself, one method for each effect.

        ``canvas.screen.fx.fade_to(background='navy')`` starts a fade over the whole canvas at once,
        and ``canvas.screen.fx.clear()`` stops what was started here. A placement has its own
        [`fx`][xnano.layout.Placement.fx], and the sound effects of what the canvas plays are
        [`canvas.speaker.fx`][xnano.devices.Speaker.fx]. See
        [`WritableEffectProperties`][xnano.effects.WritableEffectProperties].

        Examples:
            ```python
            import xnano

            with xnano.new('hello', width=8, height=1) as canvas:
                canvas.screen.fx.dissolve(duration_milliseconds=300)
                assert len(canvas.screen.fx.active) == 1
            ```
        """
        return self._canvas._screen_fx

    @property
    def layout(self) -> CanvasLayout:
        """
        How the canvas places what is written on it, chosen when the canvas is created.

        ``'overlay'`` places every piece on its own over the whole canvas. ``'column'``
        stacks the pieces from top to bottom in the order they are written, and ``'row'``
        from left to right. Each piece then takes a slot: one with a size on the stacking
        axis (``height`` in a column, ``width`` in a row, in cells or as a percentage) gets
        exactly that, and the others share what is left equally. Inside its slot a piece is
        positioned as on any canvas, so ``y='center'`` and ``y='50%'`` are measured in the
        slot. Removing a piece gives its slot back. A canvas created inside the ``with``
        block of a stacking canvas takes a slot only once it is written.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=10, layout='column') as terminal:
                terminal.screen.write('top half', y='center')
                panel = terminal.screen.new(height='50%')
                panel.screen.write('bottom half')
                rows = terminal.screen.render().splitlines()
                assert (rows[2], rows[5]) == ('top half', 'bottom half')
            ```
        """
        return self._canvas._screen_layout

    @property
    def edges(self) -> EdgeBehavior:
        """
        What content written on the canvas does at the edges of its area, unless given its own.

        ``'clip'`` lets it move past the edge, where it is not drawn; ``'stop'`` holds it
        inside its area when it moves; ``'wrap'`` continues text on the next rows of its
        area. A piece written with ``edges=...`` keeps its own; see
        [`Placement.edges`][xnano.layout.Placement.edges].

        Raises:
            ValueError: The value is not ``'clip'``, ``'stop'`` or ``'wrap'``.
        """
        return self._canvas._screen_edges

    @edges.setter
    def edges(self, value: EdgeBehavior) -> None:
        self._canvas._screen_edges = value

    @property
    def parent(self) -> ParentExpressionScope:
        """Symbolic expressions for the parent container's ``width``, ``height`` and ``size``."""
        return self._canvas._screen_parent

    @property
    def root(self) -> RootExpressionScope:
        """Symbolic expressions for the root canvas's ``width``, ``height``, ``size`` and ``time``."""
        return self._canvas._screen_root

    @property
    def output(self) -> Output:
        """The last frame drawn, and the text printed while the canvas was on the screen."""
        return self._canvas._output

    @property
    def window(self) -> _core.Size:
        """
        The size of the whole terminal window in cells, for a canvas on the screen.

        For a terminal opened with a ``height`` it is larger than ``size``, which is the region
        the canvas draws in; for one that takes the whole window the two are equal. A canvas
        from ``new()`` has no window, and this is its ``size``.
        """
        from xnano.terminal import Terminal
        from xnano.terminal._screen import window_size

        if isinstance(self._canvas._canvas, Terminal):
            size = window_size()
            return _core.Size(size.columns, size.lines)
        return self._canvas._screen_size

    def __or__(
        self, other: _core.Operation | _core.Style | Sequence[_core.Operation]
    ) -> Self:
        """Apply an operation, effect or style to the screen with ``screen | operation``."""
        if isinstance(other, (_core.Operation, _core.Style)):
            self.update(other)
        else:
            self.update(*other)
        return self

    def __ior__(
        self, other: _core.Operation | _core.Style | Sequence[_core.Operation]
    ) -> Self:
        return self.__or__(other)
