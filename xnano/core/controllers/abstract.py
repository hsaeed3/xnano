"""xnano.core.controllers.abstract

---

Backend-neutral controller contract: layout constraints, capabilities,
and paint / measure hooks shared by terminal and web controllers.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import TYPE_CHECKING, Any, Literal, Sequence, TypeAlias


if TYPE_CHECKING:
    from xnano._types import Area, Direction, Frame
    from xnano.fields import GridFieldInfo
    from xnano.tui._node_base_tmp import AbstractNode


LayoutConstraintKind: TypeAlias = Literal[
    "length", "percentage", "fill", "content", "min", "max", "ratio"
]
"""The kind of layout constraint.

Values:
    "length": A fixed length constraint.
    "percentage": A percentage constraint.
    "fill": A fill constraint.
    "content": A content constraint.
    "min": A minimum constraint.
    "max": A maximum constraint.
    "ratio": A ratio constraint.
"""


@dataclasses.dataclass(frozen=True)
class AbstractLayoutConstraint(abc.ABC):
    """The layout constraint for a given field or area within a
    viewport.

    Attributes:
        kind: The kind of layout constraint this is.
    """

    kind: LayoutConstraintKind
    """The kind of layout constraint this is."""


@dataclasses.dataclass(frozen=True, slots=True)
class LayoutConstraint(AbstractLayoutConstraint):
    """A concrete layout constraint carrying the weight/length a `kind`
    needs to actually size a split.

    This is shared vocabulary, not terminal-specific: a length/percentage/
    fill/ratio weight means the same thing whether a controller resolves it
    against terminal cells or emits it as a CSS flex-basis. `BaseGrid` builds
    these directly rather than each controller inventing its own
    constraint type.

    Attributes:
        value: The primary constraint value (a length in cells, a
            percentage, a fill weight, ...) — meaning depends on `kind`.
        value2: The secondary value; only meaningful for `kind="ratio"`,
            where the constraint is `value / value2`.
    """

    value: int = 1
    """The primary constraint value; meaning depends on `kind`."""
    value2: int = 1
    """The secondary constraint value; only used by `kind="ratio"`."""


@dataclasses.dataclass(frozen=True)
class AbstractControllerCapabilities(abc.ABC):
    """Optional feature flags a `Controller` may provide functionality
    for.
    """

    supports_effects: bool
    """Whether ``grid_play_effect`` does anything."""
    supports_movement: bool
    """Whether pointer-drag repositioning of fields can be done
    by the user.
    """
    supports_absolute_geometry: bool
    """Whether ``Area`` coordinates map to explicit cells within the
    frame, or are purely logical/flex.
    """


class AbstractController(abc.ABC):
    """Paint, measure, and layout contract for a UI host backend.

    Only ``get_capabilities`` is required; other methods are opt-in for
    the features a given interface supports (absolute geometry, frames,
    effects, and so on).
    """

    @classmethod
    @abc.abstractmethod
    def get_capabilities(cls) -> AbstractControllerCapabilities:
        """Return the feature capabilities this controller provides."""

    def commit_requests(self) -> None:
        """Flush queued paint work for the current frame into the output."""
        return None

    def begin_viewport_frame(self) -> None:
        """Start a new render frame for the viewport."""
        return None

    def get_viewport_area(self) -> Area:
        """Return the viewport area for this controller's frame.

        Returns:
            The viewport area for this controller's frame.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'get_viewport_area' for"
            "absolute geometry support."
        )

    def paint_frame(self, area: Area, frame: Frame, *, z: int = 0) -> Area:
        """Paint a decorative frame into ``area``.

        Prefer ``paint_chrome`` with a ``Style`` for new code. Controllers
        may still implement this for direct frame painting.

        Args:
            area: The area to paint the frame onto.
            frame: The frame to paint.
            z: The z-index of the frame.

        Returns:
            The area that was painted onto.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'paint_frame' for"
            "frame painting support."
        )

    def paint_chrome(self, area: Area, style: Any, *, z: int = 0) -> Area:
        """Paint interface-neutral chrome for ``style`` into ``area``.

        Default lowers ``Style`` to a ``Frame`` and calls ``paint_frame``.

        Args:
            area: Target area.
            style: A ``Style`` (or Frame-compatible object).
            z: Stacking order.

        Returns:
            The inner content area after chrome.
        """
        from xnano._types import Frame

        if isinstance(style, Frame):
            return self.paint_frame(area, style, z=z)
        frame = Frame(
            background=getattr(style, "background", None),
            border=getattr(style, "border", None),
            border_color=getattr(style, "border_color", None),
            border_sides=(
                list(style.border_sides)
                if getattr(style, "border_sides", None) is not None
                else None
            ),
            title=getattr(style, "title", None),
            title_position=getattr(style, "title_position", None),
            padding=getattr(style, "padding", None),
        )
        if frame.is_empty():
            return area
        return self.paint_frame(area, frame, z=z)

    def render_content(
        self,
        area: Area,
        content: Any,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Render a neutral ``Content`` tree into ``area``.

        Controllers override this to lower Content to nodes/IR/HTML.
        Default is a no-op so hosts without Content support still run.

        Args:
            area: Target area.
            content: A ``Content`` primitive or tree.
            z: Stacking order.
            effect_key: Optional effect target key.
        """
        return None

    def notify_field_changed(
        self,
        interface: Any,
        name: str,
        state: Any,
    ) -> None:
        """Observe live field dirtiness from an ``AbstractInterface``.

        Args:
            interface: The interface instance that changed.
            name: Field name.
            state: ``FieldState`` or ``None``.
        """
        return None

    def split_layout(
        self,
        area: Area,
        direction: Direction,
        gap: int,
        constraints: Sequence[AbstractLayoutConstraint],
    ) -> list[Area]:
        """Splits a given area into a list of sub-areas based on a given
        direction and layout constraints.

        Args:
            area: The area to split.
            direction: The direction to split the area in.
            gap: The gap between the sub-areas.
            constraints: The layout constraints for the sub-areas.

        Returns:
            A list of sub-areas.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'split_layout' for"
            "layout splitting support."
        )

    def measure_field_slot(
        self, value: Any, direction: Direction, field: GridFieldInfo
    ) -> int:
        """Measures the size of a given slot based on a given value, direction,
        and grid field info.

        Args:
            value: The value to measure the slot size for.
            direction: The direction to measure the slot size in.
            field: The field to measure the slot size for.

        Returns:
            The size of the slot.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'measure_slot' for"
            "slot measurement support."
        )

    def paint_field_slot(
        self,
        value: Any,
        area: Area,
        field: GridFieldInfo | None,
        *,
        parent_z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Paints a given field slot onto a specified viewport area.

        Args:
            value: The value to paint the field slot for.
            area: The area to paint the field slot onto.
            field: The field to paint the field slot for.
            parent_z: The z-index of the parent frame.
            effect_key: The key of the effect to paint the field slot for.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'paint_field_slot' for"
            "field slot painting support."
        )

    def play_effect(
        self,
        effect: Any,
        *,
        fields: list[str] | None = None,
    ) -> bool:
        """Plays a given effect on the specified fields.

        Args:
            effect: The effect to play.
            fields: The fields to play the effect on.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'play_effect' for"
            "effect playing support."
        )

    def render_ir(
        self, area: Area, ir: Any, *, z: int = 0, effect_key: str | None = None
    ) -> None:
        """Paints a lowered render IR onto a specified viewport area.

        This is the primitive a node's ``lower`` method enqueues through —
        the fast path shared by most node kinds, requiring no native
        widget construction on the Python side.

        Args:
            area: The area to paint the IR onto.
            ir: The lowered render IR to paint.
            z: The z-index to paint at.
            effect_key: The key of the effect targeting this area, if any.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'render_ir' for"
            "IR painting support."
        )

    def render_native(
        self,
        area: Area,
        content: Any,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Paints controller-native content with no portable IR
        representation onto a specified viewport area.

        Used by node kinds that ``to_ir`` cannot express at all (e.g. a
        chart) or cannot express for a particular instance (e.g. a
        sparkline with per-bar colors) — those nodes override ``lower``
        directly and build their native content themselves.

        Args:
            area: The area to paint the content onto.
            content: The controller-native content to paint.
            z: The z-index to paint at.
            effect_key: The key of the effect targeting this area, if any.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'render_native' for"
            "native content painting support."
        )

    def paint_node(
        self,
        node: AbstractNode,
        area: Area,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Paints a given node onto a specified viewport area.

        Concrete controllers implement this against their own interface's
        node base (e.g. `AbstractTerminalNode`) rather than the neutral
        `AbstractNode` typed here, since painting is exactly the behavior
        that differs per interface — see `AbstractTerminalNode.lower`.

        Args:
            node: The node to paint.
            area: The area to paint the node onto.
            z: The z-index of the node.
            effect_key: The key of the effect targeting this node's area,
                if any.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'paint_node' for"
            "node painting support."
        )
