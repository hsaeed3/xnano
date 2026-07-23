---
title: "Web Applications"
icon: "lucide/globe"
---

# Web Applications

!!! warning "Experimental"

    This feature is experimental and is subject to frequent changes.

A [Web]{data-preview} host is the browser counterpart to
[Terminal]{data-preview} — instead of owning a terminal window, it owns a
dependency-free HTTP server, and instead of painting cells to a local
screen, it streams those same cells to a browser `<canvas>`.

Whatever you hand a `Terminal` to run, you can hand a `Web` host too — the
same class, unchanged. It doesn't know or care which host is running it:
`Web` drives the real offscreen render engine, streams its cells over
Server-Sent Events, and routes browser key, mouse, and resize events back
through the same `@on_*` hook engine the terminal loop uses. There is no
separate HTML renderer — every component looks identical on both hosts
because both paint the same engine output.

That's the idea behind calling rendered content **orthogonal** to its host:
the same `App()` you'd hand to a `Terminal` is exactly what you hand to a
`Web` host too.

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
    <text class="gcd-chrome-label" x="138" y="17" text-anchor="middle">Web · canvas</text>
    <rect class="gcd-grid-fill" x="12" y="40" width="216" height="36" rx="4" />
    <rect x="12" y="40" width="216" height="36" rx="4" fill="url(#wcd-cell)" />
  </g>
</svg>
</div>

## A Minimal Session

Where `Terminal().run(...)` keeps a terminal window alive, `Web().run(...)`
starts a native stdlib HTTP server and keeps *that* alive.

```python title="Running a Web App" hl_lines="7"
from xnano import BaseGrid, Field
from xnano.web import Web

class App(BaseGrid):
    body: str = Field(default="hello, web!")

Web().run(App(), port=8000) # (1)!
```

1. Don't worry about `Field()` and `BaseGrid` yet — [grids]{data-preview}
   and [fields]{data-preview} cover that in depth. The only new idea here
   is `Web` itself: the thing that takes this same grid and streams its
   cells to a browser canvas instead of a terminal frame.

```bash title="Output"
xnano web → http://127.0.0.1:8000
```

Visiting that address loads a thin shell page with a full-window
`<canvas>` and a small painter script. The server renders the grid through
an offscreen `Terminal`, packs each frame as terminal cells (row-diffed
over the wire), and pushes frames over an SSE stream. Browser events —
keydown, click, resize — POST back and enter the same `@on_keyboard`,
`@on_click`, and `@on_tick` path a terminal app uses.

??? abstract "No Extra Dependencies"

    `Web` runs on Python's stdlib HTTP server. There is no Starlette,
    uvicorn, or htmx requirement for the default host — install `xnano`
    and you can serve.

    ```bash
    pip install xnano
    ```

## One Grid, Two Hosts

Because a grid never references `Terminal` or `Web` directly, the exact
same class can be handed to either one.

```python title="Same Grid, Either Host"
from xnano import BaseGrid, Field, Terminal
from xnano.web import Web

class App(BaseGrid):
    body: str = Field(default="hello!")

Terminal().run(App())   # a terminal window
Web().run(App())        # a browser tab
```

Only one of these runs at a time in a given process, but nothing about
`App` itself changes between them — the grid, its fields, and its hooks
are the host-agnostic part; `Terminal` and `Web` are just two different
stages willing to run it.

??? note "Shared vs. Per-Visitor Sessions"

    Passing a `BaseGrid` *instance* to `Web().run(...)` gives every visitor
    the same live grid — one shared state, seen by everyone connected.
    Passing the *class* itself (or a factory) creates a fresh grid per
    browser session, the same way each terminal run starts from scratch.

    ```python
    Web().run(Dashboard())   # shared across all visitors
    Web().run(Dashboard)     # a new session per visitor
    ```

## Request Hooks on Either Host

Request hooks (`@on_get_request`, `@on_post_request`, `@on_put_request`,
`@on_delete_request`, `@on_patch_request`, and the rest of the HTTP
method set) are cross-host. Handlers only mutate grid state; the host
repaints on its own schedule — the cell-stream loop under `Web`, or the
terminal frame loop when you pass `host`/`port` to `Terminal.run`. See
[web request hooks](../hooks/web-requests/index.md).

## What Doesn't Carry Over

Not everything a terminal session offers has a browser equivalent. A few
[device and cursor]{data-preview} controls — raw mode, the alternate screen
buffer, moving the caret to a specific cell — only make sense where there's
a real terminal underneath, and reduce to harmless no-ops on `Web`. Native
effects and some terminal-only sizing behavior are similarly TUI-specific.

None of that affects the core model, though: grids, fields, components, and
hooks all mean the same thing on both hosts, because both paint the same
render engine.

## Next Steps

With both hosts in view, the rest of `core-concepts` —
[grids]{data-preview}, [fields]{data-preview},
[events and hooks]{data-preview}, and [device and cursor]{data-preview} —
applies equally whether the app ends up running in a `Terminal` or served
with `Web`.

??? abstract "Sandbox & API"

    **Sandbox**

    [Live Sandbox](../sandbox.md){data-preview} <small>Starting an HTTP
    server remains outside Pyodide.</small>

    **API**

    [`Web`](../api/xnano/web/web.md#xnano.web.web.Web){data-preview} ·
    [`serve_native`](../api/xnano/web/server.md){data-preview} ·
    [`WebRenderer`](../api/xnano/web/render.md){data-preview} ·
    [`xnano.web.requests`](../api/xnano/web/requests.md){data-preview}

[Terminal]: ../api/xnano/terminal/terminal.md
[Web]: ../api/xnano/web/web.md
[grids]: grids.md
[fields]: fields.md
[events and hooks]: events.md
[device and cursor]: device.md
