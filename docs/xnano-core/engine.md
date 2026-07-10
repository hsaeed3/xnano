---
title: "Core Terminal Engine"
---

# Engine

`xnano_core.rust.engine` (exposed as `xnano_core.core`) is the Rust-side session and render tree that sits directly above crossterm/ratatui. It owns the terminal for the lifetime of an application, drives the event loop, manages effects, and renders scene-graph trees to the screen.

You don't use this module directly — `xnano` is the Python API. This page documents the primitives for contributors or anyone building on top of the core.

---

## CoreSession

`CoreSession` is the singleton runtime handle for one live application. It is the **only** type allowed to call `ratatui::init` / `ratatui::restore`.

### Creating a session

=== "Live (full-screen)"

    ```python
    from xnano_core.core import CoreSession

    with CoreSession.init(tick_rate_ms=16) as session:
        # terminal is yours — alternate screen, raw mode, etc.
        ...
    # terminal restored on __exit__
    ```

=== "Live (inline)"

    ```python
    # Reserve 10 rows inline — no alternate screen
    with CoreSession.init(inline_height=10) as session:
        ...
    ```

=== "Offscreen (tests)"

    ```python
    # No terminal claimed — in-memory buffer only
    session = CoreSession.offscreen(width=80, height=24)
    session.render(node)
    buf = session.buffer_snapshot()
    ```

!!! note
    Sessions are context managers. Always use `with` — the `Drop` impl restores the terminal on panic, but relying on it from Python is discouraged.

### Rendering

Pass a `CoreRenderNode` tree to `session.render()` each frame:

```python
from xnano_core.core import CoreSession, CoreRenderNode, CoreRenderContent, CoreRenderIR

with CoreSession.init() as session:
    node = CoreRenderNode.leaf(
        CoreRenderContent.ir(CoreRenderIR.text_raw("Hello world"))
    )
    session.render(node)
```

### The event loop

```python
with CoreSession.init(tick_rate_ms=100) as session:
    while True:
        event = session.poll_event(timeout_ms=16)  # releases GIL while waiting
        if event is None:
            continue

        kind = event.kind_str()

        if kind == "key":
            if event.key.code == ...:
                break

        elif kind == "tick":
            elapsed = event.tick.elapsed_ms
            session.render(build_frame(elapsed))

        elif kind == "resize":
            cols, rows = event.width, event.height
            session.render(build_frame_sized(cols, rows))
```

`poll_event` releases the GIL while blocking, so Python threads run during the wait. It checks Python signals on each wake so Ctrl-C interrupts cleanly.

---

## CoreRenderNode

The render tree is built from `CoreRenderNode` objects — immutable scene-graph nodes that carry geometry, content, and children.

### Leaf nodes

```python
from xnano_core.core import CoreRenderNode, CoreRenderContent, CoreRenderIR

# Simplest possible node — just some text
node = CoreRenderNode.leaf(
    CoreRenderContent.ir(CoreRenderIR.text_raw("Hello", fg=violet_color))
)
```

### Layout containers

```python
from xnano_core.rust.native import Constraint, Direction

# Vertical column: two children, first takes 3 rows, second fills the rest
col = CoreRenderNode.column(
    children=[header_node, body_node],
    constraints=[Constraint.Length(3), Constraint.Fill(1)],
    gap=1,
)

# Horizontal row: sidebar 25%, content fills
row = CoreRenderNode.row(
    children=[sidebar_node, content_node],
    constraints=[Constraint.Percentage(25), Constraint.Fill(1)],
)
```

### Absolute stacking contexts

Use `CoreRenderNode.stack` for overlays, modals, and dropdowns that need to escape their parent's clip:

```python
# A modal at absolute position (10, 5), 40×10 cells
modal = CoreRenderNode.stack(
    x=10, y=5, width=40, height=10,
    children=[modal_content_node],
)
```

### Visibility and z-order

