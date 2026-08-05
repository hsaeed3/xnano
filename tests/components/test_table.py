"""Tests for ``Table``."""

from __future__ import annotations

import dataclasses
from typing import Any, cast

import pytest

from xnano.area import Area
from xnano.components.component import ComponentRenderContext
from xnano.components.table import Column, Table
from xnano.core import Runtime
from xnano.core.content import TableGrid


def _ctx() -> ComponentRenderContext[Any]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=48, height=10))


def _node(table: Table) -> Any:
    content = table.compose(_ctx())
    assert isinstance(content, TableGrid)
    return content


def _cell_text(cell: object) -> str:
    content = getattr(cell, "content", cell)
    return str(content)


_ROWS = [
    {"service": "api", "status": "ok", "latency": 12},
    {"service": "cache", "status": "degraded", "latency": 88},
    {"service": "db", "status": "ok", "latency": 4},
]


def test_infers_columns_from_dict_keys() -> None:
    node = _node(Table(data=_ROWS))
    assert node.header is not None
    headers = [_cell_text(cell) for cell in node.header.cells]
    assert headers == ["Service", "Status", "Latency"]


def test_infers_columns_from_dataclass_fields() -> None:
    @dataclasses.dataclass
    class Service:
        name: str
        rps: int

    node = _node(Table(data=[Service("api", 10), Service("cache", 5)]))
    assert len(node.rows) == 2


def test_body_rows_match_data_length() -> None:
    node = _node(Table(data=_ROWS))
    assert len(node.rows) == 3


def test_columns_list_selects_and_orders() -> None:
    node = _node(Table(data=_ROWS, columns=["latency", "service"]))
    headers = [_cell_text(cell) for cell in node.header.cells]
    assert headers == ["Latency", "Service"]


def test_columns_dict_with_header_string() -> None:
    node = _node(
        Table(data=_ROWS, columns={"service": "Svc", "status": "State"})
    )
    headers = [_cell_text(cell) for cell in node.header.cells]
    assert headers == ["Svc", "State"]


def test_columns_dict_with_column_spec() -> None:
    node = _node(
        Table(
            data=_ROWS,
            columns={
                "latency": Column(
                    format="{}ms", horizontal_align="right", width=6
                )
            },
        )
    )
    assert _cell_text(node.rows[0].cells[0]).strip() == "12ms"

    function_format = _node(
        Table(
            data=_ROWS,
            columns={
                "latency": Column(format=lambda value: f"{value / 10:.1f}")
            },
        )
    )
    assert _cell_text(function_format.rows[0].cells[0]) == "1.2"


def test_callable_column_and_object_rows_form_a_projection() -> None:
    class Service:
        def __init__(self, name: str, latency: int) -> None:
            self.name = name
            self.latency = latency

    table = Table(
        data=[Service("api", 12), Service("db", 4)],
        columns=cast(
            Any,
            {
                "summary": lambda row: f"{row.name}:{row.latency}",
                "missing": None,
            },
        ),
    )
    node = _node(table)
    assert [_cell_text(row.cells[0]) for row in node.rows] == [
        "api:12",
        "db:4",
    ]

    inferred = _node(Table(data=[Service("worker", 7)]))
    assert [_cell_text(cell) for cell in inferred.header.cells] == [
        "Name",
        "Latency",
    ]


class Services(Table):
    service: str = Column()
    status: str = Column(foreground=lambda v: "green" if v == "ok" else "red")
    latency: int = Column(horizontal_align="right", format="{}ms", width=8)


def test_subclass_captures_declared_columns() -> None:
    assert list(Services._declared) == ["service", "status", "latency"]


def test_subclass_value_dependent_color() -> None:
    node = _node(Services(data=_ROWS))
    assert getattr(node.rows[0].cells[1], "color") == "green"
    assert getattr(node.rows[1].cells[1], "color") == "red"


def test_subclass_format_and_right_align() -> None:
    node = _node(Services(data=_ROWS))
    assert _cell_text(node.rows[0].cells[2]) == "    12ms"


def test_selection_propagates() -> None:
    node = _node(Table(data=_ROWS, selected=1))
    assert node.selected_row == 1


def test_value_and_selected_row() -> None:
    table = Table(data=_ROWS, selected=1)
    assert table.selected_row == _ROWS[1]
    assert table.value == _ROWS[1]


def test_move_clamps() -> None:
    table = Table(data=_ROWS, selected=0, focusable=True)
    assert table.move(1) == 1
    assert table.move(100) == 2
    assert table.move(-100) == 0


def test_sort_derived_order_without_mutating_data() -> None:
    original = list(_ROWS)
    table = Table(data=_ROWS, sort="latency", sort_direction="ascending")
    node = _node(table)
    first_service = _cell_text(node.rows[0].cells[0])
    assert first_service == "db"
    assert table.data == original


