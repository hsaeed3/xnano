"""
xnano.output

What a canvas has drawn, and the text a canvas on the screen held back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import xnano_core as _core

if TYPE_CHECKING:
    from xnano.canvas import Canvas

__all__ = ['Output']


class Output:
    r"""
    The last frame a canvas drew, and the text printed while it was on the screen.

    Get it from ``canvas.output``. ``text``, ``ansi``, ``size``, ``revision``,
    ``cursor_position``, ``is_cursor_visible``, ``lines()`` and ``to_cell_grid()`` read the
    last frame that was drawn without drawing a new one. To see a change, draw a frame first
    with ``canvas.step()``, ``canvas.output.render()`` or
    [`Canvas.render`][xnano.canvas.Canvas.render].

    Each of these shorthands reads its own snapshot of the last drawn frame at the moment
    it is called. Code that needs several values from one frame should call
    [`snapshot`][xnano.output.Output.snapshot] once and read them from the returned frame.

    Every member raises [`TerminalClosedError`][xnano.errors.TerminalClosedError] once the
    canvas is closed.

    Attributes:
        is_captured: Whether a canvas on the screen is holding back what is printed, so it
            cannot corrupt the screen.
        text: The last drawn frame's plain text rows joined by newlines.
        ansi: The last drawn frame as text with styling escape sequences.
        size: The size of the last drawn frame in cells.
        revision: A number that increases with every drawn frame; ``0`` before the first
            one.
        cursor_position: Where the cursor is in the last drawn frame, or ``None`` when no
            cursor is placed.
        is_cursor_visible: Whether the cursor is shown in the last drawn frame.

    Examples:
        ```python
        import xnano

        with xnano.new(width=12, height=2) as canvas:
            canvas.write('hello', x=1, y=1)
            assert canvas.output.revision == 0
            canvas.step()
            assert canvas.output.text == '\n hello'
            assert canvas.output.lines() == ['', ' hello']
            assert canvas.output.size.width == 12
            assert canvas.output.revision == 1
        ```
    """

    def __init__(self, canvas: Canvas[object, object]) -> None:
        """
        Create the output's view of a canvas. Use ``canvas.output`` instead of calling this.

        Args:
            canvas: The canvas whose frames and held-back text this reads.
        """
        self._canvas = canvas

    @property
    def is_captured(self) -> bool:
        """Whether a canvas on the screen is holding back what is printed, so it cannot corrupt the screen."""
        canvas = self._canvas
        canvas._require_open()
        return canvas._host.call(lambda: canvas._runtime.is_output_captured)

    @property
    def text(self) -> str:
        """The last drawn frame's plain text rows joined by newlines."""
        return self.snapshot().text

    @property
    def ansi(self) -> str:
        """The last drawn frame as text with styling escape sequences."""
        return self.snapshot().ansi

    @property
    def size(self) -> _core.Size:
        """The size of the last drawn frame in cells."""
        return self.snapshot().size

    @property
    def revision(self) -> int:
        """A number that increases with every drawn frame; ``0`` before the first one."""
        return self.snapshot().revision

    @property
    def cursor_position(self) -> _core.Point | None:
        """Where the cursor is in the last drawn frame, or ``None`` when no cursor is placed."""
        return self.snapshot().cursor_position

    @property
    def is_cursor_visible(self) -> bool:
        """Whether the cursor is shown in the last drawn frame."""
        return self.snapshot().is_cursor_visible

    def render(self) -> _core.FrameSnapshot:
        """
        Draw a frame now and return it.

        Raises:
            TerminalClosedError: The canvas is closed.
        """
        canvas = self._canvas
        canvas._require_open()
        return canvas._host.call(lambda: canvas._runtime.render())

    def snapshot(self) -> _core.FrameSnapshot:
        """
        Return the last frame that was drawn, without drawing.

        Raises:
            TerminalClosedError: The canvas is closed.
        """
        canvas = self._canvas
        canvas._require_open()
        return canvas._host.call(lambda: canvas._runtime.snapshot())

    def lines(self) -> list[str]:
        """
        Return the plain text rows of the last drawn frame, without drawing.

        Raises:
            TerminalClosedError: The canvas is closed.
        """
        return self.snapshot().lines()

    def to_cell_grid(self) -> bytes:
        """
        Pack the last drawn frame into the cell grid byte format, without drawing.

        Raises:
            TerminalClosedError: The canvas is closed.
        """
        return self.snapshot().to_cell_grid()

    def take_captured(self) -> str:
        """
        Return the text printed or logged since the last call, from a canvas on the screen.

        A canvas on the screen holds back anything written to standard output or standard
        error so it cannot corrupt the screen. Text you do not take is printed when the
        canvas closes.
        """
        canvas = self._canvas
        canvas._require_open()
        return canvas._host.call(lambda: canvas._runtime.take_captured_output())
