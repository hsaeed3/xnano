# History

Release notes of every xnano package, newest first. This file is generated from the GitHub releases by `scripts/history.py` (run `make history`); do not edit it by hand.

## xnano

### 2.0.0-beta.2 (pre-release)

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v2.0.0-beta.2).

### 2.0.0-beta.1 (pre-release)

Published 2026-10-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v2.0.0-beta.1).

### 1.2.3

Published 2026-08-05. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.3).

#### xnano v1.2.3

`v1.2.3` is the stable release of the 1.2.3 prerelease cycle. It brings the
ergonomics work from b1/b2 together with a clearer public API, vertical
alignment, non-blocking grid effects, a complete documentation refresh, and
faster construction of the small content values used throughout rendering.

##### Highlights

- **Grid effects are non-blocking and consistently named.** Use
  `self.grid_effect(...)` to start an effect and keep hooks, ticks, and
  rendering moving. The previous `grid_play_effect(...)` remains available as
  a deprecated alias. Effects are now covered end-to-end: tests verify that
  they paint, advance across frames, complete, cancel, and work from the
  supported hook paths. (#135)
- **Two-axis alignment.** `horizontal_align` replaces `align` for horizontal
  placement, and the new `vertical_align` supports `"top"`, `"middle"`, and
  `"bottom"` placement within a field. The old `align` spelling still works as
  a deprecated alias. The same explicit names are used by `Field`, `Text`,
  `TextBlock`, table columns, `Terminal`, and `render()`. (#139)
- **Clearer foreground naming.** APIs where `color` means a text/content
  foreground now expose `foreground`; `color` remains a deprecated,
  compatibility-preserving alias. Specific colors such as `border_color` and
  effect colors deliberately retain their existing names. (#136)
- **A current, runnable documentation site.** The Core Concepts section now
  covers the stable 1.2 API across grids, fields, state, actions, events,
  components, effects, terminal, web, requests, device controls, Markdown,
  and CLI. Runnable Pyodide examples are tested across all documentation pages,
  replacing the stale test that targeted the removed sandbox page. (#138)

##### Migration guide

###### Effects: `grid_effect()` is the canonical non-blocking API

```python
#### before (still works, deprecated)
self.grid_play_effect("fade", duration_ms=300, fields=["body"])

#### after
self.grid_effect("fade", duration_ms=300, fields=["body"])
self.status = "Animation started"  # runs immediately; hooks do not block
```

Use a handle when the calling scope owns the animation lifetime:

```python
with self.grid_effect("coalesce", duration_ms=450, fields=["body"]):
    self.status = "Animating"
```

###### Foreground and alignment names

```python
from xnano import BaseGrid, Field
from xnano.components.text import Text


class Status(BaseGrid):
    # before: color="cyan", align="center"
    label: Text = Field(
        default=Text("Ready", foreground="cyan"),
        horizontal_align="center",
        vertical_align="middle",
        height=5,
    )
```

The same migration applies to `render()`, `Terminal.render()`,
`TextBlock`, `Run`, table `Column`s, and field updates:

```python
#### before: grid_update_field("label", color="green", align="right")
self.grid_update_field(
    "label",
    foreground="green",
    horizontal_align="right",
)
```

`color` remains correct for values that name a specific thing, including
`border_color` and effects such as `FadeEffect(color="violet")`.

###### Grid helper namespace

```python
#### before (still works, deprecated)
self.set_background("slate-950")
self.schedule_update(refresh, field="body")

#### after
self.grid_set_background("slate-950")
self.grid_schedule_update(refresh, field="body")
```

###### Context event payloads

```python
from xnano.hooks import on_keyboard


@on_keyboard("ctrl+s")
def save(self, ctx):
    # before: ctx.keyboard
    if ctx.keyboard_event.matches("ctrl+s"):
        self.save_document()
```

`ctx.keyboard`, `ctx.mouse`, and `ctx.tick` still delegate to
`ctx.keyboard_event`, `ctx.mouse_event`, and `ctx.tick_event`, respectively,
but now emit a `DeprecationWarning`.

##### Grid API cleanup

`BaseGrid` now uses its public namespace consistently. Its supported helpers
are named `grid_*` (for example `grid_set_frame`, `grid_set_background`, and
`grid_schedule_update`), while internal markers use `__xnano_*__` / `_grid_*`.
Grids expose `__xnano_grid__`, allowing framework internals to recognize them
without importing `BaseGrid` and creating a circular dependency. The previous
unprefixed helper names remain deprecated aliases. (#141)

##### Rendering, content, and performance

- `Text` preserves authored indentation after newlines, including when text
  wraps.
- Multiple values passed to `render()` are measured and packed to their
  content, so `gap` is the literal number of cells between renderables rather
  than an accidental viewport-sized separation.
- `SizingLike` now gives editors useful literals for common widths/heights;
  `Sizing.parse("full")` resolves to `100%`.
- Geometry primitives now live in `xnano.area`: `Area`, `Size`, `Padding`,
  `align_area`, and the alignment aliases remain re-exported from
  `xnano.types` for compatibility.
- Hot `Run` and `TextBlock` construction keeps dataclass-generated
  initialization while retaining the deprecated `color`/`align` aliases. This
  removes the generic `*args`/`**kwargs` wrapper from rendering's high-volume
  content path; a local 200,000-`Run` construction check improved from 0.150s
  to 0.134s.

##### Context, state, and hosts

The stable host contract is the b2 contract: `state=` belongs on
`Terminal(...)`, `Terminal.offscreen(...)`, and `Web(...)`, preserving the
natural context-manager form:

```python
with Terminal(state=Notes()) as terminal:
    terminal.run(App())
```

`ctx.tick_event`, `ctx.keyboard_event`, and `ctx.mouse_event` are the
canonical event-payload accessors. The former `ctx.tick`, `ctx.keyboard`, and
`ctx.mouse` accessors remain available as deprecated aliases, so existing apps
continue to run while they migrate. Request dispatch now carries the request
through `Context.request` directly.

##### Skills and packaging

The repository now includes focused development skills for `xnano`,
documentation/examples, and `xnano-core`. The published package also includes
an application-facing `xnano` skill with references for grids, components,
hooks, hosts, and request servers; wheel verification confirms the skill files
ship under `xnano/.agents/skills`.

##### Documentation and migration

Examples, README snippets, generators, and API documentation use the stable
names: `foreground`, `horizontal_align`, `grid_effect`, and the current
`Context` event accessors. Top-level imports in the README reflect the public
`xnano` exports, while library code continues to prefer concrete internal
modules.

##### Deprecations

- `ctx.tick` → `ctx.tick_event`
- `ctx.keyboard` → `ctx.keyboard_event`
- `ctx.mouse` → `ctx.mouse_event`
- `color` → `foreground` where it represents content/text foreground
- `align` → `horizontal_align`
- `grid_play_effect(...)` → `grid_effect(...)`
- Unprefixed `BaseGrid` helpers such as `set_frame`, `set_background`, and
  `schedule_update` → their `grid_*` equivalents

All deprecated aliases continue to work and issue `DeprecationWarning`s; they
are intentionally compatibility bridges, not immediate breaks.

##### Changelog

* docs: rewrite core concepts & finalize docs for xnano 1.2 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/134
* chore: ruff/isort by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/137
* feat: improve grid ergonomics by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/142
* chore: add xnano skills by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/143
* perf: avoid deprecated alias wrapper overhead by @hsaeed3

### 1.2.3b2

Published 2026-07-31. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.3b2).

Adds deprecation to breaking changes for event accessors on `xnano.context.Context`, as well as reverting the `state` constructor change from `1.2.3b1`. The upside to passing `state=` is obvious, as it allows for the usage of the `with Terminal(state=...) as t:` context-manager pattern.

##### Hosts

**`Terminal(state=...)` and `Web(state=...)` are back on the constructor.** `1.2.3b1` moved `state` into `run()`/`render()`, which quietly broke the `with Terminal(state=...) as t:` context-manager pattern — the reason state lived at construction in the first place. Reverted: constructor state is first-class again on `Terminal`, `Terminal.offscreen`, and `Web`, exactly as in `1.2.2`.

##### Context

The event-payload accessor rename from `1.2.3b1` (`ctx.tick`/`keyboard`/`mouse` → `ctx.tick_event`/`keyboard_event`/`mouse_event`, matching `xnano.events.Event`) **stays, but is no longer a hard break.** The old names return as deprecated aliases: they delegate to the new accessors, emit a `DeprecationWarning` at runtime, and — via PEP 702 `@deprecated` — render with a strikethrough in editors. They won't be removed for several versions.

##### Docs

README examples now import everything the top-level `xnano` namespace re-exports (`BaseGrid`, `Field`, `Terminal`, `Context`, the `@on_*` hooks, `render`) straight from `xnano`, leaving `from xnano.components import Text/Component/TextBlock` to stand out as the deliberate special cases they are.

##### Deprecations

- `ctx.tick` → `ctx.tick_event`
- `ctx.keyboard` → `ctx.keyboard_event`
- `ctx.mouse` → `ctx.mouse_event`

Each still works and returns the same payload; migrate at your leisure.

##### Changelog

* release: xnano 1.2.3b2 — revert state move, deprecate event accessors by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/133

### 1.2.3b1

Published 2026-07-31. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.3b1).

#### xnano v1.2.3b1

First prerelease for the `v1.2.3` stable version.  Although this release carries no more than ergonomics upgrades and small bug fixes, it **does** contain 2 breaking changes and will remain as a beta release for the moment.

##### Rendering

- **`Text` keeps indentation after a newline.** Explicit indentation or spaces following a `\n` were dropped for any wrapping `Text` — the wrapping renderer trimmed leading whitespace off every line. Fixed in `xnano-core 0.0.17` (`trim: false`); authored indentation now lands as written. (#128)
- **`render()` packs multiple renderables by content.** Passing several top-level renderables gave each one an equal fill share of the viewport, so one-line items floated apart and any `gap` read as enormous whitespace. They now measure to their content size and pack from the top through the same layout path fields use, with `gap` as the literal number of cells between them. `gap=1` is one row, as it always should have been.

##### Sizing

Literal types for the common **`width`/`height`** values are now annotated. `SizingKeyword` (`"fit"`, `"fill"`, `"full"`, `"auto"`, the flex utilities, …) and `SizingPercentage` (`"0%"` – `"100%"`) fold into `SizingLike`, so editors autocomplete the values you reach for most while bare `str` stays in the union for open-ended forms like `"1fr"` or `"1/3"`. `Sizing.parse` also learned the `"full"` keyword (→ `100%`, matching the `w-full` rewrite) so every annotated literal actually resolves. (#102)

##### Context & hooks

- **Event payload accessors renamed** to match `xnano.events.Event`: `ctx.tick` / `ctx.keyboard` / `ctx.mouse` are now `ctx.tick_event` / `ctx.keyboard_event` / `ctx.mouse_event`. (#104)
- The internal `_beta_request` facade stash is gone — the HTTP request now rides on a real `Context.request` field instead of being `setattr`'d onto the runtime during dispatch. No user-facing change; `ctx.request` reads the same. (#105)

##### Hosts

**State moves off the constructor and into `run()` / `render()`.** `Terminal` and `Web` no longer take `state=` at construction; you pass it at paint time, and the constructors instead take a `state_type` for typing (à la `pydantic_ai.Agent`). `Web` is now generic over its state type. (#103)

##### Breaking changes

- `ctx.keyboard` / `ctx.mouse` / `ctx.tick` → `ctx.keyboard_event` / `ctx.mouse_event` / `ctx.tick_event`. (#104)
- `Terminal(state=...)` / `Web(state=...)` → pass `state=` to `run()` / `render()`:

  ```python
  # before
  Terminal(state=Notes()).run(App())
  # after
  Terminal().run(App(), state=Notes())
  ```
  (#103)

##### Changelog

* release: xnano 1.2.3b1 prerelease fixes by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/132

### 1.2.2

Published 2026-07-30. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.2).

#### xnano v1.2.2

A maintenance release on top of 1.2.1's ratatui 0.30 migration. No API breaks — this one hardens rendering, components, and validation, and opens up a browser story: **xnano now runs under Pyodide/WASM.** Everything below is bug fixes and coverage; upgrade in place.

##### Browser / WASM (Pyodide)

xnano can now render inside a Pyodide (WebAssembly) runtime. `device.py`'s ClearType capability lookup is guarded so it no longer blows up on wasm builds where the underlying terminal query is absent — the framework degrades instead of crashing on import. A new `docs/sandbox.md` walks through running xnano in the browser, and `scripts/set_version.py` now pins the sandbox alongside the rest of the release. WASM render + sandbox test suites were added to keep the path from regressing.

##### Rendering

`render()` now keeps styling from anything that carries its own — components, grids, and content primitives. Previously `styled` was driven only off the top-level kwargs, so `render(Text(...))`, `render(chart)`, and friends silently dropped their color/modifiers unless you also passed a style kwarg. A bare scalar with no style still stays plain text; anything richer keeps its paint. `lower_content` also now uses the live render area instead of a stale one, so component/content styling lands correctly.

##### Components

- **Options** windows long option lists instead of overflowing, and hover→index mapping is fixed so the dim hover indicator tracks the row your pointer is actually on. Dropdown coverage came along for the ride.
- **Chart** series were consolidated onto a single `schema.Series` (with marker support) — `chart.py` no longer carries its own parallel `Series` definition, so one type describes a series everywhere.

##### CLI & validation

- The CLI now renders help for `HelpException`, not only `HelpRequested` — invoking help through either path prints help instead of leaking an exception.
- TypedDict validation now honors `Required`/`NotRequired`.

##### Under the hood

CodSpeed continuous performance measurement added in CI, plus core/options benchmarks and runtime/options stress tests. Broad test-coverage expansion across components, the public core API, component base, entrypoint, and composition. Getting-started and zensical docs refreshed; Dependabot dependency bumps (GitHub Actions, Rust deps). `xnano-core` bumped to `0.0.16`.

##### Changelog

* chore(deps): bump actions/upload-artifact from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/98
* chore(deps): bump actions/checkout from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/99
* chore(deps): bump dorny/paths-filter from 3 to 4 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/100
* chore(deps): bump uvicorn from 0.51.0 to 0.52.0 in the python-dependencies group by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/101
* ci: add codspeed continuous performance measurement by @codspeed-hq[bot] in https://github.com/hsaeed3/xnano/pull/106
* chore: plus ultra by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/107
* fix(chart): consolidate Series onto schema.Series by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/108
* fix(options): scroll long lists with correct hover mapping by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/109
* fix(cli): handle HelpException in command dispatch by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/110
* fix(validation): respect Required/NotRequired qualifiers by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/111
* fix(device): lazy ClearType map for no-terminal-feature builds by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/112
* fix(render): preserve styling and pass live area to compose by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/113
* docs: refresh getting-started and zensical config by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/114
* test: expand coverage across components and framework by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/115
* chore(release): bump xnano to 1.2.2 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/116
* chore(release): bump xnano-core to 0.0.16 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/117
* docs(sandbox): add pyodide sandbox page by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/118
* test(pyodide): wasm render + sandbox coverage by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/119
* test(perf): benchmarks + stress suites by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/120
* test: core public API + framework coverage by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/121
* fix(tests): guard ComponentRenderContext subscript for Python 3.10 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/122
* fix(tests): skip ComponentRenderContext[Any] subscript on Python 3.10 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/123

##### New Contributors
* @codspeed-hq[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/106

### 1.2.1

Published 2026-07-29. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.1).

##### What's Changed
* chore(docs): enable instant navigation within `zensical.toml` for docs (#89) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/89
* chore(deps): add Dependabot config by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/90
* chore(deps): bump actions/download-artifact from 6 to 8 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/91
* chore(deps): bump actions/checkout from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/92
* chore(deps): bump softprops/action-gh-release from 2 to 3 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/93
* chore(deps): bump actions/setup-node from 6 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/94
* chore(deps): bump actions/setup-python from 6 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/95
* chore(deps): bump the rust-dependencies group in /xnano-core with 3 updates by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/96
* fix(xnano-core): migrate rust bindings to ratatui 0.30 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/97

##### New Contributors
* @dependabot[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/91

### 1.2.0

Published 2026-07-29. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.0).

##### xnano v1.2.0

This release promotes the former `xnano.beta` preview into the stable `xnano` namespace and retires the old framework surface entirely. The parallel `beta/` package is gone — its decoupled design *is* the framework now. Net effect: ~28,000 lines removed, one shared runtime under every host.

###### Rewritten public API

The old monolithic modules were replaced by a flat, modular DSL:

- `xnano/grid.py` (1,810 lines), `xnano/terminal/terminal.py` (1,182 lines), the full `xnano/web/*` HTML paint backenxnano/color.py`,`xnano/images.py`, and the entire private `_renderable` / `_styles` / `_types` /
`_tailwind_classes` / `_dispatcfunction_hooks` /`_core_bindings` layer are **removed**.
- In their place: `grids.py`, `ts.py`, `actions.py`,`colors.py`, `tailwind.py`, `effects.py`, `terminal.py`, `web.py`, plus `server/`, `cli/`,
`utils/`, `components/`, and a ime`, `Frame`, contentprimitives, controller, stage, dispatch).

Export changes:

- New top-level exports: `render()`, `Frame`, `Runtime`, `Component`, `Command`.
- The `Grid` alias and the bare use `BaseGrid` and the named`@on_*` hooks.
- `color=` is now `foreground=`s as a runtime alias).
- `Text` accepts plain string defaults; `grid_render(ctx)` supported.

###### One runtime for every host

Terminal, web, and the one-shot `render()` helper all run on the same offscreen `Runtime` /
`TerminalController` engine. WeHTML painter — it streams cellsfrom the same core path the terminal uses.

###### Fields, input & interaction

- `Field(z=)` threads z-order through a field's whole subtree (string, component, nested
grid) with additive global pain
- `Field(overlay=)` renders an out-of-flow centered popup that paints opaque over the panels
behind it.
- `Terminal(mouse_events=)` enables mouse capture; click-to-focus is no longer gated behind
arrow-nav.
- `Options` defaults to `searchable=False` (`Dropdown` overrides back to `True`) with a
distinct dim hover indicator separate from selection.
- Text/Options inputs no longer consume `ctrl`/`alt` chords as typed text, so app shortcuts (e.g. `ctrl+s`) reach hooks; thaced through the real terminal cursor each frame.

###### Rendering & performance

- Each live frame is drawn inside a crossterm synchronized update, so the emulator applies it
atomically — fixes row tearing se corruption that left garbledglyphs in other shells on exit.
- The showcase demo advances and adapts paint cadence toterminal size (~10–15fps), keeping full-screen truecolor motion smooth without pinning the CPU.

###### Also

- Scrollable markdown viewer and the `xnano PATH.md` runner.
- Terminal-restore fixes on exit and hangup.

### 1.1.7

Published 2026-07-28. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.7).

##### What's Changed
* beta: grid_render(ctx), color→foreground alias, str Text defaults (v1.1.7) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/77

### 1.1.6

Published 2026-07-28. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.6).

##### What's Changed
* docs/beta-context: update `README.md` to include context on `xnano.beta` API by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/75
* beta: showcase demo rewrite + render fixes (sync output, exit reset, transparent overlays) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/76

### 1.1.5

Published 2026-07-26. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.5).

##### What's Changed
* beta: ergonomics + bug-fix pass (fill, scroll, focus, threading, options) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/73
* chore: bump ``xnano`` to v1.1.5 for release by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/74

### 1.1.4

Published 2026-07-24. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.4).

##### What's Changed
* Beta ergonomics pass + stable-API deprecation cleanup by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/72

### 1.1.3

Published 2026-07-24. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.3).

##### What's Changed
* fix: make beta runtime updates reliable by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/71

### 1.1.2

Published 2026-07-23. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.2).

