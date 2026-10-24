"""
xnano.ai.models.art

Pixel art from a language model: generated, edited, animated and varied, always as
[`xnano.Art`][xnano.art.Art], with the rows and palette the model wrote kept beside it.
"""

from __future__ import annotations

import asyncio
import dataclasses
import math
import re
import struct
import weakref
import zlib
from collections.abc import Coroutine, Mapping, Sequence
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, TypeAlias, cast

from pydantic import BaseModel, Field
from pydantic_ai import BinaryContent, ModelRetry, ToolOutput

from xnano.ai import assets
from xnano.ai._generations import (
    Critique,
    GenerationError,
    GenerationReport,
    _Attempts,
    _generation_error,
)
from xnano.ai._observe import _ruled, evidence_prompt, snapshot
from xnano.ai._vector import SvgError, read_svg, traced_svg
from xnano.ai.models import TaskModel, _run_blocking
from xnano.ai.models._art_finish import finish
from xnano.ai.models._art_pixelize import pixelize
from xnano.ai.models._art_references import REFERENCES
from xnano.ai.models._image_models import image_generation_model
from xnano.art import Art, pixel_art
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from pydantic_ai.capabilities import AbstractCapability
    from pydantic_ai.images import ImageGenerationModel
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.models import KnownModelName, Model
    from pydantic_ai.settings import ModelSettings, ThinkingLevel
    from pydantic_ai.usage import UsageLimits

    from xnano._schema._axes import Percentage
    from xnano._schema._layout import PixelEncoding
    from xnano.hooks._context import Context

__all__ = [
    'Animation',
    'ArtModel',
    'ArtPatch',
    'ArtSize',
    'ArtStrategy',
    'ArtText',
    'ColorRole',
    'EditMode',
    'PaletteColor',
    'PixelRun',
]

ColorRole = Literal['outline', 'base', 'shadow', 'highlight', 'accent', 'skin', 'detail']
"""What a colour of a palette is for: ``'outline'``, ``'base'``, ``'shadow'``, ``'highlight'``, ``'accent'``, ``'skin'`` or ``'detail'``."""

ArtStrategy = Literal['program', 'svg']
"""
How the model writes the art: a small ``'program'`` of drawing calls (rectangles, ellipses,
lines, polygons, fills, mirrors and an outline), or an ``'svg'`` drawing sampled onto the
pixels.
"""

EditMode = Literal['auto', 'patch', 'redraw']
"""How an edit is written: a ``'patch'`` of the pixels that change, a ``'redraw'`` of all of them, or ``'auto'`` for the model to choose."""

ArtSize: TypeAlias = 'int | Percentage | str | tuple[int | None, int | None] | None'
"""
The size of art in pixels: a number such as ``16``, a share of the active canvas such as
``'50%'`` (a cell is one pixel wide and two tall), an expression such as ``ParentWidth - 4``, a
``(low, high)`` range the model picks within, or ``None`` for any size up to 32.
"""

_TRANSPARENT: Final = '.'
_BLOCK: Final = 2
"""A block of the sketch is this many pixels on each side."""


@dataclasses.dataclass(frozen=True, slots=True)
class _Look:
    """How a piece is drawn and shown: mirrored, as braille dots, or with box-drawing borders."""

    symmetrical: bool = False
    braille: bool = False
    borders: bool = False

    @property
    def is_flat(self) -> bool:
        """Whether the piece keeps flat colours: braille and borders trace edges themselves."""
        return self.braille or self.borders

    def notes(self) -> list[str]:
        """What the model is told about the look, before it draws."""
        notes = []
        if self.braille:
            notes.append(
                'The piece will show as braille dots, two pixels wide and four tall per '
                'terminal cell, each cell in one colour, as a line drawing: the edges '
                'between colours and against the background become solid dots, and the '
                'inside of each colour a light pattern of dots. So draw clear, distinct '
                'colour regions with simple edges; the edges carry the piece.'
            )
        if self.borders:
            notes.append(
                'The piece will show one pixel per terminal cell: the edges between colours '
                'and against the background are traced in box-drawing characters and the '
                'inside of each colour is filled with it, the look of a terminal rather than '
                'of pixel art. A cell is twice as tall as it is wide, so draw the piece about '
                'half as tall in pixels as its true proportions, with a few bold flat colour '
                'regions of simple edges: no stripes, patterns or textures, which would all '
                'become lines, and no background behind the subject.'
            )
        return notes


_LARGEST_UNSKETCHED: Final = 12
"""Art up to this many pixels on each side is drawn in one step, without a sketch."""
_MOST_PIXELS: Final = 64
_DEFAULT_MOST: Final = 32
_HEX: Final = re.compile(r'#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})')


# -- the art as the model writes it --------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class PaletteColor:
    """
    One colour of a palette, and what it is for.

    Attributes:
        role: What the colour is for, such as ``'outline'`` or ``'shadow'``.
        color: The colour as ``'#rrggbb'``.
    """

    role: ColorRole
    color: str


@dataclasses.dataclass(frozen=True, slots=True)
class PixelRun:
    """
    Pixels set in a row, from a column to the right: one letter of the palette per pixel.

    Attributes:
        row: The row, from ``0`` at the top.
        column: The first column, from ``0`` at the left.
        letters: The letters to write, one per pixel; ``'.'`` makes a pixel transparent.
    """

    row: int
    column: int
    letters: str


@dataclasses.dataclass(frozen=True, slots=True)
class ArtPatch:
    """
    A change to pixel art: the runs of pixels it sets, and any colours it adds.

    Attributes:
        runs: The pixels to set, in order.
        new_colors: The colours the runs use that the palette does not have yet.
    """

    runs: tuple[PixelRun, ...]
    new_colors: Mapping[str, PaletteColor] = dataclasses.field(
        default_factory=lambda: MappingProxyType({})
    )

    @property
    def pixel_count(self) -> int:
        """How many pixels the patch sets."""
        return sum(len(run.letters) for run in self.runs)


_text_of: weakref.WeakKeyDictionary[Art, ArtText] = weakref.WeakKeyDictionary()
"""The rows and palette each generated art was made from, so an edit reuses its letters."""


@dataclasses.dataclass(frozen=True, slots=True, eq=True)
class ArtText:
    """
    Pixel art as a model writes it: rows of one letter per pixel, and a palette with roles.

    It is what [`ArtModel`][xnano.ai.models.art.ArtModel] works with: the model names its colours by role
    under letters, then draws with those letters, and an edit changes letters. The changes
    that need no model (``flip_horizontal``, ``shift``, ``recolor``, ``scaled``, ``apply``)
    cost nothing. ``to_art()`` makes the [`Art`][xnano.art.Art] to write on a canvas.

    Attributes:
        rows: The rows, top to bottom, one letter per pixel; ``'.'`` is a transparent pixel.
        palette: The colour of each letter, and what it is for.
        width: The width in pixels.
        height: The height in pixels.

    Examples:
        ```python
        from xnano.ai.models.art import ArtText, PaletteColor

        text = ArtText(
            rows=('.oo.', 'obbo', '.oo.'),
            palette={'o': PaletteColor('outline', '#1a1c2c'), 'b': PaletteColor('base', '#b13e53')},
        )
        assert text.flip_vertical().rows == text.rows
        assert text.to_art().width == 4
        ```
    """

    rows: tuple[str, ...]
    palette: Mapping[str, PaletteColor]

    def __post_init__(self) -> None:
        """Check that the rows are even and use only letters of the palette."""
        rows = tuple(self.rows)
        object.__setattr__(self, 'rows', rows)
        object.__setattr__(self, 'palette', MappingProxyType(dict(self.palette)))
        if not rows or not rows[0]:
            raise ValueError('ArtText needs at least one row of at least one pixel.')
        width = len(rows[0])
        for index, row in enumerate(rows):
            if len(row) != width:
                raise ValueError(
                    f'Row {index} of the art has {len(row)} pixels, but row 0 has {width}. '
                    f'Give every row the same number of letters.'
                )
            unknown = sorted(set(row) - set(self.palette) - {_TRANSPARENT})
            if unknown:
                raise ValueError(
                    f'Row {index} uses {", ".join(map(repr, unknown))}, which the palette '
                    f'does not name. Add them to the palette, or use {_TRANSPARENT!r} for a '
                    f'transparent pixel.'
                )

    def __hash__(self) -> int:
        return hash((self.rows, tuple(sorted(self.palette.items()))))

    @property
    def width(self) -> int:
        """The width in pixels."""
        return len(self.rows[0])

    @property
    def height(self) -> int:
        """The height in pixels."""
        return len(self.rows)

    def to_art(
        self,
        *,
        symbol: str | None = None,
        encoding: PixelEncoding = 'half_blocks',
        borders: bool = False,
    ) -> Art:
        """
        Make the [`Art`][xnano.art.Art] of these rows and palette.

        Args:
            symbol: A name to register the art under in [`symbols`][xnano.symbols].
            encoding: How the pixels are packed into cells, as for [`pixel_art`][xnano.pixel_art].
            borders: Whether the art shows its edge in box-drawing characters, as for
                [`pixel_art`][xnano.pixel_art].
        """
        art = pixel_art(
            list(self.rows),
            {letter: color.color for letter, color in self.palette.items()},
            symbol=symbol,
            encoding=encoding,
            borders=borders,
        )
        _text_of[art] = self
        return art

    @classmethod
    def from_art(cls, art: Art) -> ArtText:
        """
        The rows and palette of art: the ones it was made from, or read from its pixels.

        Art made by [`ArtModel`][xnano.ai.models.art.ArtModel] or ``to_art`` gives back the model's own
        letters and roles. Other art is read pixel by pixel: each colour gets a letter, the
        darkest the ``'outline'`` role and the others ``'detail'``.

        Raises:
            ValueError: The art is a world, which has no pixels of its own.
        """
        known = _text_of.get(art)
        if known is not None:
            return known
        pixels = art.pixels
        if pixels is None:
            raise ValueError(
                'This art is a world, which has no pixels of its own to read. Give the art '
                'of one of its children, such as world.children[0].'
            )
        colors: dict[tuple[int, int, int], str] = {}
        rows = []
        letters = iter('abcdefghijklmnpqrstuvwxyz')
        for y in range(art.height):
            row = []
            for x in range(art.width):
                start = (y * art.width + x) * 4
                red, green, blue, alpha = pixels[start : start + 4]
                if alpha == 0:
                    row.append(_TRANSPARENT)
                    continue
                key = (red, green, blue)
                if key not in colors:
                    colors[key] = next(letters, '?')
                    if colors[key] == '?':
                        raise ValueError(
                            'This art has more than 25 colours, more than a palette of '
                            'letters can name. Reduce its colours before editing it.'
                        )
                row.append(colors[key])
            rows.append(''.join(row))
        darkest = min(colors, key=sum, default=None)
        palette = {
            letter: PaletteColor(
                'outline' if key == darkest else 'detail',
                '#{:02x}{:02x}{:02x}'.format(*key),
            )
            for key, letter in colors.items()
        }
        return cls(rows=tuple(rows), palette=palette)

    def labelled(self) -> str:
        """The rows with a column ruler above them and the row number before each, for a prompt."""
        return _ruled('\n'.join(self.rows), self.width, self.height)

    def palette_text(self) -> str:
        """The palette as one line per letter, ``o = outline #1a1c2c``, for a prompt."""
        return '\n'.join(
            f'{letter} = {color.role} {color.color}'
            for letter, color in self.palette.items()
        )

    def flip_horizontal(self) -> ArtText:
        """The art mirrored left to right."""
        return ArtText(tuple(row[::-1] for row in self.rows), self.palette)

    def flip_vertical(self) -> ArtText:
        """The art mirrored top to bottom."""
        return ArtText(self.rows[::-1], self.palette)

    def shift(self, x: int = 0, y: int = 0) -> ArtText:
        """The art moved by ``x`` pixels right and ``y`` down, inside the same size."""
        width, height = self.width, self.height
        blank = _TRANSPARENT * width
        rows = []
        for row_index in range(height):
            source = row_index - y
            if not 0 <= source < height:
                rows.append(blank)
                continue
            row = self.rows[source]
            moved = (
                (_TRANSPARENT * x + row)[:width]
                if x >= 0
                else (row[-x:] + _TRANSPARENT * -x)
            )
            rows.append(moved)
        return ArtText(tuple(rows), self.palette)

    def recolor(self, colors: Mapping[str, str]) -> ArtText:
        """
        The art with new colours for some letters, keeping their roles.

        Args:
            colors: The new ``'#rrggbb'`` colour of each letter to change.

        Raises:
            ValueError: A letter is not in the palette.
        """
        palette = dict(self.palette)
        for letter, color in colors.items():
            if letter not in palette:
                raise ValueError(
                    f'recolor() was given {letter!r}, which the palette does not have. Its '
                    f'letters are {", ".join(map(repr, palette))}.'
                )
            palette[letter] = PaletteColor(
                palette[letter].role, _normalized_color(color)[0]
            )
        return ArtText(self.rows, palette)

    def scaled(self, factor: int) -> ArtText:
        """
        The art with every pixel made ``factor`` pixels wide and tall.

        Raises:
            ValueError: ``factor`` is not a whole number of 1 or more.
        """
        if isinstance(factor, bool) or not isinstance(factor, int) or factor < 1:
            raise ValueError(
                f'scaled() needs a whole number of 1 or more, such as 2, but got {factor!r}.'
            )
        rows = tuple(
            ''.join(letter * factor for letter in row)
            for row in self.rows
            for _ in range(factor)
        )
        return ArtText(rows, self.palette)

    def apply(self, patch: ArtPatch) -> ArtText:
        """
        The art with a patch applied: its runs written, its new colours added.

        Raises:
            ValueError: A run is outside the art, or uses a letter neither palette names.
        """
        palette = {**self.palette, **patch.new_colors}
        grid = [list(row) for row in self.rows]
        for run in patch.runs:
            if (
                not 0 <= run.row < self.height
                or run.column < 0
                or (run.column + len(run.letters) > self.width)
            ):
                raise ValueError(
                    f'The run at row {run.row}, column {run.column} with '
                    f'{len(run.letters)} letters is outside the art, which is {self.width} '
                    f'by {self.height} pixels.'
                )
            for offset, letter in enumerate(run.letters):
                grid[run.row][run.column + offset] = letter
        return ArtText(tuple(''.join(row) for row in grid), palette)


