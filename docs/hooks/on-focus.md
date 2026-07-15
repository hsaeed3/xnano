---
title: "@on_focus"
icon: "lucide/focus"
---

# Automatic Focus Detection Events & Actions

Bare `@on_focus` listens to the terminal window gaining or losing OS focus. Give it a field name and it follows application focus instead — particularly useful around editable `Text(input=True)` fields.

```python title="Field Focus" hl_lines="4 8"
from xnano.events import on_focus

class Form(BaseGrid):
    @on_focus("email", kind="gained")
    def begin_email(self) -> None:
        self.hint = "Enter your email address"

    @on_focus("email", kind="lost")
    def finish_email(self) -> None:
        self.hint = ""
```

## Focus Action

`Action.focus(field=None, kind=None)` carries the same window-or-field distinction. The convenience form is `ctx.actions.focus("email", kind="gained")`.

```python title="Reusable Focus"
FOCUS_SEARCH = Action.focus("search", kind="gained")

@on_action(FOCUS_SEARCH)
def reveal_help(self) -> None:
    self.help = "Type to filter"
```

??? abstract "API"

    [`on_focus`](../api/xnano/events.md#xnano.events.on_focus){data-preview} · [`FocusAction`](../api/xnano/core/actions.md#xnano.core.actions.FocusAction){data-preview}
