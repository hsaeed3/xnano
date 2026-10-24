"""
xnano.ai._vector

SVG read into shapes and sampled onto a grid of pixels, for the ``'svg'`` strategy of
[`ArtModel`][xnano.ai.models.art.ArtModel].

Edges are hard: a pixel takes the colour of the last shape that covers its centre, with no
antialiasing, blending or opacity. ``<rect>`` (with ``rx`` and ``ry``), ``<circle>``,
``<ellipse>``, ``<line>``, ``<polyline>``, ``<polygon>``, ``<path>`` (every command, arcs
included), ``<g>`` and nested ``<svg>`` are drawn; ``transform`` takes ``translate``,
``scale``, ``rotate``, ``skewX``, ``skewY`` and ``matrix``; ``fill``, ``stroke``,
``stroke-width`` and ``fill-rule`` are read as attributes or from ``style`` and inherited
through groups. Gradients, text, images, ``<use>``, clip paths and filters are reported and
not drawn.
"""

from __future__ import annotations

import dataclasses
import math
import re
import xml.etree.ElementTree as ElementTree
from collections.abc import Mapping, Sequence
from typing import Final, TypeAlias

Point: TypeAlias = tuple[float, float]
Matrix: TypeAlias = tuple[float, float, float, float, float, float]
"""``(a, b, c, d, e, f)``, SVG's own order: x' = a*x + c*y + e and y' = b*x + d*y + f."""

_IDENTITY: Final[Matrix] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_MOST_CHARACTERS: Final = 40_000
_DEEPEST_NESTING: Final = 32
_CIRCLE_SEGMENTS: Final = 64
_NUMBER: Final = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')
_COMMAND: Final = re.compile(r'[A-Za-z]')
_HEX_COLOR: Final = re.compile(r'#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})')
_RGB_COLOR: Final = re.compile(
    r'rgba?\(\s*([\d.]+%?)\s*,?\s*([\d.]+%?)\s*,?\s*([\d.]+%?)(?:\s*[,/]\s*([\d.]+%?))?\s*\)'
)
_NAMED_COLORS: Final[Mapping[str, str]] = {
    'black': '#000000',
    'white': '#ffffff',
    'red': '#ff0000',
    'green': '#008000',
    'blue': '#0000ff',
    'yellow': '#ffff00',
    'orange': '#ffa500',
    'purple': '#800080',
    'pink': '#ffc0cb',
    'brown': '#a52a2a',
    'gray': '#808080',
    'grey': '#808080',
    'cyan': '#00ffff',
    'magenta': '#ff00ff',
    'gold': '#ffd700',
    'silver': '#c0c0c0',
    'navy': '#000080',
    'teal': '#008080',
    'maroon': '#800000',
    'olive': '#808000',
    'lime': '#00ff00',
}
_NOT_DRAWN: Final = frozenset(
    {
        'text',
        'tspan',
        'image',
        'use',
        'linearGradient',
        'radialGradient',
        'pattern',
        'filter',
        'clipPath',
        'mask',
        'foreignObject',
    }
)
_SKIPPED: Final = frozenset({'title', 'desc', 'defs', 'metadata', 'style'})
_GROUPS: Final = frozenset({'svg', 'g', 'a', 'switch'})


