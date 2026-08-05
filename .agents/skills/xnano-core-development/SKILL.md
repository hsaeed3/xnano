---
name: xnano-core-development
description: Develop and test xnano-core Rust/PyO3 bindings and engine behavior. Use for CoreSession, render tree/content/IR, native events, key bindings, editors, and Rust changes under xnano-core/.
---

# xnano-core development

Use this skill for native engine work. The package-distributed skill lives at
`xnano-core/python/xnano_core/.agents/skills/xnano-core`; this root skill adds
repository development and verification workflow.

## Boundaries

- Rust bindings live in `xnano-core/rust/src/bindings/`; engine code is under
  `rust/src/bindings/engine/`.
- Python consumers use `xnano_core.core`, whose public engine types retain the
  `Core*` names: `CoreSession`, `CoreRenderNode`, `CoreRenderContent`,
  `CoreRenderIR`, events, key bindings, editor, and terminal reference.
- Register every new PyO3 type in the engine module and preserve the Python
  barrel export. Keep binding policy separate from `xnano` grid/component
  policy.
- `CoreSession` and pointer-backed handles are unsendable and thread-bound.
  Create, render, poll, and restore them on their owning thread.
- Keep `session.rs` and `session_stub.rs` API-compatible across terminal and
  reduced/wasm builds. Preserve feature gates for terminal and editor support.

## Native rules

- `CoreSession.init(...)` is for a live terminal; `CoreSession.offscreen(...)`
  is for buffer-backed tests and non-terminal builds.
- Use `CoreRenderNode` for scene-graph layout and z-order, and
  `CoreRenderContent`/`CoreRenderIR` for the rendering payload. Prefer IR for
  framework-generated widgets to minimize Python/Rust crossings.
- Keep terminal initialization, restoration, and event ownership behind
  `xnano.Runtime`/`Terminal`; application code must not call raw crossterm
  lifecycle functions.
- Validate Python inputs at the binding boundary and return useful `PyResult`
  errors. Do not leak Rust panics or unsafe lifetime assumptions.

## Verification

After any change under `xnano-core/`, rebuild the extension before testing:

```bash
cd xnano-core
cargo clean
maturin develop --uv
cd ..
uv run pytest tests/core -q
uv run prek run --all-files
uv run ty check
```

Add focused coverage under `tests/core` for imports, offscreen sessions,
rendering, events, layout, or the changed binding. Run the full suite when the
change crosses the public runtime boundary.
