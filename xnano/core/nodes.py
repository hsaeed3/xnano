"""xnano.core.nodes

---

Shared structural base for drawable nodes (z-index and visibility).

Interface kinds define their own drawing methods on top of this base —
for example ``AbstractTerminalNode`` in ``xnano.tui.nodes`` — because
measurement and paint differ between terminal cells and browser layout.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import ClassVar, Literal, TypeAlias

NodeKind: TypeAlias = Literal["terminal", "web"]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AbstractNode(abc.ABC):
    """Abstract base class for a node that can be rendered by a controller
    onto a viewport area.

    A `Node` is a low-level intermediate representation (based on interface
    type (TUI, web UI, etc.)) of what to draw within a specific region.
    """

    kind: ClassVar[NodeKind]
    """The interface kind this node's widget or content maps to. This can be
    either one of "terminal" or "web".
    """

    z: int = 0
    """Z-index used when layering overlapping nodes."""
    visible: bool = True
    """Whether this node is painted at all."""


__all__ = (
    "AbstractNode",
    "NodeKind",
)
