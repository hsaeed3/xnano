---
title: Web UI
icon: lucide/panel-top
---

# Web UI

`Web` is the browser analogue of `Terminal`. You declare a `BaseGrid` the same
way you would for a TUI; `Web` paints it to HTML with Tailwind and htmx, keeps
a session per visitor (or one shared grid), and dispatches browser events into
the same `@on_*` hooks the terminal loop uses.

Install the web extra, then run a grid:

```bash
pip install "xnano[web]"
```

```python title="counter.py"
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.events import on_click
from xnano.webui import Web

class Counter(BaseGrid, direction="vertical", gap=1):
    label: str = Field(default="Count: 0", height=1)
    body: str = Field(default="Click me", border="rounded")
    count: int = Field(default=0, state=True)

    @on_click("body")
    def bump(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"

Web(title="counter").run(Counter())
```

Open `http://127.0.0.1:8000`. Clicks on the body field POST to an internal
htmx route; the handler mutates the grid and the page swaps the `#xnano-app`
fragment.

---

## Shared grid vs per-visitor session

Pass a **grid instance** when every browser should share one app. Pass a
**callable factory** (usually the class itself) when each visitor needs an
isolated grid:

```python
Web(title="dashboard").run(Dashboard())  # one shared grid
Web(title="app").run(Dashboard)          # new grid per browser session
```

Per-visitor mode issues an `xnano-session` cookie and stores sessions on the
host. Shared mode reuses a single default session for every request.

Optional `state=` on `Web` is attached to every session the same way
`Terminal(state=...)` attaches shared state for hooks.

---

## What hooks work on the web

| Hook / feature | Web behavior |
|---|---|
| `@on_click` / field mouse handlers | Element clicks via `POST /xnano/click/{id}` |
| `@on_keyboard` / `@on_event` | Browser `keydown` → `POST /xnano/key?binding=…` |
| `@on_tick` / `@on_state` / `@on_field` | htmx poller → `POST /xnano/tick` |
| `@on_get_request` / `@on_post_request` | Custom Starlette routes (see [Request hooks](requests.md)) |
| `Text(input=True)` | Real `<input>` synced via `POST /xnano/input/{id}` |

Effects, focus cycling, and slide remain terminal-only. Request hooks never
fire under `Terminal` — they only mark methods for the web host.

Keyboard bindings use the same string form as the terminal (`"up"`,
`"ctrl+k"`, `"esc"`). Capture is disabled while focus is inside an
`<input>` or `<textarea>`.

---

## Host API

```python
from xnano.webui import Web

web = Web(title="My App", state=None)
```

| Method | Purpose |
|---|---|
| `run(grid, host=…, port=…)` | Build the ASGI app and serve with uvicorn |
| `build_app(grid)` | Return a Starlette app without starting a server |
| `render_html(grid=None)` | Render body HTML for tests or embedding |
| `build_page(body_html)` | Wrap a fragment in the full document shell |
| `dispatch_click` / `dispatch_keyboard` / `dispatch_tick` / `dispatch_request` | Drive the default session without HTTP |

`build_app` and `run` raise `ImportError` with install instructions if the
`web` extra is missing.

The page shell loads Tailwind and htmx from CDNs, sets a dark mono body
class, and mounts the grid under `#xnano-app`. When tick hooks are present,
a poller element sits **outside** that div so fragment swaps never tear it
down. When keyboard hooks are present, a small script posts key bindings to
`/xnano/key`.

Ordinary navigation and first load receive a full HTML document. Requests
with `HX-Request` receive only the app fragment so htmx can swap
`innerHTML` on `#xnano-app`.

---

## Layout in the browser

The web controller maps grid direction, gap, sizing, borders, and titles to
flexbox and Tailwind. Field order is still layout order. Nested grids become
nested flex containers. Styled strings and `Text` values lower to HTML
through web render nodes — details in [Web rendering](rendering.md).

---

## Next steps

- [Request hooks](requests.md) — declare GET/POST routes on the grid
- [Web rendering](rendering.md) — HTML nodes and dual-host `Text`
- [CLI](../cli/index.md) — model-like command-line interface
