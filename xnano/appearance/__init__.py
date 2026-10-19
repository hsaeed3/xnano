"""
xnano.appearance

How a canvas, a placement or a region looks: its colors, border, padding and margin.

Every owner has the same four properties, ``color``, ``border``, ``padding`` and ``margin``.
Assigning to any of them changes the owner, and several assignments in a row are drawn once,
before the next frame.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar, Final, cast

import xnano_core as _core
from xnano._schema._appearance import (
    ColorName,
    ColorValue,
    Spacing,
    SpacingDictionary,
)
from xnano._schema._axes import Percentage
from xnano.appearance._look import (
    INHERIT,
    Appearance,
    BorderSideSpecification,
    resolve_spacing,
)
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from xnano.appearance._owners import _Looked

__all__ = [
    'BorderAppearance',
    'BorderSide',
    'ColorSlot',
    'Colors',
    'Edges',
    'MarginAppearance',
    'PaddingAppearance',
]

_BORDER_KINDS: Final = ('plain', 'rounded', 'double', 'thick')
_SIDE_NAMES: Final = ('top', 'right', 'bottom', 'left')


def _none_error(what: str) -> TypeError:
    if what == 'color':
        return TypeError(
            'A color cannot be None. To clear it, assign "reset" (the terminal\'s own '
            'color). If you wrote other.color.bg = canvas.color.bg.darken(0.1): darken() '
            'changes the color in place and returns nothing; to copy a darker color use '
            'other.color.bg = canvas.color.bg.value.darken(0.1).'
        )
    if what in ('padding', 'margin'):
        return TypeError(
            f'{what} cannot be None. Assign 0 to remove it, or a number of cells, a '
            f'percentage such as "10%" or a dictionary such as {{"vertical": 1}}.'
        )
    return TypeError(
        f'{what} cannot be None. Assign False to remove it, or a kind such as "rounded".'
    )


def _plain_color(value: object, name: str = 'color') -> ColorValue | None:
    """
    Turn what a color setter accepts into a value the look stores; ``None`` clears it.

    A value that is not a color raises here, at the assignment, naming ``name`` and the
    value, and leaves the look as it was.
    """
    if isinstance(value, ColorSlot):
        return value.value
    if value is None:
        raise _none_error('color')
    try:
        color = value if isinstance(value, _core.Color) else _core.Color(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise type(error)(
            f'Cannot set {name} to {value!r}: {str(error).rstrip(".")}. '
            f'{name[:1].upper()}{name[1:]} was not changed.'
        ) from None
    return None if color.is_reset else color


def _checked_spacing(value: object, field: str) -> Spacing:
    """Return a padding or margin value after checking that it can be resolved."""
    try:
        resolve_spacing(cast('Spacing', value), width=0, height=0, name=field)
    except (TypeError, ValueError) as error:
        raise type(error)(
            f'Cannot set {field} to {value!r}: {error} The {field} was not changed.'
        ) from None
    return cast('Spacing', value)


class ColorSlot:
    """
    One color of an owner: the text color, the background or the border color.

    A slot is live: changing it changes the owner. ``slot.value`` is the plain
    [`Color`][xnano_core.Color], a copy that changes nothing.

    Attributes:
        value: The plain color of the slot, or ``None`` when it has none.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            label = canvas.write('hi', background='#336699')
            label.color.bg.darken(0.2)
            darker = label.color.bg.value
            assert darker != xnano.Color('#336699')
            assert darker.darken(0.5) != label.color.bg.value
        ```
    """

    __slots__ = ('_name', '_owner')

    def __init__(self, owner: _Looked, name: str) -> None:
        """
        Make the slot of an owner. Get one from ``owner.color`` instead of calling this.

        Args:
            owner: The canvas, placement or region.
            name: ``'foreground'``, ``'background'`` or ``'border'``.
        """
        self._owner = owner
        self._name = name

    def _read(self) -> ColorValue | None:
        look = self._owner._appearance
        if look is None:
            return None
        if self._name == 'border':
            return None if look.border_style is None else look.border_style.foreground
        return look.foreground if self._name == 'foreground' else look.background

    def _write(self, value: ColorValue | None) -> None:
        look = self._owner._ensure_look()
        if self._name == 'border':
            current = look.border_style
            background = None if current is None else current.background
            if value is None and (background is None or background.is_reset):
                look.border_style = None
            else:
                look.border_style = _core.Style(foreground=value, background=background)
        elif self._name == 'foreground':
            look.foreground = value
        else:
            look.background = value
        self._owner._look_changed()

    @property
    def value(self) -> _core.Color | None:
        """The plain [`Color`][xnano_core.Color] of the slot, or ``None`` when it has none."""
        stored = self._read()
        if stored is None:
            return None
        color = stored if isinstance(stored, _core.Color) else _core.Color(stored)
        return None if color.is_reset else color

    def _require_value(self, verb: str) -> _core.Color:
        value = self.value
        if value is None:
            example = {
                'foreground': 'color.fg = "red"',
                'background': 'color.bg = "red"',
                'border': 'border.color = "red"',
            }[self._name]
            raise TerminalError(
                f'Cannot {verb} a color that is not set. Assign a color first, for '
                f'example {example}.'
            )
        return value

    def darken(self, amount: float) -> None:
        """
        Make the color darker, in place.

        This changes the owner and returns nothing. To get a darker copy, use
        ``slot.value.darken(amount)``. Assigning the result of this call to another slot
        raises a ``TypeError``, but this call has already darkened the owner by then.

        Args:
            amount: How much darker, from ``0.0`` (unchanged) to ``1.0`` (black).

        Raises:
            TerminalError: The slot has no color.
        """
        self._write(self._require_value('darken').darken(amount))

    def lighten(self, amount: float) -> None:
        """
        Make the color lighter, in place.

        Args:
            amount: How much lighter, from ``0.0`` (unchanged) to ``1.0`` (white).

        Raises:
            TerminalError: The slot has no color.
        """
        self._write(self._require_value('lighten').lighten(amount))

    def random(self, base: ColorName | ColorValue | None = None) -> _core.Color:
        """
        Set the slot to a random color, or to a random shade of ``base``, in place.

        This is ``slot = Color.random(base)``; see
        [`Color.random`][xnano_core.Color.random]. ``random.seed(...)`` repeats the colors.

        Args:
            base: The color to pick shades of, or ``None`` for any color.

        Returns:
            The [`Color`][xnano_core.Color] the slot was set to.

        Raises:
            ValueError: ``base`` is ``Color.reset``, or not a color.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                label = canvas.write('hi')
                chosen = label.color.fg.random('green')
                assert label.color.fg.value == chosen
                label.color.bg.random()
                assert label.color.bg.value is not None
            ```
        """
        color = _core.Color.random(base)
        self._write(color)
        return color

    def shade(self, function: Callable[[int, int], ColorValue | None]) -> None:
        """
        Color every cell of the owner from a function of its position, in one write.

        Args:
            function: Called with ``(x, y)`` in cells; return the color, or ``None`` to leave
                the cell alone. For half-block or braille resolution use
                ``owner.region.half_blocks.shade`` or ``owner.region.braille.shade``.

        Raises:
            TerminalError: The slot is ``border.color``, which is one color for the whole
                border and cannot be shaded.

        Examples:
            ```python
            import xnano

            with xnano.new(width=4, height=2) as canvas:
                canvas.color.bg.shade(lambda x, y: (x * 40, y * 40, 0))
                assert canvas.region[3, 1].background.to_rgb() == (120, 40, 0)
            ```
        """
        if self._name == 'border':
            raise TerminalError(
                'The border has one color, so border.color cannot be shaded cell by cell. '
                'Assign a color to border.color, or shade the content with color.fg.shade '
                'or color.bg.shade.'
            )
        from xnano.region import Region

        owner = self._owner
        region = owner if isinstance(owner, Region) else owner.region
        if self._name == 'foreground':
            region._shade_foreground(function)
        else:
            region.shade(function)

    def __repr__(self) -> str:
        return f'ColorSlot({self._name}={self.value!r})'


def _unknown_color_slot(name: str) -> AttributeError:
    """The error for ``owner.color.<name>`` when ``name`` is neither ``fg`` nor ``bg``."""
    slot = 'bg' if name in ('background', 'back') else 'fg'
    return AttributeError(
        f'color has no {name!r}. Its two colors are color.fg, the text, and color.bg, what is '
        f'behind it: write color.{slot} = ... instead.'
    )


class Colors:
    """
    The two colors of an owner: ``fg`` is the text, ``bg`` is what is behind it.

    Assigning accepts a color name, a ``(red, green, blue)`` tuple, a
    [`Color`][xnano_core.Color] or another [`ColorSlot`][xnano.appearance.ColorSlot];
    ``'reset'`` clears the color. A value that is not a color raises at the assignment and
    leaves the colors unchanged.

    Attributes:
        fg: The color of the text.
        bg: The color behind the text.
    """

    __slots__ = ('_owner',)

    def __init__(self, owner: _Looked) -> None:
        """
        Make the colors of an owner. Get them from ``owner.color`` instead of calling this.

        Args:
            owner: The canvas, placement or region.
        """
        self._owner = owner

    def __getattr__(self, name: str) -> object:
        raise _unknown_color_slot(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name not in ('_owner', 'fg', 'bg'):
            raise _unknown_color_slot(name)
        object.__setattr__(self, name, value)

    @property
    def fg(self) -> ColorSlot:
        """The color of the text."""
        return ColorSlot(self._owner, 'foreground')

    @fg.setter
    def fg(self, value: ColorName | ColorValue | ColorSlot) -> None:
        ColorSlot(self._owner, 'foreground')._write(_plain_color(value, 'color.fg'))

    @property
    def bg(self) -> ColorSlot:
        """The color behind the text."""
        return ColorSlot(self._owner, 'background')

    @bg.setter
    def bg(self, value: ColorName | ColorValue | ColorSlot) -> None:
        ColorSlot(self._owner, 'background')._write(_plain_color(value, 'color.bg'))

    def shade(self, function: Callable[[int, int], ColorValue | None]) -> None:
        """
        Color the background of every cell from a function of its position, in one write.

        Args:
            function: Called with ``(x, y)`` in cells; return the color, or ``None`` to leave
                the cell alone. For half-block or braille resolution use
                ``owner.region.half_blocks.shade`` or ``owner.region.braille.shade``.
        """
        self.bg.shade(function)

    def __repr__(self) -> str:
        return f'Colors(fg={self.fg.value!r}, bg={self.bg.value!r})'


class BorderSide:
    """
    One side of a border: ``top``, ``right``, ``bottom`` or ``left``.

    Attributes:
        kind: The kind of line on this side, or ``None`` when the side is not drawn.
        color: The color of this side, or ``None`` when it uses the border's own color.
    """

    __slots__ = ('_name', '_owner')

    def __init__(self, owner: _Looked, name: str) -> None:
        """
        Make a side. Get one from ``owner.border.top`` and its siblings instead.

        Args:
            owner: The canvas, placement or region.
            name: ``'top'``, ``'right'``, ``'bottom'`` or ``'left'``.
        """
        self._owner = owner
        self._name = name

    @property
    def kind(self) -> _core.BorderKind | None:
        """The kind of line on this side, or ``None`` when the side is not drawn."""
        look = self._owner._appearance
        if look is None:
            return None
        drawn = look.drawn_sides().get(self._name)
        return None if drawn is None else drawn[0]

    @kind.setter
    def kind(self, value: _core.BorderKind | bool | BorderSide) -> None:
        look = self._owner._ensure_look()
        if isinstance(value, BorderSide):
            value = value.kind if value.kind is not None else False
        if value is None:
            raise _none_error('A border side')
        if value is True:
            value = look.base_border_kind or 'plain'
        previous = look.sides.get(self._name)
        color = None if previous is None else previous.color
        if value is False:
            look.sides[self._name] = BorderSideSpecification(None, color)
        else:
            if value not in _BORDER_KINDS:
                raise ValueError(
                    f'{value!r} is not a border kind. Use "plain", "rounded", "double" '
                    f'or "thick", True for "plain", or False to leave the side out.'
                )
            look.sides[self._name] = BorderSideSpecification(value, color)
        self._normalize(look)
        self._owner._look_changed()

    def random(self) -> _core.BorderKind:
        """
        Draw this side with a random kind of line and return the kind.

        The kind is one of ``'plain'``, ``'rounded'``, ``'double'`` and ``'thick'``; the side
        is always drawn, and the border's other sides stay as they are. The change is drawn
        at once. ``random.seed(...)`` repeats the kinds.

        Returns:
            The [`BorderKind`][xnano.types.BorderKind] the side was set to.

        Examples:
            ```python
            import random

            import xnano

            with xnano.new(width=12, height=5) as canvas:
                card = canvas.write('hi', border='plain')
                random.seed(2)
                chosen = card.border.top.random()
                assert card.border.top.kind == chosen
            ```
        """
        kind = cast('_core.BorderKind', random.choice(_BORDER_KINDS))
        self.kind = kind
        return kind

    @property
    def color(self) -> _core.Color | None:
        """The color of this side, or ``None`` when it uses the border's own color."""
        look = self._owner._appearance
        specification = None if look is None else look.sides.get(self._name)
        if specification is None or specification.color is None:
            return None
        value = specification.color
        return value if isinstance(value, _core.Color) else _core.Color(value)

    @color.setter
    def color(self, value: ColorName | ColorValue | None) -> None:
        color = (
            None if value is None else _plain_color(value, f'border.{self._name}.color')
        )
        look = self._owner._ensure_look()
        previous = look.sides.get(self._name)
        kind = INHERIT if previous is None else previous.kind
        look.sides[self._name] = BorderSideSpecification(kind, color)
        self._normalize(look)
        self._owner._look_changed()

    def _normalize(self, look: Appearance) -> None:
        """Forget an override that says what the border already says."""
        specification = look.sides.get(self._name)
        if specification is None or specification.color is not None:
            return
        if specification.kind is INHERIT or (
            specification.kind is not None and specification.kind == look.base_border_kind
        ):
            del look.sides[self._name]

    def __bool__(self) -> bool:
        return self.kind is not None

    def __repr__(self) -> str:
        return f'BorderSide({self._name}={self.kind!r}, color={self.color!r})'


