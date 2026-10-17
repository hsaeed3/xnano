"""
xnano.canvas

The canvas: a virtual terminal of cells with a clock, hooks, sound, a cursor and state.
"""

from __future__ import annotations

import contextvars
import difflib
import itertools
import math
import threading
import time as wall_clock
from collections import deque
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Final,
    Generic,
    Literal,
    NoReturn,
    cast,
    overload,
)

import xnano_core as _core
from xnano_core import CoreContext, FrameContext, JSONValue, UpdateContext

if TYPE_CHECKING:
    from _typeshed import DataclassInstance
    from typing_extensions import Self, TypeIs, Unpack

    from xnano.audio import AudioDevice, PlaySource
    from xnano.context import Context
    from xnano.music import PlayHandle
    from xnano.terminal import Terminal
    from xnano.types import (
        CanvasSettings,
        OpenSettings,
        PlayOptions,
        RenderableEffectSpecification,
    )

from xnano._appearance import APPEARANCE_NAMES, Appearance, Spacing
from xnano._customize import Customization, apply_effects
from xnano._decoration import Decorated, insets_for
from xnano._hooks import HookHandle, _Hooked
from xnano._host import _Host, _InlineHost, _Registration, _ThreadHost
from xnano._media import Image, ImageSource, content_buffer
from xnano._optional import require
from xnano._values import (
    RGB,
    Axis,
    AxisName,
    ColorValue,
    Content,
    DepsT,
    StateT,
    ValueT,
)
from xnano.appearance import _Looked
from xnano.components import as_component, attach_component, play_component
from xnano.context import Frame, Update
from xnano.cursor import Cursor
from xnano.errors import (
    TerminalClosedError,
    TerminalError,
    release_frames,
)
from xnano.expressions import (
    Parent,
    ParentExpressionScope,
    Root,
    RootExpressionScope,
)
from xnano.input import _ESTIMATED_HOLD_SECONDS, Input
from xnano.operations import (
    ContextualOperation,
)
from xnano.output import Output
from xnano.pixel import Pixel
from xnano.placement import Placement
from xnano.region import Region
from xnano.state import (
    StateFollower,
    StateNamespace,
    _HookRun,
    _StateAccessor,
    _StateFollowers,
    commit_pending,
    create_branch,
    prepare_state,
    reference_for,
    remove_branch,
    state_field_names,
)
from xnano.time import Time

__all__ = ['Canvas', 'active', 'iter', 'new']

_active_canvas: contextvars.ContextVar[Canvas[object, object] | None] = (
    contextvars.ContextVar('xnano.active_canvas', default=None)
)
"""The canvas that module-level functions act on, per thread and per async task."""


class _Unset:
    """The value of ``deps`` and ``state`` when they were not given at all."""

    def __repr__(self) -> str:
        return 'unset'


_UNSET: Final = _Unset()

_GATE_NAMES: Final = frozenset(
    {
        'mouse',
        'scroll',
        'keyboard',
        'paste',
        'focus',
        'interrupt',
        'capture',
        'clear',
        'alternate_screen',
    }
)
"""The input gates ``new()`` and ``open()`` accept."""

_GATE_DEFAULTS: Final[Mapping[str, object]] = {
    'mouse': False,
    'scroll': False,
    'keyboard': True,
    'paste': True,
    'focus': True,
    'interrupt': True,
    'capture': True,
    'clear': True,
    'alternate_screen': True,
}

# Gates that a hook registered before the canvas is opened turns on, unless the caller gave
# them as False.
_INFERRED_GATES: Final = ('mouse', 'scroll', 'paste')

_CANVAS_APPEARANCE_NAMES: Final = APPEARANCE_NAMES - {'title'}
"""The appearance keywords of ``new()`` and ``open()``: ``title`` is the window title there."""

# A manual clock can jump far in one step, and every fixed step it crossed is run.
_MANUAL_CATCH_UP_STEPS: Final = 1 << 30
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
    """The appearance keywords with ``border=False`` and ``border=True`` read as kinds."""
    plain = dict(appearance)
    if plain.get('border') is True:
        plain['border'] = 'plain'
    elif plain.get('border') is False:
        plain['border'] = None
    return plain


def _effect_key(customization: Customization) -> str | None:
    """The key a running effect is found by, or ``None`` for a customization that is not one."""
    key = getattr(customization, 'key', None)
    return key if isinstance(key, str) else None


def _is_effect_running(
    effects: _core.EffectManager, customization: Customization
) -> bool:
    key = _effect_key(customization)
    return key is not None and bool(effects.is_running(key))


