---
title: "Terminal"
icon: "lucide/terminal"
---

# Terminal

---

## `run()` vs `render()`

### `run()` — interactive

```python
Terminal().run(MyGrid())
```

Enters the alternate screen, starts the event loop, repaints on each event (key, tick, resize). Restores the terminal on exit.

### `render()` — inline

```python
Terminal().render(
    Text("Build complete.", color="emerald-400", modifiers=["bold"]),
    Text("12 tests passed.", color="slate-400"),
)
```

Paints into the current terminal buffer and returns. Multiple renderables stack vertically.

---

## Options

```python
Terminal(
    tick_interval=16,   # ms between @on_tick calls (~60 fps)
    mouse_events=True,  # enable @on_click and @on_mouse
    width="fit",        # shrink-wrap to content width
    height=20,          # fixed inline height (no alternate screen)
)
```

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

```python
@on_keyboard("q")
def quit(self, ctx) -> None:
    ctx.terminal.request_exit()  # (1)!
```

1. Signals the loop to stop after the current frame. Prefer this over raising `Exit` directly.

---

## Context manager

```python
with Terminal() as t:
    t.run(MyGrid())
```

Guarantees teardown even if an exception is raised.

---

## App-level state

Attach a state object to the terminal and read it in any hook via `ctx.state`:

```python
from dataclasses import dataclass

@dataclass
class AppState:
    user: str = "guest"
    theme: str = "dark"

with Terminal(state=AppState(user="hammad")) as t:
    t.run(MyGrid())
```

```python
@on_keyboard("t")
def toggle_theme(self, ctx) -> None:
    ctx.state.theme = "light" if ctx.state.theme == "dark" else "dark"
```
