---
title: "Live Sandbox"
icon: "lucide/toy-brick"
---

# Live Sandbox

Edit and run real xnano programs without leaving the docs. Every editor on
these pages runs client-side through Pyodide and xnano's WebAssembly build; the
first run downloads the runtime, and later runs use the browser cache.

```pyodide install="xnano>=1.0.10" height="6"
import xnano

xnano.render("hello, sandbox!", color="violet-400", modifiers=("bold",))
```

Click **Run** or press ++ctrl+enter++. Editors on the same page may share a
named session, but a reload—or moving to another page—starts a fresh session.

!!! info "What works in the browser"

    [`xnano.render(...)`](api/xnano/_renderable.md#xnano._renderable.render){data-preview},
    [`Terminal.render(...)`](api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal.render){data-preview},
    [`Terminal.offscreen(...)`](api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal.offscreen){data-preview},
    grids, styling, components, and synthetic
    [`Action`](api/xnano/core/actions.md#xnano.core.actions.Action){data-preview}
    dispatch all use the real buffer-backed renderer.
    [`Terminal.run()`](api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal.run){data-preview}
    deliberately raises on WASM because a browser code cell cannot own a
    live OS terminal or its event polling loop.

## Live Examples

<div class="grid cards" markdown>

-   :material-console-line:{ .lg .middle } **Rendering**

    ---

    Every [`render()`](api/xnano/_renderable.md#xnano._renderable.render){data-preview} and
    [`Terminal.render()`](api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal.render){data-preview}
    option, print-compatible output,
    streams, viewport sizing, offscreen buffers, and action-driven frames.

    [Open rendering](sandbox/rendering.md)

-   :material-view-grid-outline:{ .lg .middle } **Layout & Fields**

    ---

    Grid direction, gaps, all sizing forms, alignment, nesting, visibility,
    padding, margin, frames, and field layout metadata.

    [Open layout](sandbox/layout.md)

-   :material-palette-outline:{ .lg .middle } **Styling**

    ---

    Every color input, character modifier, border style and side, titles, and
    the terminal-supported Tailwind utility groups.

    [Open styling](sandbox/styling.md)

-   :material-format-text:{ .lg .middle } **Text**

    ---

    Leaf text, styled spans, paragraphs, wrapping, alignment, placeholders,
    editable input state, visibility, stacking, and intrinsic sizing.

    [Open Text](sandbox/text.md)

-   :material-table:{ .lg .middle } **Table & Column**

    ---

    Every table option and every
    [`Column`](api/xnano/components/schema.md#xnano.components.schema.Column){data-preview}
    descriptor option, with inferred, overridden, and declarative schemas.

    [Open Table](sandbox/table.md)

-   :material-progress-clock:{ .lg .middle } **Progress**

    ---

    Ratios, totals, automatic/custom/hidden labels, both gauge styles, and all
    filled, unfilled, foreground, and background color controls.

    [Open Progress](sandbox/progress.md)

-   :material-chart-line:{ .lg .middle } **Chart & Series**

    ---

    Line, scatter, and bar datasets; automatic and explicit bounds; labels;
    palettes; legends in every position; and declarative series overrides.

    [Open Chart](sandbox/chart.md)

-   :material-chart-timeline-variant-shimmer:{ .lg .middle } **Sparkline**

    ---

    Automatic and fixed scales, global and per-bar colors, absent samples,
    custom symbols, backgrounds, visibility, and intrinsic sizing.

    [Open Sparkline](sandbox/sparkline.md)

</div>

## A Useful Editing Pattern

Most examples put the interesting choices at the top. Change a value, rerun
the cell, and compare the frame. For literal options, try each value in the
nearby tuple—Ace supplies Python syntax highlighting, indentation, selection,
search, and multiple cursors, so larger examples remain comfortable to edit.

```pyodide install="xnano>=1.0.10" height="8"
from xnano import render

border = "rounded"  # plain, rounded, double, thick, quadrant_inside, quadrant_outside
render("change me", border=border, title=border, padding=(1, 3))
```

??? example "A Useful Editing Pattern"

    [`Border`](api/xnano/_types.md#xnano._types.Border){data-preview} accepts
    `"plain"`, `"rounded"`, `"double"`, `"thick"`, `"quadrant_inside"`, and
    `"quadrant_outside"`; use `None` when no border should be drawn.
