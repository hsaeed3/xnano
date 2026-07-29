# Architecture and Code Style Guide for `xnano`

This document details the core philosophy, system architecture, native Rust
binding structures, and high-level Python code style conventions for the
`xnano` package.

## Library Structure

`xnano` is a Python multi-surface UI framework (TUI first, with web and CLI
surfaces) built on **`xnano-core`**, which exposes ratatui, crossterm, and
tachyonfx through PyO3.

The public DSL (`BaseGrid`, `Field`, components, `@on_*` hooks, `Action`,
`Style`, `render`) is interface-neutral. Presentation hosts are top-level
modules (`xnano.terminal`, `xnano.web`) plus the `xnano.cli` package. Shared
runtime machinery lives under `xnano.core`. Helpers live under `xnano.utils`.
HTTP serving lives under `xnano.server`.

```
User app (BaseGrid + Field + @on_* hooks + Action)
        |
        v
   xnano                 public DSL: grids, fields, hooks, components, …
        |
        +-- xnano.core   Runtime, Frame, content, controller, stage,
        |                dispatch, layout, exceptions, demo
        |
        +-- xnano.terminal   Terminal host (wraps Runtime)
        +-- xnano.web        Web host (offscreen Runtime + native server)
        +-- xnano.cli        Command CLI abstraction
        +-- xnano.server     NativeWebServer + RequestServer
        +-- xnano.utils      focus, validation, markup, dispatch helpers
        |
        v
   xnano_core.core       session, scene graph, render IR, unified events
        |
        v
   xnano_core.rust.native   raw ratatui/crossterm/tachyonfx bindings
```

### `xnano` — public DSL and package layout

**Location:** `xnano/` (version `1.1.7`; depends on `xnano-core==0.0.14`).

The package root lazily exports:

| Export | Module |
|--------|--------|
| `render` | `xnano.rendering` |
| `Action` | `xnano.actions` |
| `BaseGrid`, `GridSettings` | `xnano.grids` |
| `Field` | `xnano.fields` |
| `Context` | `xnano.context` |
| `Terminal` | `xnano.terminal` |
| `Web` | `xnano.web` |
| `Runtime`, `Frame` | `xnano.core` |
| `Style` | `xnano.tailwind` |
| `Component` | `xnano.components` |
| `Command` | `xnano.cli` |
| `@on_*` / `@on_action` | `xnano.hooks` |
| `hooks`, `requests`, `cli`, `components`, `core`, `events` | package barrels |

There is **no** `Grid` alias — use `BaseGrid`. Import components and supporting
types from their concrete modules (for example
`from xnano.components.text import Text`).

```
xnano/
├── __init__.py, __main__.py, py.typed
│
│  ── public DSL (flat modules) ────────────────────────────────────────
├── actions.py             # Action hierarchy + Actions performer
├── colors.py              # Color, ColorLike, Tailwind palette helpers
├── context.py             # Context passed to hooks
├── cursor.py              # Cursor controls
├── device.py              # Device / display controls
├── effects.py             # Effect descriptions (native lowering is TUI)
├── events.py              # Event types + core→Event conversion
├── fields.py              # Field, FieldInfo / GridFieldInfo, FieldState
├── grids.py               # BaseGrid, GridSettings
├── hooks.py               # @on_* / @on_action decorators
├── markdown.py            # Markdown viewport + CLI document runner
├── rendering.py           # print-like render() helper
├── requests.py            # HTTP request hooks + Request/Response
├── state.py               # State helper
├── tailwind.py            # Style + Tailwind class resolution
├── terminal.py            # Terminal host
├── types.py               # geometry, sizing, frame, keyboard/mouse/focus
├── web.py                 # Web host
│
│  ── packages ─────────────────────────────────────────────────────────
├── components/            # Bar, Button, Chart, Component, Dropdown,
│                          # Image, Input, Link, Loader, Markdown,
│                          # Options, Scrollbar, Table, Text, …
├── core/                  # Runtime, Frame, content, controller, stage,
│                          # dispatch, layout, interface, exceptions, demo
├── cli/                   # Command, Option, Argument, help
├── server/                # NativeWebServer, RequestServer
└── utils/                 # focus, validation, markup, introspection,
                           # dispatch, responsive, deprecation
```

#### Key abstractions and flow

- **`BaseGrid`** / **`Field`** — declarative layout and state fields.
  Subclass `BaseGrid` and annotate slots with `Field(...)`. Use
  `state=True` for non-rendered app data.
- **`Action`** — declarative/imperative triggers. Events answer *"what
  happened"*; actions answer *"what to do"*. Hooks bind actions; the
  runtime's `Actions` performer synthesizes them. Matching is centralized
  on `Action.matches`.
