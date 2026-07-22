---
title: "Web Requests"
icon: "lucide/route"
---

# Web Request Hooks

!!! warning "Experimental"

    Web request hooks are experimental and are subject to frequent changes.

Request hooks turn grid methods into routes when the grid is hosted by [`Web`](../../api/xnano/web/web.md#xnano.web.web.Web){data-preview}. The method updates the live session grid, then xnano renders either a complete page or an `#xnano-app` fragment for htmx.

- [`@on_get_request`](get.md){data-preview} handles reads and navigation.
- [`@on_post_request`](post.md){data-preview} handles mutations and form-like interactions.

Under [`Terminal`](../../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal){data-preview}, request decorators only mark the method. They do not register a route or participate in terminal event dispatch.

```python title="GET and POST Routes"
class Counter(BaseGrid):
    @on_get_request("/status")
    def show_status(self) -> None:
        self.message = "ready"

    @on_post_request("/increment")
    def increment(self) -> None:
        self.count += 1
```

<div class="xnano-demo" markdown>
![web request hooks dark](../../assets/hooks/web-requests-dark.gif){.demo-dark}
![web request hooks light](../../assets/hooks/web-requests-light.gif){.demo-light}
</div>

## Request Actions

[`Action.request(method, path)`](../../api/xnano/core/actions.md#xnano.core.actions.RequestAction){data-preview} represents the same trigger for host-driven dispatch. Generic [`@on_action`](../on.md){data-preview} does not register HTTP routes; keep the corresponding request decorator on the route method.

```python title="Request Actions"
REFRESH = Action.request("GET", "/status")
SUBMIT = Action.request("POST", "/save")
```

Paths are normalized to begin with `/`, and methods are normalized before matching.
