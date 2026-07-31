---
title: "Device & Cursor"
icon: "lucide/mouse-pointer"
---

# Device & Cursor

[Device]{data-preview} and [Cursor]{data-preview} sit on the **host**, not on
any grid. They control the window/tab chrome and the terminal caret.

You do not construct them. Get them from:

- `ctx.device` / `ctx.cursor` inside a hook ([Context](context.md))
- `terminal.device` / `terminal.cursor` (or the underlying `runtime`) when you
  hold a [Terminal](terminal.md)

<div class="grid-concept-diagram" role="img" aria-label="Diagram: device title and cursor sit on the host chrome outside the app grid">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="dcd-cell" width="14" height="14" patternUnits="userSpaceOnUse">
      <path d="M 14 0 L 0 0 0 14" class="gcd-grid-line" />
    </pattern>
  </defs>

  <rect class="gcd-window" x="80" y="28" width="560" height="200" rx="14" />
  <rect class="gcd-chrome" x="80" y="28" width="560" height="36" rx="14" />
  <rect class="gcd-chrome" x="80" y="48" width="560" height="16" />
  <circle class="gcd-dot" cx="104" cy="46" r="4" />
  <circle class="gcd-dot" cx="122" cy="46" r="4" />
  <circle class="gcd-dot" cx="140" cy="46" r="4" />
  <text class="gcd-chrome-label" x="360" y="50" text-anchor="middle">device.title · size · modes · clipboard</text>

  <rect class="gcd-grid-fill" x="104" y="80" width="512" height="124" rx="6" />
  <rect x="104" y="80" width="512" height="124" rx="6" fill="url(#dcd-cell)" />
  <rect class="gcd-cell-highlight" x="128" y="100" width="200" height="72" rx="4" />
  <text class="gcd-z-label gcd-z-label-on" x="228" y="140" text-anchor="middle">your grid</text>

  <rect class="gcd-z-overlay" x="420" y="132" width="3" height="28" rx="1" />
  <text class="gcd-z-caption gcd-z-caption-on" x="460" y="150">cursor</text>

  <text class="gcd-z-caption" x="360" y="248" text-anchor="middle">host chrome — not a field, not a grid slot</text>
</svg>
</div>

Title, mode flags, caret position, visibility, and style are always tracked
**locally** on the device/cursor objects (so offscreen tests and web sessions
still report consistent values). Only a **live** terminal session issues the
real escape sequences. Offscreen and web runtimes keep the Python state; live
side effects that need a real TTY are skipped.

## Device

[`Device`](../api/xnano/device.md){data-preview} covers title, viewport size,
clear/scroll, clipboard, and terminal mode flags.

### Title and size

```python title="Title" hl_lines="5"
from xnano import Context, on_state

@on_state("unread > 0")
def flash_title(self, ctx: Context) -> None:
    ctx.device.title = f"({ctx.state.unread}) inbox" # (1)!
```

1. Live terminal: window title. Web host: document title when the server
   applies it. Offscreen: stored on the device only.

```python title="Viewport size"
size = ctx.device.size  # Size(width=…, height=…) in cells
width, height = size.width, size.height
```

`size` mirrors the runtime viewport. It is read-only from the device side.

### Clear and scroll

```python title="Clear and scroll"
ctx.device.clear()                 # kind="all" by default
ctx.device.clear("purge")         # screen + scrollback
ctx.device.clear("current_line")
ctx.device.scroll_up(3)
ctx.device.scroll_down(1)
```

`clear` accepts:

| Kind | Region |
|------|--------|
| `"all"` | Entire visible screen |
| `"purge"` | Screen and scrollback |
| `"from_cursor_down"` | Caret to bottom |
| `"from_cursor_up"` | Top to caret |
| `"current_line"` | Current line only |
| `"until_new_line"` | Caret to end of line |

These only emit terminal commands when the runtime is live.

### Clipboard

```python title="Clipboard"
ctx.device.copy_to_clipboard(self.selected_text)
```

`copy_to_clipboard(text)` is the device method for putting text on the system
clipboard when the host supports it.

### Mode flags

Boolean properties toggle terminal features. State is always kept in Python;
live sessions apply the corresponding native enable/disable calls.

| Property | Default | Role |
|----------|---------|------|
| `raw_mode` | `False` | Raw input (no line buffering / echo) |
| `alternate_screen` | `False` | Alternate screen buffer (typical full-screen TUI) |
| `line_wrap` | `True` | Automatic line wrap |
| `mouse_capture` | `False` | Capture mouse for the session |
| `bracketed_paste` | `False` | Bracketed paste sequences |
| `focus_change` | `False` | OS-level terminal focus gained/lost events |
| `synchronized_updates` | `False` | Batch output updates |

