---
title: "HTTP Requests"
icon: "lucide/globe-2"
---

# HTTP Requests

UI events say what the host observed (a key, a click, a tick). **Request hooks**
say what arrived over HTTP.

They live in [`xnano.requests`](../api/xnano/requests.md){data-preview}: method
decorators (`@on_get_request`, `@on_post_request`, …), a generic `request(...)`
helper, and the `Request` / `Response` types. Handlers are methods on a
`BaseGrid`. Routes are collected when that grid is served — under
[Web](web.md), or via
[`RequestServer`](../api/xnano/server/requests.md){data-preview}.

A plain [Terminal](terminal.md) session does not open HTTP ports. Request hooks
on a grid do nothing until a server that understands them is running.

!!! warning "Experimental"

    HTTP request hooks (`xnano.requests`) and the request-oriented server path
    are experimental. The API may still change.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: HTTP request reaches a grid handler under a web host">
<svg viewBox="0 0 720 220" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="req-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="28" y="60" width="140" height="80" rx="12" />
  <text class="gcd-label" x="98" y="96" text-anchor="middle">HTTP</text>
  <text class="gcd-chrome-label" x="98" y="118" text-anchor="middle">GET /status</text>

  <line class="gcd-arrow" x1="168" y1="100" x2="220" y2="100" marker-end="url(#req-arrow)" />

  <rect class="gcd-panel gcd-panel-accent" x="232" y="48" width="200" height="104" rx="14" />
  <text class="gcd-label gcd-label-accent" x="332" y="84" text-anchor="middle">Web / server</text>
  <text class="gcd-chrome-label" x="332" y="108" text-anchor="middle">route · dispatch</text>
  <text class="gcd-chrome-label" x="332" y="128" text-anchor="middle">offscreen runtime</text>

  <line class="gcd-arrow" x1="432" y1="100" x2="488" y2="100" marker-end="url(#req-arrow)" />

  <rect class="gcd-window" x="500" y="56" width="192" height="88" rx="10" />
  <text class="gcd-chrome-label" x="596" y="90" text-anchor="middle">@on_get_request</text>
  <text class="gcd-z-label gcd-z-label-on" x="596" y="114" text-anchor="middle">grid method</text>
</svg>
</div>

## Serving HTTP

| Host / entry | Opens a port? | Serves request hooks? |
|--------------|---------------|------------------------|
| `Terminal` / `Terminal.run(...)` | No | No — TUI only |
| `Web(state=...).run(..., host=..., port=...)` | Yes | Yes — cell UI + declared routes |
| `RequestServer` / `start_request_server` / `serve_requests` | Yes | Yes — HTTP only, no browser shell |

`Web` binds `host` / `port` on `run()`. `Terminal` never takes those arguments.
Examples below assume a normal process that can listen on a socket — they are
not Pyodide demos.

## Declaring routes on a grid

Decorate a grid method with the HTTP verb and path. Paths are normalized to a
leading slash (`"status"` → `"/status"`; empty → `"/"`).

All method decorators share the same call shapes:

```python
@on_get_request                 # path defaults to "/"
@on_get_request("/status")
@on_get_request(path="/status")
```

Return a `Response`, a non-`None` value (wrapped as `Response(body=str(...))`),
or `None` (empty successful response when a route matched). Mutate grid fields
or application state the same way UI hooks do; the next paint reflects it under
`Web`.

## GET requests

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: GET request returns a JSON response">
<svg viewBox="0 0 420 90" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="gt-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel" x="16" y="20" width="110" height="50" rx="10" />
  <text class="gcd-chrome-label" x="71" y="50" text-anchor="middle">GET /status</text>
  <line class="gcd-arrow" x1="126" y1="45" x2="176" y2="45" marker-end="url(#gt-arr)" />
  <rect class="gcd-panel gcd-panel-accent" x="188" y="20" width="100" height="50" rx="10" />
  <text class="gcd-chrome-label" x="238" y="50" text-anchor="middle">handler</text>
  <line class="gcd-arrow" x1="288" y1="45" x2="338" y2="45" marker-end="url(#gt-arr)" />
  <rect class="gcd-window" x="350" y="20" width="56" height="50" rx="10" />
  <text class="gcd-chrome-label" x="378" y="50" text-anchor="middle">JSON</text>
</svg>
</div>


```python title="GET handler" hl_lines="8 9 10"
from xnano import BaseGrid, Field, Web
from xnano.requests import Response, on_get_request

class Status(BaseGrid):
    body: str = Field(default="ok")

    @on_get_request("/status")
    def status(self) -> Response:
        return Response.json({"ok": True, "body": self.body})

Web().run(Status(), port=8000)
```

```bash title="Call the route"
curl http://127.0.0.1:8000/status
```

### HEAD requests

`HEAD` uses the same path matching as `GET`. Handlers still run; servers that
speak the full method set omit the response body on the wire for `HEAD` (see
`RequestServer`).

