"""
tests.documented_attributes

Read how the lazy re-export modules document their names.

A lazy module such as ``xnano.styles`` declares each public name inside an
``if TYPE_CHECKING:`` block, assigns it to the object it re-exports and documents it with a
string placed right after the assignment. Nothing in that block runs, so the tests read it
from the syntax tree of the module.
"""

from __future__ import annotations

import ast
import inspect


def is_type_checking_block(node: ast.stmt) -> bool:
    """Whether the statement is ``if TYPE_CHECKING:``."""
    return isinstance(node, ast.If) and ast.unparse(node.test) == 'TYPE_CHECKING'


def documented_attributes(tree: ast.Module) -> list[tuple[str, str]]:
    """Each name assigned inside ``if TYPE_CHECKING:``, with the string that documents it."""
    documented: list[tuple[str, str]] = []
    for node in tree.body:
        if not (isinstance(node, ast.If) and is_type_checking_block(node)):
            continue
        for assignment, expression in zip(node.body, node.body[1:], strict=False):
            if (
                isinstance(assignment, ast.Assign)
                and isinstance(assignment.targets[0], ast.Name)
                and isinstance(expression, ast.Expr)
                and isinstance(expression.value, ast.Constant)
                and isinstance(expression.value.value, str)
            ):
                documented.append(
                    (assignment.targets[0].id, inspect.cleandoc(expression.value.value))
                )
    return documented


def names_defined_at_runtime(tree: ast.Module) -> set[str]:
    """The names a module defines at its top level, outside the ``if TYPE_CHECKING:`` block."""
    names: set[str] = set()
    for node in tree.body:
        if is_type_checking_block(node):
            continue
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(
                (alias.asname or alias.name).split('.')[0] for alias in node.names
            )
    return names