def test_sort_descending() -> None:
    table = Table(data=_ROWS, sort="latency", sort_direction="descending")
    node = _node(table)
    assert _cell_text(node.rows[0].cells[0]) == "cache"


def test_selected_row_respects_sort_display_index() -> None:
    table = Table(
        data=_ROWS,
        sort="latency",
        sort_direction="ascending",
        selected=0,
    )
    assert table.selected_row is not None
    assert table.selected_row["service"] == "db"


def test_missing_sort_column_falls_back_to_row_key() -> None:
    table = Table(
        data=_ROWS,
        columns=["service"],
        sort="latency",
        selected=0,
    )
    selected_row = table.selected_row
    assert selected_row is not None
    assert selected_row["service"] == "db"


def test_invalid_and_empty_selections_have_no_value() -> None:
    assert Table(data=_ROWS, selected=None).value is None
    assert Table(data=_ROWS, selected=-1).value is None
    assert Table(data=_ROWS, selected=99).value is None
    empty = Table(data=[], selected=2, focusable=True)
    assert empty.move(1) is None
    assert empty.selected is None


@pytest.mark.parametrize(
    ("align", "expected"),
    (("left", "x   "), ("center", " x  ")),
)
def test_fixed_width_alignment(align: str, expected: str) -> None:
    node = _node(
        Table(
            data=[{"value": "x"}],
            columns={"value": Column(width=4, horizontal_align=align)},  # type: ignore[arg-type]
        )
    )
    assert _cell_text(node.rows[0].cells[0]) == expected


def test_handle_keyboard_when_focusable() -> None:
    table = Table(data=_ROWS, selected=0, focusable=True)

    class _Key:
        def __init__(self, *names: str) -> None:
            self._names = set(names)

        def matches(self, *bindings: str) -> bool:
            return any(binding in self._names for binding in bindings)

    assert table.handle_keyboard(cast(Any, _Key("down"))) is True
    assert table.selected == 1
    assert table.handle_keyboard(cast(Any, _Key("home"))) is True
    assert table.selected == 0
    assert table.handle_keyboard(cast(Any, _Key("end"))) is True
    assert table.selected == 2


@pytest.mark.parametrize(
    ("binding", "selected", "expected"),
    (
        ("j", 4, 5),
        ("k", 4, 3),
        ("pagedown", 4, 14),
        ("pageup", 14, 4),
        ("home", 14, 0),
        ("end", 4, 24),
    ),
)
def test_log_table_navigation_shortcuts(
    binding: str,
    selected: int,
    expected: int,
) -> None:
    table = Table(
        data=[
            {"line": index, "message": f"event {index}"} for index in range(25)
        ],
        selected=selected,
        focusable=True,
    )

    class _Key:
        def matches(self, *bindings: str) -> bool:
            return binding in bindings

    assert table.handle_keyboard(cast(Any, _Key())) is True
    assert table.selected == expected
    value = table.value
    assert value is not None
    assert value["message"] == f"event {expected}"


def test_handle_keyboard_ignored_when_not_focusable() -> None:
    table = Table(data=_ROWS, selected=0, focusable=False)

    class _Key:
        def matches(self, *bindings: str) -> bool:
            return "down" in bindings

    assert table.handle_keyboard(cast(Any, _Key())) is False
    assert table.selected == 0


def test_table_passthrough_and_unknown_keys_bubble() -> None:
    table = Table(
        data=_ROWS,
        selected=0,
        focusable=True,
        passthrough=("down",),
    )

    class _Key:
        def __init__(self, binding: str) -> None:
            self.binding = binding

        def matches(self, *bindings: str) -> bool:
            return self.binding in bindings

    assert table.handle_keyboard(cast(Any, _Key("down"))) is False
    assert table.selected == 0
    assert table.handle_keyboard(cast(Any, _Key("enter"))) is False


def test_hide_header() -> None:
    node = _node(Table(data=_ROWS, show_header=False))
    assert node.header is None


def test_empty_data_is_safe() -> None:
    node = _node(Table(data=[]))
    assert node.rows == ()
    assert node.header is None

    scalar = _node(Table(data=[1, 2, 3]))
    assert scalar.header is None
    assert len(scalar.rows) == 3


def test_empty_data_with_declared_columns_keeps_header() -> None:
    node = _node(Services(data=[]))
    assert node.rows == ()
    assert node.header is not None


def test_runtime_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(48, 8)
    try:
        frame = runtime.render(Table(data=_ROWS))
        assert "Service" in frame.text
        assert "api" in frame.text
    finally:
        runtime.close()


def test_runtime_selection_highlight_symbol() -> None:
    runtime = Runtime.offscreen(48, 8)
    try:
        frame = runtime.render(
            Table(data=_ROWS, selected=0, highlight_symbol="> ")
        )
        assert "> api" in frame.text
    finally:
        runtime.close()
