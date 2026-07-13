---
title: "Chart & Series"
icon: "lucide/chart-no-axes-combined"
---

# Chart & Series Sandbox

This page covers every `Chart` parameter and every `Series` descriptor option.
Charts need vertical room, so the examples use fixed browser-safe viewports.

## Both Point Forms

A series accepts bare `y` values (x becomes the list index) or explicit
`(x, y)` pairs. The mapping key becomes its default legend label.

```pyodide install="xnano>=1.0.10" height="24"
from xnano import Terminal
from xnano.components.chart import Chart

chart = Chart(series={
    "indexed y": [2, 5, 3, 8, 6],
    "explicit xy": [(0, 7), (1, 6), (2, 7), (3, 4), (4, 5)],
})
Terminal(width=72, height=15).render(chart)
```

??? example "Both Point Forms"

    **`series`**

    [Chart.series]{data-preview} accepts a mapping of labels to bare y-values
    or `(x, y)` pairs, as defined by [SeriesData]{data-preview}.

## Every Graph Kind

`kind` is `line`, `scatter`, or `bar`. A declarative `Series` can override the
default, so one chart may mix all three.

```pyodide install="xnano>=1.0.10" height="27"
from xnano import Terminal
from xnano.components.chart import Chart
from xnano.components.schema import Series

class MixedChart(Chart):
    trend = Series(label="line", color="cyan-300", kind="line")
    samples = Series(label="scatter", color="amber-300", kind="scatter")
    volume = Series(label="bar", color="violet-400", kind="bar")

chart = MixedChart(
    series={
        "trend": [2, 4, 5, 7, 8],
        "samples": [3, 5, 4, 8, 7],
        "volume": [1, 2, 3, 2, 4],
    },
    kind="line",
)
Terminal(width=76, height=16).render(chart)
```

??? example "Every Graph Kind"

    **`kind`**

    [Chart.kind]{data-preview} accepts every [GraphTypeLike]{data-preview}
    literal: `"line" | "scatter" | "bar"`.

## Palette and Automatic Bounds

`colors=None` cycles the built-in palette. A custom sequence cycles in the
same way. `x_bounds=None` and `y_bounds=None` auto-fit the data.

```pyodide install="xnano>=1.0.10" height="25"
from xnano import Terminal
from xnano.components.chart import Chart

series = {
    "one": [1, 3, 2, 4],
    "two": [2, 4, 3, 5],
    "three": [3, 5, 4, 6],
}

chart = Chart(
    series=series,
    colors=("rose-400", "amber-300"),  # cycles: rose, amber, rose
    x_bounds=None,
    y_bounds=None,
)
Terminal(width=70, height=14).render(chart)
```

??? example "Palette and Automatic Bounds"

    **`colors`**

    [Chart.colors]{data-preview} accepts a sequence of
    [ColorLike]{data-preview} values, or `None` for the built-in palette.

    **`x_bounds`**

    [Chart.x_bounds]{data-preview} accepts a `(minimum, maximum)` float pair,
    or `None` to fit the x data automatically.

    **`y_bounds`**

    [Chart.y_bounds]{data-preview} accepts a `(minimum, maximum)` float pair,
    or `None` to fit the y data automatically.

## Explicit Bounds and Axis Labels

Bounds are `(minimum, maximum)` floats. `x_label` and `y_label` accept a string
or `None`.

```pyodide install="xnano>=1.0.10" height="24"
from xnano import Terminal
from xnano.components.chart import Chart

chart = Chart(
    series={"temperature": [(0, 19), (6, 22), (12, 28), (18, 24), (24, 20)]},
    x_bounds=(0.0, 24.0),
    y_bounds=(15.0, 30.0),
    x_label="hour",
    y_label="°C",
)
Terminal(width=70, height=15).render(chart)
```

??? example "Explicit Bounds and Axis Labels"

    **`x_label`**

    [Chart.x_label]{data-preview} accepts `str | None`.

    **`y_label`**

    [Chart.y_label]{data-preview} accepts `str | None`.

## Legend Toggle and Every Position

`legend=False` hides it. With `legend=True`, `legend_position` accepts all
eight values in `positions` below. Change `position` and rerun.

```pyodide install="xnano>=1.0.10" height="27"
from xnano import Terminal
from xnano.components.chart import Chart

positions = (
    "top",
    "top_right",
    "top_left",
    "left",
    "right",
    "bottom",
    "bottom_right",
    "bottom_left",
)
position = "bottom_left"  # try every value in positions

chart = Chart(
    series={"cpu": [2, 5, 3, 7], "memory": [6, 5, 7, 6]},
    legend=True,
    legend_position=position,
)
Terminal(width=68, height=15).render(chart)
print("remaining positions:", [item for item in positions if item != position])
```

