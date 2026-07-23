"""xnano._styles

---

Shared styling: ``Style``, Tailwind utility resolution, and related
helpers for grids and components. Terminal and web backends lower the
same style model to cells or CSS as needed.
"""

from __future__ import annotations

import abc
import dataclasses
import functools
import math
from typing import Literal, Sequence

from typing_extensions import deprecated

from xnano import _types as types
from xnano._tailwind_classes import (
    KNOWN_TAILWIND_CLASSES,
    TailwindBorderClass,
    TailwindClass,
    TailwindColorClass,
    TailwindFlexClass,
    TailwindPassthroughClass,
    TailwindSizingClass,
    TailwindSpacingClass,
    TailwindTypographyClass,
)
from xnano._types import (
    Area,
    Padding,
    PaddingLike,
    Size,
    Sizing,
    SizingKind,
    SizingLike,
)
from xnano.color import _TAILWIND_NAMES, _TAILWIND_SHADES, ColorLike

_SPACING_UNITS: frozenset[str] = frozenset(
    [
        "0",
        "0.5",
        "1",
        "1.5",
        "2",
        "2.5",
        "3",
        "3.5",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "14",
        "16",
        "20",
        "24",
        "28",
        "32",
        "36",
        "40",
        "44",
        "48",
        "52",
        "56",
        "60",
        "64",
        "72",
        "80",
        "96",
        "px",
    ]
)


def _units_for_suffix(suffix: str) -> float:
    """Return the Tailwind unit count for a spacing-scale suffix."""
    if suffix == "px":
        return 1.0
    return float(suffix)


def _cells_for_units(units: float, direction: types.Direction) -> int:
    """Aspect-corrected Tailwind-unit to terminal-cell conversion.

    One Tailwind unit is 0.25rem; a terminal cell is roughly twice as
    tall as it is wide, so ``n`` units lower to ``floor(n / 4 + 0.5)``
    rows vertically and ``floor(n / 2 + 0.5)`` columns horizontally,
    with a minimum of one cell for nonzero ``n``. Half-up rounding is
    explicit so results never depend on banker's rounding.
    """
    if units <= 0:
        return 0
    divisor = 4 if direction == "vertical" else 2
    return max(1, math.floor(units / divisor + 0.5))


@dataclasses.dataclass(slots=True)
class _TailwindStyleBuilder:
    """Mutable accumulator the class-group handlers write into."""

    color: ColorLike | None = None
    background: ColorLike | None = None
    border: types.Border | None = None
    border_color: ColorLike | None = None
    border_sides: list[types.Side] = dataclasses.field(default_factory=list)
    padding_sides: dict[str, int] = dataclasses.field(default_factory=dict)
    margin_sides: dict[str, int] = dataclasses.field(default_factory=dict)
    gap: int | None = None
    width: Sizing | None = None
    height: Sizing | None = None
    modifiers: list[types.CharacterModifier] = dataclasses.field(
        default_factory=list
    )
    align: types.Alignment | None = None
    direction: types.Direction | None = None
    cursor: str | None = None
    passthrough: list[str] = dataclasses.field(default_factory=list)

    def add_modifier(self, modifier: types.CharacterModifier) -> None:
        """Append a character modifier once, preserving order."""
        if modifier not in self.modifiers:
            self.modifiers.append(modifier)

    def add_border_side(self, side: types.Side) -> None:
        """Append a border side once, preserving order."""
        if side not in self.border_sides:
            self.border_sides.append(side)

    def set_spacing(
        self,
        sides: dict[str, int],
        prefix_axis: str,
        units: float,
    ) -> None:
        """Assign aspect-corrected cells onto the sides ``prefix_axis``
        selects.

        ``prefix_axis`` is the single-character axis/side code from the
        class prefix: ``""`` for all sides, ``"x"``/``"y"`` for an
        axis, or ``"t"``/``"r"``/``"b"``/``"l"`` for one side.
        """
        vertical = _cells_for_units(units, "vertical")
        horizontal = _cells_for_units(units, "horizontal")
        if prefix_axis == "":
            sides.update(
                top=vertical,
                bottom=vertical,
                left=horizontal,
                right=horizontal,
            )
        elif prefix_axis == "x":
            sides.update(left=horizontal, right=horizontal)
        elif prefix_axis == "y":
            sides.update(top=vertical, bottom=vertical)
        elif prefix_axis == "t":
            sides["top"] = vertical
        elif prefix_axis == "b":
            sides["bottom"] = vertical
        elif prefix_axis == "l":
            sides["left"] = horizontal
        elif prefix_axis == "r":
            sides["right"] = horizontal


