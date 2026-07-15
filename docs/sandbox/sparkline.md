---
title: "Sparkline"
icon: "lucide/chart-spline"
---

# Sparkline Sandbox

These examples cover every [Sparkline]{data-preview} parameter: `data`, `colors`,
`max_value`, `color`, `background`, `absent_value_color`,
`absent_value_symbol`, `visible`, `z`, and `fit_content`.

## Data and Automatic Scale

`data` is a list of non-negative integers. With `max_value=None`, the tallest
sample defines the scale.

```pyodide install="xnano>=1.0.10" height="18"
from xnano import Terminal
from xnano.components.sparkline import Sparkline

sparkline = Sparkline(
    data=[1, 4, 2, 8, 5, 9, 3, 7],
    max_value=None,
    color="cyan-300",
)
Terminal(width=48, height=5).render(sparkline)
```

??? example "Data and Automatic Scale"

    **`data`**

    [Sparkline.data]{data-preview} accepts a list of non-negative integers.

    **`max_value`**

    [Sparkline.max_value]{data-preview} accepts an integer ceiling, or `None`
    to derive the maximum from `data`.

## Fixed Maximum

A fixed ceiling makes separate datasets visually comparable. Values above the
ceiling render at full height.

```pyodide install="xnano>=1.0.10" height="20"
from xnano import Terminal
from xnano.components.sparkline import Sparkline

Terminal(width=52, height=9).render(
    Sparkline(data=[1, 4, 8, 12], max_value=12, color="emerald-300"),
    Sparkline(data=[1, 4, 8, 20], max_value=12, color="amber-300"),
    gap=1,
)
```

??? example "Fixed Maximum"

    **`max_value`**

    [Sparkline.max_value]{data-preview} accepts an integer ceiling, or `None`
    for automatic scaling.

## Global, Per-Bar, and Background Colors

`color` is the global foreground. `colors` supplies one color per data item
and takes precedence for those bars; its length must equal `data`. `background`
fills the widget area.

```pyodide install="xnano>=1.0.10" height="22"
from xnano import Terminal
from xnano.components.sparkline import Sparkline

data = [1, 3, 5, 7, 9]
sparkline = Sparkline(
    data=data,
    colors=("slate-400", "cyan-400", "emerald-400", "amber-400", "rose-400"),
    max_value=10,
    color="white",                 # used when colors=None
    background="slate-950",
)
Terminal(width=48, height=6).render(sparkline)
```

Set `colors=None` to use `color` for every present sample.

??? example "Global, Per-Bar, and Background Colors"

    **`colors`**

    [Sparkline.colors]{data-preview} accepts one [ColorLike]{data-preview} per
    sample, or `None` to use the global `color`.

    **`color`**

    [Sparkline.color]{data-preview} accepts any [ColorLike]{data-preview} as
    the global foreground.

    **`background`**

    [Sparkline.background]{data-preview} accepts any
    [ColorLike]{data-preview} or `None`.

## Absent Values and Symbol

Zero/absent samples can have their own color and glyph. Both options may be
`None` to use the renderer defaults.

```pyodide install="xnano>=1.0.10" height="22"
from xnano import Terminal
from xnano.components.sparkline import Sparkline

custom = Sparkline(
    data=[5, 0, 8, 0, 3, 0, 9],
    color="violet-300",
    absent_value_color="red-400",
    absent_value_symbol="×",
)
defaults = Sparkline(
    data=[5, 0, 8, 0, 3, 0, 9],
    color="cyan-300",
    absent_value_color=None,
    absent_value_symbol=None,
)
Terminal(width=48, height=9).render(custom, defaults, gap=1)
```

??? example "Absent Values and Symbol"

    **`absent_value_color`**

    [Sparkline.absent_value_color]{data-preview} accepts any
    [ColorLike]{data-preview} or `None` for the renderer default.

    **`absent_value_symbol`**

    [Sparkline.absent_value_symbol]{data-preview} accepts a glyph string, or
    `None` for the renderer default.

## Visibility, Stacking, and Fit

[Sparkline]{data-preview} defaults to `fit_content=False`, letting its field or viewport
supply enough height for useful bars.

```pyodide install="xnano>=1.0.10" height="18"
from xnano import Terminal
from xnano.components.sparkline import Sparkline

shown = Sparkline(
    data=[1, 5, 2, 8],
    visible=True,
    z=2,
    fit_content=False,
)
hidden = Sparkline(data=[9, 9, 9], visible=False, z=10, fit_content=True)

print("shared flags:", shown.visible, shown.z, shown.fit_content)
Terminal(width=44, height=5).render(shown, hidden)
```

??? example "Visibility, Stacking, and Fit"

    **`visible`**

    [Sparkline]{data-preview} accepts `visible=True | False`; hidden components
    do not paint.

    **`z`**

    [Sparkline]{data-preview} accepts an integer `z` stacking order.

    **`fit_content`**

    [Sparkline]{data-preview} accepts `fit_content=True | False`; sparklines
    default to `False` so their container supplies useful height.

[Sparkline]: ../api/xnano/components/sparkline.md#xnano.components.sparkline.Sparkline
[Sparkline.data]: ../api/xnano/components/sparkline.md#xnano.components.sparkline.Sparkline.data
[Sparkline.colors]: ../api/xnano/components/sparkline.md#xnano.components.sparkline.Sparkline.colors
[Sparkline.max_value]: ../api/xnano/components/sparkline.md#xnano.components.sparkline.Sparkline.max_value
[Sparkline.color]: ../api/xnano/components/sparkline.md#xnano.components.sparkline.Sparkline.color
[Sparkline.background]: ../api/xnano/components/sparkline.md#xnano.components.sparkline.Sparkline.background
[Sparkline.absent_value_color]: ../api/xnano/components/sparkline.md#xnano.components.sparkline.Sparkline.absent_value_color
[Sparkline.absent_value_symbol]: ../api/xnano/components/sparkline.md#xnano.components.sparkline.Sparkline.absent_value_symbol
[ColorLike]: ../api/xnano/color.md#xnano.color.ColorLike
