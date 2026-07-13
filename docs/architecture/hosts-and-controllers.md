---
title: "Hosts, Interfaces & Controllers"
icon: "lucide/server"
---

# Hosts, Interfaces & Controllers

`xnano.core` defines the contracts shared by terminal and web hosts.
These contracts separate field state, session behavior, and backend
rendering across three classes: `AbstractInterface`, `AbstractHost`, and
`AbstractController`.

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

`BaseGrid` inherits from `xnano.core.interface.AbstractInterface` to
manage declared fields and their per-instance `FieldState` objects.
Layout remains the responsibility of `BaseGrid`; `AbstractInterface`
tracks field values and reports changes.

It has two main responsibilities:

- `_init_field_states()` allocates one `FieldState` per declared field
  (both rendered fields, `_grid_fields`, and `state=True` fields,
  `_grid_state_fields`) when an instance is constructed.
- `mark_field_dirty(name)` marks that field's state dirty, refreshes
  its cached value, and calls `_notify_field_changed()`.

`_notify_field_changed()` is best-effort. It obtains the active host from
`xnano.core.hosts.get_active_host()`, finds its private `_session` or
`controller` handle, and calls `notify_field_changed()` when that method
is available. Notification errors are ignored. As a result, mutating a
grid without an active host, including in a unit test, updates its state
without raising an exception.

## `AbstractHost`: shared session behavior

`Terminal` and web sessions both implement
`xnano.core.hosts.AbstractHost`. It provides behavior that is independent
of the output surface:

- **Dispatch state:** `_hooks`, `_attached_grids`,
  `_attached_frame_grids`, and `state` form the common interface used by
  `xnano._dispatch`. They are documented on the class without strict
  types because dispatch accepts any compatible host, not only
  `Terminal`.
- **`perform(action)`:** converts an `Action`, or another object with
  `to_event()`, into an event and passes it to `dispatch_hooks()`.
  Reentrant calls are queued to avoid nested dispatch. A chain longer
  than `_MAX_PERFORM_DEPTH` (32) raises `HookError`, which stops actions
  that repeatedly trigger the same hook.
- **`navigate(key)` and `RouteTable`:** map route keys to interface
  factories. Subclasses implement `on_navigate()` when navigation also
  needs to reattach hooks or replace the controller root.
- **Lazy `actions` and `stage` properties:** create `Actions(self)` and
  `Stage(self)` on first access and reuse those instances afterward.
- **`enter_host()` and `leave_host()`:** set and clear the active host in
  `_ACTIVE_HOST`, a `contextvars.ContextVar`. Code such as
  `AbstractInterface.mark_field_dirty()` can then find the current host
  without receiving it as an argument or relying on a process-wide
  singleton.

## `AbstractController`: painting, measurement, and layout

`xnano.core.controllers.abstract.AbstractController` defines the
rendering backend API. `xnano.tui` uses `TerminalController`, while
`xnano.webui` provides its own implementation. Only
`get_capabilities()` is required. Other methods raise
`NotImplementedError` by default, so each backend implements the
features it supports.

`AbstractControllerCapabilities` is the negotiation surface:

```python
supports_effects: bool             # does grid_play_effect do anything?
supports_movement: bool            # can fields be pointer-dragged?
supports_absolute_geometry: bool   # do Area coords map to real cells,
                                    # or are they logical/flex only?
```

A grid or component calls controller methods without checking the host
type. Capability flags and unimplemented methods define the available
backend features. Controller methods fall into these groups:

- **Frame lifecycle:** `begin_viewport_frame()`, `commit_requests()`,
  `get_viewport_area()`.
- **Chrome:** `paint_frame(area, frame)` paints borders, padding, and a
  title. `paint_chrome(area, style)` first converts a `Style` to a
  `Frame`, allowing callers to work directly with styles.
- **Layout:** `split_layout(area, direction, gap, constraints)` turns
  an `AbstractLayoutConstraint` sequence into concrete sub-`Area`s;
  `measure_field_slot()` sizes one slot's content ahead of layout.
- **Content painting:** `render_content()` handles a neutral `Content`
  tree, `render_ir()` accepts a pre-lowered `CoreRenderIR`, and
  `render_native()` accepts a backend-native widget without a portable
  IR form. `paint_node()` asks the node to lower itself, so the
  controller does not inspect its concrete type.
- **Effects and fields:** `play_effect()`, `paint_field_slot()`, and
  `notify_field_changed()`. `AbstractInterface` calls the last method
  whenever a field becomes dirty.

`LayoutConstraint` in `xnano.core.controllers.abstract` is the concrete
constraint type built by `BaseGrid`. Both controllers receive the same
constraint values. The terminal controller resolves them against cells
through the native layout engine, while the web controller converts them
to CSS layout values.

## Frame sequence

A field change begins in `BaseGrid`, which is an `AbstractInterface`, and
notifies the active `AbstractHost` controller. During the next
`render_frame()`, the controller measures and lays out fields with
`measure_field_slot()` and `split_layout()`. It then paints each field
through `paint_field_slot()`, followed by `render_ir()`,
`render_native()`, or `paint_node()`. The sequence is shared by
`xnano.tui.Terminal` and `xnano.webui.Web`; their controller
implementations determine how each operation is performed.

See [Event & Render Lifecycle]{data-preview} for the dispatch path and
[Render Nodes & IR]{data-preview} for the terminal controller's render
path.

[Event & Render Lifecycle]: lifecycle.md
[Render Nodes & IR]: render-nodes.md
