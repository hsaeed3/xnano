---
title: "xnano.core.renderable"
---

# xnano.core.renderable

The print-like `render(*renderables, ...)` helper is available from the package
root:

```python
from xnano import render

render("Hello from xnano!")
```

or:

```python
import xnano

xnano.render("Hello from xnano!")
```

It writes ANSI to stdout outside an active session — the preferred path for
simple one-shot text demos. The implementation lives in
[`xnano._renderable`](../_renderable.md).

For sized native widgets (tables, charts, progress) or session-frame painting,
use `Terminal().render(...)` instead. Interactive grids use
`Terminal().run(...)`.
