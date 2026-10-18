"""
xnano._schema._appearance

The aliases and TypedDicts for color, spacing and the appearance keywords of a canvas and of
written content.
"""

from __future__ import annotations

from typing import TypeAlias, TypedDict

import xnano_core as _core
from xnano._schema._axes import Percentage
from xnano_core import (
    ColorName as ColorName,
)
from xnano_core import ColorValue as ColorValue

RGB: TypeAlias = tuple[int, int, int]
"""A color as red, green and blue channels, each from 0 to 255."""


class SpacingDictionary(TypedDict, total=False):
    """
    Space around text, edge by edge.

    Attributes:
        top: The space above, in cells.
        right: The space to the right.
        bottom: The space below.
        left: The space to the left.
        vertical: The space above and below, unless ``top`` or ``bottom`` is given.
        horizontal: The space left and right, unless ``left`` or ``right`` is given.
    """

    top: int | float | Percentage | str
    """The space above, in cells."""
    right: int | float | Percentage | str
    """The space to the right."""
    bottom: int | float | Percentage | str
    """The space below."""
    left: int | float | Percentage | str
    """The space to the left."""
    vertical: int | float | Percentage | str
    """The space above and below, unless ``top`` or ``bottom`` is given."""
    horizontal: int | float | Percentage | str
    """The space left and right, unless ``left`` or ``right`` is given."""


Spacing: TypeAlias = int | float | Percentage | str | SpacingDictionary
"""
Space around text: one value for every edge or a [`SpacingDictionary`][xnano.types.SpacingDictionary].

A whole number is a count of cells. A float (``0.1``) or a percentage string (``'10%'``) is
a share of the text's width for the left and right edges and of its height for the top and
bottom edges, read when the spacing is applied.
"""


class CanvasAppearanceArguments(TypedDict, total=False):
    """
    How a canvas itself looks: its colors, text modifiers, border, padding and margin.

    These style the canvas, not what is written into it, so ``new()`` and ``open()`` accept
    them only without content. ``title`` is not one of them: on ``new()`` and ``open()`` it is
    the window title.

    Attributes:
        style: A ready-made style that the colors and modifiers are applied over.
        foreground: The color of the cells no content covers.
        background: The color behind the cells no content covers.
        bold: Whether the canvas's own cells are bold.
        dim: Whether they are dimmed.
        italic: Whether they are italic.
        underline: Whether they are underlined.
        blink: Whether they blink.
        reverse: Whether foreground and background are swapped.
        hidden: Whether they are hidden.
        crossed_out: Whether they are struck through.
        border: The kind of border around the canvas, ``True`` for ``'plain'``, ``False`` for none.
        border_style: The style of the border.
        padding: Space between the border and what is written into the canvas.
        margin: Space outside the border.
    """

    style: _core.Style | None
    """A ready-made style that the colors and modifiers are applied over."""
    foreground: ColorValue | None
    """The foreground color."""
    background: ColorValue | None
    """The background color."""
    bold: bool
    """Whether the cells are bold."""
    dim: bool
    """Whether the cells are dimmed."""
    italic: bool
    """Whether the cells are italic."""
    underline: bool
    """Whether the cells are underlined."""
    blink: bool
    """Whether the cells blink."""
    reverse: bool
    """Whether foreground and background are swapped."""
    hidden: bool
    """Whether the cells are hidden."""
    crossed_out: bool
    """Whether the cells are struck through."""
    border: _core.BorderKind | bool | None
    """The kind of border; ``True`` is ``'plain'`` and ``False`` is none."""
    border_style: _core.Style | None
    """The style of the border."""
    padding: Spacing | None
    """Space between the border and the content."""
    margin: Spacing | None
    """Space outside the border."""


class AppearanceArguments(CanvasAppearanceArguments, total=False):
    """
    How written content looks: the appearance keywords of ``write``.

    Attributes:
        title: A title on the border of the content.
    """

    title: str | None
    """A title on the border."""
