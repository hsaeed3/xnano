"""
xnano.ai.models._art_finish

The pixel-art finishing a flat drawing gets: stray pixels merged into their surroundings, an
outline inside the silhouette with its doubled corners removed, and on each material a shadow
along its lower-right edges and a highlight along its upper-left edges, placed where a form
turns away from a light at the top left, in colours shifted in hue the way pixel artists
shift them (shadows toward blue, highlights toward yellow).

The drawing keeps what a model decides, the silhouette and the flat colour of each part, and
takes from here what a model draws badly pixel by pixel. Pixels whose colour has the role
``'detail'`` or ``'accent'`` (eyes, buttons, a gem) are never changed.
"""

from __future__ import annotations

import colorsys
import dataclasses
from collections.abc import Mapping, Sequence
from typing import Final

Palette = Mapping[str, tuple[str, str]]
"""Each letter's ``(role, '#rrggbb')``."""

MATERIAL_ROLES: Final = frozenset({'base', 'skin'})
"""The roles that are shaded: the flat colour of a material."""
PROTECTED_ROLES: Final = frozenset({'detail', 'accent'})
"""The roles the finishing never changes."""
_LETTERS: Final = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
_SIDES: Final = ((0, -1), (-1, 0), (0, 1), (1, 0))
"""Up, left, down, right."""
_SMALLEST_SHADED: Final = 6
"""A material with fewer pixels than this stays flat."""
_SMALLEST_OUTLINED: Final = 8
"""Art narrower or shorter than this many pixels gets neither outline nor shading."""
_LIT_SHARE: Final = 0.6
"""How far along its upper and left edges a material is lit, from its top-left corner."""
_SHADED_SHARE: Final = 0.4
"""From how far along its lower and right edges a material is in shadow."""


@dataclasses.dataclass(frozen=True, slots=True)
class Finished:
    """A drawing after its finishing: the rows, the palette with the added shades, and notes."""

    rows: tuple[str, ...]
    palette: dict[str, tuple[str, str]]
    notes: tuple[str, ...]


def finish(rows: Sequence[str], palette: Palette, *, transparent: str = '.') -> Finished:
    """
    Finish a flat drawing: merge stray pixels, outline it, and shade each material.

    The outline is added only when the drawing has no pixel of the role ``'outline'``, and
    the shading only when it has no pixel of the roles ``'shadow'`` or ``'highlight'``: a
    drawing that did its own keeps it. Art smaller than 8 pixels on a side has no room for
    either, and keeps only the merging of stray pixels.

    Args:
        rows: The drawing, one letter per pixel.
        palette: Each letter's role and colour.
        transparent: The letter of a transparent pixel.
    """
    grid = [list(row) for row in rows]
    colors = dict(palette)
    notes: list[str] = []
    merged = _merge_strays(grid, colors, transparent)
    if merged:
        notes.append(
            f'{merged} stray pixel{"s" if merged > 1 else ""} took the colour around '
            f'{"them" if merged > 1 else "it"}'
        )
    used_roles = {colors[letter][0] for row in grid for letter in row if letter in colors}
    is_small = len(grid) < _SMALLEST_OUTLINED or len(grid[0]) < _SMALLEST_OUTLINED
    if is_small:
        used_roles |= {'outline', 'shadow'}
    if 'outline' not in used_roles:
        outlined = _outline(grid, colors, transparent)
        if outlined:
            notes.append(f'the renderer drew the outline, {outlined} pixels')
    if not used_roles & {'shadow', 'highlight'}:
        shaded = _shade(grid, colors, transparent)
        if shaded:
            notes.append(
                f'the renderer shaded {shaded} material{"s" if shaded > 1 else ""}'
            )
    used = {letter for row in grid for letter in row}
    return Finished(
        tuple(''.join(row) for row in grid),
        {letter: color for letter, color in colors.items() if letter in used},
        tuple(notes),
    )


def shadow_of(color: str) -> str:
    """A material's shadow: one step darker, a little more saturated, shifted toward blue."""
    hue, saturation, value = _hsv(color)
    return _hex(
        _toward(hue, 240 / 360, 12 / 360), min(1.0, saturation + 0.08), value - 0.18
    )


