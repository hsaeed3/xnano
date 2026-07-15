---
title: "@on_clipboard"
icon: "lucide/clipboard-paste"
---

# Pasting Clipboard Content

`@on_clipboard` listens for pasted text. The payload lives on `ctx.clipboard`, leaving the hook free to validate it, store it, or turn it into field content.

```python title="Receiving a Paste" hl_lines="4"
from xnano.events import on_clipboard

class PastePreview(BaseGrid):
    @on_clipboard
    def preview_paste(self, ctx: Context) -> None:
        self.preview = ctx.clipboard.text
```

## Clipboard Action

`Action.clipboard(text=None)` optionally matches a particular payload. To emit a paste from inside a hook, `ctx.actions.paste("hello")` is the compact form.

```python title="A Synthetic Paste"
PASTE_SAMPLE = Action.clipboard("hello")

@on_action(PASTE_SAMPLE)
def receive_sample(self) -> None:
    self.preview = "hello"
```

Because the action supplies the text itself, this reaction can be rendered by an offscreen browser example without reaching for the system clipboard.

??? abstract "API"

    [`on_clipboard`](../api/xnano/events.md#xnano.events.on_clipboard){data-preview} · [`ClipboardAction`](../api/xnano/core/actions.md#xnano.core.actions.ClipboardAction){data-preview}
