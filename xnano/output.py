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
    """
    The frames a canvas has drawn, and the text printed while it was on the screen.

    Get it from ``canvas.output``. To print the current frame, use
    [`Canvas.render`][xnano.canvas.Canvas.render].

    Attributes:
        is_captured: Whether a canvas on the screen is holding back what is printed, so it
            cannot corrupt the screen.

    Examples:
        ```python
        import xnano

        with xnano.new(width=12, height=2) as canvas:
            canvas.write('hello', x=1, y=1)
            canvas.output.render()
            assert canvas.output.snapshot().lines()[1] == ' hello'
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

    def render(self) -> _core.FrameSnapshot:
        """Draw a frame now and return it."""
        canvas = self._canvas
        canvas._require_open()
        return canvas._host.call(lambda: canvas._runtime.render())

    def snapshot(self) -> _core.FrameSnapshot:
        """Return the last frame that was drawn, without drawing."""
        canvas = self._canvas
        canvas._require_open()
        return canvas._host.call(lambda: canvas._runtime.snapshot())

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
