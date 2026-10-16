"""
xnano.context

What a hook is called with, and one frame or update of the clock.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Generic, cast, final

import xnano_core as _core
from xnano._effect_controller import EffectController
from xnano._values import DepsT_co, StateT_co
from xnano.input import ClipboardInput, KeyboardInput, MouseInput, ScrollInput

if TYPE_CHECKING:
    from xnano._hooks import HookHandle
    from xnano.audio import AudioDevice
    from xnano.canvas import Canvas
    from xnano.cursor import Cursor
    from xnano.input import Input
    from xnano.placement import Placement
    from xnano.state import StateNamespace
    from xnano.time import Time

__all__ = ['Context', 'Frame', 'Plugin', 'Update']


@final
class Plugin:
    """
    The attachment of a hook: the hook or component that is running right now.

    ``context.plugin`` names that one attachment and nothing else. The hook itself is
    ``context.hook``.

    Attributes:
        hook: The hook this attachment belongs to.
        state: State that belongs to this attachment alone, read with ``get`` and written
            with ``push``; see [`StateNamespace`][xnano.state.StateNamespace].
    """

    __slots__ = ('hook',)

    def __init__(self, hook: HookHandle[object, object]) -> None:
        """
        Create the attachment of a hook. Use ``context.plugin`` instead of calling this.

        Args:
            hook: The hook that is running.
        """
        self.hook = hook

    @property
    def state(self) -> StateNamespace:
        """
        State that belongs to this hook alone.

        No other hook or placement sees it, and it is deleted when the hook is removed. To
        share a value between hooks, keep it in ``context.root.state``.

        Examples:
            ```python
            import xnano
            from xnano_core import Event

            with xnano.new(width=8, height=1) as canvas:

                @canvas.hook(on='key')
                def count(context: xnano.context.Context) -> None:
                    state = context.plugin.state
                    state.push('presses', state.get('presses', default=0) + 1)
                    context.root.state.push('latest', state.get('presses'))

                canvas.push(Event.key_press('a'))
                canvas.push(Event.key_press('b'))
                canvas.deliver_events()
                assert canvas.state.get('latest') == 2
            ```
        """
        return self.hook._state_namespace()


@final
class Context(Generic[DepsT_co, StateT_co]):
    """
    What a hook is called with.

    The context carries the event and live views of where the hook is attached. Its members are
    read when you use them, so a context costs almost nothing to receive. A generator hook
    receives a new context each time it resumes, so ``context.mouse.position`` is always the
    newest event's.

    ``buffer``, ``parent`` and ``root`` are live objects with concrete values:
    ``context.parent.width`` is an ``int``, and ``context.buffer`` has the verbs of a placement
    (``move``, ``up``, ``down``, ``left`` and ``right``). On a placement or canvas themselves,
    ``parent`` and ``root`` are formula scopes whose members are expressions, such as
    ``placement.parent.width``.

    ``keyboard``, ``mouse``, ``scroll`` and ``clipboard`` are always there; each member is
    ``None`` (or ``0`` for the wheel) unless the event the hook is handling is of that kind.
    Each has ``get()`` and ``push(value)``.

    Attributes:
        canvas: The root canvas the hook belongs to.
        event: The event, a [`Frame`][xnano.context.Frame] for ``hook(on='frame')``, an
            [`Update`][xnano.context.Update] for ``hook(on='tick')``, a
            [`TerminalStateChange`][xnano_core.TerminalStateChange] for ``hook(on='state')``,
            or ``None`` when no event caused the call.
        hook: The registration, so the hook can call ``hook.remove()``.
        keyboard: The key of the event, with ``key``, ``kind`` and ``modifiers``.
        mouse: The mouse button or movement of the event, with ``position``, ``button``,
            ``kind`` and ``is_down``.
        scroll: The wheel steps of the event, ``x`` and ``y``.
        clipboard: The pasted text of the event.
        buffer: The placement (or the canvas) the hook is attached to.
        parent: What contains the placement; the canvas itself for a hook on the canvas.
        root: The root canvas.
        plugin: The attachment of the hook that is running.
        deps: The dependencies given to ``new(deps=...)``.
        fx: Applies effects to the hook's buffer while the hook is active.
        time: The canvas's [`Time`][xnano.time.Time].
        audio: The canvas's [`AudioDevice`][xnano.audio.AudioDevice].
        cursor: The canvas's cursor.
        size: The canvas's size in cells.
        input: The keys and mouse buttons held down right now.

    Examples:
        ```python
        import xnano
        from xnano_core import Event

        with xnano.new(width=20, height=3) as canvas:
            label = canvas.write('hi', x=2)
            heard = []

            @label.hook(on='mouse', when="mouse.kind == 'press'")
            def pressed(context: xnano.context.Context) -> None:
                heard.append((context.mouse.position.x, context.buffer.x))

            canvas.push(Event.mouse_event(column=3, row=0, kind='press', button='left'))
            canvas.deliver_events()
            assert heard == [(3, 2)]
        ```
    """

    __slots__ = ('_core', '_owner', 'canvas', 'event', 'hook')

    canvas: Canvas[DepsT_co, StateT_co]
    """The root canvas the hook belongs to."""
    event: _core.Event | _core.TerminalStateChange | Frame | Update | None
    """
    The event: a core event for input, a [`Frame`][xnano.context.Frame] for ``hook(on='frame')``,
    an [`Update`][xnano.context.Update] for ``hook(on='tick')``, a state change for
    ``hook(on='state')``, or ``None`` when no event caused the call.
    """
    hook: HookHandle[object, object]
    """The registration, so the hook can call ``hook.remove()``."""

    def __init__(
        self,
        canvas: Canvas[DepsT_co, StateT_co],
        owner: Canvas[object, object] | Placement[object, object],
        hook: HookHandle[object, object],
        event: _core.Event | _core.TerminalStateChange | Frame | Update | None,
        core: _core.CoreContext | None,
    ) -> None:
        """
        Create a context. The runtime does this for you; hooks receive one.

        Args:
            canvas: The root canvas.
            owner: The canvas or placement the hook is attached to.
            hook: The hook that is called.
            event: The event, or ``None``.
            core: The runtime's context for the event, or ``None``.
        """
        self.canvas = canvas
        self._owner = owner
        self.hook = hook
        self.event = event
        self._core = core

    @property
    def _root_canvas(self) -> Canvas[object, object]:
        return cast('Canvas[object, object]', self.canvas)

    @property
    def _input_event(self) -> _core.Event | None:
        event = self.event
        return event if isinstance(event, _core.Event) else None

    @property
    def keyboard(self) -> KeyboardInput:
        """The key of the event; ``key`` is ``None`` unless the event is a key."""
        return KeyboardInput(self._root_canvas, self._input_event)

    @property
    def mouse(self) -> MouseInput:
        """The mouse button or movement of the event; ``position`` is ``None`` for any other."""
        return MouseInput(self._root_canvas, self._input_event)

    @property
    def scroll(self) -> ScrollInput:
        """The mouse wheel steps of the event; ``x`` and ``y`` are ``0`` unless it is a wheel."""
        return ScrollInput(self._root_canvas, self._input_event)

    @property
    def clipboard(self) -> ClipboardInput:
        """The pasted text of the event; ``text`` is ``None`` unless the event is a paste."""
        return ClipboardInput(self._root_canvas, self._input_event)

    @property
    def buffer(self) -> Placement[object, object] | Canvas[object, object]:
        """The placement the hook is attached to, or the canvas for a hook on the canvas."""
        return self._owner

    @property
    def parent(self) -> Placement[object, object] | Canvas[object, object]:
        """What contains the hook's placement: another placement, or the canvas."""
        owner = self._owner
        parent = getattr(owner, '_parent_owner', None)
        if parent is None:
            placement = getattr(owner, '_parent_placement', None)
            parent = getattr(placement, '_parent_owner', None)
        return owner if parent is None else parent

    @property
    def root(self) -> Canvas[DepsT_co, StateT_co]:
        """The root canvas."""
        return self.canvas

    @property
    def plugin(self) -> Plugin:
        """The attachment of the hook that is running."""
        return Plugin(self.hook)

    @property
    def deps(self) -> DepsT_co:
        """The dependencies given to ``new(deps=...)``, or ``None``."""
        return self.canvas.deps

    @property
    def fx(self) -> EffectController:
        """Applies effects to the hook's buffer while the hook is active."""
        return EffectController(cast('Context[object, object]', self))

    @property
    def time(self) -> Time:
        """The canvas's [`Time`][xnano.time.Time]."""
        return self.canvas.time

    @property
    def audio(self) -> AudioDevice:
        """The canvas's [`AudioDevice`][xnano.audio.AudioDevice]."""
        return self.canvas.audio

    @property
    def cursor(self) -> Cursor:
        """The canvas's cursor."""
        return self.canvas.cursor

    @property
    def size(self) -> _core.Size:
        """The canvas's size in cells."""
        return self.canvas.size

    @property
    def input(self) -> Input:
        """The keys and mouse buttons held down right now."""
        return self.canvas.input

    def local(self, point: _core.Point) -> _core.Point:
        """
        Convert a cell of the screen into a cell of the hook's buffer.

        Args:
            point: A cell in screen coordinates, such as ``context.mouse.position``.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.new(width=20, height=4) as canvas:
                placement = canvas.write('hi', x=10, y=1)

                @placement.hook(on='mouse')
                def pressed(context: xnano.context.Context) -> None:
                    if context.mouse.position is not None:
                        context.local(context.mouse.position)

                assert placement.local(Point(11, 1)) == Point(1, 0)
            ```
        """
        bounds = self._owner._buffer._absolute_bounds
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
