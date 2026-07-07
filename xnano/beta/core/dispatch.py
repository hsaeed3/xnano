"""xnano.beta.core.dispatch"""

from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

from xnano.beta.hooks import (
    _EventHooksRegistry,
    _OnKeyboardHookFunctionEntry,
    _OnMouseHookFunctionEntry,
    _OnStateHookFunctionEntry,
    _OnTickHookFunctionEntry,
)
from xnano.beta.utils.core import (
    evaluate_state_expression,
    get_first_function_parameter_type,
    get_function_extra_parameter_count,
)
from xnano.beta.utils.native_types import get_area_from_native_rect

if TYPE_CHECKING:
    from xnano.beta.context import Context
    from xnano.beta.grid import Grid, _GridSlideCapture
    from xnano.beta.terminal import Terminal
    from xnano.beta.types import Area, Coordinate


def invoke_hook(handler: Any, bound_self: Any, ctx: "Context[Any]") -> Any:
    """Invoke ``handler`` with the right arity."""
    from xnano.beta.context import Context as ContextClass

    bound_instance = getattr(handler, "__self__", None)
    if bound_instance is not None:
        function = getattr(handler, "__func__", handler)
        if get_function_extra_parameter_count(function) == 0:
            return handler()
        return handler(ctx)

    param_type = get_first_function_parameter_type(handler)
    if param_type is ContextClass:
        return handler(ctx)
    if bound_self is not None:
        return handler(bound_self, ctx)
    return handler(ctx)


def grid_clamp_slide_position(
    parent_area: "Area",
    slot_area: "Area",
    slide_axes: tuple[str, ...],
    position: "Coordinate",
) -> "Coordinate":
    x = position[0]
    y = position[1]
    if "x" in slide_axes:
        x = max(0, min(x, parent_area.width - slot_area.width))
    if "y" in slide_axes:
        y = max(0, min(y, parent_area.height - slot_area.height))
    return (x, y)


def resolve_grid_mouse_handler(grid: "Grid", field_name: str) -> Any | None:
    """Return the field-bound mouse handler for ``field_name`` on ``grid``."""
    for cls in type(grid).__mro__:
        if not (isinstance(cls, type)):
            continue
        from xnano.beta.grid import Grid as GridClass

        if not issubclass(cls, GridClass):
            continue
        handlers = cls.__dict__.get("_grid_field_handlers")
        if not isinstance(handlers, dict) or field_name not in handlers:
            continue
        attr = handlers[field_name]
        if not hasattr(attr, _EventHooksRegistry.ON_MOUSE_HOOK_ATTR):
            return None
        return attr.__get__(grid, cls)
    return None


def field_mouse_handler_matches(handler: Any, mouse: Any) -> bool:
    mouse_filter = getattr(
        handler,
        _EventHooksRegistry.ON_MOUSE_FILTER_ATTR,
        (("left",), "press"),
    )
    buttons, wanted_kind = mouse_filter
    if wanted_kind is not None and mouse.kind != wanted_kind:
        return False
    if buttons and mouse.button not in buttons:
        return False
    return True


def keyboard_matches(kbd: Any, entry: "_OnKeyboardHookFunctionEntry") -> bool:
    bindings: tuple = entry["bindings"]
    wanted_kind = entry["kind"]
    if wanted_kind is not None and kbd.kind != wanted_kind:
        return False
    if not bindings:
        return True
    for binding in bindings:
        if binding is None:
            return True
        try:
            if kbd.matches(binding):
                return True
        except Exception:
            pass
    return False


def mouse_matches(mouse: Any, entry: "_OnMouseHookFunctionEntry") -> bool:
    buttons: tuple = entry["buttons"]
    wanted_kind = entry["kind"]
    if wanted_kind is not None and mouse.kind != wanted_kind:
        return False
    if not buttons:
        return True
    return mouse.button in buttons


def resolve_hook_grid(terminal: "Terminal[Any]", handler: Any) -> Any | None:
    owner_name = getattr(handler, "__qualname__", "").split(".", 1)[0]
    for grid in reversed(terminal._attached_frame_grids):
        if type(grid).__name__ == owner_name:
            return grid
    return None


def render_frame(terminal: "Terminal[Any]", root: Any) -> None:
    from xnano.beta.grid import Grid

    terminal._field_hits.clear()
    terminal._attached_frame_grids.clear()
    terminal._mouse_geometry_active = (
        terminal.mouse_events
        and isinstance(root, Grid)
        and root._grid_needs_mouse_geometry()
    )
    sess = terminal.session
    sess.begin_frame()
    viewport = get_area_from_native_rect(sess.get_native_viewport_area())
    if isinstance(root, Grid):
        root._grid_build_frame(viewport, sess)
    sess.commit_requests()


