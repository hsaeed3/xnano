# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running tests
```bash
uv run pytest                        # all tests
uv run pytest tests/test_grid_init.py  # single test file
uv run pytest tests/test_grid_init.py::test_name  # single test
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
  visually — see `xnano/_demo.py` watercolor frame builders, which may
  need ceiling division on the vertical leftover to keep wordmarks from
  reading as shifted upward.
- `Env COLORTERM "truecolor"` is required for watercolor gradients to
  render — without it VHS's pty falls back to a 16-color ANSI palette
  and gradients collapse to a single flat tone.

---

## Architecture

This uv workspace contains the stable Python framework (`xnano` 1.0.0) and
the maturin-built Rust extension (`xnano-core` 0.0.8).

```
User app (BaseGrid + Field + @on_* hooks + Action)
    ↓
xnano               public DSL: grid, fields, events, components, …
    ├── xnano.core   host/action/content/stage/device contracts + controllers
    ├── xnano.terminal    Terminal host + native lowering
    ├── xnano.web  Web host + HTML/htmx
    └── xnano.cli    Command CLI
    ↓
xnano_core.core     session, scene graph, render IR, unified events
    ↓
xnano_core.rust.native   raw ratatui/crossterm/tachyonfx PyO3 bindings
```

### xnano (public DSL)

The package root lazy-exports `BaseGrid` (deprecated `Grid` alias),
`GridSettings`, `Field`, `Context`, `Terminal`, `Action`, `Style`, and
stable `@on_*` / `@on_action` decorators. Import components and supporting types
from their concrete modules.

Key modules:

- `grid.py`, `fields.py` — `BaseGrid`, sizing, and state fields
- `events.py` — Event types plus all `@on_*` / `@on_action(action)` decorators
- `context.py`, `state.py`, `color.py`, `effects.py` — handler context,
  app state, colors, effect *descriptions* (native lowering is TUI-only)
- `components/` — Text, Progress, Sparkline, Table, Chart, Schema
- `_*.py` — private internals only (types, styles, dispatch, validation,
  core bindings, demo). Users never import `_` modules; public re-exports
  cover the names that appear in signatures.

### xnano.core (shared contracts)

Interface-neutral engines shared by every host:

- `actions.py` — `Action` hierarchy and matching
- `content.py` — `Content` primitives components compose into
- `hosts.py` — `AbstractHost`, `RouteTable`, `get_active_host`
- `interface.py` — `AbstractInterface` / field-state base
- `device.py` — `AbstractDevice` / `AbstractCursor`
- `stage.py` — `Stage`, `LayoutMap`, cell paint helpers
- `exceptions.py` — `Exit`, `HookError`, validation errors, …
- `controllers/` — `AbstractController`, `TerminalController`, `WebController`

### Interface kinds

| Package | Role |
|---------|------|
| `xnano.terminal` | `Terminal` host, cursor/device, render nodes, tachyonfx effects |
| `xnano.web` | `Web` orchestration, `WebSession` host, request hooks, HTML nodes |
| `xnano.cli` | `Command`, options, subcommands, validation, help |

A TUI frame flows from `Terminal` to the root grid/component. Grid sizing
emits paint requests through `TerminalController`, which assembles a
`CoreRenderNode` tree for `CoreSession.render()`. Events are polled from
core and shared dispatch helpers invoke hooks through `Context`. Web reuses
the same grids/hooks/components and requires the optional `web` extra.

### xnano-core (Rust extension)

`xnano_core.core` re-exports the stateful engine registered by the compiled
`xnano_core.rust.native` extension. Important engine types are:

- `CoreSession` — terminal lifecycle, viewport, effects, clock, and event loop
- `CoreRenderNode` — scene graph with geometry, children, z-order, and effects
- `CoreRenderContent` — empty, widget, stateful, drawable, or `.ir()` content
- `CoreRenderIR` / `IrLine` — Rust-side widget descriptions and measurement in
  a single Python-to-Rust boundary crossing
- `CoreKeyBinding` — native key-binding parsing and matching
- `CoreEvent`, `CoreTickEvent`, `CoreTerminalEventKind` — unified events
- `CoreTerminalRef` — scope-guarded access to the live native terminal

Rust bindings live in `xnano-core/rust/src/bindings/`. The engine includes
session, render-tree, content bridge, render IR, key binding, events, clock,
terminal reset, and panic-hook modules. Rust structs use `Py*`; engine types
use `Core*`; pointer-backed handles are `unsendable`.

**Layer boundary rule:** Keep public DSL policy in root modules +
`components/`, shared contracts in `xnano.core`, host implementations in
`terminal`/`web`/`cli`, private plumbing in top-level `_*.py`, and terminal
runtime mechanics in `xnano_core`. Application code must use `CoreSession`
through `Terminal`, never raw native terminal lifecycle or standalone event
polling. VHS demo tooling stays under `scripts/`.

---

## Code Style

### Imports
- Standard library (except `typing`): always import the module directly — `import dataclasses`, not `from dataclasses import dataclass`
- `typing` is the exception: use `from typing import Any, TypeAlias`, etc.
- External libraries: import module directly if primarily used at top level; use `from lib import submodule` otherwise
- Lines over 79 characters must be wrapped in parentheses

### Naming
- No abbreviations: `Terminal` not `Term`, `capabilities` not `caps` — exception only for stdlib names like `repr`
- Multi-word function names: standalone functions must be multi-word (e.g., `get_name`, `as_rgb`, `get_name_as_rgb`)
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
"""xnano.grid"""
```
Or if notes are needed:
```python
"""xnano.grid

---

Additional notes here.
"""
```
`__init__.py` files use the package path, not `__init__`.

### Line length
79 characters max (enforced by ruff).
