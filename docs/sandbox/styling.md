---
title: "Styling"
icon: "lucide/palette"
---

# Styling Sandbox

xnano uses one terminal style vocabulary across
[`render()`](../api/xnano/_renderable.md#xnano._renderable.render){data-preview}, grids, fields, and
components. This page covers every accepted color form, modifier, frame
option, and Tailwind utility family that lowers to terminal cells.

## Color Inputs

`color`, `background`, and `border_color` accept a CSS color name, a Tailwind
palette binding, hex, an RGB/RGBA tuple, or a
[`Color`](../api/xnano/color.md#xnano.color.Color){data-preview} object.

```pyodide install="xnano>=1.0.10" height="19"
from xnano import render
from xnano.color import Color

samples = [
    ("named", "tomato"),
    ("Tailwind", "violet-400"),
    ("hex", "#22d3ee"),
    ("RGB", (250, 204, 21)),
    ("RGBA", (52, 211, 153, 0.8)),
    ("Color", Color(r=244, g=114, b=182)),
]

for label, value in samples:
    render(f" {label:^10} ", color=value, border="rounded", border_color=value)
```

Tailwind palette names are `amber`, `blue`, `cyan`, `emerald`, `fuchsia`,
`gray`, `green`, `indigo`, `lime`, `neutral`, `orange`, `pink`, `purple`,
`red`, `rose`, `sky`, `slate`, `stone`, `teal`, `violet`, `yellow`, and `zinc`,
plus `black` and `white`. Colored palettes accept shades `50`, `100`, `200`,
`300`, `400`, `500`, `600`, `700`, `800`, `900`, and `950`.

```pyodide install="xnano>=1.0.10" height="20"
from xnano import render

palette = "violet"  # change to any palette named above
for shade in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950):
    binding = f"{palette}-{shade}"
    render(f"{binding:>12}", color=binding, end="  ")
print()
```

??? example "Color Inputs"
    - `color`, `background`, `border_color`: [ColorLike](../api/xnano/color.md#xnano.color.ColorLike){data-preview} or `None`.
    - Named strings: [ColorName](../api/xnano/color.md#xnano.color.ColorName){data-preview}; Tailwind strings: [TailwindColorBinding](../api/xnano/color.md#xnano.color.TailwindColorBinding){data-preview}.
    - Tuples: [ColorTuple](../api/xnano/color.md#xnano.color.ColorTuple){data-preview}; objects: [Color](../api/xnano/color.md#xnano.color.Color){data-preview}.

## Color Palette

Render the complete Tailwind terminal palette at once: every palette name,
every shade from `50` through `950`, plus solid black and white.

```pyodide install="xnano>=1.0.10" height="28"
from xnano import Terminal
from xnano.components.text import Text

palettes = (
    "amber", "blue", "cyan", "emerald", "fuchsia", "gray", "green",
    "indigo", "lime", "neutral", "orange", "pink", "purple", "red",
    "rose", "sky", "slate", "stone", "teal", "violet", "yellow", "zinc",
)
shades = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950)

rows = []
for palette in palettes:
    swatches = [
        Text(
            f" {shade:^3} ",
            color="black" if shade <= 400 else "white",
            background=f"{palette}-{shade}",
        )
        for shade in shades
    ]
    rows.append(Text([Text(f"{palette:>8} ", modifiers=("bold",)), *swatches]))

rows.append(Text([
    Text("   solid ", modifiers=("bold",)),
    Text(" black ", color="white", background="black"),
    Text(" white ", color="black", background="white"),
]))

Terminal(width=72, height=24).render(*rows)
```

??? example "Color Palette"

    - Palette names: [TailwindColorName](../api/xnano/color.md#xnano.color.TailwindColorName){data-preview}.
    - Shade values: [TailwindColorShade](../api/xnano/color.md#xnano.color.TailwindColorShade){data-preview}.
    - Complete bindings: [TailwindColorBinding](../api/xnano/color.md#xnano.color.TailwindColorBinding){data-preview}.

## Foreground and Background

Field/grid backgrounds fill their framed content area. For a full-width bar,
give the field a filling width or frame chrome.

```pyodide install="xnano>=1.0.10" height="20"
from xnano import BaseGrid, Field, Terminal

class Colors(BaseGrid, border="double", border_color="slate-500", padding=1):
    header: str = Field(
        default=" foreground + background ",
        color="yellow-200",
        background="indigo-900",
        width="1fr",
        height=1,
        align="center",
    )
    body: str = Field(
        default="independent border color",
        color="#67e8f9",
        border="rounded",
        border_color="cyan-500",
        padding=1,
    )

Terminal(width=56, height=9).render(Colors())
```

??? example "Foreground and Background"
    - `color`, `background`, `border_color`: [ColorLike](../api/xnano/color.md#xnano.color.ColorLike){data-preview} or `None`.
    - `align`: [Alignment](../api/xnano/_types.md#xnano._types.Alignment){data-preview} or `None`.
    - `border`: [Border](../api/xnano/_types.md#xnano._types.Border){data-preview} or `None`; `padding`: [PaddingLike](../api/xnano/_styles.md#xnano._styles.PaddingLike){data-preview}.
    - `width`: [SizingLike](../api/xnano/_styles.md#xnano._styles.SizingLike){data-preview}.

## Character Modifiers

The complete set is `bold`, `dim`, `italic`, `underline`, `slow_blink`,
`rapid_blink`, and `reversed`. Terminal/browser support for blinking depends on
the output renderer; the ANSI codes are still emitted.

```pyodide install="xnano>=1.0.10" height="18"
from xnano import render

modifiers = (
    "bold",
    "dim",
    "italic",
    "underline",
    "slow_blink",
    "rapid_blink",
    "reversed",
)
for modifier in modifiers:
    render(f"{modifier:>12}: xnano", modifiers=(modifier,), color="cyan-300")
```

On a grid, the same choices are available as boolean class settings; on a
field or
[`Text`](../api/xnano/components/text.md#xnano.components.text.Text){data-preview},
pass the `modifiers` sequence.

```pyodide install="xnano>=1.0.10" height="16"
from xnano import BaseGrid, Field, Terminal

class ModifiedGrid(BaseGrid, bold=True, italic=True, underline=True, border="rounded"):
    inherited: str = Field(default="grid modifier flags")
    field_only: str = Field(default="field modifiers", modifiers=("dim", "reversed"))

Terminal(width=48, height=6).render(ModifiedGrid())
```

Grid settings also expose `dim`, `slow_blink`, `rapid_blink`, and `reversed` as
boolean flags.

??? example "Character Modifiers"
    - `modifiers`: a sequence of [CharacterModifier](../api/xnano/_types.md#xnano._types.CharacterModifier){data-preview} values.
    - Values: `"bold"`, `"dim"`, `"italic"`, `"underline"`, `"slow_blink"`, `"rapid_blink"`, `"reversed"`.
    - Grid flags: `bold`, `dim`, `italic`, `underline`, `slow_blink`, `rapid_blink`, `reversed` as `bool`.

## Border Styles

Use `None` for no frame, or one of the six styles below.

```pyodide install="xnano>=1.0.10" height="28"
from xnano import BaseGrid, Field, Terminal

class Borders(BaseGrid, direction="vertical", gap=0):
    plain: str = Field(default="plain", border="plain", height=3, align="center")
    rounded: str = Field(default="rounded", border="rounded", height=3, align="center")
    double: str = Field(default="double", border="double", height=3, align="center")
    thick: str = Field(default="thick", border="thick", height=3, align="center")
    inside: str = Field(default="quadrant_inside", border="quadrant_inside", height=3, align="center")
    outside: str = Field(default="quadrant_outside", border="quadrant_outside", height=3, align="center")

Terminal(width=42, height=18).render(Borders())
```

??? example "Border Styles"
    - `border`: [Border](../api/xnano/_types.md#xnano._types.Border){data-preview} or `None`.
    - Values: `"plain"`, `"rounded"`, `"double"`, `"thick"`, `"quadrant_inside"`, `"quadrant_outside"`.

## Border Sides, Title, and Position

`border_sides` accepts any combination of `top`, `right`, `bottom`, and
`left`. `title` is optional and `title_position` is `top`, `bottom`, or `None`.

```pyodide install="xnano>=1.0.10" height="23"
from xnano import BaseGrid, Field, Terminal

class FrameDetails(BaseGrid, direction="horizontal", gap=2, padding=1):
    top_left: str = Field(
        default="top + left",
        border="plain",
        border_sides=("top", "left"),
        border_color="cyan-400",
        title="top title",
        title_position="top",
        padding=1,
    )
    bottom_right: str = Field(
        default="bottom + right",
        border="double",
        border_sides=("bottom", "right"),
        border_color="amber-400",
        title="bottom title",
        title_position="bottom",
        padding=1,
    )

Terminal(width=68, height=9).render(FrameDetails())
```

??? example "Border Sides, Title, and Position"
    - `border_sides`: a sequence of [Side](../api/xnano/_types.md#xnano._types.Side){data-preview} values (`"top"`, `"right"`, `"bottom"`, `"left"`) or `None`.
    - `title`: `str | None`.
    - `title_position`: [FrameTitlePosition](../api/xnano/_types.md#xnano._types.FrameTitlePosition){data-preview} (`"top"` or `"bottom"`) or `None`.

## Tailwind `class_name`

`Field(class_name=...)` accepts a space-separated string or sequence. The web
host preserves every token; the terminal lowers the following groups:

| Group | Terminal-supported forms |
|---|---|
| Color | `text-{color}`, `bg-{color}`, `border-{color}` |
| Spacing | `p`, `px`, `py`, `pt`, `pr`, `pb`, `pl`; matching `m*`; `gap`, `gap-x`, `gap-y` |
| Border | `border`, `border-0`, `border-2/4/8`, `border-double`, `border-t/r/b/l/x/y`, every `rounded*` |
| Type | bold/light font weights, `italic`, `underline`, `animate-pulse`, `text-left/center/right` |
| Size | `w-*`, `h-*` with spacing values, fractions, `full`, `screen`, `fit`, `auto`, `min`, `max` |
| Flex | `flex`, `flex-row`, `flex-col`, `flex-1/auto/initial/none`, `grow`, `grow-0`, `shrink`, `shrink-0` |

Spacing/size suffixes are `0`, `0.5`, `1`, `1.5`, `2`, `2.5`, `3`, `3.5`,
`4`, `5`, `6`, `7`, `8`, `9`, `10`, `11`, `12`, `14`, `16`, `20`, `24`,
`28`, `32`, `36`, `40`, `44`, `48`, `52`, `56`, `60`, `64`, `72`, `80`,
`96`, and `px`.

```pyodide install="xnano>=1.0.10" height="22"
from xnano import BaseGrid, Field, Terminal

class TailwindDemo(BaseGrid, direction="vertical", gap=1):
    card: str = Field(
        default="Tailwind lowered to terminal cells",
        class_name=(
            "text-cyan-200 bg-slate-900 border-cyan-500 rounded-xl "
            "px-6 py-4 font-bold italic text-center w-full"
        ),
    )
    partial: str = Field(
        default="selected border sides + margin",
        class_name="border-double border-x border-amber-400 mx-4 p-2",
    )

Terminal(width=62, height=10).render(TailwindDemo())
```

Explicit [`Field`](../api/xnano/fields.md#xnano.fields.Field){data-preview}
keywords win over class-derived values. Unknown or web-only tokens remain in
[`Style.passthrough_classes`](../api/xnano/_styles.md#xnano._styles.Style.passthrough_classes){data-preview}
and are ignored by the terminal.

```pyodide install="xnano>=1.0.10" height="18"
from xnano import Field

field = Field(
    "explicit wins",
    class_name="text-red-500 bg-slate-900 rounded-lg cursor-pointer text-xl",
    color="green-300",
    border="double",
)
style = field.get_style()
print("color:", style.color)
print("border:", style.border)
print("original classes:", style.classes)
print("web-only passthrough:", style.passthrough_classes)
```

??? example "Tailwind `class_name`"
    - `class_name`: [ClassNameLike](../api/xnano/fields.md#xnano.fields.ClassNameLike){data-preview}.
    - Recognized literals: [TailwindClass](../api/xnano/_styles.md#xnano._styles.TailwindClass){data-preview}.
    - Groups: [ColorClassGroup](../api/xnano/_styles.md#xnano._styles.ColorClassGroup){data-preview}, [SpacingClassGroup](../api/xnano/_styles.md#xnano._styles.SpacingClassGroup){data-preview}, [BorderClassGroup](../api/xnano/_styles.md#xnano._styles.BorderClassGroup){data-preview}, [TypographyClassGroup](../api/xnano/_styles.md#xnano._styles.TypographyClassGroup){data-preview}, [SizingClassGroup](../api/xnano/_styles.md#xnano._styles.SizingClassGroup){data-preview}, [FlexClassGroup](../api/xnano/_styles.md#xnano._styles.FlexClassGroup){data-preview}.
