---
title: Declarative schemas
icon: lucide/list-tree
---

# Declarative schemas

`Column` and `Series` are class-level declarations for reusable `Table` and
`Chart` components. Their attribute names connect incoming data to display
configuration, much as a grid field connects a value to layout configuration.

```python title="declarative_table.py"
import time

from xnano.components.schema import Column
from xnano.components.table import Table
from xnano.tui import Terminal

class ServiceTable(Table):
    service: str = Column()
    status: str = Column(
        color=lambda value: "green" if value == "ready" else "yellow"
    )
    latency: int = Column(format="{} ms", align="right")  # (1)!

Terminal(width=44, height=4).render(
    ServiceTable(
        data=[
            {"service": "api", "status": "ready", "latency": 12},
            {"service": "worker", "status": "busy", "latency": 48},
        ]
    )
)
time.sleep(3)
```

1. The annotation documents the source value. `Column` holds display rules and
   is removed from the runtime class namespace when the class is created.

<div class="xnano-demo" markdown>
![A table built from a declarative column schema](../assets/components/table-columns-dark.gif){ width="700" }
</div>

<!-- Demo key: components/table-columns; viewport: 44x4 cells. -->

`Column` can define a header, accessor, formatter, foreground, background,
alignment, and width. Foreground and background values may be functions of the
cell value. `Series` can define a legend label, color, and plot kind. Declared
items retain class definition order, and inherited declarations are collected
before declarations on the child class.

See [Table](table.md#declare-a-reusable-table) and
[Chart](chart.md#declare-series-styles) for complete examples.
