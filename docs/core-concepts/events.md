---
title: "Events & Hooks"
icon: "lucide/zap"
---

# Events & Hooks

A method wrapped in an `@on_*` decorator is a **hook**. It runs when something
matching its filter happens on the live host: a key, a click, a tick, and so on.

Hooks live on the grid they affect. There is no separate event bus to register
with — declare the method on the `BaseGrid` subclass and the host dispatches
into it.

Decorators are imported from `xnano` (or `xnano.hooks`). Event **payload
types** live in [`xnano.events`](../api/xnano/events.md){data-preview}
(`KeyboardEventData`, `MouseEventData`, …).

```python
from xnano import on_keyboard, on_tick, on_click
# or: from xnano.hooks import on_keyboard, on_tick, on_click
```

<div class="grid-concept-diagram" role="img" aria-label="Diagram: host events wire straight into decorated methods on the grid — no central event bus">
<svg viewBox="0 0 720 250" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="ecd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="24" y="36" width="200" height="180" rx="14" />
  <text class="gcd-label" x="124" y="64" text-anchor="middle">host</text>

  <rect class="gcd-window" x="48" y="84" width="152" height="36" rx="8" />
  <text class="gcd-chrome-label" x="124" y="106" text-anchor="middle">key · click · tick</text>

  <rect class="gcd-window" x="48" y="132" width="152" height="36" rx="8" />
  <text class="gcd-chrome-label" x="124" y="154" text-anchor="middle">focus · resize · paste</text>

  <text class="gcd-z-caption" x="124" y="196" text-anchor="middle">what happened</text>

  <line class="gcd-arrow" x1="224" y1="126" x2="300" y2="126" marker-end="url(#ecd-arrow)" />
  <text class="gcd-z-caption" x="262" y="114" text-anchor="middle">match</text>

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

## All Events

Unfiltered: fires on **every** event the host delivers. You inspect
`ctx.event` yourself.

```python title="All events" hl_lines="7"
from xnano import BaseGrid, Field, Terminal, on_event

class Debug(BaseGrid):
    last: str = Field(default="—", height=1)

    @on_event
    def observe(self, ctx) -> None:
        self.last = ctx.event.type  # "keyboard", "mouse", "tick", …

Terminal().run(Debug())
```

Reach for specialized decorators when a filter exists — `@on_event` is for
logging, instrumentation, or multi-kind handlers that branch on
`ctx.has_keyboard_event()` / `ctx.has_mouse_event()` / …

## Context

Add a second parameter and xnano passes a [Context](context.md):

```python title="Context on a hook" hl_lines="4 5"
from xnano import Context, on_keyboard

@on_keyboard("q")
def quit(self, ctx: Context) -> None: # (1)!
    ctx.runtime.request_exit() # (2)!
```

1. Annotations are optional for dispatch; they help type checkers.
2. Prefer `ctx.runtime` for focus, exit, and host controls. `ctx.terminal` is
   the same runtime object under an older name.

Typed payloads when the hook was triggered by that kind of event:

| Attribute | Payload |
|-----------|---------|
| `ctx.keyboard_event` | `KeyboardEventData` or `None` |
| `ctx.mouse_event` | `MouseEventData` or `None` |
| `ctx.tick_event` | `TickEventData` or `None` |

Deprecated aliases still work: `ctx.keyboard`, `ctx.mouse`, `ctx.tick`. Prefer
the `*_event` names in new code.

A hook that takes only `self` gets no extra arguments. `ctx` is optional on
every decorator form.

## Grid hooks vs component input

App policy belongs on the **grid**: `@on_keyboard`, `@on_click`, `@on_action`,
and friends. Components may implement `handle_keyboard` / `handle_paste` for
widget-local consumption (editors, lists) while focused — return `True` only
when the event is handled.

```python title="Grid owns activation; component may consume keys"
from xnano import BaseGrid, Field, on_click, on_keyboard
from xnano.components.button import Button

class Form(BaseGrid):
    submit: Button = Field(
        default_factory=lambda: Button(label="Save"),
        group="submit",
    )

    @on_click(group="submit")
    @on_keyboard("enter")
    def save(self, ctx) -> None:
        ...
```

`Button` leaves activation keys free so those hooks fire. Inputs can declare
`passthrough` / `submit_keys` for the same reason. See
[Components](components.md).

## Keyboard events

