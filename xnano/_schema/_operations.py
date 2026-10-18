"""
xnano._schema._operations

The TypedDicts of the settings of the Dynamic operations, written as keyword arguments.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Literal, TypeAlias, TypedDict

import xnano_core as _core
from xnano._schema._appearance import ColorValue
from xnano._schema._layout import PixelEncoding

OperationResult: TypeAlias = '_core.Operation | _core.Style | None'
"""
What a function decorated with [`hook`][xnano.hooks.hook] may return: an operation (an effect or a
Dynamic operation included), a style or ``None``.
"""


class DynamicFillSchema(TypedDict, total=False):
    """
    The settings of [`DynamicFill`][xnano.operations.DynamicFill], as keyword arguments.

    Attributes:
        cell: The character or cell used to fill the target.
    """

    cell: _core.Cell | str
    """The character or cell used to fill the target."""


class DynamicWriteSchema(TypedDict, total=False):
    """
    The settings of [`DynamicWrite`][xnano.operations.DynamicWrite], as keyword arguments.

    Attributes:
        text: Text or styled text to write.
        x: Starting column.
        y: Starting row.
        style: Optional style applied to the written text.
        mode: Write blending mode (``'replace'``, ``'preserve_background'``).
    """

    text: _core.TextContent
    """Text or styled text to write."""

    x: int
    """Starting column."""

    y: int
    """Starting row."""

    style: _core.Style | None
    """Optional style applied to the written text."""

    mode: _core.WriteMode
    """Write blending mode (``'replace'``, ``'preserve_background'``)."""


class DynamicLayoutSchema(TypedDict, total=False):
    """
    The settings of [`DynamicLayout`][xnano.operations.DynamicLayout], as keyword arguments.

    Attributes:
        arrangement: ``'row'``, ``'column'`` or ``'overlay'``.
        sizes: Size rules for each child along the main axis.
        spacing: Cells between adjacent children.
        padding: Cells inset from the parent's edges.
    """

    arrangement: Literal['row', 'column', 'overlay']
    """``'row'``, ``'column'`` or ``'overlay'``."""

    sizes: Sequence[_core.SizeRule]
    """Size rules for each child along the main axis."""

    spacing: int
    """Cells between adjacent children."""

    padding: int
    """Cells inset from the parent's edges."""


class DynamicFuzzSchema(TypedDict, total=False):
    """
    The settings of [`DynamicFuzz`][xnano.operations.DynamicFuzz], as keyword arguments.

    Attributes:
        intensity: Percentage of glyphs to replace (``0`` to ``100``).
        seed: Optional random seed for repeatable noise.
    """

    intensity: int
    """Percentage of glyphs to replace (``0`` to ``100``)."""

    seed: int | None
    """Optional random seed for repeatable noise."""


class DynamicPixelsSchema(TypedDict, total=False):
    """
    The settings of [`DynamicPixels`][xnano.operations.DynamicPixels], as keyword arguments.

    Attributes:
        shader: Optional function ``(x, y) -> color`` evaluated across the target's pixel grid.
        pixels: Optional explicit iterable of ``(x, y, (red, green, blue))`` pixels.
        encoding: ``'half_blocks'`` or ``'braille'``.
        clip: Whether out-of-bounds pixels are clipped instead of raising ``IndexError``.
        x: Column offset of the explicit pixels, or ``None``.
        y: Row offset of the explicit pixels, or ``None``.
    """

    shader: Callable[[int, int], ColorValue | None] | None
    """Optional function ``(x, y) -> color`` evaluated across the target's pixel grid."""

    pixels: Iterable[_core.PixelEntry] | None
    """Optional explicit iterable of ``(x, y, (red, green, blue))`` pixels."""

    encoding: PixelEncoding
    """``'half_blocks'`` or ``'braille'``."""

    clip: bool
    """Whether out-of-bounds pixels are clipped instead of raising ``IndexError``."""

    x: int | None
    """Column offset of the explicit pixels, or ``None``."""

    y: int | None
    """Row offset of the explicit pixels, or ``None``."""


class DynamicRasterSchema(TypedDict, total=False):
    """
    The settings of [`DynamicRaster`][xnano.operations.DynamicRaster], as keyword arguments.

    Attributes:
        rgba: ``width * height * 4`` bytes of RGBA8 pixel data.
        width: Image width in pixels.
        height: Image height in pixels.
        x: Top-left pixel column.
        y: Top-left pixel row.
        encoding: ``'half_blocks'`` or ``'braille'``.
        mode: ``'over'`` or ``'replace'``.
    """

    rgba: bytes
    """``width * height * 4`` bytes of RGBA8 pixel data."""

    width: int
    """Image width in pixels."""

    height: int
    """Image height in pixels."""

    x: int
    """Top-left pixel column."""

    y: int
    """Top-left pixel row."""

    encoding: PixelEncoding
    """``'half_blocks'`` or ``'braille'``."""

    mode: _core.RasterMode
    """``'over'`` or ``'replace'``."""
