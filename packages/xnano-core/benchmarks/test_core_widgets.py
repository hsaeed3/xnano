"""
Benchmarks for the xnano-core widgets.

A widget repaints as soon as one of its settings is assigned, not when the runtime draws
the next frame, so the timed call of every ``paint`` benchmark is the assignment *and*
the frame that follows it. ``render(format='text')`` is timed separately, as the cost of
painting plus serializing a widget nobody mounted.
"""

from __future__ import annotations

import itertools

import pytest

from xnano_core._xnano_core import (
    Bar,
    BarChart,
    Canvas,
    CanvasCircle,
    CanvasLine,
    CanvasPoints,
    Chart,
    ChartDataset,
    Gauge,
    ItemList,
    Runtime,
    Sparkline,
    Table,
    TableRow,
    Tabs,
)

ROWS = 500


def paint(benchmark, widget, mutate):
    """Time one change to ``widget``'s data together with the runtime frame that shows it."""
    runtime = Runtime.offscreen(width=widget.width, height=widget.height)
    runtime.mount(widget, geometry='inherit')
    runtime.step()

    def change_and_draw():
        mutate()
        runtime.step()

    benchmark.pedantic(change_and_draw, rounds=300, warmup_rounds=5)
    lines = runtime.snapshot().lines()
    runtime.close()
    return lines


def test_table_paint(benchmark):
    rows = [
        TableRow([f'row {index}', 'x' * 10, str(index * 7), 'name', '界面'])
        for index in range(ROWS)
    ]
    table = Table(rows, widths=[10, 12, 8, 8, 8], width=60, height=40)
    selections = itertools.cycle(range(ROWS))

    def mutate():
        table.selected_row = next(selections)

    lines = paint(benchmark, table, mutate)
    assert any('row' in line for line in lines)


def test_table_render_text(benchmark):
    rows = [TableRow([f'row {index}', 'x' * 10, str(index * 7)]) for index in range(ROWS)]
    table = Table(rows, widths=[10, 12, 8], width=40, height=40)
    table.selected_row = ROWS // 2
    text = benchmark(table.render, format='text')
    assert f'row {ROWS // 2}' in text


def test_item_list_paint_long_list(benchmark):
    items = ItemList([f'item {index}' for index in range(20_000)], width=40, height=40)
    selections = itertools.cycle(range(0, 20_000, 7))

    def mutate():
        items.selected = next(selections)

    lines = paint(benchmark, items, mutate)
    assert any('item' in line for line in lines)


def test_tabs_paint(benchmark):
    tabs = Tabs([f'tab {index}' for index in range(30)], selected=0, width=120, height=1)
    lines = paint(benchmark, tabs, tabs.select_next)
    assert 'tab' in lines[0]


def test_gauge_paint(benchmark):
    gauge = Gauge(0.0, width=100, height=3)
    ratios = itertools.cycle((0.25, 0.75))

    def mutate():
        gauge.ratio = next(ratios)

    paint(benchmark, gauge, mutate)


def test_sparkline_paint(benchmark):
    sparkline = Sparkline([index % 17 for index in range(500)], width=200, height=3)
    paint(benchmark, sparkline, lambda: sparkline.append(7))


def test_bar_chart_paint(benchmark):
    chart = BarChart(
        [Bar(index % 9 + 1, f'b{index}') for index in range(30)], width=120, height=20
    )
    maximums = itertools.cycle((10, 11))

    def mutate():
        chart.maximum = next(maximums)

    paint(benchmark, chart, mutate)


def test_line_chart_paint(benchmark):
    datasets = [
        ChartDataset(
            name=f'series {series}',
            data=[(point, (point * (series + 1)) % 50) for point in range(500)],
            graph_type='line',
        )
        for series in range(3)
    ]
    chart = Chart(datasets, width=120, height=30)
    # Replacing a dataset's data forces a repaint of the whole chart.
    sizes = itertools.cycle((500, 499))

    def mutate():
        datasets[0].data = [(point, point % 50) for point in range(next(sizes))]

    paint(benchmark, chart, mutate)


@pytest.mark.parametrize('marker', ['braille', 'block', 'half_block'])
def test_canvas_paint_shapes(benchmark, marker):
    shapes: list = [
        CanvasLine(index, 0, 100 - index, 100, 'green') for index in range(100)
    ]
    animated_circle = CanvasCircle(50, 50, 5, 'blue')
    shapes.append(animated_circle)
    shapes += [CanvasCircle(50, 50, radius, 'blue') for radius in range(10, 45, 5)]
    shapes.append(CanvasPoints([(x, (x * 7) % 100) for x in range(500)], 'yellow'))
    canvas = Canvas(
        (0, 100), (0, 100), marker=marker, shapes=shapes, width=120, height=40
    )
    radii = itertools.cycle((5, 6))

    def mutate():
        animated_circle.radius = next(radii)

    lines = paint(benchmark, canvas, mutate)
    assert any(line.strip() for line in lines)
