"""xnano._core_bindings

---

Conversions between framework types (``Area``, ``Color``, ``Frame``,
layout constraints, …) and ``xnano_core`` native bindings used for
terminal drawing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import xnano_core.rust.native as native

from xnano._types import (
    Area,
    Border,
    CharacterModifier,
    Direction,
    Frame,
    FrameTitlePosition,
    Padding,
    PaddingLike,
    Side,
)
from xnano.color import Color, ColorLike
from xnano.core.controllers.abstract import LayoutConstraint

if TYPE_CHECKING:
    from xnano.tui.cursor import CursorStyle


_NATIVE_COLOR_CACHE: dict[tuple[int, int, int, float], native.Color] = {}
_NATIVE_COLOR_OBJECT_CACHE: dict[Color, native.Color] = {}
_NATIVE_COLOR_STRING_CACHE: dict[str, native.Color] = {}


_NATIVE_BORDER_TYPES: dict[Border, native.BorderType] = {
    "plain": native.BorderType.Plain,
    "rounded": native.BorderType.Rounded,
    "double": native.BorderType.Double,
    "thick": native.BorderType.Thick,
    "quadrant_inside": native.BorderType.QuadrantInside,
    "quadrant_outside": native.BorderType.QuadrantOutside,
}


_NATIVE_BORDER_SIDE_TYPES: dict[Side, native.Borders] = {
    "top": native.Borders.TOP,
    "bottom": native.Borders.BOTTOM,
    "left": native.Borders.LEFT,
    "right": native.Borders.RIGHT,
}


# native.CursorStyle only exists in terminal-feature builds; wasm builds
# ship the layout/render engine plus a buffer-backed CoreSession, but not
# the live cursor / device control surface.
_NATIVE_CURSOR_STYLE_TYPES: dict["CursorStyle", native.CursorStyle] = (
    {
        "default": native.CursorStyle.DefaultUserShape,
        "blinking_block": native.CursorStyle.BlinkingBlock,
        "steady_block": native.CursorStyle.SteadyBlock,
        "blinking_underline": native.CursorStyle.BlinkingUnderline,
        "steady_underline": native.CursorStyle.SteadyUnderline,
        "blinking_bar": native.CursorStyle.BlinkingBar,
        "steady_bar": native.CursorStyle.SteadyBar,
    }
    if hasattr(native, "CursorStyle")
    else {}
)


_NATIVE_DIRECTION_TYPES: dict[Direction, native.Direction] = {
    "horizontal": native.Direction.Horizontal,
    "vertical": native.Direction.Vertical,
}


_NATIVE_MODIFIER_TYPES: dict[CharacterModifier, native.Modifier] = {
    "bold": native.Modifier.BOLD,
    "dim": native.Modifier.DIM,
    "italic": native.Modifier.ITALIC,
    "underline": native.Modifier.UNDERLINED,
    "slow_blink": native.Modifier.SLOW_BLINK,
    "rapid_blink": native.Modifier.RAPID_BLINK,
    "reversed": native.Modifier.REVERSED,
}


_NATIVE_TITLE_POSITION_TYPES: dict[
    FrameTitlePosition, native.TitlePosition
] = {
    "top": native.TitlePosition.Top,
    "bottom": native.TitlePosition.Bottom,
}


def get_native_rect_from_area(area: Area) -> native.Rect:
    """Builds a ``native.Rect`` from an ``Area``.

    Args:
        area: The area to build the native rect from.

    Returns:
        The built ``native.Rect`` binding.
    """
    return native.Rect(
        x=area.x,
        y=area.y,
        width=area.width,
        height=area.height,
    )


def get_area_from_native_rect(rect: native.Rect) -> Area:
    """Builds an ``Area`` from a ``native.Rect``.

    Args:
        rect: The rect to build the area from.
    """
    return Area(
        x=rect.x,
        y=rect.y,
        width=rect.width,
        height=rect.height,
    )


def get_native_color_from_color_like(
    color: ColorLike | None,
) -> native.Color | None:
    """Parses a ``ColorLike`` input into a ratatui native ``Color`` binding.

    Args:
        color: The color to parse.

    Returns:
        The parsed ``native.Color`` binding, or ``None`` when ``color`` is
        ``None``.
    """
    if color is None:
        return None
    if isinstance(color, Color):
        cached_color = _NATIVE_COLOR_OBJECT_CACHE.get(color)
        if cached_color is not None:
            return cached_color
    if isinstance(color, str):
        cached_string = _NATIVE_COLOR_STRING_CACHE.get(color)
        if cached_string is not None:
            return cached_string

    parsed = Color.parse(color)
    key = (parsed.r, parsed.g, parsed.b, parsed.a)
    cached = _NATIVE_COLOR_CACHE.get(key)
    if cached is not None:
        return cached

    native_color = native.Color.rgb(parsed.r, parsed.g, parsed.b)
    _NATIVE_COLOR_CACHE[key] = native_color
    if isinstance(color, Color):
        _NATIVE_COLOR_OBJECT_CACHE[color] = native_color
    if isinstance(color, str):
        _NATIVE_COLOR_STRING_CACHE[color] = native_color
    return native_color


def get_native_modifier_from_modifiers(
    modifiers: list[CharacterModifier] | None,
) -> native.Modifier | None:
    """Parses a list of ``CharacterModifier`` inputs into a ratatui native
    ``Modifier`` binding.

    Args:
        modifiers: The modifiers to parse.

    Returns:
        The parsed ``native.Modifier`` binding, or ``None`` when empty.
    """
    if not modifiers:
        return None

    result = native.Modifier.EMPTY
    for modifier in modifiers:
        result = result | _NATIVE_MODIFIER_TYPES[modifier]
    return result


def get_native_padding_from_padding_like(
    value: PaddingLike | None,
) -> native.Padding | None:
    """Parses a ``PaddingLike`` input into a ratatui native ``Padding``
    binding.

    Args:
        value: The padding to parse.

    Returns:
        The parsed ``native.Padding`` binding, or ``None`` when ``value``
        is ``None``.
    """
    if value is None:
        return None
    padding = value if isinstance(value, Padding) else Padding.parse(value)
    return native.Padding.new(
        left=int(padding.left),
        right=int(padding.right),
        top=int(padding.top),
        bottom=int(padding.bottom),
    )


def get_native_style_from_kwargs(
    *,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    modifiers: list[CharacterModifier] | None = None,
) -> native.Style | None:
    """Builds a ``native.Style`` when any styling field is non-empty.

    Args:
        color: The foreground color of the style.
        background: The background color of the style.
        modifiers: The modifiers of the style.

    Returns:
        The built ``native.Style`` binding, or ``None`` when nothing was
        set.
    """
    native_color = get_native_color_from_color_like(color)
    native_background = get_native_color_from_color_like(background)
    native_modifier = get_native_modifier_from_modifiers(modifiers)

    if (
        native_color is None
        and native_background is None
        and native_modifier is None
    ):
        return None

    native_style = native.Style.new()
    if native_color is not None:
        native_style = native_style.fg(native_color)
    if native_background is not None:
        native_style = native_style.bg(native_background)
    if native_modifier is not None:
        native_style = native_style.add_modifier(native_modifier)
    return native_style


def get_native_block_from_frame(frame: Frame) -> native.Block | None:
    """Builds a ``native.Block`` when any frame field is non-empty.

    Args:
        frame: The frame to build the block from.

    Returns:
        The built ``native.Block`` binding, or ``None`` when ``frame`` is
        empty.
    """
    if frame.is_empty():
        return None
    block = (
        native.Block.bordered()
        if frame.border is not None
        else native.Block.new()
    )
    if frame.border_sides is not None:
        sides = native.Borders.NONE
        for side in frame.border_sides:
            sides = sides | _NATIVE_BORDER_SIDE_TYPES[side]
        block = block.borders(sides)
    if frame.border is not None:
        block = block.border_type(_NATIVE_BORDER_TYPES[frame.border])
    if frame.border_color is not None:
        border_style = get_native_style_from_kwargs(color=frame.border_color)
        if border_style is not None:
            block = block.border_style(border_style)
    if frame.title is not None:
        block = block.title(frame.title)
    if frame.title_position is not None:
        block = block.title_position(
            _NATIVE_TITLE_POSITION_TYPES[frame.title_position]
        )
    padding = get_native_padding_from_padding_like(frame.padding)
    if padding is not None:
        block = block.padding(padding)
    if frame.background is not None:
        background_style = get_native_style_from_kwargs(
            background=frame.background
        )
        if background_style is not None:
            block = block.style(background_style)
    return block


def get_native_layout_constraint_from_constraint(
    constraint: LayoutConstraint,
) -> native.Constraint:
    """Builds a ``native.Constraint`` from a ``LayoutConstraint``.

    Args:
        constraint: The constraint to build the native constraint from.

    Returns:
        The built ``native.Constraint`` binding.
    """
    if constraint.kind == "length":
        return native.Constraint.length(constraint.value)
    if constraint.kind == "percentage":
        return native.Constraint.percentage(constraint.value)
    if constraint.kind == "ratio":
        return native.Constraint.ratio(constraint.value, constraint.value2)
    if constraint.kind == "content":
        return native.Constraint.length(constraint.value)
    if constraint.kind == "min":
        return native.Constraint.min(constraint.value)
    if constraint.kind == "max":
        return native.Constraint.max(constraint.value)
    return native.Constraint.fill(constraint.value)


def get_native_table_constraints(
    widths: list[int | float] | None,
    column_count: int,
) -> list[Any]:
    """Build a ``list[native.Constraint]`` for a table's column widths.

    Args:
        widths: Per-column width spec.  ``int`` = fixed char width;
            ``float`` ``0.0``-``1.0`` = percentage; ``None`` = equal fill.
        column_count: Number of columns (used when ``widths`` is ``None``).

    Returns:
        A list of ``native.Constraint`` objects, one per column.
    """
    if widths is None:
        return [native.Constraint.fill(1)] * max(column_count, 1)
    result: list[Any] = []
    for width in widths:
        if isinstance(width, float):
            result.append(
                native.Constraint.percentage(
                    max(1, min(100, int(width * 100)))
                )
            )
        else:
            result.append(native.Constraint.length(max(1, int(width))))
    return result


def apply_style_kwargs_on_native_obj(
    native_obj: Any,
    *,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    modifiers: list[CharacterModifier] | None = None,
) -> Any:
    """Applies style kwargs to a native object.

    Args:
        native_obj: The native object to apply the style kwargs to.
        color: The foreground color of the style.
        background: The background color of the style.
        modifiers: The modifiers of the style.

    Returns:
        The native object with the style kwargs applied.
    """
    native_style = get_native_style_from_kwargs(
        color=color, background=background, modifiers=modifiers
    )
    if native_style is not None and hasattr(native_obj, "style"):
        return native_obj.style(native_style)
    return native_obj


def frame_length_overhead(frame: Frame, direction: Direction) -> int:
    """Return the cell overhead a frame's border/padding adds along an axis.

    Used both to measure a `FrameNode` (its child's size plus this
    overhead) and to size non-`BaseGrid` renderables sharing a `GridFieldInfo`'s
    chrome.

    Args:
        frame: The frame whose border/padding overhead to measure.
        direction: Which axis to measure the overhead along.

    Returns:
        The number of cells of overhead along `direction`.
    """
    extra = 0
    if frame.border is not None or frame.border_sides is not None:
        extra += 2
    padding = frame.padding
    if padding is not None:
        if isinstance(padding, Padding):
            extra += (
                padding.vertical
                if direction == "vertical"
                else padding.horizontal
            )
        elif isinstance(padding, int):
            extra += padding * 2
        elif isinstance(padding, tuple) and len(padding) == 2:
            vertical, horizontal = padding
            extra += (
                (vertical * 2) if direction == "vertical" else (horizontal * 2)
            )
        elif isinstance(padding, tuple) and len(padding) == 4:
            top, right, bottom, left = padding  # type: ignore[misc]
            extra += (
                (int(top or 0) + int(bottom or 0))
                if direction == "vertical"
                else (int(left or 0) + int(right or 0))
            )
    return extra


__all__ = (
    "get_native_rect_from_area",
    "get_area_from_native_rect",
    "get_native_color_from_color_like",
    "get_native_modifier_from_modifiers",
    "get_native_padding_from_padding_like",
    "get_native_style_from_kwargs",
    "get_native_block_from_frame",
    "get_native_layout_constraint_from_constraint",
    "get_native_table_constraints",
    "apply_style_kwargs_on_native_obj",
    "frame_length_overhead",
)
