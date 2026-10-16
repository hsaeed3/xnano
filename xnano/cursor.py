"""
xnano.cursor

A canvas's cursor: where it is, how it looks, and how to move it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import xnano_core as _core
from xnano._axes import check_cells, check_count

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.placement import Placement

__all__ = ['Cursor']


class Cursor:
    """
    The one cursor a canvas has.

    Get it from [`Canvas.cursor`][xnano.canvas.Canvas.cursor] or from ``context.cursor``
    inside a hook. A canvas draws no cursor until it is given a position, which a text field
    does to show where typing goes. Any thread may change it, a change is drawn on the next
    frame even when no cell changed, and a canvas on the screen gives the user's own cursor
    back when it closes. Opening a canvas on the screen keeps its cursor as it was.

    Moving is relative to where the cursor is: [`up`][xnano.cursor.Cursor.up],
    [`down`][xnano.cursor.Cursor.down], [`left`][xnano.cursor.Cursor.left] and
    [`right`][xnano.cursor.Cursor.right] move it by a count of cells, and
    [`move`][xnano.cursor.Cursor.move] moves it along both axes at once. The cursor stays
    inside the canvas, so moving past an edge stops at the edge. A cursor with no position
    moves from the top-left cell. Each of these returns the cursor, so they chain.

    Attributes:
        position: The cell the cursor is at as a [`Point`][xnano_core.Point], or ``None`` when
            it has none. Assign a ``Point``, a ``(column, row)`` pair or ``None``.
        shape: ``'block'``, ``'bar'`` or ``'underline'``; ``None`` keeps the user's own shape.
        is_blinking: Whether the cursor blinks. Setting it without a shape uses a block.
        is_visible: Whether the cursor is shown when it has a position.

    Examples:
        ```python
        import xnano
        from xnano_core import Point

        with xnano.new(width=10, height=3) as canvas:
            canvas.cursor.shape = 'bar'
            canvas.cursor.home().right(4).down()
            assert canvas.cursor.position == Point(4, 1)
        ```
    """

    def __init__(self, canvas: Canvas[object, object]) -> None:
        """
        Create the canvas's cursor. Use ``canvas.cursor`` instead of calling this.

        Args:
            canvas: The canvas the cursor belongs to.
        """
        self._canvas = canvas

    @property
    def _source(self) -> _core.Cursor:
        return self._canvas._cursor_source

    @property
    def position(self) -> _core.Point | None:
        """The cell the cursor is at, or ``None`` when it has none."""
        return self._source.position

    @position.setter
    def position(self, value: _core.Point | tuple[int, int] | None) -> None:
        self._source.position = value
        self._canvas._cursor_follow = None

    @property
    def shape(self) -> _core.CursorShape | None:
        """``'block'``, ``'bar'`` or ``'underline'``; ``None`` keeps the user's own shape."""
        return self._source.shape

    @shape.setter
    def shape(self, value: _core.CursorShape | None) -> None:
        self._source.shape = value

    @property
    def is_blinking(self) -> bool:
        """Whether the cursor blinks. Setting it without a shape uses a block."""
        return self._source.is_blinking

    @is_blinking.setter
    def is_blinking(self, value: bool) -> None:
        self._source.is_blinking = value

    @property
    def is_visible(self) -> bool:
        """Whether the cursor is shown when it has a position."""
        return self._source.is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._source.is_visible = value

    def move(self, x: int = 0, y: int = 0) -> Cursor:
        """
        Move the cursor by a number of cells along each axis.

        Args:
            x: Columns to move right; a negative number moves left.
            y: Rows to move down; a negative number moves up.

        Returns:
            The cursor, so calls can chain.

        Raises:
            TypeError: An amount is not a whole number.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.new(width=10, height=3) as canvas:
                canvas.cursor.position = (2, 1)
                canvas.cursor.move(x=3, y=-1)
                assert canvas.cursor.position == Point(5, 0)
                canvas.cursor.move(x=-99)
                assert canvas.cursor.position == Point(0, 0)
            ```
        """
        horizontal = check_cells(x, 'x')
        vertical = check_cells(y, 'y')
        source = self._source
        current = source.position
        column, row = (0, 0) if current is None else (current.x, current.y)
        size = self._canvas.size
        column = min(max(column + horizontal, 0), max(size.width - 1, 0))
        row = min(max(row + vertical, 0), max(size.height - 1, 0))
        source.position = (column, row)
        self._canvas._cursor_follow = None
        return self

    def up(self, count: int = 1) -> Cursor:
        """
        Move the cursor up by ``count`` rows, stopping at the top.

        Args:
            count: How many rows to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(y=-check_count(count))

    def down(self, count: int = 1) -> Cursor:
        """
        Move the cursor down by ``count`` rows, stopping at the bottom.

        Args:
            count: How many rows to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(y=check_count(count))

    def left(self, count: int = 1) -> Cursor:
        """
        Move the cursor left by ``count`` columns, stopping at the left edge.

        Args:
            count: How many columns to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(x=-check_count(count))

    def right(self, count: int = 1) -> Cursor:
        """
        Move the cursor right by ``count`` columns, stopping at the right edge.

        Args:
            count: How many columns to move.

        Raises:
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        return self.move(x=check_count(count))

    def home(self) -> Cursor:
        """Put the cursor in the top-left cell."""
        self._source.position = (0, 0)
        self._canvas._cursor_follow = None
        return self

    def show(self) -> Cursor:
        """
        Make the cursor visible, in the top-left cell when it has no position yet.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.new(width=10, height=3) as canvas:
                canvas.cursor.show()
                assert canvas.cursor.is_visible
                assert canvas.cursor.position == Point(0, 0)
            ```
        """
        source = self._source
        if source.position is None:
            source.position = (0, 0)
        source.is_visible = True
        return self

    def hide(self) -> Cursor:
        """Hide the cursor. Its position is kept, so [`show`][xnano.cursor.Cursor.show] brings it back."""
        self._source.is_visible = False
        return self

    def follow(
        self, target: Placement[object, object] | _core.Buffer, *, x: int = 0, y: int = 0
    ) -> Cursor:
        """
        Keep the cursor at a place inside a placement or buffer, wherever it goes.

        The cursor hides while the target, or anything above it, is hidden. Assigning
        ``position`` or calling [`move`][xnano.cursor.Cursor.move] stops the following.

        Args:
            target: The [`Placement`][xnano.placement.Placement] or buffer to follow.
            x: The column inside the target.
            y: The row inside the target.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.new(width=20, height=3) as canvas:
                field = canvas.write('name', x=5, y=1)
                canvas.cursor.follow(field, x=4)
                field.x = 8
                assert canvas.cursor.position == Point(12, 1)
            ```
        """
        buffer = target if isinstance(target, _core.Buffer) else target.core_buffer
        self._source.follow(buffer, x=x, y=y)
        self._canvas._cursor_follow = (buffer, x, y)
        return self

    def unfollow(self) -> Cursor:
        """Stop following a placement or buffer, leaving the cursor where it is."""
        source = self._source
        current = source.position
        source.follow(None)
        self._canvas._cursor_follow = None
        if current is not None:
            source.position = current
        return self

    def __repr__(self) -> str:
        position = self.position
        where = None if position is None else (position.x, position.y)
        return f'Cursor(position={where}, is_visible={self.is_visible})'
