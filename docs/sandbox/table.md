---
title: "Table & Column"
icon: "lucide/table"
---

# Table & Column Sandbox

This page covers every [Table]{data-preview} option—`data`, `columns`, `selected`,
`show_header`, `column_spacing`, all three highlight controls, and the shared
component flags—plus every [Column]{data-preview} descriptor option.

## Inferred Data Shapes

With `columns=None`, xnano infers fields from mappings, dataclass instances, or
attribute-bearing objects.

```pyodide install="xnano>=1.0.10" height="27"
import dataclasses

from xnano import Terminal
from xnano.components.table import Table

@dataclasses.dataclass
class Service:
    name: str
    status: str

class Job:
    def __init__(self, name, status):
        self.name = name
        self.status = status

tables = [
    Table(data=[{"name": "api", "status": "ok"}], columns=None),
    Table(data=[Service("db", "busy")], columns=None),
    Table(data=[Job("worker", "idle")], columns=None),
]
Terminal(width=52, height=12).render(*tables, gap=1)
```

??? example "Inferred Data Shapes"

    **`data`**

    [Table.data]{data-preview} accepts a sequence of mappings, dataclass
    instances, or objects with readable attributes.

## Columns

`columns` accepts a list of names or a mapping. Mapping values may be a header
string, a [Column]{data-preview}, an accessor callable, or `None` (the default column).

```pyodide install="xnano>=1.0.10" height="25"
from xnano import Terminal
from xnano.components.schema import Column
from xnano.components.table import Table

rows = [
    {"service": "api", "status": "ok", "latency": 12},
    {"service": "database", "status": "degraded", "latency": 340},
]

list_form = Table(data=rows, columns=["service", "status"])
mapping_form = Table(data=rows, columns={
    "service": "Service Name",                         # header string
    "upper": lambda row: row["status"].upper(),        # accessor callable
    "latency": Column(header="Latency", format="{}ms", align="right", width=10),
})

Terminal(width=66, height=11).render(list_form, mapping_form, gap=1)
```

??? example "Columns"

    **`columns`**

    [Table.columns]{data-preview} uses [ColumnsArg]{data-preview}: `None`, a
    sequence of field names, or a mapping whose values are a header `str`,
    [Column]{data-preview}, row accessor callable, or `None`.

## Selection and Highlighting

`selected` is a zero-based row index or `None`. `highlight_color`,
`highlight_background`, and `highlight_symbol` independently style that row.

```pyodide install="xnano>=1.0.10" height="21"
from xnano import Terminal
from xnano.components.table import Table

selected = 1  # try None, 0, 1, or 2
table = Table(
    data=[
        {"service": "api", "status": "ok"},
        {"service": "db", "status": "degraded"},
        {"service": "cache", "status": "ok"},
    ],
    selected=selected,
    highlight_color="white",
    highlight_background="violet-700",
    highlight_symbol="▶ ",
)
Terminal(width=48, height=8).render(table)
```

??? example "Selection and Highlighting"

    **`selected`**

    [Table.selected]{data-preview} is a zero-based `int` row index, or `None`
    for no selection.

    **`highlight_color`**

    [Table.highlight_color]{data-preview} accepts any [ColorLike]{data-preview}
    or `None`.

    **`highlight_background`**

    [Table.highlight_background]{data-preview} accepts any
    [ColorLike]{data-preview} or `None`.

    **`highlight_symbol`**

    [Table.highlight_symbol]{data-preview} accepts the string drawn before the
    selected row.

## Header and Column Spacing

`show_header` toggles the header row. `column_spacing` is the number of cells
between adjacent columns.

```pyodide install="xnano>=1.0.10" height="20"
from xnano import Terminal
from xnano.components.table import Table

rows = [{"a": 1, "b": 2, "c": 3}, {"a": 10, "b": 20, "c": 30}]
Terminal(width=48, height=8).render(
    Table(data=rows, show_header=False, column_spacing=1),
    Table(data=rows, show_header=True, column_spacing=5),
    gap=1,
)
```

??? example "Header and Column Spacing"

    **`show_header`**

    [Table.show_header]{data-preview} is `True | False`.

    **`column_spacing`**

    [Table.column_spacing]{data-preview} is the non-negative number of cells
    inserted between adjacent columns.

## `Column`

[Column]{data-preview} accepts `header`, `accessor`, `format`, `color`, `background`,
`align`, and `width`. The formatter may be a format string, callable, or
`None`; foreground/background may be static colors, value callables, or
`None`; alignment is `left`, `center`, `right`, or `None`; width is fixed
cells, a fractional share, or `None`.

