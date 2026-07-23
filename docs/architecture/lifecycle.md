---
title: "Event & Render Lifecycle"
icon: "lucide/refresh-cw"
---

# Event & Render Lifecycle

This page traces one iteration of the terminal run loop, from a raw key
event received by `xnano_core` through rendering the next frame. It is
intended for contributors working on `xnano`. Application-facing hook
and event behavior is documented in [Events & Hooks]{data-preview}.

The loop is implemented in `xnano._event_processing` and
`xnano._dispatch` and driven by
[`Terminal.run()`](../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal.run){data-preview}.
Each iteration polls
for an event, normalizes it, dispatches matching hooks, and renders a
frame.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: the run loop cycling through poll, normalize, dispatch, hooks, and render, then looping back to poll">
<svg viewBox="0 0 760 190" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="lcd-arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <!-- Stage boxes -->
  <g>
    <rect class="gcd-panel" x="20" y="55" width="120" height="60" rx="10" />
    <text class="gcd-label" x="80" y="90" text-anchor="middle">poll</text>

    <rect class="gcd-panel" x="168" y="55" width="120" height="60" rx="10" />
    <text class="gcd-label" x="228" y="90" text-anchor="middle">normalize</text>

    <rect class="gcd-panel" x="316" y="55" width="120" height="60" rx="10" />
    <text class="gcd-label" x="376" y="90" text-anchor="middle">dispatch</text>

    <rect class="gcd-panel" x="464" y="55" width="120" height="60" rx="10" />
    <text class="gcd-label" x="524" y="90" text-anchor="middle">hooks</text>

    <rect class="gcd-panel gcd-panel-accent" x="612" y="55" width="128" height="60" rx="10" />
    <text class="gcd-label gcd-label-accent" x="676" y="90" text-anchor="middle">render</text>
  </g>

  <!-- Forward arrows -->
  <line class="gcd-arrow" x1="140" y1="85" x2="164" y2="85" marker-end="url(#lcd-arrowhead)" />
  <line class="gcd-arrow" x1="288" y1="85" x2="312" y2="85" marker-end="url(#lcd-arrowhead)" />
  <line class="gcd-arrow" x1="436" y1="85" x2="460" y2="85" marker-end="url(#lcd-arrowhead)" />
  <line class="gcd-arrow" x1="584" y1="85" x2="608" y2="85" marker-end="url(#lcd-arrowhead)" />

  <!-- Loop-back arrow: render -> poll, next iteration -->
  <path class="gcd-z-connector" d="M676 115 C 676 160, 80 160, 80 119" marker-end="url(#lcd-arrowhead)" fill="none" />
  <text class="gcd-z-caption" x="378" y="152" text-anchor="middle">next iteration</text>
</svg>
</div>

## Polling

`pump_events()` asks the active
[`CoreSession`](../api/xnano-core/core.md){data-preview} for the
next event through `poll_core_event()`, which blocks for up to
`terminal.tick_interval` milliseconds. Three outcomes follow:

- **Nothing arrives within the window:** the poll is treated as idle,
  and `pump_poll()` fires any `@on_poll(when="idle")` hooks before the
  loop continues.
- **No hook consumes the event type:** `pump_events()`
  checks the terminal's hook registry (`terminal._hooks`) for
  interest before doing more work. For example, keyboard events check
  `on_keyboard_hooks` and resize events check `on_resize_hooks`. If the
  corresponding registry is empty, the event is dropped and polling
  continues immediately with `timeout=-1`.
- **A hook consumes the event type:** the raw
  [`CoreEvent`](../api/xnano-core/core.md){data-preview} is
  normalized and passed to `dispatch_hooks()`.

## Normalizing: native event to `Event`

Native input from `ratatui` and `crossterm` arrives through
`xnano_core.rust.native` as values such as `KeyEvent` and `MouseEvent`.
`xnano._event_processing.get_event_data_from_core_event()` converts
them to the public `xnano.events.EventData` subclasses:
`KeyboardEventData`, `MouseEventData`, `ResizeEventData`,
`ClipboardEventData`, and `FocusEventData`.

Keyboard normalization requires additional processing. A native
`KeyEvent` carries a
`code_name`, optional `char`, and modifier bits, and
`get_keyboard_binding_tuple_from_native_event()` converts that data to
the `(modifiers, key)` shape produced when a binding string such as
`"ctrl+s"` is parsed. Results are cached by `(code_name, char,
function_number, modifier_bits)` because this function runs for every
key event and the same combinations occur repeatedly.

