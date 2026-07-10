---
title: "Native Rust Bindings"
---

# Native Bindings

`xnano_core.rust.native` is a flat re-export of everything compiled into the Rust extension. You don't need to use any of this directly — `xnano` wraps all of it. But if you're curious about what's underneath, or you're contributing to xnano internals, this is the map.

---

## Layout

These are the ratatui primitives that xnano uses internally to split the terminal into slots.

| Symbol | What it does |
|---|---|
| `Rect` / `RefRect` | A rectangular region (x, y, width, height in cells). All layout is expressed in `Rect`s. |
| `Layout` | Splits a `Rect` into sub-rects along one axis, given a list of `Constraint`s. |
| `Constraint` | `Length(n)`, `Min(n)`, `Max(n)`, `Percentage(n)`, `Ratio(a, b)`, `Fill(n)` |
| `Flex` | What to do with leftover space: `Start`, `End`, `Center`, `SpaceBetween`, `SpaceAround` |
| `Direction` | `Horizontal` / `Vertical` |
| `Margin` | Horizontal/vertical margin applied before splitting |

xnano's `Sizing` type is the friendly Python-side API that compiles down to these:

```python
# What you write:
Field(default="Sidebar", width="25%")
Field(default="Content", width="1fr")
Field(default="Footer",  height=3)

# What xnano passes to ratatui's Layout internally:
Constraint.Percentage(25)
Constraint.Fill(1)
Constraint.Length(3)
```

---

## Widgets

Standard ratatui widgets — xnano uses a subset of these today, but all are available in the native namespace.

| Symbol | Used for |
|---|---|
| `Paragraph` | Most text content ends up here |
| `Block` | Borders and titles around any widget |
| `Span` / `Line` / `Text` | Styled text building blocks inside a `Paragraph` |
| `Sparkline` | Bar chart for numeric series |
| `Canvas` | Free-draw surface |
| `Scrollbar` / `ScrollbarState` | Optional scrollbar decorations |
| `Clear` | Clears a `Rect` to background — used before painting a slot |

Other widgets (`Chart`, `BarChart`, `Gauge`, `LineGauge`, `RatTable`, `RatList`, `Tabs`) are present in the extension but not yet wired into the Python IR.

---

## Styling

| Symbol | What it does |
|---|---|
| `Style` | Combines a foreground color, background color, and modifiers |
| `Color` | A color value — RGB, indexed, or named |
| `Modifier` | `Bold`, `Dim`, `Italic`, `Underline`, `Blink`, `Reversed`, etc. |

Color helpers — all work with `xnano_core.rust.native` types directly:

```python
from xnano_core.rust.native import tailwind_color, color_from_hex, lighten

violet = tailwind_color("violet", 500)
custom = color_from_hex("#a78bfa")
bright = lighten(violet, amount=0.2)
```

Available utilities:

- `tailwind_color(name, shade)` — look up a Tailwind CSS palette color
- `color_from_hex(hex)` / `color_from_hsl(h, s, l)` — construct a color
- `color_lerp` / `color_to_hsl` / `color_to_srgb` — conversions
- `lighten` / `darken` / `saturate` — HSL-space adjustments (fg, bg, or both variants)
- `paint` / `paint_fg` / `paint_bg` — apply a color to a `Buffer` region

---

## Buffer

The `Buffer` is the off-screen cell grid ratatui renders into each frame. xnano-core diffs the new buffer against the previous one and emits only the changed cells.

| Symbol | What it does |
|---|---|
| `Buffer` | Off-screen cell grid for one frame |
| `BufferCell` / `BufferMutView` | Per-cell read/write access — used by effects and custom drawing |
| `CompletedFrame` | Opaque handle returned after a frame is committed |

---

## Effects (tachyonfx)

tachyonfx effects operate on the `Buffer` after it's been rendered. From Python, you access them through `xnano.effects.Effect` — the native types below are what that wraps.

| Symbol | What it does |
|---|---|
| `Effect` | An opaque effect handle |
| `EffectManager` | Tracks active effects per `Rect`, advances them each tick |
| `EffectTimer` | Drives an effect for a fixed duration |

**Effect constructors:**

```python
from xnano.effects import Effect

# Typewriter assemble
Effect("coalesce", duration_ms=600)

# Colour fade
Effect("fade", color="#a78bfa", duration_ms=400)

# Random pixel dissolve
Effect("dissolve", duration_ms=500)

# Horizontal scan-line reveal
Effect("sweep_in", direction="left_to_right", gradient_length=12, duration_ms=700)
```

Full list of available names:

| Name | Description |
|---|---|
| `"coalesce"` | Characters assemble from random positions |
| `"fade"` / `"fade_from"` | Alpha or color fade in/out |
| `"dissolve"` | Random pixel-by-pixel fade |
| `"sweep_in"` / `"sweep_out"` | Horizontal scan-line reveal |
| `"slide_in"` / `"slide_out"` | Directional slide |
| `"glitch"` | Horizontal glitch distortion |
| `"hsl_shift"` | Color shift over time |

Compositors:

```python
from xnano_core.rust.native import sequence_effects, parallel_effects, ping_pong_effect

# Run two effects back-to-back
seq = sequence_effects(fade_effect, sweep_effect)

# Run two effects at the same time
par = parallel_effects(glitch_effect, hsl_effect)

# Play forward, then backward
pp = ping_pong_effect(coalesce_effect)
```

---

## Events

Crossterm event types re-exported for use in dispatch and hooks:

| Symbol | What it carries |
|---|---|
| `KeyEvent` | `.code` (`KeyCode`), `.modifiers` (`KeyModifiers`), `.kind` (`KeyEventKind`) |
| `KeyCode` | `Char(c)`, `Enter`, `Backspace`, `Esc`, `Up`, `Down`, `Left`, `Right`, `F(n)`, … |
| `KeyModifiers` | Bitflag: `SHIFT`, `CONTROL`, `ALT`, `SUPER`, `META` |
| `KeyEventKind` | `Press`, `Repeat`, `Release` |
| `MouseEvent` | `.kind`, `.column`, `.row`, `.modifiers` |
| `MouseEventKind` | `Down(button)`, `Up(button)`, `Drag(button)`, `Moved`, `ScrollUp`, `ScrollDown` |
| `MouseButton` | `Left`, `Right`, `Middle` |
| `CoreEvent` | xnano-core's wrapper — carries any of the above plus resize and tick payloads |

---

## Raw terminal control

These are the crossterm functions called at session start and teardown. You don't need to call them — they're listed here for completeness.

```python
from xnano_core.rust.native import (
    enter_alternate_screen, leave_alternate_screen,
    enable_raw_mode, disable_raw_mode,
    show_cursor, hide_cursor,
    enable_mouse_capture, disable_mouse_capture,
    enable_bracketed_paste, disable_bracketed_paste,
    terminal_size,   # -> (columns, rows)
    set_terminal_title,
    flush_stdout_buffer,
    begin_synchronized_update, end_synchronized_update,
)
```
