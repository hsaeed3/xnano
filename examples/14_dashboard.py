"""
A dashboard: a chart, a bar chart and a table, refreshed on a timer.

Every widget is described once and placed. A ``terminal.every`` timer then hands each one fresh
numbers a few times a second; assigning ``datasets``, ``data`` or ``rows`` is all it takes to
redraw. Press ``q`` to quit.
"""

import math

import xnano
from xnano.styles import Style
from xnano.widgets import (
    Bar,
    BarChart,
    Block,
    Chart,
    ChartAxis,
    ChartDataset,
    Table,
)

WIDTH = 60
POINTS = 40


def wave(elapsed_seconds: float, phase: float) -> list[tuple[float, float]]:
    """A sine wave sampled at ``POINTS`` positions."""
    return [
        (float(point), math.sin(point / 5 + elapsed_seconds * 2 + phase))
        for point in range(POINTS)
    ]


def main() -> None:
    """Draw the dashboard and keep its numbers moving."""
    with xnano.open(width=WIDTH, height=18) as terminal:
        chart = Chart(
            [
                ChartDataset(name='cpu', data=wave(0, 0), style=Style('green')),
                ChartDataset(name='gpu', data=wave(0, 2), style=Style('magenta')),
            ],
            x_axis=ChartAxis(bounds=(0, POINTS)),
            y_axis=ChartAxis(bounds=(-1, 1)),
            block=Block('load', border_type='rounded'),
        )
        bars = BarChart(
            [Bar(3, 'mon'), Bar(5, 'tue'), Bar(2, 'wed'), Bar(6, 'thu')],
            bar_width=5,
            maximum=8,
            block=Block('requests', border_type='rounded'),
        )
        table = Table(
            [['api', '12 ms'], ['db', '3 ms']],
            header=['service', 'latency'],
            widths=[16, 7],
            block=Block('services', border_type='rounded'),
        )
        terminal.add(chart, width=WIDTH, height=9)
        terminal.add(bars, y=9, width=34, height=9)
        terminal.add(table, x=34, y=9, width=WIDTH - 34, height=9)

        @terminal.every(0.2)
        def refresh(context: xnano.Context) -> None:
            elapsed = context.clock.elapsed_seconds
            chart.datasets = [
                ChartDataset(name='cpu', data=wave(elapsed, 0), style=Style('green')),
                ChartDataset(name='gpu', data=wave(elapsed, 2), style=Style('magenta')),
            ]
            bars.clear()
            for index, day in enumerate(('mon', 'tue', 'wed', 'thu')):
                bars.append(Bar(round(4 + 3 * math.sin(elapsed + index)), day))
            table.rows = [
                ['api', f'{12 + round(4 * math.sin(elapsed))} ms'],
                ['db', f'{3 + round(math.cos(elapsed))} ms'],
            ]

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