```python title="HEAD handler"
from xnano.requests import Response, on_head_request

@on_head_request("/status")
def status_head(self) -> Response:
    return Response(status=200, headers={"x-ready": "1"})
```

## POST requests

```python title="POST with body and state" hl_lines="12-16"
import dataclasses

from xnano import BaseGrid, Field, Web
from xnano.requests import Response, on_post_request

@dataclasses.dataclass
class Counters:
    hits: int = 0

class Counter(BaseGrid):
    label: str = Field(default="hits: 0")

    @on_post_request("/hit")
    def hit(self, ctx) -> Response:
        ctx.state.hits += 1
        self.label = f"hits: {ctx.state.hits}"
        return Response.json({"hits": ctx.state.hits})

Web(state=Counters()).run(Counter(), port=8000)
```

```bash title="POST the route"
curl -X POST http://127.0.0.1:8000/hit
```

Read JSON from the parsed request with `ctx.request.json()` when the client
sends a body (see [Request / Response](#request--response)).

## PUT requests

```python title="PUT replace" hl_lines="8-11"
from xnano import BaseGrid, Field, Web
from xnano.requests import Response, on_put_request

class Document(BaseGrid):
    content: str = Field(default="")

    @on_put_request("/document")
    def put_document(self, ctx) -> Response:
        payload = ctx.request.json() if ctx.request else None
        self.content = str((payload or {}).get("content", ""))
        return Response.json({"content": self.content})

Web().run(Document(), port=8000)
```

```bash
curl -X PUT http://127.0.0.1:8000/document \
  -H 'content-type: application/json' \
  -d '{"content": "hello"}'
```

## PATCH requests

```python title="PATCH partial update" hl_lines="8-12"
from xnano import BaseGrid, Field, Web
from xnano.requests import Response, on_patch_request

class Profile(BaseGrid):
    name: str = Field(default="anonymous")

    @on_patch_request("/profile")
    def patch_profile(self, ctx) -> Response:
        payload = ctx.request.json() if ctx.request else {}
        if "name" in (payload or {}):
            self.name = str(payload["name"])
        return Response.json({"name": self.name})

Web().run(Profile(), port=8000)
```

```bash
curl -X PATCH http://127.0.0.1:8000/profile \
  -H 'content-type: application/json' \
  -d '{"name": "midoriya"}'
```

## DELETE requests

```python title="DELETE" hl_lines="8-11"
from xnano import BaseGrid, Field, Web
from xnano.requests import Response, on_delete_request

class Session(BaseGrid):
    active: bool = Field(default=True, state=True)

    @on_delete_request("/session")
    def end_session(self) -> Response:
        self.active = False
        return Response(status=204)

Web().run(Session(), port=8000)
```

```bash
curl -X DELETE http://127.0.0.1:8000/session
```

## Other HTTP methods

Less common verbs use the same decorator pattern and path rules:

| Decorator | Method |
|-----------|--------|
| `@on_connect_request` | `CONNECT` |
| `@on_options_request` | `OPTIONS` |
| `@on_trace_request` | `TRACE` |
| `@on_query_request` | `QUERY` |

```python title="OPTIONS"
from xnano.requests import Response, on_options_request

@on_options_request("/items")
def items_options(self) -> Response:
    return Response(
        status=204,
        headers={"allow": "GET, POST, OPTIONS"},
    )
```

## Generic method registration

When the method is dynamic or you prefer one entry point, use
[`request(method, path)`](../api/xnano/requests.md){data-preview}:

```python title="Generic method registration" hl_lines="6 7 8"
from xnano import BaseGrid
from xnano.requests import Response, request

class App(BaseGrid):
    @request("PATCH", "/thing")
    def update(self, ctx) -> Response:
        payload = ctx.request.json() if ctx.request else {}
        return Response.json({"name": (payload or {}).get("name")})
```

`method` is uppercased. Unsupported method names raise `ValueError`. Supported
values match the dedicated decorators: `GET`, `HEAD`, `POST`, `PUT`, `DELETE`,
`CONNECT`, `OPTIONS`, `TRACE`, `PATCH`, `QUERY`.

## Request and response objects

### Incoming request

Immutable parsed request available as `ctx.request` when the server builds one
(both `Web` / native path and `RequestServer` do).

| Attribute | Meaning |
|-----------|---------|
| `method` | Uppercase HTTP method |
| `path` | Normalized path with leading `/` |
| `query` | Multi-value mapping: `str` → `tuple[str, ...]` |
| `headers` | Header map (keys lowercased on `from_parts`) |
| `body` | Raw `bytes` |

Helpers:

- `request.text(encoding="utf-8")` — decode `body`
- `request.json()` — parse JSON (`None` if body is empty)
- `Request.from_parts(method, path, *, query_string=..., headers=..., body=..., max_body=...)` — build from raw parts; raises `ValueError` if `body` exceeds `max_body` (default 1 MiB)

### Outgoing response

What a handler returns to the client.

| Attribute | Default | Meaning |
|-----------|---------|---------|
| `body` | `b""` | `bytes` or `str` |
| `status` | `200` | HTTP status code |
| `headers` | `{}` | Response headers |

```python title="Response.json"
from xnano.requests import Response

Response.json({"ready": True}, status=201)
# content-type: application/json; charset=utf-8
```

`as_bytes()` encodes a string body as UTF-8. If the handler returns a non-bool
value that is not a `Response`, dispatch wraps it as `Response(body=str(result))`.
With a runtime attached, unmatched routes become `404` with body `Not Found`.

## Handlers and context

Handlers that accept a `ctx` parameter receive the same
[Context](context.md) shape as UI hooks.

| Field | In request hooks |
|-------|------------------|
| `ctx.state` | Application state from `Web(state=...)` or the runtime |
| `ctx.request` | Parsed `Request`, or `None` if not supplied to dispatch |
| `ctx.terminal` / `ctx.runtime` | Host / runtime facade used for the dispatch |

```python title="ctx.state and ctx.request"
@on_post_request("/submit")
def submit(self, ctx) -> Response:
    mode = ctx.request.query.get("mode", ())
    data = ctx.request.json()
    ctx.state.last = data
    return Response.json({"mode": mode, "accepted": True}, status=202)
```

Handlers that omit `ctx` still work when they only need `self`.

## Named request actions

[`Action.request(method, path)`](actions.md) names an HTTP trigger the same way
`Action.keyboard` names a key. Pair it with `@on_action` when you want one
constant for both synthetic perform and real request matching.

```python title="Action.request"
from xnano import Action, BaseGrid, on_action
from xnano.requests import Response, on_get_request

GET_STATUS = Action.request("GET", "/status")

class Api(BaseGrid):
    @on_get_request("/status")
    def status(self) -> Response:
        return Response.json({"ok": True})

    @on_action(GET_STATUS)
    def on_status_action(self) -> None:
        ...
```

The actions performer also exposes `ctx.actions.request(method, path)` as a
shortcut for `perform(Action.request(...))`. See [Actions](actions.md).

## Web host and request servers

| Entry | Role |
|-------|------|
| `Web(state=...).run(source, host=..., port=...)` | Browser cell UI + request hooks for the served grid |
| `xnano.server.native.serve_native` | Lower-level native cell server used by `Web` |
| `xnano.server.requests.RequestServer` | `ThreadingHTTPServer` for one grid’s request hooks |
| `start_request_server(grid, host=..., port=..., runtime=...)` | Bind on a daemon thread; returns the server |
| `serve_requests` | Alias of `start_request_server` |

Request-only example (no browser shell):

```python title="RequestServer" hl_lines="12"
from xnano import BaseGrid
from xnano.requests import Response, on_get_request
from xnano.server.requests import start_request_server

class Health(BaseGrid):
    @on_get_request("/health")
    def health(self) -> Response:
        return Response.json({"ok": True})

server = start_request_server(Health, host="127.0.0.1", port=8000)
# server.shutdown(); server.server_close()
```

```bash
curl http://127.0.0.1:8000/health
```

`port=0` selects a free port; read it from `server.server_address[1]`.

Body size is capped (about 1 MiB) on the request server path; oversized bodies
get `413`. See the [server API](../api/xnano/server.md){data-preview}.

## Paths and routing

Matching is exact on **method** and **normalized path**:

- Paths are stripped and given a leading `/`. Empty paths become `"/"`.
- Query strings are **not** part of the path key. They appear on
  `ctx.request.query` after the route matches.
- There is no path-parameter or wildcard syntax in the current matcher —
  `"/items"` does not match `"/items/1"`.
- Registration order is preserved. A name defined on a more-derived class
  shadows the same method name from a base class when hooks are collected.
- Private methods (`_name`) are skipped unless they carry a request-hook
  marker.

```python title="Path normalization"
@on_get_request("status")   # registers as "/status"
@on_get_request("")         # registers as "/"
@on_get_request("/")        # registers as "/"
```

## Next

- [Web](web.md) — browser host that binds host/port
- [Events & Hooks](events.md) — UI `@on_*` decorators
- [Actions](actions.md) — `Action.request`
- [Context](context.md) — `ctx.state`, `ctx.request`
- [State](state.md) — shared application state

??? abstract "API"

    [`xnano.requests`](../api/xnano/requests.md){data-preview} ·
    [`Request`](../api/xnano/requests.md){data-preview} ·
    [`Response`](../api/xnano/requests.md){data-preview} ·
    [`Web`](../api/xnano/web.md){data-preview} ·
    [`RequestServer`](../api/xnano/server/requests.md){data-preview} ·
    [`Action.request`](../api/xnano/actions.md){data-preview}

[Web]: web.md
[Terminal]: terminal.md
