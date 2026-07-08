"""xnano.beta.utils.native_types"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from xnano_core.rust import native

from xnano.beta.core.nodes import (
    LineNode,
    TextNode,
    SpanNode,
)
from xnano.beta.color import ColorLike, Color
from xnano.beta.frame import Frame, FrameTitlePosition
from xnano.beta.grid import _GridLayoutConstraint
from xnano.beta.types import (
    Alignment,
    Area,
    Border,
    CharacterModifier,
    Direction,
    Padding,
    PaddingLike,
    Side,
)

if TYPE_CHECKING:
    from xnano.beta.cursor import CursorStyle


_NATIVE_COLOR_CACHE: dict[tuple, native.Color] = {}


_NATIVE_ALIGNMENT_TYPES: dict[Alignment, native.Alignment] = {
    "left": native.Alignment.Left,
    "center": native.Alignment.Center,
    "right": native.Alignment.Right,
}


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


_NATIVE_CURSOR_STYLE_TYPES: dict[CursorStyle, native.CursorStyle] = {
    "default": native.CursorStyle.DefaultUserShape,
    "blinking_block": native.CursorStyle.BlinkingBlock,
    "steady_block": native.CursorStyle.SteadyBlock,
    "blinking_underline": native.CursorStyle.BlinkingUnderline,
    "steady_underline": native.CursorStyle.SteadyUnderline,
    "blinking_bar": native.CursorStyle.BlinkingBar,
    "steady_bar": native.CursorStyle.SteadyBar,
}


_NATIVE_DIRECTION_TYPES: dict[Direction, native.Direction] = {
    "horizontal": native.Direction.Horizontal,
    "vertical": native.Direction.Vertical,
}


_NATIVE_SCROLLBAR_ORIENTATION_TYPES: dict[Any, Any] = {
    "vertical_right": native.ScrollbarOrientation.VerticalRight,
    "vertical_left": native.ScrollbarOrientation.VerticalLeft,
    "horizontal_bottom": native.ScrollbarOrientation.HorizontalBottom,
    "horizontal_top": native.ScrollbarOrientation.HorizontalTop,
}


_NATIVE_MARKER_TYPES: dict[Any, Any] = {
    "dot": native.Marker.Dot,
    "block": native.Marker.Block,
    "bar": native.Marker.Bar,
    "braille": native.Marker.Braille,
    "half_block": native.Marker.HalfBlock,
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
    """Builds a ``native.Rect`` from a ``Area``.

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
    """Builds a ``Area`` from a ``native.Rect``.

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
    """Parses a ``ColorLike`` input into a ratatui native ``Color``
    binding.

    Args:
        color: The color to parse.

    Returns:
        The parsed ``native.Color`` binding.
    """
    if color is None:
        return None

    key = ("xnano", color)
    if key in _NATIVE_COLOR_CACHE:
        return _NATIVE_COLOR_CACHE[key]

    if isinstance(color, Color):
        native_color = native.Color.rgb(color.r, color.g, color.b)
        _NATIVE_COLOR_CACHE[key] = native_color
        return native_color

    else:
        try:
            parsed = Color.parse(color)
        except Exception as e:
            raise ValueError(f"Invalid color literal: {color!r}") from e

    native_color = native.Color.rgb(parsed.r, parsed.g, parsed.b)
    _NATIVE_COLOR_CACHE[key] = native_color
    return native_color


def get_native_modifier_from_modifiers(
    modifiers: list[CharacterModifier] | None,
) -> native.Modifier | None:
    """Parses a list of ``CharacterModifier`` inputs into a ratatui native ``Modifier``
    binding.

    Args:
        modifiers: The modifiers to parse.

    Returns:
        The parsed ``native.Modifier`` binding.
    """
    if not modifiers:
        return None

    result = native.Modifier.EMPTY
    for mod in modifiers:
        result = result | _NATIVE_MODIFIER_TYPES[mod]
    return result


def get_native_padding_from_padding_like(
    value: PaddingLike | None,
) -> native.Padding | None:
    """Parses a ``PaddingLike`` input into a ratatui native ``Padding``
    binding.

    Args:
        value: The padding to parse.

    Returns:
        The parsed ``native.Padding`` binding.
    """
    if value is None:
        return None
    if not isinstance(value, Padding):
        padding = Padding.parse(value)
    else:
        padding = value
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
        The built ``native.Style`` binding.
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
        The built ``native.Block`` binding.
    """
    if frame.is_empty():
        return None
    block = native.Block.bordered()
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


def get_native_span_from_span_node(span: SpanNode) -> native.Span:
    """Builds a ``native.Span`` from a ``SpanNode``.

    Args:
        span: The span to build the native span from.

    Returns:
        The built ``native.Span`` binding.
    """
    style = get_native_style_from_kwargs(
        color=span.color, background=span.background, modifiers=span.modifiers
    )
    if style is not None:
        return native.Span.styled(span.content, style)
    return native.Span.raw(span.content)


def get_native_line_from_line_node(line: LineNode) -> native.Line:
    """Builds a ``native.Line`` from a ``LineNode``.

    Args:
        line: The line to build the native line from.

    Returns:
        The built ``native.Line`` binding.
    """
    if isinstance(line.content, str):
        result = native.Line.raw(line.content)
    else:
        result = native.Line.from_spans(
            [
                get_native_span_from_span_node(span)
                for span in line.content or []
            ]
        )
    return apply_style_kwargs_on_native_obj(
        result,
        color=line.color,
        background=line.background,
        modifiers=line.modifiers,
    )


def get_native_text_from_text_node(node: TextNode) -> native.Text:
    """Builds a ``native.Text`` from a ``TextNode``.

    Args:
        node: The text node to build the native text from.

    Returns:
        The built ``native.Text`` binding.
    """
    if node.lines:
        result = native.Text.from_lines(
            [get_native_line_from_line_node(line) for line in node.lines]
        )
    else:
        result = native.Text.raw(node.content)

    result = apply_style_kwargs_on_native_obj(
        result,
        color=node.color,
        background=node.background,
        modifiers=list(node.modifiers),
    )
    if node.align is not None:
        result = result.alignment(_NATIVE_ALIGNMENT_TYPES[node.align])
    return result


def get_native_layout_constraint_from_constraint(
    constraint: _GridLayoutConstraint,
) -> native.Constraint:
    """Builds a ``native.Constraint`` from a ``_GridLayoutConstraint``.

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
            ``float`` ``0.0``–``1.0`` = percentage; ``None`` = equal fill.
        column_count: Number of columns (used when ``widths`` is ``None``).

    Returns:
        A list of ``native.Constraint`` objects, one per column.
    """
    if widths is None:
        return [native.Constraint.fill(1)] * max(column_count, 1)
    result: list[Any] = []
    for w in widths:
        if isinstance(w, float):
            result.append(
                native.Constraint.percentage(max(1, min(100, int(w * 100))))
            )
        else:
            result.append(native.Constraint.length(max(1, int(w))))
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
