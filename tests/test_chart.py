import pytest
from xnano.chart import Sparkline, LineGauge, Bar, BarGroup, BarChart
from xnano.style import Style
from xnano.widgets import Block
from xnano import _core

def test_sparkline():
    style = Style(foreground="red")
    block = Block(title="Sparkline Block")
    
    spark = Sparkline(
        [1, 2, 3, 4],
        block=block,
        style=style,
        max_value=10,
        absent_value_style=style,
        absent_value_symbol="x"
    )
    
    assert spark._to_core() is not None
    assert repr(spark) is not None
    
    # Test _from_core
    spark2 = Sparkline._from_core(spark._to_core())
    assert repr(spark2) == repr(spark)
    
    # Test immutability
    with pytest.raises(AttributeError):
        spark.data = [2, 3]
    with pytest.raises(AttributeError):
        del spark._inner


def test_line_gauge():
    style = Style(foreground="blue")
    block = Block(title="Gauge Block")
    
    lg = LineGauge(
        ratio=0.5,
        label="50%",
        block=block,
        style=style,
        filled_style=style,
        unfilled_style=style
    )
    
    assert lg._to_core() is not None
    assert repr(lg) is not None
    
    lg2 = LineGauge._from_core(lg._to_core())
    assert repr(lg2) == repr(lg)
    
    with pytest.raises(AttributeError):
        lg.ratio = 0.8
    with pytest.raises(AttributeError):
        del lg._inner


def test_bar():
    style = Style(foreground="green")
    bar = Bar(
        5,
        "Label",
        style=style,
        value_style=style,
        text_value="Five"
    )
    
    assert bar._to_core() is not None
    assert repr(bar) is not None
    
    bar2 = Bar._from_core(bar._to_core())
    assert repr(bar2) == repr(bar)
    
    with pytest.raises(AttributeError):
        bar.value = 10
    with pytest.raises(AttributeError):
        del bar._inner


def test_bar_group():
    bar1 = Bar(5, "A")
    bar2 = Bar(10, "B")
    group = BarGroup([bar1, bar2])
    
    assert group._to_core() is not None
    assert repr(group) == "BarGroup()"
    
    group2 = BarGroup._from_core(group._to_core())
    assert repr(group2) == "BarGroup()"
    
    with pytest.raises(AttributeError):
        group.bars = []
    with pytest.raises(AttributeError):
        del group._inner


def test_bar_chart():
    style = Style(foreground="yellow")
    block = Block(title="Chart Block")
    bar1 = Bar(5, "A")
    group = BarGroup([bar1])
    
    chart = BarChart(
        [group],
        block=block,
        style=style,
        bar_width=3,
        max_value=20,
        bar_gap=2,
        group_gap=4,
        bar_style=style,
        value_style=style,
        label_style=style,
        direction="horizontal"
    )
    
    assert chart._to_core() is not None
    assert repr(chart) is not None
    
    chart2 = BarChart._from_core(chart._to_core())
    assert repr(chart2) == repr(chart)
    
    with pytest.raises(AttributeError):
        chart.groups = []
    with pytest.raises(AttributeError):
        del chart._inner