class SvgError(ValueError):
    """The SVG cannot be read; ``problems`` says exactly why."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = list(problems)
        super().__init__('; '.join(self.problems))


# -- geometry ------------------------------------------------------------------------------


def _multiplied(first: Matrix, second: Matrix) -> Matrix:
    a, b, c, d, e, f = first
    a2, b2, c2, d2, e2, f2 = second
    return (
        a * a2 + c * b2,
        b * a2 + d * b2,
        a * c2 + c * d2,
        b * c2 + d * d2,
        a * e2 + c * f2 + e,
        b * e2 + d * f2 + f,
    )


def _applied(matrix: Matrix, point: Point) -> Point:
    return (
        matrix[0] * point[0] + matrix[2] * point[1] + matrix[4],
        matrix[1] * point[0] + matrix[3] * point[1] + matrix[5],
    )


def _scale_of(matrix: Matrix) -> float:
    return math.sqrt(abs(matrix[0] * matrix[3] - matrix[1] * matrix[2])) or 1.0


def _numbers(text: str) -> list[float]:
    return [float(number) for number in _NUMBER.findall(text)]


def _transform_of(text: str | None, notes: list[str]) -> Matrix:
    """A ``transform`` attribute as one matrix, its operations composed left to right."""
    matrix = _IDENTITY
    for name, arguments in re.findall(r'([a-zA-Z]+)\s*\(([^)]*)\)', text or ''):
        values = _numbers(arguments)
        operation: Matrix
        if name == 'translate' and values:
            operation = (1, 0, 0, 1, values[0], values[1] if len(values) > 1 else 0.0)
        elif name == 'scale' and values:
            operation = (
                values[0],
                0,
                0,
                values[1] if len(values) > 1 else values[0],
                0,
                0,
            )
        elif name == 'rotate' and values:
            angle = math.radians(values[0])
            operation = (
                math.cos(angle),
                math.sin(angle),
                -math.sin(angle),
                math.cos(angle),
                0,
                0,
            )
            if len(values) >= 3:
                around = (1.0, 0.0, 0.0, 1.0, values[1], values[2])
                back = (1.0, 0.0, 0.0, 1.0, -values[1], -values[2])
                operation = _multiplied(_multiplied(around, operation), back)
        elif name == 'skewX' and values:
            operation = (1, 0, math.tan(math.radians(values[0])), 1, 0, 0)
        elif name == 'skewY' and values:
            operation = (1, math.tan(math.radians(values[0])), 0, 1, 0, 0)
        elif name == 'matrix' and len(values) == 6:
            operation = (values[0], values[1], values[2], values[3], values[4], values[5])
        else:
            notes.append(f'the transform {name}() was not understood and was ignored')
            continue
        matrix = _multiplied(matrix, operation)
    return matrix


def _ellipse_points(
    center_x: float, center_y: float, radius_x: float, radius_y: float
) -> list[Point]:
    return [
        (
            center_x + radius_x * math.cos(2 * math.pi * step / _CIRCLE_SEGMENTS),
            center_y + radius_y * math.sin(2 * math.pi * step / _CIRCLE_SEGMENTS),
        )
        for step in range(_CIRCLE_SEGMENTS)
    ]


def _rectangle_points(
    x: float, y: float, width: float, height: float, radius_x: float, radius_y: float
) -> list[Point]:
    radius_x, radius_y = min(radius_x, width / 2), min(radius_y, height / 2)
    if radius_x <= 0 or radius_y <= 0:
        return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
    points: list[Point] = []
    for center_x, center_y, start in (
        (x + width - radius_x, y + radius_y, -90),
        (x + width - radius_x, y + height - radius_y, 0),
        (x + radius_x, y + height - radius_y, 90),
        (x + radius_x, y + radius_y, 180),
    ):
        for step in range(9):
            angle = math.radians(start + 90 * step / 8)
            points.append(
                (
                    center_x + radius_x * math.cos(angle),
                    center_y + radius_y * math.sin(angle),
                )
            )
    return points


def _arc_points(
    start: Point,
    radius_x: float,
    radius_y: float,
    rotation: float,
    is_large: bool,
    is_sweep: bool,
    end: Point,
) -> list[Point]:
    """Points along an SVG elliptical arc given by its endpoints, without the start."""
    if radius_x == 0 or radius_y == 0 or start == end:
        return [end]
    radius_x, radius_y = abs(radius_x), abs(radius_y)
    cosine, sine = math.cos(math.radians(rotation)), math.sin(math.radians(rotation))
    half_x, half_y = (start[0] - end[0]) / 2, (start[1] - end[1]) / 2
    rotated_x = cosine * half_x + sine * half_y
    rotated_y = -sine * half_x + cosine * half_y
    excess = rotated_x**2 / radius_x**2 + rotated_y**2 / radius_y**2
    if excess > 1:
        radius_x, radius_y = radius_x * math.sqrt(excess), radius_y * math.sqrt(excess)
    numerator = (
        radius_x**2 * radius_y**2
        - radius_x**2 * rotated_y**2
        - radius_y**2 * rotated_x**2
    )
    denominator = radius_x**2 * rotated_y**2 + radius_y**2 * rotated_x**2
    factor = math.sqrt(max(0.0, numerator / denominator)) if denominator else 0.0
    if is_large == is_sweep:
        factor = -factor
    center_rotated_x = factor * radius_x * rotated_y / radius_y
    center_rotated_y = -factor * radius_y * rotated_x / radius_x
    center_x = (
        cosine * center_rotated_x - sine * center_rotated_y + (start[0] + end[0]) / 2
    )
    center_y = (
        sine * center_rotated_x + cosine * center_rotated_y + (start[1] + end[1]) / 2
    )

    def angle_between(ux: float, uy: float, vx: float, vy: float) -> float:
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    first_angle = angle_between(
        1,
        0,
        (rotated_x - center_rotated_x) / radius_x,
        (rotated_y - center_rotated_y) / radius_y,
    )
    sweep = angle_between(
        (rotated_x - center_rotated_x) / radius_x,
        (rotated_y - center_rotated_y) / radius_y,
        (-rotated_x - center_rotated_x) / radius_x,
        (-rotated_y - center_rotated_y) / radius_y,
    )
    if not is_sweep and sweep > 0:
        sweep -= 2 * math.pi
    elif is_sweep and sweep < 0:
        sweep += 2 * math.pi
    steps = max(4, int(abs(sweep) / (math.pi / 16)))
    points: list[Point] = []
    for step in range(1, steps + 1):
        angle = first_angle + sweep * step / steps
        points.append(
            (
                cosine * radius_x * math.cos(angle)
                - sine * radius_y * math.sin(angle)
                + center_x,
                sine * radius_x * math.cos(angle)
                + cosine * radius_y * math.sin(angle)
                + center_y,
            )
        )
    return points


def _path_rings(data: str) -> tuple[list[list[Point]], list[bool]]:
    """A path's subpaths as lists of points, and whether each one was closed."""
    tokens: list[str] = re.findall(r'[MmLlHhVvZzCcSsQqTtAa]|' + _NUMBER.pattern, data)
    rings: list[list[Point]] = []
    closed: list[bool] = []
    current: list[Point] = []
    x = y = start_x = start_y = 0.0
    command = ''
    previous_control: Point | None = None
    previous_command = ''
    index = 0

    def take(count: int) -> list[float]:
        nonlocal index
        taken = tokens[index : index + count]
        if len(taken) < count or any(_COMMAND.fullmatch(token) for token in taken):
            raise SvgError([f'the path data is cut short after the command {command!r}'])
        index += count
        return [float(token) for token in taken]

    def finish(is_closed: bool) -> None:
        nonlocal current
        if len(current) >= 2:
            rings.append(current)
            closed.append(is_closed)
        current = []

    while index < len(tokens):
        token = tokens[index]
        if _COMMAND.fullmatch(token):
            if not command and token not in 'Mm':
                raise SvgError(
                    [f'the path data must start with M, but starts with {token}']
                )
            command = token
            index += 1
            if command in 'Zz':
                finish(True)
                x, y = start_x, start_y
                previous_command = 'Z'
                continue
        elif not command:
            raise SvgError(['the path data must start with M, but starts with a number'])
        is_relative = command.islower()
        kind = command.upper()
        origin_x, origin_y = (x, y) if is_relative else (0.0, 0.0)
        if kind == 'M':
            next_x, next_y = take(2)
            finish(False)
            x, y = origin_x + next_x, origin_y + next_y
            start_x, start_y = x, y
            current = [(x, y)]
            command = 'l' if is_relative else 'L'
        elif kind == 'L':
            next_x, next_y = take(2)
            x, y = origin_x + next_x, origin_y + next_y
            current.append((x, y))
        elif kind == 'H':
            (next_x,) = take(1)
            x = x + next_x if is_relative else next_x
            current.append((x, y))
        elif kind == 'V':
            (next_y,) = take(1)
            y = y + next_y if is_relative else next_y
            current.append((x, y))
        elif kind in 'CS':
            if kind == 'C':
                values = take(6)
                first_control = (origin_x + values[0], origin_y + values[1])
                second_control = (origin_x + values[2], origin_y + values[3])
                end = (origin_x + values[4], origin_y + values[5])
            else:
                values = take(4)
                first_control = (
                    (2 * x - previous_control[0], 2 * y - previous_control[1])
                    if previous_control and previous_command in 'CS'
                    else (x, y)
                )
                second_control = (origin_x + values[0], origin_y + values[1])
                end = (origin_x + values[2], origin_y + values[3])
            start = (x, y)
            for step in range(1, 13):
                along = step / 12
                rest = 1 - along
                current.append(
                    (
                        rest**3 * start[0]
                        + 3 * rest**2 * along * first_control[0]
                        + 3 * rest * along**2 * second_control[0]
                        + along**3 * end[0],
                        rest**3 * start[1]
                        + 3 * rest**2 * along * first_control[1]
                        + 3 * rest * along**2 * second_control[1]
                        + along**3 * end[1],
                    )
                )
            previous_control, (x, y) = second_control, end
            previous_command = kind
            continue
        elif kind in 'QT':
            if kind == 'Q':
                values = take(4)
                control = (origin_x + values[0], origin_y + values[1])
                end = (origin_x + values[2], origin_y + values[3])
            else:
                values = take(2)
                control = (
                    (2 * x - previous_control[0], 2 * y - previous_control[1])
                    if previous_control and previous_command in 'QT'
                    else (x, y)
                )
                end = (origin_x + values[0], origin_y + values[1])
            start = (x, y)
            for step in range(1, 9):
                along = step / 8
                rest = 1 - along
                current.append(
                    (
                        rest**2 * start[0]
                        + 2 * rest * along * control[0]
                        + along**2 * end[0],
                        rest**2 * start[1]
                        + 2 * rest * along * control[1]
                        + along**2 * end[1],
                    )
                )
            previous_control, (x, y) = control, end
            previous_command = kind
            continue
        elif kind == 'A':
            values = take(7)
            end = (origin_x + values[5], origin_y + values[6])
            current.extend(
                _arc_points(
                    (x, y),
                    values[0],
                    values[1],
                    values[2],
                    bool(values[3]),
                    bool(values[4]),
                    end,
                )
            )
            x, y = end
        previous_control = None
        previous_command = kind
    finish(False)
    return rings, closed