##### What's Changed
* fix: complete beta runtime integration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/70

### 1.1.1

Published 2026-07-23. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.1).

##### What's Changed
* fix: exit terminal process on hangup by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/66
* chore: bump xnano to `v1.1.1` by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/67
* feat: ergonomics pass — container fields, scroll, group focus, web cursor/device parity by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/68
* feat: xnano.beta preview — decoupled framework, scrollable markdown viewer, terminal-restore fix by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/69

### 1.1.0

Published 2026-07-23. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.0).

##### What's Changed
* docs: remove data-preview annotations from index.md by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/57
* feat!: xnano 1.1.0 — big & better text update by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/63
* chore: remove .claude from tracked directories by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/64
* fix: include text editor in pyodide wheel by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/65

### 1.0.16

Published 2026-07-17. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.16).

##### What's Changed
* fix: update ``StateT | None`` removing optional None type to resolve "state might be None"  type checking errors when accessing state through context within hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/56

### 1.0.15

Published 2026-07-15. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.15).

##### What's Changed
* Bump xnano to 1.0.15, cap requires-python below 3.14 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/55

### 1.0.14

Published 2026-07-15. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.14).

##### What's Changed
* docs: cross-link xnano primitives across hooks and guide docs by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/53
* refactor: rename @on to @on_action, bump version to 1.0.14 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/54