def _check_fps(fps: object) -> float:
    if (
        isinstance(fps, bool)
        or not isinstance(fps, (int, float))
        or not math.isfinite(fps)
        or fps <= 0
    ):
        raise ValueError(
            f'fps must be a number above zero, but was {fps!r}. Use 30 or 60 for smooth '
            f'motion.'
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


def _check_size(name: str, value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(
            f'{name} must be a whole number of cells, 1 or more, but was {value!r}. Pass '
            f'{name}=40, or leave it out.'
        )
    return value


def _validate_gate_values(gates: Mapping[str, object]) -> None:
    """
    Check the values of the input gates and say which value is wrong and what is allowed.

    Args:
        gates: The gates that were given, by name.

    Raises:
        ValueError: A gate has a value it does not accept.
    """
    for name, value in gates.items():
        if name == 'mouse':
            if value == 'buttons':
                raise ValueError(
                    "mouse='buttons' is mouse=True: True reports button presses, releases "
                    "and drags. Pass mouse=True, or mouse='motion' to report every movement."
                )
            if value is not True and value is not False and value != 'motion':
                raise ValueError(
                    f"mouse must be True, False or 'motion', but was {value!r}. True reports "
                    f"button presses, releases and drags; 'motion' reports every movement too."
                )
        elif name == 'keyboard':
            if (
                value is not True
                and value is not False
                and value
                not in (
                    'disambiguated',
                    'release_events',
                )
            ):
                raise ValueError(
                    f"keyboard must be True, False, 'disambiguated' or 'release_events', but "
                    f'was {value!r}.'
                )
        elif value is not True and value is not False:
            raise ValueError(
                f'{name} must be True or False, but was {value!r}. Pass {name}=True or '
                f'{name}=False.'
            )


def _split_settings(
    function_name: str, settings: Mapping[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    """
    Split the keyword settings of ``new()`` or ``open()`` into gates and appearance.

    Args:
        function_name: ``'new'`` or ``'open'``, for the error messages.
        settings: The keyword settings that were given.

    Returns:
        The gates and the appearance keywords, each by name.

    Raises:
        TypeError: A keyword is not a gate nor an appearance keyword.
        ValueError: A gate has a value it does not accept.
    """
    gates: dict[str, object] = {}
    appearance: dict[str, object] = {}
    for name, value in settings.items():
        if name in _GATE_NAMES:
            gates[name] = value
        elif name in _CANVAS_APPEARANCE_NAMES:
            appearance[name] = value
        elif name == 'offscreen':
            raise TypeError(
                f'{function_name}() has no offscreen setting. A canvas from xnano.new() is '
                f'off the screen, and xnano.open() puts one on the screen: create the canvas '
                f'with xnano.new(...) and leave out offscreen.'
            )
        else:
            known = sorted(
                _GATE_NAMES
                | _CANVAS_APPEARANCE_NAMES
                | {'width', 'height', 'fps', 'bpm', 'title', 'effects', 'deps', 'state'}
            )
            close = difflib.get_close_matches(name, known, n=2)
            hint = (
                f' Did you mean {" or ".join(repr(item) for item in close)}?'
                if close
                else ''
            )
            raise TypeError(
                f'{function_name}() has no setting called {name!r}.{hint} The settings are '
                f'the input gates ({", ".join(sorted(_GATE_NAMES))}) and the look of the '
                f'canvas ({", ".join(sorted(_CANVAS_APPEARANCE_NAMES))}).'
            )
    _validate_gate_values(gates)
    return gates, appearance


def _appearance_with_content_error(
    function_name: str, appearance: Mapping[str, object]
) -> TypeError:
    names = ', '.join(sorted(appearance))
    first = sorted(appearance)[0]
    return TypeError(
        f'These keywords style the canvas itself, not its content: {names}. Pass them to '
        f'canvas.write(content, {first}=...) to style the content, or call {function_name}() '
        f'without content to style the canvas.'
    )


def _is_gate_on(gate: str, resolved: Mapping[str, object]) -> bool:
    """Whether the input a hook needs reaches the canvas with the gates ``resolved``."""
    if gate == 'keyboard_release':
        return resolved.get('keyboard') == 'release_events'
    value = resolved.get(gate)
    return value is not False and value is not None


def _hook_label(function: object) -> str:
    """Name a hook for a message: ``hook name``, or ``component name`` for a component's."""
    component_name = getattr(function, '_component_name', None)
    if component_name is not None:
        return f'component {component_name}'
    return f'hook {getattr(function, "__name__", "hook")}'


def _gate_message(
    label: str, gate: str, subject: str, resolved: Mapping[str, object]
) -> str:
    """Say which hook or component needs which gate, what the gate is now, and how to turn it on."""
    key = 'keyboard' if gate == 'keyboard_release' else gate
    setting = (
        f'{key}={"release_events"!r}' if gate == 'keyboard_release' else f'{key}=True'
    )
    return (
        f'The {label} needs {setting}, but {subject} has {key}={resolved.get(key)!r}, '
        f'so that input would never arrive. Turn it on when the canvas is created or opened: '
        f'xnano.new({setting}), xnano.open({setting}) or canvas.open({setting}).'
    )


class Canvas(_Hooked[DepsT, StateT], _Looked, Generic[DepsT, StateT]):
    """
    A workspace of text, pixels and sound on a clock, with or without a screen.

    A canvas is a virtual terminal. Create one with [`new`][xnano.new]: it has a size, a clock,
    hooks, a cursor, sound and state, and no screen, so it draws into memory and its time moves
    only when you move it with [`step`][xnano.canvas.Canvas.step] or
    [`iter`][xnano.canvas.Canvas.iter], which makes every run the same. ``new(realtime=True)``
    runs it on the wall clock instead, on a thread of its own. [`open`][xnano.canvas.Canvas.open]
    puts the same object on your screen, where it becomes a [`Terminal`][xnano.Terminal]
    and its time continues from where it was. It is not the drawing widget
    [`xnano.widgets.Canvas`][xnano.widgets.Canvas].

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

    def __init__(
        self,
        *,
        width: int | None,
        height: int | None,
        fps: float,
        bpm: float,
        is_realtime: bool,
        deps: object,
        state: object,
        title: str | None,
        gates: Mapping[str, object],
        appearance: Mapping[str, object],
        effects: Sequence[RenderableEffectSpecification],
    ) -> None:
        """
        Create a canvas. Use [`new`][xnano.new] instead of calling this.

        Args:
            width: The width in cells, or ``None`` for 80.
            height: The height in cells, or ``None`` for 24.
            fps: The most frames drawn per second.
            bpm: Beats per minute.
            is_realtime: Whether the canvas runs on the wall clock, on a thread of its own.
            deps: The dependencies, or the unset marker when none were given.
            state: A dataclass instance the canvas keeps and validates, or the unset marker.
            title: The window title, or ``None``.
            gates: The input gates that were given, by name.
            appearance: The appearance keywords of the canvas itself, by name.
            effects: Effects to apply to the canvas, as dictionaries with a ``kind`` key.
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
        self._is_live = False
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
            tuple[Customization, Canvas[object, object] | Placement[object, object]]
        ] = []
        self._frame_listeners: dict[int, Callable[[FrameContext], None]] = {}
        self._frame_listener_tokens = itertools.count()
        self._frame_demand = 0
        self._frame_registration: _Registration | None = None
        self._size_hook: _core.Hook | None = None
        self._parent_placement: Placement[object, object] | None = None
        self._children: list[Canvas[object, object]] = []
        self._is_closed = False
        self._is_finalized = False
        self._stop_requested = threading.Event()
        self._failure: BaseException | None = None
        self._failure_report = ''
        self._moved = 0
        self._carried: dict[str, object] | None = None
        self._cursor_follow: tuple[_core.Buffer, int, int] | None = None
        self._state_namespace: StateNamespace | None = None
        self._state_fields: frozenset[str] = frozenset()
        self._state_store: _core.TerminalStateStore | None = None
        if state is not _UNSET and state is not None:
            self._state_store = prepare_state(cast('DataclassInstance', state))
            self._state_fields = state_field_names(cast('DataclassInstance', state))
        self._state_followers: _StateFollowers | None = None
        self._state_subscription: _core.TerminalStateSubscription | None = None
        self._state_hook: _core.Hook | None = None
        self._state_marked: dict[StateFollower, _core.TerminalStateChange] = {}
        self._internal_revisions: deque[int] = deque(maxlen=16)
        self._namespace_identifiers = itertools.count(1)
        self._active_run: _HookRun | None = None
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
        self._previous = _active_canvas.get()
        _active_canvas.set(cast('Canvas[object, object]', self))
        self._host: _Host
        columns = 80 if width is None else width
        rows = 24 if height is None else height
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
            _active_canvas.set(self._previous)
            self._finalize()
            raise
        try:
            if effects:
                apply_effects(cast('Canvas[object, object]', self), effects)
        except BaseException:
            self.close(raise_failure=False)
            raise

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
            from xnano.terminal import warn_if_output_is_not_held_back

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
            self._restore_carried(runtime, carried)
        for customization, target in list(self._effects):
            target._buffer.update(customization)

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
            from xnano.terminal import _release_screen

            _release_screen()

    @property
    def _runtime(self) -> _core.Runtime:
        """The runtime, which only the canvas's loop may touch."""
        canvas = self._canvas
        runtime = canvas._runtime_object
        if runtime is None or not canvas._host.is_on_loop():
            raise TerminalError(
                "The runtime belongs to the canvas's own thread, and this is another one. "
                'Declare what you want with the canvas, which hands the work over to it.'
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

        canvas._host.post(bind)
        return registration

    def _unregister(self, registration: _Registration) -> None:
        """Cancel a registration and forget it."""
        canvas = self._canvas
        with canvas._lock:
            if registration in canvas._ledger:
                canvas._ledger.remove(registration)
        canvas._host.post(registration.cancel)

    def _follow_resize(self, core_context: _core.CoreContext) -> None:
        """Keep the size current on a canvas that runs by itself. Runs on its loop."""
        runtime = self._runtime_object
        if runtime is not None:
            self._size = runtime.device.size
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
        runtime = self._runtime
        size = runtime.device.size
        self._size = size
        if self._dirty_looks:
            with self._lock:
                owners = list(self._dirty_looks.values())
            for owner in owners:
                owner._flush_look()
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
            if not placement._bindings and not placement._limits:
                finished.append(id(placement))
        if finished:
            released = 0
            with self._lock:
                for key in finished:
                    placement = self._dynamic.get(key)
                    if (
                        placement is not None
                        and not placement._bindings
                        and not placement._limits
                    ):
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
        customization: Customization,
        target: Canvas[object, object] | Placement[object, object],
    ) -> None:
        """Remember an effect, so it starts again on the runtime of an opened canvas."""
        canvas = self._canvas
        key = _effect_key(customization)
        if key is None:
            return
        with canvas._lock:
            replaced = [
                entry for entry in canvas._effects if _effect_key(entry[0]) == key
            ]
            canvas._effects[:] = [
                entry for entry in canvas._effects if _effect_key(entry[0]) != key
            ]
            canvas._effects.append((customization, target))
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

        On a manual clock every fixed step that a jump of the clock crossed is run; on the
        wall clock a stalled loop runs a few at most.
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
                    store = canvas._state_store = prepare_state(None)
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
        revision = create_branch(store, base)
        if revision is not None:
            canvas._internal_revisions.append(revision)
        return StateNamespace(cast('Canvas[object, object]', canvas), base)

    def _remove_state_branch(self, base: tuple[str | int, ...]) -> None:
        """Delete the branch of a namespace whose placement or hook is gone."""
        canvas = self._canvas
        store = canvas._state_store
        if store is None:
            return
        revision = remove_branch(store, base)
        if revision is not None:
            canvas._internal_revisions.append(revision)

    def _commit_state(
        self, pending: dict[tuple[str | int, ...], JSONValue]
    ) -> _core.TerminalStateChange | None:
        """Save pushed values in one transaction and make sure a frame follows."""
        canvas = self._canvas
        store = canvas._ensure_store()
        change = commit_pending(store, pending)
        if change is not None:
            runtime = canvas._runtime_object
            if runtime is not None and canvas._host.is_on_loop():
                runtime.request_frame()
            else:
                canvas._request_frame()
        return change

    def _follow_state(
        self,
        follower: StateFollower,
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

    def _unfollow_state(self, follower: StateFollower) -> None:
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
        runs: dict[StateFollower, int] = {}
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
        width: int | None = None,
        height: int | None = None,
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
        created without a size fills the whole window. Any other keyword of ``new()`` except
        ``realtime`` may be given and applies before the canvas is shown; a gate given here
        wins over the one given to ``new()``. ``title`` is the window title.

        Args:
            title: The window title; ``None`` keeps the canvas's title.
            width: The width of the region to draw in.
            height: The height of the region to draw in.
            settings: Gates, appearance keywords, ``fps``, ``bpm``, ``effects``, and ``deps``
                and ``state`` for a canvas that was created without them; see
                [`OpenSettings`][xnano.types.OpenSettings].

        Returns:
            This canvas, now attached to the screen.

        Raises:
            TerminalAlreadyOpenError: Another canvas is already on the screen.
            TerminalError: This canvas is already on the screen, was written into another
                canvas, or has a hook that needs a gate given as ``False``.
            TypeError: ``realtime``, ``padding`` or ``margin`` was given, or ``deps`` or
                ``state`` that the canvas already has.
            ValueError: A ``width`` was given without a ``height``.
            RuntimeError: There is no terminal to draw on; the canvas stays as it was.

        Examples:
            ```text
            with xnano.new(width=40, height=5) as canvas:
                canvas.write('hello', border='rounded')
                canvas.step()
                canvas.open(mouse=True)        # now a xnano.Terminal, 40 by 5 below the prompt
                canvas.run(quit_on='q')
            ```
        """
        self._attach_screen(title=title, width=width, height=height, settings=settings)
        from xnano.terminal import Terminal

        assert isinstance(self, Terminal)
        return self

    def _parse_open_settings(self, settings: Mapping[str, object]) -> dict[str, object]:
        """Check the keywords of ``open()`` for this canvas; return the ones to apply."""
        if 'realtime' in settings:
            raise TypeError(
                'open() takes no realtime: a canvas on the screen always runs on the wall '
                'clock. Remove realtime=..., or keep the canvas off the screen with '
                'xnano.new(realtime=True).'
            )
        for name in ('deps', 'state'):
            if name in settings and getattr(self, f'_{name}_given'):
                raise TypeError(
                    f'{name} was already given to xnano.new(), and a canvas keeps the {name} '
                    f'it was created with. Remove {name}= from open().'
                )
        own = {'fps', 'bpm', 'effects', 'deps', 'state'}
        gates, appearance = _split_settings(
            'open', {name: value for name, value in settings.items() if name not in own}
        )
        parsed: dict[str, object] = {
            name: value for name, value in settings.items() if name in own
        }
        if 'fps' in parsed:
            parsed['fps'] = _check_fps(parsed['fps'])
        if 'bpm' in parsed:
            parsed['bpm'] = _check_bpm(parsed['bpm'])
        parsed['gates'] = gates
        parsed['appearance'] = appearance
        return parsed

    def _gates_for_screen(self, gates: Mapping[str, object]) -> dict[str, object]:
        """Every gate's value on the screen, with the inferred ones turned on by hooks."""
        needed: dict[str, list[str]] = {}
        # A hook joins its canvas on the canvas's loop, so the hooks are listed there, after
        # every hook registered before this call has joined.
        for handle in self._host.call(self._hook_handles):
            for gate in handle._needed_gates():
                needed.setdefault(gate, []).append(_hook_label(handle.function))
        resolved = {
            name: gates.get(name, default) for name, default in _GATE_DEFAULTS.items()
        }
        for gate, names in needed.items():
            if gate in gates or gate not in _INFERRED_GATES:
                if not _is_gate_on(gate, resolved):
                    raise TerminalError(
                        _gate_message(names[0], gate, 'this canvas', resolved)
                    )
            elif gate in _INFERRED_GATES:
                resolved[gate] = True
        return resolved

    def _check_gates(self, handle: HookHandle[DepsT, StateT]) -> None:
        """Refuse a hook that a canvas on the screen could never deliver events to."""
        canvas = self._canvas
        if not canvas._is_live:
            return
        for gate in handle._needed_gates():
            if not _is_gate_on(gate, canvas._resolved_gates):
                raise TerminalError(
                    _gate_message(
                        _hook_label(handle.function),
                        gate,
                        'this canvas, which is already on the screen,',
                        canvas._resolved_gates,
                    )
                )

    def _attach_screen(
        self,
        *,
        title: str | None,
        width: int | None,
        height: int | None,
        settings: Mapping[str, object],
    ) -> None:
        """Move the canvas onto a live runtime that draws on the screen."""
        from xnano import terminal as screen

        self._require_open()
        if self._is_live:
            raise TerminalError(
                'This canvas is already on the screen, and a program has one screen. Keep '
                'drawing on it, or create another canvas with xnano.new() to draw off the '
                'screen.'
            )
        if self._canvas is not self:
            raise TerminalError(
                'This canvas was written into another canvas, so it draws inside that one. '
                'Open the outer canvas instead.'
            )
        self._host.require_retirable()
        parsed = self._parse_open_settings(settings)
        width = _check_size('width', width)
        height = _check_size('height', height)
        if width is None and height is None:
            width, height = self._requested_width, self._requested_height
        if width is not None and height is None:
            raise ValueError(
                'A canvas on the screen with a width needs a height too, because it draws in '
                'a region of that size. Add height=..., or remove width.'
            )
        gates = {**self._gates, **cast('dict[str, object]', parsed['gates'])}
        resolved = self._gates_for_screen(gates)
        screen._claim_screen()
        old_host = self._host
        clock = self._time_source
        carried: dict[str, object] = {
            'elapsed_seconds': clock.elapsed_seconds,
            'frame': clock.frame,
            'is_stopped': clock.is_stopped,
        }
        fps = cast('float', parsed.get('fps', self._fps))
        window_title = self._title if title is None else title
        cursor = self._cursor
        if cursor is not None:
            carried['cursor'] = (
                cursor.position,
                cursor.shape,
                cursor.is_blinking,
                cursor.is_visible,
                self._cursor_follow,
            )

        def create_live() -> _core.Runtime:
            continued = _core.Clock.monotonic(
                elapsed_seconds=cast('float', carried['elapsed_seconds']),
                frame=cast('int', carried['frame']),
            )
            if carried['is_stopped']:
                continued.stop()
            return screen._create_live_runtime(
                fps=fps,
                width=width,
                height=height,
                gates=resolved,
                title=window_title,
                clock=continued,
            )

        try:
            new_host = _ThreadHost(
                cast('Canvas[object, object]', self), create_live, defer_bind=True
            )
        except BaseException:
            screen._release_screen()
            raise
        try:
            old_host.call(self._unbind_runtime)
            old_host.retire()
        except BaseException:
            new_host.shutdown()
            screen._release_screen()
            raise
        # The old runtime may only be dropped on the thread that created it, which is this
        # one for a canvas with a manual clock.
        self._forget_runtime()
        self._host = new_host
        self._is_live = True
        self._is_realtime = True
        self._gates = gates
        self._resolved_gates = resolved
        self._carried = carried
        self._title = window_title
        self._fps = fps
        if 'bpm' in parsed:
            self._bpm = cast('float', parsed['bpm'])
        if 'deps' in parsed:
            self._deps = cast('DepsT', parsed['deps'])
            self._deps_given = True
        if 'state' in parsed and parsed['state'] is not None:
            instance = cast('DataclassInstance', parsed['state'])
            earlier = self._state_store
            free = None
            if earlier is not None:
                free = {
                    key: value
                    for key, value in cast(
                        'dict[str, JSONValue]', earlier.snapshot().to_value()
                    ).items()
                    if key != 'xnano'
                }
            self._state_store = prepare_state(instance, free)
            self._state_fields = state_field_names(instance)
            self._state_namespace = None
            self._state_given = True
        appearance = cast('dict[str, object]', parsed['appearance'])
        if appearance:
            look = self._ensure_look()
            for name, value in _plain_appearance(appearance).items():
                setattr(look, name, value)
        try:
            new_host.bind_now()
        except BaseException:
            self._restore_screenless(carried)
            raise
        if parsed.get('effects'):
            apply_effects(
                cast('Canvas[object, object]', self),
                cast('Sequence[RenderableEffectSpecification]', parsed['effects']),
            )
        from xnano.terminal import Terminal

        object.__setattr__(self, '__class__', Terminal)

    def _restore_carried(
        self, runtime: _core.Runtime, carried: Mapping[str, object]
    ) -> None:
        """Give a new runtime the cursor and title the previous one had. Runs on its loop."""
        if self._title is not None:
            runtime.title = self._title
        cursor_state = carried.get('cursor')
        if cursor_state is None:
            return
        position, shape, is_blinking, is_visible, follow = cast(
            'tuple[_core.Point | None, _core.CursorShape | None, bool, bool, tuple[_core.Buffer, int, int] | None]',
            cursor_state,
        )
        cursor = runtime.cursor
        if follow is not None:
            buffer, column, row = follow
            cursor.follow(buffer, x=column, y=row)
        elif position is not None:
            cursor.position = position
        cursor.shape = shape
        cursor.is_blinking = is_blinking
        cursor.is_visible = is_visible

    def _restore_screenless(self, carried: Mapping[str, object]) -> None:
        """After a failed attach, give the canvas a screenless runtime again."""
        from xnano import terminal as screen

        failed_host = self._host
        self._is_live = False
        self._is_realtime = False
        self._carried = dict(carried)
        elapsed = cast('float', carried['elapsed_seconds'])
        columns = 80 if self._requested_width is None else self._requested_width
        rows = 24 if self._requested_height is None else self._requested_height
        interval_milliseconds = max(1, round(1000.0 / self._fps))

        def create_runtime() -> _core.Runtime:
            clock = _core.Clock.manual(elapsed_seconds=elapsed)
            if carried['is_stopped']:
                clock.stop()
            return _core.Runtime.offscreen(
                width=columns,
                height=rows,
                frame_interval_milliseconds=interval_milliseconds,
                clock=clock,
            )

        try:
            failed_host.shutdown()
        finally:
            screen._release_screen()
            _InlineHost(cast('Canvas[object, object]', self), create_runtime)

    # -- context management and closing --------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exception_type: object, *rest: object) -> None:
        self.close(raise_failure=exception_type is None)

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

        Closing twice is harmless. Leaving a ``with`` block closes the canvas. A canvas that
        was written into another canvas is taken off it and leaves that one running.

        Args:
            raise_failure: Whether to raise the error a callback raised on the loop, which
                stopped the canvas. A ``with`` block passes ``False`` while another error is
                already propagating.

        Raises:
            TerminalError: A callback raised on the canvas's loop, or the loop would not stop.
        """
        if self._canvas is not self:
            if not self._is_closed:
                self._is_closed = True
                root = self._canvas
                with root._lock:
                    if self in root._children:
                        root._children.remove(cast('Canvas[object, object]', self))
                placement = self._parent_placement
                if placement is not None and not root.is_closed:
                    root._host.post(self._cancel_hooks)
                    placement.remove()
            if _active_canvas.get() is self:
                _active_canvas.set(self._previous)
            return
        if not self._stop_requested.is_set() or not self._is_finalized:
            self._stop_requested.set()
            try:
                host = getattr(self, '_host', None)
                if host is not None:
                    host.shutdown()
            finally:
                self._finalize()
        if _active_canvas.get() is self:
            _active_canvas.set(self._previous)
        failure = self._failure
        if failure is not None and raise_failure:
            self._failure = None
            raise TerminalError(self._failure_text(failure)) from failure

    def _record_failure(self, error: BaseException) -> None:
        """Keep an error raised on the loop, as text plus the error without its frames."""
        self._failure_report = release_frames(error)
        self._failure = error

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
        if not canvas._host.is_autonomous:
            return canvas._runtime.device.size
        return canvas._size

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
        if self._canvas is self:
            return _core.Point(point.x, point.y)
        bounds = self._root._absolute_bounds
        return _core.Point(point.x - bounds.x, point.y - bounds.y)

    def _refuse_to_move(self) -> NoReturn:
        raise TerminalError(
            'A canvas sits at the origin and cannot be moved. Move a placement instead: '
            'placement.move(...), or canvas.write(..., x=, y=).'
        )

    def move(self, x: int = 0, y: int = 0) -> NoReturn:
        """
        Refuse to move: a canvas sits at the origin. Move a placement instead.

        Args:
            x: Columns to move right.
            y: Rows to move down.

        Raises:
            TerminalError: Always; it says to move a placement.
        """
        self._refuse_to_move()

    def up(self, count: int = 1) -> NoReturn:
        """
        Refuse to move: a canvas sits at the origin. Move a placement instead.

        Args:
            count: How many rows to move.

        Raises:
            TerminalError: Always; it says to move a placement.
        """
        self._refuse_to_move()

    def down(self, count: int = 1) -> NoReturn:
        """
        Refuse to move: a canvas sits at the origin. Move a placement instead.

        Args:
            count: How many rows to move.

        Raises:
            TerminalError: Always; it says to move a placement.
        """
        self._refuse_to_move()

    def left(self, count: int = 1) -> NoReturn:
        """
        Refuse to move: a canvas sits at the origin. Move a placement instead.

        Args:
            count: How many columns to move.

        Raises:
            TerminalError: Always; it says to move a placement.
        """
        self._refuse_to_move()

    def right(self, count: int = 1) -> NoReturn:
        """
        Refuse to move: a canvas sits at the origin. Move a placement instead.

        Args:
            count: How many columns to move.

        Raises:
            TerminalError: Always; it says to move a placement.
        """
        self._refuse_to_move()

    # -- settings ------------------------------------------------------------------------

    @property
    def fps(self) -> float:
        """The most frames drawn per second, and the rate [`iter`][xnano.canvas.Canvas.iter] aims for."""
        return self._canvas._fps

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
        canvas._host.call(lambda: setattr(canvas._runtime, 'title', value))
        canvas._title = value

    @property
    def time(self) -> Time:
        """The canvas's [`Time`][xnano.time.Time]: how long it has run, stopping, and formulas."""
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
    def region(self) -> Region:
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
        self._require_open()
        self._flush_look()
        return Region(self._content, owner=cast('Canvas[object, object]', self))

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
        if look is None or self._runtime_object is None:
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
                previous = self._decorated.insets
                self._decorated.demote(copy_cells=True)
                self._decorated = None
                # The canvas keeps the size of its screen; only a placement shrinks.
                root.width += previous.horizontal
                root.height += previous.vertical
            self._apply_content_colors(look, root)
        self._request_frame()

    # -- writing -------------------------------------------------------------------------

    def write(
        self,
        content: Content
        | Canvas[object, object]
        | _core.Operation
        | _core.Style
        | None = None,
        /,
        *,
        x: Axis | None = None,
        y: Axis | None = None,
        width: Axis | None = None,
        height: Axis | None = None,
        layer: int = 0,
        lock: bool = False,
        effects: Sequence[RenderableEffectSpecification] = (),
        style: _core.Style | None = None,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        is_bold: bool = False,
        is_dim: bool = False,
        is_italic: bool = False,
        is_underlined: bool = False,
        is_blinking: bool = False,
        is_reversed: bool = False,
        is_hidden: bool = False,
        is_crossed_out: bool = False,
        title: str | None = None,
        border: _core.BorderKind | None = None,
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

        A canvas from [`new`][xnano.new] that is written here becomes part of this one: it
        draws inside the placement, its own clock is set aside and it runs on this canvas's
        time. It may not have been given ``state`` or ``deps``, which belong to the outermost
        canvas.

        An image is added as an [`Image`][xnano.Image] (never a file path or a bare
        [`TerminalImage`][xnano_image.TerminalImage]; load one with
        [`from_image`][xnano.from_image]). With neither ``width`` nor ``height`` it keeps
        its own proportions at its own size, shrunk to fit the canvas. With one of them the
        other follows the image's proportions, and with both the image fits inside that box. An
        image sized by a percentage, or by the canvas because you gave no size, is converted
        again when the canvas is resized, unless it is locked. An animated image plays on the
        canvas's clock.

        Args:
            content: Text (or a list of lines), a [`Buffer`][xnano_core.Buffer] or widget, a
                canvas from ``new()``, the bytes of a cell grid, an image, or any
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
            effects: Effects to start on the placement, as dictionaries with a ``kind``
                key, such as ``[{'kind': 'effect.fade_to', 'color': 'red'}]``.
            style: A ready-made [`Style`][xnano.styles.Style] for text. The parameters below
                are applied over it.
            foreground: The text color.
            background: The color behind the text.
            is_bold: Whether the text is bold.
            is_dim: Whether the text is dimmed.
            is_italic: Whether the text is italic.
            is_underlined: Whether the text is underlined.
            is_blinking: Whether the text blinks.
            is_reversed: Whether foreground and background are swapped.
            is_hidden: Whether the text is hidden.
            is_crossed_out: Whether the text is struck through.
            title: A title on the border of a box around the text.
            border: The kind of border for a box around text: ``'plain'``, ``'rounded'``,
                ``'double'`` or ``'thick'``. Giving a ``title`` alone draws a plain one.
            border_style: The style of the box's border.
            padding: Space between the border and the text: a number of cells, a float or a
                percentage of the text's size, or a dictionary with ``top``, ``right``,
                ``bottom``, ``left``, ``vertical`` and ``horizontal``. Giving it draws the
                text in a box without a border unless ``border`` or ``title`` is also given.
            margin: Space outside the box, in the same forms.

        Returns:
            A [`Placement`][xnano.placement.Placement] to move, resize, listen on or remove.

        Raises:
            TypeError: A color, text modifier, title or border was given for content that is
                not text, or the content is a file path.
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
                    is_bold=True,
                    border='rounded',
                    title='Status',
                )
            ```
        """
        self._require_open()
        placement = self._canvas._place_on(
            self._content,
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
            is_bold=is_bold,
            is_dim=is_dim,
            is_italic=is_italic,
            is_underlined=is_underlined,
            is_blinking=is_blinking,
            is_reversed=is_reversed,
            is_hidden=is_hidden,
            is_crossed_out=is_crossed_out,
            title=title,
            border=border,
            border_style=border_style,
            padding=padding,
            margin=margin,
        )
        if effects:
            apply_effects(cast('Placement[object, object]', placement), effects)
        return placement

    def _place_on(
        self,
        parent_buffer: _core.Buffer,
        content: Content | Canvas[object, object] | _core.Operation | _core.Style | None,
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
        is_bold: bool = False,
        is_dim: bool = False,
        is_italic: bool = False,
        is_underlined: bool = False,
        is_blinking: bool = False,
        is_reversed: bool = False,
        is_hidden: bool = False,
        is_crossed_out: bool = False,
        title: str | None = None,
        border: _core.BorderKind | bool | None = None,
        border_style: _core.Style | None = None,
        padding: Spacing | None = None,
        margin: Spacing | None = None,
    ) -> Placement[DepsT, StateT]:
        if border is True:
            border = 'plain'
        elif border is False:
            border = None
        appearance = Appearance(
            style=style,
            foreground=foreground,
            background=background,
            is_bold=is_bold,
            is_dim=is_dim,
            is_italic=is_italic,
            is_underlined=is_underlined,
            is_blinking=is_blinking,
            is_reversed=is_reversed,
            is_hidden=is_hidden,
            is_crossed_out=is_crossed_out,
            title=title,
            border=border,
            border_style=border_style,
            padding=padding,
            margin=margin,
        )
        is_decorated = appearance.has_style or appearance.has_frame or margin is not None
        if isinstance(content, Canvas):
            return self._adopt(
                parent_buffer,
                content,
                parent_owner=parent_owner,
                x=x,
                y=y,
                width=width,
                height=height,
                layer=layer,
                look=appearance if is_decorated else None,
            )
        component = (
            None
            if content is None
            or isinstance(content, (Region, Pixel, Image, _core.Operation, _core.Style))
            or isinstance(content, (ContextualOperation, Customization))
            else as_component(content)
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
                is_bold=is_bold,
                is_dim=is_dim,
                is_italic=is_italic,
                is_underlined=is_underlined,
                is_blinking=is_blinking,
                is_reversed=is_reversed,
                is_hidden=is_hidden,
                is_crossed_out=is_crossed_out,
                title=title,
                border=border,
                border_style=border_style,
                padding=padding,
                margin=margin,
            )
            try:
                attach_component(
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
        if isinstance(content, ContextualOperation):
            if (
                content._callback is None
                and x is None
                and y is None
                and width is None
                and height is None
            ):
                if parent_buffer is self._content:
                    content.apply_to(cast('Canvas[object, object]', self))
                else:
                    content.apply_to_surface(parent_buffer)
                return Placement(self, parent_buffer, parent_buffer, parent_owner)
            effective_width: Axis = '100%' if width is None else width
            effective_height: Axis = '100%' if height is None else height
            initial_width = (
                effective_width
                if isinstance(effective_width, int)
                and not isinstance(effective_width, bool)
                else parent_buffer.width or self.width
            )
            initial_height = (
                effective_height
                if isinstance(effective_height, int)
                and not isinstance(effective_height, bool)
                else parent_buffer.height or self.height
            )
            operation_buffer = _core.Buffer(width=initial_width, height=initial_height)
            operation_buffer.layer = layer
            operation_placement: Placement[DepsT, StateT] = Placement(
                self, operation_buffer, parent_buffer, parent_owner
            )
            with self._lock:
                self._placements.append(operation_placement)
            parent_buffer.attach(operation_buffer, mode='transparent')
            operation_placement._set_axis('x', 0 if x is None else x)
            operation_placement._set_axis('y', 0 if y is None else y)
            operation_placement._set_axis('width', effective_width)
            operation_placement._set_axis('height', effective_height)
            cast('ContextualOperation[DepsT, StateT]', content).apply_to(
                operation_placement
            )
            if lock:
                for axis_name in ('x', 'y', 'width', 'height'):
                    operation_placement._set_axis(
                        axis_name, int(getattr(operation_placement, axis_name))
                    )
            return operation_placement
        if isinstance(content, (Customization, _core.Operation, _core.Style)):
            if x is None and y is None and width is None and height is None:
                if isinstance(content, Customization):
                    content.apply_to_surface(parent_buffer)
                elif isinstance(content, _core.Style):
                    parent_buffer.update(_core.ApplyStyle(content))
                else:
                    parent_buffer.update(content)
                return Placement(self, parent_buffer, parent_buffer, parent_owner)
            initial_width = (
                width
                if isinstance(width, int) and not isinstance(width, bool)
                else parent_buffer.width or self.width
            )
            initial_height = (
                height
                if isinstance(height, int) and not isinstance(height, bool)
                else parent_buffer.height or self.height
            )
            custom_buffer = _core.Buffer(width=initial_width, height=initial_height)
            custom_buffer.layer = layer
            custom_placement: Placement[DepsT, StateT] = Placement(
                self, custom_buffer, parent_buffer, parent_owner
            )
            with self._lock:
                self._placements.append(custom_placement)
            parent_buffer.attach(custom_buffer, mode='transparent')
            custom_placement._set_axis('x', 0 if x is None else x)
            custom_placement._set_axis('y', 0 if y is None else y)
            if width is not None:
                custom_placement._set_axis('width', width)
            if height is not None:
                custom_placement._set_axis('height', height)
            custom_placement.update(content)
            return custom_placement
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
        parent_buffer.attach(buffer, mode='transparent')
        requested: list[tuple[AxisName, Axis | None]] = [
            ('x', x),
            ('y', y),
            ('width', width),
            ('height', height),
        ]
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
    ) -> Placement[DepsT, StateT]:
        """Make a canvas from ``new()`` part of this one, drawn inside a placement."""
        if child._is_live:
            raise TerminalError(
                'This canvas is on the screen, so it cannot be written into another canvas. '
                'Write a canvas from xnano.new() that was never opened.'
            )
        if child.is_closed:
            raise TerminalError(
                'This canvas has been closed, so there is nothing left to write. Create a new '
                'one with xnano.new().'
            )
        if child is parent_owner:
            raise TerminalError(
                'A canvas can be written into one other canvas, once, and never into itself. '
                'Create another canvas with xnano.new() for a second copy.'
            )
        owner: Canvas[object, object] | Placement[object, object] | None = parent_owner
        while owner is not None:
            if owner is child:
                raise TerminalError(
                    'A canvas cannot be written into a canvas that is part of it. Write the '
                    'inner canvas into the outer one instead.'
                )
            if isinstance(owner, Placement):
                owner = owner._parent_owner
            else:
                owner = owner._parent_placement
        if child._canvas is not child:
            raise TerminalError(
                'A canvas can be written into one other canvas, once, and never into itself. '
                'Create another canvas with xnano.new() for a second copy.'
            )
        for name in ('state', 'deps'):
            if getattr(child, f'_{name}_given'):
                raise TerminalError(
                    f'This canvas was given {name}, and a canvas written into another one '
                    f'shares the outer canvas instead. Give {name} to the outermost canvas: '
                    f'xnano.new({name}=...) or xnano.open({name}=...).'
                )
        handles = child._host.call(child._hook_handles)
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
            root._children.append(child)
            root._children.extend(child._children)
            child._children.clear()
        child._canvas = cast('Canvas[object, object]', root)
        child._root_canvas = cast('Canvas[object, object]', root)
        child._parent_placement = cast('Placement[object, object]', placement)
        child.output = root.output
        if _active_canvas.get() is child:
            _active_canvas.set(child._previous)
        parent_buffer.attach(child_buffer, mode='transparent')
        for _ in range(len(moved_images) + len(moved_listeners) + len(moved_effects)):
            root._demand_frames()
        for moved in moved_dynamic:
            root._bindings_changed(cast('Placement[DepsT, StateT]', moved))

        def bind_on_root() -> None:
            runtime = root._runtime
            for registration in moved_ledger:
                registration.bind(runtime)
            for handle in handles:
                handle._rebind(runtime)
            for customization, target in moved_effects:
                target._buffer.update(customization)

        root._host.post(bind_on_root)
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
        return placement

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
        buffer, _ = content_buffer(content)
        return buffer, None

    def _release(self, placement: Placement[DepsT, StateT]) -> None:
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
        """Apply operations (``Write``, ``Fill``, ``Border``, customizations and operations) to the canvas."""
        self._require_open()
        for item in operations:
            if isinstance(item, ContextualOperation):
                cast('ContextualOperation[DepsT, StateT]', item).apply_to(self)
            elif isinstance(item, Customization):
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
        """Apply an operation, customization or style with ``canvas | operation``."""
        if isinstance(other, (_core.Operation, _core.Style)):
            self.update(other)
        else:
            self.update(*other)
        return self

    def __ior__(
        self,
        other: _core.Operation | _core.Style | Sequence[_core.Operation],
    ) -> Self:
        """Apply an operation, customization or style in place with ``canvas |= operation``."""
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

    @overload
    def __getitem__(self, key: tuple[int, int]) -> _core.Cell: ...
    @overload
    def __getitem__(self, key: tuple[slice, slice]) -> _core.Region: ...
    def __getitem__(
        self, key: tuple[int, int] | tuple[slice, slice]
    ) -> _core.Cell | _core.Region:
        """
        Return the cell at ``canvas[column, row]``, or the region at ``canvas[columns, rows]``.

        Args:
            key: A ``(column, row)`` pair of integers, or a pair of slices.
        """
        self._require_open()
        self._flush_look()
        return self._content[key]

    def __setitem__(
        self,
        key: tuple[slice | int, slice | int],
        value: str | ColorValue | Content,
    ) -> None:
        """
        Fill part of the canvas.

        * A string is written into the region, clipped at its edges.
        * A [`Color`][xnano_core.Color] or an ``(red, green, blue)`` tuple fills
          the region's background. (A string is always text; make a color from a hex string
          with ``Color('#336699')``.)
        * A buffer or other content is placed so that it covers the region.

        Examples:
            ```python
            import xnano

            with xnano.new(width=10, height=3) as canvas:
                canvas[0:5, 0:2] = (51, 102, 153)
                canvas[2:9, 1:2] = 'hello'
            ```
        """
        self._require_open()
        columns, rows = key
        if isinstance(columns, int) and isinstance(rows, int):
            if isinstance(value, str):
                self._content[columns, rows] = value
                return
            raise TypeError(
                'A single cell takes a string or a Cell. To fill or place something over '
                'an area, index with two slices, such as canvas[0:5, 0:2].'
            )
        size = self.size
        left, right, column_step = (
            columns.indices(size.width)
            if isinstance(columns, slice)
            else (columns, columns + 1, 1)
        )
        top, bottom, row_step = (
            rows.indices(size.height) if isinstance(rows, slice) else (rows, rows + 1, 1)
        )
        if column_step != 1 or row_step != 1:
            raise ValueError(
                'A region of the canvas is a rectangle of cells, so its slices cannot '
                'have a step. Write canvas[0:5, 0:2] instead of canvas[0:5:2, 0:2].'
            )
        if right <= left or bottom <= top:
            return
        region = self._content[left:right, top:bottom]
        if _is_color(value):
            region.update(_core.Background(value))
        elif isinstance(value, str):
            region.update(_core.Write(value))
        else:
            self.write(value, x=left, y=top, width=right - left, height=bottom - top)

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

    def step(self, *, delta_seconds: float | None = None) -> Frame:
        """
        Move time by ``delta_seconds``, one frame by default, and draw exactly one frame.

        On a canvas from ``new()`` this always works, and it moves time even while the
        canvas is stopped, which leaves it stopped: it is how a stopped canvas is walked one
        frame at a time. A canvas that runs by itself can be stepped only while it is
        stopped. One frame is ``1 / fps`` seconds; default steps and the frames of
        [`iter`][xnano.canvas.Canvas.iter] share one count, so sixty of them at ``fps=60``
        are exactly one second. A large ``delta_seconds`` is one jump: timers and fixed-step
        ``every`` hooks that it crossed all run.

        Args:
            delta_seconds: How far to move, in seconds, above zero; one frame when ``None``.

        Returns:
            The [`Frame`][xnano.context.Frame] that was drawn.

        Raises:
            ValueError: ``delta_seconds`` is not above zero.
            TerminalError: The canvas runs by itself and is not stopped.

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
        return self._canvas._step(delta_seconds)

    def _step(self, delta_seconds: float | None) -> Frame:
        self._require_open()
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
            if not drawn.wait(10.0):
                raise TerminalError(
                    'The canvas did not draw the stepped frame within 10 seconds. A callback '
                    'that never returns is blocking its loop; keep callbacks short.'
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
        canvas = self._canvas
        canvas._require_open()
        if canvas._host.is_autonomous:
            canvas._host.call(lambda: canvas._runtime.request_frame())
            return
        canvas._runtime.step()
        canvas._pushed_pointer = None

    def stop(self) -> None:
        """
        Freeze time: the same as [`Time.stop`][xnano.time.Time.stop].

        The canvas keeps drawing and hooks still hear input, but animations, effects,
        formulas, timers and the beat stand still until [`resume`][xnano.canvas.Canvas.resume].
        [`step`][xnano.canvas.Canvas.step] moves a stopped canvas one frame at a time. To end a
        loop, call [`quit`][xnano.canvas.Canvas.quit].
        """
        self._canvas._time.stop()

    def resume(self) -> None:
        """Let time run on from where [`stop`][xnano.canvas.Canvas.stop] froze it."""
        self._canvas._time.resume()

    def quit(self) -> None:
        """
        Ask the canvas's loop to end.

        Safe from any thread, including from a hook. A running ``iter()``, ``run()``,
        ``wait_for_key()`` or ``prompt()`` ends. On a canvas from ``new()`` the canvas stays
        open for writing and rendering; on a canvas that runs by itself (``realtime=True``, or
        on the screen) the loop ends and the canvas closes.
        """
        canvas = self._canvas
        canvas._stop_requested.set()
        if not canvas._is_closed and canvas._host.is_autonomous:
            canvas._host.post(lambda: canvas._stop_runtime())

    def run(self, *, quit_on: str | Sequence[str] | None = 'ctrl+c') -> None:
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
                # With the keyboard off, only the interrupt gate can end the loop on Ctrl-C.
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
            raise TerminalError(canvas._failure_text(failure)) from failure

    def wait_for_key(self, *keys: str) -> str:
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
                def press(context: xnano.context.Context) -> None:
                    canvas.push(Event.key_press('enter'))

                assert canvas.wait_for_key('enter') == 'enter'
            ```
        """
        pressed: list[str] = []
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
                def type_answer(context: xnano.context.Context) -> None:
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
            self.cursor.position = (x + len(line), y)

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
            self.cursor.is_visible = False
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
        next step, whatever the input gates say. Build events with
        [`Event`][xnano_core.Event]; ``Event.custom(name, data=...)`` makes one of your own.

        Args:
            event: The event to deliver.

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
        canvas = self._canvas
        canvas._require_open()
        if canvas._audio is None:
            require('audio', needed_for='Canvas.audio')
            from xnano.audio import AudioDevice

            with canvas._lock:
                if canvas._audio is None:
                    audio = AudioDevice(cast('Canvas[object, object]', canvas))
                    canvas._audio = audio
                    canvas._host.post(lambda: audio._bind(canvas._runtime))
        return canvas._audio

    @property
    def input(self) -> Input:
        """
        The keys held down right now, for programs that poll instead of listening.

        Read it anywhere, from any thread. A canvas opened with
        ``keyboard='release_events'`` knows exactly when a key is let go.
        """
        canvas = self._canvas
        canvas._require_open()
        if canvas._input is None:
            canvas._input = Input(cast('Canvas[object, object]', canvas))
        return canvas._input

    def play(self, playable: PlaySource, /, **options: Unpack[PlayOptions]) -> PlayHandle:
        """
        Play a note, a sound, a symbol name, a melody or a sequence of those, and return at once.

        This is [`audio.play`][xnano.audio.AudioDevice.play]; see it for what ``playable`` may
        be and for every option. On a canvas from ``new()`` the sound is recorded instead of
        played; read it with [`audio.render_sound`][xnano.audio.AudioDevice.render_sound].

        Returns:
            A [`PlayHandle`][xnano.music.PlayHandle] that tells when the sound is over.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1, bpm=100) as canvas:
                canvas.play('C4 E4 G4:2 rest C5+E5+G5', instrument='bell')
                canvas.step(delta_seconds=1.0)
                assert canvas.audio.render_sound().duration_milliseconds == 1000.0
            ```
        """
        if hasattr(playable, '__xnano_play__') or not isinstance(playable, str):
            handle = play_component(
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

    def ref(self, reader: Callable[[StateT], ValueT]) -> _core.StateReference[ValueT]:
        """
        A core reference for one field of the canvas's state.

        The reference can be used as an axis, a range bound or a widget parameter.

        Args:
            reader: A function or lambda that reads the field, such as
                ``lambda state: state.volume``.

        Raises:
            TerminalError: The canvas was created without ``state``.
        """
        store = self._canvas._state_store
        if store is None:
            raise TerminalError(
                'This canvas has no state, so ref() has nothing to read. Create it with '
                'xnano.new(state=YourDataclass()).'
            )
        return reference_for(store, reader)

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
    content: Content | Canvas[object, object] | None = None,
    /,
    *,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    **settings: Unpack[CanvasSettings],
) -> Canvas[None, None]: ...
@overload
def new(
    content: Content | Canvas[object, object] | None = None,
    /,
    *,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> Canvas[None, StateT]: ...
@overload
def new(
    content: Content | Canvas[object, object] | None = None,
    /,
    *,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    deps: DepsT,
    **settings: Unpack[CanvasSettings],
) -> Canvas[DepsT, None]: ...
@overload
def new(
    content: Content | Canvas[object, object] | None = None,
    /,
    *,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
    realtime: bool = False,
    title: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
    deps: DepsT,
    state: StateT,
    **settings: Unpack[CanvasSettings],
) -> Canvas[DepsT, StateT]: ...
def new(
    content: Content | Canvas[object, object] | None = None,
    /,
    *,
    width: int | None = None,
    height: int | None = None,
    fps: float = 60.0,
    bpm: float = 120.0,
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

    ``content``, when given, is written at the top-left corner, as ``canvas.write(content)``
    would. The appearance keywords (colors, text modifiers, ``border``, ``border_style``)
    style the canvas itself, not its content, so they are accepted only without content:
    ``new(border='rounded')`` borders the canvas, and ``new().write('hello', border='rounded')``
    borders the text. A canvas's ``foreground`` and ``background`` color the cells no content
    covers. ``padding`` and ``margin`` space content, so give them to ``canvas.write(...)``.
    ``title`` is the window title.

    The input gates (``mouse``, ``scroll``, ``keyboard``, ``paste``, ``focus``, ``interrupt``,
    ``capture``, ``clear``, ``alternate_screen``) are stored and take effect when the canvas
    is opened on the screen; see [`GateSettings`][xnano.types.GateSettings].

    Args:
        content: Something to write into the canvas at once, such as text or a widget.
        width: The width in cells; 80 when ``None``. On the screen it is the width of the
            region the canvas draws in.
        height: The height in cells; 24 when ``None``. On the screen it is the height of the
            region the canvas draws in.
        fps: The most frames drawn per second, and the length of one step of ``iter()``.
        bpm: Beats per minute for beat timers, notes and melodies.
        realtime: Whether the canvas runs by itself on the wall clock, on a thread of its own.
        title: The window title, shown when the canvas is on the screen.
        effects: Effects to apply to the canvas, as dictionaries with a ``kind`` key.
        deps: Dependencies that hooks read as ``context.deps``; the canvas never reads them.
        state: A dataclass instance the canvas keeps and validates. Hooks read and write it.
        settings: The input gates and the canvas's own look; see
            [`CanvasSettings`][xnano.types.CanvasSettings].

    Returns:
        The [`Canvas`][xnano.canvas.Canvas], which is also the one module-level functions such
        as [`active`][xnano.active] find.

    Raises:
        TypeError: An appearance keyword was given with content, ``padding`` or ``margin``
            was given, or a keyword is unknown.
        ValueError: A size, ``fps``, ``bpm`` or gate is out of range.

    Examples:
        ```python
        import xnano

        with xnano.new(width=16, height=3) as canvas:
            assert (canvas.width, canvas.height) == (16, 3)
            assert xnano.active() is canvas
            assert not canvas.time.is_realtime

        with xnano.new('hello', width=8, height=1) as greeting:
            assert greeting.render() == 'hello'
        ```
    """
    gates, appearance = _split_settings('new', settings)
    if content is not None and appearance:
        raise _appearance_with_content_error('new', appearance)
    canvas: Canvas[DepsT, StateT] = Canvas(
        width=_check_size('width', width),
        height=_check_size('height', height),
        fps=_check_fps(fps),
        bpm=_check_bpm(bpm),
        is_realtime=bool(realtime),
        deps=deps,
        state=state,
        title=title,
        gates=gates,
        appearance=appearance,
        effects=effects,
    )
    if content is not None:
        try:
            canvas.write(content)
        except BaseException:
            canvas.close(raise_failure=False)
            raise
    return canvas


@overload
def active() -> Canvas[object, object]: ...
@overload
def active(*, is_required: Literal[True]) -> Canvas[object, object]: ...
@overload
def active(*, is_required: Literal[False]) -> Canvas[object, object] | None: ...
def active(*, is_required: bool = True) -> Canvas[object, object] | None:
    """
    Return the innermost canvas that is running in this thread or task.

    A canvas is active from the moment it is created until it ends: inside nested ``with``
    blocks the inner one wins, and a canvas that was asked to [`quit`][xnano.canvas.Canvas.quit]
    gives way to the one around it. Hooks run on a canvas's loop see that canvas.

    Args:
        is_required: Whether to raise when no canvas is running.

    Raises:
        TerminalClosedError: No canvas is running and ``is_required`` is true.

    Examples:
        ```python
        import xnano

        assert xnano.active(is_required=False) is None
        with xnano.new(width=4, height=1) as outer:
            with xnano.new(width=4, height=1) as inner:
                assert xnano.active() is inner
            assert xnano.active() is outer
        ```
    """
    canvas = _active_canvas.get()
    while canvas is not None and (not canvas.is_running or canvas._canvas is not canvas):
        canvas = canvas._previous
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


def find_active() -> Canvas[object, object] | None:
    """Return the innermost running canvas, or ``None`` when none is running."""
    return active(is_required=False)