# -- the scene -----------------------------------------------------------------------------


@dataclasses.dataclass(slots=True)
class Shape:
    """One drawn element as rings of points in viewBox units, with its transforms applied."""

    index: int
    rings: list[list[Point]]
    closed: list[bool]
    fill: str | None
    stroke: str | None
    stroke_width: float
    is_even_odd: bool
    source: str
    """The element as it reads in a message, such as ``<circle cx=3 cy=4 r=2>``."""
    line_cap: str = 'butt'
    """How an open stroke ends: ``'butt'`` at its endpoints, or ``'round'`` or ``'square'`` past them."""
    is_stroke_under: bool = False
    """Whether the fill is painted over the stroke (``paint-order="stroke"``)."""
    stroke_outlines: list[list[Point]] = dataclasses.field(
        default_factory=list[list[Point]]
    )
    """The stroke as convex outlines: one per segment, and one round joint per point."""

    def __post_init__(self) -> None:
        if self.stroke is None or self.stroke_width <= 0:
            return
        half = self.stroke_width / 2

        def disc(x: float, y: float) -> list[Point]:
            return [
                (
                    x + half * math.cos(math.pi * step / 4),
                    y + half * math.sin(math.pi * step / 4),
                )
                for step in range(8)
            ]

        for ring, is_closed in zip(self.rings, self.closed, strict=True):
            count = len(ring)
            segments = count if is_closed else count - 1
            for index in range(segments):
                (start_x, start_y), (end_x, end_y) = (
                    ring[index],
                    ring[(index + 1) % count],
                )
                length = math.hypot(end_x - start_x, end_y - start_y)
                if length == 0:
                    continue
                along_x = (end_x - start_x) / length * half
                along_y = (end_y - start_y) / length * half
                if not is_closed and self.line_cap == 'square':
                    if index == 0:
                        start_x, start_y = start_x - along_x, start_y - along_y
                    if index == segments - 1:
                        end_x, end_y = end_x + along_x, end_y + along_y
                normal_x, normal_y = -along_y, along_x
                self.stroke_outlines.append(
                    [
                        (start_x + normal_x, start_y + normal_y),
                        (end_x + normal_x, end_y + normal_y),
                        (end_x - normal_x, end_y - normal_y),
                        (start_x - normal_x, start_y - normal_y),
                    ]
                )
            for index, (x, y) in enumerate(ring):
                is_end = not is_closed and index in (0, count - 1)
                if not is_end or self.line_cap == 'round':
                    self.stroke_outlines.append(disc(x, y))

    def bounds(self) -> tuple[float, float, float, float]:
        """The left, top, right and bottom of the shape, its stroke included."""
        xs = [point[0] for ring in self.rings for point in ring]
        ys = [point[1] for ring in self.rings for point in ring]
        padding = self.stroke_width / 2 if self.stroke else 0.0
        return min(xs) - padding, min(ys) - padding, max(xs) + padding, max(ys) + padding

    def fill_spans(self, y: float) -> list[tuple[float, float]]:
        """The spans of x inside the outline at height ``y``, by the shape's fill rule."""
        crossings: list[tuple[float, int]] = []
        for ring in self.rings:
            count = len(ring)
            for index in range(count):
                (start_x, start_y), (end_x, end_y) = (
                    ring[index],
                    ring[(index + 1) % count],
                )
                if (start_y <= y) != (end_y <= y):
                    crossing = start_x + (y - start_y) * (end_x - start_x) / (
                        end_y - start_y
                    )
                    crossings.append((crossing, 1 if end_y > start_y else -1))
        crossings.sort()
        if self.is_even_odd:
            return [
                (start, end)
                for (start, _), (end, _) in zip(
                    crossings[::2], crossings[1::2], strict=False
                )
            ]
        spans: list[tuple[float, float]] = []
        winding = 0
        start = 0.0
        for x, direction in crossings:
            if winding == 0:
                start = x
            winding += direction
            if winding == 0:
                spans.append((start, x))
        return spans

    def stroke_spans(self, y: float) -> list[tuple[float, float]]:
        """The spans of x the stroke covers at height ``y``."""
        spans: list[tuple[float, float]] = []
        for outline in self.stroke_outlines:
            crossings = []
            count = len(outline)
            for index in range(count):
                (start_x, start_y), (end_x, end_y) = (
                    outline[index],
                    outline[(index + 1) % count],
                )
                if (start_y <= y) != (end_y <= y):
                    crossings.append(
                        start_x + (y - start_y) * (end_x - start_x) / (end_y - start_y)
                    )
            if len(crossings) >= 2:
                spans.append((min(crossings), max(crossings)))
        spans.sort()
        merged: list[tuple[float, float]] = []
        for start, end in spans:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged


