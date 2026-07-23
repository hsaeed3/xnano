"""xnano.core.hosts

---

Shared host contract for terminal, web, and CLI sessions: navigation,
``perform``, and device / cursor / actions / stage access.
"""

from __future__ import annotations

import abc
import collections
import contextvars
from typing import TYPE_CHECKING, Any, Callable

from xnano.core.device import AbstractCursor, AbstractDevice
from xnano.core.exceptions import HookError

if TYPE_CHECKING:
    from xnano.core.actions import Actions
    from xnano.core.stage import Stage

_MAX_PERFORM_DEPTH: int = 32
"""Maximum actions drained from a single ``perform`` chain.

Runaway action → hook → action loops raise ``HookError`` instead of
overflowing the call stack.
"""


_ACTIVE_HOST: contextvars.ContextVar["AbstractHost | None"] = (
    contextvars.ContextVar("_ACTIVE_HOST", default=None)
)
"""Context-local active host for the current session/request."""


def get_active_host() -> "AbstractHost | None":
    """Return the host bound to the current context, if any.

    Returns:
        The active ``AbstractHost``, or ``None`` when no host has
        entered the context.
    """
    return _ACTIVE_HOST.get()


class RouteTable:
    """Maps route keys to interface factories for host navigation.

    Hosts resolve their active root through this table so terminal
    window swaps and web page routes share one funnel. Factories are
    called on ``resolve`` so each navigation can materialize a fresh
    root when desired.
    """

    def __init__(self) -> None:
        self._routes: dict[str, Callable[[], Any]] = {}
        self._default_key: str | None = None

    def register(
        self,
        key: str,
        factory: Callable[[], Any],
        *,
        default: bool = False,
    ) -> None:
        """Register an interface factory under ``key``.

        The first registered route becomes the default when none has
        been chosen yet. Passing ``default=True`` always promotes
        ``key`` to the default route.

        Args:
            key: Stable route identifier (window name, path, …).
            factory: Zero-arg callable returning the root interface
                (grid/component instance).
            default: When ``True``, make this the default route.
        """
        self._routes[key] = factory
        if default or self._default_key is None:
            self._default_key = key

    def resolve(self, key: str | None = None) -> Any:
        """Materialize the interface for ``key`` (or the default).

        Args:
            key: Route key to resolve. When ``None``, uses
                ``default_key``.

        Returns:
            The factory result for the resolved key.

        Raises:
            KeyError: If no key is available or ``key`` is unknown.
        """
        resolved_key = self._default_key if key is None else key
        if resolved_key is None:
            raise KeyError(
                "No route key provided and no default route is registered."
            )
        factory = self._routes.get(resolved_key)
        if factory is None:
            raise KeyError(f"Unknown route: {resolved_key!r}")
        return factory()

    @property
    def default_key(self) -> str | None:
        """Key of the default route, if one has been registered."""
        return self._default_key

    def keys(self) -> tuple[str, ...]:
        """Return registered route keys in insertion order.

        Returns:
            A tuple of route keys.
        """
        return tuple(self._routes.keys())


