"""xnano.beta.core.renderables"""

from __future__ import annotations

from typing import Any, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.beta.color import ColorLike
    from xnano.beta.frame import FrameTitlePosition
    from xnano.beta.types import (
        Alignment,
        Border,
        CharacterModifier,
        Direction,
        PaddingLike,
        Side,
    )


_RESET = "\033[0m"

_MODIFIER_CODES: dict[str, str] = {
    "bold": "\033[1m",
    "dim": "\033[2m",
    "italic": "\033[3m",
    "underline": "\033[4m",
    "slow_blink": "\033[5m",
    "rapid_blink": "\033[6m",
    "reversed": "\033[7m",
}

# (top_left, horizontal, top_right, vertical, bottom_left, bottom_right)
_BORDER_CHARS: dict[str, tuple[str, str, str, str, str, str]] = {
    "plain": ("+", "-", "+", "|", "+", "+"),
    "rounded": ("╭", "─", "╮", "│", "╰", "╯"),
    "double": ("╔", "═", "╗", "║", "╚", "╝"),
    "thick": ("┏", "━", "┓", "┃", "┗", "┛"),
    "quadrant_inside": ("▛", "▀", "▜", "▌", "▙", "▟"),
    "quadrant_outside": ("▗", "▄", "▖", "▐", "▝", "▘"),
}


def _ansi_color(r: int, g: int, b: int, *, bg: bool = False) -> str:
    return f"\033[{'48' if bg else '38'};2;{r};{g};{b}m"


def _build_ansi_prefix(
    color: Any | None,
    background: Any | None,
    modifiers: Sequence[str] | None,
) -> str:
    parts: list[str] = []
    if modifiers:
        for m in modifiers:
            code = _MODIFIER_CODES.get(m)
            if code:
                parts.append(code)
    if color is not None:
        try:
            from xnano.beta.color import Color

            c = Color.parse(color)
            parts.append(_ansi_color(c.r, c.g, c.b))
        except Exception:
            pass
    if background is not None:
        try:
            from xnano.beta.color import Color

            c = Color.parse(background)
            parts.append(_ansi_color(c.r, c.g, c.b, bg=True))
        except Exception:
            pass
    return "".join(parts)


def _renderable_to_lines(value: Any) -> list[str]:
    if isinstance(value, str):
        return value.splitlines() or [""]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    # sequences (but not strings, handled above)
    if isinstance(value, (list, tuple)):
        lines: list[str] = []
        for item in value:
            lines.extend(_renderable_to_lines(item))
        return lines
    return repr(value).splitlines() or [""]


def _apply_padding(lines: list[str], padding: Any | None) -> list[str]:
    if padding is None:
        return lines
    from xnano.beta.types import Padding

    pad = Padding.parse(padding)
    inner_width = max((len(l) for l in lines), default=0)
    h_pad = " " * pad.left + "{}" + " " * pad.right
    padded = [h_pad.format(line.ljust(inner_width)) for line in lines]
    empty = " " * (inner_width + pad.left + pad.right)
    return [empty] * pad.top + padded + [empty] * pad.bottom


def _align_lines(lines: list[str], width: int, align: str | None) -> list[str]:
    if align == "center":
        return [line.center(width) for line in lines]
    if align == "right":
        return [line.rjust(width) for line in lines]
    return [line.ljust(width) for line in lines]


