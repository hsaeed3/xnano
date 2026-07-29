# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running tests
```bash
uv run pytest                        # all tests
uv run pytest tests/test_grids.py    # single test file
uv run pytest tests/test_grids.py::test_name  # single test
```

### Linting & formatting
```bash
uv run prek run --all-files          # lint + format (ruff via prek)
```

### Type checking
```bash
uv run ty check                      # uses ty (astral.sh)
```

### Building xnano-core (Rust extension)
Any change to `xnano-core/rust/src/` requires rebuilding before changes are visible in Python:
```bash
cd xnano-core
cargo clean
maturin develop --uv
```

### Docs
```bash
uv run mkdocs serve                  # local docs server (zensical/mkdocs)
```

### Docs demo GIFs (VHS)
VHS tooling lives under `scripts/` only. Feature-tour and concept demos are
recorded with [VHS](https://github.com/charmbracelet/vhs) (`.tape` files
interpreted by the `vhs` CLI, `brew install vhs`).
```bash
uv run python scripts/generate_xnano_demos.py               # all demos
uv run python scripts/generate_xnano_demos.py --demo title  # one demo
uv run python scripts/generate_xnano_demos.py --dry-run     # print tape only
vhs themes                                                   # list built-in theme names
```
VHS quirks worth knowing before touching `Demo` settings in that script:
- `Set WindowBar` has no "off"/"none" value — the only way to omit the
  macOS traffic-light chrome is to not emit the `Set WindowBar` line at
  all (an empty string in the settings block, not a keyword).
- `Set Padding <n>` is a single value applied to all four sides, but the
  *rendered* padding is not guaranteed symmetric: VHS rasterizes the pty
  at a fixed cell size derived from `FontSize`/`LineHeight`, so leftover
  pixels after fitting whole character rows/columns into `Height`/`Width`
  get distributed unevenly (usually more slack on one edge). Columns
  tend to divide evenly in practice; rows are the common offender. Fix
  by nudging `Height` until the terminal's row count comes out even —
  probe cheaply with a throwaway tape that types a Python one-liner
  printing `shutil.get_terminal_size()` and captures it with the
  `Screenshot "<path>.png"` tape command (near-instant, no full
  recording), e.g.:
  ```
  Output "/tmp/probe.gif"
  Set Width 1000
  Set Height 230
  Set Padding 12
  Hide
  Type "python3 -c 'import shutil; print(shutil.get_terminal_size())' > /tmp/size.txt"
  Enter
  Sleep 300ms
  Show
  Screenshot "/tmp/probe.png"
  ```
- Centering content within an odd leftover row/column count also biases
  visually — see `xnano/core/demo.py` watercolor frame builders, which may
  need ceiling division on the vertical leftover to keep wordmarks from
  reading as shifted upward.
- `Env COLORTERM "truecolor"` is required for watercolor gradients to
  render — without it VHS's pty falls back to a 16-color ANSI palette
  and gradients collapse to a single flat tone.

---

## Architecture

This uv workspace contains the Python framework (`xnano` `1.1.7`) and the
maturin-built Rust extension (`xnano-core` `0.0.14`). The former `xnano.beta`
preview was migrated into the stable namespace — do not reintroduce a parallel
beta surface.

```
User app (BaseGrid + Field + @on_* hooks + Action)
    ↓
xnano               public DSL: grids, fields, hooks, components, …
    ├── xnano.core       Runtime, Frame, content, controller, stage, dispatch
    ├── xnano.terminal   Terminal host (wraps Runtime)
    ├── xnano.web        Web host (offscreen Runtime + native server)
    ├── xnano.cli        Command CLI
    ├── xnano.server     NativeWebServer + RequestServer
    └── xnano.utils      focus, validation, markup, helpers
    ↓
xnano_core.core     session, scene graph, render IR, unified events
    ↓
xnano_core.rust.native   raw ratatui/crossterm/tachyonfx PyO3 bindings
```

### xnano (public DSL)

The package root lazy-exports `BaseGrid` (no `Grid` alias), `GridSettings`,
`Field`, `Context`, `Terminal`, `Web`, `Runtime`, `Frame`, `Action`, `Style`,
`Component`, `Command`, `render`, and the stable `@on_*` / `@on_action`
decorators. Import components and supporting types from their concrete modules.

Key modules:

| Module | Role |
|--------|------|
| `grids.py`, `fields.py` | `BaseGrid`, `GridSettings`, sizing, state fields |
| `hooks.py` | `@on_keyboard`, `@on_mouse`, `@on_click`, `@on_tick`, `@on_event`, `@on_focus`, `@on_clipboard`, `@on_resize`, `@on_state`, `@on_field`, `@on_poll`, `@on_action` |
| `events.py` | Event types + `event_from_core` |
| `actions.py` | `Action` hierarchy + `Actions` performer |
| `context.py`, `state.py` | handler context and app state |
| `colors.py`, `tailwind.py`, `effects.py` | colors, `Style`, effect *descriptions* |
| `terminal.py`, `web.py` | presentation hosts |
| `rendering.py` | print-like `render()` (no session) |
| `requests.py` | HTTP request hooks + `Request` / `Response` |
| `markdown.py` | markdown viewport / `xnano PATH.md` runner |
| `types.py` | geometry, sizing, frame, keyboard/mouse/focus types |
| `cursor.py`, `device.py` | cursor and device controls |
| `components/` | `Text`, `Input`, `Button`, `Table`, `Chart`, `Bar`, `Loader`, `Options`, `Dropdown`, `Image`, `Link`, `Markdown`, `Scrollbar`, base `Component`, … |
| `core/` | `Runtime`, `Frame`, content primitives, `TerminalController`, stage, dispatch, layout, exceptions, demo |
| `cli/` | `Command`, options, help |
| `server/` | `NativeWebServer`, `RequestServer` |
| `utils/` | focus, validation, markup, introspection, responsive, deprecation |

