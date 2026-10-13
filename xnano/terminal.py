"""
xnano.terminal

The terminal you draw into, and the functions that open it.
"""

from __future__ import annotations

import contextvars
import os
import threading
import warnings
from collections.abc import Callable, Sequence
from typing import (
    TYPE_CHECKING,
    Final,
    Literal,
    cast,
    overload,
)

import xnano_core as _core
from xnano_core import FrameContext

if TYPE_CHECKING:
    from _typeshed import DataclassInstance
    from typing_extensions import Self, TypeIs
    from xnano_audio import InstrumentName, Pitch, TerminalAudioEffect
    from xnano_image import TerminalImage

    from xnano.audio import Audio, Playable
    from xnano.context import Context

from xnano._hooks import _Hooked
from xnano._host import _Host, _InlineHost, _ThreadHost
from xnano._media import ImageSource, content_buffer
from xnano._optional import is_image, require
from xnano._values import (
    RGB,
    Axis,
    AxisName,
    ColorValue,
    Content,
    PixelEncoding,
    StateT,
    TerminalBackend,
    ValueT,
)
from xnano.composition import Composition
from xnano.errors import (
    TerminalAlreadyOpenError,
    TerminalClosedError,
    TerminalError,
    release_frames,
)
from xnano.input import Input
from xnano.loop import Loop
from xnano.output import Output
from xnano.pixels import Pixels
from xnano.placement import Placement
from xnano.scene import Scene
from xnano.state import StateProxy, bind_proxy, prepare_state, reference_for

_active_terminal: contextvars.ContextVar[Terminal[object] | None] = (
    contextvars.ContextVar('xnano.active_terminal', default=None)
)
"""The terminal that module-level functions act on, per thread and per async task."""

_live_terminal_lock: Final = threading.Lock()
_live_terminal_open: bool = False


def warn_if_output_is_not_held_back(*, requested: bool, is_held_back: bool) -> None:
    """Say so when ``should_capture_output`` could not be honored on this platform."""
    if requested and not is_held_back:
        warnings.warn(
            'This platform cannot hold back what a program prints while a live terminal is '
            'open, so a print or a log record can land in the middle of a frame and '
            'corrupt the screen. Log to a file instead, or pass '
            'should_capture_output=False to silence this warning.',
            RuntimeWarning,
            stacklevel=2,
        )


def _is_color(value: object) -> TypeIs[_core.Color | RGB]:
    if isinstance(value, _core.Color):
        return True
    return (
        isinstance(value, tuple)
        and len(value) == 3
        and all(
            isinstance(channel, int) and not isinstance(channel, bool)
            for channel in value
        )
    )


def _text_content(
    content: Content,
    *,
    style: _core.Style | None,
    title: str | None,
    border: _core.BorderKind | None,
) -> Content:
    """Lines of text become one text; a style, title or border makes the text a styled box."""
    if isinstance(content, (list, tuple)) and all(
        isinstance(line, str) for line in content
    ):
        content = '\n'.join(cast('Sequence[str]', content))
    if style is None and title is None and border is None:
        return content
    if not isinstance(content, str):
        raise TypeError(
            'style, title and border decorate text, but this is not text. Add a string (or a '
            'list of lines), or give the widget its own style and block.'
        )
    if title is None and border is None:
        buffer = _core.Buffer.with_text(content)
        if style is not None:
            buffer.update(_core.ApplyStyle(style))
        return buffer
    lines = content.split('\n')
    return _core.Paragraph(
        content,
        style=style,
        block=_core.Block(title, border_type=border or 'plain'),
        width=max(max(len(line) for line in lines), len(title or '')) + 2,
        height=len(lines) + 2,
    )


