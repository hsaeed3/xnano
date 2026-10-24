"""
tests.documented_attributes

Read how the lazy re-export modules document their names.

A lazy module such as ``xnano.widgets`` declares each public name inside an
``if TYPE_CHECKING:`` block, assigns it to the object it re-exports and documents it with a
string placed right after the assignment. A lazy module that gathers names defined elsewhere,
such as ``xnano.layout``, imports them in that block instead, and each is documented where it
is defined. Nothing in that block runs, so the tests read it from the syntax tree of the module.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import pathlib


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


def imported_names(tree: ast.Module) -> dict[str, str]:
    """Each name imported inside ``if TYPE_CHECKING:``, with the module it comes from."""
    imported: dict[str, str] = {}
    for node in tree.body:
        if not is_type_checking_block(node):
            continue
        for statement in node.body:  # type: ignore[attr-defined]
            if isinstance(statement, ast.ImportFrom) and statement.module:
                for alias in statement.names:
                    imported[alias.asname or alias.name] = statement.module
    return imported


def is_documented_in(module_name: str, name: str) -> bool:
    """Whether ``name`` has a docstring where ``module_name`` defines it, following re-exports."""
    if not module_name.startswith('xnano.'):
        # The core documents its own names in its stubs.
        return True
    specification = importlib.util.find_spec(module_name)
    assert specification is not None and specification.origin is not None
    tree = ast.parse(pathlib.Path(specification.origin).read_text(encoding='utf-8'))
    if name in dict(documented_attributes(tree)):
        return True
    for statement, following in zip(tree.body, [*tree.body[1:], None], strict=True):
        if (
            isinstance(statement, (ast.ClassDef, ast.FunctionDef))
            and statement.name == name
        ):
            return ast.get_docstring(statement) is not None
        targets = (
            [statement.target]
            if isinstance(statement, ast.AnnAssign)
            else statement.targets
            if isinstance(statement, ast.Assign)
            else []
        )
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return (
                isinstance(following, ast.Expr)
                and isinstance(following.value, ast.Constant)
                and isinstance(following.value.value, str)
            )
        if isinstance(statement, ast.ImportFrom) and statement.module:
            for alias in statement.names:
                if (alias.asname or alias.name) == name:
                    return is_documented_in(statement.module, alias.name)
    source = imported_names(tree).get(name)
    return source is not None and is_documented_in(source, name)
