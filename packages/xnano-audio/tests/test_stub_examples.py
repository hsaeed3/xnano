"""Every ``Examples:`` code block in the stub's docstrings runs as written."""

from __future__ import annotations

import ast
import pathlib
import re
import textwrap

import pytest

import xnano_audio._xnano_audio as native

STUB = pathlib.Path(native.__file__).parent / '_xnano_audio' / '__init__.pyi'
if not STUB.exists():
    STUB = pathlib.Path(native.__file__).parent / '__init__.pyi'
PREAMBLE = 'from xnano_audio import *\n'


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

    visit(ast.parse(STUB.read_text(encoding='utf-8')))
    return found


EXAMPLES = collect()


def test_the_stub_documents_the_mixer_with_an_example():
    assert any(name.startswith('TerminalSound.mix') for name, _ in EXAMPLES)


@pytest.mark.parametrize(('name', 'code'), EXAMPLES, ids=[name for name, _ in EXAMPLES])
def test_example_runs(name, code):
    exec(PREAMBLE + code, {})  # noqa: S102
