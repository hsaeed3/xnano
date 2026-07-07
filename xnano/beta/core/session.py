"""xnano.beta.core.session"""

from __future__ import annotations

import contextvars
import dataclasses
import threading
from typing import (
    Any,
    Generic,
    Literal,
    Sequence,
    TypeVar,
    TYPE_CHECKING,
)

from xnano_core import core
from xnano_core.rust import native

from xnano.beta.core import (
    nodes as _nodes,
)
from xnano.beta.utils import native_types
from xnano.beta.color import Color, ColorLike
from xnano.beta.components.abstract import (
    AbstractComponent,
    ComponentRenderContext,
)
from xnano.beta.frame import Frame, PaddingLike
from xnano.beta.types import Alignment, Area, Direction, Size

if TYPE_CHECKING:
    from xnano.beta.fields import GridFieldInfo
    from xnano.beta.grid import Grid, _GridLayoutConstraint


StateT = TypeVar("StateT")


SESSION_DEVICE_LOCK: threading.RLock = threading.RLock()
"""Device lock for thread-safe access to the cursor / device configuration options
during an active session.
"""


@dataclasses.dataclass(slots=True)
class RenderRequest(Generic[StateT]):
    """A request to draw a ``native.Rect`` area onto the live terminal session."""

    native_rect: native.Rect
    """The ``ratatui`` rust native ``Rect`` area to draw."""
    native_content: Any
    """The ``xnano_core.rust.native`` component / content to be drawn."""
    z: int = 0
    """Z-index that determines paint layering order within the viewport."""
    state: StateT | None = None
    """Optional user-defined state passed alongside this render request."""
    effect_key: str | None = None
    """Optional effect lookup key recorded for this render request."""


@dataclasses.dataclass(slots=True)
class NativeRenderRequest(Generic[StateT]):
    """A request to draw a renderable value onto the live terminal session

    Attributes:
        renderable: The renderable value to draw.
        native_color: The native color to draw.
        native_background: The native background to draw.
        native_modifiers: The native modifiers to draw.
        native_alignment: The native alignment to draw.
    """

    renderable: "Any"
    native_color: native.Color | None = None
    native_background: native.Color | None = None
    native_modifiers: tuple[Any, ...] = ()
    native_alignment: native.Alignment | None = None


