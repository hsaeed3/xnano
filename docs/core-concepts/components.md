---
title: "Components"
icon: "lucide/package"
---

# Components

A component is a piece of pre-built, ready-to-use content — a progress bar, a table, a chart — that behaves like any other value you'd hand to a `Field`.

You've been styling plain strings for every example so far. A component is what you reach for once a string isn't enough to represent what you're showing.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: a Field slot can hold a plain string or a component value such as Progress">
<svg viewBox="0 0 720 210" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="ccd-cell" width="12" height="12" patternUnits="userSpaceOnUse">
      <path d="M 12 0 L 0 0 0 12" class="gcd-grid-line" />
    </pattern>
  </defs>

  <!-- Left: string value -->
  <g transform="translate(48, 36)">
    <rect class="gcd-window" x="0" y="0" width="280" height="140" rx="12" />
    <rect class="gcd-chrome" x="0" y="0" width="280" height="26" rx="12" />
    <rect class="gcd-chrome" x="0" y="14" width="280" height="12" />
    <text class="gcd-chrome-label" x="140" y="17" text-anchor="middle">Field value = str</text>
    <rect class="gcd-grid-fill" x="16" y="42" width="248" height="80" rx="6" />
    <rect x="16" y="42" width="248" height="80" rx="6" fill="url(#ccd-cell)" />
    <rect class="gcd-cell-highlight" x="32" y="58" width="216" height="48" rx="4" />
    <text class="gcd-z-label gcd-z-label-on" x="140" y="86" text-anchor="middle">"Downloading…"</text>
  </g>

  <!-- Right: component value -->
  <g transform="translate(392, 36)">
    <rect class="gcd-window" x="0" y="0" width="280" height="140" rx="12" />
    <rect class="gcd-chrome" x="0" y="0" width="280" height="26" rx="12" />
    <rect class="gcd-chrome" x="0" y="14" width="280" height="12" />
    <text class="gcd-chrome-label" x="140" y="17" text-anchor="middle">Field value = Progress</text>
    <rect class="gcd-grid-fill" x="16" y="42" width="248" height="80" rx="6" />
    <rect x="16" y="42" width="248" height="80" rx="6" fill="url(#ccd-cell)" />
    <rect class="gcd-cell-highlight-strong" x="32" y="72" width="140" height="16" rx="3" />
    <rect class="gcd-z-base" x="172" y="72" width="76" height="16" rx="3" />
    <text class="gcd-z-label gcd-z-label-on" x="140" y="112" text-anchor="middle">40%</text>
  </g>
</svg>
</div>

```python title="Using a Component" hl_lines="2 6"
from xnano import BaseGrid, Field
from xnano.components.progress import Progress

class Download(BaseGrid, direction="vertical"):
    status: str = Field(default="Downloading…", height=1)
    bar: Progress = Field(default_factory=lambda: Progress(value=0.4)) # (1)!
```

1. `Progress` is a component like any other — assign it as a field's default (or `default_factory`, since it's not a plain immutable value) the same way you would a string.

<div class="xnano-demo" markdown>
![component progress dark](../assets/concepts/component_progress-dark.gif){.demo-dark}
![component progress light](../assets/concepts/component_progress-light.gif){.demo-light}
</div>

<br/>

xnano ships a handful of built-in components — `Text`, `Table`, `Progress`, `Chart`, `Sparkline`, and `Schema` — each covered in its own page in the [Components]{data-preview} section.

You can also write your own. A component is just a small, well-defined contract to implement — covered in full, with a working example, at the start of that same section.

??? abstract "Sandbox & API"

    **Sandbox**

    [Component Gallery](../sandbox.md#live-examples){data-preview}

    **API**

    [`AbstractComponent`](../api/xnano/components/abstract.md#xnano.components.abstract.AbstractComponent){data-preview} · [`ComponentRenderContext`](../api/xnano/components/abstract.md#xnano.components.abstract.ComponentRenderContext){data-preview}

[Components]: ../components/index.md
