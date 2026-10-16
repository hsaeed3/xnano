"""
xnano.types

The types that describe what `xnano` accepts: positions and sizes as an axis, anything that can
be added to a canvas, space around text, pixel encodings, the settings of a canvas and of the
screen it is opened on, and the functions that hook into events.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict

import xnano_core as _core
from xnano._appearance import (
    Spacing as Spacing,
)
from xnano._appearance import (
    SpacingDictionary as SpacingDictionary,
)
from xnano._hooks import (
    Hook as Hook,
)
from xnano._hooks import (
    HookGenerator as HookGenerator,
)
from xnano._hooks import (
    HookKind as HookKind,
)
from xnano._hooks import (
    When as When,
)
from xnano._values import (
    Axis as Axis,
)
from xnano._values import (
    ColorValue,
)
from xnano._values import (
    Content as Content,
)
from xnano._values import (
    HeldMouseButtonName as HeldMouseButtonName,
)
from xnano._values import (
    KeyName as KeyName,
)
from xnano._values import (
    PixelEncoding as PixelEncoding,
)
from xnano._values import (
    RangeBound as RangeBound,
)
from xnano._values import (
    Renderable as Renderable,
)

__all__ = [
    'AppearanceArguments',
    'Axis',
    'CanvasAppearanceArguments',
    'CanvasSettings',
    'Content',
    'GateSettings',
    'HeldMouseButtonName',
    'Hook',
    'HookGenerator',
    'HookKind',
    'KeyName',
    'OpenSettings',
    'PixelEncoding',
    'RangeBound',
    'Renderable',
    'Spacing',
    'SpacingDictionary',
    'When',
]


class GateSettings(TypedDict, total=False):
    """
    What a screen reports to a canvas: the input gates of ``new()`` and ``open()``.

    A canvas stores the gates it is given and applies them when it is opened on a screen;
    a canvas without a screen has no device to report anything, and events pushed with
    [`Canvas.push`][xnano.canvas.Canvas.push] reach hooks whatever the gates say. A gate that
    is left out takes its default. ``mouse``, ``scroll`` and ``paste`` are turned on when the
    canvas is opened if a hook registered before that needs them; a gate given as ``False``
    stays off, and a hook that needs it raises a
    [`TerminalError`][xnano.errors.TerminalError] that says which gate to turn on.

    Attributes:
        mouse: ``True`` reports button presses, releases and drags; ``'motion'`` reports
            every movement as well. Off by default. The wheel is the ``scroll`` gate.
        scroll: Whether the mouse wheel is reported. Off by default.
        keyboard: ``True`` for ordinary key presses, ``'disambiguated'`` to tell keys such as
            ``escape`` and ``alt+key`` apart, ``'release_events'`` to also report repeats and
            releases, and ``False`` to ignore keys. ``True`` by default.
        paste: Whether pasted text arrives as one paste event instead of as key presses.
            On by default.
        focus: Whether the window gaining and losing focus is reported. On by default.
        interrupt: Whether ``Ctrl-C`` ends the loop. ``False`` delivers it as a key press.
            On by default.
        capture: Whether text printed while the screen is in use is held back and printed
            when the canvas closes. On by default.
        clear: Whether what was drawn is erased when the canvas closes. On by default.
        alternate_screen: Whether a full-window canvas draws on the alternate screen, so the
            shell's history comes back untouched. On by default.
    """

    mouse: bool | Literal['motion']
    """``True`` for presses, releases and drags; ``'motion'`` for every movement too."""
    scroll: bool
    """Whether the mouse wheel is reported."""
    keyboard: bool | Literal['disambiguated', 'release_events']
    """Which key events are reported, or ``False`` for none."""
    paste: bool
    """Whether pasted text arrives as one paste event."""
    focus: bool
    """Whether the window gaining and losing focus is reported."""
    interrupt: bool
    """Whether ``Ctrl-C`` ends the loop."""
    capture: bool
    """Whether printed text is held back while the screen is in use."""
    clear: bool
    """Whether what was drawn is erased when the canvas closes."""
    alternate_screen: bool
    """Whether a full-window canvas draws on the alternate screen."""


class CanvasAppearanceArguments(TypedDict, total=False):
    """
    How a canvas itself looks: its colors, text modifiers and border.

    These style the canvas, not what is written into it, so ``new()`` and ``open()`` accept
    them only without content. ``title`` is not one of them: on ``new()`` and ``open()`` it is
    the window title.

    Attributes:
        style: A ready-made style that the colors and modifiers are applied over.
        foreground: The color of the cells no content covers.
        background: The color behind the cells no content covers.
        is_bold: Whether the canvas's own cells are bold.
        is_dim: Whether they are dimmed.
        is_italic: Whether they are italic.
        is_underlined: Whether they are underlined.
        is_blinking: Whether they blink.
        is_reversed: Whether foreground and background are swapped.
        is_hidden: Whether they are hidden.
        is_crossed_out: Whether they are struck through.
        border: The kind of border around the canvas.
        border_style: The style of the border.
    """

    style: _core.Style | None
    """A ready-made style that the colors and modifiers are applied over."""
    foreground: ColorValue | None
    """The foreground color."""
    background: ColorValue | None
    """The background color."""
    is_bold: bool
    """Whether the cells are bold."""
    is_dim: bool
    """Whether the cells are dimmed."""
    is_italic: bool
    """Whether the cells are italic."""
    is_underlined: bool
    """Whether the cells are underlined."""
    is_blinking: bool
    """Whether the cells blink."""
    is_reversed: bool
    """Whether foreground and background are swapped."""
    is_hidden: bool
    """Whether the cells are hidden."""
    is_crossed_out: bool
    """Whether the cells are struck through."""
    border: _core.BorderKind | None
    """The kind of border."""
    border_style: _core.Style | None
    """The style of the border."""


class AppearanceArguments(CanvasAppearanceArguments, total=False):
    """
    How written content looks: the appearance keywords of ``write``.

    Attributes:
        title: A title on the border of the content.
        padding: Space between the border and the content.
        margin: Space outside the border.
    """

    title: str | None
    """A title on the border."""
    padding: Spacing | None
    """Space between the border and the content."""
    margin: Spacing | None
    """Space outside the border."""


class CanvasSettings(GateSettings, CanvasAppearanceArguments, total=False):
    """
    The keyword settings of [`new`][xnano.new]: the input gates and the canvas's own look.

    Every key is described where it is declared, in
    [`GateSettings`][xnano.types.GateSettings] and
    [`CanvasAppearanceArguments`][xnano.types.CanvasAppearanceArguments].

    Attributes:
        mouse: See [`GateSettings`][xnano.types.GateSettings]; the same for ``scroll``,
            ``keyboard``, ``paste``, ``focus``, ``interrupt``, ``capture``, ``clear`` and
            ``alternate_screen``.
        background: See [`CanvasAppearanceArguments`][xnano.types.CanvasAppearanceArguments];
            the same for the other appearance keys.
    """


class OpenSettings(CanvasSettings, total=False):
    """
    The keyword settings of [`Canvas.open`][xnano.canvas.Canvas.open] and of
    [`open`][xnano.open] given a canvas.

    Everything ``new()`` takes except ``realtime`` (a screen always runs in real time) and the
    content. ``deps`` and ``state`` are accepted only by a canvas created without them.

    Attributes:
        fps: The most frames drawn per second.
        bpm: Beats per minute for beat hooks, notes and melodies.
        effects: Effects to apply to the canvas, as dictionaries with a ``kind`` key.
        deps: The dependencies hooks and components read as ``context.deps``.
        state: A dataclass instance the canvas keeps and validates.
    """

    fps: float
    """The most frames drawn per second."""
    bpm: float
    """Beats per minute."""
    effects: Sequence[Mapping[str, object]]
    """Effects to apply, as dictionaries with a ``kind`` key."""
    deps: object
    """The dependencies hooks read as ``context.deps``."""
    state: object
    """A dataclass instance the canvas keeps and validates."""
