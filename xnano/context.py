"""
xnano.context

What a hook is called with, and one frame or update of the clock.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Generic, cast, final

import xnano_core as _core
from xnano._internal._axes import check_point
from xnano._schema._generics import DepsT_co, StateT_co
from xnano.effects._controller import EffectController
from xnano.input import ClipboardInput, KeyboardInput, MouseInput, ScrollInput

if TYPE_CHECKING:
    from collections.abc import Callable

    from xnano.audio._player import AudioDevice
    from xnano.canvas import Canvas
    from xnano.cursor import Cursor
    from xnano.hooks._handles import HookHandle
    from xnano.input import Input
    from xnano.placement import Placement
    from xnano.region import Region
    from xnano.state import StateNamespace
    from xnano.time import Time

__all__ = ['Context', 'Frame', 'Plugin', 'ReadLog', 'Update']


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
        Create the attachment of a hook or component. Use ``context.plugin`` instead of
        calling this.

        Args:
            hook: The hook or component driver that is running.
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
                def count(context: xnano.Context) -> None:
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
class ReadLog:
    """
    What a component read while it was evaluated: the record that decides when it runs again.

    A component that read nothing that changes is evaluated once. One that read the time is
    evaluated again on every frame (or every beat for a playable), one that read the size
    or the region on the screen when the screen is resized, and one that read an input when
    that input arrives.

    Attributes:
        uses_time: Whether it read the clock, the event or the held keys.
        uses_size: Whether it read the size or the region of the canvas or of a buffer on the
            screen.
        uses_deps: Whether it read the dependencies.
        input_kinds: The kinds of input it read: ``'key'``, ``'mouse'``, ``'scroll'`` or
            ``'paste'``.
    """

    __slots__ = ('input_kinds', 'uses_deps', 'uses_size', 'uses_time')

    def __init__(self) -> None:
        """Start an empty record."""
        self.uses_time = False
        self.uses_size = False
        self.uses_deps = False
        self.input_kinds: set[str] = set()

    @property
    def is_dynamic(self) -> bool:
        """Whether anything that changes was read (the dependencies never change)."""
        return self.uses_time or self.uses_size or bool(self.input_kinds)

    def __repr__(self) -> str:
        return (
            f'ReadLog(uses_time={self.uses_time}, uses_size={self.uses_size}, '
            f'uses_deps={self.uses_deps}, input_kinds={sorted(self.input_kinds)})'
        )


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
        region: The [`Region`][xnano.region.Region] of the hook's buffer: its cells on the
            screen, or for a hook on a playable the beats and semitones of what it plays.
        size: The size in cells of ``context.buffer`` on the screen, the shortcut for
            ``context.region.size``.
        input: The keys and mouse buttons held down right now.

    Examples:
        ```python
        import xnano
        from xnano_core import Event

        with xnano.new(width=20, height=3) as canvas:
            label = canvas.write('hi', x=2)
            heard = []

            @label.hook(on='mouse', when="mouse.kind == 'press'")
            def pressed(context: xnano.Context) -> None:
                heard.append((context.mouse.position.x, context.buffer.x))

            canvas.push(Event.mouse_event(column=3, row=0, kind='press', button='left'))
            canvas.deliver_events()
            assert heard == [(3, 2)]
        ```
    """

    __slots__ = ('_core', '_event', '_log', '_owner', '_timeline', 'canvas', 'hook')

    canvas: Canvas[DepsT_co, StateT_co]
    """The root canvas the hook belongs to."""
    hook: HookHandle[object, object]
    """The registration, so the hook can call ``hook.remove()``."""

    def __init__(
        self,
        canvas: Canvas[DepsT_co, StateT_co],
        owner: Canvas[object, object] | Placement[object, object],
        hook: HookHandle[object, object],
        event: _core.Event | _core.TerminalStateChange | Frame | Update | None,
        core: _core.CoreContext | None,
        log: ReadLog | None = None,
        timeline: Callable[[], Region[float]] | None = None,
    ) -> None:
        """
        Create a context. The runtime does this for you; hooks receive one.

        Args:
            canvas: The root canvas.
            owner: The canvas or placement the hook is attached to.
            hook: The hook that is called.
            event: The event, or ``None``.
            core: The runtime's context for the event, or ``None``.
            log: Where to record what is read, for a component; ``None`` for a hook.
            timeline: Returns the region on the timeline of what a playable is playing, for a
                context of a playable; ``None`` for any other, whose ``region`` is on the
                screen.
        """
        self.canvas = canvas
        self._owner = owner
        self.hook = hook
        self._event = event
        self._core = core
        self._log = log
        self._timeline = timeline

    @property
    def event(self) -> _core.Event | _core.TerminalStateChange | Frame | Update | None:
        """
        The event: a core event for input, a [`Frame`][xnano.context.Frame] for
        ``hook(on='frame')``, an [`Update`][xnano.context.Update] for ``hook(on='tick')``, a
        state change for ``hook(on='state')``, or ``None`` when no event caused the call.
        """
        log = self._log
        if log is not None:
            log.uses_time = True
        return self._event

    @property
    def _root_canvas(self) -> Canvas[object, object]:
        return cast('Canvas[object, object]', self.canvas)

    @property
    def _input_event(self) -> _core.Event | None:
        event = self._event
        return event if isinstance(event, _core.Event) else None

    def _read(self, kind: str) -> None:
        """Record that a component read an input of ``kind``."""
        log = self._log
        if log is not None:
            log.input_kinds.add(kind)

    def _read_size(self) -> None:
        log = self._log
        if log is not None:
            log.uses_size = True

    def _read_time(self) -> None:
        log = self._log
        if log is not None:
            log.uses_time = True

    @property
    def keyboard(self) -> KeyboardInput:
        """The key of the event; ``key`` is ``None`` unless the event is a key."""
        self._read('key')
        return KeyboardInput(self._root_canvas, self._input_event, self._owner)

    @property
    def mouse(self) -> MouseInput:
        """The mouse button or movement of the event; ``position`` is ``None`` for any other."""
        self._read('mouse')
        return MouseInput(self._root_canvas, self._input_event, self._owner)

    @property
    def scroll(self) -> ScrollInput:
        """The mouse wheel steps of the event; ``x`` and ``y`` are ``0`` unless it is a wheel."""
        self._read('scroll')
        return ScrollInput(self._root_canvas, self._input_event, self._owner)

    @property
    def clipboard(self) -> ClipboardInput:
        """The pasted text of the event; ``text`` is ``None`` unless the event is a paste."""
        self._read('paste')
        return ClipboardInput(self._root_canvas, self._input_event)

    @property
    def buffer(self) -> Placement[object, object] | Canvas[object, object]:
        """The placement the hook is attached to, or the canvas for a hook on the canvas."""
        self._read_size()
        return self._owner

    @property
    def parent(self) -> Placement[object, object] | Canvas[object, object]:
        """What contains the hook's placement: another placement, or the canvas."""
        self._read_size()
        owner = self._owner
        parent = getattr(owner, '_parent_owner', None)
        if parent is None:
            placement = getattr(owner, '_parent_placement', None)
            parent = getattr(placement, '_parent_owner', None)
        return owner if parent is None else parent

    @property
    def root(self) -> Canvas[DepsT_co, StateT_co]:
        """The root canvas."""
        self._read_size()
        return self.canvas

    @property
    def plugin(self) -> Plugin:
        """The attachment of the hook that is running."""
        return Plugin(self.hook)

    @property
    def deps(self) -> DepsT_co:
        """The dependencies given to ``new(deps=...)``, or ``None``."""
        log = self._log
        if log is not None:
            log.uses_deps = True
        return self.canvas.deps

    @property
    def fx(self) -> EffectController:
        """Applies effects to the hook's buffer while the hook is active."""
        return EffectController(cast('Context[object, object]', self))

    @property
    def time(self) -> Time:
        """The canvas's [`Time`][xnano.time.Time]."""
        self._read_time()
        return self.canvas.time

    @property
    def audio(self) -> AudioDevice:
        """The canvas's [`AudioDevice`][xnano.audio.AudioDevice]."""
        self._read_time()
        return self.canvas.audio

    @property
    def cursor(self) -> Cursor:
        """The canvas's cursor."""
        return self.canvas.cursor

    @property
    def region(self) -> Region[float]:
        """
        The region of the hook's buffer.

        For a hook on a canvas or a placement it is the cells of ``context.buffer`` on the
        screen, the same region as ``context.buffer.region``: ``x`` and ``y`` are its
        column and row, inside the border and padding, and ``width`` and ``height`` its
        cells. A component that reads it runs again when the screen is resized.

        For a hook on a playable, or the playable itself, it is on the timeline: a piano roll
        of the sound the playable played most recently. ``x`` is the beat that sound started
        on, counted on the canvas's clock at its [`bpm`][xnano.canvas.Canvas.bpm], ``width``
        the beats it lasts, ``y`` its lowest pitch as a MIDI number and ``height`` the
        semitones it spans. Until the playable has played, the region is empty and starts at
        the beat the canvas has reached. Reading the cells of a region on the timeline, or the
        ``beats`` of a region on the screen, raises a
        [`TerminalError`][xnano.errors.TerminalError].

        The region is typed ``Region[float]``, because the same property serves a hook on a
        playable. For whole-number ``x`` and ``width`` on the screen, read
        ``context.buffer.region``, a ``Region[int]``, or ``context.size``.

        Examples:
            ```python
            import xnano
            from xnano_core import Event

            with xnano.new(width=20, height=6) as canvas:
                seen = []

                @canvas.hook(on='key')
                def pressed(context: xnano.Context) -> None:
                    seen.append(context.region)

                canvas.push(Event.key_press('a'))
                canvas.deliver_events()
                assert (seen[0].resolution, seen[0].width, seen[0].height) == ('cells', 20, 6)
            ```

            A hook on a playable sees the timeline of its sound:

            ```python
            import xnano
            from xnano_core import Event

            seen = []


            @xnano.playable
            def chord(context: xnano.Context) -> xnano.Note:
                return xnano.note(('C4', 'G4'), beats=2)


            @chord.hook(on='key')
            def pressed(
                context: xnano.Context, component_context: xnano.components.ComponentContext
            ) -> None:
                seen.append(context.region)


            with xnano.new(width=8, height=1) as canvas:
                canvas.play(chord)
                canvas.push(Event.key_press('a'))
                canvas.deliver_events()
                assert (seen[0].width, seen[0].y, seen[0].height) == (2.0, 60, 8)
            ```
        """
        timeline = self._timeline
        if timeline is not None:
            return timeline()
        self._read_size()
        return self._owner.region

    @property
    def size(self) -> _core.Size:
        """
        The size in cells of ``context.buffer`` on the screen.

        For a hook on a canvas or a placement this is ``context.region.size``: inside the
        border and padding of a placement. A playable has no region on the screen, so for it
        this is the size of the canvas it plays on.
        """
        self._read_size()
        width, height = self._owner._region_cell_size()
        return _core.Size(width, height)

    @property
    def input(self) -> Input:
        """The keys and mouse buttons held down right now."""
        self._read_time()
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
                def pressed(context: xnano.Context) -> None:
                    if context.mouse.position is not None:
                        context.local(context.mouse.position)

                assert placement.local(Point(11, 1)) == Point(1, 0)
            ```
        """
        point = check_point(point)
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
