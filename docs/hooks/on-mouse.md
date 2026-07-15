---
title: "@on_mouse"
icon: "lucide/mouse-pointer-2"
---

# Mouse Movement, Scroll & Button Press Events

`@on_mouse` is the broad mouse hook. It can filter by button, event kind, field, or any useful combination of the three.

```python title="Watching a Field" hl_lines="4"
from xnano.events import on_mouse

class Canvas(BaseGrid):
    @on_mouse(field="preview", kind="moved")
    def track_pointer(self, ctx: Context) -> None:
        self.position = f"{ctx.mouse.column}, {ctx.mouse.row}"
```

With no arguments it defaults to a left-button press. Movement and scrolling do not carry a button, so select them with `kind="moved"`, `"scroll_up"`, or `"scroll_down"` instead.

## Mouse Action

`Action.mouse(*buttons, kind=None)` mirrors the button and kind filters. Use it for reusable low-level mouse bindings; for an ordinary field click, [`Action.click`](on-click.md) is more expressive.

```python title="A Reusable Right Click"
CONTEXT_MENU = Action.mouse("right", kind="press")

@on_action(CONTEXT_MENU)
def open_menu(self) -> None:
    self.menu = "open"
```

??? abstract "API"

    [`on_mouse`](../api/xnano/events.md#xnano.events.on_mouse){data-preview} · [`MouseAction`](../api/xnano/core/actions.md#xnano.core.actions.MouseAction){data-preview}
