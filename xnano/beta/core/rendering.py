"""xnano.beta.core.rendering

---

Lower beta components and content primitives into ``xnano_core`` render nodes.
"""

from __future__ import annotations

from typing import Any

import xnano_core.rust.native as native
from xnano_core import core

from xnano.beta.colors import get_native_color
from xnano.beta.core.content import (
    Bars,
    Canvas,
    CanvasCircle,
    CanvasLine,
    CanvasPoints,
    CanvasPrint,
    CanvasRectangle,
    CellCanvas,
    Clear,
    Gauge,
    Items,
    LineGauge,
    Native,
    Panel,
    Plot,
    PlotAxis,
    Run,
    Scrollbar,
    Sparkline,
    Stack,
    TableGrid,
    TableRow,
    TextBlock,
)

_MARKERS = {"dot": 0, "block": 1, "bar": 2, "braille": 3, "half_block": 4}
_NATIVE_MARKERS = {
    "dot": native.Marker.Dot,
    "block": native.Marker.Block,
    "bar": native.Marker.Bar,
    "braille": native.Marker.Braille,
    "half_block": native.Marker.HalfBlock,
}
_GRAPH_TYPES = {
    "scatter": native.GraphType.Scatter,
    "line": native.GraphType.Line,
    "bar": native.GraphType.Bar,
}
_LEGEND_POSITIONS = {
    "top": native.LegendPosition.Top,
    "top_right": native.LegendPosition.TopRight,
    "top_left": native.LegendPosition.TopLeft,
    "left": native.LegendPosition.Left,
    "right": native.LegendPosition.Right,
    "bottom": native.LegendPosition.Bottom,
    "bottom_right": native.LegendPosition.BottomRight,
    "bottom_left": native.LegendPosition.BottomLeft,
}
_BORDER_TYPES = {
    "plain": native.BorderType.Plain,
    "rounded": native.BorderType.Rounded,
    "double": native.BorderType.Double,
    "thick": native.BorderType.Thick,
    "quadrant_inside": native.BorderType.QuadrantInside,
    "quadrant_outside": native.BorderType.QuadrantOutside,
}
_BORDER_SIDES = {
    "top": native.Borders.TOP,
    "right": native.Borders.RIGHT,
    "bottom": native.Borders.BOTTOM,
    "left": native.Borders.LEFT,
}

_ALIGNMENTS = {
    None: None,
    "left": 0,
    "center": 1,
    "right": 2,
}
_MODIFIERS = {
    "bold": native.Modifier.BOLD,
    "dim": native.Modifier.DIM,
    "italic": native.Modifier.ITALIC,
    "underline": native.Modifier.UNDERLINED,
    "slow_blink": native.Modifier.SLOW_BLINK,
    "rapid_blink": native.Modifier.RAPID_BLINK,
    "reversed": native.Modifier.REVERSED,
    "hidden": native.Modifier.HIDDEN,
    "crossed_out": native.Modifier.CROSSED_OUT,
}


def _native_modifiers(values: tuple[str, ...]) -> list[Any]:
    """Convert character modifier names for the native renderer."""
    return [_MODIFIERS[value] for value in values]


def _line_from_runs(runs: tuple[Run, ...]) -> core.IrLine:
    """Build one renderer line from styled beta runs."""
    return core.IrLine.from_spans(
        [
            (
                run.text,
                get_native_color(run.color),
                get_native_color(run.background),
                _native_modifiers(run.modifiers),
            )
            for run in runs
        ]
    )


def _line_from_value(value: Any) -> core.IrLine:
    """Build one renderer line from public text content."""
    if isinstance(value, Run):
        return _line_from_runs((value,))
    if isinstance(value, TextBlock):
        if value.lines:
            return _line_from_runs(value.lines[0])
        return core.IrLine.styled(
            value.text,
            get_native_color(value.color),
            get_native_color(value.background),
            _native_modifiers(value.modifiers),
        )
    return core.IrLine.raw(str(value))


def _table_row(row: TableRow) -> tuple[list[Any], Any, Any, int]:
    """Convert a beta table row for render IR."""
    cells = []
    for cell in row.cells:
        if isinstance(cell, str):
            cells.append((_line_from_value(cell), None, None, []))
        else:
            cells.append(
                (
                    _line_from_value(cell.content),
                    get_native_color(cell.color),
                    get_native_color(cell.background),
                    _native_modifiers(cell.modifiers),
                )
            )
    return (
        cells,
        get_native_color(row.color),
        get_native_color(row.background),
        row.height,
    )


