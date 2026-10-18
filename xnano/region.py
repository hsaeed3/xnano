"""
xnano.region

A rectangle in the grid of a medium: cells on the screen, or beats by semitones on the timeline.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Final,
    Generic,
    Literal,
    cast,
    overload,
)

import xnano_core as _core
from xnano._internal._axes import (
    axis_expression,
    check_point,
    inspect_number,
    size_share,
    to_rgb,
)
from xnano._schema._appearance import RGB, ColorValue, Spacing
from xnano._schema._axes import NumericExpression, Percentage
from xnano._schema._generics import NumberT_co
from xnano._schema._layout import PixelAnchor as PixelAnchor
from xnano._schema._layout import Resolution as Resolution
from xnano.appearance import (
    BorderAppearance,
    Colors,
    MarginAppearance,
    PaddingAppearance,
)
from xnano.appearance._decoration import insets_for, paint_decoration
from xnano.appearance._look import (
    APPEARANCE_NAMES,
    MOST_CELLS,
    Appearance,
    appearance_fields,
    check_border_kind,
)
from xnano.appearance._owners import _Looked
from xnano.art._pixels import Pixel
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from typing_extensions import Unpack
    from xnano_image import TerminalImage

    from xnano._schema._appearance import AppearanceArguments
    from xnano._schema._axes import Axis
    from xnano._schema._content import Content
    from xnano.art._images import Image
    from xnano.canvas import Canvas
    from xnano.context import Context
    from xnano.placement import Placement

__all__ = ['PixelAnchor', 'Region', 'Resolution', 'box', 'write']

_BRAILLE_BITS: Final = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))
_BLANK: Final = _core.Cell(' ')

_TICKS_PER_BEAT: Final = 4
"""A tick is a sixteenth note, so a beat (a quarter note) is four ticks."""

_TIMELINE_RESOLUTIONS: Final = frozenset({'beats', 'ticks', 'milliseconds'})
_SCREEN_VIEWS: Final = frozenset({'cells', 'half_blocks', 'braille'})

_VIEW_APPEARANCE_MESSAGE: Final = (
    'Set canvas.{name} (or placement.{name}) instead of region.{name}: a view of a canvas '
    'or a placement has no appearance of its own. Only a region from xnano.write() or '
    'xnano.box() does.'
)


@dataclass(frozen=True, slots=True)
class _TimelineSpan:
    """
    The beats and the pitches a region on the timeline covers.

    ``tempo_changes`` holds ``(beat, beats per minute)`` pairs in beat order, the first one at
    beat ``0.0``; each tempo holds until the beat of the next pair.
    """

    start_beats: float
    length_beats: float
    lowest_pitch: int
    pitch_count: int
    tempo_changes: tuple[tuple[float, float], ...]

    def seconds_at(self, beat: float) -> float:
        """The seconds from the start of the timeline to ``beat``, through the tempo changes."""
        changes = self.tempo_changes
        seconds = 0.0
        for index, (change_beat, tempo) in enumerate(changes):
            if beat <= change_beat:
                break
            until = changes[index + 1][0] if index + 1 < len(changes) else beat
            seconds += (min(beat, until) - change_beat) * 60.0 / tempo
        return seconds


def _is_real_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_color(value: object) -> bool:
    if isinstance(value, _core.Color):
        return True
    return (
        isinstance(value, tuple)
        and len(value) == 3
        and all(
            isinstance(channel, int) and not isinstance(channel, bool)
            for channel in value
        )
    )


def _plain(color: _core.Color | None) -> ColorValue | None:
    """A cell color as a pixel color: ``None`` where the terminal's own color shows."""
    return None if color is None or color.is_reset else color


def _snapshot(surface: _core.Surface) -> _core.Buffer:
    return _core.Buffer.from_cell_grid(surface.to_cell_grid())


def _check_shade_function(function: object) -> None:
    """Refuse a ``shade`` argument that is not a function of a position."""
    if not callable(function):
        raise TypeError(
            f'shade() takes a function of the position, such as shade(lambda x, y: (x * 10, '
            f'0, 0)), but got {function!r}. Pass a function that returns a color for each '
            f'(x, y), or None to leave the cell alone.'
        )