def _normalized_color(color: str) -> tuple[str, bool]:
    """``color`` as ``'#rrggbb'``, and whether it had to be repaired to get there."""
    text = str(color).strip()
    match = _HEX.fullmatch(text)
    if match is None:
        raise ValueError(
            f'{color!r} is not a colour written as #rrggbb, such as #1a1c2c. Write each '
            f'colour as # and six hexadecimal digits.'
        )
    digits = match.group(1)
    if len(digits) == 3:
        digits = ''.join(digit * 2 for digit in digits)
    normalized = f'#{digits.lower()}'
    return normalized, normalized != text.lower() or not text.startswith('#')


@dataclasses.dataclass(frozen=True, slots=True)
class _Sketch:
    """The coarse sketch a piece is drawn from: one letter per block of 2 by 2 pixels."""

    width: int
    """The width of the piece in pixels."""
    height: int
    """The height of the piece in pixels."""
    rows: tuple[str, ...]
    """The blocks, one letter per block and ``'.'`` for an empty one."""
    palette: Mapping[str, PaletteColor]
    """The masses of the sketch, by letter."""

    @property
    def columns(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    def labelled(self) -> str:
        """The blocks under a column ruler, with the row number before each."""
        return _ruled('\n'.join(self.rows), self.columns, len(self.rows))

    def rectangles(self) -> list[tuple[int, int, int, int, str]]:
        """The blocks as rectangles at pixel scale, the largest first."""
        grid: list[list[str | None]] = [
            [None if letter == _TRANSPARENT else letter for letter in row]
            for row in self.rows
        ]
        return [
            (
                x * _BLOCK,
                y * _BLOCK,
                min(width * _BLOCK, self.width - x * _BLOCK),
                min(height * _BLOCK, self.height - y * _BLOCK),
                letter,
            )
            for x, y, width, height, letter in _rectangles_of(grid)
        ]

    def shapes(self) -> list[Any]:
        """The blocks as the shapes that paint them at pixel scale."""
        return [
            _Rectangle(
                kind='rectangle', x=x, y=y, width=width, height=height, letter=letter
            )
            for x, y, width, height, letter in self.rectangles()
        ]

    def svg(self) -> str:
        """The blocks as SVG rectangles at pixel scale, filled with their letters."""
        elements = '\n'.join(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{letter}"/>'
            for x, y, width, height, letter in self.rectangles()
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} '
            f'{self.height}">\n{elements}\n</svg>'
        )

    def is_drawn(self, x: int, y: int) -> bool | None:
        """Whether the block is a mass, or ``None`` outside the sketch."""
        if 0 <= y < len(self.rows) and 0 <= x < self.columns:
            return self.rows[y][x] != _TRANSPARENT
        return None


# -- what the model writes -----------------------------------------------------------------


class _Color(BaseModel):
    """One colour of the palette: a letter, what the colour is for, and the colour."""

    letter: Annotated[
        str, Field(description='One lowercase letter, chosen as a mnemonic.')
    ]
    role: ColorRole
    color: Annotated[str, Field(description='The colour as #rrggbb.')]


class _Run(BaseModel):
    """Pixels set in a row, from a column to the right."""

    row: int
    column: int
    letters: Annotated[
        str, Field(description="One palette letter per pixel; '.' is transparent.")
    ]


class _Rectangle(BaseModel):
    kind: Literal['rectangle']
    x: int
    y: int
    width: int
    height: int
    letter: str
    is_filled: bool = True


class _Ellipse(BaseModel):
    kind: Literal['ellipse']
    x: int
    y: int
    width: int
    height: int
    letter: str
    is_filled: bool = True


class _Line(BaseModel):
    kind: Literal['line']
    x1: int
    y1: int
    x2: int
    y2: int
    letter: str


class _Polygon(BaseModel):
    kind: Literal['polygon']
    points: list[tuple[int, int]]
    letter: str
    is_filled: bool = True


class _Fill(BaseModel):
    kind: Literal['fill']
    x: int
    y: int
    letter: str


class _Mirror(BaseModel):
    kind: Literal['mirror']
    axis: Literal['horizontal', 'vertical']


class _Outline(BaseModel):
    kind: Literal['outline']
    letter: str


_Layout: TypeAlias = Annotated[
    str,
    Field(
        description=(
            'Written before drawing: the size, then each part of the subject in painting '
            'order, from the back to the front, with its palette letters and the rows and '
            'columns it covers.'
        )
    ),
]

_Shape: TypeAlias = Annotated[
    _Rectangle | _Ellipse | _Line | _Polygon | _Fill | _Mirror | _Outline,
    Field(discriminator='kind'),
]


# -- built-in references, in each strategy's own form ------------------------------------

_PROGRAM_REFERENCE: Final = """A mushroom, 8 by 10, as a program that mirrors its left half, outlines it, then adds the spots:
o = outline #1a1c2c
r = base #b13e53
t = detail #e8d5b0
w = highlight #f4f4f4
ellipse(1, 1, W - 2, 5, 'r')
rect(3, 6, 1, 3, 't')
mirror_x()
outline('o')
for x, y in [(2, 2), (5, 2), (4, 4)]:
    pixel(x, y, 'w')"""

_PROGRAM_PRELUDE: Final = """
W = {width}
H = {height}
painting = []


def pixel(x: float, y: float, letter: str) -> None:
    painting.append(('rectangle', x, y, 1, 1, letter, True))


def rect(x: float, y: float, width: float, height: float, letter: str, is_filled: bool = True) -> None:
    painting.append(('rectangle', x, y, width, height, letter, is_filled))


def ellipse(x: float, y: float, width: float, height: float, letter: str, is_filled: bool = True) -> None:
    painting.append(('ellipse', x, y, width, height, letter, is_filled))


def circle(center_x: float, center_y: float, radius: float, letter: str) -> None:
    painting.append(('ellipse', center_x - radius, center_y - radius, 2 * radius, 2 * radius, letter, True))


def line(x1: float, y1: float, x2: float, y2: float, letter: str) -> None:
    painting.append(('line', x1, y1, x2, y2, letter))


def polygon(points, letter: str, is_filled: bool = True) -> None:
    painting.append(('polygon', [(point[0], point[1]) for point in points], letter, is_filled))


def fill(x: float, y: float, letter: str) -> None:
    painting.append(('fill', x, y, letter))


def mirror_x() -> None:
    painting.append(('mirror', 'horizontal'))


def mirror_y() -> None:
    painting.append(('mirror', 'vertical'))


def outline(letter: str) -> None:
    painting.append(('outline', letter))
"""
"""What every art program starts from: the size, and the drawing functions it calls."""

_MOST_PAINTING_CALLS: Final = 20_000

_SVG_REFERENCE: Final = """A potion, 13 by 16, as SVG:
o = outline #1a1c2c
c = detail #8b5a3c
g = base #a8d8ea
p = accent #b13e53
s = shadow #5d275d
h = highlight #f4f4f4
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 13 16">
<!-- the outline: the same forms one pixel larger, painted first -->
<g fill="o">
  <rect x="3" y="0" width="7" height="3"/>
  <rect x="4" y="2" width="5" height="4"/>
  <circle cx="6.5" cy="10.5" r="5.5"/>
</g>
<rect x="4" y="1" width="5" height="1" fill="c"/>
<rect x="5" y="3" width="3" height="3" fill="g"/>
<circle cx="6.5" cy="10.5" r="4.5" fill="g"/>
<!-- the potion fills the lower half of the glass -->
<path d="M2 10.5 A4.5 4.5 0 0 0 11 10.5 Z" fill="p"/>
<!-- one-pixel lines run through pixel centres -->
<line x1="9.5" y1="11" x2="9.5" y2="14" stroke="s"/>
<rect x="3" y="7" width="1" height="2" fill="h"/>
</svg>"""

_STRATEGY_INSTRUCTIONS: Final[dict[str, str]] = {
    'program': (
        'Write the art as a short Python program that paints palette letters onto a canvas '
        'of W by H transparent pixels; (0, 0) is the top-left pixel, x grows to the right '
        'and y downwards. Each call paints over what is there: pixel(x, y, letter); rect(x, '
        'y, width, height, letter) fills the box whose top-left pixel is (x, y); ellipse(x, '
        'y, width, height, letter) fills the ellipse inside that same box, so its centre is '
        'at (x + width / 2, y + height / 2); circle(center_x, center_y, radius, letter); '
        'line(x1, y1, x2, y2, letter); polygon(points, letter) with points as [(x, y), ...]; '
        'fill(x, y, letter), a flood fill of the area around a pixel; mirror_x() copies the '
        'left half onto the right half, so draw the left half first, and mirror_y() the top '
        "half onto the bottom. The letter '.' erases. Use loops and helper functions; plain "
        f'Python and import math are available.\n\n{_PROGRAM_REFERENCE}'
    ),
    'svg': (
        'Write the art as SVG, the way you would draw an icon, on viewBox="0 0 width height": '
        'one unit is one pixel, and pixel (x, y) is the square from (x, y) to (x + 1, y + 1). '
        'Each pixel takes the colour that covers most of it, the element painted later '
        'winning a tie, so an edge on a whole number is a clean pixel edge; a detail smaller '
        'than a pixel keeps the one pixel at its centre. A line or stroke one pixel wide runs '
        'through pixel centres, such as x1="9.5". Use <rect> (rx and ry round its corners), '
        '<circle>, <ellipse>, <line>, <polyline>, <polygon>, <path> (every command, curves '
        'and arcs included) and <g>; transform with translate, scale, rotate, skewX, skewY '
        'and matrix; fill, stroke, stroke-width, stroke-linecap, paint-order and fill-rule, '
        'as attributes or in style, inherited through <g>. Paint with the palette, by letter '
        '(fill="h") or by colour (fill="#e8739a"); there are no gradients, opacity, filters, '
        f'text or images.\n\n{_SVG_REFERENCE}'
    ),
}


_SKETCH_INSTRUCTIONS: Final = (
    'Art larger than 12 pixels is drawn in two steps. First the sketch: the size in blocks, '
    'the palette of the masses (hair, face, body, sword), and a short Python program of a '
    'few big shapes on a grid of W by H blocks, each block being 2 by 2 pixels of the piece, '
    'so a 20 by 24 piece is sketched on W = 10 by H = 12 blocks. The sketch settles '
    'proportion and placement only: where each part is, how large it is, and which is in '
    'front; no eyes, mouth or buttons, and no background behind the subject unless the '
    'request describes a scene. Its calls paint blocks, with (0, 0) the top-left block, each '
    'painting over what is there: rect(x, y, width, height, letter) fills the box whose '
    'top-left block is (x, y); ellipse(x, y, width, height, letter) fills the ellipse inside '
    'that box; circle(center_x, center_y, radius, letter); polygon(points, letter) with '
    'points as [(x, y), ...]; line(x1, y1, x2, y2, letter); mirror_x() copies the left half '
    'onto the right. Every letter is one of the palette. Centre the subject and let it fill '
    'most of the grid. Then the drawing: the piece at full size, which keeps the composition '
    'of the sketch, refines the masses, and adds the details. A drawing that abandons its '
    'sketch is sent back.'
)


def _default_most_colors(width: int, height: int) -> int:
    """About 5 colours at 8 by 8 and 16 at 32 by 32."""
    return max(5, round(math.sqrt(width * height) / 2))


# -- the model -----------------------------------------------------------------------------


