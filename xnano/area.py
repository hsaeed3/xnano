"""xnano.area

---

Geometry primitives shared by every layer: rectangular areas, measured
sizes, padding, and the alignment arithmetic that places one inside
another.
"""

from __future__ import annotations

import dataclasses
from typing import Literal, TypeAlias, Union, cast

VerticalAlignment: TypeAlias = Literal["top", "middle", "bottom"]
"""Vertical (y-axis) alignment of a grid field or area.

Values:
    ``"top"``: Aligned to the top edge.
    ``"middle"``: Centered vertically.
    ``"bottom"``: Aligned to the bottom edge.
"""

Alignment: TypeAlias = Literal["left", "right", "center"]
"""Horizontal (x-axis) alignment of a grid field or area.

Values:
    ``"left"``: Aligned to the left.
    ``"right"``: Aligned to the right.
    ``"center"``: Centered.
"""


Coordinate: TypeAlias = tuple[int, int]
"""A single ``(x, y)`` cell coordinate within the terminal grid."""


PaddingLike: TypeAlias = Union[
    int,
    tuple[int, int],
    tuple[int | None, int | None, int | None, int | None],
    "Padding",
]
"""Padding around a rectangular area, in any accepted input form:

    - A single integer, applied to all four sides.
    - A ``(vertical, horizontal)`` tuple of two integers.
    - A ``(top, right, bottom, left)`` tuple of four integers.
    - A ``Padding`` instance.
"""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Padding:
    """Padding around a rectangular area.

    Attributes:
        top: Cells above the content.
        right: Cells to the right of the content.
        bottom: Cells below the content.
        left: Cells to the left of the content.

    Examples:
        ```python
        padding = Padding.parse((1, 2))
        ```
    """

    top: int = 0
    """Cells above the content."""
    right: int = 0
    """Cells to the right of the content."""
    bottom: int = 0
    """Cells below the content."""
    left: int = 0
    """Cells to the left of the content."""

    @classmethod
    def parse(cls, padding: PaddingLike | None) -> "Padding":
        """Normalize a padding value."""
        if padding is None:
            return cls()
        if isinstance(padding, cls):
            return padding
        if isinstance(padding, int):
            return cls(
                top=padding,
                right=padding,
                bottom=padding,
                left=padding,
            )
        values = cast(
            tuple[int, int]
            | tuple[int | None, int | None, int | None, int | None],
            padding,
        )
        if len(values) == 2:
            vertical, horizontal = values
            return cls(
                top=vertical or 0,
                right=horizontal or 0,
                bottom=vertical or 0,
                left=horizontal or 0,
            )
        top, right, bottom, left = values
        return cls(
            top=top or 0,
            right=right or 0,
            bottom=bottom or 0,
            left=left or 0,
        )

    @property
    def horizontal(self) -> int:
        """Total horizontal padding."""
        return self.left + self.right

    @property
    def vertical(self) -> int:
        """Total vertical padding."""
        return self.top + self.bottom


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Size:
    """Resolved width and height in cells.

    Attributes:
        width: Width in cells.
        height: Height in cells.
    """

    width: int
    """Width in cells."""
    height: int
    """Height in cells."""

    @classmethod
    def from_tuple(cls, size: tuple[int, int]) -> "Size":
        """Create a size from ``(width, height)``."""
        return cls(width=size[0], height=size[1])

    @classmethod
    def from_int(cls, size: int) -> "Size":
        """Create a square size."""
        return cls(width=size, height=size)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Area:
    """Rectangular region of a cell grid.

    Attributes:
        x: Left column.
        y: Top row.
        width: Width in cells.
        height: Height in cells.
    """

    x: int
    """Left column."""
    y: int
    """Top row."""
    width: int
    """Width in cells."""
    height: int
    """Height in cells."""

    @property
    def size(self) -> Size:
        """Width and height of this area."""
        return Size(width=self.width, height=self.height)

    def contains(self, coordinate: Coordinate) -> bool:
        """Return whether ``coordinate`` lies inside this area."""
        column, row = coordinate
        return (
            self.x <= column < self.x + self.width
            and self.y <= row < self.y + self.height
        )

    def fit_content(
        self,
        content: Size,
        horizontal: "Alignment | None" = None,
        vertical: "VerticalAlignment | None" = None,
    ) -> "Area":
        """Fit a measured size inside this area on both axes.

        Args:
            content: Measured content size, clamped to this area.
            horizontal: Horizontal placement (default ``"left"``).
            vertical: Vertical placement (default ``"top"``).

        Returns:
            The fitted, aligned area.
        """
        return align_area(
            self,
            min(self.width, max(content.width, 1)),
            min(self.height, max(content.height, 1)),
            horizontal=horizontal,
            vertical=vertical,
        )


def align_area(
    outer: Area,
    width: int,
    height: int,
    *,
    horizontal: "Alignment | None" = None,
    vertical: "VerticalAlignment | None" = None,
) -> Area:
    """Place a ``width`` x ``height`` box inside ``outer`` on both axes.

    ``None`` on an axis anchors to its leading edge.

    Args:
        outer: The area to place the box within.
        width: Box width, clamped to ``outer``.
        height: Box height, clamped to ``outer``.
        horizontal: Horizontal placement (default ``"left"``).
        vertical: Vertical placement (default ``"top"``).

    Returns:
        The placed area, always inside ``outer``.
    """
    width = max(0, min(width, outer.width))
    height = max(0, min(height, outer.height))
    if horizontal == "right":
        x = outer.x + outer.width - width
    elif horizontal == "center":
        x = outer.x + (outer.width - width) // 2
    else:
        x = outer.x
    if vertical == "bottom":
        y = outer.y + outer.height - height
    elif vertical == "middle":
        y = outer.y + (outer.height - height) // 2
    else:
        y = outer.y
    return Area(x=x, y=y, width=width, height=height)


__all__ = (
    "Alignment",
    "Area",
    "Coordinate",
    "Padding",
    "PaddingLike",
    "Size",
    "VerticalAlignment",
    "align_area",
)
