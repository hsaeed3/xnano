"""
xnano.image

[`xnano-image`](https://github.com/hsaeed3/xnano/tree/main/packages/xnano-image) images that a
terminal can show. Needs the optional ``image`` extra: ``pip install "xnano[image]"``.
"""

from xnano import _optional

_optional.require('image', needed_for='xnano.image')

from xnano_image import (  # noqa: E402
    TerminalGraphics as TerminalGraphics,
)
from xnano_image import (  # noqa: E402
    TerminalImage as TerminalImage,
)

__all__ = ['TerminalGraphics', 'TerminalImage']
