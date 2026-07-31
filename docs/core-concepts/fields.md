---
title: "Fields"
icon: "lucide/list"
---

# Fields

Every attribute declared with `Field()` on a grid does two jobs:

1. Typed data (defaults, validation metadata).
2. A rectangular **slot** on the grid — size, style, and whether it paints.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: a Field splits into typed data and a painted slot on the grid; state=True fields have data but no slot">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="fcd-cell" width="14" height="14" patternUnits="userSpaceOnUse">
      <path d="M 14 0 L 0 0 0 14" class="gcd-grid-line" />
    </pattern>
    <marker id="fcd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel gcd-panel-accent" x="40" y="90" width="160" height="72" rx="12" />
  <text class="gcd-label gcd-label-accent" x="120" y="122" text-anchor="middle">Field()</text>
  <text class="gcd-chrome-label" x="120" y="146" text-anchor="middle">one declaration</text>

  <line class="gcd-arrow" x1="200" y1="126" x2="248" y2="126" marker-end="url(#fcd-arrow)" />

  <circle cx="268" cy="126" r="8" class="gcd-arrow-fill" />
  <line class="gcd-arrow" x1="276" y1="110" x2="330" y2="70" marker-end="url(#fcd-arrow)" />
  <line class="gcd-arrow" x1="276" y1="142" x2="330" y2="182" marker-end="url(#fcd-arrow)" />

  <rect class="gcd-panel" x="340" y="36" width="200" height="72" rx="12" />
  <text class="gcd-label" x="440" y="68" text-anchor="middle">data</text>
  <text class="gcd-chrome-label" x="440" y="90" text-anchor="middle">typed · validated · live</text>

  <rect class="gcd-panel" x="340" y="148" width="200" height="72" rx="12" />
  <text class="gcd-label" x="440" y="180" text-anchor="middle">slot</text>
  <text class="gcd-chrome-label" x="440" y="202" text-anchor="middle">size · style · paint</text>

  <g transform="translate(560, 70)">
    <rect class="gcd-window" x="0" y="0" width="140" height="120" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="140" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="140" height="10" />
    <circle class="gcd-dot" cx="14" cy="11" r="3" />
    <circle class="gcd-dot" cx="26" cy="11" r="3" />
    <circle class="gcd-dot" cx="38" cy="11" r="3" />
    <rect class="gcd-grid-fill" x="10" y="30" width="120" height="80" rx="4" />
    <rect x="10" y="30" width="120" height="80" rx="4" fill="url(#fcd-cell)" />
    <rect class="gcd-cell-highlight-strong" x="18" y="38" width="104" height="28" rx="3" />
    <text class="gcd-chrome-label" x="70" y="56" text-anchor="middle">painted</text>
    <rect class="gcd-z-base" x="18" y="76" width="104" height="24" rx="3" />
    <text class="gcd-z-label gcd-z-label-muted" x="70" y="92" text-anchor="middle">state only</text>
  </g>
</svg>
</div>

A field can set:

- Size — `width` / `height` as cells, percentages, `fr`, or `"fit"`
- Appearance — `foreground`, `background`, `border`, `padding`, `title`, …
- Whether it paints — `state=True` holds data and never claims a slot

## Declaring a Field

```python title="Declaring a Field" hl_lines="4"
from xnano import BaseGrid, Field

class Card(BaseGrid, direction="vertical"):
    heading: str = Field(
        default="Reminder",
        foreground="violet-400",
        border="rounded",
        width="fit",
    ) # (1)!
    body: str = Field(default="Water the plants.") # (2)!
```

1. Defaults and style keywords are arguments to the same `Field()` call.
2. A field with no style keywords still paints — it uses leftover space and the
   grid's plain look.

The full keyword list is on the [Field]{data-preview} API page.

### Runnable Example

<interactive />

??? tip "Try editing the code!"

    - Change `foreground` on `heading` (e.g. `"emerald-400"`).
    - Change `border` to `"double"` or `"plain"`.

