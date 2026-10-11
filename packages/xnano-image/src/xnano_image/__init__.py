"""
xnano-image

`xnano-image` is the image backend for `xnano`, and a standalone way to load,
process and convert images and animations (PNG, JPEG, GIF, WebP and the compact XNI1
container) into terminal cells from Python, with no extra compilation step.

It does not depend on `xnano-core`. The two packages exchange plain `bytes` in two
shared formats, since Python extension modules cannot share native classes:

- a **cell grid** (`XCG1`) is one terminal frame: the symbol, colors and modifiers of
  every cell;
- a **cell animation** (`XCA1`) is a sequence of cell grids, each with its display time.

`xnano-core` draws them with `TerminalWidget.cell_grid(...)` and
`TerminalWidget.cell_animation(...)`.

Everything is exported directly from this module. The public API is made up of:

- [`TerminalImage`][xnano_image.TerminalImage]: open, decode, resize, crop, quantize and
  retime an image or animation, and convert it with `to_cell_grid`, `to_cell_grids`,
  `to_cell_animation` or `to_ansi`. Export it with `encode`, `save` or `to_xni`. All
  operations release the GIL while they work.
- [`TerminalGraphics`][xnano_image.TerminalGraphics]: terminal graphics
  capabilities (`half_blocks()`, `detect()` or `from_capabilities(...)`), used to draw
  with a native graphics protocol (`sixel`, `kitty`, `iterm2`) instead of half-block
  characters.
- [`cell_grid_size`][xnano_image.cell_grid_size],
  [`cell_grid_to_text`][xnano_image.cell_grid_to_text] and
  [`cell_grid_to_ansi`][xnano_image.cell_grid_to_ansi]: inspect and print a cell
  grid.
- [`TerminalImageError`][xnano_image.TerminalImageError]: a `ValueError` raised for invalid
  data or arguments.
- [`TerminalQueryError`][xnano_image.TerminalQueryError]: an `OSError`
  raised when the terminal cannot be queried for its graphics capabilities.

Examples:
    ```python
    from xnano_image import TerminalImage, cell_grid_to_ansi

    image = TerminalImage.open('photo.png')
    print(cell_grid_to_ansi(image.to_cell_grid(40)))
    ```
"""

from xnano_image._xnano_image import (
    TerminalGraphics,
    TerminalImage,
    TerminalImageError,
    TerminalQueryError,
    __version__,
    cell_grid_size,
    cell_grid_to_ansi,
    cell_grid_to_text,
)

__all__ = (
    'TerminalGraphics',
    'TerminalImage',
    'TerminalImageError',
    'TerminalQueryError',
    '__version__',
    'cell_grid_size',
    'cell_grid_to_ansi',
    'cell_grid_to_text',
)