@dataclasses.dataclass(slots=True)
class Sampling:
    """A scene sampled onto a grid of pixels."""

    colors: list[list[str | None]]
    """The colour of each pixel by row, ``None`` where it stays transparent."""
    owners: list[list[int]]
    """The index of the shape that gave each pixel its colour, ``-1`` for a transparent one."""
    covered: list[int]
    """How many samples each shape covers, whether or not a later shape hides them."""
    visible: list[int]
    """How many samples each shape shows, where no later shape covers it."""
    rescued: list[int]
    """
    The shapes smaller than a pixel that won none by area, each kept as the one pixel at its
    centre unless a shape painted after it covers that pixel.
    """


_SAMPLES_PER_SIDE: Final = 4
"""Each pixel is sampled at 4 by 4 points."""


@dataclasses.dataclass(slots=True)
class Scene:
    """A read SVG: its viewBox, its shapes in painting order, and what was not drawn."""

    view_box: tuple[float, float, float, float]
    shapes: list[Shape] = dataclasses.field(default_factory=list[Shape])
    notes: list[str] = dataclasses.field(default_factory=list[str])
    """What was read but not drawn, or drawn differently than written."""
    unsupported: list[str] = dataclasses.field(default_factory=list[str])
    """The elements and transforms that are not drawn at all."""

    def sample(self, columns: int, rows: int) -> Sampling:
        """
        Sample the scene onto ``columns`` by ``rows`` pixels.

        Each pixel is sampled at 4 by 4 points and takes the colour that covers most of them,
        transparency included; on a tie, the shape painted later wins. A shape smaller than a
        pixel that shows but wins none keeps the one pixel at the centre of what shows of it,
        unless a shape painted after it covers that pixel.
        """
        side = _SAMPLES_PER_SIDE
        sample_columns, sample_rows = columns * side, rows * side
        left, top, width, height = self.view_box
        sample_width, sample_height = width / sample_columns, height / sample_rows
        # Each sample holds 2 * shape index + 1 for a fill, + 2 for a stroke, or 0 for nothing.
        samples = [[0] * sample_columns for _ in range(sample_rows)]
        covered = [0] * len(self.shapes)

        def paint(row: list[int], spans: list[tuple[float, float]], value: int) -> int:
            painted = 0
            for start, end in spans:
                first = max(0, math.ceil((start - left) / sample_width - 0.5))
                last = min(sample_columns, math.ceil((end - left) / sample_width - 0.5))
                if last > first:
                    row[first:last] = [value] * (last - first)
                    painted += last - first
            return painted

        for shape in self.shapes:
            _, shape_top, _, shape_bottom = shape.bounds()
            first_row = max(0, math.floor((shape_top - top) / sample_height - 0.5))
            last_row = min(
                sample_rows, math.ceil((shape_bottom - top) / sample_height + 0.5)
            )
            for sample_row in range(first_row, last_row):
                y = top + (sample_row + 0.5) * sample_height
                row = samples[sample_row]
                layers = [
                    (shape.fill, shape.fill_spans, 2 * shape.index + 1),
                    (shape.stroke, shape.stroke_spans, 2 * shape.index + 2),
                ]
                if shape.is_stroke_under:
                    layers.reverse()
                for color, spans_at, value in layers:
                    if color is not None:
                        covered[shape.index] += paint(row, spans_at(y), value)

        def color_of_value(value: int) -> str | None:
            shape = self.shapes[(value - 1) // 2]
            return shape.fill if value % 2 else shape.stroke

        visible = [0] * len(self.shapes)
        centres: dict[int, list[float]] = {}
        colors: list[list[str | None]] = [[None] * columns for _ in range(rows)]
        owners = [[-1] * columns for _ in range(rows)]
        for pixel_row in range(rows):
            block = samples[pixel_row * side : (pixel_row + 1) * side]
            for column in range(columns):
                counts: dict[str | None, int] = {}
                latest: dict[str | None, int] = {}
                for offset, row in enumerate(block):
                    for inner, value in enumerate(
                        row[column * side : (column + 1) * side]
                    ):
                        color = color_of_value(value) if value else None
                        counts[color] = counts.get(color, 0) + 1
                        latest[color] = max(latest.get(color, 0), value)
                        if value:
                            index = (value - 1) // 2
                            visible[index] += 1
                            centre = centres.setdefault(index, [0.0, 0.0])
                            centre[0] += column + (inner + 0.5) / side
                            centre[1] += pixel_row + (offset + 0.5) / side
                winner = max(counts, key=lambda color: (counts[color], latest[color]))
                colors[pixel_row][column] = winner
                if winner is not None:
                    owners[pixel_row][column] = (latest[winner] - 1) // 2
        won = {owner for row in owners for owner in row}
        rescued: list[int] = []
        pixel_samples = side * side
        for shape in self.shapes:
            index = shape.index
            if index in won or not visible[index] or covered[index] >= pixel_samples:
                continue
            centre_x, centre_y = centres[index]
            column = min(columns - 1, int(centre_x / visible[index]))
            pixel_row = min(rows - 1, int(centre_y / visible[index]))
            if owners[pixel_row][column] > index:
                continue
            colors[pixel_row][column] = (
                shape.fill if shape.fill is not None else shape.stroke
            )
            owners[pixel_row][column] = index
            rescued.append(index)
        return Sampling(colors, owners, covered, visible, rescued)


# -- reading -------------------------------------------------------------------------------


def _tag_of(element: ElementTree.Element) -> str:
    return element.tag.rsplit('}', 1)[-1]


def _attribute(element: ElementTree.Element, name: str) -> str | None:
    """An attribute, from ``style`` first and then the element itself."""
    for declaration in element.attrib.get('style', '').split(';'):
        if ':' in declaration:
            key, value = declaration.split(':', 1)
            if key.strip() == name:
                return value.strip()
    return element.attrib.get(name)


def _number(element: ElementTree.Element, name: str, default: float = 0.0) -> float:
    found = _numbers(element.attrib.get(name, '') or '')
    return found[0] if found else default


def color_of(value: str, named_colors: Mapping[str, str] | None = None) -> str | None:
    """
    A CSS colour as ``'#rrggbb'``, or ``None`` when it is not a solid colour.

    ``named_colors`` adds names of its own, such as the letters of a palette.
    """
    if named_colors and value.strip() in named_colors:
        return named_colors[value.strip()]
    text = value.strip().lower()
    if text in _NAMED_COLORS:
        return _NAMED_COLORS[text]
    match = _RGB_COLOR.fullmatch(text)
    if match is not None:
        red, green, blue, alpha = match.groups()
        if alpha is not None and _channel(alpha, 1.0) < 1.0:
            return None
        channels = (
            round(min(255.0, _channel(part, 255.0))) for part in (red, green, blue)
        )
        return '#' + ''.join(f'{channel:02x}' for channel in channels)
    match = _HEX_COLOR.fullmatch(text)
    if match is None:
        return None
    digits = match.group(1)
    if len(digits) in (3, 4):
        digits = ''.join(digit * 2 for digit in digits)
    if len(digits) == 8:
        if digits[6:] != 'ff':
            return None
        digits = digits[:6]
    return f'#{digits}'


def _channel(text: str, full: float) -> float:
    if text.endswith('%'):
        return float(text[:-1]) / 100 * full
    return float(text)


def _paint(
    value: str | None,
    current_color: str | None,
    where: str,
    problems: list[str],
    named_colors: Mapping[str, str] | None,
) -> tuple[bool, str | None]:
    """Whether a fill or stroke is given, and its colour (``None`` for ``none``)."""
    if value is None or value == 'inherit':
        return False, None
    text = value.strip()
    if text in ('none', 'transparent'):
        return True, None
    if text == 'currentColor':
        text = current_color or '#000000'
    if text.startswith('url('):
        problems.append(
            f'{where} is painted with {text}; use a solid colour, not a gradient or pattern'
        )
        return True, None
    color = color_of(text, named_colors)
    if color is None:
        problems.append(
            f'{where} is painted with {value!r}, which is not a solid colour such as #1a1c2c'
        )
    return True, color


def read_svg(
    text: str,
    *,
    default_size: tuple[float, float],
    named_colors: Mapping[str, str] | None = None,
) -> Scene:
    """
    Read SVG text into a [`Scene`][xnano.ai._vector.Scene].

    Args:
        text: The SVG.
        default_size: The width and height of the viewBox when the SVG gives neither a
            viewBox nor a width and height.
        named_colors: Colour names of its own, such as the letters of a palette, each to its
            ``'#rrggbb'``.

    Raises:
        SvgError: The SVG cannot be read, or an element in it cannot be drawn as written.
    """
    if len(text) > _MOST_CHARACTERS:
        raise SvgError(
            [f'the SVG is {len(text)} characters long; keep it under {_MOST_CHARACTERS}']
        )
    if '<!ENTITY' in text:
        raise SvgError(['the SVG declares entities; write the elements out instead'])
    try:
        root = ElementTree.fromstring(text.strip())
    except ElementTree.ParseError as error:
        raise SvgError([f'the SVG is not well-formed XML: {error}']) from None
    if _tag_of(root) != 'svg':
        raise SvgError([f'the root element is <{_tag_of(root)}>, but it must be <svg>'])
    notes: list[str] = []
    box = _numbers(root.attrib.get('viewBox', ''))
    if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
        width = _number(root, 'width', default_size[0])
        height = _number(root, 'height', default_size[1])
        box = [0.0, 0.0, width, height]
        notes.append(
            f'the SVG has no viewBox, so viewBox="0 0 {width:g} {height:g}" was used'
        )
    scene = Scene((box[0], box[1], box[2], box[3]), notes=notes)
    problems: list[str] = []

    def walk(
        element: ElementTree.Element,
        matrix: Matrix,
        fill: str | None,
        stroke: str | None,
        stroke_width: float,
        is_even_odd: bool,
        line_cap: str,
        is_stroke_under: bool,
        current_color: str | None,
        depth: int,
    ) -> None:
        tag = _tag_of(element)
        if tag in _SKIPPED:
            return
        if tag in _NOT_DRAWN:
            scene.unsupported.append(f'<{tag}> is not supported')
            return
        if depth > _DEEPEST_NESTING:
            problems.append(f'the SVG nests elements more than {_DEEPEST_NESTING} deep')
            return
        transform_notes: list[str] = []
        matrix = _multiplied(
            matrix, _transform_of(element.attrib.get('transform'), transform_notes)
        )
        scene.unsupported.extend(transform_notes)
        current_color = _attribute(element, 'color') or current_color
        where = f'<{tag}>'
        is_fill_given, own_fill = _paint(
            _attribute(element, 'fill'), current_color, where, problems, named_colors
        )
        is_stroke_given, own_stroke = _paint(
            _attribute(element, 'stroke'), current_color, where, problems, named_colors
        )
        fill = own_fill if is_fill_given else fill
        stroke = own_stroke if is_stroke_given else stroke
        width_values = _numbers(_attribute(element, 'stroke-width') or '')
        if width_values:
            stroke_width = width_values[0]
        rule = _attribute(element, 'fill-rule')
        if rule is not None:
            is_even_odd = rule.strip() == 'evenodd'
        cap = _attribute(element, 'stroke-linecap')
        if cap is not None and cap.strip() in ('butt', 'round', 'square'):
            line_cap = cap.strip()
        order = _attribute(element, 'paint-order')
        if order is not None:
            is_stroke_under = order.split()[:1] == ['stroke']
        for name in ('opacity', 'fill-opacity', 'stroke-opacity'):
            opacity = _numbers(_attribute(element, name) or '')
            if opacity and opacity[0] < 1:
                scene.notes.append(
                    f'the {name} of {where} was ignored: pixel art has no blending'
                )
        if tag in _GROUPS:
            for child in element:
                walk(
                    child,
                    matrix,
                    fill,
                    stroke,
                    stroke_width,
                    is_even_odd,
                    line_cap,
                    is_stroke_under,
                    current_color,
                    depth + 1,
                )
            return
        rings: list[list[Point]]
        closed: list[bool]
        if tag == 'rect':
            x, y = _number(element, 'x'), _number(element, 'y')
            width, height = _number(element, 'width'), _number(element, 'height')
            radius_x = _number(element, 'rx', _number(element, 'ry'))
            radius_y = _number(element, 'ry', radius_x)
            if width <= 0 or height <= 0:
                problems.append(
                    f'<rect x={x:g} y={y:g}> has no area: its width is {width:g} and its height {height:g}'
                )
                return
            rings, closed = (
                [_rectangle_points(x, y, width, height, radius_x, radius_y)],
                [True],
            )
            source = f'<rect x={x:g} y={y:g} width={width:g} height={height:g}>'
        elif tag in ('circle', 'ellipse'):
            center_x, center_y = _number(element, 'cx'), _number(element, 'cy')
            if tag == 'circle':
                radius_x = radius_y = _number(element, 'r')
                source = f'<circle cx={center_x:g} cy={center_y:g} r={radius_x:g}>'
            else:
                radius_x = _number(element, 'rx')
                radius_y = _number(element, 'ry', radius_x)
                source = f'<ellipse cx={center_x:g} cy={center_y:g} rx={radius_x:g} ry={radius_y:g}>'
            if radius_x <= 0 or radius_y <= 0:
                problems.append(f'{source} has no radius')
                return
            rings, closed = (
                [_ellipse_points(center_x, center_y, radius_x, radius_y)],
                [True],
            )
        elif tag == 'line':
            start = (_number(element, 'x1'), _number(element, 'y1'))
            end = (_number(element, 'x2'), _number(element, 'y2'))
            source = f'<line x1={start[0]:g} y1={start[1]:g} x2={end[0]:g} y2={end[1]:g}>'
            if stroke is None:
                scene.notes.append(f'{source} has no stroke, so it draws nothing')
                return
            rings, closed, fill = [[start, end]], [False], None
        elif tag in ('polygon', 'polyline'):
            values = _numbers(element.attrib.get('points', ''))
            points = list(zip(values[0::2], values[1::2], strict=False))
            if len(points) < 2:
                problems.append(f'<{tag}> needs at least two points')
                return
            rings, closed = [points], [tag == 'polygon']
            listed = ' '.join(f'{x:g},{y:g}' for x, y in points[:4])
            source = f'<{tag} points="{listed}{" ..." if len(points) > 4 else ""}">'
        elif tag == 'path':
            data = element.attrib.get('d', '')
            try:
                rings, closed = _path_rings(data)
            except SvgError as error:
                problems.extend(f'<path>: {problem}' for problem in error.problems)
                return
            if not rings:
                problems.append('a <path> has no subpath with two or more points')
                return
            source = f'<path d="{data[:40]}{"..." if len(data) > 40 else ""}">'
        else:
            scene.unsupported.append(f'<{tag}> is not supported')
            return
        if fill is None and stroke is None:
            return
        rings = [[_applied(matrix, point) for point in ring] for ring in rings]
        if not all(
            math.isfinite(value) for ring in rings for point in ring for value in point
        ):
            problems.append(f'{source} reaches coordinates too large to draw')
            return
        scene.shapes.append(
            Shape(
                index=len(scene.shapes),
                rings=rings,
                closed=closed,
                fill=fill,
                stroke=stroke,
                stroke_width=stroke_width * _scale_of(matrix),
                is_even_odd=is_even_odd,
                source=source,
                line_cap=line_cap,
                is_stroke_under=is_stroke_under,
            )
        )

    walk(root, _IDENTITY, '#000000', None, 1.0, False, 'butt', False, None, 0)
    if problems:
        raise SvgError(problems)
    return scene


# -- writing -------------------------------------------------------------------------------


def _outlines(rows: Sequence[str], letter: str) -> list[list[tuple[int, int]]]:
    """The pixels of one letter as closed outlines along pixel edges, corners only."""
    cells = {
        (x, y)
        for y, row in enumerate(rows)
        for x, value in enumerate(row)
        if value == letter
    }
    edges: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for x, y in cells:
        if (x, y - 1) not in cells:
            edges.setdefault((x, y), []).append((x + 1, y))
        if (x + 1, y) not in cells:
            edges.setdefault((x + 1, y), []).append((x + 1, y + 1))
        if (x, y + 1) not in cells:
            edges.setdefault((x + 1, y + 1), []).append((x, y + 1))
        if (x - 1, y) not in cells:
            edges.setdefault((x, y + 1), []).append((x, y))
    outlines: list[list[tuple[int, int]]] = []
    while edges:
        start = min(edges)
        outline = [start]
        point = start
        while True:
            following = edges[point].pop()
            if not edges[point]:
                del edges[point]
            if following == start:
                break
            outline.append(following)
            point = following
        outlines.append(
            [
                corner
                for index, corner in enumerate(outline)
                if not (
                    outline[index - 1][0]
                    == corner[0]
                    == outline[(index + 1) % len(outline)][0]
                    or outline[index - 1][1]
                    == corner[1]
                    == outline[(index + 1) % len(outline)][1]
                )
            ]
        )
    return outlines


def traced_svg(
    rows: Sequence[str], colors: Mapping[str, str], *, transparent: str = '.'
) -> str:
    """
    Pixel art as SVG: one ``<path>`` per colour, traced along the edges of its pixels.

    Sampling the SVG at pixel centres gives the rows back exactly. Larger colours come first,
    so the SVG reads as masses before details.

    Args:
        rows: The art, one letter per pixel.
        colors: The ``'#rrggbb'`` colour of each letter; letters without one are left out.
        transparent: The letter of a transparent pixel.
    """
    width = max((len(row) for row in rows), default=0)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {len(rows)}">'
    ]
    counts: dict[str, int] = {}
    for row in rows:
        for letter in row:
            if letter != transparent and letter in colors:
                counts[letter] = counts.get(letter, 0) + 1
    for letter in sorted(counts, key=lambda letter: (-counts[letter], letter)):
        parts = []
        for outline in _outlines(rows, letter):
            (first_x, first_y), rest = outline[0], outline[1:]
            commands = [f'M{first_x} {first_y}']
            previous_y = first_y
            for x, y in rest:
                commands.append(f'H{x}' if y == previous_y else f'V{y}')
                previous_y = y
            parts.append(''.join(commands) + 'Z')
        lines.append(
            f'<path fill="{colors[letter]}" fill-rule="evenodd" d="{" ".join(parts)}"/>'
        )
    lines.append('</svg>')
    return '\n'.join(lines)