Runs when a matching binding is pressed (or released / repeated, if you filter
by `kind`).

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: key binding matches and calls a grid hook">
<svg viewBox="0 0 480 120" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="kb-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel" x="16" y="28" width="100" height="64" rx="10" />
  <text class="gcd-label" x="66" y="66" text-anchor="middle">ctrl+s</text>
  <line class="gcd-arrow" x1="116" y1="60" x2="168" y2="60" marker-end="url(#kb-arr)" />
  <rect class="gcd-panel gcd-panel-accent" x="180" y="28" width="120" height="64" rx="10" />
  <text class="gcd-label gcd-label-accent" x="240" y="66" text-anchor="middle">match</text>
  <line class="gcd-arrow" x1="300" y1="60" x2="352" y2="60" marker-end="url(#kb-arr)" />
  <rect class="gcd-window" x="364" y="28" width="100" height="64" rx="10" />
  <text class="gcd-chrome-label" x="414" y="56" text-anchor="middle">@on_keyboard</text>
  <text class="gcd-z-label gcd-z-label-on" x="414" y="76" text-anchor="middle">save()</text>
</svg>
</div>

```python title="Keyboard bindings" hl_lines="6 12 14 18"
from xnano import BaseGrid, Field, Terminal, on_keyboard

class Counter(BaseGrid, direction="vertical", gap=1):
    label: str = Field(default="Count: 0", height=1)
    hint: str = Field(
        default="↑ / ↓ to count · q to quit",
        height=1,
        foreground="slate-500",
    )

    count: int = Field(default=0, state=True) # (1)!

    @on_keyboard("up")
    def inc(self) -> None: # (2)!
        self.count += 1
        self.label = f"Count: {self.count}"

    @on_keyboard("down")
    def dec(self) -> None:
        self.count -= 1
        self.label = f"Count: {self.count}"

    @on_keyboard("q")
    def quit(self, ctx) -> None:
        ctx.runtime.request_exit()

Terminal().run(Counter())
```

1. `count` is state-only data on this grid (`state=True` — no paint slot).
2. A hook that takes only `self` gets no extra arguments.

### Binding grammar

Bindings are primary keys, optionally with `+`-joined modifiers:

| Example | Meaning |
|---------|---------|
| `"enter"`, `"escape"`, `"tab"`, `"space"` | Named keys |
| `"up"`, `"down"`, `"left"`, `"right"` | Arrows |
| `"a"`, `"1"`, `"f1"` | Character / function keys |
| `"ctrl+s"`, `"alt+enter"`, `"shift+tab"` | Modifier + key |
| `"ctrl+shift+z"` | Multiple modifiers |

Aliases: `"esc"` → `"escape"`, `"return"` → `"enter"`. Modifier names are
`ctrl`, `alt`, and `shift` (also accepted as bare bindings for the physical
modifier key press).

Pass several bindings to one handler:

```python title="Multiple bindings"
@on_keyboard("j", "down")
def move_down(self) -> None:
    ...
```

Filter by transition with `kind=`:

```python title="kind= on keyboard"
@on_keyboard("space", kind="press")   # default filter is any kind if omitted
def jump(self) -> None:
    ...

@on_keyboard("ctrl+c", kind="release")
def on_release(self) -> None:
    ...
```

`kind` values: `"press"`, `"release"`, `"repeat"`.

When you need the payload:

```python title="Reading keyboard_event"
@on_keyboard("ctrl+s")
def save(self, ctx: Context) -> None:
    event = ctx.keyboard_event
    if event is None:
        return
    # event.binding, event.key, event.kind, event.modifiers, event.character
    self.status = f"saved via {event.binding}"
```

## Mouse and click events

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: pointer click targets a field group">
<svg viewBox="0 0 400 100" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="ms-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <circle class="gcd-dot" cx="56" cy="50" r="8" />
  <path class="gcd-line" d="M62 56 L96 72" stroke-width="2" stroke-linecap="round" />
  <line class="gcd-arrow" x1="108" y1="50" x2="168" y2="50" marker-end="url(#ms-arr)" />
  <rect class="gcd-cell-highlight-strong" x="180" y="28" width="100" height="44" rx="8" />
  <text class="gcd-z-label gcd-z-label-on" x="230" y="54" text-anchor="middle">submit</text>
  <line class="gcd-arrow" x1="280" y1="50" x2="320" y2="50" marker-end="url(#ms-arr)" />
  <text class="gcd-chrome-label" x="360" y="54" text-anchor="middle">@on_click</text>
</svg>
</div>


Pointer input is **off by default**. Enable it on the host:

```python
Terminal(mouse_events=True).run(App())
```

### Mouse movement and buttons

Filters by button and optional `kind` / field region. Defaults to **left-button
press** when button and kind are omitted.

