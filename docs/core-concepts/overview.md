---
title: "Overview"
icon: "lucide/book-open"
---

# Overview

This section covers the main pieces of [xnano]{data-preview}, grouped the same
way as the site navigation.

For a full application built step by step, see
[Getting Started](../getting-started.md).

!!! info "v1.2"

    These pages describe `v1.2.xx` and higher. Earlier releases used a different
    surface (`xnano.beta` and related hosts).

## Map

Same groups as the sidebar.

### Hosts

| Page | Topic |
|------|-------|
| [Terminal](terminal.md) | Run an app in the terminal |
| [Web](web.md) | Run the same app in a browser |

### Layout & Styling

| Page | Topic |
|------|-------|
| [Grids](grids.md) | Structure the screen with `BaseGrid` |
| [Fields](fields.md) | Put content and state in slots |
| [State](state.md) | App `state=`, `Field(state=True)`, groups, and sync |
| [Components](components.md) | Tables, inputs, charts, and other widgets |
| [Styling](styling.md) | Colors, borders, and Tailwind classes |

### Live Behavior & Events

| Page | Topic |
|------|-------|
| [Effects](effects.md) | Animate field areas |
| [Events & Hooks](events.md) | React to keys, clicks, ticks, and more |
| [Context](context.md) | Values available inside a hook |
| [Actions](actions.md) | Name a trigger once and reuse it |
| [Device & Cursor](device.md) | Window title, clipboard, and caret |

### Additional Features

Useful, but optional. Pages here that are still unstable say **Experimental**
at the top.

| Page | Topic |
|------|-------|
| [Markdown](markdown.md) | Page through a Markdown file |
| [Requests](requests.md) | Handle HTTP requests on a grid |
| [CLI Commands](cli.md) | Build small command-line tools |

## Layers

Application code is grids, fields, hooks, and components. Hosts
([Terminal](terminal.md), [Web](web.md)) run that code. Paint and the session
loop live in [xnano-core]{data-preview}.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: app grid sits on xnano DSL over xnano-core, targeting terminal or browser">
<svg viewBox="0 0 720 240" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="ovd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel gcd-panel-accent" x="200" y="20" width="320" height="48" rx="12" />
  <text class="gcd-label gcd-label-accent" x="360" y="50" text-anchor="middle">your App · grids · fields · hooks</text>

  <line class="gcd-arrow" x1="360" y1="68" x2="360" y2="92" marker-end="url(#ovd-arrow)" />

  <rect class="gcd-panel" x="200" y="96" width="320" height="48" rx="12" />
  <text class="gcd-label" x="360" y="126" text-anchor="middle">xnano · public DSL</text>

  <line class="gcd-arrow" x1="360" y1="144" x2="360" y2="168" marker-end="url(#ovd-arrow)" />

  <rect class="gcd-panel" x="200" y="172" width="320" height="48" rx="12" />
  <text class="gcd-label" x="360" y="202" text-anchor="middle">xnano-core · ratatui · paint</text>

  <rect class="gcd-window" x="40" y="100" width="120" height="56" rx="10" />
  <text class="gcd-chrome-label" x="100" y="132" text-anchor="middle">terminal</text>
  <line class="gcd-arrow" x1="160" y1="128" x2="196" y2="128" marker-end="url(#ovd-arrow)" />

  <rect class="gcd-window" x="560" y="100" width="120" height="56" rx="10" />
  <text class="gcd-chrome-label" x="620" y="132" text-anchor="middle">browser</text>
  <line class="gcd-arrow" x1="560" y1="128" x2="524" y2="128" marker-end="url(#ovd-arrow)" />
</svg>
</div>

## One frame without a session

[`render`](../api/xnano/rendering.md){data-preview} paints values once and
writes them out. It does not start an event loop.

<interactive />

??? tip "Try editing the code!"

    - Change `foreground` on the `Text`.
    - Change `modifiers` (e.g. `["bold", "italic"]`).

```pyodide install="xnano>=1.2.3b2" height="8"
from xnano import render
from xnano.components.text import Text

render(Text("Hello from xnano", foreground="pink", modifiers=["bold"]))
```

For a live terminal session, use [Terminal](terminal.md). For the same grid in a
browser, use [Web](web.md).

## Public surface checklist

Root exports and where this section covers them:

| Export / module | Concept page |
|-----------------|--------------|
| `Terminal`, `render`, `Runtime`, `Frame` | [Terminal](terminal.md) |
| `Web` | [Web](web.md) |
| `BaseGrid`, `GridSettings` | [Grids](grids.md) |
| `Field` | [Fields](fields.md) / [State](state.md) |
| `Style` (+ `xnano.colors`) | [Styling](styling.md) |
| `Component`, `xnano.components` | [Components](components.md) |
| `on_*`, `hooks`, `events` | [Events & Hooks](events.md) |
| `Context` (+ `xnano.state.State`) | [Context](context.md) |
| `Action` | [Actions](actions.md) |
| `xnano.device`, `xnano.cursor` | [Device & Cursor](device.md) |
| `xnano.markdown` | [Markdown](markdown.md) |
| `xnano.effects` | [Effects](effects.md) |
| `requests` | [Requests](requests.md) |
| `Command`, `cli` | [CLI Commands](cli.md) |
| `xnano.server` | [Web](web.md) / [Requests](requests.md) |
| `xnano.core` | Runtime, Frame, exceptions — via hosts and API reference |

Lower-level packages (`utils`, paint content helpers) stay in the
[API reference](../api/xnano/index.md).

??? abstract "API"

    [`render()`](../api/xnano/rendering.md){data-preview} ·
    [`Terminal`](../api/xnano/terminal.md){data-preview} ·
    [`Web`](../api/xnano/web.md){data-preview} ·
    [`BaseGrid`](../api/xnano/grids.md){data-preview}

[xnano]: ../getting-started.md
[xnano-core]: ../api/xnano-core/index.md
