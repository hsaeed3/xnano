"""
xnano.styles._core_styles

Colors, styles and styled text.

A [`Style`][xnano.styles.Style] holds colors and text modifiers; styled text is built from spans
of text that each carry their own style. Colors are given as names, hex strings or
``(red, green, blue)`` tuples wherever a ``ColorValue`` is accepted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from xnano_core import Color as _CoreColor
    from xnano_core import ColorName as _CoreColorName
    from xnano_core import ColorValue as _CoreColorValue
    from xnano_core import Style as _CoreStyle
    from xnano_core import StyledText as _CoreStyledText
    from xnano_core import TextContent as _CoreTextContent
    from xnano_core import TextLine as _CoreTextLine
    from xnano_core import TextSpan as _CoreTextSpan

    Color = _CoreColor
    """
    A terminal color: a named palette color, a palette index or a true color.

    Reach for it to compare or convert a color; anywhere a color is accepted, a name such
    as ``'red'``, a hex string or a ``(red, green, blue)`` tuple works too.

    ```python
    import xnano
    from xnano.styles import Color

    with xnano.new(width=12, height=1) as canvas:
        canvas.screen.write('warm', foreground=Color('#ff8800'))
        assert Color('#ff8800').to_rgb() == (255, 136, 0)
        assert 'warm' in canvas.screen.render()
    ```
    """

    ColorName = _CoreColorName
    """
    The names of the palette colors, such as ``'red'``, ``'light_blue'`` or ``'reset'``.

    Use it to annotate a parameter that accepts only a palette name.

    ```python
    import xnano
    from xnano.styles import ColorName

    sky: ColorName = 'light_blue'
    with xnano.new(width=12, height=1) as canvas:
        canvas.screen.write('sky', foreground=sky)
        assert 'sky' in canvas.screen.render()
    ```
    """

    ColorValue = _CoreColorValue
    """
    Anything that stands for a color: a name, a hex string, a tuple or a
    [`Color`][xnano.styles.Color].

    Use it to annotate a parameter that takes a color in any of those forms: a
    [`ColorName`][xnano.styles.ColorName] such as ``'red'``, a hex string such as
    ``'#ff8800'`` or a ``(red, green, blue)`` tuple.

    ```python
    import xnano
    from xnano.styles import ColorValue

    colors: list[ColorValue] = ['red', '#00ff88', (255, 136, 0)]
    with xnano.new(width=12, height=3) as canvas:
        for row, color in enumerate(colors):
            canvas.screen.write('text', y=row, foreground=color)
        assert canvas.screen.render().count('text') == 3
    ```
    """

    Style = _CoreStyle
    """
    A foreground color, a background color and text modifiers such as bold and underline.

    Reach for it when several pieces of text share one look, or to combine a look with a
    [`StyledText`][xnano.styles.StyledText] span.

    ```python
    import xnano
    from xnano.styles import Style

    alert = Style('red', bold=True)
    with xnano.new(width=12, height=1) as canvas:
        canvas.screen.write('alert', style=alert)
        assert 'bold' in alert.modifiers
        assert 'alert' in canvas.screen.render()
    ```
    """

    StyledText = _CoreStyledText
    """
    Text made of differently styled spans.

    Use it when one line of text needs more than one style.

    ```python
    import xnano
    from xnano.buffers import Buffer
    from xnano.styles import Style, StyledText, TextSpan

    message = StyledText([TextSpan('error: ', style=Style('red', bold=True)), TextSpan('disk full')])
    with xnano.new(width=20, height=1) as canvas:
        canvas.screen.write(Buffer(message))
        assert str(message) == 'error: disk full'
        assert canvas.screen.render() == 'error: disk full'
    ```
    """

    TextContent = _CoreTextContent
    """
    Text in any of its forms: a string, a [`StyledText`][xnano.styles.StyledText] or a
    list of those.

    Use it to annotate a parameter that takes text.

    ```python
    import xnano
    from xnano.buffers import Buffer
    from xnano.styles import Style, StyledText, TextContent, TextSpan

    lines: TextContent = ['plain', StyledText([TextSpan('styled', style=Style('green'))])]
    with xnano.new(width=8, height=2) as canvas:
        canvas.screen.write(Buffer(lines))
        assert canvas.screen.render().splitlines() == ['plain', 'styled']
    ```
    """

    TextLine = _CoreTextLine
    """
    One wrapped line of a text layout, with the text it holds and where it starts and
    ends.

    Read it from ``xnano_core.layout_text`` when you need to know how a text wraps at a
    given width.

    ```python
    from xnano_core import layout_text

    from xnano.styles import TextLine

    line = layout_text('hello world', width=6).lines[0]
    assert isinstance(line, TextLine)
    assert line.text == 'hello '
    assert (line.start_offset, line.end_offset, line.width) == (0, 6, 6)
    ```
    """

    TextSpan = _CoreTextSpan
    """
    A run of text with one style.

    Use it to build a [`StyledText`][xnano.styles.StyledText] whose runs look different.

    ```python
    import xnano
    from xnano.buffers import Buffer
    from xnano.styles import Style, StyledText, TextSpan

    warning = TextSpan('warning', style=Style('yellow', bold=True))
    with xnano.new(width=20, height=1) as canvas:
        canvas.screen.write(Buffer(StyledText([warning, TextSpan(': low disk')])))
        assert warning.text == 'warning'
        assert canvas.screen.render() == 'warning: low disk'
    ```
    """

_CORE_NAMES: Final[dict[str, str]] = {
    'Color': 'Color',
    'ColorName': 'ColorName',
    'ColorValue': 'ColorValue',
    'Style': 'Style',
    'StyledText': 'StyledText',
    'TextContent': 'TextContent',
    'TextLine': 'TextLine',
    'TextSpan': 'TextSpan',
}
"""The name each styles object has in ``xnano_core``, by the name it has here."""

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


def __getattr__(name: str) -> object:
    """Import an object from ``xnano_core`` the first time it is read, then keep it."""
    core_name = _CORE_NAMES.get(name)
    if core_name is None:
        raise AttributeError(
            f'xnano.styles has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    import xnano_core

    value = getattr(xnano_core, core_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
