---
title: "State"
icon: "lucide/database"
---

# State

xnano splits **data that paints** from **data that does not**, and gives you
two places to keep the latter: on a single grid, or shared across the whole
app.

That is what this page is about — not the optional
[`xnano.state.State`](../api/xnano/state.md){data-preview} helper class (a thin
bag for dynamic attributes). Most apps use a normal dataclass (or any object)
for application state.

## Two kinds of state

| Kind | Where it lives | Paints? | Shared? |
|------|----------------|---------|---------|
| **Application state** | `Terminal(state=...)` / `Web(state=...)` | No | Every grid and hook via `ctx.state` |
| **Grid state** | `Field(state=True)` on one grid | No | Only that grid instance |

Painted fields (`str`, components, nested grids) are the UI. State fields and
application state are the model. Hooks and `grid_render` move data between
them.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: application state shared to hooks; grid state stays on one grid; painted fields receive updates">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="st-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel gcd-panel-accent" x="40" y="40" width="200" height="100" rx="14" />
  <text class="gcd-label gcd-label-accent" x="140" y="78" text-anchor="middle">app state</text>
  <text class="gcd-chrome-label" x="140" y="108" text-anchor="middle">Terminal(state=…)</text>

  <rect class="gcd-panel" x="40" y="160" width="200" height="72" rx="14" />
  <text class="gcd-label" x="140" y="192" text-anchor="middle">Field(state=True)</text>
  <text class="gcd-chrome-label" x="140" y="216" text-anchor="middle">one grid only</text>

  <line class="gcd-arrow" x1="240" y1="90" x2="300" y2="90" marker-end="url(#st-arrow)" />
  <line class="gcd-arrow" x1="240" y1="196" x2="300" y2="160" marker-end="url(#st-arrow)" />

  <rect class="gcd-panel" x="312" y="72" width="168" height="120" rx="14" />
  <text class="gcd-label" x="396" y="118" text-anchor="middle">hooks</text>
  <text class="gcd-chrome-label" x="396" y="148" text-anchor="middle">ctx.state · self.*</text>

  <line class="gcd-arrow" x1="480" y1="132" x2="540" y2="132" marker-end="url(#st-arrow)" />

  <rect class="gcd-window" x="552" y="56" width="140" height="152" rx="12" />
  <rect class="gcd-chrome" x="552" y="56" width="140" height="24" rx="12" />
  <rect class="gcd-chrome" x="552" y="68" width="140" height="12" />
  <text class="gcd-chrome-label" x="622" y="72" text-anchor="middle">painted fields</text>
  <text class="gcd-z-label gcd-z-label-on" x="622" y="120" text-anchor="middle">label · list</text>
  <text class="gcd-z-label gcd-z-label-on" x="622" y="148" text-anchor="middle">visible · style</text>
</svg>
</div>

## Application state

Hand any object to the host once. Every hook on every grid sees the **same
instance** as `ctx.state`.

```python title="Application state"
import dataclasses

from xnano import BaseGrid, Context, Field, Terminal, on_keyboard

@dataclasses.dataclass
class AppState:
    count: int = 0
    title: str = "Counter"

class Counter(BaseGrid):
    label: str = Field(default="0", height=1)

    @on_keyboard("up")
    def inc(self, ctx: Context[AppState]) -> None:
        ctx.state.count += 1
        self.label = str(ctx.state.count)

Terminal(state=AppState()).run(Counter())
```

Use application state when **more than one grid** needs the same data (a note
list and an editor, a selection index and a detail panel).

- `Web(state=...)` works the same way for browser sessions.
- Type hooks as `Context[AppState]` so `ctx.state` is checked.
- `ctx.get_state()` returns the same object and raises if nothing was attached.

