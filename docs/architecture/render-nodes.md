---
title: "Render Nodes & IR"
icon: "lucide/network"
---

# Render Nodes & IR

This page follows a field value from a Python terminal node to the cells
painted by `xnano_core`. It covers the final render stages introduced in
[Event & Render Lifecycle]{data-preview}.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: Content and Node stay in Python; CoreRenderIR is the single crossing into xnano_core, which paints the terminal buffer">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="rnd-cell-grid" width="14" height="14" patternUnits="userSpaceOnUse">
      <path d="M 14 0 L 0 0 0 14" class="gcd-grid-line" />
    </pattern>
    <marker id="rnd-arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <!-- Left panel: Python side -->
  <rect class="gcd-panel" x="16" y="28" width="280" height="244" rx="16" />
  <text class="gcd-label" x="156" y="54" text-anchor="middle">python</text>

  <!-- Content box -->
  <g transform="translate(40, 74)">
    <rect class="gcd-window" x="0" y="0" width="232" height="72" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="232" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="232" height="10" />
    <circle class="gcd-dot" cx="14" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="11" r="3.5" />
    <text class="gcd-chrome-label" x="116" y="15" text-anchor="middle">content</text>
    <path class="gcd-line" d="M16 40 h56" stroke-width="3" stroke-linecap="round" />
    <path class="gcd-line-soft" d="M16 54 h96" stroke-width="3" stroke-linecap="round" />
  </g>

  <!-- Node box -->
  <g transform="translate(40, 166)">
    <rect class="gcd-window" x="0" y="0" width="232" height="72" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="232" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="232" height="10" />
    <circle class="gcd-dot" cx="14" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="11" r="3.5" />
    <text class="gcd-chrome-label" x="116" y="15" text-anchor="middle">node</text>
    <path class="gcd-line" d="M16 40 h72" stroke-width="3" stroke-linecap="round" />
    <path class="gcd-line-soft" d="M16 54 h48" stroke-width="3" stroke-linecap="round" />
  </g>

  <!-- Arrow across the boundary -->
  <line class="gcd-arrow" x1="320" y1="150" x2="392" y2="150" marker-end="url(#rnd-arrowhead)" />
  <text class="gcd-chrome-label" x="356" y="136" text-anchor="middle">CoreRenderIR</text>

  <!-- Right panel: Rust side -->
  <rect class="gcd-panel gcd-panel-accent" x="424" y="28" width="280" height="244" rx="16" />
  <text class="gcd-label gcd-label-accent" x="564" y="54" text-anchor="middle">xnano_core (rust)</text>

  <!-- Painted terminal box -->
  <g transform="translate(448, 90)">
    <rect class="gcd-window" x="0" y="0" width="232" height="140" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="232" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="232" height="10" />
    <circle class="gcd-dot" cx="14" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="26" cy="11" r="3.5" />
    <circle class="gcd-dot" cx="38" cy="11" r="3.5" />
    <text class="gcd-chrome-label" x="116" y="15" text-anchor="middle">CoreSession.render()</text>
    <rect class="gcd-grid-fill" x="8" y="28" width="216" height="104" rx="6" />
    <rect x="8" y="28" width="216" height="104" rx="6" fill="url(#rnd-cell-grid)" />
  </g>
</svg>
</div>

## Nodes: `AbstractTerminalNode`

Every terminal-renderable value is represented by a frozen
`AbstractTerminalNode` dataclass from `xnano.tui.nodes`. This includes
text, tables, progress bars, frames, and containers. Two methods define
how each node is rendered:

- **`to_ir()`** returns the node's `CoreRenderIR` representation or
  `None` when no IR representation exists. Most node types only
  implement this method. `SpanNode`, `TextNode`, `ProgressBarNode`, and
  `TableNode` each call the corresponding `CoreRenderIR` constructor.
- **`lower(area, controller, *, z, effect_key)`** paints the node into
  `area` through a controller. The default implementation (defined
  once on `AbstractTerminalNode`) calls `to_ir()` and enqueues the
  result through `controller.render_ir()`. Nodes that implement only
  `to_ir()` use this default without overriding `lower()`.

The controller calls `node.measure()` and `node.lower(...)` without
checking the concrete node type. `AbstractController.paint_node()`
therefore works with both leaf nodes such as `SpanNode` and composite
nodes such as `ContainerNode`.

