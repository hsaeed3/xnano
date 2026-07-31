---
title: "Web"
icon: "lucide/globe"
---

# Web

A [Web]{data-preview} host is the browser counterpart to
[Terminal]{data-preview}. It runs an offscreen runtime, serves a small HTTP
shell, and streams cell frames to the client. Browser key, mouse, and resize
input re-enter the same `@on_*` path a terminal session uses.

There is no separate HTML paint backend. Grids, fields, components, and hooks
are the same objects on both hosts.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: one App grid class handed to either Terminal or Web without changes">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="wcd-cell" width="12" height="12" patternUnits="userSpaceOnUse">
      <path d="M 12 0 L 0 0 0 12" class="gcd-grid-line" />
    </pattern>
    <marker id="wcd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel gcd-panel-accent" x="260" y="24" width="200" height="72" rx="12" />
  <text class="gcd-label gcd-label-accent" x="360" y="56" text-anchor="middle">App()</text>
  <text class="gcd-chrome-label" x="360" y="78" text-anchor="middle">same grid · same hooks</text>

  <line class="gcd-arrow" x1="300" y1="96" x2="180" y2="140" marker-end="url(#wcd-arrow)" />
  <line class="gcd-arrow" x1="420" y1="96" x2="540" y2="140" marker-end="url(#wcd-arrow)" />

  <g transform="translate(48, 148)">
    <rect class="gcd-window" x="0" y="0" width="240" height="88" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="240" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="240" height="10" />
    <circle class="gcd-dot" cx="14" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="11" r="3.5" />
    <text class="gcd-chrome-label" x="120" y="15" text-anchor="middle">Terminal</text>
    <rect class="gcd-grid-fill" x="12" y="32" width="216" height="44" rx="4" />
    <rect x="12" y="32" width="216" height="44" rx="4" fill="url(#wcd-cell)" />
  </g>

  <g transform="translate(432, 148)">
    <rect class="gcd-window" x="0" y="0" width="240" height="88" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="240" height="28" rx="10" />
    <rect class="gcd-chrome" x="0" y="18" width="240" height="10" />
    <circle class="gcd-dot" cx="14" cy="14" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="14" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="14" r="3.5" />
    <rect class="gcd-urlbar" x="54" y="8" width="168" height="12" rx="6" />
    <text class="gcd-chrome-label" x="138" y="17" text-anchor="middle">Web · cells</text>
    <rect class="gcd-grid-fill" x="12" y="40" width="216" height="36" rx="4" />
    <rect x="12" y="40" width="216" height="36" rx="4" fill="url(#wcd-cell)" />
  </g>
</svg>
</div>

## Running a web app

`Web().run(...)` binds a stdlib HTTP server and keeps serving until interrupted.
This needs a normal Python process — not Pyodide.

```python title="Running a Web App" hl_lines="7"
from xnano import BaseGrid, Field, Web

class App(BaseGrid):
    body: str = Field(default="hello, web!")

Web().run(App(), port=8000) # (1)!
```

1. Optional: `host=`, `Web(state=..., width=..., height=..., title=...)`.

```bash title="Output"
xnano web → http://127.0.0.1:8000
```

The default host uses Python's stdlib HTTP server via
[`serve_native`](../api/xnano/server/native.md){data-preview}.

## One grid, two hosts

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: one App class splits to Terminal or Web">
<svg viewBox="0 0 400 120" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="og-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel gcd-panel-accent" x="140" y="12" width="120" height="40" rx="10" />
  <text class="gcd-label gcd-label-accent" x="200" y="38" text-anchor="middle">App()</text>
  <line class="gcd-arrow" x1="170" y1="52" x2="100" y2="78" marker-end="url(#og-arr)" />
  <line class="gcd-arrow" x1="230" y1="52" x2="300" y2="78" marker-end="url(#og-arr)" />
  <rect class="gcd-window" x="40" y="80" width="120" height="32" rx="8" />
  <text class="gcd-chrome-label" x="100" y="100" text-anchor="middle">Terminal</text>
  <rect class="gcd-window" x="240" y="80" width="120" height="32" rx="8" />
  <text class="gcd-chrome-label" x="300" y="100" text-anchor="middle">Web</text>
</svg>
</div>

```python title="Same Grid, Either Host"
from xnano import BaseGrid, Field, Terminal, Web

class App(BaseGrid):
    body: str = Field(default="hello!")

Terminal().run(App())   # terminal session
Web().run(App())        # browser session
```

Only one of these runs at a time in a given process. The grid class does not
change.

??? note "Shared vs. per-visitor grids"

    Passing a `BaseGrid` *instance* reuses that object for every connection.
    Passing the *class* (or a factory) builds a fresh root per visitor.

    ```python
    Web().run(Dashboard())   # shared
    Web().run(Dashboard)     # new instance per visitor
    ```

## Request hooks

HTTP handlers are declared with decorators from [`xnano.requests`](requests.md)
on grid methods. When that grid is served under `Web` (or a request server),
those routes are registered. They are not Terminal APIs — see
[Requests](requests.md).

## What does not carry over

Some [device and cursor](device.md) controls only apply to a real terminal
(raw mode, alternate screen, moving the caret to a cell). On `Web` they are
no-ops. Grids, fields, components, and hooks still mean the same thing.

## Next

- [Requests](requests.md) — `@on_get_request` and related hooks
- [Grids](grids.md) / [Events & Hooks](events.md) — same as terminal

??? abstract "API"

    [`Web`](../api/xnano/web.md){data-preview} ·
    [`serve_native`](../api/xnano/server/native.md){data-preview} ·
    [`xnano.requests`](../api/xnano/requests.md){data-preview} ·
    [`Terminal`](../api/xnano/terminal.md){data-preview}

[Terminal]: ../api/xnano/terminal.md
[Web]: ../api/xnano/web.md