@deprecated(
    "'xnano.Style' is deprecated and will be removed in v1.2; use "
    "'xnano.beta.Style' instead.",
    category=DeprecationWarning,
    stacklevel=2,
)
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Style:
    """The lowered result of resolving a set of Tailwind classes.

    Attributes:
        color: Foreground color binding derived from ``text-*``.
        background: Background color binding derived from ``bg-*``.
        border: Border style derived from ``border*`` / ``rounded*``.
        border_color: Border color binding derived from
            ``border-{palette}-{shade}``.
        border_sides: Border sides derived from ``border-t|r|b|l|x|y``.
        padding: Aspect-corrected padding derived from ``p*-{n}``.
        margin: Aspect-corrected margin derived from ``m*-{n}``.
        gap: Gap in cells derived from ``gap-*``.
        width: Horizontal sizing derived from ``w-*`` / flex classes.
        height: Vertical sizing derived from ``h-*`` / flex classes.
        modifiers: Character modifiers derived from typography classes.
        align: Alignment derived from ``text-left|center|right``.
        direction: Layout direction derived from ``flex-row|col``.
        title: Chrome title text painted on the element's border.
        title_position: Where ``title`` is painted, top or bottom.
        cursor: Tailwind ``cursor-*`` token styling the pointer over
            this element.
        visible: Whether this element paints at all.
        z: Stacking order among sibling elements.
        passthrough_classes: Tokens no handler lowered — carried
            verbatim to the web backend, ignored on the terminal.
        classes: The original full token list, in order.
    """

    color: ColorLike | None = None
    """Foreground color binding derived from ``text-*``."""
    background: ColorLike | None = None
    """Background color binding derived from ``bg-*``."""
    border: types.Border | None = None
    """Border style derived from ``border*`` / ``rounded*``."""
    border_color: ColorLike | None = None
    """Border color binding derived from ``border-{palette}-{shade}``."""
    border_sides: tuple[types.Side, ...] | None = None
    """Border sides derived from ``border-t|r|b|l|x|y``."""
    padding: types.Padding | None = None
    """Aspect-corrected padding derived from ``p*-{n}``."""
    margin: types.Padding | None = None
    """Aspect-corrected margin derived from ``m*-{n}``."""
    gap: int | None = None
    """Gap in cells derived from ``gap-*``."""
    width: Sizing | None = None
    """Horizontal sizing derived from ``w-*`` / flex classes."""
    height: Sizing | None = None
    """Vertical sizing derived from ``h-*`` / flex classes."""
    modifiers: tuple[types.CharacterModifier, ...] = ()
    """Character modifiers derived from typography classes."""
    align: types.Alignment | None = None
    """Alignment derived from ``text-left|center|right``."""
    direction: types.Direction | None = None
    """Layout direction derived from ``flex-row|col``."""
    title: str | None = None
    """Chrome title text painted on the element's border."""
    title_position: Literal["top", "bottom"] | None = None
    """Where ``title`` is painted, top or bottom."""
    cursor: str | None = None
    """Tailwind ``cursor-*`` token styling the pointer over this
    element."""
    visible: bool | None = None
    """Whether this element paints at all."""
    z: int | None = None
    """Stacking order among sibling elements."""
    passthrough_classes: tuple[str, ...] = ()
    """Tokens no handler lowered — web-only or unknown classes."""
    classes: tuple[str, ...] = ()
    """The original full token list, in order."""


# Deprecated alias — ``Style`` absorbed ``TailwindStyle``; kept for one
# release so existing imports keep working.
TailwindStyle = Style


class AbstractTailwindClassGroup(abc.ABC):
    """One resolver per Tailwind utility group.

    Subclass and register with ``register_tailwind_class_group`` to
    teach the resolver a new group of classes — built-in groups are
    never edited to add one. Tokens no group matches flow to
    ``Style.passthrough_classes`` automatically, so groups are only
    needed for classes that lower into terminal vocabulary.
    """

    @abc.abstractmethod
    def match(self, token: str) -> bool:
        """Return whether this group can lower ``token``."""

    @abc.abstractmethod
    def apply(self, token: str, style: _TailwindStyleBuilder) -> None:
        """Lower ``token`` into the style accumulator."""


