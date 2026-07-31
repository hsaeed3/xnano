---
title: "Sandbox"
icon: "lucide/flask-conical"
---

# Sandbox

Every code block on this page runs live in your browser through Pyodide — no
install, no local terminal. Edit the values, rerun, and watch the frame change.

Each example is short and self-contained. Change the colors, swap the data,
resize a grid — the point is to try things. The
[component reference](api/xnano/components.md) documents every option, and
[Getting Started](getting-started.md) builds a full app from the same pieces.

## Colors

Colors accept the full Tailwind palette by name: `"emerald-400"`, `"slate-900"`,
and so on — every family, every shade from `50` to `950`. The grid below renders
all of them. Change a shade in `shades` or drop a family from `palettes` to see
the effect.

```pyodide install="xnano>=1.2.2" height="28"
from xnano import render
from xnano.components.text import Text

palettes = (
    "amber", "blue", "cyan", "emerald", "fuchsia", "gray", "green",
    "indigo", "lime", "neutral", "orange", "pink", "purple", "red",
    "rose", "sky", "slate", "stone", "teal", "violet", "yellow", "zinc",
)
shades = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950)

rows = []
for palette in palettes:
    swatches = [
        Text(
            f" {shade:^3} ",
            foreground="black" if shade <= 400 else "white",
            background=f"{palette}-{shade}",
        )
        for shade in shades
    ]
    rows.append(Text([Text(f"{palette:>8} ", modifiers=("bold",)), *swatches]))

rows.append(Text([
    Text("   solid ", modifiers=("bold",)),
    Text(" black ", foreground="white", background="black"),
    Text(" white ", foreground="black", background="white"),
]))

render(*rows)
```

A Tailwind name is one option. Anywhere a color is accepted you can also pass a
CSS name, a hex string, an `(r, g, b)` tuple, or a `Color` object.

```pyodide install="xnano>=1.2.2" height="10"
from xnano import render
from xnano.components.text import Text

render(
    Text(" tailwind ", background="indigo-500", foreground="white"),
    Text(" css name ", background="rebeccapurple", foreground="white"),
    Text("   hex    ", background="#0ea5e9", foreground="black"),
    Text("  rgb     ", background=(244, 63, 94), foreground="white"),
    gap=1,
)
```

## Text

`Text` covers single words, inline spans, and whole paragraphs from one
constructor. Nest it to style a run inside a line without breaking the surrounding
flow — pass a list of `Text` where you'd otherwise pass a string.

```pyodide install="xnano>=1.2.2" height="15"
from xnano import render
from xnano.components.text import Text

render(Text(
    [
        Text("● ", foreground="emerald-400"),
        Text("healthy ", foreground="white", modifiers=("bold",)),
        Text("12ms", foreground="slate-300", modifiers=("italic", "underline")),
    ],
    background="slate-900",
))
```

The same component can also parse its input. Pass `ansi`, `markdown`, or
`language` and `Text` renders the result instead of the raw string. The three
modes are mutually exclusive — pick one.

```pyodide install="xnano>=1.2.2" height="36"
from xnano import render
from xnano.components.text import Text

ansi = Text("\x1b[32mpassed\x1b[0m  \x1b[31mfailed\x1b[0m", ansi=True)  # (1)!

markdown = Text(
    "# Title\n\n- **bold** item\n- `code` item",
    markdown=True,  # (2)!
)

code = Text(
    "def greet(name):\n    return f'hi {name}'",
    language="python",  # (3)!
)

render(ansi, markdown, code, gap=1)
```

1. `ansi=True` turns SGR escape sequences into styled runs — pipe a subprocess'
   colored output straight in.
2. `markdown=True` renders headings, emphasis, lists, and fenced code.
3. `language="python"` syntax-highlights via a Pygments lexer name.

## Charts and Bars

A `Chart` takes a mapping of labels to data — either bare `y` values or explicit
`(x, y)` pairs. Declare a `Series` per key to set its label, color, and `kind`,
and one chart can mix line, scatter, and bar. Try changing a `kind` below.

```pyodide install="xnano>=1.2.2" height="27"
from xnano import render
from xnano.components.chart import Chart, Series

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
render(chart)
```

For a compact trend without a full plot, `Bar` renders a series inline in a
single block. Set a fixed `max_value` so separate bars share a scale and stay
comparable.

