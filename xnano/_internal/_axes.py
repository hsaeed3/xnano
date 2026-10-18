"""
xnano._internal._axes

Turn axis values (numbers, percentages, ranges, expressions) into core expressions.
"""

from __future__ import annotations

import math
from typing import (
    Final,
    cast,
)

import xnano_core as _core
from xnano._schema._appearance import RGB, ColorValue
from xnano._schema._axes import (
    Axis,
    AxisName,
    Bound,
    NumericExpression,
    RangeBound,
)
from xnano._schema._layout import CanvasLayout, EdgeBehavior
from xnano.appearance._look import MOST_CELLS
from xnano.errors import TerminalError

# The shades of the named colors in the standard xterm palette. A terminal draws a named color
# in its own theme, but a pixel needs actual channels, so these stand in for them.
NAMED_COLOR_CHANNELS: Final[dict[str, RGB]] = {
    'black': (0, 0, 0),
    'red': (205, 0, 0),
    'green': (0, 205, 0),
    'yellow': (205, 205, 0),
    'blue': (0, 0, 238),
    'magenta': (205, 0, 205),
    'cyan': (0, 205, 205),
    'gray': (229, 229, 229),
    'grey': (229, 229, 229),
    'dark_gray': (127, 127, 127),
    'dark_grey': (127, 127, 127),
    'darkgray': (127, 127, 127),
    'darkgrey': (127, 127, 127),
    'light_black': (127, 127, 127),
    'light_red': (255, 0, 0),
    'bright_red': (255, 0, 0),
    'light_green': (0, 255, 0),
    'bright_green': (0, 255, 0),
    'light_yellow': (255, 255, 0),
    'bright_yellow': (255, 255, 0),
    'light_blue': (92, 92, 255),
    'bright_blue': (92, 92, 255),
    'light_magenta': (255, 0, 255),
    'bright_magenta': (255, 0, 255),
    'light_cyan': (0, 255, 255),
    'bright_cyan': (0, 255, 255),
    'white': (255, 255, 255),
}


def to_rgb(color: ColorValue) -> RGB:
    """
    Return the red, green and blue channels of a color.

    A named color such as ``'red'`` has the shade of the standard xterm palette.

    Raises:
        ValueError: The color has no channels (an indexed color or ``'reset'`` depends on
            the user's theme) or is not a color.
    """
    if isinstance(color, tuple):
        red, green, blue = color
        for channel in (red, green, blue):
            if not 0 <= channel <= 255:
                raise TerminalError(
                    f'The color {color!r} has a channel of {channel}, but channels run from 0 '
                    f'to 255. Pass (red, green, blue) with each channel in that range.',
                    code='validation.bounds',
                    location='color',
                    input_value=color,
                )
        return (int(red), int(green), int(blue))
    if isinstance(color, str):
        named = NAMED_COLOR_CHANNELS.get(color.strip().lower())
        if named is not None:
            return named
        parsed = _core.Color(color)
    elif isinstance(color, _core.Color):
        parsed = color
    else:
        raise TerminalError(
            f'{color!r} is not a color. Pass a Color, an (red, green, blue) tuple or a '
            f"'#rrggbb' string.",
            code='validation.value',
            location='color',
            input_value=color,
        )
    channels = parsed.to_rgb()
    if channels is None and isinstance(color, _core.Color):
        channels = NAMED_COLOR_CHANNELS.get(repr(color)[7:-2])
    if channels is None:
        raise TerminalError(
            f'The color {color!r} has no red, green and blue channels, because it is '
            f"chosen by the user's theme. Pass a color name, a '#rrggbb' string or an "
            f'(red, green, blue) tuple instead.',
            code='validation.value',
            location='color',
            input_value=color,
        )
    return channels


_AXIS_NAMES: Final[tuple[AxisName, ...]] = ('x', 'y', 'width', 'height')
_PARENT_OF_AXIS: Final[dict[AxisName, NumericExpression]] = {
    'x': _core.ParentWidth,
    'width': _core.ParentWidth,
    'y': _core.ParentHeight,
    'height': _core.ParentHeight,
}


_HORIZONTAL_WORDS = ('left', 'center', 'right')
_VERTICAL_WORDS = ('top', 'center', 'bottom')


