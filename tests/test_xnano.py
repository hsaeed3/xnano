import pytest
import xnano._core as core

from xnano.color import Color
from xnano import hooks
from xnano.layout import (
    Constraint,
    Layout,
    Margin,
    Offset,
    Position,
    Rect,
    Rectangle,
    Size,
)
from xnano.scroll import (
    Scrollbar,
    ScrollbarState,
)
from xnano.style import (
    Borders,
    Padding,
    Style,
    Wrap,
)
from xnano.table import (
    Cell,
    Row,
    Table,
    TableState,
)
from xnano.text import (
    Line,
    Span,
    Text,
)
from xnano.widgets import (
    Block,
    Clear,
    Gauge,
    ListItem,
    ListState,
    ListView,
    Paragraph,
    Tabs,
)


def test_layout_classes():
    r1 = Rectangle(x=2, y=3, width=40, height=20)
    assert r1.x == 2
    assert r1.y == 3
    assert r1.width == 40
    assert r1.height == 20
    assert r1.area() == 800

    # Rect is an alias
    assert Rect is Rectangle

    # Margin, Offset, Size, Position
    m = Margin(horizontal=4, vertical=2)
    assert m.horizontal == 4
    o = Offset(x=-1, y=2)
    assert o.x == -1
    s = Size(width=10, height=5)
    assert s.width == 10
    pos = Position(x=0, y=0)
    assert pos.x == 0

    # Layout with constructor parameters (No builders!)
    layout = Layout(
        direction="horizontal",
        constraints=[Constraint.percentage(30), Constraint.fill(1)],
        margin=m,
        spacing=1,
    )
    splits = layout.split(r1)
    assert len(splits) == 2


def test_style_and_colors():
    # Hex, color names, Color object support
    c1 = Color.from_hex("#ff00ff")
    c2 = Color.from_name("red")

    style = Style(
        foreground="red", background="#0000ff", modifiers=["bold", "italic"]
    )
    assert style is not None

    p = Style.default().patch(style)
    assert p is not None

    # Check that they raise AttributeError on mutation
    with pytest.raises(AttributeError):
        style.foreground = "blue"


def test_text_primitives():
    s = Span("Hello", foreground="green", modifiers="bold")
    assert s.text == "Hello"

    l = Line([s, Span(" World")])
    assert l.text == "Hello World"

    t = Text([l, Line("New line")])
    assert len(t.lines()) == 2


def test_widgets_constructor_only():
    # No builders test
    block = Block(
        title="Title",
        borders="all",
        border_type="rounded",
        border_style=Style(foreground="cyan"),
        padding=1,
    )
    assert block is not None

    para = Paragraph(
        "Wrapped text",
        block=block,
        style=Style(foreground="white"),
        wrap=True,
        alignment="center",
    )
    assert para is not None

    item = ListItem("List item", style=Style(foreground="yellow"))
    list_view = ListView(
        [item, "Plain string"],
        block=block,
        highlight_style=Style(modifiers="bold"),
        highlight_symbol="> ",
    )
    assert list_view.len() == 2

    state = ListState(selected=1)
    assert state.selected == 1


def test_table_scroll_and_charts():
    cell = Cell("Value", style=Style(foreground="red"))
    row = Row([cell, "String cell"], height=2)
    table = Table(
        [row],
        [Constraint.length(10), Constraint.fill(1)],
        header=Row(["A", "B"]),
        highlight_symbol=">",
    )
    assert table is not None

    state = TableState(selected=0, selected_column=1)
    assert state.selected == 0
    assert state.selected_column == 1

    scrollbar = Scrollbar("vertical_right", style=Style(foreground="gray"))
    assert scrollbar is not None


def test_event_handler_matching_and_decorators():
    from xnano.keyboard import _event_matches_binding, _parse_binding

    # Test text parsing
    ctrl, shift, alt, code, char, f_num = _parse_binding("ctrl+alt+delete")
    assert ctrl is True
    assert shift is False
    assert alt is True
    assert code == core.KeyCode.Delete

    ctrl, shift, alt, code, char, f_num = _parse_binding("f11")
    assert code == core.KeyCode.F
    assert f_num == 11

    # Decorator checks
    from xnano.component import Component
    from xnano.context import Context
    import dataclasses

    @dataclasses.dataclass
    class DummyState:
        pass

    class DummyComponent(Component[DummyState]):
        @hooks.on_keyboard("q", "ctrl+c")
        def quit_handler(self, ctx: Context[DummyState]):
            pass

        def render(self, area):
            return None

    component = DummyComponent(state=DummyState())
    assert len(component._keyboard_handlers) == 1
    assert "q" in component._keyboard_handlers[0][0]
    assert "ctrl+c" in component._keyboard_handlers[0][0]
