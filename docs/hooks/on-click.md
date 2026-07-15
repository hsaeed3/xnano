---
title: "@on_click"
icon: "lucide/mouse-pointer-click"
---

# Automatic Click Events

Clicks usually belong to a visible field, so `@on_click` starts with its name. xnano uses the current layout map to decide whether the mouse press landed inside that field.

```python title="A Field Click" hl_lines="4"
from xnano.events import on_click

class Dialog(BaseGrid):
    @on_click("confirm")
    def confirm_choice(self) -> None:
        self.status = "confirmed"
```

Left press is the default. Pass `button="right"` or another mouse `kind` when the interaction calls for it.

## Click Action

`Action.click(field=None, button="left")` is the reusable form. Its field is host-side scope metadata, just like the field passed to the decorator.

```python title="Clicking from Code"
CONFIRM = Action.click("confirm")

@on_action(CONFIRM)
def confirm_choice(self) -> None:
    self.status = "confirmed"

ctx.actions.click("confirm")
```

An action-driven example can paint this result in one frame after `perform()`; it does not need a real mouse or event loop.

??? abstract "API"

    [`on_click`](../api/xnano/events.md#xnano.events.on_click){data-preview} · [`ClickAction`](../api/xnano/core/actions.md#xnano.core.actions.ClickAction){data-preview}
