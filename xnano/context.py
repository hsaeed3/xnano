"""
xnano.context

What a hook or operation is called with, and one frame or update of the clock.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Generic, final

import xnano_core as _core
from xnano._values import PixelEncoding, StateT_co
from xnano.pixels import Pixels
from xnano_core import CoreContext

if TYPE_CHECKING:
    from xnano._hooks import HookHandle
    from xnano.audio import Audio
    from xnano.placement import Placement
    from xnano.terminal import Terminal


@final
@dataclasses.dataclass(frozen=True, slots=True)
class BufferContext:
    """
    Concrete view of the target buffer inside a [`Context`][xnano.context.Context].

    Attributes:
        buffer: The underlying [`Buffer`][xnano_core.Buffer] being acted on.
        bounds: The target's rectangle in screen cells.
        x: The column of the target buffer.
        y: The row of the target buffer.
        width: The width of the target buffer in cells.
        height: The height of the target buffer in cells.
        size: The size of the target buffer in cells.
        text: The plain text shown in the target buffer.
    """

    buffer: _core.Buffer
    """The underlying [`Buffer`][xnano_core.Buffer] being acted on."""
    bounds: _core.Rectangle
    """The target's rectangle in screen cells."""

    @property
    def x(self) -> int:
        """The column of the target buffer."""
        return self.buffer.x

    @property
    def y(self) -> int:
        """The row of the target buffer."""
        return self.buffer.y

    @property
    def width(self) -> int:
        """The width of the target buffer in cells."""
        return self.buffer.width

    @property
    def height(self) -> int:
        """The height of the target buffer in cells."""
        return self.buffer.height

    @property
    def size(self) -> _core.Size:
        """The size of the target buffer in cells."""
        return _core.Size(self.buffer.width, self.buffer.height)

    @property
    def text(self) -> str:
        """The plain text shown in the target buffer."""
        return self.buffer.text

    def pixels(self, *, encoding: PixelEncoding = 'half_blocks') -> Pixels:
        """
        Return a [`Pixels`][xnano.pixels.Pixels] view of the target buffer.

        Args:
            encoding: How pixels are packed into cells.
        """
        return Pixels(self.buffer.pixels(encoding=encoding))

    def update(self, *operations: _core.Operation) -> None:
        """
        Apply core operations directly to the target buffer.

        Args:
            operations: Core operations to apply in order.
        """
        self.buffer.update(*operations)


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ParentContext:
    """
    Concrete view of the parent container inside a [`Context`][xnano.context.Context].

    Attributes:
        bounds: The parent's rectangle in screen cells.
        x: The left column of the parent in screen cells.
        y: The top row of the parent in screen cells.
        width: The width of the parent in cells.
        height: The height of the parent in cells.
        size: The size of the parent in cells.
    """

    bounds: _core.Rectangle
    """The parent's rectangle in screen cells."""

    @property
    def x(self) -> int:
        """The left column of the parent in screen cells."""
        return self.bounds.x

    @property
    def y(self) -> int:
        """The top row of the parent in screen cells."""
        return self.bounds.y

    @property
    def width(self) -> int:
        """The width of the parent in cells."""
        return self.bounds.width

    @property
    def height(self) -> int:
        """The height of the parent in cells."""
        return self.bounds.height

    @property
    def size(self) -> _core.Size:
        """The size of the parent in cells."""
        return _core.Size(self.bounds.width, self.bounds.height)

    def local(self, point: _core.Point) -> _core.Point:
        """
        Convert a point in screen cells to a point inside the parent.

        Args:
            point: A point in screen cells.
        """
        return _core.Point(point.x - self.bounds.x, point.y - self.bounds.y)


