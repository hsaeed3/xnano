"""
xnano._when

The conditions of a hook: an expression, a function or a string, compiled once.
"""

from __future__ import annotations

import ast
import difflib
import functools
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

import xnano_core as _core
from xnano_core import (
    BufferScope,
    KeyboardScope,
    MouseScope,
    ParentScope,
    RootScope,
    ScrollScope,
)

if TYPE_CHECKING:
    from xnano.context import Context

__all__ = ['CompiledWhen', 'compile_when', 'normalize_chord', 'parse_when']

_KEY_NAMES: Final = (
    *'abcdefghijklmnopqrstuvwxyz0123456789',
    'space',
    'enter',
    'escape',
    'tab',
    'backspace',
    'delete',
    'insert',
    'home',
    'end',
    'page_up',
    'page_down',
    'up',
    'down',
    'left',
    'right',
    *(f'f{number}' for number in range(1, 13)),
)
"""The key names that [`KeyName`][xnano.types.KeyName] lists."""

_NAMED_KEYS: Final = frozenset(
    {
        *_KEY_NAMES,
        *(f'f{number}' for number in range(13, 25)),
        'caps_lock',
        'scroll_lock',
        'num_lock',
        'print_screen',
        'pause',
        'menu',
        'null',
    }
)
"""Every key with a name of its own; any other key is a single character."""

_MODIFIER_TEXT: Final = (
    ('control', 'ctrl'),
    ('alt', 'alt'),
    ('shift', 'shift'),
    ('super', 'super'),
    ('meta', 'meta'),
    ('hyper', 'hyper'),
)

_MEMBERS: Final[dict[str, tuple[str, ...]]] = {
    'keyboard': ('key', 'kind', 'chord'),
    'mouse': ('position', 'button', 'kind', 'is_down'),
    'scroll': ('x', 'y'),
    'buffer': ('x', 'y', 'position', 'width', 'height', 'size', 'region'),
    'parent': ('width', 'height', 'size'),
    'root': ('width', 'height', 'time', 'delta', 'fps'),
}
"""Every member a ``when`` string may read from a scope."""

_PARTS: Final[dict[str, tuple[str, ...]]] = {
    'position': ('x', 'y'),
    'size': ('width', 'height'),
    'region': ('x', 'y', 'width', 'height', 'right', 'bottom'),
}
"""The parts of a point, a size and a rectangle that a ``when`` string may read."""

_CHOICES: Final[dict[tuple[str, str], tuple[str, ...]]] = {
    ('keyboard', 'kind'): ('press', 'repeat', 'release'),
    ('mouse', 'kind'): ('press', 'release', 'drag', 'move'),
    ('mouse', 'button'): ('left', 'right', 'middle'),
}
"""The words a text member can be compared with."""

_INPUT_SCOPES: Final = frozenset({'keyboard', 'mouse', 'scroll'})

_NATIVE_SCOPES: Final[dict[str, object]] = {
    'keyboard': KeyboardScope,
    'mouse': MouseScope,
    'scroll': ScrollScope,
    'buffer': BufferScope,
    'parent': ParentScope,
    'root': RootScope,
    'time': RootScope.time,
}


@dataclass(frozen=True, slots=True)
class CompiledWhen:
    """
    A hook's condition after it was compiled at registration.

    Attributes:
        expression: The native condition, evaluated by the runtime before Python is called.
        predicate: The Python condition, called with the context after the native one passed.
        reads: The scopes a string condition mentions.
        is_opaque: Whether the condition is an expression or a function, whose reads cannot be
            listed.
        mentions_release: Whether the condition tests for a key release.
    """

    expression: _core.Expression[bool] | None
    predicate: Callable[[Context[object, object]], bool] | None
    reads: frozenset[str]
    is_opaque: bool
    mentions_release: bool


NO_CONDITION: Final = CompiledWhen(None, None, frozenset(), False, False)


@functools.lru_cache(maxsize=1024)
def normalize_chord(entry: str) -> str:
    """
    Write a key or chord the way the runtime reports it.

    Args:
        entry: A key name or chord such as ``'q'``, ``'Esc'`` or ``'Ctrl+Shift+S'``.

    Returns:
        The canonical text: modifiers in the order ``ctrl``, ``alt``, ``shift``, ``super``, then
        the lowercase key name.

    Raises:
        ValueError: ``entry`` is not a key, with the closest valid names.
    """
    try:
        key = _core.Event.key_press(entry).key
    except ValueError as error:
        raise ValueError(_unknown_key_message(entry)) from error
    assert key is not None
    if len(key.key) != 1 and key.key not in _NAMED_KEYS:
        raise ValueError(_unknown_key_message(entry))
    parts = [text for name, text in _MODIFIER_TEXT if name in key.modifiers]
    parts.append(key.key)
    return '+'.join(parts)


