---
title: Web UI & CLI
icon: lucide/layout
---

# Web UI & CLI

The former `xnano.beta` surface graduated into public packages:

| Area | Module | Guide |
|---|---|---|
| [Web UI](../webui/index.md) | `xnano.webui` | Browser host for grids |
| [Request hooks](../webui/requests.md) | `xnano.webui.requests` | `@on_get_request` / `@on_post_request` |
| [Web rendering](../webui/rendering.md) | `xnano.webui.nodes` | HTML nodes and dual-host `Text` |
| [CLI](../cli/index.md) | `xnano.cli` | Model-like command interface |

```python
from xnano.webui import Web
from xnano.webui.requests import on_get_request, on_post_request
from xnano.cli import Command
```
