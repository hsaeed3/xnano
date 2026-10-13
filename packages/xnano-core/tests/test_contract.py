"""The ``.pyi`` stub is the documented contract: the compiled module must provide all of it."""

from __future__ import annotations

import ast
import pathlib

import pytest

import xnano_core._xnano_core as native

STUB = pathlib.Path(native.__path__[0]) / '__init__.pyi'
TREE = ast.parse(STUB.read_text(encoding='utf-8'))

CLASSES = {node.name: node for node in TREE.body if isinstance(node, ast.ClassDef)}
FUNCTIONS = {node.name for node in TREE.body if isinstance(node, ast.FunctionDef)}

# Exceptions are re-exported by name; everything else must be a real attribute.
PRIVATE_OK = {'_reference', '_external', '_state_expression'}


def member_names(cls: ast.ClassDef) -> list[str]:
    names = []
    for item in cls.body:
        if isinstance(item, ast.FunctionDef) and item.name not in {'__init__', '__new__'}:
            names.append(item.name)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return names


def test_the_stub_is_not_empty():
    assert len(CLASSES) > 100 and len(FUNCTIONS) >= 8


@pytest.mark.parametrize('name', sorted(CLASSES))
def test_class_exists_with_every_stubbed_member(name):
    assert hasattr(native, name), f'{name} is in the stub but missing from the extension'
    cls = getattr(native, name)
    if issubclass(cls, BaseException):
        return  # exception attributes are set on instances
    missing = [
        member for member in member_names(CLASSES[name]) if not hasattr(cls, member)
    ]
    assert not missing, f'{name} lacks {missing}'


@pytest.mark.parametrize('name', sorted(FUNCTIONS))
def test_function_exists(name):
    assert hasattr(native, name)


def test_the_compiled_module_is_a_package_with_core_types():
    from xnano_core._xnano_core import _core_types

    assert native.__path__ == [str(pathlib.Path(_core_types.__file__).parent)]


def test_every_name_the_stub_imports_from_core_types_exists():
    imported = [
        alias.name
        for node in TREE.body
        if isinstance(node, ast.ImportFrom) and node.module == '_core_types'
        for alias in node.names
    ]
    assert 'CoreContext' in imported
    from xnano_core._xnano_core import _core_types

    missing = [name for name in imported if not hasattr(_core_types, name)]
    assert not missing, f'_core_types lacks {missing}'


def test_the_native_runtime_finds_the_python_objects_it_constructs():
    from xnano_core._xnano_core import _core_types

    with native.Runtime.offscreen(width=10, height=3) as runtime:
        buffer = native.Buffer()
        context = runtime.mount(buffer, geometry='inherit')
        assert type(context) is _core_types.CoreContext
        assert isinstance(runtime.registry, _core_types.Registry)
        assert str(buffer()) == buffer.render(format='ansi')