def _native_style(color: Any) -> Any:
    """Build a native foreground style when a color was supplied."""
    native_color = get_native_color(color)
    return native.Style.default().fg(native_color) if native_color else None


def _plot_axis(axis: PlotAxis) -> Any:
    """Lower one beta plot axis."""
    result = native.Axis.default()
    if axis.title is not None:
        result = result.title(axis.title)
    if axis.bounds is not None:
        result = result.bounds(axis.bounds)
    if axis.labels is not None:
        result = result.labels(list(axis.labels))
    style = _native_style(axis.color)
    return result.style(style) if style is not None else result


def _plot_node(content: Plot) -> core.CoreRenderNode:
    """Lower a beta plot through the native chart widget."""
    datasets = []
    for dataset in content.datasets:
        item = native.Dataset.default().data(list(dataset.data))
        if dataset.name is not None:
            item = item.name(dataset.name)
        item = item.graph_type(_GRAPH_TYPES[dataset.graph_type])
        if dataset.marker is not None:
            item = item.marker(_NATIVE_MARKERS[dataset.marker])
        style = _native_style(dataset.color or content.color)
        datasets.append(item.style(style) if style is not None else item)
    chart = native.Chart.new(datasets)
    if content.x_axis is not None:
        chart = chart.x_axis(_plot_axis(content.x_axis))
    if content.y_axis is not None:
        chart = chart.y_axis(_plot_axis(content.y_axis))
    style = _native_style(content.color)
    if style is not None:
        chart = chart.style(style)
    position = content.legend_position if content.legend else None
    chart = chart.legend_position(
        _LEGEND_POSITIONS[position] if position is not None else None
    )
    return core.CoreRenderNode(
        content=core.CoreRenderContent.widget(chart),
        z=content.z,
        visible=content.visible,
    )


def _canvas_shape(shape: Any) -> tuple[Any, ...]:
    """Lower one beta canvas shape."""
    color = get_native_color(getattr(shape, "color", None))
    if isinstance(shape, CanvasLine):
        return ("line", shape.x1, shape.y1, shape.x2, shape.y2, color)
    if isinstance(shape, CanvasPoints):
        return ("points", list(shape.coords), color)
    if isinstance(shape, CanvasRectangle):
        return (
            "rect",
            shape.x,
            shape.y,
            shape.width,
            shape.height,
            color,
        )
    if isinstance(shape, CanvasCircle):
        return ("circle", shape.x, shape.y, shape.radius, color)
    if isinstance(shape, CanvasPrint):
        value = shape.content
        if isinstance(value, Run):
            runs = (value,)
        elif isinstance(value, TextBlock) and value.lines:
            runs = value.lines[0]
        elif isinstance(value, TextBlock):
            runs = (
                Run(
                    text=value.text,
                    color=value.color,
                    background=value.background,
                    modifiers=value.modifiers,
                ),
            )
        else:
            runs = (Run(text=str(value)),)
        spans = [
            (
                run.text,
                get_native_color(run.color),
                get_native_color(run.background),
                _native_modifiers(run.modifiers),
            )
            for run in runs
        ]
        return ("print", shape.x, shape.y, spans)
    raise TypeError(f"Unsupported canvas shape: {type(shape)!r}")