A full walkthrough lives in [Getting Started](../getting-started.md#state).

### Optional `State` helper

If you do not want a fixed schema:

```python
from xnano.state import State  # not exported from the package root

state = State(name="John", count=0)
state.count += 1
Terminal(state=state).run(App())
```

Prefer a dataclass or Pydantic model when the shape is known.

## Grid state (`Field(state=True)`)

A state field is typed data on **one** grid. It never claims a layout slot.

```python title="Grid state"
from xnano import BaseGrid, Field, Terminal, on_keyboard

class Counter(BaseGrid, direction="vertical"):
    label: str = Field(default="Count: 0", height=1)
    count: int = Field(default=0, state=True) # (1)!

    @on_keyboard("up")
    def inc(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"

Terminal().run(Counter())
```

1. Assigning to `count` schedules a repaint of this grid. The value itself is
   never drawn unless you copy it into a painted field (here, `label`).

Use grid state for local UI state: open/closed flags, local counters, temporary
buffers that no sibling grid needs.

### Plain attributes

```python
class Card(BaseGrid):
    heading: str = Field(default="Hello")
    tags: list[str] = ["a", "b"]  # never painted, no Field metadata
```

A plain attribute is normal Python. Use `Field(state=True)` when you want
`Field` defaults / validation metadata and repaint-on-assign behavior.

## Keeping the UI in sync

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: app state flows through grid_render into painted fields">
<svg viewBox="0 0 460 100" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="sy-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel" x="16" y="24" width="100" height="52" rx="10" />
  <text class="gcd-chrome-label" x="66" y="54" text-anchor="middle">ctx.state</text>
  <line class="gcd-arrow" x1="116" y1="50" x2="160" y2="50" marker-end="url(#sy-arr)" />
  <rect class="gcd-panel gcd-panel-accent" x="172" y="24" width="120" height="52" rx="10" />
  <text class="gcd-chrome-label" x="232" y="54" text-anchor="middle">grid_render</text>
  <line class="gcd-arrow" x1="292" y1="50" x2="336" y2="50" marker-end="url(#sy-arr)" />
  <rect class="gcd-window" x="348" y="24" width="96" height="52" rx="10" />
  <text class="gcd-chrome-label" x="396" y="54" text-anchor="middle">fields</text>
</svg>
</div>

State does not paint itself. Refresh painted fields from state each frame with
`grid_render`, or update them in hooks.

```python title="grid_render from application state"
from xnano import BaseGrid, Context, Field

class Dashboard(BaseGrid):
    stats: str = Field(default="")

    def grid_render(self, ctx: Context[AppState]) -> None:
        self.stats = f"{ctx.state.count} items"
```

Drive layout metadata from state with `grid_set_field` (visibility, title,
size, and so on):

```python title="Show a panel from state"
def grid_render(self, ctx: Context[AppState]) -> None:
    self.grid_set_field("editor", visible=ctx.state.editing)
```

See [Fields](fields.md) and [Grids](grids.md) for `grid_render` /
`grid_set_field` details.

## Focus groups

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: a group name addresses a field for focus">
<svg viewBox="0 0 440 110" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="fg-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel gcd-panel-accent" x="20" y="28" width="100" height="54" rx="10" />
  <text class="gcd-label gcd-label-accent" x="70" y="60" text-anchor="middle">group</text>
  <line class="gcd-arrow" x1="120" y1="55" x2="180" y2="55" marker-end="url(#fg-arr)" />
  <rect class="gcd-window" x="192" y="20" width="220" height="70" rx="10" />
  <rect class="gcd-cell-highlight-strong" x="208" y="36" width="188" height="38" rx="6" />
  <text class="gcd-z-label gcd-z-label-on" x="302" y="60" text-anchor="middle">Field(group="body")</text>
</svg>
</div>

`group=` is not state storage — it **names** a field so focus and some events
can find it across the tree.

```python title="group="
from xnano.components.input import Input

class Editor(BaseGrid):
    title: Input = Field(
        default_factory=lambda: Input(placeholder="Title"),
        group="title",
        height=1,
    )
    body: Input = Field(
        default_factory=lambda: Input(placeholder="Body", multiline=True),
        group="body",
    )
```

From a hook:

```python
ctx.focus("body")   # or ctx.runtime.focus("body")
ctx.blur()
```

Fields that share a `group` string on different grids are addressed together
by `ctx.focus(group)`, `@on_focus(group=...)`, and `@on_click(group=...)`.

`autofocus=True` prefers that field when nothing else is focused yet.

## Style and `class_name`

Painted fields can take style keywords or a Tailwind-like `class_name`. That is
presentation of the slot, not the state store — but it is often driven *from*
state in `grid_render` or hooks.

```python title="class_name and keywords"
# Static chrome
status: str = Field(
    default="ok",
    class_name="text-emerald-400 p-1 rounded-lg",
)

# Or keywords (same Style system — see Styling)
status: str = Field(default="ok", foreground="emerald-400", padding=1)
```

Change chrome at runtime when state changes:

```python
def grid_render(self, ctx: Context[AppState]) -> None:
    foreground = "emerald-400" if ctx.state.ok else "rose-400"
    self.grid_set_field("status", foreground=foreground)
    # or: self.status = "ok" / "error" and keep style fixed
```

Full style vocabulary: [Styling](styling.md).

## Related field knobs

These often travel with state-driven UIs:

| Keyword | Role |
|---------|------|
| `state=True` | Data only; no paint slot |
| `visible=` | Show or hide a painted field (often from app state) |
| `group=` | Focus / click / scroll target name |
| `autofocus=` | Default focus candidate |
| `overlay=` / `z=` | Floating panels driven by open/close state |
| `class_name=` / style keywords | How a painted slot looks |
| `scroll=` | Window overflow; drive with `ctx.scroll(group)` |

## Choosing where data lives

| Situation | Prefer |
|-----------|--------|
| Shared by several grids or hosts | Application `state=` |
| Local to one grid (counter, flag) | `Field(state=True)` |
| Shown on screen | Painted `Field` (maybe filled from state in `grid_render`) |
| One-off private Python value | Plain attribute |

## Next

- [Fields](fields.md) — slots and `Field(...)`
- [Context](context.md) — `ctx.state` inside hooks
- [Events & Hooks](events.md) — mutate state from input
- [Getting Started](../getting-started.md) — notes app using both kinds

??? abstract "API"

    [`Field`](../api/xnano/fields.md){data-preview} ·
    [`Context`](../api/xnano/context.md){data-preview} ·
    [`Terminal`](../api/xnano/terminal.md){data-preview} ·
    [`State`](../api/xnano/state.md){data-preview} ·
    [`BaseGrid`](../api/xnano/grids.md){data-preview}
