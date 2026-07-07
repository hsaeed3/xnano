# Architecture and Code Style Guide for `xnano`

This document details the core philosophy, system architecture, native Rust binding structures, and high-level Python code style conventions for the `xnano` package.

## Library Structure

`xnano` is a Python TUI framework. It sits on top of **`xnano-core`**, a separate package that exposes **ratatui**, **crossterm**, and **tachyonfx** through PyO3. The framework never calls those libraries directly — all terminal I/O, rendering, and effects go through `xnano_core`.

```
User app (Grid subclass + @on_* hooks)
        │
        ▼
   xnano.beta          ← declarative layout, events, render IR, type conversions
        │
        ▼
   xnano_core.core     ← CoreSession, CoreRenderNode, CoreRenderContent, CoreEvent
        │
        ▼
   xnano_core.rust.native  ← ratatui/crossterm/tachyonfx primitives (PyO3)
        │
        ▼
   xnano-core/rust/src/bindings  ← Rust wrappers around native types
```

### `xnano-core` — native bindings

**Location:** `xnano-core/` (workspace member, built with maturin).

#### Python package (`xnano-core/python/xnano_core/`)

| Module | Purpose |
|--------|---------|
| `xnano_core` | Minimal root — exports `CoreEvent`, `CoreTickEvent`, `CoreTerminalEventKind` |
| `xnano_core.core` | **Primary API for `xnano.beta`** — re-exports the engine layer |
| `xnano_core.rust` | Barrel import for all native primitives |
| `xnano_core.rust.native` | Compiled extension (`native.abi3.so`) + `.pyi` stubs |
| `xnano_core.rust.engine` | Stateful runtime submodule (registered by Rust on import) |

**Engine types** (import via `from xnano_core.core import …`):

- `CoreSession` — owns terminal lifecycle, effect manager, event loop. Use `CoreSession.init()` for live terminals or `CoreSession.offscreen(w, h)` for tests. Only type allowed to call `ratatui::init` / `restore`.
- `CoreRenderNode` — scene-graph node with geometry, flex layout, children, z-order, and `effect_key`. Builders: `.leaf()`, `.row()`, `.column()`, `.stack()`.
- `CoreRenderContent` — tagged payload: `.empty()`, `.widget()`, `.stateful()`, `.drawable()`.
- `CoreEvent` / `CoreTickEvent` / `CoreTerminalEventKind` — unified input and tick events from `poll_event` / `read_event`.
- `CoreTerminalRef` — scope-guarded escape hatch to the raw `DefaultTerminal`.

**Native primitives** (import via `from xnano_core.rust import native`):

- **Layout:** `Rect`, `Margin`, `Direction`, `Alignment`, `Constraint`, `Layout`, …
- **Style & text:** `Color`, `Style`, `Modifier`, `Span`, `Line`, `Text`
- **Widgets:** `Block`, `Paragraph`, `RatList`, `RatTable`, `Gauge`, `Scrollbar`, `Chart`, …
- **Buffer:** `Buffer`, `BufferCell`, `render_widget`, `render_stateful_widget`
- **Terminal & device:** `Terminal`, `Frame`, `poll_event`, `read_event`, raw mode, alternate screen, cursor control
- **Effects:** `Effect`, `EffectManager`, `fade_to`, `slide_in`, `sequence_effects`, …

#### Rust crate (`xnano-core/rust/src/`)

Entry point: `lib.rs` defines `#[pymodule] fn native` → published as `xnano_core.rust.native`.

```
bindings/
├── mod.rs              # registration hub; wires engine submodule into sys.modules
├── layout.rs           # Rect, Constraint, Layout, …
├── style.rs            # Color, Style, Modifier
├── palette.rs          # color math (hex, HSL, lerp, tailwind)
├── text.rs             # Span, Line, Text
├── widgets.rs          # Block, Paragraph, RatList, Gauge, …
├── widgets_extra.rs    # RatTable, Scrollbar, Chart, Canvas, …
├── buffer.rs           # Buffer, BufferCell, render_widget
├── terminal.rs         # Frame, Terminal, KeyEvent, MouseEvent, poll/read
├── cursor.rs           # cursor show/hide/move/style
├── terminal_device.rs  # raw mode, size, alt screen, scroll
├── event_setup.rs      # keyboard enhancement flags, mouse capture
├── command.rs          # console styling (non-TUI)
├── fx.rs               # tachyonfx effects
├── convert.rs          # (internal) Python text extraction
├── convert_core.rs     # (internal) ratatui ↔ ratatui-core buffer sync for effects
├── crossterm_exec.rs   # (internal) stdout I/O
├── frame_ext.rs        # (internal) frame cursor hide
└── engine/
    ├── session.rs      # CoreSession, CoreTerminalRef
    ├── render_tree.rs  # CoreRenderNode, tree → buffer walk
    ├── content_bridge.rs  # CoreRenderContent dispatch
    ├── events.rs       # CoreEvent, CoreTickEvent, CoreTerminalEventKind
    ├── clock.rs        # (internal) tick scheduling
    └── panic_hook.rs   # (internal) terminal restore on panic
```

