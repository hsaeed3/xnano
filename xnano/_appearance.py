"""
xnano._appearance

How a text placement or canvas looks: colors, text modifiers, border, title, padding and margin.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Final, TypeAlias, TypedDict, cast

import xnano_core as _core
from xnano._values import ColorValue

__all__ = [
    'APPEARANCE_NAMES',
    'INHERIT',
    'Appearance',
    'BorderSideSpecification',
    'Spacing',
    'SpacingDictionary',
    'resolve_spacing',
]

APPEARANCE_NAMES = frozenset(
    {
        'foreground',
        'background',
        'is_bold',
        'is_dim',
        'is_italic',
        'is_underlined',
        'is_blinking',
        'is_reversed',
        'is_hidden',
        'is_crossed_out',
        'style',
        'title',
        'border',
        'border_style',
        'padding',
        'margin',
    }
)
"""The names ``write`` and ``new`` read as appearance instead of buffer attributes."""


class SpacingDictionary(TypedDict, total=False):
    """
    Space around text, edge by edge.

    Attributes:
        top: The space above, in cells.
        right: The space to the right.
        bottom: The space below.
        left: The space to the left.
        vertical: The space above and below, unless ``top`` or ``bottom`` is given.
        horizontal: The space left and right, unless ``left`` or ``right`` is given.
    """

    top: int | float | str
    right: int | float | str
    bottom: int | float | str
    left: int | float | str
    vertical: int | float | str
    horizontal: int | float | str


Spacing: TypeAlias = int | float | str | SpacingDictionary
"""
Space around text: one value for every edge or a [`SpacingDictionary`][xnano.types.SpacingDictionary].

