"""
xnano.art

What is seen: pixel art written as text, worlds seen through a camera, single pixels and
decoded images. Images need the optional ``image`` extra: ``pip install "xnano[image]"``.

To paint pixels and images into a [`Region`][xnano.region.Region], draw an image with
[`Region.draw_image`][xnano.region.Region.draw_image] on a region viewed as
[`Region.half_blocks`][xnano.region.Region.half_blocks] (two pixels per cell) or
[`Region.braille`][xnano.region.Region.braille] (eight dots per cell).
[`Region.pixel_for_cell`][xnano.region.Region.pixel_for_cell] and
[`Region.cell_for_pixel`][xnano.region.Region.cell_for_pixel] convert between the two
coordinate systems.
"""

from xnano._schema._layout import PixelPreset as PixelPreset
from xnano.art._images import Image as Image
from xnano.art._images import load_image as load_image
from xnano.art._pixels import Pixel as Pixel
from xnano.art._worlds import Art as Art
from xnano.art._worlds import Camera as Camera
from xnano.art._worlds import draw as draw

__all__ = ['Art', 'Camera', 'Image', 'Pixel', 'PixelPreset', 'draw', 'load_image']