class BorderAppearance:
    """
    The border of an owner.

    Attributes:
        kind: ``'plain'``, ``'rounded'``, ``'double'`` or ``'thick'``; ``None`` for no border.
        top: The top side, a [`BorderSide`][xnano.appearance.BorderSide].
        right: The right side.
        bottom: The bottom side.
        left: The left side.
        color: The border color, a [`ColorSlot`][xnano.appearance.ColorSlot]. A side may have
            its own.
        title: The text written on the top edge, or ``None``.
    """

    __slots__ = ('_owner',)

    def __init__(self, owner: _Looked) -> None:
        """
        Make the border of an owner. Get it from ``owner.border`` instead of calling this.

        Args:
            owner: The canvas, placement or region.
        """
        self._owner = owner

    def _assign_all(self, value: object) -> None:
        look = self._owner._ensure_look()
        if value is None:
            raise _none_error('border')
        if isinstance(value, BorderAppearance):
            value = value.kind if value.kind is not None else False
        if value is True:
            value = 'plain'
        if value is False:
            look.border = None
            look.border_style = None
            look.title = None
        elif value in _BORDER_KINDS:
            look.border = value  # type: ignore[assignment]
        else:
            raise ValueError(
                f'{value!r} is not a border kind. Use "plain", "rounded", "double" or '
                f'"thick", True for "plain", or False to remove the border.'
            )
        look.sides.clear()
        self._owner._look_changed()

    @property
    def kind(self) -> _core.BorderKind | None:
        """The kind of border on every side that does not say otherwise."""
        look = self._owner._appearance
        return None if look is None else look.base_border_kind

    @kind.setter
    def kind(self, value: _core.BorderKind | bool) -> None:
        self._assign_all(value)

    def random(self) -> _core.BorderKind:
        """
        Draw the border on every side with a random kind of line and return the kind.

        The kind is one of ``'plain'``, ``'rounded'``, ``'double'`` and ``'thick'``. It
        replaces the kind of every side, like assigning to ``kind``, and is drawn at once.
        ``random.seed(...)`` repeats the kinds.

        Returns:
            The [`BorderKind`][xnano.types.BorderKind] the border was set to.

        Examples:
            ```python
            import random

            import xnano

            with xnano.new(width=12, height=5) as canvas:
                card = canvas.write('hi')
                random.seed(1)
                chosen = card.border.random()
                assert card.border.kind == chosen
            ```
        """
        kind = cast('_core.BorderKind', random.choice(_BORDER_KINDS))
        self._assign_all(kind)
        return kind

    def _side(self, name: str) -> BorderSide:
        return BorderSide(self._owner, name)

    @property
    def top(self) -> BorderSide:
        """The top side."""
        return self._side('top')

    @top.setter
    def top(self, value: _core.BorderKind | bool | BorderSide) -> None:
        self._side('top').kind = value

    @property
    def right(self) -> BorderSide:
        """The right side."""
        return self._side('right')

    @right.setter
    def right(self, value: _core.BorderKind | bool | BorderSide) -> None:
        self._side('right').kind = value

    @property
    def bottom(self) -> BorderSide:
        """The bottom side."""
        return self._side('bottom')

    @bottom.setter
    def bottom(self, value: _core.BorderKind | bool | BorderSide) -> None:
        self._side('bottom').kind = value

    @property
    def left(self) -> BorderSide:
        """The left side."""
        return self._side('left')

    @left.setter
    def left(self, value: _core.BorderKind | bool | BorderSide) -> None:
        self._side('left').kind = value

    @property
    def color(self) -> ColorSlot:
        """The color of the border."""
        return ColorSlot(self._owner, 'border')

    @color.setter
    def color(self, value: ColorName | ColorValue | ColorSlot) -> None:
        ColorSlot(self._owner, 'border')._write(_plain_color(value, 'border.color'))

    @property
    def title(self) -> str | None:
        """The text written on the top edge, or ``None``."""
        look = self._owner._appearance
        return None if look is None else look.title

    @title.setter
    def title(self, value: str | None) -> None:
        if value is not None and not isinstance(value, str):
            raise TypeError(
                f'Cannot set border.title to {value!r}: a title is text, but got '
                f'{type(value).__name__}. Assign a string such as "Menu", or None to '
                f'remove the title. The title was not changed.'
            )
        look = self._owner._ensure_look()
        look.title = value
        self._owner._look_changed()

    def __bool__(self) -> bool:
        look = self._owner._appearance
        return look is not None and bool(look.drawn_sides())

    def __repr__(self) -> str:
        return f'BorderAppearance(kind={self.kind!r}, title={self.title!r})'


