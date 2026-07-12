"""xnano._dispatch

---

Shared event, state, field, poll, and tick dispatch for hosts.
"""

from __future__ import annotations

import inspect
import logging
import time
from typing import TYPE_CHECKING, Any, Awaitable, Coroutine, Sequence, cast

from xnano._core_bindings import get_area_from_native_rect
from xnano._function_hooks import (
    _EventHooksRegistry,
    _OnFieldHookFunctionEntry,
    _OnFocusHookFunctionEntry,
    _OnKeyboardHookFunctionEntry,
    _OnMouseHookFunctionEntry,
    _OnPollHookFunctionEntry,
    _OnStateHookFunctionEntry,
    _OnTickHookFunctionEntry,
)
from xnano._introspection import (
    evaluate_state_expression,
    get_function_extra_parameter_count,
)
from xnano.core.exceptions import Exit


if TYPE_CHECKING:
    from xnano._function_hooks import PollWhen
    from xnano._types import Area, Coordinate
    from xnano.context import Context
    from xnano.grid import BaseGrid
    from xnano.tui.terminal import Terminal


_logger = logging.getLogger("xnano.hooks")
_KEYBOARD_ACTION_CACHE: dict[tuple[tuple[Any, ...], Any], Any] = {}
_MOUSE_ACTION_CACHE: dict[tuple[tuple[Any, ...], Any], Any] = {}


class _KeyboardEventShell:
    """Allocation-light event view used by cached keyboard Actions."""

    __slots__ = ("keyboard_event",)

    def __init__(self, keyboard_event: Any) -> None:
        self.keyboard_event = keyboard_event

    def is_keyboard_event(self) -> bool:
        return True


class _MouseEventShell:
    """Allocation-light event view used by cached mouse Actions."""

    __slots__ = ("mouse_event",)

    def __init__(self, mouse_event: Any) -> None:
        self.mouse_event = mouse_event

    def is_mouse_event(self) -> bool:
        return True


