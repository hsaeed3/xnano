---
title: "Hosts, Interfaces & Controllers"
icon: "lucide/server"
---

# Hosts, Interfaces & Controllers

`xnano.core` defines the contracts shared by terminal and web hosts.
These contracts separate field state, session behavior, and backend
rendering across three classes:
[`AbstractInterface`](../api/xnano/core/interface.md#xnano.core.interface.AbstractInterface){data-preview},
[`AbstractHost`](../api/xnano/core/hosts.md#xnano.core.hosts.AbstractHost){data-preview},
and
[`AbstractController`](../api/xnano/core/controllers/abstract.md#xnano.core.controllers.abstract.AbstractController){data-preview}.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: an interface's field mutation notifying its host, which drives a controller to measure, layout, and paint">
<svg viewBox="0 0 760 170" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="hcd-arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="20" y="40" width="200" height="70" rx="10" />
  <text class="gcd-label" x="120" y="80" text-anchor="middle">interface</text>
  <text class="gcd-chrome-label" x="120" y="128" text-anchor="middle">field state, dirty notify</text>

  <rect class="gcd-panel" x="280" y="40" width="200" height="70" rx="10" />
  <text class="gcd-label" x="380" y="80" text-anchor="middle">host</text>
  <text class="gcd-chrome-label" x="380" y="128" text-anchor="middle">session, dispatch, perform</text>

  <rect class="gcd-panel gcd-panel-accent" x="540" y="40" width="200" height="70" rx="10" />
  <text class="gcd-label gcd-label-accent" x="640" y="80" text-anchor="middle">controller</text>
  <text class="gcd-chrome-label" x="640" y="128" text-anchor="middle">measure, layout, paint</text>

  <line class="gcd-arrow" x1="220" y1="75" x2="276" y2="75" marker-end="url(#hcd-arrowhead)" />
  <line class="gcd-arrow" x1="480" y1="75" x2="536" y2="75" marker-end="url(#hcd-arrowhead)" />
  <text class="gcd-z-caption" x="248" y="65" text-anchor="middle">notifies</text>
  <text class="gcd-z-caption" x="508" y="65" text-anchor="middle">drives</text>
</svg>
</div>

## `AbstractInterface`: field state

[`BaseGrid`](../api/xnano/grid.md#xnano.grid.BaseGrid){data-preview}
inherits from
[`xnano.core.interface.AbstractInterface`](../api/xnano/core/interface.md#xnano.core.interface.AbstractInterface){data-preview}
to
manage declared fields and their per-instance `FieldState` objects.
Layout remains the responsibility of
[`BaseGrid`](../api/xnano/grid.md#xnano.grid.BaseGrid){data-preview};
[`AbstractInterface`](../api/xnano/core/interface.md#xnano.core.interface.AbstractInterface){data-preview}
tracks field values and reports changes.

It has two main responsibilities:

- `_init_field_states()` allocates one `FieldState` per declared field
  (both rendered fields, `_grid_fields`, and `state=True` fields,
  `_grid_state_fields`) when an instance is constructed.
- `mark_field_dirty(name)` marks that field's state dirty, refreshes
  its cached value, and calls `_notify_field_changed()`.

`_notify_field_changed()` is best-effort. It obtains the active host from
[`xnano.core.hosts.get_active_host()`](../api/xnano/core/hosts.md#xnano.core.hosts.get_active_host){data-preview},
finds its private `_session` or
`controller` handle, and calls `notify_field_changed()` when that method
is available. Notification errors are ignored. As a result, mutating a
grid without an active host, including in a unit test, updates its state
without raising an exception.

## `AbstractHost`: shared session behavior

[`Terminal`](../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal){data-preview}
is the concrete
[`AbstractHost`](../api/xnano/core/hosts.md#xnano.core.hosts.AbstractHost){data-preview}
implementation. Live TUI sessions run a terminal directly; the web host
drives an **offscreen**
[`Terminal`](../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal){data-preview}
through
[`WebRenderer`](../api/xnano/web/render.md#xnano.web.render.WebRenderer){data-preview}
and streams its cells to the browser. In both cases the host surface that
dispatch, fields, and controllers talk to is a `Terminal`.

[`AbstractHost`](../api/xnano/core/hosts.md#xnano.core.hosts.AbstractHost){data-preview}
provides behavior that is independent of the output surface:

- **Dispatch state:** `_hooks`, `_attached_grids`,
  `_attached_frame_grids`, and `state` form the common interface used by
  `xnano._dispatch`. They are documented on the class without strict
  types because dispatch accepts any compatible host, not only
  [`Terminal`](../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal){data-preview}.
- **`perform(action)`:** converts an
  [`Action`](../api/xnano/core/actions.md#xnano.core.actions.Action){data-preview},
  or another object with
  `to_event()`, into an event and passes it to `dispatch_hooks()`.
  Reentrant calls are queued to avoid nested dispatch. A chain longer
  than `_MAX_PERFORM_DEPTH` (32) raises `HookError`, which stops actions
  that repeatedly trigger the same hook.
- **`navigate(key)` and
  [`RouteTable`](../api/xnano/core/hosts.md#xnano.core.hosts.RouteTable){data-preview}:**
  map route keys to interface
  factories. Subclasses implement `on_navigate()` when navigation also
  needs to reattach hooks or replace the controller root.
- **Lazy `actions` and `stage` properties:** create
  [`Actions(self)`](../api/xnano/core/actions.md#xnano.core.actions.Actions){data-preview}
  and
  [`Stage(self)`](../api/xnano/core/stage.md#xnano.core.stage.Stage){data-preview}
  on first access and reuse those instances afterward.
- **`enter_host()` and `leave_host()`:** set and clear the active host in
  `_ACTIVE_HOST`, a `contextvars.ContextVar`. Code such as
  [`AbstractInterface`](../api/xnano/core/interface.md#xnano.core.interface.AbstractInterface){data-preview}`.mark_field_dirty()`
  can then find the current host
  without receiving it as an argument or relying on a process-wide
  singleton.

### Web as a cell-streaming host

[`Web`](../api/xnano/web/web.md#xnano.web.web.Web){data-preview}
is the browser analogue of
[`Terminal`](../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal){data-preview},
not a second paint backend. `Web.run()` binds a dependency-free stdlib
HTTP server that:

1. Serves a minimal shell page with a `<canvas>` client
2. Renders each frame through an offscreen
   [`Terminal`](../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal){data-preview}
   (via
   [`WebRenderer`](../api/xnano/web/render.md#xnano.web.render.WebRenderer){data-preview})
3. Streams cell rows to the browser over Server-Sent Events
4. Routes browser key, mouse, and resize events back through the same
   `xnano._dispatch` path the live terminal uses

There is no separate HTML/flex controller or session host type. Components
render on web identically to the terminal because they use the same
layout engine, nodes, and
[`TerminalController`](../api/xnano/core/controllers/tui.md#xnano.core.controllers.tui.TerminalController){data-preview}.

### Request hooks on either host

Every HTTP method has a decorator in `xnano.web.requests` —
`@on_get_request`, `@on_head_request`, `@on_post_request`,
`@on_put_request`, `@on_delete_request`, `@on_connect_request`,
`@on_options_request`, `@on_trace_request`, `@on_patch_request`,
`@on_query_request` — also re-exported from `xnano.hooks` and
`xnano.requests`. Declare them on grid methods. When the grid runs under
[`Web`](../api/xnano/web/web.md#xnano.web.web.Web){data-preview},
the native server serves those routes alongside the canvas shell. When
it runs under
[`Terminal.run(..., host=..., port=...)`](../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal.run){data-preview},
a small companion stdlib request server (`xnano.web.request_server`)
exposes the same routes while the TUI loop continues — request hooks are
cross-host, not web-only.

## `AbstractController`: painting, measurement, and layout

[`xnano.core.controllers.abstract.AbstractController`](../api/xnano/core/controllers/abstract.md#xnano.core.controllers.abstract.AbstractController){data-preview}
defines the rendering backend API. The only concrete paint implementation
is
[`TerminalController`](../api/xnano/core/controllers/tui.md#xnano.core.controllers.tui.TerminalController){data-preview}
in `xnano.core.controllers.tui`. Live terminals and the web host's
offscreen sessions both use it; there is no separate HTML controller.
Only `get_capabilities()` is required on
[`AbstractController`](../api/xnano/core/controllers/abstract.md#xnano.core.controllers.abstract.AbstractController){data-preview}.
Other methods raise `NotImplementedError` by default, so future backends
can implement the features they support.

[`AbstractControllerCapabilities`](../api/xnano/core/controllers/abstract.md#xnano.core.controllers.abstract.AbstractControllerCapabilities){data-preview}
is the negotiation surface:

```python
supports_effects: bool             # does grid_play_effect do anything?
supports_movement: bool            # can fields be pointer-dragged?
supports_absolute_geometry: bool   # do Area coords map to real cells,
                                    # or are they logical only?
```

A grid or component calls controller methods without checking the host
type. Capability flags and unimplemented methods define the available
backend features. Controller methods fall into these groups:

- **Frame lifecycle:** `begin_viewport_frame()`, `commit_requests()`,
  `get_viewport_area()`.
- **Chrome:** `paint_frame(area, frame)` paints borders, padding, and a
  title. `paint_chrome(area, style)` first converts a
  [`Style`](../api/xnano/_styles.md#xnano._styles.Style){data-preview}
  to a
  [`Frame`](../api/xnano/_types.md#xnano._types.Frame){data-preview},
  allowing callers to work directly with styles.
- **Layout:** `split_layout(area, direction, gap, constraints)` turns
  an
  [`AbstractLayoutConstraint`](../api/xnano/core/controllers/abstract.md#xnano.core.controllers.abstract.AbstractLayoutConstraint){data-preview}
  sequence into concrete sub-`Area`s;
  `measure_field_slot()` sizes one slot's content ahead of layout.
- **Content painting:** `render_content()` handles a neutral `Content`
  tree, `render_ir()` accepts a pre-lowered
  [`CoreRenderIR`](../api/xnano-core/core.md){data-preview}, and
  `render_native()` accepts a backend-native widget without a portable
  IR form. `paint_node()` asks the node to lower itself, so the
  controller does not inspect its concrete type.
- **Effects and fields:** `play_effect()`, `paint_field_slot()`, and
  `notify_field_changed()`.
  [`AbstractInterface`](../api/xnano/core/interface.md#xnano.core.interface.AbstractInterface){data-preview}
  calls the last method
  whenever a field becomes dirty.

[`LayoutConstraint`](../api/xnano/core/controllers/abstract.md#xnano.core.controllers.abstract.LayoutConstraint){data-preview}
in `xnano.core.controllers.abstract` is the concrete
constraint type built by
[`BaseGrid`](../api/xnano/grid.md#xnano.grid.BaseGrid){data-preview}.
[`TerminalController`](../api/xnano/core/controllers/tui.md#xnano.core.controllers.tui.TerminalController){data-preview}
resolves those values against cells through the native layout engine —
whether the buffer is a live terminal or the offscreen buffer the web
host snapshots for SSE.

## Frame sequence

A field change begins in
[`BaseGrid`](../api/xnano/grid.md#xnano.grid.BaseGrid){data-preview},
which is an
[`AbstractInterface`](../api/xnano/core/interface.md#xnano.core.interface.AbstractInterface){data-preview},
and
notifies the active
[`AbstractHost`](../api/xnano/core/hosts.md#xnano.core.hosts.AbstractHost){data-preview}
controller. During the next
`render_frame()`, the controller measures and lays out fields with
`measure_field_slot()` and `split_layout()`. It then paints each field
through `paint_field_slot()`, followed by `render_ir()`,
`render_native()`, or `paint_node()`. The sequence is the same for a
live
[`Terminal`](../api/xnano/terminal/terminal.md#xnano.terminal.terminal.Terminal){data-preview}
and for the offscreen terminal owned by
[`WebRenderer`](../api/xnano/web/render.md#xnano.web.render.WebRenderer){data-preview};
only the destination of the painted cells differs (the host terminal
versus an SSE stream to a canvas client).

See [Event & Render Lifecycle]{data-preview} for the dispatch path and
[Render Nodes & IR]{data-preview} for how
[`TerminalController`](../api/xnano/core/controllers/tui.md#xnano.core.controllers.tui.TerminalController){data-preview}
submits work to `xnano_core`.

[Event & Render Lifecycle]: lifecycle.md
[Render Nodes & IR]: render-nodes.md
