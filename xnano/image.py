"""
xnano.image

[`xnano-image`](https://github.com/hsaeed3/xnano/tree/main/packages/xnano-image) images that a
terminal can show. Needs the optional ``image`` extra: ``pip install "xnano[image]"``.
"""

import textwrap
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


def from_art(
    art: str | Sequence[str], palette: Mapping[str, ColorValue] | str
) -> TerminalImage:
    """
    Make an image from pixel art written as text, one character per pixel.

    This is how pixel-art sprites are written in code. The art is a multi-line string (or a
    list of rows), and the palette says what each character means; any character the palette
    does not name, such as ``'.'``, is a transparent pixel. The palette is a mapping, or one
    string of ``character=color`` pairs.

    Args:
        art: The picture, top to bottom. A multi-line string may be indented, and its first
            and last blank lines are ignored.
        palette: The color of each character, as a mapping to names, ``'#rrggbb'`` strings or
            ``(red, green, blue)`` tuples, or as a string such as ``'R=#e03040 G=green'``.

    Raises:
        ValueError: The art is empty or its rows differ in length, or the palette or a
            color in it is not valid.

    Examples:
        ```python
        from xnano.image import from_art

        heart = from_art(
            '''
            .RR.RR.
            RRRRRRR
            .RRRRR.
            ..RRR..
            ...R...
            ''',
            'R=#e03040',
        )
        assert (heart.width, heart.height) == (7, 5)
        ```
    """
    rows = _art_rows(art)
    colors = _palette_colors(palette)
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError(
            'from_art needs at least one row, and every row the same length, but got '
            f'row lengths {[len(row) for row in rows]}. Pad the short rows with ".".'
        )
    channels = {character: (*to_rgb(color), 255) for character, color in colors.items()}
    transparent = bytes(4)
    pixels = b''.join(
        bytes(channels[character]) if character in channels else transparent
        for row in rows
        for character in row
    )
    return TerminalImage.from_rgba(len(rows[0]), len(rows), pixels)


def _art_rows(art: str | Sequence[str]) -> list[str]:
    if not isinstance(art, str):
        return list(art)
    lines = textwrap.dedent(art).splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _palette_colors(palette: Mapping[str, ColorValue] | str) -> Mapping[str, ColorValue]:
    if not isinstance(palette, str):
        return palette
    colors: dict[str, ColorValue] = {}
    for pair in palette.split():
        character, separator, color = pair.partition('=')
        if not separator or len(character) != 1 or not color:
            raise ValueError(
                f'{pair!r} is not a palette entry. Write one character, an equals sign and a '
                f"color, such as 'R=#e03040 G=green', and separate entries with spaces."
            )
        colors[character] = color
    return colors
