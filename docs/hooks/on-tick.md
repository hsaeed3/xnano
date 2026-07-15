---
title: "@on_tick"
icon: "lucide/clock-3"
---

# Calling Hooks on Specific Time Intervals

A tick hook follows the host clock. Give it an interval in milliseconds for periodic work, or use bare `@on_tick` when the method should be eligible on every tick.

```python title="A One-Second Tick" hl_lines="6"
import time
from xnano.events import on_tick

class Clock(BaseGrid):
    display: str = Field(default="")

    @on_tick(1000)
    def update_clock(self) -> None:
        self.display = time.strftime("%H:%M:%S")
```

Intervals are matched against elapsed host time. Prefer a real interval over counting frames when the code means “once a second.”

## Tick Action

`Action.tick(interval_ms=0)` can drive the same hook synthetically. `ctx.actions.tick(1000)` is useful when a test wants to advance the reaction without owning a live loop.

```python title="The Equivalent Action"
SECOND = Action.tick(1000)

@on_action(SECOND)
def update_clock(self) -> None:
    self.display = "tick received"
```

??? abstract "API"

    [`on_tick`](../api/xnano/events.md#xnano.events.on_tick){data-preview} · [`TickAction`](../api/xnano/core/actions.md#xnano.core.actions.TickAction){data-preview}
