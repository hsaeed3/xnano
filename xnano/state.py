"""
xnano.state

The state of a canvas, a placement and a hook, stored in the core state store.
"""

from __future__ import annotations

import ast
import dataclasses
import functools
import inspect
import textwrap
import threading
import types
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from typing import (
    TYPE_CHECKING,
    Final,
    Protocol,
    TypeAlias,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

import xnano_core as _core
from xnano._values import DepsT, StateT
from xnano.errors import TerminalError
from xnano_core import JSONSchema, JSONValue

if TYPE_CHECKING:
    from _typeshed import DataclassInstance
    from typing_extensions import Self

    from xnano._hooks import HookHandle
    from xnano.canvas import Canvas

StateFieldT = TypeVar('StateFieldT')
StateRootT = TypeVar('StateRootT')

StatePath: TypeAlias = tuple[str | int, ...]
"""A path in the state store: object keys and array indexes, outermost first."""

_RESERVED_ROOT_KEY: Final = 'xnano'
_RESERVED_FIELD_NAMES: Final = frozenset({_RESERVED_ROOT_KEY, 'get', 'push'})
_NAMESPACE_KEY_LIMIT: Final = 64
_MISSING: Final = object()


@functools.lru_cache(maxsize=2048)
def parse_path(path: str) -> StatePath:
    """
    Split a dotted state path into the keys and indexes it names.

    Args:
        path: Parts joined by dots, such as ``'player.score'`` or ``'items.0.name'``. A part
            made only of digits is an array index. ``''`` names the whole namespace.

    Raises:
        ValueError: ``path`` is not a string or has an empty part.
    """
    if not isinstance(path, str):
        raise ValueError(
            f'A state path must be a string such as "player.score", but was {path!r}.'
        )
    if not path:
        return ()
    parsed: list[str | int] = []
    for part in path.split('.'):
        if not part:
            raise ValueError(
                f'The state path {path!r} has an empty part. Join the parts with single '
                f"dots, such as 'player.score' or 'items.0.name'."
            )
        parsed.append(int(part) if part.isascii() and part.isdigit() else part)
    return tuple(parsed)


def dotted(path: StatePath) -> str:
    """Write a state path the way ``get`` and ``push`` take it."""
    return '.'.join(str(part) for part in path)


class StateNamespace:
    """
    A branch of a canvas's state that hooks and your code read with ``get`` and write with ``push``.

    A canvas has one state tree. ``canvas.state`` (and ``context.root.state``) is its root,
    ``placement.state`` (and ``context.buffer.state``) is a branch that belongs to one placement,
    and ``context.plugin.state`` is a branch that belongs to one hook. Each is an independent
    namespace, so two hooks can both keep a ``'count'`` without meeting.

    Paths are dotted: ``'player.score'`` is the ``score`` of ``player``, and a part made only of
    digits is an index into a list (``'items.0.name'``). ``''`` is the namespace itself. Keep
    small values here, such as numbers, flags, names and short lists; the state is not a place
    for per-cell data.

    Inside a hook, a read sees the state as it was when the hook started plus whatever the hook
    pushed, and every push is saved together when the hook returns. A hook declared with
    ``on='state'`` runs again when a path it read changes; other hooks do not.

    On the root of a canvas created with ``new(state=Settings())``, the fields of the dataclass
    are also attributes with their declared types, and a write is checked against the field's
    type. A field that holds a nested dataclass reads as a new instance of that dataclass, so
    changing it changes nothing: assign the field or push a path to save a change. A whole
    number written to a ``float`` field is stored and read as a ``float``.

    Attributes:
        <field>: Every field of the state dataclass, on the root namespace only.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            canvas.state.push('player', {'name': 'Ada'})
            canvas.state.push('player.score', 3)
            assert canvas.state.get('player.score') == 3
            assert canvas.state.get('player.lives', default=0) == 0

            @canvas.hook(on='key')
            def count(context: xnano.context.Context) -> None:
                state = context.root.state
                state.push('player.score', state.get('player.score') + 1)
        ```
    """

    __slots__ = ('_base', '_canvas', '_fields', '_is_removed')

    _canvas: Canvas[object, object]
    _base: StatePath
    _fields: Mapping[str, object]
    _is_removed: bool

    def __init__(
        self,
        canvas: Canvas[object, object],
        base: StatePath,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """
        Create a namespace. Use ``canvas.state``, ``placement.state`` or ``context.plugin.state``.

        Args:
            canvas: The root canvas that owns the state store.
            base: Where the namespace starts in the store.
            fields: The declared type of every state dataclass field by name, for the root
                namespace.
        """
        object.__setattr__(self, '_canvas', canvas)
        object.__setattr__(self, '_base', base)
        object.__setattr__(self, '_fields', {} if fields is None else fields)
        object.__setattr__(self, '_is_removed', False)

    def get(self, path: str, default: JSONValue = None) -> JSONValue:
        """
        Read the value at ``path``.

        Args:
            path: A dotted path such as ``'player.score'``, or ``''`` for the whole namespace.
            default: What to return when nothing is stored at ``path``.

        Raises:
            ValueError: ``path`` is malformed.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                canvas.state.push('level', 4)
                assert canvas.state.get('level') == 4
                assert canvas.state.get('player', default='nobody') == 'nobody'
            ```
        """
        parsed = parse_path(path)
        base = self._base
        absolute = base + parsed
        if not base:
            if parsed[:1] == (_RESERVED_ROOT_KEY,):
                raise ValueError(_reserved_message(path))
            if not parsed:
                value = read_state(self._canvas, absolute, default)
                if isinstance(value, dict):
                    return {
                        key: item
                        for key, item in value.items()
                        if key != _RESERVED_ROOT_KEY
                    }
                return value
        return read_state(self._canvas, absolute, default)

    def push(self, path: str, value: JSONValue) -> None:
        """
        Write ``value`` at ``path``, creating the objects on the way.

        A name at the root that is not a declared field is added as a new value, so check the
        spelling of a root path. Inside a declared object, a name that is not one of its fields
        is refused.

        Inside a hook the write is saved when the hook returns; elsewhere it is saved at once.
        The canvas draws a frame afterwards.

        Args:
            path: A dotted path such as ``'player.score'``. ``''`` replaces a whole placement or
                hook namespace with an object, and is not allowed on the root.
            value: A number, string, flag, ``None``, list or dictionary of those.

        Raises:
            ValueError: ``path`` is malformed or names the reserved ``xnano`` key.
            TerminalError: The value does not fit a declared field, or the namespace belongs
                to a placement or hook that was removed.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                canvas.state.push('score', 1)
                canvas.state.push('score', 2)
                assert canvas.state.get('score') == 2
                canvas.state.push('player', {'name': 'Ada'})
                canvas.state.push('player.score', 5)
                assert canvas.state.get('player') == {'name': 'Ada', 'score': 5}
            ```
        """
        parsed = parse_path(path)
        base = self._base
        if not base:
            if parsed[:1] == (_RESERVED_ROOT_KEY,):
                raise ValueError(_reserved_message(path))
            if not parsed:
                raise ValueError(
                    "push('') would replace the whole root state. Push one path at a "
                    "time, such as push('score', 1)."
                )
        elif not parsed and not isinstance(value, dict):
            raise ValueError(
                f"push('') replaces the whole namespace and needs an object, but was given "
                f'{value!r}. Push a dictionary, or push one path such as push("score", 1).'
            )
        if self._is_removed:
            raise TerminalError(
                f'Could not push {path!r}: this state belongs to a placement or hook that '
                f'was removed. Push to the state of one that is still on the canvas.'
            )
        write_state(self._canvas, base + parsed, self._declared_form(parsed, value))

    def _declared_form(self, parsed: StatePath, value: JSONValue) -> JSONValue:
        """``value`` as the declared type of the field at ``parsed`` stores it."""
        if self._base or not parsed or not isinstance(parsed[0], str):
            return value
        annotation: object = self._fields.get(parsed[0])
        for part in parsed[1:]:
            annotation = _member_annotation(annotation, part)
        return cast('JSONValue', _stored_form(value, annotation))

    def __getattr__(self, name: str) -> JSONValue:
        if name not in self._fields:
            raise AttributeError(self._unknown_field_message(name, 'Read', 'get'))
        return cast(
            'JSONValue',
            _declared_value(read_state(self._canvas, (name,), None), self._fields[name]),
        )

    def _unknown_field_message(self, name: str, verb: str, method: str) -> str:
        """Explain that ``name`` is not an attribute of this namespace."""
        if not self._base:
            return (
                f"{name} is not a field of this canvas's state. {verb} a field declared on "
                f'the dataclass passed to xnano.new(state=...), or use {method}({name!r}'
                f'{", value" if method == "push" else ""}) for a path.'
            )
        return (
            f'{name} is not an attribute of this state, which has no declared fields: only '
            f"the canvas's own state does. Use {method}({name!r}"
            f'{", value" if method == "push" else ""}) with a path instead.'
        )

    def __setattr__(self, name: str, value: JSONValue) -> None:
        if name not in self._fields:
            raise TerminalError(self._unknown_field_message(name, 'Assign', 'push'))
        write_state(self._canvas, (name,), self._declared_form((name,), value))

    def __repr__(self) -> str:
        return f'StateNamespace(path={dotted(self._base)!r})'

    def _remove(self) -> None:
        """Delete this namespace's branch of the store; later pushes raise."""
        object.__setattr__(self, '_is_removed', True)
        self._canvas._remove_state_branch(self._base)


class _StateAccessor:
    """
    The declared type of ``Canvas.state``: the dataclass given to ``new(state=...)``, or a
    [`StateNamespace`][xnano.state.StateNamespace] when the canvas has none.
    """

    @overload
    def __get__(self, instance: None, owner: type) -> Self: ...
    @overload
    def __get__(self, instance: Canvas[DepsT, None], owner: type) -> StateNamespace: ...
    @overload
    def __get__(self, instance: Canvas[DepsT, object], owner: type) -> StateNamespace: ...
    @overload
    def __get__(self, instance: Canvas[DepsT, StateT], owner: type) -> StateT: ...
    def __get__(
        self, instance: Canvas[DepsT, StateT] | None, owner: type
    ) -> Self | StateNamespace | StateT:
        if instance is None:
            return self
        canvas = instance._canvas
        namespace = canvas._state_namespace
        if namespace is None:
            namespace = canvas._create_root_namespace()
        return cast('StateNamespace | StateT', namespace)


class _HookRun:
    """
    One call of a hook, as far as state is concerned: what it read and what it pushed.

    A hook reads from a snapshot taken at its first read, sees its own pushes, and its pushes
    are committed in one transaction when it returns.
    """

    __slots__ = ('handle', 'is_active', 'pending', 'reads', 'snapshot', 'thread', 'track')

    def __init__(self, track: bool) -> None:
        """
        Prepare the record of one call.

        Args:
            track: Whether to record the paths the call reads.
        """
        self.track = track
        self.handle: HookHandle[object, object] | None = None
        self.is_active = False
        self.thread = 0
        self.snapshot: _core.TerminalStateSnapshot | None = None
        self.pending: dict[StatePath, JSONValue] = {}
        self.reads: set[StatePath] = set()

    def begin(self) -> None:
        """Start a call on the current thread."""
        self.is_active = True
        self.thread = threading.get_ident()

    def discard(self) -> None:
        """End a call that raised: nothing is saved and nothing was read."""
        self.is_active = False
        self.snapshot = None
        if self.pending:
            self.pending = {}
        if self.reads:
            self.reads = set()

    def read(
        self, canvas: Canvas[object, object], path: StatePath, default: JSONValue
    ) -> JSONValue:
        """Read ``path`` as the hook sees it: the snapshot plus the hook's own pushes."""
        if self.track:
            self.reads.add(path)
        pending = self.pending
        overlays: list[tuple[StatePath, JSONValue]] | None = None
        if pending:
            if path in pending:
                return pending[path]
            length = len(path)
            for key, value in pending.items():
                size = len(key)
                if size < length and path[:size] == key:
                    found = _descend(value, path[size:])
                    return default if found is _MISSING else cast('JSONValue', found)
                if size > length and key[:length] == path:
                    if overlays is None:
                        overlays = []
                    overlays.append((key[length:], value))
        snapshot = self.snapshot
        if snapshot is None:
            store = canvas._state_store
            assert store is not None
            snapshot = self.snapshot = store.snapshot()
        try:
            stored = snapshot.at(path).to_value()
        except _core.TerminalStateValidationError:
            if overlays is None:
                return default
            stored = {}
        if overlays is not None:
            for rest, value in overlays:
                stored = _with_value(stored, rest, value)
        return stored

    def push(self, path: StatePath, value: JSONValue) -> None:
        """Stage ``value`` at ``path``; the later write to a path wins over an earlier one."""
        pending = self.pending
        if pending:
            length = len(path)
            for key in list(pending):
                size = len(key)
                if size < length:
                    if path[:size] == key:
                        pending[key] = _with_value(pending[key], path[size:], value)
                        return
                elif size > length and key[:length] == path:
                    del pending[key]
        pending[path] = value


class _StateFollowers:
    """
    The readers that run again when a state path they read changes.

    A follower is anything with ``_own_revisions`` (a deque of the store revisions it
    committed itself, which it ignores) and ``_state_followed(change)``. A follower that has
    not read anything yet follows every change.
    """

    def __init__(self) -> None:
        """Start with no followers."""
        self._everything: set[StateFollower] = set()
        self._paths: dict[StateFollower, frozenset[StatePath]] = {}
        self._exact: dict[StatePath, set[StateFollower]] = {}
        self._prefixes: dict[StatePath, set[StateFollower]] = {}

    def follow(self, follower: StateFollower, paths: frozenset[StatePath] | None) -> None:
        """Make ``follower`` follow ``paths``, or every change when ``paths`` is ``None``."""
        self.unfollow(follower)
        if paths is None:
            self._everything.add(follower)
            return
        self._paths[follower] = paths
        for path in paths:
            self._exact.setdefault(path, set()).add(follower)
            for length in range(len(path) + 1):
                self._prefixes.setdefault(path[:length], set()).add(follower)

    def unfollow(self, follower: StateFollower) -> None:
        """Stop following."""
        self._everything.discard(follower)
        paths = self._paths.pop(follower, None)
        if paths is None:
            return
        for path in paths:
            self._discard(self._exact, path, follower)
            for length in range(len(path) + 1):
                self._discard(self._prefixes, path[:length], follower)

    def affected(self, changed: Iterable[StatePath]) -> set[StateFollower]:
        """The followers that read a path inside, or around, one of the ``changed`` paths."""
        result = set(self._everything)
        exact = self._exact
        prefixes = self._prefixes
        if not (exact or prefixes):
            return result
        for path in changed:
            found = prefixes.get(path)
            if found:
                result |= found
            for length in range(len(path) + 1):
                found = exact.get(path[:length])
                if found:
                    result |= found
        return result

    @staticmethod
    def _discard(
        index: dict[StatePath, set[StateFollower]],
        path: StatePath,
        follower: StateFollower,
    ) -> None:
        followers = index.get(path)
        if followers is None:
            return
        followers.discard(follower)
        if not followers:
            del index[path]


class StateFollower(Protocol):
    """What the canvas needs from a hook or component that follows state paths."""

    _own_revisions: deque[int]

    def _state_followed(self, change: _core.TerminalStateChange) -> None:
        """Run again because a path that was read changed."""
        ...

    def _state_loop(
        self, change: _core.TerminalStateChange, others: list[StateFollower]
    ) -> None:
        """Report that this follower and ``others`` keep changing each other's state."""
        ...


def read_state(
    canvas: Canvas[object, object], path: StatePath, default: JSONValue
) -> JSONValue:
    """Read ``path`` inside a running hook (with its pushes) or straight from the store."""
    run = canvas._active_run
    if run is not None and run.thread == threading.get_ident():
        return run.read(canvas, path, default)
    store = canvas._state_store
    assert store is not None
    try:
        return store.snapshot(path).to_value()
    except _core.TerminalStateValidationError:
        return default


def write_state(
    canvas: Canvas[object, object], path: StatePath, value: JSONValue
) -> None:
    """Stage ``value`` in the running hook, or save it at once."""
    run = canvas._active_run
    if run is not None and run.thread == threading.get_ident():
        run.push(path, value)
        return
    canvas._commit_state({path: value})


def commit_pending(
    store: _core.TerminalStateStore, pending: dict[StatePath, JSONValue]
) -> _core.TerminalStateChange | None:
    """
    Save pushed values in one transaction.

    Values pushed into a placement's or hook's namespace are merged into that namespace's
    object and set once, so the cost of a commit does not grow with the depth of the path.
    """
    transaction = store.transaction()
    try:
        grouped: dict[StatePath, list[tuple[StatePath, JSONValue]]] | None = None
        for path, value in pending.items():
            if path[0] == _RESERVED_ROOT_KEY and len(path) >= 3:
                if grouped is None:
                    grouped = {}
                grouped.setdefault(path[:3], []).append((path[3:], value))
            else:
                _stage(transaction, path, value)
        if grouped is not None:
            for base, entries in grouped.items():
                _stage_namespace(store, transaction, base, entries)
        return transaction.commit()
    except _core.TerminalStateValidationError as error:
        raise _push_error(pending, error) from error


def create_branch(store: _core.TerminalStateStore, base: StatePath) -> int | None:
    """Create the empty object of a placement or hook namespace; return the revision."""
    transaction = store.transaction()
    transaction.set(base, {})
    change = transaction.commit()
    return None if change is None else change.revision


def remove_branch(store: _core.TerminalStateStore, base: StatePath) -> int | None:
    """Delete a namespace's object when it exists; return the revision."""
    if not store.snapshot().exists(base):
        return None
    transaction = store.transaction()
    transaction.remove(base)
    change = transaction.commit()
    return None if change is None else change.revision


def _stage(
    transaction: _core.TerminalStateTransaction, path: StatePath, value: JSONValue
) -> None:
    if len(path) > 1:
        snapshot = transaction.snapshot()
        if not snapshot.exists(path[:-1]):
            for length in range(1, len(path)):
                prefix = path[:length]
                if not snapshot.exists(prefix):
                    if isinstance(path[length], int):
                        break
                    transaction.set(prefix, {})
    transaction.set(path, value)


def _stage_namespace(
    store: _core.TerminalStateStore,
    transaction: _core.TerminalStateTransaction,
    base: StatePath,
    entries: list[tuple[StatePath, JSONValue]],
) -> None:
    try:
        current = store.snapshot(base).to_value()
    except _core.TerminalStateValidationError:
        current = {}
    if not isinstance(current, dict):
        current = {}
    merged: JSONValue = current
    if len(current) > _NAMESPACE_KEY_LIMIT:
        for rest, value in entries:
            _stage(transaction, base + rest, value)
        return
    for rest, value in entries:
        if len(rest) == 1 and isinstance(rest[0], str):
            current[rest[0]] = value
        else:
            merged = _with_value(merged, rest, value)
            current = merged if isinstance(merged, dict) else {}
    transaction.set(base, merged)


def _with_value(container: object, rest: StatePath, value: JSONValue) -> JSONValue:
    """A copy of ``container`` with ``value`` stored at ``rest``; the original is untouched."""
    if not rest:
        return value
    head = rest[0]
    if isinstance(head, int):
        if not isinstance(container, list) or head >= len(container):
            raise TerminalError(
                f'Could not push to index {head}: the list there is {container!r}. Push '
                f'inside a list that has that index, or push the whole list.'
            )
        copied_list = list(container)
        copied_list[head] = _with_value(container[head], rest[1:], value)
        return cast('JSONValue', copied_list)
    if container is None or container is _MISSING:
        container = {}
    if not isinstance(container, dict):
        raise TerminalError(
            f'Could not push inside {head!r}: the value there is {container!r}, which has '
            f'no keys. Push the whole value, or push to a path whose parents are objects.'
        )
    copied = dict(container)
    copied[head] = _with_value(copied.get(head), rest[1:], value)
    return cast('JSONValue', copied)


def _descend(value: object, rest: StatePath) -> object:
    for part in rest:
        if isinstance(part, int):
            if not isinstance(value, list) or part >= len(value):
                return _MISSING
            value = value[part]
        else:
            if not isinstance(value, dict) or part not in value:
                return _MISSING
            value = value[part]
    return value


def _reserved_message(path: str) -> str:
    return (
        f"The state path {path!r} starts with 'xnano', which xnano keeps for itself. Choose "
        f'another name for your value.'
    )


def _push_error(
    pending: dict[StatePath, JSONValue], error: BaseException
) -> TerminalError:
    if len(pending) == 1:
        path, value = next(iter(pending.items()))
        return TerminalError(
            f'Could not set {dotted(path)!r} to {value!r}: {error}. Use a value that matches '
            f'the type the field declares.'
        )
    names = ', '.join(repr(dotted(path)) for path in pending)
    return TerminalError(
        f'Could not save the values pushed to {names}: {error}. Nothing was saved. Use '
        f'values the fields accept.'
    )


def _type_hints(kind: type) -> dict[str, object]:
    """The resolved annotations of a state dataclass, with a teaching error for a local type."""
    try:
        return get_type_hints(kind)
    except NameError as error:
        raise TerminalError(
            f'The types of the fields of {kind.__name__} could not be resolved: {error}. '
            f'xnano resolves field types by name, so define the state dataclasses at the '
            f'top level of a module (not inside a function), or remove '
            f'`from __future__ import annotations` from that module.'
        ) from error


def state_field_types(instance: DataclassInstance) -> dict[str, object]:
    """The declared type of every field of a state dataclass, by field name."""
    hints = _type_hints(type(instance))
    return {
        field.name: hints.get(field.name, field.type)
        for field in dataclasses.fields(instance)
    }


def _dataclass_of(annotation: object) -> type[DataclassInstance] | None:
    """The dataclass an annotation names, also inside ``Optional``, or ``None``."""
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return cast('type[DataclassInstance]', annotation)
    if get_origin(annotation) in (Union, types.UnionType):
        members = [item for item in get_args(annotation) if item is not type(None)]
        if len(members) == 1:
            return _dataclass_of(members[0])
    return None


def _is_float(annotation: object) -> bool:
    """Whether an annotation is ``float``, also inside ``Optional``."""
    if annotation is float:
        return True
    if get_origin(annotation) in (Union, types.UnionType):
        members = [item for item in get_args(annotation) if item is not type(None)]
        return len(members) == 1 and members[0] is float
    return False


def _member_annotation(annotation: object, part: str | int) -> object:
    """The declared type of the field ``part`` of a dataclass annotation, or ``None``."""
    kind = _dataclass_of(annotation)
    if kind is None or not isinstance(part, str):
        return None
    return _type_hints(kind).get(part)


def _stored_form(value: object, annotation: object) -> object:
    """``value`` as a declared type keeps it: a dataclass as a dictionary, a number as a float."""
    kind = _dataclass_of(annotation)
    if kind is not None:
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            value = {
                field.name: getattr(value, field.name)
                for field in dataclasses.fields(value)
            }
        if isinstance(value, dict):
            hints = _type_hints(kind)
            return {
                key: _stored_form(item, hints.get(key)) for key, item in value.items()
            }
        return value
    if _is_float(annotation) and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    return value


def _declared_value(value: object, annotation: object) -> object:
    """A stored ``value`` as its declared type: a nested dataclass is rebuilt from its fields."""
    kind = _dataclass_of(annotation)
    if kind is not None:
        if not isinstance(value, dict):
            return value
        hints = _type_hints(kind)
        arguments = {
            field.name: _declared_value(value[field.name], hints.get(field.name))
            for field in dataclasses.fields(kind)
            if field.init and field.name in value
        }
        return kind(**arguments)
    if _is_float(annotation) and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    return value


def prepare_state(
    instance: DataclassInstance | None, free: Mapping[str, JSONValue] | None = None
) -> _core.TerminalStateStore:
    """
    Build the state store of a canvas.

    Args:
        instance: The state dataclass instance, or ``None`` for a store of free paths only.
        free: Values of the earlier store to keep, for a store that replaces it: its free
            paths and the branches xnano keeps for placements and hooks.
    """
    value: dict[str, JSONValue] = {}
    if instance is None:
        schema = _root_schema(None)
    else:
        if not dataclasses.is_dataclass(instance) or isinstance(instance, type):
            raise TypeError(
                f'{instance!r} is not a state dataclass. Pass an instance of a dataclass, '
                f'such as xnano.new(state=Settings()).'
            )
        reserved = sorted(_RESERVED_FIELD_NAMES & state_field_types(instance).keys())
        if reserved:
            raise TerminalError(
                f'The state dataclass {type(instance).__name__} has a field named '
                f'{reserved[0]!r}, which xnano uses for its own state. Rename the field.'
            )
        try:
            schema = _root_schema(type(instance))
        except TypeError as error:
            raise TerminalError(str(error)) from error
        value.update(dataclasses.asdict(instance))
    if free:
        for key, item in free.items():
            value.setdefault(key, item)
    value.setdefault(_RESERVED_ROOT_KEY, {'buffers': {}, 'plugins': {}})
    return _core.TerminalStateStore(
        value, schema=_core.TerminalStateSchema.compile(schema)
    )


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


def _root_schema(kind: type[DataclassInstance] | None) -> JSONSchema:
    """The schema of the whole store: the dataclass fields, free paths and xnano's own branch."""
    properties: dict[str, JSONValue] = {}
    if kind is not None:
        fields = _schema(kind)['properties']
        assert isinstance(fields, dict)
        properties.update(fields)
    properties[_RESERVED_ROOT_KEY] = {
        'type': 'object',
        'properties': {'buffers': {'type': 'object'}, 'plugins': {'type': 'object'}},
        'additionalProperties': False,
    }
    return {'type': 'object', 'properties': properties, 'additionalProperties': True}


def _schema(kind: type[DataclassInstance]) -> JSONSchema:
    hints = _type_hints(kind)
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
            'state_reference() needs a function or lambda that reads fields, such as '
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
            'state_reference() could not read a field path from that function. Write '
            'lambda state: state.volume, or lambda state: state.player.x.'
        )
    return tuple(reversed(names))