- **`Runtime`** — owns a `CoreSession`, the run loop, viewport mode,
  cursor/device controls, focus, stage, and paint pipeline. Prefer
  `Terminal` for apps; use `Runtime` directly when you need explicit
  session ownership. `get_active_runtime()` returns the context-local
  active runtime.
- **`Terminal`** (`xnano.terminal`) — presentation host over `Runtime`.
  Selects a live session when a TTY is available, otherwise offscreen.
  `Terminal.offscreen(...)` is the test path. `Terminal.run(...)` paints
  and pumps events until exit; it does **not** take `host=`/`port=` —
  use `Web` or `xnano.server` for HTTP.
- **`Web`** (`xnano.web`) — serves the same grids/components through an
  offscreen runtime via `xnano.server.native.serve_native` (cell stream
  to a canvas client). Request hooks from `xnano.requests` work under
  both terminal-adjacent servers and the web host.
- **`TerminalController`** (`xnano.core.controller`) — the paint controller
  that lays out grids and lowers content into a `CoreRenderNode` tree for
  `CoreSession.render()`.
- **`Content`** (`xnano.core.content`) — interface-neutral paint primitives
  (`TextBlock`, `Panel`, `Stack`, gauges, plots, canvas, …). Components
  compose these; the controller lowers them through `lower_content`.
- **`Frame`** (`xnano.core.frame`) — immutable snapshot of a rendered
  buffer (text/ANSI inspection in tests).
- **`Style`** (`xnano.tailwind`) — Tailwind-like class resolution for
  fields and grids (`class_name=`).
- A frame flows from `Terminal`/`Runtime` → root grid/component → field
  sizing and `TerminalController` paint requests → `CoreSession.render()`.
  Events are polled from core (or synthesized for web) and dispatched
  through `xnano.core.dispatch` via `Context`.

### Surfaces

| Surface | Entry | Notes |
|---------|-------|-------|
| Print helper | `from xnano import render` | One-shot styled output; no event loop |
| TUI | `from xnano.terminal import Terminal` (also root lazy export) | Live or offscreen `Runtime` |
| Web | `from xnano.web import Web` | Offscreen runtime + `NativeWebServer` |
| HTTP hooks | `from xnano.requests import on_get_request, …` | Declared on `BaseGrid` methods; served by `Web` / `xnano.server` |
| CLI | `from xnano.cli import Command` | Options, subcommands, validation, help |
| Markdown | `from xnano.markdown import run_markdown` | Also `xnano PATH.md` entrypoint |

Optional extras (see root `pyproject.toml`):

- `images` — Pillow for `Image` component
- `requests` — starlette/uvicorn for request servers

Web reuses the same grids, hooks, components, dispatch helpers, and
`TerminalController` path as the terminal host. Do not reintroduce a
`xnano.beta` product surface; that preview was migrated into the stable
namespace.

### `xnano-core` — native bindings and engine

**Location:** `xnano-core/` (version `0.0.14`; built with maturin).

| Module | Purpose |
|--------|---------|
| `xnano_core` | Minimal root exports for core events and native version |
| `xnano_core.core` | Primary engine API consumed by `xnano.core.runtime` / controller |
| `xnano_core.rust` | Barrel import for native primitives |
| `xnano_core.rust.native` | Compiled PyO3 extension plus type stubs |
| `xnano_core.rust.engine` | Stateful runtime registered by Rust |

Engine types imported from `xnano_core.core` include:

- `CoreSession` — terminal lifecycle, viewport, effects, clock, and event loop;
  use `.init()` for live terminals or `.offscreen()` for tests.
- `CoreRenderNode` — scene graph with geometry, children, z-order, visibility,
  effects, and row/column/stack builders.
- `CoreRenderContent` — empty, widget, stateful, drawable, or `.ir()` payloads.
- `CoreRenderIR` and `IrLine` — Rust-side widget descriptions and natural-size
  measurement in a single Python-to-Rust boundary crossing.
- `CoreKeyBinding` — native key-binding parsing and matching.
- `CoreTextEditor` — native text-editor state used by input-style components.
- `CoreEvent`, `CoreTickEvent`, and `CoreTerminalEventKind` — unified events.
- `CoreTerminalRef` — scope-guarded access to the live native terminal.

Rust binding modules live in `xnano-core/rust/src/bindings/`. Engine code
includes `session`, `render_tree`, `content_bridge`, `render_ir`,
`key_binding`, `editor`, `events`, `clock`, `terminal_reset`, and
`panic_hook`.

Rust structs use a `Py*` prefix while exported engine types use `Core*`.
Pointer-backed handles are `unsendable`. Prefer `CoreRenderIR` for framework
widget rendering; other `CoreRenderContent` variants bridge native/stateful
widgets and drawable callbacks.

#### Layer boundaries

