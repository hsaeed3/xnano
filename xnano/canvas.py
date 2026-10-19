"""
xnano.canvas

The canvas: a virtual terminal of cells with a clock, hooks, sound, a cursor and state.
"""

from __future__ import annotations

import contextvars
import dataclasses
import itertools
import math
import re
import threading
import time as wall_clock
import weakref
from collections import deque
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Final,
    Generic,
    Literal,
    cast,
    overload,
)

import xnano_core as _core
from xnano_core import CoreContext, FrameContext, JSONValue, UpdateContext

if TYPE_CHECKING:
    from _typeshed import DataclassInstance
    from typing_extensions import Self, TypeIs, Unpack

    from xnano._schema._content import PlaySource
    from xnano._schema._media import PlayOptions
    from xnano._schema._terminal import CanvasSettings, OpenSettings
    from xnano.audio._notes import PlayHandle
    from xnano.audio._player import AudioDevice
    from xnano.context import Context
    from xnano.terminal import Terminal
    from xnano.types import RenderableEffectSpecification

from xnano._internal._attributes import refuse_unknown_keywords
from xnano._internal._axes import (
    check_axis,
    check_edges,
    check_layer,
    check_layout,
    check_point,
    size_share,
)
from xnano._internal._content import content_buffer
from xnano._internal._dynamic_operations import DynamicOperation
from xnano._internal._optional import require
from xnano._runtime._host import _Host, _InlineHost, _Registration, _ThreadHost
from xnano._runtime._slots import (
    apply_pending_layouts,
    close_slot,
    open_slot,
    slot_of,
)
from xnano._schema._appearance import RGB, ColorValue, Spacing
from xnano._schema._axes import Axis, AxisName, Percentage
from xnano._schema._content import Content
from xnano._schema._generics import (
    DepsT,
    StateT,
    ValueT,
    WrittenDepsT,
    WrittenStateT,
)
from xnano._schema._hooks import KeyName
from xnano._schema._layout import CanvasLayout, EdgeBehavior
from xnano.appearance._decoration import Decorated, insets_for, paint_decoration
from xnano.appearance._look import (
    MOST_CELLS,
    Appearance,
    appearance_fields,
    resolve_spacing,
)
from xnano.appearance._owners import _Looked, _TextModifiers
from xnano.art._images import Image, ImageSource
from xnano.art._pixels import Pixel
from xnano.components import _as_component, _attach_component, _play_component
from xnano.context import Frame, ReadLog, Update
from xnano.cursor import Cursor
from xnano.effects._properties import EffectParameters, RenderableEffectProperties
from xnano.effects._registry import apply_effects
from xnano.errors import (
    TerminalClosedError,
    TerminalError,
    _release_frames,
)
from xnano.expressions import (
    Parent,
    ParentExpressionScope,
    Root,
    RootExpressionScope,
)
from xnano.hooks._handles import HookHandle, _Hooked
from xnano.input import _ESTIMATED_HOLD_SECONDS, Input
from xnano.operations import (
    ContextualOperation,
)
from xnano.output import Output
from xnano.placement import Placement
from xnano.region import Region
from xnano.state import (
    StateNamespace,
    _commit_pending,
    _create_branch,
    _HookRun,
    _prepare_state,
    _reference_for,
    _remove_branch,
    _state_field_types,
    _StateAccessor,
    _StateFollower,
    _StateFollowers,
)
from xnano.time import Time

__all__ = ['Canvas', 'active', 'iter', 'new']

_active_canvas: contextvars.ContextVar[
    tuple[weakref.ref[Canvas[object, object]], ...]
] = contextvars.ContextVar('xnano.active_canvas', default=())
"""Weak references to the canvases that module-level functions act on, innermost first.

The references are weak so that a canvas dropped without ``close()`` can be collected.
"""


def _live_canvases() -> list[Canvas[object, object]]:
    """The canvases of the context variable that still exist, innermost first."""
    canvases = (reference() for reference in _active_canvas.get())
    return [canvas for canvas in canvases if canvas is not None]


def _current_canvas() -> Canvas[object, object] | None:
    """Return the innermost canvas of the context variable that still exists."""
    for reference in _active_canvas.get():
        canvas = reference()
        if canvas is not None:
            return canvas
    return None


def _make_current(canvas: Canvas[object, object]) -> None:
    _active_canvas.set((weakref.ref(canvas),))


_enclosing_canvases: contextvars.ContextVar[
    tuple[weakref.ref[Canvas[object, object]], ...]
] = contextvars.ContextVar('xnano.enclosing_canvases', default=())
"""Weak references to the canvases whose ``with`` block is running, innermost first.

``new()`` writes the canvas it creates into the innermost one that is still running.
"""


def _enclosing_canvas() -> Canvas[object, object] | None:
    """Return the innermost running canvas whose ``with`` block the caller is inside."""
    for reference in _enclosing_canvases.get():
        canvas = reference()
        if canvas is not None and canvas.is_running:
            return canvas
    return None


class _Unset:
    """The value of ``deps`` and ``state`` when they were not given at all."""

    def __repr__(self) -> str:
        return 'unset'


_UNSET: Final = _Unset()

# A manual clock can jump far in one step, and the fixed steps it crossed are run, up to this
# many in one step; the rest are run by the steps that follow.
_MANUAL_CATCH_UP_STEPS: Final = 100_000
_MAXIMUM_STATE_RERUNS: Final = 64
"""The most times one hook runs again in one step because of the state its own runs changed."""

_MAXIMUM_BPM: Final = 600000.0


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
    content: Content, appearance: Appearance, is_decorated: bool
) -> tuple[Content, Appearance | None]:
    """Lines of text become one text; a decoration makes the text a styled box."""
    if isinstance(content, (list, tuple)) and all(
        isinstance(line, str) for line in content
    ):
        content = '\n'.join(cast('Sequence[str]', content))
    if not is_decorated or not isinstance(content, str):
        return content, None
    appearance.text = content
    return appearance.snapshot(), appearance


def _plain_appearance(appearance: Mapping[str, object]) -> dict[str, object]:
    """The appearance keywords as ``Appearance`` fields, with ``border=True`` and ``False`` as kinds."""
    plain = appearance_fields(appearance)
    if plain.get('border') is True:
        plain['border'] = 'plain'
    elif plain.get('border') is False:
        plain['border'] = None
    return plain


def _check_appearance(appearance: Mapping[str, object]) -> None:
    """Draw the appearance keywords on a throwaway look so that a bad value raises now."""
    look = Appearance(**cast('dict[str, object]', _plain_appearance(appearance)))  # type: ignore[arg-type]
    look.text_style()
    insets = insets_for(look, 1, 1)
    paint_decoration(
        _core.Buffer(width=1 + insets.horizontal, height=1 + insets.vertical),
        look,
        insets,
    )


def _effect_key(effect: EffectParameters) -> str | None:
    """The key a running effect is found by, or ``None`` for an operation that is not one."""
    key = getattr(effect, 'key', None)
    return key if isinstance(key, str) else None


def _is_effect_running(effects: _core.EffectManager, effect: EffectParameters) -> bool:
    key = _effect_key(effect)
    return key is not None and bool(effects.is_running(key))


def _check_fps(fps: object) -> float:
    if isinstance(fps, bool) or not isinstance(fps, (int, float)):
        raise TerminalError(
            f'fps must be a number above zero, but was {fps!r}. Use 30 or 60 for smooth '
            f'motion.',
            code='validation.type',
            location='fps',
            input_value=fps,
        )
    if not math.isfinite(fps) or fps <= 0:
        raise TerminalError(
            f'fps must be a number above zero, but was {fps!r}. Use 30 or 60 for smooth '
            f'motion.',
            code='validation.bounds',
            location='fps',
            input_value=fps,
        )
    return float(fps)


def _check_bpm(bpm: object) -> float:
    if (
        isinstance(bpm, bool)
        or not isinstance(bpm, (int, float))
        or not math.isfinite(bpm)
        or not 0 < bpm <= _MAXIMUM_BPM
    ):
        raise ValueError(
            f'The tempo {bpm!r} is out of range. Use a number of beats per minute above 0 '
            f'and at most 600000, such as bpm=120.'
        )
    return float(bpm)


def _check_title(value: object) -> str | None:
    """Return ``value`` when it is text or ``None``, which is what a window title is."""
    if value is not None and not isinstance(value, str):
        raise TypeError(
            f'title must be text or None, but got {value!r}. Pass a single line of text '
            f'such as title="My program", or None to clear it.'
        )
    return value


def _check_size(name: str, value: object) -> int | str | None:
    """
    Check a ``width`` or ``height`` of ``new()`` or ``open()``: cells, or a percentage.

    A percentage is kept as written, and read against the window when the canvas needs
    cells.
    """
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        share = size_share(stripped)
        if share is None or not 0.0 < share <= 1.0:
            raise ValueError(
                f'{name} must be a whole number of cells or a percentage of the window from '
                f"above 0% to 100%, but was {value!r}. Pass {name}=40 or {name}='50%', or "
                f'leave it out.'
            )
        return stripped
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MOST_CELLS
    ):
        raise ValueError(
            f'{name} must be a whole number of cells from 1 to {MOST_CELLS}, or a percentage '
            f"of the window such as '50%', but was {value!r}. Pass {name}=40 or "
            f"{name}='50%', or leave it out."
        )
    return value


def _is_whole_window(value: int | str | None) -> bool:
    """Whether a checked size is ``None`` or ``'100%'``: all of the window along that axis."""
    return value is None or (isinstance(value, str) and size_share(value) == 1.0)


def _size_in_cells(
    value: int | str | None,
    along: Literal['columns', 'lines'],
    default: int | None = None,
    available: int | None = None,
) -> int:
    """
    The cells of a checked size: the number, a share of the space, or ``default``.

    The space is ``available`` cells when given, which also stands for ``default``, and the
    window otherwise. The window is asked for its size only for a percentage, and
    ``default=None`` stands for the whole window along that axis.
    """
    if isinstance(value, int):
        return value
    if available is not None:
        default = None
    if value is None and default is not None:
        return default
    if available is None:
        from xnano.terminal import _screen

        space: int = getattr(_screen.window_size(), along)
    else:
        space = available
    share = 1.0 if value is None else (size_share(value) or 1.0)
    return max(1, min(MOST_CELLS, round(space * share)))


def _canvas_size(
    width: int | str | None,
    height: int | str | None,
    enclosing_size: tuple[int, int] | None,
) -> tuple[int, int]:
    """The columns and rows of a new canvas, measured in its enclosing canvas when it has one."""
    if enclosing_size is None:
        return _size_in_cells(width, 'columns', 80), _size_in_cells(height, 'lines', 24)
    return (
        _size_in_cells(width, 'columns', available=enclosing_size[0]),
        _size_in_cells(height, 'lines', available=enclosing_size[1]),
    )


_MOST_STEP_SECONDS: Final = 1_000_000_000
"""The most seconds one step may move a clock by."""


