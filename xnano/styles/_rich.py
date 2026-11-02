"""
xnano.styles._rich

Content drawn by the rich library: rich markup, tables, panels, syntax, markdown, trees and any
other rich renderable, drawn at the size of the area that it is written in.
"""

from __future__ import annotations

import functools
import io
import reprlib
import sys
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
    A rich renderable, drawn at the size of the area that it is written in.

    Make one with [`from_rich`][xnano.from_rich]. Write it like any other content. It
    accepts each object that follows the protocols of rich: an object with
    ``__rich_console__`` or ``__rich__``. An optional ``__rich_measure__`` gives the natural
    width.

    Rich draws the renderable at the width of its placement. If the write gives no width,
    rich uses the natural width of the renderable, at most the width of the canvas. If the
    write gives a height, the renderable gets it as ``options.height``. If the write gives
    no height, a renderable that fills the height, such as a ``rich.layout.Layout``, gets
    the height of the canvas. xnano draws the renderable again when its placement changes
    size.

    Rich reads the time from the canvas clock. Thus, a ``rich.spinner.Spinner`` moves with
    the canvas and stops when the clock is paused. A ``rich.progress.Progress`` reads the
    time with its own ``get_time``. To make it follow the canvas clock, give it
    ``get_time=lambda: canvas.clock.elapsed_seconds``.

    xnano draws text as ``rich.print`` draws it, with markup, emoji codes and highlighting.
    To draw text without them, give a ``rich.text.Text`` instead of a string.

    xnano keeps the colors of rich: the 16 named colors, the 256 palette colors and true
    colors. It also keeps bold, dim, italic, underlined, blinking, reverse, concealed and
    struck-through text. A double underline shows as an underline. A frame, a circle and an
    overline show as plain text. xnano cells have no links, so a link keeps its text and its
    style, but not its address. xnano does not draw rich control codes, such as cursor
    movements.

    If a renderable changes in place, call ``refresh()`` on its placement to draw it again.
    For example, do this after you add a row to a table. If rich raises an error when it
    draws the renderable, xnano does not change the error. On Python 3.11 and later, the
    error has a note that names ``from_rich()`` and the type of the renderable.

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
        """Return the cells that rich draws for the renderable, at the size of its area."""
        from rich.console import Console
        from rich.measure import Measurement

        columns, rows = surface_of(context.target).region._grid_size()
        # The hook of a component context is the driver of the component. The driver
        # knows which sizes the write gave. A size that the write did not give follows the
        # content, so rich measures the content again on each run.
        driver = context.hook
        if not getattr(driver, '_is_width_given', True):
            columns = 0
        if not getattr(driver, '_is_height_given', True):
            rows = 0
        canvas_width = max(1, context.screen.width)
        # A console with its own width and height does not read the size of the terminal.
        # The console reads the canvas clock only when rich asks for the time. Thus, only a
        # renderable that moves runs again on each frame.
        console = Console(
            width=columns or canvas_width,
            height=rows or max(1, context.screen.height),
            color_system='truecolor',
            force_terminal=True,
            legacy_windows=False,
            file=io.StringIO(),
            get_time=lambda: context.clock.elapsed_seconds,
        )
        try:
            if not columns:
                natural = Measurement.get(console, console.options, self.renderable)
                console.width = max(1, min(natural.maximum, canvas_width))
            options = console.options.update(height=rows or None)
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
        except Exception as error:
            if sys.version_info >= (3, 11):
                error.add_note(
                    f'from_rich() could not draw the {type(self.renderable).__name__} '
                    'renderable. The error above occurred when rich drew it. To find the '
                    'cause, print the renderable with rich.print().'
                )
            raise
        return _core.Buffer.with_text(_core.StyledText(spans))


@functools.lru_cache(maxsize=1024)
def _style(rich_style: Any) -> _core.Style | None:
    """
    The xnano style of a rich style.

    Rich uses its style objects again, and they are hashable. Thus, this function converts
    each style once, also when a component makes a new
    [`RichContent`][xnano.styles.RichContent] on each frame.
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

    Write the result like any other content. Rich draws it at the size of its placement. If
    the write gives no width, rich uses the natural width of the renderable. xnano draws it
    again when that size changes. xnano draws text as ``rich.print`` draws it, with markup,
    emoji codes and highlighting. For the size, the time and the styles, see
    [`RichContent`][xnano.styles.RichContent]. Rich is not a dependency of xnano. To use
    this function, install rich.

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
