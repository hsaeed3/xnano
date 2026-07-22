---
title: "@on_get_request"
icon: "lucide/download"
---

# GET Request Hooks

!!! warning "Experimental"

    Web request hooks are experimental and are subject to frequent changes.

Use [`@on_get_request`](../../api/xnano/web/requests.md#xnano.web.requests.on_get_request){data-preview} when visiting a path should read, select, or refresh something without describing a mutation.

## Register a Path

```python title="Status Route" hl_lines="6"
from xnano import BaseGrid, Field
from xnano.web.requests import on_get_request

class Dashboard(BaseGrid):
    message: str = Field(default="checking")

    @on_get_request("/status")
    def show_status(self) -> None:
        self.message = "Everything is healthy"
```

A leading slash is optional; xnano normalizes `"status"` to `"/status"`.

## Register the Root Path

Bare [`@on_get_request`](../../api/xnano/web/requests.md#xnano.web.requests.on_get_request){data-preview} defaults to `/`:

```python title="Root Route"
@on_get_request
def show_home(self) -> None:
    self.page = "home"
```

The explicit keyword form is equivalent:

```python title="Explicit Root Route"
@on_get_request(path="/")
def show_home(self) -> None:
    self.page = "home"
```

<div class="xnano-demo" markdown>
![GET request hook dark](../../assets/hooks/get-request-dark.gif){.demo-dark}
![GET request hook light](../../assets/hooks/get-request-light.gif){.demo-light}
</div>

## GET Actions

[`Action.request("GET", "/status")`](../../api/xnano/core/actions.md#xnano.core.actions.RequestAction){data-preview} describes the associated trigger. Bind the actual route with [`@on_get_request`](../../api/xnano/web/requests.md#xnano.web.requests.on_get_request){data-preview}, not [`@on_action`](../on.md){data-preview}, so [`Web`](../../api/xnano/web/web.md#xnano.web.web.Web){data-preview} can discover it.

??? abstract "API"

    [`on_get_request`](../../api/xnano/web/requests.md#xnano.web.requests.on_get_request){data-preview} · [`RequestAction`](../../api/xnano/core/actions.md#xnano.core.actions.RequestAction){data-preview}
