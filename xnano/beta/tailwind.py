"""xnano.beta.tailwind

---

Resolve Tailwind-style utility classes into xnano layout and text styles.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Sequence, TypeAlias

from xnano.beta.colors import ColorLike
from xnano.beta.types import (
    Alignment,
    Border,
    CharacterModifier,
    Direction,
    Padding,
    Side,
    Sizing,
)

TailwindClass: TypeAlias = str
"""A Tailwind utility class understood by xnano or passed through to web."""

TailwindColorClass: TypeAlias = str
"""A foreground, background, or border color class."""

TailwindBorderClass: TypeAlias = str
"""A border style or border-side class."""

TailwindFlexClass: TypeAlias = str
"""A flex growth or shrink class."""

TailwindPassthroughClass: TypeAlias = str
"""A class retained for browser output when xnano does not lower it."""

TailwindSizingClass: TypeAlias = str
"""A width or height class."""

TailwindSpacingClass: TypeAlias = str
"""A padding, margin, or gap class."""

TailwindTypographyClass: TypeAlias = str
"""A text modifier or alignment class."""

KNOWN_TAILWIND_CLASSES: frozenset[str] = frozenset()
"""Known classes are resolved by grammar, so this set is intentionally lazy."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Style:
    """Style derived from Tailwind utility classes.

    Attributes:
        color: Foreground color.
        background: Background color.
        border: Border style.
        border_color: Border color.
        border_sides: Visible border sides.
        padding: Inner spacing.
        margin: Outer spacing.
        gap: Spacing between children.
        width: Horizontal size.
        height: Vertical size.
        modifiers: Text modifiers.
        align: Horizontal alignment.
        direction: Child layout direction.
        title: Optional frame title.
        title_position: Alignment of the frame title.
        visible: Visibility override.
        cursor: Browser cursor class.
        passthrough_classes: Classes retained for browser output.
        classes: Normalized source classes.

    Examples:
        ```python
        style = resolve_tailwind_style("text-red-500 bg-black p-2 rounded")
        ```
    """

    color: ColorLike | None = None
    """Foreground color."""
    background: ColorLike | None = None
    """Background color."""
    border: Border | None = None
    """Border style."""
    border_color: ColorLike | None = None
    """Border color."""
    border_sides: tuple[Side, ...] | None = None
    """Visible border sides."""
    padding: Padding | None = None
    """Inner spacing."""
    margin: Padding | None = None
    """Outer spacing."""
    gap: int | None = None
    """Cells between children."""
    width: Sizing | None = None
    """Horizontal size."""
    height: Sizing | None = None
    """Vertical size."""
    modifiers: tuple[CharacterModifier, ...] = ()
    """Character modifiers."""
    align: Alignment | None = None
    """Horizontal alignment."""
    direction: Direction | None = None
    """Child layout direction."""
    title: str | None = None
    """Optional frame title."""
    title_position: str | None = None
    """Frame title alignment."""
    visible: bool | None = None
    """Visibility override."""
    cursor: str | None = None
    """Browser cursor name."""
    passthrough_classes: tuple[str, ...] = ()
    """Classes retained for browser output."""
    classes: tuple[str, ...] = ()
    """Normalized source classes."""


TailwindStyle = Style
"""Resolved Tailwind style."""


def normalize_tailwind_classes(
    class_name: str | Sequence[str],
) -> tuple[str, ...]:
    """Split, trim, and deduplicate utility classes."""
    source = class_name.split() if isinstance(class_name, str) else class_name
    return tuple(
        dict.fromkeys(token for item in source for token in item.split())
    )


def _spacing_cells(value: str, *, vertical: bool) -> int:
    if value == "px":
        return 1
    units = float(value)
    return max(1, math.floor(units / (4 if vertical else 2) + 0.5))