class Terminal(_Hooked[StateT]):
    """
    A surface of cells with a clock, a cursor, event hooks, sound and pixels.

    Get one from [`open`][xnano.open]. A live terminal draws on your screen and reads
    your keyboard and mouse. It runs by itself: opening it starts a loop on a thread of its
    own, and everything you add, remove or draw appears the moment it is declared, however
    slowly the rest of your program runs, because declaring only changes buffers and the
    loop draws them. An offscreen terminal draws into memory on a clock that only moves when
    you move it, which makes it deterministic; both have the same methods.

    What you put on the terminal is declared on the terminal itself:
    [`add`][xnano.Terminal.add], [`write`][xnano.Terminal.write],
    [`hook`][xnano.Terminal.hook] and indexing. Everything else is grouped by what it is:

    * ``terminal.clock`` is the [`Clock`][xnano_core.Clock] everything runs on.
    * ``terminal.cursor`` is the one [`Cursor`][xnano_core.Cursor] of the screen.
    * ``terminal.state`` is the dataclass given to ``open(state=...)``.
    * ``terminal.loop`` is the [`Loop`][xnano.Loop]: frames and simulation updates.
    * ``terminal.output`` is the [`Output`][xnano.Output]: what was drawn.
    * ``terminal.audio`` is the [`Audio`][xnano.audio.Audio]: notes, melodies, sounds and the
      microphone.

    Any thread may add, remove, write, draw and play. Hooks run on the terminal's loop, so
    keep them short.

    Attributes:
        is_closed: Whether the terminal has been closed, or its loop has ended.
        is_live: Whether the terminal draws on your screen.
        is_autonomous: Whether the terminal runs by itself on a thread of its own.
        is_running: Whether the loop is running and has not been stopped.
        backend: ``'terminal'`` for a live terminal, ``'offscreen'`` for one in memory.
        root: The buffer everything is added to, as large as the terminal.
        size: The size of the terminal in cells.
        width: The width of the terminal in cells.
        height: The height of the terminal in cells.
        title: Window title last set on the terminal; ``None`` clears the title.
        clock: The clock everything on the terminal runs on.
        cursor: The terminal's one cursor.
        state: The dataclass given to ``open(state=...)``.
        loop: The [`Loop`][xnano.Loop]: frames and simulation updates.
        output: The [`Output`][xnano.Output]: what was drawn, and held-back text.
        audio: The [`Audio`][xnano.audio.Audio]: notes, melodies, sounds and the microphone.

    Examples:
        ```python
        import xnano

        with xnano.open(offscreen=True, width=12, height=2) as terminal:
            terminal.write('hello', x=1, y=1)
            terminal.output.render()
            assert terminal.output.snapshot().lines()[1] == ' hello'
        ```
    """

    loop: Loop
    """The terminal's frame loop and simulation updates."""
    output: Output
    """The terminal's drawn frames and captured text."""

    def __init__(
        self,
        create_runtime: Callable[[], _core.Runtime],
        *,
        fps: float,
        is_live: bool,
        is_autonomous: bool,
        state: StateT,
        should_capture_output: bool = False,
    ) -> None:
        """
        Open a terminal. Use [`open`][xnano.open] instead of calling this.

        Args:
            create_runtime: Creates the runtime, on the thread that will run it.
            fps: The most frames drawn per second.
            is_live: Whether the terminal draws on the screen.
            is_autonomous: Whether the terminal runs by itself on a thread of its own.
            state: A dataclass instance the terminal keeps and validates, or ``None``.
            should_capture_output: Whether printed text is held back from a live screen.
        """
        super().__init__()
        self._terminal = self
        self._lock = threading.RLock()
        self._root = _core.Buffer()
        self._buffer = self._root
        self._fps = fps
        self._is_live = is_live
        self._placements: list[Placement[StateT]] = []
        self._timers: list[_core.ScheduledCall] = []
        self._runtime_hooks: list[_core.Hook] = []
        self._frame_hook: _core.Hook | None = None
        self._is_closed = False
        self._is_finalized = False
        self._stop_requested = threading.Event()
        self._failure: BaseException | None = None
        self._failure_report = ''
        self._should_capture_output = should_capture_output
        self._offscreen_milliseconds = 0
        self._state_proxy: StateProxy | None = None
        self._state_store = (
            None if state is None else prepare_state(cast('DataclassInstance', state))
        )
        self._images: dict[int, ImageSource] = {}
        # Only placements with a formula or a range need looking at before each frame.
        self._dynamic: dict[int, Placement[StateT]] = {}
        self._frame_callback_count = 0
        self.loop = Loop(cast('Terminal[object]', self))
        self.output = Output(cast('Terminal[object]', self))
        self._audio: Audio | None = None
        self._input: Input | None = None
        self._runtime_object: _core.Runtime | None = None
        self._clock: _core.Clock | None = None
        self._cursor: _core.Cursor | None = None
        self._size = _core.Size(0, 0)
        self._previous = _active_terminal.get()
        _active_terminal.set(cast('Terminal[object]', self))
        host_type = _ThreadHost if is_autonomous else _InlineHost
        self._host: _Host
        try:
            host_type(self, create_runtime)
            if self._state_store is not None:
                self._state_proxy = bind_proxy(self._state_store, self._request_frame)
        except BaseException:
            _active_terminal.set(self._previous)
            self._finalize()
            raise

    # -- the loop -----------------------------------------------------------------------

    def _attach(self, runtime: _core.Runtime) -> None:
        """Connect the runtime. Runs on the loop's thread."""
        self._runtime_object = runtime
        self._clock = runtime.clock
        self._cursor = runtime.cursor
        warn_if_output_is_not_held_back(
            requested=self._should_capture_output, is_held_back=runtime.is_output_captured
        )
        runtime.mount(self._root, geometry='inherit')
        self._size = runtime.device.size
        self._frame_hook = runtime.on_frame(self._on_loop_frame, target=self._root)
        if self._state_store is not None:
            runtime.watch_state(self._state_store)

    def _detach(self) -> None:
        """Release everything the terminal registered. Runs on the loop's thread."""
        self._finalize()
        self._cancel_hooks()
        if self._audio is not None:
            self._audio._close()
        self._images.clear()
        for hook in self._runtime_hooks:
            hook.cancel()
        self._runtime_hooks.clear()
        for timer in self._timers:
            timer.cancel()
        self._timers.clear()
        if self._frame_hook is not None:
            self._frame_hook.cancel()
            self._frame_hook = None
        with self._lock:
            placements = list(self._placements)
        for placement in placements:
            placement.remove()

    def _finalize(self) -> None:
        global _live_terminal_open
        with self._lock:
            if self._is_finalized:
                return
            self._is_finalized = True
            self._is_closed = True
        self._stop_requested.set()
        if self._is_live:
            with _live_terminal_lock:
                _live_terminal_open = False

    @property
    def _runtime(self) -> _core.Runtime:
        """The runtime, which only the terminal's loop may touch."""
        runtime = self._runtime_object
        if runtime is None or not self._host.is_on_loop():
            raise TerminalError(
                "The runtime belongs to the terminal's own thread, and this is another one. "
                'Declare what you want with the terminal, which hands the work over to it.'
            )
        return runtime

    def _on_loop_frame(self, core_context: FrameContext) -> None:
        """Before every frame: follow the size and evaluate the formulas."""
        runtime = self._runtime
        self._size = runtime.device.size
        with self._lock:
            placements = list(self._dynamic.values())
        # A function that runs before every frame needs a frame to run before.
        is_time_dependent = self._frame_callback_count > 0
        elapsed_seconds = runtime.clock.elapsed_seconds
        for source in list(self._images.values()):
            source.refresh(self._size, elapsed_seconds)
            if source.animation is not None:
                source.animation.advance(elapsed_seconds)
                is_time_dependent = True
        finished = []
        for placement in placements:
            is_time_dependent |= placement._apply_bindings(runtime)
            if not placement._bindings and not placement._limits:
                finished.append(id(placement))
        if finished:
            with self._lock:
                for key in finished:
                    placement = self._dynamic.get(key)
                    if (
                        placement is not None
                        and not placement._bindings
                        and not placement._limits
                    ):
                        del self._dynamic[key]
        if is_time_dependent:
            # A formula that follows time needs the next frame too.
            runtime.request_frame()

    def _request_frame(self) -> None:
        """Make sure a frame follows a change that does not touch a buffer."""
        self._host.post(lambda: self._runtime.request_frame())

    def _bindings_changed(self, placement: Placement[StateT]) -> None:
        """A formula or range was set: look at the placement before each frame."""
        with self._lock:
            self._dynamic[id(placement)] = placement
        self._host.post(lambda: self._runtime.request_frame())

    def _stop_runtime(self) -> None:
        self._runtime.stop()

    # -- lifecycle ----------------------------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exception_type: object, *rest: object) -> None:
        self.close(raise_failure=exception_type is None)

    @property
    def is_closed(self) -> bool:
        """Whether the terminal has been closed, or its loop has ended."""
        return self._is_closed

    @property
    def is_live(self) -> bool:
        """Whether the terminal draws on your screen."""
        return self._is_live

    @property
    def is_autonomous(self) -> bool:
        """Whether the terminal runs by itself on a thread of its own."""
        return self._host.is_autonomous

    @property
    def backend(self) -> TerminalBackend:
        """``'terminal'`` for a live terminal, ``'offscreen'`` for one in memory."""
        return 'terminal' if self._is_live else 'offscreen'

    def _require_open(self) -> None:
        if self._is_closed:
            if self._failure is not None:
                raise TerminalClosedError(
                    f'{self._failure_text(self._failure)} Fix that, then open a new terminal '
                    f'with xnano.open().'
                ) from self._failure
            raise TerminalClosedError(
                'This terminal has been closed, so it can no longer draw or listen. Open a '
                'new one with xnano.open(), and do the work inside its "with" block.'
            )

    def close(self, *, raise_failure: bool = True) -> None:
        """
        Give the screen back and release everything the terminal holds.

        Closing twice is harmless. Leaving a ``with`` block closes the terminal.

        Args:
            raise_failure: Whether to raise the error a callback raised on the loop, which
                stopped the terminal. A ``with`` block passes ``False`` while another
                error is already propagating.

        Raises:
            TerminalError: A callback raised on the terminal's loop, or the loop would not
                stop.
        """
        if not self._stop_requested.is_set() or not self._is_finalized:
            self._stop_requested.set()
            try:
                self._host.shutdown()
            finally:
                self._finalize()
        if _active_terminal.get() is self:
            _active_terminal.set(self._previous)
        failure = self._failure
        if failure is not None and raise_failure:
            self._failure = None
            raise TerminalError(self._failure_text(failure)) from failure

    def _record_failure(self, error: BaseException) -> None:
        """Keep an error raised on the loop, as text plus the error without its frames."""
        self._failure_report = release_frames(error)
        self._failure = error

    def _failure_text(self, failure: BaseException) -> str:
        text = (
            f'The terminal stopped because {type(failure).__name__} was raised on its '
            f'loop: {failure}.'
        )
        report = self._failure_report
        return f'{text}\n\n{report}' if report else text

    # -- geometry -----------------------------------------------------------------------

    @property
    def root(self) -> _core.Buffer:
        """
        The buffer the terminal draws, as large as the terminal.

        Everything you add is a child of this buffer, and everything you write or draw
        directly is stored in it.
        """
        return self._root

    @property
    def size(self) -> _core.Size:
        """The size of the terminal in cells."""
        if not self._host.is_autonomous:
            return self._runtime.device.size
        return self._size

    @property
    def title(self) -> str | None:
        """
        Window title last set on this terminal.

        Assign a single line of printable text to set the live terminal's title.
        Assign ``None`` to clear it. Offscreen terminals store the value without
        writing to the display.
        """
        self._require_open()
        return self._host.call(lambda: self._runtime.title)

    @title.setter
    def title(self, value: str | None) -> None:
        self._require_open()
        self._host.call(lambda: setattr(self._runtime, 'title', value))

    @property
    def cursor(self) -> _core.Cursor:
        """
        The terminal's cursor.

        A terminal has exactly one cursor. Set ``position`` (a cell, or ``None`` to hide
        it), ``shape``, ``is_blinking`` and ``is_visible``, or call ``follow`` to keep it at
        a place inside a buffer. It can be changed from any thread, and the cursor you had
        before the terminal opened is restored when it closes.

        Examples:
            Put a bar cursor at column 3 of the first row::

                terminal.cursor.position = (3, 0)
                terminal.cursor.shape = 'bar'
        """
        self._require_open()
        if self._cursor is None:
            return self._runtime.cursor
        return self._cursor

    @property
    def width(self) -> int:
        """The width of the terminal in cells."""
        return self.size.width

    @property
    def height(self) -> int:
        """The height of the terminal in cells."""
        return self.size.height

    def pixels(self, *, encoding: PixelEncoding = 'half_blocks') -> Pixels:
        """
        Return a view of the terminal's pixels.

        Args:
            encoding: ``'half_blocks'`` for one column and two rows of pixels per cell, or
                ``'braille'`` for two columns and four rows with one color per cell.
        """
        self._require_open()
        return Pixels(self._root.pixels(encoding=encoding))

    # -- content ------------------------------------------------------------------------

    def add(
        self,
        content: Content,
        *,
        x: Axis | None = None,
        y: Axis | None = None,
        width: Axis | None = None,
        height: Axis | None = None,
        layer: int = 0,
        style: _core.Style | None = None,
        title: str | None = None,
        border: _core.BorderKind | None = None,
    ) -> Placement[StateT]:
        """
        Put something on the terminal.

        On a live terminal it appears at once: this only declares it, and the terminal's
        own loop draws it. Anything you leave out is taken from the content: ``x`` and
        ``y`` default to the top-left corner, and ``width`` and ``height`` to the size of
        the content, so ``terminal.add('hello')`` shows five cells of text where it is.

        An image is converted to cells at the size you give it. With neither ``width``
        nor ``height`` it keeps its own proportions at its own size, shrunk to fit the
        terminal. With one of them the other follows the image's proportions, and with
        both the image fits inside that box. An image sized by a percentage, or by the
        terminal because you gave no size, is converted again when the terminal is resized.
        An animated image plays on the terminal's clock.

        Args:
            content: A [`Buffer`][xnano_core.Buffer] or widget, a string, the
                bytes of a cell grid, a [`TerminalImage`][xnano_image.TerminalImage] or the
                path of an image file, or any [`Renderable`][xnano.types.Renderable].
            x: The column of the left edge: a number of cells, a percentage string, an
                expression, or a range (``(0, 20)``) that limits how far it may
                travel. See [`Axis`][xnano.types.Axis].
            y: The row of the top edge, in the same forms.
            width: The width, in the same forms; the content's own width when ``None``.
            height: The height, in the same forms; the content's own height when ``None``.
            layer: Content with a higher layer is drawn over content with a lower one.
            style: The colors and modifiers of text, such as ``Style('red', bold=True)``.
            title: A title for a box around text.
            border: The kind of border for a box around text: ``'plain'``, ``'rounded'``,
                ``'double'`` or ``'thick'``. Giving a ``title`` alone draws a plain one.

        Returns:
            A [`Placement`][xnano.Placement] to move, resize, listen on or remove.

        Raises:
            TypeError: ``style``, ``title`` or ``border`` was given for content that is not
                text.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=20, height=4) as terminal:
                box = terminal.add('hello', x='50%', y=1)
                assert box.x == 10
                assert (box.width, box.height) == (5, 1)
                terminal.add('Ready', x='center', y='bottom', border='rounded', title='Status')
            ```
        """
        self._require_open()
        content = _text_content(content, style=style, title=title, border=border)
        buffer, source = self._buffer_for(content, width, height)
        buffer.layer = layer
        placement: Placement[StateT] = Placement(self, buffer)
        with self._lock:
            self._placements.append(placement)
            if source is not None:
                self._images[id(buffer)] = source
        self._root.attach(buffer, mode='transparent')
        composed = content.axes() if isinstance(content, Composition) else {}
        for axis, value in composed.items():
            placement._set_axis(axis, value)
        requested: list[tuple[AxisName, Axis | None]] = [
            ('x', x),
            ('y', y),
            ('width', width),
            ('height', height),
        ]
        for axis, value in requested:
            if value is not None:
                placement._set_axis(axis, value)
            elif axis in ('x', 'y') and axis not in composed:
                placement._set_axis(axis, 0)
        if isinstance(content, Composition):
            content.apply_mounted()
        if source is not None and source.animation is not None:
            self._request_frame()
        return placement

    def _buffer_for(
        self, content: Content, width: Axis | None, height: Axis | None
    ) -> tuple[_core.Buffer, ImageSource | None]:
        """Build the buffer that shows ``content``, and the image source that keeps it."""
        if isinstance(content, os.PathLike) or is_image(content):
            source = ImageSource.create(
                cast('TerminalImage | os.PathLike[str]', content),
                width=width,
                height=height,
                size=self.size,
                elapsed_seconds=self.clock.elapsed_seconds,
            )
            return source.buffer, source
        buffer, _ = content_buffer(content)
        return buffer, None

    def _release(self, placement: Placement[StateT]) -> None:
        with self._lock:
            if placement in self._placements:
                self._placements.remove(placement)
            self._dynamic.pop(id(placement), None)
            self._images.pop(id(placement.buffer), None)
        try:
            self._root.detach(placement.buffer)
        except ValueError:
            pass

    def write(
        self,
        text: str,
        *,
        x: int = 0,
        y: int = 0,
        style: _core.Style | None = None,
    ) -> None:
        """
        Write text into the terminal's cells, clipped at the edges.

        Args:
            text: The text to write.
            x: The column of the first character.
            y: The row of the text.
            style: The style of the text, or ``None`` for the cells' own.
        """
        self._require_open()
        self._root.update(_core.Write(text, x=x, y=y, style=style))

    def clear(self) -> None:
        """Erase everything written or drawn directly on the terminal's cells."""
        self._require_open()
        self._root.update(_core.Fill(' '))

    def update(self, *operations: _core.Operation) -> None:
        """Apply operations (``Write``, ``Fill``, ``Border`` and the rest) to the terminal."""
        self._require_open()
        self._root.update(*operations)

    def inspect(self, expression: _core.Expression[ValueT]) -> ValueT:
        """
        Evaluate an expression against the terminal and return its value.

        Args:
            expression: Any expression, such as ``Width``, ``TimeElapsed % 1`` or
                ``terminal.audio.level``.

        Examples:
            ```python
            import xnano
            from xnano_core import Width

            with xnano.open(offscreen=True, width=12, height=2) as terminal:
                assert terminal.inspect(Width) == 12
            ```
        """
        self._require_open()
        return self._host.call(lambda: self._root.inspect(expression))

    @overload
    def __getitem__(self, key: tuple[int, int]) -> _core.Cell: ...
    @overload
    def __getitem__(self, key: tuple[slice, slice]) -> _core.Region: ...
    def __getitem__(
        self, key: tuple[int, int] | tuple[slice, slice]
    ) -> _core.Cell | _core.Region:
        """
        Return the cell at ``terminal[column, row]``, or the region at ``terminal[columns, rows]``.

        Args:
            key: A ``(column, row)`` pair of integers, or a pair of slices.
        """
        self._require_open()
        return self._root[key]

    def __setitem__(
        self,
        key: tuple[slice | int, slice | int],
        value: str | ColorValue | Content,
    ) -> None:
        """
        Fill part of the terminal.

        * A string is written into the region, clipped at its edges.
        * A [`Color`][xnano_core.Color] or an ``(red, green, blue)`` tuple fills
          the region's background. (A string is always text; make a color from a hex string
          with ``Color('#336699')``.)
        * A buffer or other content is placed so that it covers the region.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=10, height=3) as terminal:
                terminal[0:5, 0:2] = (51, 102, 153)
                terminal[2:9, 1:2] = 'hello'
            ```
        """
        self._require_open()
        columns, rows = key
        if isinstance(columns, int) and isinstance(rows, int):
            if isinstance(value, str):
                self._root[columns, rows] = value
                return
            raise TypeError(
                'A single cell takes a string or a Cell. To fill or place something over '
                'an area, index with two slices, such as terminal[0:5, 0:2].'
            )
        size = self.size
        left, right, column_step = (
            columns.indices(size.width)
            if isinstance(columns, slice)
            else (columns, columns + 1, 1)
        )
        top, bottom, row_step = (
            rows.indices(size.height) if isinstance(rows, slice) else (rows, rows + 1, 1)
        )
        if column_step != 1 or row_step != 1:
            raise ValueError(
                'A region of the terminal is a rectangle of cells, so its slices cannot '
                'have a step. Write terminal[0:5, 0:2] instead of terminal[0:5:2, 0:2].'
            )
        if right <= left or bottom <= top:
            return
        region = self._root[left:right, top:bottom]
        if _is_color(value):
            region.update(_core.Background(value))
        elif isinstance(value, str):
            region.update(_core.Write(value))
        else:
            self.add(value, x=left, y=top, width=right - left, height=bottom - top)

    # -- time ---------------------------------------------------------------------------

    @property
    def is_paused(self) -> bool:
        """Whether time is stopped: see [`pause`][xnano.Terminal.pause]."""
        return self.clock.is_paused

    def pause(self) -> None:
        """
        Stop time on this terminal.

        Everything that follows the terminal's clock stands still: expressions such as
        ``TimeElapsed``, animations and effects, [`every`][xnano.Terminal.every] and
        [`after`][xnano.Terminal.after] timers, fixed-step updates, and the musical clock of
        [`audio`][xnano.Terminal.audio] when it is running. Input still arrives, so a key
        can [`resume`][xnano.Terminal.resume] it.
        """
        self._require_open()
        self.clock.pause()
        audio = self._audio
        if audio is not None:
            self._host.post(audio._hold)

    def resume(self) -> None:
        """Let time run on from where [`pause`][xnano.Terminal.pause] stopped it."""
        self._require_open()
        self.clock.resume()
        audio = self._audio
        if audio is not None:
            self._host.post(audio._release)

    @property
    def clock(self) -> _core.Clock:
        """The clock everything on the terminal runs on; any thread may read it."""
        assert self._clock is not None
        return self._clock

    @property
    def is_running(self) -> bool:
        """Whether the terminal's loop is running and has not been stopped."""
        return not self._is_closed and not self._stop_requested.is_set()

    def stop(self) -> None:
        """
        Ask the loop to stop.

        Safe from any thread, including from a callback. A live terminal can then be
        left with [`run`][xnano.Terminal.run] returning, or closed.
        """
        self._stop_requested.set()
        if not self._is_closed:
            self._host.post(lambda: self._stop_runtime())

    def run(self, *, quit_on: str | Sequence[str] | None = 'ctrl+c') -> None:
        """
        Wait until the terminal stops.

        A live terminal draws and listens by itself, so this only keeps your program alive
        until a quit key is pressed, or something calls [`stop`][xnano.Terminal.stop] (a
        key callback, another thread). Declare what you want before calling it.

        Args:
            quit_on: The key, or keys, that stop the terminal, such as ``'q'`` or
                ``('q', 'escape')``. ``'ctrl+c'`` by default; give ``None`` to leave stopping
                to your own code.

        Raises:
            TerminalError: A callback raised on the terminal's loop, or the terminal has a
                clock that only moves when you move it, so waiting would never end.
        """
        self._require_open()
        host = self._host
        if not isinstance(host, _ThreadHost):
            raise TerminalError(
                'An offscreen terminal with a manual clock never moves by itself, so run() '
                'would wait forever. Drive it with terminal.frames() or terminal.advance(), '
                'or open it with clock="real" to let it run on its own.'
            )
        if quit_on is not None:
            keys = (quit_on,) if isinstance(quit_on, str) else tuple(quit_on)

            @self.on_key(*keys)
            def quit_key(context: Context[StateT]) -> None:
                context.terminal.stop()

        try:
            while not host.wait(0.1):
                pass
        except KeyboardInterrupt:
            self.stop()
            raise
        failure = self._failure
        if failure is not None:
            self._failure = None
            raise TerminalError(self._failure_text(failure)) from failure

    def wait_for_key(self, *keys: str) -> str:
        """
        Wait until a key is pressed, and return its name.

        Your program waits here while the terminal goes on drawing and animating. It reads
        like ``input()``: nothing else runs on your thread until the key arrives.

        Args:
            keys: The keys to wait for, such as ``'enter'`` or ``'q'``. Give none to take any key.

        Returns:
            The name of the key that was pressed.

        Raises:
            TerminalError: The terminal stopped, or has a manual clock, so no key could arrive.

        Examples:
            In a program: ``terminal.wait_for_key()`` after adding "Press any key to start".
            Here a timer plays the part of the person pressing the key:

            ```python
            import xnano
            from xnano.events import Event

            with xnano.open(offscreen=True, clock='real', width=30, height=2) as terminal:
                terminal.add('Press enter to start')

                @terminal.after(0.05)
                def press(context: xnano.Context) -> None:
                    terminal.inject(Event.key_press('enter'))

                assert terminal.wait_for_key('enter') == 'enter'
            ```
        """
        pressed: list[str] = []
        done = threading.Event()

        @self.on_key(*keys)
        def hear(context: Context[StateT]) -> None:
            if context.keyboard is not None:
                pressed.append(context.keyboard.key)
            context.hook.remove()
            done.set()

        self._wait_until(done, 'a key')
        return pressed[0]

    def prompt(self, text: str, *, x: int = 0, y: int = 0, default: str = '') -> str:
        """
        Prompt for a line of text, and return what was typed.

        The prompt and the answer appear on the terminal while your program waits, like
        ``input()``. ``Enter`` submits and ``Backspace`` deletes.

        Args:
            text: What to ask, such as ``'Your name: '``.
            x: The column of the prompt.
            y: The row of the prompt.
            default: Text already in the answer, which the user can edit.

        Returns:
            What was typed, without the prompt.

        Raises:
            TerminalError: The terminal stopped, or has a manual clock, so no answer could arrive.

        Examples:
            In a program: ``name = terminal.prompt('Your name: ')``. Here a timer plays the part
            of the person typing:

            ```python
            import xnano
            from xnano.events import Event

            with xnano.open(offscreen=True, clock='real', width=30, height=2) as terminal:

                @terminal.after(0.05)
                def type_answer(context: xnano.Context) -> None:
                    for letter in 'Ada':
                        terminal.inject(Event.key_press(letter))
                    terminal.inject(Event.key_press('enter'))

                assert terminal.prompt('Your name: ') == 'Ada'
            ```
        """
        answer = [default]
        done = threading.Event()

        def show() -> None:
            line = text + answer[0]
            self.write(line + ' ', x=x, y=y)
            self.cursor.position = (x + len(line), y)

        self.cursor.shape = 'bar'
        self.cursor.is_blinking = True
        self.cursor.is_visible = True
        show()

        @self.on_key()
        def edit(context: Context[StateT]) -> None:
            key = context.keyboard
            if key is None:
                return
            if key.key == 'enter':
                done.set()
                return
            if key.key == 'backspace':
                answer[0] = answer[0][:-1]
            elif key.text is not None and not key.modifiers - {'shift'}:
                answer[0] += key.text
            show()

        try:
            self._wait_until(done, 'an answer')
        finally:
            edit.remove()
            self.cursor.is_visible = False
            self.write(' ' * (len(text) + len(answer[0]) + 1), x=x, y=y)
        return answer[0]

    def _wait_until(self, done: threading.Event, what: str) -> None:
        """Block the calling thread until ``done`` is set, or say why that cannot happen."""
        self._require_open()
        if not isinstance(self._host, _ThreadHost):
            raise TerminalError(
                f'This terminal never moves by itself, so waiting for {what} would last '
                f'forever. Open it live, or with clock="real", or drive it with '
                f'terminal.loop.step() and read the result from a hook instead.'
            )
        while not done.wait(0.1):
            if not self.is_running:
                raise TerminalError(
                    f'The terminal stopped while waiting for {what}. Wait before calling '
                    f'terminal.stop() or closing the terminal.'
                )

    @property
    def audio(self) -> Audio:
        """
        The terminal's [`Audio`][xnano.audio.Audio]: notes, melodies, sounds and the microphone.

        It needs the optional `xnano-audio` package, which is imported the first time this
        is read.

        Raises:
            ImportError: `xnano-audio` is not installed. Install it with
                ``pip install "xnano[audio]"``.
        """
        self._require_open()
        if self._audio is None:
            require('audio', needed_for='Terminal.audio')
            from xnano.audio import Audio

            with self._lock:
                if self._audio is None:
                    audio = Audio(cast('Terminal[object]', self))
                    self._audio = audio
                    self._host.post(lambda: audio._provide(self._runtime))
        return self._audio

    def scene(
        self,
        world_width: int,
        world_height: int,
        *,
        background: ColorValue = (0, 0, 0),
    ) -> Scene:
        """
        Make a pixel world drawn on this terminal, seen through a camera.

        Put sprites in it with [`Scene.add`][xnano.scene.Scene.add]; the scene redraws only when
        something changed. See [`Scene`][xnano.scene.Scene].

        Args:
            world_width: The width of the world in pixels.
            world_height: The height of the world in pixels.
            background: The color shown where no sprite is drawn.
        """
        return Scene(
            cast('Terminal[object]', self), world_width, world_height, background
        )

    @property
    def input(self) -> Input:
        """
        The keys held down right now, for programs that poll instead of listening.

        Read it inside a hook or a [`loop.on_update`][xnano.Loop.on_update] function. A
        terminal opened with ``keyboard='release_events'`` knows exactly when a key is let go.
        """
        self._require_open()
        if self._input is None:
            self._input = Input(cast('Terminal[object]', self))
        return self._input

    @property
    def tempo(self) -> float:
        """
        The tempo in beats per minute, which the length of notes, melodies and
        [`every(beats=...)`][xnano.Terminal.every] timers follow.

        It is 120 until you change it, and it can change while things are playing.

        Raises:
            ImportError: `xnano-audio` is not installed.
        """
        return self.audio.tempo

    @tempo.setter
    def tempo(self, beats_per_minute: float) -> None:
        self.audio.tempo = beats_per_minute

    def play(
        self,
        source: Playable,
        *,
        instrument: InstrumentName = 'piano',
        duration_milliseconds: int = 500,
        velocity: float = 0.8,
        effects: list[TerminalAudioEffect] | None = None,
        volume: float = 1.0,
        pan: float = 0.0,
        at_beat: int | None = None,
    ) -> None:
        """
        Play a sound, a note, a melody or melody text, and return at once.

        This is [`audio.play`][xnano.audio.Audio.play]; see it for every argument.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=8, height=1) as terminal:
                if terminal.audio.is_available:
                    terminal.tempo = 100
                    terminal.play('C4 E4 G4:2 rest C5+E5+G5', instrument='bell')
            ```
        """
        self.audio.play(
            source,
            instrument=instrument,
            duration_milliseconds=duration_milliseconds,
            velocity=velocity,
            effects=effects,
            volume=volume,
            pan=pan,
            at_beat=at_beat,
        )

    def note(
        self,
        pitch: Pitch,
        beats: float = 1.0,
        *,
        instrument: InstrumentName = 'piano',
        velocity: float = 0.8,
        effects: list[TerminalAudioEffect] | None = None,
        volume: float = 1.0,
        pan: float = 0.0,
        at_beat: int | None = None,
    ) -> None:
        """
        Play one note held for a number of beats, and return at once.

        The length follows the terminal's [`tempo`][xnano.Terminal.tempo]. This is
        [`audio.note`][xnano.audio.Audio.note]; see it for every argument.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=8, height=1) as terminal:
                if terminal.audio.is_available:

                    @terminal.every(beats=1)
                    def metronome(context: xnano.Context) -> None:
                        terminal.note('C5', beats=0.25, instrument='bell')
            ```
        """
        self.audio.note(
            pitch,
            beats,
            instrument=instrument,
            velocity=velocity,
            effects=effects,
            volume=volume,
            pan=pan,
            at_beat=at_beat,
        )

    @property
    def state(self) -> StateT:
        """
        The terminal's state: the dataclass passed to ``open(state=...)``.

        Reading and writing its fields goes through the terminal's state store, so a write
        is validated against the field's type, updates every expression that reads it,
        and draws a frame. It can be used from any thread.

        Raises:
            TerminalError: The terminal was opened without ``state``.
        """
        proxy = self._state_proxy
        if proxy is None:
            raise TerminalError(
                'This terminal has no state. Open it with open(state=YourDataclass()) to '
                'give hooks something to read and write.'
            )
        return cast('StateT', proxy)

    def inject(self, event: _core.Event) -> None:
        """
        Deliver an event to the terminal as if it had been typed, clicked or reported.

        Hooks hear it the same way as input from the keyboard and mouse. Build events
        with [`Event`][xnano_core.Event]; ``Event.custom(name, data=...)``
        makes one of your own.

        Args:
            event: The event to deliver.

        Examples:
            ```python
            import xnano
            from xnano_core import Event

            with xnano.open(offscreen=True, width=8, height=1) as terminal:
                heard = []
                terminal.hook(
                    lambda context: heard.append(context.event.custom_name),
                    when=lambda context: context.event.kind == 'custom',
                )
                terminal.inject(Event.custom('volume_changed'))
                terminal.loop.advance(0.1)
            assert heard == ['volume_changed']
            ```
        """
        self._require_open()
        self._host.post(lambda: self._runtime.inject(event))

    def ref(self, reader: Callable[[StateT], ValueT]) -> _core.StateReference[ValueT]:
        """
        A core reference for one field of the terminal's state.

        The reference can be used as an axis, a range bound or a widget parameter.

        Args:
            reader: A function or lambda that reads the field, such as
                ``lambda state: state.volume``.

        Raises:
            TerminalError: The terminal was opened without ``state``.
        """
        if self._state_store is None:
            raise TerminalError(
                'This terminal has no state, so ref() has nothing to read. Open it with '
                'open(state=YourDataclass()).'
            )
        reference = reference_for(self._state_store, reader)
        return reference

    def __str__(self) -> str:
        if self._is_closed:
            return ''
        try:
            return self.output.snapshot().ansi
        except TerminalError:
            return ''

    def __repr__(self) -> str:
        if self._is_closed:
            return f'Terminal(backend={self.backend!r}, closed)'
        size = self._size if self._host.is_autonomous else self.size
        return (
            f'Terminal(backend={self.backend!r}, width={size.width}, height={size.height}, '
            f'fps={self._fps})'
        )