def _color_binding_from_suffix(suffix: str) -> str | None:
    """Return a ``ColorLike`` binding for a class suffix, or ``None``.

    Accepts ``black``/``white`` and ``{palette}-{shade}`` forms; other
    suffixes (``text-left``, ``text-xs``, ``border-2``) return ``None``
    so color classes never shadow the other groups.
    """
    if suffix in ("black", "white"):
        return suffix
    parts = suffix.rsplit("-", 1)
    if len(parts) != 2 or parts[0] not in _TAILWIND_NAMES:
        return None
    try:
        shade = int(parts[1])
    except ValueError:
        return None
    if shade not in _TAILWIND_SHADES:
        return None
    return suffix


class ColorClassGroup(AbstractTailwindClassGroup):
    """``text-*`` / ``bg-*`` / ``border-*`` palette color classes."""

    def match(self, token: str) -> bool:
        for prefix in ("text-", "bg-", "border-"):
            if token.startswith(prefix):
                suffix = token[len(prefix) :]
                return _color_binding_from_suffix(suffix) is not None
        return False

    def apply(self, token: str, style: _TailwindStyleBuilder) -> None:
        if token.startswith("text-"):
            style.color = token[len("text-") :]
        elif token.startswith("bg-"):
            style.background = token[len("bg-") :]
        else:
            style.border_color = token[len("border-") :]


class SpacingClassGroup(AbstractTailwindClassGroup):
    """``p*-{n}`` / ``m*-{n}`` / ``gap-*`` spacing classes."""

    def _parse(self, token: str) -> tuple[str, str, str] | None:
        """Split a spacing token into (kind, axis code, unit suffix)."""
        prefix, _, suffix = token.rpartition("-")
        if not prefix or suffix not in _SPACING_UNITS:
            return None
        if prefix in ("gap", "gap-x", "gap-y"):
            return ("gap", prefix[4:], suffix)
        if len(prefix) == 1 and prefix in ("p", "m"):
            return (prefix, "", suffix)
        if (
            len(prefix) == 2
            and prefix[0] in ("p", "m")
            and prefix[1] in ("x", "y", "t", "r", "b", "l")
        ):
            return (prefix[0], prefix[1], suffix)
        return None

    def match(self, token: str) -> bool:
        return self._parse(token) is not None

    def apply(self, token: str, style: _TailwindStyleBuilder) -> None:
        parsed = self._parse(token)
        if parsed is None:
            return
        kind, axis, suffix = parsed
        units = _units_for_suffix(suffix)
        if kind == "gap":
            gap_direction: types.Direction = (
                "horizontal" if axis == "x" else "vertical"
            )
            style.gap = _cells_for_units(units, gap_direction)
        elif kind == "p":
            style.set_spacing(style.padding_sides, axis, units)
        else:
            style.set_spacing(style.margin_sides, axis, units)


_BORDER_STYLE_TOKENS: dict[str, types.Border | None] = {
    "border": "plain",
    "border-0": None,
    "border-2": "thick",
    "border-4": "thick",
    "border-8": "thick",
    "border-double": "double",
}

_BORDER_SIDE_TOKENS: dict[str, tuple[types.Side, ...]] = {
    "border-t": ("top",),
    "border-r": ("right",),
    "border-b": ("bottom",),
    "border-l": ("left",),
    "border-x": ("left", "right"),
    "border-y": ("top", "bottom"),
}

_ROUNDED_TOKENS: frozenset[str] = frozenset(
    [
        "rounded",
        "rounded-sm",
        "rounded-md",
        "rounded-lg",
        "rounded-xl",
        "rounded-2xl",
        "rounded-3xl",
        "rounded-full",
    ]
)


class BorderClassGroup(AbstractTailwindClassGroup):
    """``border*`` style/side classes and ``rounded*`` radii."""

    def match(self, token: str) -> bool:
        return (
            token in _BORDER_STYLE_TOKENS
            or token in _BORDER_SIDE_TOKENS
            or token in _ROUNDED_TOKENS
            or token == "rounded-none"
        )

    def apply(self, token: str, style: _TailwindStyleBuilder) -> None:
        if token in _BORDER_SIDE_TOKENS:
            if style.border is None:
                style.border = "plain"
            for side in _BORDER_SIDE_TOKENS[token]:
                style.add_border_side(side)
            return
        if token in _ROUNDED_TOKENS:
            style.border = "rounded"
            return
        if token == "rounded-none":
            return
        if token == "border" and style.border is not None:
            # ``border`` only establishes a default style; it never
            # downgrades a width or radius another token already set.
            return
        style.border = _BORDER_STYLE_TOKENS[token]


