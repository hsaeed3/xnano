"""
xnano.styles

Colors, styles and styled text.

A [`Style`][xnano.styles.Style] holds colors and text modifiers; styled text is built from spans
and lines that each carry their own style.
"""

from xnano_core import (
    Color as Color,
)
from xnano_core import (
    ColorName as ColorName,
)
from xnano_core import (
    ColorValue as ColorValue,
)
from xnano_core import (
    Style as Style,
)
from xnano_core import (
    StyledText as StyledText,
)
from xnano_core import (
    TextContent as TextContent,
)
from xnano_core import (
    TextLine as TextLine,
)
from xnano_core import (
    TextSpan as TextSpan,
)

__all__ = [
    'Color',
    'ColorName',
    'ColorValue',
    'Style',
    'StyledText',
    'TextContent',
    'TextLine',
    'TextSpan',
]
