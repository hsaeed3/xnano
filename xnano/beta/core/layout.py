"""xnano.beta.core.layout

---

Describe fixed, proportional, and content-sized grid constraints.
"""

from __future__ import annotations

import dataclasses
from typing import Literal, TypeAlias

LayoutConstraintKind: TypeAlias = Literal[
    "length",
    "percentage",
    "fill",
    "content",
    "min",
    "max",
    "ratio",
]
"""Sizing strategy used for one grid slot."""


@dataclasses.dataclass(frozen=True, slots=True)
class LayoutConstraint:
    """Sizing strategy and values for one grid slot.

    Example:
        ``LayoutConstraint(kind="percentage", value=50)``

    Attributes:
        kind: Constraint strategy.
        value: Primary length, percentage, weight, or ratio numerator.
        value2: Ratio denominator.
    """

    kind: LayoutConstraintKind
    """Constraint strategy."""
    value: int = 1
    """Primary constraint value."""
    value2: int = 1
    """Ratio denominator."""


__all__ = ("LayoutConstraint", "LayoutConstraintKind")
