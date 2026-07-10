---
title: Grids and fields
icon: lucide/layout-dashboard
---

# Grids and fields

A `Grid` is a typed layout. Each `Field` marks one value as a visible slot, and
the order of the declarations is the order used by the layout.

## Declare a layout

The grid direction controls the layout axis. A vertical grid places fields
from top to bottom; a horizontal grid places them from left to right.

```python title="app.py"
from xnano import Field, Grid, Terminal
from xnano.hooks import on_keyboard

class App(Grid, direction="vertical"):
    header: str = Field(
        default="My App", height=1, color="white", background="violet"
    )
    body: str = Field(default="Hello, world!")
    footer: str = Field(default="[q] quit", height=1, color="slate-500")

    @on_keyboard("q")
    def close_app(self, context) -> None:
        context.terminal.request_exit()

Terminal().run(App())
```

<div class="xnano-demo" markdown>
![A vertical grid with header body and footer](../assets/concepts/grid_basic-dark.gif){.demo-dark width="720" loading=lazy}
![A vertical grid with header body and footer](../assets/concepts/grid_basic-light.gif){.demo-light width="720" loading=lazy}
</div>

Field settings cover three concerns:

| Concern | Common settings |
|---|---|
| Layout | `width`, `height`, `gap`, `direction`, `visible` |
| Frame | `border`, `border_color`, `title`, `padding` |
| Text | `color`, `background`, `align`, `bold`, `italic` |

Values can be changed directly. Use `grid_set_field()` when the presentation
settings of a field also need to change at runtime.

## Nest grids

A field can contain another grid. Use `default_factory` so every parent gets a
new child instance.

```python title="nested.py"
from xnano import Field, Grid, Terminal
from xnano.hooks import on_keyboard

class Sidebar(Grid, direction="vertical"):
    navigation: str = Field(
        default="Home\nAbout\nSettings", border="rounded"
    )
    status: str = Field(default="Ready", height=1)

class App(Grid, direction="horizontal", gap=1):
    sidebar: Sidebar = Field(default_factory=Sidebar, width="25%")  # (1)!
    main: str = Field(default="Main content", width="1fr", border="rounded")

    @on_keyboard("q")
    def close_app(self, context) -> None:
        context.terminal.request_exit()

Terminal().run(App())
```

1. `default_factory` creates the nested grid when its parent is initialized.

<div class="xnano-demo" markdown>
![A sidebar grid nested beside a main field](../assets/concepts/grid_nested-dark.gif){.demo-dark width="760" loading=lazy}
![A sidebar grid nested beside a main field](../assets/concepts/grid_nested-light.gif){.demo-light width="760" loading=lazy}
</div>

## Derive the next frame

`grid_render()` runs before xnano paints a frame. Read state there and assign
the field values that should be visible. Keep the method limited to quick,
deterministic work.

```python title="derived.py"
from xnano import Field, Grid, Terminal
from xnano.hooks import on_keyboard

class Greeting(Grid, direction="vertical", gap=1):
    header: str = Field(default="", height=1)
    body: str = Field(default="", border="rounded")
    name: str = Field(default="world", state=True)

    def grid_render(self) -> None:  # (1)!
        self.header = f"Hello, {self.name}!"
        self.body = f"Current name: {self.name}"

    @on_keyboard("q")
    def close_app(self, context) -> None:
        context.terminal.request_exit()

Terminal().run(Greeting())
```

1. The method derives visible fields from the current state before each paint.

<div class="xnano-demo" markdown>
![A grid rendering values derived from state](../assets/concepts/grid_render_method-dark.gif){.demo-dark width="720" loading=lazy}
![A grid rendering values derived from state](../assets/concepts/grid_render_method-light.gif){.demo-light width="720" loading=lazy}
</div>

Continue with [Sizing](sizing.md) to control how grid slots share space.
