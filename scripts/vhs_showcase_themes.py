"""scripts.vhs_showcase_themes

---

VHS themes for showcase example GIFs (feed, kanban).
"""

from __future__ import annotations

import json

# Matches ``[data-md-color-scheme="default"] --md-default-bg-color``.
DOC_BG_LIGHT = "#F4F4ED"
"""Light docs page background."""

# Matches ``[data-md-color-scheme="slate"] --md-default-bg-color``.
DOC_BG_DARK = "#141519"
"""Dark docs page background."""

# Matches light ``--md-accent-fg-color``.
DOC_FG_LIGHT = "#102044"
"""Light docs primary text color."""

# Matches dark ``--md-primary-fg-color``.
DOC_FG_DARK = "#DEDCD1"
"""Dark docs primary text color."""

DOC_MARGINS = {
    "dark": DOC_BG_DARK,
    "light": DOC_BG_LIGHT,
}

# Single-tone foreground for monotone showcase recordings.
_MONO_FG = {
    "dark": "#DEDCD1",
    "light": "#102044",
}

_ANSII_KEYS = (
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
    "brightBlack",
    "brightRed",
    "brightGreen",
    "brightYellow",
    "brightBlue",
    "brightMagenta",
    "brightCyan",
    "brightWhite",
)

# Gruvbox-dark palette with docs background/foreground overrides.
_XNANO_DARK_THEME = {
    "name": "xnano-dark",
    "background": DOC_BG_DARK,
    "foreground": DOC_FG_DARK,
    "cursor": DOC_FG_DARK,
    "selection": "#2A3856",
    "black": "#3c3836",
    "red": "#cc241d",
    "green": "#98971a",
    "yellow": "#d79921",
    "blue": "#458588",
    "magenta": "#b16286",
    "cyan": "#689d6a",
    "white": "#a89984",
    "brightBlack": "#928374",
    "brightRed": "#fb4934",
    "brightGreen": "#b8bb26",
    "brightYellow": "#fabd2f",
    "brightBlue": "#83a598",
    "brightMagenta": "#d3869b",
    "brightCyan": "#8ec07c",
    "brightWhite": "#ebdbb2",
}

# Atom One Light palette with docs background/foreground overrides.
_XNANO_LIGHT_THEME = {
    "name": "xnano-light",
    "background": DOC_BG_LIGHT,
    "foreground": DOC_FG_LIGHT,
    "cursor": DOC_FG_LIGHT,
    "selection": "#85ACFA",
    "black": "#383a42",
    "red": "#e45649",
    "green": "#50a14f",
    "yellow": "#c18401",
    "blue": "#4078f2",
    "magenta": "#a626a4",
    "cyan": "#0184bc",
    "white": "#a0a1a7",
    "brightBlack": "#4f525e",
    "brightRed": "#e06c75",
    "brightGreen": "#98c379",
    "brightYellow": "#e5c07b",
    "brightBlue": "#61afef",
    "brightMagenta": "#c678dd",
    "brightCyan": "#56b6c2",
    "brightWhite": "#ffffff",
}

_DOC_THEMES = {
    "dark": _XNANO_DARK_THEME,
    "light": _XNANO_LIGHT_THEME,
}


def _build_monotone_theme(theme_key: str) -> dict[str, str]:
    background = DOC_MARGINS[theme_key]
    foreground = _MONO_FG[theme_key]
    theme = {
        "name": f"xnano-{theme_key}-mono",
        "background": background,
        "foreground": foreground,
        "cursor": foreground,
        "selection": background,
    }
    for key in _ANSII_KEYS:
        theme[key] = foreground
    return theme


_MONOTONE_THEMES = {
    "dark": _build_monotone_theme("dark"),
    "light": _build_monotone_theme("light"),
}


def get_margin_fill(theme_key: str) -> str:
    """Return the VHS ``MarginFill`` color for a docs theme key.

    Args:
        theme_key: ``"dark"`` or ``"light"``.

    Returns:
        Hex color matching the docs site background.
    """
    return DOC_MARGINS[theme_key]


def get_vhs_theme(theme_key: str) -> str:
    """Return a one-line JSON theme string for full-color showcase GIFs.

    Args:
        theme_key: ``"dark"`` or ``"light"``.

    Returns:
        Compact JSON object with terminal colors using docs bg/fg.
    """
    return json.dumps(_DOC_THEMES[theme_key], separators=(",", ":"))


def get_vhs_monotone_theme(theme_key: str) -> str:
    """Return a one-line JSON theme string for monotone showcase GIFs.

    Same docs-page background with every ANSI color mapped to a single
    foreground tone.

    Args:
        theme_key: ``"dark"`` or ``"light"``.

    Returns:
        Compact JSON monotone theme for VHS ``Set Theme``.
    """
    return json.dumps(_MONOTONE_THEMES[theme_key], separators=(",", ":"))