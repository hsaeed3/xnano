"""xnano.types"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Literal, Sequence, TypeAlias, Union


Alignment: TypeAlias = Literal["left", "right", "center"]
"""The alignment of a grid field or area along the horizontal (x) axis.

Values:
    ``"left"``: The field or area should be aligned to the left.
    ``"right"``: The field or area should be aligned to the right.
    ``"center"``: The field or area should be aligned to the center.
"""


Axis: TypeAlias = Literal["x", "y"]
"""The axis along which a grid field or area should be laid out.

Values:
    ``"x"``: The field or area should be laid out horizontally.
    ``"y"``: The field or area should be laid out vertically.
"""


Border: TypeAlias = Literal[
    "plain",
    "rounded",
    "double",
    "thick",
    "quadrant_inside",
    "quadrant_outside",
]
"""The type of border to apply around the outside edges of a rectangular
area.

Values:
    ``"plain"``: A plain border with no additional styling. (`---------`)
    ``"rounded"``: A border with rounded corners. (`╭───────╮`)
    ``"double"``: A border with double lines. (`╔═══════╗`)
    ``"thick"``: A border with thick/dark lines. (`┏━━━━━━━┓`)
    ``"quadrant_inside"``: Quadrant-style borders for inner division. (`▛▀▀▀▀▀▜`)
    ``"quadrant_outside"``: Quadrant-style borders for outer corners. (`▗▄▄▄▄▄▖`)
"""


Coordinate: TypeAlias = tuple[int, int]
"""A single (x, y) cell coordinate within the terminal grid.

Example:
    >>> position = (10, 4)  # column 10, row 4
"""


Corner: TypeAlias = Literal[
    "top-left", "top-right", "bottom-left", "bottom-right"
]
"""A single corner of a of a rectangular grid area within the
main terminal grid.

Values:
    ``"top-left"``: The top-left corner.
    ``"top-right"``: The top-right corner.
    ``"bottom-left"``: The bottom-left corner.
    ``"bottom-right"``: The bottom-right corner.
"""


Direction: TypeAlias = Literal["horizontal", "vertical"]
"""The direction in which content within a grid field or area should be
laid out.

Values:
    ``"horizontal"``: The field or area should be laid out horizontally.
    ``"vertical"``: The field or area should be laid out vertically.
"""


CharacterModifier: TypeAlias = Literal[
    "bold",
    "dim",
    "italic",
    "underline",
    "slow_blink",
    "rapid_blink",
    "reversed",
]
"""A modifier to apply to the content of a grid field or area.

Values:
    ``"bold"``: Renders the content in bold.
    ``"dim"``: The content is rendered with reduced intensity.
    ``"italic"``: Renders the content in italics.
    ``"underline"``: Adds an underline beneath the content.
    ``"slow_blink"``: Causes the content to blink slowly.
    ``"rapid_blink"``: Causes the content to blink rapidly.
    ``"reversed"``: Swaps foreground and background colors.
"""


PaddingLike: TypeAlias = Union[
    int,
    tuple[int, int],
    tuple[int | None, int | None, int | None, int | None],
    "Padding",
]
"""Padding around a rectangular area, in any accepted input form.

This can be represented as one of the following options:
    - A single integer, applied to all four sides
    - A tuple of two integers as (vertical, horizontal)
    - A tuple of four integers as (top, right, bottom, left)
    - A ``Padding`` instance
"""


ScrollbarOrientationLike: TypeAlias = Literal[
    "vertical_right",
    "vertical_left",
    "horizontal_bottom",
    "horizontal_top",
]
"""The orientation of a scrollbar widget.

Values:
    ``"vertical_right"``: Vertical scrollbar on the right edge.
    ``"vertical_left"``: Vertical scrollbar on the left edge.
    ``"horizontal_bottom"``: Horizontal scrollbar on the bottom edge.
    ``"horizontal_top"``: Horizontal scrollbar on the top edge.
"""


CanvasMarkerLike: TypeAlias = Literal[
    "dot",
    "block",
    "bar",
    "braille",
    "half_block",
]
"""The marker glyph set used when drawing on a Canvas widget.

