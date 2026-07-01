import pytest
import xnano._core as core


def test_core_layout_primitives():
    # Rect
    r = core.Rect(0, 0, 80, 24)
    assert r.x == 0
    assert r.y == 0
    assert r.width == 80
    assert r.height == 24
    assert r.area() == 1920
    assert not r.is_empty()

    # Margin
    m = core.Margin(2, 1)
    assert m.horizontal == 2
    assert m.vertical == 1

    # Offset
    o = core.Offset(5, -5)
    assert o.x == 5
    assert o.y == -5

    # Size
    s = core.Size(100, 50)
    assert s.width == 100
    assert s.height == 50

    # Position
    p = core.Position(10, 20)
    assert p.x == 10
    assert p.y == 20


def test_core_constraints_and_layout():
    c1 = core.Constraint.length(10)
    c2 = core.Constraint.percentage(50)
    c3 = core.Constraint.fill(1)

    l = core.Layout.vertical([c1, c2, c3])
    r = core.Rect(0, 0, 100, 100)
    splits = l.split(r)
    assert len(splits) == 3
    assert splits[0].height == 10
    # percentage of 100 is 50
    assert splits[1].height == 50


def test_core_styling():
    # Color
    c = core.Color.rgb(255, 0, 0)
    assert repr(c).startswith("Rgb") or "255" in repr(c)

    # Modifier
    m1 = core.Modifier.BOLD
    m2 = core.Modifier.ITALIC
    m3 = m1 | m2
    assert "BOLD" in repr(m3)
    assert "ITALIC" in repr(m3)

    # Style
    style = core.Style.default().fg(c).add_modifier(m3)
    assert repr(style) != ""


def test_core_text():
    span = core.Span.styled("Hello", core.Style.default())
    assert span.text == "Hello"
    assert span.width() == 5

    line = core.Line.from_spans([span])
    assert line.width() == 5

    text = core.Text.from_lines([line])
    assert text.width() == 5
    assert text.height() == 1


def test_core_widgets():
    block = core.Block.bordered().title(core.Line.raw("Title"))
    assert block is not None

    p = core.Paragraph.new(core.Text.raw("Paragraph text"))
    assert p is not None

    item1 = core.ListItem.new(core.Line.raw("Item 1"))
    list_widget = core.RatList.new([item1])
    assert list_widget.len() == 1

    state = core.ListState()
    state.select(0)
    assert state.selected == 0

    gauge = core.Gauge.new().percent(50)
    assert gauge is not None


def test_core_widgets_extra():
    cell = core.Cell.new(core.Line.raw("Cell"))
    row = core.Row.new([cell])
    table = core.RatTable.new([row], [core.Constraint.length(10)])
    assert table is not None

    state = core.TableState()
    state.select(5)
    assert state.selected == 5

    scrollbar = core.Scrollbar.new(core.ScrollbarOrientation.VerticalRight)
    assert scrollbar is not None

    scrollbar_state = core.ScrollbarState(100)
    assert scrollbar_state is not None
