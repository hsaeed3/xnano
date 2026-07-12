"""xnano.webui.session

---

Per-visitor (or shared) web host session: one live grid plus hooks,
the browser analogue of a terminal host.
"""

from __future__ import annotations

from typing import Any, cast

from xnano._function_hooks import (
    _EventHooksRegistry,
    _OnRequestHookEntry,
    _RequestHooksRegistry,
)
from xnano.core.controllers.webui import WebController
from xnano.core.device import AbstractCursor, AbstractDevice
from xnano.core.hosts import AbstractHost
from xnano.webui.device import WebCursor, WebDevice
from xnano.webui.requests import HttpMethod


class WebSession(AbstractHost):
    """One live browser grid session with hooks, state, and device access.

    Web analogue of ``Terminal``: renders the root grid to HTML, pumps
    tick/state/field hooks, and exposes ``device``, ``cursor``,
    ``actions``, and ``stage``.
    """

    def __init__(self, grid: Any, state: Any) -> None:
        AbstractHost.__init__(self)
        self.grid = grid
        self.state = state
        self.controller = WebController()
        self.controller.grid_observer = self._observe_grid
        self._hooks = _EventHooksRegistry()
        self._attached_grids: dict[int, Any] = {}
        self._attached_frame_grids: list[Any] = []
        self._attached_grid_classes: set[type] = set()
        self._request_hooks: list[_OnRequestHookEntry] = []
        self._request_hook_grids: dict[int, Any] = {}
        self._device: WebDevice | None = None
        self._cursor: WebCursor | None = None
        self.enter_host()

    @property
    def device(self) -> AbstractDevice:
        """Browser device controls (title, size, scroll, clipboard)."""
        if self._device is None:
            self._device = WebDevice(self)
        return self._device

    @property
    def cursor(self) -> AbstractCursor:
        """Browser caret / pointer style controls."""
        if self._cursor is None:
            self._cursor = WebCursor(self)
        return self._cursor

    def _observe_grid(self, grid: Any) -> None:
        from xnano._dispatch import track_frame_grid

        track_frame_grid(cast(Any, self), grid)
        self._collect_request_hooks(grid)

    def _collect_request_hooks(self, grid: Any) -> None:
        """Register ``@on_get_request`` / ``@on_post_request`` handlers for ``grid``.

        Bound once per grid instance so nested grids can contribute
        routes without double-binding on every paint.
        """
        grid_id = id(grid)
        if grid_id in self._request_hook_grids:
            return
        self._request_hook_grids[grid_id] = grid
        collected = _RequestHooksRegistry.from_component_class(type(grid))
        from xnano._dispatch import rebind_hook_handler

        for entry in collected.all_hooks():
            self._request_hooks.append(
                _OnRequestHookEntry(
                    method=entry["method"],
                    path=entry["path"],
                    handler=rebind_hook_handler(entry["handler"], grid),
                )
            )

    def render(self) -> str:
        """Render the session's grid to an HTML fragment."""
        self._attached_frame_grids.clear()
        return self.controller.render_grid_html(self.grid)

    def pump(self) -> None:
        """Run tick/state/field hooks, exactly like the terminal loop."""
        from xnano._dispatch import pump_tick

        pump_tick(cast(Any, self))

    def _make_context(self, event: Any = None) -> Any:
        from xnano.context import Context

        return Context(
            event=event,
            terminal=cast(Any, self),
            state=self.state,
        )

    def dispatch_click(self, target_id: str) -> str:
        """Fire the ``@on_click`` handler for ``target_id``, re-render.

        Unknown or stale ids degrade to an idempotent refresh.
        """
        info = self.controller.click_targets.get(target_id)
        if info is not None:
            from xnano._dispatch import invoke_hook
            from xnano.events import MouseEventData
            from xnano.grid import _resolve_grid_mouse_handler

            grid, field_name = info
            handler = _resolve_grid_mouse_handler(grid, field_name)
            if handler is not None:
                from xnano.core.actions import Action
                from xnano.events import Event

                # Object form of the click trigger (Action vocabulary).
                action = Action.click(field_name)
                event = action.to_event()
                if not event.is_mouse_event():
                    mouse = MouseEventData(
                        kind="press", x=0, y=0, button="left"
                    )
                    event = Event.from_data(mouse)
                ctx = self._make_context(event)
                invoke_hook(handler, grid, ctx)
        self.pump()
        return self.render()

    def dispatch_keyboard(self, binding: str) -> str:
        """Fire ``@on_event`` / ``@on_keyboard`` hooks for a keypress."""
        from xnano._dispatch import (
            invoke_hook,
            keyboard_matches,
            resolve_hook_grid,
        )
        from xnano.events import Event, KeyboardEventData

        keyboard = KeyboardEventData.from_binding(binding)
        event = Event.from_data(keyboard)
        ctx = self._make_context(event)
        for handler in self._hooks.on_event_hooks:
            grid = resolve_hook_grid(cast(Any, self), handler)
            invoke_hook(handler, grid, ctx)
        for entry in self._hooks.on_keyboard_hooks:
            if not keyboard_matches(keyboard, entry):
                continue
            handler = entry["handler"]
            grid = getattr(handler, "__self__", None)
            if grid is None:
                grid = resolve_hook_grid(cast(Any, self), handler)
            invoke_hook(handler, grid, ctx)
        self.pump()
        return self.render()

    def dispatch_input(self, target_id: str, value: str) -> None:
        """Sync an edited ``<input>`` value back onto its ``Text``."""
        info = self.controller.input_targets.get(target_id)
        if info is None:
            return
        from xnano._types import get_input_text

        grid, field_name = info
        text = get_input_text(grid, field_name)
        if text is not None:
            text.content = value
            text.cursor = len(value)
        self.pump()

    def dispatch_tick(self) -> str:
        """Run one poll tick (interval-gated hooks), re-render."""
        self.pump()
        return self.render()

    def dispatch_request(
        self,
        method: HttpMethod,
        path: str,
    ) -> str:
        """Fire matching ``@on_get_request`` / ``@on_post_request`` hooks, then re-render.

        Args:
            method: HTTP method of the request.
            path: Normalized request path (leading slash).

        Returns:
            A fresh HTML fragment for the session grid.
        """
        # Ensure request hooks from the root grid are registered even
        # before the first paint (e.g. pure API-style POSTs).
        self._collect_request_hooks(self.grid)

        from xnano._dispatch import invoke_hook

        ctx = self._make_context()
        for entry in self._request_hooks:
            if entry["method"] != method or entry["path"] != path:
                continue
            handler = entry["handler"]
            grid = getattr(handler, "__self__", None)
            if grid is None:
                grid = self.grid
            invoke_hook(handler, grid, ctx)
        self.pump()
        return self.render()

    def poll_interval_ms(self) -> int | None:
        """Return the htmx poll interval, or ``None`` when not needed.

        Polling is only wired when tick/state/field hooks exist; the
        interval is the smallest positive ``@on_tick`` interval
        (defaulting to one second) clamped to at least 100ms.
        """
        hooks = self._hooks
        if not (
            hooks.on_tick_hooks or hooks.on_state_hooks or hooks.on_field_hooks
        ):
            return None
        intervals = [
            entry["interval"]
            for entry in hooks.on_tick_hooks
            if entry["interval"] > 0
        ]
        interval = min(intervals) if intervals else 1000
        return max(100, interval)

    def wants_keyboard(self) -> bool:
        """Whether the page should capture browser keydown events."""
        return bool(
            self._hooks.on_keyboard_hooks or self._hooks.on_event_hooks
        )


_KEYBOARD_SCRIPT = """
<script>
document.addEventListener("keydown", function (event) {
  var tag = event.target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") { return; }
  var named = {
    " ": "space", "Escape": "esc", "Enter": "enter",
    "Backspace": "backspace", "Tab": "tab", "Delete": "delete",
    "ArrowUp": "up", "ArrowDown": "down",
    "ArrowLeft": "left", "ArrowRight": "right",
    "Home": "home", "End": "end",
    "PageUp": "pageup", "PageDown": "pagedown", "Insert": "insert"
  };
  var key = named[event.key];
  if (!key) {
    if (event.key.length === 1) { key = event.key.toLowerCase(); }
    else { return; }
  }
  var mods = [];
  if (event.ctrlKey) { mods.push("ctrl"); }
  if (event.altKey) { mods.push("alt"); }
  if (event.shiftKey) { mods.push("shift"); }
  var binding = mods.concat([key]).join("+");
  htmx.ajax(
    "POST",
    "/xnano/key?binding=" + encodeURIComponent(binding),
    {target: "#xnano-app", swap: "innerHTML"}
  );
});
</script>
"""


_WebSession = WebSession


__all__ = ("WebSession",)
