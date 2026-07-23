---
title: "Select"
icon: "lucide/list-filter"
---

# Select

`Select` is a fuzzy-filterable list of items. While focused, typing edits the filter `query`, matched characters are emphasized, up/down move the selection, and `value` is the selected item's plain text.

Drop it into a field like any other component — it participates in the same focus protocol as editable [Text]{data-preview} (`focusable` + `handle_keyboard`).

??? example "Interactive Example"

    The following code block is interactive and can be run directly in the browser.

    ```pyodide install="xnano>=1.0.8" hl_lines="4 5 6 7 8"
    from xnano import render
    from xnano.components.select import Select

    render(Select(items=[
        "midnight",
        "ember",
        "aurora",
        "slate",
    ]))
    ```

```python title="A Selectable List" hl_lines="4 5 6 7 8"
from xnano import render
from xnano.components.select import Select

render(Select(items=[
    "midnight",
    "ember",
    "aurora",
    "slate",
])) # (1)!
```

1. Items are plain strings (or styled `Text` leaves). With `searchable=True` (the default), a query row appears above the list; type while focused to fuzzy-filter.

## In a Grid

Place `Select` on a field and read `value` from hooks when the user confirms a choice. Enter, tab, and escape are never consumed by the component, so application hooks and focus navigation still see them:

```python title="Picking a Theme" hl_lines="5 8 9 10"
from xnano import BaseGrid, Context, Field, on_keyboard
from xnano.components.select import Select

class Picker(BaseGrid, direction="vertical"):
    themes: Select = Field(default=Select(items=["midnight", "ember", "aurora"]))

    @on_keyboard("enter")
    def _choose(self, ctx: Context) -> None:
        chosen = self.themes.value  # selected item text, or None
```

`selected` is the index within the **filtered** view (not the full `items` list). `visible_items` exposes the plain text of the currently visible rows in display order.

## Filtering

Fuzzy matching is case-insensitive subsequence scoring — consecutive matches and word-start hits rank higher. Matched characters are emphasized with `match_color` (default `"cyan"`).

```python title="Pre-filtered Query" hl_lines="2 3 4 5"
Select(
    items=["api-gateway", "api-worker", "db-primary"],
    query="apg",
    match_color="amber-400",
)
```

| Parameter | Role |
|-----------|------|
| `filter` | When `False`, `query` is ignored and every item stays visible |
| `searchable` | When `True` (default), typing while focused edits `query` |
| `match_color` | Emphasis color for matched characters; `None` disables emphasis |

### External Search Box

Set `searchable=False` and drive `query` from another field reactively — for example a `Text(input=True)` search box above the list:

```python title="External Search Box" hl_lines="6 7 8 9 10 11 12"
from xnano import BaseGrid, Field, on_field
from xnano.components.select import Select
from xnano.components.text import Text

THEME_NAMES = ["midnight", "ember", "aurora", "slate"]

class Browser(BaseGrid, direction="vertical"):
    search: Text = Field(default=Text("", input=True, placeholder="filter…"))
    results: Select = Field(
        default=Select(items=THEME_NAMES, searchable=False),
    )

    @on_field("search")
    def _sync_query(self) -> None:
        self.results.query = self.search.value
```

With `searchable=False`, only up/down selection is handled by the list; typing goes to whichever field holds focus (here, the search box).

## Highlighting and Focus

Selection chrome is controlled by `highlight_color`, `highlight_background`, and `highlight_symbol` (default `"> "`). Base `color` / `background` style the list when a row is not selected.

`focusable` (default `True`) controls whether the Select joins the tab order. Live focus state is the shared `focused` property on [AbstractComponent]{data-preview} — usable as `self.themes.focused` or `@on_field("themes.focused")`.

The full parameter list lives on the [Select]{data-preview} API reference.

??? abstract "Sandbox & API"

    **API**

    [`Select`](../api/xnano/components/select.md#xnano.components.select.Select){data-preview} · [`get_fuzzy_match`](../api/xnano/components/select.md#xnano.components.select.get_fuzzy_match){data-preview} · [`AbstractComponent`](../api/xnano/components/abstract.md#xnano.components.abstract.AbstractComponent){data-preview}

[Select]: ../api/xnano/components/select.md
[Text]: text.md
[AbstractComponent]: ../api/xnano/components/abstract.md
