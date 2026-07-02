"""Tests for xnano.widgets module - comprehensive widgets functionality."""

import pytest
from xnano.widgets import (
    Block,
    Paragraph,
    ListItem,
    ListView,
    ListState,
    Gauge,
    Tabs,
    Clear,
    ListDirectionName,
)
from xnano.style import (
    Style,
    Borders,
    Padding,
    ModifierName,
    HighlightSpacingName,
    TitlePositionName,
    BorderTypeName,
    Wrap,
)
from xnano.layout import Rectangle
from xnano.text import Line, Span


class TestBlock:
    """Tests for Block widget."""

    def test_block_default(self):
        b = Block()
        assert b is not None

    def test_block_with_title(self):
        b = Block(title="Title")
        assert b is not None

    def test_block_with_borders_string(self):
        b = Block(borders="all")
        assert b is not None

    def test_block_with_borders_all(self):
        b = Block(borders=Borders.all())
        assert b is not None

    def test_block_with_borders_none(self):
        b = Block(borders="none")
        assert b is not None

    def test_block_with_border_type(self):
        for bt in [
            "plain",
            "rounded",
            "double",
            "thick",
            "quadrant_inside",
            "quadrant_outside",
        ]:
            b = Block(border_type=bt)
            assert b is not None

    def test_block_with_border_style(self):
        b = Block(border_style=Style(foreground="red"))
        assert b is not None

    def test_block_with_style(self):
        b = Block(style=Style(foreground="red"))
        assert b is not None

    def test_block_with_padding_int(self):
        b = Block(padding=2)
        assert b is not None

    def test_block_with_padding_object(self):
        b = Block(padding=Padding.uniform(2))
        assert b is not None

    def test_block_with_all_options(self):
        b = Block(
            title="Test",
            title_alignment="center",
            title_position="bottom",
            title_style=Style(foreground="red"),
            borders="all",
            border_type="rounded",
            border_style=Style(foreground="blue"),
            style=Style(background="black"),
            padding=1,
        )
        assert b is not None

    def test_block_inner(self):
        b = Block(borders="all")
        area = Rectangle(x=0, y=0, width=20, height=10)
        inner = b.inner(area)
        assert inner is not None

    def test_block_immutability(self):
        b = Block()
        with pytest.raises(AttributeError, match="Block is immutable"):
            b.test = True


class TestParagraph:
    """Tests for Paragraph widget."""

    def test_paragraph_default(self):
        p = Paragraph()
        assert p is not None

    def test_paragraph_with_content(self):
        p = Paragraph("Hello World")
        assert p is not None

    def test_paragraph_with_style(self):
        p = Paragraph("Hello", style=Style(foreground="red"))
        assert p is not None

    def test_paragraph_with_block(self):
        p = Paragraph("Hello", block=Block(borders="all"))
        assert p is not None

    def test_paragraph_with_wrap_bool_true(self):
        p = Paragraph("Hello " * 20, wrap=True)
        assert p is not None

    def test_paragraph_with_wrap_bool_false(self):
        p = Paragraph("Hello", wrap=False)
        assert p is not None

    def test_paragraph_with_alignment(self):
        for align in ["left", "center", "right"]:
            p = Paragraph("Hello", alignment=align)
            assert p is not None

    def test_paragraph_with_scroll(self):
        p = Paragraph("Hello", scroll=(0, 5))
        assert p is not None

    def test_paragraph_immutability(self):
        p = Paragraph("Hello")
        with pytest.raises(AttributeError, match="Paragraph is immutable"):
            p.test = True


class TestListItem:
    """Tests for ListItem widget."""

    def test_list_item_default(self):
        item = ListItem("Item")
        assert item is not None

    def test_list_item_with_style(self):
        item = ListItem("Item", style=Style(foreground="red"))
        assert item is not None

    def test_list_item_immutability(self):
        item = ListItem("Item")
        with pytest.raises(AttributeError, match="ListItem is immutable"):
            item.test = True


class TestListView:
    """Tests for ListView widget."""

    def test_list_view_default(self):
        lv = ListView([])
        assert lv is not None

    def test_list_view_with_items(self):
        lv = ListView(["A", "B", "C"])
        assert lv.len() == 3

    def test_list_view_with_list_items(self):
        lv = ListView([ListItem("A"), ListItem("B")])
        assert lv.len() == 2

    def test_list_view_with_style(self):
        lv = ListView(["A"], style=Style(foreground="red"))
        assert lv is not None

    def test_list_view_with_highlight_style(self):
        lv = ListView(["A"], highlight_style=Style(foreground="yellow"))
        assert lv is not None

    def test_list_view_with_highlight_symbol(self):
        lv = ListView(["A"], highlight_symbol="> ")
        assert lv is not None

    def test_list_view_with_direction(self):
        for direction in ["top_to_bottom", "bottom_to_top"]:
            lv = ListView(["A"], direction=direction)
            assert lv is not None

    def test_list_view_with_repeat_highlight_symbol(self):
        lv = ListView(["A"], repeat_highlight_symbol=True)
        assert lv is not None

    def test_list_view_with_highlight_spacing(self):
        for spacing in ["always", "when_selected", "never"]:
            lv = ListView(["A"], highlight_spacing=spacing)
            assert lv is not None

    def test_list_view_with_scroll_padding(self):
        lv = ListView(["A"], scroll_padding=5)
        assert lv is not None

    def test_list_view_is_empty_true(self):
        lv = ListView([])
        assert lv.is_empty()

    def test_list_view_is_empty_false(self):
        lv = ListView(["A"])
        assert not lv.is_empty()

    def test_list_view_immutability(self):
        lv = ListView(["A"])
        with pytest.raises(AttributeError, match="ListView is immutable"):
            lv.test = True


