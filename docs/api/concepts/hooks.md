---
title: "Hooks"
icon: "lucide/zap"
---

# Hooks

Decorate a method on your `Grid` and xnano calls it when the matching event fires.

---

## `@on_keyboard`

```python
from xnano.beta.hooks import on_keyboard

class App(Grid, direction="vertical"):
    @on_keyboard("q")
    def quit(self, ctx) -> None:
        ctx.terminal.request_exit()

    @on_keyboard("enter")
    def submit(self) -> None:
        self.status = "Submitted!"

    @on_keyboard("ctrl+c")
    def force_quit(self, ctx) -> None:
        ctx.terminal.request_exit()
```

### Key strings

| String | Key |
|---|---|
| `"q"`, `"a"`, `"1"` | Character keys |
| `"enter"` | Enter |
| `"backspace"` | Backspace |
| `"tab"` | Tab |
| `"esc"` | Escape |
| `"up"` `"down"` `"left"` `"right"` | Arrow keys |
| `"f1"` … `"f12"` | Function keys |
| `"ctrl+q"`, `"shift+up"`, `"alt+enter"` | Modifier combos |

### Catch-all

```python
@on_keyboard
def on_any_key(self, ctx) -> None:
    char = getattr(ctx.keyboard, "character", None)
    if char and len(char) == 1:
        self.input += char
```

---

## `@on_tick`

```python
from xnano.beta.hooks import on_tick

class Clock(Grid, direction="vertical"):
    time: str = Field(default="", height=1)

    @on_tick(1000)   # every 1000ms, overrides Terminal's tick_interval
    def update(self) -> None:
        import time
        self.time = time.strftime(" %H:%M:%S")
```

!!! note
    Without a millisecond argument, `@on_tick` fires at the `Terminal`'s `tick_interval`. Set that when constructing:
    ```python
    Terminal(tick_interval=16).run(App())
    ```

---

## `@on_click`

Requires `Terminal(mouse_events=True)`.

```python
from xnano.beta.hooks import on_click

class App(Grid, direction="vertical", gap=1):
    button: str = Field(default="[ Click me ]", height=3, border="rounded")
    result: str = Field(default="", height=1)

    @on_click("button")
    def clicked(self) -> None:
        self.result = "Clicked!"

Terminal(mouse_events=True).run(App())
```

---

## `@on_state`

Fires when a `state=True` field changes:

```python
from xnano.beta.hooks import on_state

class App(Grid, direction="vertical"):
    display: str = Field(default="", height=1)
    count:   int = Field(default=0, state=True)

    @on_state("count")
    def on_count_change(self) -> None:
        self.display = f"Count is now {self.count}"
```

---

## Context

Any hook can take `ctx` as a second argument:

```python
@on_keyboard("enter")
def submit(self, ctx) -> None:
    ctx.terminal   # Terminal instance
    ctx.keyboard   # crossterm KeyEvent
    ctx.mouse      # crossterm MouseEvent (or None)
    ctx.state      # app-level state (if set on Terminal)
    ctx.grid       # root Grid instance
```

`ctx` is optional — omit it if you don't need it.

---

## Execution order

Multiple hooks matching the same event fire in declaration order. Parent grid hooks fire before child grid hooks.

!!! warning
    Exceptions raised inside hooks propagate out of the event loop and leave the terminal in raw mode. Use `ctx.terminal.request_exit()` to stop cleanly, or raise `xnano.beta.exceptions.Exit` as a last resort.
