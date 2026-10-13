"""
xnano.image

[`xnano-image`](https://github.com/hsaeed3/xnano/tree/main/packages/xnano-image) images that a
terminal can show. Needs the optional ``image`` extra: ``pip install "xnano[image]"``.
"""

from collections.abc import Mapping, Sequence

from xnano import _optional
from xnano._axes import to_rgb
from xnano._values import ColorValue

_optional.require('image', needed_for='xnano.image')

from xnano_image import (  # noqa: E402
    TerminalGraphics as TerminalGraphics,
)
from xnano_image import (  # noqa: E402
    TerminalImage as TerminalImage,
)

__all__ = ['TerminalGraphics', 'TerminalImage', 'from_art']


def from_art(rows: Sequence[str], palette: Mapping[str, ColorValue]) -> TerminalImage:
    """
    Make an image from rows of characters, one character per pixel.

    This is how pixel-art sprites are written in code. Every character in ``palette`` is a
    color; any other character, such as ``'.'``, is a transparent pixel.

    Args:
        rows: The rows of the picture, top to bottom, all of the same length.
        palette: The color of each character, as a name, ``'#rrggbb'`` string or
            ``(red, green, blue)`` tuple.

    Raises:
        ValueError: The rows are empty or differ in length, or a color is not a color.

    Examples:
        ```python
        from xnano.image import from_art

        heart = from_art(
            ['.RR.RR.', 'RRRRRRR', '.RRRRR.', '..RRR..', '...R...'],
            {'R': '#e03040'},
        )
        assert (heart.width, heart.height) == (7, 5)
        ```
    """
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError(
            'from_art needs at least one row, and every row the same length, but got '
            f'row lengths {[len(row) for row in rows]}. Pad the short rows with ".".'
        )
    channels = {character: (*to_rgb(color), 255) for character, color in palette.items()}
    transparent = bytes(4)
    pixels = b''.join(
        bytes(channels[character]) if character in channels else transparent
        for row in rows
        for character in row
    )
    return TerminalImage.from_rgba(len(rows[0]), len(rows), pixels)