def _axis_word(text: str, axis: AxisName) -> NumericExpression | float | None:
    """
    Where a word such as ``'center'`` puts something on its axis, or ``None`` for other text.

    ``x`` takes ``'left'``, ``'center'`` and ``'right'``; ``y`` takes ``'top'``, ``'center'``
    and ``'bottom'``. They place the thing inside its parent by its own size.
    """
    word = text.strip().lower()
    if word not in _HORIZONTAL_WORDS + _VERTICAL_WORDS:
        return None
    words = {'x': _HORIZONTAL_WORDS, 'y': _VERTICAL_WORDS}.get(axis)
    if words is None or word not in words:
        raise TerminalError(
            f'{text!r} cannot place the {axis}. Words work for x ("left", "center", "right") '
            f'and for y ("top", "center", "bottom"); size a {axis} with a number, a '
            f"percentage such as '50%' or an expression.",
            code='validation.value',
            location=axis,
            input_value=text,
        )
    parent, own = (
        (_core.ParentWidth, _core.Width)
        if axis == 'x'
        else (_core.ParentHeight, _core.Height)
    )
    if word in ('left', 'top'):
        return 0
    if word == 'center':
        return (parent - own) // 2
    return parent - own


def _percentage(text: str, axis: AxisName) -> float:
    stripped = text.strip()
    if not stripped.endswith('%'):
        raise TerminalError(
            f'{text!r} is not a valid {axis}. Give a number of cells such as 12, a share of '
            f"the parent such as '50%', a range such as (1, 10), or an expression.",
            code='validation.value',
            location=axis,
            input_value=text,
        )
    try:
        share = float(stripped[:-1]) / 100.0
    except ValueError:
        share = math.nan
    if not math.isfinite(share):
        raise TerminalError(
            f"{text!r} is not a percentage. Write a number followed by '%', such as '50%'.",
            code='validation.value',
            location=axis,
            input_value=text,
        )
    return share


def _limit_bound(value: object, axis: AxisName) -> Bound:
    """One end of a range: a number, a percentage of the parent or an expression."""
    if isinstance(value, bool):
        raise TerminalError(
            f'{value!r} is not a valid bound for the range of {axis}. Use a number of cells, '
            f"a percentage string such as '50%', or an expression.",
            code='validation.value',
            location=axis,
            input_value=value,
        )
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return _PARENT_OF_AXIS[axis] * _percentage(value, axis)
        except ValueError:
            raise TerminalError(
                f'{value!r} is not a valid bound for the range of {axis}. Use a number of '
                f"cells, a percentage string such as '50%', or an expression.",
                code='validation.value',
                location=axis,
                input_value=value,
            ) from None
    if isinstance(value, _core.NumericValue):
        return value
    if isinstance(value, _core.StateReference):
        return value.number
    raise TerminalError(
        f'{value!r} is not a valid bound for the range of {axis}. Use a number of cells, a '
        f"percentage string such as '50%', or an expression.",
        code='validation.value',
        location=axis,
        input_value=value,
    )


def axis_limits(
    value: tuple[RangeBound, RangeBound], axis: AxisName
) -> tuple[Bound | None, Bound | None]:
    """
    Turn a range into its lowest and highest bound; ``None`` leaves a side open.

    Args:
        value: The range as a pair ``(low, high)``, see [`Axis`][xnano.types.Axis].
        axis: ``'x'``, ``'y'``, ``'width'`` or ``'height'``.

    Raises:
        ValueError: The range is not a pair, has a bound that is not a bound, or starts
            above where it ends.
    """
    if axis not in _AXIS_NAMES:
        raise TerminalError(
            f'{axis!r} is not an axis; use one of {", ".join(_AXIS_NAMES)}.',
            code='validation.value',
            location='axis',
            input_value=axis,
        )
    if len(value) != 2:
        raise TerminalError(
            f'A range for {axis} is a pair (lowest, highest), but {value!r} has '
            f'{len(value)} items. Write it as {axis}=(lowest, highest), with None for a '
            f'side that is open.',
            code='validation.value',
            location=axis,
            input_value=value,
        )
    low = None if value[0] is None else _limit_bound(value[0], axis)
    high = None if value[1] is None else _limit_bound(value[1], axis)
    if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low > high:
        raise TerminalError(
            f'The range for {axis} starts at {low} but ends at {high}. Put the lowest '
            f'bound first.',
            code='validation.bounds',
            location=axis,
            input_value=value,
        )
    return low, high


