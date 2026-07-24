"""xnano.beta.core.controller

---

Paint beta grids through their complete layout pipeline.
"""

from __future__ import annotations

import collections.abc
from typing import Any

import xnano_core.rust.native as native
from xnano_core import core

from xnano.beta.core.content import Panel, TextBlock
from xnano.beta.core.layout import LayoutConstraint
from xnano.beta.core.rendering import lower_content
from xnano.beta.types import Area, Frame, Padding
from xnano.beta.utils.responsive import resolve_responsive_variant


class TerminalController:
    """Collect absolute beta paint requests for one native frame."""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self.nodes: list[Any] = []

    def _paint(
        self,
        content: Any,
        area: Area,
        *,
        z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        if area.width <= 0 or area.height <= 0:
            return
        self.nodes.append(
            core.CoreRenderNode(
                x=area.x,
                y=area.y,
                width=area.width,
                height=area.height,
                content=core.CoreRenderContent.empty(),
                constraints=[native.Constraint.fill(1)],
                children=[lower_content(content)],
                effect_key=effect_key,
                z=z,
            )
        )

    def commit(self) -> None:
        width, height = self.runtime.size
        node = (
            core.CoreRenderNode.stack(0, 0, width, height, self.nodes)
            if self.nodes
            else core.CoreRenderNode.leaf(core.CoreRenderContent.empty())
        )
        self.runtime.session.render(node)

    def paint_frame(self, area: Area, frame: Frame, *, z: int = 0) -> Area:
        self._paint(
            Panel(
                child=TextBlock(),
                background=frame.background,
                border=frame.border,
                border_color=frame.border_color,
                border_sides=(
                    tuple(frame.border_sides)
                    if frame.border_sides is not None
                    else None
                ),
                title=frame.title,
                title_position=frame.title_position,
                padding=frame.padding,
            ),
            area,
            z=z,
        )
        padding = Padding.parse(frame.padding)
        sides = set(frame.border_sides or ())
        all_borders = frame.border is not None
        left = padding.left + int(all_borders or "left" in sides)
        right = padding.right + int(all_borders or "right" in sides)
        top = padding.top + int(all_borders or "top" in sides)
        bottom = padding.bottom + int(all_borders or "bottom" in sides)
        return Area(
            x=area.x + left,
            y=area.y + top,
            width=max(0, area.width - left - right),
            height=max(0, area.height - top - bottom),
        )

    paint_chrome = paint_frame

    def split_layout(
        self,
        area: Area,
        direction: str,
        gap: int,
        constraints: collections.abc.Sequence[Any],
    ) -> list[Area]:
        lowered = []
        for constraint in constraints:
            if constraint.kind == "length":
                value = native.Constraint.length(constraint.value)
            elif constraint.kind == "percentage":
                value = native.Constraint.percentage(constraint.value)
            elif constraint.kind == "ratio":
                value = native.Constraint.ratio(
                    constraint.value, constraint.value2
                )
            elif constraint.kind == "min":
                value = native.Constraint.min(constraint.value)
            elif constraint.kind == "max":
                value = native.Constraint.max(constraint.value)
            else:
                value = native.Constraint.fill(max(1, constraint.value))
            lowered.append(value)
        layout = native.Layout.new(
            native.Direction.Horizontal
            if direction == "horizontal"
            else native.Direction.Vertical,
            lowered,
        )
        if gap:
            layout = layout.spacing(gap)
        return [
            Area(
                x=rect.x,
                y=rect.y,
                width=rect.width,
                height=rect.height,
            )
            for rect in layout.split(
                native.Rect(area.x, area.y, area.width, area.height)
            )
        ]

    def measure_field_slot(
        self, value: Any, direction: str, field: Any = None
    ) -> int:
        if value is None:
            return 0
        if isinstance(value, str):
            lines = value.splitlines() or [""]
            return (
                len(lines) if direction == "vertical" else max(map(len, lines))
            )
        get_size = getattr(value, "get_size", None)
        if callable(get_size):
            from xnano.beta.components.component import ComponentRenderContext

            size = get_size(
                ComponentRenderContext(
                    area=Area(x=0, y=0, width=0, height=0),
                    terminal=self.runtime,
                    state=self.runtime.state,
                    component=value,
                )
            )
            return size.height if direction == "vertical" else size.width
        return 1

    def paint_field_slot(
        self,
        value: Any,
        area: Area,
        field: Any,
        *,
        parent_z: int = 0,
        effect_key: str | None = None,
        owner: Any = None,
        owner_field_name: str | None = None,
    ) -> None:
        if isinstance(value, collections.abc.Sequence) and not isinstance(
            value, (str, bytes)
        ):
            direction = field.direction or "vertical"
            gap = field.gap or 0
            constraints = [
                LayoutConstraint(
                    "length",
                    max(1, self.measure_field_slot(item, direction, field)),
                )
                for item in value
            ]
            for item, item_area in zip(
                value, self.split_layout(area, direction, gap, constraints)
            ):
                self.paint_field_slot(
                    item,
                    item_area,
                    field,
                    parent_z=parent_z,
                    effect_key=effect_key,
                )
            return
        if isinstance(getattr(type(value), "_grid_fields", None), dict):
            value._grid_build_frame(area, self)
            return
        compose = getattr(value, "compose", None)
        if callable(compose):
            from xnano.beta.components.component import ComponentRenderContext

            context = ComponentRenderContext(
                area=area,
                terminal=self.runtime,
                state=self.runtime.state,
                component=value,
            )
            if not getattr(value, "visible", True):
                return
            area = value.before_render(context, area)
            frame = value.get_frame()
            if frame is not None:
                area = self.paint_frame(area, frame, z=value.z)
            variant = resolve_responsive_variant(
                getattr(type(value), "_component_responsive_composes", None),
                self.runtime.size[0],
            )
            if variant is not None:
                compose = getattr(value, variant)
            content = compose(context)
            if content is not None:
                self._paint(
                    content,
                    area,
                    z=getattr(value, "z", parent_z),
                    effect_key=effect_key,
                )
            value.after_render(context, area)
            return
        self._paint(
            TextBlock(
                text=str(value),
                color=getattr(field, "color", None),
                background=getattr(field, "background", None),
                modifiers=tuple(getattr(field, "modifiers", ()) or ()),
                align=getattr(field, "align", None),
            ),
            area,
            z=parent_z,
            effect_key=effect_key,
        )

    def paint_field_wireframe(self, area: Area, *, z: int = 0) -> None:
        # Painted just beneath the field's content so live text renders
        # above the dotted skeleton; empty content cells stay transparent
        # and reveal the dots around it.
        self._paint(
            TextBlock(
                text="\n".join("·" * area.width for _ in range(area.height)),
                color="slate-500",
                modifiers=("dim",),
                wrap=False,
            ),
            area,
            z=z - 1,
        )

    def paint_stage(self) -> None:
        for command in self.runtime.stage._commands:
            self._paint(
                TextBlock(
                    text=str(command["value"])[:1],
                    color=command["color"],
                    background=command["background"],
                    modifiers=command["modifiers"],
                    wrap=False,
                ),
                Area(
                    x=command["x"],
                    y=command["y"],
                    width=1,
                    height=1,
                ),
                z=10_000,
            )
        self.runtime.stage._commands.clear()


__all__ = ("TerminalController",)
