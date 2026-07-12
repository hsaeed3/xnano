"""Exhaustive tests for xnano.validation and Python/Pydantic type support."""

from __future__ import annotations

import dataclasses
import datetime
import enum
import uuid
from collections.abc import Sequence
from typing import Any, Literal, TypedDict, Union, get_args

import pytest
from pydantic import BaseModel
from pydantic_core import ValidationError, core_schema

from xnano._renderable import Renderable
from xnano._validation import (
    infer_pydantic_core_schema_name,
    layout_field_annotation,
    register_validatable_type,
    validate_type,
)
from xnano.components.text import Text
from xnano.grid import BaseGrid


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class IntColor(enum.IntEnum):
    ONE = 1
    TWO = 2


class UserModel(BaseModel):
    name: str
    age: int = 0


class ProfileModel(BaseModel):
    user: UserModel


class CustomSchemaType:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> Any:
        return core_schema.int_schema()


@dataclasses.dataclass
class Point:
    x: int
    y: int = 0


class RequiredTD(TypedDict):
    name: str


class OptionalTD(TypedDict, total=False):
    name: str
    age: int


class LeafGrid(BaseGrid):
    label: str = "leaf"


# ---------------------------------------------------------------------------
# infer_pydantic_core_schema_name
# ---------------------------------------------------------------------------


def test_infer_primitive_schema_names() -> None:
    assert infer_pydantic_core_schema_name(bool) == "bool"
    assert infer_pydantic_core_schema_name(int) == "int"
    assert infer_pydantic_core_schema_name(float) == "float"
    assert infer_pydantic_core_schema_name(str) == "str"
    assert infer_pydantic_core_schema_name(bytes) == "bytes"
    assert infer_pydantic_core_schema_name(complex) == "complex"
    assert infer_pydantic_core_schema_name(datetime.date) == "date"
    assert infer_pydantic_core_schema_name(datetime.time) == "time"
    assert infer_pydantic_core_schema_name(datetime.datetime) == "datetime"
    assert infer_pydantic_core_schema_name(datetime.timedelta) == "timedelta"
    assert infer_pydantic_core_schema_name(uuid.UUID) == "uuid"


def test_infer_container_schema_names() -> None:
    assert infer_pydantic_core_schema_name(list[int]) == "list"
    assert infer_pydantic_core_schema_name(tuple[int, str]) == "tuple"
    assert infer_pydantic_core_schema_name(set[str]) == "set"
    assert infer_pydantic_core_schema_name(frozenset[int]) == "frozenset"
    assert infer_pydantic_core_schema_name(dict[str, int]) == "dict"


def test_infer_union_and_nullable_schema_names() -> None:
    assert infer_pydantic_core_schema_name(Union[str, int]) == "union"
    assert infer_pydantic_core_schema_name(str | None) == "nullable"


def test_infer_class_schema_names() -> None:
    assert infer_pydantic_core_schema_name(Color) == "enum"
    assert infer_pydantic_core_schema_name(Point) == "dataclass"
    assert infer_pydantic_core_schema_name(UserModel) == "pydantic-model"
    assert infer_pydantic_core_schema_name(LeafGrid) == "is-instance"


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("annotation", "value"),
    [
        (bool, True),
        (int, 42),
        (float, 1.5),
        (str, "hello"),
        (bytes, b"raw"),
        (complex, 1 + 2j),
        (datetime.date, datetime.date(2026, 1, 1)),
        (datetime.time, datetime.time(12, 30)),
        (datetime.datetime, datetime.datetime(2026, 1, 1, 12, 0)),
        (datetime.timedelta, datetime.timedelta(days=1)),
        (uuid.UUID, uuid.UUID(int=0)),
    ],
)
def test_validate_primitives_accepts_valid(
    annotation: type, value: object
) -> None:
    assert validate_type(value, annotation) == value


@pytest.mark.parametrize(
    ("annotation", "value"),
    [
        (str, 1),
        (uuid.UUID, "not-a-uuid"),
        (bool, []),
        (int, []),
    ],
)
def test_validate_primitives_rejects_invalid(
    annotation: type, value: object
) -> None:
    with pytest.raises(ValidationError):
        validate_type(value, annotation)


@pytest.mark.parametrize(
    ("annotation", "value", "expected"),
    [
        (int, "1", 1),
        (float, "1.0", 1.0),
        (bytes, "bytes", b"bytes"),
        (datetime.date, "2026-01-01", datetime.date(2026, 1, 1)),
        (complex, "1+2j", 1 + 2j),
    ],
)
def test_validate_primitives_coerce_strings(
    annotation: type,
    value: object,
    expected: object,
) -> None:
    assert validate_type(value, annotation) == expected