```pyodide install="xnano>=1.0.10" height="21"
from xnano import Terminal
from xnano.components.chart import Chart

Terminal(width=62, height=12).render(
    Chart(series={"hidden legend": [1, 4, 2, 5]}, legend=False)
)
```

??? example "Legend Toggle and Every Position"

    **`legend`**

    [Chart.legend]{data-preview} accepts `True | False`.

    **`legend_position`**

    [Chart.legend_position]{data-preview} accepts every
    [LegendPositionLike]{data-preview} literal: `"top"`, `"top_right"`,
    `"top_left"`, `"left"`, `"right"`, `"bottom"`, `"bottom_right"`, or
    `"bottom_left"`.

## Every `Series` Option

`Series(label=None, color=None, kind=None)` derives/falls back to the chart.
Each value can be overridden independently.

```pyodide install="xnano>=1.0.10" height="27"
from xnano import Terminal
from xnano.components.chart import Chart
from xnano.components.schema import Series

class Declarative(Chart):
    inherited = Series(label=None, color=None, kind=None)
    customized = Series(label="Custom label", color="#f472b6", kind="scatter")

chart = Declarative(
    series={
        "inherited": [1, 3, 2, 4],
        "customized": [4, 2, 3, 1],
        "extra": [2, 2, 4, 3],       # undeclared keys still render
    },
    kind="bar",
    colors=("emerald-300", "amber-300"),
)
Terminal(width=76, height=16).render(chart)
```

??? example "Every `Series` Option"

    **`Series.label`**

    [Series]{data-preview} accepts `label: str | None`; `None` derives the label
    from the mapping key.

    **`Series.color`**

    [Series]{data-preview} accepts [ColorLike]{data-preview} or `None`; `None`
    uses the chart palette.

    **`Series.kind`**

    [Series]{data-preview} accepts [GraphTypeLike]{data-preview} or `None`;
    `None` uses the chart's `kind`.

## Visibility, Stacking, and Fit

`Chart` defaults to `fit_content=False`, so the viewport/field supplies useful
plot dimensions.

```pyodide install="xnano>=1.0.10" height="22"
from xnano import Terminal
from xnano.components.chart import Chart

shown = Chart(
    series={"visible": [1, 3, 2]},
    visible=True,
    z=4,
    fit_content=False,
)
hidden = Chart(series={"hidden": [3, 1]}, visible=False, z=9, fit_content=True)

print("shared flags:", shown.visible, shown.z, shown.fit_content)
Terminal(width=58, height=12).render(shown, hidden)
```

??? example "Visibility, Stacking, and Fit"

    **`visible`**

    [Chart]{data-preview} accepts `visible=True | False`; hidden components do
    not paint.

    **`z`**

    [Chart]{data-preview} accepts an integer `z` stacking order.

    **`fit_content`**

    [Chart]{data-preview} accepts `fit_content=True | False`; charts default to
    `False` so their container supplies useful plot dimensions.

[Chart]: ../api/xnano/components/chart.md#xnano.components.chart.Chart
[Chart.series]: ../api/xnano/components/chart.md#xnano.components.chart.Chart.series
[Chart.kind]: ../api/xnano/components/chart.md#xnano.components.chart.Chart.kind
[Chart.colors]: ../api/xnano/components/chart.md#xnano.components.chart.Chart.colors
[Chart.x_bounds]: ../api/xnano/components/chart.md#xnano.components.chart.Chart.x_bounds
[Chart.y_bounds]: ../api/xnano/components/chart.md#xnano.components.chart.Chart.y_bounds
[Chart.x_label]: ../api/xnano/components/chart.md#xnano.components.chart.Chart.x_label
[Chart.y_label]: ../api/xnano/components/chart.md#xnano.components.chart.Chart.y_label
[Chart.legend]: ../api/xnano/components/chart.md#xnano.components.chart.Chart.legend
[Chart.legend_position]: ../api/xnano/components/chart.md#xnano.components.chart.Chart.legend_position
[SeriesData]: ../api/xnano/components/chart.md#xnano.components.chart.SeriesData
[Series]: ../api/xnano/components/schema.md#xnano.components.schema.Series
[GraphTypeLike]: ../api/xnano/_types.md#xnano._types.GraphTypeLike
[LegendPositionLike]: ../api/xnano/_types.md#xnano._types.LegendPositionLike
[ColorLike]: ../api/xnano/color.md#xnano.color.ColorLike