class Edges:
    """
    The four edges of a padding or a margin, in cells.

    Reading an edge gives the number of cells it is now. Assigning accepts a number of
    cells, a float or a percentage such as ``'10%'``, which is a share of the content's size
    when the look is drawn.

    Attributes:
        top: The space above.
        right: The space to the right.
        bottom: The space below.
        left: The space to the left.
    """

    __slots__ = ('_owner',)
    _field: ClassVar[str] = ''

    def __init__(self, owner: _Looked) -> None:
        """
        Make the edges of an owner. Get them from ``owner.padding`` or ``owner.margin``.

        Args:
            owner: The canvas, placement or region.
        """
        self._owner = owner

    def _stored(self) -> Spacing | None:
        look = self._owner._appearance
        return None if look is None else getattr(look, self._field)

    def _assign_all(self, value: Spacing | Edges | None) -> None:
        if value is None:
            raise _none_error(self._field)
        if isinstance(value, Edges):
            value = cast(
                'SpacingDictionary', {name: getattr(value, name) for name in _SIDE_NAMES}
            )
        checked = _checked_spacing(value, self._field)
        look = self._owner._ensure_look()
        setattr(look, self._field, checked)
        self._owner._look_changed()

    def _resolved(self) -> tuple[int, int, int, int]:
        self._owner._flush_look()
        width, height = self._owner._look_size()
        return resolve_spacing(
            self._stored(), width=width, height=height, name=self._field
        )

    def _edge(self, name: str) -> int:
        left, right, top, bottom = self._resolved()
        return {'left': left, 'right': right, 'top': top, 'bottom': bottom}[name]

    def _set_edge(self, name: str, value: int | float | str) -> None:
        stored = self._stored()
        edges: dict[str, int | float | str]
        if isinstance(stored, dict):
            edges = {name_: stored.get(name_, 0) for name_ in _SIDE_NAMES}  # type: ignore[misc]
            vertical = stored.get('vertical')
            horizontal = stored.get('horizontal')
            for key in ('top', 'bottom'):
                if key not in stored and vertical is not None:
                    edges[key] = vertical
            for key in ('left', 'right'):
                if key not in stored and horizontal is not None:
                    edges[key] = horizontal
        else:
            base = 0 if stored is None else stored
            edges = dict.fromkeys(_SIDE_NAMES, base)
        edges[name] = value
        checked = _checked_spacing(edges, self._field)
        look = self._owner._ensure_look()
        setattr(look, self._field, cast('SpacingDictionary', checked))
        self._owner._look_changed()

    @property
    def top(self) -> int:
        """The space above."""
        return self._edge('top')

    @top.setter
    def top(self, value: int | float | Percentage | str) -> None:
        self._set_edge('top', value)

    @property
    def right(self) -> int:
        """The space to the right."""
        return self._edge('right')

    @right.setter
    def right(self, value: int | float | Percentage | str) -> None:
        self._set_edge('right', value)

    @property
    def bottom(self) -> int:
        """The space below."""
        return self._edge('bottom')

    @bottom.setter
    def bottom(self, value: int | float | Percentage | str) -> None:
        self._set_edge('bottom', value)

    @property
    def left(self) -> int:
        """The space to the left."""
        return self._edge('left')

    @left.setter
    def left(self, value: int | float | Percentage | str) -> None:
        self._set_edge('left', value)

    def __repr__(self) -> str:
        return (
            f'{type(self).__name__}(top={self.top}, right={self.right}, '
            f'bottom={self.bottom}, left={self.left})'
        )


class PaddingAppearance(Edges):
    """
    The space between the border and the content; see [`Edges`][xnano.appearance.Edges].

    Attributes:
        top: The space above.
        right: The space to the right.
        bottom: The space below.
        left: The space to the left.
    """

    __slots__ = ()
    _field = 'padding'


class MarginAppearance(Edges):
    """
    The transparent space outside the border; see [`Edges`][xnano.appearance.Edges].

    Attributes:
        top: The space above.
        right: The space to the right.
        bottom: The space below.
        left: The space to the left.
    """

    __slots__ = ()
    _field = 'margin'