| Concern | Lives in |
|---------|----------|
| Public DSL (grids, fields, events, hooks, components) | top-level modules + `components/` |
| Runtime, paint, content primitives, stage, dispatch | `xnano.core` |
| Terminal / web presentation hosts | `xnano.terminal`, `xnano.web` |
| HTTP servers | `xnano.server` |
| CLI parsing | `xnano.cli` |
| Shared helpers (focus, validation, markup, …) | `xnano.utils` |
| Scene graph, terminal lifecycle, render IR | `xnano_core.core` |
| Raw ratatui/crossterm/tachyonfx bindings | `xnano_core.rust.native` |

Do not call native terminal initialization/restoration or standalone native
event polling in application code; use `CoreSession` through `Runtime` /
`Terminal`. Keep grid/component policy in the public DSL, paint lowering in
`TerminalController` / `lower_content`, and terminal runtime mechanics in
`xnano-core`.

VHS demo recording and tape generation live under `scripts/` only — do not
embed VHS tooling under the package. The feature showcase lives in
`xnano.core.demo` and is launched by `python -m xnano` / `uv run xnano`.

## Code Style & Formatting Rules

### Import Patterns

Imports follow a very strict and opinionated pattern:

1. For **all** imports of the standard library, **aside from ``typing``**, the module must always be imported directly.
   1. Incorrect: ``from dataclasses import dataclass`` ``import typing``
   2. Correct: ``import abc`` ``import dataclasses`` ``from typing import Any``

2. For **external libraries**
   1. If the library is a single module, **or** it is used **only** for functions that are exposed at the top level of the library, the module must always be imported directly.
      1. This rule also follows up for external libraries where it is being used primarily for methods at the top level, along with one or two additional classes. These cases **must** use both import patterns.
      If it is approriate or allowed to import the associated class (even if it is available at the top level) from a lower level module, then that pattern is the perferred option.
      Example: ``import mylib\nfrom mylib.types import ImportantType``
   2. For all other libraries the library must be imported with the ``from <library_name> import <module_name>`` pattern.

3. Prefer **concrete internal modules** over package barrels when importing
   inside the package (enforced by `scripts/check_import_policy.py`):
   ``from xnano.components.text import Text``, not
   ``from xnano.components import Text`` in library code.

All import lines above 79 characters must be wrapped in parantheses
with new lines.

### Shorthand Abbreviation Rules

Class, function, method and property names never abbreviate common words or concepts.

  - **Incorrect**: ``Rect``, ``Term``, ``caps``
  - **Correct**: ``Rectangle``, ``Terminal``, ``capabilities``
  - This rule may be broken **only** in situations where the operation or abbreviation directly maps to a stdlib python name (such as ``repr``)

### Function Naming Standardization Rules