### 1.0.13

Published 2026-07-15. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.13).

##### What's Changed
* docs: integrate context7 widget within documentation and style it a bit by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/51
* fix: initialize user Grid classes by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/52

### 1.0.11

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.11).

##### What's Changed
* docs: add interactive Pyodide sandbox by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/49
* feat: add optional terminal image rendering by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/50

### 1.0.10

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.10).

##### What's Changed
* docs: rewrite and restyle documentation by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/46
* docs: unify demo generation and refresh assets by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/47
* fix(tui): render grid roots through layout by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/48

### 1.0.9

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.9).

##### What's Changed
* fix(pyodide): preserve terminal output colors by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/45

### 1.0.8

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.8).

##### What's Changed
* release(xnano/v1.0.8) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/44

### 1.0.7

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.7).

##### What's Changed
* release(xnano/v1.0.7) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/43

### 1.0.6

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.6).

### 1.0.5

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.5).

### 1.0.4

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.4).

##### What's Changed
* docs: concepts rewrite and reference restructure by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/41
* feat: Pyodide/WebAssembly wheel support for xnano-core by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/42

### 1.0.3

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.3).

### 1.0.2

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.2).

##### What's Changed
* chore(ruff): update isort configuration for improved import spacing by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/40

### 1.0.1

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.1).

