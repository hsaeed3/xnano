"""tests.webui.test_tailwind"""

from __future__ import annotations

import math
import typing
from typing import Any, cast

import pytest

from xnano._styles import (
    KNOWN_TAILWIND_CLASSES,
    TailwindBorderClass,
    TailwindColorClass,
    TailwindFlexClass,
    TailwindSizingClass,
    TailwindSpacingClass,
    normalize_tailwind_classes,
    resolve_tailwind_classes,
)
from xnano.color import Color
from xnano.fields import Field, GridFieldInfo
from xnano._types import Sizing
from xnano._types import Padding


TAILWIND_PALETTES = (
    "amber",
    "blue",
    "cyan",
    "emerald",
    "fuchsia",
    "gray",
    "green",
    "indigo",
    "lime",
    "neutral",
    "orange",
    "pink",
    "purple",
    "red",
    "rose",
    "sky",
    "slate",
    "stone",
    "teal",
    "violet",
    "yellow",
    "zinc",
)

TAILWIND_SHADES = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950)


def expected_cells(units: float, *, vertical: bool) -> int:
    """The aspect-corrected unit-to-cell formula, restated for tests."""
    if units <= 0:
        return 0
    divisor = 4 if vertical else 2
    return max(1, math.floor(units / divisor + 0.5))


def literal_members(alias: object) -> tuple[str, ...]:
    """The string members of a Literal type alias."""
    return typing.get_args(alias)


def field_info(**kwargs: Any) -> GridFieldInfo:
    """Build a ``GridFieldInfo`` through ``Field`` with typed access."""
    return cast(GridFieldInfo, Field(**kwargs))


# ---------------------------------------------------------------------------
# Resolver — color group
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("palette", TAILWIND_PALETTES)
def test_resolve_every_palette_for_all_prefixes(palette: str) -> None:
    for shade in TAILWIND_SHADES:
        binding = f"{palette}-{shade}"
        style = resolve_tailwind_classes(
            f"text-{binding} bg-{binding} border-{binding}"
        )
        assert style.color == binding
        assert style.background == binding
        assert style.border_color == binding
        assert style.passthrough_classes == ()
        # Every binding must resolve to a real RGB color downstream.
        parsed = Color.parse(binding)
        assert 0 <= parsed.r <= 255
        assert 0 <= parsed.g <= 255
        assert 0 <= parsed.b <= 255


def test_resolve_black_and_white_bindings() -> None:
    style = resolve_tailwind_classes("text-white bg-black border-black")
    assert style.color == "white"
    assert style.background == "black"
    assert style.border_color == "black"


def test_color_last_wins_within_attribute() -> None:
    style = resolve_tailwind_classes("text-red-500 text-blue-500")
    assert style.color == "blue-500"
    style = resolve_tailwind_classes("bg-slate-50 bg-slate-950")
    assert style.background == "slate-950"


def test_color_group_does_not_shadow_other_groups() -> None:
    style = resolve_tailwind_classes("text-center text-xs border-2")
    assert style.color is None
    assert style.border_color is None
    assert style.align == "center"
    assert style.border == "thick"


def test_border_color_does_not_imply_border_style() -> None:
    style = resolve_tailwind_classes("border-emerald-300")
    assert style.border_color == "emerald-300"
    assert style.border is None


def test_invalid_shades_are_passthrough() -> None:
    style = resolve_tailwind_classes("text-slate-475 bg-slate-1000")
    assert style.color is None
    assert style.background is None
    assert style.passthrough_classes == ("text-slate-475", "bg-slate-1000")


# ---------------------------------------------------------------------------
# Resolver — spacing group
# ---------------------------------------------------------------------------


SPACING_UNIT_VALUES: tuple[tuple[str, float], ...] = (
    ("0", 0),
    ("0.5", 0.5),
    ("1", 1),
    ("1.5", 1.5),
    ("2", 2),
    ("2.5", 2.5),
    ("3", 3),
    ("3.5", 3.5),
    ("4", 4),
    ("5", 5),
    ("6", 6),
    ("7", 7),
    ("8", 8),
    ("9", 9),
    ("10", 10),
    ("11", 11),
    ("12", 12),
    ("14", 14),
    ("16", 16),
    ("20", 20),
    ("24", 24),
    ("28", 28),
    ("32", 32),
    ("36", 36),
    ("40", 40),
    ("44", 44),
    ("48", 48),
    ("52", 52),
    ("56", 56),
    ("60", 60),
    ("64", 64),
    ("72", 72),
    ("80", 80),
    ("96", 96),
    ("px", 1),
)