def pump_events(terminal: "Terminal[Any]") -> None:
    from xnano.beta.context import Context
    from xnano.beta.events import Event

    core_event = terminal.session.poll_core_event(
        timeout=terminal.tick_interval
    )
    while core_event is not None:
        wrapped = Event(core_event)
        ctx = Context(event=wrapped, terminal=terminal, state=terminal.state)
        dispatch_hooks(terminal, ctx)
        if wrapped.is_mouse_event() and terminal._mouse_geometry_active:
            dispatch_field_mouse(terminal, ctx)
        core_event = terminal.session.poll_core_event(timeout=-1)


def pump_tick(terminal: "Terminal[Any]") -> None:
    from xnano.beta.context import Context

    now = time.monotonic() * 1000
    ctx = Context(event=None, terminal=terminal, state=terminal.state)
    for entry in terminal._hooks.on_tick_hooks:
        interval = entry["interval"]
        handler = entry["handler"]
        if interval > 0:
            elapsed = now - entry["last_fire_ms"]
            if elapsed < interval:
                continue
        grid = resolve_hook_grid(terminal, handler)
        invoke_hook(handler, grid, ctx)
        entry["last_fire_ms"] = now
    for entry in terminal._hooks.on_state_hooks:
        expression = entry["expression"]
        handler = entry["handler"]
        if evaluate_state_expression(expression, terminal.state):
            grid = resolve_hook_grid(terminal, handler)
            invoke_hook(handler, grid, ctx)


def dispatch_hooks(terminal: "Terminal[Any]", ctx: "Context[Any]") -> None:
    event = ctx.event
    if event is None:
        return

    for handler in terminal._hooks.on_event_hooks:
        grid = resolve_hook_grid(terminal, handler)
        invoke_hook(handler, grid, ctx)

    if event.is_keyboard_event():
        kbd = event.keyboard_event
        if kbd is not None:
            for entry in terminal._hooks.on_keyboard_hooks:
                if not keyboard_matches(kbd, entry):
                    continue
                handler = entry["handler"]
                grid = resolve_hook_grid(terminal, handler)
                invoke_hook(handler, grid, ctx)

    elif event.is_mouse_event():
        mouse = event.mouse_event
        if mouse is not None:
            for entry in terminal._hooks.on_mouse_hooks:
                if not mouse_matches(mouse, entry):
                    continue
                handler = entry["handler"]
                grid = resolve_hook_grid(terminal, handler)
                invoke_hook(handler, grid, ctx)

    elif event.is_resize_event():
        for handler in terminal._hooks.on_resize_hooks:
            grid = resolve_hook_grid(terminal, handler)
            invoke_hook(handler, grid, ctx)

    elif event.is_clipboard_event():
        for handler in terminal._hooks.on_clipboard_hooks:
            grid = resolve_hook_grid(terminal, handler)
            invoke_hook(handler, grid, ctx)

    elif event.is_focus_event():
        for handler in terminal._hooks.on_focus_hooks:
            grid = resolve_hook_grid(terminal, handler)
            invoke_hook(handler, grid, ctx)


def dispatch_field_mouse(
    terminal: "Terminal[Any]", ctx: "Context[Any]"
) -> None:
    from xnano.beta.grid import _GridSlideCapture

    mouse = ctx.event.mouse_event if ctx.event is not None else None
    if mouse is None or mouse.kind not in {"press", "drag", "release"}:
        return

    capture = terminal._slide_capture
    if capture is not None:
        if mouse.kind == "release":
            terminal._slide_capture = None
        elif mouse.kind == "drag":
            update_slide_capture(terminal, capture, mouse)
        handler = resolve_grid_mouse_handler(capture.grid, capture.field_name)
        if handler is not None and field_mouse_handler_matches(handler, mouse):
            invoke_hook(handler, capture.grid, ctx)
        return

    coordinate = (mouse.x, mouse.y)
    for hit in reversed(terminal._field_hits):
        if not hit.area.contains(coordinate):
            continue
        if mouse.kind == "press" and hit.slide_axes:
            terminal._slide_capture = _GridSlideCapture(
                grid=hit.grid,
                field_name=hit.field_name,
                parent_area=hit.parent_area,
                slot_area=hit.slot_area,
                grab_x=mouse.x - hit.area.x,
                grab_y=mouse.y - hit.area.y,
                slide_axes=hit.slide_axes,
            )
        handler = resolve_grid_mouse_handler(hit.grid, hit.field_name)
        if handler is not None and field_mouse_handler_matches(handler, mouse):
            invoke_hook(handler, hit.grid, ctx)
        return