Three kinds of node override `lower()` directly instead of relying on
the `to_ir()` path:

1. **Containers** (`ContainerNode`, `StackNode`, `FrameNode`) do not have
   a single IR representation. They divide an area among children with
   `controller.split_layout()` or paint a frame with
   `controller.paint_frame()`, then call `lower()` on each child.
2. **Native-only widgets** (`ChartNode`) have no `CoreRenderIR`
   representation. `lower()` builds a native `ratatui` `Chart`
   object directly (via `xnano_core.rust.native`) and calls
   `controller.render_native()` instead of `render_ir()`.
3. **Instance-dependent native widgets** include `SparklineNode` when
   constructed with per-bar `bars` instead of a flat `data` list. The IR
   cannot represent individual bar colors, so this form uses
   `render_native()`. Other `SparklineNode` instances use `to_ir()`.

## Content: the interface-neutral tree

Nodes are specific to the terminal backend. Components first compose
host-neutral primitives from `xnano.core.content`, including `Run`,
`TextBlock`, `Panel`, `Stack`, `Clear`, `CellCanvas`, and `Native`.
`xnano.tui.content_lower.lower_content()` walks this tree and produces
an `AbstractTerminalNode` tree. It converts a `Run` to a `SpanNode`, a
`Stack` to a `ContainerNode`, and a `Panel` to a `FrameNode` around its
lowered child. `Native(interface_kind="tui", payload=...)` lets a
component provide an existing terminal node or backend object without
first representing that value as `Content`.

## `CoreRenderIR`: the single Python↔Rust crossing

`CoreRenderIR` is exported from `xnano_core.core` and implemented in
`xnano-core/rust/src/bindings/engine/render_ir.rs`. Its constructors pack
widget data into Rust enum variants in one PyO3 call. Constructors
include `span(...)`, `text_lines(...)`, `progress_bar(...)`, and
`table(...)`. The `.measure()` method calculates size without a live
terminal buffer. `AbstractTerminalNode.measure()` uses it during layout,
including when `xnano._dispatch.measure_renderable` resolves a root
box's `fit` width.

`IrLine` is the line-level representation. `IrLine.raw(str)` stores plain
text, `IrLine.styled(...)` applies one style to a line, and
`IrLine.from_spans([...])` combines spans with different styles. Nodes
create these values through `_ir_line()` in `xnano.tui.nodes`. A
`LineNode` is therefore lowered consistently whether it appears in a
`TableNode` cell, a `ListNode` item, or another parent.

## From node to screen: `TerminalController`

`xnano.core.controllers.tui.TerminalController` is the terminal
implementation of `AbstractController` and the framework layer that
submits render work to `xnano_core`. `render_ir()` and `render_native()`
do not paint immediately. Each appends a `RenderRequest` containing the
native rectangle, content, z-index, and optional effect key to
`self._render_requests`.

`render_frame()` calls `commit_requests()` once per frame. The method
combines queued requests into one `core.CoreRenderNode` tree:

1. Each `RenderRequest` becomes `core.CoreRenderContent.ir(...)`,
   `.widget(...)`, or `.stateful(...)`, depending on whether it contains
   IR, a stateless native widget, or a native widget with render-time
   state such as a selection `ListState`.
2. Each content wraps into a `core.CoreRenderNode(x, y, width, height,
   content=..., effect_key=..., z=...)`, which forms a scene graph leaf.
3. Multiple requests are combined under a viewport-sized
   `CoreRenderNode.stack(...)`. Requests are sorted by z-index when any
   request uses a non-default value.
4. The resulting node or stack is passed to
   `self._core_session.render(node)`.

`CoreSession.render()` then walks the `CoreRenderNode` tree, resolves
each leaf's `CoreRenderContent` to a `ratatui` widget, and paints it into
the terminal buffer at the requested geometry. The buffer is diffed
against the previous frame so only changed cells are written to the
terminal.

## IR and native rendering

The IR covers widgets that benefit from a compact, portable
representation. More specialized widgets, such as charts with series
markers and legends, use `render_native()` instead of expanding the IR
for features that are rarely needed. The usual `to_ir()` to
`render_ir()` path requires one compact Rust call. Native-only widgets
construct a `ratatui` object graph in Python and pass it across the PyO3
boundary directly.

[Event & Render Lifecycle]: lifecycle.md
