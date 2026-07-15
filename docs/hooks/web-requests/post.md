---
title: "@on_post_request"
icon: "lucide/upload"
---

# POST Web Requests

POST hooks are for state-changing interactions: incrementing a counter, submitting a form, or applying a choice. htmx can target the route and swap the freshly rendered grid back into the page.

```python title="An htmx Mutation" hl_lines="6 11"
from xnano import BaseGrid, Field
from xnano.webui.requests import on_post_request

class Counter(BaseGrid):
    count: int = Field(default=0, state=True)

    @on_post_request("/increment")
    def increment(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"

# A web node can point at the route with:
# hx-post="/increment" hx-target="#xnano-app" hx-swap="innerHTML"
```

The response is a full page during ordinary navigation and an `#xnano-app` fragment when the request carries `HX-Request`.

## POST Action

`Action.request("POST", "/increment")` describes the associated trigger. Keep `@on_post_request` on the handler itself so `Web` discovers and registers the route.

??? abstract "API"

    [`on_post_request`](../../api/xnano/webui/requests.md#xnano.webui.requests.on_post_request){data-preview} · [`RequestAction`](../../api/xnano/core/actions.md#xnano.core.actions.RequestAction){data-preview}
