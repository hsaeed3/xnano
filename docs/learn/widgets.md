---
title: Widgets
icon: lucide/chart-column
---

# Widgets

A widget is ready-made content, such as a gauge, a chart, a table or a list.
You write a widget on the screen in the same way as text. A widget takes a
position, a size, a border and a title, as text does. `canvas.write()` is the
same as `canvas.screen.write()`, and `canvas.render()` is the same as
`canvas.screen.render()`.

The widgets are in [`xnano.widgets`][xnano.widgets]. xnano draws them with
[ratatui](https://ratatui.rs/concepts/widgets/), a Rust library for terminal
programs. Each section of this guide links to the ratatui widgets that draw the
xnano widgets. The ratatui pages show more examples and all the options.

## Gauges

A `Gauge` fills a bar to a ratio from `0` to `1` and shows a label on the bar.
A `LineGauge` shows the same ratio on one line. xnano draws them with the
ratatui widgets [`Gauge`][ratatui-gauge] and [`LineGauge`][ratatui-linegauge].

<!-- @code-block name="learn-widgets-gauges" type="image" height=5 -->
```python
import xnano
from xnano.styles import Style
from xnano.widgets import Gauge, LineGauge

with xnano.new(width=48, height=4) as canvas:
    canvas.write(
        Gauge(0.62, label='62% of 512 GB', gauge_style=Style('green')), width='100%'
    )
    canvas.write(
        LineGauge(0.35, label='upload', filled_style=Style('cyan')), width='100%', y=2
    )
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="learn-widgets-gauges" -->

![learn-widgets-gauges](../assets/examples/learn-widgets-gauges-light.png#only-light)
![learn-widgets-gauges](../assets/examples/learn-widgets-gauges-dark.png#only-dark)

<!-- /@code-block-asset -->

## Sparklines and bar charts

A `Sparkline` shows a series of values as bars that are one cell wide. It shows
the shape of the series in a small area. A `BarChart` shows bars, and each
`Bar` has a value and an optional label. xnano draws them with the ratatui
widgets [`Sparkline`][ratatui-sparkline], [`BarChart`][ratatui-barchart] and
[`Bar`][ratatui-bar].

<!-- @code-block name="learn-widgets-charts" type="image" height=12 -->
```python
import math

import xnano
from xnano.styles import Style
from xnano.widgets import Bar, BarChart, Sparkline

requests = [round(6 + 3 * math.sin(second / 4)) for second in range(46)]

with xnano.new(width=48, height=11) as canvas:
    canvas.write(
        Sparkline(requests, style=Style('cyan')),
        width='100%',
        height=3,
        border='rounded',
        title='requests',
    )
    canvas.write(
        BarChart(
            [Bar(73, label='cpu'), Bar(41, label='memory'), Bar(18, label='disk')],
            bar_width=8,
            bar_gap=2,
            bar_style=Style('magenta'),
        ),
        width='100%',
        height=7,
    )
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="learn-widgets-charts" -->

![learn-widgets-charts](../assets/examples/learn-widgets-charts-light.png#only-light)
![learn-widgets-charts](../assets/examples/learn-widgets-charts-dark.png#only-dark)

<!-- /@code-block-asset -->

## Tables

A `Table` takes its rows as lists of cells. To style a full row, for example
the header, use a `TableRow`. To style one cell, use a `TableCell`. xnano draws
them with the ratatui widgets [`Table`][ratatui-table], [`Row`][ratatui-row] and
[`Cell`][ratatui-cell].

<!-- @code-block name="learn-widgets-table" type="image" height=7 -->
```python
import xnano
from xnano.styles import Style
from xnano.widgets import Table, TableCell, TableRow

with xnano.new(width=48, height=6) as canvas:
    canvas.write(
        Table(
            [
                ['web', 'up', '41 ms'],
                ['api', 'up', '12 ms'],
                ['db', TableCell('down', style=Style('red')), '—'],
            ],
            header=TableRow(['service', 'status', 'p95'], style=Style(bold=True)),
        ),
        width='100%',
        border='rounded',
        title='services',
    )
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="learn-widgets-table" -->

![learn-widgets-table](../assets/examples/learn-widgets-table-light.png#only-light)
![learn-widgets-table](../assets/examples/learn-widgets-table-dark.png#only-dark)

<!-- /@code-block-asset -->

## Lists and tabs

An `ItemList` shows a list of items. `selected` sets the selected item, and
`highlight_symbol` and `highlight_style` mark it. `Tabs` shows a row of titles,
and `selected` sets the selected title. xnano draws them with the ratatui
widgets [`List`][ratatui-list] and [`Tabs`][ratatui-tabs].

<!-- @code-block name="learn-widgets-lists" type="image" height=7 -->
```python
import xnano
from xnano.styles import Style
from xnano.widgets import ItemList, Tabs

with xnano.new(width=48, height=6) as canvas:
    canvas.write(
        Tabs(
            ['mail', 'calendar', 'contacts'],
            selected=0,
            highlight_style=Style('yellow', bold=True),
        ),
        width='100%',
    )
    canvas.write(
        ItemList(
            ['inbox', 'drafts', 'sent', 'archive'],
            selected=1,
            highlight_symbol='› ',
            highlight_style=Style(reverse=True),
        ),
        height=4,
        y=2,
    )
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="learn-widgets-lists" -->

![learn-widgets-lists](../assets/examples/learn-widgets-lists-light.png#only-light)
![learn-widgets-lists](../assets/examples/learn-widgets-lists-dark.png#only-dark)

<!-- /@code-block-asset -->

## Widgets that follow the clock

Each number and text in a widget can be an
[expression](time.md#values-that-follow-the-clock). xnano calculates an
expression again on each frame. This gauge fills in ten seconds, and it needs no
hook:

<!-- @code-block name="learn-widgets-expression" type="gif" height=3
wait 4.0
-->
```python
import xnano
from xnano.widgets import Gauge

with xnano.open(height=2) as terminal:
    terminal.write(Gauge(terminal.clock / 10), width='100%')
    terminal.write('q quit', y='bottom', dim=True)
    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="learn-widgets-expression" -->

![learn-widgets-expression](../assets/examples/learn-widgets-expression-light.gif#only-light)
![learn-widgets-expression](../assets/examples/learn-widgets-expression-dark.gif#only-dark)

<!-- /@code-block-asset -->

## More widgets

`xnano.widgets` has more widgets:

| Widget | What it shows | ratatui widget |
| --- | --- | --- |
| `Chart` | Line and scatter plots of datasets on two axes | [`Chart`][ratatui-chart] |
| `Calendar` | A month, with a style for each event date in `events` | [`Monthly`][ratatui-monthly] |
| `Scrollbar` | The position in content that is longer than its area | [`Scrollbar`][ratatui-scrollbar] |
| `Paragraph` | Text that wraps, aligns and scrolls | [`Paragraph`][ratatui-paragraph] |
| `Figure` | Lines, circles, rectangles, points and maps on a plane with coordinates | [`Canvas`][ratatui-canvas] |

The [`xnano.widgets`][xnano.widgets] reference gives the arguments of each
widget.

[ratatui-gauge]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Gauge.html
[ratatui-linegauge]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.LineGauge.html
[ratatui-sparkline]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Sparkline.html
[ratatui-barchart]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.BarChart.html
[ratatui-bar]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Bar.html
[ratatui-table]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Table.html
[ratatui-row]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Row.html
[ratatui-cell]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Cell.html
[ratatui-list]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.List.html
[ratatui-tabs]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Tabs.html
[ratatui-chart]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Chart.html
[ratatui-monthly]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/calendar/struct.Monthly.html
[ratatui-scrollbar]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Scrollbar.html
[ratatui-paragraph]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Paragraph.html
[ratatui-canvas]: https://docs.rs/ratatui/0.30.0/ratatui/widgets/canvas/struct.Canvas.html
