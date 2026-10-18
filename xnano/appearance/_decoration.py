"""
xnano.appearance._decoration

The box-drawing layer: a border with a kind and a color per side, padding and margin, drawn
around content of any kind.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Final

import xnano_core as _core
from xnano.appearance._look import Appearance, resolve_spacing

__all__ = ['BORDER_GLYPHS', 'Decorated', 'Insets', 'insets_for', 'paint_decoration']

# horizontal, vertical, top left, top right, bottom left, bottom right
BORDER_GLYPHS: Final[Mapping[str, tuple[str, str, str, str, str, str]]] = {
    'plain': ('─', '│', '┌', '┐', '└', '┘'),
    'rounded': ('─', '│', '╭', '╮', '╰', '╯'),
    'double': ('═', '║', '╔', '╗', '╚', '╝'),
    'thick': ('━', '┃', '┏', '┓', '┗', '┛'),
}

_TRANSPARENT: Final = _core.Cell(' ', is_transparent=True)


@dataclasses.dataclass(frozen=True, slots=True)
class Insets:
    """
    The cells a look adds around content, as ``(left, top, right, bottom)`` for each layer.

    Attributes:
        margin: The transparent ring outside the border.
        border: The cells of the border: 1 for a side that is drawn, 0 for one that is not.
        padding: The cells between the border and the content.
    """

    margin: tuple[int, int, int, int]
    """The transparent ring outside the border."""
    border: tuple[int, int, int, int]
    """The cells of the border: 1 for a side that is drawn, 0 for one that is not."""
    padding: tuple[int, int, int, int]
    """The cells between the border and the content."""

    @property
    def left(self) -> int:
        """Everything to the left of the content."""
        return self.margin[0] + self.border[0] + self.padding[0]

    @property
    def top(self) -> int:
        """Everything above the content."""
        return self.margin[1] + self.border[1] + self.padding[1]

    @property
    def right(self) -> int:
        """Everything to the right of the content."""
        return self.margin[2] + self.border[2] + self.padding[2]

    @property
    def bottom(self) -> int:
        """Everything below the content."""
        return self.margin[3] + self.border[3] + self.padding[3]

    @property
    def horizontal(self) -> int:
        """The columns added around the content."""
        return self.left + self.right

    @property
    def vertical(self) -> int:
        """The rows added around the content."""
        return self.top + self.bottom

    def as_tuple(self) -> tuple[int, int, int, int]:
        """The totals as ``(left, top, right, bottom)``."""
        return (self.left, self.top, self.right, self.bottom)


def insets_for(look: Appearance, content_width: int, content_height: int) -> Insets:
    """
    Resolve the margin, border and padding of a look into whole cells.

    Percentages are shares of the content's size.

    Args:
        look: The look to resolve.
        content_width: The width of the content, in cells.
        content_height: The height of the content, in cells.
    """
    margin_left, margin_right, margin_top, margin_bottom = resolve_spacing(
        look.margin, width=content_width, height=content_height, name='margin'
    )
    padding_left, padding_right, padding_top, padding_bottom = resolve_spacing(
        look.padding, width=content_width, height=content_height, name='padding'
    )
    drawn = look.drawn_sides()
    return Insets(
        margin=(margin_left, margin_top, margin_right, margin_bottom),
        border=(
            int('left' in drawn),
            int('top' in drawn),
            int('right' in drawn),
            int('bottom' in drawn),
        ),
        padding=(padding_left, padding_top, padding_right, padding_bottom),
    )


def _side_style(look: Appearance, color: object) -> _core.Style | None:
    """The style of a border side: the border's style, the side's color over it, then the fill."""
    base = look.border_style
    if color is not None:
        own = _core.Style(foreground=color)  # type: ignore[arg-type]
        base = own if base is None else base.patch(own)
    if look.background is not None:
        fill = _core.Style(background=look.background)
        base = fill if base is None else fill.patch(base)
    return base


def paint_decoration(target: _core.Buffer, look: Appearance, insets: Insets) -> None:
    """
    Draw the margin, border and padding of a look on the edges of ``target``.

    ``target`` is already as large as the content plus the insets. Every cell outside the
    content is redrawn, so a smaller border or margin leaves nothing behind; the content
    area is left alone, apart from padding.

    Args:
        target: The buffer that carries the decoration.
        look: The look to draw.
        insets: The cells the look adds, from [`insets_for`][xnano.appearance._decoration.insets_for].
    """
    width = target.width
    height = target.height
    margin_left, margin_top, margin_right, margin_bottom = insets.margin
    content_x = insets.left
    content_y = insets.top
    content_width = max(0, width - insets.horizontal)
    content_height = max(0, height - insets.vertical)

    target.update(_core.Fill(_TRANSPARENT))
    box_left = margin_left
    box_top = margin_top
    box_right = width - margin_right
    box_bottom = height - margin_bottom
    if box_right <= box_left or box_bottom <= box_top:
        return
    filler = _core.Cell(' ')
    if look.background is not None:
        filler = _core.Cell(' ', background=look.background)
    target[box_left:box_right, box_top:box_bottom].update(_core.Fill(filler))
    if content_width and content_height:
        target[
            content_x : content_x + content_width, content_y : content_y + content_height
        ].update(_core.Fill(_TRANSPARENT))

    drawn = look.drawn_sides()
    if not drawn:
        return
    writes: list[_core.Operation] = []
    top = drawn.get('top')
    bottom = drawn.get('bottom')
    left = drawn.get('left')
    right = drawn.get('right')
    span = box_right - box_left
    for row, side, has_left, has_right, corner_left, corner_right in (
        (box_top, top, left is not None, right is not None, 2, 3),
        (box_bottom - 1, bottom, left is not None, right is not None, 4, 5),
    ):
        if side is None:
            continue
        kind, color = side
        glyphs = BORDER_GLYPHS[kind]
        if span == 1:
            line = glyphs[0]
        else:
            line = (
                (glyphs[corner_left] if has_left else glyphs[0])
                + glyphs[0] * (span - 2)
                + (glyphs[corner_right] if has_right else glyphs[0])
            )
        style = _side_style(look, color)
        writes.append(_core.Write(line, x=box_left, y=row, style=style))
        if look.title is not None and row == box_top and span > 2:
            title = look.title[: span - 2]
            writes.append(_core.Write(title, x=box_left + 1, y=row, style=style))
    if writes:
        target.update(*writes)
    first_row = box_top + (1 if top is not None else 0)
    last_row = box_bottom - (1 if bottom is not None else 0)
    if last_row > first_row:
        for column, side in ((box_left, left), (box_right - 1, right)):
            if side is None:
                continue
            kind, color = side
            cell = _core.Cell(BORDER_GLYPHS[kind][1], style=_side_style(look, color))
            target[column : column + 1, first_row:last_row].update(_core.Fill(cell))


class Decorated:
    """
    The two buffers of an owner whose content sits inside a decoration.

    ``outer`` is the buffer that is mounted and positioned, and it carries the margin, border
    and padding. ``inner`` is a child of ``outer`` where the content and any nested
    placements live. An owner that is not decorated has no ``Decorated``.

    Attributes:
        outer: The buffer that is mounted and positioned.
        inner: The buffer that holds the content.
        insets: The cells last drawn around the content.
    """

    __slots__ = ('inner', 'insets', 'outer')

    def __init__(self, outer: _core.Buffer, inner: _core.Buffer) -> None:
        """
        Pair an outer buffer with the inner buffer attached to it.

        Args:
            outer: The buffer that is mounted and positioned.
            inner: The buffer that holds the content.
        """
        self.outer = outer
        self.inner = inner
        self.insets = Insets((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))

    @classmethod
    def promote(cls, outer: _core.Buffer, *, copy_cells: bool) -> Decorated:
        """
        Move the content of ``outer`` into a new child buffer, keeping ``outer`` in place.

        Args:
            outer: The buffer to promote. Its cells and its child buffers move to the child.
            copy_cells: Whether the cells of ``outer`` are content that must be kept (a
                widget or a region), rather than a text that is drawn again.
        """
        inner = _core.Buffer(width=outer.width, height=outer.height)
        if copy_cells:
            inner.update(_core.Paste(outer, mode='replace'))
        for child in list(outer.children):
            outer.detach(child)
            inner.attach(child, mode='transparent')
        outer.update(_core.Fill(_TRANSPARENT))
        outer.attach(inner, mode='transparent')
        return cls(outer, inner)

    def demote(self, *, copy_cells: bool) -> None:
        """
        Move the content back into ``outer`` and drop ``inner``.

        Args:
            copy_cells: Whether the cells of ``inner`` are content that must be kept.
        """
        outer = self.outer
        inner = self.inner
        for child in list(inner.children):
            inner.detach(child)
            outer.attach(child, mode='transparent')
        outer.detach(inner)
        outer.width = max(1, outer.width - self.insets.horizontal)
        outer.height = max(1, outer.height - self.insets.vertical)
        outer.update(_core.Fill(_core.Cell(' ')))
        if copy_cells:
            outer.update(_core.Paste(inner, mode='replace'))

    def repaint(self, look: Appearance, insets: Insets) -> None:
        """
        Place ``inner`` inside ``outer`` and draw the decoration around it.

        Args:
            look: The look to draw.
            insets: The cells the look adds around the content.
        """
        self.inner.x = insets.left
        self.inner.y = insets.top
        paint_decoration(self.outer, look, insets)
        self.insets = insets

    def fit_inner(self) -> None:
        """Make ``inner`` as large as ``outer`` leaves room for."""
        self.inner.width = max(0, self.outer.width - self.insets.horizontal)
        self.inner.height = max(0, self.outer.height - self.insets.vertical)