All functions must be named using the following conventions:

 - Function names that are not class methods **must never** be a single word.
   - NOTE: This is not a rule 100% of the time. For example, one of the
     ``zyx`` library's main user facing abstractions are called `semantic
     operations`, which are llm-powered operations that perform various tasks
     on python objects. **ONLY IF** a function is intended or implemented as
     one of the core features and/or user facing abstractions **AND** it's
     usage is presented in documentation as ``import module`` then
     ``module.fn()`` ``module.fn2()`` then it may be a single word.
     - Example: The semantic operations in ``zyx`` are named ``zyx.edit(...)``
       (uses an LLM to edit python objects), ``zyx.parse(...)`` (confidence
       based LLM parsing), ``zyx.run(...)`` (standard agent loop).
     - In xnano, the top-level ``render()`` helper is such a public single-word
       API.

Below is a structured list of common function types and how they should be named:

**Case**: For class methods that return one of their own properties and/or
fields.
**Pattern**: ``get_<property_name>()``
**Example**: ``get_name()``

**Case**: For class methods that return themselves, or a copy of themselves (or their entire/main value) in a mutated format.
**Pattern**: ``as_<mutated_format>()``
**Example**: ``Color(<some_content>).as_rgb()``

**Case**: For class methods that return a copy of one of their own properties and/or fields in a mutated format.
**Pattern**: ``get_<property_name>_as_<mutated_format>()``
**Example**: ``get_name_as_rgb()``

**Case**: For class methods that directly modify itself in place.
**Pattern**: ``<verb>``
**Example**: ``normalize()``, ``capitalize()``

### **Documentation**

### Module Headers

Documentation is **essential** to ``xnano`` and follows a very strict standardization.

**Module / Script Naming**

All modules (scripts) must contain a header docstring that follows
the following format:

**Case 1: If No Notes are Required (Most Cases)**

```python
"""<path>.<to>.<module>"""
```

**Case 2: If **ANY** Non-Title Content is Necessary**

```python
"""<path>.<to>.<module>

---

<additional content / notes only if necessary or if
this is an __init__.py to a core subpackage>
"""
```

Notes:

1. All scripts must contain the header docstring.
2. There is no ``.py`` extension in module name.
3. ``__init__.py`` files never contain ``__init__`` just the module name.
4. Additional content / notes must always be separated with a divider and new lines, the first line must always only be the path of the module.

### Classes (& Class Style Guide [IMPORTANT])

Classes are the core building blocks of ``xnano``'s design philosophy and follow ``pydantic``'s design conventions and ideas. Classes should be **preferred** to be defined as dataclasses over classes with their own
``__init__`` methods when possible.

Classes are **heavily** attribute based, specifically the attributes they
are initialized with.

Properties must only be used to represent attributes that are initialized
within the class as private attributes, **computed on post initialization**,
and represent a derived representation of one or more of the class's main
attributes.
   - Example:

      ```python
      @dataclasses.dataclass
      class MyClass:
         # NOTES;
         # The first line(s) must only be to describe the main (and short)
         # purpose of the class and cannot be more than 2 sentences.
         """This is a class that does some stuff.

         Attributes:
            property: This is a property
            another_property: This is another property
         """

         # NOTES:
         # no additional lines between docstrings/fields
         # only primary fieds must recieve a docstring, these docstrings should be more detailed than what was described on 'Attributes:'
         # If docstring is more than a line, the end `"""` must be on a
         # new line, for a 1 line docstring it is on the same line.
         property: str
         """This is a property."""
         another_property: int
         """A very important very detailed thing that does a lot of
         very important stuff.

         Heres what it does wow look how cool!
         """

         # NOTES:
         # single space separating main init level fields from private attributes
         # only important private attributes require docstrings, otherwise
         # not needed
         # private attributes **must NEVER** be on the iniialization list
         # or available as init args
         _some_private_attribute: int = dataclasses.field(init=False)
         _another_private_attribute: int = dataclasses.field(init=False)

         def __post_init__(self):
            self._new_private_attribute = self.property + 1

         # NOTES:
         # Only important private attributes or computed proeprties
         # that represent a derived representation of one or more of the
         # class's main attributes can be properties.
         @property
         def new_private_attribute(self) -> int:
            """This is a property."""
            # properties do not include 'Returns:' in their docstring
            return self._new_private_attribute

         # even though tis is a private attribute, it recieves a dcostring
         # because it is a function
         def get_some_private_attribute(self) -> str:
            """This is a property.

            Returns:
               The value of the attribute.
            """
            return self._some_private_attribute
      ```

### Functions

Function docstrings are structured using the standard `Args:`, `Returns:` and `Raises:` sections.

### Types

The package **heavily** utilizes type aliases, and especially
``typing.Union`` and ``typing.Literal`` based types. Any types that are
defined inline must be annotated with an associated docstring **and
separated by 2 lines from other content** (same as all other item types
except for class methods which are 1 new line and class fields/attributes
which are no new lines unless going from init attributes to private
attributes).

Whenever applicable the package uses the ``|`` syntax over ``typing.Union``
following a strict set of conditions based on where the type is being used.

**Case 1: If the type is used as a class attribute or field**:
   Unless the type is something simple such as ``int | bool`` , the type must be defined as a ``TypeAlias`` outside the class first.

**Case 2: If the type is used as a function parameter or return type**:
   If it is a on-off type, it may be annotated inline within a function parameter **untill or unless** it goes far enough to cause a new line within the function signature.

   In this case it must be defined as a ``TypeAlias`` outside the function first.

   **Bad Example**

   ```python
   def my_function(my_type : (
      int | bool | SomeModel | SomeOtherModel
   )) -> ...

   def my_function(
      my_type: (
         int
         | bool
         | ...
      )
   )
   ```

   **Good Example**

   ```python
   MyType: TypeAlias = int | bool | ...
   """This is a ..."""

   # if the union is more than a single line, it must be wrapped in
   # paranthesis with this format
   MyType: TypeAlias = (
      int
      | bool
      | ...
   )
   """This is a ..."""

   def my_function(
      my_type: MyType
   ) -> MyType:
      """This is a function."""
      return my_type
   ```

## Testing, Linting, and Formatting

### TESTING

All testing is done through ``pytest``, all code changes must be followed by running:

```bash
uv run pytest
```

### LINTING

All linting & pre-commit configuration is handled through ``ruff`` and ``prek`` all code
changes must be followed by running:

```bash
uv run prek run --all-files
```

### TYPE CHECKING

```bash
uv run ty check
```

### xnano-core SPECIFIC RULES

**ANY** changes to ``xnano-core`` must be followed by running:

```bash
cd xnano-core
cargo clean
maturin develop --uv
```