_TYPOGRAPHY_MODIFIER_TOKENS: dict[str, types.CharacterModifier] = {
    "font-semibold": "bold",
    "font-bold": "bold",
    "font-extrabold": "bold",
    "font-black": "bold",
    "font-thin": "dim",
    "font-extralight": "dim",
    "font-light": "dim",
    "italic": "italic",
    "underline": "underline",
    "animate-pulse": "slow_blink",
}

_TYPOGRAPHY_ALIGN_TOKENS: dict[str, types.Alignment] = {
    "text-left": "left",
    "text-center": "center",
    "text-right": "right",
}

_TYPOGRAPHY_NOOP_TOKENS: frozenset[str] = frozenset(
    ["font-normal", "font-medium", "not-italic", "no-underline"]
)


class TypographyClassGroup(AbstractTailwindClassGroup):
    """Font weight/style, text decoration, and alignment classes.

    ``font-semibold`` and heavier lower to the ``bold`` modifier;
    ``font-light`` and lighter approximate as ``dim``. ``text-{size}``
    classes have no terminal equivalent and stay passthrough.
    """

    def match(self, token: str) -> bool:
        return (
            token in _TYPOGRAPHY_MODIFIER_TOKENS
            or token in _TYPOGRAPHY_ALIGN_TOKENS
            or token in _TYPOGRAPHY_NOOP_TOKENS
        )

    def apply(self, token: str, style: _TailwindStyleBuilder) -> None:
        modifier = _TYPOGRAPHY_MODIFIER_TOKENS.get(token)
        if modifier is not None:
            style.add_modifier(modifier)
            return
        align = _TYPOGRAPHY_ALIGN_TOKENS.get(token)
        if align is not None:
            style.align = align


_SIZING_FULL_TOKENS: frozenset[str] = frozenset(["full", "screen"])
_SIZING_FIT_TOKENS: frozenset[str] = frozenset(["fit", "auto", "min", "max"])


class SizingClassGroup(AbstractTailwindClassGroup):
    """``w-*`` / ``h-*`` width and height classes."""

    def _parse(self, token: str) -> tuple[types.Direction, str] | None:
        if token.startswith("w-"):
            return ("horizontal", token[2:])
        if token.startswith("h-"):
            return ("vertical", token[2:])
        return None

    def _sizing_for_suffix(
        self, suffix: str, direction: types.Direction
    ) -> Sizing | None:
        if suffix in _SIZING_FULL_TOKENS:
            return Sizing.percent(100)
        if suffix in _SIZING_FIT_TOKENS:
            return Sizing.fit()
        if "/" in suffix:
            numerator, _, denominator = suffix.partition("/")
            try:
                return Sizing.ratio(int(numerator), int(denominator))
            except ValueError:
                return None
        if suffix in _SPACING_UNITS:
            return Sizing.cells(
                _cells_for_units(_units_for_suffix(suffix), direction)
            )
        return None

    def match(self, token: str) -> bool:
        parsed = self._parse(token)
        if parsed is None:
            return False
        direction, suffix = parsed
        return self._sizing_for_suffix(suffix, direction) is not None

    def apply(self, token: str, style: _TailwindStyleBuilder) -> None:
        parsed = self._parse(token)
        if parsed is None:
            return
        direction, suffix = parsed
        sizing = self._sizing_for_suffix(suffix, direction)
        if sizing is None:
            return
        if direction == "horizontal":
            style.width = sizing
        else:
            style.height = sizing


_FLEX_DIRECTION_TOKENS: dict[str, types.Direction] = {
    "flex-row": "horizontal",
    "flex-col": "vertical",
}

_FLEX_WEIGHT_TOKENS: frozenset[str] = frozenset(
    [
        "flex-1",
        "flex-auto",
        "flex-initial",
        "flex-none",
        "grow",
        "grow-0",
        "shrink",
        "shrink-0",
    ]
)