The resulting
[`xnano.events.Event`](../api/xnano/events.md#xnano.events.Event){data-preview}
is stored in a
[`Context`](../api/xnano/context.md#xnano.context.Context){data-preview}
with the terminal and user state, then passed through the remaining
dispatch stages.

## Dispatch: matching hooks to the event

`dispatch_hooks(terminal, ctx)` in `xnano._dispatch` first runs the
terminal's `on_event_hooks`. These are the general
[`@on_event`](../api/xnano/events.md#xnano.events.on_event){data-preview}
hooks that receive every event. It then checks
`event.is_keyboard_event()`, `is_mouse_event()`, `is_resize_event()`,
`is_clipboard_event()`, or `is_focus_event()` and runs the matching
registry.

Two framework behaviors are reserved ahead of user hooks on the
keyboard branch:

1. **Tab and backtab focus navigation** (`_handle_focus_navigation`)
   consumes the key only when focus moves to a field. An
   `on_keyboard("tab")` hook still runs when no fields can receive focus.
2. **Focused focusable component** (`_handle_focused_text_input`) feeds
   the key to the component that currently holds field focus when that
   value is duck-typed as focusable — `focusable` is truthy and
   `handle_keyboard` is callable (for example
   [`Text`](../api/xnano/components/text.md#xnano.components.text.Text){data-preview}`(input=True)`).
   The component's `handle_keyboard` may consume character and edit keys
   before any user
   [`@on_keyboard`](../api/xnano/events.md#xnano.events.on_keyboard){data-preview}
   hook sees them.

Matching is implemented by
[`Action`](../api/xnano/core/actions.md#xnano.core.actions.Action){data-preview}
in `xnano.core.actions`.
`keyboard_matches()` and `mouse_matches()` build and cache an
[`Action.keyboard(...)`](../api/xnano/core/actions.md#xnano.core.actions.KeyboardAction){data-preview}
or
[`Action.mouse(...)`](../api/xnano/core/actions.md#xnano.core.actions.MouseAction){data-preview},
then call `.matches()`
against a lightweight event object. Real device input and synthetic
`host.perform(action)` calls therefore use the same matching logic.

`resolve_hook_grid()` identifies the grid instance for each dispatched
hook. Bound methods provide the instance through `__self__`. For
unbound handlers collected from a class, the function walks
`terminal._attached_frame_grids` and compares the owner in
`__qualname__` with each grid's MRO. Hooks declared on a base grid class
can therefore resolve to a live subclass instance.

## Hook collection and rebinding

Hooks are collected once per grid class, not rediscovered for each
event. `_EventHooksRegistry._get_component_class_hooks` is cached with
`functools.cache`; it walks the MRO and reads the `__xnano_on_*__`
attributes added by the `@on_*` decorators. If a subclass overrides a
method name, only the override is registered.

The cached class template contains unbound functions. The first time
`render_frame()` encounters a grid instance, `track_frame_grid()` copies
the template with `_EventHooksRegistry.from_component_class()`.
`merge_hooks()` then uses `rebind_hook_handler()` to bind each handler to
the live instance before adding it to the terminal's `_hooks` registry.
The registration lasts for the terminal session, so grid instances are
expected to remain stable across frames.

## Other pumps: tick, poll, field/state hooks

Two more pumps run inside the same loop iteration, independent of
whether an event arrived:

- `pump_tick()` fires
  [`@on_tick`](../api/xnano/events.md#xnano.events.on_tick){data-preview}
  hooks whose interval has elapsed
  (`interval=0` means every iteration), then evaluates
  [`@on_state`](../api/xnano/events.md#xnano.events.on_state){data-preview}
  /
  [`@on_field`](../api/xnano/events.md#xnano.events.on_field){data-preview}
  expressions (`evaluate_state_expression`) against shared
  state or the grid's own fields and fires any that are newly truthy.
- `pump_poll()` fires
  [`@on_poll`](../api/xnano/events.md#xnano.events.on_poll){data-preview}`(when="idle")`
  after an empty poll and
  `when="frame"` hooks every iteration regardless of events.

All three pumps call `invoke_hook()`. It resolves handler arity through
`_call_hook` and runs coroutine results through `run_awaitable` on a new
event loop because the TUI loop is synchronous. `Exit`,
`KeyboardInterrupt`, and `SystemExit` propagate so
[`Terminal.run()`](../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal.run){data-preview}
can restore the terminal before exiting. Other uncaught exceptions are
logged and re-raised.

## Rendering the next frame

After dispatch completes, `render_frame()` paints the next frame. A
[`BaseGrid`](../api/xnano/grid.md#xnano.grid.BaseGrid){data-preview}
root follows this layout path:

1. `track_frame_grid()` registers the root. Nested grids attach lazily
   as
   [`TerminalController`](../api/xnano/core/controllers/tui.md#xnano.core.controllers.tui.TerminalController){data-preview}`.paint_field_slot()`
   reaches them during
   painting.
2. The first focusable component field (duck-typed via `focusable` and
   `handle_keyboard`, for example an editable
   [`Text`](../api/xnano/components/text.md#xnano.components.text.Text){data-preview})
   receives focus on the first frame so its caret or focus chrome is
   rendered before the first key event.
3. `resolve_root_area()` constrains the viewport to the root's width
   setting. Fixed widths and bounded `fit` values require measurement;
   `fill` and unbounded `fit` values do not.
4. `root._grid_build_frame(root_area, session)` runs the grid's own
   layout engine.
   [`BaseGrid`](../api/xnano/grid.md#xnano.grid.BaseGrid){data-preview}
   walks the fields, resolves constraints,
   and paints each field slot.
5. Stage overlays (wireframe / paint canvas from `ctx.stage`) are
   composited at a high z-index without changing field content.
6. `session.commit_requests()` flushes the frame's batched paint
   requests to `xnano_core` in one call.

A non-grid root from an inline `render()` call skips the grid layout
engine. Its renderables are placed downward from the root area's
top-left corner. Each one is measured with
`measure_renderable_in_field()` and limited to the remaining viewport
height.

[Render Nodes & IR]{data-preview} describes how
[`TerminalController`](../api/xnano/core/controllers/tui.md#xnano.core.controllers.tui.TerminalController){data-preview}`.commit_requests()`
converts queued `RenderRequest`
objects into a
[`CoreRenderNode`](../api/xnano-core/core.md){data-preview} tree and
passes it to
[`CoreSession.render()`](../api/xnano-core/core.md){data-preview}.

[Events & Hooks]: ../core-concepts/events.md
[Render Nodes & IR]: render-nodes.md
