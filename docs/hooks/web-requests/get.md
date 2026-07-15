---
title: "@on_get_request"
icon: "lucide/download"
---

# GET Web Requests

Use a GET hook when visiting a path should read, select, or refresh something without describing a mutation.

```python title="A Status Route" hl_lines="4"
from xnano.webui.requests import on_get_request

class Dashboard(BaseGrid):
    @on_get_request("/status")
    def show_status(self) -> None:
        self.message = "Everything is healthy"
```

Bare `@on_get_request` and `@on_get_request(path="/")` both register `/`. A leading slash is optional in the supplied path; xnano adds it during normalization.

## GET Action

The associated trigger is `Action.request("GET", "/status")`. Unlike terminal action families, bind the route with `@on_get_request`, not generic `@on_action`, so it becomes part of the web application's route table.

??? abstract "API"

    [`on_get_request`](../../api/xnano/webui/requests.md#xnano.webui.requests.on_get_request){data-preview} · [`RequestAction`](../../api/xnano/core/actions.md#xnano.core.actions.RequestAction){data-preview}
