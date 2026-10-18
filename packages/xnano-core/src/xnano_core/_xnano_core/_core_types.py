"""
xnano_core._xnano_core._core_types

Type aliases and the few Python objects the native module needs.

The aliases are the literals and unions that cannot be expressed inside the PyO3 bindings.
The classes are the objects the native runtime constructs or imports at run time: the hook
signals, the contexts handed to hooks, the operation registry and the lazy rendering.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from types import TracebackType
from typing import TYPE_CHECKING, Literal, Protocol, TypeAlias, TypedDict, TypeVar

# Read when the module runs, not under `TYPE_CHECKING`, so that `ColorValue` is a union that
# `typing.get_type_hints` can combine with other types.
from xnano_core._xnano_core import Color

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from xnano_core._xnano_core import (
        Buffer,
        CanvasCircle,
        CanvasLabel,
        CanvasLayer,
        CanvasLine,
        CanvasMap,
        CanvasMarker,
        CanvasPoints,
        CanvasRectangle,
        Clock,
        Device,
        Event,
        EventStream,
        Expression,
        InputState,
        Operation,
        Rectangle,
        Region,
        Runtime,
        StyledText,
        TerminalStateChange,
    )

OperationType = TypeVar('OperationType')


class ContextArguments(TypedDict, total=False):
    """
    What every context is created with.

    Attributes:
        buffer: The buffer the context is about.
        target: The buffer or region the context draws on; the buffer itself when omitted.
        runtime: The runtime the buffer is mounted on.
        event: The event being handled.
        state_change: The state change that triggered a watch.
    """

    buffer: Buffer
    """The buffer the context is about."""
    target: Buffer | Region | None
    """The buffer or region the context draws on; the buffer itself when omitted."""
    runtime: Runtime
    """The runtime the buffer is mounted on."""
    event: Event | None
    """The event being handled."""
    state_change: TerminalStateChange | None
    """The state change that triggered a watch."""


JSONValue: TypeAlias = (
    'None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]'
)
"""A finite JSON-compatible value."""

JSONSchema: TypeAlias = 'dict[str, JSONValue]'
"""A JSON Schema document."""

StatePath: TypeAlias = 'tuple[str | int, ...]'
"""A path into a state tree: object keys are ``str`` and array indexes are ``int``."""

TextContent: TypeAlias = 'str | StyledText | Sequence[str | StyledText]'
"""Text accepted by writing operations and components."""

Modifier: TypeAlias = Literal[
    'bold', 'dim', 'italic', 'underline', 'blink', 'reverse', 'hidden', 'crossed_out'
]
"""A text style modifier."""

Coordinate: TypeAlias = tuple[int, int]
"""A ``(column, row)`` pair."""

PixelEntry: TypeAlias = tuple[int, int, tuple[int, int, int]]
"""One pixel: ``(column, row, (red, green, blue))``."""

PixelEncoding: TypeAlias = Literal['half_blocks', 'braille']

CursorShape: TypeAlias = Literal['block', 'bar', 'underline']
"""What a terminal cursor looks like."""
"""How logical pixels pack into cells."""

Interpolation: TypeAlias = Literal[
    'linear',
    'back_in',
    'back_out',
    'back_in_out',
    'bounce_in',
    'bounce_out',
    'bounce_in_out',
    'circ_in',
    'circ_out',
    'circ_in_out',
    'cubic_in',
    'cubic_out',
    'cubic_in_out',
    'elastic_in',
    'elastic_out',
    'elastic_in_out',
    'expo_in',
    'expo_out',
    'expo_in_out',
    'quad_in',
    'quad_out',
    'quad_in_out',
    'quart_in',
    'quart_out',
    'quart_in_out',
    'quint_in',
    'quint_out',
    'quint_in_out',
    'sine_in',
    'sine_out',
    'sine_in_out',
    'smooth_step',
    'spring',
    'reverse',
    'ease_in',
]
"""How an effect eases between its start and end; ``'ease_in'`` is ``'quad_in'``."""

KeyModifier: TypeAlias = Literal['control', 'shift', 'alt', 'super', 'meta', 'hyper']
"""A modifier key held during a key event."""

MouseButton: TypeAlias = Literal['left', 'right', 'middle']
"""A mouse button."""

EventKind: TypeAlias = Literal[
    'key',
    'mouse',
    'paste',
    'resize',
    'focus_gained',
    'focus_lost',
    'tick',
    'timer',
    'frame',
    'wake',
    'exit_requested',
    'custom',
]
"""What an event reports."""

HookEventKind: TypeAlias = Literal[
    'key',
    'mouse',
    'paste',
    'resize',
    'focus_gained',
    'focus_lost',
    'tick',
    'timer',
    'frame',
    'wake',
    'exit_requested',
    'custom',
    'mount',
    'unmount',
    'change',
    'state_change',
    'before_render',
    'after_render',
]
"""What a hook can listen to."""

ColorName: TypeAlias = Literal[
    'black',
    'red',
    'green',
    'yellow',
    'blue',
    'magenta',
    'cyan',
    'gray',
    'grey',
    'dark_gray',
    'dark_grey',
    'darkgray',
    'darkgrey',
    'light_black',
    'light_red',
    'bright_red',
    'light_green',
    'bright_green',
    'light_yellow',
    'bright_yellow',
    'light_blue',
    'bright_blue',
    'light_magenta',
    'bright_magenta',
    'light_cyan',
    'bright_cyan',
    'white',
    'reset',
]
"""
A named ANSI terminal color.