```python title="Mouse capture on the device"
# Prefer Terminal(mouse_events=True) for app-level mouse hooks.
# Device flag is the lower-level session switch:
ctx.device.mouse_capture = True
```

For click/hover hooks on grids, pass `mouse_events=True` to
[`Terminal`](terminal.md) when you construct it — that wires mouse into the
event loop. Setting `device.mouse_capture` alone is useful when you already
hold a live session (for example the [markdown](markdown.md) pager enables it
for wheel and hover).

```python title="Reading flags"
if ctx.device.alternate_screen:
    ...
ctx.device.raw_mode = True   # live only; needs a real TTY
```

## Cursor

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: caret position on a cell grid">
<svg viewBox="0 0 360 100" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="cu-cell" width="14" height="14" patternUnits="userSpaceOnUse">
      <path d="M 14 0 L 0 0 0 14" class="gcd-grid-line" />
    </pattern>
  </defs>
  <rect class="gcd-window" x="40" y="16" width="280" height="68" rx="10" />
  <rect class="gcd-grid-fill" x="52" y="28" width="256" height="44" rx="4" />
  <rect x="52" y="28" width="256" height="44" rx="4" fill="url(#cu-cell)" />
  <rect class="gcd-z-overlay" x="148" y="36" width="3" height="28" rx="1" />
  <text class="gcd-z-caption gcd-z-caption-on" x="168" y="54">move(x, y)</text>
</svg>
</div>

[`Cursor`](../api/xnano/cursor.md){data-preview} is the host caret: show/hide,
style, position, save/restore, blinking.

Most apps leave the caret alone and let focused `Input` fields own editing.
Use cursor controls when you draw selection yourself, drive a custom caret, or
hide the system caret over a full-screen paint.

### Visibility and style

```python title="Visibility" hl_lines="4"
from xnano import Context, on_focus

@on_focus("search", kind="gained")
def hide_system_caret(self, ctx: Context) -> None:
    ctx.cursor.visible = False
```

```python title="Style"
ctx.cursor.style = "blinking_bar"
ctx.cursor.enable_blinking()
ctx.cursor.disable_blinking()  # maps blinking_* styles to steady_*
```

| Style | Appearance |
|-------|------------|
| `"default"` | Terminal default |
| `"blinking_block"` / `"steady_block"` | Block |
| `"blinking_underline"` / `"steady_underline"` | Underline |
| `"blinking_bar"` / `"steady_bar"` | Vertical bar |

### Position

Position is tracked in cells as `(x, y)`. Live terminals move the real caret;
offscreen/web keep the local coordinates for tests and frame inspection.

```python title="Position"
ctx.cursor.move(4, 2)
ctx.cursor.position = (0, 0)
x, y = ctx.cursor.position
# same as: ctx.cursor.get_position()

ctx.cursor.move_up()
ctx.cursor.move_down(2)
ctx.cursor.move_left()
ctx.cursor.move_right(3)

ctx.cursor.save()
ctx.cursor.move(10, 5)
ctx.cursor.restore()
```

## Live vs offscreen vs web

| Concern | Live terminal | Offscreen / tests | Web host |
|---------|---------------|-------------------|----------|
| `title`, flags, `size` | Applied + tracked | Tracked locally | Tracked; title may map to the page |
| `clear` / `scroll_*` | Escape sequences | No-op on the wire | No-op on the wire |
| `cursor` position | Real caret moves | Local coords only | Local coords only |
| `cursor` visibility / style | Applied when live | Tracked locally | Tracked; no browser caret |

Offscreen is intentional: a headless or web server must not dump terminal
control sequences onto the process that owns stdout.

```python title="From a Terminal you own"
from xnano import Terminal

terminal = Terminal(title="My App")
# after the session is live / after render attaches a runtime:
terminal.device.title = "My App"
terminal.cursor.visible = True
```

## Next

- [Context](context.md) — `ctx.device` / `ctx.cursor` on every hook
- [Terminal](terminal.md) — `mouse_events`, live session
- [Markdown](markdown.md) — uses mouse capture for wheel / image hover
- [Effects](effects.md) — field paint transitions (not the system caret)

??? abstract "API"

    [`Device`](../api/xnano/device.md){data-preview} ·
    [`Cursor`](../api/xnano/cursor.md){data-preview} ·
    [`ClearType`](../api/xnano/device.md){data-preview} ·
    [`CursorStyle`](../api/xnano/cursor.md){data-preview} ·
    [`Context`](../api/xnano/context.md){data-preview}

[Device]: ../api/xnano/device.md
[Cursor]: ../api/xnano/cursor.md
[Context]: context.md
