"""scripts.vhs_recording"""

from __future__ import annotations

import os
from typing import Literal, TypeAlias

from xnano.color import ColorLike


ColorRole: TypeAlias = Literal["foreground", "background"]
"""Whether a color is applied as foreground or background during VHS remaps."""

DOC_BG_DARK = "#141519"
"""Docs dark page background — matches ``extras.css`` slate scheme."""

DOC_BG_LIGHT = "#F4F4ED"
"""Docs light page background — matches ``extras.css`` default scheme."""

MONO_FG_DARK = "#DEDCD1"
"""Single-tone foreground for dark showcase monotone recordings."""

MONO_FG_LIGHT = "#102044"
"""Single-tone foreground for light showcase monotone recordings."""


def get_vhs_theme_key() -> str:
    """Return the active docs theme key for VHS recordings.

    Returns:
        ``"dark"`` or ``"light"`` (defaults to ``"dark"``).
    """
    theme_key = os.environ.get("XNANO_VHS_THEME", "dark")
    if theme_key in ("dark", "light"):
        return theme_key
    return "dark"


def is_vhs_mono_mode() -> bool:
    """Return whether showcase monotone remapping is enabled."""
    return os.environ.get("XNANO_VHS_MONO") == "1"


def is_vhs_docs_background_mode() -> bool:
    """Return whether widget backgrounds should match the docs page."""
    return os.environ.get("XNANO_VHS_DOCS_BG") == "1" or is_vhs_mono_mode()


def get_vhs_color_cache_token() -> str:
    """Return a cache-busting token for native color memoization."""
    if is_vhs_mono_mode():
        return f"mono:{get_vhs_theme_key()}"
    if is_vhs_docs_background_mode():
        return f"docs_bg:{get_vhs_theme_key()}"
    return ""


def get_vhs_docs_background() -> str:
    """Return the docs-page background hex for the active VHS theme key."""
    if get_vhs_theme_key() == "light":
        return DOC_BG_LIGHT
    return DOC_BG_DARK


def get_vhs_mono_foreground() -> str:
    """Return the single-tone foreground hex for the active VHS theme key."""
    if get_vhs_theme_key() == "light":
        return MONO_FG_LIGHT
    return MONO_FG_DARK


def remap_color_for_vhs(
    color: ColorLike | None,
    *,
    role: ColorRole = "foreground",
) -> ColorLike | None:
    """Remap a color for VHS demo recordings when env flags are set.

    Args:
        color: Original color literal or ``Color`` instance.
        role: Whether the color is used as foreground or background.

    Returns:
        Remapped color, or the original when no VHS mode is active.
    """
    if is_vhs_mono_mode():
        if role == "background":
            return get_vhs_docs_background()
        return get_vhs_mono_foreground()

    # Docs-background mode intentionally leaves authored colors untouched.
    # The renderer now paints field backgrounds behind text cells only (not
    # the whole slot), so accent backgrounds such as a violet header read as
    # designed against the docs page and no longer need to be flattened.
    return color
