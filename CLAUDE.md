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
uv run mkdocs serve                  # local docs server
```

### Docs demo GIFs (VHS)
`scripts/generate_xnano_demos.py` records the `docs/assets/xnano-*.gif`
feature-tour GIFs with [VHS](https://github.com/charmbracelet/vhs)
(`.tape` files interpreted by the `vhs` CLI, `brew install vhs`).
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
  visually — see `xnano/core/demo/title.py`'s `_build_watercolor_frame`,
  which had to switch from floor to ceiling division on the vertical
  leftover to stop the wordmark from reading as shifted upward.
- `Env COLORTERM "truecolor"` is required for the watercolor gradient to
  render — without it VHS's pty falls back to a 16-color ANSI palette
  and gradients collapse to a single flat tone.

---

## Architecture

This is a Python TUI framework (`xnano`) layered over a Rust extension (`xnano-core`). It is a uv **workspace** with two packages:

```
xnano/          ← Python framework (1.0.0b2)
xnano-core/     ← Rust extension built with maturin (0.0.5)
```

### Layer stack (top → bottom)

```
User app  (Grid subclass + @on_* hooks)
    ↓
xnano.beta          declarative layout, events, render IR, type conversions
    ↓
xnano_core.core     CoreSession, CoreRenderNode, CoreRenderContent, CoreEvent
    ↓
xnano_core.rust.native   ratatui / crossterm / tachyonfx (compiled PyO3 extension)
    ↓
xnano-core/rust/src/bindings/   Rust wrappers
```

### xnano.beta (Python framework)

All active implementation lives under `xnano/beta/`. The root `xnano/` package is a thin re-export shell.

Key modules:
- `grid.py`, `fields.py` — `Grid`, `Field`, `GridSettings` — declarative layout with metaclass magic
- `terminal.py` — `Terminal` — session owner, `run(grid)` entry point, context manager
- `hooks.py`, `context.py` — `@on_keyboard`, `@on_tick`, `@on_click`, `@on_mouse`; `Context` passed to handlers
- `core/dispatch.py` — per-frame render loop: render → poll events → fire hooks
- `core/session.py` — batches `RenderRequest`s → assembles `CoreRenderNode` tree → calls `CoreSession.render()`
- `core/nodes.py` — render IR: `SpanNode`, `ParagraphNode`, `FrameNode`, etc. (immutable, lowered to native widgets)
- `utils/native_types.py` — Python ↔ native type conversions
- `components/abstract.py` — `AbstractComponent` base; implement `get_node() → RenderNode`

Per-frame data flow:
1. `Terminal.run(grid)` opens `CoreSession`
2. `dispatch.render_frame()` → `Grid._grid_build_frame()` splits viewport into field areas, paints slot values
3. `Session.commit_requests()` assembles `CoreRenderNode` tree
4. `CoreSession.render(root_node)` walks tree, runs effects, writes to terminal
5. `dispatch.pump_events()` / `pump_tick()` → `Event.from_core_event()` → `@on_*` handlers via `Context`

### xnano-core (Rust extension)

Built with maturin; published as `xnano_core.rust.native` (compiled `.abi3.so`).

Key engine types (import via `from xnano_core.core import …`):
- `CoreSession` — terminal lifecycle, effect manager, event loop. Use `.init()` for live or `.offscreen(w, h)` for tests
- `CoreRenderNode` — scene-graph node with geometry, flex, children, z-order. Builders: `.leaf()`, `.row()`, `.column()`, `.stack()`
- `CoreRenderContent` — tagged payload: `.empty()`, `.widget()`, `.stateful()`, `.drawable()`
- `CoreEvent` / `CoreTickEvent` / `CoreTerminalEventKind` — unified events from `poll_event` / `read_event`

Rust source is in `xnano-core/rust/src/bindings/`. Rust structs are prefixed `Py*`; engine types use `Core*`. Pointer-backed handles (`Frame`, `CoreSession`) are `unsendable`.

**Layer boundary rule:** Never call `native.Terminal.init()`, `restore_terminal()`, or standalone `native.poll_event()` in app code — always go through `CoreSession` via `Terminal`. Never put layout/grid logic in `xnano_core`.

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
"""xnano.beta.grid"""
```
Or if notes are needed:
```python
"""xnano.beta.grid

---

Additional notes here.
"""
```
`__init__.py` files use the package path, not `__init__`.

### Line length
79 characters max (enforced by ruff).
