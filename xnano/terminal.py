"""
xnano.terminal

A canvas on your screen, and the function that opens one.
"""

from __future__ import annotations

import threading
import warnings
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Final, cast, overload

import xnano_core as _core
from xnano._values import Content, DepsT, StateT
from xnano.canvas import (
    Canvas,
    _appearance_with_content_error,
    _split_settings,
    new,
)
from xnano.errors import TerminalAlreadyOpenError

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from xnano.types import CanvasSettings, OpenSettings

__all__ = ['Terminal', 'open']

_live_terminal_lock: Final = threading.Lock()
_live_terminal_open: bool = False


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

    Examples:
        ```text
        with xnano.open(width=20, height=2) as terminal:
            terminal.write('hello')
            assert isinstance(terminal, xnano.Terminal)
            terminal.run(quit_on='q')
        ```
    """


def warn_if_output_is_not_held_back(*, requested: bool, is_held_back: bool) -> None:
    """Say so when ``capture`` could not be honored on this platform."""
    if requested and not is_held_back:
        warnings.warn(
            'This platform cannot hold back what a program prints while a canvas is on the '
            'screen, so a print or a log record can land in the middle of a frame and '
            'corrupt the screen. Log to a file instead, or pass capture=False to silence '
            'this warning.',
            RuntimeWarning,
            stacklevel=2,
        )


def _claim_screen() -> None:
    """Take the one screen of the program, or say that another canvas has it."""
    global _live_terminal_open
    with _live_terminal_lock:
        if _live_terminal_open:
            raise TerminalAlreadyOpenError(
                'A canvas is already on the screen, and a program has only one screen. Close '
                'it first, or draw into xnano.new() and show that instead.'
            )
        _live_terminal_open = True


def _release_screen() -> None:
    """Give the one screen of the program back."""
    global _live_terminal_open
    with _live_terminal_lock:
        _live_terminal_open = False


def _create_live_runtime(
    *,
    fps: float,
    width: int | None,
    height: int | None,
    gates: Mapping[str, object],
    title: str | None,
    clock: _core.Clock,
) -> _core.Runtime:
    """Create the runtime that draws on the screen, with the input the gates ask for."""
    mouse = gates['mouse']
    keyboard = gates['keyboard']
    uses_alternate_screen = bool(gates['alternate_screen']) and height is None
    options = _core.TerminalOptions(
        input=_core.InputOptions(
            mouse='buttons' if mouse is True else 'off' if mouse is False else 'motion',
            scroll=bool(gates['scroll']),
            bracketed_paste=bool(gates['paste']),
            focus_reporting=bool(gates['focus']),
            interrupt='stop' if gates['interrupt'] else 'event',
            keyboard='basic'
            if keyboard is True
            else 'off'
            if keyboard is False
            else 'disambiguated'
            if keyboard == 'disambiguated'
            else 'release_events',
        ),
        alternate_screen=uses_alternate_screen,
        should_capture_output=bool(gates['capture']),
        should_clear_on_close=bool(gates['clear']) and not uses_alternate_screen,
    )
    runtime = _core.Runtime.live(
        frame_interval_milliseconds=max(1, round(1000.0 / fps)),
        inline_height=height,
        inline_width=width,
        options=options,
        clock=clock,
    )
    if title is not None:
        runtime.title = title
    return runtime


@overload
def open(
    canvas: Canvas[DepsT, StateT],
    /,
    *,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    **settings: Unpack[OpenSettings],
) -> Terminal[DepsT, StateT]: ...
@overload
def open(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[Mapping[str, object]] = (),
    **settings: Unpack[CanvasSettings],
) -> Terminal[None, None]: ...
@overload
def open(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[Mapping[str, object]] = (),
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> Terminal[None, StateT]: ...
@overload
def open(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[Mapping[str, object]] = (),
    deps: DepsT,
    **settings: Unpack[CanvasSettings],
) -> Terminal[DepsT, None]: ...
@overload
def open(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[Mapping[str, object]] = (),
    deps: DepsT,
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> Terminal[DepsT, StateT]: ...
def open(
    canvas_or_content: Canvas[object, object] | Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
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
    shell's history comes back untouched. Give ``height`` (and optionally ``width``) to draw in
    a region of that size below the cursor instead; that region is erased when the canvas
    closes, unless you pass ``clear=False``. ``title`` is the window title.

    The input gates say what the screen reports: ``mouse`` for buttons and drags, ``scroll``
    for the wheel, ``keyboard``, ``paste``, ``focus`` and ``interrupt`` (``Ctrl-C``), and
    ``capture`` holds back what the program prints while the canvas is on the screen. See
    [`GateSettings`][xnano.types.GateSettings]. ``mouse``, ``scroll`` and ``paste`` are turned
    on by themselves when a hook registered before opening needs them.

    Args:
        canvas_or_content: A canvas from ``new()``, or content to write into a new canvas.
        title: The window title; ``None`` keeps the canvas's title.
        width: The width of the region to draw in; the whole window when neither ``width``
            nor ``height`` is given.
        height: The height of the region to draw in.
        settings: The other keywords of ``new()`` except ``realtime``: the gates, the
            canvas's look, ``fps``, ``bpm``, ``effects``, ``deps`` and ``state``.

    Returns:
        The open [`Terminal`][xnano.Terminal], which is also the one module-level functions
        such as [`active`][xnano.active] find.

    Raises:
        TerminalAlreadyOpenError: Another canvas is already on the screen.
        TypeError: ``realtime`` was given, an appearance keyword was given with content,
            ``padding`` or ``margin`` was given, or a keyword is unknown.
        ValueError: A ``width`` was given without a ``height``, or a value is out of range.
        RuntimeError: There is no terminal to draw on.

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
    if width is not None and height is None:
        raise ValueError(
            'A canvas on the screen with a width needs a height too, because it draws in a '
            'region of that size. Add height=..., or remove width.'
        )
    # Checked here as well as in new(), so that an error names open().
    own = {'fps', 'bpm', 'effects', 'deps', 'state'}
    _, appearance = _split_settings(
        'open', {name: value for name, value in settings.items() if name not in own}
    )
    if canvas_or_content is not None and appearance:
        raise _appearance_with_content_error('open', appearance)
    canvas: Canvas[DepsT, StateT] = new(
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
