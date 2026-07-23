"""xnano.beta.utils.introspection

---

Hook signature inspection and safe state-expression evaluation.

State/field expressions (``@on_state("count > 0")``) are evaluated by
walking a parsed AST with a small, fixed set of operators rather than
calling ``eval``: names resolve only against the supplied namespace,
calls are limited to a whitelist of pure builtins, and attribute access
to dunder names is refused. There is no code execution path, so a
crafted expression can read declared state but cannot reach the
interpreter.
"""

from __future__ import annotations

import ast
import inspect
import operator
from typing import Any, Callable, TypeVar

StateT = TypeVar("StateT")


_FIRST_PARAM_TYPE_CACHE: dict[Callable, type | None] = {}
_EXTRA_PARAM_COUNT_CACHE: dict[Callable, int] = {}
_PARSED_EXPRESSION_CACHE: dict[str, ast.Expression | None] = {}
"""Parsed ``eval``-mode AST trees for ``evaluate_state_expression``, keyed
by expression source. ``None`` marks a source that failed to parse, so a
persistently invalid expression is not re-parsed on every call."""
_STATE_SAFE_BUILTINS: dict[str, Any] = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "isinstance": isinstance,
    "hasattr": hasattr,
    "getattr": getattr,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
}

_BINARY_OPERATORS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
    ast.Invert: operator.invert,
}
_COMPARE_OPERATORS: dict[type[ast.cmpop], Callable[[Any, Any], Any]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.In: lambda item, container: item in container,
    ast.NotIn: lambda item, container: item not in container,
}


class _UnsupportedExpression(Exception):
    """Raised when an expression uses a construct outside the safe set."""


def get_compiled_state_expression(expression: str) -> ast.Expression | None:
    """Return the cached parsed AST for ``expression``.

    Parses and caches on first use; a source that fails to parse is cached
    as ``None`` so it is not retried on every call.

    Args:
        expression: The expression source to parse.

    Returns:
        The parsed ``eval``-mode AST, or ``None`` when ``expression`` does
            not parse.
    """
    if expression in _PARSED_EXPRESSION_CACHE:
        return _PARSED_EXPRESSION_CACHE[expression]
    try:
        tree: ast.Expression | None = ast.parse(expression, mode="eval")
    except SyntaxError:
        tree = None
    _PARSED_EXPRESSION_CACHE[expression] = tree
    return tree


