"""xnano.beta.utils.core"""

from __future__ import annotations

import contextvars
import inspect
import types
from typing import Any, Callable, TypeVar


StateT = TypeVar("StateT")


_FIRST_PARAM_TYPE_CACHE: dict[Callable, type | None] = {}
_EXTRA_PARAM_COUNT_CACHE: dict[Callable, int] = {}
_COMPILED_EXPRESSION_CACHE: dict[str, types.CodeType | None] = {}
"""Compiled ``eval`` code objects for ``evaluate_state_expression``, keyed
by expression source. ``None`` marks an expression that failed to compile,
so a persistently invalid expression is not recompiled on every call."""
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


def get_compiled_state_expression(expression: str) -> types.CodeType | None:
    """Return the cached compiled code object for ``expression``.

    Compiles and caches on first use; a source that fails to compile is
    cached as ``None`` so it is not retried on every call.

    Args:
        expression: The expression source to compile.

    Returns:
        The compiled code object, or ``None`` when ``expression`` does not
            compile.
    """
    if expression in _COMPILED_EXPRESSION_CACHE:
        return _COMPILED_EXPRESSION_CACHE[expression]
    try:
        code = compile(expression, "<state-expression>", "eval")
    except SyntaxError:
        code = None
    _COMPILED_EXPRESSION_CACHE[expression] = code
    return code


def evaluate_state_expression(
    expression: str,
    state: StateT,
) -> bool:
    """Evaluate ``expression`` against ``state``'s attributes.

    Safe eval — globals are restricted to a small whitelist. Returns ``False``
    on any exception, including ``AttributeError``. The expression is
    compiled once and cached by source, since hooks re-evaluate the same
    expression on every tick/frame.

    Args:
        expression: The expression to evaluate.
        state: The state to evaluate the expression against.

    Returns:
        The result of the expression evaluation.
    """
    if state is None:
        return False
    code = get_compiled_state_expression(expression)
    if code is None:
        return False
    try:
        ns: dict[str, Any] = {}
        if hasattr(state, "__dict__"):
            ns.update(vars(state))
        ns["state"] = state
        return bool(eval(code, {"__builtins__": _STATE_SAFE_BUILTINS}, ns))  # noqa: S307
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
