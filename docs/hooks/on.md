---
title: "@on_action"
icon: "lucide/link"
---

# Creating Reusable & Named Actions

`@on_action` binds a method to an action you've already built. It is the small bridge between a meaningful application name such as `SAVE` and the physical event that currently represents it.

```python title="Binding a Named Action" hl_lines="3 6"
from xnano import Action, BaseGrid, on_action

SAVE = Action.keyboard("ctrl+s")

class Editor(BaseGrid):
    @on_action(SAVE)
    def save_document(self) -> None:
        self.status = "saved"
```

The action stays immutable and reusable; the method still owns the reaction. For a one-off key, click, or tick, its specialized decorator is shorter and more direct.

## Supported Actions

`@on_action` accepts keyboard, mouse, click, focus, clipboard, tick, and resize actions. `RequestAction` belongs to the web request decorators instead, because a request also has to become a registered route.

```python title="Performing the Same Trigger"
terminal.perform(SAVE)

# From inside another hook:
ctx.actions.perform(SAVE)
```

Performing the action synthesizes its event and sends it through ordinary dispatch. It does not call `save_document()` directly.

!!! note "Renamed from `@on`"

    `@on` remains available for existing applications, but it is deprecated. New code should import and use `@on_action`; the binding and dispatch behavior is otherwise identical.

??? abstract "API"

    [`on_action`](../api/xnano/events.md#xnano.events.on_action){data-preview} · [`Action`](../api/xnano/core/actions.md#xnano.core.actions.Action){data-preview}
