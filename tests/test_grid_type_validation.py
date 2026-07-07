"""Grid integration tests for Python and Pydantic type validation."""

from __future__ import annotations

import dataclasses
import datetime
import enum
import uuid
from typing import Literal, TypedDict

import pytest
from pydantic import BaseModel, Field as PydanticField

from helpers import assign_attr, invalid_field
from xnano.beta import Field, Grid
from xnano.beta.components import Text
from xnano.beta.core.renderable import Renderable
from xnano.beta.exceptions import FieldValidationError
from xnano.beta.types import Area


class Status(enum.Enum):
    ON = "on"
    OFF = "off"


class ConfigModel(BaseModel):
    theme: str = "dark"
    retries: int = 3


class NestedConfigGrid(BaseModel):
    config: ConfigModel


@dataclasses.dataclass
class Metrics:
    count: int


class SettingsTD(TypedDict):
    verbose: bool


class TypedLayoutGrid(Grid):
    label: Literal["on", "off"] = Field(default="on")
    body: Renderable | str = Field(default="hello")
    count: int | None = Field(default=None, state=True)
    status: Status = Field(default=Status.ON, state=True)
    when: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime(
            2026, 1, 1, tzinfo=datetime.timezone.utc
        ),
        state=True,
    )
    uid: uuid.UUID = Field(
        default_factory=lambda: uuid.UUID(int=0),
        state=True,
    )
    config: ConfigModel = Field(default_factory=ConfigModel, state=True)
    metrics: Metrics = Field(default_factory=lambda: Metrics(0), state=True)


class StrictLayoutGrid(Grid):
    child: "ChildGrid" = Field(default_factory=lambda: ChildGrid())
    paragraph: Text = Field(default_factory=lambda: Text(content="hi"))


class ChildGrid(Grid):
    value: int = Field(default=1, state=True, strict=True)


class PydanticLayoutGrid(Grid):
    payload: ConfigModel = Field(default_factory=ConfigModel)


class PydanticNestedGrid(Grid):
    nested: NestedConfigGrid = Field(
        default_factory=lambda: NestedConfigGrid(config=ConfigModel())
    )


class LooseSetFieldGrid(Grid):
    name: str = Field(default="ok")


def test_literal_layout_field_validates() -> None:
    grid = TypedLayoutGrid()
    assert grid.label == "on"


def test_literal_layout_field_rejects_invalid_on_init() -> None:
    class LiteralPanel(Grid):
        mode: Literal["on", "off"] = invalid_field("maybe")

    with pytest.raises(FieldValidationError, match="mode"):
        LiteralPanel()


def test_union_layout_field_accepts_str_and_renderable() -> None:
    grid = TypedLayoutGrid()
    assert grid.body == "hello"
    grid.grid_set_field("body", Text(content="styled"))
    assert isinstance(grid.body, Text)


def test_optional_state_field_accepts_none() -> None:
    grid = TypedLayoutGrid()
    grid.count = None
    assert grid.count is None


def test_enum_state_field_accepts_member() -> None:
    grid = TypedLayoutGrid()
    grid.status = Status.OFF
    assert grid.status is Status.OFF


def test_enum_state_field_rejects_raw_string_without_strict() -> None:
    grid = TypedLayoutGrid()
    assign_attr(grid, "status", "off")
    assert grid.status == "off"


def test_enum_state_field_rejects_with_strict_runtime() -> None:
    class StrictEnumGrid(Grid):
        status: Status = Field(default=Status.ON, state=True, strict=True)

    grid = StrictEnumGrid()
    with pytest.raises(FieldValidationError, match="status"):
        assign_attr(grid, "status", "cyan")


def test_datetime_state_field_with_strict() -> None:
    class StrictDateGrid(Grid):
        when: datetime.datetime = Field(
            default_factory=lambda: datetime.datetime(
                2026, 1, 1, tzinfo=datetime.timezone.utc
            ),
            state=True,
            strict=True,
        )

    grid = StrictDateGrid()
    with pytest.raises(FieldValidationError, match="when"):
        assign_attr(grid, "when", "not-a-datetime")


