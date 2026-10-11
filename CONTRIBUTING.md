# Contributing to xnano

Thank you for contributing to xnano. Contributions of all sizes are welcome,
including bug fixes, documentation improvements, tests, examples, performance
work, and new ideas.

This guide describes the workflow used to keep changes focused, reviewable,
and easy to understand later.

## Before starting

Small fixes, documentation improvements, and test additions can be submitted
directly.

Please open an issue or discussion before beginning work on:

- a new public API or component;
- a change to established behavior;
- a new dependency;
- a significant architectural change;
- a change spanning multiple xnano surfaces; or
- work whose desired behavior is not yet clear.

Early discussion helps confirm the direction before substantial implementation
work begins.

## Development setup

Clone the repository and install its development dependencies. This requires
[`uv`](https://docs.astral.sh/uv/getting-started/installation/) and
[Rust](https://rust-lang.org/tools/install/):

```bash
make install
```

The repository is one Cargo workspace (`crates/`) and one uv workspace
(`packages/`). Run `make help` to list every available command. The most common
ones are summarized in [Validation](#validation).

Create a focused branch from the latest `main`:

```bash
git switch main
git pull --ff-only
git switch -c <type>/<short-description>
```

Examples:

```text
feat/table-row-selection
fix/context-state-typing
docs/action-hooks
refactor/core-input-handling
```

Branch names should be short, lowercase, and use hyphens between words.
Commits directly to `main` are not allowed.

## Making changes

Keep each pull request focused on one coherent outcome. Avoid combining
unrelated refactors, formatting changes, documentation rewrites, and behavioral
changes in the same pull request.

When changing behavior:

- add or update tests;
- update relevant documentation and examples;
- preserve the separation between the Python-independent engine crates, the
  thin PyO3 binding crates, and the Python packages;
- avoid unrelated cleanup unless it is necessary for the change.

Follow the architecture and code style documented in `AGENTS.md`.

## Commit and pull request titles

xnano uses the following format for pull request titles and final squash
commit messages:

```text
<type>(<scope>): <summary>
```

The scope is optional:

```text
<type>: <summary>
```

### Types

Use one of the following types:

| Type | Use |
| --- | --- |
| `feat` | Add user-visible functionality |
| `fix` | Correct incorrect behavior |
| `docs` | Change documentation or examples only |
| `refactor` | Restructure code without changing behavior |
| `perf` | Improve performance |
| `test` | Add or improve tests only |
| `build` | Change packaging, dependencies, or build tooling |
| `ci` | Change continuous integration or release automation |
| `chore` | Perform repository maintenance not covered above |
| `release` | Prepare a versioned release |

### Scopes

Scopes identify the area affected by the change. Prefer stable subsystem names
such as:

```text
grid
fields
hooks
actions
components
tui
webui
cli
core
xnano-core
xnano-audio
xnano-image
docs
release
```

Use the type to describe the kind of change and the scope to describe where it
happened.

Good:

```text
fix(context): preserve the declared state type
feat(tui): add optional terminal image rendering
docs(hooks): explain action matching
refactor(core): centralize input dispatch
ci: build WebAssembly wheels for Pyodide
release: prepare xnano 1.1.0
```

Avoid:

```text
docs(fix): correct the hooks page
chore(docs): document the new component
Fixed context state type.
feat/new-component
```

Write summaries in the imperative mood, begin them with a lowercase letter,
and do not end them with punctuation. Describe the outcome, not the files that
were edited.

If a change is incompatible with previous behavior, add `!` and explain the
migration in the pull request:

```text
feat(grid)!: remove the deprecated Grid alias
```

Intermediate commits on a working branch do not need to follow this format
perfectly. Pull requests are normally squash merged, so the pull request title
must be suitable as the final commit message.

## Pull requests

A good pull request allows someone unfamiliar with the implementation to
understand why the change exists and how it was verified.

Use this structure:

```markdown
## Summary

- Describe the behavior or outcome that changed.
- Explain why the change is needed.

## Validation

- `make check`
- `make test`

## Notes

Include migration details, screenshots, terminal recordings, design decisions,
or follow-up work when relevant.
```

Keep descriptions concise, but include enough context to review the change
without reconstructing its purpose from the diff.

Draft pull requests are welcome for work in progress or early design feedback.

Before requesting review:

- review the complete diff yourself;
- remove debugging code and unrelated changes;
- confirm the PR title follows the commit convention;
- update tests, documentation, and examples where applicable;
- report exactly which validation commands were run;
- call out known limitations or follow-up work.

## Validation

Format the repository, then run the full set of checks from the root
directory:

```bash
make format-all
make check
make test
```

`make check` runs linting (`ruff`, `griffe`, `cargo fmt`, `cargo clippy`),
spellchecking, type checking (`basedpyright`), and coverage report generation.
`make test` runs the Rust and Python test suites themselves.

Changes to Rust code under `crates/*/src/` additionally require rebuilding the
native extensions before testing:

```bash
make rebuild-rust
```

Pure Python changes do not need a Rust rebuild. If tests fail to load an
extension module (`.so`), run `make test-sync` instead of `make test`.

Documentation changes should also build successfully. The API reference is
generated from the package sources, so regenerate it after adding, renaming or
removing a module:

```bash
uv run python scripts/docs/autogenerate_api_references.py
make docs-build
```

Each package under `packages/` has its own `Makefile` with the same commands
scoped to that package, plus `make all` (format, build, lint, and test) for a
faster check while working on a single package. It does not replace `make check`
at the root level.

Run focused tests while developing, then run the complete required checks
before opening or updating the pull request.

If a check cannot be run locally, say so clearly in the pull request and
explain why.

## Review and merging

Pull requests are normally squash merged. The pull request title becomes the
commit subject on `main`, so it should describe the complete result of the
change.

A pull request is ready to merge when:

- its purpose and scope are clear;
- required tests and checks pass;
- documentation reflects user-visible changes;
- review comments are resolved; and
- the final title and description accurately represent the merged change.

Release preparation should remain separate from ordinary feature and fix pull
requests unless the release is the explicit purpose of the change.

## Reporting bugs

A useful bug report includes:

- the xnano and Python versions;
- the operating system and terminal, browser, or CLI environment;
- a minimal reproducible example;
- the expected behavior;
- the actual behavior and full traceback, if any.

Please remove secrets and unrelated application code from reproductions.

## Proposing features

Describe the problem before proposing an implementation. Include the intended
user experience, alternatives considered, and which xnano surfaces would be
affected.

A feature request does not need a complete technical design, but it should make
the desired outcome clear.

## Community expectations

Be considerate, specific, and constructive. Review the work you submit and
respect the time required to understand and maintain it.

## AI-assisted contributions

Tool-assisted contributions are welcome, including work created with AI, but
disclosure is **mandatory** and the contributor remains responsible for
understanding, testing, and explaining the complete change.

- A pull request containing AI-generated or AI-assisted code, documentation,
  or description text must say so in its description, naming the tool and the
  exact model used, for example `Generated with Claude Code (claude-sonnet-5-5)`.
- Commits written by an AI agent end with a `Co-Authored-By:` trailer naming
  the model, for example
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- The submitter must have read and run everything the AI produced before
  requesting review.