```pyodide install="xnano>=1.2.2" height="22"
from xnano import render
from xnano.components.bar import Bar

render(
    Bar(data=[1, 4, 8, 12, 5, 9, 3], foreground="emerald-300", max_value=12),
    Bar(data=[1, 4, 8, 20, 6, 3, 10], foreground="amber-300", max_value=12),
    gap=1,
)
```

## Tables

Point `Table` at a list of dicts, dataclasses, or plain objects and it infers
the columns. For control, declare a `Column`: it takes a formatter, an accessor,
alignment, and width. Pass a callable for `color` or `background` and it receives
the cell value, so a column can style itself from its own data.

```pyodide install="xnano>=1.2.2" height="30"
from xnano import render
from xnano.components.schema import Column
from xnano.components.table import Table

class Services(Table):
    service: str = Column(
        header="SERVICE",
        accessor=lambda row: row["meta"]["name"],
        format=lambda value: value.upper(),
        color="cyan-300",
        width=14,
    )
    status: str = Column(
        color=lambda value: "green-300" if value == "ok" else "red-300",  # (1)!
        background=lambda value: "green-950" if value == "ok" else "red-950",
        align="center",
        width=14,
    )
    latency: int = Column(
        format="{} ms",  # (2)!
        align="right",
        width=12,
    )

table = Services(data=[
    {"meta": {"name": "api"}, "status": "ok", "latency": 12},
    {"meta": {"name": "database"}, "status": "degraded", "latency": 340},
])
render(table)
```

1. Pass a callable for `color` or `background` and it receives the cell value —
   the "degraded" row turns red without a second pass over the data.
2. A plain `str.format` template also works when you just need units.

Without any `Column` descriptors, `Table` infers columns straight from the keys:

```pyodide install="xnano>=1.2.2" height="12"
from xnano import render
from xnano.components.table import Table

render(Table(data=[
    {"name": "api", "region": "us-east", "requests": 1204},
    {"name": "worker", "region": "eu-west", "requests": 87},
]))
```

## Nested Grids

A grid can be another grid's field value, so a sidebar-and-content shell is a few
lines. Each child sets its own size with the sizing grammar — fractions (`"1/3"`),
`fr` units (`"2fr"`), `"fit"`, or a fixed cell count. Adjust the `width` values to
re-balance the layout.

```pyodide install="xnano>=1.2.2" height="25"
from xnano import BaseGrid, Field, render

class Sidebar(BaseGrid, direction="vertical", gap=1, border="rounded", title="nav"):
    home: str = Field(default="Home", height=1)
    search: str = Field(default="Search", height=1)
    settings: str = Field(default="Settings", height=1)

class App(BaseGrid, direction="horizontal", gap=2, border="double", title="nested grids", padding=1):
    sidebar: Sidebar = Field(default_factory=Sidebar, width="1/3")
    content: list[str] = Field(
        default_factory=lambda: ["overview", "metrics", "activity"],
        direction="vertical",
        gap=1,
        width="2fr",
        border="plain",
        title="content",
    )

render(App())
```

## Actions

You don't need a live terminal to drive a grid. An `Action` travels the same
dispatch path as real input, so you can render a grid to attach its hooks,
perform an action, and render again to see the updated state. This is also how
you test a grid frame-by-frame. Here a counter increments twice between frames.

```pyodide install="xnano>=1.2.2" height="24"
from xnano import Action, BaseGrid, Field, Terminal, on_action

INCREMENT = Action.keyboard("right")

class Counter(BaseGrid, border="rounded", title="synthetic action", padding=1):
    label: str = Field(default="count: 0", align="center")
    count: int = Field(default=0, state=True)

    @on_action(INCREMENT)
    def increment(self) -> None:
        self.count += 1
        self.label = f"count: {self.count}"

counter = Counter()
terminal = Terminal.offscreen(cols=42, rows=7)
try:
    terminal.render(counter)              # attaches hooks and paints frame zero
    terminal.actions.perform(INCREMENT)   # synthetic input; no polling loop
    terminal.actions.perform(INCREMENT)
    terminal.render(counter)              # paints the mutated frame
    print(terminal.get_output_as_ansi())
finally:
    terminal.close()
```

This is the same `@on_*` machinery a live app runs on, so the notes app from
[Getting Started](getting-started.md) can be tested the same way — in a browser,
without opening a terminal.

*[TUI]: A text-based user interface (your terminal applications).
[xnano]: index.md
