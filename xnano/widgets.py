"""
xnano.widgets

Widgets that draw themselves: text, tables, charts, gauges, figures and lists.

A widget is a description of something to draw. Pass one to [`Screen.write`][xnano.devices.Screen.write]
or draw it into a [`Buffer`][xnano.buffers.Buffer]; every number and text in it can be an
[`Expression`][xnano.expressions.Expression] that is evaluated again on each frame.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from xnano_core import Bar as _CoreBar
    from xnano_core import BarChart as _CoreBarChart
    from xnano_core import BarGroup as _CoreBarGroup
    from xnano_core import Block as _CoreBlock
    from xnano_core import Calendar as _CoreCalendar
    from xnano_core import Canvas as _CoreCanvas
    from xnano_core import CanvasCircle as _CoreCanvasCircle
    from xnano_core import CanvasLabel as _CoreCanvasLabel
    from xnano_core import CanvasLine as _CoreCanvasLine
    from xnano_core import CanvasMap as _CoreCanvasMap
    from xnano_core import CanvasPoints as _CoreCanvasPoints
    from xnano_core import CanvasRectangle as _CoreCanvasRectangle
    from xnano_core import Chart as _CoreChart
    from xnano_core import ChartAxis as _CoreChartAxis
    from xnano_core import ChartDataset as _CoreChartDataset
    from xnano_core import Gauge as _CoreGauge
    from xnano_core import ItemList as _CoreItemList
    from xnano_core import LineGauge as _CoreLineGauge
    from xnano_core import ListItem as _CoreListItem
    from xnano_core import Paragraph as _CoreParagraph
    from xnano_core import Scrollbar as _CoreScrollbar
    from xnano_core import Sparkline as _CoreSparkline
    from xnano_core import SparklineBar as _CoreSparklineBar
    from xnano_core import Table as _CoreTable
    from xnano_core import TableCell as _CoreTableCell
    from xnano_core import TableRow as _CoreTableRow
    from xnano_core import Tabs as _CoreTabs
    from xnano_core import Widget as _CoreWidget

    Bar = _CoreBar
    """
    One labelled value in a [`BarChart`][xnano.widgets.BarChart].

    Build bars when each value needs its own label or style.

    ```python
    import xnano
    from xnano.widgets import Bar, BarChart

    chart = BarChart([Bar(3, 'a'), Bar(5, 'b')], bar_width=3, width=8, height=4)
    with xnano.new(width=8, height=4) as canvas:
        canvas.screen.write(chart)
        assert 'a' in canvas.screen.render().splitlines()[-1]
    ```
    """

    BarChart = _CoreBarChart
    """
    Bars, or groups of bars, drawn against a common scale.

    Reach for it to compare a handful of values side by side.

    ```python
    import xnano
    from xnano.widgets import Bar, BarChart

    chart = BarChart([Bar(3, 'a'), Bar(5, 'b')], bar_width=3, width=8, height=4)
    chart.maximum = 6
    with xnano.new(width=8, height=4) as canvas:
        canvas.screen.write(chart)
        assert chart.maximum == 6
        assert canvas.screen.render().strip()
    ```
    """

    BarGroup = _CoreBarGroup
    """
    A labelled group of [`Bar`][xnano.widgets.Bar] values drawn together in a
    [`BarChart`][xnano.widgets.BarChart].

    Use it to put related bars under one label.

    ```python
    import xnano
    from xnano.widgets import Bar, BarChart, BarGroup

    group = BarGroup([Bar(3, 'a'), Bar(2, 'b')], 'Q1')
    with xnano.new(width=12, height=5) as canvas:
        canvas.screen.write(BarChart([group], bar_width=3, width=12, height=5))
        assert 'Q1' in canvas.screen.render()
    ```
    """

    Block = _CoreBlock
    """
    A border with titles and padding that frames other content.

    Pass it as the ``block`` of a widget to frame it, or write it on its own for a plain
    box.

    ```python
    import xnano
    from xnano.widgets import Block

    with xnano.new(width=12, height=3) as canvas:
        canvas.screen.write(Block('Status', width=12, height=3))
        assert 'Status' in canvas.screen.render()
    ```
    """

    Calendar = _CoreCalendar
    """
    A monthly calendar whose days can be marked with styles.

    Use it to show a month, or to highlight the days that hold events.

    ```python
    import xnano
    from xnano.styles import Style
    from xnano.widgets import Calendar

    calendar = Calendar(2026, 10, month_header_style=Style('yellow', bold=True), width=22, height=8)
    with xnano.new(width=22, height=8) as canvas:
        canvas.screen.write(calendar)
        assert 'October' in canvas.screen.render()
    ```
    """

    Chart = _CoreChart
    """
    Lines or points plotted against two axes.

    Reach for it to plot series of numbers; use a [`Figure`][xnano.widgets.Figure] to draw
    free-form shapes instead.

    ```python
    import xnano
    from xnano.widgets import Chart, ChartAxis, ChartDataset

    series = ChartDataset(name='load', data=[(0, 0), (1, 2), (2, 1)], graph_type='line')
    chart = Chart(
        [series],
        x_axis=ChartAxis(bounds=(0, 2)),
        y_axis=ChartAxis(bounds=(0, 2)),
        width=20,
        height=8,
    )
    with xnano.new(width=20, height=8) as canvas:
        canvas.screen.write(chart)
        assert canvas.screen.render().strip()
    ```
    """

    ChartAxis = _CoreChartAxis
    """
    One axis of a [`Chart`][xnano.widgets.Chart]: its bounds, labels and title.

    Pass two of them as ``x_axis`` and ``y_axis`` to set the range a chart shows.

    ```python
    import xnano
    from xnano.widgets import Chart, ChartAxis, ChartDataset

    axis = ChartAxis(title='time', bounds=(0, 10), labels=['0', '10'])
    chart = Chart([ChartDataset(data=[(0, 0), (10, 5)])], x_axis=axis, width=24, height=8)
    with xnano.new(width=24, height=8) as canvas:
        canvas.screen.write(chart)
        assert 'time' in canvas.screen.render()
    ```
    """

    ChartDataset = _CoreChartDataset
    """
    A series of ``(x, y)`` points that a [`Chart`][xnano.widgets.Chart] draws, with a
    name, a marker and a style.

    Give a chart one dataset for every series it plots.

    ```python
    import xnano
    from xnano.widgets import Chart, ChartDataset

    series = ChartDataset(name='load', data=[(0, 0), (1, 1)], graph_type='line')
    series.data = [(0, 1), (1, 0)]
    with xnano.new(width=20, height=8) as canvas:
        canvas.screen.write(Chart([series], width=20, height=8))
        assert series.data[0] == (0.0, 1.0)
        assert canvas.screen.render().strip()
    ```
    """

    Figure = _CoreCanvas
    """
    A coordinate plane that shapes, points and labels are drawn on; it is not a
    [`Canvas`][xnano.canvas.Canvas].

    Reach for it to draw lines, circles, maps and labels at coordinates of your own; its
    shapes are the ``FigureXxx`` classes of this module. They are the classes that
    ``xnano_core`` calls ``Canvas``, ``CanvasCircle``, ``CanvasLine`` and so on, so their
    reprs and type names read that way.

    Maps to [`xnano_core.Canvas`][xnano_core.Canvas].

    ```python
    import xnano
    from xnano.widgets import Figure, FigureCircle

    figure = Figure(x_bounds=(-10, 10), y_bounds=(-10, 10), marker='braille')
    figure.extend_shapes([FigureCircle(0, 0, 5, 'yellow')])
    with xnano.new(figure, width=20, height=10) as canvas:
        assert canvas.screen.render().strip()
    ```
    """

    FigureCircle = _CoreCanvasCircle
    """
    A circle outline on a [`Figure`][xnano.widgets.Figure].

    Add it to a figure with its center and radius in the figure's coordinates.

    Maps to [`xnano_core.CanvasCircle`][xnano_core.CanvasCircle].

    ```python
    import xnano
    from xnano.widgets import Figure, FigureCircle

    circle = FigureCircle(5, 5, 3, 'blue')
    figure = Figure((0, 10), (0, 10), marker='block', shapes=[circle], width=20, height=10)
    with xnano.new(width=20, height=10) as canvas:
        canvas.screen.write(figure)
        assert '█' in canvas.screen.render()
    ```
    """

    FigureLabel = _CoreCanvasLabel
    """
    Text printed at a position of a [`Figure`][xnano.widgets.Figure], always on top of its
    shapes.

    Use it to name a point or a shape.

    Maps to [`xnano_core.CanvasLabel`][xnano_core.CanvasLabel].

    ```python
    import xnano
    from xnano.widgets import Figure, FigureLabel

    label = FigureLabel(1, 5, 'hello')
    figure = Figure((0, 10), (0, 10), shapes=[label], width=10, height=5)
    with xnano.new(width=10, height=5) as canvas:
        canvas.screen.write(figure)
        assert 'hello' in canvas.screen.render()
    ```
    """

    FigureLine = _CoreCanvasLine
    """
    A straight line between two points of a [`Figure`][xnano.widgets.Figure], optionally
    filled down to a baseline.

    Use it for segments, axes and outlines.

    Maps to [`xnano_core.CanvasLine`][xnano_core.CanvasLine].

    ```python
    import xnano
    from xnano.widgets import Figure, FigureLine

    line = FigureLine(0, 0, 10, 10, 'green')
    figure = Figure((0, 10), (0, 10), marker='block', shapes=[line], width=10, height=5)
    with xnano.new(width=10, height=5) as canvas:
        canvas.screen.write(figure)
        assert '█' in canvas.screen.render()
    ```
    """

    FigureMap = _CoreCanvasMap
    """
    The map of the world on a [`Figure`][xnano.widgets.Figure], in longitude and latitude.

    Give the figure the bounds ``(-180, 180)`` and ``(-90, 90)`` so the map fills it.

    Maps to [`xnano_core.CanvasMap`][xnano_core.CanvasMap].

    ```python
    import xnano
    from xnano.widgets import Figure, FigureMap

    figure = Figure((-180, 180), (-90, 90), shapes=[FigureMap('low', 'white')], width=40, height=12)
    with xnano.new(width=40, height=12) as canvas:
        canvas.screen.write(figure)
        assert canvas.screen.render().strip()
    ```
    """

    FigurePoints = _CoreCanvasPoints
    """
    A set of single points on a [`Figure`][xnano.widgets.Figure].

    Use it for scatter plots and markers.

    Maps to [`xnano_core.CanvasPoints`][xnano_core.CanvasPoints].

    ```python
    import xnano
    from xnano.widgets import Figure, FigurePoints

    points = FigurePoints([(1, 1), (5, 5)], 'yellow')
    figure = Figure((0, 10), (0, 10), marker='block', shapes=[points], width=10, height=5)
    with xnano.new(width=10, height=5) as canvas:
        canvas.screen.write(figure)
        assert len(points) == 2
        assert '█' in canvas.screen.render()
    ```
    """

    FigureRectangle = _CoreCanvasRectangle
    """
    An axis-aligned rectangle outline on a [`Figure`][xnano.widgets.Figure].

    Add it to a figure with its lower-left corner and its size in the figure's
    coordinates.

    Maps to [`xnano_core.CanvasRectangle`][xnano_core.CanvasRectangle].

    ```python
    import xnano
    from xnano.widgets import Figure, FigureRectangle

    frame = FigureRectangle(0, 0, 10, 10, 'red')
    figure = Figure((0, 10), (0, 10), marker='block', shapes=[frame], width=10, height=5)
    with xnano.new(width=10, height=5) as canvas:
        canvas.screen.write(figure)
        assert '█' in canvas.screen.render()
    ```
    """

    Gauge = _CoreGauge
    """
    A bar filled to a ratio, with an optional label.

    Reach for it to show progress; the ratio can be an expression that follows a value.

    ```python
    import xnano
    from xnano.widgets import Gauge

    gauge = Gauge(0.5, label='half', width=12, height=1)
    with xnano.new(width=12, height=1) as canvas:
        canvas.screen.write(gauge)
        gauge.ratio = 0.75
        assert 'half' in canvas.screen.render()
    ```
    """

    ItemList = _CoreItemList
    """
    A list of items, one of which can be selected.

    Reach for it for menus and pickers; move the selection with ``select_next`` and its
    relatives.

    ```python
    import xnano
    from xnano.widgets import ItemList

    items = ItemList(['one', 'two', 'three'], selected=1, highlight_symbol='> ', width=12, height=3)
    with xnano.new(width=12, height=3) as canvas:
        canvas.screen.write(items)
        assert '> two' in canvas.screen.render()
    ```
    """

    LineGauge = _CoreLineGauge
    """
    A progress indicator drawn with a thin line.

    Use it instead of a [`Gauge`][xnano.widgets.Gauge] when the indicator should take one
    row and little weight.

    ```python
    import xnano
    from xnano.widgets import LineGauge

    gauge = LineGauge(0.5, label='half', width=16, height=1)
    with xnano.new(width=16, height=1) as canvas:
        canvas.screen.write(gauge)
        assert 'half' in canvas.screen.render()
    ```
    """

    ListItem = _CoreListItem
    """
    One entry of an [`ItemList`][xnano.widgets.ItemList], with its own style.

    Use it when an item needs a look of its own; a plain string is enough otherwise.

    ```python
    import xnano
    from xnano.styles import Style
    from xnano.widgets import ItemList, ListItem

    items = ItemList([ListItem('urgent', style=Style('red')), 'later'], width=10, height=2)
    with xnano.new(width=10, height=2) as canvas:
        canvas.screen.write(items)
        assert canvas.screen.render().splitlines() == ['urgent', 'later']
    ```
    """

    Paragraph = _CoreParagraph
    """
    Styled text that wraps, aligns and scrolls.

    Reach for it when text has to fit a width or sit inside a
    [`Block`][xnano.widgets.Block].

    ```python
    import xnano
    from xnano.widgets import Paragraph

    paragraph = Paragraph('hello brave new world', should_wrap=True, width=10, height=3)
    with xnano.new(width=10, height=3) as canvas:
        canvas.screen.write(paragraph)
        assert canvas.screen.render().splitlines() == ['hello', 'brave new', 'world']
    ```
    """

    Scrollbar = _CoreScrollbar
    """
    A bar that shows where the visible part sits within longer content.

    Draw one beside a list or a paragraph and move it with ``next`` and ``previous``.

    ```python
    import xnano
    from xnano.widgets import Scrollbar

    scrollbar = Scrollbar(10, 0, viewport_content_length=3, width=1, height=5)
    with xnano.new(width=1, height=5) as canvas:
        canvas.screen.write(scrollbar)
        scrollbar.next()
        assert scrollbar.content_position == 1
        assert canvas.screen.render().strip()
    ```
    """

    Sparkline = _CoreSparkline
    """
    A compact history of numbers drawn as small bars.

    Reach for it to show a trend in a row or two; ``append`` adds a sample.

    ```python
    import xnano
    from xnano.widgets import Sparkline

    sparkline = Sparkline([1, 3, 2, 5], width=5, height=1)
    with xnano.new(width=5, height=1) as canvas:
        canvas.screen.write(sparkline)
        sparkline.append(4)
        assert len(sparkline.values) == 5
        assert canvas.screen.render().strip()
    ```
    """

    SparklineBar = _CoreSparklineBar
    """
    One sample of a [`Sparkline`][xnano.widgets.Sparkline] with a style of its own.

    Use it to color the samples that matter.

    ```python
    import xnano
    from xnano.styles import Style
    from xnano.widgets import Sparkline, SparklineBar

    sparkline = Sparkline([1, SparklineBar(5, Style('red')), 2], width=3, height=1)
    with xnano.new(width=3, height=1) as canvas:
        canvas.screen.write(sparkline)
        assert canvas.screen.render().strip()
    ```
    """

    Table = _CoreTable
    """
    Rows and columns of text with an optional header and a selection.

    Reach for it for tabular data; a column width is a number of cells or a
    [`SizeRule`][xnano.layout.SizeRule].

    ```python
    import xnano
    from xnano.widgets import Table

    table = Table(
        [['ada', '36'], ['alan', '41']],
        header=['name', 'age'],
        widths=[6, 4],
        width=12,
        height=3,
    )
    with xnano.new(width=12, height=3) as canvas:
        canvas.screen.write(table)
        assert canvas.screen.render().splitlines()[0].split() == ['name', 'age']
    ```
    """

    TableCell = _CoreTableCell
    """
    One cell of a [`TableRow`][xnano.widgets.TableRow], with its own style and a column
    span.

    Use it when a cell needs a look of its own or spans several columns; a plain string is
    enough otherwise.

    ```python
    import xnano
    from xnano.styles import Style
    from xnano.widgets import Table, TableCell, TableRow

    row = TableRow([TableCell('total', style=Style(bold=True)), '77'])
    with xnano.new(width=12, height=1) as canvas:
        canvas.screen.write(Table([row], widths=[6, 4], width=12, height=1))
        assert canvas.screen.render().split() == ['total', '77']
    ```
    """

    TableRow = _CoreTableRow
    """
    One row of a [`Table`][xnano.widgets.Table], with a height and margins.

    Use it when a row is taller than one line or needs a style of its own.

    ```python
    import xnano
    from xnano.widgets import Table, TableRow

    row = TableRow(['ada', '36'], height=2)
    with xnano.new(width=12, height=2) as canvas:
        canvas.screen.write(Table([row], widths=[6, 4], width=12, height=2))
        assert canvas.screen.render().split() == ['ada', '36']
    ```
    """

    Tabs = _CoreTabs
    """
    A row of titles, one of which is selected.

    Reach for it to switch between views; move the selection with ``select_next`` and
    ``select_previous``.

    ```python
    import xnano
    from xnano.widgets import Tabs

    tabs = Tabs(['one', 'two'], selected=0, width=20, height=1)
    with xnano.new(width=20, height=1) as canvas:
        canvas.screen.write(tabs)
        tabs.select_next()
        assert tabs.selected == 1
        assert 'two' in canvas.screen.render()
    ```
    """

    Widget = _CoreWidget
    """
    The base class of every widget: a buffer painted from settings that can be
    expressions.

    Use it in ``isinstance`` checks and annotations for code that accepts any widget.

    ```python
    import xnano
    from xnano.widgets import Gauge, Widget

    gauge = Gauge(0.5, label='half', width=12, height=1)
    assert isinstance(gauge, Widget)
    with xnano.new(width=12, height=1) as canvas:
        canvas.screen.write(gauge)
        assert 'half' in canvas.screen.render()
    ```
    """

_CORE_NAMES: Final[dict[str, str]] = {
    'Bar': 'Bar',
    'BarChart': 'BarChart',
    'BarGroup': 'BarGroup',
    'Block': 'Block',
    'Calendar': 'Calendar',
    'Chart': 'Chart',
    'ChartAxis': 'ChartAxis',
    'ChartDataset': 'ChartDataset',
    'Figure': 'Canvas',
    'FigureCircle': 'CanvasCircle',
    'FigureLabel': 'CanvasLabel',
    'FigureLine': 'CanvasLine',
    'FigureMap': 'CanvasMap',
    'FigurePoints': 'CanvasPoints',
    'FigureRectangle': 'CanvasRectangle',
    'Gauge': 'Gauge',
    'ItemList': 'ItemList',
    'LineGauge': 'LineGauge',
    'ListItem': 'ListItem',
    'Paragraph': 'Paragraph',
    'Scrollbar': 'Scrollbar',
    'Sparkline': 'Sparkline',
    'SparklineBar': 'SparklineBar',
    'Table': 'Table',
    'TableCell': 'TableCell',
    'TableRow': 'TableRow',
    'Tabs': 'Tabs',
    'Widget': 'Widget',
}
"""The name each widgets object has in ``xnano_core``, by the name it has here."""

__all__ = [
    'Bar',
    'BarChart',
    'BarGroup',
    'Block',
    'Calendar',
    'Chart',
    'ChartAxis',
    'ChartDataset',
    'Figure',
    'FigureCircle',
    'FigureLabel',
    'FigureLine',
    'FigureMap',
    'FigurePoints',
    'FigureRectangle',
    'Gauge',
    'ItemList',
    'LineGauge',
    'ListItem',
    'Paragraph',
    'Scrollbar',
    'Sparkline',
    'SparklineBar',
    'Table',
    'TableCell',
    'TableRow',
    'Tabs',
    'Widget',
]


def __getattr__(name: str) -> object:
    """Import an object from ``xnano_core`` the first time it is read, then keep it."""
    core_name = _CORE_NAMES.get(name)
    if core_name is None:
        raise AttributeError(
            f'xnano.widgets has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    import xnano_core

    value = getattr(xnano_core, core_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