Values:
    ``"dot"``: Single-pixel dots.
    ``"block"``: Full-block characters.
    ``"bar"``: Horizontal bar characters.
    ``"braille"``: Braille dot matrix (highest resolution).
    ``"half_block"``: Half-block characters.
"""


GraphTypeLike: TypeAlias = Literal["line", "scatter", "bar"]
"""How a ``Chart`` dataset is plotted.

Values:
    ``"line"``: Connect points with lines.
    ``"scatter"``: Draw points without connecting lines.
    ``"bar"``: Draw each point as a vertical bar.
"""


LegendPositionLike: TypeAlias = Literal[
    "top",
    "top_right",
    "top_left",
    "left",
    "right",
    "bottom",
    "bottom_right",
    "bottom_left",
]
"""Placement of a ``Chart``'s legend within its area."""


Side: TypeAlias = Literal["top", "bottom", "left", "right"]
"""A single side of a of a rectangular grid area within the
main terminal grid.

Values:
    ``"top"``: The top side.
    ``"bottom"``: The bottom side.
    ``"left"``: The left side.
    ``"right"``: The right side.
"""


SizePercentage: TypeAlias = tuple[float, float] | float
"""The percentage of the parent grid area's width and height that
a field/area should occupy.

This can be passed in as a (width, height) tuple or a single float value
representing fixed percentage on both axes.

Example:
    >>> SizePercentage(0.5, 0.75)  # 50% width, 75% height
    >>> SizePercentage(0.5)        # 50% on both axes
"""


Flex: TypeAlias = (
    int
    | Literal[
        "flex-1",
        "flex-auto",
        "flex-initial",
        "flex-none",
        "grow",
        "grow-0",
        "shrink",
        "shrink-0",
    ]
)
"""Relative fill weight for proportional layout, or a Tailwind flex utility.

Numeric values set the fill weight directly. Tailwind classes map to
proportional grow weights:

    ``"flex-1"``, ``"flex-auto"``, ``"grow"``, ``"shrink"`` → weight ``1``
    ``"flex-initial"``, ``"flex-none"``, ``"grow-0"``, ``"shrink-0"`` → weight ``0``
"""


_FLEX_CLASS_WEIGHTS: dict[str, int] = {
    "flex-1": 1,
    "flex-auto": 1,
    "grow": 1,
    "shrink": 1,
    "flex-initial": 0,
    "flex-none": 0,
    "grow-0": 0,
    "shrink-0": 0,
}


