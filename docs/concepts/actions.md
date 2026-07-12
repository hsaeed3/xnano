---
title: Actions
icon: lucide/play
---

# Actions

Events describe something that happened. Actions describe a trigger that can
be named, shared, matched, or performed. Both use the same dispatch path, so a
keyboard action performed in a test reaches the same hooks as the equivalent
terminal input.

## Define a trigger

Create actions with the `Action` factories. Actions are frozen values, which
makes them safe to define once at module level and reuse across grids.

```python title="shortcuts.py"
from xnano import Action

SAVE = Action.keyboard("ctrl+s")
CANCEL = Action.keyboard("escape")
REFRESH = Action.keyboard("r", "f5")
```

An action stores the filter, not a callback. `SAVE`, for example, means “a
keyboard event matching `ctrl+s`.” It does not decide how an application saves
its data.

The built-in action families are:

| Factory | Trigger |
|---|---|
| `Action.keyboard(*bindings, kind=None)` | Keyboard binding and optional press, release, or repeat kind |
| `Action.mouse(*buttons, kind=None)` | Mouse button and optional mouse-event kind |
| `Action.click(field=None, button="left")` | Mouse press with optional field metadata |
| `Action.focus(field=None, kind=None)` | Window or field focus change |
| `Action.clipboard(text=None)` | Clipboard paste, optionally with exact text |
| `Action.tick(interval_ms=0)` | Host tick |
| `Action.resize(width=None, height=None)` | Resize, optionally constrained to an exact size |
| `Action.request(method, path)` | Web request method and path |

## Bind an action to a hook

Use `@on` when an action is shared or represents an application-level command.
The specialized decorators remain the shortest form for a one-off binding.

```python title="editor.py"
from xnano import Action, BaseGrid, Field, Terminal, on
from xnano.events import on_keyboard

SAVE = Action.keyboard("ctrl+s")

class Editor(BaseGrid, direction="vertical", gap=1):
    document: str = Field(default="Draft", border="rounded")
    status: str = Field(default="Unsaved", height=1)

    @on(SAVE)  # (1)!
    def save_document(self) -> None:
        self.status = "Saved"

    @on_keyboard("q")
    def close_editor(self, context) -> None:
        context.terminal.request_exit()

Terminal().run(Editor())
```

1. `@on(SAVE)` is equivalent to `@on_keyboard("ctrl+s")`, but gives the
   trigger a reusable application-level name.

An action can be bound to methods on multiple grids. Each method remains an
independent hook; the shared action only standardizes what invokes it.

## Perform an action

Every host exposes `perform()`, and a hook context exposes the convenience
helper `context.actions`. Performing an action synthesizes its event and sends
it through normal hook dispatch.

```python title="commands.py"
from xnano import Action, BaseGrid, Field, Terminal, on

INCREMENT = Action.keyboard("+")
INCREMENT_TWICE = Action.keyboard("ctrl+i")

class Counter(BaseGrid):
    count: int = Field(default=0, state=True)

    @on(INCREMENT)
    def increment(self) -> None:
        self.count += 1

    @on(INCREMENT_TWICE)
    def increment_twice(self, context) -> None:
        context.actions.perform(INCREMENT)
        context.actions.press("+")  # (1)!

terminal = Terminal.offscreen()
terminal.attach_grid(Counter())
terminal.perform(INCREMENT)  # (2)!
```

1. `press()` is shorthand for performing `Action.keyboard(...)`.
2. Hosts accept the action object directly. This is useful for tests,
   automation, and adapters that are not physical input devices.

Actions performed from inside a hook are queued until the current dispatch
finishes. This prevents nested dispatch from interrupting a handler midway
through its work. A depth guard also stops an action from triggering itself
forever.

The host-bound helper provides readable shortcuts:

```python
context.actions.press("ctrl+s")
context.actions.paste("Hello")
context.actions.focus(kind="gained")
context.actions.resize(width=100, height=30)
context.actions.tick(1000)
```

## Actions and host-specific behavior

Action matching is interface-neutral, but some operations still need host
context:

- `Action.click(field)` carries a field name, but generic `perform()` does not
  perform layout hit-testing. Browser target dispatch and terminal mouse input
  resolve the actual field before invoking field click handlers.
- `Action.request()` represents a request trigger. Web routing still owns the
  request lifecycle, response, and route handler invocation.
- A performed resize, focus, or clipboard action invokes matching hooks; it
  does not resize a physical terminal, focus an operating-system window, or
  write to the system clipboard.

Use actions when code needs to name or synthesize *what should happen*. Use
the host's device and cursor APIs when code needs to directly control the
underlying interface.

Continue with [Hooks](hooks.md) for the complete event-hook model, or see the
[`xnano.core.actions` reference](../api/core/actions.md) for every action type
and helper method.
