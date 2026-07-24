"""xnano.beta.utils.responsive

---

Viewport breakpoints and zero-cost detection of responsive render hooks.

Grids and components may declare size-specific render variants
(``grid_render_small``, ``compose_large``, …). They are opt-in: the base
class defines each as a marked no-op, and a class that overrides none
carries an empty override map — so the per-frame path skips all
breakpoint work entirely rather than probing methods every render.
"""

from __future__ import annotations

from typing import Any, Callable, Literal, TypeAlias

Breakpoint: TypeAlias = Literal[
    "extra_small",
    "small",
    "medium",
    "large",
    "extra_large",
]
"""One of the ordered viewport size names below."""

BREAKPOINT_NAMES: tuple[Breakpoint, ...] = (
    "extra_small",
    "small",
    "medium",
    "large",
    "extra_large",
)
"""Viewport size names, smallest to largest."""

# Exclusive upper bounds in terminal columns; the widest tier is
# unbounded. Chosen around common terminal widths — an 80-column window
# is ``medium``, a split pane is ``small``, a full-screen wide window is
# ``large``/``extra_large``.
_BREAKPOINT_UPPER_BOUNDS: tuple[tuple[Breakpoint, int], ...] = (
    ("extra_small", 40),
    ("small", 80),
    ("medium", 120),
    ("large", 160),
)

_RESPONSIVE_NOOP_ATTR = "_xnano_responsive_noop"


def breakpoint_for_width(width: int) -> Breakpoint:
    """Return the breakpoint name for a viewport ``width`` in columns."""
    for name, upper in _BREAKPOINT_UPPER_BOUNDS:
        if width < upper:
            return name
    return "extra_large"


def responsive_noop(method: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a base render variant as an unoverridden no-op.

    Detection compares against this marker rather than a base class, so
    the same helper works for grids and components without either needing
    to reference the other's base type during class creation.
    """
    setattr(method, _RESPONSIVE_NOOP_ATTR, True)
    return method


def collect_responsive_overrides(
    cls: type,
    prefix: str,
) -> dict[Breakpoint, str]:
    """Map each overridden ``{prefix}{size}`` variant to its method name.

    Returns an empty dict when a class overrides none, which callers use
    to gate every breakpoint computation. Computed once per class at
    creation time.
    """
    overrides: dict[Breakpoint, str] = {}
    for size in BREAKPOINT_NAMES:
        method_name = f"{prefix}{size}"
        method = getattr(cls, method_name, None)
        if method is not None and not getattr(
            method, _RESPONSIVE_NOOP_ATTR, False
        ):
            overrides[size] = method_name
    return overrides


def resolve_responsive_variant(
    overrides: dict[Breakpoint, str] | None,
    width: int,
) -> str | None:
    """Return the variant method name for ``width``, or ``None``.

    ``None`` means "use the base method": either the class overrides no
    variants, or none covers the current breakpoint.
    """
    if not overrides:
        return None
    return overrides.get(breakpoint_for_width(width))


__all__ = (
    "BREAKPOINT_NAMES",
    "Breakpoint",
    "breakpoint_for_width",
    "collect_responsive_overrides",
    "resolve_responsive_variant",
    "responsive_noop",
)
