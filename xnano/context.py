"""
xnano.context

What a hook or operation is called with, and one frame or update of the clock.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Generic, final

import xnano_core as _core
from xnano._values import DepsT_co, StateT_co
from xnano.pixels import Pixels
from xnano_core import CoreContext

if TYPE_CHECKING:
    from xnano._hooks import HookHandle
    from xnano.audio import AudioDevice
    from xnano.canvas import Canvas
    from xnano.cursor import Cursor
    from xnano.placement import Placement
    from xnano.time import Time


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

    @property
    def pixels(self) -> Pixels:
        """The pixels of the target buffer: ``context.buffer.pixels[column, row] = color``."""
        return Pixels(self.buffer.pixels())

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
    Concrete view of the root canvas inside a [`Context`][xnano.context.Context].

    Attributes:
        canvas: The root [`Canvas`][xnano.canvas.Canvas].
        state: The root canvas's typed state.
        width: The width of the root canvas in cells.
        height: The height of the root canvas in cells.
        size: The size of the root canvas in cells.
        bounds: The rectangle of the root canvas in cells.
        time: The root canvas's [`Time`][xnano.time.Time].
        fps: Target frame rate of the root canvas.
        audio: The root canvas's [`AudioDevice`][xnano.audio.AudioDevice].
        cursor: The root canvas's cursor.
    """

    canvas: Canvas[object, object]
    """The root [`Canvas`][xnano.canvas.Canvas]."""
    state: StateT_co
    """The root canvas's typed state."""

    @property
    def width(self) -> int:
        """The width of the root canvas in cells."""
        return self.canvas.width

    @property
    def height(self) -> int:
        """The height of the root canvas in cells."""
        return self.canvas.height

    @property
    def size(self) -> _core.Size:
        """The size of the root canvas in cells."""
        return self.canvas.size

    @property
    def bounds(self) -> _core.Rectangle:
        """The rectangle of the root canvas in cells."""
        size = self.canvas.size
        return _core.Rectangle(0, 0, size.width, size.height)

    @property
    def time(self) -> Time:
        """The root canvas's [`Time`][xnano.time.Time]."""
        return self.canvas.time

    @property
    def fps(self) -> float:
        """Target frame rate of the root canvas."""
        return self.canvas.fps

    @property
    def audio(self) -> AudioDevice:
        """The root canvas's [`AudioDevice`][xnano.audio.AudioDevice]."""
        return self.canvas.audio

    @property
    def cursor(self) -> Cursor:
        """The root canvas's cursor."""
        return self.canvas.cursor


@final
@dataclasses.dataclass(frozen=True, slots=True)
class Context(Generic[DepsT_co, StateT_co]):
    """
    What a hook or contextual operation is called with.

    The callback is never handed a bare event. The context carries the event, the target
    buffer, its parent and root scopes, and the canvas it happened in.

    Attributes:
        canvas: The canvas the hook belongs to.
        target: The canvas or placement the hook is attached to.
        event: The event, or ``None`` when a wait ran out. A state change is delivered as a
            [`TerminalStateChange`][xnano_core.TerminalStateChange], a frame of
            ``hook(on='frame')`` as a [`Frame`][xnano.context.Frame] and a step of
            ``hook(on='tick')`` as an [`Update`][xnano.context.Update].
        hook: The registration, so the hook can call ``hook.remove()``.
        keyboard: The key event, or ``None``. Its ``key`` is the key's name.
        mouse: The mouse event, or ``None``.
        pasted: The pasted text, or ``None``.
        size_changed: The new size, or ``None``.
        focus_gained: The focus-gained event, or ``None``.
        bounds: The target's rectangle in screen cells.
        state: The canvas's state.
        core: The underlying context, when the call came from the runtime.
        size: The canvas's size in cells.
        cursor: The canvas's cursor.
        input: The keys that are pressed and the cell under the pointer.
        audio: The canvas's [`AudioDevice`][xnano.audio.AudioDevice].
        time: The canvas's [`Time`][xnano.time.Time].
        x: The left column of the target in screen cells.
        y: The top row of the target in screen cells.
        width: The width of the target in cells.
        height: The height of the target in cells.
        buffer: Concrete [`BufferContext`][xnano.context.BufferContext] for the target.
        parent: Concrete [`ParentContext`][xnano.context.ParentContext] for the target's parent.
        root: Concrete [`RootContext`][xnano.context.RootContext] for the canvas.
    """

    canvas: Canvas[object, object]
    """The canvas the hook belongs to."""
    target: Canvas[object, object] | Placement[object, object]
    """The canvas or placement the hook is attached to."""
    event: _core.Event | _core.TerminalStateChange | Frame | Update | None
    """
    The event, or ``None`` when a wait ran out.

    A state change is delivered as a
    [`TerminalStateChange`][xnano_core.TerminalStateChange], a frame of ``hook(on='frame')``
    as a [`Frame`][xnano.context.Frame] and a step of ``hook(on='tick')`` as an
    [`Update`][xnano.context.Update].
    """
    hook: HookHandle[object, object]
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
    """The canvas's state."""
    core: CoreContext | None
    """The underlying context, when the call came from the runtime."""

    @property
    def audio(self) -> AudioDevice:
        """The canvas's audio."""
        return self.canvas.audio

    @property
    def size(self) -> _core.Size:
        """The canvas's size in cells."""
        return self.canvas.size

    @property
    def cursor(self) -> Cursor:
        """The canvas's cursor."""
        return self.canvas.cursor

    @property
    def input(self) -> _core.InputState:
        """The keys that are pressed and the cell under the pointer."""
        if self.core is not None:
            return self.core.input
        return self.canvas._runtime.input

    @property
    def time(self) -> Time:
        """The canvas's [`Time`][xnano.time.Time]."""
        return self.canvas.time

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
        size = self.canvas.size
        return ParentContext(bounds=_core.Rectangle(0, 0, size.width, size.height))

    @property
    def root(self) -> RootContext[StateT_co]:
        """Concrete [`RootContext`][xnano.context.RootContext] for the canvas."""
        return RootContext(canvas=self.canvas, state=self.state)

    def local(self, point: _core.Point) -> _core.Point:
        """
        Convert a point in screen cells to a point inside the hook's target.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.new(width=20, height=4) as canvas:
                placement = canvas.write('hi', x=10, y=1)

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
    One frame of a canvas's clock.

    Attributes:
        canvas: The canvas the frame belongs to.
        index: The number of steps the canvas's clock has counted, which is
            [`Time.frame`][xnano.time.Time.frame] when the frame was made.
        elapsed_seconds: Seconds on the canvas's clock.
        delta_seconds: Seconds since the previous frame (``0.0`` for the first).
        area: The rectangle the frame is drawn into, in cells.
    """

    canvas: Canvas[object, object]
    """The canvas the frame belongs to."""
    index: int
    """
    The number of steps the canvas's clock has counted, which is
    [`Time.frame`][xnano.time.Time.frame] when the frame was made.
    """
    elapsed_seconds: float
    """Seconds on the canvas's clock."""
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
        canvas: The canvas the update belongs to.
        elapsed_seconds: Seconds on the update's clock.
        delta_seconds: Seconds this update advances.
        is_fixed_step: Whether the update runs at a fixed rate.
    """

    canvas: Canvas[object, object]
    """The canvas the update belongs to."""
    elapsed_seconds: float
    """Seconds on the update's clock."""
    delta_seconds: float
    """Seconds this update advances."""
    is_fixed_step: bool
    """Whether the update runs at a fixed rate."""
