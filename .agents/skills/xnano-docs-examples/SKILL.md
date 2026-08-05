---
name: xnano-docs-examples
description: Update xnano documentation, examples, API pages, and generated demos. Use when docs or examples change, or when library files are added, renamed, or removed.
---

# xnano docs and examples

Use this skill for documentation and runnable examples. Treat docs and examples
as part of the public API: they must use the current stable `xnano` namespace
and concrete import paths.

## Workflow

- Read the implementation and its tests before documenting behavior. Do not
  invent options, aliases, component names, or host arguments.
- Keep examples minimal, runnable, and representative. Prefer `BaseGrid`,
  `Field`, `Component`, `Terminal.offscreen`, and `Web` patterns already used
  in the repository.
- Update nearby conceptual docs and API references when a public symbol,
  behavior, or import path changes. Remove stale `Grid`, `xnano.beta`, and
  obsolete color/API examples.
- For native changes, document the public Python-facing behavior rather than
  exposing internal Rust implementation details.

## Generated documentation and demos

If any new, renamed, or removed file is added under `xnano/` or `xnano-core/`,
inspect and run the repository's documentation update scripts before handoff.
Use any branch-specific `update_docs` script when present. In this repository,
the relevant generators include:

```bash
uv run python scripts/generate_api_docs.py
uv run python scripts/generate_component_demos.py
uv run python scripts/generate_hook_demos.py
uv run python scripts/generate_tutorial_demos.py
uv run python scripts/generate_showcase_demos.py
uv run python scripts/generate_readme_demos.py
```

Run only the generators affected by the change; use `--check` where supported.
Do not hand-edit generated output when the source generator is the source of
truth. Check generated assets and links into the same diff.

## Verification

- Run the focused documentation/example tests, especially Pyodide documentation
  and rendering tests when examples are embedded or browser-compatible.
- Confirm every code block imports from the current public API and uses valid
  `ColorLike`, `grid_settings`, hook, host, and component conventions.
- Run the repository's required checks after implementation when the change is
  code-affecting: `uv run pytest`, `uv run prek run --all-files`, and
  `uv run ty check`.
