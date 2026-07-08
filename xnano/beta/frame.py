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


def field_has_frame_chrome(field: object) -> bool:
    """Whether a field defines border, title, or padding chrome.

    Args:
        field: A ``GridFieldInfo``-like object with optional frame attributes.

    Returns:
        True when the field has structural frame chrome beyond text styling.
    """
    return (
        getattr(field, "border", None) is not None
        or getattr(field, "title", None) is not None
        or getattr(field, "padding", None) is not None
    )


def frame_from_field(field: object | None) -> Frame | None:
    """Build a ``Frame`` from a field's chrome, or ``None`` when absent.

    Text-only ``background`` on a field styles rendered content and is not
    promoted to frame fill unless border, title, or padding chrome is present.

    Args:
        field: The field describing border, padding, title, and optional fill.

    Returns:
        A ``Frame`` when the field defines any chrome, otherwise ``None``.
    """
    if field is None:
        return None

    has_frame_chrome = field_has_frame_chrome(field)
    border_sides = getattr(field, "border_sides", None)
    frame = Frame(
        background=getattr(field, "background", None)
        if has_frame_chrome
        else None,
        border=getattr(field, "border", None),
        border_color=getattr(field, "border_color", None),
        border_sides=list(border_sides) if border_sides is not None else None,
        title=getattr(field, "title", None),
        title_position=getattr(field, "title_position", None),
        padding=getattr(field, "padding", None),
    )
    return None if frame.is_empty() else frame


__all__ = (
    "Frame",
    "FrameTitlePosition",
    "field_has_frame_chrome",
    "frame_from_field",
)
