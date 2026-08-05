---
title: "Markdown Rendering"
icon: "lucide/file-text"
---

# Markdown Rendering

!!! warning "Experimental"

    The document pager (`run_markdown`, `render_markdown`, `MarkdownViewport`)
    is experimental. The API may still change. The `Markdown` **component** used
    as a field value is separate and is not covered by this warning.

[xnano.markdown]{data-preview} loads Markdown from a string, bytes, or file path
and either paints one frame or opens an **interactive pager** — scrollable
viewport, status line, and keyboard / wheel navigation.

This is separate from the [`Markdown`](../api/xnano/components/markdown.md){data-preview}
**component**, which is a field value for embedding markdown inside a grid. The
module here is a document runner and viewport.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: markdown source becomes a scrollable viewport under Terminal">
<svg viewBox="0 0 720 240" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="md-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
    <pattern id="md-cell" width="12" height="12" patternUnits="userSpaceOnUse">
      <path d="M 12 0 L 0 0 0 12" class="gcd-grid-line" />
    </pattern>
  </defs>

  <rect class="gcd-panel" x="36" y="56" width="168" height="128" rx="14" />
  <text class="gcd-label" x="120" y="100" text-anchor="middle">source</text>
  <text class="gcd-chrome-label" x="120" y="128" text-anchor="middle">path · text · bytes</text>

  <line class="gcd-arrow" x1="204" y1="120" x2="268" y2="120" marker-end="url(#md-arrow)" />

  <rect class="gcd-panel gcd-panel-accent" x="280" y="56" width="176" height="128" rx="14" />
  <text class="gcd-label gcd-label-accent" x="368" y="100" text-anchor="middle">run_markdown</text>
  <text class="gcd-chrome-label" x="368" y="128" text-anchor="middle">pager · scroll</text>

  <line class="gcd-arrow" x1="456" y1="120" x2="520" y2="120" marker-end="url(#md-arrow)" />

  <g transform="translate(532, 40)">
    <rect class="gcd-window" x="0" y="0" width="160" height="160" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="160" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="160" height="10" />
    <text class="gcd-chrome-label" x="80" y="15" text-anchor="middle">viewport</text>
    <rect class="gcd-grid-fill" x="12" y="32" width="136" height="96" rx="4" />
    <rect x="12" y="32" width="136" height="96" rx="4" fill="url(#md-cell)" />
    <path class="gcd-line" d="M24 48 h80" stroke-width="3" stroke-linecap="round" />
    <path class="gcd-line-soft" d="M24 64 h104" stroke-width="3" stroke-linecap="round" />
    <path class="gcd-line-soft" d="M24 80 h72" stroke-width="3" stroke-linecap="round" />
    <rect class="gcd-z-base" x="12" y="136" width="136" height="16" rx="3" />
    <text class="gcd-chrome-label" x="80" y="147" text-anchor="middle">status</text>
  </g>
</svg>
</div>

## Interactive pager

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: a tall document scrolled through a shorter viewport">
<svg viewBox="0 0 360 140" xmlns="http://www.w3.org/2000/svg" fill="none">
  <rect class="gcd-z-base" x="48" y="12" width="140" height="116" rx="8" />
  <text class="gcd-chrome-label" x="118" y="36" text-anchor="middle">document</text>
  <rect class="gcd-window" x="200" y="28" width="120" height="72" rx="8" />
  <rect class="gcd-cell-highlight-strong" x="212" y="40" width="96" height="36" rx="4" />
  <text class="gcd-chrome-label" x="260" y="62" text-anchor="middle">viewport</text>
  <rect class="gcd-z-base" x="212" y="82" width="96" height="10" rx="2" />
  <text class="gcd-z-caption" x="260" y="120" text-anchor="middle">scroll offset</text>
</svg>
</div>

[`run_markdown`](../api/xnano/markdown.md){data-preview} opens a live session when
a TTY is available. The document is taller than the screen when needed; you
scroll the window rather than painting everything at once.

```python title="run_markdown"
from xnano.markdown import run_markdown

run_markdown("README.md") # (1)!
# or: run_markdown("# Title\n\nBody text.")
```

1. Path, literal markdown string, or `bytes`. Paths set a base directory for
   relative images.

CLI / entrypoint:

```bash
xnano README.md
# same as: python -m xnano README.md
```

With no path, `xnano` runs the feature demo instead.

### Navigation

| Input | Action |
|-------|--------|
| arrows, `j` / `k` | Line scroll |
| `PageUp` / `PageDown`, `space` | Page scroll |
| `Home` / `g`, `End` / `G` | Start / end of document |
| mouse wheel | Scroll |
| `i` / click / hover | Expand image preview (when images are present) |
| `q` / `esc` | Quit (esc first clears a pinned image expand) |

A status line at the bottom shows scroll position and short hints.

## One frame

[`render_markdown`](../api/xnano/markdown.md){data-preview} paints once and returns
a [`Frame`](../api/xnano/core/frame.md){data-preview}. No event loop.

```python title="render_markdown"
from xnano.markdown import render_markdown

frame = render_markdown("# Hello\n\nA single frame.")
print(frame.text)
```

<interactive />

??? tip "Try editing the code!"

    - Change the heading text.
    - Add a second paragraph to the string.

```pyodide install="xnano>=1.2.3" height="12"
from xnano.markdown import render_markdown

frame = render_markdown("# Hello\n\nA single frame from Markdown.")
print(frame.text)
```

## Loading helpers

```python
from pathlib import Path

from xnano.markdown import is_markdown_path, load_markdown_source

is_markdown_path("notes.md")  # True if the file exists with a .md-like suffix

text, base = load_markdown_source(Path("docs/guide.md"))
# base is the parent directory for relative assets
```

Supported suffixes include `.md`, `.markdown`, `.mdown`, `.mkd`, and `.mkdn`.

## Viewport and images

[`MarkdownViewport`](../api/xnano/markdown.md){data-preview} is the windowed
body used by the pager: block-aware layout (text + images), scroll offset, and
hover/pin expand for local images.

Inline images paint as compact half-block thumbnails (never upscaled past native
cell resolution). Expand with hover, click, or `i` for a larger preview without
decoding full-size images on every frame.

The `Markdown` **component** is still the right choice when markdown is one
slot inside a larger app grid. Use `xnano.markdown` when the document *is* the
session.

## Next

- [Terminal](terminal.md) — host used by the pager
- [Components](components.md) — `Markdown` as a field value
- [Device & Cursor](device.md) — mouse capture for wheel / hover when live

??? abstract "API"

    [`xnano.markdown`](../api/xnano/markdown.md){data-preview} ·
    [`run_markdown`](../api/xnano/markdown.md){data-preview} ·
    [`render_markdown`](../api/xnano/markdown.md){data-preview} ·
    [`Markdown` component](../api/xnano/components/markdown.md){data-preview}

[xnano.markdown]: ../api/xnano/markdown.md