def inspect_number(buffer: _core.Buffer, expression: NumericExpression) -> float:
    """
    Evaluate a numeric expression against a buffer.

    Raises:
        TypeError: The expression reads input that has not been seen yet, such as the
            pointer position before the pointer has moved, so it has no value.
    """
    result = buffer.inspect(cast('_core.Expression[float]', expression))
    if result is None:
        raise TypeError(
            'This formula has no value yet because it reads input that has not been seen, '
            'such as PointerPosition before the pointer has moved. Assign a number now and '
            'update it from a hook that runs when the input arrives, or use a formula that '
            'does not depend on unseen input.'
        )
    return float(result)


def axis_expression(value: Axis, axis: AxisName) -> NumericExpression | float:
    """
    Turn an axis value into a number or an expression that is evaluated on every frame.

    Args:
        value: The axis value, see [`Axis`][xnano.types.Axis]. A range is not a value;
            see [`axis_limits`][xnano._internal._axes.axis_limits].
        axis: ``'x'``, ``'y'``, ``'width'`` or ``'height'``.

    Raises:
        ValueError: The value is not one of the forms an axis accepts.
    """
    if axis not in _AXIS_NAMES:
        raise TerminalError(
            f'{axis!r} is not an axis; use one of {", ".join(_AXIS_NAMES)}.',
            code='validation.value',
            location='axis',
            input_value=axis,
        )
    if isinstance(value, bool) or (isinstance(value, float) and not math.isfinite(value)):
        raise TerminalError(
            f'{value!r} is not a valid {axis}. Give a number of cells, a percentage string, '
            f'a range or an expression.',
            code='validation.value',
            location=axis,
            input_value=value,
        )
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        word = _axis_word(value, axis)
        if word is not None:
            return word
        return _PARENT_OF_AXIS[axis] * _percentage(value, axis)
    if isinstance(value, _core.NumericValue):
        return value
    if isinstance(value, _core.StateReference):
        return value.number
    raise TerminalError(
        f'{value!r} is not a valid {axis}. Give a number of cells, a percentage string, a '
        f'range or an expression.',
        code='validation.value',
        location=axis,
        input_value=value,
    )


def check_size(converted: object, axis: AxisName, value: object) -> None:
    """
    Refuse a width or height that is a negative number of cells or more than a buffer holds.

    Raises:
        ValueError: ``axis`` is ``'width'`` or ``'height'`` and ``converted`` is below 0 or
            above 65535.
    """
    if (
        axis in ('width', 'height')
        and isinstance(converted, (int, float))
        and (converted < 0 or converted > MOST_CELLS)
    ):
        raise TerminalError(
            f'{axis} must be a whole number of cells from 0 to {MOST_CELLS}, but was '
            f'{value!r}. Pass a size such as {axis}=4, or leave {axis} out to use the size '
            f'of the content.',
            code='validation.bounds',
            location=axis,
            input_value=value,
        )


def size_share(text: str) -> float | None:
    """The share of ``'50%'`` (0.5), or ``None`` when the text is not a percentage."""
    if not text.endswith('%'):
        return None
    try:
        share = float(text[:-1]) / 100.0
    except ValueError:
        return None
    return share if math.isfinite(share) else None


def check_axis(value: Axis, axis: AxisName) -> None:
    """
    Raise the error that assigning ``value`` to ``axis`` would raise, changing nothing.

    Raises:
        ValueError: The value is not one of the forms an axis accepts.
    """
    if isinstance(value, tuple):
        axis_limits(value, axis)
        return
    check_size(axis_expression(value, axis), axis, value)


_LEAST_LAYER: Final = -(2**31)
_MOST_LAYER: Final = 2**31 - 1


def check_edges(value: object) -> EdgeBehavior:
    """
    Return ``value`` when it is an edges setting.

    Raises:
        ValueError: The value is not ``'clip'``, ``'stop'`` or ``'wrap'``.
    """
    if value not in ('clip', 'stop', 'wrap'):
        raise TerminalError(
            f"edges must be 'clip', 'stop' or 'wrap', but got {value!r}. Pass edges='stop' to "
            f"keep content inside its area when it moves, edges='wrap' to continue text on "
            f"the next rows, or edges='clip' to let it move past the edge.",
            code='validation.value',
            location='edges',
            input_value=value,
        )
    return cast('EdgeBehavior', value)


