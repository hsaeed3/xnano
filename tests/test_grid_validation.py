"""Tests for grid field validation on init and setattr."""

from __future__ import annotations

import pytest
from helpers import assign_attr, invalid_field
from pydantic import BaseModel

from xnano._renderable import Renderable
from xnano.core.exceptions import FieldValidationError
from xnano.fields import Field
from xnano.grid import BaseGrid


class Leaf(BaseGrid):
    label: str = Field(default="hello")


class Root(BaseGrid, direction="horizontal"):
    left: Leaf = Field(default_factory=Leaf)
    right: Leaf = Field(default_factory=Leaf)


class LooseGrid(BaseGrid, strict=False):
    count: int = invalid_field("not-an-int")


class StrictStateGrid(BaseGrid):
    count: int = 0


class StrictRuntimeGrid(BaseGrid):
    count: int = Field(default=0, state=True, strict=True)


class ModelGrid(BaseGrid):
    model: "UserModel" = Field(default_factory=lambda: UserModel(name="ada"))


class UserModel(BaseModel):
    name: str


class UnannotatedLayoutGrid(BaseGrid):
    body = "hello"


def test_strict_init_accepts_nested_grids() -> None:
    root = Root()
    assert isinstance(root.left, Leaf)
    assert isinstance(root.right, Leaf)


def test_strict_init_rejects_invalid_layout_field() -> None:
    class Bad(BaseGrid):
        label: str = invalid_field(123)

    with pytest.raises(FieldValidationError, match="label"):
        Bad()


def test_strict_init_rejects_invalid_nested_grid() -> None:
    class Bad(BaseGrid):
        child: Leaf = invalid_field(123)

    with pytest.raises(FieldValidationError, match="child"):
        Bad()


def test_strict_init_accepts_any_renderable_value() -> None:
    class Panel(BaseGrid):
        body: Renderable = invalid_field(123)

    grid = Panel()
    assert grid.body == 123


def test_strict_disabled_skips_init_validation() -> None:
    grid = LooseGrid()
    assert grid.count == "not-an-int"


def test_unannotated_layout_field_accepts_renderables() -> None:
    grid = UnannotatedLayoutGrid()
    assert grid.body == "hello"

    grid = UnannotatedLayoutGrid()
    object.__setattr__(grid, "body", Leaf())
    grid._grid_validate_init()


def test_unannotated_layout_field_accepts_any_value() -> None:
    class Panel(UnannotatedLayoutGrid):
        pass

    grid = Panel()
    object.__setattr__(grid, "body", 123)
    grid._grid_validate_init()
    assert grid.body == 123


def test_pydantic_model_field_accepts_instance() -> None:
    grid = ModelGrid()
    assert grid.model.name == "ada"


def test_pydantic_model_field_rejects_wrong_type() -> None:
    class Bad(ModelGrid):
        model: UserModel = invalid_field(123)

    with pytest.raises(FieldValidationError, match="model"):
        Bad()


def test_state_field_without_runtime_strict_allows_bad_assignment() -> None:
    grid = StrictStateGrid()
    assign_attr(grid, "count", "nope")
    assert grid.count == "nope"


def test_state_field_with_runtime_strict_rejects_bad_assignment() -> None:
    grid = StrictRuntimeGrid()
    with pytest.raises(FieldValidationError, match="count"):
        assign_attr(grid, "count", "nope")


def test_none_skips_init_validation() -> None:
    class OptionalBody(BaseGrid):
        body: Renderable | None = Field(default=None)

    grid = OptionalBody()
    assert grid.body is None