##### What's Changed
* [ImgBot] Optimize images by @imgbot[bot] in https://github.com/hsaeed3/xnano/pull/31
* feat: Tailwind CSS class_name support for grid fields by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/32
* refactor: finalize module layout and interface-neutral core by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/33
* test: update suite for module layout and BaseGrid by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/34
* chore: retarget examples and scripts to the new package layout by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/35
* refactor: polish package docs, Actions tests, and type fixes by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/36
* docs: retarget site, README, and nav for the new package layout by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/37
* docs: retarget AGENTS.md and CLAUDE.md for the new package layout by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/38
* refactor: optimize runtime dispatch and enforce imports by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/39

### 1.0.0

Published 2026-07-10. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0).

##### What's Changed
* refactor: migrate xnano.beta into the stable xnano namespace by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/16
* docs: update API reference for the xnano namespace migration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/17
* chore: update examples and dev scripts for the xnano namespace migration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/18
* perf: optimize core rendering and framework hot paths by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/19
* docs: reorganize guides and expand documentation site by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/21
* [ImgBot] Optimize images by @imgbot[bot] in https://github.com/hsaeed3/xnano/pull/22
* Harden terminal teardown and add background cell-filter effects by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/23
* Add xnano feature showcase demo app by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/24
* docs: add title/feature-tour demo GIFs and VHS tooling by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/25
* refactor(core): sound BufferMutView borrows and unicode IR measure by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/26
* refactor(arch): fix hook registration, layout measure, and event cache by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/27
* feat(beta): web UI host, htmx controller, and request hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/28
* feat(beta): add Command CLI class by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/29
* docs(beta): Web UI, request hooks, and Commands preview docs by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/30

