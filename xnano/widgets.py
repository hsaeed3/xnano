"""
xnano.widgets

Widgets that draw themselves: text, tables, charts, gauges, canvases and lists.

A widget is a description of something to draw. Pass one to [`Terminal.write`][xnano.terminal.Terminal.write]
or draw it into a [`Buffer`][xnano.buffers.Buffer]; every number and text in it can be an
[`Expression`][xnano.expressions.Expression] that is evaluated again on each frame.
"""

from xnano_core import (
    Bar as Bar,
)
from xnano_core import (
    BarChart as BarChart,
)
from xnano_core import (
    BarGroup as BarGroup,
)
from xnano_core import (
    Block as Block,
)
from xnano_core import (
    Calendar as Calendar,
)
from xnano_core import (
    Canvas as Canvas,
)
from xnano_core import (
    CanvasCircle as CanvasCircle,
)
from xnano_core import (
    CanvasLabel as CanvasLabel,
)
from xnano_core import (
    CanvasLine as CanvasLine,
)
from xnano_core import (
    CanvasMap as CanvasMap,
)
from xnano_core import (
    CanvasPoints as CanvasPoints,
)
from xnano_core import (
    CanvasRectangle as CanvasRectangle,
)
from xnano_core import (
    Chart as Chart,
)
from xnano_core import (
    ChartAxis as ChartAxis,
)
from xnano_core import (
    ChartDataset as ChartDataset,
)
from xnano_core import (
    Gauge as Gauge,
)
from xnano_core import (
    ItemList as ItemList,
)
from xnano_core import (
    LineGauge as LineGauge,
)
from xnano_core import (
    ListItem as ListItem,
)
from xnano_core import (
    Paragraph as Paragraph,
)
from xnano_core import (
    Scrollbar as Scrollbar,
)
from xnano_core import (
    Sparkline as Sparkline,
)
from xnano_core import (
    SparklineBar as SparklineBar,
)
from xnano_core import (
    Table as Table,
)
from xnano_core import (
    TableCell as TableCell,
)
from xnano_core import (
    TableRow as TableRow,
)
from xnano_core import (
    Tabs as Tabs,
)
from xnano_core import (
    Widget as Widget,
)

__all__ = [
    'Bar',
    'BarChart',
    'BarGroup',
    'Block',
    'Calendar',
    'Canvas',
    'CanvasCircle',
    'CanvasLabel',
    'CanvasLine',
    'CanvasMap',
    'CanvasPoints',
    'CanvasRectangle',
    'Chart',
    'ChartAxis',
    'ChartDataset',
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