class ArtModel(TaskModel):
    """
    Generate and edit pixel art: [`xnano.Art`][xnano.art.Art] from a description.

    A piece larger than 12 pixels is drawn in two steps. First the model sketches it: the
    size, a palette of its masses (hair, face, body), and a few big shapes on a grid of blocks
    of 2 by 2 pixels, which settles the proportions and the placement of each part. Then it
    draws the piece at full size over that sketch, in the form of its ``strategy``, as flat
    colours: one base colour per material, and the details; a drawing that leaves the
    composition of its sketch is sent back. A piece of 12 pixels or less is drawn in one step.
    The renderer then finishes the piece the way a pixel artist does, with the light from the
    top left: lone pixels take the colour around them, the silhouette gets an outline inside
    it in a dark colour of its own, and each material gets a shadow along its lower-right
    edges and a highlight along its upper-left edges, in colours shifted in hue. The model
    names its colours by role (base, skin, detail, accent, and outline, shadow or highlight
    when it draws those itself, which the renderer then leaves alone) under letters. Every
    answer is checked as it arrives: a size outside the range, an unknown letter, too many
    colours or a program that fails goes back to the model with the exact fault. A safe repair
    (a colour written ``'#f8c'``, a code fence around the program) is made instead of a retry
    and reported in ``last_generation``, as is what the renderer added. Built-in references,
    the two closest to each request, show the craft in the strategy's own form; the
    ``'art-references'`` library of [`xnano.ai.assets`][xnano.ai.assets] adds more when it is
    installed.

    An ``image_model`` draws the piece as a picture instead: an image model paints the sprite
    scaled up on a flat background, and the picture's own pixel grid is read back into pixel
    art, one sample per drawn pixel, the background keyed out, the sprite cropped to its bounds
    and shrunk by a whole factor when it is larger than asked, and its colours reduced to the
    palette. The language model then edits and critiques that art as it does any other.

    Args:
        model: The language model to ask.
        strategy: How the model writes the art: ``'program'`` (the default: a short program
            of rectangles, ellipses, polygons, mirroring and an outline) or ``'svg'`` (an
            SVG drawing, for round and diagonal forms).
        width: The width of what ``generate`` makes, in the forms of
            [`ArtSize`][xnano.ai.models.art.ArtSize]; each call can give its own.
        height: The height, in the same forms.
        max_colors: The most colours a piece may have; ``None`` scales with the size, from
            about 5 at 8 by 8 to 16 at 32 by 32.
        style: How the art should look, such as ``'chunky outlines, warm palette'``.
        critique: How many rounds of critique ``generate`` runs, unless a call gives its own:
            in each, a vision model sees the piece as an image and lists what to fix, the
            model draws it again, and the piece with the best score is kept. ``0`` by default.
        critic: The vision model that critiques; ``None`` asks ``model``, which must then
            see images.
        image_model: An image generation model that draws the piece as a picture, by name
            (``'openrouter:google/gemini-2.5-flash-image'``, or one pydantic-ai knows such as
            ``'openai:gpt-image-1'``) or as a pydantic-ai ``ImageGenerationModel``; ``None``
            draws with ``model`` in the form of ``strategy``.
        instructions: What the model is told before every request.
        model_settings: pydantic-ai settings for every request.
        capabilities: pydantic-ai capabilities for the agent.
        retries: How many times an answer that fails its checks is sent back.
        usage_limits: Limits on the requests and tokens of one call.
        thinking: Whether the model reasons before answering. ``None``, the default, leaves
            that to the model; ``False`` turns it off where the model allows it, and some
            models cannot turn it off.
        cache: Whether the unchanging start of every prompt is cached by the provider.

    Attributes:
        strategy: How the model writes the art.
        critique: How many rounds of critique ``generate`` runs.
        critic: The vision model that critiques, or ``None`` for the model itself.
        image_model: The image generation model that draws, or ``None``.
        last_generation: How the last call went, or ``None`` before the first.

    Examples:
        ```python
        from xnano.ai.models.art import ArtModel, ArtText
        from xnano.ai.testing import scripted_model

        answer = {
            'layout': 'A coin filling the canvas.',
            'palette': [
                {'letter': 'o', 'role': 'outline', 'color': '#1a1c2c'},
                {'letter': 'y', 'role': 'base', 'color': '#ffcd75'},
            ],
            'width': 4,
            'height': 4,
            'program': "ellipse(0, 0, W, H, 'o'); rect(1, 1, 2, 2, 'y')",
        }
        artist = ArtModel(scripted_model(answer).model, width=4, height=4)
        coin = artist.generate('a gold coin')
        assert ArtText.from_art(coin).rows == ('.oo.', 'oyyo', 'oyyo', '.oo.')
        assert artist.last_generation.attempts == 1
        ```
    """

    _task_instructions = (
        'You draw pixel art for a terminal program, the way a pixel artist works: the '
        'silhouette first, then flat colours, then details. Lay the piece out before drawing '
        'it: choose the size, then place each part at the rows and columns it covers, in '
        'painting order from the back to the front, because what is painted later covers '
        'what came before (hair behind the head, then the face, then the eyes). Proportions '
        'at this scale: a character is 2 to 3 heads tall at 16 pixels and 3 to 4 at 32, the '
        'head is a third to half of the sprite, eyes are 1 by 2 pixels at 16 and 2 by 2 at '
        '24 to 32, arms are 1 pixel wide at 16, and the hair, hat or weapon that makes the '
        'subject recognisable belongs to the silhouette. Name the colours by role under '
        'single lowercase letters chosen as mnemonics: one flat base colour per material '
        "(role 'base', or 'skin' for skin), and the few 'detail' and 'accent' colours of "
        'eyes, mouths, buttons and gems. Paint only those: no outline, no shadows, no '
        'highlights, and no stray single pixels. The renderer finishes the piece the way '
        'pixel artists do, with the light from the top left: it outlines the silhouette, and '
        'shades each material with a shadow along its lower-right edges and a highlight along '
        'its upper-left edges, in hue-shifted colours of its own. An example shows the form '
        'of an answer, never the subject: draw what was asked for.'
    )

    def __init__(
        self,
        model: Model | KnownModelName | str | None = None,
        *,
        strategy: ArtStrategy = 'program',
        width: ArtSize = (None, _DEFAULT_MOST),
        height: ArtSize = (None, _DEFAULT_MOST),
        max_colors: int | None = None,
        style: str | None = None,
        critique: int = 0,
        critic: Model | KnownModelName | str | None = None,
        image_model: ImageGenerationModel | str | None = None,
        instructions: str | None = None,
        model_settings: ModelSettings | None = None,
        capabilities: Sequence[AbstractCapability[Any]] = (),
        retries: int = 3,
        usage_limits: UsageLimits | None = None,
        thinking: ThinkingLevel | None = None,
        cache: bool = True,
    ) -> None:
        """
        Create the art model; nothing is sent until the first call.

        Raises:
            ValueError: ``strategy`` is not one of the strategies, ``max_colors`` is not a
                whole number from 2 to 25, or ``critique`` is not a whole number from 0 to 3.
        """
        _check_critique(critique)
        if strategy not in _STRATEGY_INSTRUCTIONS:
            raise ValueError(
                f"strategy must be 'program' or 'svg', but was {strategy!r}."
            )
        if max_colors is not None and (
            isinstance(max_colors, bool)
            or not isinstance(max_colors, int)
            or not 2 <= max_colors <= 25
        ):
            raise ValueError(
                f'max_colors must be a whole number from 2 to 25, or None, but was '
                f'{max_colors!r}.'
            )
        parts = [
            _STRATEGY_INSTRUCTIONS[strategy],
            _SKETCH_INSTRUCTIONS,
            instructions or '',
        ]
        if style:
            parts.append(f'Draw in this style: {style}.')
        super().__init__(
            model,
            instructions='\n\n'.join(part for part in parts if part),
            model_settings=model_settings,
            capabilities=capabilities,
            retries=retries,
            usage_limits=usage_limits,
            thinking=thinking,
            cache=cache,
        )
        self.strategy: ArtStrategy = strategy
        self.style = style
        self._width = width
        self._height = height
        self._max_colors = max_colors
        self.critique = critique
        self.critic = critic
        self.image_model = image_model
        self.last_generation: GenerationReport | None = None

    # -- generating ---------------------------------------------------------------------

    def generate_async(
        self,
        request: str,
        evidence: object = None,
        *,
        width: ArtSize = None,
        height: ArtSize = None,
        symmetrical: bool = False,
        braille: bool = False,
        borders: bool = False,
        candidates: int = 1,
        critique: int | None = None,
        symbol: str | None = None,
    ) -> Coroutine[Any, Any, Art]:
        """
        Draw pixel art from a description, with ``await``.

        The sizes are read when this is called; await the result for the art.

        Args:
            request: What to draw, such as ``'a knight with a red plume'``.
            evidence: What the art is for, such as the hook's context; see
                [`Evidence`][xnano.ai.Evidence].
            width: The width; ``None`` uses the model's.
            height: The height; ``None`` uses the model's.
            symmetrical: Whether the piece is symmetric about its vertical middle, like a
                face or a creature seen from the front. The model then draws only the left
                half, which is mirrored to make the right half (an odd width shares its
                middle column), so the two sides match exactly. ``False`` by default.
            braille: Whether the art shows as braille dots, two by four per terminal cell in
                one colour per cell: a finer, drawing-like look that pixel art cannot have.
                The model is told, and draws for it. ``False`` by default.
            borders: Whether the art shows one pixel per cell, its edge traced in box-drawing
                characters and its inside filled with colour: the look of a terminal, which
                pixel art cannot have. The model is told that a cell is twice as tall as it
                is wide, and draws for it. ``False`` by default.
            candidates: How many pieces to draw at once; the one that is valid, within its
                colours and the most connected is kept.
            critique: How many rounds of critique to run; ``None`` uses the model's. See
                [`Critique`][xnano.ai.Critique].
            symbol: A name to register the art under in [`symbols`][xnano.symbols].

        Returns:
            A coroutine that gives the [`Art`][xnano.art.Art].

        Raises:
            ValueError: A size is not one of the forms of ``ArtSize``, ``candidates`` is not
                1 or more, or ``critique`` is not a whole number from 0 to 3.
            GenerationError: No answer could be made into the art, even after the retries;
                its ``generation`` lists every problem, when awaited.
            TerminalError: The model could not be reached (``ai.model``), when awaited.
        """
        widths = _pixel_range(self._width if width is None else width, 'width')
        heights = _pixel_range(self._height if height is None else height, 'height')
        if (
            isinstance(candidates, bool)
            or not isinstance(candidates, int)
            or candidates < 1
        ):
            raise ValueError(
                f'candidates must be a whole number of 1 or more, but was {candidates!r}.'
            )
        for name, flag in (
            ('symmetrical', symmetrical),
            ('braille', braille),
            ('borders', borders),
        ):
            if not isinstance(flag, bool):
                raise ValueError(f'{name} must be True or False, but was {flag!r}.')
        rounds = self.critique if critique is None else _check_critique(critique)
        return self._generate(
            request,
            snapshot(evidence),
            widths,
            heights,
            _Look(symmetrical, braille, borders),
            candidates,
            rounds,
            symbol,
        )

    def generate(
        self,
        request: str,
        evidence: object = None,
        *,
        width: ArtSize = None,
        height: ArtSize = None,
        symmetrical: bool = False,
        braille: bool = False,
        borders: bool = False,
        candidates: int = 1,
        critique: int | None = None,
        symbol: str | None = None,
    ) -> Art:
        """
        Draw pixel art from a description, waiting for it.

        The same as [`generate_async`][xnano.ai.models.art.ArtModel.generate_async], for code that does
        not await.
        """
        return _run_blocking(
            self.generate_async(
                request,
                evidence,
                width=width,
                height=height,
                symmetrical=symmetrical,
                braille=braille,
                borders=borders,
                candidates=candidates,
                critique=critique,
                symbol=symbol,
            ),
            'generate',
        )

    async def _generate(
        self,
        request: str,
        evidence: object,
        widths: tuple[int, int],
        heights: tuple[int, int],
        look: _Look,
        candidates: int,
        rounds: int,
        symbol: str | None,
    ) -> Art:
        if candidates == 1:
            text, report = await self._draw(request, evidence, widths, heights, look=look)
        else:
            outcomes = await asyncio.gather(
                *(
                    self._draw(request, evidence, widths, heights, look=look)
                    for _ in range(candidates)
                ),
                return_exceptions=True,
            )
            drawn = [outcome for outcome in outcomes if isinstance(outcome, tuple)]
            if not drawn:
                failure = next(o for o in outcomes if isinstance(o, BaseException))
                raise failure
            text, report = max(drawn, key=lambda pair: _quality(pair[0], pair[1]))
        if rounds:
            text, report = await self._critiqued(request, text, report, rounds, look)
        self.last_generation = report
        if look.braille:
            text = _dotted(text)
        return text.to_art(
            symbol=symbol,
            encoding='braille' if look.braille else 'half_blocks',
            borders=look.borders,
        )

    async def _critiqued(
        self,
        request: str,
        text: ArtText,
        report: GenerationReport,
        rounds: int,
        look: _Look,
    ) -> tuple[ArtText, GenerationReport]:
        """Critique the piece and draw it again, ``rounds`` times; keep the best-scored one."""
        critiques: list[Critique] = []
        problems = list(report.problems)
        attempts_count = report.attempts
        current = text
        best: tuple[int, ArtText] | None = None
        for round_index in range(rounds + 1):
            critique = await self._critique(request, current)
            critiques.append(critique)
            if best is None or critique.score > best[0]:
                best = (critique.score, current)
            if round_index == rounds or not critique.problems:
                break
            listed = '\n'.join(f'- {problem}' for problem in critique.problems)
            revision = '\n\n'.join(
                [
                    f'This is a second attempt. A critic scored the last piece '
                    f'{critique.score} out of 10 and found:\n{listed}',
                    f'The last piece, {current.width} by {current.height}:\n{current.labelled()}',
                    f'Its palette:\n{current.palette_text()}',
                    'Fix those problems at the same size, and keep what works.',
                ]
            )
            try:
                current, revised = await self._draw(
                    request,
                    None,
                    (current.width, current.width),
                    (current.height, current.height),
                    look=look,
                    revision=revision,
                )
            except GenerationError as error:
                # A revision that never passed its checks leaves the best piece so far.
                problems.extend(error.generation.problems)
                break
            attempts_count += revised.attempts
            problems.extend(revised.problems)
        assert best is not None
        return best[1], dataclasses.replace(
            report,
            attempts=attempts_count,
            problems=tuple(problems),
            critiques=tuple(critiques),
        )

    async def _critique(self, request: str, text: ArtText) -> Critique:
        """Ask the critic what is wrong with the piece, showing it as an image."""

        def critique(score: int, problems: list[str]) -> Critique:
            """Score the piece from 1 (unreadable) to 10 (nothing to fix); list each problem."""
            if not 1 <= score <= 10:
                raise ModelRetry(f'The score must be from 1 to 10, but was {score}.')
            kept = tuple(problem.strip() for problem in problems if problem.strip())
            return Critique(score=score, problems=kept)

        prompt = [
            (
                f'Critique this pixel art of: {request}. The image shows it scaled up; the '
                'rows below are the same piece, one letter per pixel, with its palette. Judge '
                'first whether it reads as the request: is each thing the request names '
                'there, recognisable, in proportion and in its place? Then judge the craft: a '
                'clear silhouette, light from the top left, one outline colour, no stray '
                'pixels. Score how well it reads as the request first and its craft second, '
                'and list the concrete problems to fix, the most important first, naming rows '
                'and columns where you can; list none if nothing needs fixing.'
                f'\n\n{text.labelled()}\n\nIts palette:\n{text.palette_text()}'
            ),
            BinaryContent(data=_png_of(text), media_type='image/png'),
        ]
        result = await self._ask(
            prompt,
            ToolOutput(critique, name='critique'),
            operation='generate',
            instructions='You are now a critic of pixel art, not its artist.',
            model=self.critic,
        )
        return result.output

    async def _draw(
        self,
        request: str,
        evidence: object,
        widths: tuple[int, int],
        heights: tuple[int, int],
        *,
        look: _Look,
        revision: str | None = None,
    ) -> tuple[ArtText, GenerationReport]:
        """Draw the piece with the image model when there is one, else with the language model."""
        if self.image_model is not None:
            return await self._draw_from_picture(
                request, widths, heights, revision, look.symmetrical
            )
        return await self._draw_once(
            request, evidence, widths, heights, look=look, revision=revision
        )

    async def _draw_from_picture(
        self,
        request: str,
        widths: tuple[int, int],
        heights: tuple[int, int],
        revision: str | None,
        symmetrical: bool,
    ) -> tuple[ArtText, GenerationReport]:
        """Have the image model paint the piece, and read the pixel art out of the picture."""
        from pydantic_ai.exceptions import AgentRunError, UserError
        from xnano_image import TerminalImage

        assert self.image_model is not None
        attempts = _Attempts()
        attempts.begin()
        most_colors = self._max_colors or _default_most_colors(widths[1], heights[1])
        subject = request.strip().rstrip('.')
        subject = subject[0].lower() + subject[1:] if subject else 'something'
        prompt = (
            f'A pixel art sprite of {subject}, for a retro video game: a small sprite of '
            f'about {widths[1]} by {heights[1]} pixels, scaled up with hard square pixels, '
            f'flat colours, a dark outline, no anti-aliasing, no gradients, no text, centred '
            f'and filling the frame, on a flat solid magenta background (#ff00ff) with '
            f'nothing else in the picture.'
        )
        if revision:
            prompt = f'{prompt}\n\n{revision}'
        try:
            result = await image_generation_model(self.image_model).generate(prompt)
        except (AgentRunError, UserError) as error:
            raise self._model_error(error, 'generate') from error
        picture = TerminalImage.from_bytes(result.images[0].content.data)
        try:
            pixelized = pixelize(
                picture, widths=widths, heights=heights, most_colors=most_colors
            )
        except ValueError as error:
            attempts.problems.append(str(error))
            raise self._generation_error(attempts, 'generate') from error
        attempts.notes.append(
            f'the picture drew its pixels {pixelized.pitch} picture pixels wide'
        )
        if pixelized.shrink > 1:
            attempts.notes.append(
                f'the sprite was shrunk by {pixelized.shrink} to fit {widths[1]} by '
                f'{heights[1]} pixels'
            )
        colors = {
            letter: PaletteColor('outline' if index == 0 else 'base', color)
            for index, (letter, color) in enumerate(pixelized.palette.items())
        }
        rows = pixelized.rows
        if symmetrical:
            half = (len(rows[0]) + 1) // 2
            rows = tuple(_mirrored_row(row[:half], odd=len(row) % 2 == 1) for row in rows)
            attempts.notes.append('the left half of the picture was mirrored')
        return ArtText(rows, colors), attempts.report('image')

    async def _draw_once(
        self,
        request: str,
        evidence: object,
        widths: tuple[int, int],
        heights: tuple[int, int],
        *,
        look: _Look,
        revision: str | None = None,
    ) -> tuple[ArtText, GenerationReport]:
        """Draw the piece: a sketch first unless it is small, then the drawing itself."""
        attempts = _Attempts()
        most_colors = self._max_colors or _default_most_colors(widths[1], heights[1])
        symmetrical = look.symmetrical
        drawn_widths = _half_widths(widths) if symmetrical else widths
        check = _Checker(
            attempts,
            drawn_widths,
            heights,
            most_colors,
            mirror_widths=widths if symmetrical else None,
            is_flat=look.is_flat,
        )
        for note in look.notes():
            revision = f'{note}\n\n{revision}' if revision else note
        if symmetrical:
            half = (
                'The piece is symmetrical, so draw only its left half: the canvas is the '
                'left half of the whole piece, and the right half is its mirror image. The '
                'middle of the subject lies on the right edge of the canvas (the last '
                'column, x = W - 1), so every part that crosses the middle (a head, a body, '
                'a hat) reaches that edge, and nothing is centred on the half canvas. Do '
                'not use mirror_x().'
            )
            revision = f'{half}\n\n{revision}' if revision else half
        widths = drawn_widths
        history: Sequence[ModelMessage] | None = None
        try:
            if widths[1] > _LARGEST_UNSKETCHED or heights[1] > _LARGEST_UNSKETCHED:
                prompt = self._sketch_prompt(
                    request, evidence, widths, heights, most_colors, revision
                )
                sketched = await self._ask(
                    prompt, self._sketch_output(check), operation='generate'
                )
                history = sketched.all_messages()
                prompt = self._drawing_prompt(
                    request, evidence, sketched.output, most_colors, revision
                )
            else:
                prompt = self._generation_prompt(
                    request, evidence, widths, heights, most_colors
                )
                if revision:
                    prompt = f'{prompt}\n\n{revision}'
            result = await self._ask(
                prompt,
                self._output_for(check),
                operation='generate',
                message_history=history,
            )
        except TerminalError as error:
            self.last_generation = attempts.report(
                self.strategy, sketch=check.composition
            )
            if error.code == 'ai.generation':
                raise self._generation_error(attempts, 'generate') from error
            raise
        text: ArtText = result.output
        return text, attempts.report(self.strategy, sketch=check.composition)

    def _sketch_output(self, check: _Checker) -> object:
        def sketch(
            layout: _Layout,
            palette: list[_Color],
            width_in_blocks: int,
            height_in_blocks: int,
            program: str,
        ) -> _Sketch:
            """Give the layout, the palette of the masses and the size of the sketch in blocks (the piece is twice that in pixels), then the Python program that paints the masses on W = width_in_blocks by H = height_in_blocks blocks."""
            return check.sketch(palette, width_in_blocks, height_in_blocks, program)

        return ToolOutput(sketch, name='sketch')

    def _output_for(self, check: _Checker) -> object:
        strategy = self.strategy
        if strategy == 'svg':

            def draw_svg(
                layout: _Layout, palette: list[_Color], width: int, height: int, svg: str
            ) -> ArtText:
                """Give the layout, the palette and the size in pixels, then the SVG, painted with the palette's colours or letters."""
                return check.svg(palette, width, height, svg)

            return ToolOutput(draw_svg, name='draw_svg')

        def draw_program(
            layout: _Layout, palette: list[_Color], width: int, height: int, program: str
        ) -> ArtText:
            """Give the layout, the palette and the size, then the program that paints the letters."""
            return check.program(palette, width, height, program)

        return ToolOutput(draw_program, name='draw_program')

    def _generation_prompt(
        self,
        request: str,
        evidence: object,
        widths: tuple[int, int],
        heights: tuple[int, int],
        most_colors: int,
    ) -> str:
        """The prompt of a piece drawn in one step: the request, the sizes and references."""
        lines = [
            f'Draw: {request}',
            _size_sentence(widths, heights),
            f'Use at most {most_colors} colours.',
        ]
        lines.extend(
            _reference_text(reference, self.strategy)
            for reference in self._closest_references(request)
        )
        if evidence is not None:
            lines.append(f'What the art is for:\n{evidence_prompt(evidence)}')
        return '\n\n'.join(lines)

    def _sketch_prompt(
        self,
        request: str,
        evidence: object,
        widths: tuple[int, int],
        heights: tuple[int, int],
        most_colors: int,
        revision: str | None,
    ) -> str:
        """The prompt of the sketch: the request and the sizes, and no references."""
        lines = [f'Sketch: {request}', _blocks_sentence(widths, heights)]
        if widths[0] != widths[1] or heights[0] != heights[1]:
            lines.append(
                'Choose the size: about 8 blocks (16 pixels) for an item or an icon, 8 to 12 '
                'blocks for a character or a portrait, and up to 16 blocks for a scene.'
            )
        lines.append(
            f'Name only the masses in the palette; the drawing adds the rest, up to '
            f'{most_colors} colours in all.'
        )
        if evidence is not None:
            lines.append(f'What the art is for:\n{evidence_prompt(evidence)}')
        if revision:
            lines.append(revision)
        return '\n\n'.join(lines)

    def _drawing_prompt(
        self,
        request: str,
        evidence: object,
        sketch: _Sketch,
        most_colors: int,
        revision: str | None,
    ) -> str:
        """The prompt of the drawing: the request, the sketch to keep, and references."""
        lines = [
            f'Draw: {request}',
            (
                f'Your sketch, {sketch.width} by {sketch.height} pixels on {sketch.columns} '
                f'by {len(sketch.rows)} blocks; block (x, y) is the pixels from '
                f'({_BLOCK}x, {_BLOCK}y) to ({_BLOCK}x + {_BLOCK - 1}, {_BLOCK}y + '
                f'{_BLOCK - 1}):\n{sketch.labelled()}'
            ),
            f'Its masses:\n{_palette_text(sketch.palette)}',
        ]
        if self.strategy == 'program':
            lines.append(
                'The sketch is already painted on the canvas at pixel scale when your program '
                'starts. Refine it: round the corners of the masses and shape them (a head '
                'is round, a chin narrower than a brow), then paint the details in flat '
                'colours. Keep the composition of the sketch.'
            )
        else:
            lines.append(
                'Start from the sketch as SVG, below: replace each blocky mass with the shape '
                'it stands for, keeping its place and size, then paint the details in flat '
                f'colours.\n{sketch.svg()}'
            )
        lines.append(
            f'Give the whole palette: the letters of the sketch, and the colours you add, at '
            f'most {most_colors} in all. The size is {sketch.width} by {sketch.height}.'
        )
        lines.extend(
            _reference_text(reference, self.strategy)
            for reference in self._closest_references(request)
        )
        if evidence is not None:
            lines.append(f'What the art is for:\n{evidence_prompt(evidence)}')
        if revision:
            lines.append(revision)
        return '\n\n'.join(lines)

    def _closest_references(self, request: str) -> list[dict[str, object]]:
        return assets._closest(
            _references(), request, fields=('subject', 'tags'), count=2
        )

    def _generation_error(self, attempts: _Attempts, operation: str) -> GenerationError:
        report = attempts.report(self.strategy)
        self.last_generation = report
        return _generation_error(
            f'ArtModel.{operation}()', 'art', self._model_name(), report
        )

    # -- editing ------------------------------------------------------------------------

    def edit_async(
        self,
        art: Art,
        request: str,
        *,
        protect: Sequence[str] = (),
        allow_new_colors: bool = False,
        max_changes: float = 0.5,
        mode: EditMode = 'auto',
        symbol: str | None = None,
    ) -> Coroutine[Any, Any, Art]:
        """
        Change pixel art as asked, with ``await``: a patch of the pixels that change.

        The art itself is not changed: a new [`Art`][xnano.art.Art] is returned, so when the
        edit fails the art you had is still there.

        Args:
            art: The art to change.
            request: The change, such as ``'give the knight a blue cape'``.
            protect: Roles or letters whose pixels must not change, such as
                ``['outline', 'skin']``.
            allow_new_colors: Whether the edit may add colours to the palette.
            max_changes: The largest share of the drawn pixels a patch may change; a
                larger change is drawn again whole (``mode='auto'``) or refused.
            mode: ``'patch'``, ``'redraw'``, or ``'auto'`` for the model to choose.
            symbol: A name to register the new art under in [`symbols`][xnano.symbols].

        Returns:
            A coroutine that gives the new art.

        Raises:
            ValueError: ``mode`` or ``max_changes`` is out of range, or ``protect`` names a
                role or letter the art does not have.
            GenerationError: No answer made a valid edit, when awaited.
        """
        if mode not in ('auto', 'patch', 'redraw'):
            raise ValueError(
                f"mode must be 'auto', 'patch' or 'redraw', but was {mode!r}."
            )
        if isinstance(max_changes, bool) or not 0 < max_changes <= 1:
            raise ValueError(
                f'max_changes must be a share above 0 and at most 1, such as 0.5, but was '
                f'{max_changes!r}.'
            )
        text = ArtText.from_art(art)
        protected = _protected_letters(text, protect)
        return self._edit(
            text, request, protected, allow_new_colors, max_changes, mode, symbol
        )

    def edit(
        self,
        art: Art,
        request: str,
        *,
        protect: Sequence[str] = (),
        allow_new_colors: bool = False,
        max_changes: float = 0.5,
        mode: EditMode = 'auto',
        symbol: str | None = None,
    ) -> Art:
        """
        Change pixel art as asked, waiting for it.

        The same as [`edit_async`][xnano.ai.models.art.ArtModel.edit_async].

        Examples:
            ```python
            from xnano.ai.models.art import ArtModel, ArtText, PaletteColor
            from xnano.ai.testing import scripted_model

            coin = ArtText(
                rows=('.oo.', 'oyyo', '.oo.'),
                palette={
                    'o': PaletteColor('outline', '#1a1c2c'),
                    'y': PaletteColor('base', '#ffcd75'),
                },
            ).to_art()
            patch = {'runs': [{'row': 1, 'column': 1, 'letters': 'oo'}], 'new_colors': []}
            artist = ArtModel(scripted_model(('patch', patch)).model)
            dented = artist.edit(coin, 'put a dent in the middle')
            assert dented.pixel(1, 1) == coin.pixel(0, 1)
            ```
        """
        return _run_blocking(
            self.edit_async(
                art,
                request,
                protect=protect,
                allow_new_colors=allow_new_colors,
                max_changes=max_changes,
                mode=mode,
                symbol=symbol,
            ),
            'edit',
        )

    async def _edit(
        self,
        text: ArtText,
        request: str,
        protected: frozenset[str],
        allow_new_colors: bool,
        max_changes: float,
        mode: EditMode,
        symbol: str | None,
    ) -> Art:
        attempts = _Attempts()
        check = _EditChecker(
            attempts, text, protected, allow_new_colors, max_changes, mode
        )
        outputs: list[object] = []
        if mode in ('auto', 'patch'):

            def patch(runs: list[_Run], new_colors: list[_Color]) -> ArtText:
                """Set the pixels that change, as runs along rows, with any new colours."""
                return check.patch(runs, new_colors)

            outputs.append(ToolOutput(patch, name='patch'))
        if mode in ('auto', 'redraw'):

            def redraw(palette: list[_Color], rows: list[str]) -> ArtText:
                """Draw every row again at the same size, for a change to most of the piece."""
                return check.redraw(palette, rows)

            outputs.append(ToolOutput(redraw, name='redraw'))
        lines = [
            f'Change the art: {request}',
            f'The art, {text.width} by {text.height}, with a column ruler and row numbers:\n'
            f'{text.labelled()}',
            f'Its palette:\n{text.palette_text()}',
        ]
        if protected:
            lines.append(
                'Do not change any pixel drawn with these letters: '
                + ', '.join(sorted(protected))
                + '.'
            )
        if not allow_new_colors:
            lines.append('Use only the colours of the palette.')
        if mode == 'auto':
            lines.append(
                'Give a patch of the pixels that change; redraw only when most of the piece '
                'changes.'
            )
        try:
            result = await self._ask(
                '\n\n'.join(lines),
                outputs if len(outputs) > 1 else outputs[0],
                operation='edit',
            )
        except TerminalError as error:
            if error.code == 'ai.generation':
                raise self._generation_error(attempts, 'edit') from error
            raise
        edited: ArtText = result.output
        self.last_generation = attempts.report(self.strategy)
        return edited.to_art(symbol=symbol)

    def variants_async(
        self, art: Art, requests: Sequence[str], **edit_options: Any
    ) -> Coroutine[Any, Any, list[Art]]:
        """
        Make one edit of the art for each request, all at once, with ``await``.

        Args:
            art: The art to change.
            requests: One change for each variant, such as ``['winter coat', 'chain mail']``.
            edit_options: The keywords of [`edit`][xnano.ai.models.art.ArtModel.edit], for every
                variant.

        Returns:
            A coroutine that gives the variants, in the order of the requests.
        """
        edits = [self.edit_async(art, request, **edit_options) for request in requests]

        async def gather() -> list[Art]:
            return list(await asyncio.gather(*edits))

        return gather()

    def variants(
        self, art: Art, requests: Sequence[str], **edit_options: Any
    ) -> list[Art]:
        """
        Make one edit of the art for each request, all at once, waiting for them.

        The same as [`variants_async`][xnano.ai.models.art.ArtModel.variants_async].
        """
        return _run_blocking(
            self.variants_async(art, requests, **edit_options), 'variants'
        )

    # -- animating ----------------------------------------------------------------------

    def animate_async(
        self, art: Art, request: str, *, frames: int = 2, fps: float = 4.0
    ) -> Coroutine[Any, Any, Animation]:
        """
        Animate pixel art, with ``await``: one patch of the art for each frame.

        Every frame is a patch of the same base art, so the frames never drift away from it.

        Args:
            art: The art to animate.
            request: The motion, such as ``'a two-frame idle bob'``.
            frames: How many frames.
            fps: How many frames are shown each second.

        Returns:
            A coroutine that gives the [`Animation`][xnano.ai.models.art.Animation].

        Raises:
            ValueError: ``frames`` is not a whole number from 2 to 16, or ``fps`` is not
                above 0.
            GenerationError: No answer made valid frames, when awaited.
        """
        if (
            isinstance(frames, bool)
            or not isinstance(frames, int)
            or not 2 <= frames <= 16
        ):
            raise ValueError(
                f'frames must be a whole number from 2 to 16, but was {frames!r}.'
            )
        if isinstance(fps, bool) or not fps > 0:
            raise ValueError(f'fps must be above 0, such as 4, but was {fps!r}.')
        return self._animate(ArtText.from_art(art), request, frames, float(fps))

    def animate(
        self, art: Art, request: str, *, frames: int = 2, fps: float = 4.0
    ) -> Animation:
        """
        Animate pixel art, waiting for it.

        The same as [`animate_async`][xnano.ai.models.art.ArtModel.animate_async].
        """
        return _run_blocking(
            self.animate_async(art, request, frames=frames, fps=fps), 'animate'
        )

    async def _animate(
        self, text: ArtText, request: str, frames: int, fps: float
    ) -> Animation:
        attempts = _Attempts()
        check = _EditChecker(attempts, text, frozenset(), False, 1.0, 'patch')

        def animation(frames_runs: list[list[_Run]]) -> list[ArtText]:
            """Give one list of runs for each frame, each a patch of the base art."""
            if len(frames_runs) != frames:
                raise attempts.refuse(
                    [f'there are {len(frames_runs)} frames, but {frames} were asked for'],
                    then=f'Give exactly {frames} frames.',
                )
            return [check.patch(runs, []) for runs in frames_runs]

        prompt = '\n\n'.join(
            [
                f'Animate the art: {request}. Give {frames} frames, each a patch of the base '
                f'art below (an empty patch shows the base art as it is).',
                f'The base art, {text.width} by {text.height}:\n{text.labelled()}',
                f'Its palette:\n{text.palette_text()}',
            ]
        )
        try:
            result = await self._ask(
                prompt, ToolOutput(animation, name='animation'), operation='animate'
            )
        except TerminalError as error:
            if error.code == 'ai.generation':
                raise self._generation_error(attempts, 'animate') from error
            raise
        texts: list[ArtText] = result.output
        self.last_generation = attempts.report(self.strategy)
        return Animation(frames=tuple(text.to_art() for text in texts), fps=fps)


