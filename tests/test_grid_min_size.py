"""tests.test_grid_min_size"""

from __future__ import annotations

from xnano.beta import Field, Grid
from xnano.beta.grid import _layout_constraint_for_field


def test_grid_min_size_with_border() -> None:
    class MinSizeGrid(Grid):
        body: str = Field(default="hello", border="rounded")

    grid = MinSizeGrid()
    field = grid._grid_field_info("body")

    constraint = _layout_constraint_for_field(field, "vertical")
    assert constraint.kind == "min"
    assert constraint.value == 3

    grid.grid_set_field("body", size=1)
    field = grid._grid_field_info("body")
    constraint = _layout_constraint_for_field(field, "vertical")
    assert constraint.kind == "length"
    assert constraint.value == 3

    grid.grid_set_field("body", size=5)
    field = grid._grid_field_info("body")
    constraint = _layout_constraint_for_field(field, "vertical")
    assert constraint.kind == "length"
    assert constraint.value == 5
