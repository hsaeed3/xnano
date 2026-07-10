---
title: Hooks
icon: lucide/zap
---

# Hooks

A hook is a grid method associated with an event. Decorators register the
method when the grid class is created; the terminal calls it when a matching
event arrives.

## Keyboard input

Pass one or more key bindings to `on_keyboard`. Character keys use their
literal value, while named keys use values such as `"enter"`, `"up"`, or
`"ctrl+c"`.

```python title="counter.py"
from xnano import Field, Grid, Terminal
from xnano.hooks import on_keyboard

class Counter(Grid, direction="vertical", gap=1):
    label: str = Field(default="Count: 0", height=3, border="rounded")
    hint: str = Field(default="↑ / ↓ to count · q to quit", height=1)
    count: int = Field(default=0, state=True)

    @on_keyboard("up")
    def increase(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"

    @on_keyboard("down")
    def decrease(self) -> None:
        self.count -= 1
        self.label = f"Count: {self.count}"

    @on_keyboard("q")
    def close_app(self, context) -> None:
        context.terminal.request_exit()

Terminal().run(Counter())
```

<div class="xnano-demo" markdown>
![A counter responding to arrow keys](../assets/concepts/hooks_keyboard-dark.gif){.demo-dark width="720" loading=lazy}
![A counter responding to arrow keys](../assets/concepts/hooks_keyboard-light.gif){.demo-light width="720" loading=lazy}
</div>

Call `on_keyboard` without bindings to receive every key. The hook context
exposes normalized keyboard data when a text editor or command palette needs
the exact character.

## Timed updates

`on_tick` runs at a millisecond interval. It is suited to clocks, progress
updates, and small periodic checks. Work that can block should remain outside
the render loop.

```python title="clock.py"
import time

from xnano import Field, Grid, Terminal
from xnano.hooks import on_keyboard, on_tick

class Clock(Grid):
    display: str = Field(default="", border="rounded", title=" Clock ")

    @on_tick(1000)  # (1)!
    def update_time(self) -> None:
        self.display = time.strftime("%H:%M:%S")

    @on_keyboard("q")
    def close_app(self, context) -> None:
        context.terminal.request_exit()

Terminal().run(Clock())
```

1. The interval is measured in milliseconds.

<div class="xnano-demo" markdown>
![A clock updating once per second](../assets/concepts/hooks_tick-dark.gif){.demo-dark width="680" loading=lazy}
![A clock updating once per second](../assets/concepts/hooks_tick-light.gif){.demo-light width="680" loading=lazy}
</div>

## Field clicks

`on_click` associates a handler with one named field. Enable mouse events on
the terminal, then update ordinary grid fields inside the handler.

```python title="button.py"
from xnano import Field, Grid, Terminal
from xnano.hooks import on_click, on_keyboard

class App(Grid, direction="vertical", gap=1):
    button: str = Field(default="[ Click me ]", height=3, border="rounded")
    result: str = Field(default="Waiting...", height=1)

    @on_click("button")  # (1)!
    def show_result(self) -> None:
        self.result = "Clicked!"

    @on_keyboard("q")
    def close_app(self, context) -> None:
        context.terminal.request_exit()

Terminal(mouse_events=True).run(App())
```

1. The field name is checked against its current rendered area.

<div class="xnano-demo" markdown>
![A field responding to a mouse click](../assets/concepts/hooks_click-dark.gif){.demo-dark width="680" loading=lazy}
![A field responding to a mouse click](../assets/concepts/hooks_click-light.gif){.demo-light width="680" loading=lazy}
</div>

Other hooks cover raw events, resize, focus, polling, field expressions, and
shared state. See the [`xnano.hooks` reference](../api/hooks.md) for their full
signatures.
