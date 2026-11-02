"""
xnano.styles._rich

Content drawn by the rich library: rich markup, tables, panels, syntax, markdown, trees and any
other rich renderable, laid out at the width of the area it is written in.
"""

from __future__ import annotations

import functools
import io
import reprlib
from typing import TYPE_CHECKING, Any

import xnano_core as _core
from xnano._internal._surface import surface_of

if TYPE_CHECKING:
    from rich.console import RenderableType

    from xnano.hooks._context import Context

__all__ = ['RichContent', 'from_rich']

_STANDARD_COLORS = (
    'black',
    'red',
    'green',
    'yellow',
    'blue',
    'magenta',
    'cyan',
    'gray',
    'dark_gray',
    'light_red',
    'light_green',
    'light_yellow',
    'light_blue',
    'light_magenta',
    'light_cyan',
    'white',
)
"""The xnano names of the 16 terminal colors, in the order of their ANSI numbers."""

_INSTALL_RICH = (
    'from_rich() draws with the rich library, which is not installed. Install it with '
    'pip install rich, and try again.'
)


class RichContent:
    """
    A rich renderable, drawn at the width of the area it is written in.

    Make one with [`from_rich`][xnano.from_rich] and write it like any other content. Rich lays
    it out at the width of its placement, or at its natural width (at most the width of the
    canvas) when the placement has none, and draws it again when that width changes, so a
    table or a panel always fits. Colors and text modifiers come through as they are: the 16
    named colors, the 256 palette colors and true colors, and bold, dim, italic, underline,
    blink, reverse, concealed and strikethrough text.

    Rich renderables that change in place, such as a table that gets a new row, are drawn
    again when you call ``refresh()`` on the placement.

    Attributes:
        renderable: What rich draws: rich markup text, or an object with ``__rich_console__``
            or ``__rich__``.

    Examples:
        ```python
        import xnano
        from rich.table import Table

        table = Table('service', 'status')
        table.add_row('web', '[green]up[/green]')

        with xnano.new(width=30, height=6) as canvas:
            canvas.screen.write(xnano.from_rich(table))
            assert 'web' in canvas.screen.render()
        ```
    """

    __slots__ = ('renderable',)

    def __init__(self, renderable: RenderableType) -> None:
        """
        Wrap a rich renderable. Use [`from_rich`][xnano.from_rich], which checks it first.

        Args:
            renderable: Rich markup text, or an object with ``__rich_console__`` or
                ``__rich__``.
        """
        self.renderable = renderable

    def __repr__(self) -> str:
        return f'RichContent({self.renderable!r})'

    def __xnano_write__(self, context: Context[object, object]) -> _core.Buffer:
        """Lay the renderable out with rich at the width of its area, and return its cells."""
        from rich.console import Console
        from rich.measure import Measurement

        columns, rows = surface_of(context.target).region._grid_size()
        canvas_width = max(1, context.screen.width)
        console = Console(
            width=columns or canvas_width,
            color_system='truecolor',
            force_terminal=True,
            legacy_windows=False,
            file=io.StringIO(),
        )
        if not columns:
            natural = Measurement.get(console, console.options, self.renderable)
            columns = max(1, min(natural.maximum, canvas_width))
        options = console.options.update(width=columns, height=rows or None)
        lines = console.render_lines(self.renderable, options, pad=False)
        spans: list[_core.TextSpan] = []
        for index, line in enumerate(lines):
            if index:
                spans.append(_core.TextSpan('\n'))
            spans.extend(
                _core.TextSpan(segment.text, style=_style(segment.style))
                for segment in line
                if segment.text and not segment.control
            )
        return _core.Buffer.with_text(_core.StyledText(spans))


@functools.lru_cache(maxsize=1024)
def _style(rich_style: Any) -> _core.Style | None:
    """
    The xnano style of a rich style.

    Rich reuses its style objects, and they are hashable, so each is converted once, also
    when a component makes a new [`RichContent`][xnano.styles.RichContent] on every frame.
    """
    if rich_style is None:
        return None
    return _core.Style(
        _color(rich_style.color),
        _color(rich_style.bgcolor),
        bold=bool(rich_style.bold),
        dim=bool(rich_style.dim),
        italic=bool(rich_style.italic),
        underline=bool(rich_style.underline or rich_style.underline2),
        blink=bool(rich_style.blink),
        rapid_blink=bool(rich_style.blink2),
        reverse=bool(rich_style.reverse),
        hidden=bool(rich_style.conceal),
        crossed_out=bool(rich_style.strike),
    )


def _color(color: Any) -> str | tuple[int, int, int] | None:
    """The xnano color of a rich color: a name, a palette index or ``(red, green, blue)``."""
    if color is None or color.is_default:
        return None
    kind = color.type.name
    if kind in ('STANDARD', 'WINDOWS'):
        return _STANDARD_COLORS[color.number]
    if kind == 'EIGHT_BIT':
        return str(color.number)
    red, green, blue = color.get_truecolor()
    return (red, green, blue)


def from_rich(renderable: RenderableType) -> RichContent:
    """
    Draw anything the rich library draws: rich markup, a table, a panel, syntax and more.

    Write the result like any other content. Rich lays it out at the width of its placement,
    or at its natural width (at most the width of the canvas) when the placement has none, and
    draws it again when that width changes. Colors and text modifiers come through as they
    are. Rich itself is not a dependency of xnano: install it to use this.

    Args:
        renderable: Rich markup text such as ``'[bold red]error[/]'``, or any rich renderable:
            an object with ``__rich_console__`` or ``__rich__``, such as a
            ``rich.table.Table``, a ``rich.panel.Panel`` or a ``rich.syntax.Syntax``.

    Returns:
        The content, ready for [`Screen.write`][xnano.devices.Screen.write].

    Raises:
        ImportError: The rich library is not installed.
        TypeError: ``renderable`` is not something rich can draw.

    Examples:
        ```python
        import xnano
        from rich.panel import Panel

        with xnano.new(width=24, height=3) as canvas:
            canvas.screen.write(xnano.from_rich(Panel('[bold]ready[/bold]')), width='100%')
            assert 'ready' in canvas.screen.render()
        ```
    """
    try:
        from rich.protocol import is_renderable
    except ImportError:
        raise ImportError(_INSTALL_RICH) from None
    if not is_renderable(renderable):
        raise TypeError(
            f'from_rich() draws what rich can render, but got the '
            f'{type(renderable).__name__} {reprlib.repr(renderable)}. Pass rich markup text '
            'or a rich renderable, such as a rich.table.Table, or write the value with '
            'screen.write() directly.'
        )
    return RichContent(renderable)
