---
name: xnano
description: Best practices for building and changing xnano applications with BaseGrid, Field, components, hooks, Terminal, Web, and the shared runtime.
---

# xnano

Use this skill for work in the public `xnano` Python package. Keep application
code interface-neutral: grids, fields, components, hooks, and actions describe
the app; `Terminal` and `Web` choose where it is presented.

## Core rules

- Use `BaseGrid`, never `Grid`. Declare layout with annotated `Field(...)` values.
- Use `Field(state=True)` for application data that is not rendered. Use
  `default_factory` for mutable defaults.
- Prefer concrete imports such as `from xnano.components.text import Text`.
  The package root and barrels are for public user imports, not internal code.
- Compose custom components through `Component.compose()` and the content
  primitives in `xnano.core.content`; do not call ratatui or crossterm directly.
- Bind behavior with `xnano.hooks` or `Action` objects. Hooks may take no
  context argument or one `Context`; keep them synchronous unless the runtime
  is deliberately run from a compatible synchronous context.
- Use `Terminal.offscreen(...)` for deterministic rendering tests. `Terminal`
  owns the runtime and does not accept web host/port arguments; use `Web` or
  `xnano.server` for HTTP.
- Keep terminal and web behavior in the shared grid/component path. Do not
  introduce an `xnano.beta` surface or bypass `Runtime` for terminal lifecycle.

## Common patterns

Use `@on_tick` for a field-specific periodic update. Use `grid_render()` when
the whole grid should refresh before every frame; it is not a timer.

```python
import time

from xnano import BaseGrid, Field
from xnano.hooks import on_tick


class Clock(BaseGrid):
    clock: str = Field(default="")

    @on_tick(1000)
    def update_clock(self) -> None:
        self.clock = time.strftime("%H:%M:%S")
```

```python
class Dashboard(BaseGrid):
    header: str = Field(default="")
    body: str = Field(default="")

    def grid_render(self) -> None:
        self.header = self.get_header_text()
        self.body = self.get_body_text()
```

Prefer the typed `grid_settings` class attribute over `BaseGrid` class-header
keywords when declaring layout settings. The class-header form is supported,
but `GridSettings` gives type checkers a precise place to validate the options.

```python
from xnano.grids import BaseGrid, GridSettings


class Dashboard(BaseGrid):
    grid_settings: GridSettings = {
        "direction": "vertical",
        "gap": 1,
        "title": "Dashboard",
    }
```

Keep application data in state fields and render it through ordinary fields.
This separates state from layout and lets hooks watch the value cleanly.

```python
from xnano import BaseGrid, Field
from xnano.hooks import on_keyboard


class Counter(BaseGrid):
    label: str = Field(default="Count: 0")
    count: int = Field(default=0, state=True)

    @on_keyboard("up")
    def increment(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"
```

Play effects from a grid after its target field has rendered. Target specific
fields instead of animating the whole session:

```python
from xnano import BaseGrid, Field
from xnano.hooks import on_keyboard


class Panel(BaseGrid):
    body: str = Field(default="Ready")

    @on_keyboard("enter")
    def play_intro(self) -> None:
        self.grid_play_effect("fade", duration_ms=300, fields=["body"])
```

Use xnano's `ColorLike` values everywhere a color is accepted. Do not import
Rich color, text, or style objects. Plain color names, hex strings, RGB/RGBA
tuples, `Color`, and Tailwind palette values are all valid xnano colors; use
`foreground` for text, `background` for fills, and `border_color` for borders.
`color` is a deprecated alias for `foreground` in compatible dataclasses.

```python
from xnano.colors import tailwind_color
from xnano.components.text import Text
from xnano.grids import BaseGrid, Field


class Status(BaseGrid):
    title: Text = Field(
        default=Text(
            content="Ready",
            foreground=tailwind_color("emerald", 400),
        ),
        background=tailwind_color("slate", 900),
        border_color=tailwind_color("slate", 700),
    )
```

When styling a field with utilities, use xnano Tailwind classes such as
`class_name="text-emerald-400 bg-slate-900"`; do not pass a Rich `Style` or a
CSS/Tailwind object where a `ColorLike` is expected.

Prefer the built-in components, content primitives, `Action`, `Context`,
`Request`, and `Response` types over custom wrappers. Use synchronous hooks by
default; an async hook must not hide blocking work.

## Choose a reference

- Layout, fields, state, sizing, styling, focus, and scrolling: [grids](references/grids.md)
- Built-in and custom components: [components](references/components.md)
- Event hooks, actions, and context: [hooks](references/hooks.md)
- Rendering, terminal, runtime, and web hosts: [hosts](references/hosts.md)
- HTTP request hooks and servers: [server](references/server.md)

## Verification

Prefer a focused test using an offscreen terminal for rendering and dispatch.
Run the repository checks required by `AGENTS.md` after implementation:
`uv run pytest`, `uv run prek run --all-files`, and `uv run ty check`.
