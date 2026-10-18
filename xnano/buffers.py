"""
xnano.buffers

Buffers: grids of cells that hold text and styles.

A [`Buffer`][xnano.buffers.Buffer] is what a canvas draws; each [`Cell`][xnano.buffers.Cell] holds
one symbol with its colors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from xnano_core import Buffer as _CoreBuffer
    from xnano_core import Cell as _CoreCell

    Buffer = _CoreBuffer
    """
    A grid of cells with a position and a size, which a canvas draws.

    Write one onto a canvas to place prepared content, or build one cell by cell with
    [`Cell`][xnano.buffers.Cell].

    ```python
    import xnano
    from xnano.buffers import Buffer

    card = Buffer('hello', width=8, height=2)
    with xnano.new(width=12, height=3) as canvas:
        canvas.write(card, x=2, y=1)
        assert canvas.render().splitlines()[1] == '  hello'
    ```
    """

    Cell = _CoreCell
    """
    One symbol with its style, copied out of or written into a buffer.

    Use it to read or change a single cell of a [`Buffer`][xnano.buffers.Buffer].

    ```python
    import xnano
    from xnano.buffers import Buffer, Cell

    buffer = Buffer(width=3, height=1)
    buffer[1, 0] = Cell('x', foreground='red')
    with xnano.new(width=3, height=1) as canvas:
        canvas.write(buffer)
        assert buffer[1, 0].symbol == 'x'
        assert canvas.render() == ' x'
    ```
    """

_CORE_NAMES: Final[dict[str, str]] = {
    'Buffer': 'Buffer',
    'Cell': 'Cell',
}
"""The name each buffers object has in ``xnano_core``, by the name it has here."""

__all__ = [
    'Buffer',
    'Cell',
]


def __getattr__(name: str) -> object:
    """Import an object from ``xnano_core`` the first time it is read, then keep it."""
    core_name = _CORE_NAMES.get(name)
    if core_name is None:
        raise AttributeError(
            f'xnano.buffers has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    import xnano_core

    value = getattr(xnano_core, core_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