@final
@dataclasses.dataclass(frozen=True, slots=True)
class RootContext(Generic[StateT_co]):
    """
    Concrete view of the root terminal inside a [`Context`][xnano.context.Context].

    Attributes:
        terminal: The root [`Terminal`][xnano.terminal.Terminal].
        state: The root terminal's typed state.
        width: The width of the root terminal in cells.
        height: The height of the root terminal in cells.
        size: The size of the root terminal in cells.
        bounds: The rectangle of the root terminal in cells.
        time: Seconds elapsed on the root terminal's clock.
        fps: Target frame rate of the root terminal.
        clock: The root terminal's clock.
        audio: The root terminal's [`Audio`][xnano.audio.Audio].
        cursor: The root terminal's cursor.
    """

    terminal: Terminal[object]
    """The root [`Terminal`][xnano.terminal.Terminal]."""
    state: StateT_co
    """The root terminal's typed state."""

    @property
    def width(self) -> int:
        """The width of the root terminal in cells."""
        return self.terminal.width

    @property
    def height(self) -> int:
        """The height of the root terminal in cells."""
        return self.terminal.height

    @property
    def size(self) -> _core.Size:
        """The size of the root terminal in cells."""
        return self.terminal.size

    @property
    def bounds(self) -> _core.Rectangle:
        """The rectangle of the root terminal in cells."""
        size = self.terminal.size
        return _core.Rectangle(0, 0, size.width, size.height)

    @property
    def time(self) -> float:
        """Seconds elapsed on the root terminal's clock."""
        return self.terminal.clock.elapsed_seconds

    @property
    def fps(self) -> float:
        """Target frame rate of the root terminal."""
        return self.terminal.loop.fps

    @property
    def clock(self) -> _core.Clock:
        """The root terminal's clock."""
        return self.terminal.clock

    @property
    def audio(self) -> Audio:
        """The root terminal's [`Audio`][xnano.audio.Audio]."""
        return self.terminal.audio

    @property
    def cursor(self) -> _core.Cursor:
        """The root terminal's cursor."""
        return self.terminal.cursor


@final
@dataclasses.dataclass(frozen=True, slots=True)
class Context(Generic[StateT_co]):
    """
    What a hook or contextual operation is called with.

    The callback is never handed a bare event. The context carries the event, the target
    buffer, its parent and root scopes, and the terminal it happened in.

    Attributes:
        terminal: The terminal the hook belongs to.
        target: The terminal or placement the hook is attached to.
        event: The event, or ``None`` when a wait or frame tick ran. A state change is
            delivered as a [`TerminalStateChange`][xnano_core.TerminalStateChange].
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
        time: Seconds on the terminal's clock (shorthand for ``elapsed_seconds``).
        delta: Seconds since the previous frame.
        x: The left column of the target in screen cells.
        y: The top row of the target in screen cells.
        width: The width of the target in cells.
        height: The height of the target in cells.
        buffer: Concrete [`BufferContext`][xnano.context.BufferContext] for the target.
        parent: Concrete [`ParentContext`][xnano.context.ParentContext] for the target's parent.
        root: Concrete [`RootContext`][xnano.context.RootContext] for the terminal.
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

    @property
    def time(self) -> float:
        """Seconds on the terminal's clock when the event or frame ran."""
        return self.clock.elapsed_seconds

    @property
    def delta(self) -> float:
        """Seconds since the previous frame."""
        if isinstance(self.core, _core.FrameContext):
            return self.core.delta_seconds
        return 1.0 / self.terminal.loop.fps

    @property
    def x(self) -> int:
        """The left column of the target in screen cells."""
        return self.bounds.x

    @property
    def y(self) -> int:
        """The top row of the target in screen cells."""
        return self.bounds.y

    @property
    def width(self) -> int:
        """The width of the target in cells."""
        return self.bounds.width

    @property
    def height(self) -> int:
        """The height of the target in cells."""
        return self.bounds.height

    @property
    def buffer(self) -> BufferContext:
        """Concrete [`BufferContext`][xnano.context.BufferContext] for the target."""
        return BufferContext(buffer=self.target._buffer, bounds=self.bounds)

    @property
    def parent(self) -> ParentContext:
        """Concrete [`ParentContext`][xnano.context.ParentContext] for the target's parent."""
        parent_buffer = getattr(self.target, '_parent_buffer', None)
        if isinstance(parent_buffer, _core.Buffer):
            return ParentContext(bounds=parent_buffer._absolute_bounds)
        size = self.terminal.size
        return ParentContext(bounds=_core.Rectangle(0, 0, size.width, size.height))

    @property
    def root(self) -> RootContext[StateT_co]:
        """Concrete [`RootContext`][xnano.context.RootContext] for the terminal."""
        return RootContext(terminal=self.terminal, state=self.state)

    def local(self, point: _core.Point) -> _core.Point:
        """
        Convert a point in screen cells to a point inside the hook's target.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.open(offscreen=True, width=20, height=4) as terminal:
                placement = terminal.write('hi', x=10, y=1)

                @placement.hook
                def pressed(context: xnano.context.Context) -> None:
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
