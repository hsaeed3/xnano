---
title: Images and GIFs
description: Native-resolution still images and real-time GIF playback.
---

# Images and GIFs

Image support is an optional extra so the base xnano installation remains
small:

```bash
pip install "xnano[images]"
```

`Image` converts two vertical source pixels into one `▀` terminal cell. The
upper pixel is truecolor foreground and the lower pixel is truecolor
background, preserving every source pixel without requiring a terminal image
protocol.

```python
from xnano.images import Image
from xnano.tui import Terminal

Terminal().render(Image("photo.png"))
Terminal().run(Image("animation.gif"))
```

`render()` paints a still image—or the first GIF frame—immediately. `run()`
keeps the live terminal repainting and selects frames from the GIF's original
wall-clock durations, so playback does not speed up or slow down with the
terminal tick rate. The same component works through the buffer-backed
WASM/Pyodide render path.

Call `animation.seek(milliseconds)` before a render when a buffer-backed host
needs a deterministic animation timestamp.

## Placement and scaling

The default `fit="crop"` never resizes source pixels. It aligns the source and
viewport centers, crops overflow equally around the center, and pads a smaller
source around the center.

```python
Image("photo.png")                 # native resolution, centered crop
Image("photo.png", fit="contain")  # preserve ratio, show the whole image
Image("photo.png", fit="cover")    # preserve ratio, fill and crop
Image("photo.png", fit="stretch")  # fill the exact target rectangle
Image("photo.png", fit="smart")    # adapt cover/contain to the viewport
```

`smart` uses a light center crop when the source and viewport have similar
aspect ratios. For strongly different shapes it switches to containment, so
small or narrow regions keep the complete composition. The built-in demo
uses this adaptive mode and recalculates it whenever the available area
changes.

For denser terminal mapping, set `horizontal_pixels_per_cell=2`. Each 2×2
source-pixel block then becomes one terminal cell: the two upper pixels are
averaged into the `▀` foreground and the two lower pixels into its
background. The demo clips use this mode, while the default remains the
lossless-width 1×2 mapping.

Because most terminal cells are roughly twice as tall as they are wide, raw
2×2 mapping can look horizontally compressed. Set
`correct_terminal_aspect=True` to compensate before sampling while retaining
one processed 2×2 block per cell. The built-in demo enables this correction.

Animated images are decoded eagerly when the component is created. This makes
the first paint immediate and keeps playback free of frame-time file I/O.

## Dependency-free precomputed frames

`ImageData.from_bytes()` loads xnano's compact XNI1 frame container using only
the standard library. It is intended for WASM bundles and built-in assets that
must render without installing Pillow:

```python
from xnano.images import Image, ImageData

data = ImageData.from_bytes(payload)
animation = Image(data)
```

The source encoder is
[`scripts/precompute_demo_image.py`](https://github.com/hsaeed3/xnano/blob/main/scripts/precompute_demo_image.py).

The optional `python -m xnano` clips are stored separately as `luffy.xni` and
`luffy_deck.xni`; neither is included in the wheel. When an image intro is
randomly selected, xnano checks its ignored `xnano/<name>.xni` cache, then
`docs/assets/<name>.xni` during development, and finally the matching GitHub
raw file. A successful first download populates the package-local cache, so
later launches do not make a network request. If all three paths fail, the
resolver raises an error naming the missing asset. XNI decoding uses only the
standard library, so the demo clips do not require Pillow or the `images`
extra.

`luffy_deck.xni` retains all 71 source frames but overrides their original
60 ms delays with an exact 30 FPS 33/34 ms cadence. The resulting 2.367-second
clip is intentionally fast-forwarded for smoother terminal motion.

---

::: xnano.images.Image

[API reference]: ../api/xnano/images.md
