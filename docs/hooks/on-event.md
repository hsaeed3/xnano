---
title: "@on_event"
icon: "lucide/radio-tower"
---

# _'All Events'_ Handler

`@on_event` is the catch-all: it runs for every detected terminal event before you narrow the behavior yourself. It is useful for activity indicators, diagnostics, and genuinely cross-cutting reactions.

```python title="Showing the Last Event" hl_lines="4"
from xnano.events import on_event

class Activity(BaseGrid):
    @on_event
    def show_activity(self, ctx: Context) -> None:
        self.status = f"last event: {ctx.event.kind}"
```

If the method only cares about keys, resizing, or another known family, prefer that family's decorator. It documents the match and lets dispatch do the filtering.

## Actions

There is no catch-all `Action` builder. An action describes a concrete trigger, while `@on_event` deliberately accepts all terminal events. Perform the specific action you want the hook to observe, such as `Action.keyboard("enter")` or `Action.resize(width=80)`.

??? abstract "API"

    [`on_event`](../api/xnano/events.md#xnano.events.on_event){data-preview} · [`Event`](../api/xnano/events.md#xnano.events.Event){data-preview}