class Canvas(_Hooked[DepsT, StateT], _TextModifiers, Generic[DepsT, StateT]):
    """
    A workspace of text, pixels and sound on a clock, with or without a screen.

    A canvas is a virtual terminal. Create one with [`new`][xnano.new]: it has a size, a clock,
    hooks, a cursor, sound and state, and no screen, so it draws into memory and its time moves
    only when you move it with [`step`][xnano.canvas.Canvas.step] or
    [`iter`][xnano.canvas.Canvas.iter], which makes every run the same. ``new(realtime=True)``
    runs it on the wall clock instead, on a thread of its own. [`open`][xnano.canvas.Canvas.open]
    puts the same object on your screen, where it becomes a [`Terminal`][xnano.Terminal]
    and its time continues from where it was. It is not the drawing widget
    [`xnano.widgets.Figure`][xnano.widgets.Figure].

    How a canvas ends depends on who moves its clock. On a canvas from ``new()``,
    [`quit`][xnano.canvas.Canvas.quit] only ends a running ``iter()``: the canvas stays open
    for writing and rendering. On a canvas that runs by itself (``realtime=True``, or opened
    on the screen) its loop ends with ``quit()``, ``Ctrl-C`` or a quit key of
    [`run`][xnano.canvas.Canvas.run], and that closes the canvas. [`close`][xnano.canvas.Canvas.close]
    (or leaving the ``with`` block) always closes it. The three states are:

    | State | Read it from | Meaning |
    | --- | --- | --- |
    | running | ``is_running`` | open, and its loop has not been asked to end |
    | time stopped | ``time.is_stopped`` | frozen by ``stop()``; it still draws and hears input |
    | closed | ``is_closed`` | torn down; it cannot draw or listen |

    What you put on the canvas is declared on the canvas itself:
    [`write`][xnano.canvas.Canvas.write], [`hook`][xnano.canvas.Canvas.hook] and indexing.
    Everything else is grouped by what it is: ``canvas.time`` is the
    [`Time`][xnano.time.Time], ``canvas.cursor`` the one [`Cursor`][xnano.cursor.Cursor],
    ``canvas.output`` the [`Output`][xnano.output.Output] of drawn frames and
    ``canvas.audio`` the [`AudioDevice`][xnano.audio.AudioDevice].

    Any thread may write, remove, draw and play. Hooks run on the canvas's loop, so keep them
    short.

    Attributes:
        is_closed: Whether the canvas has been torn down.
        is_running: Whether the canvas is open and its loop has not been asked to end.
        core_buffer: The core buffer everything is added to, as large as the canvas.
        parent: Symbolic expressions for the parent container's ``width``, ``height`` and ``size``.
        root: Symbolic expressions for the root canvas's geometry and clock.
        size: The size of the canvas in cells.
        width: The width of the canvas in cells.
        height: The height of the canvas in cells.
        x: The column of the canvas, which is ``0`` for a canvas that is not written into another.
        y: The row of the canvas, which is ``0`` for a canvas that is not written into another.
        title: The window title; ``None`` clears it.
        fps: The most frames drawn per second.
        bpm: Beats per minute for beat timers, notes and melodies.
        deps: The dependencies given to ``new(deps=...)``, which hooks read.
        time: The [`Time`][xnano.time.Time] everything on the canvas runs on.
        cursor: The canvas's one cursor.
        state: The dataclass given to ``new(state=...)``.
        output: The [`Output`][xnano.output.Output]: what was drawn, and held-back text.
        audio: The [`AudioDevice`][xnano.audio.AudioDevice]: notes, melodies, sounds and the
            microphone.
        input: The keys held down right now, for programs that poll instead of listening.

    Examples:
        ```python
        import xnano

        with xnano.new(width=12, height=2, fps=10) as canvas:
            greeting = canvas.write('hello', x=1, y=1)
            for frame in canvas.iter(count=3):
                greeting.text = f'frame {frame.index}'
            assert canvas.render().splitlines()[1] == ' frame 2'
            assert round(canvas.time.elapsed, 3) == 0.3
        ```
    """

    output: Output
    """The canvas's drawn frames and captured text."""

    def __new__(cls, *arguments: object, **keywords: object) -> Self:
        """Refuse a direct call: a canvas is created with ``xnano.new``."""
        if arguments or 'is_realtime' not in keywords:
            raise TypeError(
                f'{cls.__name__} is not created by calling it. Create a canvas with '
                f'xnano.new(...), or put one on the screen with xnano.open(...).'
            )
        return super().__new__(cls)

    def __init__(
        self,
        *,
        width: int | str | None,
        height: int | str | None,
        fps: float,
        bpm: float,
        is_realtime: bool,
        deps: object,
        state: object,
        title: str | None,
        gates: Mapping[str, object],
        appearance: Mapping[str, object],
        effects: Sequence[RenderableEffectSpecification],
        enclosing: Canvas[object, object] | None = None,
        layout: CanvasLayout = 'overlay',
        edges: EdgeBehavior = 'clip',
    ) -> None:
        """
        Create a canvas. Use [`new`][xnano.new] instead of calling this.

        Args:
            width: The width in cells or as a percentage of the window, or ``None`` for 80.
            height: The height in cells or as a percentage of the window, or ``None`` for 24.
            fps: The most frames drawn per second.
            bpm: Beats per minute.
            is_realtime: Whether the canvas runs on the wall clock, on a thread of its own.
            deps: The dependencies, or the unset marker when none were given.
            state: A dataclass instance the canvas keeps and validates, or the unset marker.
            title: The window title, or ``None``.
            gates: The terminal settings that were given, by name.
            appearance: The appearance keywords of the canvas itself, by name.
            effects: Effects to apply to the canvas, as dictionaries with a ``kind`` key.
            enclosing: The canvas whose ``with`` block this one was created in, which its
                sizes are measured in and which closes it, or ``None``.
            layout: How the canvas places what is written on it.
            edges: What content written on the canvas does at the edges of its area.
        """
        super().__init__()
        self._canvas = self
        self._root_canvas = self
        self._lock = threading.RLock()
        self._root = _core.Buffer()
        self._buffer = self._root
        self._fps = fps
        self._bpm = bpm
        self._is_realtime = is_realtime
        self._requested_width = width
        self._requested_height = height
        self._deps_given = deps is not _UNSET
        self._deps = cast('DepsT', None if deps is _UNSET else deps)
        self._state_given = state is not _UNSET
        self._title = title
        self._gates: dict[str, object] = dict(gates)
        self._resolved_gates: dict[str, object] = {}
        self._appearance = (
            Appearance(**cast('dict[str, object]', _plain_appearance(appearance)))  # type: ignore[arg-type]
            if appearance
            else None
        )
        self._decorated: Decorated | None = None
        self._dirty_looks: dict[int, _Looked] = {}
        self._placements: list[Placement[DepsT, StateT]] = []
        self._ledger: list[_Registration] = []
        self._effects: list[
            tuple[EffectParameters, Canvas[object, object] | Placement[object, object]]
        ] = []
        self._frame_listeners: dict[int, Callable[[FrameContext], None]] = {}
        self._frame_listener_tokens = itertools.count()
        self._frame_demand = 0
        self._frame_registration: _Registration | None = None
        self._size_hook: _core.Hook | None = None
        self._parent_placement: Placement[object, object] | None = None
        self._children: list[Canvas[object, object]] = []
        self._enclosing: weakref.ref[Canvas[object, object]] | None = None
        self._enclosing_size: tuple[int, int] | None = None
        self._nested_canvases: list[weakref.ref[Canvas[object, object]]] = []
        self._areas: dict[int, Placement[object, object]] = {}
        self._is_hidden_until_written = False
        self._layout: CanvasLayout = layout
        self._edges: EdgeBehavior = edges
        self._slots: list[
            tuple[Placement[object, object] | None, _core.Buffer, _core.SizeRule]
        ] = []
        self._is_layout_pending = False
        self._pending_layouts: dict[int, Canvas[object, object]] = {}
        if enclosing is not None:
            self._enclosing = weakref.ref(enclosing)
            self._enclosing_size = (enclosing.width, enclosing.height)
            with enclosing._lock:
                enclosing._nested_canvases.append(
                    weakref.ref(cast('Canvas[object, object]', self))
                )
        self._is_closed = False
        self._is_finalized = False
        self._stop_requested = threading.Event()
        self._failure: BaseException | None = None
        self._is_failure_reported = False
        self._failure_report = ''
        self._moved = 0
        self._carried: dict[str, object] | None = None
        self._cursor_follow: tuple[_core.Buffer, int, int] | None = None
        self._state_namespace: StateNamespace | None = None
        self._state_fields: dict[str, object] = {}
        self._state_store: _core.TerminalStateStore | None = None
        if state is not _UNSET and state is not None:
            self._state_store = _prepare_state(cast('DataclassInstance', state))
            self._state_fields = _state_field_types(cast('DataclassInstance', state))
        self._state_followers: _StateFollowers | None = None
        self._state_subscription: _core.TerminalStateSubscription | None = None
        self._state_hook: _core.Hook | None = None
        self._state_marked: dict[_StateFollower, _core.TerminalStateChange] = {}
        self._internal_revisions: deque[int] = deque(maxlen=16)
        self._namespace_identifiers = itertools.count(1)
        self._active_run_by_thread = threading.local()
        self._images: dict[int, ImageSource] = {}
        # Only placements with a formula or a range need looking at before each frame.
        self._dynamic: dict[int, Placement[DepsT, StateT]] = {}
        self._time = Time(cast('Canvas[object, object]', self))
        self._cursor_view = Cursor(cast('Canvas[object, object]', self))
        self.output = Output(cast('Canvas[object, object]', self))
        self._audio: AudioDevice | None = None
        self._input: Input | None = None
        self._runtime_object: _core.Runtime | None = None
        self._clock: _core.Clock | None = None
        self._cursor: _core.Cursor | None = None
        self._input_state: _core.InputState | None = None
        self._pushed_pointer: tuple[tuple[int, int], object, int] | None = None
        self._size = _core.Size(0, 0)
        self._previous_chain = tuple(
            reference for reference in _active_canvas.get() if reference() is not None
        )
        _active_canvas.set(
            (weakref.ref(cast('Canvas[object, object]', self)), *self._previous_chain)
        )
        self._host: _Host
        columns, rows = _canvas_size(width, height, self._enclosing_size)
        interval_milliseconds = max(1, round(1000.0 / fps))

        def create_runtime() -> _core.Runtime:
            runtime = _core.Runtime.offscreen(
                width=columns,
                height=rows,
                frame_interval_milliseconds=interval_milliseconds,
                clock=_core.Clock.monotonic() if is_realtime else None,
            )
            if title is not None:
                runtime.title = title
            return runtime

        try:
            if is_realtime:
                _ThreadHost(cast('Canvas[object, object]', self), create_runtime)
            else:
                _InlineHost(cast('Canvas[object, object]', self), create_runtime)
        except BaseException:
            _active_canvas.set(self._previous_chain)
            self._finalize()
            raise
        try:
            if effects:
                apply_effects(cast('Canvas[object, object]', self), effects)
        except BaseException:
            self.close(raise_failure=False)
            raise
        self._renderable_effects = RenderableEffectProperties(
            cast('Canvas[object, object]', self)
        )
        self._seal()

    # -- the runtime ---------------------------------------------------------------------

    def _bind(self, runtime: _core.Runtime) -> None:
        """Connect the canvas to a runtime and register everything again. Runs on its loop."""
        self._runtime_object = runtime
        self._clock = runtime.clock
        self._cursor = runtime.cursor
        input_state = runtime.input
        if self._input is not None:
            input_state.estimate_holds(timeout_seconds=_ESTIMATED_HOLD_SECONDS)
        self._input_state = input_state
        if self._is_live:
            from xnano.terminal._screen import warn_if_output_is_not_held_back

            warn_if_output_is_not_held_back(
                requested=self._resolved_gates.get('capture') is True,
                is_held_back=runtime.is_output_captured,
            )
        runtime.mount(self._root, geometry='inherit')
        self._size = runtime.device.size
        if self._host.is_autonomous and self._size_hook is None:
            self._size_hook = self._root.add_hook(self._follow_resize, events=['resize'])
        if self._appearance is not None:
            self._look_is_dirty = False
            self._redraw_look()
            self._look_was_drawn(self)
        if self._state_followers is not None and self._state_store is not None:
            runtime.watch_state(self._state_store)
        for registration in list(self._ledger):
            registration.bind(runtime)
        for handle in self._hook_handles():
            handle._rebind(runtime)
        audio = self._audio
        if audio is not None:
            audio._bind(runtime)
        carried = self._carried
        if carried is not None:
            self._carried = None
            from xnano.terminal._screen import restore_carried

            restore_carried(self, runtime, carried)
        for effect, target in list(self._effects):
            target._buffer.update(effect)

    def _unbind_runtime(self) -> None:
        """Release what belongs to the runtime that is going away. Runs on its loop."""
        runtime = self._runtime
        effects = runtime.effects
        with self._lock:
            running = [
                entry for entry in self._effects if _is_effect_running(effects, entry[0])
            ]
            finished = len(self._effects) - len(running)
            self._effects[:] = running
        for _ in range(finished):
            self._release_frames()
        for registration in list(self._ledger):
            registration.unbind()
        for handle in self._hook_handles():
            handle._unbind()
        if self._audio is not None:
            self._audio._close()
        runtime.unmount(self._root)

    @property
    def _is_live(self) -> bool:
        """Whether the canvas is on the screen, which is when it is a ``Terminal``."""
        from xnano.terminal import Terminal

        return isinstance(self, Terminal)

    @property
    def _active_run(self) -> _HookRun | None:
        """The hook or component run the calling thread is inside, or ``None``."""
        return getattr(self._active_run_by_thread, 'run', None)

    @_active_run.setter
    def _active_run(self, run: _HookRun | None) -> None:
        self._active_run_by_thread.run = run

    def _note_dynamic_read(self) -> None:
        """Record that the component running on this thread read the time, input or audio."""
        run = self._canvas._active_run
        if run is not None and run.is_active and run.thread == threading.get_ident():
            log = getattr(run.handle, 'log', None)
            if isinstance(log, ReadLog):
                log.uses_time = True

    def _forget_runtime(self) -> None:
        """Let go of the runtime, which may only be dropped on its own thread."""
        self._runtime_object = None

    def _detach(self) -> None:
        """Release everything the canvas registered. Runs on the canvas's loop."""
        self._finalize()
        self._cancel_hooks()
        if self._audio is not None:
            self._audio._close()
        self._images.clear()
        self._frame_listeners.clear()
        for registration in self._ledger:
            registration.cancel()
        self._ledger.clear()
        self._frame_registration = None
        if self._size_hook is not None:
            self._size_hook.cancel()
            self._size_hook = None
        if self._state_hook is not None:
            self._state_hook.cancel()
            self._state_hook = None
        if self._state_subscription is not None:
            self._state_subscription.cancel()
            self._state_subscription = None
        self._state_followers = None
        self._state_marked.clear()
        with self._lock:
            placements = list(self._placements)
        for placement in placements:
            placement.remove()

    def _finalize(self) -> None:
        with self._lock:
            if self._is_finalized:
                return
            self._is_finalized = True
            self._is_closed = True
        self._stop_requested.set()
        if self._is_live:
            from xnano.terminal._screen import release_screen

            release_screen()

    @property
    def _runtime(self) -> _core.Runtime:
        """The runtime, which only the canvas's loop may touch."""
        canvas = self._canvas
        runtime = canvas._runtime_object
        if runtime is None:
            canvas._require_open()
            raise TerminalError(
                'The canvas has no runtime at this moment, because it is being moved onto '
                'the screen. Use it again once open() has returned.'
            )
        host = canvas._host
        if not host.is_on_loop():
            host.require_usable()
            raise TerminalError(
                "The runtime belongs to the canvas's own thread, and this is another one. "
                'Declare what you want with the canvas, which hands the work over to it.',
                code='canvas.thread',
            )
        return runtime

    def _hook_handles(self) -> list[HookHandle[DepsT, StateT]]:
        """Every hook on the canvas and on everything written into it."""
        handles = list(self._registrations)
        with self._lock:
            placements = list(self._placements)
            children = list(self._children)
        for placement in placements:
            handles.extend(placement._registrations)
        for child in children:
            handles.extend(cast('list[HookHandle[DepsT, StateT]]', child._registrations))
        return handles

    def _register(
        self,
        factory: Callable[[_core.Runtime], object],
        *,
        due_seconds: float | None = None,
    ) -> _Registration:
        """Register something with the runtime, and remember how, for a later runtime."""
        canvas = self._canvas
        registration = _Registration(factory, due_seconds=due_seconds)
        with canvas._lock:
            canvas._ledger.append(registration)

        def bind() -> None:
            if registration.handle is None and not registration.is_cancelled:
                registration.bind(canvas._runtime)

        try:
            canvas._host.post(bind)
        except BaseException:
            with canvas._lock:
                if registration in canvas._ledger:
                    canvas._ledger.remove(registration)
            raise
        return registration

    def _unregister(self, registration: _Registration) -> None:
        """Cancel a registration and forget it."""
        canvas = self._canvas
        with canvas._lock:
            if registration in canvas._ledger:
                canvas._ledger.remove(registration)
        canvas._host.post(registration.cancel)

    def _follow_resize(self, core_context: _core.CoreContext) -> None:
        """
        Keep the size current on a canvas that runs by itself. Runs on its loop.

        The cells of the canvas are resized now rather than at the next frame, so a hook for
        the resize reads the new size from ``context.region``.
        """
        runtime = self._runtime_object
        if runtime is not None:
            self._size = runtime.device.size
            root = self._root
            root.width = self._size.width
            root.height = self._size.height
            if self._appearance is not None:
                self._redraw_look()

    # -- frames --------------------------------------------------------------------------

    def _demand_frames(self) -> None:
        """Run the canvas's own work before every frame until the demand is released."""
        canvas = self._canvas
        with canvas._lock:
            canvas._frame_demand += 1
            if canvas._frame_demand != 1:
                return
        canvas._frame_registration = canvas._register(
            lambda runtime: runtime.on_frame(canvas._on_loop_frame, target=canvas._root)
        )

    def _release_frames(self) -> None:
        """Release one demand for frames; at none, nothing runs before a frame."""
        canvas = self._canvas
        with canvas._lock:
            canvas._frame_demand = max(0, canvas._frame_demand - 1)
            if canvas._frame_demand:
                return
            registration = canvas._frame_registration
            canvas._frame_registration = None
        if registration is not None:
            canvas._unregister(registration)

    def _on_loop_frame(self, core_context: FrameContext) -> None:
        """Before a frame: follow the size, images and formulas, then the frame functions."""
        if self._host.is_autonomous and self._stop_requested.is_set():
            # The loop was asked to end: nothing is evaluated for the frames that remain.
            return
        runtime = self._runtime
        size = runtime.device.size
        self._size = size
        if self._dirty_looks:
            with self._lock:
                owners = list(self._dirty_looks.values())
            for owner in owners:
                owner._flush_look()
        if self._pending_layouts:
            apply_pending_layouts(cast('Canvas[object, object]', self))
        with self._lock:
            placements = list(self._dynamic.values())
        is_time_dependent = False
        elapsed_seconds = runtime.clock.elapsed_seconds
        for source in list(self._images.values()):
            source.refresh(size, elapsed_seconds)
            if source.animation is not None:
                source.animation.advance(elapsed_seconds)
                is_time_dependent = True
        finished = []
        for placement in placements:
            is_time_dependent |= placement._apply_bindings(runtime)
            if not placement._needs_frames():
                finished.append(id(placement))
        if finished:
            released = 0
            with self._lock:
                for key in finished:
                    placement = self._dynamic.get(key)
                    if placement is not None and not placement._needs_frames():
                        del self._dynamic[key]
                        released += 1
            for _ in range(released):
                self._release_frames()
        if self._effects:
            is_time_dependent |= self._follow_effects(runtime)
        # Taken after the formulas ran: a component whose placement they resized asks for a
        # listener, which must run before this frame is drawn. A function that runs before
        # every frame needs a frame to run before.
        with self._lock:
            listeners = list(self._frame_listeners.values())
        is_time_dependent |= bool(listeners)
        for listener in listeners:
            listener(core_context)
        if is_time_dependent:
            # Something that follows time needs the next frame too.
            runtime.request_frame()

    def _follow_effects(self, runtime: _core.Runtime) -> bool:
        """Forget effects that finished; return whether one finished on this frame."""
        effects = runtime.effects
        with self._lock:
            running = [
                entry for entry in self._effects if _is_effect_running(effects, entry[0])
            ]
            finished = len(self._effects) - len(running)
            self._effects[:] = running
        for _ in range(finished):
            self._release_frames()
        # The frame after an effect ends shows its last state.
        return finished > 0

    def _record_effect(
        self,
        effect: EffectParameters,
        target: Canvas[object, object] | Placement[object, object],
    ) -> None:
        """Remember an effect, so it starts again on the runtime of an opened canvas."""
        canvas = self._canvas
        key = _effect_key(effect)
        if key is None:
            return
        with canvas._lock:
            replaced = [
                entry for entry in canvas._effects if _effect_key(entry[0]) == key
            ]
            canvas._effects[:] = [
                entry for entry in canvas._effects if _effect_key(entry[0]) != key
            ]
            canvas._effects.append((effect, target))
        if not replaced:
            canvas._demand_frames()

    def _on_frame(self, callback: Callable[[Frame], object]) -> Callable[[], None]:
        """
        Call ``callback`` with a [`Frame`][xnano.context.Frame] before every frame.

        Returns:
            A function that stops the calls.
        """
        canvas = self._canvas
        canvas._require_open()
        token = next(canvas._frame_listener_tokens)
        previous: list[float | None] = [None]

        def listener(core_context: FrameContext) -> None:
            elapsed = core_context.elapsed_seconds
            last = previous[0]
            previous[0] = elapsed
            callback(
                Frame(
                    canvas=cast('Canvas[object, object]', canvas),
                    index=canvas._runtime.clock.frame,
                    elapsed_seconds=elapsed,
                    delta_seconds=0.0 if last is None else elapsed - last,
                    area=core_context.area,
                )
            )

        with canvas._lock:
            canvas._frame_listeners[token] = listener
        canvas._demand_frames()
        canvas._request_frame()

        def cancel() -> None:
            with canvas._lock:
                removed = canvas._frame_listeners.pop(token, None)
            if removed is not None:
                canvas._release_frames()

        return cancel

    def _on_update(
        self,
        callback: Callable[[Update], object],
        *,
        fixed_step_seconds: float | None = None,
    ) -> _Registration:
        """
        Call ``callback`` with an [`Update`][xnano.context.Update] for simulation updates.

        On a manual clock the fixed steps that a jump of the clock crossed are run, at most
        100000 in one step and the rest in the steps that follow; on the wall clock a stalled
        loop runs a few at most.
        """
        canvas = self._canvas
        canvas._require_open()

        def hook(core_context: UpdateContext) -> None:
            callback(
                Update(
                    canvas=cast('Canvas[object, object]', canvas),
                    elapsed_seconds=core_context.elapsed_seconds,
                    delta_seconds=core_context.delta_seconds,
                    is_fixed_step=core_context.is_fixed_step,
                )
            )

        def factory(runtime: _core.Runtime) -> _core.Hook:
            is_manual = runtime.clock.source == 'manual'
            return runtime.on_update(
                hook,
                target=canvas._root,
                fixed_step_seconds=fixed_step_seconds,
                maximum_catch_up_steps=_MANUAL_CATCH_UP_STEPS if is_manual else 4,
                overflow='retain' if is_manual else 'drop',
            )

        return canvas._register(factory)

    def _request_frame(self) -> None:
        """Make sure a frame follows a change that does not touch a buffer."""
        canvas = self._canvas
        canvas._host.post(lambda: canvas._runtime.request_frame())

    # -- state ---------------------------------------------------------------------------

    def _ensure_store(self) -> _core.TerminalStateStore:
        """The canvas's state store, which is built the first time something needs it."""
        canvas = self._canvas
        store = canvas._state_store
        if store is None:
            with canvas._lock:
                store = canvas._state_store
                if store is None:
                    store = canvas._state_store = _prepare_state(None)
        return store

    def _create_root_namespace(self) -> StateNamespace:
        """The namespace of the whole state, which ``canvas.state`` returns."""
        canvas = self._canvas
        with canvas._lock:
            namespace = canvas._state_namespace
            if namespace is None:
                canvas._ensure_store()
                namespace = canvas._state_namespace = StateNamespace(
                    cast('Canvas[object, object]', canvas),
                    (),
                    fields=canvas._state_fields,
                )
        return namespace

    def _new_state_namespace(self, kind: str) -> StateNamespace:
        """A namespace of its own for a placement (``'buffers'``) or a hook (``'plugins'``)."""
        canvas = self._canvas
        store = canvas._ensure_store()
        base = ('xnano', kind, str(next(canvas._namespace_identifiers)))
        revision = _create_branch(store, base)
        if revision is not None:
            canvas._internal_revisions.append(revision)
        return StateNamespace(cast('Canvas[object, object]', canvas), base)

    def _remove_state_branch(self, base: tuple[str | int, ...]) -> None:
        """Delete the branch of a namespace whose placement or hook is gone."""
        canvas = self._canvas
        store = canvas._state_store
        if store is None:
            return
        revision = _remove_branch(store, base)
        if revision is not None:
            canvas._internal_revisions.append(revision)

    def _commit_state(
        self, pending: dict[tuple[str | int, ...], JSONValue]
    ) -> _core.TerminalStateChange | None:
        """Save pushed values in one transaction and make sure a frame follows."""
        canvas = self._canvas
        canvas._host.require_usable()
        store = canvas._ensure_store()
        change = _commit_pending(store, pending)
        if change is not None:
            runtime = canvas._runtime_object
            if runtime is not None and canvas._host.is_on_loop():
                runtime.request_frame()
            else:
                canvas._request_frame()
        return change

    def _follow_state(
        self,
        follower: _StateFollower,
        paths: frozenset[tuple[str | int, ...]] | None,
    ) -> None:
        """Run ``follower`` again when a path in ``paths`` changes, or any path when ``None``."""
        canvas = self._canvas
        followers = canvas._state_followers
        if followers is None:
            store = canvas._ensure_store()
            followers = canvas._state_followers = _StateFollowers()
            canvas._state_subscription = store.subscribe([()], canvas._on_state_change)
            canvas._state_hook = canvas._root.add_hook(
                canvas._flush_state, events=['state_change']
            )
            canvas._runtime.watch_state(store)
        followers.follow(follower, paths)

    def _unfollow_state(self, follower: _StateFollower) -> None:
        """Stop running ``follower`` when state changes."""
        canvas = self._canvas
        followers = canvas._state_followers
        if followers is not None:
            followers.unfollow(follower)
        canvas._state_marked.pop(follower, None)

    def _on_state_change(self, change: _core.TerminalStateChange) -> None:
        """Mark the followers a committed change reaches. Runs while the store is drained."""
        followers = self._state_followers
        if followers is None or change.revision in self._internal_revisions:
            return
        revision = change.revision
        for follower in followers.affected(change.paths):
            if revision not in follower._own_revisions:
                self._state_marked[follower] = change

    def _flush_state(self, _: CoreContext) -> None:
        """Run the followers that were marked, then those their commits marked in turn."""
        store = self._state_store
        marked = self._state_marked
        if store is None or not marked:
            return
        runs: dict[_StateFollower, int] = {}
        while marked:
            batch = list(marked.items())
            marked.clear()
            for follower, change in batch:
                count = runs.get(follower, 0) + 1
                runs[follower] = count
                if count > _MAXIMUM_STATE_RERUNS:
                    marked.clear()
                    follower._state_loop(
                        change, [other for other in runs if other is not follower]
                    )
                    return
                follower._state_followed(change)
            store.drain_notifications()

    def _bindings_changed(self, placement: Placement[DepsT, StateT]) -> None:
        """A formula or range was set: look at the placement before each frame."""
        canvas = self._canvas
        with canvas._lock:
            is_new = id(placement) not in canvas._dynamic
            canvas._dynamic[id(placement)] = placement
        if is_new:
            canvas._demand_frames()
        canvas._host.post(lambda: canvas._runtime.request_frame())

    def _stop_runtime(self) -> None:
        self._runtime.stop()

    # -- opening on the screen -----------------------------------------------------------

    def open(
        self,
        *,
        title: str | None = None,
        width: int | Percentage | str | None = None,
        height: int | Percentage | str | None = None,
        **settings: Unpack[OpenSettings],
    ) -> Terminal[DepsT, StateT]:
        """
        Put this canvas on your screen, and return it as a [`Terminal`][xnano.Terminal].

        The same object is returned: after this, ``isinstance(canvas, xnano.Terminal)`` is
        true. From then on it runs by itself on a thread of its own and on the wall clock, which
        continues from the time the canvas had: elapsed time, the frame count, ``every`` and
        ``after`` timers and a stopped clock carry over, and so do the cursor, the title,
        everything written and every hook. Effects that were running start again from their
        beginning, and keyboard focus and a captured pointer are released.

        ``width`` and ``height`` are the size of the canvas: the ones given here, else the
        ones given to ``new()``, draw in a region of that size below the cursor; a canvas
        created without a size, or with ``'100%'`` for both, fills the whole window. A
        percentage such as ``'50%'`` is a share of the window when the canvas is opened. Any
        other keyword of ``new()`` except ``realtime`` may be given and applies before the
        canvas is shown; a terminal setting given here wins over the one given to ``new()``.
        ``title`` is the window title.

        Args:
            title: The window title; ``None`` keeps the canvas's title.
            width: The width of the region to draw in: cells, or a percentage of the window.
            height: The height of the region to draw in: cells, or a percentage of the window.
            settings: Terminal settings, appearance keywords, ``fps``, ``bpm``, ``effects``,
                and ``deps`` and ``state`` for a canvas that was created without them; see
                [`OpenSettings`][xnano.types.OpenSettings].

        Returns:
            This canvas, now attached to the screen.

        Raises:
            TerminalAlreadyOpenError: Another canvas is already on the screen.
            TerminalError: This canvas is already on the screen, was written into another
                canvas, has a hook that needs a terminal setting given as ``False``, or
                there is no terminal to draw on; the canvas stays as it was.
            TypeError: ``realtime`` was given, ``deps`` or ``state`` that the canvas already
                has, or an effect that is not a visual effect dictionary.
            ValueError: A ``width`` was given without a ``height``, or a value is out of
                range.

        Examples:
            ```text
            with xnano.new(width=40, height=5) as canvas:
                canvas.write('hello', border='rounded')
                canvas.step()
                canvas.open(mouse=True)        # now a xnano.Terminal, 40 by 5 below the prompt
                canvas.run(quit_on='q')
            ```
        """
        from xnano.terminal import Terminal
        from xnano.terminal._screen import attach_screen

        attach_screen(self, title=title, width=width, height=height, settings=settings)

        assert isinstance(self, Terminal)
        return self

    def _tell_followers(self, change: _core.TerminalStateChange) -> None:
        """Run what follows state that a new store changed. Runs on the canvas's loop."""
        followers = self._state_followers
        if followers is None:
            return
        for follower in followers.affected(change.paths):
            self._state_marked[follower] = change
        self._flush_state(cast('CoreContext', None))
        self._runtime.request_frame()

    # -- context management and closing --------------------------------------------------

    def __enter__(self) -> Self:
        _enclosing_canvases.set(
            (
                weakref.ref(cast('Canvas[object, object]', self)),
                *_enclosing_canvases.get(),
            )
        )
        return self

    def __exit__(self, exception_type: object, *rest: object) -> None:
        _enclosing_canvases.set(
            tuple(
                reference
                for reference in _enclosing_canvases.get()
                if reference() is not self
            )
        )
        if self._canvas is not self or self._enclosing_canvas_is_running():
            # It stays usable, and ends with the canvas it is part of or was created in.
            if _current_canvas() is self:
                _active_canvas.set(self._previous_chain)
            return
        self.close(raise_failure=exception_type is None)

    def _enclosing_canvas_is_running(self) -> bool:
        """Whether the canvas this one was created in is still running."""
        enclosing = None if self._enclosing is None else self._enclosing()
        return enclosing is not None and enclosing.is_running

    def _is_enclosed_by(self, outer: Canvas[object, object]) -> bool:
        """Whether this canvas was created, directly or through others, in ``outer``'s block."""
        reference = self._enclosing
        while reference is not None:
            enclosing = reference()
            if enclosing is None:
                return False
            if enclosing is outer:
                return True
            reference = enclosing._enclosing
        return False

    def _close_nested_canvases(self) -> None:
        """Close the canvases created in this one's block that were not written anywhere."""
        with self._lock:
            nested = [reference() for reference in self._nested_canvases]
            self._nested_canvases.clear()
        for canvas in nested:
            if canvas is not None and canvas._canvas is canvas:
                canvas.close(raise_failure=False)

    @property
    def is_closed(self) -> bool:
        """Whether the canvas has been torn down: closed, or its loop has ended."""
        return self._is_closed or (self._canvas is not self and self._canvas.is_closed)

    @property
    def is_running(self) -> bool:
        """Whether the canvas is open and its loop has not been asked to end."""
        canvas = self._canvas
        return (
            not self._is_closed
            and not canvas._is_closed
            and not canvas._stop_requested.is_set()
        )

    def _is_inside(self, outer: Canvas[object, object]) -> bool:
        """Whether this canvas was written, directly or through others, into ``outer``."""
        owner: Canvas[object, object] | Placement[object, object] | None = (
            self._parent_placement
        )
        while owner is not None:
            if owner is outer:
                return True
            if isinstance(owner, Placement):
                owner = owner._parent_owner
            else:
                owner = owner._parent_placement
        return False

    def _require_attached(self) -> None:
        """Raise when this canvas can no longer hold a hook."""
        self._require_open()

    def _require_own_presence(self) -> None:
        """Refuse a control call from a canvas written into another one and then closed."""
        if self._is_closed and self._canvas is not self:
            self._require_open()

    def _require_open(self) -> None:
        if self._canvas is not self:
            if self._is_closed:
                raise TerminalClosedError(
                    'This canvas has been closed, so it no longer draws inside the canvas it '
                    'was written into. Write a new one into it.'
                )
            self._canvas._require_open()
            return
        if self._is_closed:
            if self._failure is not None:
                raise TerminalClosedError(
                    f'{self._failure_text(self._failure)} Fix that, then create a new canvas '
                    f'with xnano.new() or xnano.open().'
                ) from self._failure
            raise TerminalClosedError(
                'This canvas has been closed, so it can no longer draw or listen. Create a new '
                'one with xnano.new() or xnano.open(), and do the work inside its "with" block.'
            )

    def close(self, *, raise_failure: bool = True) -> None:
        """
        Release everything the canvas holds, and give the screen back if it has one.

        Closing twice is harmless. Leaving a ``with`` block closes the canvas, unless it is
        part of another canvas or was created inside another canvas's ``with`` block: then it
        stays usable and closes with that canvas. Closing a canvas closes the canvases created
        inside its block that were not written anywhere. Closing a canvas that was written into
        another one takes it off and leaves that one running.

        Args:
            raise_failure: Whether to raise the error a callback raised on the loop, which
                stopped the canvas. A ``with`` block passes ``False`` while another error is
                already propagating.

        Raises:
            TerminalError: A callback raised on the canvas's loop, or the loop would not stop.
        """
        self._close_nested_canvases()
        if self._canvas is not self:
            if not self._is_closed:
                self._is_closed = True
                root = self._canvas
                closing: list[Canvas[object, object]] = [
                    cast('Canvas[object, object]', self)
                ]
                with root._lock:
                    # A canvas written into this one is part of it, so it ends with it.
                    closing.extend(
                        inner
                        for inner in list(root._children)
                        if inner is not self
                        and inner._is_inside(cast('Canvas[object, object]', self))
                    )
                    for canvas in closing:
                        canvas._is_closed = True
                        if canvas in root._children:
                            root._children.remove(canvas)
                placement = self._parent_placement
                if placement is not None and not root.is_closed:
                    for canvas in closing:
                        root._host.post(canvas._cancel_hooks)
                    placement.remove()
            if _current_canvas() is self:
                _active_canvas.set(self._previous_chain)
            return
        if not self._stop_requested.is_set() or not self._is_finalized:
            host = getattr(self, '_host', None)
            if host is not None:
                host.require_closable()
            self._stop_requested.set()
            try:
                if host is not None:
                    host.shutdown()
            finally:
                self._finalize()
        if _current_canvas() is self:
            _active_canvas.set(self._previous_chain)
        failure = self._failure
        if failure is not None and raise_failure and not self._is_failure_reported:
            self._failure = None
            raise TerminalError(
                self._failure_text(failure), code='canvas.callback'
            ) from failure

    def _record_failure(self, error: BaseException) -> None:
        """Keep an error raised on the loop, as text plus the error without its frames."""
        self._failure_report = _release_frames(error)
        self._failure = error

    def _raise_failure(self) -> None:
        """On a canvas whose clock you move, raise the error a hook raised, once it has."""
        failure = self._failure
        if failure is None or self._host.is_autonomous or self._is_failure_reported:
            return
        # The canvas ends with the failure, as one that runs by itself does.
        self._is_failure_reported = True
        self.close(raise_failure=False)
        raise TerminalError(
            self._failure_text(failure), code='canvas.callback'
        ) from failure

    def _failure_text(self, failure: BaseException) -> str:
        text = (
            f'The canvas stopped because {type(failure).__name__} was raised on its '
            f'loop: {str(failure).rstrip(".")}.'
        )
        report = self._failure_report
        return f'{text}\n\n{report}' if report else text

    # -- geometry ------------------------------------------------------------------------

    @property
    def core_buffer(self) -> _core.Buffer:
        """
        The core buffer the canvas draws, as large as the canvas.

        Everything you write is a child of this buffer, and everything drawn directly on the
        canvas is stored in it. A canvas with a border, padding or margin draws them around
        a buffer of its own; this is the buffer inside them.
        """
        self._flush_look()
        return self._content

    @property
    def parent(self) -> ParentExpressionScope:
        """Symbolic expressions for the parent container's ``width``, ``height`` and ``size``."""
        return Parent

    @property
    def root(self) -> RootExpressionScope:
        """Symbolic expressions for the root canvas's ``width``, ``height``, ``size`` and ``time``."""
        return Root

    @property
    def size(self) -> _core.Size:
        """The size of the canvas in cells."""
        canvas = self._canvas
        if canvas is not self:
            return _core.Size(self._root.width, self._root.height)
        if canvas._host.is_autonomous or canvas._runtime_object is None:
            return canvas._size
        return canvas._runtime.device.size

    @property
    def width(self) -> int:
        """The width of the canvas in cells."""
        return self.size.width

    @property
    def height(self) -> int:
        """The height of the canvas in cells."""
        return self.size.height

    @property
    def x(self) -> int:
        """The column of the canvas: ``0``, unless it was written into another canvas."""
        return 0 if self._canvas is self else self._root.x

    @property
    def y(self) -> int:
        """The row of the canvas: ``0``, unless it was written into another canvas."""
        return 0 if self._canvas is self else self._root.y

    def local(self, point: _core.Point) -> _core.Point:
        """
        Convert a cell of the screen into a cell of this canvas.

        Args:
            point: A cell in screen coordinates, such as ``context.mouse.position``.

        Examples:
            ```python
            import xnano
            from xnano_core import Point

            with xnano.new(width=10, height=3) as canvas:
                assert canvas.local(Point(4, 1)) == Point(4, 1)
            ```
        """
        point = check_point(point)
        if self._canvas is self:
            return _core.Point(point.x, point.y)
        bounds = self._root._absolute_bounds
        return _core.Point(point.x - bounds.x, point.y - bounds.y)

    def _written_placement(self) -> Placement[object, object]:
        """Return the placement this canvas is drawn in, or refuse when it has none."""
        placement = self._parent_placement
        if placement is None:
            raise TerminalError(
                'This canvas is not written into another canvas, so it sits at the origin and '
                'cannot be moved. Move a placement instead: placement.move(...), or '
                'canvas.write(..., x=, y=). To move a canvas, create it inside the "with" block '
                'of another canvas, or write it into one with outer.write(canvas).',
                code='canvas.composition',
            )
        self._require_open()
        return placement

    def move(self, x: int = 0, y: int = 0) -> Self:
        """
        Move a canvas that is written into another one by a number of cells along each axis.

        This moves the placement the canvas is drawn in; see
        [`Placement.move`][xnano.placement.Placement.move].

        Args:
            x: Columns to move right; a negative number moves left.
            y: Rows to move down; a negative number moves up.

        Returns:
            The canvas, so calls can chain.

        Raises:
            TerminalError: The canvas is not written into another canvas, so it sits at the
                origin and cannot move.
            TypeError: An amount is not a whole number.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=3) as outer:
                inner = outer.new('box', width=4, height=1)
                inner.move(x=2, y=1)
                assert (inner.x, inner.y) == (2, 1)
                assert outer.render().splitlines()[1] == '  box'
            ```
        """
        self._written_placement().move(x=x, y=y)
        return self

    def up(self, count: int = 1) -> Self:
        """
        Move a written canvas up by ``count`` rows; see [`move`][xnano.canvas.Canvas.move].

        Args:
            count: How many rows to move.

        Raises:
            TerminalError: The canvas is not written into another canvas.
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        self._written_placement().up(count)
        return self

    def down(self, count: int = 1) -> Self:
        """
        Move a written canvas down by ``count`` rows; see [`move`][xnano.canvas.Canvas.move].

        Args:
            count: How many rows to move.

        Raises:
            TerminalError: The canvas is not written into another canvas.
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        self._written_placement().down(count)
        return self

    def left(self, count: int = 1) -> Self:
        """
        Move a written canvas left by ``count`` columns; see [`move`][xnano.canvas.Canvas.move].

        Args:
            count: How many columns to move.

        Raises:
            TerminalError: The canvas is not written into another canvas.
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        self._written_placement().left(count)
        return self

    def right(self, count: int = 1) -> Self:
        """
        Move a written canvas right by ``count`` columns; see [`move`][xnano.canvas.Canvas.move].

        Args:
            count: How many columns to move.

        Raises:
            TerminalError: The canvas is not written into another canvas.
            TypeError: ``count`` is not a whole number.
            ValueError: ``count`` is negative.
        """
        self._written_placement().right(count)
        return self

    # -- settings ------------------------------------------------------------------------

    @property
    def fps(self) -> float:
        """
        The most frames drawn per second, and the rate [`iter`][xnano.canvas.Canvas.iter] aims for.

        Assign a new rate at any time, from a hook as well: the next frame follows it, and a
        canvas from ``new()`` steps by the new length from its next step on. A canvas written
        into another one runs on that canvas's frames, so assigning to it changes the rate of
        the canvas it is written into.

        Raises:
            TypeError: The rate is not a number.
            ValueError: The rate is not above 0.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1, fps=10) as canvas:
                canvas.step()
                canvas.fps = 20
                frame = canvas.step()
                assert round(frame.delta_seconds, 3) == 0.05
            ```
        """
        return self._canvas._fps

    @fps.setter
    def fps(self, value: float) -> None:
        canvas = self._canvas
        canvas._require_open()
        fps = _check_fps(value)
        interval_milliseconds = max(1, round(1000.0 / fps))
        canvas._host.call(
            lambda: setattr(
                canvas._runtime, 'frame_interval_milliseconds', interval_milliseconds
            )
        )
        canvas._fps = fps

    @property
    def bpm(self) -> float:
        """
        Beats per minute: the length of a beat for beat timers, notes and melodies.

        It is 120 unless ``new(bpm=...)`` said otherwise, and it can change while things
        are playing; the change applies from the next beat.

        Raises:
            ValueError: The tempo is not above 0 and at most 600000.
        """
        return self._canvas._bpm

    @bpm.setter
    def bpm(self, value: float) -> None:
        canvas = self._canvas
        canvas._bpm = _check_bpm(value)
        audio = canvas._audio
        if audio is not None:
            canvas._host.post(audio._apply_tempo)

    @property
    def deps(self) -> DepsT:
        """The dependencies given to ``new(deps=...)``, or ``None``. Hooks read them."""
        return cast('DepsT', self._canvas._deps)

    @property
    def title(self) -> str | None:
        """
        The window title last set on this canvas.

        Assign a single line of printable text to set the title of the window a canvas on the
        screen draws in, or ``None`` to clear it. A canvas without a screen keeps the value
        and shows it when it is opened.
        """
        canvas = self._canvas
        canvas._require_open()
        return canvas._host.call(lambda: canvas._runtime.title)

    @title.setter
    def title(self, value: str | None) -> None:
        canvas = self._canvas
        canvas._require_open()
        _check_title(value)
        canvas._host.call(lambda: setattr(canvas._runtime, 'title', value))
        canvas._title = value

    @property
    def time(self) -> Time:
        """The canvas's [`Time`][xnano.time.Time]: how long it has run, stopping, and formulas."""
        self._require_own_presence()
        self._note_dynamic_read()
        return self._canvas._time

    @property
    def cursor(self) -> Cursor:
        """
        The canvas's [`Cursor`][xnano.cursor.Cursor].

        A canvas has exactly one cursor. Set its ``position`` (a cell, or ``None`` to hide
        it), ``shape``, ``is_blinking`` and ``is_visible``, move it with ``up``, ``down``,
        ``left``, ``right`` and ``move``, or ``follow`` a placement. It can be changed from
        any thread, and on the screen the cursor you had before is restored when the canvas
        closes.

        Examples:
            ```python
            import xnano

            with xnano.new(width=10, height=2) as canvas:
                canvas.cursor.position = (3, 0)
                canvas.cursor.shape = 'bar'
                assert canvas.cursor.position.x == 3
            ```
        """
        self._require_own_presence()
        canvas = self._canvas
        canvas._require_open()
        return canvas._cursor_view

    @property
    def _cursor_source(self) -> _core.Cursor:
        canvas = self._canvas
        canvas._require_open()
        if canvas._cursor is None:
            return canvas._runtime.cursor
        return canvas._cursor

    @property
    def _time_source(self) -> _core.Clock:
        clock = self._canvas._clock
        if clock is None:
            raise TerminalClosedError(
                'The canvas has no time yet, because it is not attached to a running loop.'
            )
        return clock

    @property
    def region(self) -> Region[int]:
        """
        The cells of the canvas as a [`Region`][xnano.region.Region]: read and write
        ``canvas.region[x, y]``.

        The default resolution is one cell. ``canvas.region.half_blocks`` addresses two
        pixels per cell and ``canvas.region.braille`` eight dots.

        Examples:
            ```python
            import xnano

            with xnano.new(width=4, height=2) as canvas:
                canvas.region[0, 0] = xnano.Pixel('diamond')
                canvas.region.half_blocks[1, 0] = (255, 0, 0)
                assert canvas.region[0, 0].character == '◆'
                assert canvas.region.half_blocks.height == 4
            ```
        """
        return Region(self._region_buffer(), owner=cast('Canvas[object, object]', self))

    def _region_buffer(self) -> _core.Buffer:
        """The buffer that ``region`` addresses, drawn up to date."""
        self._require_own_presence()
        self._require_open()
        self._flush_look()
        return self._content

    def _region_cell_size(self) -> tuple[int, int]:
        """The width and height of ``region`` in cells, without making the region."""
        buffer = self._region_buffer()
        return (buffer.width, buffer.height)

    # -- the look ------------------------------------------------------------------------

    @property
    def _content(self) -> _core.Buffer:
        """The buffer that everything written on the canvas is a child of."""
        decorated = self._decorated
        return self._root if decorated is None else decorated.inner

    def _look_canvas(self) -> Canvas[object, object] | None:
        return None if self._is_closed else cast('Canvas[object, object]', self._canvas)

    def _look_size(self) -> tuple[int, int]:
        return (self._root.width, self._root.height)

    def _ensure_look(self) -> Appearance:
        self._require_open()
        return super()._ensure_look()

    def _look_is_dirty_for(self, owner: _Looked) -> None:
        """An owner's look changed: draw it before the next frame."""
        canvas = self._canvas
        with canvas._lock:
            is_new = id(owner) not in canvas._dirty_looks
            canvas._dirty_looks[id(owner)] = owner
        if is_new:
            canvas._demand_frames()
        canvas._request_frame()

    def _look_was_drawn(self, owner: _Looked) -> None:
        """An owner's look was drawn: stop asking for frames on its behalf."""
        canvas = self._canvas
        with canvas._lock:
            was_dirty = canvas._dirty_looks.pop(id(owner), None) is not None
        if was_dirty:
            canvas._release_frames()

    def _redraw_look(self) -> None:
        """Draw the canvas's own colors, border, padding and margin on its cells."""
        look = self._appearance
        if look is None or self._canvas._runtime_object is None:
            return
        root = self._root
        insets = insets_for(look, root.width, root.height)
        has_frame = bool(insets.horizontal or insets.vertical)
        if has_frame:
            if self._decorated is None:
                self._decorated = Decorated.promote(root, copy_cells=True)
            decorated = self._decorated
            decorated.insets = insets
            decorated.fit_inner()
            self._apply_content_colors(look, decorated.inner)
            decorated.repaint(look, insets)
        else:
            if self._decorated is not None:
                width, height = root.width, root.height
                self._decorated.demote(copy_cells=True)
                self._decorated = None
                # The canvas keeps the size it had; only a placement shrinks.
                root.width = width
                root.height = height
            self._apply_content_colors(look, root)
        self._request_frame()

    # -- writing -------------------------------------------------------------------------

    def new(
        self,
        content: Content | None = None,
        /,
        *,
        width: int | Percentage | str | None = None,
        height: int | Percentage | str | None = None,
        effects: Sequence[RenderableEffectSpecification] = (),
        **settings: Unpack[CanvasSettings],
    ) -> Canvas[DepsT, StateT]:
        """
        Create a canvas inside this one and draw it here at once, at the top-left corner.

        This is [`new`][xnano.new] followed by ``canvas.write(child)``: the child's size is
        measured in this canvas (``'50%'`` is half of it, and no size fills it), it runs on
        this canvas's time and hears its input, and it closes with this canvas. Move it with
        [`move`][xnano.canvas.Canvas.move] and its relatives, or create it with
        [`new`][xnano.new] and write it with ``x`` and ``y`` to place it elsewhere.

        Args:
            content: Something to write into the new canvas at once, such as text.
            width: The width in cells, or a percentage of this canvas such as ``'50%'``.
            height: The height in cells, or a percentage of this canvas.
            effects: Effects to apply to the new canvas, as dictionaries with a ``kind`` key.
            settings: The terminal settings and the new canvas's own look; see
                [`CanvasSettings`][xnano.types.CanvasSettings].

        Returns:
            The new [`Canvas`][xnano.canvas.Canvas], already drawn in this one.

        Raises:
            TypeError: An appearance keyword was given with content, or a keyword is unknown.
            ValueError: A size, terminal setting or border kind is out of range.
            TerminalError: This canvas is closed, or a hook of the new canvas needs a
                terminal setting this canvas turned off.

        Examples:
            ```python
            import xnano

            with xnano.new(width=12, height=4) as outer:
                panel = outer.new(height='50%', border='plain')
                assert (panel.width, panel.height) == (12, 2)
                assert outer.render().splitlines()[0] == '┌──────────┐'
            ```
        """
        self._require_open()
        canvas: Canvas[DepsT, StateT] = _create(
            content,
            width=width,
            height=height,
            fps=self.fps,
            bpm=self.bpm,
            effects=effects,
            enclosing=cast('Canvas[object, object]', self),
            **settings,
        )
        try:
            self.write(cast('Canvas[object, object]', canvas))
        except BaseException:
            canvas.close(raise_failure=False)
            raise
        return canvas

    @refuse_unknown_keywords
    def write(
        self,
        content: Content | Canvas[WrittenDepsT, WrittenStateT] | None = None,
        /,
        *,
        x: Axis | None = None,
        y: Axis | None = None,
        width: Axis | None = None,
        height: Axis | None = None,
        layer: int = 0,
        lock: bool = False,
        edges: EdgeBehavior | None = None,
        effects: Sequence[RenderableEffectSpecification] = (),
        style: _core.Style | None = None,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        bold: bool = False,
        dim: bool = False,
        italic: bool = False,
        underline: bool = False,
        blink: bool = False,
        reverse: bool = False,
        hidden: bool = False,
        crossed_out: bool = False,
        title: str | None = None,
        border: _core.BorderKind | bool | None = None,
        border_style: _core.Style | None = None,
        padding: Spacing | None = None,
        margin: Spacing | None = None,
    ) -> Placement[DepsT, StateT]:
        """
        Put something on the canvas: text, a widget, a buffer, another canvas or an image.

        On a canvas that runs by itself it appears at once: this only declares it, and the
        canvas's own loop draws it. Anything you leave out is taken from the content: ``x``
        and ``y`` default to the top-left corner, and ``width`` and ``height`` to the size of
        the content, so ``canvas.write('hello')`` shows five cells of text where it is.
        Change the text later by assigning the placement's
        [`text`][xnano.placement.Placement.text].

        Inside the ``with`` block of a canvas created in this one's block, what is written here
        is placed and clipped within that canvas's area of this one: where it is written, or
        the top-left corner while it is not. Positions such as ``y='center'`` are measured in
        that area, and that canvas's ``edges`` applies there.

        A canvas from [`new`][xnano.new] that is written here becomes part of this one: it
        draws inside the placement, its own clock is set aside and it runs on this canvas's
        time. It may not have been given ``state`` or ``deps``, which belong to the outermost
        canvas. Its audio is not carried over: a musical clock it started and a note it was
        playing stop, and a formula that reads its ``audio.beat`` follows the outer canvas's
        musical clock, which starts at the first beat.

        An image is added as an [`Image`][xnano.Image] (never a file path or a bare
        [`TerminalImage`][xnano_image.TerminalImage]; load one with
        [`load_image`][xnano.load_image]). With neither ``width`` nor ``height`` it keeps
        its own proportions at its own size, shrunk to fit the canvas. With one of them the
        other follows the image's proportions, and with both the image fits inside that box. An
        image sized by a percentage, or by the canvas because you gave no size, is converted
        again when the canvas is resized, unless it is locked. An animated image plays on the
        canvas's clock.

        A box from [`box`][xnano.box] with a relative size (a percentage, a formula or a state
        reference), written with a ``width`` or a ``height``, or written with a look, is drawn
        at the size of its placement, and its look becomes the placement's look, so it is
        drawn again when the canvas is resized. The size given to ``write`` wins over the
        box's own. The look keywords given to ``write`` win over the box's look and the rest
        of the box's look stays, and ``border=False`` leaves out the box's own border, title,
        border style and sides. A box written with a look and no size keeps its own size,
        border included, so the look of the write replaces the look of the box instead of
        surrounding it, and a ``margin`` given to ``write`` surrounds it outside that size,
        a percentage margin being a share of the box. The border of such a box is part of its
        placement, so ``placement.region`` starts inside it. A box written as it is, with no
        size and no look, and any other region, is written as a snapshot of its cells. The
        look given to ``write`` surrounds a region that is not a box, and ``placement.region``
        of a snapshot includes the cells of its border.

        Args:
            content: Text (or a list of lines), a [`Buffer`][xnano_core.Buffer] or widget, a
                canvas from ``new()``, an image, or any
                [`Renderable`][xnano.types.Renderable]; ``None`` for an empty placement.
            x: The column of the left edge: a number of cells, a percentage string, a word
                (``'left'``, ``'center'`` or ``'right'``), an expression, or a range
                (``(0, 20)``) that limits how far it may travel. See
                [`Axis`][xnano.types.Axis].
            y: The row of the top edge, in the same forms (``'top'``, ``'center'``,
                ``'bottom'``).
            width: The width, in the same forms; the content's own width when ``None``.
            height: The height, in the same forms; the content's own height when ``None``.
            layer: Content with a higher layer is drawn over content with a lower one.
            lock: Keep the position and size the content has now, whatever the canvas's
                size does afterwards: percentages, words and formulas are read once.
            edges: What the content does at the edges of its area: ``'clip'``, ``'stop'`` or
                ``'wrap'``; see [`Placement.edges`][xnano.placement.Placement.edges]. Left
                out, it follows what it is written on.
            effects: Effects to start on the placement, as dictionaries with a ``kind``
                key, such as ``[{'kind': 'effect.fade_to', 'foreground': 'red'}]``.
            style: A ready-made [`Style`][xnano.styles.Style] for text. The parameters below
                are applied over it.
            foreground: The text color.
            background: The color behind the text.
            bold: Whether the text is bold.
            dim: Whether the text is dimmed.
            italic: Whether the text is italic.
            underline: Whether the text is underlined.
            blink: Whether the text blinks.
            reverse: Whether foreground and background are swapped.
            hidden: Whether the text is hidden.
            crossed_out: Whether the text is struck through.
            title: A title on the border of a box around the text.
            border: The kind of border for a box around the content, a
                [`BorderKind`][xnano.types.BorderKind] such as ``'plain'``, ``'rounded'``,
                ``'double'`` or ``'thick'``; ``True`` for ``'plain'`` and ``False`` for none.
                Giving a ``title`` alone draws a plain one.
            border_style: The style of the box's border.
            padding: Space between the border and the text: a number of cells, a float or a
                percentage of the text's size, or a dictionary with ``top``, ``right``,
                ``bottom``, ``left``, ``vertical`` and ``horizontal``. Giving it draws the
                text in a box without a border unless ``border`` or ``title`` is also given.
            margin: Space outside the box, in the same forms.

        Returns:
            A [`Placement`][xnano.placement.Placement] to move, resize, listen on or remove.

        Raises:
            TypeError: The content is a file path, raw bytes, or an operation, style or effect
                (apply those with ``canvas.update(...)`` instead).
            TerminalError: The content is a canvas that cannot be written here.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=4) as canvas:
                box = canvas.write('hello', x='50%', y=1)
                assert box.x == 10
                assert (box.width, box.height) == (5, 1)
                canvas.write(
                    'Ready',
                    x='center',
                    y='bottom',
                    foreground='green',
                    bold=True,
                    border='rounded',
                    title='Status',
                )
            ```
        """
        self._require_open()
        if isinstance(content, Region):
            content._require_drawable('canvas.write()')
            width, height = content._written_size(width, height)
        if edges is not None:
            edges = check_edges(edges)
        area = self._area_for_write(content)
        if area is not None:
            return area.write(  # type: ignore[return-value]
                content,
                x=x,
                y=y,
                width=width,
                height=height,
                layer=layer,
                lock=lock,
                edges=edges,
                effects=effects,
                style=style,
                foreground=foreground,
                background=background,
                bold=bold,
                dim=dim,
                italic=italic,
                underline=underline,
                blink=blink,
                reverse=reverse,
                hidden=hidden,
                crossed_out=crossed_out,
                title=title,
                border=border,
                border_style=border_style,
                padding=padding,
                margin=margin,
            )
        parent_buffer = self._content
        slot: _core.Buffer | None = None
        if self._layout != 'overlay':
            slot, width, height = open_slot(
                cast('Canvas[object, object]', self),
                content if isinstance(content, Canvas) else None,
                width,
                height,
            )
            parent_buffer = slot
        try:
            placement = self._canvas._place_on(
                parent_buffer,
                content,
                parent_owner=cast('Canvas[object, object]', self),
                x=x,
                y=y,
                width=width,
                height=height,
                layer=layer,
                lock=lock,
                style=style,
                foreground=foreground,
                background=background,
                bold=bold,
                dim=dim,
                italic=italic,
                underline=underline,
                blink=blink,
                reverse=reverse,
                hidden=hidden,
                crossed_out=crossed_out,
                title=title,
                border=border,
                border_style=border_style,
                padding=padding,
                margin=margin,
            )
        except BaseException:
            if slot is not None:
                close_slot(cast('Canvas[object, object]', self), slot)
            raise
        if slot is not None:
            self._slots[-1] = (
                cast('Placement[object, object]', placement),
                *self._slots[-1][1:],
            )
        if effects:
            apply_effects(cast('Placement[object, object]', placement), effects)
        placement._take_edges(edges, content)
        return placement

    # -- the layout ----------------------------------------------------------------------

    @property
    def layout(self) -> CanvasLayout:
        """
        How the canvas places what is written on it, chosen when the canvas is created.

        ``'overlay'`` places every piece on its own over the whole canvas. ``'column'``
        stacks the pieces from top to bottom in the order they are written, and ``'row'``
        from left to right. Each piece then takes a slot: one with a size on the stacking
        axis (``height`` in a column, ``width`` in a row, in cells or as a percentage) gets
        exactly that, and the others share what is left equally. Inside its slot a piece is
        positioned as on any canvas, so ``y='center'`` and ``y='50%'`` are measured in the
        slot. Removing a piece gives its slot back. A canvas created inside the ``with``
        block of a stacking canvas takes a slot only once it is written.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=10, layout='column') as terminal:
                terminal.write('top half', y='center')
                panel = terminal.new(height='50%')
                panel.write('bottom half')
                rows = terminal.render().splitlines()
                assert (rows[2], rows[5]) == ('top half', 'bottom half')
            ```
        """
        return self._layout

    @property
    def edges(self) -> EdgeBehavior:
        """
        What content written on the canvas does at the edges of its area, unless given its own.

        ``'clip'`` lets it move past the edge, where it is not drawn; ``'stop'`` holds it
        inside its area when it moves; ``'wrap'`` continues text on the next rows of its
        area. A piece written with ``edges=...`` keeps its own; see
        [`Placement.edges`][xnano.placement.Placement.edges].

        Raises:
            ValueError: The value is not ``'clip'``, ``'stop'`` or ``'wrap'``.
        """
        return self._edges

    @edges.setter
    def edges(self, value: EdgeBehavior) -> None:
        self._require_open()
        self._edges = check_edges(value)
        root = self._canvas
        with root._lock:
            placements = list(root._placements)
        for placement in placements:
            if not placement._removed and placement._edges is None:
                placement._follow_edges()

    def _area_for_write(
        self, content: Content | Canvas[WrittenDepsT, WrittenStateT] | None
    ) -> Placement[object, object] | None:
        """
        The area of this canvas that a write lands in, or ``None`` for all of it.

        Inside the ``with`` block of a canvas created in this one's block, it is that canvas's
        area of this one.
        """
        for reference in _enclosing_canvases.get():
            entered = reference()
            if entered is None or not entered.is_running:
                continue
            if entered is self or entered is content:
                return None
            if not entered._is_enclosed_by(cast('Canvas[object, object]', self)):
                return None
            return entered._area_on(cast('Canvas[object, object]', self))
        return None

    def _area_on(self, outer: Canvas[object, object]) -> Placement[object, object]:
        """The empty placement of ``outer`` that covers this canvas's area of it."""
        area = self._areas.get(id(outer))
        if area is not None and not area._removed and area._parent_owner is outer:
            return area
        placement = self._parent_placement
        slot = None if placement is None else slot_of(outer, placement)
        if slot is not None:
            area = outer._canvas._place_on(
                slot, None, parent_owner=outer, x=0, y=0, width='100%', height='100%'
            )
            area._edges_owner = cast('Canvas[object, object]', self)
            self._areas[id(outer)] = cast('Placement[object, object]', area)
            return cast('Placement[object, object]', area)
        is_written_here = placement is not None and placement._parent_owner is outer
        enclosing = None if self._enclosing is None else self._enclosing()
        if enclosing is outer:
            width: Axis = (
                '100%' if self._requested_width is None else self._requested_width
            )
            height: Axis = (
                '100%' if self._requested_height is None else self._requested_height
            )
        else:
            width, height = self.width, self.height
        area = outer._canvas._place_on(
            outer._content,
            None,
            parent_owner=outer,
            x=self.x if is_written_here else 0,
            y=self.y if is_written_here else 0,
            width=width,
            height=height,
        )
        area._edges_owner = cast('Canvas[object, object]', self)
        self._areas[id(outer)] = cast('Placement[object, object]', area)
        return cast('Placement[object, object]', area)

    def _place_on(
        self,
        parent_buffer: _core.Buffer,
        content: Content | Canvas[WrittenDepsT, WrittenStateT] | None,
        *,
        parent_owner: Canvas[object, object] | Placement[object, object],
        x: Axis | None = None,
        y: Axis | None = None,
        width: Axis | None = None,
        height: Axis | None = None,
        layer: int = 0,
        lock: bool = False,
        style: _core.Style | None = None,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        bold: bool = False,
        dim: bool = False,
        italic: bool = False,
        underline: bool = False,
        blink: bool = False,
        reverse: bool = False,
        hidden: bool = False,
        crossed_out: bool = False,
        title: str | None = None,
        border: _core.BorderKind | bool | None = None,
        border_style: _core.Style | None = None,
        padding: Spacing | None = None,
        margin: Spacing | None = None,
    ) -> Placement[DepsT, StateT]:
        check_layer(layer)
        removes_border = border is False
        if border is True:
            border = 'plain'
        elif border is False:
            border = None
        appearance = Appearance(
            style=style,
            foreground=foreground,
            background=background,
            **appearance_fields(  # type: ignore[arg-type]
                {
                    'bold': bold,
                    'dim': dim,
                    'italic': italic,
                    'underline': underline,
                    'blink': blink,
                    'reverse': reverse,
                    'hidden': hidden,
                    'crossed_out': crossed_out,
                }
            ),
            title=title,
            border=border,
            border_style=border_style,
            padding=padding,
            margin=margin,
        )
        is_decorated = appearance.has_style or appearance.has_frame or margin is not None
        if isinstance(content, (_core.Operation, _core.Style)):
            raise TypeError(
                f'write() takes content to show, and a {type(content).__name__} changes '
                f'something that is already shown instead. Apply it with '
                f'canvas.update(...) or canvas | operation, or with placement.update(...) '
                f'to change one placement.'
            )
        if isinstance(content, Canvas):
            return self._adopt(
                parent_buffer,
                cast('Canvas[object, object]', content),
                parent_owner=parent_owner,
                x=x,
                y=y,
                width=width,
                height=height,
                layer=layer,
                look=appearance if is_decorated else None,
                lock=lock,
            )
        if (
            isinstance(content, Region)
            and content._box_size is not None
            and (
                width is not None or height is not None or is_decorated or removes_border
            )
        ):
            return self._place_box(
                parent_buffer,
                content,
                appearance,
                removes_border=removes_border,
                parent_owner=parent_owner,
                x=x,
                y=y,
                width=width,
                height=height,
                layer=layer,
                lock=lock,
            )
        component = (
            None
            if content is None or isinstance(content, (Region, Pixel, Image))
            else _as_component(content)
        )
        if component is not None:
            # A component is drawn into an empty placement that has the position and the
            # look the caller asked for; its first result then gives the placement its size.
            placement = self._place_on(
                parent_buffer,
                None,
                parent_owner=parent_owner,
                x=x,
                y=y,
                width=width,
                height=height,
                layer=layer,
                style=style,
                foreground=foreground,
                background=background,
                bold=bold,
                dim=dim,
                italic=italic,
                underline=underline,
                blink=blink,
                reverse=reverse,
                hidden=hidden,
                crossed_out=crossed_out,
                title=title,
                border=border,
                border_style=border_style,
                padding=padding,
                margin=margin,
            )
            try:
                _attach_component(
                    cast('Placement[object, object]', placement),
                    component,
                    is_width_given=width is not None,
                    is_height_given=height is not None,
                )
            except BaseException:
                placement.remove()
                raise
            if lock:
                for axis_name in ('x', 'y', 'width', 'height'):
                    placement._set_axis(axis_name, int(getattr(placement, axis_name)))
            return placement
        if content is None:
            content = _core.Buffer()
        picture = content if isinstance(content, Image) else None
        text_appearance: Appearance | None = None
        is_text = picture is None and (
            isinstance(content, str)
            or (
                isinstance(content, (list, tuple))
                and all(isinstance(line, str) for line in content)
            )
        )
        if picture is not None:
            x = picture.x if x is None else x
            y = picture.y if y is None else y
            width = picture.width if width is None else width
            height = picture.height if height is None else height
            layer = picture.layer if layer == 0 else layer
            lock = lock or picture.lock
        else:
            if isinstance(content, Region):
                # A region is written as a snapshot, so changing it later changes nothing
                # on the canvas.
                content = content.copy()
            content, text_appearance = _text_content(content, appearance, is_decorated)
        buffer, source = self._buffer_for(picture or content, width, height)
        content_buffer = buffer
        decorated: Decorated | None = None
        if is_decorated and not is_text and not isinstance(content, Region):
            insets = insets_for(appearance, buffer.width, buffer.height)
            if (insets.horizontal or insets.vertical) and isinstance(
                buffer, _core.Widget
            ):
                # A widget with no size given keeps its own size, but the box around it
                # must still fit in the parent, so the border is not cut off.
                if width is None:
                    available = parent_buffer.width - insets.horizontal
                    if 0 < available < buffer.width:
                        buffer.width = available
                if height is None:
                    available = parent_buffer.height - insets.vertical
                    if 0 < available < buffer.height:
                        buffer.height = available
                insets = insets_for(appearance, buffer.width, buffer.height)
            if insets.horizontal or insets.vertical:
                # Content that is not text keeps its own buffer, inside a buffer that
                # carries the border, padding and margin.
                outer = _core.Buffer(
                    width=buffer.width + insets.horizontal,
                    height=buffer.height + insets.vertical,
                )
                outer.attach(buffer, mode='transparent')
                decorated = Decorated(outer, buffer)
                decorated.insets = insets
                buffer = outer
        buffer.layer = layer
        placement: Placement[DepsT, StateT] = Placement(
            self, buffer, parent_buffer, parent_owner
        )
        placement._decorated = decorated
        with self._lock:
            self._placements.append(placement)
            # Only an image that animates or follows the canvas's size is looked at before
            # a frame, so only that kind holds a demand for frames.
            needs_frames = source is not None and source.needs_frames
            if source is not None and needs_frames:
                self._images[id(content_buffer)] = source
        if needs_frames:
            self._demand_frames()
        placement._is_text = is_text
        if text_appearance is not None:
            placement._appearance = text_appearance
        elif is_decorated:
            # Content that is not text takes the same look: a border, padding and colors.
            placement._appearance = appearance
        # The runtime may draw a frame at any moment, so the buffer stays hidden until its
        # position, size and look are set; it never shows for a frame in the wrong place.
        buffer.is_visible = False
        parent_buffer.attach(buffer, mode='transparent')
        requested: list[tuple[AxisName, Axis | None]] = [
            ('x', x),
            ('y', y),
            ('width', width),
            ('height', height),
        ]
        try:
            for axis, value in requested:
                if value is not None:
                    placement._set_axis(axis, value)
                elif axis in ('x', 'y'):
                    placement._set_axis(axis, 0)
            if source is not None and source.animation is not None:
                self._request_frame()
            if placement._appearance is not None and not is_text:
                placement._look_is_dirty = True
                placement._flush_look()
            if lock:
                for axis_name in ('x', 'y', 'width', 'height'):
                    placement._set_axis(axis_name, int(getattr(placement, axis_name)))
        except BaseException:
            placement.remove()
            raise
        buffer.is_visible = True
        return placement

    def _place_box(
        self,
        parent_buffer: _core.Buffer,
        box: Region[float],
        written_look: Appearance,
        *,
        removes_border: bool,
        parent_owner: Canvas[object, object] | Placement[object, object],
        x: Axis | None,
        y: Axis | None,
        width: Axis | None,
        height: Axis | None,
        layer: int,
        lock: bool,
    ) -> Placement[DepsT, StateT]:
        """
        Place a box at the size it is written with, drawing its look again when that changes.

        The placement takes the look of the box, with the look given to the write laid over
        it, and the cells that were drawn inside the box. With ``removes_border`` the write
        was given ``border=False``, so the border of the box, with its title, border style
        and sides, is left out before the look of the write is laid over it. An axis the
        write leaves without a size takes the size of the box, border included, plus the
        margin the write gives on that axis, so the look of the write replaces the look of
        the box instead of surrounding it, and a margin stays outside the box. A margin
        that is a share is measured against the box and becomes whole cells on such an axis,
        so the box is not measured again against the larger placement.
        """
        box._flush_look()
        box_look = box._appearance
        assert box_look is not None
        box_width, box_height = box._cell_size()
        margin_left, margin_right, margin_top, margin_bottom = resolve_spacing(
            written_look.margin, width=box_width, height=box_height, name='margin'
        )
        written_margin = written_look.margin
        if written_margin is not None:
            margin_edges: dict[str, object] = {}
            if isinstance(written_margin, dict):
                margin_edges.update(written_margin)
            else:
                for edge_name in ('left', 'right', 'top', 'bottom'):
                    margin_edges[edge_name] = written_margin
            if width is None:
                margin_edges['left'] = margin_left
                margin_edges['right'] = margin_right
            if height is None:
                margin_edges['top'] = margin_top
                margin_edges['bottom'] = margin_bottom
            written_look = dataclasses.replace(
                written_look, margin=cast('Spacing', margin_edges)
            )
        if width is None:
            width = box_width + margin_left + margin_right
        if height is None:
            height = box_height + margin_top + margin_bottom
        if removes_border:
            box_look = dataclasses.replace(
                box_look, border=None, title=None, border_style=None, sides={}
            )
        look = box_look.merged_with(written_look)
        inner = box._inner_cells()
        placement = self._place_on(
            parent_buffer,
            None,
            parent_owner=parent_owner,
            x=x,
            y=y,
            width=width,
            height=height,
            layer=layer,
        )
        try:
            placement._is_box = True
            placement._appearance = look
            placement._look_is_dirty = True
            placement._flush_look()
            if inner is not None:
                placement._content.update(_core.Paste(inner, mode='replace'))
                self._request_frame()
            if lock:
                for axis_name in ('x', 'y', 'width', 'height'):
                    placement._set_axis(axis_name, int(getattr(placement, axis_name)))
        except BaseException:
            placement.remove()
            raise
        return placement

    def _adopt(
        self,
        parent_buffer: _core.Buffer,
        child: Canvas[object, object],
        *,
        parent_owner: Canvas[object, object] | Placement[object, object],
        x: Axis | None,
        y: Axis | None,
        width: Axis | None,
        height: Axis | None,
        layer: int,
        look: Appearance | None = None,
        lock: bool = False,
    ) -> Placement[DepsT, StateT]:
        """Make a canvas from ``new()`` part of this one, drawn inside a placement."""
        if child._is_live:
            raise TerminalError(
                'This canvas is on the screen, so it cannot be written into another canvas. '
                'Write a canvas from xnano.new() that was never opened.',
                code='canvas.composition',
            )
        if child.is_closed:
            raise TerminalError(
                'This canvas has been closed, so there is nothing left to write. Create a new '
                'one with xnano.new().',
                code='canvas.closed',
            )
        if child is parent_owner:
            raise TerminalError(
                'A canvas can be written into one other canvas, once, and never into itself. '
                'Create another canvas with xnano.new() for a second copy.',
                code='canvas.composition',
            )
        owner: Canvas[object, object] | Placement[object, object] | None = parent_owner
        while owner is not None:
            if owner is child:
                raise TerminalError(
                    'A canvas cannot be written into a canvas that is part of it. Write the '
                    'inner canvas into the outer one instead.',
                    code='canvas.composition',
                )
            if isinstance(owner, Placement):
                owner = owner._parent_owner
            else:
                owner = owner._parent_placement
        is_showing = child._canvas is not child and child._is_hidden_until_written
        if child._canvas is not child and not is_showing:
            raise TerminalError(
                'A canvas can be written into one other canvas, once, and never into itself. '
                'Create another canvas with xnano.new() for a second copy.',
                code='canvas.composition',
            )
        if is_showing and child._canvas is not self._canvas:
            raise TerminalError(
                'This canvas was created inside the "with" block of another canvas, so it '
                'belongs to that one and can only be shown inside it. Create it outside that '
                '"with" block to write it into another canvas.',
                code='canvas.composition',
            )
        for name in ('state', 'deps'):
            if getattr(child, f'_{name}_given'):
                raise TerminalError(
                    f'This canvas was given {name}, and a canvas written into another one '
                    f'shares the outer canvas instead. Give {name} to the outermost canvas: '
                    f'xnano.new({name}=...) or xnano.open({name}=...).',
                    code='canvas.composition',
                )
        # Everything the caller gave is checked before the child is changed, so a refusal
        # leaves the canvas as it was and it can be written again.
        check_layer(layer)
        requested_axes: list[tuple[AxisName, Axis | None]] = [
            ('x', x),
            ('y', y),
            ('width', width),
            ('height', height),
        ]
        for axis_name, value in requested_axes:
            if value is not None:
                check_axis(value, axis_name)
        if is_showing:
            return self._show_hidden_canvas(
                parent_buffer,
                child,
                parent_owner=parent_owner,
                x=x,
                y=y,
                width=width,
                height=height,
                layer=layer,
                look=look,
                lock=lock,
            )
        from xnano.terminal._settings import check_gates

        handles = child._host.call(child._hook_handles)
        for handle in handles:
            check_gates(self, cast('HookHandle[DepsT, StateT]', handle))
        if child._audio is not None:
            # Formulas that read the beat or the level read the outer canvas's audio device.
            self._canvas.audio  # noqa: B018
        child._host.call(child._unbind_runtime)
        child._host.retire()
        child._forget_runtime()
        root = self._canvas
        with child._lock:
            moved_placements = list(child._placements)
            moved_dynamic = list(child._dynamic.values())
            moved_images = dict(child._images)
            moved_listeners = dict(child._frame_listeners)
            moved_ledger = [
                registration
                for registration in child._ledger
                if registration is not child._frame_registration
            ]
            moved_effects = list(child._effects)
            moved_layouts = dict(child._pending_layouts)
            child._pending_layouts.clear()
            child._placements.clear()
            child._dynamic.clear()
            child._images.clear()
            child._frame_listeners.clear()
            child._ledger.clear()
            child._effects.clear()
            child._frame_registration = None
            child._frame_demand = 0
        if child._size_hook is not None:
            child._size_hook.cancel()
            child._size_hook = None
        child_buffer = child._root
        child_buffer.layer = layer
        placement: Placement[DepsT, StateT] = Placement(
            self, child_buffer, parent_buffer, parent_owner
        )
        with root._lock:
            root._placements.append(placement)
            for moved in moved_placements:
                moved._canvas = cast('Canvas[object, object]', root)
                root._placements.append(cast('Placement[DepsT, StateT]', moved))
            root._images.update(moved_images)
            root._frame_listeners.update(moved_listeners)
            root._ledger.extend(moved_ledger)
            root._effects.extend(moved_effects)
            root._pending_layouts.update(moved_layouts)
            inner_children = list(child._children)
            for inner in inner_children:
                inner._canvas = cast('Canvas[object, object]', root)
                inner._root_canvas = cast('Canvas[object, object]', root)
                inner.output = root.output
            root._children.append(child)
            root._children.extend(inner_children)
            child._children.clear()
        child._canvas = cast('Canvas[object, object]', root)
        child._root_canvas = cast('Canvas[object, object]', root)
        child._parent_placement = cast('Placement[object, object]', placement)
        child.output = root.output
        if _current_canvas() is child:
            _active_canvas.set(child._previous_chain)
        parent_buffer.attach(child_buffer, mode='transparent')
        for _ in range(
            len(moved_images)
            + len(moved_listeners)
            + len(moved_effects)
            + len(moved_layouts)
        ):
            root._demand_frames()
        for moved in moved_dynamic:
            root._bindings_changed(cast('Placement[DepsT, StateT]', moved))

        def bind_on_root() -> None:
            runtime = root._runtime
            for registration in moved_ledger:
                registration.bind(runtime)
            for handle in handles:
                handle._rebind(runtime)
            for effect, target in moved_effects:
                target._buffer.update(effect)

        root._host.post(bind_on_root)
        try:
            self._flush_moved_looks(child, moved_placements)
            self._lay_out_written_canvas(
                placement,
                child,
                x=x,
                y=y,
                width=width,
                height=height,
                look=look,
                lock=lock,
            )
        except BaseException:
            # As with any other content, a write that fails leaves nothing behind.
            placement.remove()
            raise
        return placement

    def _show_hidden_canvas(
        self,
        parent_buffer: _core.Buffer,
        child: Canvas[object, object],
        *,
        parent_owner: Canvas[object, object] | Placement[object, object],
        x: Axis | None,
        y: Axis | None,
        width: Axis | None,
        height: Axis | None,
        layer: int,
        look: Appearance | None,
        lock: bool,
    ) -> Placement[DepsT, StateT]:
        """Show a canvas that was created in a ``with`` block, where it is written now."""
        placement = cast('Placement[DepsT, StateT]', child._parent_placement)
        child_buffer = child._root
        if placement._parent_buffer is not parent_buffer:
            try:
                placement._parent_buffer.detach(child_buffer)
            except ValueError:
                pass
            placement._parent_buffer = parent_buffer
            placement._parent_owner = parent_owner
            parent_buffer.attach(child_buffer, mode='transparent')
        placement._canvas = self
        child_buffer.layer = layer
        try:
            self._lay_out_written_canvas(
                placement,
                child,
                x=x,
                y=y,
                width=width,
                height=height,
                look=look,
                lock=lock,
            )
        except BaseException:
            placement.remove()
            raise
        child._is_hidden_until_written = False
        placement.is_visible = True
        return placement

    def _lay_out_written_canvas(
        self,
        placement: Placement[DepsT, StateT],
        child: Canvas[object, object],
        *,
        x: Axis | None,
        y: Axis | None,
        width: Axis | None,
        height: Axis | None,
        look: Appearance | None,
        lock: bool,
    ) -> None:
        """Give the placement of a written canvas its position, size and look."""
        requested_width = child._requested_width
        requested_height = child._requested_height
        placement._set_axis('x', 0 if x is None else x)
        placement._set_axis('y', 0 if y is None else y)
        placement._set_axis(
            'width',
            width
            if width is not None
            else '100%'
            if requested_width is None
            else requested_width,
        )
        placement._set_axis(
            'height',
            height
            if height is not None
            else '100%'
            if requested_height is None
            else requested_height,
        )
        if look is not None:
            # The colors, border, padding and margin given with the canvas decorate it.
            placement._appearance = look
            placement._look_is_dirty = True
            placement._flush_look()
        if lock:
            for axis_name in ('x', 'y', 'width', 'height'):
                placement._set_axis(axis_name, int(getattr(placement, axis_name)))

    def _flush_moved_looks(
        self,
        child: Canvas[object, object],
        moved_placements: Sequence[Placement[object, object]],
    ) -> None:
        """Register the looks that changed before a canvas was adopted with its new root."""
        child._dirty_looks.clear()
        for owner in (child, *moved_placements):
            if owner._look_is_dirty:
                owner._look_is_dirty = False
                owner._look_changed()

    def _buffer_for(
        self, content: Content, width: Axis | None, height: Axis | None
    ) -> tuple[_core.Buffer, ImageSource | None]:
        """Build the buffer that shows ``content``, and the image source that keeps it."""
        if isinstance(content, Image):
            source = ImageSource.create(
                content,
                width=width,
                height=height,
                size=self.size,
                elapsed_seconds=self.time.elapsed,
            )
            return source.buffer, source
        try:
            buffer, _ = content_buffer(content)
        except ValueError as error:
            too_large = re.search(r'a buffer cannot be (\d+) x (\d+)', str(error))
            if too_large is None:
                raise
            raise ValueError(
                f'write() shows content of at most {MOST_CELLS} by {MOST_CELLS} cells, but '
                f'this content is {too_large[1]} by {too_large[2]}. Pass shorter lines or '
                f'fewer of them, or split the content across several writes.'
            ) from None
        return buffer, None

    def _release(self, placement: Placement[DepsT, StateT]) -> None:
        owner = placement._parent_owner
        if isinstance(owner, Canvas) and owner._slots and not owner._is_closed:
            slot = slot_of(owner, cast('Placement[object, object]', placement))
            if slot is not None:
                close_slot(owner, slot)
        canvas = self._canvas
        buffer = placement._buffer
        with canvas._lock:
            if placement in canvas._placements:
                canvas._placements.remove(placement)
            was_dynamic = canvas._dynamic.pop(id(placement), None) is not None
            had_image = (
                canvas._images.pop(id(placement._content), None) is not None
                or canvas._images.pop(id(buffer), None) is not None
            )
            effects_before = len(canvas._effects)
            canvas._effects[:] = [
                entry for entry in canvas._effects if entry[1] is not placement
            ]
            dropped_effects = effects_before - len(canvas._effects)
        for _ in range(int(was_dynamic) + int(had_image) + dropped_effects):
            canvas._release_frames()
        try:
            canvas._root.detach(buffer)
        except ValueError:
            pass

    def clear(self) -> None:
        """Erase everything written or drawn directly on the canvas's cells."""
        self._require_open()
        self._flush_look()
        self._content.update(_core.Fill(' '))

    def update(self, *operations: _core.Operation | _core.Style) -> Self:
        """
        Change the canvas's own cells with operations, styles or effects.

        ``canvas | operation`` does the same. To put content on the canvas, use
        [`write`][xnano.canvas.Canvas.write] instead.

        Args:
            operations: What to apply, in order: a core operation such as ``Fill`` or
                ``Write``, a style, or an xnano effect or dynamic operation.

        Returns:
            The canvas, so calls chain.

        Examples:
            ```python
            import xnano
            from xnano_core import Fill

            with xnano.new(width=4, height=1) as canvas:
                canvas.update(Fill('.'))
                assert canvas.render() == '....'
                canvas | Fill('#')
                assert canvas.render() == '####'
            ```
        """
        self._require_open()
        for item in operations:
            if isinstance(item, ContextualOperation):
                cast('ContextualOperation[DepsT, StateT]', item).apply_to(self)
            elif isinstance(item, DynamicOperation):
                item.apply_to(cast('Canvas[object, object]', self))
            elif isinstance(item, _core.Style):
                self._content.update(_core.ApplyStyle(item))
            else:
                self._content.update(item)
        return self

    def __or__(
        self,
        other: _core.Operation | _core.Style | Sequence[_core.Operation],
    ) -> Self:
        """Apply an operation, effect or style with ``canvas | operation``."""
        if isinstance(other, (_core.Operation, _core.Style)):
            self.update(other)
        else:
            self.update(*other)
        return self

    def __ior__(
        self,
        other: _core.Operation | _core.Style | Sequence[_core.Operation],
    ) -> Self:
        """Apply an operation, effect or style in place with ``canvas |= operation``."""
        return self.__or__(other)

    def inspect(self, expression: _core.Expression[ValueT]) -> ValueT:
        """
        Evaluate an expression against the canvas and return its value.

        Args:
            expression: Any expression, such as ``Width``, ``TimeElapsed % 1`` or
                ``canvas.audio.level``.

        Examples:
            ```python
            import xnano
            from xnano_core import Width

            with xnano.new(width=12, height=2) as canvas:
                assert canvas.inspect(Width) == 12
            ```
        """
        self._require_open()
        return self._canvas._host.call(lambda: self._root.inspect(expression))

    # -- time ----------------------------------------------------------------------------

    def _default_milliseconds(self) -> int:
        """The next default step of a manual clock, so that steps never drift from ``fps``."""
        interval = 1000.0 / self._fps
        moved = self._moved
        return round((moved + 1) * interval) - round(moved * interval)

    def _frame_now(self, delta_seconds: float) -> Frame:
        clock = self._time_source
        size = self.size
        return Frame(
            canvas=cast('Canvas[object, object]', self),
            index=clock.frame,
            elapsed_seconds=clock.elapsed_seconds,
            delta_seconds=delta_seconds,
            area=_core.Rectangle(0, 0, size.width, size.height),
        )

    def iter(
        self, *, count: int | None = None, seconds: float | None = None
    ) -> Iterator[Frame]:
        """
        Iterate over the canvas's frames, drawing between them; pass ``count=`` or ``seconds=``,
        or break out of the loop.

        Each iteration yields a [`Frame`][xnano.context.Frame], and whatever you change
        before asking for the next one is drawn. On a canvas from ``new()`` each iteration
        moves the clock by one frame of its ``fps``, so the same loop produces the same
        frames every run; without ``count`` or ``seconds`` it runs as fast as your code. A
        canvas that runs by itself draws as you declare, so there this only paces your code
        at its ``fps``: if you are slow, frames are skipped rather than queued.

        [`stop`][xnano.canvas.Canvas.stop] freezes the time ``iter()`` follows: the
        iterations go on drawing and hooks still run, but the clock stands still until
        [`resume`][xnano.canvas.Canvas.resume]. To move a stopped canvas one frame, call
        [`step`][xnano.canvas.Canvas.step].

        The iteration ends when ``count`` frames have been yielded, when the canvas's time has
        run for ``seconds`` (whichever comes first), when the canvas is asked to
        [`quit`][xnano.canvas.Canvas.quit] or closed, or when you break out of the loop.

        Args:
            count: The most frames to yield.
            seconds: The most seconds of the canvas's time to run for.

        Raises:
            TerminalError: ``seconds`` without ``count`` on a stopped canvas, which would
                never reach the end.
            TerminalClosedError: The canvas is closed.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1, fps=10) as canvas:
                frames = list(canvas.iter(count=3))
            assert [frame.elapsed_seconds for frame in frames] == [0.0, 0.1, 0.2]
            ```
        """
        self._require_own_presence()
        canvas = self._canvas
        canvas._require_open()
        if count is not None and (
            isinstance(count, bool) or not isinstance(count, int) or count < 0
        ):
            raise ValueError(
                f'count must be a whole number of frames, 0 or more, but was {count!r}.'
            )
        if seconds is not None and (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or not seconds > 0
        ):
            raise ValueError(
                f'seconds must be a number above zero, but was {seconds!r}. Pass count= to '
                f'stop after a number of frames instead.'
            )
        if seconds is not None and count is None:
            canvas._refuse_endless_seconds(seconds)
        return canvas._frames(count, seconds)

    def _refuse_endless_seconds(self, seconds: float) -> None:
        if self._time_source.is_stopped:
            raise TerminalError(
                f'A stopped canvas never reaches seconds={seconds:g}, because its time stands '
                f'still. Give count= as well, or call canvas.resume() first.'
            )

    def _frames(self, count: int | None, seconds: float | None) -> Iterator[Frame]:
        self._raise_failure()
        clock = self._time_source
        start = clock.elapsed_seconds
        previous = start
        yielded = 0
        is_autonomous = self._host.is_autonomous
        interval = 1.0 / self._fps
        deadline = wall_clock.monotonic()
        while self.is_running:
            if count is not None and yielded >= count:
                return
            elapsed = clock.elapsed_seconds
            if seconds is not None and elapsed - start >= seconds - 1e-9:
                return
            if seconds is not None and count is None:
                self._refuse_endless_seconds(seconds)
            size = self.size
            yield Frame(
                canvas=cast('Canvas[object, object]', self),
                index=clock.frame,
                elapsed_seconds=elapsed,
                delta_seconds=elapsed - previous,
                area=_core.Rectangle(0, 0, size.width, size.height),
            )
            previous = elapsed
            yielded += 1
            if not self.is_running:
                return
            if is_autonomous:
                now = wall_clock.monotonic()
                deadline += interval
                if deadline < now - interval:
                    deadline = now
                self._stop_requested.wait(max(0.0, deadline - now))
            else:
                runtime = self._runtime
                if not clock.is_stopped:
                    runtime.clock.step(self._default_milliseconds())
                    self._moved += 1
                if self._frame_demand:
                    runtime.request_frame()
                runtime.step()
                self._pushed_pointer = None
                self._raise_failure()

    def step(self, *, delta_seconds: float | None = None) -> Frame:
        """
        Move time by ``delta_seconds``, one frame by default, and draw exactly one frame.

        On a canvas from ``new()`` this always works, and it moves time even while the
        canvas is stopped, which leaves it stopped: it is how a stopped canvas is walked one
        frame at a time. A canvas that runs by itself can be stepped only while it is
        stopped. One frame is ``1 / fps`` seconds; default steps and the frames of
        [`iter`][xnano.canvas.Canvas.iter] share one count, so sixty of them at ``fps=60``
        are exactly one second. A large ``delta_seconds`` is one jump: timers that it crossed
        all run, and so do fixed-step ``every`` hooks, at most 100000 of their steps in one
        step; the steps that remain run in the steps that follow.

        Args:
            delta_seconds: How far to move, in seconds, above zero; one frame when ``None``.

        Returns:
            The [`Frame`][xnano.context.Frame] that was drawn.

        Raises:
            ValueError: ``delta_seconds`` is not above zero.
            TerminalError: The canvas runs by itself and is not stopped.
            TerminalClosedError: The canvas was closed.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1, fps=10) as canvas:
                frame = canvas.step()
                assert frame.elapsed_seconds == 0.1
                canvas.stop()
                canvas.step(delta_seconds=0.5)
                assert canvas.time.elapsed == 0.6
                assert canvas.time.is_stopped
            ```
        """
        self._require_own_presence()
        return self._canvas._step(delta_seconds)

    def _step(self, delta_seconds: float | None) -> Frame:
        self._require_open()
        self._raise_failure()
        milliseconds = 0
        if delta_seconds is not None:
            if (
                isinstance(delta_seconds, bool)
                or not isinstance(delta_seconds, (int, float))
                or not math.isfinite(delta_seconds)
                or delta_seconds <= 0
            ):
                raise ValueError(
                    f'delta_seconds must be a number above zero, but was {delta_seconds!r}. '
                    f'To deliver pushed events and draw without moving time, call '
                    f'canvas.deliver_events().'
                )
            if delta_seconds > _MOST_STEP_SECONDS:
                raise ValueError(
                    f'delta_seconds must be at most {_MOST_STEP_SECONDS:,} seconds, but was '
                    f'{delta_seconds!r}. Step by a smaller amount, or step several times.'
                )
            milliseconds = round(delta_seconds * 1000)
            if milliseconds < 1:
                raise ValueError(
                    f'delta_seconds={delta_seconds!r} is less than a millisecond, the '
                    f'smallest step of a clock. Step by 0.001 or more.'
                )
        if not self._host.is_autonomous:
            if delta_seconds is None:
                milliseconds = self._default_milliseconds()
                self._moved += 1
            runtime = self._runtime
            runtime.clock.step(milliseconds)
            if self._frame_demand:
                runtime.request_frame()
            runtime.step()
            self._pushed_pointer = None
            self._raise_failure()
            return self._frame_now(milliseconds / 1000.0)
        if not self._time_source.is_stopped:
            raise TerminalError(
                'This canvas runs by itself on the wall clock, so it cannot be stepped by '
                'hand. Call canvas.stop() first, then step() moves it one frame at a time; or '
                'use canvas.iter() to follow it.'
            )
        if delta_seconds is None:
            milliseconds = max(1, round(1000.0 / self._fps))
        drawn = threading.Event()

        def step_on_loop() -> None:
            runtime = self._runtime
            runtime.clock.step(milliseconds)
            hook: list[_core.Hook] = []

            def after_frame(core_context: FrameContext) -> None:
                drawn.set()
                if hook:
                    hook[0].cancel()

            hook.append(runtime.on_frame(after_frame, target=self._root))
            runtime.request_frame()

        if self._host.is_on_loop():
            step_on_loop()
        else:
            self._host.call(step_on_loop)
            deadline = wall_clock.monotonic() + 10.0
            while not drawn.wait(0.05):
                if self._is_closed or self._stop_requested.is_set():
                    raise TerminalClosedError(
                        'The canvas was closed while step() waited for its frame. Create a '
                        'new canvas, or stop stepping before you close this one.'
                    )
                if wall_clock.monotonic() >= deadline:
                    raise TerminalError(
                        'The canvas did not draw the stepped frame within 10 seconds. A '
                        'callback that never returns is blocking its loop; keep callbacks '
                        'short.',
                        code='canvas.timeout',
                    )
        return self._frame_now(milliseconds / 1000.0)

    def deliver_events(self) -> None:
        """
        Deliver pushed events to their hooks and draw a frame, without moving time.

        Events pushed with [`push`][xnano.canvas.Canvas.push] reach their hooks at the
        canvas's next step; this is that step on a canvas whose clock you move. A canvas that
        runs by itself delivers them on its own.

        Examples:
            ```python
            import xnano
            from xnano_core import Event

            with xnano.new(width=8, height=1) as canvas:
                heard = []
                canvas.hook(lambda context: heard.append(context.event.kind))
                canvas.push(Event.custom('ping'))
                canvas.deliver_events()
                assert heard == ['custom']
                assert canvas.time.elapsed == 0.0
            ```
        """
        self._require_own_presence()
        canvas = self._canvas
        canvas._require_open()
        if canvas._host.is_autonomous:
            canvas._host.call(lambda: canvas._runtime.request_frame())
            return
        canvas._raise_failure()
        canvas._runtime.step()
        canvas._pushed_pointer = None
        canvas._raise_failure()

    def stop(self) -> None:
        """
        Freeze time: the same as [`Time.stop`][xnano.time.Time.stop].

        The canvas keeps drawing and hooks still hear input, but animations, effects,
        formulas, timers and the beat stand still until [`resume`][xnano.canvas.Canvas.resume].
        [`step`][xnano.canvas.Canvas.step] moves a stopped canvas one frame at a time. To end a
        loop, call [`quit`][xnano.canvas.Canvas.quit].
        """
        self._require_own_presence()
        self._canvas._time.stop()

    def resume(self) -> None:
        """Let time run on from where [`stop`][xnano.canvas.Canvas.stop] froze it."""
        self._require_own_presence()
        self._canvas._time.resume()

    def quit(self) -> None:
        """
        Ask the canvas's loop to end.

        Safe from any thread, including from a hook. A running ``iter()``, ``run()``,
        ``wait_for_key()`` or ``prompt()`` ends. On a canvas from ``new()`` the canvas stays
        open for writing and rendering; on a canvas that runs by itself (``realtime=True``, or
        on the screen) the loop ends and the canvas closes.
        """
        self._require_own_presence()
        canvas = self._canvas
        canvas._stop_requested.set()
        if not canvas._is_closed and canvas._host.is_autonomous:
            canvas._host.post(lambda: canvas._stop_runtime())

    def run(self, *, quit_on: KeyName | Sequence[KeyName] | None = 'ctrl+c') -> None:
        """
        Wait until the canvas's loop ends.

        A canvas that runs by itself draws and listens on its own, so this only keeps your
        program alive until a quit key is pressed, or something calls
        [`quit`][xnano.canvas.Canvas.quit] (a hook, another thread). Declare what you want
        before calling it.

        Args:
            quit_on: The key, or keys, that end the loop, such as ``'q'`` or
                ``('q', 'escape')``. ``'ctrl+c'`` by default; give ``None`` to leave ending
                to your own code.

        Raises:
            TerminalError: A callback raised on the canvas's loop, or the canvas has a clock
                that only moves when you move it, so waiting would never end.
        """
        canvas = self._canvas
        canvas._require_open()
        host = canvas._host
        if not isinstance(host, _ThreadHost):
            raise TerminalError(
                'A canvas with a manual clock never moves by itself, so run() would wait '
                'forever. Drive it with canvas.iter() or canvas.step(), open it on the screen '
                'with canvas.open(), or create it with realtime=True.'
            )
        if quit_on is not None:
            keys = (quit_on,) if isinstance(quit_on, str) else tuple(quit_on)
            if canvas._is_live and canvas._resolved_gates.get('keyboard') is False:
                # With the keyboard off, only the interrupt setting can end the loop on Ctrl-C.
                keys = tuple(key for key in keys if key != 'ctrl+c')
            if keys:

                @canvas.hook(on='key', keys=keys)
                def quit_key(context: Context[DepsT, StateT]) -> None:
                    context.canvas.quit()

        try:
            while not host.wait(0.1):
                pass
        except KeyboardInterrupt:
            canvas.quit()
            raise
        failure = canvas._failure
        if failure is not None:
            canvas._failure = None
            raise TerminalError(
                canvas._failure_text(failure), code='canvas.callback'
            ) from failure

    def wait_for_key(self, *keys: KeyName) -> KeyName:
        """
        Wait until a key is pressed, and return its name.

        Your program waits here while the canvas goes on drawing and animating. It reads
        like ``input()``: nothing else runs on your thread until the key arrives.

        Args:
            keys: The keys to wait for, such as ``'enter'`` or ``'q'``. Give none to take any key.

        Returns:
            The name of the key that was pressed.

        Raises:
            TerminalError: The canvas ended, or has a manual clock, so no key could arrive.

        Examples:
            In a program: ``canvas.wait_for_key()`` after adding "Press any key to start".
            Here a timer plays the part of the person pressing the key:

            ```python
            import xnano
            from xnano.events import Event

            with xnano.new(realtime=True, width=30, height=2) as canvas:
                canvas.write('Press enter to start')

                @canvas.hook(on='tick', after=0.05)
                def press(context: xnano.Context) -> None:
                    canvas.push(Event.key_press('enter'))

                assert canvas.wait_for_key('enter') == 'enter'
            ```
        """
        pressed: list[KeyName] = []
        done = threading.Event()

        @self.hook(on='key', keys=keys or None)
        def hear(context: Context[DepsT, StateT]) -> None:
            key = context.keyboard.key
            if key is not None:
                pressed.append(key)
            context.hook.remove()
            done.set()

        self._wait_until(done, 'a key')
        return pressed[0]

    def prompt(self, text: str, *, x: int = 0, y: int = 0, default: str = '') -> str:
        """
        Prompt for a line of text, and return what was typed.

        The prompt and the answer appear on the canvas while your program waits, like
        ``input()``. ``Enter`` submits and ``Backspace`` deletes.

        Args:
            text: What to ask, such as ``'Your name: '``.
            x: The column of the prompt.
            y: The row of the prompt.
            default: Text already in the answer, which the user can edit.

        Returns:
            What was typed, without the prompt.

        Raises:
            TerminalError: The canvas ended, or has a manual clock, so no answer could arrive.

        Examples:
            In a program: ``name = canvas.prompt('Your name: ')``. Here a timer plays the part
            of the person typing:

            ```python
            import xnano
            from xnano.events import Event

            with xnano.new(realtime=True, width=30, height=2) as canvas:

                @canvas.hook(on='tick', after=0.05)
                def type_answer(context: xnano.Context) -> None:
                    for letter in 'Ada':
                        canvas.push(Event.key_press(letter))
                    canvas.push(Event.key_press('enter'))

                assert canvas.prompt('Your name: ') == 'Ada'
            ```
        """
        answer = [default]
        done = threading.Event()

        shown = self.write(text + default + ' ', x=x, y=y)

        def show() -> None:
            line = text + answer[0]
            shown.text = line + ' '
            self.cursor.position = (x + _core.display_width(line), y)

        cursor = self.cursor
        previous = (cursor.shape, cursor.is_blinking, cursor.is_visible, cursor.position)
        following = cursor._canvas._cursor_follow
        self.cursor.shape = 'bar'
        self.cursor.is_blinking = True
        self.cursor.is_visible = True
        show()

        @self.hook(on='key', when="keyboard.kind != 'release'")
        def edit(context: Context[DepsT, StateT]) -> None:
            key = context.keyboard
            if key.key is None:
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
            cursor.is_visible = False
            cursor.is_blinking = previous[1]
            cursor.shape = previous[0]
            if following is None:
                cursor.position = previous[3]
            else:
                cursor.follow(following[0], x=following[1], y=following[2])
            cursor.is_visible = previous[2]
            shown.remove()
        return answer[0]

    def _wait_until(self, done: threading.Event, what: str) -> None:
        """Block the calling thread until ``done`` is set, or say why that cannot happen."""
        self._require_open()
        if not isinstance(self._canvas._host, _ThreadHost):
            raise TerminalError(
                f'This canvas never moves by itself, so waiting for {what} would last '
                f'forever. Open it on the screen with canvas.open(), or create it with '
                f'realtime=True, or drive it with canvas.step() and read the result from a '
                f'hook instead.'
            )
        while not done.wait(0.1):
            if not self.is_running:
                raise TerminalError(
                    f'The canvas ended while waiting for {what}. Wait before calling '
                    f'canvas.quit() or closing the canvas.'
                )

    # -- input, output, sound and state --------------------------------------------------

    def render(self, *, format: Literal['text', 'ansi'] = 'text') -> str:
        """
        Draw the current frame and return it, without a screen.

        A canvas that was written into another one returns its own cells alone, at its own
        size, as they stand in the outer canvas's current frame.

        Args:
            format: ``'text'`` for the characters alone, ``'ansi'`` for the characters with
                their colors and styles as escape codes.

        Raises:
            ValueError: ``format`` is neither ``'text'`` nor ``'ansi'``.

        Examples:
            ```python
            import xnano

            with xnano.new(width=6, height=2) as canvas:
                canvas.write('hello', y=1)
                assert canvas.render().splitlines() == ['', 'hello']
                assert 'hello' in canvas.render(format='ansi')
            ```
        """
        if format not in ('text', 'ansi'):
            raise ValueError(
                f"format must be 'text' or 'ansi', but was {format!r}. 'text' gives the "
                f"characters, 'ansi' the characters with their colors."
            )
        self._require_own_presence()
        canvas = self._canvas
        canvas._require_open()
        if canvas is not self:
            root_buffer = self._root

            def render_child() -> str:
                canvas._runtime.render()
                return root_buffer.render(format=format)

            return canvas._host.call(render_child)
        snapshot = canvas._host.call(lambda: canvas._runtime.render())
        if format == 'ansi':
            return snapshot.ansi
        return '\n'.join(snapshot.lines())

    def push(self, event: _core.Event) -> None:
        """
        Deliver an event to the canvas as if it had been typed, clicked or reported.

        Hooks hear it the same way as input from the keyboard and mouse, at the canvas's
        next step, whatever the terminal settings say. Build events with
        [`Event`][xnano_core.Event]; ``Event.custom(name, data=...)`` makes one of your own.

        Args:
            event: The event to deliver.

        Raises:
            TypeError: The value is not an [`Event`][xnano_core.Event].

        Examples:
            ```python
            import xnano
            from xnano_core import Event

            with xnano.new(width=8, height=1) as canvas:
                heard = []
                canvas.hook(
                    lambda context: heard.append(context.event.custom_name),
                    when=lambda context: context.event.kind == 'custom',
                )
                canvas.push(Event.custom('volume_changed'))
                canvas.deliver_events()
            assert heard == ['volume_changed']
            ```
        """
        if not isinstance(event, _core.Event):
            raise TypeError(
                f'push() takes an Event such as xnano_core.Event.custom("ping"), but got '
                f'{event!r}. To press a key, push xnano_core.Event.key_press("q"), or call '
                f'context.keyboard.push("q") inside a hook.'
            )
        self._require_own_presence()
        canvas = self._canvas
        canvas._require_open()
        canvas._host.post(lambda: canvas._runtime.inject(event))

    @property
    def audio(self) -> AudioDevice:
        """
        The canvas's [`AudioDevice`][xnano.audio.AudioDevice]: notes, melodies, sounds and the microphone.

        It needs the optional `xnano-audio` package, which is imported the first time this
        is read.

        Raises:
            ImportError: `xnano-audio` is not installed. Install it with
                ``pip install "xnano[audio]"``.
        """
        self._require_own_presence()
        canvas = self._canvas
        canvas._require_open()
        self._note_dynamic_read()
        if canvas._audio is None:
            require('audio', needed_for='Canvas.audio')
            from xnano.audio._player import AudioDevice

            with canvas._lock:
                if canvas._audio is None:
                    audio = AudioDevice(cast('Canvas[object, object]', canvas))
                    canvas._audio = audio
                    canvas._host.post(lambda: audio._bind(canvas._runtime))
        return canvas._audio

    @property
    def fx(self) -> RenderableEffectProperties:
        """
        The visual effects of the canvas itself, one method for each effect.

        ``canvas.fx.fade_to(background='navy')`` starts a fade over the whole canvas at once,
        and ``canvas.fx.clear()`` stops what was started here. A placement has its own
        [`fx`][xnano.placement.Placement.fx], and the sound effects of what the canvas plays are
        [`canvas.audio.fx`][xnano.audio.AudioDevice.fx]. See
        [`RenderableEffectProperties`][xnano.effects.RenderableEffectProperties].

        Examples:
            ```python
            import xnano

            with xnano.new('hello', width=8, height=1) as canvas:
                canvas.fx.dissolve(duration_milliseconds=300)
                assert len(canvas.fx.active) == 1
            ```
        """
        self._require_open()
        return self._renderable_effects

    @property
    def input(self) -> Input:
        """
        The keys held down right now, for programs that poll instead of listening.

        Read it anywhere, from any thread. A canvas opened with
        ``keyboard='release_events'`` knows exactly when a key is let go.
        """
        self._require_own_presence()
        canvas = self._canvas
        canvas._require_open()
        self._note_dynamic_read()
        if canvas._input is None:
            canvas._input = Input(cast('Canvas[object, object]', canvas))
        return canvas._input

    def play(self, playable: PlaySource, /, **options: Unpack[PlayOptions]) -> PlayHandle:
        """
        Play a note, a sound, a symbol name, a melody or a sequence of those, and return at once.

        This is [`audio.play`][xnano.audio.AudioDevice.play]; see it for what ``playable`` may
        be and for every option. On a canvas from ``new()`` the sound is recorded instead of
        played; read it with [`audio.render_sound`][xnano.audio.AudioDevice.render_sound].

        Args:
            playable: What to play: a note, a sound, a symbol name, melody text such as
                ``'C4 E4 G4:2'``, a MIDI number, a frequency, or a sequence of those.
            options: The settings of [`PlayOptions`][xnano.types.PlayOptions], such as
                ``instrument``, ``volume``, ``pan``, ``beats`` and ``at_beat``.

        Returns:
            A [`PlayHandle`][xnano.audio.PlayHandle] that tells when the sound is over.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1, bpm=100) as canvas:
                canvas.play('C4 E4 G4:2 rest C5+E5+G5', instrument='bell')
                canvas.step(delta_seconds=1.0)
                assert canvas.audio.render_sound().duration_milliseconds == 1000.0
            ```
        """
        self._require_own_presence()
        if hasattr(playable, '__xnano_play__') or not isinstance(playable, str):
            handle = _play_component(
                cast('Canvas[object, object]', self._canvas), playable, options
            )
            if handle is not None:
                return handle
        return self.audio.play(playable, **options)

    state = _StateAccessor()
    """
    The canvas's state: values that hooks and your code share, read and written by path.

    ``canvas.state.get('player.score')`` reads a value and ``canvas.state.push('player.score',
    3)`` writes one; see [`StateNamespace`][xnano.state.StateNamespace] for the path rules. A
    canvas created with ``new(state=Settings())`` also gives the fields of the dataclass as
    attributes with their declared types, so ``canvas.state.volume`` is an ``int`` for a field
    declared ``volume: int``; a write is checked against the field's type. A type checker
    sees ``get`` and ``push`` only on a canvas without a state dataclass, but both exist on
    every canvas.

    The state can be used from any thread. A write updates every expression that reads the
    field and draws a frame.
    """

    def state_reference(
        self, reader: Callable[[StateT], ValueT]
    ) -> _core.StateReference[ValueT]:
        """
        A core reference for one field of the canvas's state.

        The reference can be used as an axis, a range bound or a widget parameter.

        Args:
            reader: A function or lambda that reads the field, such as
                ``lambda state: state.volume``.

        Raises:
            TypeError: ``reader`` is not a function.
            TerminalError: The canvas was created without ``state``.
        """
        if not callable(reader):
            raise TypeError(
                f'state_reference() takes a function that reads one field, but got '
                f'{reader!r}. Pass a function such as lambda state: state.volume.'
            )
        store = self._canvas._state_store
        if store is None:
            raise TerminalError(
                'This canvas has no state, so state_reference() has nothing to read. Create it with '
                'xnano.new(state=YourDataclass()).'
            )
        return _reference_for(store, reader)

    def __str__(self) -> str:
        if self.is_closed:
            return ''
        try:
            return self.render()
        except TerminalError:
            return ''

    def __repr__(self) -> str:
        name = type(self).__name__
        if self.is_closed:
            return f'{name}(closed)'
        size = self._size if self._canvas._host.is_autonomous else self.size
        return f'{name}(width={size.width}, height={size.height}, fps={self.fps:g})'


@overload
def new(
    content: Content | Canvas[WrittenDepsT, WrittenStateT] | None = None,
    /,
    *,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float | None = None,
    bpm: float | None = None,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    **settings: Unpack[CanvasSettings],
) -> Canvas[None, None]: ...
@overload
def new(
    content: Content | Canvas[WrittenDepsT, WrittenStateT] | None = None,
    /,
    *,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float | None = None,
    bpm: float | None = None,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> Canvas[None, StateT]: ...
@overload
def new(
    content: Content | Canvas[WrittenDepsT, WrittenStateT] | None = None,
    /,
    *,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float | None = None,
    bpm: float | None = None,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    deps: DepsT,
    **settings: Unpack[CanvasSettings],
) -> Canvas[DepsT, None]: ...
@overload
def new(
    content: Content | Canvas[WrittenDepsT, WrittenStateT] | None = None,
    /,
    *,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float | None = None,
    bpm: float | None = None,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    deps: DepsT,
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> Canvas[DepsT, StateT]: ...
def new(
    content: Content | Canvas[WrittenDepsT, WrittenStateT] | None = None,
    /,
    *,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float | None = None,
    bpm: float | None = None,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    deps: object = _UNSET,
    state: object = _UNSET,
    **settings: object,
) -> Canvas[DepsT, StateT]:
    """
    Create a canvas: a virtual terminal with a clock, hooks, sound, a cursor and state.

    It has no screen and draws into memory. Its clock moves only when you move it, with
    [`step`][xnano.canvas.Canvas.step] or [`iter`][xnano.canvas.Canvas.iter], so every run is
    the same; ``realtime=True`` runs it on the wall clock on a thread of its own instead.
    [`Canvas.open`][xnano.canvas.Canvas.open] (or [`open`][xnano.open]) puts it on the screen.
    A ``with`` block closes it.

    A canvas with a manual clock belongs to the thread that created it: use it, and close it,
    on that thread, for example with a ``with`` block in the worker that made it. A canvas
    that several threads use, or that is closed after its thread has ended, is created with
    ``realtime=True``.

    ``content``, when given, is written at the top-left corner, as ``canvas.write(content)``
    would. The appearance keywords (colors, text modifiers, ``border``, ``border_style``)
    style the canvas itself, not its content, so they are accepted only without content:
    ``new(border='rounded')`` borders the canvas, and ``new().write('hello', border='rounded')``
    borders the text. A canvas's ``foreground`` and ``background`` color the cells no content
    covers. ``padding`` and ``margin`` pad and space the canvas itself. ``title`` is the
    window title.

    Created inside the ``with`` block of another canvas, the new canvas belongs to that one
    from the start but is hidden in it: its size is measured in that canvas (``'50%'`` is
    half of it, and no size fills it), it runs on that canvas's time and its hooks hear that
    canvas's input. ``outer.write(canvas, x=..., y=...)`` shows it, once, where it is
    written. Leaving its own ``with`` block keeps it; it closes with the canvas it belongs
    to. Inside its ``with`` block, ``outer.write(...)`` places content within the new
    canvas's area of ``outer``. It takes that canvas's ``edges`` unless given its own.
    [`Canvas.new`][xnano.canvas.Canvas.new] creates a canvas that is shown at once. A canvas
    given ``state`` or ``deps`` stays on its own, because those belong to the outermost
    canvas: it is measured in the canvas around it, takes its ``fps``, ``bpm`` and ``edges``
    unless given its own, and closes with it.

    The terminal settings (``mouse``, ``scroll``, ``keyboard``, ``paste``, ``focus``,
    ``interrupt``, ``capture``, ``clear``, ``alternate_screen``) are stored and take effect
    when the canvas is opened on the screen; see
    [`TerminalSettings`][xnano.types.TerminalSettings].

    Args:
        content: Something to write into the canvas at once, such as text or a widget.
        width: The width in cells, or a percentage of the window such as ``'50%'``, read
            when the canvas is created; 80 when ``None``. On the screen it is the width of
            the region the canvas draws in, read again when it is opened.
        height: The height in cells, or a percentage of the window such as ``'50%'``; 24
            when ``None``. On the screen it is the height of the region the canvas draws
            in, and ``'100%'`` for both sizes fills the whole window.
        fps: The most frames drawn per second, and the length of one step of ``iter()``;
            the enclosing canvas's, else 60, when ``None``.
        bpm: Beats per minute for beat timers, notes and melodies; the enclosing canvas's,
            else 120, when ``None``.
        realtime: Whether the canvas runs by itself on the wall clock, on a thread of its own.
        title: The window title, shown when the canvas is on the screen.
        effects: Effects to apply to the canvas, as dictionaries with a ``kind`` key.
        deps: Dependencies that hooks read as ``context.deps``; the canvas never reads them.
        state: A dataclass instance the canvas keeps and validates. Hooks read and write it.
        settings: The terminal settings and the canvas's own look; see
            [`CanvasSettings`][xnano.types.CanvasSettings].

    Returns:
        The [`Canvas`][xnano.canvas.Canvas], which is also the one module-level functions such
        as [`active`][xnano.active] find.

    Raises:
        TypeError: An appearance keyword was given with content, or a keyword is unknown.
        ValueError: A size (1 to 65535 cells), ``fps``, ``bpm``, ``realtime``, terminal
            setting or border kind is out of range.

    Examples:
        ```python
        import xnano

        with xnano.new(width=16, height=3) as canvas:
            assert (canvas.width, canvas.height) == (16, 3)
            assert xnano.active() is canvas
            assert not canvas.time.is_realtime

        with xnano.new('hello', width=8, height=1) as greeting:
            assert greeting.render() == 'hello'

        with xnano.new(width=12, height=4) as outer:
            with xnano.new(height='50%') as inner:
                inner.write('inside')
            assert (inner.width, inner.height) == (12, 2)
            assert outer.render().strip() == ''
            outer.write(inner, y=2)
            assert outer.render().splitlines()[2] == 'inside'
            assert xnano.active() is outer
        ```
    """
    enclosing = _enclosing_canvas()
    canvas: Canvas[DepsT, StateT] = _create(
        content,
        width=width,
        height=height,
        fps=fps,
        bpm=bpm,
        realtime=realtime,
        title=title,
        effects=effects,
        deps=deps,
        state=state,
        enclosing=enclosing,
        **settings,
    )
    if enclosing is not None and deps is _UNSET and state is _UNSET:
        try:
            placement = enclosing._canvas._place_on(
                enclosing._content,
                cast('Canvas[object, object]', canvas),
                parent_owner=enclosing,
            )
            placement.is_visible = False
        except BaseException:
            canvas.close(raise_failure=False)
            raise
        canvas._is_hidden_until_written = True
    return canvas


def _create(
    content: Content | Canvas[WrittenDepsT, WrittenStateT] | None = None,
    /,
    *,
    width: int | Percentage | str | None = None,
    height: int | Percentage | str | None = None,
    fps: float | None = None,
    bpm: float | None = None,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    deps: object = _UNSET,
    state: object = _UNSET,
    enclosing: Canvas[object, object] | None = None,
    **settings: object,
) -> Canvas[DepsT, StateT]:
    """Create a canvas as ``new()`` describes, measured in ``enclosing`` when given."""
    from xnano.terminal._settings import appearance_with_content_error, split_settings

    settings = dict(settings)
    layout = check_layout(settings.pop('layout', 'overlay'))
    edges = check_edges(
        settings.pop('edges', 'clip' if enclosing is None else enclosing.edges)
    )
    gates, appearance = split_settings('new', settings)
    if content is not None and appearance:
        raise appearance_with_content_error('new', appearance)
    if fps is None:
        fps = 60.0 if enclosing is None else enclosing.fps
    if bpm is None:
        bpm = 120.0 if enclosing is None else enclosing.bpm
    canvas: Canvas[DepsT, StateT] = Canvas(
        width=_check_size('width', width),
        height=_check_size('height', height),
        fps=_check_fps(fps),
        bpm=_check_bpm(bpm),
        is_realtime=_check_realtime(realtime),
        deps=deps,
        state=state,
        title=_check_title(title),
        gates=gates,
        appearance=appearance,
        effects=effects,
        enclosing=enclosing,
        layout=layout,
        edges=edges,
    )
    if content is not None:
        try:
            canvas.write(content)
        except BaseException:
            canvas.close(raise_failure=False)
            raise
    return canvas


def _check_realtime(value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError(
            f'realtime must be True or False, but was {value!r}. Pass realtime=True to run '
            f'the canvas on the wall clock, or leave it out to move the clock yourself with '
            f'step() or iter().'
        )
    return value


@overload
def active() -> Canvas[object, object]: ...
@overload
def active(*, is_required: Literal[True]) -> Canvas[object, object]: ...
@overload
def active(*, is_required: Literal[False]) -> Canvas[object, object] | None: ...
def active(*, is_required: bool = True) -> Canvas[object, object] | None:
    """
    Return the innermost canvas that is running in this thread or task.

    A canvas is active from the moment it is created until it ends: the most recently created
    one wins, and a canvas that was asked to [`quit`][xnano.canvas.Canvas.quit] gives way to the
    one created before it. A canvas created inside the ``with`` block of another one belongs
    to that canvas, so the outer canvas stays active. Hooks run on a canvas's loop see that
    canvas.

    Args:
        is_required: Whether to raise when no canvas is running.

    Raises:
        TerminalClosedError: No canvas is running and ``is_required`` is true.

    Examples:
        ```python
        import xnano

        assert xnano.active(is_required=False) is None
        with xnano.new(width=4, height=1) as outer:
            assert xnano.active() is outer
            with xnano.new(width=4, height=1):
                assert xnano.active() is outer
        assert xnano.active(is_required=False) is None
        ```
    """
    canvas = next(
        (
            candidate
            for candidate in _live_canvases()
            if candidate.is_running and candidate._canvas is candidate
        ),
        None,
    )
    if canvas is None and is_required:
        raise TerminalClosedError(
            'No canvas is running. Create one with "with xnano.new() as canvas:" or '
            '"with xnano.open() as terminal:", and call this inside the block.'
        )
    return canvas


def iter(*, count: int | None = None, seconds: float | None = None) -> Iterator[Frame]:
    """
    Iterate over the frames of the active canvas, drawing between them.

    This is [`Canvas.iter`][xnano.canvas.Canvas.iter] for the innermost running canvas, so a
    loop does not need the canvas in hand.

    Args:
        count: The most frames to yield.
        seconds: The most seconds of the canvas's time to run for.

    Raises:
        TerminalClosedError: No canvas is running.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            ball = canvas.write('o')
            for frame in xnano.iter(count=3):
                ball.x = frame.index
            assert ball.x == 2
        ```
    """
    return active().iter(count=count, seconds=seconds)