**Binding conventions:** Rust structs are prefixed `Py*` (e.g. `PyBuffer` → Python `Buffer`). Engine types use the `Core*` prefix. Pointer-backed handles (`Frame`, `BufferMutView`, `CoreSession`) are `unsendable`. Widget rendering resolves via registered `Py*` types, `_to_core()`, or duck-typed `.render()`.

### `xnano` — Python framework

**Location:** `xnano/` (depends on `xnano-core>=0.0.1`).

All implementation lives under **`xnano.beta`**. The root `xnano` package is a thin shell (`from xnano import Text`).

```
xnano/beta/
├── grid.py, fields.py       # Grid, Field, GridSettings — declarative layout
├── terminal.py              # Terminal — session owner & event loop entry point
├── hooks.py, context.py     # @on_* decorators, Context for handler scope
├── events.py                # Event + typed sub-events (keyboard, mouse, resize, …)
├── color.py, frame.py, types.py   # Color, Frame, Area, Size, Alignment, …
├── keyboard.py, mouse.py    # key/button/modifier types
├── cursor.py, device.py     # thin facades over native terminal control
├── exceptions.py            # Exit, FieldValidationError, TerminalNotActiveError
├── components/
│   ├── abstract.py          # AbstractComponent, ComponentRenderContext
│   └── text.py              # Text — unified text component
├── core/
│   ├── session.py           # Session — paint IR → CoreRenderNode bridge
│   ├── nodes.py             # render IR (SpanNode, ParagraphNode, FrameNode, …)
│   ├── renderable.py        # Renderable marker, render() helper
│   └── dispatch.py          # per-frame render, event pump, hook dispatch
└── utils/
    ├── native_types.py      # Python ↔ native type conversions
    ├── events.py            # CoreEvent → xnano Event parsing
    ├── validation.py        # pydantic-core field validation
    └── core.py              # hook arity, state expression eval
```

#### Key abstractions

| Abstraction | Role |
|-------------|------|
| **`Grid`** | Declarative layout container. Subclass with `Field(...)` layout fields and optional `state=True` fields. Metaclass generates `__init__`, collects fields, wires mouse handlers. |
| **`Field`** | Layout field descriptor — size/flex/fit, styling, frame, slide axes. `state=True` fields hold app state (not rendered). |
| **`Terminal`** | Context manager / `run(grid)` entry. Wraps `CoreSession` in internal `Session`. Exposes `cursor` and `device`. `Terminal.offscreen(cols, rows)` for test buffers. |
| **`Session`** (internal) | Batches per-frame paint requests → builds `CoreRenderNode` tree → calls `CoreSession.render()`. |
| **Render IR** (`core/nodes.py`) | Immutable nodes (`SpanNode`, `ParagraphNode`, `FrameNode`, …) lowered to native widgets via `NodeAssembler`. |
| **`AbstractComponent`** | User-facing renderable; implements `get_node()` → `RenderNode`. `Text` adapts to span/line/paragraph modes. |
| **`Event` + `@on_*`** | `Event` wraps `CoreEvent`; decorators (`on_keyboard`, `on_mouse`, `on_tick`, …) register handlers on grid classes. `dispatch.py` drives the render → poll → hook loop. |

#### Per-frame data flow

1. `Terminal.run(grid)` opens `CoreSession`.
2. `dispatch.render_frame()` → `Grid._grid_build_frame()` splits viewport into field areas, paints slot values.
3. `Session` accumulates `RenderRequest`s → `commit_requests()` assembles `CoreRenderNode` tree.
4. `CoreSession.render(root_node)` walks tree, runs effects, writes to terminal.
5. `dispatch.pump_events()` / `pump_tick()` → `Event.from_core_event(...)` → `@on_*` handlers via `Context`.

#### Layer boundaries

| Concern | Lives in |
|---------|----------|
| Declarative layout, hooks, field validation | `xnano.beta` |
| Paint IR → native widget lowering | `xnano.beta.core` + `utils/native_types` |
| Scene graph assembly, terminal lifecycle, effects | `xnano_core.core` (engine) |
| Raw ratatui/crossterm/tachyonfx types | `xnano_core.rust.native` |

**Do not** call `native.Terminal.init()` / `restore_terminal()` or standalone `native.poll_event()` in app code — use `CoreSession` via `Terminal`. **Do not** put layout/grid logic in `xnano_core`; there is no `Grid` in the core layer.

#### Public API

- `xnano` → `Text`
- `xnano.beta` → `Grid`, `Field`, `GridSettings`, `Terminal`, `Context`, `Color`, `Text`, `AbstractComponent`, `Renderable`, `render`, `@on_*` decorators, `Exit`

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

``xnano.beta`` **HEAVILY** utilizes type aliases, and especially ``typing.Union`` and ``typing.Literal`` based types. Any types that are defined inline must be annotated with an associated docstring **and separated by 2 lines from other content (same as all other item types except for class methods which are 1 new line and class fields/attributes which are no new lines unless going from init attributes to private attributes)

Whenever applicatble ``xnano.beta`` uses the ``|`` syntax over ``typing.Union`` following a strict set of conditions based on where the type is
being used.

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