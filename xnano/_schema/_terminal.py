"""
xnano._schema._terminal

The settings that `new` and `open` take, the terminal settings of the screen and the look of the
canvas, and the names of what a terminal reports about itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict

import xnano_core as _core
from xnano._schema._appearance import CanvasAppearanceArguments
from xnano._schema._layout import CanvasLayout, EdgeBehavior

if TYPE_CHECKING:
    from xnano._schema._effects import WritableEffectSpecification

ColorProfile: TypeAlias = _core.ColorProfile
"""
How many colors a terminal displays.

``'no_terminal'`` means standard output is not a terminal at all, such as a pipe or a file.
``'no_color'`` is a terminal that displays no colors. ``'ansi16'`` displays the 16 basic colors,
``'ansi256'`` displays 256 and ``'truecolor'`` displays any RGB color.

Maps to [`xnano_core.ColorProfile`][xnano_core.ColorProfile].
"""

GraphicsProtocol: TypeAlias = _core.GraphicsProtocol
"""
How images are drawn into a terminal.

``'half_blocks'`` draws an image with colored half-block characters, which every terminal that
shows colors can display. ``'sixel'``, ``'kitty'`` and ``'iterm2'`` are the image protocols of
terminals that can draw real pixels.

Maps to [`xnano_core.GraphicsProtocol`][xnano_core.GraphicsProtocol].
"""

CapabilityStatus: TypeAlias = _core.CapabilityStatus
"""
Whether a terminal feature is available.

``'unknown'`` means the terminal did not answer, so the feature may or may not work.

Maps to [`xnano_core.CapabilityStatus`][xnano_core.CapabilityStatus].
"""


class TerminalSettings(TypedDict, total=False):
    """
    What a canvas asks the terminal for: the input it reports and how the screen is used.

    A canvas stores the terminal settings it is given and applies them when it is opened on a
    screen; a canvas without a screen has no device to report anything, and events pushed with
    [`Canvas.push`][xnano.canvas.Canvas.push] reach hooks whatever the settings say. A setting
    that is left out takes its default. ``mouse``, ``scroll`` and ``paste`` are turned on when
    the canvas is opened if a hook registered before that needs them; a setting given as
    ``False`` stays off, and a hook that needs it raises a
    [`TerminalError`][xnano.errors.TerminalError] that says which setting to turn on.

    Attributes:
        mouse: ``True`` reports button presses, releases and drags; ``'motion'`` reports
            every movement as well. Unset by default: turned on when a hook registered before
            the canvas is opened needs it. The wheel is the ``scroll`` setting.
        scroll: Whether the mouse wheel is reported. Unset by default: turned on when a hook
            registered before the canvas is opened needs it.
        keyboard: ``True`` for ordinary key presses, ``'disambiguated'`` to tell keys such as
            ``escape`` and ``alt+key`` apart, ``'release_events'`` to also report repeats and
            releases, and ``False`` to ignore keys. ``True`` by default.
        paste: Whether pasted text arrives as one paste event instead of as key presses.
            Unset by default, which means on.
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


class CanvasSettings(TerminalSettings, CanvasAppearanceArguments, total=False):
    """
    The keyword settings of [`new`][xnano.new]: the terminal settings and the canvas's own look.

    Every key is described where it is declared, in
    [`TerminalSettings`][xnano.terminal.TerminalSettings] and
    [`CanvasAppearanceArguments`][xnano.styles.CanvasAppearanceArguments].

    Attributes:
        mouse: See [`TerminalSettings`][xnano.terminal.TerminalSettings]; the same for ``scroll``,
            ``keyboard``, ``paste``, ``focus``, ``interrupt``, ``capture``, ``clear`` and
            ``alternate_screen``.
        background: See [`CanvasAppearanceArguments`][xnano.styles.CanvasAppearanceArguments];
            the same for the other appearance keys.
        layout: How the canvas places what is written on it; see
            [`CanvasLayout`][xnano.canvas.CanvasLayout]. ``'overlay'`` when left out.
        edges: What content written on the canvas does at the edges of its area, unless it
            is given its own; see [`EdgeBehavior`][xnano.layout.EdgeBehavior]. ``'clip'``
            when left out.
    """

    layout: CanvasLayout
    """How the canvas places what is written on it."""
    edges: EdgeBehavior
    """What content does at the edges of its area."""


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
    effects: Sequence[WritableEffectSpecification]
    """Effects to apply, as dictionaries with a ``kind`` key."""
    deps: object
    """The dependencies hooks read as ``context.deps``."""
    state: object
    """A dataclass instance the canvas keeps and validates."""