# -- checking what the model wrote ---------------------------------------------------------


class _Checker:
    """The checks a generated piece passes, and the repairs that are made instead of a retry."""

    def __init__(
        self,
        attempts: _Attempts,
        widths: tuple[int, int],
        heights: tuple[int, int],
        most_colors: int,
        *,
        mirror_widths: tuple[int, int] | None = None,
        is_flat: bool = False,
    ) -> None:
        self.attempts = attempts
        self.is_flat = is_flat
        """Whether the piece keeps its flat colours, without the renderer's outline and shading."""
        self.widths = widths
        self.heights = heights
        self.most_colors = most_colors
        self.composition: _Sketch | None = None
        """The sketch the piece is drawn from, once the model has made one."""
        self.mirror_widths = mirror_widths
        """The widths of the whole piece when the model draws its left half, else ``None``."""

    def sketch(
        self, palette: Sequence[_Color], columns: int, block_rows: int, program: str
    ) -> _Sketch:
        self.attempts.begin()
        problems: list[str] = []
        colors = self.palette(palette, problems)
        width = _pixels_of_blocks(columns, self.widths, 'wide', problems)
        height = _pixels_of_blocks(block_rows, self.heights, 'tall', problems)
        if problems:
            raise self.attempts.refuse(
                problems, then='Send the whole sketch again, fixed.'
            )
        code, _ = _without_code_fence(program)
        try:
            shapes = _run_art_program(code, columns, block_rows)
        except ValueError as error:
            raise self.attempts.refuse(
                [str(error)], then='Send the whole sketch again, fixed.'
            ) from None
        rows = self._painted(columns, block_rows, shapes, colors, problems)
        drawn = sum(letter != _TRANSPARENT for row in rows for letter in row)
        share = drawn / (columns * block_rows)
        if not problems:
            problems.extend(self._half_problems(rows))
        if not problems and share < 0.25:
            problems.append(
                f'the sketch fills {share:.0%} of its {columns} by {block_rows} blocks; its '
                f'coordinates are blocks, not pixels, so centre the subject and let it fill '
                f'most of the grid'
            )
        if problems:
            raise self.attempts.refuse(
                problems, then='Send the whole sketch again, fixed.'
            )
        used = set(''.join(rows))
        self.composition = _Sketch(
            width,
            height,
            tuple(rows),
            {letter: color for letter, color in colors.items() if letter in used},
        )
        return self.composition

    def _with_sketch_colors(
        self, colors: dict[str, PaletteColor], problems: list[str]
    ) -> dict[str, PaletteColor]:
        """The palette of the drawing, with the sketch's letters kept when it left them out."""
        if self.composition is None:
            return colors
        merged = {**self.composition.palette, **colors}
        if len(merged) > self.most_colors >= len(colors):
            problems.append(
                f'with the letters of the sketch the palette has {len(merged)} colours, at '
                f'most {self.most_colors} are allowed'
            )
        return merged

    def palette(
        self, palette: Sequence[_Color], problems: list[str]
    ) -> dict[str, PaletteColor]:
        colors: dict[str, PaletteColor] = {}
        for entry in palette:
            letter = entry.letter.strip()
            if len(letter) != 1 or letter == _TRANSPARENT or letter.isspace():
                problems.append(f'the palette letter {entry.letter!r} is not one letter')
                continue
            if letter in colors:
                problems.append(f'the letter {letter!r} is in the palette twice')
                continue
            try:
                color, was_repaired = _normalized_color(entry.color)
            except ValueError:
                problems.append(f'{letter!r} has the colour {entry.color!r}, not #rrggbb')
                continue
            if was_repaired:
                self.attempts.notes.append(
                    f'the colour {entry.color!r} of {letter!r} read as {color}'
                )
            colors[letter] = PaletteColor(entry.role, color)
        if len(colors) > self.most_colors:
            problems.append(
                f'the palette has {len(colors)} colours, at most {self.most_colors} are allowed'
            )
        return colors

    def rows(self, palette: Sequence[_Color], rows: Sequence[str]) -> ArtText:
        self.attempts.begin()
        problems: list[str] = []
        colors = self.palette(palette, problems)
        width = _expected_width([row.rstrip() for row in rows], self.widths)
        return self._finish(self._cleaned(rows, width), colors, problems)

    def svg(
        self, palette: Sequence[_Color], width: int, height: int, svg: str
    ) -> ArtText:
        self.attempts.begin()
        problems: list[str] = []
        colors = self.palette(palette, problems)
        self._check_size(
            width, height, problems, then='Send the SVG again at an allowed size.'
        )
        colors = self._with_sketch_colors(colors, problems)
        text, was_fenced = _without_code_fence(svg)
        if was_fenced:
            self.attempts.notes.append(
                'the markdown code fence around the SVG was removed'
            )
        text, was_surrounded = _svg_element(text)
        if was_surrounded:
            self.attempts.notes.append('the text around the <svg> element was removed')
        then = 'Send the whole answer again with the SVG fixed.'
        try:
            scene = read_svg(
                text,
                default_size=(width, height),
                named_colors={letter: color.color for letter, color in colors.items()},
            )
        except SvgError as error:
            raise self.attempts.refuse([*problems, *error.problems], then=then) from None
        problems.extend(
            f'{unsupported}; draw only with the supported elements'
            for unsupported in scene.unsupported
        )
        _, _, box_width, box_height = scene.view_box
        if abs(box_width / box_height - width / height) > 0.01:
            problems.append(
                f'the viewBox is {box_width:g} by {box_height:g}, which would stretch art of '
                f'{width} by {height} pixels; use viewBox="0 0 {width} {height}"'
            )
        elif (box_width, box_height) != (width, height):
            self.attempts.notes.append(
                f'the viewBox of {box_width:g} by {box_height:g} was scaled onto {width} by '
                f'{height} pixels'
            )
        self.attempts.notes.extend(scene.notes)
        if not scene.shapes:
            problems.append('the SVG paints nothing: it has no filled or stroked shape')
        if problems:
            raise self.attempts.refuse(problems, then=then)
        sampling = scene.sample(width, height)
        problems.extend(
            f'{shape.source} lies outside the art or has no area, so it draws nothing: '
            f'move it onto the art, give it a size, or remove it'
            for shape in scene.shapes
            if sampling.covered[shape.index] == 0
        )
        hidden = sum(
            1
            for shape in scene.shapes
            if sampling.covered[shape.index] and not sampling.visible[shape.index]
        )
        if hidden:
            self.attempts.notes.append(
                '1 shape is hidden under the shapes painted after it'
                if hidden == 1
                else f'{hidden} shapes are hidden under the shapes painted after them'
            )
        if sampling.rescued:
            listed = ', '.join(
                scene.shapes[index].source for index in sampling.rescued[:4]
            )
            count = len(sampling.rescued)
            self.attempts.notes.append(
                f'1 shape smaller than a pixel was kept as one pixel: {listed}'
                if count == 1
                else f'{count} shapes smaller than a pixel were each kept as one pixel: '
                f'{listed}'
            )
        letters: dict[str, str] = {}
        for letter, color in list(colors.items()):
            if color.color in letters:
                del colors[letter]
                self.attempts.notes.append(
                    f'{letter!r} has the colour of {letters[color.color]!r}, '
                    f'{color.color}, so it was read as {letters[color.color]!r}'
                )
            else:
                letters[color.color] = letter
        unknown: dict[str, str] = {}
        rows: list[str] = []
        for y, row in enumerate(sampling.colors):
            written = []
            for x, color in enumerate(row):
                if color is None:
                    written.append(_TRANSPARENT)
                elif color in letters:
                    written.append(letters[color])
                else:
                    unknown.setdefault(color, scene.shapes[sampling.owners[y][x]].source)
                    written.append(_TRANSPARENT)
            rows.append(''.join(written))
        listed = ', '.join(f'{color} ({letter})' for color, letter in letters.items())
        problems.extend(
            f'{source} paints {color}, which is not a colour of the palette; paint with '
            f'{listed}, or add the colour to the palette'
            for color, source in unknown.items()
        )
        if problems:
            raise self.attempts.refuse(problems, then=then)
        return self._finish(rows, colors, problems)

    def program(
        self, palette: Sequence[_Color], width: int, height: int, program: str
    ) -> ArtText:
        self.attempts.begin()
        problems: list[str] = []
        colors = self.palette(palette, problems)
        self._check_size(
            width, height, problems, then='Send the program again at an allowed size.'
        )
        colors = self._with_sketch_colors(colors, problems)
        code, was_fenced = _without_code_fence(program)
        if was_fenced:
            self.attempts.notes.append(
                'the markdown code fence around the program was removed'
            )
        try:
            shapes = _run_art_program(code, width, height)
        except ValueError as error:
            raise self.attempts.refuse(
                [*problems, str(error)],
                then='Send the whole answer again with the program fixed.',
            ) from None
        if self.composition is not None and (width, height) == (
            self.composition.width,
            self.composition.height,
        ):
            shapes = [*self.composition.shapes(), *shapes]
        return self._finish(
            self._painted(width, height, shapes, colors, problems), colors, problems
        )

    def _painted(
        self,
        width: int,
        height: int,
        shapes: Sequence[Any],
        colors: Mapping[str, PaletteColor],
        problems: list[str],
    ) -> list[str]:
        """The rows the shapes paint in order; a shape with an unknown letter is a problem."""
        grid = [[_TRANSPARENT] * width for _ in range(height)]
        unknown: dict[str, str] = {}
        for index, shape in enumerate(shapes):
            letter = getattr(shape, 'letter', None)
            if letter is not None and letter != _TRANSPARENT and letter not in colors:
                unknown.setdefault(letter, f'{shape.kind} at {index}')
                continue
            _paint(grid, shape)
        problems.extend(
            f'the {first} of the painting order (counting from 0) paints with {letter!r}, '
            f'which the palette does not name'
            for letter, first in unknown.items()
        )
        return [''.join(row) for row in grid]

    def _check_size(
        self, width: int, height: int, problems: list[str], *, then: str
    ) -> None:
        if not (self.widths[0] <= width <= self.widths[1]) or not (
            self.heights[0] <= height <= self.heights[1]
        ):
            problems.append(
                f'the size is {width} by {height}; {_size_sentence(self.widths, self.heights)}'
            )
            raise self.attempts.refuse(problems, then=then)

    def _cleaned(self, rows: Sequence[str], width: int) -> list[str]:
        """
        The rows with their spaces read as transparent pixels.

        Trailing spaces are dropped, unless keeping them as transparent pixels gives the row
        the width of the others.
        """
        cleaned = []
        spaced: list[int] = []
        trimmed: list[int] = []
        for index, row in enumerate(rows):
            kept = row.rstrip()
            filled = row.rstrip('\r\n').replace(' ', _TRANSPARENT)
            if len(filled) == width and len(kept) != width:
                letters = filled
            else:
                letters = kept.replace(' ', _TRANSPARENT)
            if ' ' in kept or (letters == filled and filled != row.rstrip('\r\n')):
                spaced.append(index)
            elif letters != row:
                trimmed.append(index)
            cleaned.append(letters)
        if spaced:
            self.attempts.notes.append(
                f'the spaces in {_rows_phrase(spaced)} were read as transparent pixels'
            )
        if trimmed:
            self.attempts.notes.append(
                f'the trailing spaces of {_rows_phrase(trimmed)} were removed'
            )
        return cleaned

    def _finish(
        self, rows: list[str], colors: dict[str, PaletteColor], problems: list[str]
    ) -> ArtText:
        height = len(rows)
        width = _expected_width(rows, self.widths)
        if not self.heights[0] <= height <= self.heights[1]:
            problems.append(
                f'there are {height} rows; {_size_sentence(self.widths, self.heights)}'
            )
        if not self.widths[0] <= width <= self.widths[1]:
            problems.append(
                f'the rows have {width} pixels; {_size_sentence(self.widths, self.heights)}'
            )
        wrong = [index for index, row in enumerate(rows) if len(row) != width]
        problems.extend(
            f'row {index} has {len(rows[index])} pixels instead of {width}: {rows[index]!r}'
            for index in wrong
        )
        if wrong:
            problems.append(
                f'the rows under a column ruler, to count by:\n{_ruled(chr(10).join(rows), width)}'
            )
        unknown: dict[str, list[int]] = {}
        for index, row in enumerate(rows):
            for letter in sorted(set(row) - set(colors) - {_TRANSPARENT}):
                unknown.setdefault(letter, []).append(index)
        problems.extend(
            f'{letter!r} in {_rows_phrase(indexes)} is not a letter of the palette; use a '
            f'palette letter, {_TRANSPARENT!r} for a transparent pixel, or add it to the palette'
            for letter, indexes in unknown.items()
        )
        used = set(''.join(rows))
        unused = [letter for letter in colors if letter not in used]
        if not problems and unused:
            for letter in unused:
                del colors[letter]
            self.attempts.notes.append(
                f'the unused palette letters {", ".join(map(repr, unused))} were dropped'
            )
        if not problems and used <= {_TRANSPARENT}:
            problems.append('every pixel is transparent')
        if not problems and self.composition is not None:
            problems.extend(self._sketch_problems(rows))
        if not problems:
            problems.extend(self._half_problems(rows))
        if problems:
            raise self.attempts.refuse(
                problems,
                then='Send the whole answer again with these fixed, and nothing else changed.',
            )
        if self.mirror_widths is not None:
            low, high = self.mirror_widths
            odd = low == high and low % 2 == 1
            rows = [_mirrored_row(row, odd=odd) for row in rows]
        if self.is_flat:
            return ArtText(tuple(rows), colors)
        finished = finish(
            rows, {letter: (color.role, color.color) for letter, color in colors.items()}
        )
        self.attempts.notes.extend(finished.notes)
        return ArtText(
            finished.rows,
            {
                letter: PaletteColor(cast('ColorRole', role), color)
                for letter, (role, color) in finished.palette.items()
            },
        )

    def _half_problems(self, rows: Sequence[str]) -> list[str]:
        """Whether a left half reaches the right edge of its canvas, the middle of the piece."""
        if self.mirror_widths is None:
            return []
        with_pixels = [row for row in rows if set(row) - {_TRANSPARENT}]
        reaching = sum(row[-1] != _TRANSPARENT for row in with_pixels)
        if with_pixels and reaching < 0.3 * len(with_pixels):
            return [
                f'only {reaching} of the {len(with_pixels)} rows with pixels reach the right '
                f'edge of the canvas, which is the middle of the whole piece; a symmetrical '
                f'piece is drawn as its left half, up to that edge, not as a whole figure '
                f'centred on the half canvas'
            ]
        return []

    def _sketch_problems(self, rows: Sequence[str]) -> list[str]:
        """Where the drawing left its sketch: the blocks well inside a mass that are empty."""
        sketch = self.composition
        assert sketch is not None
        height, width = len(rows), len(rows[0])
        if (width, height) != (sketch.width, sketch.height):
            return [
                f'the art is {width} by {height}, but the sketch was for {sketch.width} by '
                f'{sketch.height}; draw it at the size of the sketch'
            ]
        empty_inside: list[str] = []
        interior = 0
        for block_y in range(len(sketch.rows)):
            for block_x in range(sketch.columns):
                if not sketch.is_drawn(block_x, block_y):
                    continue
                around = (
                    sketch.is_drawn(block_x + step_x, block_y + step_y)
                    for step_x, step_y in ((1, 0), (-1, 0), (0, 1), (0, -1))
                )
                if any(neighbour is False for neighbour in around):
                    continue  # a block on the edge of a mass may change shape
                interior += 1
                pixels = [
                    rows[y][x]
                    for y in range(block_y * _BLOCK, min((block_y + 1) * _BLOCK, height))
                    for x in range(block_x * _BLOCK, min((block_x + 1) * _BLOCK, width))
                ]
                if sum(pixel != _TRANSPARENT for pixel in pixels) * 2 < len(pixels):
                    empty_inside.append(
                        f'block ({block_x}, {block_y}), pixels ({block_x * _BLOCK}, '
                        f'{block_y * _BLOCK})'
                    )
        if len(empty_inside) >= 3 and len(empty_inside) > 0.3 * interior:
            return [
                f'{len(empty_inside)} blocks inside the masses of the sketch are empty, such '
                f'as {", ".join(empty_inside[:3])}; the drawing abandoned its sketch, and '
                f'must keep its composition'
            ]
        return []


