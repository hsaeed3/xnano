---
title: "Progress"
icon: "lucide/activity"
---

# Progress Sandbox

These cells cover every `Progress` parameter: `value`, `total`, `label`,
`style`, `color`, `background`, `filled_color`, `unfilled_color`, and the
shared `visible`, `z`, and `fit_content` flags.

## Ratio and Value/Total Modes

Without `total`, `value` is a `0.0`–`1.0` ratio. With `total`, the ratio is
`value / total`. Results are clamped; a non-positive total becomes zero.

```pyodide install="xnano>=1.0.10" height="20"
from xnano import Terminal
from xnano.components.progress import Progress

bars = [
    Progress(value=0.35),
    Progress(value=68, total=100),
    Progress(value=1.4, label="clamped to 100%"),
    Progress(value=-0.2, label="clamped to 0%"),
    Progress(value=5, total=0, label="non-positive total"),
]
Terminal(width=52, height=8).render(*bars, gap=1)
```

??? example "Ratio and Value/Total Modes"

    **`value`**

    [Progress.value]{data-preview} accepts `int | float`: a ratio without
    `total`, or an absolute amount with one.

    **`total`**

    [Progress.total]{data-preview} accepts `int | float | None`; `None` selects
    ratio mode.

## Labels

`label=None` derives a percentage, a string uses custom text, and `False`
hides the label.

```pyodide install="xnano>=1.0.10" height="17"
from xnano import Terminal
from xnano.components.progress import Progress

Terminal(width=50, height=6).render(
    Progress(value=0.42, label=None),
    Progress(value=0.42, label="indexing files"),
    Progress(value=0.42, label=False),
    gap=1,
)
```

??? example "Labels"

    **`label`**

    [Progress.label]{data-preview} accepts a custom `str`, `None` for an
    automatic percentage, or `False` to hide the label.

## Styles and Colors

`style` is `bar` or `line`. `color` styles the bar and is also the line's
default filled color. `filled_color` and `unfilled_color` override the two
line portions; `background` styles the widget area.

```pyodide install="xnano>=1.0.10" height="22"
from xnano import Terminal
from xnano.components.progress import Progress

bar = Progress(
    value=0.72,
    style="bar",
    label="bar",
    color="emerald-400",
    background="slate-900",
)
line = Progress(
    value=0.72,
    style="line",
    label="line with explicit portions",
    color="white",
    background="slate-900",
    filled_color="cyan-300",
    unfilled_color="slate-600",
)
line_fallback = Progress(
    value=0.72,
    style="line",
    label="filled_color=None uses color",
    color="amber-300",
    filled_color=None,
    unfilled_color=None,
)

Terminal(width=60, height=7).render(bar, line, line_fallback, gap=1)
```

??? example "Styles and Colors"

    **`style`**

    [Progress.style]{data-preview} accepts every [ProgressStyle]{data-preview}
    literal: `"bar" | "line"`.

    **`color`**

    [Progress.color]{data-preview} accepts any [ColorLike]{data-preview}.

    **`background`**

    [Progress.background]{data-preview} accepts any [ColorLike]{data-preview}
    or `None`.

    **`filled_color`**

    [Progress.filled_color]{data-preview} accepts any
    [ColorLike]{data-preview} or `None`; in line mode, `None` falls back to
    `color`.

    **`unfilled_color`**

    [Progress.unfilled_color]{data-preview} accepts any
    [ColorLike]{data-preview} or `None`; `None` uses the renderer default.

## Visibility, Stacking, and Fit

`Progress` defaults to `fit_content=False`, because a useful gauge normally
fills the width supplied by its field or terminal. All components also accept
`visible` and `z`.

```pyodide install="xnano>=1.0.10" height="18"
from xnano import Terminal
from xnano.components.progress import Progress

shown = Progress(value=0.8, visible=True, z=2, fit_content=False)
hidden = Progress(value=0.2, visible=False, z=10, fit_content=True)

print("ratio:", shown.ratio)
print("shared flags:", shown.visible, shown.z, shown.fit_content)
Terminal(width=48, height=4).render(shown, hidden)
```

??? example "Visibility, Stacking, and Fit"

    **`visible`**

    [Progress]{data-preview} accepts `visible=True | False`; hidden components
    do not paint.

    **`z`**

    [Progress]{data-preview} accepts an integer `z` stacking order.

    **`fit_content`**

    [Progress]{data-preview} accepts `fit_content=True | False`; progress
    defaults to `False` so its container supplies the useful width.

[Progress]: ../api/xnano/components/progress.md#xnano.components.progress.Progress
[Progress.value]: ../api/xnano/components/progress.md#xnano.components.progress.Progress.value
[Progress.total]: ../api/xnano/components/progress.md#xnano.components.progress.Progress.total
[Progress.label]: ../api/xnano/components/progress.md#xnano.components.progress.Progress.label
[Progress.style]: ../api/xnano/components/progress.md#xnano.components.progress.Progress.style
[Progress.color]: ../api/xnano/components/progress.md#xnano.components.progress.Progress.color
[Progress.background]: ../api/xnano/components/progress.md#xnano.components.progress.Progress.background
[Progress.filled_color]: ../api/xnano/components/progress.md#xnano.components.progress.Progress.filled_color
[Progress.unfilled_color]: ../api/xnano/components/progress.md#xnano.components.progress.Progress.unfilled_color
[ProgressStyle]: ../api/xnano/components/progress.md#xnano.components.progress.ProgressStyle
[ColorLike]: ../api/xnano/color.md#xnano.color.ColorLike