def update_slide_capture(
    terminal: "Terminal[Any]", capture: Any, mouse: Any
) -> None:
    position = capture.grid._grid_field_position(capture.field_name)
    x = position[0]
    y = position[1]
    if "x" in capture.slide_axes:
        x = mouse.x - capture.grab_x - capture.parent_area.x
    if "y" in capture.slide_axes:
        y = mouse.y - capture.grab_y - capture.parent_area.y
    clamped = grid_clamp_slide_position(
        capture.parent_area,
        capture.slot_area,
        capture.slide_axes,
        position=(x, y),
    )
    capture.grid.__dict__.setdefault("_grid_field_positions", {})[
        capture.field_name
    ] = clamped


def track_frame_grid(terminal: "Terminal[Any]", grid: Any) -> None:
    grid_class = type(grid)
    if grid_class not in terminal._attached_grid_classes:
        collected = _EventHooksRegistry.from_component_class(grid_class)
        merge_hooks(terminal, collected, grid=grid)
        terminal._attached_grid_classes.add(grid_class)
    terminal._attached_frame_grids.append(grid)
    terminal._attached_grids.add(id(grid))


def merge_hooks(
    terminal: "Terminal[Any]", other: _EventHooksRegistry, grid: Any = None
) -> None:
    terminal._hooks.on_event_hooks.extend(other.on_event_hooks)
    terminal._hooks.on_resize_hooks.extend(other.on_resize_hooks)
    terminal._hooks.on_clipboard_hooks.extend(other.on_clipboard_hooks)
    terminal._hooks.on_focus_hooks.extend(other.on_focus_hooks)
    terminal._hooks.on_poll_hooks.extend(other.on_poll_hooks)

    for entry in other.on_keyboard_hooks:
        handler = entry["handler"]
        if grid is not None:
            name = getattr(handler, "__name__", None)
            if name and hasattr(grid, name):
                handler = getattr(grid, name)
        terminal._hooks.on_keyboard_hooks.append(
            _OnKeyboardHookFunctionEntry(
                bindings=entry["bindings"],
                kind=entry["kind"],
                handler=handler,
            )
        )

    for entry in other.on_mouse_hooks:
        handler = entry["handler"]
        if (
            getattr(handler, _EventHooksRegistry.ON_MOUSE_FIELD_ATTR, None)
            is not None
        ):
            continue
        if grid is not None:
            name = getattr(handler, "__name__", None)
            if name and hasattr(grid, name):
                handler = getattr(grid, name)
        terminal._hooks.on_mouse_hooks.append(
            _OnMouseHookFunctionEntry(
                buttons=entry["buttons"],
                kind=entry["kind"],
                handler=handler,
            )
        )

    for entry in other.on_tick_hooks:
        handler = entry["handler"]
        if grid is not None:
            name = getattr(handler, "__name__", None)
            if name and hasattr(grid, name):
                handler = getattr(grid, name)
        terminal._hooks.on_tick_hooks.append(
            _OnTickHookFunctionEntry(
                interval=entry["interval"],
                handler=handler,
                last_fire_ms=0.0,
            )
        )

    for entry in other.on_state_hooks:
        handler = entry["handler"]
        if grid is not None:
            name = getattr(handler, "__name__", None)
            if name and hasattr(grid, name):
                handler = getattr(grid, name)
        terminal._hooks.on_state_hooks.append(
            _OnStateHookFunctionEntry(
                expression=entry["expression"],
                handler=handler,
            )
        )


def drain_pending_hooks(terminal: "Terminal[Any]") -> None:
    from xnano.beta.hooks import _PENDING_HOOKS

    for handler in _PENDING_HOOKS:
        terminal._hooks.register_hook(handler)
    _PENDING_HOOKS.clear()


def register_default_hooks(terminal: "Terminal[Any]") -> None:
    if terminal._default_hooks_registered:
        return
    from xnano.beta.exceptions import Exit

    def _handle_ctrl_c(ctx: "Context[Any]") -> None:
        if ctx.terminal is not None:
            ctx.terminal.request_exit()
        raise Exit()

    setattr(_handle_ctrl_c, _EventHooksRegistry.ON_KEYBOARD_HOOK_ATTR, True)
    setattr(
        _handle_ctrl_c,
        _EventHooksRegistry.ON_KEYBOARD_FILTER_ATTR,
        (("ctrl+c",), None),
    )
    terminal._hooks.on_keyboard_hooks.append(
        _OnKeyboardHookFunctionEntry(
            bindings=("ctrl+c",),
            kind=None,
            handler=_handle_ctrl_c,
        )
    )
    terminal._default_hooks_registered = True
