"""
tests.helpers

Stub reader, annotation matcher, strict ANSI validator, cell animation reader and
image factories.
"""

from __future__ import annotations

import ast
import pathlib
import re
import struct

import xnano_image._xnano_image as native
from xnano_image import TerminalImage

STUB = pathlib.Path(native.__file__).parent / '_xnano_image' / '__init__.pyi'
if not STUB.exists():
    STUB = pathlib.Path(native.__file__).parent / '__init__.pyi'
if not STUB.exists():
    STUB = (
        pathlib.Path(__file__).resolve().parents[1]
        / 'python'
        / 'xnano_image'
        / '_xnano_image'
        / '__init__.pyi'
    )

TREE = ast.parse(STUB.read_text())


class StubFunction:
    def __init__(self, node: ast.FunctionDef, owner: str | None):
        self.node = node
        self.name = node.name
        self.owner = owner
        decorators = {ast.unparse(decorator) for decorator in node.decorator_list}
        self.is_static = 'staticmethod' in decorators
        self.is_property = 'property' in decorators
        self.returns = ast.unparse(node.returns) if node.returns else None
        self.doc = ast.get_docstring(node)
        arguments = node.args
        self.positional_parameters = [
            argument.arg
            for argument in arguments.posonlyargs + arguments.args
            if argument.arg != 'self'
        ]
        self.keyword_only_parameters = [argument.arg for argument in arguments.kwonlyargs]
        self.parameters = self.positional_parameters + self.keyword_only_parameters


class StubClass:
    def __init__(self, node: ast.ClassDef):
        self.name = node.name
        self.doc = ast.get_docstring(node)
        self.methods = {
            item.name: StubFunction(item, node.name)
            for item in node.body
            if isinstance(item, ast.FunctionDef)
        }


CLASSES = {
    node.name: StubClass(node) for node in TREE.body if isinstance(node, ast.ClassDef)
}
FUNCTIONS = {
    node.name: StubFunction(node, None)
    for node in TREE.body
    if isinstance(node, ast.FunctionDef)
}


def matches(value: object, annotation: str) -> bool:
    """Whether ``value`` satisfies the stub annotation string."""
    return _matches(value, ast.parse(annotation.strip(), mode='eval').body)


def _matches(value: object, node: ast.expr) -> bool:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _matches(value, node.left) or _matches(value, node.right)
    if isinstance(node, ast.Constant) and node.value is None:
        return value is None
    if isinstance(node, ast.Name):
        if node.id == 'float':
            return isinstance(value, float)
        if node.id == 'int':
            return isinstance(value, int) and not isinstance(value, bool)
        if node.id in ('str', 'bool', 'bytes'):
            return isinstance(value, {'str': str, 'bool': bool, 'bytes': bytes}[node.id])
        native_class = getattr(native, node.id, None)
        return isinstance(value, native_class) if isinstance(native_class, type) else True
    if isinstance(node, ast.Subscript):
        head = ast.unparse(node.value)
        inner = node.slice
        if head == 'Literal':
            choices = inner.elts if isinstance(inner, ast.Tuple) else [inner]
            return any(
                isinstance(choice, ast.Constant) and value == choice.value
                for choice in choices
            )
        if head == 'list':
            return isinstance(value, list) and all(
                _matches(item, inner) for item in value
            )
        if head == 'tuple' and isinstance(inner, ast.Tuple):
            return (
                isinstance(value, tuple)
                and len(value) == len(inner.elts)
                and all(
                    _matches(item, element)
                    for item, element in zip(value, inner.elts, strict=True)
                )
            )
    return True


# ----------------------------------------------------------- ANSI checker

_SGR = re.compile(r'\x1b\[([0-9;]*)m')
_OSC8 = re.compile(r'\x1b\]8;[^\x1b\x07]*;[^\x1b\x07]*(?:\x1b\\|\x07)')


