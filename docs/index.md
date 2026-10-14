---
title: "xnano"
icon: "fontawesome/solid/x"
---

# xnano

xnano is a terminal for Python, built on the [ratatui](https://ratatui.rs) and
[tachyonfx](https://github.com/ratatui/tachyonfx) Rust crates. It gives you a surface of
cells to put things on: text, widgets, images, pixels and sound. There is no framework to learn
first. Every position and size can be a formula of time, of the terminal's size or of anything
else on screen, so a layout is a line of Python that is evaluated again on every frame.

```python
import xnano
from xnano.expressions import ParentWidth, TimeElapsed, Width

with xnano.iter(width=40, height=3) as terminal:
    terminal.write('Hello, world!', x='center')
    ball = terminal.write('●', y=2)
    ball.x = (ParentWidth - Width) * (TimeElapsed % 2 / 2)
    terminal.run(quit_on='q')
```

The `xnano` distribution installs the terminal and its Rust engine, and two optional extras:

| Distribution | Import | What it provides |
| --- | --- | --- |
| `xnano` | `xnano` | The terminal API: `open`, placements, hooks, input, pixels, scenes and sound. |
| `xnano-core` | `xnano_core` | The compiled engine: buffers, widgets, operations, effects and the expression language. |
| `xnano-audio` | `xnano_audio` | Synthesis, melodies, playback and capture. Install with `pip install "xnano[audio]"`. |
| `xnano-image` | `xnano_image` | Image and animation loading and conversion to terminal cells. Install with `pip install "xnano[image]"`. |

Start with the [getting started guide](learn/index.md), then read the
[API reference](api-reference/index.md). The repository's `examples/` folder has twenty-one
runnable programs, from a hello world to a playable pixel-art world.

!!! note "Looking for xnano v1?"

    Everything here is xnano v2. The previous grid-and-field API is on the
    [`v1` branch](https://github.com/hsaeed3/xnano/tree/v1); install the latest v1 release,
    [1.2.3](https://github.com/hsaeed3/xnano/releases/tag/xnano%2Fv1.2.3), with
    `pip install "xnano>=1.2.3,<2"`. Its guides are kept under [Legacy v1](v1/index.md).
