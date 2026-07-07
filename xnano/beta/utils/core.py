"""xnano.beta.utils.core"""

from __future__ import annotations

import contextvars
import inspect
from typing import Any, Callable, TypeVar


StateT = TypeVar("StateT")


_FIRST_PARAM_TYPE_CACHE: dict[Callable, type | None] = {}
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


def evaluate_state_expression(
    expression: str,
    state: StateT,
) -> bool:
    """Evaluate ``expression`` against ``state``'s attributes.

    Safe eval — globals are restricted to a small whitelist. Returns ``False``
    on any exception, including ``AttributeError``.

    Args:
        expression: The expression to evaluate.
        state: The state to evaluate the expression against.

    Returns:
        The result of the expression evaluation.
    """
    if state is None:
        return False
    try:
        ns: dict[str, Any] = {}
        if hasattr(state, "__dict__"):
            ns.update(vars(state))
        ns["state"] = state
        return bool(
            eval(expression, {"__builtins__": _STATE_SAFE_BUILTINS}, ns)
        )  # noqa: S307
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
