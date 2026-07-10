"""xnano.components.abstract

---

`AbstractComponent` is the base every built-in component (`Text`, `Table`,
`Chart`, `Progress`, `Sparkline`, ...) inherits from. A component composes
one or more render nodes from a declarative definition — the same relationship
`Grid` has to `Field`, just for widget-shaped content instead of layout.

A component supports an interface (terminal, web) by implementing that
interface's `get_*_node` method: `get_terminal_node` for the terminal,
`get_web_node` for the web. Both default to returning `None` and are
entirely opt-in — a controller only ever calls the one method matching its
own interface, so a terminal-only component (everything built in today)
never has to define or think about the other one. A component that wants
to support both interfaces implements both methods side by side, each
free to compose a completely different node tree since the two interfaces
have no shared node representation.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any, Generic, TypeVar, TYPE_CHECKING

from xnano.types import Size

if TYPE_CHECKING:
    from xnano.core.nodes.terminal import AbstractTerminalNode
    from xnano.frame import Frame
    from xnano.terminal import Terminal
    from xnano.types import Area


StateT = TypeVar("StateT")


@dataclasses.dataclass(frozen=True, slots=True)
class ComponentRenderContext(Generic[StateT]):
    """Render-time scope passed to component hooks.

    Attributes:
        area: The `Area` to render.
        terminal: The `Terminal` to render.
        state: The `StateT` to render.
        component: The `AbstractComponent` to render.
    """

    area: "Area"
    terminal: "Terminal[StateT] | None" = None
    state: StateT | None = None
    component: "AbstractComponent | None" = None


@dataclasses.dataclass
class AbstractComponent(abc.ABC):
    """Abstract base class for a declarative, multi-interface UI component.

    Every hook here is opt-in — a plain `AbstractComponent` renders as
    nothing on every interface. Implement `get_terminal_node` and/or
    `get_web_node` to give a component a representation on one or both
    interfaces.
    """

    visible: bool = dataclasses.field(default=True, kw_only=True)
    z: int = dataclasses.field(default=0, kw_only=True)
    fit_content: bool = dataclasses.field(default=True, kw_only=True)

    def get_frame(self) -> "Frame | None":
        """Return an optional frame panel to wrap the composed content of
        this component around.

        Returns:
            An optional `Frame` to wrap the composed content of this
            component around.
        """
        return None

    def get_size(self, ctx: ComponentRenderContext[StateT]) -> Size:
        """Return the preferred cell size of this component.

        Args:
            ctx: The `ComponentRenderContext` to measure.
        """
        return Size(width=0, height=0)

    def before_render(
        self,
        ctx: ComponentRenderContext[StateT],
        area: "Area",
    ) -> "Area":
        """Called before rendering; returns the effective render area.

        Args:
            ctx: The `ComponentRenderContext` before rendering.
            area: The `Area` to render.

        Returns:
            The effective `Area` to render.
        """
        return area

    def after_render(
        self,
        ctx: ComponentRenderContext[StateT],
        area: "Area",
    ) -> None:
        """Called after rendering; should perform any post-render clean up
        or side effects.

        Args:
            ctx: The `ComponentRenderContext` after rendering.
            area: The `Area` after rendering.
        """
        return None

    def get_terminal_node(
        self, ctx: ComponentRenderContext[StateT]
    ) -> "AbstractTerminalNode | None":
        """Prepare the terminal render node tree for this component.

        Args:
            ctx: The `ComponentRenderContext` to prepare the node for.

        Returns:
            The terminal render node for this component, or `None`
            (the default) when it has no terminal representation.
        """
        return None

    def get_web_node(self, ctx: ComponentRenderContext[StateT]) -> Any | None:
        """Prepare the web render node tree for this component.

        Reserved for the web interface — `xnano.core.nodes.web` doesn't
        exist yet, so every component returns `None` here today. Typed as
        `Any` rather than a forward reference to an `AbstractWebNode` that
        doesn't exist yet; narrow this once that module lands.

        Args:
            ctx: The `ComponentRenderContext` to prepare the node for.

        Returns:
            The web render node for this component, or `None` (the
            default) when it has no web representation.
        """
        return None


__all__ = (
    "AbstractComponent",
    "ComponentRenderContext",
)
