"""Every ``Examples:`` code block in the stub's docstrings runs as written."""

from __future__ import annotations

import ast
import pathlib
import re
import textwrap

import pytest

import xnano._xnano_core as native

STUB = pathlib.Path(native.__path__[0]) / '__init__.pyi'
PREAMBLE = (
    'from xnano._xnano_core import *\nfrom xnano._xnano_core._core_types import *\n'
)


def collect() -> list[tuple[str, str]]:
    found = []

    def visit(node: ast.AST, prefix: str = '') -> None:
        for child in getattr(node, 'body', []):
            if not isinstance(child, (ast.ClassDef, ast.FunctionDef)):
                continue
            name = prefix + child.name
            doc = ast.get_docstring(child) or ''
            if 'Examples:' in doc:
                section = doc.split('Examples:', 1)[1]
                for index, block in enumerate(
                    re.findall(r'```python\n(.*?)```', section, re.DOTALL)
                ):
                    found.append((f'{name}[{index}]', textwrap.dedent(block)))
            if isinstance(child, ast.ClassDef):
                visit(child, name + '.')

    visit(ast.parse(STUB.read_text()))
    return found


EXAMPLES = collect()


def test_the_stub_documents_its_api_with_examples():
    assert len(EXAMPLES) > 250


def test_every_public_class_and_function_has_an_example():
    tree = ast.parse(STUB.read_text())
    documented = {name.split('[')[0].split('.')[0] for name, _ in EXAMPLES}
    missing = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        and not node.name.startswith('_')
        and node.name not in documented
    ]
    assert not missing, f'no example for {missing}'


@pytest.mark.parametrize(('name', 'code'), EXAMPLES, ids=[name for name, _ in EXAMPLES])
def test_example_runs(name, code, capsys):
    exec(PREAMBLE + code, {})  # noqa: S102