### xnano.core (runtime and paint)

Shared engine used by every host:

- `runtime.py` — `Runtime`, `get_active_runtime()`; owns `CoreSession`
- `frame.py` — immutable render snapshot
- `content.py` — interface-neutral paint primitives (`TextBlock`, `Panel`, `Stack`, gauges, plots, canvas, …)
- `controller.py` — `TerminalController` (layout + paint requests)
- `rendering.py` — `lower_content` (content → `CoreRenderNode`)
- `stage.py` — `Stage`, `LayoutMap`
- `dispatch.py` — event / idle / frame / post-init dispatch
- `layout.py` — layout constraints
- `interface.py` — `AbstractInterface` (field-state base for grids)
- `exceptions.py` — `Exit`, `HookError`, validation errors, …
- `demo.py` — `python -m xnano` showcase

### Surfaces

| Package / module | Role |
|------------------|------|
| `xnano.terminal` | `Terminal` over live or offscreen `Runtime` |
| `xnano.web` | `Web` orchestration via `serve_native` |
| `xnano.server` | cell-stream web server + standalone request server |
| `xnano.cli` | `Command`, options, subcommands, validation, help |
| `xnano.rendering` | one-shot `render()` without an event loop |

A TUI frame flows from `Terminal` → `Runtime` → root grid/component.
Grid sizing emits paint requests through `TerminalController`, which
assembles a `CoreRenderNode` tree for `CoreSession.render()`. Events are
polled from core and shared dispatch helpers invoke hooks through
`Context`. Web reuses the same grids/hooks/components and the same
offscreen `Runtime` / `TerminalController` path, streaming cells to a
canvas — no separate HTML paint backend.

### xnano-core (Rust extension)

`xnano_core.core` re-exports the stateful engine registered by the compiled
`xnano_core.rust.native` extension. Important engine types are:

- `CoreSession` — terminal lifecycle, viewport, effects, clock, and event loop
- `CoreRenderNode` — scene graph with geometry, children, z-order, and effects
- `CoreRenderContent` — empty, widget, stateful, drawable, or `.ir()` content
- `CoreRenderIR` / `IrLine` — Rust-side widget descriptions and measurement in
  a single Python-to-Rust boundary crossing
- `CoreKeyBinding` — native key-binding parsing and matching
- `CoreTextEditor` — native text-editor state for input components
- `CoreEvent`, `CoreTickEvent`, `CoreTerminalEventKind` — unified events
- `CoreTerminalRef` — scope-guarded access to the live native terminal

Rust bindings live in `xnano-core/rust/src/bindings/`. The engine includes
session, render-tree, content bridge, render IR, key binding, editor, events,
clock, terminal reset, and panic-hook modules. Rust structs use `Py*`; engine
types use `Core*`; pointer-backed handles are `unsendable`.

**Layer boundary rule:** Keep public DSL policy in top-level modules +
`components/`, runtime/paint in `xnano.core`, presentation hosts in
`terminal`/`web`/`cli`, HTTP in `server/`, helpers in `utils/`, and terminal
runtime mechanics in `xnano_core`. Application code must use `CoreSession`
through `Runtime` / `Terminal`, never raw native terminal lifecycle or
standalone event polling. Web must go through `Web` / `serve_native`
(offscreen runtime), not a parallel HTML controller. VHS demo tooling stays
under `scripts/`. Showcase content lives in `xnano.core.demo`.

### Common import patterns

```python
from xnano import BaseGrid, Field, Terminal, render
from xnano.hooks import on_keyboard, on_tick, on_click
from xnano.components.text import Text
from xnano.context import Context

# Offscreen testing
terminal = Terminal.offscreen(cols=40, rows=12)
frame = terminal.render(App())
assert "Hello" in frame.text
terminal.close()
```

---

## Code Style

### Imports
- Standard library (except `typing`): always import the module directly — `import dataclasses`, not `from dataclasses import dataclass`
- `typing` is the exception: use `from typing import Any, TypeAlias`, etc.
- External libraries: import module directly if primarily used at top level; use `from lib import submodule` otherwise
- Inside the package, import from concrete modules (not barrels) — see `scripts/check_import_policy.py`
- Lines over 79 characters must be wrapped in parentheses

### Naming
- No abbreviations: `Terminal` not `Term`, `capabilities` not `caps` — exception only for stdlib names like `repr`
- Multi-word function names: standalone functions must be multi-word (e.g., `get_name`, `as_rgb`, `get_name_as_rgb`)
- Public single-word exception: top-level `render()`
- Class methods that modify in place: single verb (`normalize()`, `capitalize()`)

### Classes
- Prefer `@dataclasses.dataclass` over custom `__init__`
- Private attributes must use `dataclasses.field(init=False)` and never appear in `__init__`
- Properties only for derived representations of private attributes computed in `__post_init__`
- Field docstrings immediately follow the field (no blank line); multi-line docstrings end `"""` on its own line

### Type aliases
- Use `TypeAlias` for any union that would cause a line break in a function signature or class attribute
- Multi-line unions wrapped in parentheses with `|` on each new line

### Documentation (module headers)
Every module must start with a header docstring:
```python
"""xnano.grids"""
```
Or if notes are needed:
```python
"""xnano.grids

---

Additional notes here.
"""
```
`__init__.py` files use the package path, not `__init__`.

### Line length
79 characters max (enforced by ruff).
