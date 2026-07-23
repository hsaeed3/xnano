---
title: "@on_post_request"
icon: "lucide/upload"
---

# POST Request Hooks

!!! warning "Experimental"

    Web request hooks are experimental and are subject to frequent
    changes.

Use
[`@on_post_request`](../../api/xnano/requests.md#xnano.requests){data-preview}
for state-changing interactions such as submitting a form, incrementing a
counter, or applying a choice. The handler mutates grid state only; the
host repaints on its own schedule.

`POST` is one of ten method decorators. Prefer `@on_put_request` /
`@on_patch_request` / `@on_delete_request` when the HTTP verb matters;
every method shares this same path and host model. See the
[method table](index.md#every-http-method){data-preview}.

## Register a Mutation

```python title="Increment Route" hl_lines="7"
from xnano import BaseGrid, Field
from xnano.web.requests import on_post_request

class Counter(BaseGrid):
    count: int = Field(default=0, state=True)
    label: str = Field(default="Count: 0")

    @on_post_request("/increment")
    def increment(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"
```

Bare
[`@on_post_request`](../../api/xnano/requests.md#xnano.requests){data-preview}
and
[`@on_post_request(path="/")`](../../api/xnano/requests.md#xnano.requests){data-preview}
register the root path, just like their GET counterparts.

## Host the Routes

Under
[`Web`](../../api/xnano/web/web.md#xnano.web.web.Web){data-preview}, the
path becomes a `POST` route on the native server. Call it from any HTTP
client — the canvas reflects the mutation on the next cell-stream frame:

```python title="Web" hl_lines="2"
from xnano.web import Web

Web(title="counter").run(Counter)
# curl -X POST http://127.0.0.1:8000/increment
```

Under
[`Terminal`](../../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal){data-preview},
the same decorator marks the method, and
`Terminal.run(..., host=..., port=...)` starts a background request
server when any request hooks are present:

```python title="Terminal" hl_lines="2 3 4 5"
from xnano.terminal import Terminal

Terminal().run(
    Counter(),
    host="127.0.0.1",
    port=8000,
)
# curl -X POST http://127.0.0.1:8000/increment  → empty 200, TUI repaints
```

Handlers never return HTML or fragments. The response is empty (`204`
under `Web`, empty `200` under the terminal request server); the live
session's next paint shows the new state.

<div class="xnano-demo" markdown>
![POST request hook dark](../../assets/hooks/post-request-dark.gif){.demo-dark}
![POST request hook light](../../assets/hooks/post-request-light.gif){.demo-light}
</div>

## POST Actions

[`Action.request("POST", "/increment")`](../../api/xnano/core/actions.md#xnano.core.actions.RequestAction){data-preview}
describes the associated trigger. Keep
[`@on_post_request`](../../api/xnano/requests.md#xnano.requests){data-preview}
on the method so the host registers the route.

??? abstract "API"

    [`on_post_request`](../../api/xnano/requests.md#xnano.requests){data-preview}
    ·
    [`RequestAction`](../../api/xnano/core/actions.md#xnano.core.actions.RequestAction){data-preview}