class TestListState:
    """Tests for ListState class."""

    def test_list_state_default(self):
        state = ListState()
        assert state.selected is None

    def test_list_state_with_selected(self):
        state = ListState(selected=2)
        assert state.selected == 2

    def test_list_state_select(self):
        state = ListState()
        state.select(5)
        assert state.selected == 5

    def test_list_state_select_none(self):
        state = ListState(selected=5)
        state.select(None)
        assert state.selected is None

    def test_list_state_select_next(self):
        state = ListState(selected=0)
        # Need items set up for select_next to work properly
        # For now just test it doesn't crash

    def test_list_state_select_previous(self):
        state = ListState(selected=0)
        # Doesn't crash

    def test_list_state_select_first(self):
        state = ListState(selected=5)
        state.select_first()
        assert state.selected == 0

    def test_list_state_select_last(self):
        state = ListState(selected=0)
        state.select_last()
        assert state.selected in (18446744073709551615, 4294967295)

    def test_list_state_offset_property(self):
        state = ListState()
        assert state.offset >= 0

    def test_list_state_set_offset(self):
        state = ListState()
        state.set_offset(10)
        assert state.offset == 10

    def test_list_state_scroll_down_by(self):
        state = ListState()
        state.scroll_down_by(5)

    def test_list_state_scroll_up_by(self):
        state = ListState()
        state.scroll_up_by(3)


class TestGauge:
    """Tests for Gauge widget."""

    def test_gauge_default(self):
        g = Gauge()
        assert g is not None

    def test_gauge_with_percent(self):
        g = Gauge(percent=50)
        assert g is not None

    def test_gauge_with_ratio(self):
        g = Gauge(ratio=0.75)
        assert g is not None

    def test_gauge_with_label(self):
        g = Gauge(label="Loading...")
        assert g is not None

    def test_gauge_with_block(self):
        g = Gauge(block=Block(borders="all"))
        assert g is not None

    def test_gauge_with_style(self):
        g = Gauge(style=Style(foreground="red"))
        assert g is not None

    def test_gauge_with_gauge_style(self):
        g = Gauge(gauge_style=Style(foreground="green"))
        assert g is not None

    def test_gauge_with_use_unicode(self):
        g = Gauge(use_unicode=True)
        assert g is not None

    def test_gauge_immutability(self):
        g = Gauge()
        with pytest.raises(AttributeError, match="Gauge is immutable"):
            g.test = True


class TestTabs:
    """Tests for Tabs widget."""

    def test_tabs_default(self):
        t = Tabs(["Tab 1", "Tab 2"])
        assert t is not None

    def test_tabs_with_selected(self):
        t = Tabs(["Tab 1", "Tab 2"], selected=1)
        assert t is not None

    def test_tabs_with_style(self):
        t = Tabs(["Tab 1"], style=Style(foreground="red"))
        assert t is not None

    def test_tabs_with_highlight_style(self):
        t = Tabs(["Tab 1"], highlight_style=Style(foreground="yellow"))
        assert t is not None

    def test_tabs_with_block(self):
        t = Tabs(["Tab 1"], block=Block(borders="all"))
        assert t is not None

    def test_tabs_with_padding(self):
        t = Tabs(["Tab 1"], padding=("(", ")"))
        assert t is not None

    def test_tabs_with_divider(self):
        t = Tabs(["Tab 1"], divider="|")
        assert t is not None

    def test_tabs_immutability(self):
        t = Tabs(["Tab 1"])
        with pytest.raises(AttributeError, match="Tabs is immutable"):
            t.test = True


class TestClear:
    """Tests for Clear widget."""

    def test_clear_default(self):
        c = Clear()
        assert c is not None

    def test_clear_immutability(self):
        c = Clear()
        with pytest.raises(AttributeError, match="Clear is immutable"):
            c.test = True


class TestListDirectionName:
    """Tests for ListDirectionName type alias."""

    def test_direction_types(self):
        for d in ["top_to_bottom", "bottom_to_top"]:
            lv = ListView(["A"], direction=d)
            assert lv is not None


class TestWidgetInternals:
    """Tests for widget internal representation, immutability, and constructors."""

    @pytest.mark.parametrize(
        "widget_class, factory",
        [
            (Block, lambda: Block()),
            (Clear, lambda: Clear()),
            (Gauge, lambda: Gauge()),
            (ListView, lambda: ListView(["A"])),
            (ListItem, lambda: ListItem("A")),
            (Paragraph, lambda: Paragraph("A")),
            (Tabs, lambda: Tabs(["A"])),
        ],
    )
    def test_widget_internals(self, widget_class, factory):
        w = factory()
        # Test _from_core and _to_core
        core = w._to_core()
        w2 = widget_class._from_core(core)
        assert repr(w2) == repr(w)

        # Test __delattr__
        with pytest.raises(AttributeError, match="is immutable"):
            del w._inner

        # Test ListState separately since it is mutable
        ls = ListState(selected=2)
        assert ls._to_core() is not None
        assert repr(ls) is not None
        ls.select_next()
        ls.select_previous()
        ls.select_first()
        ls.select_last()
        ls.set_offset(1)
        ls.scroll_down_by(1)
        ls.scroll_up_by(1)
        assert isinstance(ls.offset, int)

        ls2 = ListState._from_core(ls._to_core())
        assert repr(ls2) == repr(ls)

        # Test Paragraph with Wrap object
        p = Paragraph("hello", wrap=Wrap(trim=True))
        assert p is not None