##### New Contributors
* @imgbot[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/22

### 1.0.0b4

Published 2026-07-10. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0b4).

##### What's Changed
* feat: field focus, editable text input, and on_focus/on_field/on_poll hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/14
* feat: add Table, Chart, and Progress declarative components by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/15

### 1.0.0b3

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0b3).

##### What's Changed
* fix(render_ir): push field background onto spans rather than flood-filling slot by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/8
* fix(frame): restrict Field background to text cells; add TailwindColorBinding and VHS utils by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/9
* docs: add showcase, restructure nav, add concept demos, and VHS scripts by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/10
* docs(readme): replace demo GIFs with concept dark GIFs; add render and styled-text examples by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/11
* fix(render_tree): clamp absolute rect to buffer bounds on terminal resize by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/12
* feat(demo): add python -m xnano interactive showcase by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/13

### 1.0.0b2

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0b2).

##### What's Changed
* feat(standardized-sizing) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/7

### 1.0.0b1

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0b1).

##### What's Changed
* refactor(demos): streamline demo steps and improve function formatting by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/5
* feat(render): update `render(..)` call compatibility and functionality by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/6

### 0.99.7

Published 2026-07-07. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v0.99.7).

### 0.99.6

Published 2026-07-07. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v0.99.6).

##### What's Changed
* refactor(tui) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/3
* refactor(beta) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/4