def _update_spacing(
    values: dict[str, int],
    axis: str,
    suffix: str,
) -> None:
    vertical = _spacing_cells(suffix, vertical=True)
    horizontal = _spacing_cells(suffix, vertical=False)
    if not axis:
        values.update(
            top=vertical,
            right=horizontal,
            bottom=vertical,
            left=horizontal,
        )
    elif axis == "x":
        values.update(left=horizontal, right=horizontal)
    elif axis == "y":
        values.update(top=vertical, bottom=vertical)
    else:
        values[
            {"t": "top", "r": "right", "b": "bottom", "l": "left"}[axis]
        ] = vertical if axis in ("t", "b") else horizontal


def _color_from_class(token: str, prefix: str) -> str | None:
    if not token.startswith(prefix):
        return None
    value = token.removeprefix(prefix)
    return value if value else None


def resolve_tailwind_classes(class_name: str | Sequence[str]) -> Style:
    """Resolve supported utilities and preserve unknown classes for web."""
    tokens = normalize_tailwind_classes(class_name)
    values: dict[str, object] = {}
    padding: dict[str, int] = {}
    margin: dict[str, int] = {}
    modifiers: list[CharacterModifier] = []
    border_sides: list[Side] = []
    passthrough: list[str] = []

    for token in tokens:
        if token.startswith("text-"):
            suffix = token[5:]
            if suffix in ("left", "right", "center"):
                values["align"] = suffix
            elif suffix in ("bold", "italic"):
                modifiers.append(suffix)  # ty: ignore[invalid-argument-type]
            else:
                values["color"] = suffix
        elif token.startswith("bg-"):
            values["background"] = token[3:]
        elif token in ("font-bold", "italic", "underline"):
            modifier = "bold" if token == "font-bold" else token
            modifiers.append(modifier)  # ty: ignore[invalid-argument-type]
        elif token == "opacity-50":
            modifiers.append("dim")
        elif token in ("flex", "flex-row"):
            values["direction"] = "horizontal"
        elif token == "flex-col":
            values["direction"] = "vertical"
        elif token.startswith("gap-"):
            values["gap"] = _spacing_cells(token[4:], vertical=False)
        elif token.startswith(
            ("p-", "px-", "py-", "pt-", "pr-", "pb-", "pl-")
        ):
            prefix, suffix = token.split("-", 1)
            _update_spacing(padding, prefix[1:], suffix)
        elif token.startswith(
            ("m-", "mx-", "my-", "mt-", "mr-", "mb-", "ml-")
        ):
            prefix, suffix = token.split("-", 1)
            _update_spacing(margin, prefix[1:], suffix)
        elif token.startswith("w-"):
            values["width"] = Sizing.parse(token[2:].replace("full", "100%"))
        elif token.startswith("h-"):
            values["height"] = Sizing.parse(token[2:].replace("full", "100%"))
        elif token in ("border", "rounded", "rounded-md", "rounded-lg"):
            values["border"] = (
                "rounded" if token.startswith("rounded") else "plain"
            )
        elif token in ("border-t", "border-r", "border-b", "border-l"):
            side = {
                "border-t": "top",
                "border-r": "right",
                "border-b": "bottom",
                "border-l": "left",
            }[token]
            border_sides.append(side)  # ty: ignore[invalid-argument-type]
        elif (color := _color_from_class(token, "border-")) is not None:
            values["border_color"] = color
        elif token.startswith("cursor-"):
            values["cursor"] = token[7:]
        else:
            passthrough.append(token)

    return Style(
        **values,  # ty: ignore[invalid-argument-type]
        padding=Padding(**padding) if padding else None,
        margin=Padding(**margin) if margin else None,
        modifiers=tuple(dict.fromkeys(modifiers)),
        border_sides=tuple(dict.fromkeys(border_sides)) or None,
        passthrough_classes=tuple(passthrough),
        classes=tokens,
    )


__all__ = (
    "KNOWN_TAILWIND_CLASSES",
    "Style",
    "TailwindBorderClass",
    "TailwindClass",
    "TailwindColorClass",
    "TailwindFlexClass",
    "TailwindPassthroughClass",
    "TailwindSizingClass",
    "TailwindSpacingClass",
    "TailwindStyle",
    "TailwindTypographyClass",
    "normalize_tailwind_classes",
    "resolve_tailwind_classes",
)