```python
node = CoreRenderNode(
    content=CoreRenderContent.ir(CoreRenderIR.text_raw("Overlay")),
    z=10,        # paints on top of siblings with lower z
    visible=True,
)

hidden = CoreRenderNode(
    content=CoreRenderContent.ir(CoreRenderIR.text_raw("Hidden")),
    visible=False,  # skipped entirely — no layout, no paint
)
```

!!! info "Layout slot is still consumed"
    A node with `visible=False` still occupies its layout slot — it's CSS `visibility: hidden`, not `display: none`. To truly remove a node, omit it from the tree.

---

## CoreRenderContent

`CoreRenderContent` is the payload that a node paints into its rect. Four variants:

```python
# Nothing — layout-only node
CoreRenderContent.empty()

# A built-in ratatui widget
CoreRenderContent.widget(Paragraph(...))

# A stateful widget + its state object
CoreRenderContent.stateful(my_list, my_list_state)

# A Python callback that draws directly into the buffer
CoreRenderContent.drawable(lambda buf, rect: ...)

# An IR node — rendered entirely in Rust, fastest path
CoreRenderContent.ir(CoreRenderIR.text_raw("Fast"))
```

---

## CoreRenderIR

`CoreRenderIR` is the fastest rendering path — all data crosses the Python→Rust boundary in a single call, and the widget is built and painted entirely in Rust.

```python
from xnano_core.core import CoreRenderIR, IrLine

# Plain text
CoreRenderIR.text_raw("Hello world", fg=white, align=0)

# Multi-line from IrLine objects
CoreRenderIR.text_lines([
    IrLine.styled("Header\n", fg=violet, modifiers=[bold]),
    IrLine.raw("Body text\n"),
])

# Paragraph with word wrap
CoreRenderIR.paragraph_raw(
    "Long content that will wrap...",
    fg=white,
    wrap=True,
)

# Sparkline bar chart
CoreRenderIR.sparkline(
    data=[10, 20, 15, 30, 25],
    max_value=100,
    fg=teal_color,
)

# Measure natural size without rendering
ir = CoreRenderIR.text_raw("Hello")
width, height = ir.measure()
```

### IrLine

`IrLine` builds a single styled line for use in `text_lines` and `paragraph_lines`:

```python
IrLine.raw("plain text")

IrLine.styled("bold header", fg=white, modifiers=[bold])

IrLine.from_spans([
    ("● ", green,  None, []),
    ("Done", white, None, [bold]),
    (": all tests passed", slate, None, []),
])
```

---

## CoreKeyBinding

Key bindings are parsed once in Rust and matched zero-copy on every event:

```python
from xnano_core.core import CoreKeyBinding

quit_binding  = CoreKeyBinding.parse("ctrl+c")
enter_binding = CoreKeyBinding.parse("enter")
f5_binding    = CoreKeyBinding.parse("f5")

# In your event loop:
if event.kind_str() == "key":
    if quit_binding.matches(event.key):
        break
```

!!! tip "Cache your bindings"
    Parse bindings once at startup and reuse them. Each `CoreKeyBinding.parse` call compiles the string; `matches` is the fast path.

---

## Effects

Effects are registered on the session and run automatically each frame:

```python
from xnano_core.rust.native import coalesce, sweep_in

# Run once, cleans itself up
session.add_effect(coalesce(duration_ms=600))

# Keyed — replaces any previous effect with the same key
session.add_unique_effect("banner", sweep_in(duration_ms=400))

# Cancel early
session.cancel_effect("banner")

# Check if any effects are still running
if session.is_animating():
    session.render(current_frame)

# Look up the rect a keyed render node resolved to
area = session.effect_area_for("banner")
if area:
    session.add_unique_effect("banner", sweep_in(duration_ms=400))
```

---

## CoreTerminalRef

A scope-guarded escape hatch for direct ratatui `Terminal::draw` access:

```python
ref = session.get_terminal()
ref.draw(lambda frame: frame.render_widget(my_widget, my_rect))

# Or propagate errors:
completed = ref.try_draw(lambda frame: ...)

cols, rows = ref.size().width, ref.size().height
```