def _apply_border(
    lines: list[str],
    border: str | None,
    border_sides: Sequence[str] | None,
    border_color_prefix: str,
    title: str | None,
    title_position: str | None,
) -> list[str]:
    if border is None and not border_sides:
        return lines

    chars = _BORDER_CHARS.get(border or "plain", _BORDER_CHARS["plain"])
    tl, h, tr, v, bl, br = chars

    # which sides to draw
    sides = (
        set(border_sides)
        if border_sides
        else {"top", "bottom", "left", "right"}
    )
    draw_top = "top" in sides
    draw_bottom = "bottom" in sides
    draw_left = "left" in sides
    draw_right = "right" in sides

    inner_width = max((len(l) for l in lines), default=0)
    bc = border_color_prefix
    rst = _RESET if bc else ""

    result: list[str] = []

    if draw_top:
        top_fill = h * inner_width
        if title:
            # place title in top border
            tp = title_position or "top"
            if tp == "bottom":
                pass  # handled below
            else:
                label = f" {title} "
                fill_len = max(0, inner_width - len(label))
                left_fill = h * (fill_len // 2)
                right_fill = h * (fill_len - fill_len // 2)
                top_fill = left_fill + label + right_fill
        left_corner = (bc + tl + rst) if draw_left else ""
        right_corner = (bc + tr + rst) if draw_right else ""
        result.append(left_corner + bc + top_fill + rst + right_corner)

    for line in lines:
        left_wall = (bc + v + rst) if draw_left else ""
        right_wall = (bc + v + rst) if draw_right else ""
        result.append(left_wall + line + right_wall)

    if draw_bottom:
        bot_fill = h * inner_width
        if title and (title_position or "top") == "bottom":
            label = f" {title} "
            fill_len = max(0, inner_width - len(label))
            left_fill = h * (fill_len // 2)
            right_fill = h * (fill_len - fill_len // 2)
            bot_fill = left_fill + label + right_fill
        left_corner = (bc + bl + rst) if draw_left else ""
        right_corner = (bc + br + rst) if draw_right else ""
        result.append(left_corner + bc + bot_fill + rst + right_corner)

    return result


def _join_horizontal(groups: list[list[str]]) -> list[str]:
    if not groups:
        return []
    height = max(len(g) for g in groups)
    widths = [max((len(l) for l in g), default=0) for g in groups]
    result: list[str] = []
    for row in range(height):
        parts: list[str] = []
        for g, w in zip(groups, widths):
            parts.append(g[row].ljust(w) if row < len(g) else " " * w)
        result.append("".join(parts))
    return result


def _render_to_stdout(
    renderables: tuple[Any, ...],
    *,
    direction: str,
    color: Any | None,
    background: Any | None,
    modifiers: Sequence[str] | None,
    align: str | None,
    border: str | None,
    border_sides: Sequence[str] | None,
    border_color: Any | None,
    title: str | None,
    title_position: str | None,
    padding: Any | None,
) -> None:
    prefix = _build_ansi_prefix(color, background, modifiers)
    suffix = _RESET if prefix else ""
    border_color_prefix = _build_ansi_prefix(border_color, None, None)

    line_groups: list[list[str]] = []
    for renderable in renderables:
        raw_lines = _renderable_to_lines(renderable)
        raw_lines = _apply_padding(raw_lines, padding)

        if align:
            width = max((len(l) for l in raw_lines), default=0)
            raw_lines = _align_lines(raw_lines, width, align)

        if prefix:
            raw_lines = [prefix + line + suffix for line in raw_lines]

        raw_lines = _apply_border(
            raw_lines,
            border,
            border_sides,
            border_color_prefix,
            title,
            title_position,
        )
        line_groups.append(raw_lines)

    if direction == "horizontal":
        final_lines = _join_horizontal(line_groups)
    else:
        final_lines = [line for group in line_groups for line in group]

    print("\n".join(final_lines))


class Renderable:
    """Marker type for renderable values accepted by layout fields and render().

    A renderable is any value — strings, ints, floats, dataclasses, pydantic
    models, ``AbstractComponent``, ``Grid``, ``AbstractRenderNode``, or a
    ``Sequence`` of those.  Anything is displayable via ``str()``.
    """


def render(
    *renderables: Any,
    direction: Direction = "vertical",
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    modifiers: Sequence[CharacterModifier] | None = None,
    align: Alignment | None = None,
    border: Border | None = None,
    border_sides: Sequence[Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: PaddingLike | None = None,
) -> None:
    """Display the given renderables as a print-like output on the terminal display.

    Accepts any renderable value — strings, numbers, components, grids, render
    nodes, dataclasses, pydantic models, or sequences of those.  When called
    outside an active terminal session the values are printed to stdout.

    Args:
        *renderables: Values to display.
        direction: Layout direction when multiple renderables are given.
        color: Foreground color for text content.
        background: Background color for the render area.
        modifiers: Character modifiers (bold, italic, etc.) applied to text.
        align: Horizontal alignment of content within the area.
        border: Border style to wrap the rendered area.
        border_sides: Specific sides on which to draw the border.
        border_color: Color of the border.
        title: Title drawn in the border frame.
        title_position: Alignment of the border title.
        padding: Padding around the content area.
    """
    from xnano.beta.fields import GridFieldInfo
    from xnano.beta.terminal import _ACTIVE_TERMINAL
    from xnano.beta.utils.native_types import get_area_from_native_rect

    field = GridFieldInfo(
        color=color,
        background=background,
        modifiers=list(modifiers) if modifiers else None,
        align=align,
        border=border,
        border_sides=list(border_sides) if border_sides else None,
        border_color=border_color,
        title=title,
        title_position=title_position,
        padding=padding,
        direction=direction,
    )

    terminal = _ACTIVE_TERMINAL.get()
    if terminal is not None:
        sess = terminal.session
        area = get_area_from_native_rect(sess.get_native_viewport_area())
        for renderable in renderables:
            sess.grid_paint_slot(renderable, area, field)
    else:
        _render_to_stdout(
            renderables,
            direction=direction,
            color=color,
            background=background,
            modifiers=modifiers,
            align=align,
            border=border,
            border_sides=border_sides,
            border_color=border_color,
            title=title,
            title_position=title_position,
            padding=padding,
        )


__all__ = ("Renderable", "render")
