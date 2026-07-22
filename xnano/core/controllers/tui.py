"""xnano.core.controllers.tui

---

Terminal paint controller: the concrete ``AbstractController`` that draws
to the screen through ``xnano_core``. Grids and terminal render nodes call
into this controller for measure/split/paint; it is the only framework
layer that talks to ``xnano_core`` for rendering.
"""

from __future__ import annotations

import dataclasses
import re
import threading
from typing import TYPE_CHECKING, Any, Generic, Sequence, TypeVar

import xnano_core.rust.native as native
from xnano_core import core

from xnano import _core_bindings as native_types
from xnano._types import Alignment, Area, Direction, Size
from xnano.components.abstract import (
    AbstractComponent,
    ComponentRenderContext,
)
from xnano.core.controllers.abstract import (
    AbstractController,
    AbstractControllerCapabilities,
    LayoutConstraint,
)
from xnano.tui.effects import (
    apply_native_cell_filter,
    build_native_effect,
)
from xnano.tui.nodes import AbstractTerminalNode, ParagraphNode

if TYPE_CHECKING:
    from xnano._types import Frame
    from xnano.core.controllers.abstract import AbstractLayoutConstraint
    from xnano.effects import AbstractEffect
    from xnano.fields import GridFieldInfo
    from xnano.core.nodes import AbstractNode


StateT = TypeVar("StateT")


SESSION_DEVICE_LOCK: threading.RLock = threading.RLock()
"""Device lock for thread-safe access to the cursor / device configuration
options during an active session.
"""


_ANSI_NAMED_FOREGROUNDS: dict[str, int] = {
    "Black": 30,
    "Red": 31,
    "Green": 32,
    "Yellow": 33,
    "Blue": 34,
    "Magenta": 35,
    "Cyan": 36,
    "Gray": 37,
    "DarkGray": 90,
    "LightRed": 91,
    "LightGreen": 92,
    "LightYellow": 93,
    "LightBlue": 94,
    "LightMagenta": 95,
    "LightCyan": 96,
    "White": 97,
}
"""ANSI foreground codes keyed by native color representation."""


_ANSI_MODIFIERS: dict[str, int] = {
    "BOLD": 1,
    "DIM": 2,
    "ITALIC": 3,
    "UNDERLINED": 4,
    "SLOW_BLINK": 5,
    "RAPID_BLINK": 6,
    "REVERSED": 7,
    "HIDDEN": 8,
    "CROSSED_OUT": 9,
}
"""ANSI SGR codes keyed by native modifier representation."""


def _get_ansi_color_code(
    color: native.Color, *, background: bool
) -> str | None:
    """Return the SGR fragment for a native terminal color."""
    value = repr(color)
    named = _ANSI_NAMED_FOREGROUNDS.get(value)
    if named is not None:
        if background:
            named += 10
        return str(named)
    match = re.fullmatch(r"Rgb\((\d+), (\d+), (\d+)\)", value)
    if match is not None:
        channel = 48 if background else 38
        return f"{channel};2;{';'.join(match.groups())}"
    match = re.fullmatch(r"Indexed\((\d+)\)", value)
    if match is not None:
        channel = 48 if background else 38
        return f"{channel};5;{match.group(1)}"
    return None


def _get_ansi_style(cell: native.BufferCell) -> tuple[str, ...]:
    """Return all SGR fragments needed to reproduce a buffer cell style."""
    codes: list[str] = []
    foreground = _get_ansi_color_code(cell.fg, background=False)
    background = _get_ansi_color_code(cell.bg, background=True)
    if foreground is not None:
        codes.append(foreground)
    if background is not None:
        codes.append(background)
    modifier_names = set(repr(cell.modifier).split(" | "))
    codes.extend(
        str(code)
        for name, code in _ANSI_MODIFIERS.items()
        if name in modifier_names
    )
    return tuple(codes)


def _get_buffer_as_ansi(buffer: native.Buffer) -> str:
    """Serialize a native buffer while preserving its terminal cell styles."""
    area = buffer.area
    lines: list[str] = []
    for y in range(area.y, area.y + area.height):
        cells = [buffer.cell(x, y) for x in range(area.x, area.x + area.width)]
        while cells and (cells[-1] is None or not cells[-1].symbol.strip()):
            cells.pop()

        parts: list[str] = []
        active_style: tuple[str, ...] = ()
        for cell in cells:
            if cell is None:
                continue
            style = _get_ansi_style(cell)
            if style != active_style:
                if active_style:
                    parts.append("\x1b[0m")
                if style:
                    parts.append(f"\x1b[{';'.join(style)}m")
                active_style = style
            parts.append(cell.symbol)
        if active_style:
            parts.append("\x1b[0m")
        lines.append("".join(parts))
    return "\n".join(lines)


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
    ir_content: Any | None = None
    """Optional ``CoreRenderIR`` object (bypasses native widget wrapping)."""


