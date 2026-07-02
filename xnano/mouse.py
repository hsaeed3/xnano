"""xnano.mouse"""

from __future__ import annotations

from typing import Literal, TypeAlias, cast

from xnano import _core


MouseButtonName: TypeAlias = Literal["left", "right", "middle", "unknown"]
"""The mouse button involved in a mouse event."""


MouseEventKind: TypeAlias = Literal[
    "down",
    "up",
    "drag",
    "moved",
    "scroll_up",
    "scroll_down",
    "scroll_left",
    "scroll_right",
]
"""The type of mouse event."""


class MouseEvent:
    """A mouse input event."""

    __slots__ = ("kind", "x", "y", "button")
    kind: MouseEventKind
    x: int
    y: int
    button: MouseButtonName

    def __init__(
        self,
        kind: MouseEventKind,
        x: int,
        y: int,
        button: MouseButtonName,
    ) -> None:
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "button", button)

    @classmethod
    def _from_core(cls, event: _core.MouseEvent) -> MouseEvent:
        """Construct from a native mouse event."""
        return cls(
            kind=cast(MouseEventKind, event.kind),
            x=event.x,
            y=event.y,
            button=cast(MouseButtonName, event.button),
        )

    def __repr__(self) -> str:
        return f"MouseEvent(kind={self.kind!r}, x={self.x}, y={self.y}, button={self.button!r})"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("MouseEvent is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("MouseEvent is immutable")


__all__ = (
    "MouseButtonName",
    "MouseEventKind",
    "MouseEvent",
)
