"""xnano.beta.fields"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Literal, Sequence, TypeVar, overload

from xnano.beta import types
from xnano.beta.color import ColorLike, Color
from xnano.beta.frame import Frame, FrameTitlePosition


UNSET = object()


def _normalize_slide_axes(
    slide: Sequence[types.Axis] | None,
) -> list[str]:
    if not slide:
        return []
    axes: list[str] = []
    for axis in slide:
        if axis not in ("x", "y"):
            raise ValueError(
                f"slide axes must be 'x' and/or 'y', got {axis!r}"
            )
        if axis not in axes:
            axes.append(axis)
    return axes


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GridFieldInfo:
    """Descriptor class for layout, frame and additional rendering metadata for
    a field within a grid.

    Attributes:
        default: Static default value for this field.
        default_factory: Callable that produces the default value each time an instance is created.
        state: Whether this field is a stateful field (does not ever represent renderable content).
        strict: When ``True`` and this field is a state field, assignments are validated
            against the field's type annotation using ``pydantic_core``.
        init: Whether this field should be included within the constructor of it's parent grid class.
        visible: Whether this field is visible on the live terminal display.
        modifiers: Modifiers to apply to all characters within this field. This can be a list
            including "bold", "dim", "italic", "underline", "slow_blink", "rapid_blink",
            "reversed".
        color: The foreground color of content within this field.
        background: The background color of this field's frame area.
        size: Fixed size as a percentage of the parent area's axis length. Ignored when `
            `fit`` is ``True``.
        flex: Relative fill weight when ``size`` is ``None``. Higher values claim proportionally
            more space.
        fit: Size the field to its content each frame. When set, ``size`` becomes a maximum clamp.
        gap: The gap between fields in this field or area.
        direction: The direction in which content within this field or area should be laid out.
        align: The horizontal alignment of content within this field's area.
        border: A border style to be applied onto the outer frame of the rectangular area this
            field occupies.
        border_sides: The sides of the border to be applied onto the outer frame of the area
            this field occupies.
        border_color: The color of this field's border, if one is set.
        title: A title to be displayed around the outer frame of this field's area.
        title_position: The alignment of the title within the outer frame of this
            field's area.
        padding: The padding to be applied around the content area of this field.
        slide: The axes along which this field may slide within its parent grid.
    """

    default: Any = UNSET
    """Static default value for this field."""

    _: dataclasses.KW_ONLY

    strict: bool = False
    """When ``True`` and this field is a state field, assignments are validated
    against the field's type annotation using ``pydantic_core``."""
    default_factory: Callable[[], Any] | None = None
    """Callable that produces the default value each time an instance is created."""
    state: bool | None = None
    """Whether this field is a stateful field (does not ever represent renderable content)."""
    init: bool = True
    """Whether this field should be included within the constructor of it's parent grid class."""
    visible: bool | None = None
    """Whether this field is visible on the live terminal display."""
    modifiers: Sequence[types.CharacterModifier] | None = None
    """Modifiers to apply to all characters within this field.

    This can be a list of any of the following modifiers:
        - ``"bold"``: Renders the content in bold.
        - ``"dim"``: The content is rendered with reduced intensity.
        - ``"italic"``: Renders the content in italics.
        - ``"underline"``: Adds an underline beneath the content.
        - ``"slow_blink"``: Causes the content to blink slowly.
        - ``"rapid_blink"``: Causes the content to blink rapidly.
        - ``"reversed"``: Swaps foreground and background colors.
    """
    color: ColorLike | None = None
    """The foreground color of content within this field."""
    background: ColorLike | None = None
    """The background color of this field's frame area."""
    size: types.SizePercentage | None = None
    """Fixed size as a percentage of the parent area's axis length. Ignored when ``fit`` is ``True``."""
    flex: int | None = None
    """Relative fill weight when ``size`` is ``None``. Higher values claim proportionally more space."""
    fit: bool | None = None
    """Size the field to its content each frame. When set, ``size`` becomes a maximum clamp."""
    gap: int | None = None
    """The gap between fields in this field or area."""
    direction: types.Direction | None = None
    """The direction in which content within this field or area should be
    laid out.
    """
    align: types.Alignment | None = None
    """The horizontal alignment of content within this field's area."""
    border: types.Border | None = None
    """A border style to be applied onto the outer frame of the rectangular area
    this field occupies.
    """
    border_sides: Sequence[types.Side] | None = None
    """The sides of the border to be applied onto the outer frame of the area
    this field occupies.
    """
    border_color: ColorLike | None = None
    """The color of this field's border, if one is set."""
    title: str | None = None
    """A title to be displayed around the outer frame of this field's area."""
    title_position: FrameTitlePosition | None = None
    """The alignment of the title within the outer frame of this field's area."""
    padding: types.PaddingLike | None = None
    """The padding to be applied around the content area of this field."""
    slide: list[str] | None = None
    """The axes along which this field may slide within its parent grid."""


@overload
def Field(
    default: None,
    *,
    default_factory: None = None,
    state: bool = False,
    strict: bool = False,
    init: bool = True,
    visible: bool | None = None,
    modifiers: Sequence[types.CharacterModifier] | None = None,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    size: types.SizePercentage | None = None,
    flex: int | None = None,
    fit: bool | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
) -> Any: ...


@overload
def Field(
    default: _T,
    *,
    default_factory: None = None,
    state: bool = False,
    strict: bool = False,
    init: bool = True,
    visible: bool | None = None,
    modifiers: Sequence[types.CharacterModifier] | None = None,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    size: types.SizePercentage | None = None,
    flex: int | None = None,
    fit: bool | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
) -> _T: ...


@overload
def Field(
    *,
    default_factory: Callable[[], _T],
    state: bool = False,
    strict: bool = False,
    init: bool = True,
    visible: bool | None = None,
    modifiers: Sequence[types.CharacterModifier] | None = None,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    size: types.SizePercentage | None = None,
    flex: int | None = None,
    fit: bool | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
) -> _T: ...


@overload
def Field(
    *,
    default: Any = UNSET,
    default_factory: None = None,
    state: bool = False,
    strict: bool = False,
    init: bool = True,
    visible: bool | None = None,
    modifiers: Sequence[types.CharacterModifier] | None = None,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    size: types.SizePercentage | None = None,
    flex: int | None = None,
    fit: bool | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
) -> Any: ...


def Field(
    default: Any = UNSET,
    *,
    default_factory: Callable[[], Any] | None = None,
    state: bool = False,
    strict: bool = False,
    init: bool = True,
    visible: bool | None = None,
    modifiers: Sequence[types.CharacterModifier] | None = None,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    size: types.SizePercentage | None = None,
    flex: int | None = None,
    fit: bool | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
) -> GridFieldInfo:
    """Create a new grid field info instance.

    Args:
        default: Static default value for this field.
        default_factory: Callable that produces the default value each time an instance is created.
        state: Whether this field is a stateful field (does not ever represent renderable content).
        strict: When ``True`` and this field is a state field, assignments are validated
            against the field's type annotation using ``pydantic_core``.
        init: Whether this field should be included within the constructor of it's parent grid class.
        visible: Whether this field is visible on the live terminal display.
        modifiers: Modifiers to apply to all characters within this field. This can be a list
            including "bold", "dim", "italic", "underline", "slow_blink", "rapid_blink",
            "reversed".
        color: The foreground color of content within this field.
        background: The background color of this field's frame area.
        size: Fixed size as a percentage of the parent area's axis length. Ignored when `
            `fit`` is ``True``.
        flex: Relative fill weight when ``size`` is ``None``. Higher values claim proportionally
            more space.
        fit: Size the field to its content each frame. When set, ``size`` becomes a maximum clamp.
        gap: The gap between fields in this field or area.
        direction: The direction in which content within this field or area should be laid out.
        align: The horizontal alignment of content within this field's area.
        border: A border style to be applied onto the outer frame of the rectangular area this
            field occupies.
        border_sides: The sides of the border to be applied onto the outer frame of the area
            this field occupies.
        border_color: The color of this field's border, if one is set.
        title: A title to be displayed around the outer frame of this field's area.
        title_position: The alignment of the title within the outer frame of this
            field's area.
        padding: The padding to be applied around the content area of this field.
        slide: The axes along which this field may slide within its parent grid.

    Returns:
        A new ``GridFieldInfo`` instance with all display/layout metadata.
    """
    return GridFieldInfo(
        default=default,
        default_factory=default_factory,
        state=state,
        strict=strict,
        init=init,
        visible=visible,
        color=color,
        modifiers=modifiers,
        background=background,
        size=size,
        flex=flex,
        fit=fit,
        gap=gap,
        direction=direction,
        align=align,
        border=border,
        border_sides=border_sides,
        border_color=border_color,
        title=title,
        title_position=title_position,
        padding=padding,
        slide=_normalize_slide_axes(slide),
    )  # type: ignore[return-value]


__all__ = (
    "Field",
    "GridFieldInfo",
    "UNSET",
)