```pyodide install="xnano>=1.2.3b2" height="12"
from xnano import BaseGrid, Field, render

class Card(BaseGrid, direction="vertical"):
    heading: str = Field(
        default="Reminder",
        foreground="violet-400",
        border="rounded",
        width="fit",
    )
    body: str = Field(default="Water the plants.")

render(Card())
```

## State Fields

`state=True` marks data that should not render:

```python title="State Field"
count: int = Field(default=0, state=True)
```

Assigning to a state field still schedules a repaint of the grid that owns it.
Shared application state (`Terminal(state=...)` / `Web(state=...)`), focus
`group=`, and keeping painted fields in sync are covered under
[State](state.md).

## Fields vs. Plain Attributes

Not every attribute needs `Field()`. A plain annotation is a normal Python
attribute: typed, live, never painted.

<interactive />

```python title="Fields vs. Plain Attributes" hl_lines="5"
from xnano import BaseGrid, Field

class Card(BaseGrid, direction="vertical"):
    heading: str = Field(default="Reminder")
    tags: list[str] = ["home", "chores"] # (1)!
```

1. `tags` is never given a slot, so it never appears on the grid.

`state=True` still goes through `Field()` metadata and validation. Use a plain
attribute when you do not need that.

### Runnable Example

??? tip "Try editing the code!"

    - Change `heading`'s `default=`.
    - Add another entry to the `tags` list (it still will not paint).

```pyodide install="xnano>=1.2.3b2" height="8"
from xnano import BaseGrid, Field, render

class Card(BaseGrid, direction="vertical"):
    heading: str = Field(default="Reminder")
    # this is a plain attribute, it will not render
    tags: list[str] = ["home", "chores"]

render(Card())
```

## Borders, focus, and overlays

Any painted field can take border chrome without a wrapper grid:

```python
notes: str = Field(
    default="…",
    border="rounded",
    title="Saved Notes",
    padding=1,
)
```

- `group=` names a focus target for `ctx.focus(...)` / `ctx.runtime.focus(...)`
  and click/focus hooks.
- `overlay=True` floats the field over the grid content (centered; use `z` and
  `visible` as needed).
- `width` / `height` accept absolute cells, `"50%"`, `"1fr"`, `"fit"`, and similar
  sizing strings.

See [Getting Started](../getting-started.md) for `group` and overlay popups.

## Refreshing fields each frame

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: each frame grid_render updates field values before layout">
<svg viewBox="0 0 440 90" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="rf-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel" x="16" y="20" width="88" height="50" rx="10" />
  <text class="gcd-chrome-label" x="60" y="50" text-anchor="middle">frame</text>
  <line class="gcd-arrow" x1="104" y1="45" x2="148" y2="45" marker-end="url(#rf-arr)" />
  <rect class="gcd-panel gcd-panel-accent" x="160" y="20" width="120" height="50" rx="10" />
  <text class="gcd-chrome-label" x="220" y="50" text-anchor="middle">grid_render</text>
  <line class="gcd-arrow" x1="280" y1="45" x2="324" y2="45" marker-end="url(#rf-arr)" />
  <rect class="gcd-window" x="336" y="20" width="88" height="50" rx="10" />
  <text class="gcd-chrome-label" x="380" y="50" text-anchor="middle">layout</text>
</svg>
</div>

Override `grid_render` on the grid to sync painted fields from state before
layout:

```python title="grid_render"
from xnano import BaseGrid, Context, Field

class Dashboard(BaseGrid):
    stats: str = Field(default="")

    def grid_render(self, ctx: Context) -> None:
        count = len(ctx.state.saved) if ctx.state is not None else 0
        self.stats = f"{count} notes"
```

Change layout metadata at runtime with `grid_set_field` (not for `state=True`
fields):

```python title="grid_set_field"
self.grid_set_field("editor", visible=True, z=2)
```

Optional responsive hooks (`grid_render_small`, `grid_render_medium`, …) run when
the viewport crosses size tiers — see
[`BaseGrid`](../api/xnano/grids.md){data-preview}.

??? abstract "API"

    [`Field`](../api/xnano/fields.md){data-preview} ·
    [`BaseGrid`](../api/xnano/grids.md){data-preview} ·
    [Styling](styling.md)

[Field]: ../api/xnano/fields.md
