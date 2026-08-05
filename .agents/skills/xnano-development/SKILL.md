---
name: xnano-development
description: Develop and test the public xnano Python library. Use for changes under xnano/, public DSL behavior, components, hooks, rendering, runtime, and Python tests.
---

# xnano development

Use this skill for the Python library, not native Rust binding changes or docs-only work.

## Before editing

- Read the repository `AGENTS.md` and inspect the complete path from public API
  to runtime/controller before choosing a fix.
- Preserve unrelated dirty-worktree changes. Do not reintroduce `xnano.beta` or
  a `Grid` alias.
- Search all callers before changing shared dispatch, rendering, field, hook,
  or runtime behavior; fix the shared path rather than patching one caller.

## Public design rules

- Use `BaseGrid` with annotated `Field(...)` declarations. Prefer a typed
  `grid_settings: GridSettings` class attribute over class-header settings
  keywords when declaring layout configuration.
- Use `Field(state=True)` for non-rendered application state and
  `default_factory` for mutable values. Keep rendering policy in grids and
  components, not in native bindings.
- Use `@on_tick` for field-specific periodic changes and `grid_render()` for
  whole-grid work that must run before every frame. `grid_render()` is not a
  timer.
- Use xnano `ColorLike` values (`foreground`, `background`, `border_color`,
  `tailwind_color(...)`, hex, RGB/RGBA tuples, or known color names). Never
  pass Rich `Color`, `Text`, or `Style` objects.
- Import concrete internal modules, for example
  `from xnano.components.text import Text`; do not rely on package barrels in
  library code.
- Use `Terminal.offscreen(...)` for deterministic tests. Do not initialize
  crossterm directly or make `Terminal` serve HTTP.

## Implementation patterns

Prefer the smallest existing abstraction that fits. Components return
interface-neutral content from `compose()`; hooks may accept zero arguments or
one `Context`; actions centralize synthetic event matching. Keep one behavior
per hook and one HTTP operation per request handler.

For a rendering change, add the narrowest regression test that exercises the
public result: an offscreen `Frame`, dispatched event, field mutation, or
component content tree. Test edge cases at trust boundaries and preserve
backward-compatible aliases only when the public contract requires them.

## Verification

Run the relevant focused tests first, then the repository checks required by
`AGENTS.md`:

```bash
uv run pytest
uv run prek run --all-files
uv run ty check
```

Do not run the Rust rebuild for Python-only changes. Native changes belong to
the `xnano-core-development` skill.
