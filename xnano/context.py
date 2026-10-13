"""
xnano.context

What a hook is called with, and one frame or update of the clock.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Generic, final

import xnano_core as _core
from xnano._values import StateT_co
from xnano_core import CoreContext

if TYPE_CHECKING:
    from xnano._hooks import HookHandle
    from xnano.audio import Audio
    from xnano.placement import Placement
    from xnano.terminal import Terminal


@final
@dataclasses.dataclass(frozen=True, slots=True)
class Context(Generic[StateT_co]):
    """
    What a hook is called with.

    The hook is never handed a bare event. The context carries the event and the
    terminal it happened in.

    Attributes:
        terminal: The terminal the hook belongs to.
        target: The terminal or placement the hook is attached to.
        event: The event, or ``None`` when a wait ran out. A state change is delivered as
            a [`TerminalStateChange`][xnano_core.TerminalStateChange].
        hook: The registration, so the hook can call ``hook.remove()``.
        keyboard: The key event, or ``None``. Its ``key`` is the key's name.
        mouse: The mouse event, or ``None``.
        pasted: The pasted text, or ``None``.
        size_changed: The new size, or ``None``.
        focus_gained: The focus-gained event, or ``None``.
        bounds: The target's rectangle in screen cells.
        state: The terminal's state.
        core: The underlying context, when the call came from the runtime.
        clock: The terminal's clock.
        size: The terminal's size in cells.
        cursor: The terminal's cursor.
        input: The keys that are pressed and the cell under the pointer.
        audio: The terminal's [`Audio`][xnano.audio.Audio].
        elapsed_seconds: Seconds on the terminal's clock when the event was handled.
    """

    terminal: Terminal[object]
    """The terminal the hook belongs to."""
    target: Terminal[object] | Placement[object]
    """The terminal or placement the hook is attached to."""
    event: _core.Event | _core.TerminalStateChange | None
    """
    The event, or ``None`` when a wait ran out.

    A state change is delivered as a
    [`TerminalStateChange`][xnano_core.TerminalStateChange].
    """
    hook: HookHandle[object]
    """The registration, so the hook can call ``hook.remove()``."""
    keyboard: _core.KeyEvent | None
    """The key event, or ``None``. Its ``key`` is the key's name, such as ``'q'`` or ``'enter'``."""
    mouse: _core.MouseEvent | None
    """The mouse event, or ``None``."""
    pasted: str | None
    """The pasted text, or ``None``."""
    size_changed: _core.Size | None
    """The new size, or ``None``."""
    focus_gained: _core.Event | None
    """The focus-gained event, or ``None``."""
    bounds: _core.Rectangle
    """The target's rectangle in screen cells."""
    state: StateT_co
    """The terminal's state."""
    core: CoreContext | None
    """The underlying context, when the call came from the runtime."""

    @property
    def audio(self) -> Audio:
        """The terminal's audio."""
        return self.terminal.audio

    @property
    def clock(self) -> _core.Clock:
        """The terminal's clock."""
        return self.terminal.clock

    @property
    def size(self) -> _core.Size:
        """The terminal's size in cells."""
        return self.terminal.size

    @property
    def cursor(self) -> _core.Cursor:
        """The terminal's cursor."""
        return self.terminal.cursor

    @property
    def input(self) -> _core.InputState:
        """The keys that are pressed and the cell under the pointer."""
        if self.core is not None:
            return self.core.input
        return self.terminal._runtime.input

    @property
    def elapsed_seconds(self) -> float:
        """Seconds on the terminal's clock when the event was handled."""
        return self.clock.elapsed_seconds

    def local(self, point: _core.Point) -> _core.Point:
        """
        Convert a point in screen cells to a point inside the hook's target.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.open(offscreen=True, width=20, height=4) as terminal:
                placement = terminal.add('hi', x=10, y=1)

                @placement.hook
                def pressed(context: xnano.Context) -> None:
                    if context.mouse is not None:
                        context.local(context.mouse.position)
            ```
        """
        bounds = self.bounds
        return _core.Point(point.x - bounds.x, point.y - bounds.y)


@final
@dataclasses.dataclass(frozen=True, slots=True)
class Frame:
    """
    One frame of a terminal's clock.

    Attributes:
        terminal: The terminal the frame belongs to.
        index: How many frames came before this one.
        elapsed_seconds: Seconds on the terminal's clock.
        delta_seconds: Seconds since the previous frame (``0.0`` for the first).
        area: The rectangle the frame is drawn into, in cells.
    """

    terminal: Terminal[object]
    """The terminal the frame belongs to."""
    index: int
    """How many frames came before this one."""
    elapsed_seconds: float
    """Seconds on the terminal's clock."""
    delta_seconds: float
    """Seconds since the previous frame (``0.0`` for the first)."""
    area: _core.Rectangle
    """The rectangle the frame is drawn into, in cells."""


@final
@dataclasses.dataclass(frozen=True, slots=True)
class Update:
    """
    One step of a simulation, which runs separately from drawing.

    Attributes:
        terminal: The terminal the update belongs to.
        elapsed_seconds: Seconds on the update's clock.
        delta_seconds: Seconds this update advances.
        is_fixed_step: Whether the update runs at a fixed rate.
    """

    terminal: Terminal[object]
    """The terminal the update belongs to."""
    elapsed_seconds: float
    """Seconds on the update's clock."""
    delta_seconds: float
    """Seconds this update advances."""
    is_fixed_step: bool
    """Whether the update runs at a fixed rate."""
