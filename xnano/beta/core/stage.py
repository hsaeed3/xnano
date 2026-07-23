"""xnano.beta.core.stage

---

Expose field layout areas and targeted cell painting for the current frame.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Sequence

from xnano.beta.colors import ColorLike
from xnano.beta.types import Area, CharacterModifier


@dataclasses.dataclass(slots=True)
class Stage:
    """Store named layout areas and frame-local paint requests.

    Example:
        ``stage.paint_cell(2, 1, "!", color="yellow")``

    Attributes:
        areas: Areas keyed by field or effect name.
    """

    areas: dict[str, Area] = dataclasses.field(default_factory=dict)
    """Areas keyed by field or effect name."""

    _commands: list[dict[str, Any]] = dataclasses.field(
        default_factory=list,
        init=False,
        repr=False,
    )
    """Cell writes queued for the current frame."""

    def get_area(self, name: str) -> Area | None:
        """Return the area registered for a name.

        Args:
            name: Field or effect name.

        Returns:
            Its area, or ``None`` when it has not been laid out.
        """
        return self.areas.get(name)

    def paint_cell(
        self,
        x: int,
        y: int,
        value: str,
        *,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: Sequence[CharacterModifier] | None = None,
    ) -> None:
        """Queue one styled cell write for the current frame.

        Args:
            x: Cell column.
            y: Cell row.
            value: Character or grapheme to paint.
            color: Foreground color.
            background: Background color.
            modifiers: Character modifiers.
        """
        self._commands.append(
            {
                "x": x,
                "y": y,
                "value": value,
                "color": color,
                "background": background,
                "modifiers": tuple(modifiers or ()),
            },
        )


LayoutMap = dict[str, Area]

__all__ = ("LayoutMap", "Stage")
