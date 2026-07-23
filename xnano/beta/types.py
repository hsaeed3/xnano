"""xnano.beta.types

---

Type aliases and values for layout, input, styling, charts, and components.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, Union, cast

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike

Alignment: TypeAlias = Literal["left", "right", "center"]
"""Horizontal (x-axis) alignment of a grid field or area.

Values:
    ``"left"``: Aligned to the left.
    ``"right"``: Aligned to the right.
    ``"center"``: Centered.
"""


ScrollLike: TypeAlias = "bool | Literal['vertical', 'horizontal', 'auto']"
"""``Field(scroll=...)`` value. ``True`` scrolls along the field's
``direction``; ``"vertical"``/``"horizontal"`` force an axis; ``"auto"``
scrolls only when content overflows the slot."""


Axis: TypeAlias = Literal["x", "y"]
"""The axis a grid field or area lays out along.

Values:
    ``"x"``: Horizontal layout.
    ``"y"``: Vertical layout.
"""


Border: TypeAlias = Literal[
    "plain",
    "rounded",
    "double",
    "thick",
    "quadrant_inside",
    "quadrant_outside",
]
"""Border style drawn around a rectangular area's outer edges.

Values:
    ``"plain"``: A plain border. (``---------``)
    ``"rounded"``: Rounded corners. (``╭───────╮``)
    ``"double"``: Double lines. (``╔═══════╗``)
    ``"thick"``: Thick/dark lines. (``┏━━━━━━━┓``)
    ``"quadrant_inside"``: Quadrant-style inner division. (``▛▀▀▀▀▀▜``)
    ``"quadrant_outside"``: Quadrant-style outer corners. (``▗▄▄▄▄▄▖``)
"""


Coordinate: TypeAlias = tuple[int, int]
"""A single ``(x, y)`` cell coordinate within the terminal grid."""


Corner: TypeAlias = Literal[
    "top-left", "top-right", "bottom-left", "bottom-right"
]
"""A single corner of a rectangular grid area.

Values:
    ``"top-left"``, ``"top-right"``, ``"bottom-left"``, ``"bottom-right"``.
"""


Direction: TypeAlias = Literal["horizontal", "vertical"]
"""The direction content within a grid field or area lays out along.

Values:
    ``"horizontal"``: Laid out horizontally.
    ``"vertical"``: Laid out vertically.
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
"""A modifier applied to the content of a grid field or area.

Values:
    ``"bold"``: Bold text.
    ``"dim"``: Reduced intensity.
    ``"italic"``: Italic text.
    ``"underline"``: Underlined text.
    ``"slow_blink"``: Slow blink.
    ``"rapid_blink"``: Rapid blink.
    ``"reversed"``: Swapped foreground/background colors.
"""


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


ScrollbarOrientationLike: TypeAlias = Literal[
    "vertical_right",
    "vertical_left",
    "horizontal_bottom",
    "horizontal_top",
]
"""Placement of a scrollbar widget.

Values:
    ``"vertical_right"``, ``"vertical_left"``: Vertical, right/left edge.
    ``"horizontal_bottom"``, ``"horizontal_top"``: Horizontal, bottom/top
    edge.
"""


CanvasMarkerLike: TypeAlias = Literal[
    "dot",
    "block",
    "bar",
    "braille",
    "half_block",
]
"""Marker glyph set used when drawing on a Canvas widget.

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
    ``"line"``: Connected line.
    ``"scatter"``: Unconnected points.
    ``"bar"``: Vertical bars.
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
"""A single side of a rectangular grid area.

Values:
    ``"top"``, ``"bottom"``, ``"left"``, ``"right"``.
"""


SizePercentage: TypeAlias = tuple[float, float] | float
"""Percentage of the parent area's width/height a field should occupy —
a ``(width, height)`` tuple, or one float applied to both axes.
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
"""Relative fill weight for proportional layout, or a Tailwind flex
utility. Numeric values set the fill weight directly; Tailwind classes
map to proportional grow weights — see ``resolve_flex_weight``.
"""


