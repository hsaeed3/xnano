---
title: "Components"
icon: "lucide/package"
---

# Components

A [component]{data-preview} is a small, reusable piece of content you put in a
`Field` — or paint on its own with `render()` / `Terminal`. A plain string is
enough for a label. Reach for a component when the slot needs structure,
interaction, or its own live attributes.

What makes components useful is how many **patterns** stack on the same idea:
nest styled pieces, declare schema on a subclass, keep attributes live, or
subclass `Component` for something entirely yours.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: a Field can hold a string or a component with its own attributes and structure">
<svg viewBox="0 0 720 220" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="ccd-cell" width="12" height="12" patternUnits="userSpaceOnUse">
      <path d="M 12 0 L 0 0 0 12" class="gcd-grid-line" />
    </pattern>
    <marker id="ccd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="40" y="60" width="160" height="100" rx="14" />
  <text class="gcd-label" x="120" y="100" text-anchor="middle">Field</text>
  <text class="gcd-chrome-label" x="120" y="128" text-anchor="middle">slot · chrome</text>

  <line class="gcd-arrow" x1="200" y1="110" x2="260" y2="110" marker-end="url(#ccd-arrow)" />

  <rect class="gcd-panel gcd-panel-accent" x="272" y="40" width="200" height="140" rx="14" />
  <text class="gcd-label gcd-label-accent" x="372" y="76" text-anchor="middle">component</text>
  <text class="gcd-chrome-label" x="372" y="108" text-anchor="middle">live attributes</text>
  <text class="gcd-chrome-label" x="372" y="132" text-anchor="middle">nest · declare · focus</text>

  <line class="gcd-arrow" x1="472" y1="110" x2="532" y2="110" marker-end="url(#ccd-arrow)" />

  <g transform="translate(544, 48)">
    <rect class="gcd-window" x="0" y="0" width="148" height="124" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="148" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="148" height="10" />
    <rect class="gcd-grid-fill" x="12" y="32" width="124" height="76" rx="4" />
    <rect x="12" y="32" width="124" height="76" rx="4" fill="url(#ccd-cell)" />
    <rect class="gcd-cell-highlight-strong" x="20" y="48" width="72" height="14" rx="2" />
    <rect class="gcd-z-base" x="20" y="72" width="100" height="14" rx="2" />
  </g>
</svg>
</div>

## In a field

Use `default_factory` when the default is a component instance (not a plain
immutable value):

```python title="Component as a field value"
from xnano import BaseGrid, Field
from xnano.components.loader import Loader
from xnano.components.options import Options

class Panel(BaseGrid, direction="vertical", gap=1):
    status: str = Field(default="Working…", height=1) # (1)!
    progress: Loader = Field(
        default_factory=lambda: Loader(value=0.4, style="bar"),
        height=1,
    )
    items: Options = Field(default_factory=Options, border="rounded")
```

1. A `str` field still paints as text — no component required.

Field chrome (`border`, `title`, `padding`, `group`, …) still applies around
whatever the component paints. See [Fields](fields.md) and [State](state.md).

<interactive />

??? tip "Try editing the code!"

    - Change `value=` on the `Loader` (0.0–1.0).
    - Change `style` to `"line"` or `"spinner"`.

```pyodide install="xnano>=1.2.3" height="11"
from xnano import BaseGrid, Field, render
from xnano.components.loader import Loader

class Panel(BaseGrid, direction="vertical", gap=1):
    status: str = Field(default="Working…", height=1)
    progress: Loader = Field(
        default_factory=lambda: Loader(value=0.4, style="bar"),
        height=1,
    )

render(Panel())
```

## Nested pieces

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: nested Text spans sit inside one line">
<svg viewBox="0 0 440 90" xmlns="http://www.w3.org/2000/svg" fill="none">
  <rect class="gcd-window" x="24" y="18" width="392" height="54" rx="10" />
  <rect class="gcd-cell-highlight-strong" x="40" y="32" width="48" height="26" rx="4" />
  <text class="gcd-z-label gcd-z-label-on" x="64" y="50" text-anchor="middle">●</text>
  <rect class="gcd-panel" x="96" y="32" width="120" height="26" rx="4" />
  <text class="gcd-chrome-label" x="156" y="50" text-anchor="middle">healthy</text>
  <rect class="gcd-z-base" x="224" y="32" width="80" height="26" rx="4" />
  <text class="gcd-chrome-label" x="264" y="50" text-anchor="middle">12ms</text>