class _EditChecker:
    """The checks an edit passes: inside the art, known letters, protected pixels kept."""

    def __init__(
        self,
        attempts: _Attempts,
        text: ArtText,
        protected: frozenset[str],
        allow_new_colors: bool,
        max_changes: float,
        mode: EditMode,
    ) -> None:
        self.attempts = attempts
        self.text = text
        self.protected = protected
        self.allow_new_colors = allow_new_colors
        self.max_changes = max_changes
        self.mode = mode

    def _new_colors(
        self, new_colors: Sequence[_Color], problems: list[str]
    ) -> dict[str, PaletteColor]:
        if new_colors and not self.allow_new_colors:
            problems.append('new colours were added, but this edit uses only the palette')
            return {}
        checker = _Checker(self.attempts, (1, _MOST_PIXELS), (1, _MOST_PIXELS), 25)
        added = checker.palette(new_colors, problems)
        problems.extend(
            f'the new colour {letter!r} is already a letter of the palette'
            for letter in added
            if letter in self.text.palette
        )
        return added

    def patch(self, runs: Sequence[_Run], new_colors: Sequence[_Color]) -> ArtText:
        self.attempts.begin()
        problems: list[str] = []
        added = self._new_colors(new_colors, problems)
        letters = set(self.text.palette) | set(added) | {_TRANSPARENT}
        patch_runs = []
        for run in runs:
            unknown = sorted(set(run.letters) - letters)
            if unknown:
                problems.append(
                    f'the run at row {run.row}, column {run.column} uses {", ".join(map(repr, unknown))}'
                )
            elif (
                not 0 <= run.row < self.text.height
                or run.column < 0
                or run.column + len(run.letters) > self.text.width
            ):
                problems.append(
                    f'the run at row {run.row}, column {run.column} with {len(run.letters)} letters '
                    f'goes outside the art, which is {self.text.width} by {self.text.height}'
                )
            else:
                patch_runs.append(PixelRun(run.row, run.column, run.letters))
        if problems:
            raise self.attempts.refuse(
                problems, then='Send the patch again with these fixed.'
            )
        patch = ArtPatch(tuple(patch_runs), added)
        drawn = (
            sum(1 for row in self.text.rows for letter in row if letter != _TRANSPARENT)
            or 1
        )
        if patch.pixel_count > self.max_changes * drawn and self.mode != 'patch':
            raise self.attempts.refuse(
                [
                    f'the patch sets {patch.pixel_count} pixels, more than {self.max_changes:.0%} of the {drawn} drawn'
                ],
                then='Redraw the whole piece instead.',
            )
        edited = self.text.apply(patch)
        self._check_protected(edited)
        return edited

    def redraw(self, palette: Sequence[_Color], rows: Sequence[str]) -> ArtText:
        size = (self.text.width, self.text.width)
        checker = _Checker(self.attempts, size, (self.text.height, self.text.height), 25)
        edited = checker.rows(palette, rows)
        problems: list[str] = []
        added = set(edited.palette) - set(self.text.palette)
        if added and not self.allow_new_colors:
            problems.append(
                f'the redraw adds {", ".join(map(repr, sorted(added)))}, but this edit uses only the palette'
            )
        if problems:
            raise self.attempts.refuse(
                problems, then='Send the rows again with these fixed.'
            )
        self._check_protected(edited)
        return edited

    def _check_protected(self, edited: ArtText) -> None:
        if not self.protected:
            return
        changed = []
        for y, (before, after) in enumerate(
            zip(self.text.rows, edited.rows, strict=True)
        ):
            for x, (old, new) in enumerate(zip(before, after, strict=True)):
                if old in self.protected and new != old:
                    changed.append(f'({x}, {y})')
        if changed:
            raise self.attempts.refuse(
                [f'protected pixels changed at {", ".join(changed[:12])}'],
                then='Leave every pixel of the protected letters as it is.',
            )


