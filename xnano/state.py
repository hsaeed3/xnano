"""
xnano.state

Typed terminal state, stored in the core state store.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import textwrap
import types
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

import xnano_core as _core
from xnano.errors import TerminalError
from xnano_core import JSONSchema, JSONValue

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

StateFieldT = TypeVar('StateFieldT')
StateRootT = TypeVar('StateRootT')


class StateProxy:
    """
    Attribute reads and writes for a terminal's dataclass state.

    Attributes:
        <field>: Every field of the state dataclass, read and written through the
            terminal's state store.
    """

    _store: _core.TerminalStateStore
    _request_frame: Callable[[], None]

    def __init__(
        self, store: _core.TerminalStateStore, request_frame: Callable[[], None]
    ) -> None:
        """
        Wrap a state store.

        Args:
            store: The terminal's state store.
            request_frame: Called after each write, so a frame follows it.
        """
        object.__setattr__(self, '_store', store)
        object.__setattr__(self, '_request_frame', request_frame)

    def __getattr__(self, name: str) -> JSONValue:
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            return self._store.reference((name,)).get()
        except Exception as error:
            raise AttributeError(
                f"{name} is not a field of this terminal's state. Read a field that was "
                f'declared on the dataclass passed to open(state=...).'
            ) from error

    def __setattr__(self, name: str, value: JSONValue) -> None:
        try:
            self._store.reference((name,)).set(value)
        except _core.TerminalStateValidationError as error:
            raise TerminalError(
                f'Could not set state.{name} to {value!r}: {error}. Use a value the field '
                f'accepts.'
            ) from error
        self._request_frame()


def prepare_state(instance: DataclassInstance) -> _core.TerminalStateStore:
    """Build a store from a dataclass instance."""
    if not dataclasses.is_dataclass(instance) or isinstance(instance, type):
        raise TypeError(
            f'{instance!r} is not a state dataclass. Pass an instance of a dataclass, '
            f'such as open(state=Settings()).'
        )
    try:
        schema = _core.TerminalStateSchema.compile(_schema(type(instance)))
    except TypeError as error:
        raise TerminalError(str(error)) from error
    return _core.TerminalStateStore(dataclasses.asdict(instance), schema=schema)


def bind_proxy(
    store: _core.TerminalStateStore, request_frame: Callable[[], None]
) -> StateProxy:
    """
    Return a proxy whose reads and writes go through ``store``.

    Args:
        store: The state store.
        request_frame: Called after each write, so a frame follows it.
    """
    return StateProxy(store, request_frame)


def reference_for(
    store: _core.TerminalStateStore,
    reader: Callable[[StateRootT], StateFieldT],
) -> _core.StateReference[StateFieldT]:
    """
    Return the state branch a ``lambda state: state.field`` reads.

    Args:
        store: The state store.
        reader: A function that reads one field of the state.
    """
    return cast(
        '_core.StateReference[StateFieldT]', store.reference(_attribute_path(reader))
    )


def _schema(kind: type[DataclassInstance]) -> JSONSchema:
    hints = get_type_hints(kind)
    properties = {}
    for field in dataclasses.fields(kind):
        properties[field.name] = _json_type(hints.get(field.name, field.type), field.name)
    return {'type': 'object', 'properties': properties, 'additionalProperties': False}


def _json_type(annotation: object, field_name: str) -> JSONSchema:
    if annotation is int:
        return {'type': 'integer'}
    if annotation is float:
        return {'type': 'number'}
    if annotation is bool:
        return {'type': 'boolean'}
    if annotation is str:
        return {'type': 'string'}
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        arguments = [item for item in get_args(annotation) if item is not type(None)]
        if len(arguments) == 1 and type(None) in get_args(annotation):
            return {'anyOf': [_json_type(arguments[0], field_name), {'type': 'null'}]}
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return _schema(annotation)
    raise TypeError(
        f'The state field {field_name} has type {annotation!r}, which cannot be stored. '
        f'Use int, float, bool, str, None, or a nested dataclass.'
    )


def _attribute_path(reader: Callable[..., object]) -> tuple[str, ...]:
    try:
        source = inspect.getsource(reader)
        tree = ast.parse(textwrap.dedent(source))
    except (OSError, SyntaxError) as error:
        raise TypeError(
            'ref() needs a function or lambda that reads fields, such as '
            'lambda state: state.volume.'
        ) from error
    lambdas = [node for node in ast.walk(tree) if isinstance(node, ast.Lambda)]
    node = lambdas[-1].body if lambdas else None
    if node is None:
        functions = [item for item in ast.walk(tree) if isinstance(item, ast.FunctionDef)]
        if functions and isinstance(functions[-1].body[-1], ast.Return):
            node = functions[-1].body[-1].value
    names: list[str] = []
    while isinstance(node, ast.Attribute):
        names.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name) or not names:
        raise TypeError(
            'ref() could not read a field path from that function. Write '
            'lambda state: state.volume, or lambda state: state.player.x.'
        )
    return tuple(reversed(names))