```python title="Mouse button filter" hl_lines="10 14"
from xnano import BaseGrid, Field, Terminal, on_mouse

class Menu(BaseGrid, direction="vertical"):
    status: str = Field(default="right-click for menu", height=1)

    @on_mouse("right", kind="press")
    def open_menu(self) -> None:
        self.status = "context menu"

    @on_mouse(kind="scroll_up")
    def scroll_up(self) -> None:
        ...

Terminal(mouse_events=True).run(Menu())
```

`kind` values: `"press"`, `"release"`, `"drag"`, `"move"`, `"scroll_up"`,
`"scroll_down"`, `"scroll_left"`, `"scroll_right"`.

Buttons: `"left"`, `"right"`, `"middle"`. Move and scroll kinds report no
button — a button filter would never match them.

Scope to a field's painted region with `field=`:

```python title="Mouse on a field region"
@on_mouse("left", field="sidebar", kind="press")
def select_sidebar(self, ctx) -> None:
    ...
```

### Clicks

Convenience for a press on a **field** or a **group**. Requires either a field
name or `group=`.

```python title="Click by field or group" hl_lines="11 14"
from xnano import BaseGrid, Field, Terminal, on_click
from xnano.components.button import Button

class Toolbar(BaseGrid, direction="horizontal", gap=1):
    save: Button = Field(
        default_factory=lambda: Button(label="Save"),
        group="save",
        height=1,
    )
    body: str = Field(default="Click Save or this body", border="rounded")

    @on_click(group="save") # (1)!
    def do_save(self) -> None:
        self.body = "saved"

    @on_click("body") # (2)!
    def highlight_body(self) -> None:
        self.body = "body clicked"

Terminal(mouse_events=True).run(Toolbar())
```

1. Group-scoped: fires when any field with `Field(group="save")` is clicked,
   including across nested grids.
2. Field-scoped: binds to the `body` field on this grid class.

Optional kwargs on `@on_click`: `button=` (default `"left"`), `kind=`
(default `"press"`).

```python
@on_click(group="rows", button="left", kind="press")
def select_row(self, ctx) -> None:
    mouse = ctx.mouse_event
    ...
```

## Timers and frame ticks

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: clock ticks fire a hook on an interval">
<svg viewBox="0 0 400 110" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="tk-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <circle class="gcd-panel" cx="70" cy="55" r="36" />
  <path class="gcd-line" d="M70 55 L70 32" stroke-width="2.5" stroke-linecap="round" />
  <path class="gcd-line" d="M70 55 L88 55" stroke-width="2.5" stroke-linecap="round" />
  <text class="gcd-chrome-label" x="70" y="98" text-anchor="middle">1000 ms</text>
  <line class="gcd-arrow" x1="116" y1="55" x2="180" y2="55" marker-end="url(#tk-arr)" />
  <rect class="gcd-panel gcd-panel-accent" x="192" y="28" width="180" height="54" rx="10" />
  <text class="gcd-label gcd-label-accent" x="282" y="60" text-anchor="middle">@on_tick → update()</text>
</svg>
</div>

Clock / frame timing. Pass an interval in **milliseconds**, or bare
`@on_tick` for every frame.

```python title="Interval tick" hl_lines="8"
import time

from xnano import BaseGrid, Field, Terminal, on_tick

class Clock(BaseGrid, direction="vertical"):
    display: str = Field(default="", height=3, border="rounded", title=" Time ")

    @on_tick(1000) # (1)!
    def update(self) -> None:
        self.display = time.strftime("  %H:%M:%S")

Terminal().run(Clock())
```

1. Interval in milliseconds. Bare `@on_tick` (or interval `0`) fires every
   frame.

Keyword form is equivalent:

```python
@on_tick(interval_milliseconds=250)
def pulse(self) -> None:
    ...
```

Payload: `ctx.tick_event` → `TickEventData` with `elapsed_ms`.

## Focus changes

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: focus moves to a named group on a field">
<svg viewBox="0 0 480 120" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="fc-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel" x="20" y="28" width="120" height="64" rx="10" />
  <text class="gcd-chrome-label" x="80" y="56" text-anchor="middle">ctx.focus</text>
  <text class="gcd-z-label gcd-z-label-on" x="80" y="76" text-anchor="middle">"body"</text>
  <line class="gcd-arrow" x1="140" y1="60" x2="200" y2="60" marker-end="url(#fc-arr)" />
  <rect class="gcd-window" x="212" y="20" width="240" height="80" rx="10" />
  <rect class="gcd-z-base" x="228" y="40" width="88" height="40" rx="6" />
  <text class="gcd-chrome-label" x="272" y="64" text-anchor="middle">title</text>
  <rect class="gcd-cell-highlight-strong" x="332" y="40" width="100" height="40" rx="6" />
  <text class="gcd-z-label gcd-z-label-on" x="382" y="64" text-anchor="middle">body</text>
