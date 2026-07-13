---
title: "xnano-core"
icon: "lucide/cpu"
---

# xnano-core

Grids, fields, hooks, and components are implemented in Python. They do
not access the terminal directly. `xnano-core` provides the Rust runtime
that owns the terminal session, processes terminal events, and renders
the output described by Python.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: Python owns grids and fields; a single IR crossing into xnano-core handles session, paint, and events">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="xcd-cell" width="12" height="12" patternUnits="userSpaceOnUse">
      <path d="M 12 0 L 0 0 0 12" class="gcd-grid-line" />
    </pattern>
    <marker id="xcd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <!-- Python -->
  <rect class="gcd-panel" x="28" y="28" width="280" height="224" rx="16" />
  <text class="gcd-label" x="168" y="56" text-anchor="middle">python · xnano</text>

  <rect class="gcd-window" x="56" y="80" width="224" height="40" rx="8" />
  <text class="gcd-chrome-label" x="168" y="104" text-anchor="middle">BaseGrid · Field · hooks</text>

  <rect class="gcd-window" x="56" y="136" width="224" height="40" rx="8" />
  <text class="gcd-chrome-label" x="168" y="160" text-anchor="middle">components · Content</text>

  <rect class="gcd-window" x="56" y="192" width="224" height="40" rx="8" />
  <text class="gcd-chrome-label" x="168" y="216" text-anchor="middle">controllers · nodes</text>

  <!-- Crossing -->
  <line class="gcd-arrow" x1="308" y1="140" x2="380" y2="140" marker-end="url(#xcd-arrow)" />
  <text class="gcd-z-caption gcd-z-caption-on" x="344" y="126" text-anchor="middle">IR</text>
  <text class="gcd-z-caption" x="344" y="160" text-anchor="middle">once / frame</text>

  <!-- Rust -->
  <rect class="gcd-panel gcd-panel-accent" x="392" y="28" width="300" height="224" rx="16" />
  <text class="gcd-label gcd-label-accent" x="542" y="56" text-anchor="middle">rust · xnano-core</text>

  <rect class="gcd-window" x="420" y="80" width="244" height="40" rx="8" />
  <text class="gcd-chrome-label" x="542" y="104" text-anchor="middle">CoreSession</text>

  <rect class="gcd-window" x="420" y="136" width="244" height="40" rx="8" />
  <text class="gcd-chrome-label" x="542" y="160" text-anchor="middle">ratatui · tachyonfx</text>

  <g transform="translate(420, 192)">
    <rect class="gcd-window" x="0" y="0" width="244" height="40" rx="8" />
    <rect class="gcd-grid-fill" x="12" y="10" width="220" height="20" rx="3" />
    <rect x="12" y="10" width="220" height="20" rx="3" fill="url(#xcd-cell)" />
  </g>
</svg>
</div>

## Why Rust

A terminal interface may redraw after every input event or clock tick.
Buffer updates, cell diffs, and terminal I/O all run frequently, so xnano
keeps that work in Rust. `CoreSession` manages the live terminal and render
cycle, [ratatui](https://ratatui.rs) updates and diffs the buffer, and
[tachyonfx](https://github.com/ratatui/tachyonfx) runs terminal effects.
The normal render path crosses from Python into Rust once per frame. See
[Render Nodes & IR]{data-preview} for the details of that boundary.

## Scope

`xnano-core` does not define `BaseGrid`, `Field`, hooks, or components. Its
API deals with sessions, render nodes, key bindings, terminal events, and
other runtime primitives.

This boundary keeps application-facing APIs in Python and moves terminal
lifecycle and rendering work into Rust. [Interfaces & Hosts]{data-preview}
describes the Python contracts that sit above the runtime.

## Direct installation

Applications normally install and import `xnano`, which includes
`xnano-core` as a dependency. The package is published separately so the
native extension and the WASM/Pyodide build can be distributed
independently. The WASM build uses buffer-backed sessions and does not
open a live terminal.

```bash
pip install xnano-core
```

The [xnano-core]{data-preview} API reference documents `CoreSession`,
`CoreRenderNode`, `CoreKeyBinding`, and the rest of the public runtime API.

[Render Nodes & IR]: render-nodes.md
[Interfaces & Hosts]: hosts-and-controllers.md
[xnano-core]: ../api/xnano-core/xnano-core.md
