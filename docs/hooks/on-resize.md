---
title: "@on_resize"
icon: "lucide/maximize-2"
---

# Window Resize Events & Actions

`@on_resize` fires after the terminal reports a new cell size. The current event's dimensions are available through `Context`.

```python title="Reading the New Size" hl_lines="4"
from xnano.events import on_resize

class Status(BaseGrid):
    @on_resize
    def show_size(self, ctx: Context) -> None:
        self.label = f"{ctx.resize.width} × {ctx.resize.height}"
```

Keep the handler about application policy; the host and controller already take care of laying the frame out again.

## Resize Action

`Action.resize(width=None, height=None)` matches either dimension when supplied. Performing it is a clean way to exercise resize behavior without changing a real terminal window.

```python title="A Synthetic Resize"
NARROW = Action.resize(width=40, height=12)

@on_action(NARROW)
def use_compact_layout(self) -> None:
    self.mode = "compact"
```

??? abstract "API"

    [`on_resize`](../api/xnano/events.md#xnano.events.on_resize){data-preview} · [`ResizeAction`](../api/xnano/core/actions.md#xnano.core.actions.ResizeAction){data-preview}
