"""xnano.beta.frame"""

from __future__ import annotations

import dataclasses
import re
from typing import Literal, TypeAlias, Union, TYPE_CHECKING

from xnano.beta.color import ColorLike, Color
from xnano.beta.types import Border, Side, PaddingLike


FrameTitlePosition: TypeAlias = Literal["top", "bottom"]
"""The side of the frame to display the title on.

Values:
    ``"top"``: The top side of the frame.
    ``"bottom"``: The bottom side of the frame.
"""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Frame:
    """Visual border, title, and background applied to a grid cell's outer edge.

    Attributes:
        background: Fill color behind the cell's content area.
        border: Border style drawn around the cell. ``None`` renders no border.
        border_color: Color of the border lines.
        border_sides: Subset of sides to draw; draws all sides when ``None``.
        title: Text label rendered on the border edge.
        title_position: Which edge the title appears on — top or bottom.
    """

    background: ColorLike | None = None
    """Fill color behind the cell's content area."""
    border: Border | None = None
    """Border style drawn around the cell. ``None`` renders no border."""
    border_color: ColorLike | None = None
    """Color of the border lines."""
    border_sides: list[Side] | None = None
    """Subset of sides to draw; draws all sides when ``None``."""
    title: str | None = None
    """Text label rendered on the border edge."""
    title_position: FrameTitlePosition | None = None
    """Which edge the title appears on — top or bottom."""
    padding: PaddingLike | None = None
    """Padding around the cell's content area."""

    def is_empty(self) -> bool:
        """Whether this frame's attributes are all empty.

        Returns:
            True if all attributes are empty, False otherwise.
        """
        return (
            self.background is None
            and self.border is None
            and self.border_color is None
            and self.border_sides is None
            and self.title is None
            and self.title_position is None
            and self.padding is None
        )


__all__ = (
    "Frame",
    "FrameTitlePosition",
)
