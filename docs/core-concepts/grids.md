---
title: "Grids & Layout"
icon: "lucide/grid"
---

# Grids & Layout

Whether the host is a terminal or a browser, layout in [xnano]{data-preview} is
a 2D grid of cells.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: terminal and browser hosts become the same surfaces with a grid overlay">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="gcd-cell-grid" width="14" height="14" patternUnits="userSpaceOnUse">
      <path d="M 14 0 L 0 0 0 14" class="gcd-grid-line" />
    </pattern>
    <marker id="gcd-arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="16" y="28" width="280" height="244" rx="16" />
  <text class="gcd-label" x="156" y="54" text-anchor="middle">hosts</text>

  <g transform="translate(40, 70)">
    <rect class="gcd-window" x="0" y="0" width="232" height="88" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="232" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="232" height="10" />
    <circle class="gcd-dot" cx="14" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="11" r="3.5" />
    <text class="gcd-chrome-label" x="116" y="15" text-anchor="middle">terminal</text>
    <path class="gcd-line" d="M16 38 h48" stroke-width="3" stroke-linecap="round" />
    <path class="gcd-line-soft" d="M16 52 h96" stroke-width="3" stroke-linecap="round" />
    <path class="gcd-line-soft" d="M16 66 h72" stroke-width="3" stroke-linecap="round" />
  </g>

  <g transform="translate(40, 172)">
    <rect class="gcd-window" x="0" y="0" width="232" height="80" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="232" height="28" rx="10" />
    <rect class="gcd-chrome" x="0" y="18" width="232" height="10" />
    <circle class="gcd-dot" cx="14" cy="14" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="14" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="14" r="3.5" />
    <rect class="gcd-urlbar" x="54" y="8" width="160" height="12" rx="6" />
    <text class="gcd-chrome-label" x="134" y="17" text-anchor="middle">browser</text>
    <path class="gcd-line" d="M16 46 h80" stroke-width="3" stroke-linecap="round" />
    <path class="gcd-line-soft" d="M16 60 h120" stroke-width="3" stroke-linecap="round" />
  </g>

  <line class="gcd-arrow" x1="320" y1="150" x2="392" y2="150" marker-end="url(#gcd-arrowhead)" />

  <rect class="gcd-panel gcd-panel-accent" x="424" y="28" width="280" height="244" rx="16" />
  <text class="gcd-label gcd-label-accent" x="564" y="54" text-anchor="middle">grid</text>

  <g transform="translate(448, 70)">
    <rect class="gcd-window" x="0" y="0" width="232" height="88" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="232" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="232" height="10" />
    <circle class="gcd-dot" cx="14" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="11" r="3.5" />
    <text class="gcd-chrome-label" x="116" y="15" text-anchor="middle">terminal</text>
    <rect class="gcd-grid-fill" x="8" y="28" width="216" height="52" rx="6" />
    <rect x="8" y="28" width="216" height="52" rx="6" fill="url(#gcd-cell-grid)" />
  </g>

  <g transform="translate(448, 172)">
    <rect class="gcd-window" x="0" y="0" width="232" height="80" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="232" height="28" rx="10" />
    <rect class="gcd-chrome" x="0" y="18" width="232" height="10" />
    <circle class="gcd-dot" cx="14" cy="14" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="14" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="14" r="3.5" />
    <rect class="gcd-urlbar" x="54" y="8" width="160" height="12" rx="6" />
    <text class="gcd-chrome-label" x="134" y="17" text-anchor="middle">browser</text>
    <rect class="gcd-grid-fill" x="8" y="34" width="216" height="38" rx="6" />
    <rect x="8" y="34" width="216" height="38" rx="6" fill="url(#gcd-cell-grid)" />
  </g>
</svg>
</div>

A [BaseGrid]{data-preview} is a resizable, focusable, rectangular region. Fields
on the grid mark smaller regions that can:

- Render content <small>(text, components, nested grids)</small>
- Hold typed state <small>(including `state=True` fields that never paint)</small>
- Handle input through `@on_*` hooks