##### New Contributors
* @hsaeed3 made their first contribution in https://github.com/hsaeed3/xnano/pull/3

## xnano-core

### 2.0.0-beta.2 (pre-release)

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v2.0.0-beta.2).

### 2.0.0-beta.1 (pre-release)

Published 2026-10-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v2.0.0-beta.1).

### 0.0.17

Published 2026-07-31. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.17).

#### xnano-core v0.0.17

Silly little layout bug fixes.

##### Text wrapping

Wrapped paragraphs now **preserve authored leading whitespace**. The native paragraph widget wrapped with ratatui's `Wrap { trim: true }`, which strips leading whitespace from every laid-out line — so any indentation after a `\n` silently vanished the moment a paragraph wrapped (which is the default). Switched to `trim: false`, so indentation the caller wrote survives to the buffer. This is the native half of xnano's `Text` indentation fix (see xnano #128); markdown, tables, and every other paragraph-backed surface inherit the corrected behavior.

### 0.0.16

Published 2026-07-30. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.16).

##### What's Changed
* chore(deps): bump actions/upload-artifact from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/98
* chore(deps): bump actions/checkout from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/99
* chore(deps): bump dorny/paths-filter from 3 to 4 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/100
* chore(deps): bump uvicorn from 0.51.0 to 0.52.0 in the python-dependencies group by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/101
* ci: add codspeed continuous performance measurement by @codspeed-hq[bot] in https://github.com/hsaeed3/xnano/pull/106
* chore: plus ultra by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/107
* fix(chart): consolidate Series onto schema.Series by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/108
* fix(options): scroll long lists with correct hover mapping by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/109
* fix(cli): handle HelpException in command dispatch by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/110
* fix(validation): respect Required/NotRequired qualifiers by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/111
* fix(device): lazy ClearType map for no-terminal-feature builds by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/112
* fix(render): preserve styling and pass live area to compose by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/113
* docs: refresh getting-started and zensical config by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/114
* test: expand coverage across components and framework by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/115
* chore(release): bump xnano to 1.2.2 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/116
* chore(release): bump xnano-core to 0.0.16 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/117
* docs(sandbox): add pyodide sandbox page by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/118
* test(pyodide): wasm render + sandbox coverage by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/119
* test(perf): benchmarks + stress suites by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/120
* test: core public API + framework coverage by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/121
* fix(tests): guard ComponentRenderContext subscript for Python 3.10 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/122

