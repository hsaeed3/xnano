"""
xnano.terminal._opening

A terminal that is being opened from a coroutine: awaited, or entered with ``async with``.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Generator
from typing import TYPE_CHECKING, Generic

from xnano._schema._generics import DepsT, StateT

if TYPE_CHECKING:
    from xnano.terminal import Terminal


class OpeningTerminal(Generic[DepsT, StateT]):
    """
    A terminal that is being opened: await it, or enter it with ``async with``.

    [`open_async`][xnano.open_async] and
    [`Canvas.open_async`][xnano.canvas.Canvas.open_async] return one. ``await`` gives the open
    [`Terminal`][xnano.Terminal]. ``async with`` opens it, gives it to the block and closes it
    when the block ends, the way ``with xnano.open()`` does. The terminal is opened once:
    awaiting again gives the same terminal.

    Attributes:
        terminal: The open terminal, or ``None`` until it is awaited or entered.

    Examples:
        ```text
        async with xnano.open_async(height=3) as terminal:
            terminal.screen.write('hello')
            await terminal.run_async(stop_on='q')

        terminal = await xnano.open_async(height=3)
        ```
    """

    __slots__ = ('_open_terminal', '_terminal')

    def __init__(
        self,
        open_terminal: Callable[[], Coroutine[object, object, Terminal[DepsT, StateT]]],
    ) -> None:
        """
        Keep the coroutine function that opens the terminal; nothing opens until it is awaited.

        Args:
            open_terminal: Opens the terminal and returns it.
        """
        self._open_terminal = open_terminal
        self._terminal: Terminal[DepsT, StateT] | None = None

    @property
    def terminal(self) -> Terminal[DepsT, StateT] | None:
        """The open terminal, or ``None`` until it is awaited or entered."""
        return self._terminal

    async def _open_once(self) -> Terminal[DepsT, StateT]:
        if self._terminal is None:
            self._terminal = await self._open_terminal()
        return self._terminal

    def __await__(self) -> Generator[object, None, Terminal[DepsT, StateT]]:
        return self._open_once().__await__()

    async def __aenter__(self) -> Terminal[DepsT, StateT]:
        terminal = await self._open_once()
        return await terminal.__aenter__()

    async def __aexit__(self, exception_type: object, *rest: object) -> None:
        terminal = self._terminal
        if terminal is not None:
            await terminal.__aexit__(exception_type, *rest)
