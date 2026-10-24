"""
xnano.ai.models._art_pixelize

Pixel art read out of a picture that an image model drew in the pixel-art style.

Such a picture is a sprite scaled up on a flat background, drawn with large square pixels of
its own. The picture's pixel grid is found from where its colours change, one sample is taken
at the centre of each cell (never a blur across cells, which would soften the edges), the
background is keyed out, the sprite is cropped to its bounds, shrunk by a whole factor when it
is larger than the size asked for, and its colours are reduced to a palette.
"""

from __future__ import annotations

import dataclasses
import math
from collections import Counter
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from xnano_image import TerminalImage

Color = tuple[int, int, int]

_SMALLEST_PITCH: Final = 6
_LARGEST_PITCH: Final = 64
_KEY_DISTANCE: Final = 48.0
"""How far a colour may be from the background colour and still count as background."""
_FRINGE_DISTANCE: Final = 110.0
"""How far a colour beside the background may be from it and still be its fringe."""
_SAME_COLOR: Final = 20.0
"""Two palette colours closer than this are one colour."""
_LETTERS: Final = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


@dataclasses.dataclass(frozen=True, slots=True)
class Pixelized:
    """The sprite read out of a picture."""

    rows: tuple[str, ...]
    """The sprite, one letter per pixel and ``'.'`` for the background."""
    palette: dict[str, str]
    """Each letter's colour as ``'#rrggbb'``, the darkest first."""
    pitch: int
    """How many picture pixels one pixel of the sprite measured."""
    shrink: int
    """The whole factor the sprite was shrunk by to fit the size asked for; 1 for none."""


