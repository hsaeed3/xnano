"""
xnano.layout

Where things are written and how much room they take.

A [`Placement`][xnano.layout.Placement] is something written on a screen, with its position
and size, which follow the lines written before it unless you say where it goes. A
[`Region`][xnano.layout.Region] is a rectangle of cells: of a screen, of a placement, or one
built with [`write`][xnano.layout.write] or [`box`][xnano.layout.box]. Positions and sizes take
a number of cells, a share such as ``'50%'``, a word such as ``'center'`` or ``'next'``, or a
formula of [`xnano.expressions`][xnano.expressions]; [`Point`][xnano.layout.Point],
[`Size`][xnano.layout.Size] and [`Rectangle`][xnano.layout.Rectangle] are plain values measured
in cells.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from xnano._schema._axes import Axis as Axis
    from xnano._schema._axes import FlowPosition as FlowPosition
    from xnano._schema._axes import HorizontalPosition as HorizontalPosition
    from xnano._schema._axes import Percentage as Percentage
    from xnano._schema._axes import RangeBound as RangeBound
    from xnano._schema._axes import VerticalPosition as VerticalPosition
    from xnano._schema._layout import Anchor as Anchor
    from xnano._schema._layout import EdgeBehavior as EdgeBehavior
    from xnano.layout._geometry import Point as Point
    from xnano.layout._geometry import Rectangle as Rectangle
    from xnano.layout._geometry import Size as Size
    from xnano.layout._geometry import SizeRule as SizeRule
    from xnano.layout._placement import Placement as Placement
    from xnano.layout._region import PixelAnchor as PixelAnchor
    from xnano.layout._region import Region as Region
    from xnano.layout._region import Resolution as Resolution
    from xnano.layout._region import box as box
    from xnano.layout._region import write as write

_MODULES: Final[dict[str, str]] = {
    'Anchor': 'xnano._schema._layout',
    'Axis': 'xnano._schema._axes',
    'EdgeBehavior': 'xnano._schema._layout',
    'FlowPosition': 'xnano._schema._axes',
    'HorizontalPosition': 'xnano._schema._axes',
    'Percentage': 'xnano._schema._axes',
    'PixelAnchor': 'xnano.layout._region',
    'Placement': 'xnano.layout._placement',
    'Point': 'xnano.layout._geometry',
    'RangeBound': 'xnano._schema._axes',
    'Rectangle': 'xnano.layout._geometry',
    'Region': 'xnano.layout._region',
    'Resolution': 'xnano.layout._region',
    'Size': 'xnano.layout._geometry',
    'SizeRule': 'xnano.layout._geometry',
    'VerticalPosition': 'xnano._schema._axes',
    'box': 'xnano.layout._region',
    'write': 'xnano.layout._region',
}
"""The module each name comes from, imported the first time the name is read."""

__all__ = [
    'Anchor',
    'Axis',
    'EdgeBehavior',
    'FlowPosition',
    'HorizontalPosition',
    'Percentage',
    'PixelAnchor',
    'Placement',
    'Point',
    'RangeBound',
    'Rectangle',
    'Region',
    'Resolution',
    'Size',
    'SizeRule',
    'VerticalPosition',
    'box',
    'write',
]


def __getattr__(name: str) -> object:
    """Import a name the first time it is read, then keep it."""
    module = _MODULES.get(name)
    if module is None:
        raise AttributeError(
            f'xnano.layout has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    value = getattr(importlib.import_module(module), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
