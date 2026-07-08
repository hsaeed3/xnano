---
title: "Getting Started"
icon: "lucide/sparkles"
---

# Getting Started

---

## Install

=== "pip"

    ```bash
    pip install "xnano==1.0.0b3"
    ```

=== "uv"

    ```bash
    uv add xnano
    ```

=== "poetry"

    ```bash
    poetry add xnano
    ```

Python 3.10+. The Rust extension (`xnano-core`) is bundled in the wheel — no system dependencies.

---

## Print something

```python
from xnano.beta import Terminal
from xnano.beta.components import Text

Terminal().render(
    Text("Hello from xnano!", color="violet", modifiers=["bold"])
)
```

`render()` paints inline and returns — no alternate screen, no event loop.

---

## Build a layout

```python
from xnano.beta import Field, Grid, Terminal
from xnano.beta.hooks import on_keyboard

class Hello(Grid, direction="vertical"):
    message: str = Field(default="Press q to quit.", height=1)

    @on_keyboard("q")
    def quit(self, ctx) -> None:
        ctx.terminal.request_exit()

Terminal().run(Hello())
```

`run()` enters the alternate screen and starts the event loop. When `request_exit()` is called the loop stops and the terminal is restored.

!!! note
    Everything lives under `xnano.beta` while the API is being finalized.

---

## What `run()` does

1. Resolves layout from your field declarations
2. Paints the first frame
3. Hands off to the Rust event loop — blocks on input, fires tick timers, calls your hooks
4. On exit, restores the terminal

---

## Next steps

- [Terminal](terminal.md) — run modes and configuration
- [Grid & Fields](grid.md) — layouts and field options
- [Sizing](sizing.md) — width and height values
- [Hooks](hooks.md) — keyboard, tick, click, state
