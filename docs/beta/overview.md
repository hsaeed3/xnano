---
title: Beta
icon: lucide/flask-conical
---

# Beta

`xnano.beta` is the prototype surface for APIs that reuse the same grids and
components as the terminal, then target other hosts — a browser, or a
command-line entry point. Nothing under `xnano.beta` is frozen yet. Import
concrete modules directly; the package root only re-exports the main names.

```python
from xnano.beta.web import Web
from xnano.beta.requests import on_get_request, on_post_request
from xnano.beta.commands import Command
```

## What is here

| Area | Module | Role |
|---|---|---|
| [Web UI](webui/index.md) | `xnano.beta.web` | Browser host for grids — sessions, HTML shell, htmx routes |
| [Request hooks](webui/requests.md) | `xnano.beta.requests` | `@on_get_request` / `@on_post_request` on grid methods |
| [Web rendering](webui/rendering.md) | `xnano.beta.nodes.web`, `xnano.beta.components.text` | HTML nodes and web-capable `Text` |
| [Commands](commands/index.md) | `xnano.beta.commands` | Model-like CLI for options, flags, and subcommands |

The terminal guides under [Concepts](../concepts/getting-started.md) still
describe the stable public path. Beta code sits beside that model: the same
`Grid`, `Field`, and `@on_*` hooks, with extra entry points for web and CLI.

## Install extras

The web host needs Starlette and uvicorn:

```bash
pip install "xnano[web]"
```

Commands only need the base package.

## Stability

Treat beta docs as previews. Names, routes, and HTML details can change before
they graduate into the main `xnano` namespace. Prefer the patterns shown in the
pages linked above over copying private helpers from the source tree.
