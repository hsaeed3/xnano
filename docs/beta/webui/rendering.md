---
title: Web rendering
icon: lucide/code-xml
---

# Web rendering

Terminal components lower to terminal render nodes. The web path does the
same with an HTML-oriented node tree under `xnano.beta.nodes.web`, driven by
the web controller and a beta `Text` that implements `get_web_node`.

You rarely construct web nodes by hand — the controller builds them while
painting a grid. Understanding the layers helps when you customize content or
debug missing markup.

---

## Layers

```
Grid field value
    → component.get_web_node(ctx)   # beta Text, or future components
    → AbstractWebNode.to_html()     # span / paragraph / container
    → WebController field slot      # flex, frame, htmx attrs
    → #xnano-app fragment
```

`WebController` owns layout: direction, gap, sizing, borders, titles, click
target ids, and editable input wiring. Content inside a slot comes from the
field value — a plain string is escaped and styled from field settings; a
component that implements `get_web_node` supplies its own node tree.

---

## Web nodes

| Node | HTML role |
|---|---|
| `WebSpanNode` | Styled `<span>` (or bare escaped text) |
| `WebParagraphNode` | Block of text: plain lines or lines of spans |
| `WebContainerNode` | Flex row/column of child web nodes |
| `AbstractWebNode` | Base type; `kind` is `"web"`; implement `to_html()` |

Styling is shared through `build_style_attrs`: colors become inline
`rgb(...)` styles (the same `Color.parse` path as the terminal), modifiers
map to Tailwind utilities (`font-bold`, `italic`, `underline`,
`opacity-60`, `animate-pulse`), and alignment becomes `text-left` /
`text-center` / `text-right`. Invisible nodes render as empty strings.

```python
from xnano.beta.nodes.web import WebParagraphNode, WebSpanNode

line = WebParagraphNode(
    lines=(
        (
            WebSpanNode(content="ok", color="emerald-400", modifiers=("bold",)),
            WebSpanNode(content=" ready", color="slate-400"),
        ),
    ),
    wrap=True,
)
html = line.to_html()
```

---

## Beta `Text`

`xnano.beta.components.text.Text` subclasses the stable terminal `Text` and
adds `get_web_node`. Use it in grids that must paint under both hosts, or
when you only care about web:

```python title="styled.py"
from xnano.beta.components.text import Text
from xnano.fields import Field
from xnano.grid import Grid
from xnano.beta.web import Web

class Banner(Grid):
    title: Text = Field(
        default=Text("Title", color="cyan", modifiers=("bold",))
    )
    body: str = Field(default="Body text")

Web(title="banner").run(Banner())
```

Shape rules match the terminal component:

| `content` | Web result |
|---|---|
| `str` | One `WebParagraphNode` |
| Nested leaf `Text` values in a list | One paragraph line of `WebSpanNode`s |
| Nested lists / non-leaf children | One paragraph line per child |
| `input=True` empty leaf | Placeholder string with dim/gray styling when empty |

Editable fields (`Text(input=True)`) become real `<input>` elements. The
controller assigns an input target id; the browser posts changes to
`/xnano/input/{id}`, and the session writes the value back onto the `Text`
instance before re-pumping hooks.

Import the beta class when you need web nodes:

```python
from xnano.beta.components.text import Text  # get_web_node implemented
# from xnano.components import Text         # terminal path only
```

A plain terminal `Text` without `get_web_node` does not contribute structured
web markup; prefer the beta subclass for dual-host content.

---

## Frames and chrome

Field and grid frames (borders, titles, padding) are applied by the web
controller as HTML wrappers around slot content — not by the text nodes
themselves. Clickable fields receive htmx attributes that POST to
`/xnano/click/{target_id}` and swap `#xnano-app`.

---

## Programmatic render

```python
from xnano.beta.web import Web

web = Web(title="probe")
fragment = web.render_html(Banner())
page = web.build_page(fragment)
```

`render_html` returns body content only. `build_page` adds the doctype,
CDN scripts, title, and optional keyboard/poll extras based on the session's
registered hooks.

See [Web UI](index.md) for hosting and [Request hooks](requests.md) for custom
routes.
