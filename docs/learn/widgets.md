---
title: Widgets
icon: lucide/chart-column
---

# Widgets

Widgets draw the things text alone can't: gauges, charts, tables, lists and
tabs. They come from [ratatui](https://ratatui.rs/concepts/widgets/), the Rust
library xnano draws with, and live in [`xnano.widgets`][xnano.widgets].

A widget is a description of something to draw. You write it like any other
content, so it takes a position, a size, a border and a title the same way text
does.

## Gauges

A `Gauge` fills a bar to a ratio between `0` and `1`, with a label on it. A
`LineGauge` does the same on a single line.

<!-- @code-block name="learn-widgets-gauges" type="image" height=4 -->
```python
import xnano
from xnano.styles import Style
from xnano.widgets import Gauge, LineGauge

with xnano.new(width=48, height=4) as canvas:
    canvas.screen.write(
        Gauge(0.62, label='62% of 512 GB', gauge_style=Style('green')), width='100%'
    )
    canvas.screen.write(
        LineGauge(0.35, label='upload', filled_style=Style('cyan')), width='100%', y=2
    )
    print(canvas.screen.render(format='ansi'))
```

## Sparklines and bar charts

A `Sparkline` draws a row of values as bars one cell wide, the shape of a series
at a glance. A `BarChart` draws labelled bars.

<!-- @code-block name="learn-widgets-charts" type="image" height=11 -->
```python
import math

import xnano
from xnano.styles import Style
from xnano.widgets import Bar, BarChart, Sparkline

requests = [round(6 + 3 * math.sin(second / 4)) for second in range(46)]

with xnano.new(width=48, height=11) as canvas:
    canvas.screen.write(
        Sparkline(requests, style=Style('cyan')),
        width='100%',
        height=3,
        border='rounded',
        title='requests',
    )
    canvas.screen.write(
        BarChart(
            [Bar(73, label='cpu'), Bar(41, label='memory'), Bar(18, label='disk')],
            bar_width=8,
            bar_gap=2,
            bar_style=Style('magenta'),
        ),
        width='100%',
        height=7,
    )
    print(canvas.screen.render(format='ansi'))
```

## Tables

A `Table` takes its rows as lists. A `TableRow` styles a whole row, such as the
header, and a `TableCell` styles one cell.

<!-- @code-block name="learn-widgets-table" type="image" height=6 -->
```python
import xnano
from xnano.styles import Style
from xnano.widgets import Table, TableCell, TableRow

with xnano.new(width=48, height=6) as canvas:
    canvas.screen.write(
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
    print(canvas.screen.render(format='ansi'))
```

## Lists and tabs

An `ItemList` shows a list with one item selected, marked by its
`highlight_symbol` and `highlight_style`. `Tabs` shows a row of titles with one
selected.

<!-- @code-block name="learn-widgets-lists" type="image" height=6 -->
```python
import xnano
from xnano.styles import Style
from xnano.widgets import ItemList, Tabs

with xnano.new(width=48, height=6) as canvas:
    canvas.screen.write(
        Tabs(
            ['mail', 'calendar', 'contacts'],
            selected=0,
            highlight_style=Style('yellow', bold=True),
        ),
        width='100%',
    )
    canvas.screen.write(
        ItemList(
            ['inbox', 'drafts', 'sent', 'archive'],
            selected=1,
            highlight_symbol='› ',
            highlight_style=Style(reverse=True),
        ),
        height=4,
        y=2,
    )
    print(canvas.screen.render(format='ansi'))
```

## Widgets that follow the clock

Every number and text in a widget can be an
[expression](time.md#values-that-follow-the-clock), which xnano works out again
on every frame. This gauge fills over ten seconds, with no hook:

<!-- @code-block name="learn-widgets-expression" type="gif" height=2
wait 4.0
-->
```python
import xnano
from xnano.widgets import Gauge

with xnano.open(height=2) as terminal:
    terminal.screen.write(Gauge(terminal.clock / 10), width='100%')
    terminal.screen.write('q quit', y='bottom', dim=True)
    terminal.run(stop_on='q')
```

## More widgets

`xnano.widgets` also has a `Chart` for line and scatter plots, a `Calendar`, a
`Scrollbar`, `Paragraph` for wrapped text, and `Figure` for drawing lines,
circles, rectangles and maps. The [`xnano.widgets`][xnano.widgets] reference
covers each one, and its link to the ratatui widget it draws with.