def pixelize(
    picture: TerminalImage,
    *,
    widths: tuple[int, int],
    heights: tuple[int, int],
    most_colors: int,
) -> Pixelized:
    """
    Read the sprite out of a picture drawn in the pixel-art style.

    Args:
        picture: The picture, a sprite on a flat background.
        widths: The lowest and highest width the sprite may have, in pixels.
        heights: The lowest and highest height, in pixels.
        most_colors: The most colours the sprite may have.

    Raises:
        ValueError: The picture has no sprite on its background.
    """
    grid = _colors_of(picture)
    pitch = min(_pitch_of(_edges(grid, 0)), _pitch_of(_edges(grid, 1)))
    phase_x = _phase_of(_edges(grid, 0), pitch)
    phase_y = _phase_of(_edges(grid, 1), pitch)
    centres_x = range(phase_x % pitch + pitch // 2, len(grid[0]), pitch)
    centres_y = range(phase_y % pitch + pitch // 2, len(grid), pitch)
    samples = [[_sample(grid, x, y) for x in centres_x] for y in centres_y]
    keyed = _keyed(samples, _background_of(samples))
    drawn = [
        (x, y) for y, row in enumerate(keyed) for x, pixel in enumerate(row) if pixel
    ]
    if not drawn:
        raise ValueError(
            'The picture has no sprite on its background: every sample matched the '
            'background colour.'
        )
    left, right = min(x for x, _ in drawn), max(x for x, _ in drawn)
    top, bottom = min(y for _, y in drawn), max(y for _, y in drawn)
    cropped = [row[left : right + 1] for row in keyed[top : bottom + 1]]
    shrink = max(
        1,
        math.ceil(len(cropped[0]) / widths[1]),
        math.ceil(len(cropped) / heights[1]),
    )
    if shrink > 1:
        cropped = _shrunk(cropped, shrink)
    quantized = _quantized(cropped, most_colors)
    colors = sorted(
        {pixel for row in quantized for pixel in row if pixel is not None},
        key=lambda color: sum(color),
    )
    letters = {color: _LETTERS[index] for index, color in enumerate(colors)}
    rows = tuple(
        ''.join('.' if pixel is None else letters[pixel] for pixel in row)
        for row in quantized
    )
    palette = {
        letter: f'#{color[0]:02x}{color[1]:02x}{color[2]:02x}'
        for color, letter in letters.items()
    }
    return Pixelized(rows, palette, pitch, shrink)


def _colors_of(picture: TerminalImage) -> list[list[Color]]:
    data = picture.to_rgba()
    width = picture.width
    return [
        [
            (
                data[(y * width + x) * 4],
                data[(y * width + x) * 4 + 1],
                data[(y * width + x) * 4 + 2],
            )
            for x in range(width)
        ]
        for y in range(picture.height)
    ]


def _edges(grid: list[list[Color]], axis: int) -> list[float]:
    """How much the colours change between neighbouring columns (axis 0) or rows (axis 1)."""
    height, width = len(grid), len(grid[0])
    step = 4
    if axis == 0:
        return [
            float(
                sum(_distance(grid[y][x - 1], grid[y][x]) for y in range(0, height, step))
            )
            if x
            else 0.0
            for x in range(width)
        ]
    return [
        float(sum(_distance(grid[y - 1][x], grid[y][x]) for x in range(0, width, step)))
        if y
        else 0.0
        for y in range(height)
    ]


def _pitch_of(profile: Sequence[float]) -> int:
    """The period at which the edges repeat most strongly: the size of a drawn pixel."""
    mean = sum(profile) / len(profile)
    centred = [value - mean for value in profile]
    best, best_score = _SMALLEST_PITCH, float('-inf')
    for period in range(_SMALLEST_PITCH, min(_LARGEST_PITCH, len(centred) // 4) + 1):
        pairs = len(centred) - period
        score = sum(centred[i] * centred[i + period] for i in range(pairs)) / pairs
        # A multiple of the pitch scores almost as well; the shortest period wins a near tie.
        if score > best_score * 1.05 if best_score > 0 else score > best_score:
            best, best_score = period, score
    return best


def _phase_of(profile: Sequence[float], pitch: int) -> int:
    """Where the grid lines fall within a period."""
    sums = [0.0] * pitch
    for index, value in enumerate(profile):
        sums[index % pitch] += value
    return max(range(pitch), key=lambda offset: sums[offset])


def _sample(grid: list[list[Color]], x: int, y: int) -> Color:
    """The colour at a cell's centre: the median of the 3 by 3 pixels around it."""
    around = [
        grid[y + step_y][x + step_x]
        for step_y in (-1, 0, 1)
        for step_x in (-1, 0, 1)
        if 0 <= y + step_y < len(grid) and 0 <= x + step_x < len(grid[0])
    ]
    return tuple(
        sorted(pixel[channel] for pixel in around)[len(around) // 2]
        for channel in range(3)
    )  # type: ignore[return-value]


def _background_of(samples: list[list[Color]]) -> Color:
    """The colour that fills most of the picture's border."""
    border: Counter[Color] = Counter()
    for row in (samples[0], samples[-1]):
        border.update(_coarse(pixel) for pixel in row)
    for row in samples:
        border.update((_coarse(row[0]), _coarse(row[-1])))
    return border.most_common(1)[0][0]


def _keyed(samples: list[list[Color]], key: Color) -> list[list[Color | None]]:
    """
    The samples with the background removed.

    The background is every sample near the key colour that touches the picture's border,
    directly or through other such samples; a sprite's own pixels of a similar colour stay.
    """
    height, width = len(samples), len(samples[0])
    is_key = [[_distance(pixel, key) < _KEY_DISTANCE for pixel in row] for row in samples]
    removed = [[False] * width for _ in range(height)]
    queue = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if (x in (0, width - 1) or y in (0, height - 1)) and is_key[y][x]
    ]
    for x, y in queue:
        removed[y][x] = True
    while queue:
        x, y = queue.pop()
        for step_x, step_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            next_x, next_y = x + step_x, y + step_y
            if (
                0 <= next_x < width
                and 0 <= next_y < height
                and is_key[next_y][next_x]
                and not removed[next_y][next_x]
            ):
                removed[next_y][next_x] = True
                queue.append((next_x, next_y))
    # The fringe: a sample beside the background that is tinted toward it belongs to it.
    for y in range(height):
        for x in range(width):
            if removed[y][x] or _distance(samples[y][x], key) >= _FRINGE_DISTANCE:
                continue
            if any(
                0 <= x + step_x < width
                and 0 <= y + step_y < height
                and removed[y + step_y][x + step_x]
                for step_x, step_y in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                removed[y][x] = True
    return [
        [None if removed[y][x] else samples[y][x] for x in range(width)]
        for y in range(height)
    ]


def _coarse(color: Color) -> Color:
    return tuple(channel // 24 * 24 + 12 for channel in color)  # type: ignore[return-value]


def _distance(first: Color, second: Color) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second, strict=True)))


def _shrunk(pixels: list[list[Color | None]], factor: int) -> list[list[Color | None]]:
    """
    The pixels shrunk by a whole factor.

    Each block of ``factor`` by ``factor`` pixels becomes its centre pixel, which keeps lines
    and edges crisp; a block that is mostly background becomes background, and one whose
    centre is background but which is mostly drawn takes its most common colour.
    """
    shrunk: list[list[Color | None]] = []
    for y in range(0, len(pixels), factor):
        line: list[Color | None] = []
        for x in range(0, len(pixels[0]), factor):
            block = [
                pixels[row][column]
                for row in range(y, min(y + factor, len(pixels)))
                for column in range(x, min(x + factor, len(pixels[0])))
            ]
            opaque = [pixel for pixel in block if pixel is not None]
            if len(opaque) * 2 < len(block):
                line.append(None)
                continue
            centre = pixels[min(y + factor // 2, len(pixels) - 1)][
                min(x + factor // 2, len(pixels[0]) - 1)
            ]
            line.append(
                centre if centre is not None else Counter(opaque).most_common(1)[0][0]
            )
        shrunk.append(line)
    return shrunk


def _quantized(
    pixels: list[list[Color | None]], most_colors: int
) -> list[list[Color | None]]:
    """The pixels with their colours reduced to at most ``most_colors`` by a median cut."""
    opaque = [pixel for row in pixels for pixel in row if pixel is not None]
    boxes: list[list[Color]] = [opaque]
    while len(boxes) < most_colors:
        boxes.sort(key=_spread, reverse=True)
        box = boxes.pop(0)
        if len(box) <= 1 or _spread(box) < 24:
            boxes.append(box)
            break
        channel = max(range(3), key=lambda index: _range(box, index))
        box.sort(key=lambda color: color[channel])
        half = len(box) // 2
        boxes.extend([box[:half], box[half:]])
    centres: list[Color] = []
    for box in sorted((box for box in boxes if box), key=len, reverse=True):
        centre: Color = tuple(  # type: ignore[assignment]
            round(sum(color[channel] for color in box) / len(box)) for channel in range(3)
        )
        if all(_distance(centre, other) >= _SAME_COLOR for other in centres):
            centres.append(centre)

    def nearest(color: Color) -> Color:
        return min(centres, key=lambda centre: _distance(color, centre))

    return [
        [None if pixel is None else nearest(pixel) for pixel in row] for row in pixels
    ]


def _range(box: list[Color], channel: int) -> int:
    return max(color[channel] for color in box) - min(color[channel] for color in box)


def _spread(box: list[Color]) -> int:
    return max(_range(box, channel) for channel in range(3)) if len(box) > 1 else -1
