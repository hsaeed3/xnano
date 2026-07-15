---
title: "@on_keyboard"
icon: "lucide/keyboard"
---

# Keyboard Inputs, Events & Actions

Keyboard hooks can listen to one binding, several alternatives, or every keyboard event. A binding is written the way you'd say it: `"enter"`, `"ctrl+s"`, or `"shift+tab"`.

```python title="Keyboard Alternatives" hl_lines="4"
from xnano.events import on_keyboard

class ListView(BaseGrid):
    @on_keyboard("down", "j")
    def select_next(self) -> None:
        self.index += 1
```

Use `kind="press"`, `"release"`, or `"repeat"` when the transition matters. With no binding, the hook receives every keyboard event and `ctx.keyboard` carries its parsed data.

## Keyboard Action

`Action.keyboard(*bindings, kind=None)` carries the same filters. Empty bindings mean any keyboard event.

```python title="The Equivalent Action"
NEXT = Action.keyboard("down", "j")

@on_action(NEXT)
def select_next(self) -> None:
    self.index += 1
```

For a synthetic press, use `terminal.perform(NEXT)` or `ctx.actions.press("down")`. That is also the browser-safe way to demonstrate a keyboard reaction: render once, perform the action, and render the changed frame.

??? abstract "API"

    [`on_keyboard`](../api/xnano/events.md#xnano.events.on_keyboard){data-preview} · [`KeyboardAction`](../api/xnano/core/actions.md#xnano.core.actions.KeyboardAction){data-preview}