</svg>
</div>

Two scopes:

| Form | Fires on |
|------|----------|
| Bare `@on_focus` | OS-level **window** focus gained / lost |
| `@on_focus("field")` / `field=` | Application **field** focus |
| `@on_focus(group=...)` | Any field sharing that `Field(group=...)` |

Filter with `kind="gained"` or `kind="lost"`.

```python title="Window and field focus" hl_lines="8 12"
from xnano import BaseGrid, Context, Field, Terminal, on_focus
from xnano.components.input import Input

class Search(BaseGrid, direction="vertical", gap=1):
    status: str = Field(default="unfocused", height=1, foreground="slate-500")
    query: Input = Field(default_factory=Input, group="search", height=1)

    @on_focus(kind="gained") # (1)!
    def window_in(self) -> None:
        self.status = "window focused"

    @on_focus("query", kind="gained") # (2)!
    def search_in(self, ctx: Context) -> None:
        self.status = "search focused"
        ctx.cursor.visible = False

    @on_focus(group="search", kind="lost")
    def search_out(self) -> None:
        self.status = "search blurred"

Terminal().run(Search())
```

1. Window-level terminal focus (host must report focus-change events).
2. Field name on this grid. Prefer `group=` when the same label is shared
   across nested grids — same string as `Field(group=...)`.

`ctx.focus("search")` / `ctx.blur()` move field focus from any hook. See
[State](state.md) for focus groups.

## Window resize

Fires when the host viewport changes size.

```python title="Resize" hl_lines="7"
from xnano import BaseGrid, Field, Terminal, on_resize

class Layout(BaseGrid):
    info: str = Field(default="", height=1)

    @on_resize
    def on_size(self, ctx) -> None:
        w, h = ctx.device.size.width, ctx.device.size.height
        self.info = f"{w} × {h}"

Terminal().run(Layout())
```

Resize payload is on `ctx.event.resize_event` (`width`, `height` in cells).
`ctx.device.size` tracks the same viewport.

## Clipboard paste

Fires on paste / clipboard input (bracketed paste when the host supports it).

```python title="Paste" hl_lines="7"
from xnano import BaseGrid, Field, Terminal, on_clipboard

class PasteTarget(BaseGrid):
    preview: str = Field(default="paste something", border="rounded")

    @on_clipboard
    def accept(self, ctx) -> None:
        event = ctx.event.clipboard_event
        text = event.text if event is not None else ""
        self.preview = (text or "")[:80]

Terminal().run(PasteTarget())
```

To **write** the system clipboard from a hook, use
`ctx.device.copy_to_clipboard(text)` — see [Device](device.md).

## State and field conditions

Watch shared application state or this grid's own fields. Two expression
shapes:

| Expression | Behavior |
|------------|----------|
| Bare name (`"count"`, `"user.name"`) | Fire **once per mutation** of that value |
| Predicate (`"count > 0"`) | Fire **every frame** the expression is truthy |

### Application state

Evaluated against `ctx.state` (the object passed to `Terminal(state=...)` /
`Web(state=...)`).

```python title="Watch application state" hl_lines="14 18"
import dataclasses

from xnano import BaseGrid, Context, Field, Terminal, on_keyboard, on_state

@dataclasses.dataclass
class AppState:
    count: int = 0

class Counter(BaseGrid, direction="vertical", gap=1):
    label: str = Field(default="0", height=1)
    banner: str = Field(default="", height=1, foreground="emerald-400")

    @on_keyboard("up")
    def inc(self, ctx: Context[AppState]) -> None:
        ctx.state.count += 1
        self.label = str(ctx.state.count)

    @on_state("count") # (1)!
    def count_changed(self, ctx: Context[AppState]) -> None:
        self.banner = f"changed → {ctx.state.count}"

    @on_state("count > 5") # (2)!
    def high(self, ctx: Context[AppState]) -> None:
        self.banner = "high"

Terminal(state=AppState()).run(Counter())
```

1. Mutation form: once when `count` changes.
2. Expression form: every frame while truthy.

### Grid field values

Same rules against **this grid's** fields (`self.count`, nested attributes /
indexing as the expression language allows).