def _unknown_key_message(entry: str) -> str:
    close = difflib.get_close_matches(entry.lower(), _KEY_NAMES, n=3)
    hint = f' Did you mean {" or ".join(repr(name) for name in close)}?' if close else ''
    return (
        f'{entry!r} is not a key name.{hint} Use a name from xnano.types.KeyName such as '
        f"'q', 'enter' or 'page_up', or a chord such as 'ctrl+s'."
    )


def _key_name(entry: str) -> str:
    """The name of a single key, which has no modifiers, in the runtime's spelling."""
    chord = normalize_chord(entry)
    if '+' in chord and chord != '+' and not chord.endswith('++'):
        raise ValueError(
            f'{entry!r} is a key with modifiers, but keyboard.key holds the key alone. '
            f"Compare keyboard.chord instead: keyboard.chord == '{chord}'."
        )
    return chord


def _fail(text: str, node: ast.AST | None, problem: str) -> ValueError:
    column = getattr(node, 'col_offset', None)
    where = '' if column is None else f' at column {column}'
    pointer = ''
    if column is not None:
        pointer = f'\n  {text}\n  {" " * column}^'
    return ValueError(f'The condition {text!r} has a problem{where}: {problem}{pointer}')


class _Parser:
    """Check a condition string and turn it into an expression, or a function of the context."""

    def __init__(self, text: str) -> None:
        """Parse and check ``text``, remembering the scopes it reads."""
        self.text = text
        self.reads: set[str] = set()
        self.mentions_release = False
        self.uses_deps = False
        self.tree = self._parse()

    def _parse(self) -> ast.expr:
        try:
            tree = ast.parse(self.text.strip(), mode='eval')
        except SyntaxError as error:
            raise ValueError(
                f'The condition {self.text!r} is not valid: {error.msg}. Write it like an '
                f'expression, such as "keyboard.key == \'q\' and not mouse.is_down".'
            ) from error
        return self._check(tree.body)

    # -- checking ------------------------------------------------------------------------

    def _check(self, node: ast.expr) -> ast.expr:
        if isinstance(node, ast.BoolOp):
            return ast.copy_location(
                ast.BoolOp(
                    op=node.op, values=[self._check(value) for value in node.values]
                ),
                node,
            )
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, (ast.Not, ast.USub)):
                raise _fail(self.text, node, 'only not and a minus sign are allowed')
            return ast.copy_location(
                ast.UnaryOp(op=node.op, operand=self._check(node.operand)), node
            )
        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                raise _fail(self.text, node, 'only + - * / are allowed')
            return ast.copy_location(
                ast.BinOp(
                    left=self._check(node.left),
                    op=node.op,
                    right=self._check(node.right),
                ),
                node,
            )
        if isinstance(node, ast.Compare):
            return self._check_compare(node)
        if isinstance(node, ast.Constant):
            if node.value is not None and not isinstance(
                node.value, (str, int, float, bool)
            ):
                raise _fail(self.text, node, 'only text, numbers, True, False and None')
            return node
        if isinstance(node, (ast.Tuple, ast.List)):
            return ast.copy_location(
                ast.Tuple(elts=[self._check(item) for item in node.elts], ctx=ast.Load()),
                node,
            )
        if isinstance(node, ast.Name):
            return self._check_name(node)
        if isinstance(node, ast.Attribute):
            return self._check_attribute(node)
        raise _fail(
            self.text,
            node,
            f'{type(node).__name__} is not allowed. The operators are == != < <= > >= in, '
            f'and, or, not and + - * /, and the names are keyboard, mouse, scroll, buffer, '
            f'parent, root, time and deps',
        )

    def _check_name(self, node: ast.Name) -> ast.expr:
        if node.id == 'deps':
            self.uses_deps = True
            self.reads.add('deps')
            return node
        if node.id == 'time':
            self.reads.add('time')
            return node
        if node.id in _MEMBERS:
            # A bare scope is only the left side of a member; _check_attribute handles it.
            raise _fail(
                self.text,
                node,
                f'{node.id} needs a member, such as {node.id}.{_MEMBERS[node.id][0]}',
            )
        if node.id in ('True', 'False', 'None'):
            return node
        known = ', '.join((*_MEMBERS, 'time', 'deps'))
        raise _fail(
            self.text,
            node,
            f'{node.id} is not a name. The names are {known}. Put text in quotes, or '
            f'compare a member with a key or button name, such as keyboard.key == escape',
        )

    def _check_attribute(self, node: ast.Attribute) -> ast.expr:
        chain: list[str] = []
        current: ast.expr = node
        while isinstance(current, ast.Attribute):
            chain.append(current.attr)
            current = current.value
        if not isinstance(current, ast.Name):
            raise _fail(self.text, node, 'only members of the scopes can be read')
        chain.reverse()
        scope = current.id
        if scope == 'deps':
            self.uses_deps = True
            self.reads.add('deps')
            return node
        if scope == 'time':
            raise _fail(
                self.text,
                node,
                'time is a number of seconds and has no members; use root.delta for the time '
                'since the previous frame',
            )
        if scope not in _MEMBERS:
            known = ', '.join((*_MEMBERS, 'time', 'deps'))
            raise _fail(
                self.text, current, f'{scope} is not a name. The names are {known}'
            )
        member = chain[0]
        is_part = len(chain) == 2 and chain[1] in _PARTS.get(member, ())
        if member not in _MEMBERS[scope] or (len(chain) > 1 and not is_part):
            close = difflib.get_close_matches(member, _MEMBERS[scope], n=1)
            hint = f' Did you mean {scope}.{close[0]}?' if close else ''
            raise _fail(
                self.text,
                node,
                f'{scope}.{".".join(chain)} is not a member.{hint} The members of {scope} '
                f'are {", ".join(_MEMBERS[scope])}',
            )
        self.reads.add(scope)
        return node

    def _check_compare(self, node: ast.Compare) -> ast.expr:
        operands = [node.left, *node.comparators]
        checked: list[ast.expr] = []
        for index, operand in enumerate(operands):
            other = operands[index - 1] if index else operands[1]
            checked.append(self._operand(operand, other, node))
        for index, operator in enumerate(node.ops):
            if not isinstance(
                operator,
                (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn),
            ):
                raise _fail(
                    self.text,
                    node,
                    'the comparisons are == != < <= > >= in and not in',
                )
            if isinstance(operator, (ast.Eq, ast.In)):
                pair = (checked[index], checked[index + 1])
                if any(_member_of(side) == ('keyboard', 'kind') for side in pair) and any(
                    _is_release_word(side) for side in pair
                ):
                    self.mentions_release = True
        return ast.copy_location(
            ast.Compare(left=checked[0], ops=node.ops, comparators=checked[1:]), node
        )

    def _operand(self, operand: ast.expr, other: ast.expr, node: ast.Compare) -> ast.expr:
        """Check one side of a comparison, reading bare words and text as key or button names."""
        member = _member_of(other)
        if (
            isinstance(operand, ast.Name)
            and member is not None
            and operand.id not in (*_NATIVE_SCOPES, 'deps', 'True', 'False', 'None')
        ):
            return self._word(operand.id, member, operand)
        if isinstance(operand, ast.Constant) and isinstance(operand.value, str):
            if member is not None:
                return self._word(operand.value, member, operand)
            return operand
        if isinstance(operand, (ast.Tuple, ast.List)):
            if member is None:
                return self._check(operand)
            words = []
            for item in operand.elts:
                if isinstance(item, ast.Name):
                    words.append(self._word(item.id, member, item))
                elif isinstance(item, ast.Constant) and isinstance(item.value, str):
                    words.append(self._word(item.value, member, item))
                else:
                    words.append(self._check(item))
            return ast.copy_location(ast.Tuple(elts=words, ctx=ast.Load()), operand)
        return self._check(operand)

    def _word(self, word: str, member: tuple[str, str], node: ast.expr) -> ast.expr:
        scope, name = member
        try:
            if (scope, name) == ('keyboard', 'key'):
                word = _key_name(word)
            elif (scope, name) == ('keyboard', 'chord'):
                word = normalize_chord(word)
            elif (scope, name) in _CHOICES:
                choices = _CHOICES[scope, name]
                if word not in choices:
                    close = difflib.get_close_matches(word, choices, n=1)
                    hint = f' Did you mean {close[0]!r}?' if close else ''
                    raise ValueError(
                        f'{word!r} is not a {scope} {name}.{hint} The choices are '
                        f'{", ".join(repr(choice) for choice in choices)}.'
                    )
        except ValueError as error:
            raise _fail(self.text, node, str(error)) from error
        return ast.copy_location(ast.Constant(value=word), node)

    # -- building ------------------------------------------------------------------------

    def native(self) -> _core.Expression[bool]:
        """Build the native expression."""
        try:
            result = self._build(self.tree, _NATIVE_SCOPES, is_native=True)
        except TypeError as error:
            raise ValueError(
                f'The condition {self.text!r} cannot be built: {error}'
            ) from error
        if not isinstance(result, _core.Expression):
            raise ValueError(
                f'The condition {self.text!r} is {result!r}, which is not a condition. '
                f'Compare something, such as keyboard.key == "q".'
            )
        return cast('_core.Expression[bool]', result)

    def function(self) -> Callable[[Context[object, object]], bool]:
        """Build the Python function that evaluates the string with a context."""

        def predicate(context: Context[object, object]) -> bool:
            names = _live_names(context)
            return bool(self._build(self.tree, names, is_native=False))

        return predicate

    def _build(
        self, node: ast.expr, names: dict[str, object], *, is_native: bool
    ) -> object:
        build = functools.partial(self._build, names=names, is_native=is_native)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id == 'True':
                return True
            if node.id == 'False':
                return False
            if node.id == 'None':
                return None
            return names[node.id]
        if isinstance(node, ast.Attribute):
            value = build(node.value)
            if value is None and not is_native:
                return None
            return getattr(value, node.attr)
        if isinstance(node, ast.Tuple):
            return tuple(build(item) for item in node.elts)
        if isinstance(node, ast.UnaryOp):
            operand = build(node.operand)
            if operand is None and not is_native and not isinstance(node.op, ast.Not):
                return None
            if isinstance(node.op, ast.Not):
                return ~operand if is_native else not operand  # type: ignore[operator]
            return -operand  # type: ignore[operator]
        if isinstance(node, ast.BinOp):
            left, right = build(node.left), build(node.right)
            if not is_native and (left is None or right is None):
                return None
            if isinstance(node.op, ast.Add):
                return left + right  # type: ignore[operator]
            if isinstance(node.op, ast.Sub):
                return left - right  # type: ignore[operator]
            if isinstance(node.op, ast.Mult):
                return left * right  # type: ignore[operator]
            return left / right  # type: ignore[operator]
        if isinstance(node, ast.BoolOp):
            values = [build(value) for value in node.values]
            if is_native:
                joined = values[0]
                for value in values[1:]:
                    joined = (
                        joined & value  # type: ignore[operator]
                        if isinstance(node.op, ast.And)
                        else joined | value  # type: ignore[operator]
                    )
                return joined
            if isinstance(node.op, ast.And):
                return all(build(value) for value in node.values)
            return any(build(value) for value in node.values)
        if isinstance(node, ast.Compare):
            operands = [build(node.left), *(build(item) for item in node.comparators)]
            results = [
                _compare(
                    operator, operands[index], operands[index + 1], is_native=is_native
                )
                for index, operator in enumerate(node.ops)
            ]
            joined = results[0]
            for result in results[1:]:
                joined = joined & result if is_native else (joined and result)  # type: ignore[operator]
            return joined
        raise AssertionError(f'unchecked node {node!r}')


