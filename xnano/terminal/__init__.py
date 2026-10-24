"""
xnano.terminal

The real screen: the canvas that is on it, the function that opens one, the settings it is asked
for and what the terminal can do, which [`capabilities`][xnano.terminal.capabilities] reports.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator, Sequence
from typing import TYPE_CHECKING, cast, overload

from xnano._schema._axes import Percentage
from xnano._schema._content import Content
from xnano._schema._generics import DepsT, StateT
from xnano._schema._terminal import CapabilityStatus as CapabilityStatus
from xnano._schema._terminal import ColorProfile as ColorProfile
from xnano._schema._terminal import GraphicsProtocol as GraphicsProtocol
from xnano._schema._terminal import OpenSettings as OpenSettings
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
from xnano.terminal._opening import OpeningTerminal as OpeningTerminal
from xnano.terminal._settings import (
    appearance_with_content_error,
    split_settings,
)

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from xnano._schema._effects import WritableEffectSpecification
    from xnano._schema._hooks import KeyName
    from xnano._schema._terminal import CanvasSettings
    from xnano.hooks._context import Frame

__all__ = [
    'CapabilityStatus',
    'ColorProfile',
    'GraphicsCapabilities',
    'GraphicsProtocol',
    'KeyboardCapabilities',
    'OpenSettings',
    'OpeningTerminal',
    'Terminal',
    'TerminalCapabilities',
    'TerminalSettings',
    'capabilities',
    'iter',
    'iter_async',
    'open',
    'open_async',
]


class Terminal(Canvas[DepsT, StateT]):
    """
    A canvas that draws on your screen and reads your keyboard and mouse.

    A canvas becomes a terminal when it is opened, with [`open`][xnano.open] or
    [`Canvas.open`][xnano.canvas.Canvas.open]: it is the same object, and
    ``isinstance(canvas, xnano.Terminal)`` is how to ask whether a canvas is on the screen.
    It has every member of [`Canvas`][xnano.canvas.Canvas], and its devices are the real ones:
    its screen is the terminal's, its speaker the computer's sound, and its keyboard and mouse
    the person's. It runs by itself: opening it
    starts a loop on a thread of its own, and everything you write, remove or draw appears the
    moment it is declared, however slowly the rest of your program runs, because declaring
    only changes buffers and the loop draws them. A program has one screen, so only one
    terminal is open at a time.

    Attributes:
        is_closed: Whether the terminal has been closed, or its loop has ended.
        is_running: Whether the loop is running and has not been asked to end.
        capabilities: What the terminal answered about itself when the canvas was opened.
        settings: Every setting the terminal was opened with, as it was resolved.

    Examples:
        ```text
        with xnano.open(width=20, height=2) as terminal:
            terminal.screen.write('hello')
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
    effects: Sequence[WritableEffectSpecification] = (),
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
    effects: Sequence[WritableEffectSpecification] = (),
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
    effects: Sequence[WritableEffectSpecification] = (),
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
    effects: Sequence[WritableEffectSpecification] = (),
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
    the screen. See [`TerminalSettings`][xnano.terminal.TerminalSettings]. ``mouse``, ``scroll``
    and ``paste`` are turned on by themselves when a hook registered before opening needs
    them. A hook added after opening turns nothing on: one that needs input the screen does
    not report is attached and never runs.

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
            terminal.screen.write('hello')
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
    canvas: Canvas[DepsT, StateT] = _canvas_to_open(
        'open',
        canvas_or_content,
        title=title,
        width=width,
        height=height,
        settings=settings,
    )
    try:
        return canvas.open()
    except BaseException:
        canvas.close(raise_failure=False)
        raise


@overload
def open_async(
    canvas: Canvas[DepsT, StateT],
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    **settings: Unpack[OpenSettings],
) -> OpeningTerminal[DepsT, StateT]: ...
@overload
def open_async(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[WritableEffectSpecification] = (),
    **settings: Unpack[CanvasSettings],
) -> OpeningTerminal[None, None]: ...
@overload
def open_async(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[WritableEffectSpecification] = (),
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> OpeningTerminal[None, StateT]: ...
@overload
def open_async(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[WritableEffectSpecification] = (),
    deps: DepsT,
    **settings: Unpack[CanvasSettings],
) -> OpeningTerminal[DepsT, None]: ...
@overload
def open_async(
    content: Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[WritableEffectSpecification] = (),
    deps: DepsT,
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> OpeningTerminal[DepsT, StateT]: ...
def open_async(
    canvas_or_content: Canvas[object, object] | Content | None = None,
    /,
    *,
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    **settings: object,
) -> OpeningTerminal[DepsT, StateT]:
    """
    Put a canvas on your screen like [`open`][xnano.open], from a coroutine.

    The keywords, the canvas and the errors are the ones ``open()`` has; the terminal is
    asked what it can do while your event loop goes on running other tasks. Await the result
    for the [`Terminal`][xnano.Terminal], or enter it with ``async with``, which closes it and
    gives the screen back when the block ends. Errors are raised when it is awaited or
    entered.

    Then wait with the ``_async`` spellings, which let the rest of your program run:
    [`run_async`][xnano.canvas.Canvas.run_async],
    [`iter_async`][xnano.canvas.Canvas.iter_async],
    [`keyboard.wait_async`][xnano.devices.Keyboard.wait_async] and
    [`keyboard.prompt_async`][xnano.devices.Keyboard.prompt_async].

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
        The opening terminal: await it, or use it in ``async with``.

    Examples:
        ```text
        async def main() -> None:
            async with xnano.open_async(height=3, mouse=True) as terminal:
                terminal.screen.write('hello')
                await terminal.run_async(quit_on='q')

        asyncio.run(main())
        ```
    """
    if isinstance(canvas_or_content, Canvas):
        return cast('Canvas[DepsT, StateT]', canvas_or_content).open_async(
            title=title,
            width=width,
            height=height,
            **settings,  # type: ignore[arg-type]
        )

    async def open_new() -> Terminal[DepsT, StateT]:
        canvas: Canvas[DepsT, StateT] = _canvas_to_open(
            'open_async',
            canvas_or_content,
            title=title,
            width=width,
            height=height,
            settings=settings,
        )
        try:
            return await canvas.open_async()
        except BaseException:
            canvas.close(raise_failure=False)
            raise

    return OpeningTerminal(open_new)


@overload
def iter(
    canvas: Canvas[DepsT, StateT],
    /,
    *,
    frames: int | None = None,
    seconds: float | None = None,
    quit_on: KeyName | Sequence[KeyName] | None = 'ctrl+c',
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    **settings: Unpack[OpenSettings],
) -> Iterator[Frame]: ...
@overload
def iter(
    content: Content | None = None,
    /,
    *,
    frames: int | None = None,
    seconds: float | None = None,
    quit_on: KeyName | Sequence[KeyName] | None = 'ctrl+c',
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[WritableEffectSpecification] = (),
    deps: object = ...,
    state: object = ...,
    **settings: Unpack[CanvasSettings],
) -> Iterator[Frame]: ...
def iter(
    canvas_or_content: Canvas[object, object] | Content | None = None,
    /,
    *,
    frames: int | None = None,
    seconds: float | None = None,
    quit_on: KeyName | Sequence[KeyName] | None = 'ctrl+c',
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    **settings: object,
) -> Iterator[Frame]:
    """
    Open a terminal and run it one frame at a time: the program's main loop, as a ``for`` loop.

    It takes the keywords of [`open`][xnano.open] (so ``xnano.iter(fps=30, mouse=True)`` opens
    the terminal at 30 frames a second with the mouse on), opens the terminal when the loop
    starts, and closes it when the loop ends. Each [`Frame`][xnano.hooks.Frame] has the
    terminal in ``frame.canvas`` and the events that arrived since the previous frame in
    ``frame.events``; anything you change before the next frame is drawn.

    Without ``frames`` or ``seconds`` it runs the way [`run`][xnano.canvas.Canvas.run] does:
    until a key of ``quit_on`` is pressed, the terminal is asked to
    [`quit`][xnano.canvas.Canvas.quit], or you break out of the loop. With them, it also ends
    after that many frames, or when the terminal has run that long. To run a canvas you have
    one frame at a time, use [`Canvas.iter`][xnano.canvas.Canvas.iter].

    Args:
        canvas_or_content: A canvas from ``new()`` to open, or content to write into a new
            one.
        frames: The most frames to yield.
        seconds: The most seconds to run for.
        quit_on: The key, or keys, that end the loop and close the terminal; ``None`` for
            none.
        title: The window title.
        width: The width of the region to draw in, as for ``open()``.
        height: The height of the region to draw in, as for ``open()``.
        settings: The other keywords of ``open()``: the terminal settings, the look,
            ``fps``, ``bpm``, ``effects``, ``deps`` and ``state``.

    Yields:
        Each frame, until the loop ends.

    Raises:
        TerminalAlreadyOpenError: Another canvas is already on the screen.
        TerminalError: There is no terminal to draw on.

    Examples:
        ```text
        ball = None
        for frame in xnano.iter(height=3, fps=30, quit_on='q'):
            if ball is None:
                ball = frame.canvas.screen.write('o')
            for event in frame.events:
                if event.key is not None and event.key.key == 'space':
                    ball.x = 0
            ball.x = (ball.x + 1) % frame.canvas.screen.width
        ```
    """
    # The keywords were checked by the overloads of this function, which are those of open().
    opening = cast('Callable[..., Terminal[object, object]]', open)
    with opening(
        canvas_or_content, title=title, width=width, height=height, **settings
    ) as terminal:
        yield from terminal.iter(frames=frames, seconds=seconds, quit_on=quit_on)


@overload
def iter_async(
    canvas: Canvas[DepsT, StateT],
    /,
    *,
    frames: int | None = None,
    seconds: float | None = None,
    quit_on: KeyName | Sequence[KeyName] | None = 'ctrl+c',
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    **settings: Unpack[OpenSettings],
) -> AsyncIterator[Frame]: ...
@overload
def iter_async(
    content: Content | None = None,
    /,
    *,
    frames: int | None = None,
    seconds: float | None = None,
    quit_on: KeyName | Sequence[KeyName] | None = 'ctrl+c',
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    effects: Sequence[WritableEffectSpecification] = (),
    deps: object = ...,
    state: object = ...,
    **settings: Unpack[CanvasSettings],
) -> AsyncIterator[Frame]: ...
async def iter_async(
    canvas_or_content: Canvas[object, object] | Content | None = None,
    /,
    *,
    frames: int | None = None,
    seconds: float | None = None,
    quit_on: KeyName | Sequence[KeyName] | None = 'ctrl+c',
    title: str | None = None,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    **settings: object,
) -> AsyncIterator[Frame]:
    """
    Open a terminal and run it one frame at a time with ``async for``, like [`iter`][xnano.iter].

    The keywords, the frames and the ways the loop ends are the ones ``iter()`` has. Between
    frames the rest of your event loop runs, and the terminal's ``async def`` hooks run on it.

    Yields:
        Each frame, until the loop ends.

    Examples:
        ```text
        async def main() -> None:
            async for frame in xnano.iter_async(height=3, seconds=2):
                ...
        ```
    """
    opening = cast('Callable[..., OpeningTerminal[object, object]]', open_async)
    async with opening(
        canvas_or_content, title=title, width=width, height=height, **settings
    ) as terminal:
        async for frame in terminal.iter_async(
            frames=frames, seconds=seconds, quit_on=quit_on
        ):
            yield frame


def _canvas_to_open(
    operation: str,
    content: object,
    *,
    title: str | None,
    width: int | Percentage | str | None,
    height: int | Percentage | str | None,
    settings: dict[str, object],
) -> Canvas[DepsT, StateT]:
    """Check the keywords of ``open`` or ``open_async``, and create the canvas they open."""
    if 'realtime' in settings:
        raise TypeError(
            f'{operation}() takes no realtime: a canvas on the screen always runs on the wall '
            f'clock. Remove realtime=..., or keep the canvas off the screen with '
            f'xnano.new(realtime=True).'
        )
    if height is None and not _is_whole_window(_check_size('width', width)):
        raise ValueError(
            'A canvas on the screen with a width needs a height too, because it draws in a '
            "region of that size. Add height=... (cells, a percentage such as '50%', or "
            "'fit' for the height of the content), or remove width."
        )
    _check_size('height', height)
    # Checked here as well as in new(), so that an error names open().
    own = {'fps', 'bpm', 'effects', 'deps', 'state', 'layout', 'edges'}
    _, appearance = split_settings(
        operation, {name: value for name, value in settings.items() if name not in own}
    )
    if content is not None and appearance:
        raise appearance_with_content_error(operation, appearance)
    return _create(
        content,  # type: ignore[arg-type]
        title=title,
        width=width,
        height=height,
        **settings,  # type: ignore[arg-type]
    )
