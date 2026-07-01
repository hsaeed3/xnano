"""xnano.layout"""

from __future__ import annotations

import dataclasses
from typing import Any, Literal, Sequence, TypeAlias, Union, cast

from xnano import _core


Direction: TypeAlias = Literal["horizontal", "vertical"]
"""The axis along which a layout splits its area."""


Alignment: TypeAlias = Literal["left", "center", "right"]
"""Horizontal text or widget alignment within a region."""


Flex: TypeAlias = Literal[
    "legacy", "start", "end", "center", "space_between", "space_around"
]
"""Flex distribution mode for dividing remaining space among constraints."""


_DIRECTION: dict[Direction, _core.Direction] = {
    "horizontal": _core.Direction.Horizontal,
    "vertical": _core.Direction.Vertical,
}


_ALIGNMENT: dict[Alignment, _core.Alignment] = {
    "left": _core.Alignment.Left,
    "center": _core.Alignment.Center,
    "right": _core.Alignment.Right,
}


_FLEX: dict[Flex, _core.Flex] = {
    "legacy": _core.Flex.Legacy,
    "start": _core.Flex.Start,
    "end": _core.Flex.End,
    "center": _core.Flex.Center,
    "space_between": _core.Flex.SpaceBetween,
    "space_around": _core.Flex.SpaceAround,
}


def _core_direction(value: Direction) -> _core.Direction:
    return _DIRECTION[value]


def _core_alignment(value: Alignment) -> _core.Alignment:
    return _ALIGNMENT[value]