def _member_of(node: ast.expr) -> tuple[str, str] | None:
    """``('keyboard', 'key')`` for the node ``keyboard.key``, else ``None``."""
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in _MEMBERS
    ):
        return node.value.id, node.attr
    return None


def _is_release_word(node: ast.expr) -> bool:
    """Whether the node is the text ``'release'``, or a tuple that holds it."""
    if isinstance(node, ast.Constant):
        return node.value == 'release'
    if isinstance(node, ast.Tuple):
        return any(_is_release_word(item) for item in node.elts)
    return False


def _compare(
    operator: ast.cmpop, left: object, right: object, *, is_native: bool
) -> object:
    if isinstance(operator, (ast.In, ast.NotIn)):
        if isinstance(right, tuple):
            if is_native:
                found = left == right[0]  # type: ignore[operator]
                for item in right[1:]:
                    found = found | (left == item)  # type: ignore[operator]
            else:
                found = left in right
        elif not is_native and (left is None or right is None):
            found = False
        else:
            found = right.contains(left)  # type: ignore[attr-defined]
        if isinstance(operator, ast.NotIn):
            return ~found if is_native else not found  # type: ignore[operator]
        return found
    if isinstance(operator, ast.Eq):
        return left == right
    if isinstance(operator, ast.NotEq):
        if not is_native and (left is None or right is None):
            return False
        return left != right
    if not is_native and (left is None or right is None):
        return False
    if isinstance(operator, ast.Lt):
        return left < right  # type: ignore[operator]
    if isinstance(operator, ast.LtE):
        return left <= right  # type: ignore[operator]
    if isinstance(operator, ast.Gt):
        return left > right  # type: ignore[operator]
    return left >= right  # type: ignore[operator]


