---
title: "Title & Clipboard"
icon: "lucide/clipboard"
---

# Title & Clipboard

Window title and clipboard sit on the host's [device]{data-preview}, not on any grid. From a hook, use `ctx.device` — the same API on terminal and web.

Layout and fields stay on the grid. Title and clipboard do not.

## Setting the Title

```python title="Setting the Title" hl_lines="4"
from xnano import Context, on_keyboard

@on_keyboard("t")
def set_title(self, ctx: Context) -> None:
    ctx.device.title = "my app" # (1)!
```

1. On a terminal this is the window title; on web it is the tab title. Same assignment either way.

## Title From Shared State

Pair title updates with `Terminal(state=...)` when the title should track app-wide data.

```python title="State First" hl_lines="4 5 6"
import dataclasses

@dataclasses.dataclass
class AppState:
    unread: int = 0
```

```python title="Sync Title and Label" hl_lines="3 4 5 6 7"
def _sync(self, ctx: Context[AppState]) -> None:
    state = ctx.get_state()
    self.label = f"Inbox: {state.unread} unread"
    ctx.device.title = (
        f"({state.unread}) inbox" if state.unread else "inbox"
    )
```

```python title="Keys That Bump Unread" hl_lines="3 4 5 6 9 10 11 12"
from xnano import on_keyboard

@on_keyboard("+")
def more(self, ctx: Context[AppState]) -> None:
    ctx.get_state().unread += 1
    self._sync(ctx)

@on_keyboard("-")
def less(self, ctx: Context[AppState]) -> None:
    state = ctx.get_state()
    state.unread = max(0, state.unread - 1)
    self._sync(ctx)
```

## Full Inbox Example

```python title="Full Inbox Example"
import dataclasses
from xnano import BaseGrid, Field, Terminal, Context, on_keyboard

@dataclasses.dataclass
class AppState:
    unread: int = 0

class Inbox(BaseGrid, direction="vertical", gap=1):
    label: str = Field(default="Inbox: 0 unread", height=1)
    hint: str = Field(
        default="+ / − unread · q quit",
        height=1,
        color="slate-500",
    )

    def _sync(self, ctx: Context[AppState]) -> None:
        state = ctx.get_state()
        self.label = f"Inbox: {state.unread} unread"
        ctx.device.title = (
            f"({state.unread}) inbox" if state.unread else "inbox"
        )

    @on_keyboard("+")
    def more(self, ctx: Context[AppState]) -> None:
        ctx.get_state().unread += 1
        self._sync(ctx)

    @on_keyboard("-")
    def less(self, ctx: Context[AppState]) -> None:
        state = ctx.get_state()
        state.unread = max(0, state.unread - 1)
        self._sync(ctx)

    @on_keyboard("q")
    def quit(self, ctx: Context) -> None:
        ctx.terminal.request_exit()

Terminal(state=AppState()).run(Inbox())
```

## Copy to Clipboard

`copy_to_clipboard` is on the same device object.

```python title="Copy to Clipboard" hl_lines="4 5"
from xnano import Context, on_keyboard

@on_keyboard("ctrl+c")
def copy(self, ctx: Context) -> None:
    ctx.device.copy_to_clipboard(self.text) # (1)!
    self.status = "copied."
```

1. Clipboard write uses the host implementation — terminal or browser — behind one method.

## Full Clipboard Example

```python title="Full Clipboard Example"
from xnano import BaseGrid, Field, Terminal, Context, on_keyboard

class Snippet(BaseGrid, direction="vertical", gap=1):
    text: str = Field(
        default="hello from xnano",
        height=1,
        border="rounded",
        title=" snippet ",
    )
    status: str = Field(
        default="ctrl+c to copy · q quit",
        height=1,
        color="slate-500",
    )

    @on_keyboard("ctrl+c")
    def copy(self, ctx: Context) -> None:
        ctx.device.copy_to_clipboard(self.text)
        self.status = "copied."
        ctx.device.title = "snippet · copied"

    @on_keyboard("q")
    def quit(self, ctx: Context) -> None:
        ctx.terminal.request_exit()

Terminal().run(Snippet())
```

<br/>

To hide the caret when you draw your own selection highlight: `ctx.cursor.visible = False`. Terminal-only knobs (raw mode, alternate screen, mouse capture) exist only on the terminal device and are no-ops on web — details on [Device & Cursor]{data-preview}.

[device]: ../core-concepts/device.md
[Device & Cursor]: ../core-concepts/device.md
[Context]: ../api/xnano/context.md