``gray`` and ``grey`` are the same color, and so are ``light_`` and ``bright_``.
``dark_gray`` is the dim gray. ``reset`` restores the terminal default.
"""

ColorValue: TypeAlias = Color | ColorName | str | tuple[int, int, int]
"""
A color, an ANSI color name, a ``'#rrggbb'`` string, or a ``(red, green, blue)`` tuple.

A Tailwind name such as ``'slate-400'`` is a [`TailwindColorBinding`][xnano_core._xnano_core._core_types.TailwindColorBinding].
It is not parsed by [`Color`][xnano_core._xnano_core.Color].
"""

TailwindColorName: TypeAlias = Literal[
    'slate',
    'gray',
    'zinc',
    'neutral',
    'stone',
    'red',
    'orange',
    'amber',
    'yellow',
    'lime',
    'green',
    'emerald',
    'teal',
    'cyan',
    'sky',
    'blue',
    'indigo',
    'violet',
    'purple',
    'fuchsia',
    'pink',
    'rose',
]
"""A Tailwind palette that has shades."""

TailwindColorShade: TypeAlias = Literal[
    50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950
]
"""A Tailwind shade."""

TailwindColorBinding: TypeAlias = Literal[
    'slate-50',
    'slate-100',
    'slate-200',
    'slate-300',
    'slate-400',
    'slate-500',
    'slate-600',
    'slate-700',
    'slate-800',
    'slate-900',
    'slate-950',
    'gray-50',
    'gray-100',
    'gray-200',
    'gray-300',
    'gray-400',
    'gray-500',
    'gray-600',
    'gray-700',
    'gray-800',
    'gray-900',
    'gray-950',
    'zinc-50',
    'zinc-100',
    'zinc-200',
    'zinc-300',
    'zinc-400',
    'zinc-500',
    'zinc-600',
    'zinc-700',
    'zinc-800',
    'zinc-900',
    'zinc-950',
    'neutral-50',
    'neutral-100',
    'neutral-200',
    'neutral-300',
    'neutral-400',
    'neutral-500',
    'neutral-600',
    'neutral-700',
    'neutral-800',
    'neutral-900',
    'neutral-950',
    'stone-50',
    'stone-100',
    'stone-200',
    'stone-300',
    'stone-400',
    'stone-500',
    'stone-600',
    'stone-700',
    'stone-800',
    'stone-900',
    'stone-950',
    'red-50',
    'red-100',
    'red-200',
    'red-300',
    'red-400',
    'red-500',
    'red-600',
    'red-700',
    'red-800',
    'red-900',
    'red-950',
    'orange-50',
    'orange-100',
    'orange-200',
    'orange-300',
    'orange-400',
    'orange-500',
    'orange-600',
    'orange-700',
    'orange-800',
    'orange-900',
    'orange-950',
    'amber-50',
    'amber-100',
    'amber-200',
    'amber-300',
    'amber-400',
    'amber-500',
    'amber-600',
    'amber-700',
    'amber-800',
    'amber-900',
    'amber-950',
    'yellow-50',
    'yellow-100',
    'yellow-200',
    'yellow-300',
    'yellow-400',
    'yellow-500',
    'yellow-600',
    'yellow-700',
    'yellow-800',
    'yellow-900',
    'yellow-950',
    'lime-50',
    'lime-100',
    'lime-200',
    'lime-300',
    'lime-400',
    'lime-500',
    'lime-600',
    'lime-700',
    'lime-800',
    'lime-900',
    'lime-950',
    'green-50',
    'green-100',
    'green-200',
    'green-300',
    'green-400',
    'green-500',
    'green-600',
    'green-700',
    'green-800',
    'green-900',
    'green-950',
    'emerald-50',
    'emerald-100',
    'emerald-200',
    'emerald-300',
    'emerald-400',
    'emerald-500',
    'emerald-600',
    'emerald-700',
    'emerald-800',
    'emerald-900',
    'emerald-950',
    'teal-50',
    'teal-100',
    'teal-200',
    'teal-300',
    'teal-400',
    'teal-500',
    'teal-600',
    'teal-700',
    'teal-800',
    'teal-900',
    'teal-950',
    'cyan-50',
    'cyan-100',
    'cyan-200',
    'cyan-300',
    'cyan-400',
    'cyan-500',
    'cyan-600',
    'cyan-700',
    'cyan-800',
    'cyan-900',
    'cyan-950',
    'sky-50',
    'sky-100',
    'sky-200',
    'sky-300',
    'sky-400',
    'sky-500',
    'sky-600',
    'sky-700',
    'sky-800',
    'sky-900',
    'sky-950',
    'blue-50',
    'blue-100',
    'blue-200',
    'blue-300',
    'blue-400',
    'blue-500',
    'blue-600',
    'blue-700',
    'blue-800',
    'blue-900',
    'blue-950',
    'indigo-50',
    'indigo-100',
    'indigo-200',
    'indigo-300',
    'indigo-400',
    'indigo-500',
    'indigo-600',
    'indigo-700',
    'indigo-800',
    'indigo-900',
    'indigo-950',
    'violet-50',
    'violet-100',
    'violet-200',
    'violet-300',
    'violet-400',
    'violet-500',
    'violet-600',
    'violet-700',
    'violet-800',
    'violet-900',
    'violet-950',
    'purple-50',
    'purple-100',
    'purple-200',
    'purple-300',
    'purple-400',
    'purple-500',
    'purple-600',
    'purple-700',
    'purple-800',
    'purple-900',
    'purple-950',
    'fuchsia-50',
    'fuchsia-100',
    'fuchsia-200',
    'fuchsia-300',
    'fuchsia-400',
    'fuchsia-500',
    'fuchsia-600',
    'fuchsia-700',
    'fuchsia-800',
    'fuchsia-900',
    'fuchsia-950',
    'pink-50',
    'pink-100',
    'pink-200',
    'pink-300',
    'pink-400',
    'pink-500',
    'pink-600',
    'pink-700',
    'pink-800',
    'pink-900',
    'pink-950',
    'rose-50',
    'rose-100',
    'rose-200',
    'rose-300',
    'rose-400',
    'rose-500',
    'rose-600',
    'rose-700',
    'rose-800',
    'rose-900',
    'rose-950',
]
"""
A Tailwind palette and shade, such as ``'slate-400'``.