class _BufferView:
    """What ``buffer`` means inside a condition that is evaluated in Python."""

    __slots__ = ('_context',)

    def __init__(self, context: Context[object, object]) -> None:
        """Read the scope from the live ``context``."""
        self._context = context

    @property
    def _core_buffer(self) -> _core.Buffer:
        return self._context._owner._buffer

    @property
    def x(self) -> int:
        return self._core_buffer.x

    @property
    def y(self) -> int:
        return self._core_buffer.y

    @property
    def position(self) -> _core.Point:
        return _core.Point(self._core_buffer.x, self._core_buffer.y)

    @property
    def width(self) -> int:
        return self._core_buffer.width

    @property
    def height(self) -> int:
        return self._core_buffer.height

    @property
    def size(self) -> _core.Size:
        return _core.Size(self._core_buffer.width, self._core_buffer.height)

    @property
    def region(self) -> _core.Rectangle:
        return self._core_buffer._absolute_bounds


class _ParentView:
    """What ``parent`` means inside a condition that is evaluated in Python."""

    __slots__ = ('_context',)

    def __init__(self, context: Context[object, object]) -> None:
        """Read the scope from the live ``context``."""
        self._context = context

    @property
    def width(self) -> int:
        return self._context.parent.width

    @property
    def height(self) -> int:
        return self._context.parent.height

    @property
    def size(self) -> _core.Size:
        parent = self._context.parent
        return _core.Size(parent.width, parent.height)


