"""xnano.tailwind"""

from __future__ import annotations

from typing import Literal, TypeAlias

from xnano import _core
from xnano.color import Color


TailwindShade: TypeAlias = Literal[
    50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950
]
"""A Tailwind CSS color shade value."""


def tailwind(name: str, shade: TailwindShade) -> Color:
    """Look up a color from the Tailwind CSS palette.

    Args:
        name: The Tailwind color name (e.g. 'red', 'blue', 'slate', 'emerald').
        shade: The shade intensity (50–950).

    Returns:
        The Color at the given name and shade.

    Example::

        red_500 = tailwind('red', 500)
        slate_900 = tailwind('slate', 900)
    """
    return Color.from_native(_core.tailwind_color(name, shade))


__all__ = ("TailwindShade", "tailwind")