##### New Contributors
* @codspeed-hq[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/106

### 0.0.15

Published 2026-07-29. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.15).

##### What's Changed
* chore(docs): enable instant navigation within `zensical.toml` for docs (#89) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/89
* chore(deps): add Dependabot config by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/90
* chore(deps): bump actions/download-artifact from 6 to 8 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/91
* chore(deps): bump actions/checkout from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/92
* chore(deps): bump softprops/action-gh-release from 2 to 3 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/93
* chore(deps): bump actions/setup-node from 6 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/94
* chore(deps): bump actions/setup-python from 6 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/95
* chore(deps): bump the rust-dependencies group in /xnano-core with 3 updates by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/96
* fix(xnano-core): migrate rust bindings to ratatui 0.30 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/97

##### New Contributors
* @dependabot[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/91

### 0.0.14

Published 2026-07-29. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.14).

##### What's Changed
* docs(chore): add pointer for `uv run xnano` demo within README.md by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/78
* beta: field z/overlay, mouse events, input & Options ergonomics (#82) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/83
* Migrate xnano.beta into the stable namespace + terminal/demo perf by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/84
* release(xnano-core): bump `xnano-core` to `v1.0.14` for release by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/85

### 0.0.13

Published 2026-07-28. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.13).

##### What's Changed
* docs/beta-context: update `README.md` to include context on `xnano.beta` API by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/75
* beta: showcase demo rewrite + render fixes (sync output, exit reset, transparent overlays) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/76

### 0.0.12

Published 2026-07-23. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.12).

