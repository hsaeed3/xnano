"""xnano.beta.utils.dispatch

---

Invoke synchronous and asynchronous hooks with supported signatures.
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Coroutine, cast

from xnano.beta.core.exceptions import Exit
from xnano.beta.utils.introspection import get_function_extra_parameter_count

if TYPE_CHECKING:
    from xnano.beta.context import Context


_logger = logging.getLogger("xnano.beta.hooks")


def run_awaitable(awaitable: Awaitable[Any]) -> Any:
    """Drive an async hook result to completion on a free event loop.

    Args:
        awaitable: A coroutine or other awaitable returned by a hook.

    Returns:
        The awaitable's result.

    Raises:
        RuntimeError: If called while an asyncio event loop is already
            running on this thread (the sync run loop cannot nest
            ``asyncio.run``).
        TypeError: If ``awaitable`` is not a coroutine object.
    """
    # Async hooks are optional. Keep asyncio and its comparatively large
    # import graph out of the synchronous startup and first-render path.
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        if inspect.iscoroutine(awaitable):
            return asyncio.run(cast(Coroutine[Any, Any, Any], awaitable))

        async def _drain() -> Any:
            return await awaitable

        return asyncio.run(_drain())
    raise RuntimeError(
        "async @on_* hooks cannot run while an asyncio event loop is "
        "already active on this thread; call Runtime.live() from a "
        "sync context, or wrap it with asyncio.to_thread(...)."
    )


def _call_hook(handler: Any, bound_self: Any, ctx: "Context[Any]") -> Any:
    """Invoke ``handler`` with the right arity (sync call only).

    Handlers may take zero extra parameters or a single ``Context``,
    whether they are bound methods, unbound methods resolved against a
    live grid (``bound_self``), or free functions.
    """
    bound_instance = getattr(handler, "__self__", None)
    if bound_instance is not None:
        function = getattr(handler, "__func__", handler)
        if get_function_extra_parameter_count(function) == 0:
            return handler()
        return handler(ctx)

    count = get_function_extra_parameter_count(handler)
    if bound_self is not None:
        if count == 0:
            return handler(bound_self)
        return handler(bound_self, ctx)
    if count == 0:
        return handler()
    return handler(ctx)


def invoke_hook(handler: Any, bound_self: Any, ctx: "Context[Any]") -> Any:
    """Invoke ``handler`` with the right arity, awaiting async results.

    Uncaught exceptions (other than ``Exit`` / ``KeyboardInterrupt`` /
    ``SystemExit``) are logged at ERROR and re-raised so the run loop
    can restore the host terminal on the way out.
    """
    name = getattr(handler, "__qualname__", repr(handler))
    try:
        result = _call_hook(handler, bound_self, ctx)
        if inspect.isawaitable(result):
            return run_awaitable(result)
        return result
    except Exit:
        raise
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        _logger.exception("Uncaught exception in hook %s", name)
        raise


__all__ = ("invoke_hook", "run_awaitable")
