"""xnano._validation

---

Runtime type and value validation helpers used by fields and CLI.
"""

from __future__ import annotations

import collections.abc
import dataclasses
import datetime
import enum
import functools
import inspect
import types
import uuid
from typing import (
    Any,
    Callable,
    Generator,
    Literal,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic_core import (
    SchemaValidator,
    core_schema,
)


_SCHEMA_VALIDATOR_CACHE: dict[Any, SchemaValidator] = {}
_RENDERABLE_SCHEMA: Any | None = None
_RENDERABLE_ANNOTATION: Any | None = None


def _is_union_origin(origin: object | None) -> bool:
    """Return whether ``origin`` is a union type from ``typing`` or ``types``."""
    return origin is Union or origin is types.UnionType


_PRIMITIVE_SCHEMAS: dict[type, Any] = {
    bool: core_schema.bool_schema(),
    int: core_schema.int_schema(),
    float: core_schema.float_schema(),
    str: core_schema.str_schema(),
    bytes: core_schema.bytes_schema(),
    complex: core_schema.complex_schema(),
    type(None): core_schema.none_schema(),
    datetime.date: core_schema.date_schema(),
    datetime.time: core_schema.time_schema(),
    datetime.datetime: core_schema.datetime_schema(),
    datetime.timedelta: core_schema.timedelta_schema(),
    uuid.UUID: core_schema.uuid_schema(),
}


_SUPPORTED_SCHEMA_TYPE_FUNCTIONS: dict[str, Callable] = {
    "bool": core_schema.bool_schema,
    "bytes": core_schema.bytes_schema,
    "float": core_schema.float_schema,
    "int": core_schema.int_schema,
    "str": core_schema.str_schema,
    "complex": core_schema.complex_schema,
    "list": core_schema.list_schema,
    "tuple": core_schema.tuple_schema,
    "set": core_schema.set_schema,
    "frozenset": core_schema.frozenset_schema,
    "dict": core_schema.dict_schema,
    "generator": core_schema.generator_schema,
    "model-fields": core_schema.model_fields_schema,
    "typed-dict": core_schema.typed_dict_schema,
    "dataclass": core_schema.dataclass_schema,
    "dataclass-args": core_schema.dataclass_args_schema,
    "pydantic-model": core_schema.model_schema,
    "date": core_schema.date_schema,
    "time": core_schema.time_schema,
    "datetime": core_schema.datetime_schema,
    "timedelta": core_schema.timedelta_schema,
    "literal": core_schema.literal_schema,
    "enum": core_schema.enum_schema,
    "is-instance": core_schema.is_instance_schema,
    "is-subclass": core_schema.is_subclass_schema,
    "nullable": core_schema.nullable_schema,
    "union": core_schema.union_schema,
    "tagged-union": core_schema.tagged_union_schema,
    "chain": core_schema.chain_schema,
    "lax-or-strict": core_schema.lax_or_strict_schema,
    "json-or-python": core_schema.json_or_python_schema,
    "arguments": core_schema.arguments_schema,
    "arguments-v3": core_schema.arguments_v3_schema,
    "call": core_schema.call_schema,
    "custom-error": core_schema.custom_error_schema,
    "json": core_schema.json_schema,
    "url": core_schema.url_schema,
    "multi-host-url": core_schema.multi_host_url_schema,
    "uuid": core_schema.uuid_schema,
    "missing-sentinel": core_schema.missing_sentinel_schema,
    "function-before": core_schema.with_info_before_validator_function,
    "function-after": core_schema.with_info_after_validator_function,
    "function-wrap": core_schema.with_info_wrap_validator_function,
    "function-plain": core_schema.with_info_plain_validator_function,
    "definition-ref": core_schema.definition_reference_schema,
    "definitions": core_schema.definitions_schema,
}


@functools.lru_cache(maxsize=1024)
def infer_pydantic_core_schema_name(annotation: type) -> str:
    """Infers the ``pydantic_core`` schema name for a given type annotation.

    Args:
        annotation: The type to infer the schema name for.

    Returns:
        The ``pydantic_core`` schema name string for the given type.
    """
    origin = get_origin(annotation)
    if _is_union_origin(origin):
        args = get_args(annotation)
        if type(None) in args:
            return "nullable"
        return "union"

    _ORIGIN_MAP: dict = {
        list: "list",
        tuple: "tuple",
        set: "set",
        frozenset: "frozenset",
        dict: "dict",
        Generator: "generator",
    }
    if origin in _ORIGIN_MAP:
        return _ORIGIN_MAP[origin]

    _TYPE_MAP: dict[type, str] = {
        bool: "bool",
        bytes: "bytes",
        float: "float",
        int: "int",
        str: "str",
        complex: "complex",
        datetime.date: "date",
        datetime.time: "time",
        datetime.datetime: "datetime",
        datetime.timedelta: "timedelta",
        uuid.UUID: "uuid",
    }
    if annotation in _TYPE_MAP:
        return _TYPE_MAP[annotation]

    if inspect.isclass(annotation):
        if issubclass(annotation, enum.Enum):
            return "enum"
        if dataclasses.is_dataclass(annotation):
            return "dataclass"
        if hasattr(annotation, "model_fields"):
            return "pydantic-model"

    return "is-instance"


def _get_renderable_annotation() -> Any:
    global _RENDERABLE_ANNOTATION
    if _RENDERABLE_ANNOTATION is None:
        from xnano._renderable import Renderable

        _RENDERABLE_ANNOTATION = Renderable
    return _RENDERABLE_ANNOTATION


def _build_renderable_schema() -> Any:
    global _RENDERABLE_SCHEMA
    if _RENDERABLE_SCHEMA is not None:
        return _RENDERABLE_SCHEMA
    _RENDERABLE_SCHEMA = core_schema.any_schema()
    return _RENDERABLE_SCHEMA


def _is_grid_type(annotation: Any) -> bool:
    if not inspect.isclass(annotation):
        return False
    from xnano.grid import BaseGrid

    try:
        return issubclass(annotation, BaseGrid)
    except TypeError:
        return False


def _is_component_type(annotation: Any) -> bool:
    if not inspect.isclass(annotation):
        return False
    from xnano.components.abstract import AbstractComponent

    try:
        return issubclass(annotation, AbstractComponent)
    except TypeError:
        return False


def _is_pydantic_model_type(annotation: Any) -> bool:
    if not inspect.isclass(annotation):
        return False
    return hasattr(annotation, "model_fields") or hasattr(
        annotation, "__pydantic_validator__"
    )


def layout_field_annotation() -> Any:
    """Default type annotation for layout fields without an explicit one."""
    return _get_renderable_annotation()


def _build_core_schema(annotation: Any) -> Any:
    if annotation is _get_renderable_annotation():
        return _build_renderable_schema()

    if annotation is Any:
        return core_schema.any_schema()

    if annotation in _PRIMITIVE_SCHEMAS:
        return _PRIMITIVE_SCHEMAS[annotation]

    origin = get_origin(annotation)
    args = get_args(annotation)

    if (
        origin is collections.abc.Sequence
        or annotation is collections.abc.Sequence
    ):
        item_schema = (
            _build_core_schema(args[0]) if args else core_schema.any_schema()
        )
        return core_schema.union_schema(
            [
                core_schema.list_schema(items_schema=item_schema),
                core_schema.tuple_schema(
                    items_schema=[item_schema] if args else []
                ),
            ]
        )

    if _is_union_origin(origin):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return core_schema.nullable_schema(_build_core_schema(non_none[0]))
        return core_schema.union_schema([_build_core_schema(a) for a in args])

    if origin is Literal:
        return core_schema.literal_schema(list(args))

    if origin is list:
        return core_schema.list_schema(
            items_schema=_build_core_schema(args[0])
            if args
            else core_schema.any_schema()
        )

    if origin is set:
        return core_schema.set_schema(
            items_schema=_build_core_schema(args[0])
            if args
            else core_schema.any_schema()
        )

    if origin is frozenset:
        return core_schema.frozenset_schema(
            items_schema=_build_core_schema(args[0])
            if args
            else core_schema.any_schema()
        )

    if origin is dict:
        return core_schema.dict_schema(
            keys_schema=_build_core_schema(args[0])
            if args
            else core_schema.any_schema(),
            values_schema=_build_core_schema(args[1])
            if len(args) > 1
            else core_schema.any_schema(),
        )

    if origin is tuple:
        return core_schema.tuple_schema(
            items_schema=[_build_core_schema(a) for a in args] if args else []
        )

    if not inspect.isclass(annotation):
        return core_schema.any_schema()

    if _is_grid_type(annotation) or _is_component_type(annotation):
        return core_schema.is_instance_schema(annotation)

    if _is_pydantic_model_type(annotation):
        return core_schema.is_instance_schema(annotation)

    if issubclass(annotation, enum.Enum):
        return core_schema.enum_schema(annotation, list(annotation))

    if hasattr(annotation, "__required_keys__"):
        try:
            hints = get_type_hints(annotation)
        except Exception:
            hints = getattr(annotation, "__annotations__", {})
        return core_schema.typed_dict_schema(
            {
                name: core_schema.typed_dict_field(
                    _build_core_schema(hint),
                    required=name in annotation.__required_keys__,
                )
                for name, hint in hints.items()
            }
        )

    if dataclasses.is_dataclass(annotation):
        try:
            hints = get_type_hints(annotation)
        except Exception:
            hints = {f.name: f.type for f in dataclasses.fields(annotation)}
        dc_fields = [
            core_schema.dataclass_field(
                name=f.name,
                schema=_build_core_schema(hints.get(f.name, Any)),
            )
            for f in dataclasses.fields(annotation)
        ]
        return core_schema.dataclass_schema(
            cls=annotation,
            schema=core_schema.dataclass_args_schema(
                annotation.__name__, dc_fields
            ),
            fields=[f.name for f in dataclasses.fields(annotation)],
        )

    if hasattr(annotation, "__get_pydantic_core_schema__"):
        get_schema = annotation.__get_pydantic_core_schema__
        params = list(inspect.signature(get_schema).parameters)
        if len(params) >= 2:
            return get_schema(
                annotation,
                lambda source, /: core_schema.any_schema(),
            )
        return get_schema(annotation)

    pydantic_schema = getattr(annotation, "__pydantic_core_schema__", None)
    if pydantic_schema is not None:
        if callable(pydantic_schema):
            params = list(inspect.signature(pydantic_schema).parameters)
            if params and params[0] == "cls":
                return pydantic_schema(annotation)
            return pydantic_schema(annotation)
        return pydantic_schema

    return core_schema.is_instance_schema(annotation)


def register_validatable_type(annotation: Any) -> SchemaValidator:
    """Builds and caches a ``SchemaValidator`` for a type annotation.

    Supports primitives, stdlib types, generic containers, ``Literal``,
    ``Union``, enums, ``TypedDict``, dataclasses, and pydantic models.
    Falls back to an isinstance check for unrecognised types.

    Args:
        annotation: The type annotation to build a validator for.

    Returns:
        A cached ``SchemaValidator`` for the given annotation.
    """
    try:
        if annotation not in _SCHEMA_VALIDATOR_CACHE:
            _SCHEMA_VALIDATOR_CACHE[annotation] = SchemaValidator(
                schema=_build_core_schema(annotation)
            )
        return _SCHEMA_VALIDATOR_CACHE[annotation]
    except TypeError:
        return SchemaValidator(schema=_build_core_schema(annotation))


def validate_type(value: Any, annotation: Any) -> Any:
    """Validates a value against a type annotation using ``pydantic_core``.

    Args:
        value: The value to validate.
        annotation: The type annotation to validate against.

    Returns:
        The validated (and coerced, where applicable) value.

    Raises:
        ValidationError: If ``value`` does not satisfy ``annotation``.
    """
    return register_validatable_type(annotation).validate_python(value)


__all__ = (
    "layout_field_annotation",
    "validate_type",
)
