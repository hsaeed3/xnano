"""
xnano.terminal

The real screen: the canvas that is on it, the function that opens one, the settings it is asked
for and what the terminal can do, which [`capabilities`][xnano.terminal.capabilities] reports.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast, overload

from xnano._schema._axes import Percentage
from xnano._schema._content import Content
from xnano._schema._generics import DepsT, StateT
from xnano._schema._terminal import TerminalSettings as TerminalSettings
from xnano.canvas import (
    Canvas,
    _check_size,
    _create,
    _is_whole_window,
)
from xnano.terminal._capabilities import (
    GraphicsCapabilities as GraphicsCapabilities,
)
from xnano.terminal._capabilities import (
    KeyboardCapabilities as KeyboardCapabilities,
)
from xnano.terminal._capabilities import (
    TerminalCapabilities as TerminalCapabilities,
)
from xnano.terminal._capabilities import (
    capabilities as capabilities,
)
from xnano.terminal._capabilities import (
    capabilities_from_core,
)
from xnano.terminal._screen import window_size
from xnano.terminal._settings import (
    appearance_with_content_error,
    split_settings,
)
from xnano_core import Size

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from xnano._schema._terminal import CanvasSettings, OpenSettings
    from xnano.types import RenderableEffectSpecification

__all__ = [
    'GraphicsCapabilities',
    'KeyboardCapabilities',
    'Terminal',
    'TerminalCapabilities',
    'TerminalSettings',
    'capabilities',
    'open',
]


class Terminal(Canvas[DepsT, StateT]):
    """
    A canvas that draws on your screen and reads your keyboard and mouse.

    A canvas becomes a terminal when it is opened, with [`open`][xnano.open] or
    [`Canvas.open`][xnano.canvas.Canvas.open]: it is the same object, and
    ``isinstance(canvas, xnano.Terminal)`` is how to ask whether a canvas is on the screen.
    It has every member of [`Canvas`][xnano.canvas.Canvas]. It runs by itself: opening it
    starts a loop on a thread of its own, and everything you write, remove or draw appears the
    moment it is declared, however slowly the rest of your program runs, because declaring
    only changes buffers and the loop draws them. A program has one screen, so only one
    terminal is open at a time.

    Attributes:
        is_closed: Whether the terminal has been closed, or its loop has ended.
        is_running: Whether the loop is running and has not been asked to end.
        capabilities: What the terminal answered about itself when the canvas was opened.
        window: The size of the whole terminal window in cells.
        settings: Every setting the terminal was opened with, as it was resolved.

    Examples:
        ```text
        with xnano.open(width=20, height=2) as terminal:
            terminal.write('hello')
            assert isinstance(terminal, xnano.Terminal)
            terminal.run(quit_on='q')
        ```
    """

    @property
    def capabilities(self) -> TerminalCapabilities:
        """What the terminal answered about itself when the canvas was opened."""
        return self._host.call(
            lambda: capabilities_from_core(
                self._runtime.device.capabilities, self._runtime.device.keyboard
            )
        )

    @property
    def window(self) -> Size:
        """
        The size of the whole terminal window in cells.

        For a terminal opened with a ``height`` it is larger than
        [`size`][xnano.canvas.Canvas.size], which is the region the canvas draws in; for a
        terminal that takes the whole window the two are equal.
        """
        size = window_size()
        return Size(size.columns, size.lines)

    @property
    def settings(self) -> TerminalSettings:
        """A copy of every setting of the terminal, including the ones that hooks turned on."""
        return cast('TerminalSettings', dict(self._resolved_gates))


@overload
def open(
    canvas: Canvas[DepsT, StateT],
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    **settings: Unpack[OpenSettings],
) -> Terminal[DepsT, StateT]: ...
@overload
def open(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[RenderableEffectSpecification] = (),
    **settings: Unpack[CanvasSettings],
) -> Terminal[None, None]: ...
@overload
def open(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[RenderableEffectSpecification] = (),
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> Terminal[None, StateT]: ...
@overload
def open(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[RenderableEffectSpecification] = (),
    deps: DepsT,
    **settings: Unpack[CanvasSettings],
) -> Terminal[DepsT, None]: ...
@overload
def open(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[RenderableEffectSpecification] = (),
    deps: DepsT,
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> Terminal[DepsT, StateT]: ...
def open(
    canvas_or_content: Canvas[object, object] | Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    **settings: object,
) -> Terminal[DepsT, StateT]:
    """
    Put a canvas on your screen and return it as a [`Terminal`][xnano.Terminal].

    Given a canvas from [`new`][xnano.new], this is [`Canvas.open`][xnano.canvas.Canvas.open]:
    the same object is attached to the screen and its time continues. Given content or
    nothing, it creates the canvas with ``new()`` (the same keywords, except ``realtime``)
    and attaches that. From here on, anything you write, remove or draw appears at once, on a
    loop of the canvas's own that your code never waits for. A ``with`` block closes it and
    gives the screen back.

    By default the canvas takes over the whole window, on the alternate screen so that your
    shell's history comes back untouched; ``width='100%', height='100%'`` asks for the same.
    Give ``height`` (and optionally ``width``) to draw in a region of that size below the cursor
    instead, in cells or as a percentage of the window such as ``'50%'``; that region is erased
    when the canvas closes, unless you pass ``clear=False``. ``title`` is the window title.

    The terminal settings say what the screen reports: ``mouse`` for buttons and drags,
    ``scroll`` for the wheel, ``keyboard``, ``paste``, ``focus`` and ``interrupt``
    (``Ctrl-C``), and ``capture`` holds back what the program prints while the canvas is on
    the screen. See [`TerminalSettings`][xnano.types.TerminalSettings]. ``mouse``, ``scroll``
    and ``paste`` are turned on by themselves when a hook registered before opening needs
    them.

    Args:
        canvas_or_content: A canvas from ``new()``, or content to write into a new canvas.
        title: The window title; ``None`` keeps the canvas's title.
        width: The width of the region to draw in, in cells or as a percentage of the
            window; the whole window when neither ``width`` nor ``height`` is given.
        height: The height of the region to draw in, in cells or as a percentage of the
            window.
        settings: The other keywords of ``new()`` except ``realtime``: the terminal
            settings, the canvas's look, ``fps``, ``bpm``, ``effects``, ``deps`` and ``state``.

    Returns:
        The open [`Terminal`][xnano.Terminal], which is also the one module-level functions
        such as [`active`][xnano.active] find.

    Raises:
        TerminalAlreadyOpenError: Another canvas is already on the screen.
        TerminalError: There is no terminal to draw on.
        TypeError: ``realtime`` was given, an appearance keyword was given with content, or a
            keyword is unknown.
        ValueError: A ``width`` was given without a ``height``, or a value is out of range.

    Examples:
        ```text
        with xnano.open(height=3, mouse=True) as terminal:
            terminal.write('hello')
            terminal.run(quit_on='q')
        ```
    """
    if isinstance(canvas_or_content, Canvas):
        return cast('Canvas[DepsT, StateT]', canvas_or_content).open(
            title=title,
            width=width,
            height=height,
            **settings,  # type: ignore[arg-type]
        )
    if 'realtime' in settings:
        raise TypeError(
            'open() takes no realtime: a canvas on the screen always runs on the wall clock. '
            'Remove realtime=..., or keep the canvas off the screen with '
            'xnano.new(realtime=True).'
        )
    if height is None and not _is_whole_window(_check_size('width', width)):
        raise ValueError(
            'A canvas on the screen with a width needs a height too, because it draws in a '
            "region of that size. Add height=... (cells, or a percentage such as '50%'), or "
            'remove width.'
        )
    # Checked here as well as in new(), so that an error names open().
    own = {'fps', 'bpm', 'effects', 'deps', 'state', 'layout', 'edges'}
    _, appearance = split_settings(
        'open', {name: value for name, value in settings.items() if name not in own}
    )
    if canvas_or_content is not None and appearance:
        raise appearance_with_content_error('open', appearance)
    canvas: Canvas[DepsT, StateT] = _create(
        canvas_or_content,  # type: ignore[arg-type]
        title=title,
        width=width,
        height=height,
        **settings,  # type: ignore[arg-type]
    )
    try:
        return canvas.open()
    except BaseException:
        canvas.close(raise_failure=False)
        raise
