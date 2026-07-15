---
title: "Overview"
icon: "lucide/graduation-cap"
---

# Overview

Working examples of common xnano patterns — streaming text, forms, lists, tabs, shared state, dual hosts, and more. Most pages are small and self-contained; a few put several ideas together.

These assume you've already read [Core Concepts]{data-preview} — especially [grids]{data-preview}, [fields]{data-preview}, [events & hooks]{data-preview}, and [context]{data-preview}.

## Interaction

| Tutorial | What it shows |
|---|---|
| [Streaming Content](streaming-content.md) | Live field streaming and `render(..., stream=...)` |
| [Text Inputs](text-inputs.md) | Editable `Text(input=True)` fields, focus, and submit |
| [Selection Lists](selection-list.md) | Keyboard-navigable lists with a live selection highlight |
| [Tabs](tabs.md) | Multi-screen layouts switched from one keybinding |
| [Confirm Dialogs](confirm-dialog.md) | A nullable overlay field as a modal confirm step |

## Layout & Display

| Tutorial | What it shows |
|---|---|
| [Nested Panels](nested-panels.md) | Grids inside grids — sidebars, headers, content regions |
| [Composed Text](composed-text.md) | Multi-span status lines and mixed styling with `Text` |
| [grid_render](grid-render.md) | Recomputing display every frame with `grid_render()` |
| [Scrollable Logs](scrollable-log.md) | A windowed, scrollable log feed from a longer buffer |

## Live Data

| Tutorial | What it shows |
|---|---|
| [Live Progress](live-progress.md) | Animating a `Progress` bar from `@on_tick` |
| [Live Sparklines](live-sparklines.md) | Rolling metric history with `Sparkline` |
| [Table Browser](table-browser.md) | Selecting rows in a declarative `Table` |

## State, Actions & Hosts

| Tutorial | What it shows |
|---|---|
| [Shared State](shared-state.md) | App-wide state on `Terminal(state=...)` typed through `Context` |
| [Action Bindings](action-bindings.md) | Reusable `Action` constants bound with `@on_action` |
| [Title & Clipboard](title-and-clipboard.md) | Window titles and clipboard from `ctx.device` |
| [Dual Host](dual-host.md) | The same grid on `Terminal` and `Web` |
| [CLI Commands](cli-commands.md) | Options and subcommands with `xnano.cli.Command` |

## Reuse

| Tutorial | What it shows |
|---|---|
| [Custom Components](custom-component.md) | A small reusable widget via `AbstractComponent` |

## Running the Examples

One-shot `render()` examples may be interactive in the browser. Anything that needs a live event loop (`.run()`, key presses, ticks) is plain Python you run locally:

```bash
uv run python your_snippet.py
```

<br/>

Larger demos that combine several of these live under `examples/` — `agent_chat.py`, `dashboard.py`, `tabs_nav.py`, and the rest.

[Core Concepts]: ../core-concepts/grids.md
[grids]: ../core-concepts/grids.md
[fields]: ../core-concepts/fields.md
[events & hooks]: ../core-concepts/events.md
[context]: ../core-concepts/context.md
