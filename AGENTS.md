# Architecture and Code Style Guide for `xnano`

This document details the core philosophy, system architecture, native Rust
binding structures, and high-level Python code style conventions for the
`xnano` package.

## Library Structure

`xnano` 1.0 is a Python multi-surface UI framework (TUI first, with web and
CLI hosts) built on **`xnano-core`**, which exposes ratatui, crossterm, and
tachyonfx through PyO3.

The public DSL (`BaseGrid`, `Field`, components, `@on_*` hooks, `Action`,
`Style`) is interface-neutral. Concrete hosts live under `xnano.terminal`,
`xnano.web`, and `xnano.cli`. Shared contracts and engines live under
`xnano.core`. Private plumbing uses top-level `_*.py` modules only.

```
User app (BaseGrid + Field + @on_* hooks + Action)
        |
        v
   xnano                 public DSL: grid, fields, events, components, …
        |
        +-- xnano.core   interface-neutral contracts (host, action, content,
        |                style consumers, stage, controllers)
        |
        +-- xnano.terminal    Terminal host + native lowering
        +-- xnano.web  Web host + HTML/htmx backend
        +-- xnano.cli    Command CLI abstraction
        |
        v
   xnano_core.core       session, scene graph, render IR, unified events
        |
        v
   xnano_core.rust.native   raw ratatui/crossterm/tachyonfx bindings
```

### `xnano` — public DSL and package layout

**Location:** `xnano/` (version 1.0.0; depends on `xnano-core==0.0.8`).

The package root lazily exports `BaseGrid` (with deprecated `Grid` alias),
`GridSettings`, `Field`, `Context`, `Terminal`, `Action`, `Style`, and the
stable `@on_*` / `@on_action` decorators. Import components and supporting types
from their concrete modules.

```
xnano/
├── __init__.py, __main__.py, py.typed
│
│  ── private internals (top-level `_` modules only) ────────────────────
├── _types.py              # geometry, sizing, frame, keyboard/mouse/focus
├── _styles.py             # Style + Tailwind resolver / class groups
├── _tailwind_classes.py   # generated Tailwind Literal coverage
├── _function_hooks.py     # hook registries, entries, markers
├── _event_processing.py   # native → Event parsing
├── _dispatch.py           # shared pump / layout / hook dispatch
├── _renderable.py         # string/ANSI renderable coercion
├── _validation.py         # field / CLI validation helpers
├── _introspection.py      # hook-callable introspection
├── _core_bindings.py      # framework ↔ xnano_core native conversions
├── _demo.py               # `python -m xnano` showcase content
│
│  ── public DSL (interface-neutral) ────────────────────────────────────
├── grid.py                # BaseGrid (+ Grid alias), GridSettings
├── fields.py              # Field, FieldInfo / GridFieldInfo, FieldState
├── components/            # Text, Table, Chart, Progress, Sparkline, Schema
├── color.py, effects.py, events.py, context.py, state.py
│
│  ── shared contracts / engines ────────────────────────────────────────
├── core/
│   ├── actions.py         # Action hierarchy + matching
│   ├── content.py         # interface-neutral Content primitives
│   ├── hosts.py           # AbstractHost, RouteTable, get_active_host
│   ├── interface.py       # AbstractInterface (field state base)
│   ├── device.py          # AbstractDevice / AbstractCursor
│   ├── stage.py           # Stage, LayoutMap, cell paint helpers
│   ├── exceptions.py      # Exit, HookError, validation errors, …
│   └── controllers/       # abstract + TerminalController + WebController
│
│  ── interface kinds ───────────────────────────────────────────────────
├── tui/                   # Terminal host, cursor, device, nodes, effects
├── webui/                 # Web host, session, requests, HTML nodes
└── cli/                   # Command CLI
```

#### Key abstractions and flow

- **`BaseGrid`** / **`Field`** — declarative layout and state fields.
  Prefer subclassing `BaseGrid` (`Grid` remains a one-release alias).
- **`Action`** — declarative/imperative triggers. Events answer *"what
  happened"*; actions answer *"what to do"*. Hooks bind actions; hosts
  `perform` them. Matching is centralized on `Action.matches`.
- **`AbstractHost`** — shared contract for `Terminal`, `WebSession`, and
  future hosts: registry, state, pump, `perform`, device/cursor/actions/
  stage, and `RouteTable` navigation.
