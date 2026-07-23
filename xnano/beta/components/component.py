"""xnano.beta.components.component

---

Create custom components and compose them from public content primitives.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from xnano.beta.core.content import (
    Bars,
    Canvas,
    CellCanvas,
    Clear,
    Content,
    Gauge,
    Items,
    LineGauge,
    Panel,
    Plot,
    Run,
    Sparkline,
    Stack,
    TableGrid,
    TextBlock,
)
from xnano.beta.core.content import (
    Scrollbar as ScrollbarContent,
)
from xnano.beta.types import Size

if TYPE_CHECKING:
    from xnano.beta.events import KeyboardEventData
    from xnano.beta.terminal import Terminal
    from xnano.beta.types import Area


StateT = TypeVar("StateT")


@dataclasses.dataclass(frozen=True, slots=True)
class ComponentRenderContext(Generic[StateT]):
    """Render-time scope passed into component paint hooks.

    Attributes:
        area: Target area for this paint.
        terminal: Terminal handling the render, when available.
        state: Application state for this paint.
        component: Component being rendered, when known.
    """

    area: "Area"
    """Area assigned to the component."""
    terminal: "Terminal[StateT] | None" = None
    """Terminal handling the render."""
    state: StateT | None = None
    """Application state for this paint."""
    component: "Component | None" = None
    """Component being rendered."""


class _ComponentMeta(type):
    """Collect recognized declarative descriptors on component subclasses.

    Ordinary annotated dataclass fields stay ordinary fields. Only values
    that are ``ComponentDescriptor`` instances are captured into
    ``_declared`` (copied per subclass, preserving MRO order). Empty
    subclasses pay no per-frame schema cost.
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> "_ComponentMeta":
        # Lazy import avoids a hard cycle with table/chart descriptors.
        from xnano.beta.components.schema import ComponentDescriptor

        declared: dict[str, ComponentDescriptor] = {}
        for base in bases:
            inherited = getattr(base, "_declared", None)
            if inherited:
                for key, value in inherited.items():
                    declared[key] = value
        for key, value in list(namespace.items()):
            if isinstance(value, ComponentDescriptor):
                # Bind a per-subclass copy so mutation cannot leak.
                bound = (
                    dataclasses.replace(value)
                    if dataclasses.is_dataclass(value)
                    else value
                )
                if hasattr(bound, "name"):
                    bound.name = key
                declared[key] = bound
                del namespace[key]
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        cls._declared = declared  # ty: ignore[unresolved-attribute]
        return cls


@dataclasses.dataclass
class Component(metaclass=_ComponentMeta):
    """Base class for custom xnano components.

    Component attributes are live state: changing an attribute changes the
    next rendered frame. Implement ``compose()`` to return content. Interactive
    components can also implement ``handle_keyboard()`` or ``handle_paste()``.

    The framework updates the read-only ``focused`` property when the
    component gains or loses field focus.

    Example:
        ``Text(content="Ready", color="green")``

    Attributes:
        visible: Whether the component is rendered.
        z: Paint order relative to sibling components.
        fit_content: Whether layout should prefer the natural content size.
    """

    _xnano_component_base: ClassVar[bool] = True
    _declared: ClassVar[dict[str, Any]] = {}

    visible: bool = dataclasses.field(default=True, kw_only=True)
    """Whether this component paints at all."""
    z: int = dataclasses.field(default=0, kw_only=True)
    """Stacking order among sibling content."""
    fit_content: bool = dataclasses.field(default=True, kw_only=True)
    """When ``True``, paint at natural size inside a larger slot."""

    _input_focused: bool = dataclasses.field(
        default=False, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        self.component_post_init()

    def component_post_init(self) -> None:
        """Initialize subclass state after dataclass fields are assigned.

        Override this method instead of ``__post_init__``.
        """
        return None

    @property
    def focused(self) -> bool:
        """Whether this component currently holds field focus."""
        return bool(self._input_focused)

    def get_frame(self) -> Any | None:
        """Optional frame/panel chrome around composed content."""
        return None

    def get_size(self, ctx: ComponentRenderContext[StateT]) -> Size:
        """Return the preferred cell size of this component."""
        return Size(width=0, height=0)

    def before_render(
        self,
        ctx: ComponentRenderContext[StateT],
        area: "Area",
    ) -> "Area":
        """Called before rendering; returns the effective render area."""
        return area

    def after_render(
        self,
        ctx: ComponentRenderContext[StateT],
        area: "Area",
    ) -> None:
        """Called after rendering for optional post-paint work."""
        return None

    def compose(self, ctx: ComponentRenderContext[StateT]) -> Content | None:
        """Compose interface-neutral content for this component.

        Returns:
            A ``Content`` tree, or ``None`` when nothing should paint.
        """
        return None

    def handle_keyboard(self, keyboard: "KeyboardEventData") -> bool:
        """Optional keyboard handler while focused.

        Returns:
            ``True`` when the event was consumed.
        """
        return False

    def handle_paste(self, text: str) -> bool:
        """Optional paste handler while focused.

        Returns:
            ``True`` when the paste was consumed.
        """
        return False


__all__ = (
    "Bars",
    "Canvas",
    "CellCanvas",
    "Clear",
    "Component",
    "ComponentRenderContext",
    "Content",
    "Gauge",
    "Items",
    "LineGauge",
    "Panel",
    "Plot",
    "Run",
    "ScrollbarContent",
    "Sparkline",
    "Stack",
    "TableGrid",
    "TextBlock",
)
