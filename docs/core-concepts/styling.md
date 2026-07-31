---
title: "Colors & Styling"
icon: "lucide/palette"
---

# Colors & Styling

Color, border, padding, and modifiers use one vocabulary on
[Field](fields.md){data-preview}, [GridSettings](grids.md){data-preview}, and
components.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: Field, GridSettings, and components share one Style vocabulary">
<svg viewBox="0 0 720 200" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="scd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="40" y="48" width="140" height="64" rx="12" />
  <text class="gcd-label" x="110" y="86" text-anchor="middle">Field</text>

  <rect class="gcd-panel" x="210" y="48" width="160" height="64" rx="12" />
  <text class="gcd-label" x="290" y="86" text-anchor="middle">GridSettings</text>

  <rect class="gcd-panel" x="400" y="48" width="160" height="64" rx="12" />
  <text class="gcd-label" x="480" y="86" text-anchor="middle">components</text>

  <line class="gcd-arrow" x1="110" y1="112" x2="110" y2="140" marker-end="url(#scd-arrow)" />
  <line class="gcd-arrow" x1="290" y1="112" x2="290" y2="140" marker-end="url(#scd-arrow)" />
  <line class="gcd-arrow" x1="480" y1="112" x2="480" y2="140" marker-end="url(#scd-arrow)" />

  <path class="gcd-arrow" d="M110 148 H 580" fill="none" />
  <rect class="gcd-panel gcd-panel-accent" x="200" y="148" width="320" height="40" rx="10" />
  <text class="gcd-label gcd-label-accent" x="360" y="174" text-anchor="middle">Style · color · border · modifiers</text>
</svg>
</div>

## Color

A color can be a name, a hex string, an RGB tuple, or a Tailwind shade.

```python title="Color Inputs"
Field(foreground="violet")
Field(foreground="#a78bfa")
Field(foreground=(167, 139, 250))
Field(foreground="violet-400")
```

`foreground` sets text color; `background` fills the slot (by default when a
background is set). `color=` is a deprecated alias for `foreground`.

Tailwind shades cover the default palette (`slate`, `violet`, `emerald`, …) at
weights `50`–`950`.

<interactive />

??? tip "Try editing the code!"

    - Change any `background=` value.
    - Change a `foreground=` value.

```pyodide install="xnano>=1.2.3b2" height="8"
from xnano import render
from xnano.components.text import Text

render(
    Text(" violet ", background="violet-500", foreground="white"),
    Text("  hex   ", background="#0ea5e9", foreground="black"),
    Text("  rgb   ", background=(244, 63, 94), foreground="white"),
    gap=1,
)
```

## Borders and modifiers

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: a rounded border around bold text">
<svg viewBox="0 0 320 90" xmlns="http://www.w3.org/2000/svg" fill="none">
  <rect class="gcd-window" x="48" y="16" width="224" height="58" rx="14" />
  <rect class="gcd-cell-highlight-strong" x="64" y="30" width="192" height="30" rx="6" />
  <text class="gcd-z-label gcd-z-label-on" x="160" y="50" text-anchor="middle">border · bold</text>
</svg>
</div>

```python title="Borders and Modifiers"
Field(
    border="rounded",
    modifiers=["bold", "italic"],
)
```

Border styles include `"plain"`, `"rounded"`, `"double"`, `"thick"`,
`"quadrant_inside"`, and `"quadrant_outside"`. Modifiers include `"bold"`,
`"dim"`, `"italic"`, `"underline"`, `"slow_blink"`, `"rapid_blink"`, and
`"reversed"`.

<interactive />

??? tip "Try editing the code!"

    - Change `border` on the field.
    - Change `modifiers` (e.g. add `"underline"`).

```pyodide install="xnano>=1.2.3b2" height="6"
from xnano import BaseGrid, Field, render

class Card(BaseGrid):
    label: str = Field(
        default="styled",
        border="rounded",
        modifiers=["bold"],
        foreground="violet-400",
        padding=1,
    )

render(Card())
```

## Tailwind classes (_experimental_)

Anywhere a field accepts `class_name`, you can use a utility string instead of
individual keywords:

```python title="Tailwind Classes"
Field(class_name="text-violet-400 bg-slate-900 p-2 rounded-lg")
```

Cell-level classes (color, padding, margin, border) lower into the same style
as keyword arguments. Utilities without a cell equivalent (`flex-*`, `shadow-*`,
`transition-*`, …) are ignored by the layout pipeline.

Keyword arguments and `class_name` resolve to the same [Style]{data-preview}.
Use keywords when a value is computed; use `class_name` when you already have a
utility string.

??? abstract "API"

    [`Style`](../api/xnano/tailwind.md){data-preview} ·
    [`ColorLike`](../api/xnano/colors.md){data-preview} ·
    [`Field`](../api/xnano/fields.md){data-preview}

[Style]: ../api/xnano/tailwind.md
