"""xnano.core.nodes.abstract

A node is the smallest unit of drawable content in xnano: a span of text,
a progress bar, a frame around some other node, and so on. Every interface
xnano supports (terminal today, web later) has its own family of node
types, and this module defines the base every one of them shares.

That shared base only covers structure, not behavior: a z-index for
layering, and a visibility flag. It does not define how a node draws
itself, because that genuinely differs between interfaces. A terminal
node measures its own size in character cells, because nothing else will
— there's no layout engine underneath it. A web node has no equivalent
step, because the browser's layout engine handles that instead. Giving
both a shared "draw yourself" method would only paper over that
difference, not remove it.

So each interface defines its own base with its own drawing methods —
see `AbstractTerminalNode` in `xnano.core.nodes.terminal` — and every
concrete node (a span, a paragraph, a frame, ...) implements those methods
on itself. This matters beyond style: the previous implementation
(`xnano.beta.core.nodes.NodeAssembler`) instead used one big function that
checked "is this node a paragraph? a table? a chart?" one type at a time,
and had to repeat that same check across three separate functions
(measuring, building, and lowering nodes) that could drift out of sync
with each other. Letting each node describe its own behavior removes that
whole class of bug and means adding a new node type never requires
touching code outside that node's own class.
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