A whole number is a count of cells. A float (``0.1``) or a percentage string (``'10%'``) is
a share of the text's width for the left and right edges and of its height for the top and
bottom edges, read when the spacing is applied.
"""


def _refuse_negative(value: float, name: str, *, shown: object = None) -> None:
    """Refuse a space that is less than nothing, or that is not a number of cells."""
    if value < 0 or (isinstance(value, float) and not math.isfinite(value)):
        keyword = name.split('[')[0]
        raise ValueError(
            f'{name} must be zero or more and finite, but got '
            f'{value if shown is None else shown!r}. '
            f'Pass {keyword}=0 for no space.'
        )


MOST_CELLS: Final = 65535


def _within_cells(cells: int, name: str, shown: object) -> int:
    """Return ``cells`` when a buffer can hold that much space."""
    if cells > MOST_CELLS:
        keyword = name.split('[')[0]
        raise ValueError(
            f'{name} must be at most {MOST_CELLS} cells, but got {shown!r}. Pass a smaller '
            f'space, such as {keyword}=2.'
        )
    return cells


def _scaled_cells(available: int, factor: float) -> int:
    """Return ``available * factor`` in cells, or more than a buffer holds if it overflows."""
    product = available * factor
    if not math.isfinite(product) or product > MOST_CELLS:
        return MOST_CELLS + 1
    return round(product)


def _cells(value: object, available: int, name: str) -> int:
    keyword = name.split('[')[0]
    if isinstance(value, bool):
        raise TypeError(
            f'{name} must be a whole number of cells, a float or a percentage string, but '
            f'got {value!r}. Pass {keyword}=1, {keyword}=0.1 or {keyword}="10%".'
        )
    if isinstance(value, (int, float)):
        _refuse_negative(value, name)
        if isinstance(value, int):
            return _within_cells(value, name, value)
        return _within_cells(_scaled_cells(available, value), name, value)
    if isinstance(value, str) and value.strip().endswith('%'):
        try:
            share = float(value.strip()[:-1]) / 100.0
        except ValueError:
            share = None
        if share is not None:
            _refuse_negative(share, name, shown=value)
            return _within_cells(_scaled_cells(available, share), name, value)
    raise TypeError(
        f'{name} must be a whole number of cells, a float or a percentage string, but got '
        f'{value!r}. Pass {keyword}=1, {keyword}=0.1 or {keyword}="10%".'
    )


def resolve_spacing(
    value: Spacing | None, *, width: int, height: int, name: str = 'spacing'
) -> tuple[int, int, int, int]:
    """
    Turn a spacing into whole cells for ``(left, right, top, bottom)``.

    Args:
        value: The spacing, or ``None`` for none.
        width: The width that a share on the left and right edges is a share of.
        height: The height that a share on the top and bottom edges is a share of.
        name: The parameter name, for error messages.

    Raises:
        TypeError: A value is not a number of cells, a float, a percentage string or a
            dictionary of those.
        ValueError: A dictionary has an edge name that does not exist.
    """
    if value is None:
        return 0, 0, 0, 0
    if not isinstance(value, dict):
        return (
            _cells(value, width, name),
            _cells(value, width, name),
            _cells(value, height, name),
            _cells(value, height, name),
        )
    unknown = sorted(
        set(value) - {'top', 'right', 'bottom', 'left', 'vertical', 'horizontal'}
    )
    if unknown:
        raise ValueError(
            f'{name} has no edge called {unknown[0]!r}. Use top, right, bottom, left, '
            f'vertical or horizontal.'
        )

    def edge(first: str, second: str, available: int) -> int:
        if first in value:
            return _cells(value[first], available, f'{name}[{first!r}]')  # type: ignore[literal-required]
        if second in value:
            return _cells(value[second], available, f'{name}[{second!r}]')  # type: ignore[literal-required]
        return 0

    return (
        edge('left', 'horizontal', width),
        edge('right', 'horizontal', width),
        edge('top', 'vertical', height),
        edge('bottom', 'vertical', height),
    )


def check_border_kind(border: object) -> None:
    """
    Refuse a border that is not a kind, a ``bool`` or ``None``.

    Raises:
        ValueError: The border is not one of ``'plain'``, ``'rounded'``, ``'double'`` or
            ``'thick'``.
    """
    if border is None or isinstance(border, bool):
        return
    if border not in ('plain', 'rounded', 'double', 'thick'):
        raise ValueError(
            f'{border!r} is not a border kind. Use "plain", "rounded", "double" or '
            f'"thick", True for "plain", or False to remove the border.'
        )


INHERIT: Final = object()
"""Marks a border side that takes the kind of the whole border."""


@dataclasses.dataclass(slots=True)
class BorderSideSpecification:
    """
    What one side of a border does differently from the others.

    Attributes:
        kind: The kind of line on this side, ``None`` when the side is not drawn, or
            ``INHERIT`` for the kind of the whole border.
        color: The color of this side, or ``None`` for the border's own color.
    """

    kind: object = INHERIT
    color: ColorValue | None = None


def _snapshot(buffer: _core.Buffer) -> _core.Buffer:
    """Copy what a buffer shows into a buffer of plain cells."""
    return _core.Buffer.from_cell_grid(buffer.to_cell_grid())


_BOOLEAN_FIELDS: Final = frozenset(
    {
        'is_bold',
        'is_dim',
        'is_italic',
        'is_underlined',
        'is_blinking',
        'is_reversed',
        'is_hidden',
        'is_crossed_out',
    }
)
_STYLE_FIELDS: Final = frozenset({'style', 'border_style'})


@dataclasses.dataclass(slots=True)
class Appearance:
    """
    The look of a piece of text, kept so that it can be changed after the text is shown.

    Attributes:
        text: The text, line by line.
        style: A ready-made style that the color and modifier fields are applied over.
        foreground: The text color.
        background: The color behind the text.
        is_bold: Whether the text is bold.
        is_dim: Whether the text is dimmed.
        is_italic: Whether the text is italic.
        is_underlined: Whether the text is underlined.
        is_blinking: Whether the text blinks.
        is_reversed: Whether foreground and background are swapped.
        is_hidden: Whether the text is hidden.
        is_crossed_out: Whether the text is struck through.
        title: A title on the border.
        border: The kind of border, a [`BorderKind`][xnano.types.BorderKind] such as ``'plain'``.
        border_style: The style of the border.
        padding: Space between the border and the text.
        margin: Space outside the border.
    """

    text: str = ''
    style: _core.Style | None = None
    foreground: ColorValue | None = None
    background: ColorValue | None = None
    is_bold: bool = False
    is_dim: bool = False
    is_italic: bool = False
    is_underlined: bool = False
    is_blinking: bool = False
    is_reversed: bool = False
    is_hidden: bool = False
    is_crossed_out: bool = False
    title: str | None = None
    border: _core.BorderKind | None = None
    border_style: _core.Style | None = None
    padding: Spacing | None = None
    margin: Spacing | None = None
    sides: dict[str, BorderSideSpecification] = dataclasses.field(default_factory=dict)
    revision: int = 0

    def __setattr__(self, name: str, value: object) -> None:
        """Set a field, refusing a value of the wrong type and leaving the field as it was."""
        if name in _BOOLEAN_FIELDS:
            if not isinstance(value, bool):
                raise TypeError(
                    f'{name} must be True or False, but got {value!r}. Pass {name}=True '
                    f'to turn it on, or {name}=False to turn it off.'
                )
        elif name in _STYLE_FIELDS:
            if value is not None and not isinstance(
                value, (_core.Style, _core.DynamicStyle)
            ):
                raise TypeError(
                    f'{name} must be a Style or None, but got {value!r}. Pass a style such '
                    f'as {name}=Style(foreground="red"), or None for none.'
                )
        elif name in ('foreground', 'background'):
            if value is not None and not isinstance(value, _core.Color):
                try:
                    _core.Color(value)  # type: ignore[arg-type]
                except (TypeError, ValueError) as error:
                    raise type(error)(
                        f'{name} must be a color, but got {value!r}: '
                        f'{str(error).rstrip(".")}.'
                    ) from None
        elif name == 'title':
            if value is not None and not isinstance(value, str):
                raise TypeError(
                    f'title must be text or None, but got {value!r}. Pass a string such '
                    f'as title="Menu", or None for no title.'
                )
            if value is not None and ('\n' in value or '\r' in value):
                raise ValueError(
                    f'title must be a single line, but got {value!r}. Pass a title without '
                    f'line breaks, such as title="Menu".'
                )
        elif name == 'text' and not isinstance(value, str):
            raise TypeError(
                f'text must be a string, but got {value!r}. Pass text such as "hello", '
                f'and join lines with newlines.'
            )
        object.__setattr__(self, name, value)

    @property
    def base_border_kind(self) -> _core.BorderKind | None:
        """The kind of border the sides share unless they say otherwise."""
        if self.border is not None:
            return self.border
        if self.title is not None or self.border_style is not None:
            return 'plain'
        return None

    def drawn_sides(self) -> dict[str, tuple[_core.BorderKind, ColorValue | None]]:
        """The sides that are drawn, by name, with their kind and own color."""
        drawn: dict[str, tuple[_core.BorderKind, ColorValue | None]] = {}
        base = self.base_border_kind
        for name in ('top', 'right', 'bottom', 'left'):
            specification = self.sides.get(name)
            kind = (
                base
                if specification is None or specification.kind is INHERIT
                else specification.kind
            )
            if kind is not None:
                drawn[name] = (
                    cast('_core.BorderKind', kind),
                    None if specification is None else specification.color,
                )
        return drawn

    def text_buffer(self) -> _core.Buffer:
        """The text with its colors and modifiers, without border, padding or margin."""
        buffer = _core.Buffer.with_text(self.text)
        style = self.text_style()
        if style is not None:
            buffer.update(_core.ApplyStyle(style))
        return buffer

    @property
    def has_style(self) -> bool:
        """Whether any color or text modifier is set."""
        return self.style is not None or any(
            (
                self.foreground is not None,
                self.background is not None,
                self.is_bold,
                self.is_dim,
                self.is_italic,
                self.is_underlined,
                self.is_blinking,
                self.is_reversed,
                self.is_hidden,
                self.is_crossed_out,
            )
        )

    @property
    def has_frame(self) -> bool:
        """Whether a border, title or padding surrounds the text."""
        return any(
            (
                self.title is not None,
                self.border is not None,
                self.border_style is not None,
                self.padding not in (None, 0, {}),
            )
        )

    def text_style(self) -> _core.Style | None:
        """The style of the text: the ready-made style with the color and modifiers over it."""
        if not self.has_style:
            return self.style
        own = _core.Style(
            self.foreground,
            self.background,
            bold=self.is_bold,
            dim=self.is_dim,
            italic=self.is_italic,
            underline=self.is_underlined,
            blink=self.is_blinking,
            reverse=self.is_reversed,
            hidden=self.is_hidden,
            crossed_out=self.is_crossed_out,
        )
        return own if self.style is None else self.style.patch(own)

    def render(self) -> _core.Buffer:
        """Build the buffer that shows the text with its border, padding and margin."""
        lines = self.text.split('\n')
        text_width = max((len(line) for line in lines), default=0)
        text_height = len(lines)
        style = self.text_style()
        if not self.has_frame:
            inner = _core.Buffer.with_text(self.text)
            if style is not None:
                inner.update(_core.ApplyStyle(style))
        else:
            left, right, top, bottom = resolve_spacing(
                self.padding, width=text_width, height=text_height, name='padding'
            )
            has_border = (
                self.title is not None
                or self.border is not None
                or self.border_style is not None
            )
            edge = 2 if has_border else 0
            width = text_width + left + right + edge
            if self.title is not None:
                width = max(width, len(self.title) + 2)
            block = _core.Block(
                self.title,
                borders='all' if has_border else 'none',
                border_type=self.border or 'plain',
                border_style=self.border_style,
                padding=(left, right, top, bottom),
            )
            inner = _core.Paragraph(
                self.text,
                style=style,
                block=block,
                width=width,
                height=text_height + top + bottom + edge,
            )
        if self.margin is None:
            return inner
        left, right, top, bottom = resolve_spacing(
            self.margin, width=inner.width, height=inner.height, name='margin'
        )
        if not (left or right or top or bottom):
            return inner
        outer = _core.Buffer(
            width=inner.width + left + right, height=inner.height + top + bottom
        )
        outer.update(_core.Paste(_snapshot(inner), x=left, y=top))
        return outer

    def snapshot(self) -> _core.Buffer:
        """The text as a buffer of plain cells, which can be copied into another buffer."""
        return _snapshot(self.render())