@pytest.mark.parametrize(("suffix", "units"), SPACING_UNIT_VALUES)
def test_padding_scale_aspect_corrected(suffix: str, units: float) -> None:
    style = resolve_tailwind_classes(f"p-{suffix}")
    vertical = expected_cells(units, vertical=True)
    horizontal = expected_cells(units, vertical=False)
    assert style.padding == Padding(
        top=vertical, right=horizontal, bottom=vertical, left=horizontal
    )


@pytest.mark.parametrize(("suffix", "units"), SPACING_UNIT_VALUES)
def test_margin_scale_aspect_corrected(suffix: str, units: float) -> None:
    style = resolve_tailwind_classes(f"m-{suffix}")
    vertical = expected_cells(units, vertical=True)
    horizontal = expected_cells(units, vertical=False)
    assert style.margin == Padding(
        top=vertical, right=horizontal, bottom=vertical, left=horizontal
    )


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("px-8", Padding(right=4, left=4)),
        ("py-8", Padding(top=2, bottom=2)),
        ("pt-4", Padding(top=1)),
        ("pr-4", Padding(right=2)),
        ("pb-4", Padding(bottom=1)),
        ("pl-4", Padding(left=2)),
        ("mx-8", Padding(right=4, left=4)),
        ("my-8", Padding(top=2, bottom=2)),
        ("mt-2", Padding(top=1)),
        ("mr-2", Padding(right=1)),
        ("mb-2", Padding(bottom=1)),
        ("ml-2", Padding(left=1)),
    ],
)
def test_per_side_and_axis_spacing(token: str, expected: Padding) -> None:
    style = resolve_tailwind_classes(token)
    result = style.padding if token.startswith("p") else style.margin
    assert result == expected


def test_spacing_sides_accumulate() -> None:
    style = resolve_tailwind_classes("px-8 pt-4 pb-0")
    assert style.padding == Padding(top=1, right=4, bottom=0, left=4)


def test_spacing_later_token_overwrites_side() -> None:
    style = resolve_tailwind_classes("p-4 pt-0")
    assert style.padding == Padding(top=0, right=2, bottom=1, left=2)
    style = resolve_tailwind_classes("pt-4 p-0")
    assert style.padding == Padding()


def test_padding_and_margin_are_independent() -> None:
    style = resolve_tailwind_classes("p-4 m-2")
    assert style.padding == Padding(top=1, right=2, bottom=1, left=2)
    assert style.margin == Padding(top=1, right=1, bottom=1, left=1)


def test_resolve_gap_variants() -> None:
    assert resolve_tailwind_classes("gap-4").gap == 1
    assert resolve_tailwind_classes("gap-y-4").gap == 1
    assert resolve_tailwind_classes("gap-x-4").gap == 2
    assert resolve_tailwind_classes("gap-0").gap == 0
    assert resolve_tailwind_classes("gap-8 gap-2").gap == 1


def test_unscaled_spacing_suffix_is_passthrough() -> None:
    style = resolve_tailwind_classes("p-13 m-99 gap-17")
    assert style.padding is None
    assert style.margin is None
    assert style.gap is None
    assert style.passthrough_classes == ("p-13", "m-99", "gap-17")


# ---------------------------------------------------------------------------
# Resolver — border group
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("border", "plain"),
        ("border-2", "thick"),
        ("border-4", "thick"),
        ("border-8", "thick"),
        ("border-double", "double"),
    ],
)
def test_border_style_tokens(token: str, expected: str) -> None:
    assert resolve_tailwind_classes(token).border == expected


@pytest.mark.parametrize(
    "token",
    [
        "rounded",
        "rounded-sm",
        "rounded-md",
        "rounded-lg",
        "rounded-xl",
        "rounded-2xl",
        "rounded-3xl",
        "rounded-full",
    ],
)
def test_rounded_tokens(token: str) -> None:
    assert resolve_tailwind_classes(token).border == "rounded"


