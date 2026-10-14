# xnano-image

Load, process and convert images and animations to terminal cells without external libraries.

## Install

```bash
pip install xnano-image
```

Or install as an extra of the top-level `xnano` package:

```bash
pip install "xnano[image]"
```

## Example

```python
from xnano_image import TerminalImage, TerminalGraphics

# Create an image from raw RGBA bytes
width, height = 2, 2
pixels = bytes([255, 0, 0, 255] * (width * height))  # Red pixels
image = TerminalImage.from_rgba(width, height, pixels)

# Convert to terminal cells (half-block characters by default)
grid = image.to_cell_grid(columns=10, rows=5)

# Or load from a file: image = TerminalImage.open('photo.png')
# Half blocks work in every terminal; TerminalGraphics.detect() asks for sixel, kitty or iterm2
graphics = TerminalGraphics.half_blocks()
```

## What it provides

- **Image loading**: PNG, JPEG, GIF, WebP and the compact XNI1 container format
- **Processing**: resize, crop, scale, fit, quantize, flatten transparency and retime animations
- **Conversion**: to terminal cell grids (text) or animations with frame timing, with half-blocks or native graphics protocols
- **No external tools**: decoding and processing are built in
- **Graphics detection**: query terminal capabilities for sixel, Kitty or iTerm2 support

## Links

- **Repository**: https://github.com/hsaeed3/xnano
- **Documentation**: https://xnano.hammad.app
- **API reference**: https://xnano.hammad.app/api-reference/
- **License**: MIT
