---
title: "xnano"
icon: "fontawesome/solid/x"
---

# xnano

xnano is a terminal for Python, built on the [ratatui](https://ratatui.rs) and
[tachyonfx](https://github.com/ratatui/tachyonfx) Rust crates. It gives you a
surface of cells to put things on: text, widgets, images, pixels and sound.
There is no framework to learn first. You build small values from the inside out
(`xnano.region`, `xnano.pixel_art`, `xnano.Note`), put them on a canvas, and the
canvas can be put on your screen. Every position and size can be an expression of
time, of the canvas's size or of anything else on screen, so a layout is a line
of Python that is evaluated again on every frame.

```python
import xnano
from xnano.expressions import ParentWidth, TimeElapsed, Width

card = xnano.region('Hello, world!', border='rounded', padding={'horizontal': 2})
print(card.render())  # a value renders on its own, with no screen

with xnano.open(width=40, height=6) as terminal:
    terminal.screen.write(card, x='center')
    ball = terminal.screen.write('●', y=5)
    ball.x = (ParentWidth - Width) * (TimeElapsed % 2 / 2)
    terminal.run(stop_on='q')
```

The `xnano` distribution installs the terminal and its Rust engine, and two
optional extras:

| Distribution | Import | What it provides |
| --- | --- | --- |
| `xnano` | `xnano` | The terminal API: `new`, `open`, placements, hooks, effects, components, input, regions, art, images and sound. |
| `xnano-core` | `xnano_core` | The compiled engine: buffers, widgets, operations, effects and the expression language. |
| `xnano-audio` | `xnano_audio` | Synthesis, melodies, playback and capture. Install with `pip install "xnano[audio]"`. |
| `xnano-image` | `xnano_image` | Image and animation loading and conversion to terminal cells. Install with `pip install "xnano[image]"`. |

Start with the [getting started guide](learn/index.md), then read the
[API reference](api-reference/index.md). For a larger example, run
`python -m xnano` (or the `xnano` command) to see the features working together.
Its source is `xnano/demo.py`.

<!-- markdownlint-disable MD046 -->

!!! note "Looking for xnano v1?"

    Everything here is xnano v2. The previous grid-and-field API is on the
    [`v1` branch](https://github.com/hsaeed3/xnano/tree/v1); install the latest
    v1 release, [1.2.3](https://github.com/hsaeed3/xnano/releases/tag/xnano%2Fv1.2.3),
    with `pip install "xnano>=1.2.3,<2"`. Its guides are kept under
    [Legacy v1](v1/index.md).

<!-- markdownlint-enable MD046 -->