def test_validate_any_accepts_everything() -> None:
    assert validate_type(1, Any) == 1
    assert validate_type("x", Any) == "x"
    assert validate_type(object(), Any) is not None


def test_validate_none_only_accepts_none() -> None:
    assert validate_type(None, type(None)) is None
    with pytest.raises(ValidationError):
        validate_type(0, type(None))


# ---------------------------------------------------------------------------
# Unions, optionals, literals
# ---------------------------------------------------------------------------


def test_validate_union_accepts_either_member() -> None:
    assert validate_type("a", Union[str, int]) == "a"
    assert validate_type(1, Union[str, int]) == 1
    with pytest.raises(ValidationError):
        validate_type([], Union[str, int])


def test_validate_nullable_union() -> None:
    assert validate_type(None, str | None) is None
    assert validate_type("ok", str | None) == "ok"
    with pytest.raises(ValidationError):
        validate_type(1, str | None)


def test_validate_literal() -> None:
    ann = Literal["on", "off"]
    assert validate_type("on", ann) == "on"
    with pytest.raises(ValidationError):
        validate_type("maybe", ann)


# ---------------------------------------------------------------------------
# Containers
# ---------------------------------------------------------------------------


def test_validate_list() -> None:
    assert validate_type([1, 2, 3], list[int]) == [1, 2, 3]
    with pytest.raises(ValidationError):
        validate_type([1, "two"], list[int])


def test_validate_empty_list_annotation() -> None:
    assert validate_type([], list) == []


def test_validate_tuple_fixed() -> None:
    assert validate_type((1, "a"), tuple[int, str]) == (1, "a")
    with pytest.raises(ValidationError):
        validate_type((1, 2), tuple[int, str])


def test_validate_set_and_frozenset() -> None:
    assert validate_type({"a", "b"}, set[str]) == {"a", "b"}
    assert validate_type(frozenset({"a"}), frozenset[str]) == frozenset({"a"})
    with pytest.raises(ValidationError):
        validate_type({1}, set[str])


def test_validate_dict() -> None:
    assert validate_type({"a": 1}, dict[str, int]) == {"a": 1}
    with pytest.raises(ValidationError):
        validate_type({"a": "nope"}, dict[str, int])


def test_validate_sequence_accepts_list_or_tuple() -> None:
    assert validate_type([1, 2], Sequence[int]) == [1, 2]
    # pydantic-core may normalize tuples to lists for homogeneous sequences.
    assert validate_type((1, 2), Sequence[int]) in ([1, 2], (1, 2))
    with pytest.raises(ValidationError):
        validate_type("not-a-sequence", Sequence[int])


def test_validate_bare_sequence() -> None:
    assert validate_type([1, "a"], Sequence) == [1, "a"]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


def test_validate_enum_member() -> None:
    assert validate_type(Color.RED, Color) is Color.RED
    assert validate_type("red", Color) is Color.RED
    with pytest.raises(ValidationError):
        validate_type("cyan", Color)


def test_validate_int_enum() -> None:
    assert validate_type(IntColor.ONE, IntColor) is IntColor.ONE


# ---------------------------------------------------------------------------
# TypedDict
# ---------------------------------------------------------------------------


def test_validate_typed_dict_required_key() -> None:
    assert validate_type({"name": "ada"}, RequiredTD) == {"name": "ada"}
    with pytest.raises(ValidationError):
        validate_type({}, RequiredTD)


def test_validate_typed_dict_optional_keys() -> None:
    assert validate_type({}, OptionalTD) == {}
    assert validate_type({"name": "ada", "age": 3}, OptionalTD) == {
        "name": "ada",
        "age": 3,
    }


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def test_validate_dataclass_from_dict() -> None:
    result = validate_type({"x": 1, "y": 2}, Point)
    assert result == Point(1, 2)


def test_validate_dataclass_from_instance() -> None:
    point = Point(3, 4)
    assert validate_type(point, Point) == point


def test_validate_dataclass_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        validate_type({"x": "nope"}, Point)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


def test_validate_pydantic_model_accepts_instance_only() -> None:
    model = UserModel(name="ada")
    assert validate_type(model, UserModel) is model


def test_validate_pydantic_model_rejects_dict() -> None:
    with pytest.raises(ValidationError):
        validate_type({"name": "ada"}, UserModel)


def test_validate_pydantic_model_rejects_wrong_type() -> None:
    with pytest.raises(ValidationError):
        validate_type("ada", UserModel)


