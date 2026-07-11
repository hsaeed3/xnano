"""scripts.generate_tailwind_literal

---

One-off generator for the ``TailwindClass`` Literal blocks committed in
``xnano/beta/tailwind.py``. Never imported at runtime — rerun it and
paste the output below the generated-code marker in that module when
the supported class vocabulary changes:

    uv run python scripts/generate_tailwind_literal.py
"""

from __future__ import annotations


TAILWIND_PALETTES: list[str] = [
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
]

TAILWIND_SHADES: list[int] = [
    50,
    100,
    200,
    300,
    400,
    500,
    600,
    700,
    800,
    900,
    950,
]

SPACING_SCALE: list[str] = [
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

PADDING_PREFIXES: list[str] = ["p", "px", "py", "pt", "pr", "pb", "pl"]
MARGIN_PREFIXES: list[str] = ["m", "mx", "my", "mt", "mr", "mb", "ml"]
GAP_PREFIXES: list[str] = ["gap", "gap-x", "gap-y"]

BORDER_CLASSES: list[str] = [
    "border",
    "border-0",
    "border-2",
    "border-4",
    "border-8",
    "border-double",
    "border-t",
    "border-r",
    "border-b",
    "border-l",
    "border-x",
    "border-y",
    "rounded",
    "rounded-none",
    "rounded-sm",
    "rounded-md",
    "rounded-lg",
    "rounded-xl",
    "rounded-2xl",
    "rounded-3xl",
    "rounded-full",
]

TYPOGRAPHY_CLASSES: list[str] = [
    "font-thin",
    "font-extralight",
    "font-light",
    "font-normal",
    "font-medium",
    "font-semibold",
    "font-bold",
    "font-extrabold",
    "font-black",
    "italic",
    "not-italic",
    "underline",
    "no-underline",
    "line-through",
    "animate-pulse",
    "text-left",
    "text-center",
    "text-right",
    "text-xs",
    "text-sm",
    "text-base",
    "text-lg",
    "text-xl",
    "text-2xl",
    "text-3xl",
    "text-4xl",
    "text-5xl",
    "text-6xl",
    "text-7xl",
    "text-8xl",
    "text-9xl",
]

SIZING_FRACTIONS: list[str] = [
    "1/2",
    "1/3",
    "2/3",
    "1/4",
    "2/4",
    "3/4",
    "1/5",
    "2/5",
    "3/5",
    "4/5",
    "1/6",
    "5/6",
]

SIZING_KEYWORDS: list[str] = ["full", "screen", "fit", "auto", "min", "max"]

FLEX_CLASSES: list[str] = [
    "flex",
    "flex-row",
    "flex-col",
    "flex-1",
    "flex-auto",
    "flex-initial",
    "flex-none",
    "grow",
    "grow-0",
    "shrink",
    "shrink-0",
]

PASSTHROUGH_CLASSES: list[str] = [
    "shadow",
    "shadow-sm",
    "shadow-md",
    "shadow-lg",
    "shadow-xl",
    "shadow-2xl",
    "shadow-inner",
    "shadow-none",
    "transition",
    "transition-all",
    "transition-colors",
    "transition-opacity",
    "transition-shadow",
    "transition-transform",
    "truncate",
    "overflow-hidden",
    "overflow-auto",
    "overflow-scroll",
    "overflow-visible",
    "opacity-0",
    "opacity-25",
    "opacity-50",
    "opacity-60",
    "opacity-75",
    "opacity-100",
    "cursor-pointer",
    "cursor-default",
    "select-none",
    "select-text",
]


def build_color_classes() -> list[str]:
    """Return every ``{text,bg,border}-{binding}`` color class."""
    bindings: list[str] = ["black", "white"]
    for palette in TAILWIND_PALETTES:
        for shade in TAILWIND_SHADES:
            bindings.append(f"{palette}-{shade}")
    return [
        f"{prefix}-{binding}"
        for prefix in ("text", "bg", "border")
        for binding in bindings
    ]


def build_spacing_classes() -> list[str]:
    """Return every padding, margin, and gap spacing class."""
    prefixes = PADDING_PREFIXES + MARGIN_PREFIXES + GAP_PREFIXES
    return [
        f"{prefix}-{unit}" for prefix in prefixes for unit in SPACING_SCALE
    ]


def build_sizing_classes() -> list[str]:
    """Return every ``w-*`` / ``h-*`` sizing class."""
    suffixes = SPACING_SCALE + SIZING_FRACTIONS + SIZING_KEYWORDS
    return [f"{axis}-{suffix}" for axis in ("w", "h") for suffix in suffixes]


def emit_literal(name: str, values: list[str]) -> str:
    """Render one ``TypeAlias`` Literal block as source text."""
    lines = [f"{name}: TypeAlias = Literal["]
    for value in values:
        lines.append(f'    "{value}",')
    lines.append("]")
    return "\n".join(lines)


def main() -> None:
    blocks = [
        emit_literal("TailwindColorClass", build_color_classes()),
        emit_literal("TailwindSpacingClass", build_spacing_classes()),
        emit_literal("TailwindBorderClass", BORDER_CLASSES),
        emit_literal("TailwindTypographyClass", TYPOGRAPHY_CLASSES),
        emit_literal("TailwindSizingClass", build_sizing_classes()),
        emit_literal("TailwindFlexClass", FLEX_CLASSES),
        emit_literal("TailwindPassthroughClass", PASSTHROUGH_CLASSES),
    ]
    print("\n\n\n".join(blocks))


if __name__ == "__main__":
    main()
