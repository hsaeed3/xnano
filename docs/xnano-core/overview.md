---
title: "Overview"
---

# xnano-core

xnano-core is the compiled Rust extension that does the actual terminal work — rendering frames, driving the event loop, and managing effects. It ships as a separate package (`xnano-core` on PyPI) and is always installed automatically when you install `xnano`. You never import it yourself.

---

## The short version

When you write a `Grid` and call `Terminal().run()`, here's what actually happens:

1. xnano converts your Python `Grid`, `Field`, and `Text` declarations into a small intermediate representation — a tree of render nodes.
2. That tree gets handed to a `Session` object, which speaks to xnano-core.
3. xnano-core (Rust) renders the tree into an off-screen buffer, diffs it against what's already on screen, and emits only the changed cells.

The Rust layer also owns the event loop — blocking on input, firing tick timers, and calling back into Python for each event.

---

## What lives where

xnano-core ships two sub-packages:

| Package | What's in it |
|---|---|
| `xnano_core.rust.native` | The full ratatui / crossterm / tachyonfx surface — widgets, layout primitives, effects, event types, and raw terminal control |
| `xnano_core.core` | A thin session bridge that Python uses to start and drive a live render loop |

You'll rarely need to think about either of these. They're the engine room; `xnano.beta` is the steering wheel.

---

## Architecture

```
Your Python Grid / Terminal call
        │
        ▼
  xnano.beta  ──── render-node tree ────▶  xnano.beta.core.session
                                                  │
                                                  ▼
                                         xnano_core.core  (Rust)
                                                  │
                             ┌────────────────────┴──────────────────────┐
                             ▼                                           ▼
                    xnano_core.rust.native                   xnano_core.rust.native
                      ratatui widgets                          crossterm I/O
```

**Python is responsible for:**

- Interpreting `Sizing` constraints (`"25%"`, `"1fr"`, `3`) and translating them into ratatui `Constraint` values
- Converting your `Text`, `Sparkline`, and other components into render nodes
- Dispatching `@on_keyboard`, `@on_mouse`, `@on_tick`, and `@on_state` hooks

**Rust is responsible for:**

- Running the event loop and frame timing
- Buffer diffing and writing escape sequences to stdout
- Visual effects via tachyonfx

---

## Versioning

xnano-core versions are pinned exactly. xnano will refuse to start if the installed version doesn't match what it was built against — the protocol between the two layers isn't stable across revisions yet.

```python
# xnano/beta/core/version.py
_COMPATIBLE_XNANO_CORE_VERSION = "0.0.5"
```

If you hit a version mismatch error, reinstall `xnano` (it will pull the right `xnano-core` along with it) rather than upgrading `xnano-core` on its own.

---

## Sub-pages

- [Engine](engine.md) — event loop, session lifecycle, frame commit
- [Native Bindings](native.md) — ratatui, crossterm, and tachyonfx surface exposed to Python