def resolve_flex_weight(flex: Flex | None) -> int | None:
    """Normalize a ``Flex`` value to a numeric fill weight.

    Args:
        flex: A numeric fill weight or Tailwind flex utility class.

    Returns:
        The resolved fill weight, or ``None`` when ``flex`` is ``None``.

    Raises:
        ValueError: If ``flex`` is an unrecognized flex utility class.
        TypeError: If ``flex`` is not a supported type.
    """
    if flex is None:
        return None
    if isinstance(flex, int):
        return flex
    if isinstance(flex, str):
        if flex not in _FLEX_CLASS_WEIGHTS:
            raise ValueError(
                f"flex must be an int or a supported Tailwind flex class, "
                f"got {flex!r}"
            )
        return _FLEX_CLASS_WEIGHTS[flex]
    raise TypeError(
        f"flex must be an int or a supported Tailwind flex class, "
        f"got {type(flex).__name__}"
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Padding:
    """The padding applied around a rectangular area.

    Attributes:
        top: The padding on the top side of the area.
        right: The padding on the right side of the area.
        bottom: The padding on the bottom side of the area.
        left: The padding on the left side of the area.
    """

    top: int = 0
    """The padding on the top side of the area."""
    right: int = 0
    """The padding on the right side of the area."""
    bottom: int = 0
    """The padding on the bottom side of the area."""
    left: int = 0
    """The padding on the left side of the area."""

    @classmethod
    def parse(
        cls,
        padding: PaddingLike | None,
    ) -> Padding:
        """Normalize any accepted padding form into a ``Padding``.

        Args:
            padding: Padding around a rectangular area, in any accepted
                input form.

        Returns:
            A ``Padding`` instance.
        """
        if padding is None:
            return cls()
        if isinstance(padding, Padding):
            return padding
        if isinstance(padding, int):
            return cls(
                top=padding, right=padding, bottom=padding, left=padding
            )
        if len(padding) == 2:
            vertical, horizontal = padding
            return cls(
                top=vertical if vertical is not None else 0,
                right=horizontal if horizontal is not None else 0,
                bottom=vertical if vertical is not None else 0,
                left=horizontal if horizontal is not None else 0,
            )
        top, right, bottom, left = padding
        return cls(
            top=top if top is not None else 0,
            right=right if right is not None else 0,
            bottom=bottom if bottom is not None else 0,
            left=left if left is not None else 0,
        )

    @property
    def horizontal(self) -> int:
        """The total padding along the horizontal axis."""
        return self.left + self.right

    @property
    def vertical(self) -> int:
        """The total padding along the vertical axis."""
        return self.top + self.bottom


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Size:
    """The resolved size of a rectangular grid area within the
    main terminal grid.

    Attributes:
        width: The width of the grid area.
        height: The height of the grid area.
    """

    width: int
    """The width of the grid area."""
    height: int
    """The height of the grid area."""

    @classmethod
    def from_tuple(cls, size: tuple[int, int]) -> Size:
        """Creates a ``Size`` instance from a tuple of two integers.

        Args:
            size: A tuple of two integers representing the width and height of the grid area.

        Returns:
            A ``GridSize`` instance.
        """
        return cls(width=size[0], height=size[1])

    @classmethod
    def from_int(cls, size: int) -> Size:
        """Creates a ``Size`` instance from a single integer.

        Args:
            size: A single integer representing the width and height of the grid area.

        Returns:
            A ``GridSize`` instance.
        """
        return cls(width=size, height=size)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Area:
    """A rectangular grid region within the main terminal grid or
    display area.

    ``Area`` is a purely geometric type and does not contain
    any renderable content of it's own.

    Attributes:
        x: The x-coordinate of the top-left corner of the grid area.
        y: The y-coordinate of the top-left corner of the grid area.
        width: The width of the grid area.
        height: The height of the grid area.
    """

    x: int
    """The x-coordinate of the top-left corner of the grid area."""
    y: int
    """The y-coordinate of the top-left corner of the grid area."""
    width: int
    """The width of the grid area."""
    height: int
    """The height of the grid area."""

    @property
    def size(self) -> Size:
        """The size of this area."""
        return Size(width=self.width, height=self.height)

    def contains(self, coordinate: Coordinate) -> bool:
        """Return whether a terminal cell coordinate lies inside this area.

        Args:
            coordinate: The (x, y) cell coordinate to check.

        Returns:
            True if the coordinate lies inside the area, False otherwise.
        """
        column, row = coordinate
        return (
            self.x <= column < self.x + self.width
            and self.y <= row < self.y + self.height
        )

    def fit_content(
        self,
        content: Size,
        align: Alignment = "left",
    ) -> Area:
        """Shrink this area to fit a measured content size.

        The fitted area is clamped to this area's bounds, aligned
        horizontally by ``align``, and centered vertically.

        Args:
            content: The measured size of the content to fit.
            align: The horizontal alignment of the fitted area.

        Returns:
            A new ``GridArea`` positioned within this one.
        """
        width = min(self.width, max(content.width, 1))
        height = min(self.height, max(content.height, 1))
        if align == "right":
            x = self.x + self.width - width
        elif align == "center":
            x = self.x + (self.width - width) // 2
        else:
            x = self.x
        y = self.y + (self.height - height) // 2
        return Area(x=x, y=y, width=width, height=height)


__all__ = (
    "Alignment",
    "Axis",
    "Border",
    "Coordinate",
    "Corner",
    "Direction",
    "CharacterModifier",
    "PaddingLike",
    "ScrollbarOrientationLike",
    "CanvasMarkerLike",
    "GraphTypeLike",
    "LegendPositionLike",
    "Side",
    "SizePercentage",
    "Flex",
    "resolve_flex_weight",
    "Padding",
    "Size",
    "Area",
)