def test_border_zero_and_rounded_none() -> None:
    assert resolve_tailwind_classes("border-0").border is None
    assert resolve_tailwind_classes("rounded-none").border is None


def test_border_does_not_downgrade_existing_style() -> None:
    assert resolve_tailwind_classes("border-2 border").border == "thick"
    assert resolve_tailwind_classes("rounded border").border == "rounded"


@pytest.mark.parametrize(
    ("token", "sides"),
    [
        ("border-t", ("top",)),
        ("border-r", ("right",)),
        ("border-b", ("bottom",)),
        ("border-l", ("left",)),
        ("border-x", ("left", "right")),
        ("border-y", ("top", "bottom")),
    ],
)
def test_border_side_tokens(token: str, sides: tuple[str, ...]) -> None:
    style = resolve_tailwind_classes(token)
    assert style.border == "plain"
    assert style.border_sides == sides


def test_border_sides_accumulate_without_duplicates() -> None:
    style = resolve_tailwind_classes("border-t border-x border-t")
    assert style.border_sides == ("top", "left", "right")


def test_full_border_leaves_sides_unset() -> None:
    assert resolve_tailwind_classes("border").border_sides is None


# ---------------------------------------------------------------------------
# Resolver — typography group
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "modifier"),
    [
        ("font-semibold", "bold"),
        ("font-bold", "bold"),
        ("font-extrabold", "bold"),
        ("font-black", "bold"),
        ("font-thin", "dim"),
        ("font-extralight", "dim"),
        ("font-light", "dim"),
        ("italic", "italic"),
        ("underline", "underline"),
        ("animate-pulse", "slow_blink"),
    ],
)
def test_typography_modifier_tokens(token: str, modifier: str) -> None:
    assert resolve_tailwind_classes(token).modifiers == (modifier,)


def test_typography_modifiers_accumulate_in_order() -> None:
    style = resolve_tailwind_classes("font-bold italic underline font-bold")
    assert style.modifiers == ("bold", "italic", "underline")


@pytest.mark.parametrize(
    "token", ["font-normal", "font-medium", "not-italic", "no-underline"]
)
def test_typography_noop_tokens(token: str) -> None:
    style = resolve_tailwind_classes(token)
    assert style.modifiers == ()
    assert style.passthrough_classes == ()


@pytest.mark.parametrize(
    ("token", "align"),
    [
        ("text-left", "left"),
        ("text-center", "center"),
        ("text-right", "right"),
    ],
)
def test_alignment_tokens(token: str, align: str) -> None:
    assert resolve_tailwind_classes(token).align == align


def test_alignment_last_wins() -> None:
    style = resolve_tailwind_classes("text-left text-right")
    assert style.align == "right"


@pytest.mark.parametrize(
    "token",
    [
        "text-xs",
        "text-sm",
        "text-base",
        "text-lg",
        "text-xl",
        "text-2xl",
        "text-9xl",
    ],
)
def test_text_sizes_are_passthrough(token: str) -> None:
    style = resolve_tailwind_classes(token)
    assert style.passthrough_classes == (token,)
    assert style.color is None
    assert style.align is None


# ---------------------------------------------------------------------------
# Resolver — sizing group
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("w-full", Sizing.percent(100)),
        ("h-full", Sizing.percent(100)),
        ("w-screen", Sizing.percent(100)),
        ("h-screen", Sizing.percent(100)),
        ("w-fit", Sizing.fit()),
        ("w-auto", Sizing.fit()),
        ("w-min", Sizing.fit()),
        ("w-max", Sizing.fit()),
        ("h-fit", Sizing.fit()),
        ("w-1/2", Sizing.ratio(1, 2)),
        ("w-2/3", Sizing.ratio(2, 3)),
        ("w-3/4", Sizing.ratio(3, 4)),
        ("h-1/3", Sizing.ratio(1, 3)),
        ("h-4/5", Sizing.ratio(4, 5)),
        ("w-5/6", Sizing.ratio(5, 6)),
    ],
)
def test_sizing_keyword_and_fraction_tokens(
    token: str, expected: Sizing
) -> None:
    style = resolve_tailwind_classes(token)
    result = style.width if token.startswith("w-") else style.height
    assert result == expected


