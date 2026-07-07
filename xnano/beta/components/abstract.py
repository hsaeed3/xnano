"""xnano.beta.components.abstract"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any, Generic, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.beta.core.session import Session
    from xnano.beta.core.nodes import RenderNode
    from xnano.beta.frame import Frame
    from xnano.beta.terminal import Terminal
    from xnano.beta.types import Area, Direction, Size


StateT = TypeVar("StateT")


@dataclasses.dataclass(frozen=True, slots=True)
class ComponentRenderContext(Generic[StateT]):
    """Render-time scope passed to component hooks.

    Attributes:
        area: The ``Area`` to render.
        terminal: The ``Terminal`` to render.
        state: The ``StateT`` to render.
        component: The ``AbstractComponent`` to render.
    """

    area: Area
    terminal: "Terminal[StateT] | None" = None
    state: StateT | None = None
    component: "AbstractComponent | None" = None


@dataclasses.dataclass
class AbstractComponent(abc.ABC):
    """Abstract base class that provides an opt-in compatbility like interface
    for creating custom TUI components using native ``xnano-core`` widgets.

    NOTE: For an ``AbstractComponent`` to be rendered, it must at least
    implement the ``get_node`` method.
    """

    visible: bool = dataclasses.field(default=True, kw_only=True)
    z: int = dataclasses.field(default=0, kw_only=True)
    fit_content: bool = dataclasses.field(default=True, kw_only=True)

    def get_frame(self) -> Frame | None:
        """Return an optional frame panel to wrap the composed content of
        this component around.

        Returns:
            An optional ``Frame`` to wrap the composed content of this component around.
        """
        return None

    def get_size(self, ctx: ComponentRenderContext[StateT]) -> Size:
        """Return the preferred cell size of this component.

        Args:
            ctx: The ``Component    RenderContext`` to measure.
        """
        return Size(width=0, height=0)

    def before_render(
        self,
        ctx: ComponentRenderContext[StateT],
        area: Area,
    ) -> Area:
        """Called before rendering; returns the effective render area.

        Args:
            ctx: The ``ComponentRenderContext`` before rendering.
            area: The ``Area`` to render.

        Returns:
            The effective ``Area`` to render.
        """
        return area

    def after_render(
        self,
        ctx: ComponentRenderContext[StateT],
        area: Area,
    ) -> None:
        """Called after rendering; should perform any post-render clean up
        or side effects.

        Args:
            ctx: The ``ComponentRenderContext`` after rendering.
            area: The ``Area`` after rendering.
        """
        return None

    def get_node(
        self, ctx: ComponentRenderContext[StateT]
    ) -> RenderNode | None:
        """Prepare the ``RenderNode`` that maps to this component
        to be rendered.

        Args:
            ctx: The ``ComponentRenderContext`` to prepare the ``RenderNode`` for.

        Returns:
            The ``RenderNode`` that maps to this component.
        """
        return None


__all__ = (
    "AbstractComponent",
    "ComponentRenderContext",
)
