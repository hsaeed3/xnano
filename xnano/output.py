"""
xnano.output

What the terminal has drawn, and the text a live terminal held back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import xnano_core as _core

if TYPE_CHECKING:
    from xnano.terminal import Terminal

__all__ = ['Output']


class Output:
    """
    The frames a terminal has drawn, and the text printed while it was live.

    Get it from [`Terminal.output`][xnano.terminal.Terminal.output].

    Attributes:
        is_captured: Whether a live terminal is holding back what is printed, so it
            cannot corrupt the screen.

    Examples:
        ```python
        import xnano

        with xnano.iter(offscreen=True, width=12, height=2) as terminal:
            terminal.write('hello', x=1, y=1)
            terminal.output.render()
            assert terminal.output.snapshot().lines()[1] == ' hello'
        ```
    """

    def __init__(self, terminal: Terminal[object]) -> None:
        """
        Create the output's view of a terminal. Use ``terminal.output`` instead of calling this.

        Args:
            terminal: The terminal whose frames and held-back text this reads.
        """
        self._terminal = terminal

    @property
    def is_captured(self) -> bool:
        """Whether a live terminal is holding back what is printed, so it cannot corrupt the screen."""
        terminal = self._terminal
        terminal._require_open()
        return terminal._host.call(lambda: terminal._runtime.is_output_captured)

    def render(self) -> _core.FrameSnapshot:
        """Draw a frame now and return it."""
        terminal = self._terminal
        terminal._require_open()
        return terminal._host.call(lambda: terminal._runtime.render())

    def snapshot(self) -> _core.FrameSnapshot:
        """Return the last frame that was drawn, without drawing."""
        terminal = self._terminal
        terminal._require_open()
        return terminal._host.call(lambda: terminal._runtime.snapshot())

    def take_captured(self) -> str:
        """
        Return the text printed or logged since the last call, from a live terminal.

        A live terminal holds back anything written to standard output or standard error
        so it cannot corrupt the screen. Text you do not take is printed when the terminal
        closes.
        """
        terminal = self._terminal
        terminal._require_open()
        return terminal._host.call(lambda: terminal._runtime.take_captured_output())
