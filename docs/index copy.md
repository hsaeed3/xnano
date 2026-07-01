---
icon: lucide/smile
title: " "
---

<span class="page-index"></span>

![ZYX Hero](./assets/xnano-light.png){ align=center .hero-light }
![ZYX Hero](./assets/xnano-dark.png){ align=center .hero-dark }

( e(x)tremely nano rust-based TUI framework built on ``ratatui`` and ``tachyonfx`` )
{ .hero-tagline }

<p align="center">
  <a href="https://pypi.org/project/xnano" target="_blank"><img src="https://img.shields.io/pypi/v/xnano.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/xnano" target="_blank"><img src="https://img.shields.io/pypi/pyversions/xnano.svg?cacheSeconds=3600" alt="Python version"></a>
  <a href="https://github.com/hsaeed3/xnano/blob/main/LICENSE" target="_blank"><img src="https://img.shields.io/github/license/hsaeed3/xnano.svg" alt="License"></a>
</p>

---

`xnano` gives you a FastAPI/Typer-style developer experience for terminal apps: simple constructors, strong type hints, clean event loops, and expressive composable APIs.

## Install and run

<div class="termy">

```console
$ pip install xnano
---> 100%
Successfully installed xnano xnano-core

$ python examples/dashboard.py
```

</div>

`xnano` ships as a high-level Python API on top of `xnano-core`, a Rust bridge over `ratatui` (rendering/layout/widgets) and `tachyonfx` (effects/transitions).

---

## Why xnano

<div class="z-grid">
  <div class="z-card">
    <h3>Declarative and typed</h3>
    <p>Build UIs with constructor-based components like <code>Layout(...)</code>, <code>Block(...)</code>, and <code>Paragraph(...)</code> with precise type hints throughout.</p>
  </div>
  <div class="z-card">
    <h3>Rust performance</h3>
    <p>Immediate-mode rendering and efficient diffing from <code>ratatui</code>, surfaced through a Python API that feels native and ergonomic.</p>
  </div>
  <div class="z-card">
    <h3>Animation-ready</h3>
    <p>Compose effects with <code>tachyonfx</code> primitives like <code>coalesce</code>, <code>dissolve</code>, <code>slide_in</code>, and <code>ping_pong</code>.</p>
  </div>
</div>

---

## The core mental model

1. **Open a terminal context** with `Terminal()`.
2. **Poll events** (`poll_event`) and update state.
3. **Draw every frame** with `term.draw(...)`.
4. **Render widgets into layout areas** from `Layout(...).split(frame.area())`.
5. **Optionally process effects** with `frame.process_effects(...)`.

This is the same immediate-mode architecture used by modern TUIs in Rust: explicit state, explicit rendering, predictable behavior.

---

## Quickstart

```python
from xnano import (
    Block,
    Constraint,
    EventHandler,
    Layout,
    Paragraph,
    Style,
    Terminal,
    poll_event,
)

handler = EventHandler()

@handler.on_key("ctrl+c", "q")
def quit_app(event) -> None:
    raise SystemExit

with Terminal() as term:
    while True:
        event = poll_event(16)
        if event:
            handler.dispatch(event)

        def draw(frame):
            layout = Layout(
                direction="vertical",
                constraints=[Constraint.length(3), Constraint.fill(1)],
            )
            header, body = layout.split(frame.area())
            frame.render_widget(
                Paragraph(
                    " xnano ",
                    style=Style(foreground="white", modifiers="bold"),
                    block=Block(borders="all", border_type="rounded"),
                ),
                header,
            )
            frame.render_widget(
                Paragraph(
                    "Press q to exit.",
                    block=Block(title="Status", borders="all"),
                ),
                body,
            )

        term.draw(draw)
```

---

## Built on ratatui + tachyonfx

### `ratatui` context

- Immediate-mode terminal rendering (draw full frame, diff, flush).
- Constraint-based layout splitting (`length`, `percentage`, `fill`, ratios).
- Rich widget primitives: paragraphs, lists, tables, gauges, charts, tabs, scrollbars.

### `tachyonfx` context

- Shader-like terminal effects over cell buffers.
- Color, dissolve/coalesce, sweep/slide, interpolation and timing composition.
- Effect orchestration via `EffectManager` and composition helpers (`sequence`, `parallel`, `repeat`).

`xnano` keeps these capabilities but exposes them with Python-first names, literals, and conversion helpers so you can stay in idiomatic Python.

---

## API tour

| Module | Primary objects |
| --- | --- |
| `xnano.terminal` | `Terminal`, `Frame`, `Event`, `EventHandler`, `poll_event` |
| `xnano.layout` | `Layout`, `Constraint`, `Rectangle`, `Margin`, `Position` |
| `xnano.widgets` | `Block`, `Paragraph`, `ListView`, `ListState`, `Gauge`, `Tabs`, `Clear` |
| `xnano.table` | `Table`, `Row`, `Cell`, `TableState` |
| `xnano.chart` | `Sparkline`, `LineGauge`, `BarChart`, `BarGroup`, `Bar` |
| `xnano.style` / `xnano.text` | `Style`, `Modifier`, `Borders`, `Padding`, `Span`, `Line`, `Text` |
| `xnano.effect` | `Effect`, `EffectManager`, `fade_*`, `dissolve`, `coalesce`, `slide_*`, `sweep_*` |
| `xnano.tailwind` | `tailwind(name, shade)` color helper |
| `xnano.buffer` | Off-screen rendering and inspection utilities |

---

## Example apps in this repository

- [`examples/dashboard.py`](https://github.com/hsaeed3/xnano/blob/main/examples/dashboard.py): live metrics dashboard with sparklines, gauges, and table selection.
- [`examples/effects_demo.py`](https://github.com/hsaeed3/xnano/blob/main/examples/effects_demo.py): interactive effect triggers using `EffectManager`.
- [`examples/tabs_nav.py`](https://github.com/hsaeed3/xnano/blob/main/examples/tabs_nav.py): tabbed navigation with selectable list views.
- [`examples/agent_chat.py`](https://github.com/hsaeed3/xnano/blob/main/examples/agent_chat.py): multi-panel command/chat style UI with dynamic updates.

---

## Live example demos

Autoplay terminal recordings of each example. Regenerate with `python scripts/generate_demo_gifs.py` (requires the `vhs` CLI).

<div class="z-grid">
  <div class="z-card">
    <h3><code>dashboard.py</code></h3>
    <img src="assets/demos/dashboard.gif" alt="xnano dashboard example demo" style="width:100%; border-radius: 8px;" loading="lazy">
  </div>
  <div class="z-card">
    <h3><code>effects_demo.py</code></h3>
    <img src="assets/demos/effects_demo.gif" alt="xnano effects demo example" style="width:100%; border-radius: 8px;" loading="lazy">
  </div>
  <div class="z-card">
    <h3><code>tabs_nav.py</code></h3>
    <img src="assets/demos/tabs_nav.gif" alt="xnano tabs navigation example demo" style="width:100%; border-radius: 8px;" loading="lazy">
  </div>
  <div class="z-card">
    <h3><code>agent_chat.py</code></h3>
    <img src="assets/demos/agent_chat.gif" alt="xnano agent chat example demo" style="width:100%; border-radius: 8px;" loading="lazy">
  </div>
</div>