def run_awaitable(awaitable: Awaitable[Any]) -> Any:
    """Drive an async hook result to completion on a free event loop.

    Args:
        awaitable: A coroutine or other awaitable returned by a hook.

    Returns:
        The awaitable's result.

    Raises:
        RuntimeError: If called while an asyncio event loop is already
            running on this thread (the sync TUI loop cannot nest
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
        "already active on this thread; call Terminal.run() from a "
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
    ``SystemExit``) are logged at ERROR and re-raised so the terminal
    run loop can restore the host terminal on the way out.
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


def grid_clamp_slide_position(
    parent_area: "Area",
    slot_area: "Area",
    slide_axes: tuple[str, ...],
    position: "Coordinate",
) -> "Coordinate":
    from xnano.grid import _grid_clamp_slide_position

    return _grid_clamp_slide_position(
        parent_area, slot_area, list(slide_axes), position
    )


def resolve_grid_mouse_handler(
    grid: "BaseGrid", field_name: str
) -> Any | None:
    """Return the field-bound mouse handler for ``field_name`` on ``grid``."""
    from xnano.grid import _resolve_grid_mouse_handler

    return _resolve_grid_mouse_handler(grid, field_name)


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
    """Match a keyboard payload against a hook entry via ``Action.matches``.

    Builds a tiny event shell around ``kbd`` so Actions remain the single
    matching implementation for both device input and performed actions.
    """
    from xnano.core.actions import Action

    cache_key = (entry["bindings"], entry["kind"])
    action = _KEYBOARD_ACTION_CACHE.get(cache_key)
    if action is None:
        action = Action.keyboard(*entry["bindings"], kind=entry["kind"])
        _KEYBOARD_ACTION_CACHE[cache_key] = action
    return action.matches(_KeyboardEventShell(kbd))


def mouse_matches(mouse: Any, entry: "_OnMouseHookFunctionEntry") -> bool:
    """Match a mouse payload against a hook entry via ``Action.matches``."""
    from xnano.core.actions import Action

    cache_key = (entry["buttons"], entry["kind"])
    action = _MOUSE_ACTION_CACHE.get(cache_key)
    if action is None:
        action = Action.mouse(*cast(Any, entry["buttons"]), kind=entry["kind"])
        _MOUSE_ACTION_CACHE[cache_key] = action
    return action.matches(_MouseEventShell(mouse))


def resolve_hook_grid(terminal: "Terminal[Any]", handler: Any) -> Any | None:
    """Return the grid instance a hook handler belongs to, if any.

    Bound methods carry their own instance. Unbound handlers fall back to
    matching the class named in their ``__qualname__`` against the frame's
    painted grids (including base classes, so a hook declared on a parent
    grid class resolves for a subclass instance).
    """
    bound_instance = getattr(handler, "__self__", None)
    if bound_instance is not None:
        return bound_instance
    owner_name = getattr(handler, "__qualname__", "").split(".", 1)[0]
    if not owner_name:
        return None
    for grid in reversed(terminal._attached_frame_grids):
        if any(base.__name__ == owner_name for base in type(grid).__mro__):
            return grid
    return None


def measure_renderable(root: Any) -> tuple[int, int]:
    """Return ``(width, height)`` for a non-BaseGrid renderable from its content.

    Measurement is session-independent, so this may be called before a
    terminal session is entered (to size an inline viewport, for example).

    Args:
        root: A renderable value — a component, render node, string, or any
            value with a string representation.

    Returns:
        The measured ``(width, height)`` in terminal cells.
    """
    from xnano._types import Area
    from xnano.components.abstract import (
        AbstractComponent,
        ComponentRenderContext,
    )
    from xnano.tui.nodes import AbstractTerminalNode

    if isinstance(root, AbstractComponent):
        ctx = ComponentRenderContext(area=Area(x=0, y=0, width=0, height=0))
        if type(root).get_size is not AbstractComponent.get_size:
            size = root.get_size(ctx)
            return size.width, size.height
        node = root.get_terminal_node(ctx)
        if node is not None:
            size = node.measure()
            return size.width, size.height
        return 0, 0

    if isinstance(root, AbstractTerminalNode):
        size = root.measure()
        return size.width, size.height

    text = root if isinstance(root, str) else str(root)
    lines = text.splitlines() or [""]
    width = max((len(line) for line in lines), default=0)
    return width, len(lines)


def field_frame(field: Any) -> Any | None:
    """Build a ``Frame`` from a ``GridFieldInfo``'s chrome, or ``None``.

    Args:
        field: The ``GridFieldInfo`` describing border, padding, and title, or
            ``None``.

    Returns:
        A ``Frame`` when the field defines any chrome, otherwise ``None``.
    """
    from xnano._types import frame_from_field

    return frame_from_field(field)


def measure_renderable_in_field(
    renderable: Any, field: Any
) -> tuple[int, int]:
    """Return ``(width, height)`` for a renderable including field chrome.

    Args:
        renderable: The renderable value to measure.
        field: The ``GridFieldInfo`` whose border/padding overhead is added to
            the measured content size, or ``None``.

    Returns:
        The measured ``(width, height)`` in terminal cells including any frame
        overhead.
    """
    from xnano._core_bindings import frame_length_overhead

    width, height = measure_renderable(renderable)
    frame = field_frame(field)
    if frame is not None:
        width += frame_length_overhead(frame, "horizontal")
        height += frame_length_overhead(frame, "vertical")
    return width, height


def measure_renderables_height(
    renderables: "Sequence[Any]", field: Any = None
) -> int:
    """Return the summed content height of a sequence of renderables.

    Args:
        renderables: The renderable values to measure.
        field: Optional ``GridFieldInfo`` whose border/padding overhead is
            included in each renderable's measured height.

    Returns:
        The total measured height in terminal rows (at least ``0``).
    """
    total = 0
    for renderable in renderables:
        _, height = measure_renderable_in_field(renderable, field)
        total += max(height, 0)
    return total


def resolve_root_area(
    terminal: "Terminal[Any]",
    viewport: "Area",
    *,
    renderables: "Sequence[Any] | None" = None,
    field: Any = None,
):
    """Constrain the viewport to the root box's width sizing.

    The root box's height is already baked into the viewport (inline height or
    fullscreen), so only its width sizing needs to be resolved here.

    Runs every frame, so the common cases short-circuit before any content
    measurement: fill and unbounded ``fit`` widths let the content size itself
    (each renderable is clamped to the viewport downstream), and fixed
    ``cells`` / ``percent`` / ``ratio`` widths never need to measure content.

    Args:
        terminal: The active terminal (holds the resolved root width sizing).
        viewport: The full viewport area to constrain.
        renderables: The inline renderables being drawn, measured only for a
            bounded ``fit`` width. ``None`` for a ``BaseGrid`` (whose intrinsic
            width is not measured, so it fills the viewport width).
        field: The shared style field for ``renderables`` (its chrome is
            included when measuring).

    Returns:
        The root box ``Area`` within the viewport (``viewport`` itself when no
        constraint applies).
    """
    sizing = terminal._root_width_sizing
    if sizing is None or sizing.is_fill:
        return viewport
    # Unbounded ``fit`` needs no root constraint — the content already sizes
    # itself, and re-measuring here would duplicate the per-renderable pass.
    if sizing.is_fit and sizing.minimum is None and sizing.maximum is None:
        return viewport

    content_width = 0
    if sizing.is_fit:
        if renderables is None:
            return viewport
        content_width = max(
            (
                measure_renderable_in_field(renderable, field)[0]
                for renderable in renderables
            ),
            default=0,
        )
        if content_width <= 0:
            return viewport

    width = sizing.resolve(viewport.width, content_width)
    width = max(1, min(width, viewport.width))
    if width >= viewport.width:
        return viewport

    from xnano._types import Area

    return Area(
        x=viewport.x, y=viewport.y, width=width, height=viewport.height
    )


def render_frame(
    terminal: "Terminal[Any]",
    root: Any = None,
    *,
    renderables: "Sequence[Any] | None" = None,
    field: Any = None,
) -> None:
    """Paint one frame.

    A ``BaseGrid`` ``root`` drives the full layout engine; otherwise the frame is a
    sequence of inline ``renderables`` sharing one style ``field``, stacked
    downward from the root box's top-left corner. A lone ``root`` renderable is
    treated as a one-item inline sequence.
    """
    from xnano._types import Area
    from xnano.fields import GridFieldInfo
    from xnano.grid import BaseGrid

    is_grid = isinstance(root, BaseGrid)
    terminal._field_hits.clear()
    terminal._attached_frame_grids.clear()
    terminal._mouse_geometry_active = (
        terminal.mouse_events and is_grid and root._grid_needs_mouse_geometry()
    )
    sess = terminal.session
    sess.begin_viewport_frame()
    viewport = get_area_from_native_rect(sess.get_native_viewport_area())

    if is_grid:
        from xnano._types import (
            FieldFocus,
            ensure_default_field_focus,
            is_input_text,
            place_cursor_for_focus,
            sync_input_focus_flags,
        )

        # Re-register the root after the per-frame clear so focus walking and
        # hook grid resolution still see the live tree. Nested grids re-attach
        # from ``TerminalController.paint_field_slot`` while painting.
        track_frame_grid(terminal, root)

        # Seed focus before paint so the caret/placeholder render correctly
        # on the first frame.
        if getattr(terminal, "_field_focus", None) is None:
            fields = getattr(type(root), "_grid_fields", {}) or {}
            for field_name in fields:
                value = getattr(root, field_name, None)
                if is_input_text(value):
                    terminal._field_focus = FieldFocus(
                        grid=root, field_name=field_name
                    )
                    cast(Any, value)._input_focused = True
                    break
        else:
            current = terminal._field_focus
            text = getattr(current.grid, current.field_name, None)
            if is_input_text(text):
                cast(Any, text)._input_focused = True

        root_area = resolve_root_area(terminal, viewport)
        root._grid_build_frame(root_area, sess)
        _paint_stage_overlay(terminal, sess, viewport)
        sess.commit_requests()
        ensure_default_field_focus(terminal)
        sync_input_focus_flags(terminal)
        place_cursor_for_focus(terminal)
        return

    # Inline content: the root box may be offset from the screen origin (inline
    # sessions), so stack content downward from its own top-left corner.
    items = renderables if renderables is not None else ()
    if not items and root is not None:
        items = (root,)
    slot_field = field if field is not None else GridFieldInfo()
    root_area = resolve_root_area(
        terminal, viewport, renderables=items, field=slot_field
    )
    frame = field_frame(slot_field)
    offset_y = 0
    for renderable in items:
        width, height = measure_renderable_in_field(renderable, slot_field)
        width = min(width, root_area.width) if width > 0 else root_area.width
        remaining = root_area.height - offset_y
        height = min(height, remaining) if height > 0 else remaining
        if height <= 0:
            break
        area = Area(
            x=root_area.x,
            y=root_area.y + offset_y,
            width=width,
            height=height,
        )
        if frame is not None:
            inner = sess.paint_frame(area, frame)
            sess.paint_field_slot(renderable, inner, slot_field)
        else:
            sess.paint_field_slot(renderable, area, slot_field)
        offset_y += height

    _paint_stage_overlay(terminal, sess, viewport)
    sess.commit_requests()


def _paint_stage_overlay(
    terminal: "Terminal[Any]",
    sess: Any,
    viewport: "Area",
) -> None:
    """Composite Stage wireframe/paint overlays after content paint.

    Overlay-only: never rewrites field content. Wireframe and
    CellCanvas paints land at a high z on top of the live grid.
    """
    stage = getattr(terminal, "stage", None)
    if stage is None:
        return
    # Keep stage lattice size aligned with the viewport for wireframes.
    try:
        from xnano._types import Size

        stage.set_size(Size(width=viewport.width, height=viewport.height))
    except Exception:
        pass
    canvas = None
    if stage.is_wireframe():
        canvas = stage.build_wireframe_canvas()
    overlay = stage.take_overlay()
    if overlay is not None:
        canvas = overlay
    if canvas is None:
        return
    render_content = getattr(sess, "render_content", None)
    if render_content is not None:
        render_content(viewport, canvas, z=10_000)
    stage.clear_paints()


def pump_poll(
    terminal: "Terminal[Any]",
    when: "PollWhen",
) -> None:
    """Fire ``@on_poll`` handlers registered for ``when``."""
    from xnano.context import Context

    if not terminal._hooks.on_poll_hooks:
        return
    ctx = Context(event=None, terminal=terminal, state=terminal.state)
    for entry in terminal._hooks.on_poll_hooks:
        if entry["when"] != when:
            continue
        handler = entry["handler"]
        grid = getattr(handler, "__self__", None)
        if grid is None:
            grid = resolve_hook_grid(terminal, handler)
        invoke_hook(handler, grid, ctx)


def pump_events(terminal: "Terminal[Any]") -> None:
    from xnano.context import Context
    from xnano.events import Event

    # ``poll_core_event(timeout=0)`` blocks until input arrives, which would
    # stall the render loop for a ``Terminal(tick_interval=0)`` — clamp to a
    # 1ms wait so ticks and repaints keep flowing.
    core_event = terminal.session.poll_core_event(
        timeout=max(1, terminal.tick_interval)
    )
    if core_event is None:
        # Idle: the blocking poll returned no input within the tick window.
        pump_poll(terminal, "idle")
        return
    while core_event is not None:
        kind = core_event.kind_str()
        hooks = terminal._hooks
        has_consumers = bool(hooks.on_event_hooks)
        if kind == "key":
            has_consumers = has_consumers or bool(hooks.on_keyboard_hooks)
        elif kind == "mouse":
            has_consumers = (
                has_consumers
                or terminal._mouse_geometry_active
                or bool(hooks.on_mouse_hooks)
            )
        elif kind == "resize":
            has_consumers = has_consumers or bool(hooks.on_resize_hooks)
        elif kind == "paste":
            has_consumers = (
                has_consumers
                or terminal._field_focus is not None
                or bool(hooks.on_clipboard_hooks)
            )
        elif kind in ("focus_gained", "focus_lost"):
            has_consumers = has_consumers or bool(hooks.on_focus_hooks)
        if not has_consumers:
            core_event = terminal.session.poll_core_event(timeout=-1)
            continue
        wrapped = Event(core_event)
        ctx = Context(event=wrapped, terminal=terminal, state=terminal.state)
        dispatch_hooks(terminal, ctx)
        if wrapped.is_mouse_event() and terminal._mouse_geometry_active:
            dispatch_field_mouse(terminal, ctx)
        core_event = terminal.session.poll_core_event(timeout=-1)


def pump_tick(terminal: "Terminal[Any]") -> None:
    hooks = terminal._hooks
    if not (
        hooks.on_tick_hooks or hooks.on_state_hooks or hooks.on_field_hooks
    ):
        return

    from xnano.context import Context

    now = time.monotonic() * 1000 if hooks.on_tick_hooks else 0.0
    ctx: Context[Any] | None = None
    for entry in hooks.on_tick_hooks:
        interval = entry["interval"]
        handler = entry["handler"]
        if interval > 0 and entry["last_fire_ms"] is not None:
            elapsed = now - entry["last_fire_ms"]
            if elapsed < interval:
                continue
        grid = resolve_hook_grid(terminal, handler)
        if ctx is None:
            ctx = Context(event=None, terminal=terminal, state=terminal.state)
        invoke_hook(handler, grid, ctx)
        entry["last_fire_ms"] = now
    for entry in hooks.on_state_hooks:
        expression = entry["expression"]
        handler = entry["handler"]
        if evaluate_state_expression(expression, terminal.state):
            grid = resolve_hook_grid(terminal, handler)
            if ctx is None:
                ctx = Context(
                    event=None, terminal=terminal, state=terminal.state
                )
            invoke_hook(handler, grid, ctx)
    for entry in hooks.on_field_hooks:
        expression = entry["expression"]
        handler = entry["handler"]
        # Prefer the bound instance over resolve_hook_grid — the latter
        # matches by class name and can't distinguish multiple instances of
        # the same grid class registered on the same terminal.
        grid = getattr(handler, "__self__", None)
        if grid is None:
            grid = resolve_hook_grid(terminal, handler)
        if grid is not None and evaluate_state_expression(expression, grid):
            if ctx is None:
                ctx = Context(
                    event=None, terminal=terminal, state=terminal.state
                )
            invoke_hook(handler, grid, ctx)


def _handle_focus_navigation(terminal: "Terminal[Any]", keyboard: Any) -> bool:
    """Handle tab / backtab for field focus. Returns True if consumed.

    Only reserves the key when a field actually receives focus — with no
    focusable fields (or only one, already focused), tab/backtab fall
    through to the app's own ``@on_keyboard("tab")`` hooks.
    """
    from xnano._types import cycle_field_focus

    if keyboard.matches("tab"):
        return cycle_field_focus(terminal, reverse=False)
    if keyboard.matches("backtab"):
        return cycle_field_focus(terminal, reverse=True)
    return False


def _handle_focused_text_input(
    terminal: "Terminal[Any]", keyboard: Any
) -> bool:
    """Feed a key to the focused editable Text. Returns True if consumed."""
    from xnano._types import apply_text_keyboard, focused_input_text

    text = focused_input_text(terminal)
    if text is None:
        return False
    handle = getattr(text, "handle_keyboard", None)
    if callable(handle):
        return bool(handle(keyboard))
    return apply_text_keyboard(text, keyboard)


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
            # Field focus navigation (tab) is reserved by the framework.
            if _handle_focus_navigation(terminal, kbd):
                return
            # Editable Text consumes character/edit keys while focused.
            if _handle_focused_text_input(terminal, kbd):
                return
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
        from xnano._types import focused_input_text

        text = focused_input_text(terminal)
        if text is not None and isinstance(text.content, str):
            paste = (
                event.clipboard_event.text
                if event.clipboard_event is not None
                else None
            )
            if paste:
                position = (
                    text.cursor
                    if text.cursor is not None
                    else len(text.content)
                )
                position = max(0, min(position, len(text.content)))
                text.content = (
                    text.content[:position] + paste + text.content[position:]
                )
                text.cursor = position + len(paste)
        for handler in terminal._hooks.on_clipboard_hooks:
            grid = resolve_hook_grid(terminal, handler)
            invoke_hook(handler, grid, ctx)

    elif event.is_focus_event():
        focus = event.focus_event
        focus_kind = focus.kind if focus is not None else None
        for entry in terminal._hooks.on_focus_hooks:
            # Terminal-window focus hooks only (field is None).
            if entry["field"] is not None:
                continue
            kind_filter = entry["kind"]
            if kind_filter is not None:
                if focus_kind == "gained" and kind_filter != "gained":
                    continue
                if focus_kind == "lost" and kind_filter != "lost":
                    continue
            handler = entry["handler"]
            grid = resolve_hook_grid(terminal, handler)
            invoke_hook(handler, grid, ctx)


def dispatch_field_mouse(
    terminal: "Terminal[Any]", ctx: "Context[Any]"
) -> None:
    from xnano.grid import _GridSlideCapture

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
        if mouse.kind == "press":
            from xnano._types import is_input_text, set_field_focus

            value = getattr(hit.grid, hit.field_name, None)
            if is_input_text(value):
                set_field_focus(terminal, hit.grid, hit.field_name)
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
    """Register ``grid`` for this frame, merging its hooks on first sight.

    Hooks are registered once per grid *instance* and bound to it, so two
    live grids of the same class each receive their own events — a
    per-class guard would leave every instance after the first without
    hooks (or firing with the wrong ``self``). Registration is permanent
    for the terminal's lifetime; grids are meant to be stable instances,
    not rebuilt every frame.
    """
    attached = terminal._attached_grids
    if id(grid) not in attached:
        collected = _EventHooksRegistry.from_component_class(type(grid))
        merge_hooks(terminal, collected, grid=grid)
        # The strong reference keeps ``id(grid)`` unique for the life of
        # the terminal (bound hook handlers hold the instance anyway).
        attached[id(grid)] = grid
    terminal._attached_frame_grids.append(grid)


def rebind_hook_handler(handler: Any, grid: Any) -> Any:
    """Rebind an unbound handler to its ``grid`` instance method by name.

    Hooks declared on a ``BaseGrid`` subclass are captured as unbound functions
    at class-creation time; once a live ``grid`` instance exists, the same
    handler must be looked up as a bound method on that instance so ``self``
    resolves correctly.

    Args:
        handler: The hook handler collected from the component class.
        grid: The live grid instance to rebind against, or ``None``.

    Returns:
        The bound method when ``grid`` declares an attribute of the same
        name as ``handler``; otherwise ``handler`` unchanged.
    """
    if grid is None:
        return handler
    name = getattr(handler, "__name__", None)
    if name and hasattr(grid, name):
        return getattr(grid, name)
    return handler


def merge_hooks(
    terminal: "Terminal[Any]", other: _EventHooksRegistry, grid: Any = None
) -> None:
    terminal._hooks.on_event_hooks.extend(
        rebind_hook_handler(handler, grid) for handler in other.on_event_hooks
    )
    terminal._hooks.on_resize_hooks.extend(
        rebind_hook_handler(handler, grid) for handler in other.on_resize_hooks
    )
    terminal._hooks.on_clipboard_hooks.extend(
        rebind_hook_handler(handler, grid)
        for handler in other.on_clipboard_hooks
    )

    for entry in other.on_focus_hooks:
        terminal._hooks.on_focus_hooks.append(
            _OnFocusHookFunctionEntry(
                field=entry["field"],
                kind=entry["kind"],
                handler=rebind_hook_handler(entry["handler"], grid),
            )
        )

    for entry in other.on_poll_hooks:
        terminal._hooks.on_poll_hooks.append(
            _OnPollHookFunctionEntry(
                when=entry["when"],
                handler=rebind_hook_handler(entry["handler"], grid),
            )
        )

    for entry in other.on_keyboard_hooks:
        terminal._hooks.on_keyboard_hooks.append(
            _OnKeyboardHookFunctionEntry(
                bindings=entry["bindings"],
                kind=entry["kind"],
                handler=rebind_hook_handler(entry["handler"], grid),
            )
        )

    for entry in other.on_mouse_hooks:
        handler = entry["handler"]
        if (
            getattr(handler, _EventHooksRegistry.ON_MOUSE_FIELD_ATTR, None)
            is not None
        ):
            continue
        terminal._hooks.on_mouse_hooks.append(
            _OnMouseHookFunctionEntry(
                buttons=entry["buttons"],
                kind=entry["kind"],
                handler=rebind_hook_handler(handler, grid),
            )
        )

    for entry in other.on_tick_hooks:
        terminal._hooks.on_tick_hooks.append(
            _OnTickHookFunctionEntry(
                interval=entry["interval"],
                handler=rebind_hook_handler(entry["handler"], grid),
                last_fire_ms=None,
            )
        )

    for entry in other.on_state_hooks:
        terminal._hooks.on_state_hooks.append(
            _OnStateHookFunctionEntry(
                expression=entry["expression"],
                handler=rebind_hook_handler(entry["handler"], grid),
            )
        )

    for entry in other.on_field_hooks:
        terminal._hooks.on_field_hooks.append(
            _OnFieldHookFunctionEntry(
                expression=entry["expression"],
                handler=rebind_hook_handler(entry["handler"], grid),
            )
        )


def drain_pending_hooks(terminal: "Terminal[Any]") -> None:
    from xnano._function_hooks import _PENDING_HOOKS

    for handler in _PENDING_HOOKS:
        terminal._hooks.register_hook(handler)
    _PENDING_HOOKS.clear()


def register_default_hooks(terminal: "Terminal[Any]") -> None:
    if terminal._default_hooks_registered:
        return
    from xnano.core.exceptions import Exit

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