[`Color`][xnano_core._xnano_core.Color] does not parse these. Pass the palette and shade
to [`Color.from_tailwind`][xnano_core._xnano_core.Color.from_tailwind].
"""

KeyName: TypeAlias = Literal[
    'a',
    'b',
    'c',
    'd',
    'e',
    'f',
    'g',
    'h',
    'i',
    'j',
    'k',
    'l',
    'm',
    'n',
    'o',
    'p',
    'q',
    'r',
    's',
    't',
    'u',
    'v',
    'w',
    'x',
    'y',
    'z',
    '0',
    '1',
    '2',
    '3',
    '4',
    '5',
    '6',
    '7',
    '8',
    '9',
    'enter',
    'escape',
    'backspace',
    'tab',
    'space',
    'delete',
    'insert',
    'up',
    'down',
    'left',
    'right',
    'home',
    'end',
    'page_up',
    'page_down',
    'caps_lock',
    'scroll_lock',
    'num_lock',
    'print_screen',
    'pause',
    'menu',
    'f1',
    'f2',
    'f3',
    'f4',
    'f5',
    'f6',
    'f7',
    'f8',
    'f9',
    'f10',
    'f11',
    'f12',
]
"""A key name as events report it and bindings accept it, such as ``q``, ``enter`` or ``page_up``."""

KeyBindingText: TypeAlias = 'KeyName | str'
"""A key optionally preceded by ``+``-joined modifiers, such as ``q``, ``ctrl+c`` or ``shift+tab``."""

WriteMode: TypeAlias = Literal['replace', 'preserve_background']
"""How written text treats the background already in the cell."""

PasteMode: TypeAlias = Literal['replace', 'preserve_background', 'transparent']
"""How copied cells combine with the destination."""

RasterMode: TypeAlias = Literal['replace', 'over']
"""How RGBA pixels combine with what is already there."""

KeyEventKind: TypeAlias = Literal['press', 'repeat', 'release']
"""Whether a key was pressed, held down or released."""

MouseEventKind: TypeAlias = Literal['press', 'release', 'drag', 'move', 'scroll']
"""What a mouse event reports."""

GeometryMode: TypeAlias = Literal['inherit', 'explicit']
"""Whether a buffer takes its geometry from its parent or keeps its own."""

PixelAnchor: TypeAlias = Literal['top_left', 'center', 'bottom_right']
"""Which pixel of a cell a cell coordinate refers to."""

RenderFormat: TypeAlias = Literal['text', 'ansi']
"""How a buffer serializes: plain text rows or text with ANSI styling."""

BorderKind: TypeAlias = Literal['plain', 'rounded', 'double', 'thick']
"""The line style of a border."""

TriggerKind: TypeAlias = Literal[
    'immediate',
    'frame',
    'update',
    'key',
    'key_release',
    'click',
    'drag',
    'mouse',
    'paste',
    'resize',
    'state_change',
    'every',
    'after',
]
"""When something runs: a moment of the loop, an interval, or a kind of event."""

Side: TypeAlias = Literal['left', 'right', 'top', 'bottom']
"""A side of a rectangle."""

Orientation: TypeAlias = Literal['horizontal', 'vertical']
"""The direction something runs in."""

ColorProfile: TypeAlias = Literal[
    'no_terminal', 'no_color', 'ansi16', 'ansi256', 'truecolor'
]
"""How many colors a terminal can display."""

CanvasShape: TypeAlias = 'CanvasLine | CanvasRectangle | CanvasCircle | CanvasPoints | CanvasMap | CanvasLabel | CanvasLayer | CanvasMarker'
"""Anything a canvas can draw."""

ScalarExpression: TypeAlias = (
    'Expression[bool] | Expression[int | float] | Expression[str]'
)
"""An expression of a number, text or a condition."""

HookCallback: TypeAlias = 'Callable[[CoreContext], None]'
"""A function a hook calls with its context."""

HookDecorator: TypeAlias = 'Callable[[HookCallback], HookCallback]'
"""A decorator that registers a hook callback and returns it unchanged."""

EvolveSymbolSet: TypeAlias = Literal[
    'blocks_horizontal',
    'blocks_vertical',
    'circle_fill',
    'circles',
    'quadrants',
    'shaded',
    'squares',
]
"""The symbols an evolve effect steps through."""

CapabilityStatus: TypeAlias = Literal['supported', 'unsupported', 'unknown']
"""Whether a terminal feature is available."""

GraphicsProtocol: TypeAlias = Literal['half_blocks', 'sixel', 'kitty', 'iterm2']
"""How images are drawn into a terminal."""


class HookSignal(Exception):
    """
    Control flow recognized only while the runtime executes a hook.

    Raise one of its subclasses from a hook callback. Outside a hook it is an ordinary
    exception.
    """


class Skip(HookSignal):
    """End the current hook and continue dispatch."""


class Invalidate(HookSignal):
    """End the current hook and request a display frame."""


class Stop(HookSignal):
    """End the hook and request that the runtime stop."""


class Propagate(HookSignal):
    """End the current hook and continue with the parent event target."""


class EvaluationContext:
    """
    What an expression or operation handler can see.

    Args:
        buffer: The buffer that owns the target.
        target: The buffer or region the work applies to. Defaults to ``buffer``.
        runtime: The runtime the buffer is mounted on, if any.
        event: The event being handled, if any.
    """

    def __init__(
        self,
        *,
        buffer: Buffer,
        target: Buffer | Region | None = None,
        runtime: Runtime | None = None,
        event: Event | None = None,
        **extras: object,
    ) -> None:
        self._buffer = buffer
        self._target = buffer if target is None else target
        self._runtime = runtime
        self._event = event
        self._extras = extras

    @property
    def buffer(self) -> Buffer:
        """The buffer that owns the target."""
        return self._buffer

    @property
    def target(self) -> Buffer | Region:
        """The buffer or region the work applies to."""
        return self._target

    @property
    def runtime(self) -> Runtime | None:
        """The runtime the buffer is mounted on, or ``None`` offline."""
        return self._runtime

    @property
    def device(self) -> Device | None:
        """The runtime's device, or ``None`` offline."""
        return None if self._runtime is None else self._runtime.device

    @property
    def clock(self) -> Clock | None:
        """The runtime's clock, or ``None`` offline."""
        return None if self._runtime is None else self._runtime.clock

    @property
    def event(self) -> Event | None:
        """The event being handled, or ``None``."""
        return self._event

    def update(self, *operations: Operation) -> None:
        """Apply operations to the target, in order."""
        self._target.update(*operations)


