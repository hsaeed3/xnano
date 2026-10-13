---
title: "xnano"
icon: "fontawesome/solid/x"
---

# xnano

xnano is a Python terminal UI framework built on the [ratatui](https://ratatui.rs) and
[tachyonfx](https://github.com/ratatui/tachyonfx) Rust crates. The Rust engine owns the cell
store, layout, input, effects and persistent state; Python drives it.

The `xnano` distribution installs three packages:

| Distribution | Import | What it provides |
| --- | --- | --- |
| `xnano-core` | `xnano` | The terminal runtime, buffers, operations, effects, input and state. |
| `xnano-audio` | `xnano_audio` | Synthesis, melodies, playback and capture. |
| `xnano-image` | `xnano_image` | Image and animation loading and conversion to terminal cells. |

The API is currently available as the compiled module `xnano_core._xnano_core`; the reference
lists every class and function with examples.


The [legacy v1 guides](v1/index.md) cover the previous high-level API, available from `xnano.deprecated`.
