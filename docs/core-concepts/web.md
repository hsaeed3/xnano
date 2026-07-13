---
title: "Web Applications"
icon: "lucide/globe"
---

# Web Applications

!!! warning "Experimental"

    This feature is experimental and is subject to frequent changes.

A [Web]{data-preview} host is the browser counterpart to [Terminal]{data-preview} — instead of owning a terminal window, it owns a live web server, and instead of painting cells to a screen, it serves your app as an actual page over HTTP.

Whatever you hand a `Terminal` to run, you can hand a `Web` host too — the same class, unchanged. It doesn't know or care which host is running it: `Web` just answers keyboard events, clicks, and ticks from a browser tab instead of a terminal window, and paints HTML instead of cells.

That's the idea behind calling rendered content **orthogonal** to its host: the same `App()` you'd hand to a `Terminal` is exactly what you hand to a `Web` host too.

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

  <!-- Shared App -->
  <rect class="gcd-panel gcd-panel-accent" x="260" y="24" width="200" height="72" rx="12" />
  <text class="gcd-label gcd-label-accent" x="360" y="56" text-anchor="middle">App()</text>
  <text class="gcd-chrome-label" x="360" y="78" text-anchor="middle">same grid · same hooks</text>

  <line class="gcd-arrow" x1="300" y1="96" x2="180" y2="140" marker-end="url(#wcd-arrow)" />
  <line class="gcd-arrow" x1="420" y1="96" x2="540" y2="140" marker-end="url(#wcd-arrow)" />

  <!-- Terminal host -->
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

  <!-- Web host -->
  <g transform="translate(432, 148)">
    <rect class="gcd-window" x="0" y="0" width="240" height="88" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="240" height="28" rx="10" />
    <rect class="gcd-chrome" x="0" y="18" width="240" height="10" />
    <circle class="gcd-dot" cx="14" cy="14" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="14" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="14" r="3.5" />
    <rect class="gcd-urlbar" x="54" y="8" width="168" height="12" rx="6" />
    <text class="gcd-chrome-label" x="138" y="17" text-anchor="middle">Web</text>
    <rect class="gcd-grid-fill" x="12" y="40" width="216" height="36" rx="4" />
    <rect x="12" y="40" width="216" height="36" rx="4" fill="url(#wcd-cell)" />
  </g>
</svg>
</div>

## A Minimal Session

Where `Terminal().run(...)` keeps a terminal window alive, `Web().run(...)` starts an actual server process and keeps *that* alive.

```python title="Running a Web App" hl_lines="7"
from xnano import BaseGrid, Field
from xnano.webui import Web

class App(BaseGrid):
    body: str = Field(default="hello, web!")

Web().run(App(), port=8000) # (1)!
```

1. Don't worry about `Field()` and `BaseGrid` yet — [grids]{data-preview} and [fields]{data-preview} cover that in depth. The only new idea here is `Web` itself: the thing that takes this same grid and serves it as a page instead of a terminal frame.

```bash title="Output"
INFO:     Started server process [79107]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Visiting that address renders the grid as HTML, wired up with [HTMX](https://htmx.org/) so that hooks — the same `@on_keyboard`, `@on_click`, and `@on_tick` decorators a terminal app uses — fire from real browser events: a keydown in the page, a click on an element, a poll on an interval.

??? abstract "Web Dependencies"

    `Web` needs no extra dependencies to build its HTML/HTMX layout, but running a real server does — [starlette](https://www.starlette.io/) to route requests and [uvicorn](https://www.uvicorn.org/) to serve them. Both come with the `web` extra:

    ```bash
    pip install "xnano[web]"
    ```

## One Grid, Two Hosts

Because a grid never references `Terminal` or `Web` directly, the exact same class can be handed to either one.

```python title="Same Grid, Either Host"
from xnano import BaseGrid, Field, Terminal
from xnano.webui import Web

class App(BaseGrid):
    body: str = Field(default="hello!")

Terminal().run(App())   # a terminal window
Web().run(App())        # a browser tab
```

Only one of these runs at a time in a given process, but nothing about `App` itself changes between them — the grid, its fields, and its hooks are the host-agnostic part; `Terminal` and `Web` are just two different stages willing to run it.

??? note "Shared vs. Per-Visitor Sessions"

    Passing a `BaseGrid` *instance* to `Web().run(...)` gives every visitor the same live grid — one shared state, seen by everyone connected. Passing the *class* itself instead creates a fresh grid per browser session, the same way each terminal run starts from scratch.

    ```python
    Web().run(Dashboard())   # shared across all visitors
    Web().run(Dashboard)     # a new session per visitor
    ```

## What Doesn't Carry Over

Not everything a terminal session offers has a browser equivalent. A few [device and cursor]{data-preview} controls — raw mode, the alternate screen buffer, moving the caret to a specific cell — only make sense where there's a real terminal underneath, and reduce to harmless no-ops on `Web`. Native effects and some terminal-only sizing behavior are similarly TUI-specific.

None of that affects the core model, though: grids, fields, and hooks all mean the same thing on both hosts.

## Next Steps

With both hosts in view, the rest of `core-concepts` — [grids]{data-preview}, [fields]{data-preview}, [events and hooks]{data-preview}, and [device and cursor]{data-preview} — applies equally whether the app ends up running in a `Terminal` or served with `Web`.

[Terminal]: ../api/xnano/tui/terminal.md
[Web]: ../api/xnano/webui/web.md
[grids]: grids.md
[fields]: fields.md
[events and hooks]: events.md
[device and cursor]: device.md