def highlight_of(color: str) -> str:
    """A material's highlight: one step lighter, a little less saturated, shifted toward yellow."""
    hue, saturation, value = _hsv(color)
    return _hex(
        _toward(hue, 55 / 360, 8 / 360), max(0.0, saturation - 0.15), value + 0.12
    )


def outline_of(color: str) -> str:
    """The outline derived from the darkest material: very dark, hued, never pure black."""
    hue, saturation, value = _hsv(color)
    return _hex(
        _toward(hue, 250 / 360, 20 / 360),
        min(1.0, saturation * 0.8 + 0.1),
        max(0.12, value * 0.35),
    )


def _merge_strays(grid: list[list[str]], colors: Palette, transparent: str) -> int:
    """Give a lone pixel of a material the colour around it; return how many were merged."""
    merged = 0
    height = len(grid)
    width = len(grid[0]) if grid else 0
    for y in range(height):
        for x in range(width):
            letter = grid[y][x]
            if _role(colors, letter) not in MATERIAL_ROLES:
                continue
            around = [
                grid[y + step_y][x + step_x]
                for step_x, step_y in _SIDES
                if 0 <= x + step_x < width and 0 <= y + step_y < height
            ]
            if len(around) >= 3 and len(set(around)) == 1 and around[0] != letter:
                if _role(colors, around[0]) in PROTECTED_ROLES:
                    continue
                grid[y][x] = around[0]
                merged += 1
    return merged


def _outline(
    grid: list[list[str]], colors: dict[str, tuple[str, str]], transparent: str
) -> int:
    """Draw the outline inside the silhouette, without doubled corners; return its pixels."""
    height = len(grid)
    width = len(grid[0]) if grid else 0
    materials = [
        colors[letter][1]
        for letter, (role, _) in colors.items()
        if role in MATERIAL_ROLES and any(letter in row for row in grid)
    ]
    if not materials:
        return 0
    darkest = min(materials, key=lambda color: _hsv(color)[2])
    letter = _free_letter(colors, preferred='o')
    colors[letter] = ('outline', outline_of(darkest))
    ring = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if _is_edge(grid, colors, transparent, x, y)
    }
    ring -= _doubled_corners(ring)
    for x, y in ring:
        grid[y][x] = letter
    return len(ring)


def _is_edge(
    grid: list[list[str]], colors: Palette, transparent: str, x: int, y: int
) -> bool:
    """Whether the pixel is drawn and touches a transparent pixel on one of its sides."""
    pixel = grid[y][x]
    if pixel == transparent or _role(colors, pixel) in PROTECTED_ROLES:
        return False
    return any(
        _at(grid, x + step_x, y + step_y) == transparent for step_x, step_y in _SIDES
    )


