---
title: "Actions"
icon: "lucide/play"
---

# Actions

An event is what the host observed. An [Action]{data-preview} is a named
trigger your app cares about — and something you can perform as synthetic
input.

Define a binding once; reuse it across hooks, tests, and hosts.

```python title="Naming a Trigger"
from xnano import Action

SAVE = Action.keyboard("ctrl+s")
```

`SAVE` is an immutable value, not a callback.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: a real event or performed action travels through the same action matching and hook dispatch path">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="acd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="24" y="32" width="176" height="84" rx="12" />
  <text class="gcd-label" x="112" y="62" text-anchor="middle">real input</text>
  <text class="gcd-chrome-label" x="112" y="88" text-anchor="middle">Ctrl+S key event</text>

  <rect class="gcd-panel" x="24" y="164" width="176" height="84" rx="12" />
  <text class="gcd-label" x="112" y="194" text-anchor="middle">perform</text>
  <text class="gcd-chrome-label" x="112" y="220" text-anchor="middle">actions.perform(SAVE)</text>

  <line class="gcd-arrow" x1="200" y1="74" x2="284" y2="124" marker-end="url(#acd-arrow)" />
  <line class="gcd-arrow" x1="200" y1="206" x2="284" y2="156" marker-end="url(#acd-arrow)" />

  <rect class="gcd-panel gcd-panel-accent" x="296" y="86" width="192" height="108" rx="14" />
  <text class="gcd-label gcd-label-accent" x="392" y="120" text-anchor="middle">SAVE</text>
  <text class="gcd-chrome-label" x="392" y="146" text-anchor="middle">Action.keyboard</text>
  <text class="gcd-z-caption" x="392" y="172" text-anchor="middle">matches ctrl+s</text>

  <line class="gcd-arrow" x1="488" y1="140" x2="548" y2="140" marker-end="url(#acd-arrow)" />

  <rect class="gcd-panel" x="560" y="88" width="136" height="104" rx="14" />
  <text class="gcd-label" x="628" y="120" text-anchor="middle">hook</text>
  <text class="gcd-chrome-label" x="628" y="148" text-anchor="middle">@on_action(SAVE)</text>
  <text class="gcd-z-label gcd-z-label-on" x="628" y="172" text-anchor="middle">save()</text>
</svg>
</div>

## Binding an action

```python title="Binding an Action" hl_lines="3 5"
from xnano import Action, on_action

SAVE = Action.keyboard("ctrl+s") # (1)!

@on_action(SAVE) # (2)!
def save(self) -> None:
    self.dirty = False
    self.status = "saved"
```

1. Same binding grammar as `@on_keyboard`: `"enter"`, `"ctrl+s"`, `"alt+left"`, …
2. Changing `SAVE` updates every hook that references it.

Specialized decorators are fine for one-off bindings:

```python title="Actions and Specialized Hooks"
@on_action(Action.keyboard("escape"))
def close(self) -> None: ...

@on_keyboard("escape")
def close(self) -> None: ...
```

The same action can be bound on more than one grid:

```python title="Shared Trigger"
from xnano import Action, BaseGrid, on_action

SAVE = Action.keyboard("ctrl+s")

class Editor(BaseGrid):
    @on_action(SAVE)
    def save_document(self) -> None:
        self.status = "saved"

class Settings(BaseGrid):
    @on_action(SAVE)
    def save_preferences(self) -> None:
        self.status = "preferences saved"
```

## Performing an action

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: perform injects a synthetic event into the same dispatch path">
<svg viewBox="0 0 440 90" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="pf-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel" x="16" y="20" width="110" height="50" rx="10" />
  <text class="gcd-chrome-label" x="71" y="50" text-anchor="middle">perform(SAVE)</text>
  <line class="gcd-arrow" x1="126" y1="45" x2="176" y2="45" marker-end="url(#pf-arr)" />
  <rect class="gcd-panel gcd-panel-accent" x="188" y="20" width="100" height="50" rx="10" />
  <text class="gcd-chrome-label" x="238" y="50" text-anchor="middle">dispatch</text>
  <line class="gcd-arrow" x1="288" y1="45" x2="338" y2="45" marker-end="url(#pf-arr)" />
  <rect class="gcd-window" x="350" y="20" width="72" height="50" rx="10" />
  <text class="gcd-chrome-label" x="386" y="50" text-anchor="middle">hooks</text>
</svg>
</div>

The host turns an action into an event on the same path as real input.

```python title="Performing an Action" hl_lines="2 6"
from xnano import Context, on_keyboard

terminal.actions.perform(SAVE) # (1)!

@on_keyboard("f2")
def save_from_shortcut(self, ctx: Context) -> None:
    ctx.actions.perform(SAVE) # (2)!
```

1. Useful in tests and host code that holds a `Terminal`.
2. Inside a hook, `ctx.actions` is bound to the active runtime.

The performer (`terminal.actions` / `ctx.actions`) has four entry points:

| Method | Role |
|--------|------|
| `perform(action)` | Queue any `Action` instance |
| `keyboard(*bindings, kind="press")` | Shortcut for `Action.keyboard` |
| `click(field=None, button="left")` | Shortcut for `Action.click` |
| `request(method, path="/")` | Shortcut for `Action.request` |

Other families (focus, clipboard, tick, resize, mouse) are built with
`Action.*` and passed to `perform`:

```python
ctx.actions.perform(Action.focus("search", kind="gained"))
ctx.actions.perform(Action.tick(16))
ctx.actions.perform(Action.clipboard("pasted text"))
```


<interactive />

??? tip "Try editing the code!"

    - Change the initial `count` default.
    - Perform `INCREMENT` a third time before the final render.

```pyodide install="xnano>=1.2.3b2" height="12"
from xnano import Action, BaseGrid, Field, Terminal, on_action

INCREMENT = Action.keyboard("right")

class Counter(BaseGrid, border="rounded", title=" action ", padding=1):
    label: str = Field(default="count: 0", horizontal_align="center")
    count: int = Field(default=0, state=True)

    @on_action(INCREMENT)
    def increment(self) -> None:
        self.count += 1
        self.label = f"count: {self.count}"

counter = Counter()
terminal = Terminal()
terminal.render(counter)
terminal.actions.perform(INCREMENT)
terminal.actions.perform(INCREMENT)
terminal.render(counter)
```

??? warning "Avoid action loops"

    A performed action can trigger a hook that performs another action. Queueing
    is ordered, but a hook that always re-performs its own trigger is still a
    loop.

## Action families

| Builder | Matches | Specialized hook |
|---------|---------|------------------|
| `Action.keyboard(*bindings, kind=None)` | key press / release / repeat | `@on_keyboard` |
| `Action.mouse(*buttons, kind=None)` | mouse button or movement | `@on_mouse` |
| `Action.click(field=None, button="left")` | click | `@on_click` |
| `Action.focus(field=None, kind=None)` | focus change | `@on_focus` |
| `Action.clipboard(text=None)` | paste | `@on_clipboard` |
| `Action.tick(interval_ms=0)` | clock tick | `@on_tick` |
| `Action.resize(width=None, height=None)` | resize | `@on_resize` |
| `Action.request(method, path)` | HTTP route | [request hooks](requests.md) |

`matches(event)` tests an event; `to_event()` builds the synthetic payload for
`perform()`.

??? abstract "API"

    [`Action`](../api/xnano/actions.md){data-preview} ·
    [`Context`](../api/xnano/context.md){data-preview}

[Action]: ../api/xnano/actions.md
[Context]: ../api/xnano/context.md