# --------------------------------------------------------------------------------------
# Opening
# --------------------------------------------------------------------------------------


@overload
def open(
    *,
    offscreen: bool = False,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    clock: Literal['real', 'manual'] | None = None,
    inline_height: int | None = None,
    should_clear_on_close: bool | None = None,
    mouse: Literal['off', 'buttons', 'motion'] = 'off',
    interrupt: Literal['event', 'stop'] = 'stop',
    keyboard: Literal['basic', 'disambiguated', 'release_events'] = 'basic',
    should_capture_output: bool = True,
    should_use_alternate_screen: bool = True,
    state: None = None,
) -> Terminal[None]: ...
@overload
def open(
    *,
    offscreen: bool = False,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    clock: Literal['real', 'manual'] | None = None,
    inline_height: int | None = None,
    should_clear_on_close: bool | None = None,
    mouse: Literal['off', 'buttons', 'motion'] = 'off',
    interrupt: Literal['event', 'stop'] = 'stop',
    keyboard: Literal['basic', 'disambiguated', 'release_events'] = 'basic',
    should_capture_output: bool = True,
    should_use_alternate_screen: bool = True,
    state: StateT,
) -> Terminal[StateT]: ...
def open(
    *,
    offscreen: bool = False,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    clock: Literal['real', 'manual'] | None = None,
    inline_height: int | None = None,
    should_clear_on_close: bool | None = None,
    mouse: Literal['off', 'buttons', 'motion'] = 'off',
    interrupt: Literal['event', 'stop'] = 'stop',
    keyboard: Literal['basic', 'disambiguated', 'release_events'] = 'basic',
    should_capture_output: bool = True,
    should_use_alternate_screen: bool = True,
    state: StateT | None = None,
) -> Terminal[StateT] | Terminal[None]:
    """
    Open a terminal.

    By default this takes over your screen and starts drawing: from here on, anything you
    add, remove or draw appears at once, on a loop of the terminal's own that your code
    never waits for. A ``with`` block closes it and gives the screen back.

    Give ``height`` (and optionally ``width``) to draw in a region of that size below the
    cursor instead of taking over the whole screen. That region is transient: it is
    erased when the terminal closes, like any other live application.

    With ``offscreen=True`` it draws into memory instead, on a clock that only moves when
    you move it (``clock='manual'``, the default), or that runs by itself
    (``clock='real'``).

    Args:
        offscreen: Draw into memory instead of onto the screen.
        width: The width in cells. Offscreen: 80 by default. Live: the width of the
            region to draw in; the whole window when ``None``.
        height: The height in cells. Offscreen: 24 by default. Live: the height of the
            region to draw in; the whole window when ``None``.
        fps: The rate frames are drawn at, at most.
        clock: ``'real'`` for a terminal that runs by itself, ``'manual'`` for one that
            moves only when you call ``frames``, ``advance`` or ``step``. Live terminals
            always run on a real clock; the default offscreen clock is ``'manual'``.
        inline_height: Draw this many rows below the cursor and leave them on the screen
            when the terminal closes. Live terminals only; ``height`` is the transient
            equivalent.
        should_clear_on_close: Whether a live region is erased when the terminal closes.
            ``True`` by default when ``height`` is given, ``False`` otherwise.
        title: Window title; ``None`` leaves the existing title untouched.
        keyboard: ``'basic'`` for ordinary key presses, ``'disambiguated'`` to tell keys such
            as ``escape`` and ``alt+key`` apart, and ``'release_events'`` to also receive key
            repeats and releases (``context.keyboard.kind``). The last two need a terminal with the
            enhanced keyboard protocol, such as kitty, and fall back to ``'basic'`` elsewhere.
        mouse: ``'buttons'`` to receive clicks and drags, ``'motion'`` to receive all
            movement. Live terminals only.
        interrupt: What ``Ctrl-C`` does on a live terminal: ``'stop'`` ends the loop,
            ``'event'`` delivers it as a key press for you to handle.
        should_capture_output: Whether text printed during a live session is held back from
            the screen and printed when the terminal closes. This works on macOS and Linux;
            elsewhere a ``RuntimeWarning`` says it could not be done.
        should_use_alternate_screen: Whether a full-window live terminal draws on the
            alternate screen, so your shell's history comes back untouched.
        state: A dataclass instance the terminal keeps and validates. Hooks read and write
            it as ``context.state``.

    Returns:
        The open [`Terminal`][xnano.Terminal], which is also the one module-level
        functions such as [`active`][xnano.active] find.

    Raises:
        TerminalAlreadyOpenError: A live terminal is already open.
        ValueError: An argument does not apply to the kind of terminal, or is out of range.
        RuntimeError: A live terminal was requested but there is no terminal to draw on.

    Examples:
        ```python
        import xnano

        with xnano.open(offscreen=True, width=16, height=3) as terminal:
            assert terminal.size.width == 16
            assert xnano.active() is terminal
        ```
    """
    global _live_terminal_open
    if fps <= 0:
        raise ValueError(
            f'fps must be above zero, but was {fps}. Use 30 or 60 for smooth motion.'
        )
    interval_milliseconds = max(1, int(round(1000.0 / fps)))
    if offscreen:
        if (
            inline_height is not None
            or mouse != 'off'
            or keyboard != 'basic'
            or should_clear_on_close is not None
        ):
            raise ValueError(
                'inline_height, mouse, keyboard and should_clear_on_close only apply to a live '
                'terminal, but offscreen=True was given. Remove them, or remove '
                'offscreen=True.'
            )
        kind = 'manual' if clock is None else clock
        columns = 80 if width is None else width
        rows = 24 if height is None else height

        def create_offscreen() -> _core.Runtime:
            runtime = _core.Runtime.offscreen(
                width=columns,
                height=rows,
                frame_interval_milliseconds=interval_milliseconds,
                clock=_core.Clock.monotonic() if kind == 'real' else None,
            )
            if title is not None:
                runtime.title = title
            return runtime

        return Terminal(
            create_offscreen,
            fps=fps,
            is_live=False,
            is_autonomous=kind == 'real',
            state=cast('StateT', state),
        )

    if clock == 'manual':
        raise ValueError(
            'A live terminal runs on real time, so clock="manual" does not apply. Use '
            'offscreen=True for a clock you move yourself.'
        )
    if width is not None and height is None:
        raise ValueError(
            'A live terminal with a width needs a height too, because it draws in a region '
            'of that size. Add height=..., or remove width.'
        )
    if height is not None and inline_height is not None:
        raise ValueError(
            'height and inline_height both set the number of rows to draw in. Keep height '
            'for a region that is erased when the terminal closes, or inline_height for one '
            'that stays.'
        )
    region_height = height if height is not None else inline_height
    region_width = width
    clears = (
        should_clear_on_close if should_clear_on_close is not None else height is not None
    )
    with _live_terminal_lock:
        if _live_terminal_open:
            raise TerminalAlreadyOpenError(
                'A live terminal is already open, and a program has only one screen. Close '
                'it first, or draw into xnano.open(offscreen=True) and show that instead.'
            )
        _live_terminal_open = True

    def create_live() -> _core.Runtime:
        options = _core.TerminalOptions(
            input=_core.InputOptions(mouse=mouse, interrupt=interrupt, keyboard=keyboard),
            alternate_screen=should_use_alternate_screen and region_height is None,
            should_capture_output=should_capture_output,
            should_clear_on_close=clears,
        )
        runtime = _core.Runtime.live(
            frame_interval_milliseconds=interval_milliseconds,
            inline_height=region_height,
            inline_width=region_width,
            options=options,
        )
        if title is not None:
            runtime.title = title
        return runtime

    try:
        return Terminal(
            create_live,
            fps=fps,
            is_live=True,
            is_autonomous=True,
            state=cast('StateT', state),
            should_capture_output=should_capture_output,
        )
    except BaseException:
        with _live_terminal_lock:
            _live_terminal_open = False
        raise


@overload
def active() -> Terminal: ...
@overload
def active(*, required: Literal[False]) -> Terminal | None: ...
def active(*, required: bool = True) -> Terminal | None:
    """
    Return the terminal opened most recently in this thread or task.

    Callbacks run on a terminal's loop see that terminal.

    Args:
        required: Whether to raise when no terminal is open.

    Raises:
        TerminalClosedError: No terminal is open and ``required`` is true.
    """
    terminal = _active_terminal.get()
    if terminal is None and required:
        raise TerminalClosedError(
            'No terminal is open. Open one with "with xnano.open() as terminal:" and call '
            'this inside the block.'
        )
    return terminal


def find_active() -> Terminal | None:
    """Return the active terminal, or ``None`` when no terminal is open."""
    return active(required=False)
