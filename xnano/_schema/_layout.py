"""
xnano._schema._layout

The aliases for how a canvas places content, what content does at an edge, how effects ease and
move, how pixels are encoded and anchored, the pixel presets, and the resolutions of a region.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

CanvasLayout: TypeAlias = Literal['overlay', 'column', 'row']
"""
How a canvas places what is written on it.

``'overlay'`` places every piece on its own, over the whole canvas. ``'column'`` stacks the
pieces from top to bottom in the order they are written, and ``'row'`` from left to right.
"""

EdgeBehavior: TypeAlias = Literal['clip', 'stop', 'wrap']
"""
What content does at the edges of its area.

``'clip'`` lets it go past the edge, where it is not drawn. ``'stop'`` holds it inside the
area when it moves. ``'wrap'`` continues text on the next rows of the area.
"""

Interpolation: TypeAlias = Literal[
    'linear',
    'back_in',
    'back_out',
    'back_in_out',
    'bounce_in',
    'bounce_out',
    'bounce_in_out',
    'circ_in',
    'circ_out',
    'circ_in_out',
    'cubic_in',
    'cubic_out',
    'cubic_in_out',
    'elastic_in',
    'elastic_out',
    'elastic_in_out',
    'expo_in',
    'expo_out',
    'expo_in_out',
    'quad_in',
    'quad_out',
    'quad_in_out',
    'quart_in',
    'quart_out',
    'quart_in_out',
    'quint_in',
    'quint_out',
    'quint_in_out',
    'sine_in',
    'sine_out',
    'sine_in_out',
    'smooth_step',
    'spring',
    'reverse',
    'ease_in',
]
"""
How an effect eases between its start and end: ``'linear'``, or a curve such as
``'quad_in_out'`` or ``'bounce_out'``. ``'ease_in'`` is ``'quad_in'``.
"""

MotionDirection: TypeAlias = Literal[
    'left_to_right', 'right_to_left', 'up_to_down', 'down_to_up'
]
"""The direction a sweep, slide or stretch effect moves in."""

PixelEncoding: TypeAlias = Literal['half_blocks', 'braille']
"""``'half_blocks'``: one column and two rows of pixels per cell. ``'braille'``: two by four."""

Anchor: TypeAlias = tuple[int, int]
"""
The ``(x, y)`` pixel inside an [`Art`][xnano.art.Art] that sits at the art's ``(x, y)``.

``anchor=(3, 8)`` makes ``(x, y)`` the place a character's feet touch; ``(0, 0)`` is the top-left
pixel.
"""

Resolution: TypeAlias = Literal[
    'cells', 'half_blocks', 'braille', 'beats', 'ticks', 'milliseconds'
]
"""
The grid a [`Region`][xnano.region.Region] is measured in.

The first three are grids on the screen: ``'cells'`` measures a region in terminal cells,
``'half_blocks'`` in pixels, one by two per cell, and ``'braille'`` in dots, two by four per
cell.

The last three are grids on the timeline: ``'beats'`` measures it in beats, ``'ticks'`` in
sixteenth notes (4 per beat) and ``'milliseconds'`` in thousandths of a second, which follows
the tempo. In every timeline grid ``y`` is the lowest pitch of the region as a MIDI number and
``height`` is how many semitones it spans.
"""

PixelAnchor: TypeAlias = Literal['top_left', 'center', 'bottom_right']
"""
Which pixel of a cell [`Region.pixel_for_cell`][xnano.region.Region.pixel_for_cell] returns.

``'top_left'`` is the top left pixel of the cell, ``'center'`` the pixel in its middle and
``'bottom_right'`` the bottom right pixel.
"""

PixelPreset: TypeAlias = Literal[
    'block',
    'half_top',
    'half_bottom',
    'shade_light',
    'shade_medium',
    'shade_dark',
    'braille',
    'circle',
    'circle_outline',
    'dot',
    'diamond',
    'star',
    'line_horizontal',
    'line_vertical',
    'corner_top_left_rounded',
    'corner_top_right_rounded',
    'corner_bottom_left_rounded',
    'corner_bottom_right_rounded',
    'corner_top_left_square',
    'corner_top_right_square',
    'corner_bottom_left_square',
    'corner_bottom_right_square',
    'arrow_up',
    'arrow_down',
    'arrow_left',
    'arrow_right',
    'check',
    'cross',
]
"""The names of the characters ``Pixel`` knows: ``Pixel('diamond')`` draws ``◆``."""
