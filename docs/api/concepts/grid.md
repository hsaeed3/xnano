---
title: "Grid & Fields"
icon: "lucide/layout-dashboard"
---

# Grid & Fields

---

## Basics

Subclass `Grid`, add typed fields, run it. Field order is layout order.

```python
from xnano.beta import Field, Grid, Terminal

class App(Grid, direction="vertical"):
    header: str = Field(default="My App", height=1, color="white", background="violet")
    body:   str = Field(default="Hello, world!")
    footer: str = Field(default="[q] quit", height=1, color="slate-500")

Terminal().run(App())
```

---

## Grid options

```python
class Toolbar(Grid, direction="horizontal", gap=2, background="slate-900"):
    ...
```

| Option | Values |
|---|---|
| `direction` | `"vertical"` (default) · `"horizontal"` |
| `gap` | int — empty cells between fields |
| `background` | color string |

---

## Field options

### Appearance

```python
Field(
    default="My field",
    color="white",
    background="slate-800",
    modifiers=["bold", "italic"],
    align="center",            # "left" · "center" · "right"
    border="rounded",          # "plain" · "rounded" · "double" · "thick"
    border_color="violet-500",
    title=" My Title ",
    padding=(1, 2),            # (vertical, horizontal) cells
)
```

### Sizing

```python
Field(default="Fixed",   height=3)       # 3 rows
Field(default="Quarter", height="25%")   # 25% of available space
Field(default="Fill",    height="1fr")   # remaining space
Field(default="Compact", height="fit")   # shrink to content
```

See [Sizing](sizing.md).

### State

`state=True` makes a field reactive — changing it triggers a repaint:

```python
class Counter(Grid, direction="vertical"):
    label: str = Field(default="0", height=1)
    count: int = Field(default=0, state=True)
```

---

## Nesting

```python
class Sidebar(Grid, direction="vertical"):
    nav:    str = Field(default="- Home\n- About", border="rounded")
    status: str = Field(default="Ready", height=1, color="slate-500")

class App(Grid, direction="horizontal"):
    sidebar: Sidebar = Field(default_factory=Sidebar, width="25%")
    main:    str     = Field(default="Main content",  width="1fr", border="rounded")

Terminal().run(App())
```

!!! tip
    Use `default_factory=` for mutable defaults and nested grids — it's called fresh each time an instance is created.

---

## `grid_render()`

Called once per frame before painting. Update field values here:

```python
class App(Grid, direction="vertical"):
    header: str = Field(default="", height=1)
    name:   str = Field(default="world", state=True)

    def grid_render(self) -> None:
        self.header = f"Hello, {self.name}!"
```

---

## Updating styles at runtime

```python
def grid_render(self) -> None:
    if self.error:
        self.grid_set_field("status", border_color="red-500", color="red-400")
        self.status = "Error!"
    else:
        self.grid_set_field("status", border_color="emerald-500", color="emerald-400")
        self.status = "OK"
```

---

## Grid dimensions

`self.rows` and `self.columns` are available inside `grid_render()` and any hook:

```python
def grid_render(self) -> None:
    self.chart = build_sparkline(self.data, width=self.columns - 4)
```