@pytest.mark.parametrize(("suffix", "units"), SPACING_UNIT_VALUES)
def test_sizing_numeric_scale(suffix: str, units: float) -> None:
    style = resolve_tailwind_classes(f"w-{suffix} h-{suffix}")
    assert style.width == Sizing.cells(expected_cells(units, vertical=False))
    assert style.height == Sizing.cells(expected_cells(units, vertical=True))


def test_sizing_axes_are_independent() -> None:
    style = resolve_tailwind_classes("w-full h-4")
    assert style.width == Sizing.percent(100)
    assert style.height == Sizing.cells(1)


def test_sizing_last_wins() -> None:
    style = resolve_tailwind_classes("w-full w-1/2")
    assert style.width == Sizing.ratio(1, 2)


# ---------------------------------------------------------------------------
# Resolver — flex group
# ---------------------------------------------------------------------------


def test_resolve_flex_direction() -> None:
    assert resolve_tailwind_classes("flex-col").direction == "vertical"
    assert resolve_tailwind_classes("flex-row").direction == "horizontal"
    assert resolve_tailwind_classes("flex-row flex-col").direction == (
        "vertical"
    )


@pytest.mark.parametrize(
    ("token", "weight"),
    [
        ("flex-1", 1),
        ("flex-auto", 1),
        ("grow", 1),
        ("shrink", 1),
        ("flex-initial", 0),
        ("flex-none", 0),
        ("grow-0", 0),
        ("shrink-0", 0),
    ],
)
def test_flex_weight_tokens_set_both_axes(token: str, weight: int) -> None:
    style = resolve_tailwind_classes(token)
    assert style.width == Sizing.fraction(weight)
    assert style.height == Sizing.fraction(weight)


def test_bare_flex_is_recognized_but_lowers_nothing() -> None:
    style = resolve_tailwind_classes("flex")
    assert style.passthrough_classes == ()
    assert style.width is None
    assert style.direction is None


def test_explicit_sizing_after_flex_weight_wins() -> None:
    style = resolve_tailwind_classes("flex-1 h-4")
    assert style.height == Sizing.cells(1)
    assert style.width == Sizing.fraction(1)


# ---------------------------------------------------------------------------
# Resolver — passthrough, input forms, caching
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "token",
    [
        "shadow-lg",
        "hover:bg-red-500",
        "focus:ring-2",
        "md:flex-row",
        "transition-colors",
        "truncate",
        "overflow-hidden",
        "cursor-pointer",
        "select-none",
        "opacity-50",
        "completely-made-up-class",
    ],
)
def test_unlowerable_classes_are_passthrough(token: str) -> None:
    style = resolve_tailwind_classes(token)
    assert style.passthrough_classes == (token,)
    assert style.color is None
    assert style.background is None
    assert style.border is None
    assert style.padding is None
    assert style.width is None


def test_passthrough_preserves_order_among_lowered() -> None:
    style = resolve_tailwind_classes("shadow p-2 truncate text-red-500")
    assert style.passthrough_classes == ("shadow", "truncate")
    assert style.classes == ("shadow", "p-2", "truncate", "text-red-500")


def test_string_and_sequence_forms_are_equivalent() -> None:
    from_string = resolve_tailwind_classes("p-2 text-red-500")
    from_sequence = resolve_tailwind_classes(("p-2", "text-red-500"))
    from_list = resolve_tailwind_classes(["p-2", "text-red-500"])
    assert from_string == from_sequence == from_list


def test_normalize_splits_embedded_spaces_and_collapses() -> None:
    assert normalize_tailwind_classes("  p-2   m-1 ") == ("p-2", "m-1")
    assert normalize_tailwind_classes(["p-2 m-1", "border"]) == (
        "p-2",
        "m-1",
        "border",
    )
    assert normalize_tailwind_classes("") == ()