_FLEX_CLASS_WEIGHTS: dict[str, int] = {
    "flex-1": 1,
    "flex-auto": 1,
    "flex-initial": 0,
    "flex-none": 0,
    "grow": 1,
    "grow-0": 0,
    "shrink": 1,
    "shrink-0": 0,
}


def resolve_flex_weight(flex: Flex | None) -> int | None:
    """Return the numeric layout weight represented by ``flex``."""
    if flex is None:
        return None
    if isinstance(flex, int):
        return max(0, flex)
    return _FLEX_CLASS_WEIGHTS.get(flex)


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

    def fit_content(self, content: Size, align: Alignment = "left") -> "Area":
        """Fit a measured size inside this area."""
        width = min(self.width, max(content.width, 1))
        height = min(self.height, max(content.height, 1))
        if align == "right":
            x = self.x + self.width - width
        elif align == "center":
            x = self.x + (self.width - width) // 2
        else:
            x = self.x
        return Area(
            x=x,
            y=self.y + (self.height - height) // 2,
            width=width,
            height=height,
        )


SizingKind: TypeAlias = Literal[
    "cells",
    "percent",
    "ratio",
    "fraction",
    "fit",
]
"""The kind of sizing intent expressed by a ``Sizing``.

Values:
    ``"cells"``: A fixed cell count.
    ``"percent"``: A percentage of the available axis length.
    ``"ratio"``: A ``numerator / denominator`` fraction of the axis
    length.
    ``"fraction"``: A relative fill weight across leftover space.
``"fit"``: The measured intrinsic size of the content.
"""


