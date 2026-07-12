---
title: "xnano.core.renderable"
---

# xnano.core.renderable

Renderable helpers live under `xnano._renderable`. The module exports a
print-like `render(*renderables, ...)` that writes ANSI to stdout outside an
active session — the preferred path for simple one-shot text demos.

For sized native widgets (tables, charts, progress) or session-frame painting,
use `Terminal().render(...)` instead. Interactive grids use
`Terminal().run(...)`.