class TerminalController(AbstractController, Generic[StateT]):
    """Live-terminal implementation of ``AbstractController``.

    Owns the ``xnano_core`` session, batches render requests for a frame,
    and lowers framework types (``Area``, ``Frame``, layout constraints,
    terminal render nodes) into native ratatui widgets.
    """

    __slots__ = (
        "_core_session",
        "_is_offscreen",
        "_terminal_width",
        "_terminal_height",
        "_last_viewport",
        "_render_requests",
        "_native_frame_cache",
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
        self._native_frame_cache: dict[int, tuple[Any, Any]] = {}

    @classmethod
    def get_capabilities(cls) -> AbstractControllerCapabilities:
        return AbstractControllerCapabilities(
            supports_effects=True,
            supports_movement=True,
            supports_absolute_geometry=True,
        )

    def leave(self) -> None:
        """Exit the underlying ``CoreSession``."""
        self._core_session.restore()

    def begin_viewport_frame(self) -> None:
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

        needs_sorting = False
        first_z_index = requests[0].z
        for request in requests:
            if request.z != first_z_index:
                needs_sorting = True
                break

        if needs_sorting:
            requests = sorted(requests, key=lambda r: r.z)

        children: list[Any] = [None] * len(requests)
        for index, request in enumerate(requests):
            if request.ir_content is not None:
                content = core.CoreRenderContent.ir(request.ir_content)
            elif request.state is None:
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
        """Return the current viewport as a ``native.Rect``.

        For inline sessions the viewport is offset from the screen origin, so
        this returns the terminal's true frame area (position included) rather
        than assuming ``(0, 0)``.
        """
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
        rect = self._core_session.get_viewport_area()
        self._last_viewport = rect
        return rect

    def get_viewport_area(self) -> Area:
        """Return the current viewport as an ``Area``."""
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

    def get_core_session_output_as_ansi(self) -> str:
        """Return buffered terminal output with ANSI cell styles preserved."""
        return _get_buffer_as_ansi(self._core_session.buffer_snapshot())

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

    def render_ir(
        self,
        area: Area,
        ir: Any,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        self._render_requests.append(
            RenderRequest(
                native_rect=native_types.get_native_rect_from_area(area),
                native_content=None,
                z=z,
                effect_key=effect_key,
                ir_content=ir,
            )
        )

    def render_native(
        self,
        area: Area,
        content: Any,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        self._render_requests.append(
            RenderRequest(
                native_rect=native_types.get_native_rect_from_area(area),
                native_content=content,
                z=z,
                effect_key=effect_key,
            )
        )

    def paint_node(
        self,
        node: "AbstractNode",
        area: Area,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Paint a terminal render node — just delegates to the node itself.

        The controller never inspects which *concrete* node it has; `node`
        decides how to lower itself (see `AbstractTerminalNode.lower`). It
        does, however, require a terminal node specifically — a node built
        for a different interface reaching this controller is a real bug
        upstream, not something to silently paint.
        """
        if not isinstance(node, AbstractTerminalNode):
            raise TypeError(
                "TerminalController.paint_node() requires an "
                f"AbstractTerminalNode, got {type(node).__name__!r}"
            )
        node.lower(area, self, z=z, effect_key=effect_key)

    def paint_frame(
        self,
        area: Area,
        frame: "Frame",
        *,
        z: int = 0,
    ) -> Area:
        """Paint the chrome ``frame`` around ``area`` and return the inner area."""
        cache_key = id(frame)
        cached = self._native_frame_cache.get(cache_key)
        if cached is not None and cached[0] is frame:
            block = cached[1]
        else:
            block = native_types.get_native_block_from_frame(frame)
            if len(self._native_frame_cache) >= 256:
                self._native_frame_cache.clear()
            self._native_frame_cache[cache_key] = (frame, block)
        if block is None:
            return area

        native_rect = native_types.get_native_rect_from_area(area)
        self.render_native(area, block, z=z)
        return native_types.get_area_from_native_rect(block.inner(native_rect))

    def split_layout(
        self,
        area: Area,
        direction: Direction,
        gap: int,
        constraints: Sequence["AbstractLayoutConstraint"],
    ) -> list[Area]:
        """Split ``area`` along ``direction`` with ``constraints``."""
        native_constraints: list[Any] = []
        for constraint in constraints:
            if not isinstance(constraint, LayoutConstraint):
                raise TypeError(
                    "TerminalController.split_layout() requires concrete "
                    f"LayoutConstraint instances, got "
                    f"{type(constraint).__name__!r}"
                )
            native_constraints.append(
                native_types.get_native_layout_constraint_from_constraint(
                    constraint
                )
            )
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

    def measure_field_slot(
        self,
        value: Any,
        direction: Direction,
        field: "GridFieldInfo",
    ) -> int:
        """Return the content length along ``direction`` for a slot value."""
        if value is None:
            return 0

        if isinstance(value, AbstractComponent):
            ctx = ComponentRenderContext(
                area=Area(x=0, y=0, width=0, height=0)
            )
            if type(value).get_size is not AbstractComponent.get_size:
                size = value.get_size(ctx)
            else:
                content = value.compose(ctx)
                node = None
                if content is not None:
                    from xnano.tui.content_lower import lower_content

                    node = lower_content(content)
                if node is None:
                    node = value.get_terminal_node(ctx)
                size = (
                    node.measure()
                    if node is not None
                    else Size(width=0, height=0)
                )
            return size.height if direction == "vertical" else size.width

        if isinstance(value, AbstractTerminalNode):
            size = value.measure()
            return size.height if direction == "vertical" else size.width

        if isinstance(value, str):
            lines = value.split("\n")
            if direction == "vertical":
                return len(lines)
            return max(len(line) for line in lines) if lines else 0

        return 0

    def play_effect(
        self,
        effect: "AbstractEffect",
        *,
        fields: list[str] | None = None,
    ) -> bool:
        """Bind and run an effect on one or more layout field areas.

        Args:
            effect: The effect description to play. ``effect.key`` (if
                set) is used to derive a stable, de-duplicating id per
                target field.
            fields: Layout field names to target. When omitted or empty,
                no effect is started.

        Returns:
            ``True`` when at least one field area was found and an
            effect started.
        """
        if not fields:
            return False

        native_effect = apply_native_cell_filter(
            effect, build_native_effect(effect)
        )
        started = False
        for field_name in fields:
            area = self._core_session.effect_area_for(field_name)
            if area is None:
                continue
            effect_id = (
                f"{effect.key}:{field_name}"
                if effect.key is not None
                else field_name
            )
            self._core_session.add_unique_effect(
                effect_id,
                native_effect.with_area(area),
            )
            started = True
        return started

    def render_content(
        self,
        area: Area,
        content: Any,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Lower neutral Content to nodes and paint into ``area``."""
        from xnano.tui.content_lower import lower_content

        node = lower_content(content)
        if node is None:
            return
        self.paint_node(node, area, z=z, effect_key=effect_key)

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

        Prefers ``compose()`` → Content → node lowering; falls back to
        ``get_terminal_node`` for components not yet converted.
        """
        if not component.visible:
            return

        area = component.before_render(ctx, area)
        content = component.compose(ctx)
        node = None
        if content is not None:
            from xnano.tui.content_lower import lower_content

            node = lower_content(content)
        if node is None:
            node = component.get_terminal_node(ctx)
        frame = component.get_frame()

        if node is None and frame is None:
            component.after_render(ctx, area)
            return

        draw_area = area
        if component.fit_content and not fill_area:
            if type(component).get_size is not AbstractComponent.get_size:
                measured = component.get_size(ctx)
            elif node is not None:
                measured = node.measure()
            else:
                measured = Size(width=0, height=0)

            alignment: Alignment = "left"
            if isinstance(node, ParagraphNode) and node.align is not None:
                alignment = node.align
            if measured.width > 0 or measured.height > 0:
                draw_area = area.fit_content(measured, align=alignment)

        if node is not None:
            self.paint_node(
                node, draw_area, z=component.z, effect_key=effect_key
            )
        elif frame is not None:
            self.paint_frame(draw_area, frame, z=component.z)
        component.after_render(ctx, area)

    def paint_field_slot(
        self,
        value: Any,
        area: Area,
        field: "GridFieldInfo | None",
        *,
        parent_z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Dispatch-render a layout field's value into ``area``."""
        if value is None:
            return

        from xnano.grid import BaseGrid

        if isinstance(value, BaseGrid):
            from xnano.tui.terminal import _ACTIVE_TERMINAL

            # Re-register nested grids every frame (the render path clears
            # ``_attached_frame_grids`` at the start of each paint).
            terminal = _ACTIVE_TERMINAL.get()
            if terminal is not None:
                from xnano._dispatch import track_frame_grid

                track_frame_grid(terminal, value)
            value._grid_build_frame(area, self)
            return

        if isinstance(value, AbstractComponent):
            from xnano.tui.terminal import _ACTIVE_TERMINAL

            terminal = _ACTIVE_TERMINAL.get()
            ctx = ComponentRenderContext(area=area, terminal=terminal)
            # A content-sized (``fit``) field already carries a slot matching
            # its content, so the component renders at its natural size rather
            # than stretching to fill.
            fill_area = not (
                field is not None
                and (
                    (field.width is not None and field.width.is_fit)
                    or (field.height is not None and field.height.is_fit)
                )
            )
            self.render_component(
                value,
                area,
                ctx,
                fill_area=fill_area,
                effect_key=effect_key,
            )
            return

        if isinstance(value, AbstractTerminalNode):
            self.paint_node(value, area, z=parent_z, effect_key=effect_key)
            return

        from xnano.core.content import AbstractContent

        if isinstance(value, AbstractContent):
            self.render_content(area, value, z=parent_z, effect_key=effect_key)
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


__all__ = ("TerminalController", "RenderRequest", "SESSION_DEVICE_LOCK")