@dataclasses.dataclass(frozen=True, slots=True)
class Sizing:
    """Single-axis layout size.

    Attributes:
        kind: Sizing strategy.
        value: Cell count, percentage, numerator, or fill weight.
        denominator: Denominator for ratio sizing.
        minimum: Optional minimum cell count.
        maximum: Optional maximum cell count.

    Examples:
        ```python
        sidebar = Sizing.parse("25%")
        content = Sizing.parse("1fr")
        ```
    """

    kind: SizingKind
    """Sizing strategy."""
    value: int = 0
    """Cell count, percentage, numerator, or fill weight."""
    denominator: int = 1
    """Denominator for ratio sizing."""
    minimum: int | None = None
    """Optional minimum cell count."""
    maximum: int | None = None
    """Optional maximum cell count."""

    @classmethod
    def cells(cls, count: int) -> "Sizing":
        """Create a fixed cell size."""
        return cls(kind="cells", value=max(0, int(count)))

    @classmethod
    def percent(cls, percentage: float) -> "Sizing":
        """Create a percentage of the available length."""
        value = percentage * 100 if 0 <= percentage <= 1 else percentage
        return cls(kind="percent", value=max(0, min(100, round(value))))

    @classmethod
    def ratio(cls, numerator: int, denominator: int) -> "Sizing":
        """Create a ratio of the available length."""
        return cls(
            kind="ratio",
            value=max(0, int(numerator)),
            denominator=max(1, int(denominator)),
        )

    @classmethod
    def fraction(cls, weight: int = 1) -> "Sizing":
        """Create a proportional fill size."""
        return cls(kind="fraction", value=max(0, int(weight)))

    @classmethod
    def fit(
        cls,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> "Sizing":
        """Create a content-measured size."""
        return cls(kind="fit", minimum=minimum, maximum=maximum)

    def with_bounds(
        self,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> "Sizing":
        """Return this size with new cell bounds."""
        return dataclasses.replace(self, minimum=minimum, maximum=maximum)

    @property
    def is_fill(self) -> bool:
        """Whether this size fills remaining space."""
        return self.kind == "fraction"

    @property
    def is_fit(self) -> bool:
        """Whether this size follows measured content."""
        return self.kind == "fit"

    def resolve(self, available: int, content: int | None = None) -> int:
        """Resolve this size to cells."""
        if self.kind == "cells":
            length = self.value
        elif self.kind == "percent":
            length = available * self.value // 100
        elif self.kind == "ratio":
            length = available * self.value // self.denominator
        elif self.kind == "fit":
            length = content or 0
        else:
            length = available
        if self.minimum is not None:
            length = max(length, self.minimum)
        if self.maximum is not None:
            length = min(length, self.maximum)
        return max(0, length)

    @classmethod
    def parse(cls, value: "SizingLike | None") -> "Sizing | None":
        """Normalize a supported sizing value."""
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, bool):
            raise TypeError("bool is not a valid sizing value")
        if isinstance(value, int):
            return cls.cells(value)
        if isinstance(value, float):
            return (
                cls.percent(value)
                if 0 <= value <= 1
                else cls.cells(round(value))
            )
        if not isinstance(value, str):
            raise TypeError(
                "sizing must be an int, float, str, or Sizing, "
                f"got {type(value).__name__}"
            )
        token = value.strip().lower()
        if token in ("fit", "auto", "content"):
            return cls.fit()
        if token in ("fill", "grow"):
            return cls.fraction()
        if token in _FLEX_CLASS_WEIGHTS:
            return cls.fraction(_FLEX_CLASS_WEIGHTS[token])
        if token.endswith("%"):
            percentage = float(token[:-1])
            return cls(
                kind="percent",
                value=max(0, min(100, round(percentage))),
            )
        if token.endswith("fr"):
            return cls.fraction(int(token[:-2].strip() or "1"))
        if "/" in token:
            numerator, denominator = token.split("/", 1)
            return cls.ratio(int(numerator), int(denominator))
        try:
            return cls.cells(int(token))
        except ValueError as error:
            raise ValueError(f"invalid sizing string: {value!r}") from error


SizingLike: TypeAlias = Union[int, float, str, Sizing]
"""Any value accepted where a ``Sizing`` is expected — see
``Sizing.parse`` for the full list of accepted forms.
"""


FrameTitlePosition: TypeAlias = Literal["top", "bottom"]
"""The side of a frame to display its title on.

Values:
    ``"top"``, ``"bottom"``.
"""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Frame:
    """Border, title, background, and padding around content.

    Attributes:
        background: Fill color.
        border: Border style.
        border_color: Border color.
        border_sides: Sides to draw.
        title: Border title.
        title_position: Title edge.
        padding: Inner padding.
    """

    background: "ColorLike | None" = None
    """Fill color."""
    border: Border | None = None
    """Border style."""
    border_color: "ColorLike | None" = None
    """Border color."""
    border_sides: list[Side] | None = None
    """Sides to draw."""
    title: str | None = None
    """Border title."""
    title_position: FrameTitlePosition | None = None
    """Title edge."""
    padding: PaddingLike | None = None
    """Inner padding."""

    def is_empty(self) -> bool:
        """Return whether this frame has no visible attributes."""
        return not any(
            (
                self.background,
                self.border,
                self.border_color,
                self.border_sides,
                self.title,
                self.title_position,
                self.padding,
            )
        )


def field_has_frame_chrome(field: object) -> bool:
    """Return whether a field defines structural frame styling."""
    return any(
        getattr(field, name, None) is not None
        for name in ("border", "title", "padding")
    )


def frame_from_field(field: object | None) -> Frame | None:
    """Build frame styling from a field definition."""
    if field is None:
        return None
    has_chrome = field_has_frame_chrome(field)
    sides = getattr(field, "border_sides", None)
    frame = Frame(
        background=getattr(field, "background", None) if has_chrome else None,
        border=getattr(field, "border", None),
        border_color=getattr(field, "border_color", None),
        border_sides=list(sides) if sides is not None else None,
        title=getattr(field, "title", None),
        title_position=getattr(field, "title_position", None),
        padding=getattr(field, "padding", None),
    )
    return None if frame.is_empty() else frame


KnownKeyboardBinding: TypeAlias = Literal[
    "ctrl+c",
    "ctrl+d",
    "ctrl+z",
    "ctrl+x",
    "ctrl+v",
    "ctrl+a",
    "ctrl+s",
    "ctrl+w",
    "ctrl+r",
    "ctrl+f",
    "ctrl+up",
    "ctrl+down",
    "ctrl+left",
    "ctrl+right",
    "shift+tab",
    "shift+up",
    "shift+down",
    "shift+left",
    "shift+right",
    "alt+enter",
    "alt+backspace",
    "alt+up",
    "alt+down",
    "alt+left",
    "alt+right",
]
"""Commonly used keybindings accepted by ``@on_keyboard``."""


KeyboardModifier: TypeAlias = Literal["ctrl", "shift", "alt"]
"""A modifier key held alongside the primary action key."""


KeyboardKey: TypeAlias = Literal[
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n",
    "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "enter", "esc", "backspace", "tab", "backtab",
    "up", "down", "left", "right",
    "home", "end", "pageup", "pagedown", "insert", "delete", "space",
    "null", "capslock", "scrolllock", "numlock", "printscreen", "pause",
    "menu", "keypadbegin", "media",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11",
    "f12", "other",
]  # fmt: skip
"""Standard character/named keys accepted by ``@on_keyboard``."""


KeyboardBinding: TypeAlias = Union[KnownKeyboardBinding, KeyboardKey, str]
"""A keyboard binding: a primary key optionally preceded by ``+``-joined
modifiers (``"ctrl+a"``, ``"shift+tab"``, ``"alt+enter"``,
``"ctrl+shift+z"``, ...).
"""


MouseButton: TypeAlias = Literal["left", "right", "middle", "unknown"]
"""The mouse button that triggered a mouse event."""


@dataclasses.dataclass(frozen=True, slots=True)
class FieldFocus:
    """Focused grid field.

    Attributes:
        grid: Grid containing the field.
        field_name: Field attribute name.
        group: Optional cross-grid focus group.
    """

    grid: Any
    """Grid containing the field."""
    field_name: str
    """Field attribute name."""
    group: str | None = None
    """Optional cross-grid focus group."""


@dataclasses.dataclass(slots=True)
class ScrollHandle:
    """Mutable scroll state for a field.

    Attributes:
        group: Field group controlling this scroll region.
        axis: Scroll axis.
        offset: Current cell offset.
        follow: Whether new content keeps the viewport at the end.
    """

    group: str
    """Field group controlling this scroll region."""
    axis: Axis
    """Scroll axis."""
    offset: int = 0
    """Current cell offset."""
    follow: bool = False
    """Whether new content keeps the viewport at the end."""

    def scroll(self, delta: int) -> int:
        """Move the offset by ``delta`` cells."""
        self.offset = max(0, self.offset + delta)
        if delta:
            self.follow = False
        return self.offset

    def scroll_to(self, offset: int) -> int:
        """Set the offset in cells."""
        self.offset = max(0, offset)
        self.follow = False
        return self.offset

    def scroll_to_end(self) -> None:
        """Follow the end of the content."""
        self.follow = True


def is_component(value: Any) -> bool:
    """Return whether a value follows the beta component contract."""
    return bool(getattr(type(value), "_xnano_component_base", False))


def uses_default_component_size(value: Any) -> bool:
    """Return whether a component uses the default layout size."""
    return is_component(value) and not bool(
        getattr(value, "fit_content", False)
    )


def is_focusable_component(value: Any) -> bool:
    """Return whether a beta component accepts field focus."""
    return is_component(value) and bool(getattr(value, "focusable", False))


__all__ = (
    "Alignment",
    "Area",
    "Axis",
    "Border",
    "CanvasMarkerLike",
    "CharacterModifier",
    "Coordinate",
    "Corner",
    "Direction",
    "FieldFocus",
    "Flex",
    "Frame",
    "FrameTitlePosition",
    "GraphTypeLike",
    "KeyboardBinding",
    "KeyboardKey",
    "KeyboardModifier",
    "KnownKeyboardBinding",
    "LegendPositionLike",
    "MouseButton",
    "Padding",
    "PaddingLike",
    "ScrollHandle",
    "ScrollLike",
    "ScrollbarOrientationLike",
    "Side",
    "Size",
    "SizePercentage",
    "Sizing",
    "SizingKind",
    "SizingLike",
    "field_has_frame_chrome",
    "frame_from_field",
    "is_component",
    "is_focusable_component",
    "resolve_flex_weight",
    "uses_default_component_size",
)