def test_validate_nested_pydantic_model_field() -> None:
    profile = ProfileModel(user=UserModel(name="ada"))
    assert validate_type(profile, ProfileModel).user.name == "ada"


def test_validate_pydantic_model_with_field_defaults() -> None:
    model = UserModel(name="ada")
    assert validate_type(model, UserModel).age == 0


def test_validate_pydantic_model_subclass_instance() -> None:
    class Admin(UserModel):
        role: str = "admin"

    admin = Admin(name="root")
    assert validate_type(admin, UserModel).name == "root"


# ---------------------------------------------------------------------------
# Framework / xnano types
# ---------------------------------------------------------------------------


def test_layout_field_annotation_is_renderable() -> None:
    assert layout_field_annotation() is Renderable


def test_validate_renderable_members() -> None:
    renderable = layout_field_annotation()
    assert validate_type("hello", renderable) == "hello"
    assert validate_type(Text(content="hi"), renderable).content == "hi"
    assert validate_type(LeafGrid(), renderable).label == "leaf"
    assert validate_type(["a", "b"], renderable) == ["a", "b"]
    assert validate_type(123, renderable) == 123
    assert validate_type(3.14, renderable) == 3.14


def test_validate_grid_subclass() -> None:
    leaf = LeafGrid()
    assert validate_type(leaf, LeafGrid) is leaf
    with pytest.raises(ValidationError):
        validate_type("not-a-grid", LeafGrid)


def test_validate_component_subclass() -> None:
    text = Text(content="x")
    assert validate_type(text, Text) is text
    with pytest.raises(ValidationError):
        validate_type("text", Text)


# ---------------------------------------------------------------------------
# Custom pydantic core schema hook
# ---------------------------------------------------------------------------


def test_validate_type_with_custom_pydantic_core_schema() -> None:
    assert validate_type(7, CustomSchemaType) == 7
    assert validate_type("7", CustomSchemaType) == 7
    with pytest.raises(ValidationError):
        validate_type([], CustomSchemaType)


class LegacySchemaType:
    @classmethod
    def __pydantic_core_schema__(cls, source_type: Any) -> Any:
        return core_schema.bool_schema()


def test_validate_type_with_legacy_pydantic_core_schema_callable() -> None:
    assert validate_type(True, LegacySchemaType) is True
    with pytest.raises(ValidationError):
        validate_type([], LegacySchemaType)


# ---------------------------------------------------------------------------
# register_validatable_type / caching
# ---------------------------------------------------------------------------


def test_register_validatable_type_caches_validator() -> None:
    first = register_validatable_type(int)
    second = register_validatable_type(int)
    assert first is second


def test_register_validatable_type_validates_same_as_validate_type() -> None:
    validator = register_validatable_type(str)
    assert validator.validate_python("ok") == "ok"
    with pytest.raises(ValidationError):
        validator.validate_python(1)


# ---------------------------------------------------------------------------
# Coercion edges pydantic-core allows
# ---------------------------------------------------------------------------


def test_int_coerces_from_bool() -> None:
    assert validate_type(True, int) == 1


def test_float_coerces_from_int() -> None:
    assert validate_type(2, float) == 2.0


def test_str_does_not_coerce_from_int() -> None:
    with pytest.raises(ValidationError):
        validate_type(1, str)


# ---------------------------------------------------------------------------
# Non-class annotations fall back to any
# ---------------------------------------------------------------------------


def test_non_class_annotation_accepts_anything() -> None:
    # A typing.TypeVar-like object isn't a class; should use any_schema path.
    annotation = get_args(list[Any])[0] if get_args(list[Any]) else Any
    assert validate_type("anything", annotation) == "anything"


def test_validate_bare_tuple_annotation() -> None:
    assert validate_type((1, "a"), tuple) == (1, "a")


def test_validate_bare_dict_annotation() -> None:
    assert validate_type({"a": 1}, dict) == {"a": 1}


def test_validate_union_with_multiple_non_none_members() -> None:
    ann = Union[int, str, bytes]
    assert validate_type(1, ann) == 1
    assert validate_type("x", ann) == "x"
    with pytest.raises(ValidationError):
        validate_type([], ann)


def test_validate_pydantic_model_with_validator_attr() -> None:
    class LegacyValidatorModel(BaseModel):
        n: int

    assert hasattr(LegacyValidatorModel, "model_fields")
    assert (
        validate_type(LegacyValidatorModel(n=1), LegacyValidatorModel).n == 1
    )
