---
title: "Schema"
icon: "lucide/braces"
---

# Schema

There's no `Schema` widget to instantiate. `Column` and `Series` are descriptors — declared once as class attributes on a `Table` or `Chart` subclass, the same way a `BaseGrid` declares `Field`.

Reach for a bare `Table(data=..., columns=...)` when the shape of your data changes call to call. Reach for a subclass when it doesn't — the columns become part of the class itself, not an argument you pass around.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: data-driven Table with columns= argument versus declarative Table subclass with Column descriptors">
<svg viewBox="0 0 720 220" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="sch-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <!-- Data-driven -->
  <rect class="gcd-panel" x="36" y="28" width="300" height="164" rx="14" />
  <text class="gcd-label" x="186" y="58" text-anchor="middle">data-driven</text>
  <rect class="gcd-window" x="60" y="76" width="252" height="40" rx="8" />
  <text class="gcd-chrome-label" x="186" y="100" text-anchor="middle">Table(data=…, columns=…)</text>
  <path class="gcd-line" d="M80 140 h80" stroke-width="3" stroke-linecap="round" />
  <path class="gcd-line-soft" d="M80 156 h160" stroke-width="3" stroke-linecap="round" />
  <text class="gcd-z-caption" x="186" y="176" text-anchor="middle">shape changes per call</text>

  <!-- Declarative -->
  <rect class="gcd-panel gcd-panel-accent" x="384" y="28" width="300" height="164" rx="14" />
  <text class="gcd-label gcd-label-accent" x="534" y="58" text-anchor="middle">declarative</text>
  <rect class="gcd-window" x="408" y="76" width="252" height="40" rx="8" />
  <text class="gcd-chrome-label" x="534" y="100" text-anchor="middle">class Services(Table)</text>
  <text class="gcd-z-label gcd-z-label-on" x="534" y="140" text-anchor="middle">service = Column()</text>
  <text class="gcd-z-label gcd-z-label-on" x="534" y="160" text-anchor="middle">latency = Column(…)</text>
  <text class="gcd-z-caption gcd-z-caption-on" x="534" y="182" text-anchor="middle">schema on the class</text>
</svg>
</div>

??? example "Interactive Example"

    The following code block is interactive and can be run directly in the browser.

    ```pyodide install="xnano>=1.0.8" hl_lines="4 5 6"
    from xnano import render
    from xnano.components.table import Column, Table

    class Services(Table):
        service: str = Column()
        status: str = Column(color=lambda v: "green" if v == "ok" else "red")
        latency: int = Column(align="right", format="{}ms")

    render(Services(data=[
        {"service": "api", "status": "ok", "latency": 12},
        {"service": "db", "status": "degraded", "latency": 340},
    ]))
    ```

```python title="A Declarative Table" hl_lines="4 5 6"
from xnano.components.table import Column, Table

class Services(Table):
    service: str = Column() # (1)!
    status: str = Column(color=lambda v: "green" if v == "ok" else "red") # (2)!
    latency: int = Column(align="right", format="{}ms")

Services(data=rows, selected=0)
```

1. A bare `Column()` derives its header from the attribute name (`service` → `"Service"`) and reads the same-named key or attribute off each row.
2. `color` — and `background`, `format` — accept a callable, so a cell's style can depend on its own value.

<div class="xnano-demo" markdown>
![table declarative dark](../assets/components/table_declarative-dark.gif){.demo-dark}
![table declarative light](../assets/components/table_declarative-light.gif){.demo-light}
</div>

<br/>

`Chart` follows the same pattern with `Series()` instead of `Column()`, for styling one series at a time:

```python title="A Declarative Chart" hl_lines="2 3"
class Latency(Chart):
    p50 = Series(color="green")
    p99 = Series(color="red")

Latency(series={"p50": [12, 14, 11], "p99": [88, 95, 90]})
```

<br/>

Both descriptors are documented in full on the [Schema]{data-preview} API reference, alongside [Table]{data-preview} and [Chart]{data-preview}.

[Schema]: ../api/xnano/components/schema.md
[Table]: table.md
[Chart]: chart.md
