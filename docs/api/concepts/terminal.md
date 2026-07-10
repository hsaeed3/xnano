---
title: "Terminal"
icon: "lucide/terminal"
---

# Terminal

`Terminal` is the entry point for everything in xnano. It owns the terminal session — raw mode, alternate screen, event loop, teardown — and exposes two modes depending on what you're building.

---

## `run()` vs `render()`

### `render()` — inline

Use `render()` when you want styled output in the current terminal buffer. It paints the renderables, then returns. The terminal stays in normal mode; the cursor advances below the output. This is the right choice for CLI tools that want rich output without a full TUI.

```python title="render.py"
from xnano import Terminal
from xnano.components import Text

Terminal().render(
    Text("Build complete.", color="emerald-400", modifiers=["bold"]),
    Text("12 tests passed.", color="slate-400"),
)
```

<div class="xnano-demo" markdown>
![terminal render dark](../../assets/concepts/terminal_render-dark.gif){.demo-dark}
![terminal render light](../../assets/concepts/terminal_render-light.gif){.demo-light}
</div>

### `run()` — interactive

Use `run()` for interactive apps. It switches to the alternate screen, starts the event loop, and repaints on every event (key press, tick, resize). When `request_exit()` is called the terminal is fully restored.

```python
Terminal().run(MyGrid())
```

---

## Options

```python title="Terminal options"
Terminal(
    tick_interval=16,   # (1)!
    mouse_events=True,  # (2)!
    width="fit",        # (3)!
    height=20,          # (4)!
)
```

1. Milliseconds between `@on_tick` calls. `16` ≈ 60 fps. Defaults to `1000` (1 second) if not set.
2. Enables `@on_click` and `@on_mouse` hooks. Off by default.
3. Shrink-wrap to content width. Only applies in inline (`render()`) mode.
4. Fixed inline height — renders a block that many rows tall, no alternate screen.

### Sizing

| Option | Behaviour |
|---|---|
| `width="fit"` | Shrink-wrap to widest renderable |
| `width="50%"` | 50% of terminal columns |
| `height=10` | 10-row inline viewport |
| `height="fit"` | Shrink-wrap to content height |

!!! warning
    `height="fit"` has no effect on `Grid` apps — grids always fill the available area. xnano will emit a warning if you combine them.

---

## Exiting

The right way to stop a `run()` session is `ctx.terminal.request_exit()`. Calling it signals the loop to stop after the current frame finishes. The terminal is then restored automatically — alternate screen dismissed, raw mode cleared, cursor shown.

```python title="Exiting cleanly" hl_lines="3"
@on_keyboard("q")
def quit(self, ctx) -> None:
    ctx.terminal.request_exit()  # (1)!
```

1. Signals the loop to stop after the current frame finishes. The terminal is then restored automatically.

---

## Context manager

You can use `Terminal` as a context manager. The terminal session is guaranteed to be restored when the block exits, even if an exception is raised inside it. This is useful when you need to do setup or hold a reference to the terminal before running.

```python title="Guaranteed teardown"
with Terminal() as t:
    t.run(MyGrid())
# terminal restored here even if an exception was raised
```

---

## App-level state

For state that belongs to the application rather than a single grid — user preferences, auth tokens, config — attach a state object to `Terminal` and read it in any hook via `ctx.state`. The state object can be any Python object; a `dataclass` works well.

```python title="Shared app state" hl_lines="1 2 3 4 5 11"
from dataclasses import dataclass
from xnano import Field, Grid, Terminal
from xnano.hooks import on_keyboard

@dataclass
class AppState:
    theme: str = "dark"

class App(Grid, direction="vertical", gap=1):
    header: str = Field(default="", height=1, color="white", background="violet-900")
    body:   str = Field(default="Press t to toggle theme · q to quit", color="slate-400")

    def grid_render(self) -> None:
        self.header = f"  Theme: {self.state.theme}"

    @on_keyboard("t")
    def toggle(self, ctx) -> None:
        ctx.state.theme = "light" if ctx.state.theme == "dark" else "dark"

    @on_keyboard("q")
    def quit(self, ctx) -> None:
        ctx.terminal.request_exit()

with Terminal(state=AppState()) as t:
    t.run(App())
```

<div class="xnano-demo" markdown>
![terminal state dark](../../assets/concepts/terminal_state-dark.gif){.demo-dark}
![terminal state light](../../assets/concepts/terminal_state-light.gif){.demo-light}
</div>

State is shared across all grids in the session. Any hook, in any nested grid, can read and write `ctx.state`. The next repaint will reflect the change.