<div class="grid-concept-diagram" role="img" aria-label="Diagram: a terminal grid with a smaller focused region of cells highlighted">
<svg viewBox="0 0 720 264" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="gcd-cell-grid-lg" width="18" height="18" patternUnits="userSpaceOnUse">
      <path d="M 18 0 L 0 0 0 18" class="gcd-grid-line" />
    </pattern>
    <pattern id="gcd-focus-stripes" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="8" height="8" class="gcd-stripe-bg" />
      <rect width="3.5" height="8" class="gcd-stripe-fg" />
    </pattern>
    <clipPath id="gcd-term-clip">
      <rect x="40" y="72" width="640" height="152" rx="8" />
    </clipPath>
  </defs>

  <rect class="gcd-window" x="24" y="28" width="672" height="208" rx="16" />
  <rect class="gcd-chrome" x="24" y="28" width="672" height="32" rx="16" />
  <rect class="gcd-chrome" x="24" y="44" width="672" height="16" />
  <circle class="gcd-dot" cx="48" cy="44" r="5" />
  <circle class="gcd-dot" cx="66" cy="44" r="5" />
  <circle class="gcd-dot" cx="84" cy="44" r="5" />
  <text class="gcd-chrome-label" x="360" y="49" text-anchor="middle">terminal</text>

  <g clip-path="url(#gcd-term-clip)">
    <rect class="gcd-grid-fill" x="40" y="72" width="640" height="152" />
    <rect x="40" y="72" width="640" height="152" fill="url(#gcd-cell-grid-lg)" />
    <rect class="gcd-cell-highlight" x="76" y="90" width="126" height="72" rx="3" />
    <rect class="gcd-cell-focus" x="94" y="108" width="54" height="36" rx="2" fill="url(#gcd-focus-stripes)" />
    <rect class="gcd-cell-focus-ring" x="94" y="108" width="54" height="36" rx="2" />
  </g>
</svg>
</div>

??? abstract "The `z` axis"

    Along with x and y, fields and grids accept a `z` value. For each cell, the
    highest `z` wins. Use it for overlays and stacked panels.

    <div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: lower z selection is not rendered; higher z overlay is rendered">
    <svg viewBox="0 0 460 220" xmlns="http://www.w3.org/2000/svg" fill="none">
      <defs>
        <pattern id="gcd-z-cell-grid" width="14" height="14" patternUnits="userSpaceOnUse">
          <path d="M 14 0 L 0 0 0 14" class="gcd-grid-line" />
        </pattern>
        <filter id="gcd-z-soft-shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="3" stdDeviation="3.5" flood-opacity="0.28" />
        </filter>
      </defs>
      <g transform="translate(24, 48)">
        <rect class="gcd-window" x="0" y="0" width="300" height="148" rx="12" />
        <rect class="gcd-chrome" x="0" y="0" width="300" height="24" rx="12" />
        <rect class="gcd-chrome" x="0" y="14" width="300" height="10" />
        <circle class="gcd-dot" cx="14" cy="12" r="3.5" />
        <circle class="gcd-dot" cx="26" cy="12" r="3.5" />
        <circle class="gcd-dot" cx="38" cy="12" r="3.5" />
        <text class="gcd-chrome-label" x="150" y="16" text-anchor="middle">terminal</text>
        <rect class="gcd-grid-fill" x="10" y="32" width="280" height="106" rx="6" />
        <rect x="10" y="32" width="280" height="106" rx="6" fill="url(#gcd-z-cell-grid)" />
        <rect class="gcd-z-base" x="28" y="48" width="96" height="54" rx="3" />
        <text class="gcd-z-label gcd-z-label-muted" x="76" y="79" text-anchor="middle">z = 0</text>
        <text class="gcd-z-caption gcd-z-caption-muted" x="134" y="78">this isn't rendered</text>
        <path class="gcd-z-connector" d="M28 48 L52 18" />
        <path class="gcd-z-connector" d="M124 48 L148 18" />
        <path class="gcd-z-connector" d="M28 102 L52 72" />
        <path class="gcd-z-connector" d="M124 102 L148 72" />
      </g>
      <g transform="translate(48, 18)" filter="url(#gcd-z-soft-shadow)">
        <rect class="gcd-z-overlay" x="0" y="0" width="96" height="54" rx="3" />
        <rect class="gcd-z-overlay-inner" x="6" y="6" width="84" height="42" rx="2" />
        <text class="gcd-z-label gcd-z-label-on" x="48" y="32" text-anchor="middle">z = 1</text>
        <text class="gcd-z-caption gcd-z-caption-on" x="106" y="32">this is rendered</text>
      </g>
    </svg>
    </div>

## Creating a Grid

`BaseGrid` is declared like a Pydantic model: subclass it and annotate slots
with [`Field`](fields.md){data-preview}.

<interactive />

??? tip "Try editing the code!"

    - Change `direction` between `"vertical"` and `"horizontal"`.
    - Change the `title` field's `default=`.

```pyodide install="xnano>=1.2.3" height="8"
from xnano import BaseGrid, Field, render

class App(BaseGrid, direction="vertical"):
    title: str = Field(default="My App", border="rounded")
    body: str = Field(default="Hello")
    name: str = Field(default="Hammad", state=True)

render(App())
```

```python title="Creating a Grid" hl_lines="4 5 6 7"
from xnano import BaseGrid, Field

class App(BaseGrid, direction="vertical"): # (1)!
    title: str = Field(default="My App", border="rounded") # (2)!
    body: str = Field(default="Hello")
    name: str = Field(default="Hammad", state=True) # (3)!
```

1. Grid settings go on the class header (`direction`, `gap`, `border`, …) or on
   a `grid_settings` attribute.
