"""xnano.console"""

from __future__ import annotations

from typing import Literal, TypeAlias

from xnano import _core


ConsoleColorName: TypeAlias = Literal[
    "reset",
    "black",
    "dark_grey",
    "red",
    "dark_red",
    "green",
    "dark_green",
    "yellow",
    "dark_yellow",
    "blue",
    "dark_blue",
    "magenta",
    "dark_magenta",
    "cyan",
    "dark_cyan",
    "white",
    "grey",
    "ansi_value",
    "rgb",
]
"""Console color names supported by crossterm."""


ConsoleAttributeName: TypeAlias = Literal[
    "reset",
    "bold",
    "dim",
    "italic",
    "underlined",
    "double_underlined",
    "undercurled",
    "underdotted",
    "underdashed",
    "slow_blink",
    "rapid_blink",
    "reverse",
    "hidden",
    "crossed_out",
    "fraktur",
    "no_bold",
    "normal_intensity",
    "no_italic",
    "no_underline",
    "no_blink",
    "no_reverse",
    "no_hidden",
    "not_crossed_out",
    "framed",
    "encircled",
    "overlined",
    "not_framed_or_encircled",
    "not_overlined",
]
"""Console text attribute names supported by crossterm."""


_CONSOLE_COLOR: dict[ConsoleColorName, _core.ConsoleColor] = {
    "reset": _core.ConsoleColor.Reset,
    "black": _core.ConsoleColor.Black,
    "dark_grey": _core.ConsoleColor.DarkGrey,
    "red": _core.ConsoleColor.Red,
    "dark_red": _core.ConsoleColor.DarkRed,
    "green": _core.ConsoleColor.Green,
    "dark_green": _core.ConsoleColor.DarkGreen,
    "yellow": _core.ConsoleColor.Yellow,
    "dark_yellow": _core.ConsoleColor.DarkYellow,
    "blue": _core.ConsoleColor.Blue,
    "dark_blue": _core.ConsoleColor.DarkBlue,
    "magenta": _core.ConsoleColor.Magenta,
    "dark_magenta": _core.ConsoleColor.DarkMagenta,
    "cyan": _core.ConsoleColor.Cyan,
    "dark_cyan": _core.ConsoleColor.DarkCyan,
    "white": _core.ConsoleColor.White,
    "grey": _core.ConsoleColor.Grey,
    "ansi_value": _core.ConsoleColor.AnsiValue,
    "rgb": _core.ConsoleColor.Rgb,
}


_CONSOLE_ATTRIBUTE: dict[ConsoleAttributeName, _core.ConsoleAttribute] = {
    "reset": _core.ConsoleAttribute.Reset,
    "bold": _core.ConsoleAttribute.Bold,
    "dim": _core.ConsoleAttribute.Dim,
    "italic": _core.ConsoleAttribute.Italic,
    "underlined": _core.ConsoleAttribute.Underlined,
    "double_underlined": _core.ConsoleAttribute.DoubleUnderlined,
    "undercurled": _core.ConsoleAttribute.Undercurled,
    "underdotted": _core.ConsoleAttribute.Underdotted,
    "underdashed": _core.ConsoleAttribute.Underdashed,
    "slow_blink": _core.ConsoleAttribute.SlowBlink,
    "rapid_blink": _core.ConsoleAttribute.RapidBlink,
    "reverse": _core.ConsoleAttribute.Reverse,
    "hidden": _core.ConsoleAttribute.Hidden,
    "crossed_out": _core.ConsoleAttribute.CrossedOut,
    "fraktur": _core.ConsoleAttribute.Fraktur,
    "no_bold": _core.ConsoleAttribute.NoBold,
    "normal_intensity": _core.ConsoleAttribute.NormalIntensity,
    "no_italic": _core.ConsoleAttribute.NoItalic,
    "no_underline": _core.ConsoleAttribute.NoUnderline,
    "no_blink": _core.ConsoleAttribute.NoBlink,
    "no_reverse": _core.ConsoleAttribute.NoReverse,
    "no_hidden": _core.ConsoleAttribute.NoHidden,
    "not_crossed_out": _core.ConsoleAttribute.NotCrossedOut,
    "framed": _core.ConsoleAttribute.Framed,
    "encircled": _core.ConsoleAttribute.Encircled,
    "overlined": _core.ConsoleAttribute.OverLined,
    "not_framed_or_encircled": _core.ConsoleAttribute.NotFramedOrEncircled,
    "not_overlined": _core.ConsoleAttribute.NotOverLined,
}


def _core_console_color(value: ConsoleColorName) -> _core.ConsoleColor:
    return _CONSOLE_COLOR[value]


def _core_console_attribute(
    value: ConsoleAttributeName,
) -> _core.ConsoleAttribute:
    return _CONSOLE_ATTRIBUTE[value]


def set_foreground_color(
    color: ConsoleColorName,
    *,
    ansi_value: int | None = None,
    rgb: tuple[int, int, int] | None = None,
) -> None:
    """Set the console foreground color."""
    _core.set_foreground_color(
        _core_console_color(color),
        ansi_value=ansi_value,
        rgb=rgb,
    )


def set_background_color(
    color: ConsoleColorName,
    *,
    ansi_value: int | None = None,
    rgb: tuple[int, int, int] | None = None,
) -> None:
    """Set the console background color."""
    _core.set_background_color(
        _core_console_color(color),
        ansi_value=ansi_value,
        rgb=rgb,
    )


def reset_color() -> None:
    """Reset console colors to the terminal default."""
    _core.reset_color()


def set_attribute(attribute: ConsoleAttributeName) -> None:
    """Set a console text attribute."""
    _core.set_attribute(_core_console_attribute(attribute))


def print_styled_content(
    text: str,
    *,
    foreground: ConsoleColorName | None = None,
    background: ConsoleColorName | None = None,
    attribute: ConsoleAttributeName | None = None,
    foreground_ansi: int | None = None,
    background_ansi: int | None = None,
    foreground_rgb: tuple[int, int, int] | None = None,
    background_rgb: tuple[int, int, int] | None = None,
) -> None:
    """Print styled text directly to stdout."""
    _core.print_styled_content(
        text,
        foreground=(
            _core_console_color(foreground) if foreground is not None else None
        ),
        background=(
            _core_console_color(background) if background is not None else None
        ),
        attribute=(
            _core_console_attribute(attribute)
            if attribute is not None
            else None
        ),
        foreground_ansi=foreground_ansi,
        background_ansi=background_ansi,
        foreground_rgb=foreground_rgb,
        background_rgb=background_rgb,
    )


def print_text(text: str) -> None:
    """Print plain text directly to stdout."""
    _core.print_text(text)


def flush_stdout_buffer() -> None:
    """Flush queued stdout commands."""
    _core.flush_stdout_buffer()


__all__ = (
    "ConsoleAttributeName",
    "ConsoleColorName",
    "flush_stdout_buffer",
    "print_styled_content",
    "print_text",
    "reset_color",
    "set_attribute",
    "set_background_color",
    "set_foreground_color",
)
