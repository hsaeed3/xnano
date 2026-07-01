"""xnano.style"""

from __future__ import annotations

import dataclasses
from typing import Literal, Sequence, TypeAlias

from xnano import _core
from xnano._convert import (
    ColorLike,
    ModifierLike,
    _resolve_color,
    _resolve_modifier,
)
from xnano.color import Color


ModifierName: TypeAlias = Literal[
    "bold",
    "dim",
    "italic",
    "underlined",
    "slow_blink",
    "rapid_blink",
    "reversed",
    "hidden",
    "crossed_out",
]
"""Name of a text display modifier."""


BorderSide: TypeAlias = Literal["top", "right", "bottom", "left"]
"""A single side of a border."""


BorderName = BorderSide


BorderTypeName: TypeAlias = Literal[
    "plain",
    "rounded",
    "double",
    "thick",
    "quadrant_inside",
    "quadrant_outside",
]
"""The visual style of border line characters."""


TitlePositionName: TypeAlias = Literal["top", "bottom"]
"""Position of a block title."""


HighlightSpacingName: TypeAlias = Literal["always", "when_selected", "never"]
"""When to reserve space for the highlight symbol in list/table widgets."""


_MODIFIER: dict[ModifierName, _core.Modifier] = {
    "bold": _core.Modifier.BOLD,
    "dim": _core.Modifier.DIM,
    "italic": _core.Modifier.ITALIC,
    "underlined": _core.Modifier.UNDERLINED,
    "slow_blink": _core.Modifier.SLOW_BLINK,
    "rapid_blink": _core.Modifier.RAPID_BLINK,
    "reversed": _core.Modifier.REVERSED,
    "hidden": _core.Modifier.HIDDEN,
    "crossed_out": _core.Modifier.CROSSED_OUT,
}


_BORDER: dict[BorderSide, _core.Borders] = {
    "top": _core.Borders.TOP,
    "right": _core.Borders.RIGHT,
    "bottom": _core.Borders.BOTTOM,
    "left": _core.Borders.LEFT,
}


_BORDER_TYPE: dict[BorderTypeName, _core.BorderType] = {
    "plain": _core.BorderType.Plain,
    "rounded": _core.BorderType.Rounded,
    "double": _core.BorderType.Double,
    "thick": _core.BorderType.Thick,
    "quadrant_inside": _core.BorderType.QuadrantInside,
    "quadrant_outside": _core.BorderType.QuadrantOutside,
}


_TITLE_POSITION: dict[TitlePositionName, _core.TitlePosition] = {
    "top": _core.TitlePosition.Top,
    "bottom": _core.TitlePosition.Bottom,
}


_HIGHLIGHT_SPACING: dict[HighlightSpacingName, _core.HighlightSpacing] = {
    "always": _core.HighlightSpacing.Always,
    "when_selected": _core.HighlightSpacing.WhenSelected,
    "never": _core.HighlightSpacing.Never,
}


def _core_modifier(names: frozenset[ModifierName]) -> _core.Modifier:
    result = _core.Modifier.EMPTY
    for name in names:
        result = result | _MODIFIER[name]
    return result


def _core_borders(names: frozenset[BorderSide]) -> _core.Borders:
    if not names:
        return _core.Borders.NONE
    result = _core.Borders.NONE
    for name in names:
        result = result | _BORDER[name]
    return result


def _core_border_type(value: BorderTypeName) -> _core.BorderType:
    return _BORDER_TYPE[value]


def _core_title_position(value: TitlePositionName) -> _core.TitlePosition:
    return _TITLE_POSITION[value]