def test_normalize_rejects_bad_types() -> None:
    with pytest.raises(TypeError):
        normalize_tailwind_classes(cast(Any, 3))
    with pytest.raises(TypeError):
        normalize_tailwind_classes(cast(Any, ("p-2", 3)))
    with pytest.raises(TypeError):
        normalize_tailwind_classes(cast(Any, None))


def test_resolution_is_cached() -> None:
    first = resolve_tailwind_classes("p-2 text-red-500")
    second = resolve_tailwind_classes(("p-2", "text-red-500"))
    assert first is second


def test_register_tailwind_class_group() -> None:
    from xnano import _styles as tailwind

    class _AccentGroup(tailwind.AbstractTailwindClassGroup):
        def match(self, token: str) -> bool:
            return token == "accent"

        def apply(
            self, token: str, style: tailwind._TailwindStyleBuilder
        ) -> None:
            style.color = "violet-500"

    group = _AccentGroup()
    tailwind.register_tailwind_class_group(group)
    try:
        assert resolve_tailwind_classes("accent").color == "violet-500"
    finally:
        tailwind._TAILWIND_CLASS_GROUPS.remove(group)
        tailwind._resolve_tokens.cache_clear()


def test_builtin_groups_match_before_registered_groups() -> None:
    from xnano import _styles as tailwind

    class _HijackGroup(tailwind.AbstractTailwindClassGroup):
        def match(self, token: str) -> bool:
            return True

        def apply(
            self, token: str, style: tailwind._TailwindStyleBuilder
        ) -> None:
            style.color = "red-500"

    group = _HijackGroup()
    tailwind.register_tailwind_class_group(group)
    try:
        assert resolve_tailwind_classes("bg-blue-500").background == (
            "blue-500"
        )
        assert resolve_tailwind_classes("shadow-lg").color == "red-500"
    finally:
        tailwind._TAILWIND_CLASS_GROUPS.remove(group)
        tailwind._resolve_tokens.cache_clear()


# ---------------------------------------------------------------------------
# Literal <-> runtime drift
# ---------------------------------------------------------------------------


def test_known_classes_sanity() -> None:
    assert "text-slate-950" in KNOWN_TAILWIND_CLASSES
    assert "p-0.5" in KNOWN_TAILWIND_CLASSES
    assert "rounded-lg" in KNOWN_TAILWIND_CLASSES
    assert "flex-col" in KNOWN_TAILWIND_CLASSES
    assert "shadow-2xl" in KNOWN_TAILWIND_CLASSES
    assert all(isinstance(name, str) for name in KNOWN_TAILWIND_CLASSES)


def test_every_known_class_resolves_without_error() -> None:
    for token in KNOWN_TAILWIND_CLASSES:
        resolve_tailwind_classes((token,))


@pytest.mark.parametrize(
    "alias",
    [
        TailwindColorClass,
        TailwindSpacingClass,
        TailwindBorderClass,
        TailwindSizingClass,
        TailwindFlexClass,
    ],
    ids=["color", "spacing", "border", "sizing", "flex"],
)
def test_lowerable_literal_groups_never_fall_through(alias: object) -> None:
    """Every Literal member of a lowerable group must match a handler.

    Guards against drift between the generated Literal blocks and the
    runtime group matchers — a member falling through to passthrough
    means the Literal advertises a class the resolver cannot lower.
    """
    for token in literal_members(alias):
        style = resolve_tailwind_classes((token,))
        assert style.passthrough_classes == (), (
            f"{token!r} advertised as lowerable but fell through"
        )


# ---------------------------------------------------------------------------
# Field(class_name=...)
# ---------------------------------------------------------------------------


def test_field_derives_attributes_from_class_name() -> None:
    info = field_info(
        default="hi",
        class_name="m-2 p-2 border rounded-lg bg-slate-900 text-slate-100",
    )
    assert info.color == "slate-100"
    assert info.background == "slate-900"
    assert info.border == "rounded"
    assert info.padding == Padding(top=1, right=1, bottom=1, left=1)
    assert info.margin == Padding(top=1, right=1, bottom=1, left=1)
    assert info.class_name == (
        "m-2",
        "p-2",
        "border",
        "rounded-lg",
        "bg-slate-900",
        "text-slate-100",
    )


