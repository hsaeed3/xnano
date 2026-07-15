---
title: "Events & Hooks"
icon: "lucide/zap"
---

# Events & Hooks

A grid isn't just laid out once. A method wrapped in one of xnano's `@on_*` decorators turns into a hook — fired whenever something happens to it, whether that's a key press, a click, or a tick of the clock.

Hooks live directly on the grid they affect, the same way a Pydantic validator lives on the model it validates.

There's no central event bus to register with, and no dispatch table to maintain. Decorate a method, and xnano wires it up the moment the grid is live.

A hook can react to:

- Keyboard presses <small>(`@on_keyboard`)</small>
- Mouse clicks and movement <small>(`@on_mouse`, `@on_click`)</small>
- The clock <small>(`@on_tick`)</small>
- Focus, resize, clipboard, and state changes <small>(`@on_focus`, `@on_resize`, `@on_clipboard`, `@on_state`)</small>

<div class="grid-concept-diagram" role="img" aria-label="Diagram: host events wire straight into decorated methods on the grid — no central event bus">
<svg viewBox="0 0 720 250" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="ecd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <!-- Host -->
  <rect class="gcd-panel" x="24" y="36" width="200" height="180" rx="14" />
  <text class="gcd-label" x="124" y="64" text-anchor="middle">host</text>

  <rect class="gcd-window" x="48" y="84" width="152" height="36" rx="8" />
  <text class="gcd-chrome-label" x="124" y="106" text-anchor="middle">key · click · tick</text>

  <rect class="gcd-window" x="48" y="132" width="152" height="36" rx="8" />
  <text class="gcd-chrome-label" x="124" y="154" text-anchor="middle">focus · resize · paste</text>

  <text class="gcd-z-caption" x="124" y="196" text-anchor="middle">what happened</text>

  <line class="gcd-arrow" x1="224" y1="126" x2="300" y2="126" marker-end="url(#ecd-arrow)" />
  <text class="gcd-z-caption" x="262" y="114" text-anchor="middle">match</text>

  <!-- Grid with hooks on methods -->
  <rect class="gcd-panel gcd-panel-accent" x="312" y="36" width="384" height="180" rx="14" />
  <text class="gcd-label gcd-label-accent" x="504" y="64" text-anchor="middle">grid</text>

  <rect class="gcd-window" x="340" y="86" width="152" height="48" rx="8" />
  <text class="gcd-chrome-label" x="416" y="106" text-anchor="middle">@on_keyboard</text>
  <text class="gcd-z-label gcd-z-label-on" x="416" y="124" text-anchor="middle">def inc(self)</text>

  <rect class="gcd-window" x="512" y="86" width="152" height="48" rx="8" />
  <text class="gcd-chrome-label" x="588" y="106" text-anchor="middle">@on_tick</text>
  <text class="gcd-z-label gcd-z-label-on" x="588" y="124" text-anchor="middle">def pulse(self)</text>

  <rect class="gcd-window" x="340" y="150" width="324" height="40" rx="8" />
  <text class="gcd-chrome-label" x="502" y="174" text-anchor="middle">hooks live on the grid — not a global bus</text>
</svg>
</div>

## Responding to Keys

`@on_keyboard` fires the decorated method whenever a matching key is pressed. Combine it with a `state=True` field from the last page, and a handler becomes a plain, live counter.

```python title="Responding to Keys" hl_lines="8 10 14"
from xnano import BaseGrid, Field, Terminal
from xnano.events import on_keyboard

class Counter(BaseGrid, direction="vertical", gap=1):
    label: str = Field(default="Count: 0", height=1)
    hint:  str = Field(default="↑ / ↓ to count", height=1, color="slate-500")

    count: int = Field(default=0, state=True) # (1)!

    @on_keyboard("up")
    def inc(self) -> None: # (2)!
        self.count += 1
        self.label = f"Count: {self.count}"

    @on_keyboard("down")
    def dec(self) -> None:
        self.count -= 1
        self.label = f"Count: {self.count}"

Terminal().run(Counter())
```