```pyodide install="xnano>=1.0.10" height="30"
from xnano import Terminal
from xnano.components.schema import Column
from xnano.components.table import Table

class Services(Table):
    service: str = Column(
        header="SERVICE",
        accessor=lambda row: row["meta"]["name"],
        format=lambda value: value.upper(),
        color="cyan-300",
        background=None,
        align="left",
        width=14,
    )
    status: str = Column(
        format=None,
        color=lambda value: "green-300" if value == "ok" else "red-300",
        background=lambda value: "green-950" if value == "ok" else "red-950",
        align="center",
        width=14,
    )
    latency: int = Column(
        header=None,                 # derives "Latency"
        format="{} ms",             # str.format template
        color=None,
        background=None,
        align="right",
        width=12,
    )

table = Services(data=[
    {"meta": {"name": "api"}, "status": "ok", "latency": 12},
    {"meta": {"name": "database"}, "status": "degraded", "latency": 340},
])
Terminal(width=52, height=7).render(table)
```

??? example "`Column`"

    **`Column.header`**

    [Column]{data-preview} accepts `header: str | None`; `None` derives a title
    from the field name.

    **`Column.accessor`**

    [Column]{data-preview} accepts `accessor: Callable[[row], value] | None`;
    `None` uses normal key or attribute lookup.

    **`Column.format`**

    [Column]{data-preview} accepts a `str.format` template, a value callable,
    or `None`.

    **`Column.color`**

    [Column]{data-preview} accepts a [ColorLike]{data-preview}, a callable that
    returns one from the cell value, or `None`.

    **`Column.background`**

    [Column]{data-preview} accepts a [ColorLike]{data-preview}, a callable that
    returns one from the cell value, or `None`.

    **`Column.align`**

    [Column]{data-preview} accepts `"left"`, `"center"`, `"right"`, or `None`.

    **`Column.width`**

    [Column]{data-preview} accepts integer cells, a fractional `float`, or
    `None`.

## Fractional Column Widths

When every resolved column has a width, floats represent fractional shares.
Use integer widths when you also want text padding from `align`.

```pyodide install="xnano>=1.0.10" height="18"
from xnano import Terminal
from xnano.components.schema import Column
from xnano.components.table import Table

table = Table(
    data=[{"name": "build", "detail": "running documentation checks"}],
    columns={
        "name": Column(width=0.25),
        "detail": Column(width=0.75),
    },
)
Terminal(width=60, height=5).render(table)
```

??? example "Fractional Column Widths"

    **`Column.width`**

    [Column]{data-preview} accepts integer cell widths, fractional `float`
    shares, or `None`.

## Visibility, Stacking, and Intrinsic Size

```pyodide install="xnano>=1.0.10" height="18"
from xnano import Terminal
from xnano.components.table import Table

shown = Table(
    data=[{"flag": "visible", "z": 3}],
    visible=True,
    z=3,
    fit_content=True,
)
hidden = Table(data=[{"flag": "hidden"}], visible=False, z=9, fit_content=False)

print("shared flags:", shown.visible, shown.z, shown.fit_content)
Terminal(width=44, height=6).render(shown, hidden)
```

`z` matters when sibling paint areas overlap. `fit_content=True` asks the
table to use its measured size; `False` lets the containing field or viewport
dictate the extent.

??? example "Visibility, Stacking, and Intrinsic Size"

    **`visible`**

    [Table]{data-preview} accepts `visible=True | False`; hidden components do
    not paint.

    **`z`**

    [Table]{data-preview} accepts an integer `z` stacking order.

    **`fit_content`**

    [Table]{data-preview} accepts `fit_content=True | False` to choose measured
    or container-supplied dimensions.

[Table]: ../api/xnano/components/table.md#xnano.components.table.Table
[Table.data]: ../api/xnano/components/table.md#xnano.components.table.Table.data
[Table.columns]: ../api/xnano/components/table.md#xnano.components.table.Table.columns
[Table.selected]: ../api/xnano/components/table.md#xnano.components.table.Table.selected
[Table.show_header]: ../api/xnano/components/table.md#xnano.components.table.Table.show_header
[Table.column_spacing]: ../api/xnano/components/table.md#xnano.components.table.Table.column_spacing
[Table.highlight_color]: ../api/xnano/components/table.md#xnano.components.table.Table.highlight_color
[Table.highlight_background]: ../api/xnano/components/table.md#xnano.components.table.Table.highlight_background
[Table.highlight_symbol]: ../api/xnano/components/table.md#xnano.components.table.Table.highlight_symbol
[ColumnsArg]: ../api/xnano/components/table.md#xnano.components.table.ColumnsArg
[Column]: ../api/xnano/components/schema.md#xnano.components.schema.Column
[ColorLike]: ../api/xnano/color.md#xnano.color.ColorLike