def _evaluate_node(node: ast.AST, names: dict[str, Any]) -> Any:
    """Evaluate one AST node against ``names`` within the safe subset."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in names:
            return names[node.id]
        if node.id in _STATE_SAFE_BUILTINS:
            return _STATE_SAFE_BUILTINS[node.id]
        raise _UnsupportedExpression(f"unknown name {node.id!r}")
    if isinstance(node, ast.BoolOp):
        values = node.values
        if isinstance(node.op, ast.And):
            result: Any = True
            for value in values:
                result = _evaluate_node(value, names)
                if not result:
                    return result
            return result
        result = False
        for value in values:
            result = _evaluate_node(value, names)
            if result:
                return result
        return result
    if isinstance(node, ast.UnaryOp):
        handler = _UNARY_OPERATORS.get(type(node.op))
        if handler is None:
            raise _UnsupportedExpression("unsupported unary operator")
        return handler(_evaluate_node(node.operand, names))
    if isinstance(node, ast.BinOp):
        handler = _BINARY_OPERATORS.get(type(node.op))
        if handler is None:
            raise _UnsupportedExpression("unsupported binary operator")
        return handler(
            _evaluate_node(node.left, names),
            _evaluate_node(node.right, names),
        )
    if isinstance(node, ast.Compare):
        left = _evaluate_node(node.left, names)
        for op, comparator in zip(node.ops, node.comparators):
            handler = _COMPARE_OPERATORS.get(type(op))
            if handler is None:
                raise _UnsupportedExpression("unsupported comparison")
            right = _evaluate_node(comparator, names)
            if not handler(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Subscript):
        return _evaluate_node(node.value, names)[
            _evaluate_node(node.slice, names)
        ]
    if isinstance(node, ast.Attribute):
        if node.attr.startswith("_"):
            raise _UnsupportedExpression("private attribute access refused")
        return getattr(_evaluate_node(node.value, names), node.attr)
    if isinstance(node, ast.Call):
        function = node.func
        if not isinstance(function, ast.Name):
            raise _UnsupportedExpression("only builtin calls are allowed")
        target = _STATE_SAFE_BUILTINS.get(function.id)
        if target is None or node.keywords:
            raise _UnsupportedExpression(f"call to {function.id!r} refused")
        return target(*(_evaluate_node(arg, names) for arg in node.args))
    if isinstance(node, ast.List):
        return [_evaluate_node(item, names) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_evaluate_node(item, names) for item in node.elts)
    if isinstance(node, ast.Set):
        return {_evaluate_node(item, names) for item in node.elts}
    if isinstance(node, ast.Dict):
        return {
            _evaluate_node(key, names): _evaluate_node(value, names)
            for key, value in zip(node.keys, node.values)
            if key is not None
        }
    if isinstance(node, ast.IfExp):
        if _evaluate_node(node.test, names):
            return _evaluate_node(node.body, names)
        return _evaluate_node(node.orelse, names)
    raise _UnsupportedExpression(
        f"unsupported expression: {type(node).__name__}"
    )


def evaluate_state_expression(
    expression: str,
    state: StateT,
) -> bool:
    """Evaluate ``expression`` against ``state``'s attributes.

    Safe by construction — the expression is walked node by node over a
    fixed operator/builtin set, never executed. Returns ``False`` on any
    error, including an unknown name, an unsupported construct, or an
    ``AttributeError``. The parse is cached by source, since hooks
    re-evaluate the same expression on every tick/frame.

    Args:
        expression: The expression to evaluate.
        state: The object whose attributes the expression reads.

    Returns:
        The truthiness of the evaluated expression.
    """
    if state is None:
        return False
    tree = get_compiled_state_expression(expression)
    if tree is None:
        return False
    try:
        names: dict[str, Any] = {}
        if hasattr(state, "__dict__"):
            names.update(vars(state))
        names["state"] = state
        return bool(_evaluate_node(tree.body, names))
    except Exception:
        return False


def get_first_function_parameter_type(function: Callable) -> type | None:
    """Returns the type annotation of the first parameter of a
    function.

    Args:
        function: The function to get the first parameter type from.

    Returns:
        The type annotation of the first parameter of the function (if
            one exists).
    """
    cached = _FIRST_PARAM_TYPE_CACHE.get(function)
    if cached is not None or function in _FIRST_PARAM_TYPE_CACHE:
        return cached

    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        _FIRST_PARAM_TYPE_CACHE[function] = None
        return None

    parameters = list(signature.parameters.values())
    if not parameters:
        _FIRST_PARAM_TYPE_CACHE[function] = None
        return None

    first_parameter = parameters[0]
    if first_parameter.name in ("self", "cls"):
        if len(parameters) < 2:
            _FIRST_PARAM_TYPE_CACHE[function] = None
            return None

        annotation = parameters[1].annotation
    else:
        annotation = first_parameter.annotation

    if annotation is inspect.Parameter.empty:
        _FIRST_PARAM_TYPE_CACHE[function] = None
        return None

    if isinstance(annotation, type):
        _FIRST_PARAM_TYPE_CACHE[function] = annotation
        return annotation

    _FIRST_PARAM_TYPE_CACHE[function] = None
    return None


def get_function_extra_parameter_count(function: Callable) -> int:
    """Return parameters after ``self`` / ``cls`` on a callable.

    Args:
        function: The callable to inspect.

    Returns:
        The number of parameters following ``self`` or ``cls``.
    """
    if function in _EXTRA_PARAM_COUNT_CACHE:
        return _EXTRA_PARAM_COUNT_CACHE[function]

    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        _EXTRA_PARAM_COUNT_CACHE[function] = 0
        return 0

    parameters = list(signature.parameters.values())
    if not parameters:
        _EXTRA_PARAM_COUNT_CACHE[function] = 0
        return 0

    start = 1 if parameters[0].name in ("self", "cls") else 0
    count = len(parameters) - start
    _EXTRA_PARAM_COUNT_CACHE[function] = count
    return count


__all__ = (
    "evaluate_state_expression",
    "get_compiled_state_expression",
    "get_first_function_parameter_type",
    "get_function_extra_parameter_count",
)