class Region(_Looked, Generic[NumberT_co]):
    """
    A rectangle in the grid of a medium: cells on the screen, or beats by semitones on the timeline.

    A region **on the screen** is a rectangle of cells that you can read and write, one cell
    or dot at a time. It is either *standalone*, made by [`write`][xnano.write] or
    [`box`][xnano.box], which owns its cells and can be written into a canvas, or a *live
    view* of the cells of a canvas or a placement, from ``canvas.region`` and
    ``placement.region``. Coordinates are region coordinates, ``(0, 0)`` being the top-left
    cell. ``(x, y) in region`` and ``region.local(point)`` use screen cells, the frame of
    ``context.mouse.position``.

    The default resolution is one cell. ``region.half_blocks`` addresses two pixels per cell
    (one above the other) and ``region.braille`` eight dots per cell (two by four, one color
    for the whole cell); ``region.cells`` is the view in whole cells again. Reading gives a
    [`Pixel`][xnano.art.Pixel]; assigning accepts a pixel, a color (the background of a cell,
    the color of a pixel or dot), a ``str`` (text) or, over a slice, anything ``write``
    accepts.

    A standalone region owns ``color``, ``border``, ``padding`` and ``margin`` and draws
    them in its own cells, so its coordinates include them: ``(0, 0)`` of a bordered region
    is the corner of the border. On a live view they belong to the canvas or the placement,
    and the coordinates address the area inside them. A region written into a canvas is a
    snapshot: changing the region afterwards changes nothing on the canvas. The look of a
    ``box`` with a relative size, or written with a width or a height, is the exception:
    its placement draws it again at its own size, so it follows the canvas when the canvas
    is resized. A region made by ``write`` draws its text again whenever its look changes,
    so cells you edited are replaced; edit the cells of a ``box`` instead.

    A region **on the timeline** is a piano roll: ``x`` is the beat it starts on and ``width``
    how many beats it lasts, ``y`` is its lowest pitch as a MIDI number and ``height`` how
    many semitones it spans. It has no cells, so ``region.beats``, ``region.ticks`` (sixteenth
    notes, 4 per beat) and ``region.milliseconds`` (through the tempo) are the views that
    measure it, and reading ``cells``, ``half_blocks``, ``braille``, ``size`` or a cell raises
    a [`TerminalError`][xnano.errors.TerminalError]. The same holds the other way around: a
    region on the screen refuses ``beats``, ``ticks`` and ``milliseconds``.
    ``(beat, pitch) in region`` and ``region.local((beat, pitch))`` use the grid of the region.

    The type parameter says which medium a region is in. A region on the screen is a
    ``Region[int]``: its ``x`` and ``width`` are whole numbers, so ``range(region.width)``
    type-checks. A region on the timeline is a ``Region[float]``: its ``x`` and ``width`` are
    beats, ticks or milliseconds and can be fractions. ``canvas.region``, ``placement.region``,
    [`write`][xnano.write] and [`box`][xnano.box] give a ``Region[int]``; the ``region`` of a
    note, a melody or a sound gives a ``Region[float]``, and so does ``context.region``, which
    is on the screen or on the timeline depending on what the hook is attached to. Annotate
    a parameter as ``Region`` to accept either.

    Attributes:
        width: The width in cells, or in pixels or dots at the other screen resolutions; on
            the timeline, how many beats, ticks or milliseconds it lasts.
        height: The height in cells, or in pixels or dots at the other screen resolutions; on
            the timeline, how many semitones it spans.
        x: The screen column of the left edge; on the timeline, the beat, tick or millisecond
            it starts at.
        y: The screen row of the top edge; on the timeline, the lowest pitch as a MIDI number.
        resolution: The grid the region is measured in: ``'cells'``, ``'half_blocks'`` or
            ``'braille'`` on the screen, ``'beats'``, ``'ticks'`` or ``'milliseconds'`` on
            the timeline.
        size: The width and height of a region on the screen, at its resolution.
        cells: The same region as whole cells.
        braille: The same cells as braille dots.
        half_blocks: The same cells as half-block pixels.
        beats: The same region on the timeline, measured in beats.
        ticks: The same region on the timeline, measured in sixteenth notes.
        milliseconds: The same region on the timeline, measured in milliseconds.
        color: The colors of a standalone region.
        border: The border of a standalone region.
        padding: The padding of a standalone region.
        margin: The margin of a standalone region.

    Examples:
        ```python
        import xnano

        card = xnano.write('hello', border='rounded')
        assert card.render().splitlines()[0] == '╭─────╮'

        with xnano.new(width=8, height=2) as canvas:
            region = canvas.region
            region[0:4, 0:1] = 'abcd'
            region[5, 0] = xnano.Pixel('diamond', foreground='red')
            region[0, 1] = (0, 0, 255)
            assert region[5, 0].character == '◆'
            assert region[1, 0].character == 'b'
            assert (1, 1) in region
            assert (region.size.width, region.size.height) == (8, 2)
            dots = region.braille
            assert (dots.width, dots.height) == (16, 8)
            assert dots.cells.resolution == 'cells'
        ```

        A note, a melody or a sound has a region on the timeline:

        ```python
        import pytest
        import xnano
        from xnano.errors import TerminalError

        region = xnano.note(('C4', 'G4'), beats=2).region
        assert (region.x, region.width, region.y, region.height) == (0.0, 2.0, 60, 8)
        assert region.ticks.width == 8.0
        with pytest.raises(TerminalError):
            region.half_blocks
        ```
    """

    def __init__(
        self,
        buffer: _core.Buffer,
        *,
        owner: Canvas[object, object] | Placement[object, object] | None = None,
        inset: tuple[int, int, int, int] = (0, 0, 0, 0),
        resolution: Resolution = 'cells',
        is_standalone: bool = False,
        look: Appearance | None = None,
        is_text: bool = False,
        timeline: _TimelineSpan | None = None,
    ) -> None:
        """
        Wrap a buffer. Get a region from ``write``, ``box`` or ``canvas.region`` instead.

        Args:
            buffer: The core buffer whose cells the region addresses.
            owner: The canvas or placement a live view belongs to.
            inset: Cells left out on the left, top, right and bottom of the buffer.
            resolution: The grid of the region: ``'cells'``, ``'half_blocks'`` or
                ``'braille'`` on the screen, ``'beats'``, ``'ticks'`` or ``'milliseconds'``
                on the timeline.
            is_standalone: Whether the region owns its buffer and its look.
            look: The look of a standalone region.
            is_text: Whether a standalone region shows the text of its look.
            timeline: The beats and pitches of a region on the timeline. Get that region
                from the ``region`` of a note, a melody or a sound instead.

        Raises:
            TerminalError: ``timeline`` is given with a resolution on the screen, or a
                resolution on the timeline is given without ``timeline``.
        """
        if timeline is None and resolution in _TIMELINE_RESOLUTIONS:
            raise TerminalError(
                f'Region() got the timeline resolution {resolution!r} without a timeline, '
                f'but a region on the timeline needs the beats and pitches it covers. Get '
                f'it from the region of a note, a melody or a sound, or pass a screen '
                f"resolution: 'cells', 'half_blocks' or 'braille'.",
                code='validation.value',
                location='resolution',
                input_value=resolution,
            )
        if timeline is not None and resolution not in _TIMELINE_RESOLUTIONS:
            raise TerminalError(
                f'Region() got a timeline with the screen resolution {resolution!r}, but '
                f'a region on the timeline is measured in beats. Pass resolution='
                f"'beats', 'ticks' or 'milliseconds'.",
                code='validation.value',
                location='resolution',
                input_value=resolution,
            )
        self._buffer = buffer
        self._owner = owner
        self._inset = inset
        self._resolution: Resolution = resolution
        self._is_standalone = is_standalone
        self._is_text = is_text
        self._appearance = look
        self._timeline = timeline
        self._canvas: Canvas[object, object] | None = None
        self._insets_applied: tuple[int, int, int, int] | None = None
        # The width and height a box was made with: whole cells, or the relative size it
        # keeps until it is written.
        self._box_size: (
            tuple[
                int
                | str
                | NumericExpression
                | _core.StateReference[int]
                | _core.StateReference[float],
                int
                | str
                | NumericExpression
                | _core.StateReference[int]
                | _core.StateReference[float],
            ]
            | None
        ) = None
        self._seal()

    @classmethod
    def _from_buffer(cls, buffer: _core.Buffer) -> Region[int]:
        """A standalone region that owns ``buffer`` and has no look."""
        return cast('Region[int]', cls(buffer, is_standalone=True))

    # -- the medium ----------------------------------------------------------------------

    def _require_screen(self, name: str) -> None:
        """Refuse ``name``, the member as a user writes it, on a region on the timeline."""
        if self._timeline is None:
            return
        if name.removeprefix('region.') in _SCREEN_VIEWS:
            subject = f'{name} is a view of a region on the screen'
        else:
            subject = f'{name} needs a region on the screen'
        raise TerminalError(
            f'{subject}, but this region is on the timeline: beats by semitones, from a '
            f'Note, a Melody, a Sound or the context of a playable. On the timeline read '
            f'region.beats, region.ticks or region.milliseconds, and x, y, width and height.'
        )

    def _require_drawable(self, name: str) -> None:
        """Refuse to draw a region on the timeline for ``name``, the call as a user writes it."""
        if self._timeline is None:
            return
        raise TerminalError(
            f'{name} draws the cells of a region on the screen, but this region is on the '
            f'timeline: beats by semitones, from a Note, a Melody, a Sound or the context '
            f'of a playable, and it has no cells. Draw the region of a canvas or a '
            f'placement, or one made by xnano.write() or xnano.box(), or play the note, '
            f'melody or sound with canvas.play().'
        )

    def _require_timeline(self, name: str) -> None:
        """Refuse ``name``, the member as a user writes it, on a region on the screen."""
        if self._timeline is not None:
            return
        raise TerminalError(
            f'{name} is a view of a region on the timeline, but this region is on the '
            f'screen: cells of a canvas, a placement, xnano.write() or xnano.box(). On the '
            f'screen read region.cells, region.half_blocks or region.braille, and x, y, '
            f'width and height.'
        )

    # -- the look (standalone only) ------------------------------------------------------

    def _require_standalone(self, name: str) -> None:
        if not self._is_standalone:
            raise TerminalError(_VIEW_APPEARANCE_MESSAGE.format(name=name))

    @property
    def color(self) -> Colors:  # type: ignore[override]
        """The colors of a standalone region; see [`Colors`][xnano.appearance.Colors]."""
        self._require_screen('region.color')
        self._require_standalone('color')
        return Colors(self)

    @property
    def border(self) -> BorderAppearance:  # type: ignore[override]
        """The border of a standalone region; see [`BorderAppearance`][xnano.appearance.BorderAppearance]."""
        self._require_screen('region.border')
        self._require_standalone('border')
        return BorderAppearance(self)

    @border.setter
    def border(self, value: _core.BorderKind | bool) -> None:
        self._require_screen('region.border')
        self._require_standalone('border')
        BorderAppearance(self)._assign_all(value)

    @property
    def padding(self) -> PaddingAppearance:  # type: ignore[override]
        """The padding of a standalone region; see [`Edges`][xnano.appearance.Edges]."""
        self._require_screen('region.padding')
        self._require_standalone('padding')
        return PaddingAppearance(self)

    @padding.setter
    def padding(self, value: Spacing) -> None:
        self._require_screen('region.padding')
        self._require_standalone('padding')
        PaddingAppearance(self)._assign_all(value)

    @property
    def margin(self) -> MarginAppearance:  # type: ignore[override]
        """The margin of a standalone region; see [`Edges`][xnano.appearance.Edges]."""
        self._require_screen('region.margin')
        self._require_standalone('margin')
        return MarginAppearance(self)

    @margin.setter
    def margin(self, value: Spacing) -> None:
        self._require_screen('region.margin')
        self._require_standalone('margin')
        MarginAppearance(self)._assign_all(value)

    def _look_text(self) -> str:
        return self._buffer.text

    def _look_canvas(self) -> Canvas[object, object] | None:
        return self._canvas

    def _look_size(self) -> tuple[int, int]:
        return (self._buffer.width, self._buffer.height)

    def _redraw_look(self) -> None:
        """Draw the look into the cells of a standalone region."""
        look = self._appearance
        if look is None:
            return
        buffer = self._buffer
        if self._is_text and not look.sides:
            drawn = look.snapshot()
            buffer.width = drawn.width
            buffer.height = drawn.height
            buffer.update(_core.Fill(_BLANK), _core.Paste(drawn, mode='replace'))
            return
        content: _core.Buffer | None = None
        if self._is_text:
            content = look.text_buffer()
            insets = insets_for(look, content.width, content.height)
            buffer.width = content.width + insets.horizontal
            buffer.height = content.height + insets.vertical
        else:
            # A box keeps its outer size, and its content is whatever is inside the ring.
            content = self._inner_cells()
            insets = insets_for(look, buffer.width, buffer.height)
        paint_decoration(buffer, look, insets)
        if content is not None and content.width and content.height:
            buffer.update(
                _core.Paste(content, x=insets.left, y=insets.top, mode='replace')
            )
        if not self._is_text:
            # A box paints its own colors on the cells inside its border and padding.
            inner_width = buffer.width - insets.left - insets.right
            inner_height = buffer.height - insets.top - insets.bottom
            if inner_width > 0 and inner_height > 0:
                inner = _snapshot(
                    buffer[
                        insets.left : insets.left + inner_width,
                        insets.top : insets.top + inner_height,
                    ]
                )
                self._apply_content_colors(look, inner)
                buffer.update(
                    _core.Paste(inner, x=insets.left, y=insets.top, mode='replace')
                )
        self._insets_applied = insets.as_tuple()

    def _inner_cells(self) -> _core.Buffer | None:
        """A copy of the cells inside the border and padding that were drawn, if there are any."""
        insets = self._insets_applied
        if insets is None:
            return None
        left, top, right, bottom = insets
        buffer = self._buffer
        inner_width = max(0, buffer.width - left - right)
        inner_height = max(0, buffer.height - top - bottom)
        if not inner_width or not inner_height:
            return None
        return _snapshot(buffer[left : left + inner_width, top : top + inner_height])

    def _written_size(
        self, width: Axis | None, height: Axis | None
    ) -> tuple[Axis | None, Axis | None]:
        """
        The width and height a write gives this region.

        A box with a relative size, or a box written with a width or a height, takes the
        size of its placement: its own size for an axis the write leaves out. Any other
        region is written at the size it has, so nothing is filled in. A box written with a
        look is given its size when the canvas places it.
        """
        box_size = self._box_size
        if box_size is None:
            return (width, height)
        is_relative = any(not isinstance(size, int) for size in box_size)
        if not is_relative and width is None and height is None:
            return (width, height)
        return (
            cast('Axis', box_size[0]) if width is None else width,
            cast('Axis', box_size[1]) if height is None else height,
        )

    # -- geometry ------------------------------------------------------------------------

    def _surface(self) -> _core.Surface:
        """The cells this region addresses."""
        self._flush_look()
        buffer = self._buffer
        left, top, right, bottom = self._inset
        if not (left or top or right or bottom):
            return buffer
        return buffer[
            left : max(left, buffer.width - right), top : max(top, buffer.height - bottom)
        ]

    def _cell_size(self) -> tuple[int, int]:
        self._flush_look()
        left, top, right, bottom = self._inset
        return (
            max(0, self._buffer.width - left - right),
            max(0, self._buffer.height - top - bottom),
        )

    def _grid_size(self) -> tuple[int, int]:
        """The width and height of a region on the screen, in the grid of its resolution."""
        width, height = self._cell_size()
        if self._resolution == 'braille':
            return (width * 2, height * 4)
        if self._resolution == 'half_blocks':
            return (width, height * 2)
        return (width, height)

    def _screen_origin(self) -> tuple[int, int]:
        """The screen column and row of the top-left cell of a region on the screen."""
        inset_x, inset_y = self._inset[0], self._inset[1]
        try:
            bounds = self._buffer._absolute_bounds
        except Exception:
            return (inset_x, inset_y)
        return (int(bounds.x) + inset_x, int(bounds.y) + inset_y)

    def _timeline_extent(self, span: _TimelineSpan) -> tuple[float, float]:
        """Where a region on the timeline starts and how long it lasts, in its resolution."""
        if self._resolution == 'ticks':
            return (
                span.start_beats * _TICKS_PER_BEAT,
                span.length_beats * _TICKS_PER_BEAT,
            )
        if self._resolution == 'milliseconds':
            start = span.seconds_at(span.start_beats)
            end = span.seconds_at(span.start_beats + span.length_beats)
            return (start * 1000.0, (end - start) * 1000.0)
        return (span.start_beats, span.length_beats)

    @property
    def width(self) -> NumberT_co:
        """
        The width of the region.

        On the screen it is counted in cells, or in pixels or dots at the other resolutions,
        and is a whole number (``int``). On the timeline it is how long the region lasts, in
        beats, ticks or milliseconds (``float``).
        """
        span = self._timeline
        if span is not None:
            return cast('NumberT_co', self._timeline_extent(span)[1])
        return cast('NumberT_co', self._grid_size()[0])

    @property
    def height(self) -> int:
        """
        The height of the region.

        On the screen it is counted in cells, or in pixels or dots at the other resolutions.
        On the timeline it is how many semitones the region spans: 1 for a single note, and
        more for a chord or a melody, at every timeline resolution.
        """
        span = self._timeline
        if span is not None:
            return span.pitch_count
        return self._grid_size()[1]

    @property
    def resolution(self) -> Resolution:
        """
        The grid the region is measured in.

        On the screen it is ``'cells'``, ``'half_blocks'`` (1 by 2 per cell) or ``'braille'``
        (2 by 4). On the timeline it is ``'beats'``, ``'ticks'`` (sixteenth notes, 4 per beat)
        or ``'milliseconds'``.
        """
        return self._resolution

    @property
    def x(self) -> NumberT_co:
        """
        The position of the region's left edge.

        On the screen it is the column, a whole number (``int``), and 0 for a region that is
        not on screen. On the timeline it is the beat, tick or millisecond the region starts
        at (``float``).
        """
        span = self._timeline
        if span is not None:
            return cast('NumberT_co', self._timeline_extent(span)[0])
        return cast('NumberT_co', self._screen_origin()[0])

    @property
    def y(self) -> int:
        """
        The position of the region's top edge.

        On the screen it is the row, and 0 for a region that is not on screen. On the
        timeline it is the lowest pitch of the region as a MIDI number, at every timeline
        resolution; 0 when nothing is played.
        """
        span = self._timeline
        if span is not None:
            return span.lowest_pitch
        return self._screen_origin()[1]

    @property
    def size(self) -> _core.Size:
        """
        The width and height of a region on the screen, at its resolution.

        Raises:
            TerminalError: The region is on the timeline, which has no cells. Read its
                ``width`` and ``height`` instead.
        """
        self._require_screen('region.size')
        width, height = self._grid_size()
        return _core.Size(width, height)

    def __contains__(self, point: object) -> bool:
        """
        Whether a screen cell, or a beat and a pitch on the timeline, is inside the region.

        Args:
            point: On the screen, a ``(x, y)`` pair or a [`Point`][xnano_core.Point] in screen
                cells, such as ``context.mouse.position``. On the timeline, a ``(beat, pitch)``
                pair of numbers in the grid of the region, where the pitch is a MIDI number.
                Anything else is not inside.
        """
        span = self._timeline
        if span is not None:
            if not (
                isinstance(point, tuple)
                and len(point) == 2
                and _is_real_number(point[0])
                and _is_real_number(point[1])
            ):
                return False
            beat, pitch = cast('tuple[float, float]', point)
            origin_x, width = self._timeline_extent(span)
            return (
                origin_x <= beat < origin_x + width
                and span.lowest_pitch <= pitch < span.lowest_pitch + span.pitch_count
            )
        if isinstance(point, _core.Point):
            column, row = point.x, point.y
        elif isinstance(point, tuple) and len(point) == 2:
            column, row = point
        else:
            return False
        width, height = self._cell_size()
        origin_x, origin_y = self._screen_origin()
        return (
            origin_x <= column < origin_x + width and origin_y <= row < origin_y + height
        )

    @overload
    def local(self, point: _core.Point) -> _core.Point: ...
    @overload
    def local(self, point: tuple[float, float]) -> tuple[float, float]: ...
    def local(
        self, point: _core.Point | tuple[float, float]
    ) -> _core.Point | tuple[float, float]:
        """
        Convert a screen cell, or a beat and a pitch, into a position in this region.

        Args:
            point: On the screen, a cell in screen coordinates as a
                [`Point`][xnano_core.Point], such as ``context.mouse.position``. On the
                timeline, a ``(beat, pitch)`` pair of numbers in the grid of the region.

        Returns:
            On the screen, the cell relative to the region's top-left cell. On the timeline,
            the ``(beat, pitch)`` pair relative to the region's start and lowest pitch.

        Raises:
            TerminalError: The point is a tuple for a region on the screen, or a ``Point`` or
                anything but a pair of numbers for a region on the timeline.
        """
        span = self._timeline
        if span is not None:
            if not (
                isinstance(point, tuple)
                and len(point) == 2
                and _is_real_number(point[0])
                and _is_real_number(point[1])
            ):
                raise TerminalError(
                    f'local() takes a (beat, pitch) pair of numbers for a region on the '
                    f'timeline, but got {point!r}. Pass the beat in {self._resolution} and '
                    f'the pitch as a MIDI number, such as region.local((1.5, 62)).',
                    code='validation.type',
                    location='point',
                    input_value=point,
                )
            return (
                point[0] - self._timeline_extent(span)[0],
                point[1] - span.lowest_pitch,
            )
        point = check_point(point)
        origin_x, origin_y = self._screen_origin()
        return _core.Point(point.x - origin_x, point.y - origin_y)

    def resize(self, width: int, height: int) -> None:
        """
        Change the size of the region, in cells.

        On a view of a placement this resizes the placement. A standalone region made by
        [`box`][xnano.box] keeps its cells where they fit, and a box with a relative size
        takes the whole-cell size given here and keeps it. A region made by
        [`write`][xnano.write] is sized by its text, border, padding and margin, so it
        cannot be resized.

        Args:
            width: The new width in cells.
            height: The new height in cells.

        Raises:
            TerminalError: The region is the view of a canvas, whose size follows its screen,
                a slice of another region, or it was made by ``write``, whose size follows
                its text; or it is on the timeline, which has no cells.
            ValueError: A size is below 1 or above 65535.
        """
        self._require_screen('region.resize()')
        _check_cell_counts('resize', width, height)
        if width < 1 or height < 1:
            raise ValueError(
                f'A region is at least 1 by 1 cells, but resize got {width} by {height}. '
                f'Pass whole numbers of cells, 1 or more.'
            )
        owner = self._owner
        if self._is_standalone and self._is_text:
            raise TerminalError(
                'A region made by write() is sized by its text, border, padding and margin, '
                'so resize() cannot change it. Make a region of a size you choose with '
                'xnano.box(width, height), or change the text or the padding.'
            )
        if self._is_standalone:
            self._resize_standalone(width, height)
            if self._box_size is not None:
                self._box_size = (width, height)
            return
        if owner is None or not hasattr(owner, '_set_axis'):
            if owner is None or any(self._inset):
                raise TerminalError(
                    'A slice of a region is a window onto it and cannot be resized. Resize the '
                    'region it was taken from with its resize(width, height), or take a new '
                    'slice.'
                )
            raise TerminalError(
                'The size of a canvas follows its screen or its width and height; set '
                'those instead of resizing its region.'
            )
        left, top, right, bottom = self._inset
        placement = cast('Placement[object, object]', owner)
        extra_width = left + right
        extra_height = top + bottom
        decorated = getattr(placement, '_decorated', None)
        if decorated is not None:
            extra_width += decorated.insets.horizontal
            extra_height += decorated.insets.vertical
        placement.width = width + extra_width
        placement.height = height + extra_height

    def _resize_standalone(self, width: int, height: int) -> None:
        """Resize the cells of a standalone region and draw its border, padding and margin again."""
        buffer = self._buffer
        if self._appearance is None:
            buffer.width = width
            buffer.height = height
            return
        self._flush_look()
        carried: _core.Buffer | None = None
        previous = self._insets_applied
        if previous is not None:
            left, top, right, bottom = previous
            inner_width = max(0, buffer.width - left - right)
            inner_height = max(0, buffer.height - top - bottom)
            if inner_width and inner_height:
                carried = _snapshot(
                    buffer[left : left + inner_width, top : top + inner_height]
                )
        buffer.width = width
        buffer.height = height
        buffer.update(_core.Fill(_BLANK))
        self._insets_applied = None
        self._redraw_look()
        applied = self._insets_applied
        if carried is not None and applied is not None:
            kept_width = min(carried.width, max(0, width - applied[0] - applied[2]))
            kept_height = min(carried.height, max(0, height - applied[1] - applied[3]))
            if kept_width and kept_height:
                if (kept_width, kept_height) != (carried.width, carried.height):
                    carried = _snapshot(carried[0:kept_width, 0:kept_height])
                buffer.update(
                    _core.Paste(carried, x=applied[0], y=applied[1], mode='replace')
                )

    # -- the resolution views ------------------------------------------------------------

    def _view(self, resolution: Resolution) -> Region[NumberT_co]:
        """The same cells, or the same span on the timeline, at another resolution."""
        view: Region[NumberT_co] = Region(
            self._buffer,
            owner=self._owner,
            inset=self._inset,
            resolution=resolution,
            is_standalone=False,
            timeline=self._timeline,
        )
        view._canvas = self._canvas
        if self._is_standalone:
            view._appearance = None
        return view

    @property
    def cells(self) -> Region[int]:
        """
        The same region as whole cells, whatever resolution it was viewed at.

        Raises:
            TerminalError: The region is on the timeline, which has no cells. Read
                ``beats``, ``ticks`` or ``milliseconds`` instead.
        """
        self._require_screen('region.cells')
        return cast('Region[int]', self._view('cells'))

    @property
    def braille(self) -> Region[int]:
        """
        The same cells as braille dots: two columns and four rows per cell.

        A dot is drawn in the color of its cell, so the eight dots of a cell share one color.

        Raises:
            TerminalError: The region is on the timeline, which has no cells. Read
                ``beats``, ``ticks`` or ``milliseconds`` instead.

        Examples:
            ```python
            import xnano

            with xnano.new(width=4, height=2) as canvas:
                dots = canvas.region.braille
                dots[0, 0] = (255, 255, 255)
                assert dots[0, 0].character == '•'
                assert dots[1, 0].character == ' '
            ```
        """
        self._require_screen('region.braille')
        return cast('Region[int]', self._view('braille'))

    @property
    def half_blocks(self) -> Region[int]:
        """
        The same cells as pixels, two to a cell: one above the other.

        Raises:
            TerminalError: The region is on the timeline, which has no cells. Read
                ``beats``, ``ticks`` or ``milliseconds`` instead.
        """
        self._require_screen('region.half_blocks')
        return cast('Region[int]', self._view('half_blocks'))

    @property
    def beats(self) -> Region[float]:
        """
        The same region on the timeline, measured in beats.

        Raises:
            TerminalError: The region is on the screen, which has no beats. Read ``cells``,
                ``half_blocks`` or ``braille`` instead.
        """
        self._require_timeline('region.beats')
        return cast('Region[float]', self._view('beats'))

    @property
    def ticks(self) -> Region[float]:
        """
        The same region on the timeline, measured in ticks: sixteenth notes, 4 to a beat.

        Raises:
            TerminalError: The region is on the screen, which has no beats. Read ``cells``,
                ``half_blocks`` or ``braille`` instead.
        """
        self._require_timeline('region.ticks')
        return cast('Region[float]', self._view('ticks'))

    @property
    def milliseconds(self) -> Region[float]:
        """
        The same region on the timeline, measured in milliseconds through the tempo.

        A tempo that changes inside the region makes its beats different lengths in
        milliseconds, so ``x`` and ``width`` follow the tempo at each beat.

        Raises:
            TerminalError: The region is on the screen, which has no beats. Read ``cells``,
                ``half_blocks`` or ``braille`` instead.
        """
        self._require_timeline('region.milliseconds')
        return cast('Region[float]', self._view('milliseconds'))

    def _pixel_view(self) -> _core.PixelView:
        encoding = 'braille' if self._resolution == 'braille' else 'half_blocks'
        return self._surface().pixels(encoding=encoding)

    # -- reading -------------------------------------------------------------------------

    def _check_point(self, key: object) -> None:
        if isinstance(key, _core.Point):
            raise TypeError(
                'region[...] takes region cells, but this is a screen cell. Convert it '
                'first: region[region.local(point).x, region.local(point).y].'
            )
        if not isinstance(key, tuple) or len(key) != 2:
            raise TypeError(
                f'A region is indexed by (x, y), such as region[3, 1] or region[0:5, 0:2], '
                f'but got {key!r}.'
            )

    def _check_bounds(self, x: object, y: object) -> tuple[int, int]:
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, int)
            or not isinstance(y, int)
        ):
            raise TypeError(
                f'A region coordinate is a whole number or a slice, but got ({x!r}, {y!r}).'
            )
        width, height = self._grid_size()
        if not (0 <= x < width and 0 <= y < height):
            raise IndexError(
                f'The coordinates ({x}, {y}) are outside this region. Region coordinates '
                f"start at (0, 0) in the region's top-left corner: x runs from 0 to "
                f'{width - 1} and y from 0 to {height - 1}. A screen cell, such as '
                f'context.mouse.position, needs region.local(point) first.'
            )
        return x, y

    @overload
    def __getitem__(self, key: tuple[int, int]) -> Pixel: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def __getitem__(self, key: tuple[int | slice, int | slice]) -> Region[int]: ...
    def __getitem__(self, key: tuple[int | slice, int | slice]) -> Pixel | Region[int]:
        """
        Read a cell (a [`Pixel`][xnano.art.Pixel]) or take a part of the region.

        Args:
            key: ``(x, y)`` in region coordinates, or two slices without a step.

        Raises:
            IndexError: A coordinate is outside the region; the message names the valid ranges.
            TypeError: The key is a screen [`Point`][xnano_core.Point] or not a pair.
            ValueError: A slice has a step, or a slice is taken from a pixel resolution.
            TerminalError: The region is on the timeline, which has no cells.
        """
        if self._timeline is not None:  # checked inline: indexing is the hot path
            self._require_screen('region[x, y]')
        if type(key) is tuple and len(key) == 2 and self._resolution == 'cells':
            column, row = key
            if type(column) is int and type(row) is int:
                self._flush_look()
                buffer = self._buffer
                if (
                    not any(self._inset)
                    and 0 <= column < buffer.width
                    and 0 <= row < buffer.height
                ):
                    cell = buffer[column, row]
                    foreground = cell.foreground
                    background = cell.background
                    return Pixel._of(
                        cell.symbol,
                        None if foreground is None or foreground.is_reset else foreground,
                        None if background is None or background.is_reset else background,
                    )
        self._check_point(key)
        column, row = key
        if isinstance(column, slice) or isinstance(row, slice):
            if self._resolution != 'cells':
                raise ValueError(
                    f'A slice of a {self._resolution} region would cut cells in two. '
                    f'Take the slice from the cell region (region[0:5, 0:2]) and then '
                    f'use .{self._resolution}.'
                )
            width, height = self._cell_size()
            first_x, last_x = self._span(column, width, 'x')
            first_y, last_y = self._span(row, height, 'y')
            left, top, right, bottom = self._inset
            view: Region[int] = Region(
                self._buffer,
                owner=self._owner,
                inset=(
                    left + first_x,
                    top + first_y,
                    right + (width - last_x),
                    bottom + (height - last_y),
                ),
            )
            view._canvas = self._canvas
            return view
        column, row = self._check_bounds(column, row)
        surface = self._surface()
        if self._resolution == 'cells':
            cell = surface[column, row]
            return Pixel._of(
                cell.symbol, _plain(cell.foreground), _plain(cell.background)
            )
        if self._resolution == 'half_blocks':
            cell = surface[column, row // 2]
            is_top = row % 2 == 0
            symbol = cell.symbol
            if symbol == '▀':
                color = cell.foreground if is_top else cell.background
            elif symbol == '▄':
                color = cell.background if is_top else cell.foreground
            elif symbol == '█':
                color = cell.foreground
            else:
                color = cell.background
            plain = _plain(color)
            return Pixel._of('█', plain) if plain is not None else Pixel._of(' ')
        cell = surface[column // 2, row // 4]
        code = ord(cell.symbol[0]) - 0x2800 if cell.symbol else -1
        is_set = 0 <= code <= 0xFF and bool(code & _BRAILLE_BITS[row % 4][column % 2])
        return Pixel._of('•', _plain(cell.foreground)) if is_set else Pixel._of(' ')

    @staticmethod
    def _span(index: object, size: int, name: str) -> tuple[int, int]:
        if isinstance(index, slice):
            start, stop, step = index.indices(size)
            if step != 1:
                raise ValueError(
                    f'A region is a rectangle, so a slice of {name} cannot have a step '
                    f'(it was {index.step}). Write region[0:5, 0:2] instead of '
                    f'region[0:5:2, 0:2].'
                )
            return start, max(start, stop)
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError(
                f'A region coordinate is a whole number or a slice, but got {index!r}.'
            )
        if not 0 <= index < size:
            raise IndexError(
                f'The {name} coordinate {index} is outside this region, which has {size} '
                f'cells along {name}. Region coordinates start at 0 in the top-left corner.'
            )
        return index, index + 1

    # -- writing -------------------------------------------------------------------------

    def __setitem__(
        self,
        key: tuple[int | slice, int | slice],
        value: Pixel | _core.Color | tuple[int, int, int] | str | object,
    ) -> None:
        """
        Write a pixel, a color, text or content into a cell or a part of the region.

        * A [`Pixel`][xnano.art.Pixel] writes its character and colors; over a slice it fills it.
        * A [`Color`][xnano_core.Color] or an ``(red, green, blue)`` tuple sets the background
          of a cell (the color of a pixel or dot at the other resolutions). A ``str`` is never
          a color: make one with ``Color('#336699')``.
        * A ``str`` is text, written from the cell and clipped at the slice.
        * Any other content that ``write`` accepts covers a slice.

        Args:
            key: ``(x, y)`` in region coordinates, or two slices without a step.
            value: What to write.

        Raises:
            IndexError: A coordinate is outside the region.
            TypeError: A single cell was given content that needs a slice, a screen
                [`Point`][xnano_core.Point] was used as the key, or text was written at a
                pixel resolution.
            ValueError: A slice has a step.
            TerminalError: The region is on the timeline, which has no cells.
        """
        if self._timeline is not None:  # checked inline: indexing is the hot path
            self._require_screen('region[x, y]')
        if type(key) is tuple and len(key) == 2 and self._resolution == 'cells':
            column, row = key
            if type(column) is int and type(row) is int and type(value) is Pixel:
                self._flush_look()
                buffer = self._buffer
                if (
                    not any(self._inset)
                    and 0 <= column < buffer.width
                    and 0 <= row < buffer.height
                ):
                    buffer[column, row] = value.cell()
                    return
        self._check_point(key)
        column, row = key
        if isinstance(column, int) and isinstance(row, int):
            x, y = self._check_bounds(column, row)
            self._set_cell(x, y, value)
            return
        width, height = self._grid_size()
        first_x, last_x = self._span(column, width, 'x')
        first_y, last_y = self._span(row, height, 'y')
        if last_x <= first_x or last_y <= first_y:
            return
        self._set_block(first_x, last_x, first_y, last_y, value)

    def _set_cell(self, x: int, y: int, value: object) -> None:
        resolution = self._resolution
        if isinstance(value, Pixel):
            if resolution == 'cells':
                self._surface()[x, y] = value.cell()
                return
            color = value.foreground if value.foreground is not None else value.background
            if color is not None:
                self._pixel_view().write([(x, y, to_rgb(color))])
            return
        if _is_color(value):
            if resolution == 'cells':
                self._surface().set_background_colors(
                    [cast('ColorValue', value)], width=1, x=x, y=y
                )
            else:
                self._pixel_view().write([(x, y, to_rgb(cast('ColorValue', value)))])
            return
        if isinstance(value, str):
            if resolution != 'cells':
                raise TypeError(
                    f'Text is written at cell resolution, but this region is '
                    f'{resolution}. Write the text into the cell region instead.'
                )
            self._surface().write(value, x=x, y=y)
            return
        raise TypeError(
            'A single cell takes a str, a color or a Pixel. To place other content over '
            'an area, index with two slices, such as region[0:5, 0:2].'
        )

    def _set_block(
        self, first_x: int, last_x: int, first_y: int, last_y: int, value: object
    ) -> None:
        resolution = self._resolution
        if resolution != 'cells':
            if isinstance(value, Pixel):
                color = (
                    value.foreground if value.foreground is not None else value.background
                )
                if color is None:
                    return
            elif _is_color(value):
                color = cast('ColorValue', value)
            else:
                raise TypeError(
                    f'A {resolution} region takes a color or a Pixel, but got '
                    f'{type(value).__name__}. Write text and content into the cell region.'
                )
            channels = to_rgb(color)
            self._pixel_view().write(
                (x, y, channels)
                for y in range(first_y, last_y)
                for x in range(first_x, last_x)
            )
            return
        surface = self._surface()
        part = surface[first_x:last_x, first_y:last_y]
        if isinstance(value, Pixel):
            part.fill(value.cell())
        elif _is_color(value):
            part.update(_core.Background(cast('ColorValue', value)))
        elif isinstance(value, str):
            part.update(_core.Write(value))
        else:
            self._cover(first_x, last_x, first_y, last_y, value)

    def _cover(
        self, first_x: int, last_x: int, first_y: int, last_y: int, value: object
    ) -> None:
        owner = self._owner
        if owner is not None and not self._is_standalone:
            left, top, _, _ = self._inset
            cast('Placement[object, object]', owner).write(
                cast('Content', value),
                x=left + first_x,
                y=top + first_y,
                width=last_x - first_x,
                height=last_y - first_y,
            )
            return
        from xnano._internal._content import content_buffer

        content, _ = content_buffer(cast('Content', value))
        copy = content.copy()
        copy.width = last_x - first_x
        copy.height = last_y - first_y
        self._surface().update(_core.Paste(copy, x=first_x, y=first_y, mode='replace'))

    # -- drawing -------------------------------------------------------------------------

    def shade(self, function: Callable[[int, int], ColorValue | None]) -> None:
        """
        Color every cell, pixel or dot from a function of its position, in one write.

        At the default resolution the function is called for each cell and the result is
        the cell's background; ``region.half_blocks.shade`` and ``region.braille.shade`` call
        it for each pixel or dot.

        Args:
            function: Called with ``(x, y)`` in region coordinates; return the color, or
                ``None`` to leave the cell alone.

        Raises:
            TerminalError: The region is on the timeline, which has no cells.

        Examples:
            ```python
            import xnano

            with xnano.new(width=4, height=2) as canvas:
                canvas.region.shade(lambda x, y: (x * 60, y * 60, 0) if x < 3 else None)
                assert canvas.region[2, 1].background.to_rgb() == (120, 60, 0)
                canvas.region.half_blocks.shade(lambda x, y: (0, y * 30, 0))
                assert canvas.region.half_blocks[0, 3].foreground is not None
            ```
        """
        self._require_screen('region.shade()')
        _check_shade_function(function)
        if self._resolution == 'cells':
            width, height = self._cell_size()
            if width == 0 or height == 0:
                return
            colors = [
                function(column, row) for row in range(height) for column in range(width)
            ]
            self._surface().set_background_colors(colors, width=width)
            return
        view = self._pixel_view()
        colored: list[tuple[int, int, RGB]] = []
        for row in range(view.height):
            for column in range(view.width):
                color = function(column, row)
                if color is not None:
                    colored.append((column, row, to_rgb(color)))
        view.write(colored)

    def _shade_foreground(
        self, function: Callable[[int, int], ColorValue | None]
    ) -> None:
        """Color the text of every cell from a function of its position, in one write."""
        _check_shade_function(function)
        width, height = self._cell_size()
        if width == 0 or height == 0:
            return
        colors = [
            function(column, row) for row in range(height) for column in range(width)
        ]
        self._surface().set_foreground_colors(colors, width=width)

    def draw_color_bytes(
        self,
        data: bytes,
        *,
        width: int,
        height: int,
        x: int = 0,
        y: int = 0,
        mode: _core.RasterMode = 'over',
    ) -> None:
        """
        Draw a row-major RGBA image with its top-left pixel at ``(x, y)``.

        At the default resolution the image is drawn with half-block pixels.

        Args:
            data: ``width * height * 4`` bytes of red, green, blue and alpha.
            width: The image width in pixels.
            height: The image height in pixels.
            x: The pixel column of the image's left edge.
            y: The pixel row of the image's top edge.
            mode: ``'over'`` blends by alpha; ``'replace'`` overwrites.

        Raises:
            TerminalError: The region is on the timeline, which has no cells.
        """
        self._require_screen('region.draw_color_bytes()')
        self._pixel_view().draw_rgba(
            data, width=width, height=height, x=x, y=y, mode=mode
        )

    def draw_image(
        self,
        image: Image | TerminalImage,
        *,
        x: int = 0,
        y: int = 0,
        mode: _core.RasterMode = 'over',
        frame_index: int = 0,
    ) -> None:
        """
        Draw an image with its top-left pixel at ``(x, y)``.

        Pixels outside the region are skipped, so drawing a large image at a negative ``x``
        and ``y`` scrolls it. At the default resolution the image is drawn with half-block
        pixels.

        Args:
            image: An [`Image`][xnano.Image] or a ``TerminalImage`` from ``xnano_image``. It
                needs the optional ``xnano-image`` package.
            x: The pixel column of the image's left edge. May be negative.
            y: The pixel row of the image's top edge. May be negative.
            mode: ``'over'`` blends by alpha; ``'replace'`` overwrites.
            frame_index: Which frame of an animated image to draw.

        Raises:
            TerminalError: The region is on the timeline, which has no cells.
        """
        self._require_screen('region.draw_image()')
        from xnano.art._images import Image

        picture = image.decoded if isinstance(image, Image) else image
        if not hasattr(picture, 'to_rgba'):
            raise TypeError(
                f'draw_image() takes an xnano.Image or a TerminalImage, but got '
                f'{image!r}. Load one with xnano.load_image(path) first.'
            )
        self.draw_color_bytes(
            picture.to_rgba(frame_index),
            width=picture.width,
            height=picture.height,
            x=x,
            y=y,
            mode=mode,
        )

    def cell_for_pixel(self, x: int, y: int) -> tuple[int, int]:
        """
        Return the cell that holds a pixel or dot.

        Args:
            x: The pixel or dot column.
            y: The pixel or dot row.

        Raises:
            TerminalError: The region is on the timeline, which has no cells.
        """
        self._require_screen('region.cell_for_pixel()')
        if self._resolution == 'cells':
            return (x, y)
        return self._pixel_view().cell_at(x, y)

    def pixel_for_cell(
        self, x: int, y: int, *, anchor: PixelAnchor = 'center'
    ) -> tuple[int, int]:
        """
        Return the pixel or dot at an anchor of a cell.

        The mouse reports cells; this picks one pixel of the cell the pointer is over.

        Args:
            x: The cell column.
            y: The cell row.
            anchor: Which pixel of the cell to return.

        Raises:
            TerminalError: The region is on the timeline, which has no cells.
        """
        self._require_screen('region.pixel_for_cell()')
        if self._resolution == 'cells':
            return (x, y)
        return self._pixel_view().pixel_at(x, y, anchor=anchor)

    def copy(self) -> Region[int]:
        """
        Return a standalone region with a copy of these cells and, for one, its look.

        Raises:
            TerminalError: The region is on the timeline, which has no cells.
        """
        self._require_screen('region.copy()')
        copy: Region[int] = Region(_snapshot(self._surface()), is_standalone=True)
        if self._is_standalone and self._appearance is not None:
            import dataclasses

            copy._appearance = dataclasses.replace(
                self._appearance, sides=dict(self._appearance.sides)
            )
            copy._is_text = self._is_text
            copy._insets_applied = self._insets_applied
            copy._box_size = self._box_size
        return copy

    def render(self, *, format: Literal['text', 'ansi'] = 'text') -> str:
        """
        Draw the region to a string.

        Args:
            format: ``'text'`` for the characters only, ``'ansi'`` with colors and styles.

        Raises:
            TerminalError: The region is on the timeline, which has no cells.

        Examples:
            ```python
            import xnano

            assert xnano.write('hi', padding=1).render().splitlines() == ['', ' hi']
            ```
        """
        self._require_screen('region.render()')
        return _snapshot(self._surface()).render(format=format)

    def __str__(self) -> str:
        """
        Return the characters of a region on the screen, so ``print(region)`` shows it.

        A region on the timeline has no characters, so ``str`` of it is its ``repr``.
        """
        if self._timeline is not None:
            return repr(self)
        return self.render()

    def __xnano_render__(self, context: Context | None = None) -> _core.Buffer:
        """Return the buffer that shows the region: its own, or a copy for a view."""
        self._require_screen('region.__xnano_render__()')
        if self._is_standalone:
            self._flush_look()
            return self._buffer
        return _snapshot(self._surface())

    def __repr__(self) -> str:
        if self._timeline is not None:
            return (
                f'Region(timeline, x={self.x!r}, width={self.width!r}, y={self.y}, '
                f'height={self.height}, resolution={self._resolution!r})'
            )
        kind = 'standalone' if self._is_standalone else 'view'
        return (
            f'Region({kind}, width={self.width}, height={self.height}, '
            f'resolution={self._resolution!r})'
        )


def _timeline_region(
    *,
    start_beats: float,
    length_beats: float,
    pitches: Iterable[int],
    tempo_changes: tuple[tuple[float, float], ...],
) -> Region[float]:
    """
    A region on the timeline that starts at a beat, lasts some beats and spans some pitches.

    The region covers every pitch from the lowest of ``pitches`` to the highest, so a chord
    spans several semitones. Without pitches (a melody of rests, or nothing played yet) it
    starts at pitch 0 and spans none. ``tempo_changes`` are ``(beat, beats per minute)`` pairs
    in beat order, the first at beat ``0.0``.

    Raises:
        ValueError: ``tempo_changes`` is empty, its first change is not at beat ``0.0``, or
            a tempo is not above 0 beats per minute.
    """
    if not tempo_changes:
        raise ValueError(
            'A timeline region needs the starting tempo as its first tempo change, but '
            'tempo_changes is empty. Pass at least ((0.0, beats_per_minute),).'
        )
    first_beat = tempo_changes[0][0]
    if first_beat != 0.0:
        raise ValueError(
            f'The first tempo change of a timeline region is the starting tempo, so it is '
            f'at beat 0.0, but it is at beat {first_beat!r}. Start tempo_changes with '
            f'(0.0, beats_per_minute).'
        )
    for beat, tempo in tempo_changes:
        if not tempo > 0:
            raise ValueError(
                f'Every tempo of a timeline region is above 0 beats per minute, but the '
                f'tempo at beat {beat!r} is {tempo!r}. Pass a tempo such as 120.0.'
            )
    played = list(pitches)
    span = _TimelineSpan(
        start_beats=float(start_beats),
        length_beats=float(length_beats),
        lowest_pitch=min(played) if played else 0,
        pitch_count=max(played) - min(played) + 1 if played else 0,
        tempo_changes=tempo_changes,
    )
    # A timeline region has no cells: this placeholder only keeps the buffer typed, and every
    # screen member refuses the region before it reaches the buffer.
    return Region(_core.Buffer(width=1, height=1), resolution='beats', timeline=span)


_PLACEMENT_NAMES: Final = frozenset(
    {'x', 'y', 'width', 'height', 'layer', 'lock', 'effects'}
)


def _check_cell_counts(function_name: str, width: object, height: object) -> None:
    """Raise a ``TypeError`` that says what to pass when a size is not a whole number."""
    for name, value in (('width', width), ('height', height)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                f'{function_name}() takes the {name} as a whole number of cells, but got '
                f'{value!r}. Pass a number such as 4.'
            )
        if value > MOST_CELLS:
            raise ValueError(
                f'{function_name}() takes the {name} as at most {MOST_CELLS} cells, but got '
                f'{value!r}. Pass a number such as 40.'
            )


def _standalone_look(
    function_name: str, text: str, appearance: dict[str, object]
) -> Appearance:
    unknown = sorted(set(appearance) - APPEARANCE_NAMES)
    if unknown:
        hint = ''
        if unknown[0] in _PLACEMENT_NAMES:
            examples = {
                'lock': 'True',
                'effects': "[{'kind': 'effect.fade_to', 'foreground': 'red'}]",
            }
            hint = (
                f' Position it when you write it on a canvas: '
                f'canvas.write(region, {unknown[0]}={examples.get(unknown[0], "1")}).'
            )
        raise TypeError(
            f'{function_name}() has no setting called {unknown[0]!r}. The look of a region '
            f'is {", ".join(sorted(APPEARANCE_NAMES))}.{hint}'
        )
    settings = appearance_fields(appearance)
    check_border_kind(settings.get('border'))
    border = settings.get('border')
    if border is True:
        border = 'plain'
    elif border is False:
        border = None
    settings['border'] = border
    return Appearance(text=text, **cast('dict[str, object]', settings))  # type: ignore[arg-type]


def write(text: str, /, **appearance: Unpack[AppearanceArguments]) -> Region[int]:
    """
    Build a standalone region from text (does not draw).

    The region is sized to the text and is a value that you write into a canvas. It owns its
    cells. Write it into a canvas with ``canvas.write(region)``, print it
    with [`render`][xnano.region.Region.render], or change its look afterwards with
    ``region.border`` and its siblings.

    Args:
        text: The text, line by line.
        appearance: The look of the text: colors, text modifiers, ``border``, ``title``,
            ``padding`` and ``margin``; see [`AppearanceArguments`][xnano.types.AppearanceArguments].

    Raises:
        TypeError: ``text`` is not a string.

    Examples:
        ```python
        import xnano

        card = xnano.write('hello', border='rounded', padding={'horizontal': 1})
        assert card.render().splitlines()[1] == '│ hello │'
        card.border = False
        assert card.render().strip() == 'hello'
        ```
    """
    if not isinstance(text, str):
        raise TypeError(
            f'xnano.write() takes text, but got {text!r}. To show other content, create a '
            f'canvas with xnano.new() and call canvas.write(content).'
        )
    look = _standalone_look('write', text, cast('dict[str, object]', appearance))
    region: Region[int] = Region(
        _core.Buffer(width=1, height=1), is_standalone=True, look=look, is_text=True
    )
    region._redraw_look()
    return region


def _measuring_space() -> tuple[int, int]:
    """The width and height a relative size of a box is measured against."""
    # Imported here because the canvas and the terminal import this module.
    from xnano.canvas import active
    from xnano.terminal._screen import window_size

    canvas = active(is_required=False)
    if canvas is not None:
        return (canvas.width, canvas.height)
    window = window_size()
    return (window.columns, window.lines)


def _box_formula(axis: Literal['width', 'height']) -> str:
    """A formula of the canvas that sizes ``axis``, for the messages that refuse a size."""
    return 'ParentWidth - 4' if axis == 'width' else 'ParentHeight - 4'


def _box_forms(axis: Literal['width', 'height']) -> str:
    """The ways to give one size of a box, for the messages that refuse a size."""
    return (
        f"a whole number of cells such as 20, a share of the canvas such as '50%', a "
        f'formula such as {_box_formula(axis)}, or a reference to the canvas state from '
        f'canvas.state_reference()'
    )


def _is_relative_size(value: object) -> bool:
    """Whether a size of a box is measured against a space, not given in whole cells."""
    return isinstance(value, (str, _core.NumericValue, _core.StateReference))


def _box_cells(
    value: object, axis: Literal['width', 'height'], space: tuple[int, int]
) -> int:
    """
    Return the cells of one size of ``xnano.box()``, measured against ``space``.

    Raises:
        TerminalError: The size is a whole number of cells outside 1 to 65535, is not a
            whole number of cells, a share of the space such as ``'50%'``, a formula or a
            state reference, is a share of 0% or less, or is a formula that reads the clock
            or input that has not arrived. A relative size that measures outside 1 to 65535
            cells is held to that range instead of refused.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        if value < 1 or value > MOST_CELLS:
            raise TerminalError(
                f'xnano.box() takes the {axis} as 1 to {MOST_CELLS} whole cells, but got '
                f'{value!r}. Pass a size in that range, a share of the canvas such as '
                f"'50%', or a formula such as {_box_formula(axis)}.",
                code='validation.bounds',
                location=axis,
                input_value=value,
            )
        return value
    if isinstance(value, str):
        value = value.strip()
        share = size_share(value)
        if share is None:
            raise TerminalError(
                f'xnano.box() takes the {axis} as {_box_forms(axis)}, but got {value!r}. '
                f'Text that is not a percentage, such as a word that places a box, does not '
                f'size it; pass one of those forms.',
                code='validation.value',
                location=axis,
                input_value=value,
            )
        if share <= 0:
            raise TerminalError(
                f'xnano.box() takes the {axis} as a share of the canvas above 0%, but got '
                f"{value!r}. Pass a share such as '50%', or a number of cells such as 20.",
                code='validation.bounds',
                location=axis,
                input_value=value,
            )
    elif not _is_relative_size(value):
        raise TerminalError(
            f'xnano.box() takes the {axis} as {_box_forms(axis)}, but got {value!r}. A '
            f'decimal number or a boolean is not a count of cells and a range is a limit, '
            f'not a size, so pass one of those forms.',
            code='validation.type',
            location=axis,
            input_value=value,
        )
    converted = axis_expression(cast('Axis', value), axis)
    parent = _core.Buffer(width=space[0], height=space[1])
    child = _core.Buffer(width=1, height=1)
    parent.attach(child)
    try:
        cells = inspect_number(child, cast('NumericExpression', converted))
    except (_core.RuntimeRequiredError, TypeError) as error:
        raise TerminalError(
            f'xnano.box() cannot size the {axis} with {value!r}, because that formula reads '
            f'the clock or input that has not arrived, so it has no value before '
            f'the box is written. Pass {_box_forms(axis)}, or write the box with '
            f'canvas.write(box, {axis}=formula).',
            code='validation.value',
            location=axis,
            input_value=value,
        ) from error
    return max(1, min(MOST_CELLS, int(cells + 0.5)))


def box(
    width: int
    | Percentage
    | str
    | NumericExpression
    | _core.StateReference[int]
    | _core.StateReference[float],
    height: int
    | Percentage
    | str
    | NumericExpression
    | _core.StateReference[int]
    | _core.StateReference[float],
    /,
    **appearance: Unpack[AppearanceArguments],
) -> Region[int]:
    """
    Build an empty standalone rectangle of cells (does not draw).

    The region is a value that you write into a canvas. It has no border unless you pass
    ``border``: ``'plain'`` or another kind, or ``True`` for ``'plain'``. A ``background``
    colors every cell of the box. A box with a relative size is drawn at the size of its
    placement when it is written, and again whenever the canvas is resized.

    The look given to ``canvas.write(box, ...)`` is laid over the look of the box: a color,
    border, title or padding that the write names wins, and the rest stays as the box has
    it. ``border=False`` leaves out the border of the box, with its title, border style and
    sides. A box written with a look keeps its size, border included, so the look of the
    write replaces the look of the box instead of surrounding it, and a ``margin`` given to
    the write is space around that size.

    Args:
        width: The width in cells, border included: a whole number, a percentage such as
            ``'50%'``, a formula such as ``ParentWidth - 4`` or a reference to the canvas
            state from ``canvas.state_reference()``. A relative size (every form but a whole
            number) is measured where the box is written, like
            ``canvas.write(..., width='50%')``, and until then against the active canvas or,
            with none, the terminal window. Until the box is written, a relative size that
            measures outside 1 to 65535 cells is held to that range.
        height: The height in cells, border included, in the same forms as ``width``.
        appearance: The look of the box: colors, text modifiers, ``border``, ``title``,
            ``padding`` and ``margin``; see [`AppearanceArguments`][xnano.types.AppearanceArguments].
            When the placement of a box draws its look, its border is on the placement and
            ``placement.region`` addresses the cells inside the border and padding. That is
            the case for a relative box, a box written with a width or height, and a box
            written with a look. A whole-number box written as it is is a snapshot whose
            border is part of its cells, so ``placement.region`` includes the border.

    Raises:
        TerminalError: A size is not a whole number of cells, a percentage, a formula or a
            state reference; a whole number is outside 1 to 65535; a share is 0% or less; or a
            formula reads the clock or input that has not arrived. A relative size that
            measures outside 1 to 65535 cells is held to that range, not refused.

    Examples:
        ```python
        import xnano

        assert xnano.box(5, 3).render().strip() == ''
        frame = xnano.box(5, 3, border='plain')
        assert frame.render().splitlines() == ['┌───┐', '│   │', '└───┘']
        with xnano.new(width=80, height=4) as canvas:
            half = xnano.box('50%', 3)
            assert half.width == 40
            placement = canvas.write(xnano.box('50%', 3, border='plain'))
            assert placement.width == 40
            card = canvas.write(xnano.box(6, 3, border='plain'), border=False)
            assert (card.width, card.height) == (6, 3)
        ```
    """
    space = (0, 0)
    if _is_relative_size(width) or _is_relative_size(height):
        space = _measuring_space()
    cells_wide = _box_cells(width, 'width', space)
    cells_high = _box_cells(height, 'height', space)
    look = _standalone_look('box', '', cast('dict[str, object]', appearance))
    region: Region[int] = Region(
        _core.Buffer(width=cells_wide, height=cells_high),
        is_standalone=True,
        look=look,
        is_text=False,
    )
    region._box_size = (
        width.strip() if isinstance(width, str) else width,
        height.strip() if isinstance(height, str) else height,
    )
    region._redraw_look()
    return region
