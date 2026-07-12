"""scripts.vhs_doc_themes

---

VHS margin colors aligned with ``docs/stylesheets/extras.css``.
"""

from __future__ import annotations

# Matches ``[data-md-color-scheme="default"] --md-default-bg-color``.
DOC_BG_LIGHT = "#F4F4ED"
"""Light docs page background."""

# Matches ``[data-md-color-scheme="slate"] --md-default-bg-color``.
DOC_BG_DARK = "#141519"
"""Dark docs page background."""

VHS_THEMES = {
    "dark": "GruvboxDark",
    "light": "AtomOneLight",
}
"""Built-in VHS terminal themes — only ``MarginFill`` is overridden to docs bg."""

DOC_MARGINS = {
    "dark": DOC_BG_DARK,
    "light": DOC_BG_LIGHT,
}


def get_theme_name(theme_key: str) -> str:
    """Return a built-in VHS theme name for ``Set Theme``.

    Args:
        theme_key: ``"dark"`` or ``"light"``.

    Returns:
        Theme name accepted by VHS.
    """
    return VHS_THEMES[theme_key]


def get_margin_fill(theme_key: str) -> str:
    """Return the VHS ``MarginFill`` color for a docs theme key.

    Args:
        theme_key: ``"dark"`` or ``"light"``.

    Returns:
        Hex color matching the docs site background.
    """
    return DOC_MARGINS[theme_key]
