"""
tests.helpers

Stub reader and annotation matcher: the ``.pyi`` file is the documented
contract, and these helpers check the compiled module against it (a ``str``
must be a ``str``, never a dict or a Rust debug dump).
"""

from __future__ import annotations

import ast
import pathlib

import xnano_audio._xnano_audio as native

STUB = pathlib.Path(native.__file__).parent / '_xnano_audio' / '__init__.pyi'
if not STUB.exists():
    STUB = pathlib.Path(native.__file__).parent / '__init__.pyi'
if not STUB.exists():
    STUB = (
        pathlib.Path(__file__).resolve().parents[1]
        / 'python'
        / 'xnano_audio'
        / '_xnano_audio'
        / '__init__.pyi'
    )

TREE = ast.parse(STUB.read_text())


class StubFunction:
    def __init__(self, node: ast.FunctionDef, owner: str | None):
        self.node = node
        self.name = node.name
        self.owner = owner
        decorators = {ast.unparse(d) for d in node.decorator_list}
        self.is_static = 'staticmethod' in decorators
        self.is_property = 'property' in decorators
        self.returns = ast.unparse(node.returns) if node.returns else None
        self.doc = ast.get_docstring(node)
        args = node.args
        names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
        self.parameters = [n for n in names if n != 'self']


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
        cls = getattr(native, node.id, None)
        return isinstance(value, cls) if isinstance(cls, type) else True
    if isinstance(node, ast.Subscript):
        head = ast.unparse(node.value)
        inner = node.slice
        if head == 'Optional':
            return value is None or _matches(value, inner)
        if head == 'list':
            return isinstance(value, list) and all(_matches(v, inner) for v in value)
    return True
