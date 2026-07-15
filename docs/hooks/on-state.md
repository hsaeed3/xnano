---
title: "@on_state"
icon: "lucide/database-zap"
---

# Triggering Events on "Global" State Conditions

`@on_state` evaluates an expression against the host's shared state on each tick and fires while that expression is truthy. State attributes are available by name, with `state` bound to the complete object.

```python title="Watching Shared State" hl_lines="4"
from xnano.events import on_state

class LoadingStatus(BaseGrid):
    @on_state("is_loading")
    def show_spinner(self) -> None:
        self.status = "Loading…"
```

The expression is a condition, not a change detector. If `is_loading` stays true, the hook remains eligible on later ticks too. Make handlers idempotent or update the condition when they should run once.

## Actions

State predicates have no associated action: the trigger is the live state itself. Change the state through your normal application path, then let the next host tick evaluate it. Use [`@on_field`](on-field.md) when the values belong to the grid rather than shared host state.

??? abstract "API"

    [`on_state`](../api/xnano/events.md#xnano.events.on_state){data-preview} · [`State`](../api/xnano/state.md){data-preview}