class CoreContext(EvaluationContext):
    """
    A hook's view of the runtime: device, clock, input and focus.

    Every context has a runtime; offline code uses
    [`EvaluationContext`][xnano_core._xnano_core._core_types.EvaluationContext].
    """

    def __init__(
        self,
        *,
        runtime: Runtime,
        buffer: Buffer,
        target: Buffer | Region | None = None,
        event: Event | None = None,
        state_change: TerminalStateChange | None = None,
        **extras: object,
    ) -> None:
        super().__init__(
            buffer=buffer, target=target, runtime=runtime, event=event, **extras
        )
        self._state_change = state_change

    @property
    def runtime(self) -> Runtime:
        """The runtime the buffer is mounted on."""
        if self._runtime is None:
            raise RuntimeError(
                'This context has no runtime. Use EvaluationContext for offline work.'
            )
        return self._runtime

    @property
    def device(self) -> Device:
        """The runtime's device."""
        return self.runtime.device

    @property
    def clock(self) -> Clock:
        """The runtime's clock."""
        return self.runtime.clock

    @property
    def input(self) -> InputState:
        """The runtime's pressed keys and pointer position."""
        return self.runtime.input

    @property
    def bounds(self) -> Rectangle:
        """The buffer's bounds in screen coordinates."""
        return self._buffer._absolute_bounds

    @property
    def is_focused(self) -> bool:
        """Whether the buffer has input focus."""
        return self.runtime._is_focused(self._buffer)

    @property
    def state_change(self) -> TerminalStateChange | None:
        """The state change that triggered a watch, or ``None``."""
        return self._state_change

    def invalidate(self, area: Rectangle | None = None) -> None:
        """Request a redraw of ``area``, or of the whole target."""
        self._target.invalidate(area)

    def focus(self) -> bool:
        """Give the buffer input focus. Returns whether it could take it."""
        return self.runtime._focus(self._buffer)

    def stop(self) -> None:
        """Stop the runtime."""
        self.runtime.stop()