def lower_content(content: Any) -> core.CoreRenderNode:
    """Lower a beta renderable into one native render node.

    Args:
        content: String, component, content primitive, or native payload.

    Returns:
        A render node accepted by ``CoreSession.render``.
    """
    grid_fields = getattr(type(content), "_grid_fields", None)
    if isinstance(grid_fields, dict):
        children: list[core.CoreRenderNode] = []
        constraints: list[Any] = []
        for name, field in grid_fields.items():
            value = getattr(content, name, None)
            if value is None or getattr(field, "visible", None) is False:
                continue
            children.append(
                core.CoreRenderNode(
                    content=core.CoreRenderContent.empty(),
                    effect_key=name,
                    constraints=[native.Constraint.fill(1)],
                    children=[lower_content(value)],
                )
            )
            sizing = (
                field.height
                if content._grid_direction == "vertical"
                else field.width
            )
            if sizing is None or sizing.kind in {"fraction", "fill"}:
                constraint = native.Constraint.fill(
                    1 if sizing is None else max(1, sizing.value)
                )
            elif sizing.kind == "cells":
                constraint = native.Constraint.length(sizing.value)
            elif sizing.kind == "percent":
                constraint = native.Constraint.percentage(sizing.value)
            elif sizing.kind == "ratio":
                constraint = native.Constraint.ratio(
                    sizing.value,
                    sizing.denominator,
                )
            else:
                constraint = native.Constraint.min(sizing.minimum or 1)
            constraints.append(constraint)
        factory = (
            core.CoreRenderNode.row
            if content._grid_direction == "horizontal"
            else core.CoreRenderNode.column
        )
        return factory(
            children,
            constraints=constraints,
            gap=content._grid_gap,
        )
    compose = getattr(content, "compose", None)
    if callable(compose):
        from xnano.beta.components.component import ComponentRenderContext
        from xnano.beta.types import Area

        # A component with responsive compose variants swaps in the one
        # matching the live window width; the plain `compose` handles
        # every tier a component leaves unoverridden. Skipped entirely for
        # content without an override map.
        responsive = getattr(
            type(content), "_component_responsive_composes", None
        )
        if responsive:
            from xnano.beta.core.runtime import get_active_runtime
            from xnano.beta.utils.responsive import (
                resolve_responsive_variant,
            )

            runtime = get_active_runtime()
            if runtime is not None:
                variant = resolve_responsive_variant(
                    responsive, runtime.size[0]
                )
                if variant is not None:
                    compose = getattr(content, variant)
        content = compose(
            ComponentRenderContext(
                area=Area(x=0, y=0, width=0, height=0),
            )
        )
    if content is None:
        return core.CoreRenderNode.leaf(core.CoreRenderContent.empty())
    if isinstance(content, str):
        content = TextBlock(text=content)
    if isinstance(content, Run):
        render_ir = core.CoreRenderIR.span(
            content.text,
            get_native_color(content.color),
            get_native_color(content.background),
            _native_modifiers(content.modifiers),
        )
    elif isinstance(content, TextBlock):
        if content.lines:
            render_ir = core.CoreRenderIR.paragraph_lines(
                [_line_from_runs(line) for line in content.lines],
                get_native_color(content.color),
                get_native_color(content.background),
                _native_modifiers(content.modifiers),
                _ALIGNMENTS[content.align],
                content.wrap,
            )
        else:
            render_ir = core.CoreRenderIR.paragraph_raw(
                content.text,
                get_native_color(content.color),
                get_native_color(content.background),
                _native_modifiers(content.modifiers),
                _ALIGNMENTS[content.align],
                content.wrap,
            )
    elif isinstance(content, Gauge):
        render_ir = core.CoreRenderIR.progress_bar(
            content.progress,
            content.label,
            get_native_color(content.color),
            get_native_color(content.background),
        )
    elif isinstance(content, LineGauge):
        render_ir = core.CoreRenderIR.line_gauge(
            content.progress,
            content.label,
            get_native_color(content.color),
            get_native_color(content.background),
            get_native_color(content.filled_color),
            get_native_color(content.unfilled_color),
        )
    elif isinstance(content, Bars):
        groups = [
            (
                group.label,
                [
                    (
                        bar.value,
                        bar.label,
                        bar.text_value,
                        get_native_color(bar.color),
                        None,
                        get_native_color(bar.value_color),
                        None,
                    )
                    for bar in group.bars
                ],
            )
            for group in content.groups
        ]
        render_ir = core.CoreRenderIR.bar_chart(
            groups,
            content.bar_width,
            content.bar_gap,
            content.group_gap,
            content.max_value,
            content.direction == "horizontal",
            get_native_color(content.color),
            get_native_color(content.value_color),
            get_native_color(content.label_color),
        )
    elif isinstance(content, Plot):
        return _plot_node(content)
    elif isinstance(content, Sparkline):
        render_ir = core.CoreRenderIR.sparkline(
            list(content.data),
            content.max_value,
            get_native_color(content.color),
            get_native_color(content.background),
            get_native_color(content.absent_value_color),
            content.absent_value_symbol,
        )
    elif isinstance(content, Items):
        render_ir = core.CoreRenderIR.list(
            [_line_from_value(item) for item in content.items],
            content.selected,
            get_native_color(content.color),
            get_native_color(content.background),
            get_native_color(content.highlight_color),
            get_native_color(content.highlight_background),
            content.highlight_symbol,
        )
    elif isinstance(content, TableGrid):
        columns = max(
            (len(row.cells) for row in content.rows),
            default=(
                len(content.header.cells) if content.header is not None else 1
            ),
        )
        widths = (
            [(2, 1.0)] * columns
            if content.column_widths is None
            else [
                (1, width * 100.0)
                if isinstance(width, float)
                else (0, float(width))
                for width in content.column_widths
            ]
        )
        render_ir = core.CoreRenderIR.table(
            [_table_row(row) for row in content.rows],
            _table_row(content.header) if content.header is not None else None,
            _table_row(content.footer) if content.footer is not None else None,
            widths,
            content.column_spacing,
            content.selected_row,
            content.selected_column,
            get_native_color(content.highlight_color),
            get_native_color(content.highlight_background),
            content.highlight_symbol,
        )
    elif isinstance(content, Scrollbar):
        orientations = {
            "vertical_right": 0,
            "vertical_left": 1,
            "horizontal_bottom": 2,
            "horizontal_top": 3,
        }
        render_ir = core.CoreRenderIR.scrollbar(
            orientations.get(content.orientation, 0),
            content.content_length,
            content.position,
            content.viewport_length,
            get_native_color(content.color),
            get_native_color(content.thumb_color),
            get_native_color(content.track_color),
            content.begin_symbol,
            content.end_symbol,
        )
    elif isinstance(content, Clear):
        render_ir = core.CoreRenderIR.clear()
    elif isinstance(content, CellCanvas):
        lines = [
            core.IrLine.from_spans(
                [
                    (
                        span.text,
                        get_native_color(span.color),
                        get_native_color(span.background),
                        _native_modifiers(span.modifiers),
                    )
                    for span in row
                ]
            )
            for row in content.rows
        ]
        render_ir = core.CoreRenderIR.text_lines(lines)
    elif isinstance(content, Canvas):
        render_ir = core.CoreRenderIR.canvas(
            [_canvas_shape(shape) for shape in content.shapes],
            content.x_bounds,
            content.y_bounds,
            get_native_color(content.background),
            _MARKERS[content.marker],
        )
    elif isinstance(content, Native):
        if isinstance(content.payload, core.CoreRenderNode):
            return content.payload
        if isinstance(content.payload, core.CoreRenderIR):
            render_ir = content.payload
        else:
            render_ir = core.CoreRenderIR.paragraph_raw(str(content.payload))
    elif isinstance(content, Stack):
        children = [lower_content(child) for child in content.children]
        factory = (
            core.CoreRenderNode.row
            if content.direction == "horizontal"
            else core.CoreRenderNode.column
        )
        return factory(
            children,
            constraints=[native.Constraint.fill(1)] * len(children),
            gap=content.gap,
        )
    elif isinstance(content, Panel):
        from xnano.beta.types import Padding

        block = native.Block.default()
        sides = content.border_sides
        if content.border is not None or sides:
            borders = native.Borders.ALL
            if sides:
                borders = native.Borders.NONE
                for side in sides:
                    borders = borders | _BORDER_SIDES[side]
            block = block.borders(borders).border_type(
                _BORDER_TYPES[content.border or "plain"]
            )
        if content.title is not None:
            block = (
                block.title_bottom(content.title)
                if content.title_position == "bottom"
                else block.title_top(content.title)
            )
        border_color = get_native_color(content.border_color)
        if border_color is not None:
            block = block.border_style(native.Style.default().fg(border_color))
        background = get_native_color(content.background)
        if background is not None:
            block = block.style(native.Style.default().bg(background))
        padding = Padding.parse(content.padding)
        block = block.padding(
            native.Padding.new(
                padding.left,
                padding.right,
                padding.top,
                padding.bottom,
            )
        )
        horizontal_border = int(
            content.border is not None
            or bool(sides and ("left" in sides or "right" in sides))
        )
        vertical_border = int(
            content.border is not None
            or bool(sides and ("top" in sides or "bottom" in sides))
        )
        return core.CoreRenderNode(
            content=core.CoreRenderContent.widget(block),
            direction=native.Direction.Vertical,
            constraints=[native.Constraint.fill(1)],
            margin=native.Margin(
                max(padding.left, padding.right) + horizontal_border,
                max(padding.top, padding.bottom) + vertical_border,
            ),
            children=[lower_content(content.child)],
            z=content.z,
            visible=content.visible,
        )
    else:
        render_ir = core.CoreRenderIR.paragraph_raw(str(content))
    return core.CoreRenderNode(
        content=core.CoreRenderContent.ir(render_ir),
        z=getattr(content, "z", 0),
        visible=getattr(content, "visible", True),
    )


__all__ = ("lower_content",)
