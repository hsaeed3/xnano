---
title: Request hooks
icon: lucide/route
---

# Request hooks

`@on_get_request` and `@on_post_request` mark grid methods as HTTP handlers
when the grid is served by `Web`. Paths become Starlette routes. After a
handler runs, the session re-renders — full page for ordinary browser
navigation, `#xnano-app` fragment for htmx (`HX-Request`).

Under `Terminal` the decorators only attach metadata. Methods stay on the
class and never fire during a TUI frame.

```python title="counter.py"
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.webui.requests import on_get_request, on_post_request
from xnano.webui import Web

class Counter(BaseGrid, direction="vertical", gap=1):
    label: str = Field(default="Count: 0")
    count: int = Field(default=0, state=True)

    @on_post_request("/increment")
    def increment(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"

    @on_get_request("/status")
    def status(self) -> None:
        self.label = f"status:{self.count}"

    @on_get_request("/")
    def visit(self) -> None:
        # runs on every full page load of the index
        pass

Web(title="counter").run(Counter)
```

Wire UI controls with htmx attributes that target the app root:

```html
<button
  hx-post="/increment"
  hx-target="#xnano-app"
  hx-swap="innerHTML"
>
  Increment
</button>
```

---

## Decorator forms

Both decorators accept a path string, or mark a method with a default path
of `/`:

```python
@on_get_request("/status")
def show_status(self) -> None: ...

@on_get_request
def index(self) -> None: ...  # path defaults to "/"

@on_post_request(path="/increment")
def increment(self) -> None: ...
```

Paths are normalized to a leading slash. Empty input becomes `"/"`. Handlers
receive the same optional `Context` arity rules as other hooks — zero
arguments, or a context with `state` attached from `Web(state=...)`.

---

## How routes are registered

When `Web.build_app(grid)` runs, it scans the attached grid class (and nested
grids as they paint) for request hooks. Each unique `(method, path)` pair
becomes a Starlette `Route`, except:

| Reserved | Reason |
|---|---|
| `GET /` | Already the index endpoint (fires `@on_get_request("/")` before first paint) |
| Paths under `/xnano/` | Built-in click, key, tick, and input endpoints |

POST custom routes default to fragment responses (typical htmx swap targets).
GET custom routes return a full page unless the request carries `HX-Request`.

Nested grids can contribute routes. A name defined on a more-derived class
shadows the same method name on a base class, matching terminal hook
collection.

---

## Dispatch without a browser

For tests and programmatic use:

```python
from xnano.webui import Web

web = Web()
web.render_html(Counter())
html = web.dispatch_request("POST", "/increment")
```

`dispatch_request` normalizes the path, invokes matching handlers on the live
session grid, pumps tick/state/field hooks, and returns a fresh HTML
fragment.

---

## Same grid, two hosts

A grid can mix terminal hooks and request hooks:

```python
from xnano.events import on_keyboard
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.webui.requests import on_post_request

class Counter(BaseGrid):
    count: int = Field(default=0, state=True)
    label: str = Field(default="Count: 0")

    @on_keyboard("up")
    def from_key(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"

    @on_post_request("/increment")
    def from_http(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"
```

`Terminal().run(Counter())` only sees keyboard and paint. `Web().run(Counter)`
registers `/increment` and still dispatches browser keyboard events if you
add them.

Continue with [Web rendering](rendering.md) for how field values become HTML.
