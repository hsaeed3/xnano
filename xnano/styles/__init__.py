"""
xnano.styles

How things look: colors, styles and styled text, and the look of anything written on a screen.

A [`Style`][xnano.styles.Style] holds colors and text modifiers, and styled text is built from
spans that each carry their own. A screen, a placement and a region each have the same four
properties for their look, ``color``, ``border``, ``padding`` and ``margin``, which are
[`Colors`][xnano.styles.Colors], a [`BorderAppearance`][xnano.styles.BorderAppearance], a
[`PaddingAppearance`][xnano.styles.PaddingAppearance] and a
[`MarginAppearance`][xnano.styles.MarginAppearance]. Colors are given as names, hex strings or
``(red, green, blue)`` tuples wherever a [`ColorValue`][xnano.styles.ColorValue] is accepted.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from xnano._schema._appearance import AppearanceArguments as AppearanceArguments
    from xnano._schema._appearance import (
        CanvasAppearanceArguments as CanvasAppearanceArguments,
    )
    from xnano._schema._appearance import Spacing as Spacing
    from xnano._schema._appearance import SpacingDictionary as SpacingDictionary
    from xnano.styles._appearance import BorderAppearance as BorderAppearance
    from xnano.styles._appearance import BorderSide as BorderSide
    from xnano.styles._appearance import Colors as Colors
    from xnano.styles._appearance import ColorSlot as ColorSlot
    from xnano.styles._appearance import Edges as Edges
    from xnano.styles._appearance import MarginAppearance as MarginAppearance
    from xnano.styles._appearance import PaddingAppearance as PaddingAppearance
    from xnano.styles._core_styles import Color as Color
    from xnano.styles._core_styles import ColorName as ColorName
    from xnano.styles._core_styles import ColorValue as ColorValue
    from xnano.styles._core_styles import Style as Style
    from xnano.styles._core_styles import StyledText as StyledText
    from xnano.styles._core_styles import TextContent as TextContent
    from xnano.styles._core_styles import TextLine as TextLine
    from xnano.styles._core_styles import TextSpan as TextSpan
    from xnano_core import BorderKind as BorderKind

_MODULES: Final[dict[str, str]] = {
    'AppearanceArguments': 'xnano._schema._appearance',
    'BorderAppearance': 'xnano.styles._appearance',
    'BorderKind': 'xnano_core',
    'BorderSide': 'xnano.styles._appearance',
    'CanvasAppearanceArguments': 'xnano._schema._appearance',
    'Color': 'xnano.styles._core_styles',
    'ColorName': 'xnano.styles._core_styles',
    'ColorSlot': 'xnano.styles._appearance',
    'ColorValue': 'xnano.styles._core_styles',
    'Colors': 'xnano.styles._appearance',
    'Edges': 'xnano.styles._appearance',
    'MarginAppearance': 'xnano.styles._appearance',
    'PaddingAppearance': 'xnano.styles._appearance',
    'Spacing': 'xnano._schema._appearance',
    'SpacingDictionary': 'xnano._schema._appearance',
    'Style': 'xnano.styles._core_styles',
    'StyledText': 'xnano.styles._core_styles',
    'TextContent': 'xnano.styles._core_styles',
    'TextLine': 'xnano.styles._core_styles',
    'TextSpan': 'xnano.styles._core_styles',
}
"""The module each name comes from, imported the first time the name is read."""

__all__ = [
    'AppearanceArguments',
    'BorderAppearance',
    'BorderKind',
    'BorderSide',
    'CanvasAppearanceArguments',
    'Color',
    'ColorName',
    'ColorSlot',
    'ColorValue',
    'Colors',
    'Edges',
    'MarginAppearance',
    'PaddingAppearance',
    'Spacing',
    'SpacingDictionary',
    'Style',
    'StyledText',
    'TextContent',
    'TextLine',
    'TextSpan',
]


def __getattr__(name: str) -> object:
    """Import a name the first time it is read, then keep it."""
    module = _MODULES.get(name)
    if module is None:
        raise AttributeError(
            f'xnano.styles has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    value = getattr(importlib.import_module(module), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
