---
title: "Runtime Context"
icon: "lucide/key"
---

# Runtime Context

The second parameter on a hook is a [Context]{data-preview}: the event that
fired, application state, runtime/host controls, and related helpers.

You do not construct `Context` yourself. The host builds one per hook call.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: the host builds a Context bag of event, runtime, state, and device, then passes it into the hook">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="ctx-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="28" y="40" width="168" height="200" rx="14" />
  <text class="gcd-label" x="112" y="72" text-anchor="middle">host</text>
  <path class="gcd-line" d="M52 100 h88" stroke-width="3" stroke-linecap="round" />
  <path class="gcd-line-soft" d="M52 120 h120" stroke-width="3" stroke-linecap="round" />
  <path class="gcd-line-soft" d="M52 140 h72" stroke-width="3" stroke-linecap="round" />
  <text class="gcd-chrome-label" x="112" y="190" text-anchor="middle">builds ctx</text>
  <text class="gcd-chrome-label" x="112" y="210" text-anchor="middle">per hook call</text>

  <line class="gcd-arrow" x1="196" y1="140" x2="248" y2="140" marker-end="url(#ctx-arrow)" />

  <rect class="gcd-panel gcd-panel-accent" x="260" y="28" width="220" height="224" rx="14" />
  <text class="gcd-label gcd-label-accent" x="370" y="58" text-anchor="middle">Context</text>

  <rect class="gcd-window" x="284" y="78" width="172" height="32" rx="8" />
  <text class="gcd-chrome-label" x="370" y="98" text-anchor="middle">event</text>

  <rect class="gcd-window" x="284" y="120" width="172" height="32" rx="8" />
  <text class="gcd-chrome-label" x="370" y="140" text-anchor="middle">runtime / surface</text>

  <rect class="gcd-window" x="284" y="162" width="172" height="32" rx="8" />
  <text class="gcd-chrome-label" x="370" y="182" text-anchor="middle">state</text>

  <rect class="gcd-window" x="284" y="204" width="172" height="32" rx="8" />
  <text class="gcd-chrome-label" x="370" y="224" text-anchor="middle">device · cursor</text>

  <line class="gcd-arrow" x1="480" y1="140" x2="532" y2="140" marker-end="url(#ctx-arrow)" />

  <rect class="gcd-panel" x="544" y="88" width="152" height="104" rx="14" />
  <text class="gcd-label" x="620" y="124" text-anchor="middle">hook</text>
  <text class="gcd-z-label gcd-z-label-on" x="620" y="150" text-anchor="middle">def on_*(</text>
  <text class="gcd-z-label gcd-z-label-on" x="620" y="168" text-anchor="middle">self, ctx)</text>
</svg>
</div>

## Reading the event

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: context exposes typed event payloads">
<svg viewBox="0 0 400 100" xmlns="http://www.w3.org/2000/svg" fill="none">
  <rect class="gcd-panel gcd-panel-accent" x="20" y="20" width="100" height="60" rx="10" />
  <text class="gcd-label gcd-label-accent" x="70" y="55" text-anchor="middle">ctx</text>
  <rect class="gcd-window" x="148" y="16" width="112" height="28" rx="6" />
  <text class="gcd-chrome-label" x="204" y="34" text-anchor="middle">keyboard_event</text>
  <rect class="gcd-window" x="148" y="52" width="112" height="28" rx="6" />
  <text class="gcd-chrome-label" x="204" y="70" text-anchor="middle">mouse_event</text>
  <rect class="gcd-window" x="276" y="34" width="100" height="28" rx="6" />
  <text class="gcd-chrome-label" x="326" y="52" text-anchor="middle">tick_event</text>
</svg>
</div>

!!! abstract "Optional"

    Defining a ``ctx`` parameter on a hook is optional, all of these are
    accepted forms of defining a hook:

    ```python
    @on_tick(1000)
    def tick(self) -> None:
        ...

    @on_tick(1000)
    def tick(self, ctx: Context) -> None:
        ...

    @on_tick(1000)
    def tick(self, ctx: Context[SomeState]) -> None:
      ...
    ```

```python title="Reading the Event"
from xnano import Context, on_keyboard

@on_keyboard("enter")
def submit(self, ctx: Context) -> None:
    key = ctx.keyboard_event  # KeyboardEventData, or None
    runtime = ctx.runtime     # active Runtime
```

`ctx.keyboard_event` and `ctx.mouse_event` are set only when that kind of event
triggered the hook. A `@on_tick` handler sees `None` for both.

`ctx.surface` reports the presentation surface (`"terminal"`, `"web"`, or
offscreen).

## Typing Context by state

`Context` is generic over the object passed to `Terminal(state=...)` or
`Web(state=...)`. How application state relates to `Field(state=True)` and
painted fields is covered under [State](state.md).

```python title="Typing Context by State" hl_lines="4 9"
import dataclasses

from xnano import BaseGrid, Context, Field, Terminal, on_keyboard

@dataclasses.dataclass
class AppState:
    count: int = 0

class Counter(BaseGrid, direction="vertical"):
    label: str = Field(default="Count: 0", height=1)

    @on_keyboard("up")
    def inc(self, ctx: Context[AppState]) -> None: # (1)!
        ctx.state.count += 1 # (2)!
        self.label = f"Count: {ctx.state.count}"

Terminal(state=AppState()).run(Counter())
```

1. `Context[AppState]` is for type checkers; runtime behavior is unchanged.
2. `ctx.state` is the same object handed to the host. `ctx.get_state()` raises if
   no state was attached.

A plain dataclass or Pydantic model works. [`State`](../api/xnano/state.md) is
an optional convenience bag (not exported from the package root):

```python
from xnano.state import State

state = State(name="John", count=0)
```

## Other attributes

| Attribute / method | Role |
|--------------------|------|
| `ctx.event` | Full event object |
| `ctx.keyboard_event` / `ctx.mouse_event` / `ctx.tick_event` | Typed payloads (or `None`) |
| `ctx.request` | HTTP [`Request`](requests.md) when a request hook fired |
| `ctx.surface` | `"terminal"`, `"web"`, or `"offscreen"` |
| `ctx.device` / `ctx.cursor` | Host chrome ([Device](device.md)) |
| `ctx.actions` | Synthetic [actions](actions.md) (`perform`, `keyboard`, `click`, `request`) |
| `ctx.stage` | Layout map for advanced paint |
| `ctx.focus(group)` / `ctx.blur()` | Field focus by `Field(group=...)` |
| `ctx.focused_group` | Current focus group name |
| `ctx.scroll(group)` | Scroll handle for a named group |
| `ctx.call_soon(...)` | Schedule work on the runtime |
| `ctx.has_*_event()` | Predicates for keyboard, mouse, focus, resize, clipboard |

`ctx.terminal` / `ctx.host` are aliases for the same runtime object as
`ctx.runtime`. Prefer `ctx.runtime` in new code.

Deprecated aliases still work: `ctx.keyboard`, `ctx.mouse`, `ctx.tick`.

??? abstract "API"

    [`Context`](../api/xnano/context.md){data-preview} ·
    [`Action`](../api/xnano/actions.md){data-preview} ·
    [`Runtime`](../api/xnano/core/runtime.md){data-preview} ·
    [`State`](../api/xnano/state.md){data-preview}

[Context]: ../api/xnano/context.md
