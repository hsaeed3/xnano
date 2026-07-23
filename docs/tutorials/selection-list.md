---
title: "Selection Lists"
icon: "lucide/list-checks"
---

# Selection Lists

[Select]{data-preview} is the built-in filterable list: items, a highlight, up/down movement, and optional fuzzy typing. Drop it on a [Field]{data-preview} and read `.value` when the user activates a row.

## One Select

```python title="One Select" hl_lines="6 7 8 9 10"
from xnano import BaseGrid, Field, Terminal, Context, on_keyboard
from xnano.components.select import Select

ITEMS = ["Home", "Projects", "Settings", "About"]

class Menu(BaseGrid, direction="vertical", gap=1):
    menu: Select = Field(
        default_factory=lambda: Select(items=ITEMS), # (1)!
        border="rounded",
        title=" Menu ",
    )
    status: str = Field(default="Select an item.", height=1, color="slate-400")
    hint: str = Field(
        default="↑ / ↓ · move   type · filter   enter · activate   q · quit",
        height=1,
        color="slate-500",
    )

    @on_keyboard("enter")
    def activate(self) -> None:
        self.status = f"Opened: {self.menu.value or '—'}" # (2)!

    @on_keyboard("q")
    def quit(self, ctx: Context) -> None:
        ctx.terminal.request_exit()

Terminal().run(Menu())
```

1. Focus is automatic — `Select` is focusable like `Text(input=True)`. Typing while focused edits the filter query; up/down move the highlight.
2. `.value` is the plain text of the selected (filtered) row, or `None` when nothing matches.

<div class="xnano-demo" markdown>
![selection list dark](../assets/tutorials/selection_list-dark.gif){.demo-dark}
![selection list light](../assets/tutorials/selection_list-light.gif){.demo-light}
</div>

<br/>

## Filtering

Fuzzy filter is on by default (`filter=True`, `searchable=True`). Matched characters pick up `match_color`. Set `searchable=False` when another field should own the query string instead of direct typing.

```python title="Filtering" hl_lines="3 4 5 6"
menu: Select = Field(
    default_factory=lambda: Select(
        items=ITEMS,
        searchable=True, # (1)!
        match_color="cyan",
    ),
    border="rounded",
    title=" Menu ",
)
```

1. With `searchable=False`, assign `self.menu.query = "..."` from a hook (for example after a separate `Text(input=True)` search box updates).

## Reading Selection

`.selected` is the index in the **filtered** view. Prefer `.value` when you only need the chosen string.

```python title="Reading Selection" hl_lines="3 4 5"
@on_keyboard("enter")
def activate(self) -> None:
    choice = self.menu.value
    self.status = f"Opened: {choice or '—'}"
```

??? note "Highlight and focus"

    - `highlight_color` / `highlight_background` / `highlight_symbol` style the active row.
    - Live focus is on the component as `.focused` (same property as other focusable widgets).
    - Enter, tab, and escape fall through so your hooks and tab navigation still see them.

## From Scratch (optional)

You can still paint rows yourself when you need a custom layout — items plus an index in state, a [Text]{data-preview} body with a highlight on the active row, and keyboard hooks that move the index.

```python title="Items and Index" hl_lines="8 9"
from xnano import BaseGrid, Field
from xnano.components.text import Text

ITEMS = ["Home", "Projects", "Settings", "About"]

class Menu(BaseGrid, direction="vertical", gap=1):
    body: Text = Field(default=Text(""), border="rounded", title=" Menu ")
    status: str = Field(default="Select an item.", height=1, color="slate-400")

    items: list = Field(default_factory=lambda: list(ITEMS), state=True)
    selected: int = Field(default=0, state=True) # (1)!
```

1. `selected` is pure state — never painted on its own.

```python title="Painting Rows" hl_lines="1 2 3 4 5 6 7 8 9 10 11 12"
def _paint(self) -> None:
    rows: list[Text] = []
    for index, item in enumerate(self.items):
        if index == self.selected:
            rows.append(
                Text([Text(f" › {item}", color="violet-300", modifiers=("bold",))])
            ) # (1)!
        else:
            rows.append(Text([Text(f"   {item}", color="slate-400")]))
    self.body = Text(rows)

def __post_init__(self) -> None:
    self._paint()
```

1. The highlight is just different text (and style) on the selected row.

```python title="Moving and Activating" hl_lines="3 4 5 8 9 10 13 14 15"
from xnano import on_keyboard

@on_keyboard("up")
def move_up(self) -> None:
    self.selected = (self.selected - 1) % len(self.items)
    self._paint()

@on_keyboard("down")
def move_down(self) -> None:
    self.selected = (self.selected + 1) % len(self.items)
    self._paint()

@on_keyboard("enter")
def activate(self) -> None:
    self.status = f"Opened: {self.items[self.selected]}"
```

For long buffers that need scrolling, see [scrollable logs]{data-preview}. Prefer [Select]{data-preview} for ordinary menus and pickers.

[BaseGrid]: ../api/xnano/grid.md
[Field]: ../api/xnano/fields.md
[Terminal]: ../api/xnano/terminal/terminal.md
[Context]: ../api/xnano/context.md
[Text]: ../api/xnano/components/text.md
[Select]: ../api/xnano/components/select.md
[scrollable logs]: scrollable-log.md