def _core_highlight_spacing(
    value: HighlightSpacingName,
) -> _core.HighlightSpacing:
    return _HIGHLIGHT_SPACING[value]


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Modifier:
    """Text display modifiers such as bold, italic, or underlined."""

    names: frozenset[ModifierName] = dataclasses.field(
        default_factory=frozenset
    )

    def __init__(self, *names: ModifierName) -> None:
        """Create a modifier from one or more modifier names."""
        object.__setattr__(self, "names", frozenset(names))

    @classmethod
    def _from_core(cls, core_mod: _core.Modifier) -> Modifier:
        """Construct from a native ``_core.Modifier``."""
        text = repr(core_mod).lower()
        if text in ("none", "empty"):
            return cls()
        active = []
        for name in _MODIFIER:
            if name.replace("_", "") in text.replace("_", ""):
                active.append(name)
        return cls(*active)

    from_native = _from_core

    @classmethod
    def empty(cls) -> Modifier:
        return cls()

    @classmethod
    def of(cls, *names: ModifierName) -> Modifier:
        return cls(*names)

    def _to_core(self) -> _core.Modifier:
        return _core_modifier(self.names)

    def __or__(self, other: Modifier) -> Modifier:
        result = object.__new__(Modifier)
        object.__setattr__(result, "names", self.names | other.names)
        return result

    def __repr__(self) -> str:
        if not self.names:
            return "Modifier()"
        ordered = sorted(self.names)
        return f"Modifier({', '.join(repr(n) for n in ordered)})"


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Borders:
    """A set of border sides for a block widget."""

    sides: frozenset[BorderSide] = dataclasses.field(default_factory=frozenset)

    def __init__(self, *sides: BorderSide) -> None:
        """Create borders from one or more side names."""
        object.__setattr__(self, "sides", frozenset(sides))

    @classmethod
    def none(cls) -> Borders:
        return cls()

    @classmethod
    def all(cls) -> Borders:
        result = object.__new__(cls)
        object.__setattr__(result, "sides", frozenset(_BORDER))
        return result

    @classmethod
    def of(cls, *sides: BorderSide) -> Borders:
        return cls(*sides)

    def _to_core(self) -> _core.Borders:
        return _core_borders(self.sides)

    @property
    def names(self) -> frozenset[BorderSide]:
        return self.sides

    def __or__(self, other: Borders) -> Borders:
        result = object.__new__(Borders)
        object.__setattr__(result, "sides", self.sides | other.sides)
        return result

    def __repr__(self) -> str:
        if not self.sides:
            return "Borders()"
        ordered = sorted(self.sides)
        return f"Borders({', '.join(repr(s) for s in ordered)})"


class Style:
    """A combined foreground color, background color, and text modifier style."""

    __slots__ = ("_inner",)
    _inner: _core.Style

    def __init__(
        self,
        *,
        foreground: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: ModifierLike | None = None,
    ) -> None:
        """Create a new Style.

        Args:
            foreground: Text color.
            background: Background color.
            modifiers: Text modifiers (e.g. "bold", ["bold", "italic"]).
        """
        inner = _core.Style.default()
        if foreground is not None:
            inner = inner.fg(_resolve_color(foreground))
        if background is not None:
            inner = inner.bg(_resolve_color(background))
        if modifiers is not None:
            inner = inner.add_modifier(_resolve_modifier(modifiers))
        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.Style) -> Style:
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Style:
        return self._inner

    @classmethod
    def default(cls) -> Style:
        return cls._from_core(_core.Style.default())

    @classmethod
    def reset(cls) -> Style:
        return cls._from_core(_core.Style.reset())

    @classmethod
    def from_parts(
        cls,
        *,
        fg: Color | None = None,
        bg: Color | None = None,
        modifiers: Modifier | None = None,
    ) -> Style:
        return cls(foreground=fg, background=bg, modifiers=modifiers)

    def patch(self, other: Style) -> Style:
        """Return a new Style overlaying another Style's properties."""
        return Style._from_core(self._inner.patch(other._to_core()))

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Style is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Style is immutable")


class Padding:
    """Inner padding for a Block widget."""

    __slots__ = ("_inner",)
    _inner: _core.Padding

    def __init__(
        self,
        left: int = 0,
        right: int = 0,
        top: int = 0,
        bottom: int = 0,
    ) -> None:
        object.__setattr__(
            self, "_inner", _core.Padding.new(left, right, top, bottom)
        )

    @classmethod
    def _from_core(cls, inner: _core.Padding) -> Padding:
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Padding:
        return self._inner

    @classmethod
    def zero(cls) -> Padding:
        return cls._from_core(_core.Padding.zero())

    @classmethod
    def uniform(cls, value: int) -> Padding:
        return cls._from_core(_core.Padding.uniform(value))

    @classmethod
    def horizontal(cls, value: int) -> Padding:
        return cls._from_core(_core.Padding.horizontal(value))

    @classmethod
    def vertical(cls, value: int) -> Padding:
        return cls._from_core(_core.Padding.vertical(value))

    @classmethod
    def symmetric(cls, horizontal: int, vertical: int) -> Padding:
        return cls._from_core(_core.Padding.symmetric(horizontal, vertical))

    @classmethod
    def new(cls, left: int, right: int, top: int, bottom: int) -> Padding:
        return cls(left, right, top, bottom)

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Padding is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Padding is immutable")


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Wrap:
    """Word-wrap settings for text."""

    trim: bool = False

    def _to_core(self) -> _core.Wrap:
        return _core.Wrap(self.trim)

    def __repr__(self) -> str:
        return f"Wrap(trim={self.trim})"


__all__ = (
    "BorderName",
    "BorderSide",
    "BorderTypeName",
    "Borders",
    "HighlightSpacingName",
    "Modifier",
    "ModifierName",
    "Padding",
    "Style",
    "TitlePositionName",
    "Wrap",
)