# -- shapes, programs and sizes ------------------------------------------------------------


def _paint(grid: list[list[str]], shape: Any) -> None:
    height, width = len(grid), len(grid[0])

    def put(x: int, y: int, letter: str) -> None:
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = letter

    kind = shape.kind
    if kind == 'rectangle':
        for y in range(shape.y, shape.y + shape.height):
            for x in range(shape.x, shape.x + shape.width):
                edge = y in (shape.y, shape.y + shape.height - 1) or x in (
                    shape.x,
                    shape.x + shape.width - 1,
                )
                if shape.is_filled or edge:
                    put(x, y, shape.letter)
    elif kind == 'ellipse':
        center_x = shape.x + (shape.width - 1) / 2
        center_y = shape.y + (shape.height - 1) / 2
        radius_x = max(shape.width / 2, 0.5)
        radius_y = max(shape.height / 2, 0.5)
        for y in range(shape.y, shape.y + shape.height):
            for x in range(shape.x, shape.x + shape.width):
                distance = ((x - center_x) / radius_x) ** 2 + (
                    (y - center_y) / radius_y
                ) ** 2
                inner = ((x - center_x) / max(radius_x - 1, 0.5)) ** 2 + (
                    (y - center_y) / max(radius_y - 1, 0.5)
                ) ** 2
                if distance <= 1.0 and (shape.is_filled or inner > 1.0):
                    put(x, y, shape.letter)
    elif kind == 'line':
        for x, y in _line_points(shape.x1, shape.y1, shape.x2, shape.y2):
            put(x, y, shape.letter)
    elif kind == 'polygon':
        points = shape.points
        if shape.is_filled and len(points) >= 3:
            for y in range(height):
                crossings = []
                for (x1, y1), (x2, y2) in zip(
                    points, [*points[1:], points[0]], strict=True
                ):
                    if (y1 <= y < y2) or (y2 <= y < y1):
                        crossings.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
                crossings.sort()
                for start, end in zip(crossings[::2], crossings[1::2], strict=False):
                    for x in range(math.ceil(start), math.floor(end) + 1):
                        put(x, y, shape.letter)
        for (x1, y1), (x2, y2) in zip(points, [*points[1:], points[0]], strict=True):
            for x, y in _line_points(x1, y1, x2, y2):
                put(x, y, shape.letter)
    elif kind == 'fill':
        if not (0 <= shape.x < width and 0 <= shape.y < height):
            return
        target = grid[shape.y][shape.x]
        if target == shape.letter:
            return
        stack = [(shape.x, shape.y)]
        while stack:
            x, y = stack.pop()
            if 0 <= x < width and 0 <= y < height and grid[y][x] == target:
                grid[y][x] = shape.letter
                stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    elif kind == 'outline':
        drawn = {
            (x, y)
            for y, row in enumerate(grid)
            for x, letter in enumerate(row)
            if letter != _TRANSPARENT
        }
        around = {
            (x + step_x, y + step_y)
            for x, y in drawn
            for step_x, step_y in ((1, 0), (-1, 0), (0, 1), (0, -1))
        }
        for x, y in around - drawn:
            put(x, y, shape.letter)
    elif kind == 'mirror':
        if shape.axis == 'horizontal':
            for row in grid:
                for x in range(width // 2):
                    row[width - 1 - x] = row[x]
        else:
            for y in range(height // 2):
                grid[height - 1 - y] = list(grid[y])


def _line_points(x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
    """The pixels of a line from one point to another, with no gaps."""
    points = []
    dx, dy = abs(x2 - x1), -abs(y2 - y1)
    step_x, step_y = (1 if x1 < x2 else -1), (1 if y1 < y2 else -1)
    error = dx + dy
    x, y = x1, y1
    while True:
        points.append((x, y))
        if (x, y) == (x2, y2) or len(points) > 4 * _MOST_PIXELS:
            return points
        doubled = 2 * error
        if doubled >= dy:
            error += dy
            x += step_x
        if doubled <= dx:
            error += dx
            y += step_y


def _run_art_program(program: str, width: int, height: int) -> list[Any]:
    """Run an art program in a sandbox on a canvas of ``width`` by ``height``; return its shapes."""
    from xnano._internal._optional import require

    monty = require('monty', needed_for="ArtModel(strategy='program')")
    prelude = _PROGRAM_PRELUDE.replace('{width}', str(width)).replace(
        '{height}', str(height)
    )
    with (
        monty.Monty(min_processes=1, max_processes=1) as pool,
        pool.checkout(
            script_name='art.py',
            limits={'max_feed_duration_secs': 2.0, 'max_memory': 64 * 1024 * 1024},
            type_check=True,
        ) as session,
    ):
        session.feed_run(prelude)
        try:
            session.feed_run(program)
        except monty.MontyError as error:
            raise ValueError(f'the program failed: {error}') from None
        painting = session.feed_run('painting')
    if not isinstance(painting, list):
        raise ValueError(
            'the program replaced the list painting, which the drawing functions fill; '
            'leave it alone'
        )
    if len(painting) > _MOST_PAINTING_CALLS:
        raise ValueError(
            f'the program made {len(painting)} drawing calls; keep it under '
            f'{_MOST_PAINTING_CALLS} by drawing rectangles instead of single pixels'
        )
    try:
        return [_painted_shape(call) for call in painting]
    except (TypeError, ValueError) as error:
        raise ValueError(f'a drawing call could not be read: {error}') from None


def _painted_shape(call: object) -> Any:
    """One recorded drawing call as the shape it paints."""
    if not isinstance(call, (list, tuple)) or not call:
        raise ValueError(f'{call!r} is not a drawing call')
    kind, *values = call

    def whole(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f'{kind} takes numbers as coordinates, but got {value!r}')
        return math.floor(value + 0.5)

    if kind == 'rectangle':
        x, y, width, height, letter, is_filled = values
        return _Rectangle(
            kind='rectangle',
            x=whole(x),
            y=whole(y),
            width=whole(width),
            height=whole(height),
            letter=letter,
            is_filled=bool(is_filled),
        )
    if kind == 'ellipse':
        x, y, width, height, letter, is_filled = values
        return _Ellipse(
            kind='ellipse',
            x=whole(x),
            y=whole(y),
            width=whole(width),
            height=whole(height),
            letter=letter,
            is_filled=bool(is_filled),
        )
    if kind == 'line':
        x1, y1, x2, y2, letter = values
        return _Line(
            kind='line',
            x1=whole(x1),
            y1=whole(y1),
            x2=whole(x2),
            y2=whole(y2),
            letter=letter,
        )
    if kind == 'polygon':
        points, letter, is_filled = values
        if not isinstance(points, (list, tuple)) or not all(
            isinstance(point, (list, tuple)) and len(point) == 2 for point in points
        ):
            raise TypeError(f'polygon takes points as [(x, y), ...], but got {points!r}')
        return _Polygon(
            kind='polygon',
            points=[(whole(x), whole(y)) for x, y in points],
            letter=letter,
            is_filled=bool(is_filled),
        )
    if kind == 'fill':
        x, y, letter = values
        return _Fill(kind='fill', x=whole(x), y=whole(y), letter=letter)
    if kind == 'outline':
        (letter,) = values
        return _Outline(kind='outline', letter=letter)
    (axis,) = values
    return _Mirror(kind='mirror', axis=axis)


def _pixel_range(size: object, axis: str) -> tuple[int, int]:
    """The lowest and highest number of pixels a size allows along ``axis``."""
    if size is None:
        return (1, _DEFAULT_MOST)
    if isinstance(size, tuple):
        if len(size) != 2:
            raise ValueError(
                f'A {axis} range is a (low, high) pair, such as (8, 32), but was {size!r}.'
            )
        low, high = size
        low = 1 if low is None else _whole_pixels(low, axis)
        high = _DEFAULT_MOST if high is None else _whole_pixels(high, axis)
        if low > high:
            raise ValueError(
                f'The {axis} range {size!r} has its low end above its high end.'
            )
        return (low, high)
    if isinstance(size, int) and not isinstance(size, bool):
        pixels = _whole_pixels(size, axis)
        return (pixels, pixels)
    import xnano

    # A share of the canvas or an expression is measured like a box: a cell is one pixel wide and
    # two pixels tall.
    measured = xnano.box(size, 1) if axis == 'width' else xnano.box(1, size)  # type: ignore[arg-type]
    cells = int(measured.width if axis == 'width' else measured.height)
    pixels = _whole_pixels(cells if axis == 'width' else cells * 2, axis)
    return (pixels, pixels)


def _whole_pixels(value: object, axis: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= _MOST_PIXELS
    ):
        raise ValueError(
            f'The {axis} of art must be a whole number of pixels from 1 to {_MOST_PIXELS}, '
            f'but was {value!r}. Pass a number such as 16, a range such as (8, 32), or a '
            f"share of the canvas such as '50%'."
        )
    return value


def _expected_width(rows: Sequence[str], widths: tuple[int, int]) -> int:
    """The width every row should have: the asked width, or the most common allowed one."""
    low, high = widths
    if low == high:
        return low
    lengths = [len(row) for row in rows]
    allowed = [length for length in lengths if low <= length <= high] or lengths
    if not allowed:
        return low
    return max(dict.fromkeys(allowed), key=allowed.count)


def _rows_phrase(indexes: Sequence[int]) -> str:
    """``row 3``, or ``rows 1, 4 and 6``."""
    if len(indexes) == 1:
        return f'row {indexes[0]}'
    return f'rows {", ".join(map(str, indexes[:-1]))} and {indexes[-1]}'


def _without_code_fence(text: str) -> tuple[str, bool]:
    """The text without a markdown code fence around it, and whether it had one."""
    stripped = text.strip()
    if not stripped.startswith('```'):
        return text, False
    lines = stripped.splitlines()[1:]
    if lines and lines[-1].strip().startswith('```'):
        lines = lines[:-1]
    return '\n'.join(lines), True


def _svg_element(text: str) -> tuple[str, bool]:
    """The ``<svg>`` element alone, and whether there was text around it."""
    start, end = text.find('<svg'), text.rfind('</svg>')
    if start == -1 or end < start:
        return text, False
    after = end + len('</svg>')
    return text[start:after], bool(text[:start].strip() or text[after:].strip())


def _dotted(text: ArtText) -> ArtText:
    """
    The art as braille line art: solid along the edges, a light pattern of dots inside.

    A pixel on an edge (a neighbour is transparent or another colour) stays; inside its
    colour, one pixel in four stays, so the region shows as a light field of dots.
    """
    rows = text.rows
    height, width = len(rows), len(rows[0])

    def is_edge(x: int, y: int) -> bool:
        letter = rows[y][x]
        return any(
            not (0 <= x + step_x < width and 0 <= y + step_y < height)
            or rows[y + step_y][x + step_x] != letter
            for step_x in (-1, 0, 1)
            for step_y in (-1, 0, 1)
        )

    dotted = tuple(
        ''.join(
            letter
            if letter == _TRANSPARENT or is_edge(x, y) or (x % 2 == 0 and y % 2 == 0)
            else _TRANSPARENT
            for x, letter in enumerate(row)
        )
        for y, row in enumerate(rows)
    )
    return ArtText(dotted, dict(text.palette))


def _half_widths(widths: tuple[int, int]) -> tuple[int, int]:
    """The widths of the left half of a piece with these widths."""
    return (-(-widths[0] // 2), -(-widths[1] // 2))


def _mirrored_row(half: str, *, odd: bool) -> str:
    """A row made of its left half and the mirror image; an odd row shares its middle."""
    return half + (half[-2::-1] if odd else half[::-1])


def _blocks_of_pixels(pixels: int) -> int:
    """How many blocks of the sketch cover this many pixels."""
    return -(-pixels // _BLOCK)


def _pixels_of_blocks(
    blocks: int, allowed: tuple[int, int], axis: str, problems: list[str]
) -> int:
    """The pixels a sketch of ``blocks`` blocks stands for along one axis, within ``allowed``."""
    low, high = allowed
    if low == high:
        if blocks != _blocks_of_pixels(low):
            problems.append(
                f'the piece is exactly {low} pixels {axis}, which is '
                f'{_blocks_of_pixels(low)} blocks, but the sketch is {blocks} blocks {axis}'
            )
        return low
    pixels = blocks * _BLOCK
    if not low <= pixels <= high:
        problems.append(
            f'{blocks} blocks is {pixels} pixels {axis}; the sketch must be from '
            f'{_blocks_of_pixels(low)} to {high // _BLOCK} blocks {axis}'
        )
    return pixels


def _blocks_sentence(widths: tuple[int, int], heights: tuple[int, int]) -> str:
    """How large the sketch may be, in blocks."""

    def part(axis: str, low: int, high: int) -> str:
        if low == high:
            return f'exactly {_blocks_of_pixels(low)} blocks {axis} ({low} pixels)'
        return (
            f'from {_blocks_of_pixels(low)} to {high // _BLOCK} blocks {axis} ({low} to '
            f'{high} pixels)'
        )

    return f'The sketch must be {part("wide", *widths)} and {part("tall", *heights)}.'


def _size_sentence(widths: tuple[int, int], heights: tuple[int, int]) -> str:
    def part(axis: str, low: int, high: int) -> str:
        return (
            f'exactly {low} pixels {axis}'
            if low == high
            else f'from {low} to {high} pixels {axis}'
        )

    return f'The art must be {part("wide", *widths)} and {part("tall", *heights)}.'


def _palette_text(palette: Mapping[str, PaletteColor]) -> str:
    """A palette as one line per letter, ``o = outline #1a1c2c``."""
    return '\n'.join(
        f'{letter} = {color.role} {color.color}' for letter, color in palette.items()
    )


def _references() -> list[dict[str, object]]:
    """The installed ``art-references`` library, and the built-in references it does not have."""
    installed = assets._entries('art-references')
    subjects = {entry.get('subject') for entry in installed}
    return [
        *installed,
        *(entry for entry in REFERENCES if entry['subject'] not in subjects),
    ]


def _reference_text(entry: Mapping[str, object], strategy: str) -> str:
    """A reference as the model is shown it: its palette, and the art in the strategy's form."""
    rows = entry.get('rows')
    palette = entry.get('palette')
    if not isinstance(rows, list) or not isinstance(palette, Mapping):
        return ''
    written_rows = [str(row) for row in rows]
    colors = '\n'.join(
        f'{letter} = {color.get("role")} {color.get("color")}'
        for letter, color in palette.items()
        if isinstance(color, Mapping)
    )
    if strategy == 'svg' and isinstance(entry.get('svg'), str):
        written = str(entry['svg']).strip()
        form = 'as SVG'
    elif strategy == 'svg':
        written = traced_svg(
            written_rows,
            {
                str(letter): str(color.get('color'))
                for letter, color in palette.items()
                if isinstance(color, Mapping)
            },
        )
        form = 'as SVG traced from its pixels'
    elif isinstance(entry.get('program'), str):
        written = str(entry['program']).rstrip()
        form = 'as a program'
    else:
        written = _reference_program(written_rows)
        form = 'as a program of rectangles traced from its pixels'
    return (
        f'A reference: {entry.get("subject")}, {entry.get("width")} by '
        f'{entry.get("height")}, {form}:\n{colors}\n{written}'
    )


def _rectangles_of(
    grid: Sequence[Sequence[str | None]],
) -> list[tuple[int, int, int, int, str]]:
    """
    Disjoint rectangles covering every cell of the grid that is not ``None``.

    Each is ``(x, y, width, height, letter)``; the largest come first, so a drawing reads as
    its masses before its details.
    """
    height = len(grid)
    width = len(grid[0]) if grid else 0
    taken = [[False] * width for _ in range(height)]
    rectangles: list[tuple[int, int, int, int, str]] = []
    for y in range(height):
        for x in range(width):
            letter = grid[y][x]
            if letter is None or taken[y][x]:
                continue
            run = 1
            while (
                x + run < width and grid[y][x + run] == letter and not taken[y][x + run]
            ):
                run += 1
            rows = 1
            while y + rows < height and all(
                grid[y + rows][x + offset] == letter and not taken[y + rows][x + offset]
                for offset in range(run)
            ):
                rows += 1
            for row in range(y, y + rows):
                for column in range(x, x + run):
                    taken[row][column] = True
            rectangles.append((x, y, run, rows, letter))
    rectangles.sort(key=lambda rectangle: -(rectangle[2] * rectangle[3]))
    return rectangles


def _traced_drawing(
    rows: Sequence[str],
) -> list[tuple[int, int, int, int, str] | None]:
    """
    The rectangles that redraw the rows, with ``None`` where the left half is mirrored.

    A piece whose drawn pixels are at least 80 percent symmetric is drawn as its left half,
    a mirror, and the pixels that differ; the rest as rectangles alone.
    """
    width = len(rows[0]) if rows else 0
    grid: list[list[str | None]] = [
        [None if letter == _TRANSPARENT else letter for letter in row] for row in rows
    ]
    drawn = same = 0
    for row in rows:
        for x, letter in enumerate(row):
            if letter == _TRANSPARENT and row[-1 - x] == _TRANSPARENT:
                continue
            drawn += 1
            same += letter == row[-1 - x]
    if drawn == 0 or same / drawn < 0.8:
        return list(_rectangles_of(grid))
    half = (width + 1) // 2
    left = [row[:half] for row in grid]
    drawing: list[tuple[int, int, int, int, str] | None] = list(_rectangles_of(left))
    drawing.append(None)
    differences: list[list[str | None]] = []
    for row in rows:
        mirrored = row[:half] + row[: width // 2][::-1]
        differences.append(
            [
                None if letter == twin else letter
                for letter, twin in zip(row, mirrored, strict=True)
            ]
        )
    drawing.extend(_rectangles_of(differences))
    return drawing


def _reference_program(rows: Sequence[str]) -> str:
    lines = []
    for rectangle in _traced_drawing(rows):
        if rectangle is None:
            lines.append('mirror_x()')
            continue
        x, y, width, height, letter = rectangle
        if width == height == 1:
            lines.append(f'pixel({x}, {y}, {letter!r})')
        else:
            lines.append(f'rect({x}, {y}, {width}, {height}, {letter!r})')
    return '\n'.join(lines)


def _protected_letters(text: ArtText, protect: Sequence[str]) -> frozenset[str]:
    if isinstance(protect, str):
        protect = (protect,)
    letters = set()
    for item in protect:
        by_role = [letter for letter, color in text.palette.items() if color.role == item]
        if by_role:
            letters.update(by_role)
        elif item in text.palette:
            letters.add(item)
        else:
            roles = sorted({color.role for color in text.palette.values()})
            raise ValueError(
                f'protect names {item!r}, which is neither a role nor a letter of the art. '
                f'Its roles are {", ".join(roles)} and its letters '
                f'{", ".join(map(repr, text.palette))}.'
            )
    return frozenset(letters)


def _quality(text: ArtText, report: GenerationReport) -> tuple[float, int, int]:
    """How good a candidate is: how connected its pixels are, then the fewest repairs."""
    return (_connected_share(text), -len(report.problems), -len(report.notes))


def _connected_share(text: ArtText) -> float:
    """The share of the drawn pixels in the largest group of touching ones."""
    drawn = {
        (x, y)
        for y, row in enumerate(text.rows)
        for x, letter in enumerate(row)
        if letter != _TRANSPARENT
    }
    if not drawn:
        return 0.0
    largest = 0
    unseen = set(drawn)
    while unseen:
        stack = [unseen.pop()]
        size = 0
        while stack:
            x, y = stack.pop()
            size += 1
            for neighbour in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    stack.append(neighbour)
        largest = max(largest, size)
    return largest / len(drawn)


def _check_critique(rounds: object) -> int:
    if isinstance(rounds, bool) or not isinstance(rounds, int) or not 0 <= rounds <= 3:
        raise ValueError(
            f'critique must be a whole number of rounds from 0 to 3, but was {rounds!r}.'
        )
    return rounds


_PNG_SIZE: Final = 256
"""About how many pixels wide and tall the image a critic sees is."""


def _png_of(text: ArtText) -> bytes:
    """The art as a PNG image, each pixel scaled up to a square, on a light grey ground."""
    scale = max(1, _PNG_SIZE // max(text.width, text.height))
    colors = {
        letter: bytes.fromhex(color.color[1:]) for letter, color in text.palette.items()
    }
    ground = bytes((0xE0, 0xE0, 0xE0))
    rows = []
    for row in text.rows:
        line = b''.join(colors.get(letter, ground) * scale for letter in row)
        rows.extend([b'\x00' + line] * scale)

    def chunk(kind: bytes, data: bytes) -> bytes:
        checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', checksum)

    header = struct.pack(
        '>IIBBBBB', text.width * scale, text.height * scale, 8, 2, 0, 0, 0
    )
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', header)
        + chunk(b'IDAT', zlib.compress(b''.join(rows)))
        + chunk(b'IEND', b'')
    )


# -- animations ----------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class Animation:
    """
    Frames of pixel art shown one after another: what [`ArtModel.animate`][xnano.ai.models.art.ArtModel.animate] makes.

    Write it like art, with ``canvas.screen.write(animation)``: it shows the frame the
    canvas's clock is on, and moves to the next one ``fps`` times a second.

    Attributes:
        frames: The frames, in order.
        fps: How many frames are shown each second.

    Examples:
        ```python
        import xnano
        from xnano.ai.models.art import Animation

        blink = Animation(
            frames=(xnano.pixel_art(['#'], {'#': 'white'}), xnano.pixel_art(['.'], {})),
            fps=2,
        )
        with xnano.new(width=2, height=1) as canvas:
            canvas.screen.write(blink)
            assert blink.frame_at(0.0) is blink.frames[0]
            assert blink.frame_at(0.5) is blink.frames[1]
        ```
    """

    frames: tuple[Art, ...]
    fps: float

    def __post_init__(self) -> None:
        """Check the frames and the rate."""
        if not self.frames:
            raise ValueError('An Animation needs at least one frame.')
        if isinstance(self.fps, bool) or not self.fps > 0:
            raise ValueError(f'fps must be above 0, such as 4, but was {self.fps!r}.')

    def frame_at(self, seconds: float) -> Art:
        """The frame shown ``seconds`` after the animation started."""
        return self.frames[int(seconds * self.fps) % len(self.frames)]

    def __xnano_write__(self, context: Context[object, object]) -> Art:
        """The frame the canvas's clock is on."""
        return self.frame_at(context.clock.elapsed_seconds)