def test_field_derives_sizing_direction_and_gap() -> None:
    info = field_info(
        default="hi",
        class_name="w-1/2 h-4 flex-col gap-4 text-center font-bold",
    )
    assert info.width == Sizing.ratio(1, 2)
    assert info.height == Sizing.cells(1)
    assert info.direction == "vertical"
    assert info.gap == 1
    assert info.align == "center"
    assert info.modifiers == ("bold",)


@pytest.mark.parametrize(
    ("kwargs", "attr", "expected"),
    [
        ({"color": "red"}, "color", "red"),
        ({"background": "blue"}, "background", "blue"),
        ({"border": "double"}, "border", "double"),
        ({"padding": 3}, "padding", 3),
        ({"margin": 2}, "margin", 2),
        ({"width": "75%"}, "width", Sizing.percent(75)),
        ({"height": 9}, "height", Sizing.cells(9)),
        ({"align": "right"}, "align", "right"),
        ({"direction": "horizontal"}, "direction", "horizontal"),
        ({"gap": 5}, "gap", 5),
        (
            {"modifiers": ("underline",)},
            "modifiers",
            ("underline",),
        ),
    ],
)
def test_field_explicit_kwargs_win(
    kwargs: dict[str, Any], attr: str, expected: Any
) -> None:
    info = field_info(
        default="x",
        class_name=(
            "text-blue-500 bg-red-500 border p-1 m-1 w-full h-full "
            "text-left flex-row gap-2 font-bold"
        ),
        **kwargs,
    )
    assert getattr(info, attr) == expected


def test_field_accepts_sequence() -> None:
    info = field_info(default="x", class_name=("p-2", "font-bold"))
    assert info.modifiers == ("bold",)
    assert info.class_name == ("p-2", "font-bold")


def test_field_accepts_single_token() -> None:
    info = field_info(default="x", class_name="text-red-500")
    assert info.color == "red-500"
    assert info.class_name == ("text-red-500",)


def test_field_without_class_name_has_no_tokens() -> None:
    info = field_info(default="x", color="red", padding=1)
    assert info.class_name is None
    assert info.margin is None


def test_field_keeps_unknown_classes_in_tokens() -> None:
    info = field_info(default="x", class_name="shadow-lg custom-thing")
    assert info.class_name == ("shadow-lg", "custom-thing")
    assert info.color is None


# ---------------------------------------------------------------------------
# grid_set_field
# ---------------------------------------------------------------------------


def test_grid_set_field_class_name_roundtrip() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        header: str = Field(default="hi")

    app = App()
    app.grid_set_field("header", class_name="bg-blue-500 p-2 font-bold")
    info = app._grid_field_info("header")
    assert info.background == "blue-500"
    assert info.padding == Padding(top=1, right=1, bottom=1, left=1)
    assert info.modifiers == ("bold",)
    assert info.class_name == ("bg-blue-500", "p-2", "font-bold")


def test_grid_set_field_explicit_key_wins_over_class_name() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        header: str = Field(default="hi")

    app = App()
    app.grid_set_field("header", color="red", class_name="text-blue-500")
    info = app._grid_field_info("header")
    assert info.color == "red"


def test_grid_set_field_class_name_accepts_sequence() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        header: str = Field(default="hi")

    app = App()
    app.grid_set_field("header", class_name=("m-2", "border rounded"))
    info = app._grid_field_info("header")
    assert info.margin == Padding(top=1, right=1, bottom=1, left=1)
    assert info.border == "rounded"
    assert info.class_name == ("m-2", "border", "rounded")


def test_grid_set_field_modifier_flags_toggle() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        header: str = Field(default="hi")

    app = App()
    app.grid_set_field("header", bold=True, italic=True)
    assert app._grid_field_info("header").modifiers == ("bold", "italic")
    app.grid_set_field("header", bold=False)
    assert app._grid_field_info("header").modifiers == ("italic",)
    app.grid_set_field("header", underline=True)
    assert app._grid_field_info("header").modifiers == (
        "italic",
        "underline",
    )


