---
title: "@on_field"
icon: "lucide/grid-2x2-check"
---

# Triggering Events on Field  Changes or Conditions

`@on_field` watches the grid's own values. Layout fields and `state=True` fields are both available by name in its expression.

```python title="Watching a Grid Field" hl_lines="6"
from xnano import BaseGrid, Field
from xnano.events import on_field

class Checkout(BaseGrid):
    total: int = Field(default=0, state=True)

    @on_field("total > 0")
    def enable_checkout(self) -> None:
        self.button = "Checkout ready"
```

Like `@on_state`, this is level-triggered: it runs while the expression is true, not only on the instant it changes from false to true.

## Actions

There is no field action. Assign the field normally and allow a tick to evaluate the predicate. When an explicit command would read more clearly than a continuously true condition, bind a named `Action` with [`@on_action`](on.md) instead.

??? abstract "API"

    [`on_field`](../api/xnano/events.md#xnano.events.on_field){data-preview} · [`Field`](../api/xnano/fields.md#xnano.fields.Field){data-preview}
