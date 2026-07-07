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
        for renderable in renderables:
            if isinstance(renderable, str):
                print(renderable)
            else:
                print(repr(renderable))


__all__ = ("Renderable", "render")