class Session(Generic[StateT]):
    """Internal session adapter bridging xnano's paint IR to ``xnano_core``."""

    __slots__ = (
        "_core_session",
        "_is_offscreen",
        "_terminal_width",
        "_terminal_height",
        "_last_viewport",
        "_render_requests",
        "_assembler",
    )

    def __init__(
        self,
        core_session: core.CoreSession,
        *,
        terminal_width: int | None = None,
        terminal_height: int | None = None,
        is_offscreen: bool = False,
    ) -> None:
        self._core_session = core_session
        self._is_offscreen = is_offscreen
        self._terminal_width = terminal_width
        self._terminal_height = terminal_height
        self._last_viewport: native.Rect | None = None
        self._render_requests: list[RenderRequest[StateT]] = []
        self._assembler: _nodes.NodeAssembler = _nodes.NodeAssembler()

    def leave(self) -> None:
        """Exit the underlying ``CoreSession``."""
        self._core_session.restore()

    def begin_frame(self) -> None:
        """Clear pending render requests to start a new frame."""
        self._render_requests.clear()

    def commit_requests(self) -> None:
        """Flush all pending render requests to the ``CoreSession``."""
        requests = self._render_requests
        if not requests:
            self._core_session.render(
                core.CoreRenderNode.leaf(core.CoreRenderContent.empty())
            )
            return

        needs_sorting: bool = False
        first_z_index: int = requests[0].z
        for request in requests:
            if request.z != first_z_index:
                needs_sorting = True
                break

        if needs_sorting:
            requests = sorted(requests, key=lambda r: r.z)

        children: list[Any] = [None] * len(requests)
        for index, request in enumerate(requests):
            if request.state is None:
                content = core.CoreRenderContent.widget(request.native_content)
            else:
                content = core.CoreRenderContent.stateful(
                    request.native_content, request.state
                )
            children[index] = core.CoreRenderNode(
                x=request.native_rect.x,
                y=request.native_rect.y,
                width=request.native_rect.width,
                height=request.native_rect.height,
                content=content,
                effect_key=request.effect_key,
                z=request.z,
            )
        if len(children) == 1:
            node = children[0]
        else:
            viewport = self._last_viewport or self.get_native_viewport_area()
            node = core.CoreRenderNode.stack(
                0, 0, viewport.width, viewport.height, children
            )
        self._core_session.render(node)

    def get_native_viewport_area(self) -> native.Rect:
        """Return the current viewport as a ``native.Rect``."""
        if (
            self._terminal_width is not None
            and self._terminal_height is not None
        ):
            return native.Rect(
                x=0,
                y=0,
                width=self._terminal_width,
                height=self._terminal_height,
            )
        size = self._core_session.get_size()
        rect = native.Rect(x=0, y=0, width=size.width, height=size.height)
        self._last_viewport = rect
        return rect

    def get_viewport_area(self) -> Area:
        """Return the current viewport as a :class:`~xnano.grid.types.GridArea`."""
        return Area(
            x=0,
            y=0,
            width=self._terminal_width or self._core_session.get_size().width,
            height=self._terminal_height
            or self._core_session.get_size().height,
        )

    def get_core_session_output_text(self) -> str:
        """Return the buffered terminal output as a newline-joined string."""
        buffer = self._core_session.buffer_snapshot()
        return "\n".join(buffer.to_string_lines())

    def request_render(
        self,
        native_rect: native.Rect,
        native_content: Any,
        *,
        z: int = 0,
    ) -> None:
        """Enqueue a render request at the given ``native_rect`` and ``z``-index."""
        self._render_requests.append(
            RenderRequest(
                native_rect=native_rect, native_content=native_content, z=z
            )
        )

    def request_render_with_state(
        self,
        native_rect: native.Rect,
        native_content: Any,
        state: StateT,
        *,
        z: int = 0,
    ) -> None:
        """Enqueue a stateful render request."""
        self._render_requests.append(
            RenderRequest(
                native_rect=native_rect,
                native_content=native_content,
                state=state,
                z=z,
            )
        )

    def render_native(
        self,
        rect: native.Rect,
        content: Any,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Enqueue a native widget for rendering at ``rect``.

        Args:
            rect: The ``native.Rect`` area to draw.
            content: The native content to draw.
            z: The ``z``-index to draw at.
            effect_key: Optional key for :meth:`grid_play_effect` lookups.
        """
        self._render_requests.append(
            RenderRequest(
                native_rect=rect,
                native_content=content,
                z=z,
                effect_key=effect_key,
            )
        )

    def render_native_with_state(
        self,
        rect: native.Rect,
        content: Any,
        state: Any,
        *,
        z: int = 0,
    ) -> None:
        """Enqueue a stateful native widget for rendering at ``rect``.

        Args:
            rect: The ``native.Rect`` area to draw.
            content: The native content to draw.
            state: The state to draw with.
            z: The ``z``-index to draw at.
        """
        self._render_requests.append(
            RenderRequest(
                native_rect=rect, native_content=content, state=state, z=z
            )
        )

    def render_component(
        self,
        component: AbstractComponent,
        area: Area,
        ctx: ComponentRenderContext[StateT],
        *,
        fill_area: bool = False,
        effect_key: str | None = None,
    ) -> None:
        """Draw a component into the session at the given area.

        Args:
            component: The ``AbstractComponent`` to draw.
            area: The ``Area`` to draw the component at.
            ctx: The ``RenderContext`` to draw the component with.
        """
        node: _nodes.RenderNode | None = None
        if not component.visible:
            return

        area = component.before_render(ctx, area)
        if type(component).get_node is not AbstractComponent.get_node:
            node = component.get_node(ctx)
        else:
            node = None
        frame = component.get_frame()

        if node is None and frame is None:
            component.after_render(ctx, area)
            return

        draw_area = area
        if component.fit_content and not fill_area:
            if type(component).get_size is not AbstractComponent.get_size:
                measured = component.get_size(ctx)
            else:
                measured = self._assembler.measure_node(node)  # type: ignore

            alignment: Alignment = "left"
            if (
                isinstance(node, _nodes.ParagraphNode)
                and node.align is not None
            ):
                alignment = node.align
            if measured.width > 0 or measured.height > 0:
                draw_area = area.fit_content(measured, align=alignment)
        self.paint_node(
            node,  # type: ignore
            draw_area,
            z=component.z,
            effect_key=effect_key,
        )
        component.after_render(ctx, area)

    def poll_core_event(self, timeout: int = 0) -> core.CoreEvent | None:
        """Poll for a core event; returns ``None`` for offscreen sessions.

        Args:
            timeout: Milliseconds to wait. ``0`` blocks until an event is
                available. ``-1`` returns immediately without waiting.
                Positive values block up to that many milliseconds.
        """
        if self._is_offscreen:
            return None
        try:
            if timeout < 0:
                timeout_ms = 0
            elif timeout == 0:
                timeout_ms = 2**31 - 1
            else:
                timeout_ms = timeout
            return self._core_session.poll_event(timeout_ms=timeout_ms)
        except OSError:
            return None

    def paint_node(
        self,
        node: _nodes.RenderNode,
        area: Area,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Lower a render IR node to native widgets via the assembler."""
        self._assembler.lower_node_to_native(
            node,
            area,
            self,
            z,
            effect_key=effect_key,
        )

    def grid_paint_frame(
        self,
        area: Area,
        frame: Frame,
        *,
        z: int = 0,
    ) -> Area:
        """Paint the chrome ``frame`` around ``area`` and return the inner area.

        Args:
            area: The ``Area`` to paint the frame around.
            frame: The ``Frame`` to paint.
            z: The ``z``-index to paint at.

        Returns:
            The inner ``Area`` after painting the frame.
        """
        block = native_types.get_native_block_from_frame(frame)
        if block is None:
            return area

        native_rect = native_types.get_native_rect_from_area(area)
        self.render_native(native_rect, block, z=z)
        return native_types.get_area_from_native_rect(block.inner(native_rect))

    def grid_split_layout(
        self,
        area: Area,
        direction: Direction,
        gap: int,
        constraints: Sequence[_GridLayoutConstraint],
    ) -> list[Area]:
        """Split ``area`` along ``direction`` with ``constraints``.

        Args:
            area: The ``Area`` to split.
            direction: The ``Direction`` to split along.
            gap: The ``gap`` between the areas.
            constraints: The ``constraints`` to apply to the areas.

        Returns:
            The ``list[Area]`` after splitting the area.
        """
        native_constraints = [
            native_types.get_native_layout_constraint_from_constraint(c)
            for c in constraints
        ]
        native_layout = native.Layout.new(
            native_types._NATIVE_DIRECTION_TYPES[direction], native_constraints
        )
        if gap:
            native_layout = native_layout.spacing(gap)

        return [
            native_types.get_area_from_native_rect(rect)
            for rect in native_layout.split(
                native_types.get_native_rect_from_area(area)
            )
        ]

    def grid_measure_slot(
        self,
        value: Any,
        direction: Direction,
        field: "GridFieldInfo",
    ) -> int:
        """Return the content length along ``direction`` for a slot value."""
        from xnano.beta.components.abstract import (
            AbstractComponent,
            ComponentRenderContext,
        )
        from xnano.beta.core.nodes import AbstractRenderNode

        if value is None:
            return 0

        if isinstance(value, AbstractComponent):
            if type(value).get_size is not AbstractComponent.get_size:
                ctx = ComponentRenderContext(
                    area=Area(x=0, y=0, width=0, height=0)
                )
                size = value.get_size(ctx)
            else:
                ctx = ComponentRenderContext(
                    area=Area(x=0, y=0, width=0, height=0)
                )
                node = value.get_node(ctx)
                size = (
                    self._assembler.measure_node(node)
                    if node is not None
                    else Size(width=0, height=0)
                )
            return size.height if direction == "vertical" else size.width

        if isinstance(value, AbstractRenderNode):
            size = self._assembler.measure_node(value)
            return size.height if direction == "vertical" else size.width

        if isinstance(value, str):
            lines = value.split("\n")
            if direction == "vertical":
                return len(lines)
            return max(len(line) for line in lines) if lines else 0

        return 0

    def grid_play_effect(
        self,
        effect: Any,
        *,
        fields: list[str] | None = None,
        key: str | None = None,
    ) -> bool:
        """Bind and run an effect on one or more layout field areas.

        Args:
            effect: A :class:`~xnano_core.rust.native.Effect` instance.
            fields: Layout field names to target. When omitted or empty, no
                effect is started.
            key: Optional unique effect id prefix. Each field uses
                ``field_name`` when omitted, or ``{key}:{field_name}`` when set.

        Returns:
            ``True`` when at least one field area was found and an effect
            started.
        """
        if not fields:
            return False

        started = False
        for field_name in fields:
            area = self._core_session.effect_area_for(field_name)
            if area is None:
                continue
            effect_id = (
                f"{key}:{field_name}" if key is not None else field_name
            )
            self._core_session.add_unique_effect(
                effect_id,
                effect.with_area(area),
            )
            started = True
        return started

    def grid_paint_slot(
        self,
        value: Any,
        area: Area,
        field: "GridFieldInfo | None",
        *,
        parent_z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Dispatch-render a layout field's value into ``area``."""
        from xnano.beta.components.abstract import (
            AbstractComponent,
            ComponentRenderContext,
        )
        from xnano.beta.core.nodes import AbstractRenderNode, ParagraphNode
        from xnano.beta.terminal import _ACTIVE_TERMINAL

        if value is None:
            return

        from xnano.beta.grid import Grid

        if isinstance(value, Grid):
            value._grid_build_frame(area, self)
            return

        if isinstance(value, AbstractComponent):
            terminal = _ACTIVE_TERMINAL.get()
            ctx = ComponentRenderContext(area=area, terminal=terminal)
            fill_area = not bool(field is not None and field.fit)
            self.render_component(
                value,
                area,
                ctx,
                fill_area=fill_area,
                effect_key=effect_key,
            )
            return

        if isinstance(value, AbstractRenderNode):
            self.paint_node(value, area, z=parent_z, effect_key=effect_key)
            return

        node = ParagraphNode(
            text=str(value),
            color=field.color if field is not None else None,
            background=field.background if field is not None else None,
            modifiers=tuple(field.modifiers)
            if (field is not None and field.modifiers)
            else (),
            align=field.align if field is not None else None,
            z=parent_z,
        )
        self.paint_node(node, area, z=parent_z, effect_key=effect_key)
