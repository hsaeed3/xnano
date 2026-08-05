# Server and HTTP Requests

Declare routes on a grid or component with request hooks from
`xnano.requests`:

```python
from xnano import BaseGrid
from xnano.requests import Request, Response, on_get_request, on_post_request


class App(BaseGrid):
    @on_get_request("/health")
    def health(self) -> Response:
        return Response.json({"ok": True})

    @on_post_request("/message")
    def message(self, request: Request) -> Response:
        return Response.json({"message": request.json()})
```

Handlers may use the supported zero/context/request signatures; inspect the
request dispatch path when adding a less common shape. `Request` exposes the
uppercase method, normalized path, multi-value query mapping, headers, and raw
body, with `.text()` and `.json()` helpers. `Response` can return text, bytes,
or JSON with explicit status and headers.

Use the named decorators for `GET`, `HEAD`, `POST`, `PUT`, `DELETE`, `CONNECT`,
`OPTIONS`, `TRACE`, `PATCH`, and `QUERY`, or `request(method, path)` for a
supported method. Paths are normalized to a leading slash.

## Serving

- `Web.run(...)` serves the browser shell, `/xnano/frame`, browser events, and
  declared request hooks from one offscreen runtime.
- `xnano.server.start_request_server(...)` / `serve_requests(...)` serves
  request hooks through the standard-library threaded HTTP server.
- `RequestServer` accepts a grid instance or class and may expose a runtime to
  request contexts.

Request bodies are limited to 1 MiB by default. Keep request validation and
authentication in the handler or a shared application boundary; never treat a
request hook as a trusted internal call. Do not add a second web framework or
duplicate native server routing for ordinary routes.
