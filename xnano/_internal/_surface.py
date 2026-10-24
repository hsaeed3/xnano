"""
xnano._internal._surface

Where content is written and drawn for an owner that is a canvas or a placement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.devices._screen import Screen
    from xnano.layout._placement import Placement

__all__ = ['surface_of']


def surface_of(
    owner: Canvas[object, object] | Placement[object, object],
) -> Screen[object, object] | Placement[object, object]:
    """
    Where content is written and drawn for ``owner``: the screen of a canvas, or a placement.

    A canvas draws through its screen and a placement is its own surface, so code that serves
    both reads sizes, regions and edges, and writes, through this.
    """
    # Imported here because the canvas imports the modules that call this.
    from xnano.canvas import Canvas

    return owner.screen if isinstance(owner, Canvas) else owner