- **`Content` / `Style` / `Stage`** — components compose interface-neutral
  content; controllers lower content into TUI IR/nodes or HTML; stage
  exposes layout maps and cell paint helpers on the active host.
- **`Terminal`** (`xnano.terminal`) — owns `CoreSession`, the run loop,
  viewport mode, cursor/device controls, and offscreen sessions. It is
  an `AbstractHost`.
- **`TerminalController` / `WebController`** — backend painting only.
  `TerminalController` is the only framework layer that talks to
  `xnano_core` for terminal rendering.
- A TUI frame flows from `Terminal` → root grid/component → field sizing
  and controller paint requests → `CoreSession.render()`. Events are
  polled from core and dispatched through `_dispatch` via `Context`.

### `xnano.terminal` / `xnano.web` / `xnano.cli`

| Surface | Entry | Notes |
|---------|-------|-------|
| TUI | `from xnano.terminal import Terminal` (also root lazy export) | ratatui session, native effects lowering |
| Web | `from xnano.web import Web` | Starlette/uvicorn, HTML flex + htmx; optional `web` extra |
| HTTP hooks | `from xnano.web.requests import on_get_request, on_post_request` | declared on `BaseGrid` methods |
| CLI | `from xnano.cli import Command` | options, subcommands, validation, help |

Web reuses the same grids, hooks, components, and dispatch helpers as the
terminal host. Do not reintroduce a `xnano.beta` product surface; beta
docs paths are redirects only.

### `xnano-core` — native bindings and engine

**Location:** `xnano-core/` (version 0.0.8; built with maturin).

| Module | Purpose |
|--------|---------|
| `xnano_core` | Minimal root exports for core events and native version |
| `xnano_core.core` | Primary engine API consumed by `xnano.terminal` / controllers |
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
- `CoreEvent`, `CoreTickEvent`, and `CoreTerminalEventKind` — unified events.
- `CoreTerminalRef` — scope-guarded access to the live native terminal.

Rust binding modules live in `xnano-core/rust/src/bindings/`. Engine code
includes `session`, `render_tree`, `content_bridge`, `render_ir`,
`key_binding`, `events`, `clock`, `terminal_reset`, and `panic_hook`.

Rust structs use a `Py*` prefix while exported engine types use `Core*`.
Pointer-backed handles are `unsendable`. Prefer `CoreRenderIR` for framework
widget rendering; other `CoreRenderContent` variants bridge native/stateful
widgets and drawable callbacks.

#### Layer boundaries

| Concern | Lives in |
|---------|----------|
| Public DSL (grid, fields, events, components) | `xnano` package root modules + `components/` |
| Shared host/action/content/stage contracts | `xnano.core` |
| Backend paint contracts | `xnano.core.controllers` |
| Terminal host + native lowering | `xnano.terminal` |
| Web host + HTML/HTTP | `xnano.web` |
| CLI parsing | `xnano.cli` |
| Private plumbing | top-level `xnano/_*.py` only |
| Scene graph, terminal lifecycle, render IR | `xnano_core.core` |
| Raw ratatui/crossterm/tachyonfx bindings | `xnano_core.rust.native` |

Do not call native terminal initialization/restoration or standalone native
event polling in application code; use `CoreSession` through `Terminal`.
Keep grid/component policy in the public DSL, backend painting in
controllers/nodes, and terminal runtime mechanics in `xnano-core`.

VHS demo recording and tape generation live under `scripts/` only — do not
embed VHS tooling under the package.

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
   - NOTE: This is not a rule 100% of the time. For example, one of the ``zyx`` library's main user facing abstractions are called `semantic operations`, which are llm-powered operations that perform various tasks on python objects. **ONLY IF** a function is intended or implemented as one of the core features and/or user facing abstractions **AND** it's usage is presented in documentation as ``import module`` then ``module.fn()`` ``module.fn2()`` then it may be a single word.
     - Example: The semantic operations in ``zyx`` are named ``zyx.edit(...)`` (uses an LLM to edit python objects), ``zyx.parse(...)`` (confidence based LLM parsing), ``zyx.run(...)`` (standard agent loop).

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

```uv run pytest``

### LINTING

All linting & pre-commit configuration is handled through ``ruff`` and ``prek`` all code
changes must be followed by running:

``uv run prek run --all-files``

### xnano-core SPECIFIC RULES

**ANY** changes to ``xnano-core`` must be followed by running:

```bash
cd xnano-core
cargo clean
maturin develop --uv
```
