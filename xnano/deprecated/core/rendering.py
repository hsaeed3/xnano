"""
xnano.deprecated.core.rendering

---

Lower components and content primitives into ``xnano_core`` render nodes.
"""

from __future__ import annotations

import collections
import functools
from typing import Any

from xnano.deprecated import _native as engine
from xnano.deprecated import _ratatui as ratatui
from xnano.deprecated.colors import get_native_color
from xnano.deprecated.core.content import (
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

_MARKERS = {
    'dot': ratatui.RatatuiMarker.Dot,
    'block': ratatui.RatatuiMarker.Block,
    'bar': ratatui.RatatuiMarker.Bar,
    'braille': ratatui.RatatuiMarker.Braille,
    'half_block': ratatui.RatatuiMarker.HalfBlock,
}
_GRAPH_TYPES = {
    'scatter': ratatui.RatatuiGraphType.Scatter,
    'line': ratatui.RatatuiGraphType.Line,
    'bar': ratatui.RatatuiGraphType.Bar,
}
_LEGEND_POSITIONS = {
    'top': ratatui.RatatuiLegendPosition.Top,
    'top_right': ratatui.RatatuiLegendPosition.TopRight,
    'top_left': ratatui.RatatuiLegendPosition.TopLeft,
    'left': ratatui.RatatuiLegendPosition.Left,
    'right': ratatui.RatatuiLegendPosition.Right,
    'bottom': ratatui.RatatuiLegendPosition.Bottom,
    'bottom_right': ratatui.RatatuiLegendPosition.BottomRight,
    'bottom_left': ratatui.RatatuiLegendPosition.BottomLeft,
}
_BORDER_TYPES = {
    'plain': ratatui.RatatuiBorderType.Plain,
    'rounded': ratatui.RatatuiBorderType.Rounded,
    'double': ratatui.RatatuiBorderType.Double,
    'thick': ratatui.RatatuiBorderType.Thick,
    'quadrant_inside': ratatui.RatatuiBorderType.QuadrantInside,
    'quadrant_outside': ratatui.RatatuiBorderType.QuadrantOutside,
}
_BORDER_SIDES = {
    'top': ratatui.RatatuiBorders.TOP,
    'right': ratatui.RatatuiBorders.RIGHT,
    'bottom': ratatui.RatatuiBorders.BOTTOM,
    'left': ratatui.RatatuiBorders.LEFT,
}
_ALIGNMENTS = {
    None: None,
    'left': ratatui.RatatuiAlignment.Left,
    'center': ratatui.RatatuiAlignment.Center,
    'right': ratatui.RatatuiAlignment.Right,
}
_SCROLLBAR_ORIENTATIONS = {
    'vertical_right': ratatui.RatatuiScrollbarOrientation.VerticalRight,
    'vertical_left': ratatui.RatatuiScrollbarOrientation.VerticalLeft,
    'horizontal_bottom': ratatui.RatatuiScrollbarOrientation.HorizontalBottom,
    'horizontal_top': ratatui.RatatuiScrollbarOrientation.HorizontalTop,
}
_MODIFIERS = {
    'bold': ratatui.RatatuiModifier.BOLD,
    'dim': ratatui.RatatuiModifier.DIM,
    'italic': ratatui.RatatuiModifier.ITALIC,
    'underline': ratatui.RatatuiModifier.UNDERLINED,
    'slow_blink': ratatui.RatatuiModifier.SLOW_BLINK,
    'rapid_blink': ratatui.RatatuiModifier.RAPID_BLINK,
    'reversed': ratatui.RatatuiModifier.REVERSED,
    'hidden': ratatui.RatatuiModifier.HIDDEN,
    'crossed_out': ratatui.RatatuiModifier.CROSSED_OUT,
}


def _native_modifiers(values: tuple[str, ...]) -> list[Any]:
    """Convert character modifier names for the native renderer."""
    return [_MODIFIERS[value] for value in values]


@functools.lru_cache(maxsize=4096)
def _native_style(
    foreground: Any,
    background: Any,
    modifiers: tuple[str, ...],
) -> Any:
    """Build one native style from public colors and modifier names."""
    style = ratatui.RatatuiStyle.default()
    native_foreground = get_native_color(foreground)
    if native_foreground is not None:
        style = style.foreground(native_foreground)
    native_background = get_native_color(background)
    if native_background is not None:
        style = style.background(native_background)
    for modifier in modifiers:
        style = style.add_modifier(_MODIFIERS[modifier])
    return style


def _span(
    text: str,
    foreground: Any = None,
    background: Any = None,
    modifiers: tuple[str, ...] = (),
) -> Any:
    """Build one styled native span."""
    return ratatui.RatatuiSpan.styled(
        text, _native_style(foreground, background, tuple(modifiers))
    )


def _line_from_runs(runs: tuple[Run, ...]) -> Any:
    """Build one native line from styled runs."""
    return ratatui.RatatuiLine.from_spans(
        [_span(run.text, run.foreground, run.background, run.modifiers) for run in runs]
    )


def _line_from_value(value: Any) -> Any:
    """Build one native line from public text content."""
    if isinstance(value, Run):
        return _line_from_runs((value,))
    if isinstance(value, TextBlock):
        if value.lines:
            return _line_from_runs(value.lines[0])
        return ratatui.RatatuiLine.from_spans(
            [_span(value.text, value.foreground, value.background, value.modifiers)]
        )
    return ratatui.RatatuiLine.raw(str(value))


def _table_row(row: TableRow) -> engine.CoreTableRow:
    """Convert a table row for the native table widget."""
    cells = []
    for cell in row.cells:
        if isinstance(cell, str):
            cells.append(engine.CoreTableCell(_line_from_value(cell)))
        else:
            cells.append(
                engine.CoreTableCell(
                    _line_from_value(cell.content),
                    foreground=get_native_color(cell.foreground),
                    background=get_native_color(cell.background),
                    modifiers=_native_modifiers(cell.modifiers),
                )
            )
    return engine.CoreTableRow(
        cells,
        foreground=get_native_color(row.foreground),
        background=get_native_color(row.background),
        height=row.height,
    )


def _foreground_style(color: Any) -> Any:
    """Build a native foreground style when a color was supplied."""
    native_color = get_native_color(color)
    return (
        ratatui.RatatuiStyle.default().foreground(native_color) if native_color else None
    )


def _plot_axis(axis: PlotAxis) -> Any:
    """Lower one plot axis."""
    result = ratatui.RatatuiAxis.default()
    if axis.title is not None:
        result = result.title(axis.title)
    if axis.bounds is not None:
        result = result.bounds(axis.bounds)
    if axis.labels is not None:
        result = result.labels(list(axis.labels))
    style = _foreground_style(axis.color)
    return result.style(style) if style is not None else result


def _plot_content(content: Plot) -> engine.CoreRenderContent:
    """Lower a plot through the native chart widget."""
    datasets = []
    for dataset in content.datasets:
        item = ratatui.RatatuiDataset.default().data(list(dataset.data))
        if dataset.name is not None:
            item = item.name(dataset.name)
        item = item.graph_type(_GRAPH_TYPES[dataset.graph_type])
        if dataset.marker is not None:
            item = item.marker(_MARKERS[dataset.marker])
        style = _foreground_style(dataset.color or content.color)
        datasets.append(item.style(style) if style is not None else item)
    chart = ratatui.RatatuiChart.new(datasets)
    if content.x_axis is not None:
        chart = chart.x_axis(_plot_axis(content.x_axis))
    if content.y_axis is not None:
        chart = chart.y_axis(_plot_axis(content.y_axis))
    style = _foreground_style(content.color)
    if style is not None:
        chart = chart.style(style)
    position = content.legend_position if content.legend else None
    chart = chart.legend_position(
        _LEGEND_POSITIONS[position] if position is not None else None
    )
    return engine.CoreRenderContent.ratatui_widget(chart)


def _canvas_shape(shape: Any) -> engine.CoreCanvasShape:
    """Lower one canvas shape."""
    color = get_native_color(getattr(shape, 'color', None))
    if isinstance(shape, CanvasLine):
        return engine.CoreCanvasShape.line(
            shape.x1, shape.y1, shape.x2, shape.y2, color=color
        )
    if isinstance(shape, CanvasPoints):
        return engine.CoreCanvasShape.points(list(shape.coords), color=color)
    if isinstance(shape, CanvasRectangle):
        return engine.CoreCanvasShape.rectangle(
            shape.x, shape.y, shape.width, shape.height, color=color
        )
    if isinstance(shape, CanvasCircle):
        return engine.CoreCanvasShape.circle(shape.x, shape.y, shape.radius, color=color)
    if isinstance(shape, CanvasPrint):
        return engine.CoreCanvasShape.text(
            shape.x, shape.y, _line_from_value(shape.content), color
        )
    raise TypeError(
        f'Cannot draw a canvas shape of type {type(shape).__name__}. '
        'Use CanvasLine, CanvasPoints, CanvasRectangle, CanvasCircle or CanvasPrint.'
    )


def _grid_field_size(sizing: Any) -> engine.CoreNodeSize | int:
    """Convert a grid field's declared size along the grid's direction."""
    if sizing is None or sizing.kind in {'fraction', 'fill'}:
        return engine.CoreNodeSize.fill(1 if sizing is None else max(1, sizing.value))
    if sizing.kind == 'cells':
        return sizing.value
    if sizing.kind == 'percent':
        return engine.CoreNodeSize.percent(sizing.value)
    if sizing.kind == 'ratio':
        return engine.CoreNodeSize.ratio(sizing.value, sizing.denominator)
    return engine.CoreNodeSize.minimum(sizing.minimum or 1)


_CELL_CANVAS_WIDGET_CACHE_CAPACITY = 64
_cell_canvas_widget_cache: collections.OrderedDict[int, tuple[Any, Any]] = (
    collections.OrderedDict()
)
"""Identity-keyed LRU of lowered ``CellCanvas`` widgets.

Lowering a canvas builds one native line per row and resolves a native style
for every span, which dominates the cost of painting per-pixel canvases
(backgrounds, splashes, image frames). A canvas usually repaints unchanged
across many frames, so the lowered ``CoreWidget`` is cached and reused.
``CoreWidget`` is immutable, so sharing one instance across frames is safe.
Each entry keeps a strong reference to the source canvas so its ``id`` cannot
be reused by another object while cached. The cache is bounded so long-running
animations do not grow it without limit."""


def cell_canvas_widget(content: CellCanvas) -> engine.CoreWidget:
    """
    Return the native widget that paints a ``CellCanvas``.

    Args:
        content: The canvas to paint.

    Returns:
        A text widget with one unwrapped line per canvas row.
    """
    key = id(content)
    cached = _cell_canvas_widget_cache.get(key)
    if cached is not None and cached[0] is content:
        _cell_canvas_widget_cache.move_to_end(key)
        return cached[1]
    lines = [
        ratatui.RatatuiLine.from_spans(
            [
                _span(span.text, span.foreground, span.background, span.modifiers)
                for span in row
            ]
        )
        for row in content.rows
    ]
    widget = engine.CoreWidget.text(lines, should_wrap=False)
    _cell_canvas_widget_cache[key] = (content, widget)
    _cell_canvas_widget_cache.move_to_end(key)
    while len(_cell_canvas_widget_cache) > _CELL_CANVAS_WIDGET_CACHE_CAPACITY:
        _cell_canvas_widget_cache.popitem(last=False)
    return widget


def _panel_node(content: Panel) -> engine.CoreRenderNode:
    """Lower a panel: a block behind its child, inset by borders and padding."""
    from xnano.deprecated.area import Padding

    block = ratatui.RatatuiBlock.default()
    sides = content.border_sides
    if content.border is not None or sides:
        borders = ratatui.RatatuiBorders.ALL
        if sides:
            borders = ratatui.RatatuiBorders.NONE
            for side in sides:
                borders = borders | _BORDER_SIDES[side]
        block = block.borders(borders).border_type(
            _BORDER_TYPES[content.border or 'plain']
        )
    if content.title is not None:
        block = (
            block.title_bottom(content.title)
            if content.title_position == 'bottom'
            else block.title_top(content.title)
        )
    border_color = get_native_color(content.border_color)
    if border_color is not None:
        block = block.border_style(
            ratatui.RatatuiStyle.default().foreground(border_color)
        )
    background = get_native_color(content.background)
    if background is not None:
        block = block.style(ratatui.RatatuiStyle.default().background(background))
    padding = Padding.parse(content.padding)
    has_all_borders = content.border is not None
    side_names = set(sides or ())
    inset = ratatui.RatatuiPadding.new(
        padding.left + int(has_all_borders or 'left' in side_names),
        padding.right + int(has_all_borders or 'right' in side_names),
        padding.top + int(has_all_borders or 'top' in side_names),
        padding.bottom + int(has_all_borders or 'bottom' in side_names),
    )
    return engine.CoreRenderNode(
        content=engine.CoreRenderContent.ratatui_widget(block),
        children=[
            engine.CoreRenderNode(
                padding=inset,
                children=[lower_content(content.child)],
            )
        ],
        is_visible=content.visible,
    )


def lower_content(content: Any) -> engine.CoreRenderNode:
    """
    Lower a renderable into one native render node.

    Args:
        content: String, component, content primitive, or native payload.

    Returns:
        A render node accepted by ``CoreSession.render``.
    """
    grid_fields = getattr(type(content), '_grid_fields', None)
    if isinstance(grid_fields, dict):
        is_vertical = content._grid_direction != 'horizontal'
        children: list[engine.CoreRenderNode] = []
        for name, field in grid_fields.items():
            value = getattr(content, name, None)
            if value is None or getattr(field, 'visible', None) is False:
                continue
            children.append(
                engine.CoreRenderNode(
                    key=name,
                    size=_grid_field_size(field.height if is_vertical else field.width),
                    children=[lower_content(value)],
                )
            )
        return engine.CoreRenderNode(
            children=children,
            arrangement='column' if is_vertical else 'row',
            spacing=content._grid_gap,
        )
    compose = getattr(content, 'compose', None)
    if callable(compose):
        from xnano.deprecated.area import Area
        from xnano.deprecated.components.component import ComponentRenderContext
        from xnano.deprecated.core.runtime import get_active_runtime

        runtime = get_active_runtime()
        # A component with responsive compose variants swaps in the one
        # matching the live window width; the plain `compose` handles
        # every tier a component leaves unoverridden. Skipped entirely for
        # content without an override map.
        responsive = getattr(type(content), '_component_responsive_composes', None)
        if responsive and runtime is not None:
            from xnano.deprecated.utils.responsive import (
                resolve_responsive_variant,
            )

            variant = resolve_responsive_variant(responsive, runtime.size[0])
            if variant is not None:
                compose = getattr(content, variant)
        width, height = runtime.size if runtime is not None else (0, 0)
        content = compose(
            ComponentRenderContext(
                area=Area(x=0, y=0, width=width, height=height),
            )
        )
    if content is None:
        return engine.CoreRenderNode()
    if isinstance(content, str):
        content = TextBlock(text=content)
    widget: engine.CoreWidget | engine.CoreRenderContent
    if isinstance(content, Run):
        widget = engine.CoreWidget.text(
            _span(
                content.text, content.foreground, content.background, content.modifiers
            ),
            should_wrap=False,
        )
    elif isinstance(content, TextBlock):
        widget = engine.CoreWidget.text(
            [_line_from_runs(line) for line in content.lines]
            if content.lines
            else content.text,
            foreground=get_native_color(content.foreground),
            background=get_native_color(content.background),
            modifiers=_native_modifiers(content.modifiers),
            alignment=_ALIGNMENTS[content.horizontal_align],
            should_wrap=content.wrap,
        )
    elif isinstance(content, Gauge):
        widget = engine.CoreWidget.gauge(
            content.progress,
            label=content.label,
            foreground=get_native_color(content.foreground),
            background=get_native_color(content.background),
        )
    elif isinstance(content, LineGauge):
        widget = engine.CoreWidget.line_gauge(
            content.progress,
            label=content.label,
            foreground=get_native_color(content.foreground),
            background=get_native_color(content.background),
            filled_foreground=get_native_color(content.filled_color),
            unfilled_foreground=get_native_color(content.unfilled_color),
        )
    elif isinstance(content, Bars):
        widget = engine.CoreWidget.bar_chart(
            [
                engine.CoreBarGroup(
                    [
                        engine.CoreBar(
                            bar.value,
                            label=bar.label,
                            text_value=bar.text_value,
                            foreground=get_native_color(bar.color),
                            value_foreground=get_native_color(bar.value_color),
                        )
                        for bar in group.bars
                    ],
                    label=group.label,
                )
                for group in content.groups
            ],
            bar_width=content.bar_width,
            bar_gap=content.bar_gap,
            group_gap=content.group_gap,
            maximum_value=content.max_value,
            direction=(
                ratatui.RatatuiDirection.Horizontal
                if content.direction == 'horizontal'
                else ratatui.RatatuiDirection.Vertical
            ),
            foreground=get_native_color(content.color),
            value_foreground=get_native_color(content.value_color),
            label_foreground=get_native_color(content.label_color),
        )
    elif isinstance(content, Plot):
        widget = _plot_content(content)
    elif isinstance(content, Sparkline):
        widget = engine.CoreWidget.sparkline(
            list(content.data),
            maximum_value=content.max_value,
            foreground=get_native_color(content.foreground),
            background=get_native_color(content.background),
            absent_value_foreground=get_native_color(content.absent_value_color),
            absent_value_symbol=content.absent_value_symbol,
        )
    elif isinstance(content, Items):
        widget = engine.CoreWidget.item_list(
            [_line_from_value(item) for item in content.items],
            selected_index=content.selected,
            foreground=get_native_color(content.foreground),
            background=get_native_color(content.background),
            highlight_foreground=get_native_color(content.highlight_color),
            highlight_background=get_native_color(content.highlight_background),
            highlight_symbol=content.highlight_symbol,
        )
    elif isinstance(content, TableGrid):
        columns = max(
            (len(row.cells) for row in content.rows),
            default=(len(content.header.cells) if content.header is not None else 1),
        )
        column_widths = (
            [ratatui.RatatuiConstraint.fill(1)] * columns
            if content.column_widths is None
            else [
                ratatui.RatatuiConstraint.percentage(int(width * 100))
                if isinstance(width, float)
                else ratatui.RatatuiConstraint.length(width)
                for width in content.column_widths
            ]
        )
        widget = engine.CoreWidget.table(
            [_table_row(row) for row in content.rows],
            header=_table_row(content.header) if content.header is not None else None,
            footer=_table_row(content.footer) if content.footer is not None else None,
            column_widths=column_widths,
            column_spacing=content.column_spacing,
            selected_row=content.selected_row,
            selected_column=content.selected_column,
            highlight_foreground=get_native_color(content.highlight_color),
            highlight_background=get_native_color(content.highlight_background),
            highlight_symbol=content.highlight_symbol,
        )
    elif isinstance(content, Scrollbar):
        widget = engine.CoreWidget.scrollbar(
            content_length=content.content_length,
            position=content.position,
            viewport_length=content.viewport_length,
            orientation=_SCROLLBAR_ORIENTATIONS.get(
                content.orientation,
                ratatui.RatatuiScrollbarOrientation.VerticalRight,
            ),
            foreground=get_native_color(content.color),
            thumb_foreground=get_native_color(content.thumb_color),
            track_foreground=get_native_color(content.track_color),
            begin_symbol=content.begin_symbol,
            end_symbol=content.end_symbol,
        )
    elif isinstance(content, Clear):
        widget = engine.CoreWidget.clear()
    elif isinstance(content, CellCanvas):
        widget = cell_canvas_widget(content)
    elif isinstance(content, Canvas):
        widget = engine.CoreWidget.canvas(
            [_canvas_shape(shape) for shape in content.shapes],
            x_bounds=content.x_bounds,
            y_bounds=content.y_bounds,
            background=get_native_color(content.background),
            marker=_MARKERS[content.marker],
        )
    elif isinstance(content, Native):
        payload = content.payload
        if isinstance(payload, engine.CoreRenderNode):
            return payload
        if isinstance(payload, (engine.CoreWidget, engine.CoreRenderContent)):
            widget = payload
        else:
            widget = engine.CoreWidget.text(str(payload))
    elif isinstance(content, Stack):
        return engine.CoreRenderNode(
            children=[lower_content(child) for child in content.children],
            arrangement='row' if content.direction == 'horizontal' else 'column',
            spacing=content.gap,
        )
    elif isinstance(content, Panel):
        return _panel_node(content)
    else:
        widget = engine.CoreWidget.text(str(content))
    return engine.CoreRenderNode(
        content=widget,
        is_visible=getattr(content, 'visible', True),
    )


__all__ = ('cell_canvas_widget', 'lower_content')
