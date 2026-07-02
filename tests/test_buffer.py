"""Tests for xnano.buffer module - comprehensive buffer functionality."""

import pytest
import xnano._core as _core
from xnano.buffer import Buffer, render_widget, render_stateful_widget
from xnano.layout import Rectangle, Constraint, Layout
from xnano.widgets import Block, Paragraph, ListState
from xnano.style import Style


class TestBuffer:
    """Tests for Buffer class."""

    def test_buffer_empty(self):
        r = Rectangle(x=0, y=0, width=10, height=5)
        buf = Buffer.empty(r)
        assert buf is not None
        assert buf.area.width == 10
        assert buf.area.height == 5

    def test_buffer_invalid_instantiation(self):
        with pytest.raises(
            TypeError,
            match="Buffer instances must be created using factory methods",
        ):
            Buffer()

    def test_buffer_immutability(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        with pytest.raises(AttributeError, match="Buffer is immutable"):
            buf.x = 10
        with pytest.raises(AttributeError, match="Buffer is immutable"):
            buf._inner = _core.Buffer.empty(
                Rectangle(x=0, y=0, width=10, height=5)._to_core()
            )

    def test_buffer_cell_symbol(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        symbol = buf.cell_symbol(0, 0)
        assert isinstance(symbol, str)

    def test_buffer_cell_foreground(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        fg = buf.cell_foreground(0, 0)
        assert fg is not None

    def test_buffer_cell_background(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        bg = buf.cell_background(0, 0)
        assert bg is not None

    def test_buffer_cell_fg_alias(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        fg = buf.cell_fg(0, 0)
        assert fg is not None

    def test_buffer_cell_bg_alias(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        bg = buf.cell_bg(0, 0)
        assert bg is not None

    def test_buffer_cell_modifier(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        mod = buf.cell_modifier(0, 0)
        assert mod is not None

    def test_buffer_set_string(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        style = Style(foreground="red")
        buf.set_string(0, 0, "Hello", style)
        assert buf.cell_symbol(0, 0) == "H"
        assert buf.cell_symbol(1, 0) == "e"
        assert buf.cell_symbol(2, 0) == "l"
        assert buf.cell_symbol(3, 0) == "l"
        assert buf.cell_symbol(4, 0) == "o"

    def test_buffer_set_string_multi_char(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        style = Style(foreground="red")
        buf.set_string(0, 0, "Test", style)
        assert buf.cell_symbol(0, 0) == "T"
        assert buf.cell_symbol(1, 0) == "e"
        assert buf.cell_symbol(2, 0) == "s"
        assert buf.cell_symbol(3, 0) == "t"

    def test_buffer_lines(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        lines = buf.lines()
        assert isinstance(lines, list)
        assert len(lines) == 5

    def test_buffer_to_core(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        core_buf = buf._to_core()
        assert core_buf is not None

    def test_buffer_repr(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        assert repr(buf) is not None

    def test_buffer_delattr(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=10, height=5))
        with pytest.raises(AttributeError, match="Buffer is immutable"):
            del buf._inner

    def test_buffer_instance_render_widget(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=20, height=10))
        para = Paragraph("Test content")
        buf.render_widget(para, Rectangle(x=0, y=0, width=20, height=10))
        assert "Test" in buf.lines()[0]

    def test_buffer_instance_render_stateful_widget(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=20, height=10))
        from xnano.widgets import ListView, ListItem

        list_view = ListView([ListItem("A")])
        state = ListState()
        buf.render_stateful_widget(
            list_view, Rectangle(x=0, y=0, width=20, height=10), state
        )


class TestRenderFunctions:
    """Tests for render widget functions."""

    def test_render_widget_paragraph(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=20, height=10))
        para = Paragraph("Test content")
        render_widget(para, Rectangle(x=0, y=0, width=20, height=10), buf)
        lines = buf.lines()
        assert "Test" in lines[0]

    def test_render_widget_block(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=20, height=5))
        block = Block(borders="all")
        render_widget(block, Rectangle(x=0, y=0, width=20, height=5), buf)

    def test_render_stateful_widget_list(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=20, height=10))
        from xnano.widgets import ListView, ListItem

        list_view = ListView([ListItem("A"), ListItem("B"), ListItem("C")])
        state = ListState()
        state.select(1)
        render_stateful_widget(
            list_view, Rectangle(x=0, y=0, width=20, height=10), state, buf
        )

    def test_render_stateful_widget_table(self):
        buf = Buffer.empty(Rectangle(x=0, y=0, width=40, height=10))
        from xnano.table import Table, Row, Cell, TableState

        table = Table(
            [Row([Cell("A"), Cell("B")])],
            [Constraint.length(10), Constraint.length(10)],
        )
        state = TableState(selected=0)
        render_stateful_widget(
            table, Rectangle(x=0, y=0, width=40, height=10), state, buf
        )

    def test_buffer_tuple_shorthands(self):
        # 1. empty with 4-tuple
        buf = Buffer.empty((0, 0, 40, 20))
        assert buf.area.width == 40
        assert buf.area.height == 20

        # 2. render_widget with 4-tuple
        para = Paragraph("Hello")
        buf.render_widget(para, (0, 0, 20, 5))
        assert "Hello" in buf.lines()[0]

        # Test string rendering in buffer.render_widget
        buf.render_widget("World", (0, 0, 20, 5))

        # 3. render_stateful_widget with 4-tuple
        from xnano.widgets import ListView, ListItem

        list_view = ListView([ListItem("A")])
        state = ListState()
        buf.render_stateful_widget(list_view, (0, 0, 20, 5), state)

        # 4. render_widget function with 4-tuple and string
        render_widget("TestHelper", (0, 0, 20, 5), buf)

        # 5. render_stateful_widget function with 4-tuple
        render_stateful_widget(list_view, (0, 0, 20, 5), state, buf)

    def test_buffer_render_declarative(self):
        buf = Buffer.empty((0, 0, 40, 20))
        para = Paragraph("Item")
        from xnano.widgets import ListView, ListItem

        list_view = ListView([ListItem("A")])
        state = ListState()

        # Render list/sequence of items
        buf.render(
            [para, (para, (0, 5, 20, 5)), (list_view, (0, 10, 20, 5), state)]
        )
        assert "Item" in buf.lines()[0]
        assert "Item" in buf.lines()[5]

        # Render single widget
        buf2 = Buffer.empty((0, 0, 40, 20))
        buf2.render(para)
        assert "Item" in buf2.lines()[0]

        # Render single widget with explicit area
        buf3 = Buffer.empty((0, 0, 40, 20))
        buf3.render(para, (0, 2, 20, 5))
        assert "Item" in buf3.lines()[2]

        # Invalid tuple length
        with pytest.raises(ValueError, match="Invalid draw tuple"):
            buf.render([(para, (0, 0, 20, 5), state, "extra")])