def _core_flex(value: Flex) -> _core.Flex:
    return _FLEX[value]


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Margin:
    """Spacing around a rectangular area."""

    horizontal: int = 0
    vertical: int = 0

    def _to_core(self) -> _core.Margin:
        return _core.Margin(self.horizontal, self.vertical)

    get_core_margin = _to_core

    def __repr__(self) -> str:
        return (
            f"Margin(horizontal={self.horizontal}, vertical={self.vertical})"
        )


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Offset:
    """A signed x/y displacement."""

    x: int = 0
    y: int = 0

    def _to_core(self) -> _core.Offset:
        return _core.Offset(self.x, self.y)

    get_core_offset = _to_core

    def __repr__(self) -> str:
        return f"Offset(x={self.x}, y={self.y})"


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Size:
    """Terminal dimensions (width/height)."""

    width: int
    height: int

    def _to_core(self) -> _core.Size:
        return _core.Size(self.width, self.height)

    get_core_size = _to_core

    def __repr__(self) -> str:
        return f"Size(width={self.width}, height={self.height})"


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Position:
    """An x/y coordinate on the terminal grid."""

    x: int
    y: int

    @classmethod
    def origin(cls) -> Position:
        return cls(x=0, y=0)

    def _to_core(self) -> _core.Position:
        return _core.Position(self.x, self.y)

    get_core_position = _to_core

    def __repr__(self) -> str:
        return f"Position(x={self.x}, y={self.y})"


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Rectangle:
    """An axis-aligned rectangle."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    @classmethod
    def zero(cls) -> Rectangle:
        return cls(x=0, y=0, width=0, height=0)

    @classmethod
    def _from_core(cls, rect: _core.Rect) -> Rectangle:
        return cls(x=rect.x, y=rect.y, width=rect.width, height=rect.height)

    def _to_core(self) -> _core.Rect:
        return _core.Rect(self.x, self.y, self.width, self.height)

    get_core_rect = _to_core

    def area(self) -> int:
        return self._to_core().area()

    def is_empty(self) -> bool:
        return self._to_core().is_empty()

    def inner(self, margin: Margin) -> Rectangle:
        return Rectangle._from_core(self._to_core().inner(margin._to_core()))

    def left(self) -> int:
        return self._to_core().left()

    def right(self) -> int:
        return self._to_core().right()

    def top(self) -> int:
        return self._to_core().top()

    def bottom(self) -> int:
        return self._to_core().bottom()

    def offset(self, offset: Offset) -> Rectangle:
        return Rectangle._from_core(self._to_core().offset(offset._to_core()))

    def union(self, other: Rectangle) -> Rectangle:
        return Rectangle._from_core(self._to_core().union(other._to_core()))

    def intersection(self, other: Rectangle) -> Rectangle:
        return Rectangle._from_core(
            self._to_core().intersection(other._to_core())
        )

    def intersects(self, other: Rectangle) -> bool:
        return self._to_core().intersects(other._to_core())

    def contains(self, x: int, y: int) -> bool:
        if not (0 <= x <= 65535 and 0 <= y <= 65535):
            return False
        return self._to_core().contains(x, y)

    def __repr__(self) -> str:
        return f"Rectangle(x={self.x}, y={self.y}, width={self.width}, height={self.height})"


Rect = Rectangle


class Constraint:
    """A layout size constraint."""

    __slots__ = ("_inner",)
    _inner: _core.Constraint

    def __init__(self) -> None:
        raise TypeError(
            "Constraint instances are created via factory methods: "
            "Constraint.length(), Constraint.percentage(), etc."
        )

    @classmethod
    def _from_core(cls, inner: _core.Constraint) -> Constraint:
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Constraint:
        return self._inner

    get_core_constraint = _to_core

    @classmethod
    def min(cls, value: int) -> Constraint:
        return cls._from_core(_core.Constraint.min(value))

    @classmethod
    def max(cls, value: int) -> Constraint:
        return cls._from_core(_core.Constraint.max(value))

    @classmethod
    def length(cls, value: int) -> Constraint:
        return cls._from_core(_core.Constraint.length(value))

    @classmethod
    def percentage(cls, value: int) -> Constraint:
        return cls._from_core(_core.Constraint.percentage(value))

    @classmethod
    def ratio(cls, numerator: int, denominator: int) -> Constraint:
        return cls._from_core(_core.Constraint.ratio(numerator, denominator))

    @classmethod
    def fill(cls, value: int) -> Constraint:
        return cls._from_core(_core.Constraint.fill(value))

    @classmethod
    def from_lengths(cls, values: list[int]) -> list[Constraint]:
        return [
            cls._from_core(c) for c in _core.Constraint.from_lengths(values)
        ]

    @classmethod
    def from_percentages(cls, values: list[int]) -> list[Constraint]:
        return [
            cls._from_core(c)
            for c in _core.Constraint.from_percentages(values)
        ]

    @classmethod
    def from_ratios(cls, values: list[tuple[int, int]]) -> list[Constraint]:
        return [
            cls._from_core(c) for c in _core.Constraint.from_ratios(values)
        ]

    @classmethod
    def from_mins(cls, values: list[int]) -> list[Constraint]:
        return [cls._from_core(c) for c in _core.Constraint.from_mins(values)]

    @classmethod
    def from_maxes(cls, values: list[int]) -> list[Constraint]:
        return [cls._from_core(c) for c in _core.Constraint.from_maxes(values)]

    @classmethod
    def from_fills(cls, values: list[int]) -> list[Constraint]:
        return [cls._from_core(c) for c in _core.Constraint.from_fills(values)]

    def apply(self, length: int) -> int:
        return self._inner.apply(length)

    def __repr__(self) -> str:
        return repr(self._inner)


RectangleLike: TypeAlias = Union[Rectangle, tuple[int, int, int, int]]
"""A Rectangle or a tuple of (x, y, width, height)."""

ConstraintLike: TypeAlias = Union[Constraint, int, float, str]
"""A Constraint object or a number/string representation constraint."""


def _resolve_rectangle(value: RectangleLike) -> Rectangle:
    if isinstance(value, Rectangle):
        return value
    if isinstance(value, tuple) and len(value) == 4:
        return Rectangle(x=value[0], y=value[1], width=value[2], height=value[3])
    raise TypeError(f"expected Rectangle or 4-tuple, got {type(value)!r}")


def _resolve_constraint(value: ConstraintLike) -> _core.Constraint:
    if isinstance(value, Constraint):
        return value._to_core()
    if isinstance(value, int):
        return _core.Constraint.length(value)
    if isinstance(value, float):
        return _core.Constraint.percentage(int(value * 100))
    if isinstance(value, str):
        val = value.strip().lower()
        if val.endswith("%"):
            return _core.Constraint.percentage(int(val[:-1]))
        if val in ("fill", "*"):
            return _core.Constraint.fill(1)
        if val.endswith("*"):
            factor = val[:-1].strip()
            return _core.Constraint.fill(int(factor) if factor else 1)
        if val.isdigit():
            return _core.Constraint.length(int(val))
    raise TypeError(f"Invalid constraint: {value!r}")


class Layout:
    """A constraint-based layout engine that splits a Rectangle."""

    __slots__ = ("_inner", "_keys")
    _inner: _core.Layout
    _keys: list[str] | None

    def __init__(
        self,
        direction: Direction = "vertical",
        constraints: Sequence[ConstraintLike] | dict[str, ConstraintLike] | None = None,
        *,
        margin: Margin | int | None = None,
        horizontal_margin: int | None = None,
        vertical_margin: int | None = None,
        flex: Flex | None = None,
        spacing: int | None = None,
    ) -> None:
        """Create a new Layout configuration.

        Args:
            direction: ``"horizontal"`` or ``"vertical"``.
            constraints: The list of constraints.
            margin: Uniform Margin (or integer cell value) on all sides.
            horizontal_margin: Margin on left/right sides.
            vertical_margin: Margin on top/bottom sides.
            flex: Flex distribution mode.
            spacing: Space gap between split regions.
        """
        inner = _core.Layout.default()

        inner = inner.direction(_core_direction(direction))
        keys: list[str] | None = None
        if constraints is not None:
            if isinstance(constraints, dict):
                constraints_dict = cast(dict[str, ConstraintLike], constraints)
                keys = list(constraints_dict.keys())
                inner = inner.constraints(
                    [_resolve_constraint(c) for c in constraints_dict.values()]
                )
            else:
                inner = inner.constraints(
                    [_resolve_constraint(c) for c in constraints]
                )

        if margin is not None:
            if isinstance(margin, int):
                inner = inner.margin(margin)
            else:
                inner = inner.margin_xy(margin._to_core())
        if horizontal_margin is not None:
            inner = inner.horizontal_margin(horizontal_margin)
        if vertical_margin is not None:
            inner = inner.vertical_margin(vertical_margin)
        if flex is not None:
            inner = inner.flex(_core_flex(flex))
        if spacing is not None:
            inner = inner.spacing(spacing)

        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_keys", keys)

    @classmethod
    def _from_core(cls, inner: _core.Layout) -> Layout:
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        object.__setattr__(obj, "_keys", None)
        return obj

    def _to_core(self) -> _core.Layout:
        return self._inner

    get_core_layout = _to_core

    def split(self, area: RectangleLike) -> Any:
        """Split a rectangle into sub-regions."""
        resolved_area = _resolve_rectangle(area)
        rects = [
            Rectangle._from_core(r)
            for r in self._inner.split(resolved_area._to_core())
        ]
        if self._keys is not None:
            return dict(zip(self._keys, rects))
        return rects

    def map(
        self,
        area: RectangleLike,
        widgets: dict[str, Any] | Sequence[Any],
        states: dict[str, Any] | Sequence[Any] | None = None,
    ) -> list[tuple[Any, Rectangle] | tuple[Any, Rectangle, Any]]:
        """Map widgets (and optionally states) to the layout's split areas."""
        areas = self.split(area)

        result: list[tuple[Any, Rectangle] | tuple[Any, Rectangle, Any]] = []
        if isinstance(areas, dict):
            if not isinstance(widgets, dict):
                raise TypeError(
                    "When layout uses named constraints, widgets must be a dict "
                    "mapping keys to widgets"
                )

            areas_dict = cast(dict[str, Rectangle], areas)
            widgets_dict = cast(dict[str, Any], widgets)
            states_dict = cast(dict[str, Any], states) if isinstance(states, dict) else {}

            for key, widget in widgets_dict.items():
                if key not in areas_dict:
                    raise KeyError(f"No split area named {key!r} in layout")
                a = areas_dict[key]
                s = states_dict.get(key)

                if s is not None:
                    result.append((widget, a, s))
                else:
                    result.append((widget, a))
        else:
            if isinstance(widgets, dict):
                raise TypeError(
                    "When layout uses list constraints, widgets must be a list/sequence"
                )
            areas_list = cast(list[Rectangle], areas)
            widgets_seq = cast(Sequence[Any], widgets)
            states_seq = (
                cast(Sequence[Any], states)
                if isinstance(states, Sequence) and not isinstance(states, (str, bytes))
                else None
            )

            if len(widgets_seq) > len(areas_list):
                raise ValueError(
                    f"More widgets ({len(widgets_seq)}) than split areas ({len(areas_list)})"
                )

            for i, widget in enumerate(widgets_seq):
                a = areas_list[i]
                s = None
                if states_seq is not None and i < len(states_seq):
                    s = states_seq[i]
                if s is not None:
                    result.append((widget, a, s))
                else:
                    result.append((widget, a))
        return result

    def __repr__(self) -> str:
        return repr(self._inner)


__all__ = (
    "Alignment",
    "Constraint",
    "ConstraintLike",
    "Direction",
    "Flex",
    "Layout",
    "Margin",
    "Offset",
    "Position",
    "Rect",
    "Rectangle",
    "RectangleLike",
    "Size",
)
