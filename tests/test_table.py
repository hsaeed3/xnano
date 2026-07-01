import pytest
from xnano.table import Cell, Row, Table, TableState
from xnano.style import Style
from xnano.layout import Constraint
from xnano.widgets import Block
from xnano import _core

def test_cell():
    style = Style(foreground="green")
    cell = Cell("A", style=style)
    assert cell._to_core() is not None
    assert repr(cell) == "Cell()"
    
    cell2 = Cell._from_core(cell._to_core())
    assert repr(cell2) == "Cell()"
    
    with pytest.raises(AttributeError):
        cell.content = "B"
    with pytest.raises(AttributeError):
        del cell._inner


def test_row():
    style = Style(foreground="blue")
    cell1 = Cell("A")
    row = Row(
        [cell1, "B", "C"],
        style=style,
        height=3,
        top_margin=1,
        bottom_margin=1
    )
    
    assert row._to_core() is not None
    assert repr(row) is not None
    
    row2 = Row._from_core(row._to_core())
    assert repr(row2) == repr(row)
    
    with pytest.raises(AttributeError):
        row.height = 4
    with pytest.raises(AttributeError):
        del row._inner


def test_table():
    style = Style(foreground="yellow")
    block = Block(title="Table Block")
    row = Row(["Val1", "Val2"])
    
    table = Table(
        [row],
        [Constraint.percentage(50), Constraint.percentage(50)],
        header=Row(["Col1", "Col2"]),
        footer=Row(["Foot1", "Foot2"]),
        block=block,
        style=style,
        row_highlight_style=style,
        column_highlight_style=style,
        cell_highlight_style=style,
        highlight_symbol=">",
        highlight_spacing="always",
        column_spacing=2
    )
    
    assert table._to_core() is not None
    assert repr(table) is not None
    
    table2 = Table._from_core(table._to_core())
    assert repr(table2) == repr(table)
    
    with pytest.raises(AttributeError):
        table.rows = []
    with pytest.raises(AttributeError):
        del table._inner


def test_table_state():
    state = TableState(selected=0, selected_column=0)
    assert state._to_core() is not None
    assert repr(state) is not None
    
    assert state.selected == 0
    assert state.selected_column == 0
    
    # State selection & traversal
    state.select(1)
    assert state.selected == 1
    state.select_column(1)
    assert state.selected_column == 1
    
    state.select_cell((2, 2))
    assert state.selected_cell() == (2, 2)
    
    state.select_next()
    state.select_previous()
    state.select_next_column()
    state.select_previous_column()
    
    state.select_first()
    state.select_last()
    state.select_first_column()
    state.select_last_column()
    
    # Scroll methods
    state.scroll_down_by(5)
    state.scroll_up_by(5)
    state.scroll_right_by(2)
    state.scroll_left_by(2)
    
    # Offset property
    assert isinstance(state.offset, int)
    
    # Construct from core
    state2 = TableState._from_core(state._to_core())
    assert repr(state2) == repr(state)