class FrameContext(CoreContext):
    """
    A frame callback's view: every layout and drawing uses this frame's destination.

    Args:
        area: The drawable rectangle of this frame.
        elapsed_seconds: Seconds on the runtime clock.
        delta_seconds: Seconds since the previous frame.
        damaged_areas: Screen areas that changed since the previous frame.
    """

    def __init__(
        self,
        *,
        area: Rectangle,
        elapsed_seconds: float,
        delta_seconds: float,
        damaged_areas: tuple[Rectangle, ...] = (),
        **extras: Unpack[ContextArguments],
    ) -> None:
        super().__init__(**extras)
        self._area = area
        self._elapsed_seconds = elapsed_seconds
        self._delta_seconds = delta_seconds
        self._damaged_areas = damaged_areas

    @property
    def area(self) -> Rectangle:
        """The drawable rectangle of this frame."""
        return self._area

    @property
    def elapsed_seconds(self) -> float:
        """Seconds on the runtime clock."""
        return self._elapsed_seconds

    @property
    def delta_seconds(self) -> float:
        """Seconds since the previous display frame."""
        return self._delta_seconds

    @property
    def damaged_areas(self) -> tuple[Rectangle, ...]:
        """Screen areas that changed since the previous frame."""
        return self._damaged_areas


class UpdateContext(CoreContext):
    """
    A simulation update's view.

    Args:
        elapsed_seconds: Seconds on the update's clock.
        delta_seconds: Seconds this update advances.
        is_fixed_step: Whether this is a fixed-step update.
    """

    def __init__(
        self,
        *,
        elapsed_seconds: float,
        delta_seconds: float,
        is_fixed_step: bool = False,
        **extras: Unpack[ContextArguments],
    ) -> None:
        super().__init__(**extras)
        self._elapsed_seconds = elapsed_seconds
        self._delta_seconds = delta_seconds
        self._is_fixed_step = is_fixed_step

    @property
    def elapsed_seconds(self) -> float:
        """Seconds on the update's clock."""
        return self._elapsed_seconds

    @property
    def delta_seconds(self) -> float:
        """Seconds this update advances."""
        return self._delta_seconds

    @property
    def is_fixed_step(self) -> bool:
        """Whether this is a fixed-step update."""
        return self._is_fixed_step


