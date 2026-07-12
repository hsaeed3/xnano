"""Tests for xnano.components.table — declarative Table."""

from __future__ import annotations

import dataclasses

from helpers import render_component_to_text

from xnano._types import Area
from xnano.components.abstract import ComponentRenderContext
from xnano.components.schema import Column
from xnano.components.table import Table
from xnano.tui.nodes import TableNode


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=48, height=10))


_ROWS = [
    {"service": "api", "status": "ok", "latency": 12},
    {"service": "cache", "status": "degraded", "latency": 88},
]


# ---------------------------------------------------------------------------
# Data-driven column inference
# ---------------------------------------------------------------------------


def test_infers_columns_from_dict_keys() -> None:
    node = Table(data=_ROWS).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.header is not None
    headers = [
        c.content if hasattr(c, "content") else c for c in node.header.cells
    ]  # type: ignore[union-attr]
    assert headers == ["Service", "Status", "Latency"]


def test_infers_columns_from_dataclass_fields() -> None:
    @dataclasses.dataclass
    class Svc:
        name: str
        rps: int

    node = Table(data=[Svc("api", 10), Svc("cache", 5)]).get_terminal_node(
        _ctx()
    )
    assert isinstance(node, TableNode)
    assert len(node.rows) == 2


def test_infers_columns_from_object_attributes() -> None:
    class Obj:
        def __init__(self) -> None:
            self.a = 1
            self.b = 2

    node = Table(data=[Obj()]).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.header is not None


def test_body_rows_match_data_length() -> None:
    node = Table(data=_ROWS).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert len(node.rows) == 2


# ---------------------------------------------------------------------------
# columns argument overrides
# ---------------------------------------------------------------------------


def test_columns_list_selects_and_orders() -> None:
    node = Table(data=_ROWS, columns=["latency", "service"]).get_terminal_node(
        _ctx()
    )
    assert isinstance(node, TableNode)
    assert node.header is not None
    headers = [
        c.content if hasattr(c, "content") else c for c in node.header.cells
    ]
    assert headers == ["Latency", "Service"]


def test_columns_dict_with_header_string() -> None:
    node = Table(
        data=_ROWS, columns={"service": "Svc", "status": "State"}
    ).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.header is not None
    headers = [
        c.content if hasattr(c, "content") else c for c in node.header.cells
    ]
    assert headers == ["Svc", "State"]


def _cell_text(cell: object) -> str:
    content = getattr(cell, "content", cell)
    return str(content)


def test_columns_dict_with_column_spec() -> None:
    node = Table(
        data=_ROWS,
        columns={"latency": Column(format="{}ms", align="right", width=6)},
    ).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert _cell_text(node.rows[0].cells[0]).strip() == "12ms"


def test_columns_dict_with_accessor() -> None:
    node = Table(
        data=_ROWS,
        columns={"combined": lambda r: f"{r['service']}:{r['latency']}"},
    ).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert _cell_text(node.rows[0].cells[0]) == "api:12"


# ---------------------------------------------------------------------------
# Declarative subclass with Column descriptors
# ---------------------------------------------------------------------------


class Services(Table):
    service: str = Column()
    status: str = Column(color=lambda v: "green" if v == "ok" else "red")
    latency: int = Column(align="right", format="{}ms", width=8)


def test_subclass_captures_declared_columns() -> None:
    assert list(Services._declared) == ["service", "status", "latency"]


def test_subclass_renders_declared_columns() -> None:
    node = Services(data=_ROWS).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.header is not None
    headers = [
        c.content if hasattr(c, "content") else c for c in node.header.cells
    ]
    assert headers == ["Service", "Status", "Latency"]


def test_subclass_value_dependent_color() -> None:
    node = Services(data=_ROWS).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    # status column is index 1
    ok_cell = node.rows[0].cells[1]
    degraded_cell = node.rows[1].cells[1]
    assert getattr(ok_cell, "color") == "green"
    assert getattr(degraded_cell, "color") == "red"


def test_subclass_format_and_right_align() -> None:
    node = Services(data=_ROWS).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    latency_cell = node.rows[0].cells[2]
    assert _cell_text(latency_cell) == "    12ms"  # rjust(8)


def test_subclass_sets_column_widths_when_all_set() -> None:
    class Fixed(Table):
        a: str = Column(width=10)
        b: str = Column(width=20)

    node = Fixed(data=[{"a": "x", "b": "y"}]).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.column_widths == [10, 20]


def test_partial_widths_yield_none() -> None:
    class Mixed(Table):
        a: str = Column(width=10)
        b: str = Column()

    node = Mixed(data=[{"a": "x", "b": "y"}]).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.column_widths is None


# ---------------------------------------------------------------------------
# Selection / options
# ---------------------------------------------------------------------------


def test_selection_propagates() -> None:
    node = Table(data=_ROWS, selected=1).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.selected_row == 1


def test_hide_header() -> None:
    node = Table(data=_ROWS, show_header=False).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.header is None


def test_threads_z_and_visible() -> None:
    node = Table(data=_ROWS, z=4, visible=False).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.z == 4
    assert node.visible is False


# ---------------------------------------------------------------------------
# Offscreen render
# ---------------------------------------------------------------------------


def test_render_shows_headers_and_data() -> None:
    out = render_component_to_text(Table(data=_ROWS), width=48, height=6)
    assert "Service" in out
    assert "api" in out
    assert "degraded" in out


def test_render_selection_highlight_symbol() -> None:
    out = render_component_to_text(
        Table(data=_ROWS, selected=0, highlight_symbol="> "),
        width=48,
        height=6,
    )
    assert "> api" in out


def test_render_subclass_formats_values() -> None:
    out = render_component_to_text(Services(data=_ROWS), width=48, height=6)
    assert "12ms" in out
    assert "88ms" in out


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_data_is_safe() -> None:
    node = Table(data=[]).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.rows == []
    assert node.header is None


def test_empty_data_with_declared_columns_keeps_header() -> None:
    node = Services(data=[]).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert node.rows == []
    assert node.header is not None
    headers = [
        cell.content if hasattr(cell, "content") else cell
        for cell in node.header.cells
    ]
    assert headers == ["Service", "Status", "Latency"]


def test_render_empty_table_is_safe() -> None:
    out = render_component_to_text(Table(data=[]), width=20, height=4)
    assert isinstance(out, str)


def test_missing_keys_render_blank() -> None:
    rows = [{"a": 1, "b": 2}, {"a": 3}]  # second row missing "b"
    node = Table(data=rows, columns=["a", "b"]).get_terminal_node(_ctx())
    assert isinstance(node, TableNode)
    assert _cell_text(node.rows[1].cells[1]) == ""


def test_selection_out_of_range_is_safe() -> None:
    out = render_component_to_text(
        Table(data=_ROWS, selected=99), width=48, height=6
    )
    assert "api" in out