class _RootView:
    """What ``root`` means inside a condition that is evaluated in Python."""

    __slots__ = ('_context',)

    def __init__(self, context: Context[object, object]) -> None:
        """Read the scope from the live ``context``."""
        self._context = context

    @property
    def width(self) -> int:
        return self._context.canvas.width

    @property
    def height(self) -> int:
        return self._context.canvas.height

    @property
    def time(self) -> float:
        return self._context.time.elapsed

    @property
    def delta(self) -> float:
        return self._context.time.delta

    @property
    def fps(self) -> float:
        return self._context.time.fps


def _live_names(context: Context[object, object]) -> dict[str, object]:
    return {
        'keyboard': context.keyboard,
        'mouse': context.mouse,
        'scroll': context.scroll,
        'buffer': _BufferView(context),
        'parent': _ParentView(context),
        'root': _RootView(context),
        'time': context.time.elapsed,
        'deps': context.deps,
    }


@functools.lru_cache(maxsize=1024)
def parse_when(text: str) -> CompiledWhen:
    """
    Compile a condition string once; the same string gives the same result.

    Args:
        text: A condition such as ``"keyboard.key == 'q' and not mouse.is_down"``.

    Returns:
        The compiled condition: a native expression, or a Python function when the string
        reads ``deps``.

    Raises:
        ValueError: The string is not a condition, with the column of the problem.
    """
    parser = _Parser(text)
    reads = frozenset(parser.reads)
    if parser.uses_deps:
        return CompiledWhen(
            None, parser.function(), reads, False, parser.mentions_release
        )
    return CompiledWhen(parser.native(), None, reads, False, parser.mentions_release)


def compile_when(when: object) -> CompiledWhen:
    """
    Compile the ``when`` of a hook, whichever form it was written in.

    Args:
        when: ``None``, an expression, a function of the context or a string.

    Raises:
        TypeError: ``when`` is a plain ``bool``, which is what ``is`` gives, or another type.
        ValueError: A string is not a valid condition.
    """
    if when is None:
        return NO_CONDITION
    if isinstance(when, bool):
        raise TypeError(
            f'when= received {when}. That is what `is` and `and` give on an expression. '
            f'Build the condition with ==, & and |, for example '
            f'Keyboard.key == "q", or write it as a string, "keyboard.key == \'q\'".'
        )
    if isinstance(when, _core.Expression):
        return CompiledWhen(
            cast('_core.Expression[bool]', when), None, frozenset(), True, False
        )
    if isinstance(when, str):
        return parse_when(when)
    if callable(when):
        return CompiledWhen(
            None,
            cast('Callable[[Context[object, object]], bool]', when),
            frozenset(),
            True,
            False,
        )
    raise TypeError(
        f'when= takes a condition expression, a function of the context or a string, but '
        f'received {when!r} of type {type(when).__name__}. For example '
        f'when="keyboard.key == \'q\'" or when=lambda context: context.mouse.is_down.'
    )