def check_layout(value: object) -> CanvasLayout:
    """
    Return ``value`` when it is a canvas layout.

    Raises:
        ValueError: The value is not ``'overlay'``, ``'column'`` or ``'row'``.
    """
    if value not in ('overlay', 'column', 'row'):
        raise TerminalError(
            f"layout must be 'overlay', 'column' or 'row', but got {value!r}. Pass "
            f"layout='column' to stack what is written from top to bottom, layout='row' to "
            f"stack it from left to right, or layout='overlay' to place each piece on its own.",
            code='validation.value',
            location='layout',
            input_value=value,
        )
    return cast('CanvasLayout', value)


def check_layer(value: object) -> int:
    """
    Return ``value`` when it is a whole number that can be a layer.

    Raises:
        TypeError: The value is not a whole number.
        ValueError: The value is outside the range of a layer.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TerminalError(
            f'layer must be a whole number, but got {value!r}. Pass layer=1 to draw above '
            f'the rest, or layer=-1 to draw below it.',
            code='validation.type',
            location='layer',
            input_value=value,
        )
    if not _LEAST_LAYER <= value <= _MOST_LAYER:
        raise TerminalError(
            f'layer must be a whole number from {_LEAST_LAYER} to {_MOST_LAYER}, but got '
            f'{value!r}. Pass layer=1 to draw above the rest, or layer=-1 to draw below it.',
            code='validation.bounds',
            location='layer',
            input_value=value,
        )
    return value


def check_point(value: object) -> _core.Point:
    """
    Return ``value`` when it is a screen cell.

    Raises:
        TypeError: The value is not a [`Point`][xnano_core.Point].
    """
    if not isinstance(value, _core.Point):
        raise TerminalError(
            f'local() takes a Point, but got {value!r}. Pass a cell such as '
            f'context.mouse.position, or xnano_core.Point(x, y).',
            code='validation.type',
            location='point',
            input_value=value,
        )
    return value


LEAST_CELL: Final = -(2**31)
MOST_CELL: Final = 2**31 - 1


def check_cells(value: object, name: str) -> int:
    """
    Return ``value`` when it is a whole number of cells.

    Raises:
        TypeError: The value is not a whole number.
        ValueError: The value is outside the range of a cell number.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TerminalError(
            f'{name} must be a whole number of cells, but got {value!r}. Pass '
            f'{name}=1 for one cell, or a negative number for the other way.',
            code='validation.type',
            location=name,
            input_value=value,
        )
    if not LEAST_CELL <= value <= MOST_CELL:
        raise TerminalError(
            f'{name} must be a whole number of cells from {LEAST_CELL} to {MOST_CELL}, '
            f'but got {value!r}. Pass {name}=1 for one cell, or a negative number for the '
            f'other way.',
            code='validation.bounds',
            location=name,
            input_value=value,
        )
    return value


def check_count(value: object, *, verb: str, opposite: str) -> int:
    """
    Return ``value`` when it is a whole number of cells that is not negative.

    Args:
        value: The count to check.
        verb: The name of the method the count was given to, such as ``'up'``.
        opposite: The name of the method that moves the other way, such as ``'down'``.

    Raises:
        TypeError: The value is not a whole number.
        ValueError: The value is negative or above the range of a cell number.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TerminalError(
            f'count must be a whole number of cells, but got {value!r}. Pass count=1 to '
            f'move one cell with {verb}().',
            code='validation.type',
            location='count',
            input_value=value,
        )
    if value > MOST_CELL:
        raise TerminalError(
            f'count must be at most {MOST_CELL}, but got {value}. Pass a smaller count, '
            f'such as count=1 to move one cell with {verb}().',
            code='validation.bounds',
            location='count',
            input_value=value,
        )
    if value < 0:
        raise TerminalError(
            f'count must be zero or more, but got {value}. To move the other way, call '
            f'{opposite}() instead of {verb}().',
            code='validation.bounds',
            location='count',
            input_value=value,
        )
    return value
