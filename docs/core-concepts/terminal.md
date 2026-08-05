---
title: "Terminal"
icon: "lucide/monitor"
---

# Terminal

A [Terminal]{data-preview} is a presentation host: it owns a live or offscreen
session, paints frames, and dispatches keyboard, mouse, and tick events into
your grids' `@on_*` hooks.

Grids do not open a session by themselves. Pass content to `Terminal` (or to
[`render`](../api/xnano/rendering.md){data-preview} for a one-shot frame).

<div class="grid-concept-diagram" role="img" aria-label="Diagram: Terminal owns the session loop around a root grid — open, run events and frames, exit">
<svg viewBox="0 0 720 240" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="tcd-cell" width="12" height="12" patternUnits="userSpaceOnUse">
      <path d="M 12 0 L 0 0 0 12" class="gcd-grid-line" />
    </pattern>
    <marker id="tcd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="40" y="28" width="640" height="184" rx="16" />
  <text class="gcd-label" x="360" y="56" text-anchor="middle">Terminal session</text>

  <rect class="gcd-window" x="72" y="80" width="100" height="48" rx="10" />
  <text class="gcd-chrome-label" x="122" y="108" text-anchor="middle">open</text>

  <line class="gcd-arrow" x1="172" y1="104" x2="208" y2="104" marker-end="url(#tcd-arrow)" />

  <g transform="translate(220, 72)">
    <rect class="gcd-window" x="0" y="0" width="200" height="100" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="200" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="200" height="10" />
    <circle class="gcd-dot" cx="12" cy="11" r="3" />
    <circle class="gcd-dot" cx="24" cy="11" r="3" />
    <circle class="gcd-dot" cx="36" cy="11" r="3" />
    <text class="gcd-chrome-label" x="100" y="15" text-anchor="middle">root grid</text>
    <rect class="gcd-grid-fill" x="12" y="32" width="176" height="56" rx="4" />
    <rect x="12" y="32" width="176" height="56" rx="4" fill="url(#tcd-cell)" />
  </g>

  <path class="gcd-z-connector" d="M320 172 C 320 200, 122 200, 122 128" marker-end="url(#tcd-arrow)" fill="none" />
  <text class="gcd-z-caption" x="230" y="196" text-anchor="middle">events · frames</text>

  <line class="gcd-arrow" x1="420" y1="122" x2="470" y2="122" marker-end="url(#tcd-arrow)" />

  <rect class="gcd-panel gcd-panel-accent" x="484" y="80" width="160" height="80" rx="12" />
  <text class="gcd-label gcd-label-accent" x="564" y="116" text-anchor="middle">exit</text>
  <text class="gcd-chrome-label" x="564" y="138" text-anchor="middle">request_exit()</text>
</svg>
</div>

## One frame

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: render paints one frame then stops">
<svg viewBox="0 0 400 90" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="of-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel" x="20" y="20" width="88" height="50" rx="10" />
  <text class="gcd-chrome-label" x="64" y="50" text-anchor="middle">render()</text>
  <line class="gcd-arrow" x1="108" y1="45" x2="156" y2="45" marker-end="url(#of-arr)" />
  <rect class="gcd-window" x="168" y="20" width="100" height="50" rx="10" />
  <text class="gcd-chrome-label" x="218" y="50" text-anchor="middle">1 frame</text>
  <line class="gcd-arrow" x1="268" y1="45" x2="316" y2="45" marker-end="url(#of-arr)" />
  <rect class="gcd-panel" x="328" y="20" width="56" height="50" rx="10" />
  <text class="gcd-chrome-label" x="356" y="50" text-anchor="middle">stop</text>
</svg>
</div>

[`render`](../api/xnano/rendering.md){data-preview} paints once and returns
control. It does not run the event loop.

<interactive />

??? tip "Try editing the code!"

    - Change the string.
    - Change `color` (e.g. `"emerald-400"`).

```pyodide install="xnano>=1.2.3b2" height="3"
from xnano import render

render("hello, terminal!", foreground="blue")
```

```python title="render()"
from xnano import render

render("hello, terminal!", foreground="blue") # (1)!
```

1. Opens a short-lived paint path, writes the frame, then stops.

## A live session

`Terminal().run(...)` keeps painting and dispatching until exit.

```python title="A Persistent Session" hl_lines="3 4"
from xnano import Terminal

terminal = Terminal()
terminal.run("hello, terminal!") # (1)!
```

1. Unlike `render()`, `.run()` stays open until the app exits.

`Terminal` also has `.render(...)` for a single frame on that host (returns a
[`Frame`](../api/xnano/core/frame.md){data-preview}).

## Running a grid

Pass a `BaseGrid` as the root. Fields become regions of the screen; hooks on
the grid receive events.

```python title="Running a Grid" hl_lines="8"
from xnano import BaseGrid, Field, Terminal

class App(BaseGrid, direction="vertical"):
    title: str = Field(default="My App", border="rounded")
    name: str = Field(default="Hammad", state=True)

terminal = Terminal()
terminal.run(App()) # (1)!
```

1. Layout and field details are covered under [Grids](grids.md) and
   [Fields](fields.md).

### Runnable Example

<interactive />

??? tip "Try editing the code!"

    - Change `title`'s `default=`.
    - Change `border` on the title field.

```pyodide install="xnano>=1.2.3b2" height="9"
from xnano import BaseGrid, Field, render

class App(BaseGrid, direction="vertical"):
    title: str = Field(default="My App", border="rounded")
    body: str = Field(default="Hello")

# As Terminal.render() requires a live terminal session, we cannot use it
# here in the browser directly.
render(App())
```

## State and mouse

Application-wide state is attached at construction and available on every
hook as `ctx.state` (see [Context](context.md)):

```python
Terminal(state=AppState()).run(App())
```

Mouse input is off by default. Enable it when you need click-to-focus,
`@on_click`, or `@on_mouse`:

```python
Terminal(state=AppState(), mouse_events=True).run(App())
```

Constructor options include `state=`, `title=`, `tick_interval=`, and
`mouse_events=`. Exit a running loop with `terminal.request_exit()` or
`ctx.runtime.request_exit()` from a hook.

`Terminal` does not serve HTTP. Browser hosting is [Web](web.md). Request
handlers are [Requests](requests.md).

Under the hood, `Terminal` owns a [`Runtime`](../api/xnano/core/runtime.md){data-preview}
(`terminal.runtime`). Prefer `Terminal` in apps; use `Runtime` when you need
explicit session ownership. [`Frame`](../api/xnano/core/frame.md){data-preview}
is the immutable snapshot returned by `.render(...)`.

## Next

- [Grids](grids.md) — what gets laid out
- [Events & Hooks](events.md) — keyboard, tick, and the rest
- [Device & Cursor](device.md) — title, clipboard, caret
- [Markdown](markdown.md) / [Effects](effects.md)

??? abstract "API"

    [`Terminal`](../api/xnano/terminal.md){data-preview} ·
    [`render()`](../api/xnano/rendering.md){data-preview} ·
    [`Runtime`](../api/xnano/core/runtime.md){data-preview} ·
    [`Frame`](../api/xnano/core/frame.md){data-preview}

[Terminal]: ../api/xnano/terminal.md
