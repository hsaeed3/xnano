"""xnano.fields

Provides a set of `Field` descriptors for defining and annotating grid
fields with layout, sizing, and style information.

Example:
    ```python
    from xnano import Grid, Field

    class MyGrid(Grid):
        title: str = Field(default="My Grid")
        content: str = Field(default="Hello, world!")
        data: int = Field(default=0, state=True)
    ```
"""

from __future__ import annotations

import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    Sequence,
    TypeAlias,
    TypeVar,
    Union,
    overload,
)

from xnano import types
from xnano.color import ColorLike
from xnano.frame import Frame, FrameTitlePosition
from xnano.sizing import Sizing, SizingLike

if TYPE_CHECKING:
    from xnano.beta.tailwind import TailwindClass


UNSET = object()


ClassNameLike: TypeAlias = Union[
    "TailwindClass",
    str,
    "list[TailwindClass | str]",
]
"""Tailwind classes as a single class, a space-separated string, or a
list of class tokens. See ``xnano.beta.tailwind.TailwindClass`` for the
full supported vocabulary; unknown tokens are carried verbatim to the
web backend and ignored by the terminal.
"""


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

    Example:
        ```python
        from xnano import Grid, Field

        class MyGrid(Grid):
            title: str = Field(default="My Grid")
            data: int = Field(default=0, state=True)
        ```

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
        background: The background color behind this field's text cells. Pair
            with a filling ``width`` for a full-width bar; fills the framed
            content area when the field also defines border/title/padding chrome.
        width: Horizontal extent sizing (``10``, ``"50%"``, ``"1fr"``, ``"fit"``,
            or a ``Sizing``). Drives the split constraint in horizontal layouts;
            shrinks the slot along the cross axis otherwise.
        height: Vertical extent sizing (``3``, ``"50%"``, ``"1fr"``, ``"fit"``,
            or a ``Sizing``). Drives the split constraint in vertical layouts;
            shrinks the slot along the cross axis otherwise.
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
    """The background color of content within this field.

    Paints behind the field's text cells only, not the whole slot — so a plain
    ``background`` reads as an accent behind the content. Pair it with a filling
    ``width`` (e.g. ``width="1fr"``) for a full-width bar such as a header or
    status line. When the field also defines border, title, or padding chrome,
    this color fills the framed content area instead.
    """
    width: "Sizing | None" = None
    """Sizing intent for the field's horizontal extent.

    Accepts any `Sizing` or shorthand (``10`` cells,
    ``"50%"``, ``"1fr"``, ``"fit"``). When the grid lays out horizontally this
    drives the split constraint; otherwise it shrinks the slot to this width.
    """
    height: "Sizing | None" = None
    """Sizing intent for the field's vertical extent.

    Accepts any `Sizing` or shorthand (``3`` cells,
    ``"50%"``, ``"1fr"``, ``"fit"``). When the grid lays out vertically this
    drives the split constraint; otherwise it shrinks the slot to this height.
    """
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
    class_name: tuple[str, ...] | None = None
    """Tailwind CSS class tokens attached to this field.

    Normalized from the ``class_name`` argument to ``Field``. The web
    backend emits these classes verbatim; the terminal backend renders
    through the lowered attributes instead.
    """
    margin: types.PaddingLike | None = None
    """The margin to be applied around the outer area of this field.

    Also populated by Tailwind ``m*-{n}`` classes through
    ``class_name``; the terminal insets the field's slot by this
    amount before painting.
    """


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
    width: SizingLike | None = None,
    height: SizingLike | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    margin: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
    class_name: ClassNameLike | None = None,
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
    width: SizingLike | None = None,
    height: SizingLike | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    margin: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
    class_name: ClassNameLike | None = None,
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
    width: SizingLike | None = None,
    height: SizingLike | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    margin: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
    class_name: ClassNameLike | None = None,
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
    width: SizingLike | None = None,
    height: SizingLike | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    margin: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
    class_name: ClassNameLike | None = None,
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
    width: SizingLike | None = None,
    height: SizingLike | None = None,
    gap: int | None = None,
    direction: types.Direction | None = None,
    align: types.Alignment | None = None,
    border: types.Border | None = None,
    border_sides: Sequence[types.Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: types.PaddingLike | None = None,
    margin: types.PaddingLike | None = None,
    slide: Sequence[types.Axis] | None = None,
    class_name: ClassNameLike | None = None,
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
        background: The background color behind this field's text cells. Pair
            with a filling ``width`` for a full-width bar; fills the framed
            content area when the field also defines border/title/padding chrome.
        width: Horizontal extent sizing (``10``, ``"50%"``, ``"1fr"``, ``"fit"``,
            or a ``Sizing``). Drives the split constraint in horizontal layouts;
            shrinks the slot along the cross axis otherwise.
        height: Vertical extent sizing (``3``, ``"50%"``, ``"1fr"``, ``"fit"``,
            or a ``Sizing``). Drives the split constraint in vertical layouts;
            shrinks the slot along the cross axis otherwise.
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
        margin: The margin to be applied around the outer area of this field.
        slide: The axes along which this field may slide within its parent grid.
        class_name: Tailwind CSS classes styling this field — a space-separated
            string or a sequence of class tokens. Classes are lowered into the
            standard field attributes (see ``xnano.beta.tailwind``); an explicit
            keyword argument always overrides a class-derived value. Classes
            with no terminal equivalent are ignored by the terminal backend and
            emitted verbatim by the web backend.

    Returns:
        A new ``GridFieldInfo`` instance with all display/layout metadata,
        including the normalized ``class_name`` tokens.
    """
    tokens: tuple[str, ...] | None = None
    if class_name is not None:
        from xnano.beta.tailwind import (
            normalize_tailwind_classes,
            resolve_tailwind_classes,
        )

        tokens = normalize_tailwind_classes(class_name)
        resolved = resolve_tailwind_classes(tokens)
        if color is None:
            color = resolved.color
        if background is None:
            background = resolved.background
        if border is None:
            border = resolved.border
        if border_color is None:
            border_color = resolved.border_color
        if border_sides is None:
            border_sides = resolved.border_sides
        if padding is None:
            padding = resolved.padding
        if margin is None:
            margin = resolved.margin
        if gap is None:
            gap = resolved.gap
        if width is None:
            width = resolved.width
        if height is None:
            height = resolved.height
        if modifiers is None and resolved.modifiers:
            modifiers = resolved.modifiers
        if align is None:
            align = resolved.align
        if direction is None:
            direction = resolved.direction

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
        width=Sizing.parse(width),
        height=Sizing.parse(height),
        gap=gap,
        direction=direction,
        align=align,
        border=border,
        border_sides=border_sides,
        border_color=border_color,
        title=title,
        title_position=title_position,
        padding=padding,
        margin=margin,
        slide=_normalize_slide_axes(slide),
        class_name=tokens,
    )  # type: ignore[return-value]


__all__ = (
    "ClassNameLike",
    "Field",
    "GridFieldInfo",
    "UNSET",
)
