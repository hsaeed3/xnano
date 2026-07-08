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
