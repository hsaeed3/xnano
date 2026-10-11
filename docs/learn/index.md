---
title: "Getting Started"
icon: "fontawesome/solid/bolt"
---

# Getting Started

## Install

```bash
pip install xnano
```

Install only what you need with `pip install xnano-core`, `pip install xnano-audio` or
`pip install xnano-image`.

## Draw into a buffer

A [`Buffer`][xnano._xnano_core.Buffer] holds a grid of cells. Operations change it, and
`render` serializes it without opening a terminal.

```python
from xnano._xnano_core import Border, Buffer, Write

card = Buffer(width=12, height=3)
card.update(Border('rounded'), Write('hello', x=3, y=1))
print(card.render(format='text'))
```

## Run it on a runtime

A [`Runtime`][xnano._xnano_core.Runtime] mounts buffers, routes input and renders frames.
An offscreen runtime needs no terminal, which makes it the right choice for tests.

```python
from xnano._xnano_core import Buffer, Runtime, Write

with Runtime.offscreen(width=20, height=3) as runtime:
    buffer = Buffer()
    runtime.mount(buffer, geometry='inherit')
    buffer.update(Write('mounted'))
    runtime.step()
    print(runtime.snapshot().lines()[0])
```

Use `Runtime.live()` to draw to the real terminal.