def test_grid_set_field_modifier_flags_on_top_of_class_name() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        header: str = Field(default="hi")

    app = App()
    app.grid_set_field("header", class_name="font-bold", dim=True)
    assert app._grid_field_info("header").modifiers == ("bold", "dim")


def test_grid_set_field_modifier_flags_with_explicit_modifiers() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        header: str = Field(default="hi")

    app = App()
    app.grid_set_field("header", modifiers=("underline",), bold=True)
    assert app._grid_field_info("header").modifiers == (
        "underline",
        "bold",
    )


# ---------------------------------------------------------------------------
# Terminal rendering
# ---------------------------------------------------------------------------


def render_grid_offscreen(grid: Any, *, cols: int = 30, rows: int = 9) -> str:
    from tests.helpers import (
        close_offscreen_app,
        open_offscreen_app,
        paint,
    )

    terminal = open_offscreen_app(grid, cols=cols, rows=rows)
    try:
        return paint(terminal, grid)
    finally:
        close_offscreen_app(terminal)


def test_terminal_renders_class_name_field() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        content: str = Field(
            default="hello",
            class_name="border rounded p-2 m-2 text-red-500",
        )

    output = render_grid_offscreen(App())
    assert "hello" in output
    assert "╭" in output  # rounded border corner

    lines = output.split("\n")
    top_border_row = next(
        index for index, line in enumerate(lines) if "╭" in line
    )
    # m-2 → 1-row top margin and 1-column left margin.
    assert top_border_row == 1
    assert lines[top_border_row].index("╭") == 1


def test_terminal_class_name_matches_explicit_kwargs() -> None:
    """Class-derived chrome must render identically to explicit kwargs."""
    from xnano import BaseGrid

    class ByClass(BaseGrid):
        content: str = Field(
            default="hello", class_name="border p-4 text-red-500"
        )

    class ByKwargs(BaseGrid):
        content: str = Field(
            default="hello",
            border="plain",
            padding=(1, 2),
            color="red-500",
        )

    assert render_grid_offscreen(ByClass()) == render_grid_offscreen(
        ByKwargs()
    )


def test_terminal_margin_insets_content() -> None:
    from xnano import BaseGrid

    class Plain(BaseGrid):
        content: str = Field(default="hello")

    class WithMargin(BaseGrid):
        content: str = Field(default="hello", class_name="m-4")

    plain_lines = render_grid_offscreen(Plain()).split("\n")
    margin_lines = render_grid_offscreen(WithMargin()).split("\n")
    plain_row = next(
        index for index, line in enumerate(plain_lines) if "hello" in line
    )
    margin_row = next(
        index for index, line in enumerate(margin_lines) if "hello" in line
    )
    # m-4 → 1 row of top margin and 2 columns of left margin.
    assert margin_row == plain_row + 1
    assert margin_lines[margin_row].index("hello") == (
        plain_lines[plain_row].index("hello") + 2
    )


def test_terminal_asymmetric_margin_sides() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        content: str = Field(
            default="hello", class_name="mt-4 ml-8 border"
        )

    lines = render_grid_offscreen(App()).split("\n")
    top_border_row = next(
        index for index, line in enumerate(lines) if "┌" in line
    )
    assert top_border_row == 1  # mt-4 → 1 row
    assert lines[top_border_row].index("┌") == 4  # ml-8 → 4 columns


def test_terminal_width_class_constrains_split() -> None:
    from xnano import BaseGrid

    class App(BaseGrid, direction="horizontal"):
        left: str = Field(default="L", class_name="w-8 border")
        right: str = Field(default="R", border="plain")

    lines = render_grid_offscreen(App(), cols=30, rows=5).split("\n")
    border_row = next(line for line in lines if "┌" in line)
    # w-8 → a 4-column slot (cells sizing spans the whole slot,
    # border included).
    assert border_row.index("┐") - border_row.index("┌") == 3


def test_terminal_height_class_constrains_split() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        top: str = Field(default="T", class_name="h-16 border")
        bottom: str = Field(default="B")

    lines = render_grid_offscreen(App(), cols=20, rows=10).split("\n")
    top_row = next(index for index, l in enumerate(lines) if "┌" in l)
    bottom_row = next(index for index, l in enumerate(lines) if "└" in l)
    # h-16 → a 4-row slot (cells sizing spans the whole slot,
    # border included).
    assert bottom_row - top_row == 3