def ansi_problems(text: str) -> list[str]:
    """
    Everything wrong with ``text`` as ANSI, empty when it is well formed.

    Allowed: SGR sequences with valid parameters and OSC 8 hyperlinks. Any
    other escape, any stray control character, and any truncated sequence is a
    problem, as is output that does not end with a reset.
    """
    problems: list[str] = []
    rest = _OSC8.sub('', text)
    position = 0
    while True:
        escape_position = rest.find('\x1b', position)
        if escape_position < 0:
            break
        match = _SGR.match(rest, escape_position)
        if not match:
            problems.append(
                f'unrecognized escape at {escape_position}: '
                f'{rest[escape_position : escape_position + 12]!r}'
            )
            position = escape_position + 1
            continue
        problems += _sgr_problems(match.group(1).split(';'))
        position = match.end()
    bare = _SGR.sub('', rest)
    for character in bare:
        if ord(character) < 0x20 and character not in '\n\t' or ord(character) == 0x7F:
            problems.append(f'control character {character!r}')
            break
    for line in text.split('\n'):
        if line and '\x1b[' in line and not line.endswith('\x1b[0m'):
            problems.append(f'line does not end with a reset: {line[-12:]!r}')
            break
    return problems


def _sgr_problems(parameters: list[str]) -> list[str]:
    problems: list[str] = []
    numbers: list[int] = []
    for parameter in parameters:
        if parameter == '':
            numbers.append(0)
        elif parameter.isdigit():
            numbers.append(int(parameter))
        else:
            return [f'non-numeric SGR parameter {parameter!r}']
    index = 0
    while index < len(numbers):
        number = numbers[index]
        if number in (38, 48, 58):
            if index + 1 >= len(numbers):
                problems.append('extended color without a mode')
                break
            mode = numbers[index + 1]
            needed = {5: 1, 2: 3}.get(mode)
            if needed is None:
                problems.append(f'bad extended color mode {mode}')
                break
            values = numbers[index + 2 : index + 2 + needed]
            if len(values) != needed or any(value > 255 for value in values):
                problems.append(f'bad extended color values {values}')
            index += 2 + needed
            continue
        if number > 107:
            problems.append(f'SGR code {number} out of range')
        index += 1
    return problems


# ---------------------------------------------------- cell animation reader


def read_cell_animation(data: bytes) -> tuple[bool, list[tuple[int, bytes]]]:
    """
    Split ``XCA1`` bytes into ``(should_loop, [(duration_milliseconds, cell_grid)])``.

    Follows the documented layout of the shared format byte for byte, so the tests
    pin the contract independently of any reader in the native packages.
    """
    assert data[:4] == b'XCA1', data[:8]
    flags, frame_count = struct.unpack_from('<BI', data, 4)
    position = 9
    frames = []
    for _ in range(frame_count):
        duration_milliseconds, length = struct.unpack_from('<II', data, position)
        position += 8
        frames.append((duration_milliseconds, data[position : position + length]))
        position += length
    assert position == len(data), 'trailing bytes after the last frame'
    return bool(flags & 1), frames


# ------------------------------------------------------------- factories


def solid(width, height, color=(255, 0, 0), alpha=255, duration_milliseconds=100):
    return TerminalImage.from_rgba(
        width,
        height,
        bytes([*color, alpha]) * (width * height),
        duration_milliseconds=duration_milliseconds,
    )


def gradient(width, height):
    data = bytearray()
    for row in range(height):
        for column in range(width):
            data += bytes(
                [
                    column * 255 // max(width - 1, 1),
                    row * 255 // max(height - 1, 1),
                    (column + row) % 256,
                    255,
                ]
            )
    return TerminalImage.from_rgba(width, height, bytes(data))


def animation(frames=3, width=6, height=4, duration_milliseconds=50):
    return TerminalImage.from_frames(
        [
            solid(
                width,
                height,
                (index * 80 % 256, 40, 200 - index * 30),
                duration_milliseconds=duration_milliseconds,
            )
            for index in range(frames)
        ]
    )
