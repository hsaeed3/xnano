---
title: "Web Requests"
icon: "lucide/route"
---

# Web Request Hooks

Request hooks turn grid methods into routes when the grid is hosted by `Web`. The handler changes the live session grid, then xnano renders either a full page or an `#xnano-app` fragment for an htmx request.

- [`@on_get_request`](get.md) reads or navigates to a resource.
- [`@on_post_request`](post.md) performs a mutation and is the natural target for `hx-post`.

Both decorators are harmless under `Terminal`: the method remains on the class, but no terminal event dispatches it.

## Request Actions

`Action.request(method, path)` represents the same trigger for host-driven dispatch. Request actions are not accepted by the generic `@on_action`; use the request decorator so `Web` can register the route itself.

```python title="A Request Action"
REFRESH = Action.request("GET", "/status")
SUBMIT = Action.request("POST", "/save")
```

Paths are normalized to begin with `/`, and methods are matched case-insensitively after normalization.