</svg>
</div>

Several components accept nested content. `Text` is the usual example: a list
of `Text` (or strings) becomes independently styled runs in one line.

```python title="Nested Text"
from xnano.components.text import Text

Text([
    Text("● ", foreground="emerald-400"),
    Text("healthy ", modifiers=("bold",)),
    Text("12ms", foreground="slate-300"),
])
```

<interactive />

??? tip "Try editing the code!"

    - Change a nested `foreground`.
    - Change the status string.

```pyodide install="xnano>=1.2.3" height="8"
from xnano import render
from xnano.components.text import Text

render(Text([
    Text("● ", foreground="emerald-400"),
    Text("healthy ", foreground="white", modifiers=("bold",)),
    Text("12ms", foreground="slate-300"),
], background="slate-900"))
```

The same idea shows up elsewhere: a `Button` label can be a string or `Text`;
table cells format through `Column` callables; charts declare multiple series
on one class.

## Live attributes

Component fields are **live**. Change `items`, `value`, `data`, `label`, … and
the next frame reflects it — same spirit as assigning a grid field.

```python title="Update in grid_render"
from xnano import BaseGrid, Context, Field
from xnano.components.options import Options

class SavedNotes(BaseGrid):
    notes: Options = Field(default_factory=Options, border="rounded")

    def grid_render(self, ctx: Context) -> None:
        self.notes.items = tuple(
            n.name for n in ctx.state.saved
        ) or ("no notes yet",)
```

That is the usual loop: keep shared data in [state](state.md), push a view of
it onto component attributes each frame (or in a hook).

## Declarative subclasses

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: Column and Series descriptors declared on a subclass">
<svg viewBox="0 0 460 110" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="dc-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel" x="20" y="16" width="160" height="78" rx="10" />
  <text class="gcd-chrome-label" x="100" y="40" text-anchor="middle">class Services(Table)</text>
  <text class="gcd-z-caption" x="100" y="62" text-anchor="middle">status = Column(…)</text>
  <text class="gcd-z-caption" x="100" y="80" text-anchor="middle">latency = Column(…)</text>
  <line class="gcd-arrow" x1="180" y1="55" x2="240" y2="55" marker-end="url(#dc-arr)" />
  <rect class="gcd-panel gcd-panel-accent" x="252" y="28" width="180" height="54" rx="10" />
  <text class="gcd-label gcd-label-accent" x="342" y="60" text-anchor="middle">schema · paint</text>
</svg>
</div>

Some built-ins are meant to be **subclassed** with descriptors on the class
body. The metaclass collects those descriptors; you get a typed schema without
building columns or series by hand every time.

### Tables — `Column`

```python title="Table with Column descriptors"
from xnano.components.schema import Column
from xnano.components.table import Table

class Services(Table):
    service: str = Column(
        header="SERVICE",
        accessor=lambda row: row["meta"]["name"],
        format=lambda value: value.upper(),
        width=14,
    )
    status: str = Column(
        foreground=lambda value: "green-300" if value == "ok" else "red-300",
        horizontal_align="center",
    )
    latency: int = Column(format="{} ms", horizontal_align="right", width=12)

table = Services(data=[
    {"meta": {"name": "api"}, "status": "ok", "latency": 12},
    {"meta": {"name": "database"}, "status": "degraded", "latency": 340},
])
```

Without descriptors, `Table(data=[...])` still works and infers columns from
keys.

### Charts — `Series`

```python title="Chart with Series descriptors"
from xnano.components.chart import Chart
from xnano.components.schema import Series

class Latency(Chart):
    p50 = Series(color="green", kind="line")
    p99 = Series(color="red", kind="scatter", label="99th")

chart = Latency(series={"p50": [1, 2, 3], "p99": [4, 5, 6]})
```

Descriptors are the “declare once, reuse the type” pattern. Instance
construction stays light: pass `data=` / `series=` and go.

## Custom components

Subclass [`Component`](../api/xnano/components/component.md){data-preview}
(prefer `@dataclasses.dataclass`) when a built-in is not enough.

Patterns available on every custom component:

| Pattern | What you get |
|---------|----------------|
| Dataclass attributes | Live state on the instance |
| `component_post_init` | Setup after fields are assigned (prefer this over `__post_init__`) |
| Paint method | Return interface-neutral content for the slot |
| `visible` / `z` / `fit_content` | Shared layout flags on every component |
| `focused` | Read-only; true while this component holds field focus |
| `handle_keyboard` / `handle_paste` | Optional input while focused (`True` = consumed) |
| Responsive paint variants | Optional size-tier overrides when the viewport changes |
| `get_size` / frame hooks | Preferred size and before/after paint hooks |