def test_uuid_state_field_with_strict() -> None:
    class StrictUuidGrid(Grid):
        uid: uuid.UUID = Field(
            default_factory=lambda: uuid.UUID(int=0),
            state=True,
            strict=True,
        )

    grid = StrictUuidGrid()
    with pytest.raises(FieldValidationError, match="uid"):
        assign_attr(grid, "uid", "not-a-uuid")


def test_pydantic_model_state_field_accepts_instance() -> None:
    grid = TypedLayoutGrid()
    assert grid.config.theme == "dark"


def test_pydantic_model_state_field_rejects_dict_with_strict() -> None:
    class StrictConfigGrid(Grid):
        config: ConfigModel = Field(
            default_factory=ConfigModel, state=True, strict=True
        )

    grid = StrictConfigGrid()
    with pytest.raises(FieldValidationError, match="config"):
        assign_attr(grid, "config", {"theme": "light"})


def test_dataclass_state_field_accepts_instance() -> None:
    grid = TypedLayoutGrid()
    grid.metrics = Metrics(5)
    assert grid.metrics.count == 5


def test_dataclass_state_field_rejects_wrong_type_with_strict() -> None:
    class StrictMetricsGrid(Grid):
        metrics: Metrics = Field(
            default_factory=lambda: Metrics(0),
            state=True,
            strict=True,
        )

    grid = StrictMetricsGrid()
    with pytest.raises(FieldValidationError, match="metrics"):
        assign_attr(grid, "metrics", "not-metrics")


def test_nested_grid_and_component_validate_on_init() -> None:
    grid = StrictLayoutGrid()
    assert isinstance(grid.child, ChildGrid)
    assert isinstance(grid.paragraph, Text)


def test_nested_grid_rejects_wrong_type() -> None:
    class Bad(StrictLayoutGrid):
        child: ChildGrid = invalid_field(Text(content="nope"))

    with pytest.raises(FieldValidationError, match="child"):
        Bad()


def test_pydantic_model_layout_field_rejects_dict() -> None:
    class Bad(PydanticLayoutGrid):
        payload: ConfigModel = invalid_field({"theme": "x"})

    with pytest.raises(FieldValidationError, match="payload"):
        Bad()


def test_pydantic_nested_model_layout_field() -> None:
    grid = PydanticNestedGrid()
    assert grid.nested.config.theme == "dark"


def test_set_field_validates_under_strict_grid() -> None:
    grid = LooseSetFieldGrid()
    with pytest.raises(FieldValidationError, match="name"):
        grid.grid_set_field("name", 123)


def test_set_field_allows_valid_renderable() -> None:
    class Panel(Grid):
        body: Renderable = invalid_field("hi")

    panel = Panel()
    panel.grid_set_field("body", Text(content="ok"))
    assert isinstance(panel.body, Text)


def test_set_field_position_does_not_validate_value() -> None:
    class SlidePanel(Grid):
        body: str = Field(default="hi", slide=["x"])

    panel = SlidePanel()
    panel._grid_last_parent_area = Area(x=0, y=0, width=10, height=5)
    panel._grid_last_slot_areas = {
        "body": Area(x=0, y=0, width=4, height=2),
    }
    panel.grid_set_field("body", position=(2, 0))
    assert panel.field_position("body")[0] == 2


def test_field_validation_error_wraps_validation_error() -> None:
    class Bad(Grid):
        n: int = invalid_field("x")

    with pytest.raises(FieldValidationError) as exc:
        Bad()
    assert (
        "ValidationError" in str(exc.value)
        or "validation" in str(exc.value).lower()
    )


def test_none_layout_value_skips_validation() -> None:
    class OptionalPanel(Grid):
        body: Renderable | None = Field(default=None)

    panel = OptionalPanel()
    assert panel.body is None


def test_strict_child_state_field_validates_on_assignment() -> None:
    grid = StrictLayoutGrid()
    with pytest.raises(FieldValidationError, match="value"):
        assign_attr(grid.child, "value", "bad")


def test_init_validation_coerces_nothing_for_layout_fields() -> None:
    class IntPanel(Grid):
        n: int = Field(default=3)

    panel = IntPanel()
    assert panel.n == 3
    assert isinstance(panel.n, int)
