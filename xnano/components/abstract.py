"""xnano.components.abstract

---

``AbstractComponent`` base for built-in widgets. Components compose
content or interface-specific nodes (``get_terminal_node`` /
``get_web_node``); each method is opt-in per host kind.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from xnano._types import Size

if TYPE_CHECKING:
    from xnano._types import Area, Frame
    from xnano.terminal.nodes import AbstractTerminalNode
    from xnano.terminal.terminal import Terminal


StateT = TypeVar("StateT")


@dataclasses.dataclass(frozen=True, slots=True)
class ComponentRenderContext(Generic[StateT]):
    """Render-time scope passed into component paint hooks.

    Attributes:
        area: Target area for this paint.
        terminal: Active host when available.
        state: Application state for this paint.
        component: Component being rendered, when known.
    """

    area: "Area"
    terminal: "Terminal[StateT] | None" = None
    state: StateT | None = None
    component: "AbstractComponent | None" = None


@dataclasses.dataclass
class AbstractComponent(abc.ABC):
    """Base for declarative widgets used inside grids.

    Override ``compose`` and/or ``get_terminal_node`` / ``get_web_node``
    to provide a representation; unimplemented paths simply paint nothing
    for that host kind.
    """

    visible: bool = dataclasses.field(default=True, kw_only=True)
    z: int = dataclasses.field(default=0, kw_only=True)
    fit_content: bool = dataclasses.field(default=True, kw_only=True)

    @property
    def focused(self) -> bool:
        """Whether this component currently holds field focus.

        Live alongside ``visible`` / ``z``: the focus machinery keeps
        it in sync every frame, so ``self.name.focused`` in a hook and
        ``@on_field("name.focused")`` both read the current state.
        Components that never take focus always return ``False``.
        """
        return bool(getattr(self, "_input_focused", False))

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

    def compose(self, ctx: ComponentRenderContext[StateT]) -> Any | None:
        """Compose interface-neutral
        [`Content`](../core/content.md#xnano.core.content.Content){data-preview}
        for this component.

        Controllers prefer this over ``get_*_node``. Default returns
        ``None``; components may implement
        [`Content`](../core/content.md#xnano.core.content.Content){data-preview}
        trees and/or interface-specific ``get_terminal_node`` /
        ``get_web_node``.

        Args:
            ctx: Render context for this paint.

        Returns:
            A ``Content`` tree, or ``None``.
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
