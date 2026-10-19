"""
xnano._schema._media

The aliases and settings for showing images and playing sound.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict

if TYPE_CHECKING:
    from xnano_audio import InstrumentName

    from xnano._schema._effects import PlayableEffectSpecification

Extra: TypeAlias = Literal['audio', 'image', 'monty']
"""
An optional part of xnano: ``'audio'`` needs the xnano-audio package, ``'image'`` the
xnano-image package and ``'monty'`` the pydantic-monty package.
"""

ImageFit: TypeAlias = Literal['contain', 'cover', 'stretch', 'crop', 'smart']
"""
How a picture sits in a box of a given width and height.

``'contain'`` fits it entirely inside the box. ``'cover'`` fills the box and crops what
overflows. ``'stretch'`` fills the box exactly. ``'crop'`` never resizes it: it is centered,
cropped or padded. ``'smart'`` is ``'cover'`` when the aspect ratios nearly match and
``'contain'`` otherwise.
"""

ResamplingFilter: TypeAlias = Literal['nearest', 'bilinear', 'catmull_rom', 'lanczos3']
"""
How pixels are blended when a picture is resized.

``'nearest'`` keeps hard pixel edges, which suits a small picture that is enlarged.
``'bilinear'``, ``'catmull_rom'`` and ``'lanczos3'`` smooth the result, which suits photographs.
"""


class PlayOptions(TypedDict, total=False):
    """
    The keyword options of [`play`][xnano.play]. An option replaces the same value on a
    [`Note`][xnano.Note].

    Attributes:
        instrument: A built-in instrument, from
            [`instrument_names`][xnano_audio.instrument_names].
        velocity: How hard a note is played, from 0.0 to 1.0.
        effects: Sound effects as dictionaries with a ``kind`` key.
        volume: Playback gain from 0.0 to 1.0.
        pan: Stereo position from -1.0 (left) to 1.0 (right).
        at_beat: Start when the musical clock reaches this beat.
        beats: How long a note name, a number or a ``Note`` is held, in beats.
    """

    instrument: InstrumentName
    """A built-in instrument name."""
    velocity: float
    """How hard a note is played."""
    effects: Sequence[PlayableEffectSpecification]
    """Sound effects as dictionaries with a ``kind`` key."""
    volume: float
    """Playback gain."""
    pan: float
    """Stereo position."""
    at_beat: int
    """The beat of the musical clock to start on."""
    beats: float
    """The length in beats."""
