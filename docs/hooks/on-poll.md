---
title: "@on_poll"
icon: "lucide/refresh-cw"
---

# Calling a Hook on Every Host Cycle (_Polling_)

Poll hooks give small pieces of background work a place in the host cycle. Bare `@on_poll` uses `"idle"`; `@on_poll("frame")` runs once per rendered frame.

```python title="Idle and Frame Polling" hl_lines="4 8"
from xnano.events import on_poll

class Worker(BaseGrid):
    @on_poll
    def check_queue(self) -> None:
        self.status = "waiting"

    @on_poll("frame")
    def count_frame(self) -> None:
        self.frames += 1
```

Keep frame work short: it sits on the rendering path. For a fixed cadence, [`@on_tick(interval)`](on-tick.md) communicates the timing more precisely.

## Actions

Polling is host lifecycle behavior, so it has no associated action and cannot be bound through `@on_action`. Browser examples should show the resulting frame directly or use a concrete action; they should not start a polling loop with `Terminal.run()`.

??? abstract "API"

    [`on_poll`](../api/xnano/events.md#xnano.events.on_poll){data-preview}
