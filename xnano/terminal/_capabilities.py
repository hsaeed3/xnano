"""
xnano.terminal._capabilities

What the terminal can show and report, as xnano values.
"""

from __future__ import annotations

import dataclasses

import xnano_core as _core
from xnano._schema._terminal import CapabilityStatus, ColorProfile, GraphicsProtocol
from xnano.errors import TerminalAlreadyOpenError
from xnano.terminal import _screen


@dataclasses.dataclass(frozen=True, slots=True)
class KeyboardCapabilities:
    """
    What the keys of the terminal can report.

    A terminal reports every key press. Whether it can also tell ``escape`` from the start of
    ``alt+key``, report a key being held or released, or report a modifier key on its own
    depends on the enhanced keyboard protocol, which a terminal may or may not offer.

    Maps to [`xnano_core.KeyboardCapabilities`][xnano_core.KeyboardCapabilities].

    Attributes:
        enhancement: Whether the terminal offers the enhanced keyboard protocol.
        can_disambiguate_keys: Whether keys such as ``escape`` and ``alt+key`` are told apart.
        can_report_release_events: Whether key repeats and releases are reported.
        can_report_modifier_keys: Whether modifier keys on their own are reported.
        unavailable_reason: Why the enhanced protocol is unavailable, or ``None``.
    """

    enhancement: CapabilityStatus
    """Whether the terminal offers the enhanced keyboard protocol, or ``'unknown'``."""
    can_disambiguate_keys: bool
    """
    Whether keys such as ``escape`` and ``alt+key`` are told apart.

    This is what [`keyboard='disambiguated'`][xnano.types.TerminalSettings] asks for.
    """
    can_report_release_events: bool
    """
    Whether key repeats and releases are reported.

    This is what [`keyboard='release_events'`][xnano.types.TerminalSettings] asks for.
    """
    can_report_modifier_keys: bool
    """Whether modifier keys such as ``shift`` and ``ctrl`` are reported on their own."""
    unavailable_reason: str | None
    """Why the enhanced protocol is unavailable, or ``None`` when no reason is known."""


@dataclasses.dataclass(frozen=True, slots=True)
class GraphicsCapabilities:
    """
    How the terminal can draw images.

    Maps to [`xnano_image.TerminalGraphics`][xnano_image.TerminalGraphics], read from the
    ``graphics_protocol`` and ``cell_size_in_pixels`` of
    [`xnano_core.TerminalCapabilities`][xnano_core.TerminalCapabilities], so it needs no
    extra installed.

    Attributes:
        protocol: The best image protocol the terminal supports.
        cell_size_in_pixels: The ``(width, height)`` of one cell in pixels, or ``None``.
    """

    protocol: GraphicsProtocol
    """The best image protocol the terminal supports, or ``'half_blocks'``."""
    cell_size_in_pixels: tuple[int, int] | None
    """The ``(width, height)`` of one cell in pixels, or ``None`` when it is not known."""


@dataclasses.dataclass(frozen=True, slots=True)
class TerminalCapabilities:
    """
    What the terminal can show and report.

    Read it with [`capabilities`][xnano.terminal.capabilities] before a canvas is opened, or
    with [`Terminal.capabilities`][xnano.terminal.Terminal.capabilities] on an open terminal.

    Maps to [`xnano_core.TerminalCapabilities`][xnano_core.TerminalCapabilities].

    Attributes:
        is_available: Whether a canvas can be put on the screen here.
        colors: How many colors the terminal displays.
        keyboard: What the keys of the terminal can report.
        graphics: How the terminal can draw images.
    """

    is_available: bool
    """Whether a canvas can be put on the screen here."""
    colors: ColorProfile
    """How many colors the terminal displays."""
    keyboard: KeyboardCapabilities
    """What the keys of the terminal can report."""
    graphics: GraphicsCapabilities
    """How the terminal can draw images."""


def capabilities_from_core(
    terminal: _core.TerminalCapabilities, keyboard: _core.KeyboardCapabilities
) -> TerminalCapabilities:
    """Build the value that users read from the two answers of the core."""
    return TerminalCapabilities(
        is_available=terminal.is_terminal and terminal.is_live_terminal_available,
        colors=terminal.color_profile,
        keyboard=KeyboardCapabilities(
            enhancement=keyboard.enhancement,
            can_disambiguate_keys=keyboard.disambiguates_keys,
            can_report_release_events=keyboard.reports_event_types,
            can_report_modifier_keys=keyboard.reports_all_keys,
            unavailable_reason=keyboard.unavailable_reason,
        ),
        graphics=GraphicsCapabilities(
            protocol=terminal.graphics_protocol,
            cell_size_in_pixels=terminal.cell_size_in_pixels,
        ),
    )


def capabilities() -> TerminalCapabilities:
    """
    Ask the terminal this program runs in what it can show and report.

    The answer says how many colors the terminal displays, which image protocol it can draw
    with, whether its keyboard reports key releases, and whether a canvas can be put on its
    screen at all. Call it before opening a canvas, to choose colors or a graphics protocol
    that suit the terminal. It waits a fraction of a second for the terminal to answer, and a
    status the terminal did not answer is ``'unknown'``.

    While a canvas is on the screen it reads the terminal's input, so the terminal cannot be
    asked again. Read [`Terminal.capabilities`][xnano.terminal.Terminal.capabilities] on the
    open terminal instead.

    Returns:
        What the terminal can show and report. ``is_available`` is ``False`` when the program
        does not run in a terminal.

    Raises:
        TerminalAlreadyOpenError: A canvas is on the screen.

    Examples:
        ```python
        import xnano

        terminal_capabilities = xnano.terminal.capabilities()
        assert terminal_capabilities.colors in (
            'no_terminal',
            'no_color',
            'ansi16',
            'ansi256',
            'truecolor',
        )
        assert terminal_capabilities.graphics.protocol in (
            'half_blocks',
            'sixel',
            'kitty',
            'iterm2',
        )
        ```
    """
    if _screen.is_screen_claimed:
        raise TerminalAlreadyOpenError(
            'xnano.terminal.capabilities() asks the terminal directly, and it cannot while a '
            'canvas is on the screen reading its input, because the canvas would take the '
            'answer. Read terminal.capabilities on the open terminal instead, which holds what '
            'the terminal answered when the canvas was opened, or call '
            'xnano.terminal.capabilities() before opening a canvas.'
        )
    return capabilities_from_core(
        _core.detect_terminal_capabilities(), _core.query_keyboard_capabilities()
    )