```python title="Watch grid fields" hl_lines="10 14"
from xnano import BaseGrid, Field, Terminal, on_field, on_keyboard

class Cart(BaseGrid, direction="vertical"):
    total: int = Field(default=0, state=True)
    status: str = Field(default="empty", height=1)

    @on_keyboard("a")
    def add(self) -> None:
        self.total += 1

    @on_field("total") # (1)!
    def total_changed(self) -> None:
        self.status = f"total={self.total}"

    @on_field("total > 0") # (2)!
    def ready(self) -> None:
        self.status = "checkout ready"

Terminal().run(Cart())
```

1. Fires once when `total` is assigned a new value.
2. Fires every frame while `total > 0`.

Prefer bare names when you only need to react to changes; prefer expressions
when a continuous “while true” condition is intentional. See [State](state.md).

## Background polling

Background / idle work. Default is `when="idle"` (once per idle event wait).
Pass `when="frame"` to run every frame.

```python title="Idle poll" hl_lines="8"
from xnano import BaseGrid, Field, Terminal, on_poll

class Worker(BaseGrid):
    status: str = Field(default="idle", height=1)
    _n: int = 0

    @on_poll # (1)!
    def pump(self) -> None:
        self._n += 1
        if self._n % 30 == 0:
            self.status = f"idle pumps: {self._n}"

    @on_poll("frame") # (2)!
    def every_frame(self) -> None:
        ...

Terminal().run(Worker())
```

1. Same as `@on_poll("idle")` / `@on_poll(when="idle")`.
2. Keyword form: `@on_poll(when="frame")`.

Use idle for cheap housekeeping that should not thrash every paint. Use frame
when the work must stay locked to the render cycle (prefer `@on_tick` when you
need a fixed millisecond interval).

## Named actions

Bind a named [Action](actions.md) instead of repeating a binding string.
Events answer *what happened*; actions name *what your app cares about* and
can also be performed as synthetic input.

```python title="Named action" hl_lines="3 5"
from xnano import Action, BaseGrid, Field, Terminal, on_action

SAVE = Action.keyboard("ctrl+s") # (1)!

class Editor(BaseGrid):
    status: str = Field(default="unsaved", height=1)

    @on_action(SAVE) # (2)!
    def save(self) -> None:
        self.status = "saved"

Terminal().run(Editor())
```

1. Same binding grammar as `@on_keyboard`.
2. Changing `SAVE` updates every hook that references it.

`@on_action` accepts keyboard, mouse/click, focus, clipboard, resize, and tick
actions. Full perform/match API: [Actions](actions.md).

## HTTP requests

HTTP is a separate surface: `@on_get_request`, `@on_post_request`, and related
decorators live in `xnano.requests`, not `xnano.hooks`. They run when a grid is
served under [Web](web.md) or a request server — a plain `Terminal` session
does not open ports.

See [HTTP Requests](requests.md).

## Decorator index

| Decorator | Role |
|-----------|------|
| `@on_keyboard` | Key bindings (`kind=`, multiple bindings) |
| `@on_mouse` / `@on_click` | Pointer (`Terminal(..., mouse_events=True)`) |
| `@on_tick` | Clock interval (ms) or every frame |
| `@on_focus` | Window or field focus (`kind=`, `group=`) |
| `@on_resize` | Host resize |
| `@on_clipboard` | Paste |
| `@on_state` / `@on_field` | Expression / mutation watch |
| `@on_poll` | Idle or every frame |
| `@on_event` | All events (no filter) |
| `@on_action(...)` | Named [Action](actions.md) |
| `@on_get_request` / … | HTTP — [Requests](requests.md) |

Live event loops need a real terminal (or web host). Static
`render(...)` / `Terminal().render(...)` examples paint one frame and do not
drive hooks that require input or time.

## Next

- [Context](context.md) — `ctx` attributes and state typing
- [Actions](actions.md) — named triggers and `perform`
- [State](state.md) — application state, field state, focus groups
- [Components](components.md) — `handle_keyboard` vs grid hooks
- [Terminal](terminal.md) — `mouse_events=`, tick interval, `run`

??? abstract "API"

    [`xnano.hooks`](../api/xnano/hooks.md){data-preview} ·
    [`xnano.events`](../api/xnano/events.md){data-preview} ·
    [`Context`](../api/xnano/context.md){data-preview} ·
    [`Action`](../api/xnano/actions.md){data-preview} ·
    [`xnano.requests`](../api/xnano/requests.md){data-preview}

[Context]: context.md
[Action]: actions.md