class AbstractHost(abc.ABC):
    """Shared host contract for terminal, web, and CLI sessions.

    ``Terminal``, web sessions, and the CLI runner implement this so
    dispatch, ``perform``, navigation, and device / cursor / actions /
    stage access share one shape.

    Duck surface expected by shared dispatch helpers (subclasses
    typically initialize these in ``__init__``):

    - ``_hooks`` — event hook registry
    - ``_attached_grids`` — ``id → grid`` map for hook rebinding
    - ``_attached_frame_grids`` — grids visited this frame
    - ``state`` — user state threaded into ``Context``
    """

    def __init__(self) -> None:
        self._perform_queue: collections.deque[Any] = collections.deque()
        self._dispatching: bool = False
        self._routes: RouteTable = RouteTable()
        self._active_root: Any = None
        self._actions: Any = None
        self._stage: Any = None
        # Dispatch duck surface — subclasses may overwrite.
        self._hooks: Any = None
        self._attached_grids: dict[int, Any] = {}
        self._attached_frame_grids: list[Any] = []
        self.state: Any = None

    @property
    @abc.abstractmethod
    def device(self) -> AbstractDevice:
        """Device controls for this host (title, clear, size, clipboard)."""

    @property
    @abc.abstractmethod
    def cursor(self) -> AbstractCursor:
        """Cursor / caret controls for this host (visibility and style)."""

    @property
    def actions(self) -> "Actions":
        """Perform synthetic input and requests against this host.

        Returns:
            An ``Actions`` helper bound to this host.
        """
        if self._actions is None:
            from xnano.core.actions import Actions

            self._actions = Actions(self)
        return self._actions

    @property
    def stage(self) -> "Stage":
        """Layout map and cell-level paint / wireframe for this host.

        Returns:
            A ``Stage`` for layout lookup and overlay painting.
        """
        if self._stage is None:
            from xnano.core.stage import Stage

            self._stage = Stage(self)
        return self._stage

    @property
    def routes(self) -> RouteTable:
        """Route table used by ``navigate``."""
        return self._routes

    @property
    def active_root(self) -> Any:
        """Currently active root interface, if one is set."""
        return self._active_root

    def perform(self, action: Any) -> None:
        """Synthesize an event from ``action`` and run the dispatch pump.

        Re-entrancy: when already dispatching, ``action`` is queued and
        drained after the current pass completes — never nested. A
        chain longer than ``_MAX_PERFORM_DEPTH`` raises ``HookError``.

        Args:
            action: An object exposing ``to_event()`` (typically an
                ``Action``), or a pre-built event accepted by
                ``dispatch_hooks``.

        Raises:
            HookError: If the perform chain exceeds the depth guard.
        """
        self._perform_queue.append(action)
        if self._dispatching:
            return
        self._dispatching = True
        depth = 0
        try:
            while self._perform_queue:
                if depth >= _MAX_PERFORM_DEPTH:
                    self._perform_queue.clear()
                    raise HookError(
                        "perform",
                        RuntimeError(
                            "Action perform chain exceeded max depth "
                            f"({_MAX_PERFORM_DEPTH})"
                        ),
                    )
                next_action = self._perform_queue.popleft()
                self._dispatch_performed_action(next_action)
                depth += 1
        finally:
            self._dispatching = False

    def _dispatch_performed_action(self, action: Any) -> None:
        """Lower ``action`` to an event and run ``dispatch_hooks``.

        Args:
            action: Action or event-like object.
        """
        event = action
        to_event = getattr(action, "to_event", None)
        if callable(to_event):
            event = to_event()

        from typing import Any as TypingAny
        from typing import cast

        from xnano import _dispatch
        from xnano.context import Context

        # Hosts (Terminal, and the web host's session terminal) duck-type
        # the Terminal surface that dispatch_hooks expects.
        host = cast(TypingAny, self)
        ctx = Context(
            event=event,
            terminal=host,
            state=self.state,
        )
        _dispatch.dispatch_hooks(host, ctx)

    def navigate(self, key: str) -> None:
        """Swap the active root using the route table.

        Resolves ``key``, stores the result as ``active_root``, and
        notifies subclasses through ``on_navigate``.

        Args:
            key: Registered route key.

        Raises:
            KeyError: If ``key`` is not registered.
        """
        root = self._routes.resolve(key)
        self._active_root = root
        self.on_navigate(key, root)

    def on_navigate(self, key: str, root: Any) -> None:
        """Hook invoked after a successful ``navigate``.

        Subclasses override to reattach hooks, update the controller
        root, or map the key to a URL path. Default is a no-op.

        Args:
            key: Route key that was resolved.
            root: Materialized root interface instance.
        """
        return None

    def enter_host(self) -> "AbstractHost":
        """Bind this host as the context-local active host.

        Returns:
            ``self`` for context-manager style use.
        """
        self._host_token = _ACTIVE_HOST.set(self)
        return self

    def leave_host(self) -> None:
        """Clear the context-local active host if it is this instance."""
        token = getattr(self, "_host_token", None)
        if token is not None:
            _ACTIVE_HOST.reset(token)
            self._host_token = None
        elif _ACTIVE_HOST.get() is self:
            _ACTIVE_HOST.set(None)


__all__ = (
    "AbstractHost",
    "RouteTable",
    "_ACTIVE_HOST",
    "_MAX_PERFORM_DEPTH",
    "get_active_host",
)
