---
title: Sizing
icon: lucide/ruler
---

# Sizing

A field's `width` or `height` tells the parent grid how to divide its
available space. Use the attribute that matches the grid direction: heights in
a vertical grid and widths in a horizontal grid.

| Value | Meaning | Good for |
|---|---|---|
| `3` | Exactly three terminal cells | Headers and status lines |
| `"25%"` | A percentage of the available axis | Sidebars |
| `"1fr"` | One share of the remaining space | Main content |
| `"fit"` | The measured size of the content | Labels and badges |

## Mix sizing units

Fixed and fitted fields are resolved first. Percentages are resolved next,
then fractional fields divide what remains.

```python title="sizing.py"
from xnano import Field, BaseGrid, Terminal

class App(BaseGrid, direction="vertical", gap=1):
    header: str = Field(default="fixed: 1 row", height=1)  # (1)!
    summary: str = Field(default="percent: 25%", height="25%")
    body: str = Field(default="fraction: the remainder", height="1fr")  # (2)!
    footer: str = Field(default="fit: measured", height="fit")

Terminal().run(App())
```

1. Integer sizes are terminal cells: rows for height and columns for width.
2. Fractional sizes receive space only after the other constraints are known.

<div class="xnano-demo" markdown>
![Four vertically sized fields in a terminal](../assets/concepts/sizing_mix-dark.gif){.demo-dark width="760" loading=lazy}
![Four vertically sized fields in a terminal](../assets/concepts/sizing_mix-light.gif){.demo-light width="760" loading=lazy}
</div>

In a horizontal grid, the same rules apply to `width`. For example, a
20-column sidebar beside a flexible main panel uses `width=20` and
`width="1fr"`.

## Bounds and terminal sizing

Use `min_width`, `max_width`, `min_height`, and `max_height` when a flexible
field needs a usable limit. `Terminal` also accepts width and height settings
for inline rendering. Full-screen grids use the terminal's available viewport.

Next, learn how [hooks](hooks.md) update a running layout.
