"""
xnano.geometry

Points, sizes and rectangles, measured in cells.

These are plain values; the position of something that moves is an
[`Expression`][xnano.expressions.Expression] instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from xnano_core import Point as _CorePoint
    from xnano_core import Rectangle as _CoreRectangle
    from xnano_core import Size as _CoreSize
    from xnano_core import SizeRule as _CoreSizeRule

    Point = _CorePoint
    """
    A cell position, counted in columns (``x``) and rows (``y``) from the top-left.

    Use it where a position is a value of its own, such as the cell of a click, or to add
    and subtract positions.

    ```python
    import xnano
    from xnano.geometry import Point

    with xnano.new(width=20, height=4) as canvas:
        start = Point(2, 1) + Point(1, 0)
        canvas.write('here', x=start.x, y=start.y)
        assert canvas.render().splitlines()[1] == '   here'
    ```
    """

    Rectangle = _CoreRectangle
    """
    A rectangle of cells, measured from its top-left corner.

    Its left and top edges are inclusive and its right and bottom edges are exclusive. Use
    it to describe an area, such as the bounds of a placement, and to test whether a
    [`Point`][xnano.geometry.Point] falls inside.

    ```python
    import xnano
    from xnano.geometry import Point, Rectangle

    area = Rectangle(2, 1, 10, 2)
    with xnano.new(width=20, height=4) as canvas:
        canvas.write('box', x=area.x, y=area.y, width=area.width, height=area.height)
        assert area.contains(Point(2, 1))
        assert not area.contains(Point(12, 1))
        assert area.area == 20
    ```
    """

    Size = _CoreSize
    """
    A width and a height, counted in cells.

    Use it where a size is a value of its own, such as the size of a canvas.

    ```python
    import xnano
    from xnano.geometry import Size

    with xnano.new(width=20, height=4) as canvas:
        assert canvas.size == Size(20, 4)
        assert Size(2, 1) + Size(3, 3) == Size(5, 4)
    ```
    """

    SizeRule = _CoreSizeRule
    """
    How much space one child takes along the main axis of a layout.

    A rule is a fixed number of cells, a percentage, a share of what is left or a limit.
    Pass it where a column of a [`Table`][xnano.widgets.Table] takes a rule instead of a
    number of cells.

    ```python
    import xnano
    from xnano.geometry import SizeRule
    from xnano.widgets import Table, TableRow

    rows = [TableRow(['name', 'value'])]
    table = Table(rows, widths=[SizeRule.cells(6), SizeRule.fill()], width=16, height=1)
    with xnano.new(width=16, height=1) as canvas:
        canvas.write(table)
        assert canvas.render() == 'name   value'
    ```
    """

_CORE_NAMES: Final[dict[str, str]] = {
    'Point': 'Point',
    'Rectangle': 'Rectangle',
    'Size': 'Size',
    'SizeRule': 'SizeRule',
}
"""The name each geometry object has in ``xnano_core``, by the name it has here."""

__all__ = [
    'Point',
    'Rectangle',
    'Size',
    'SizeRule',
]


def __getattr__(name: str) -> object:
    """Import an object from ``xnano_core`` the first time it is read, then keep it."""
    core_name = _CORE_NAMES.get(name)
    if core_name is None:
        raise AttributeError(
            f'xnano.geometry has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    import xnano_core

    value = getattr(xnano_core, core_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
