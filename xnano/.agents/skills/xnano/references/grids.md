# Grids and Fields

## Declare layout

Subclass `BaseGrid` and annotate every layout slot:

```python
from xnano import BaseGrid, Field
from xnano.components.text import Text


class Dashboard(BaseGrid, direction="vertical", gap=1):
    title: Text = Field(default=Text("Dashboard"), height=1)
    count: int = Field(default=0, state=True)
```

`BaseGrid` lays out rendered fields and nested grids/components. Grid class
keywords and `grid_settings` configure direction, gap, border, title, padding,
colors, modifiers, and strict validation.

## Rendered fields versus state

- A normal `Field` is a rendered slot whose value may be text, a component, a
  nested grid, or supported content.
- `Field(state=True)` is non-rendered application state. It is still reactive
  and can be watched with `@on_field`.
- Use `default_factory` for lists, dictionaries, grids, and components that
  must not be shared between instances.
- `strict=True` validates state assignments against annotations. Keep trust
  boundary validation explicit; do not weaken it to make a type error vanish.

Field metadata includes `width`, `height`, `visible`, `z`, `overlay`, `margin`,
`padding`, `border`, `title`, `align`, `class_name`, `scroll`, `group`, and
`autofocus`. Sizing accepts cells, percentages, ratios such as `"1fr"`, and
`"fit"`. `overlay=True` removes a field from normal flow; pair it with `z` for
popups or modals.

## Live updates

Prefer direct assignment for values:

```python
self.count += 1
self.title = Text(f"Count: {self.count}")
```

Use `grid_set_field(name, value=..., ...)` when changing a value and/or runtime
field metadata. Use `grid_update_field(name, ...)` for metadata-only updates.
These methods cannot change a field's `state`, default, or constructor status.

Fields sharing `group` provide terminal-wide focus, click, and scroll identity.
Use `ctx.focus("group")`, `ctx.blur()`, `ctx.is_focused("group")`, and
`ctx.scroll("group")` from hooks. A scroll field is driven by its scroll handle;
do not guess offsets from terminal dimensions.

Override `grid_render()` for per-frame value refresh and use
`grid_render_<breakpoint>()` only for breakpoint-specific setup. Keep layout
policy in grids and paint lowering in the framework.
