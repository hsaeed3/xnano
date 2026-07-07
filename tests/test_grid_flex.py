"""tests.test_grid_flex"""

from __future__ import annotations

from xnano.beta import Field, Grid
from xnano.beta.grid import _layout_constraint_for_field


def test_field_accepts_tailwind_flex_class() -> None:
    class FlexGrid(Grid):
        body: str = Field(default="hello", flex="flex-1")

    field = FlexGrid()._grid_field_info("body")
    assert field.flex == 1


def test_field_accepts_numeric_flex() -> None:
    class FlexGrid(Grid):
        body: str = Field(default="hello", flex=3)

    field = FlexGrid()._grid_field_info("body")
    assert field.flex == 3


def test_grid_set_field_normalizes_tailwind_flex() -> None:
    class FlexGrid(Grid):
        body: str = Field(default="hello")

    grid = FlexGrid()
    grid.grid_set_field("body", flex="grow")

    field = grid._grid_field_info("body")
    assert field.flex == 1


def test_layout_constraint_uses_fill_for_grow_classes() -> None:
    class FlexGrid(Grid):
        body: str = Field(default="hello", flex="flex-1")

    field = FlexGrid()._grid_field_info("body")
    constraint = _layout_constraint_for_field(field, "vertical")

    assert constraint.kind == "fill"
    assert constraint.value == 1


def test_layout_constraint_uses_min_for_no_grow_classes() -> None:
    class FlexGrid(Grid):
        body: str = Field(default="hello", flex="flex-none")

    field = FlexGrid()._grid_field_info("body")
    constraint = _layout_constraint_for_field(field, "vertical")

    assert constraint.kind == "min"
    assert constraint.value == 1
