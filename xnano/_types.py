"""xnano._types

---

Shared type vocabulary: geometry (``Area``, ``Size``, ``Coordinate``),
sizing (``Sizing``, ``SizingLike``), frame chrome (``Frame``,
``Padding``, ``Border``), keyboard/mouse aliases, and field-focus
helpers for editable ``Text`` input.
"""

from __future__ import annotations

import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeAlias,
    Union,
)

from xnano.color import ColorLike

if TYPE_CHECKING:
    from xnano.components.text import Text
    from xnano.events import FocusHookKind, KeyboardEventData
    from xnano.terminal.terminal import Terminal


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


SizingKind: TypeAlias = Literal[
    "cells",
    "percent",
    "ratio",
    "fraction",
    "fit",
]
"""The kind of sizing intent expressed by a ``Sizing``.

Values:
    ``"cells"``: A fixed number of terminal cells.
    ``"percent"``: A percentage (0-100) of the available axis length.
    ``"ratio"``: A ``numerator / denominator`` fraction of the axis length.
    ``"fraction"``: A relative fill weight distributed across leftover space.
    ``"fit"``: The measured intrinsic size of the content.
"""


@dataclasses.dataclass(frozen=True, slots=True)
class Sizing:
    """A single-axis sizing intent.

    ``Sizing`` is the unified currency of layout: the same value can describe a
    grid field's width, a terminal's height, or a renderable's extent. Use the
    constructor helpers (``cells``, ``percent``, ``ratio``, ``fraction``,
    ``fit``) or ``parse`` to build one.

    Attributes:
        kind: The kind of sizing intent.
        value: The primary magnitude — cell count, percentage, ratio
            numerator, or fill weight depending on ``kind``.
        denominator: The ratio denominator (only meaningful for ``"ratio"``).
        minimum: An optional lower clamp in cells applied after resolution.
        maximum: An optional upper clamp in cells applied after resolution.
    """

    kind: SizingKind
    """The kind of sizing intent."""
    value: int = 0
    """The primary magnitude for this sizing intent."""
    denominator: int = 1
    """The ratio denominator (only meaningful for ``"ratio"``)."""
    minimum: int | None = None
    """An optional lower clamp in cells applied after resolution."""
    maximum: int | None = None
    """An optional upper clamp in cells applied after resolution."""

    @classmethod
    def cells(cls, count: int) -> Sizing:
        """Return a fixed-length sizing of ``count`` terminal cells.

        Args:
            count: The number of cells to occupy.

        Returns:
            A ``"cells"`` ``Sizing``.
        """
        return cls(kind="cells", value=max(0, int(count)))

    @classmethod
    def percent(cls, percentage: float) -> Sizing:
        """Return a percentage sizing of the available axis length.

        Args:
            percentage: The percentage of the axis to occupy. Values in the
                ``0..=1`` range are treated as fractions (``0.5`` → 50%);
                larger values are treated as literal percentages.

        Returns:
            A ``"percent"`` ``Sizing``.
        """
        pct = percentage * 100 if 0 <= percentage <= 1 else percentage
        return cls(kind="percent", value=max(0, min(100, int(round(pct)))))

    @classmethod
    def ratio(cls, numerator: int, denominator: int) -> Sizing:
        """Return a ratio sizing of ``numerator / denominator`` of the axis.

        Args:
            numerator: The ratio numerator.
            denominator: The ratio denominator.

        Returns:
            A ``"ratio"`` ``Sizing``.
        """
        return cls(
            kind="ratio",
            value=max(0, int(numerator)),
            denominator=max(1, int(denominator)),
        )

    @classmethod
    def fraction(cls, weight: int = 1) -> Sizing:
        """Return a relative fill-weight sizing.

        Args:
            weight: The fill weight. Higher weights claim proportionally more
                of the leftover space.

        Returns:
            A ``"fraction"`` ``Sizing``.
        """
        return cls(kind="fraction", value=max(0, int(weight)))

    @classmethod
    def fit(
        cls,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> Sizing:
        """Return a content-measured sizing.

        Args:
            minimum: An optional lower clamp in cells.
            maximum: An optional upper clamp in cells.

        Returns:
            A ``"fit"`` ``Sizing``.
        """
        return cls(kind="fit", minimum=minimum, maximum=maximum)

    def with_bounds(
        self,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> Sizing:
        """Return a copy of this sizing with clamps applied.

        Args:
            minimum: An optional lower clamp in cells.
            maximum: An optional upper clamp in cells.

        Returns:
            A new ``Sizing`` carrying the given bounds.
        """
        return dataclasses.replace(self, minimum=minimum, maximum=maximum)

    @property
    def is_fill(self) -> bool:
        """Whether this sizing grows to fill the available axis."""
        return self.kind == "fraction"

    @property
    def is_fit(self) -> bool:
        """Whether this sizing measures its content."""
        return self.kind == "fit"

    def resolve(self, available: int, content: int | None = None) -> int:
        """Resolve this sizing to a concrete cell length.

        Args:
            available: The available axis length to resolve against.
            content: The measured content length, used by ``"fit"`` sizings.

        Returns:
            The resolved length in cells, after applying any clamps.
        """
        if self.kind == "cells":
            length = self.value
        elif self.kind == "percent":
            length = available * self.value // 100
        elif self.kind == "ratio":
            length = available * self.value // self.denominator
        elif self.kind == "fit":
            length = content if content is not None else 0
        else:  # fraction — a lone fill claims all available space
            length = available
        if self.minimum is not None:
            length = max(length, self.minimum)
        if self.maximum is not None:
            length = min(length, self.maximum)
        return max(0, length)

    @classmethod
    def parse(cls, value: SizingLike | None) -> Sizing | None:
        """Normalize any accepted sizing form into a ``Sizing``.

        Accepted forms:
            - ``None`` → ``None``
            - ``Sizing`` → itself
            - ``int`` → ``cells``
            - ``float`` in ``0..=1`` → ``percent``, otherwise ``cells``
            - ``"50%"`` → ``percent``
            - ``"2fr"`` → ``fraction``
            - ``"fit"`` / ``"auto"`` / ``"content"`` → ``fit``
            - ``"fill"`` / ``"grow"`` / Tailwind flex class → ``fraction``
            - a decimal string → ``cells``

        Args:
            value: The value to normalize.

        Returns:
            A ``Sizing`` instance, or ``None`` when ``value`` is ``None``.

        Raises:
            ValueError: If a string value is not a recognized sizing form.
            TypeError: If ``value`` is an unsupported type.
        """
        if value is None:
            return None
        if isinstance(value, Sizing):
            return value
        if isinstance(value, bool):
            raise TypeError("bool is not a valid sizing value")
        if isinstance(value, int):
            return cls.cells(value)
        if isinstance(value, float):
            if 0 <= value <= 1:
                return cls.percent(value)
            return cls.cells(int(value))
        if isinstance(value, str):
            return cls._parse_string(value)
        raise TypeError(
            f"sizing must be an int, float, str, or Sizing, "
            f"got {type(value).__name__}"
        )

    @classmethod
    def _parse_string(cls, text: str) -> Sizing:
        token = text.strip().lower()
        if token in ("fit", "auto", "content"):
            return cls.fit()
        if token in ("fill", "grow"):
            return cls.fraction(1)
        if token in _FLEX_CLASS_WEIGHTS:
            return cls.fraction(_FLEX_CLASS_WEIGHTS[token])
        if token.endswith("%"):
            # A ``%`` string is always a literal percentage — ``"1%"`` means
            # one percent, unlike the bare-float form where ``0..=1`` reads
            # as a fraction (``0.5`` → 50%).
            pct = float(token[:-1])
            return cls(kind="percent", value=max(0, min(100, int(round(pct)))))
        if token.endswith("fr"):
            weight = token[:-2].strip() or "1"
            return cls.fraction(int(weight))
        if "/" in token:
            numerator, _, denominator = token.partition("/")
            return cls.ratio(int(numerator), int(denominator))
        try:
            return cls.cells(int(token))
        except ValueError as error:
            raise ValueError(f"invalid sizing string: {text!r}") from error


SizingLike: TypeAlias = Union[int, float, str, Sizing]
"""Any value accepted where a ``Sizing`` is expected.

See ``Sizing.parse`` for the full list of accepted forms.
"""


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
"""Convenience alias providing a list of commonly used keybindings that
can be set within the ``on_keyboard`` event hook.
"""


KeyboardModifier: TypeAlias = Literal["ctrl", "shift", "alt"]
"""A modifier key that can be held along with the primary action
key for classifying keyboard events.
"""


KeyboardKey: TypeAlias = Literal[
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "enter",
    "esc",
    "backspace",
    "tab",
    "backtab",
    "up",
    "down",
    "left",
    "right",
    "home",
    "end",
    "pageup",
    "pagedown",
    "insert",
    "delete",
    "space",
    "null",
    "capslock",
    "scrolllock",
    "numlock",
    "printscreen",
    "pause",
    "menu",
    "keypadbegin",
    "media",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
    "other",
]
"""Convenience alias representing the standard character keys that
can be set and/or recieved by ``on_keyboard`` event hooks.
"""


KeyboardBinding: TypeAlias = Union[KnownKeyboardBinding, KeyboardKey, str]
"""``"ctrl+e"`` | ``"enter"`` | ``"shift+f1"`` | ``"3"`` | ``"h"`` | ``"alt+home"``

A keyboard event binding representing a primary trigger key that is
optionally followed by one or more modifier keys held or released at the
same time.

A keyboard binding can be provided in the following formats:

## Without Modifiers

When defining a keyboard binding without modifiers, the primary trigger
key can be provided as one of the following types:

- 'a' - 'z'   : Letter keys.
- '0' - '9'   : Number keys.
- 'enter'     : Enter/Return key.
- 'esc'       : Escape key.
- 'backspace' : Backspace key.
- 'tab', 'backtab' : Tab and BackTab keys.
- 'up', 'down', 'left', 'right' : Arrow keys.
- 'home', 'end', 'pageup', 'pagedown', 'insert', 'delete', 'space', 'null'
- 'capslock', 'scrolllock', 'numlock', 'printscreen', 'pause', 'menu'
- 'keypadbegin', 'media', 'f1' - 'f12', 'other'

## With Modifiers

Bindings including modifier keys are expressed as a string using '+' notation.
Valid modifier keys are 'ctrl', 'shift', and 'alt'. Modifiers must precede
the base key, separated by '+'.

For example:
- 'ctrl+a'        : Control and 'a' key.
- 'shift+tab'     : Shift and Tab key.
- 'alt+enter'     : Alt and Enter key.
- 'ctrl+shift+z'  : Control, Shift, and 'z' key.
"""


MouseButton: TypeAlias = Literal["left", "right", "middle", "unknown"]
"""The name of a mouse button that can be pressed or released to trigger
a mouse event.
"""


@dataclasses.dataclass(frozen=True, slots=True)
class FieldFocus:
    """Identity of the currently focused layout field.

    Attributes:
        grid: The grid instance that owns the field.
        field_name: Layout field name on ``grid``.
    """

    grid: Any
    field_name: str


def is_focusable_component(value: Any) -> bool:
    """Return whether ``value`` is a focusable, keyboard-driven component.

    Any component that declares ``focusable`` truthy and implements
    ``handle_keyboard`` participates in field focus — ``Text(input=True)``
    and ``Select`` alike.
    """
    from xnano.components.abstract import AbstractComponent

    return (
        isinstance(value, AbstractComponent)
        and bool(getattr(value, "focusable", False))
        and callable(getattr(value, "handle_keyboard", None))
    )


def get_focusable_component(grid: Any, field_name: str) -> Any | None:
    """Return the focusable component on ``grid.field_name``, if any."""
    value = getattr(grid, field_name, None)
    if is_focusable_component(value):
        return value
    return None


def collect_focusable_fields(terminal: Terminal[Any]) -> list[FieldFocus]:
    """Collect focusable input fields in paint/declaration order.

    Walks ``terminal._attached_frame_grids`` (outer-most first, then nested
    grids as they appear during the last frame) and, for each grid, its
    ``_grid_fields`` declaration order.
    """
    result: list[FieldFocus] = []
    seen: set[tuple[int, str]] = set()
    for grid in terminal._attached_frame_grids:
        fields = getattr(type(grid), "_grid_fields", None) or getattr(
            grid, "_grid_fields", {}
        )
        for field_name in fields:
            value = getattr(grid, field_name, None)
            if is_focusable_component(value):
                key = (id(grid), field_name)
                if key not in seen:
                    seen.add(key)
                    result.append(FieldFocus(grid=grid, field_name=field_name))
            elif hasattr(value, "_grid_fields"):
                # Nested grids are also listed in _attached_frame_grids when
                # painted; no need to recurse here.
                pass
    return result


def sync_input_focus_flags(terminal: Terminal[Any]) -> None:
    """Set ``Text._input_focused`` on every attached input to match focus."""
    current = getattr(terminal, "_field_focus", None)
    for target in collect_focusable_fields(terminal):
        text = get_focusable_component(target.grid, target.field_name)
        if text is None or not hasattr(text, "_input_focused"):
            continue
        text._input_focused = (
            current is not None
            and current.grid is target.grid
            and current.field_name == target.field_name
        )


def focused_component(terminal: Terminal[Any]) -> Any | None:
    """Return the focusable component for the current field focus, if any."""
    current = getattr(terminal, "_field_focus", None)
    if current is None:
        return None
    return get_focusable_component(current.grid, current.field_name)


def apply_text_keyboard(text: Text, keyboard: KeyboardEventData) -> bool:
    """Apply a keyboard event to an editable ``Text``.

    Consumes printable characters, backspace/delete, and left/right/home/end.
    Leaves tab, enter, escape, and arrows up/down for application hooks.

    Args:
        text: The input ``Text`` to mutate.
        keyboard: The keyboard sub-event.

    Returns:
        ``True`` when the event was handled (and should not fire other
        character-level keyboard hooks).
    """
    if not text.input or not isinstance(text.content, str):
        return False
    kind = keyboard.kind
    if kind is not None and kind not in ("press", "repeat"):
        return False

    content = text.content
    position = text.cursor if text.cursor is not None else len(content)
    position = max(0, min(position, len(content)))

    if keyboard.matches("backspace"):
        if position > 0:
            text.content = content[: position - 1] + content[position:]
            text.cursor = position - 1
        return True
    if keyboard.matches("delete"):
        if position < len(content):
            text.content = content[:position] + content[position + 1 :]
            text.cursor = position
        return True
    if keyboard.matches("left"):
        text.cursor = max(0, position - 1)
        return True
    if keyboard.matches("right"):
        text.cursor = min(len(content), position + 1)
        return True
    if keyboard.matches("home"):
        text.cursor = 0
        return True
    if keyboard.matches("end"):
        text.cursor = len(content)
        return True
    # Navigation / submit keys stay available to @on_keyboard hooks.
    if keyboard.matches(
        "tab",
        "backtab",
        "enter",
        "esc",
        "up",
        "down",
        "pageup",
        "pagedown",
    ):
        return False

    character = keyboard.character
    if (
        character is not None
        and len(character) == 1
        and character.isprintable()
        and character not in ("\n", "\r", "\t")
    ):
        text.content = content[:position] + character + content[position:]
        text.cursor = position + 1
        return True
    return False


def _mark_text_focused(text: Any | None, focused: bool) -> None:
    if text is not None and hasattr(text, "_input_focused"):
        text._input_focused = focused


def set_field_focus(
    terminal: Terminal[Any],
    grid: Any,
    field_name: str,
    *,
    fire_hooks: bool = True,
) -> bool:
    """Focus ``grid.field_name`` when it holds an editable ``Text``.

    Args:
        terminal: The live terminal.
        grid: Owner grid.
        field_name: Layout field name.
        fire_hooks: Whether to fire field ``@on_focus`` handlers.

    Returns:
        ``True`` when focus was set (or already there).
    """
    text = get_focusable_component(grid, field_name)
    if text is None:
        return False
    previous = getattr(terminal, "_field_focus", None)
    target = FieldFocus(grid=grid, field_name=field_name)
    # Compared by identity (not ``==``) so focus tracking never depends on a
    # BaseGrid subclass overriding equality.
    if (
        previous is not None
        and previous.grid is grid
        and previous.field_name == field_name
    ):
        _mark_text_focused(text, True)
        sync_input_focus_flags(terminal)
        return True

    if previous is not None:
        prev_text = get_focusable_component(previous.grid, previous.field_name)
        _mark_text_focused(prev_text, False)
        if fire_hooks:
            _fire_field_focus_hooks(terminal, previous, kind="lost")

    terminal._field_focus = target
    _mark_text_focused(text, True)
    sync_input_focus_flags(terminal)
    terminal._field_focus_announced = True

    if fire_hooks:
        _fire_field_focus_hooks(terminal, target, kind="gained")
    return True


def clear_field_focus(
    terminal: Terminal[Any],
    *,
    fire_hooks: bool = True,
) -> None:
    """Clear field focus on ``terminal``."""
    previous = getattr(terminal, "_field_focus", None)
    if previous is None:
        return
    prev_text = get_focusable_component(previous.grid, previous.field_name)
    _mark_text_focused(prev_text, False)
    if fire_hooks:
        _fire_field_focus_hooks(terminal, previous, kind="lost")
    terminal._field_focus = None
    terminal._field_focus_announced = False
    sync_input_focus_flags(terminal)


def cycle_field_focus(
    terminal: Terminal[Any],
    *,
    reverse: bool = False,
) -> bool:
    """Move field focus to the next (or previous) input field.

    Returns:
        ``True`` when focus moved or was established.
    """
    targets = collect_focusable_fields(terminal)
    if not targets:
        return False
    current = getattr(terminal, "_field_focus", None)
    if current is None:
        pick = targets[-1] if reverse else targets[0]
        return set_field_focus(terminal, pick.grid, pick.field_name)

    index = 0
    # Identity comparison, as in ``set_field_focus`` above.
    for i, target in enumerate(targets):
        if (
            target.grid is current.grid
            and target.field_name == current.field_name
        ):
            index = i
            break
    if reverse:
        index = (index - 1) % len(targets)
    else:
        index = (index + 1) % len(targets)
    pick = targets[index]
    return set_field_focus(terminal, pick.grid, pick.field_name)


def ensure_default_field_focus(terminal: Terminal[Any]) -> None:
    """Focus the first input field when nothing is focused yet."""
    current = getattr(terminal, "_field_focus", None)
    if current is not None:
        sync_input_focus_flags(terminal)
        # Seeded pre-paint focus still needs a one-shot ``gained`` announce.
        if not getattr(terminal, "_field_focus_announced", False):
            terminal._field_focus_announced = True
            _fire_field_focus_hooks(terminal, current, kind="gained")
        return
    targets = collect_focusable_fields(terminal)
    if targets:
        set_field_focus(
            terminal,
            targets[0].grid,
            targets[0].field_name,
            fire_hooks=True,
        )


def place_cursor_for_focus(terminal: Terminal[Any]) -> None:
    """Move the hardware cursor into the focused input field, if any."""
    current = getattr(terminal, "_field_focus", None)
    if current is None:
        return
    text = get_focusable_component(current.grid, current.field_name)
    if text is None:
        return
    if getattr(text, "owns_cursor", False):
        # The component paints its own caret (multi-line editor, list
        # highlight); keep the hardware cursor out of the way.
        try:
            terminal.cursor.visible = False
        except Exception:
            pass
        return
    if not isinstance(text.content, str):
        return
    slots = getattr(current.grid, "_grid_last_slot_areas", None) or {}
    area = slots.get(current.field_name)
    if area is None:
        return
    position = text.cursor if text.cursor is not None else len(text.content)
    position = max(0, min(position, len(text.content)))
    # Clamp caret into the painted slot width.
    column = min(position, max(0, area.width - 1))
    try:
        terminal.cursor.visible = True
        terminal.cursor.move_to(area.x + column, area.y)
    except Exception:
        pass


def _fire_field_focus_hooks(
    terminal: Terminal[Any],
    target: FieldFocus,
    *,
    kind: "FocusHookKind",
) -> None:
    from xnano._dispatch import invoke_hook, resolve_hook_grid
    from xnano.context import Context
    from xnano.events import FocusEventData

    focus_data = FocusEventData(
        kind="field_gained" if kind == "gained" else "field_lost",
        field=target.field_name,
    )
    ctx = Context(event=None, terminal=terminal, state=terminal.state)
    terminal._last_field_focus_event = focus_data

    for entry in terminal._hooks.on_focus_hooks:
        field_filter = entry["field"]
        kind_filter = entry["kind"]
        handler = entry["handler"]

        if field_filter is None:
            # Terminal-only focus hooks ignore field focus transitions.
            continue
        if field_filter != target.field_name:
            continue
        if kind_filter is not None and kind_filter != kind:
            continue

        grid = target.grid
        bound = getattr(handler, "__self__", None)
        if bound is None:
            name = getattr(handler, "__name__", None)
            if name and hasattr(grid, name):
                handler = getattr(grid, name)
            else:
                resolved = resolve_hook_grid(terminal, handler)
                if resolved is not None:
                    grid = resolved
        invoke_hook(handler, grid, ctx)


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
    "Sizing",
    "SizingKind",
    "SizingLike",
    "Frame",
    "FrameTitlePosition",
    "field_has_frame_chrome",
    "frame_from_field",
    "KnownKeyboardBinding",
    "KeyboardModifier",
    "KeyboardKey",
    "KeyboardBinding",
    "MouseButton",
    "FieldFocus",
    "is_focusable_component",
    "get_focusable_component",
    "collect_focusable_fields",
    "sync_input_focus_flags",
    "focused_component",
    "apply_text_keyboard",
    "set_field_focus",
    "clear_field_focus",
    "cycle_field_focus",
    "ensure_default_field_focus",
    "place_cursor_for_focus",
)
