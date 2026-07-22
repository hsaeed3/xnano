---
title: "Device & Cursor"
icon: "lucide/mouse-pointer"
---

# Device & Cursor

Every host — terminal or browser — exposes two small controls that sit outside the grid entirely: a `device`, for things like the window title, clearing the screen, and the clipboard, and a `cursor`, for the caret itself.

Neither belongs to any grid you build. They belong to the host underneath it, the same way `document.title` belongs to the page, not to any one component on it.

Both are available on [Context]{data-preview}, alongside the event and the terminal — reached the same way from any hook, on any host.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: device title and cursor sit on the host chrome outside the app grid">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <pattern id="dcd-cell" width="14" height="14" patternUnits="userSpaceOnUse">
      <path d="M 14 0 L 0 0 0 14" class="gcd-grid-line" />
    </pattern>
  </defs>

  <!-- Outer host window -->
  <rect class="gcd-window" x="80" y="28" width="560" height="200" rx="14" />
  <!-- Title bar = device -->
  <rect class="gcd-chrome" x="80" y="28" width="560" height="36" rx="14" />
  <rect class="gcd-chrome" x="80" y="48" width="560" height="16" />
  <circle class="gcd-dot" cx="104" cy="46" r="4" />
  <circle class="gcd-dot" cx="122" cy="46" r="4" />
  <circle class="gcd-dot" cx="140" cy="46" r="4" />
  <text class="gcd-chrome-label" x="360" y="50" text-anchor="middle">device.title · clipboard · window</text>

  <!-- Grid body -->
  <rect class="gcd-grid-fill" x="104" y="80" width="512" height="124" rx="6" />
  <rect x="104" y="80" width="512" height="124" rx="6" fill="url(#dcd-cell)" />
  <rect class="gcd-cell-highlight" x="128" y="100" width="200" height="72" rx="4" />
  <text class="gcd-z-label gcd-z-label-on" x="228" y="140" text-anchor="middle">your grid</text>

  <!-- Cursor caret outside grid ownership -->
  <rect class="gcd-z-overlay" x="420" y="132" width="3" height="28" rx="1" />
  <text class="gcd-z-caption gcd-z-caption-on" x="460" y="150">cursor</text>

  <text class="gcd-z-caption" x="360" y="248" text-anchor="middle">host chrome — not a field, not a grid slot</text>
</svg>
</div>

## The Device

A device is the one thing every grid on a host shares — its window or tab.

```python title="Setting the Window Title" hl_lines="3"
@on_state("unread > 0")
def flash_title(self, ctx: Context) -> None:
    unread = ctx.get_state().unread
    ctx.device.title = f"({unread}) inbox" # (1)!
```

1. `ctx.device.title` sets the terminal window's or browser tab's title — whichever host the app happens to be running on.

<br/>

The clipboard works the same way, from either host:

```python title="Copying to the Clipboard" hl_lines="2"
@on_keyboard("ctrl+c")
def copy_selection(self, ctx: Context) -> None:
    ctx.device.copy_to_clipboard(self.selected_text)
```

## The Cursor

The cursor isn't part of your grid at all — it's the host's own caret, borrowed for as long as your app is running.

```python title="Hiding the Cursor" hl_lines="2"
@on_focus("search", kind="gained")
def hide_caret_while_searching(self, ctx: Context) -> None:
    ctx.cursor.visible = False # (1)!
```

1. Most apps never touch `cursor.visible` — it defaults to on. Turn it off for anything that draws its own selection or highlight instead of relying on the caret.

## Terminal vs. Browser

Not every control means the same thing on both hosts. `Device` and `Cursor` share one contract, but a browser has no raw terminal underneath to back some of it.

On the terminal, the cursor is a real, movable caret.

```python title="Moving the Cursor" hl_lines="3"
@on_tick(500)
def blink_marker(self, ctx: Context) -> None:
    ctx.cursor.move_to(4, 2) # (1)!
    ctx.cursor.style = "blinking_bar"
```

1. `move_to` — and the rest of the position/movement methods — never errors on a web host, since it's part of the shared contract. It's just a no-op there: a browser has no single caret position to move.

<br/>

The same goes for `device`. Raw mode, the alternate screen buffer, mouse capture, and a handful of other terminal-mode flags only exist on [TerminalDevice]{data-preview} — [WebDevice]{data-preview} has no raw mode to toggle and no alternate screen to swap to.

| | Terminal | Browser |
|---|---|---|
| `device` | full control — title, size, clipboard, screen, terminal modes | title, size, clipboard — screen/mode controls are no-ops |
| `cursor` | a real, movable caret — position, visibility, style | visibility and style only — position is a no-op |

??? abstract "Full Device and Cursor Reference"

    - `device.title`, `device.size`, `device.clear()`, `device.scroll_up()` / `scroll_down()`, `device.copy_to_clipboard()` — the shared [Device]{data-preview} contract, on both hosts.
    - `device.raw_mode`, `device.alternate_screen`, `device.line_wrap`, `device.mouse_capture`, `device.bracketed_paste`, `device.focus_change`, `device.synchronized_updates` — [TerminalDevice]{data-preview} only.
    - `cursor.visible`, `cursor.style` — the shared [Cursor]{data-preview} contract, on both hosts.
    - `cursor.move_to()` and the rest of the position/movement methods, `enable_blinking()` / `disable_blinking()` — [TerminalCursor]{data-preview} only.
    - [WebDevice]{data-preview} implements the same `Device`/`Cursor` contract for the browser host, with terminal-only members reduced to safe no-ops.

??? abstract "Sandbox & API"

    **Sandbox**

    [Explicit Offscreen Buffer](../sandbox/rendering.md#explicit-offscreen-buffer){data-preview} <small>Live device control is unavailable in Pyodide.</small>

    **API**

    [`AbstractDevice`](../api/xnano/core/device.md#xnano.core.device.AbstractDevice){data-preview} · [`TerminalDevice`](../api/xnano/terminal/device.md#xnano.terminal.device.TerminalDevice){data-preview} · [`TerminalCursor`](../api/xnano/terminal/cursor.md#xnano.terminal.cursor.TerminalCursor){data-preview}

[Context]: ../api/xnano/context.md
[Device]: ../api/xnano/core/device.md
[Cursor]: ../api/xnano/core/device.md
[TerminalDevice]: ../api/xnano/terminal/device.md
[TerminalCursor]: ../api/xnano/terminal/cursor.md
[WebDevice]: ../api/xnano/web/device.md