Minimal example:

```python title="A small custom component"
import dataclasses

from xnano.components.component import Component
from xnano.core.content import TextBlock

@dataclasses.dataclass
class Badge(Component):
    text: str
    foreground: str = "cyan"

    def compose(self, ctx):  # (1)!
        return TextBlock.from_plain(self.text, foreground=self.foreground)
```

1. The paint hook is how a component turns attributes into content. Built-ins
   do the same under the hood; you only write it for custom types.

Drop it in a field like any other component:

```python
class Header(BaseGrid):
    badge: Badge = Field(default_factory=lambda: Badge("beta"))
```

Or paint it alone: `render(Badge("ok"))`.

### Focus and grid hooks

Interactive pieces usually stay **hook-driven on the grid**, not buried only
inside the component. Give the field a `group`, then bind `@on_click` /
`@on_keyboard` on the grid — same as [Events & Hooks](events.md).

```python title="Button + grid hooks"
from xnano import BaseGrid, Field, on_click, on_keyboard
from xnano.components.button import Button

class Form(BaseGrid):
    submit: Button = Field(
        default_factory=lambda: Button(label="Save"),
        group="submit",
    )

    @on_click(group="submit")
    @on_keyboard("enter", group="submit")
    def save(self, ctx) -> None:
        ...
```

`Button` leaves activation keys free so those hooks fire. Inputs can declare
`passthrough` / `submit_keys` for the same reason: app shortcuts keep working
while the user types.

Override `handle_keyboard` / `handle_paste` on a custom component when the
widget itself should consume keys (editors, lists). Return `True` only when
you handled the event.

## Built-in set

| Component | Module | Typical use |
|-----------|--------|-------------|
| `Text` | `xnano.components.text` | Labels, nested runs, optional input mode |
| `Input` | `xnano.components.input` | Single-line / multiline editor |
| `Options` / `Select` | `xnano.components.options` | Browseable list (`Select` is an alias) |
| `Button` | `xnano.components.button` | Focusable control + grid hooks |
| `Table` | `xnano.components.table` | Rows of data; subclass with `Column` |
| `Chart` | `xnano.components.chart` | Plots; subclass with `Series` |
| `Bar` | `xnano.components.bar` | Compact sample series |
| `Loader` | `xnano.components.loader` | Spinner or determinate bar/line |
| `Dropdown` | `xnano.components.dropdown` | Dropdown control |
| `Image` | `xnano.components.image` | Image (`images` extra) |
| `Link` | `xnano.components.link` | Link text |
| `Markdown` | `xnano.components.markdown` | Markdown *in a field* |
| `Scrollbar` | `xnano.components.scrollbar` | Scroll chrome |
| `Column` / `Series` | `xnano.components.schema` | Descriptors for table/chart subclasses |
| `Component` | `xnano.components.component` | Base for custom widgets |

For paging a whole file as a session, see [Markdown](markdown.md) — that is
the document runner, not the field component.

## Grids vs components

| | Grid | Component |
|---|------|-----------|
| Role | Layout + hooks + nested structure | Content (and optional focus) in a slot |
| Nesting | Other grids as fields | Nested content / descriptors inside one type |
| Events | `@on_*` on methods | Optional `handle_*`; app hooks still on the grid |
| State | `Field(state=True)`, app `state=` | Live attributes on the instance |

Use a nested grid when you need regions, focus groups, and hooks as a unit.
Use a component when the unit is “one widget with its own data shape.”

## Next

- [Fields](fields.md) — slots that hold components
- [State](state.md) — keep models and views in sync
- [Events & Hooks](events.md) — wire interaction on the grid
- [Styling](styling.md) — colors and `class_name` on fields

??? abstract "API"

    [`Component`](../api/xnano/components/component.md){data-preview} ·
    [`Text`](../api/xnano/components/text.md){data-preview} ·
    [`Table`](../api/xnano/components/table.md){data-preview} ·
    [`Chart`](../api/xnano/components/chart.md){data-preview} ·
    [`Column` / `Series`](../api/xnano/components/schema.md){data-preview} ·
    [components index](../api/xnano/components.md)

[component]: ../api/xnano/components/component.md
