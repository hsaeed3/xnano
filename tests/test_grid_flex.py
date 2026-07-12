"""tests.test_grid_flex

Fill-weight sizing on grid fields. Tailwind flex utilities (``"flex-1"``,
``"grow"``, ``"flex-none"``) are accepted anywhere a ``Sizing`` is — they
lower to fraction (fill) weights through ``Sizing.parse``.
"""

from __future__ import annotations

from xnano.fields import Field
from xnano.grid import BaseGrid, _layout_constraint_for_field
from xnano._types import Sizing


def test_field_accepts_tailwind_flex_class() -> None:
    class FlexGrid(BaseGrid):
        body: str = Field(default="hello", height="flex-1")

    field = FlexGrid()._grid_field_info("body")
    assert field.height == Sizing.fraction(1)


def test_field_accepts_numeric_fraction() -> None:
    class FlexGrid(BaseGrid):
        body: str = Field(default="hello", height="3fr")

    field = FlexGrid()._grid_field_info("body")
    assert field.height == Sizing.fraction(3)


def test_grid_set_field_normalizes_tailwind_flex() -> None:
    class FlexGrid(BaseGrid):
        body: str = Field(default="hello")

    grid = FlexGrid()
    grid.grid_set_field("body", height="grow")

    field = grid._grid_field_info("body")
    assert field.height == Sizing.fraction(1)


def test_layout_constraint_uses_fill_for_grow_classes() -> None:
    class FlexGrid(BaseGrid):
        body: str = Field(default="hello", height="flex-1")

    field = FlexGrid()._grid_field_info("body")
    constraint = _layout_constraint_for_field(field, "vertical")

    assert constraint.kind == "fill"
    assert constraint.value == 1


def test_layout_constraint_uses_min_for_no_grow_classes() -> None:
    class FlexGrid(BaseGrid):
        body: str = Field(default="hello", height="flex-none")

    field = FlexGrid()._grid_field_info("body")
    constraint = _layout_constraint_for_field(field, "vertical")

    assert constraint.kind == "min"
    assert constraint.value == 1


def test_field_without_layout_sizing_fills() -> None:
    class FlexGrid(BaseGrid):
        body: str = Field(default="hello")

    field = FlexGrid()._grid_field_info("body")
    constraint = _layout_constraint_for_field(field, "vertical")

    assert constraint.kind == "fill"
    assert constraint.value == 1