2. `Field(...)` sizes and styles the slot, and holds the value.
3. `state=True` keeps the value off the paint path.

## Grid Settings

Settings that apply to the whole grid — layout direction, gap, outer frame —
are separate from individual fields.

<interactive />

??? tip "Try editing the code!"

    - Change `gap` (e.g. `0` or `2`).
    - Change `direction` to `"vertical"`.

```pyodide install="xnano>=1.2.3" height="7"
from xnano import BaseGrid, Field, render

class Dashboard(BaseGrid, direction="horizontal", gap=1, border="rounded", title=" Dashboard "):
    left: str = Field(default="Left", width="1fr")
    right: str = Field(default="Right", width="1fr")

render(Dashboard())
```

```python title="Grid Settings" hl_lines="3"
from xnano import BaseGrid, Field

class Dashboard(BaseGrid, direction="horizontal", gap=1, border="rounded", title=" Dashboard "): # (1)!
    left: str = Field(default="Left", width="1fr")
    right: str = Field(default="Right", width="1fr")
```

1. Everything after `BaseGrid` in the class header is a grid setting.

The same settings can be declared on `grid_settings`:

=== "Class header"

    ```python
    class Dashboard(BaseGrid, direction="horizontal", gap=1, border="rounded"):
        ...
    ```

=== "`grid_settings` attribute"

    ```python
    from xnano import BaseGrid, GridSettings

    class Dashboard(BaseGrid):
        grid_settings = GridSettings(
            direction="horizontal",
            gap=1,
            border="rounded",
        )
        ...
    ```

Both forms merge if used together; a subclass's `grid_settings` wins over
inherited class-header values.

`direction` and `gap` are the common ones. Color, borders, padding, title, and
modifiers use the same vocabulary as [Field](fields.md){data-preview}, applied
to the grid's outer frame. See [GridSettings]{data-preview}.

## Nested Grids

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: parent grid holds nested child grids as fields">
<svg viewBox="0 0 400 120" xmlns="http://www.w3.org/2000/svg" fill="none">
  <rect class="gcd-window" x="24" y="12" width="352" height="96" rx="10" />
  <text class="gcd-chrome-label" x="200" y="30" text-anchor="middle">App</text>
  <rect class="gcd-cell-highlight-strong" x="40" y="40" width="100" height="52" rx="6" />
  <text class="gcd-z-label gcd-z-label-on" x="90" y="70" text-anchor="middle">sidebar</text>
  <rect class="gcd-panel" x="156" y="40" width="200" height="52" rx="6" />
  <text class="gcd-chrome-label" x="256" y="70" text-anchor="middle">content</text>
</svg>
</div>

A field value can be another `BaseGrid`. Nested grids are ordinary content.

```python title="Nested Grids"
from xnano import BaseGrid, Field

class Sidebar(BaseGrid, direction="vertical"):
    home: str = Field(default="Home", height=1)
    search: str = Field(default="Search", height=1)

class App(BaseGrid, direction="horizontal"):
    sidebar: Sidebar = Field(default_factory=Sidebar, width="1/3")
    content: str = Field(default="…", width="2fr")
```

`overlay=True` on a field takes that field out of flow and centers it over the
grid (with `z` for stacking). See [Getting Started](../getting-started.md) for a
full popup example.

Useful grid methods:

| Method | Role |
|--------|------|
| `grid_render` / `grid_render_*` | Refresh fields each frame (or per size tier) |
| `grid_set_field(name, ...)` | Mutate a field value or layout metadata at runtime |
| `grid_effect(...)` | Animate field areas — [Effects](effects.md) |

## Displaying Content

Grids do not know which host will run them. The same instance (or class) can go
to a [Terminal](terminal.md){data-preview} or a [Web](web.md){data-preview} host.

### Terminal

=== "`render()`"

    ```python title="render()"
    from xnano import render

    render(App()) # (1)!
    ```

    1. One-shot paint, similar to `print` with layout and style.

=== "`Terminal`"

    ```python title="Terminal"
    from xnano import Terminal

    Terminal().run(App()) # (1)!
    ```

    1. Live session: frames and events until exit.

### Web

```python title="Web"
from xnano import Web

Web().run(App(), port=8000)
```

HTTP request hooks on grids are a separate surface — see
[Requests](requests.md).

??? abstract "API"

    [`BaseGrid`](../api/xnano/grids.md){data-preview} ·
    [`GridSettings`](../api/xnano/grids.md){data-preview} ·
    [`Field`](../api/xnano/fields.md){data-preview} ·
    [`Terminal`](../api/xnano/terminal.md){data-preview} ·
    [`Web`](../api/xnano/web.md){data-preview}

[BaseGrid]: ../api/xnano/grids.md
[GridSettings]: ../api/xnano/grids.md
[Field]: fields.md