def test_terminal_ignores_web_only_classes() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        content: str = Field(
            default="hello",
            class_name="shadow-lg transition hover:bg-red-500 truncate",
        )

    output = render_grid_offscreen(App())
    assert "hello" in output


def test_terminal_grid_with_multiple_class_name_fields() -> None:
    from xnano import BaseGrid

    class App(BaseGrid, gap=1):
        header: str = Field(
            default="Header", class_name="h-4 border-b font-bold"
        )
        body: str = Field(default="Body", class_name="flex-1 p-2")
        footer: str = Field(default="Footer", class_name="h-4 text-center")

    output = render_grid_offscreen(App(), cols=30, rows=12)
    assert "Header" in output
    assert "Body" in output
    assert "Footer" in output


# ---------------------------------------------------------------------------
# Web rendering
# ---------------------------------------------------------------------------


def render_grid_html(grid: Any) -> str:
    from xnano.core.controllers.webui import WebController

    return WebController().render_grid_html(grid)


def test_web_emits_raw_classes_verbatim() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        header: str = Field(
            default="Dashboard",
            class_name="p-2 bg-slate-900 text-slate-100 shadow-lg",
        )

    html = render_grid_html(App())
    assert "bg-slate-900" in html
    assert "text-slate-100" in html
    assert "shadow-lg" in html
    # Class-derived styling must not duplicate as inline styles.
    assert "color: rgb" not in html
    assert "background-color" not in html
    assert "padding:" not in html


def test_web_emits_unknown_classes_verbatim() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        body: str = Field(default="x", class_name="my-custom-class md:p-8")

    html = render_grid_html(App())
    assert "my-custom-class" in html
    assert "md:p-8" in html


def test_web_inline_style_when_kwarg_overrides_class() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        body: str = Field(
            default="x", color="red", class_name="text-blue-500"
        )

    html = render_grid_html(App())
    assert "text-blue-500" in html
    assert "color: rgb(255, 0, 0)" in html


def test_web_suppresses_covered_modifier_classes() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        body: str = Field(default="x", class_name="font-bold")

    html = render_grid_html(App())
    assert html.count("font-bold") == 1


def test_web_suppresses_covered_alignment() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        body: str = Field(default="x", class_name="text-center")

    html = render_grid_html(App())
    assert html.count("text-center") == 1


def test_web_suppresses_covered_sizing() -> None:
    from xnano import BaseGrid

    class App(BaseGrid, direction="horizontal"):
        left: str = Field(default="L", class_name="w-1/2")
        right: str = Field(default="R")

    html = render_grid_html(App())
    assert "w-1/2" in html
    assert "flex-basis" not in html


def test_web_inline_sizing_when_kwarg_overrides_class() -> None:
    from xnano import BaseGrid

    class App(BaseGrid, direction="horizontal"):
        left: str = Field(default="L", width="75%", class_name="w-1/2")
        right: str = Field(default="R")

    html = render_grid_html(App())
    assert "w-1/2" in html
    assert "flex-basis: 75%" in html


def test_web_suppresses_covered_frame_chrome() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        body: str = Field(default="x", class_name="border rounded-lg p-1")

    html = render_grid_html(App())
    assert html.count("rounded-lg") == 1
    assert "padding:" not in html
    assert "border-zinc-600" not in html


def test_web_keeps_frame_chrome_without_class_name() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        body: str = Field(default="x", border="rounded", padding=1)

    html = render_grid_html(App())
    assert "rounded-lg" in html
    assert "border-zinc-600" in html
    assert "padding:" in html


def test_web_flex_weight_class_replaces_flex_grow_style() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        body: str = Field(default="x", class_name="flex-1")

    html = render_grid_html(App())
    assert "flex-1" in html
    assert "flex-grow" not in html


def test_web_margin_classes_have_no_inline_margin() -> None:
    from xnano import BaseGrid

    class App(BaseGrid):
        body: str = Field(default="x", class_name="m-4")

    html = render_grid_html(App())
    assert "m-4" in html
    assert "margin" not in html