def _doubled_corners(ring: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """
    The elbow pixels that make a line two pixels thick at a step of a diagonal.

    A pixel of the ring with one ring neighbour beside it and one above or below it, where
    those two touch at their corners, is an elbow. It is removed when one of its two runs is
    short, which is a step in a slope; the corner of a box has long runs on both sides.
    """
    removed: set[tuple[int, int]] = set()
    for x, y in sorted(ring):
        beside = [(x + step, y) for step in (-1, 1) if (x + step, y) in ring]
        stacked = [(x, y + step) for step in (-1, 1) if (x, y + step) in ring]
        if len(beside) != 1 or len(stacked) != 1:
            continue
        if (beside[0][0], stacked[0][1]) not in ring:
            continue  # the two neighbours do not meet at a corner
        horizontal = _run(ring, x, y, beside[0][0] - x, 0)
        vertical = _run(ring, x, y, 0, stacked[0][1] - y)
        if min(horizontal, vertical) <= 2:
            removed.add((x, y))
    return removed


def _run(ring: set[tuple[int, int]], x: int, y: int, step_x: int, step_y: int) -> int:
    """How many ring pixels follow in a direction, the first neighbour included."""
    length = 0
    while (x + step_x * (length + 1), y + step_y * (length + 1)) in ring:
        length += 1
    return length


def _shade(
    grid: list[list[str]], colors: dict[str, tuple[str, str]], transparent: str
) -> int:
    """
    Shade each material as a form lit from the top left.

    A pixel on a material's upper or left edge takes the highlight along the first part of
    that edge, from the top-left corner; a pixel on its lower or right edge takes the shadow
    along the last part of that edge, toward the bottom-right corner. The rest of an edge
    stays flat, so no band hugs the outline all the way round.
    """
    height = len(grid)
    width = len(grid[0]) if grid else 0
    shaded = 0
    materials = [letter for letter, (role, _) in colors.items() if role in MATERIAL_ROLES]
    for material in materials:
        pixels = [
            (x, y) for y in range(height) for x in range(width) if grid[y][x] == material
        ]
        if len(pixels) < _SMALLEST_SHADED:
            continue
        left = min(x for x, _ in pixels)
        top = min(y for _, y in pixels)
        span_x = max(1, max(x for x, _ in pixels) - left)
        span_y = max(1, max(y for _, y in pixels) - top)
        shadow = highlight = None
        changes: list[tuple[int, int, str]] = []
        for x, y in pixels:
            sides = [_at(grid, x + step_x, y + step_y) for step_x, step_y in _SIDES]
            if sum(side == material for side in sides) < 2:
                continue  # a line one pixel wide stays flat
            above, before, below, after = sides
            along_x = (x - left) / span_x
            along_y = (y - top) / span_y
            is_shaded = (
                _is_dark_side(colors, material, after)
                and along_y >= _SHADED_SHARE
                or _is_dark_side(colors, material, below)
                and along_x >= _SHADED_SHARE
            )
            is_lit = (
                _is_lit_side(colors, transparent, before)
                and along_y <= _LIT_SHARE
                or _is_lit_side(colors, transparent, above)
                and along_x <= _LIT_SHARE
            )
            if is_shaded and not is_lit:
                if shadow is None:
                    shadow = _free_letter(colors)
                    colors[shadow] = ('shadow', shadow_of(colors[material][1]))
                changes.append((x, y, shadow))
            elif is_lit and not is_shaded:
                if highlight is None:
                    highlight = _free_letter(colors)
                    colors[highlight] = ('highlight', highlight_of(colors[material][1]))
                changes.append((x, y, highlight))
        for x, y, letter in changes:
            grid[y][x] = letter
        if changes:
            shaded += 1
    return shaded


def _is_dark_side(colors: Palette, material: str, side: str | None) -> bool:
    """Whether a neighbour ends the material on its shaded side."""
    return (
        side is not None
        and side != material
        and _role(colors, side) not in PROTECTED_ROLES
    )


def _is_lit_side(colors: Palette, transparent: str, side: str | None) -> bool:
    """Whether a neighbour is the open air or the outline, where the light comes from."""
    return side is not None and (side == transparent or _role(colors, side) == 'outline')


def _at(grid: list[list[str]], x: int, y: int) -> str | None:
    """The letter at a position, or ``None`` outside the drawing."""
    if 0 <= y < len(grid) and 0 <= x < len(grid[y]):
        return grid[y][x]
    return None


def _role(colors: Palette, letter: str) -> str | None:
    entry = colors.get(letter)
    return entry[0] if entry else None


def _free_letter(colors: Palette, *, preferred: str | None = None) -> str:
    if preferred is not None and preferred not in colors:
        return preferred
    for letter in _LETTERS:
        if letter not in colors and letter != '.':
            return letter
    raise ValueError('The palette has no letter left for a shade.')


def _hsv(color: str) -> tuple[float, float, float]:
    digits = color.lstrip('#')
    red, green, blue = (int(digits[index : index + 2], 16) / 255 for index in (0, 2, 4))
    return colorsys.rgb_to_hsv(red, green, blue)


def _hex(hue: float, saturation: float, value: float) -> str:
    red, green, blue = colorsys.hsv_to_rgb(
        hue % 1.0, min(1.0, max(0.0, saturation)), min(1.0, max(0.0, value))
    )
    return '#' + ''.join(f'{round(channel * 255):02x}' for channel in (red, green, blue))


def _toward(hue: float, target: float, step: float) -> float:
    """Move a hue toward a target by at most ``step``, the short way round the wheel."""
    difference = (target - hue + 0.5) % 1.0 - 0.5
    if abs(difference) <= step:
        return target
    return hue + (step if difference > 0 else -step)