class EventContext(CoreContext):
    """
    A routed input event's view.

    Args:
        local_pointer: For mouse events, the pointer position relative to the target buffer.
    """

    def __init__(
        self,
        *,
        local_pointer: tuple[int, int] | None = None,
        **extras: Unpack[ContextArguments],
    ) -> None:
        super().__init__(**extras)
        self._local_pointer = local_pointer
        self._is_consumed = False

    @property
    def event(self) -> Event:
        """The event being handled."""
        if self._event is None:
            raise RuntimeError(
                'This context has no event. Read event only from an active event hook.'
            )
        return self._event

    @property
    def is_consumed(self) -> bool:
        """Whether a hook consumed the event."""
        return self._is_consumed

    @property
    def local_pointer(self) -> tuple[int, int] | None:
        """The pointer position relative to the target buffer, for mouse events."""
        return self._local_pointer

    def consume(self) -> None:
        """Stop the event from reaching any other hook."""
        self._is_consumed = True

    def capture_pointer(self) -> None:
        """Receive drag and release events until release, focus loss or unmount."""
        self.runtime._consume_pointer(self._buffer, True)

    def release_pointer(self) -> None:
        """Stop capturing the pointer."""
        self.runtime._consume_pointer(self._buffer, False)


class Extension(Protocol):
    """Something that adds operations to a registry."""

    @property
    def name(self) -> str:
        """A unique name; installing an extension twice with one name registers it once."""
        ...

    def register(self, registry: Registry) -> None:
        """Add this extension's operations to ``registry``."""
        ...


