---
title: "xnano.events"
---

::: xnano.events

## Actions

`events.py` describes *what happened* — a keypress, a click, a tick — after the fact. `xnano.core.actions` describes the same thing as a value: something you can build once, store, compare, and hand to `@on(...)` instead of repeating a binding across every handler that cares about it.

```python
from xnano.core.actions import Action
from xnano.events import on

SAVE = Action.keyboard("ctrl+s")

@on(SAVE)
def save(self, ctx) -> None:
    ...
```

<br/>

Every `@on_*` decorator in this module is really building one of these under the hood — `@on_keyboard("ctrl+s")` and `@on(Action.keyboard("ctrl+s"))` register the exact same hook.

### Action Types

Each event family gets its own frozen `Action` subclass, built through a classmethod on the base `Action` class:

| Classmethod | Returns | Matches |
|---|---|---|
| `Action.keyboard(*bindings, kind=None)` | `KeyboardAction` | A key binding, optionally filtered by press/release/repeat. |
| `Action.mouse(*buttons, kind=None)` | `MouseAction` | Any mouse button/kind combination. |
| `Action.click(field=None, button="left")` | `ClickAction` | A button press, optionally scoped to a layout field. |
| `Action.focus(field=None, kind=None)` | `FocusAction` | Terminal window or field focus changes. |
| `Action.clipboard(text=None)` | `ClipboardAction` | A paste event, optionally an exact match. |
| `Action.tick(interval_ms=0)` | `TickAction` | A host clock tick, at or below an interval. |
| `Action.resize(width=None, height=None)` | `ResizeAction` | A terminal resize, optionally an exact size. |
| `Action.request(method, path)` | `RequestAction` | An HTTP request to a web host route — no terminal equivalent. |

<br/>

Every subclass implements the same two-method contract: `matches(event)` — does this event satisfy the action's filters — and `to_event()`, which synthesizes an equivalent event. `to_event()` is what makes `Actions` (below) possible: performing an action means synthesizing its event and running it through the same dispatch pump a real one would take.

### Performing Actions

Hooks bind Actions to *reactions*. `Actions` — reached as `ctx.actions` — goes the other way: it lets code *perform* an action against the live host, as if the matching input had actually happened.

```python
@on_keyboard("ctrl+r")
def replay_save(self, ctx) -> None:
    ctx.actions.press("ctrl+s") # (1)!
```

1. `ctx.actions.press(...)` synthesizes a keyboard event and runs it through the same dispatch pump a real key press would — any `@on_keyboard("ctrl+s")` hook fires exactly as if the user had pressed it.

<br/>

`Actions` exposes one method per action family — `press`, `click`, `focus`, `paste`, `resize`, `tick`, and `request` — each a thin wrapper around the matching `Action.<name>(...)` builder plus `perform()`.

::: xnano.core.actions