##### What's Changed
* docs: remove data-preview annotations from index.md by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/57
* feat!: xnano 1.1.0 — big & better text update by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/63
* chore: remove .claude from tracked directories by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/64
* fix: include text editor in pyodide wheel by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/65

### 0.0.11

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.11).

### 0.0.10

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.10).

##### What's Changed
* docs: concepts rewrite and reference restructure by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/41
* feat: Pyodide/WebAssembly wheel support for xnano-core by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/42

### 0.0.9

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.9).

### 0.0.8

Published 2026-07-10. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.8).

##### What's Changed
* refactor: migrate xnano.beta into the stable xnano namespace by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/16
* docs: update API reference for the xnano namespace migration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/17
* chore: update examples and dev scripts for the xnano namespace migration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/18
* perf: optimize core rendering and framework hot paths by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/19
* docs: reorganize guides and expand documentation site by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/21
* [ImgBot] Optimize images by @imgbot[bot] in https://github.com/hsaeed3/xnano/pull/22
* Harden terminal teardown and add background cell-filter effects by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/23
* Add xnano feature showcase demo app by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/24
* docs: add title/feature-tour demo GIFs and VHS tooling by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/25
* refactor(core): sound BufferMutView borrows and unicode IR measure by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/26
* refactor(arch): fix hook registration, layout measure, and event cache by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/27
* feat(beta): web UI host, htmx controller, and request hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/28
* feat(beta): add Command CLI class by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/29
* docs(beta): Web UI, request hooks, and Commands preview docs by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/30

##### New Contributors
* @imgbot[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/22

### 0.0.7

Published 2026-07-10. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.7).

##### What's Changed
* feat: field focus, editable text input, and on_focus/on_field/on_poll hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/14
* feat: add Table, Chart, and Progress declarative components by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/15

### 0.0.6

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.6).

##### What's Changed
* fix(render_ir): push field background onto spans rather than flood-filling slot by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/8
* fix(frame): restrict Field background to text cells; add TailwindColorBinding and VHS utils by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/9
* docs: add showcase, restructure nav, add concept demos, and VHS scripts by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/10
* docs(readme): replace demo GIFs with concept dark GIFs; add render and styled-text examples by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/11
* fix(render_tree): clamp absolute rect to buffer bounds on terminal resize by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/12
* feat(demo): add python -m xnano interactive showcase by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/13

### 0.0.5

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.5).

##### What's Changed
* feat(standardized-sizing) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/7

### 0.0.4

Published 2026-07-07. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.4).

##### What's Changed
* refactor(tui) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/3
* refactor(beta) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/4

##### New Contributors
* @hsaeed3 made their first contribution in https://github.com/hsaeed3/xnano/pull/3

## xnano-audio

### 0.2.0

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-audio/v0.2.0).

### 0.1.0

Published 2026-10-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-audio/v0.1.0).

## xnano-image

### 0.2.0

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-image/v0.2.0).

### 0.1.0

Published 2026-10-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-image/v0.1.0).