class Registry:
    """Operation handlers and extension installs for a buffer or runtime."""

    def __init__(self) -> None:
        self._handlers: dict[type, tuple[Callable[..., None], bool]] = {}
        self._installed: set[str] = set()

    def register(
        self,
        operation: type[OperationType],
        handler: Callable[[EvaluationContext, OperationType], None],
        *,
        requires_runtime: bool = False,
    ) -> None:
        """
        Apply ``operation`` instances with ``handler``.

        Args:
            operation: The operation class. Subclasses use their parent's handler unless
                they register their own.
            handler: Called as ``handler(context, operation)``.
            requires_runtime: Whether the handler needs an active runtime. Without one,
                applying the operation raises ``RuntimeRequiredError``.
        """
        self._handlers[operation] = (handler, requires_runtime)

    def _entry(self, operation_type: type) -> tuple[Callable[..., None], bool] | None:
        for candidate in operation_type.__mro__:
            entry = self._handlers.get(candidate)
            if entry is not None:
                return entry
        return None

    def resolve(
        self, operation: OperationType
    ) -> Callable[[EvaluationContext, OperationType], None]:
        """
        Return the function that applies ``operation``.

        Raises:
            UnsupportedOperationError: No handler is registered for the operation's type.
        """
        from xnano_core._xnano_core import RuntimeRequiredError, UnsupportedOperationError

        entry = self._entry(type(operation))
        if entry is None:
            name = type(operation).__name__
            raise UnsupportedOperationError(
                f'this registry cannot apply a {name}. Install the extension that '
                f'provides it with `registry.install(extension)` or register a handler '
                f'with `registry.register({name}, handler)`.'
            )
        handler, requires_runtime = entry
        if not requires_runtime:
            return handler

        def guarded(context: EvaluationContext, operation: OperationType) -> None:
            if context.runtime is None:
                raise RuntimeRequiredError(
                    f'{type(operation).__name__} needs a mounted target and an active '
                    f'runtime. Mount the buffer with Runtime.mount(buffer) and apply the '
                    f'operation through the mounted buffer.'
                )
            handler(context, operation)

        return guarded

    def supports(self, operation: type) -> bool:
        """Whether a handler exists for ``operation`` or one of its parents."""
        return self._entry(operation) is not None

    def install(self, extension: Extension) -> None:
        """Add an extension's operations. Installing it again does nothing."""
        if extension.name in self._installed:
            return
        self._installed.add(extension.name)
        extension.register(self)

    def copy(self) -> Registry:
        """A new registry with the same handlers and installs."""
        duplicate = Registry()
        duplicate._handlers = dict(self._handlers)
        duplicate._installed = set(self._installed)
        return duplicate


_default_registry = Registry()


def default_registry() -> Registry:
    """The registry used by buffers and runtimes that were not given one."""
    return _default_registry


class Rendering:
    """
    A lazy static or live render of a buffer.

    ``str(rendering)`` serializes without hooks, audio or terminal negotiation. Entering the
    rendering opens (or joins) a runtime and mounts the buffer immediately, without blocking;
    drive the work with the runtime's ``run()`` or ``step()``. Leaving unmounts the buffer and
    closes the runtime only if the rendering opened it. Exceptions are never suppressed.

    Args:
        buffer: The buffer to render.
        runtime: A runtime to mount on. Without one, entering opens a live runtime.
    """

    def __init__(self, buffer: Buffer, runtime: Runtime | None = None) -> None:
        self._buffer = buffer
        self._runtime = runtime
        self._owns_runtime = False
        self._is_mounted = False

    @property
    def buffer(self) -> Buffer:
        """The buffer being rendered."""
        return self._buffer

    def __str__(self) -> str:
        return self._buffer.render(format='ansi')

    def __enter__(self) -> CoreContext:
        if self._runtime is None:
            from xnano_core._xnano_core import Runtime

            self._runtime = Runtime.live()
            self._owns_runtime = True
        runtime = self._runtime
        try:
            runtime.__enter__()
            context = runtime.mount(self._buffer, geometry='inherit')
        except BaseException:
            if self._owns_runtime:
                runtime.close()
            raise
        self._is_mounted = True
        return context

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        runtime = self._runtime
        try:
            if runtime is not None and self._is_mounted and not runtime.is_closed:
                runtime.unmount(self._buffer)
        finally:
            self._is_mounted = False
            if runtime is not None and self._owns_runtime:
                runtime.close()
                self._runtime = None
                self._owns_runtime = False
        return False


async def _next_event(stream: EventStream) -> Event:
    """Wait for the next event of ``stream`` without blocking the asyncio loop."""
    import asyncio  # only programs that await events pay for asyncio

    runtime = stream._runtime
    wake = asyncio.Event()
    loop = asyncio.get_running_loop()
    token = runtime._add_notifier(lambda: loop.call_soon_threadsafe(wake.set))
    try:
        while True:
            event = stream._poll()
            if event is not None:
                return event
            if runtime.is_closed:
                raise StopAsyncIteration
            result = runtime.step(timeout_milliseconds=0)
            event = stream._poll()
            if event is not None:
                return event
            if not result.is_running:
                raise StopAsyncIteration
            if result.events_processed == 0 and not result.did_render:
                delay = runtime._next_deadline_seconds()
                wake.clear()
                try:
                    await asyncio.wait_for(wake.wait(), delay)
                except asyncio.TimeoutError:
                    pass
            else:
                await asyncio.sleep(0)
    finally:
        runtime._remove_notifier(token)