1. Nothing new here — `count` is the same `state=True` field from the last page: live data, never painted directly.
2. A hook that takes just `self` is called with no extra arguments. Add a second parameter (covered next) when a handler needs more than the grid itself.

<div class="xnano-demo" markdown>
![counter dark](../assets/concepts/hooks_keyboard-dark.gif){.demo-dark}
![counter light](../assets/concepts/hooks_keyboard-light.gif){.demo-light}
</div>

## The Context Object

Add a second parameter to any hook, and xnano fills it with a [Context]{data-preview} — the event that fired, the live [Terminal]{data-preview}, and whatever application state you're tracking.

```python title="The Context Object" hl_lines="1 4 5"
from xnano import Context
from xnano.events import on_keyboard

@on_keyboard("q")
def quit(self, ctx: Context) -> None: # (1)!
    ctx.terminal.request_exit() # (2)!
```

1. Typing `ctx` as `Context` isn't required — xnano dispatches on the handler's *arity*, not its annotations — but it's what gets you autocomplete on `ctx.terminal`, `ctx.keyboard`, and everything else it carries.
2. `ctx.terminal` is the live `Terminal` running this grid; `request_exit()` ends its session.

<br/>

`Context` deserves its own page — its concept page covers what else it carries, and how to type it against your own application state.

## Reacting to the Clock

`@on_tick` fires on a repeating interval instead of a discrete event — useful for clocks, animations, or polling something in the background.

```python title="Reacting to the Clock" hl_lines="6"
import time
from xnano import BaseGrid, Field, Terminal
from xnano.events import on_tick

class Clock(BaseGrid, direction="vertical"):
    display: str = Field(default="", height=3, border="rounded", title=" Time ")

    @on_tick(1000) # (1)!
    def update(self) -> None:
        self.display = time.strftime("  %H:%M:%S")

Terminal().run(Clock())
```

1. The number is an interval in milliseconds. A bare `@on_tick` fires on every frame instead — pass a short interval (`16`, for roughly 60fps) for animation.

<div class="xnano-demo" markdown>
![clock dark](../assets/concepts/hooks_tick-dark.gif){.demo-dark}
![clock light](../assets/concepts/hooks_tick-light.gif){.demo-light}
</div>

??? abstract "More Ways to Bind"

    A few more hooks round out the set — each documented in full on the [events]{data-preview} API reference.

    - `@on_click("field_name")` — a click on a specific field's area.
    - `@on_focus` / `@on_focus("field_name")` — terminal window focus, or a field gaining/losing input focus.
    - `@on_resize` — the terminal was resized.
    - `@on_clipboard` — a paste event.
    - `@on_state("expression")` / `@on_field("expression")` — fires each tick when a Python expression evaluated against shared state (or the grid's own fields) comes out truthy.
    - `@on_poll` — fires on idle waits or every frame, for background work.
    - `@on_action(SAVE)` — bind a reusable [Action]{data-preview} (e.g. `Action.keyboard("ctrl+s")`) instead of repeating the same binding across handlers.

## Keep Going

The [Hooks & Actions guide](../hooks/index.md){data-preview} is the complete, example-led reference: every decorator gets its own page, beside the action that can represent the same trigger. It also covers state and polling hooks that intentionally have no action counterpart, plus the GET and POST hooks used by web grids.

??? abstract "Sandbox & API"

    **Sandbox**

    [Action-Driven Frames](../sandbox/rendering.md#action-driven-frames-without-run){data-preview}

    **API**

    [`events`](../api/xnano/events.md){data-preview} · [`Action`](../api/xnano/core/actions.md#xnano.core.actions.Action){data-preview} · [`Context`](../api/xnano/context.md#xnano.context.Context){data-preview}

[Context]: ../api/xnano/context.md
[Terminal]: ../api/xnano/tui/terminal.md
[Action]: ../api/xnano/core/actions.md
[events]: ../api/xnano/events.md