class FlexClassGroup(AbstractTailwindClassGroup):
    """``flex`` direction and grow/shrink weight classes.

    Weight classes lower to a fraction ``Sizing`` on both axes — a
    fill sizing on the cross axis leaves the slot unchanged, so the
    weight only takes effect along the parent's layout direction.
    """

    def match(self, token: str) -> bool:
        return (
            token == "flex"
            or token in _FLEX_DIRECTION_TOKENS
            or token in _FLEX_WEIGHT_TOKENS
        )

    def apply(self, token: str, style: _TailwindStyleBuilder) -> None:
        direction = _FLEX_DIRECTION_TOKENS.get(token)
        if direction is not None:
            style.direction = direction
            return
        if token in _FLEX_WEIGHT_TOKENS:
            sizing = Sizing.parse(token)
            style.width = sizing
            style.height = sizing


_TAILWIND_CLASS_GROUPS: list[AbstractTailwindClassGroup] = [
    ColorClassGroup(),
    SpacingClassGroup(),
    BorderClassGroup(),
    TypographyClassGroup(),
    SizingClassGroup(),
    FlexClassGroup(),
]


def register_tailwind_class_group(
    group: AbstractTailwindClassGroup,
) -> None:
    """Register an additional class-group resolver.

    Registered groups match after the built-in groups, in registration
    order. Registration clears the resolver cache so already-resolved
    class lists pick up the new group.

    Args:
        group: The class-group resolver to append.
    """
    _TAILWIND_CLASS_GROUPS.append(group)
    _resolve_tokens.cache_clear()


def normalize_tailwind_classes(
    class_name: str | Sequence[str],
) -> tuple[str, ...]:
    """Normalize a class string or sequence into a token tuple.

    Args:
        class_name: A space-separated class string, or a sequence of
            individual class tokens.

    Returns:
        The individual class tokens, in order.

    Raises:
        TypeError: If ``class_name`` is not a string or a sequence of
            strings.
    """
    if isinstance(class_name, str):
        return tuple(class_name.split())
    if isinstance(class_name, Sequence):
        tokens: list[str] = []
        for token in class_name:
            if not isinstance(token, str):
                raise TypeError(
                    "class_name sequence entries must be strings, got "
                    f"{type(token).__name__!r}"
                )
            tokens.extend(token.split())
        return tuple(tokens)
    raise TypeError(
        "class_name must be a string or a sequence of strings, got "
        f"{type(class_name).__name__!r}"
    )


@functools.lru_cache(maxsize=512)
def _resolve_tokens(tokens: tuple[str, ...]) -> Style:
    builder = _TailwindStyleBuilder()
    for token in tokens:
        for group in _TAILWIND_CLASS_GROUPS:
            if group.match(token):
                group.apply(token, builder)
                break
        else:
            if token.startswith("cursor-"):
                builder.cursor = token
            builder.passthrough.append(token)

    padding = (
        types.Padding(**builder.padding_sides)
        if builder.padding_sides
        else None
    )
    margin = (
        types.Padding(**builder.margin_sides) if builder.margin_sides else None
    )
    return Style(
        color=builder.color,
        background=builder.background,
        border=builder.border,
        border_color=builder.border_color,
        border_sides=(
            tuple(builder.border_sides) if builder.border_sides else None
        ),
        padding=padding,
        margin=margin,
        gap=builder.gap,
        width=builder.width,
        height=builder.height,
        modifiers=tuple(builder.modifiers),
        align=builder.align,
        direction=builder.direction,
        cursor=builder.cursor,
        passthrough_classes=tuple(builder.passthrough),
        classes=tokens,
    )


def resolve_tailwind_classes(
    class_name: str | Sequence[str],
) -> Style:
    """Lower Tailwind classes into a ``Style``.

    Tokens are matched against the registered class groups in order;
    the first matching group lowers the token. Within one attribute a
    later token overrides an earlier one, while padding, margin,
    border sides, and modifiers accumulate. Tokens no group matches
    (web-only utilities, unknown strings) land in
    ``Style.passthrough_classes``.

    Args:
        class_name: A space-separated class string, or a sequence of
            individual class tokens.

    Returns:
        The lowered ``Style``.
    """
    return _resolve_tokens(normalize_tailwind_classes(class_name))


__all__ = (
    "AbstractTailwindClassGroup",
    "Area",
    "BorderClassGroup",
    "ColorClassGroup",
    "FlexClassGroup",
    "KNOWN_TAILWIND_CLASSES",
    "Padding",
    "PaddingLike",
    "Size",
    "Sizing",
    "SizingClassGroup",
    "SizingKind",
    "SizingLike",
    "SpacingClassGroup",
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
    "TypographyClassGroup",
    "normalize_tailwind_classes",
    "register_tailwind_class_group",
    "resolve_tailwind_classes",
)
