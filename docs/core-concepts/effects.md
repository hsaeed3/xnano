---
title: "Effects"
icon: "lucide/sparkles"
---

# Effects

An [effect]{data-preview} is a short visual transition over one or more field
areas: fades, sweeps, slides, dissolves, paints, and related kinds. Effects are
**descriptions** in Python. The active runtime lowers them onto the native paint
path (terminal and web share the same runtime).

Effects do not replace layout, styling, or hooks. You trigger them when
something should animate — often from a hook, after a field update, or once when
a panel appears. They need an active runtime and painted field geometry.

<div class="grid-concept-diagram" role="img" aria-label="Diagram: an effect description targets a named field area on the grid">
<svg viewBox="0 0 720 240" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="fx-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
    <pattern id="fx-cell" width="12" height="12" patternUnits="userSpaceOnUse">
      <path d="M 12 0 L 0 0 0 12" class="gcd-grid-line" />
    </pattern>
  </defs>

  <rect class="gcd-panel" x="40" y="48" width="200" height="144" rx="14" />
  <text class="gcd-label" x="140" y="88" text-anchor="middle">effect</text>
  <text class="gcd-chrome-label" x="140" y="120" text-anchor="middle">fade · slide · sweep</text>
  <text class="gcd-chrome-label" x="140" y="148" text-anchor="middle">duration_ms · color</text>

  <line class="gcd-arrow" x1="240" y1="120" x2="300" y2="120" marker-end="url(#fx-arrow)" />

  <rect class="gcd-panel gcd-panel-accent" x="312" y="72" width="160" height="96" rx="12" />
  <text class="gcd-label gcd-label-accent" x="392" y="112" text-anchor="middle">grid_effect</text>
  <text class="gcd-chrome-label" x="392" y="140" text-anchor="middle">fields=[…]</text>

  <line class="gcd-arrow" x1="472" y1="120" x2="532" y2="120" marker-end="url(#fx-arrow)" />

  <g transform="translate(544, 56)">
    <rect class="gcd-window" x="0" y="0" width="148" height="128" rx="10" />
    <rect class="gcd-chrome" x="0" y="0" width="148" height="22" rx="10" />
    <rect class="gcd-chrome" x="0" y="12" width="148" height="10" />
    <text class="gcd-chrome-label" x="74" y="15" text-anchor="middle">grid</text>
    <rect class="gcd-grid-fill" x="12" y="32" width="124" height="80" rx="4" />
    <rect x="12" y="32" width="124" height="80" rx="4" fill="url(#fx-cell)" />
    <rect class="gcd-cell-highlight-strong" x="20" y="40" width="108" height="36" rx="3" />
    <text class="gcd-z-label gcd-z-label-on" x="74" y="62" text-anchor="middle">body</text>
  </g>
</svg>
</div>

## Playing effects on fields

The usual entrypoint is
[`BaseGrid.grid_effect`](../api/xnano/grids.md){data-preview}. Pass a known
kind string (or a built effect instance) and the **field names** to animate.
Field names match the attributes on the grid; during paint those slots are
tagged so the runtime can target their rects.

```python title="grid_effect" hl_lines="10 11 12 13 14"
from xnano import BaseGrid, Field, Terminal, on_keyboard

class Panel(BaseGrid, direction="vertical"):
    title: str = Field(default="Hello", height=1, border="rounded")
    body: str = Field(default="Press f to fade this panel.")

    @on_keyboard("f")
    def fade_body(self) -> None:
        self.grid_effect(
            "fade", # (1)!
            color="violet-400", # (2)!
            duration_ms=300,
            fields=["body"], # (3)!
        )

Terminal().run(Panel())
```

1. Known kinds are listed under each family below (and as
   `KnownEffectKind` in the API).
2. Effect APIs use `color=` / `background=` for color-driven kinds. That is
   separate from field styling, which prefers `foreground=` on `Field`.
3. `fields` is required for work to start. An empty list or omit means no
   effect runs. Multiple names are allowed.

`grid_effect` returns `True` when at least one field area was found and
the runtime accepted the effect. It returns `False` when there is no active
runtime (for example outside a session) or the fields could not be resolved.

When the first argument is a **kind string**, keyword arguments mirror
[`Effect(...)`](../api/xnano/effects.md){data-preview}: `duration_ms`, `color`,
`background`, `direction`, `gradient_length`, `randomness`, `interpolation`,
`effects`, `child`, `times`, and `key`. When the first argument is already an
`AbstractEffect` instance, those kwargs are ignored — set options on the
instance itself.

## Fades

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: field color fades from dim to bright">
<svg viewBox="0 0 420 100" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <linearGradient id="fd-grad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="currentColor" stop-opacity="0.15" />
      <stop offset="100%" stop-color="currentColor" stop-opacity="0.85" />
    </linearGradient>
    <marker id="fd-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-window" x="24" y="24" width="120" height="52" rx="8" />
  <rect x="40" y="40" width="88" height="20" rx="4" class="gcd-z-base" />
  <text class="gcd-chrome-label" x="84" y="54" text-anchor="middle">body</text>
  <line class="gcd-arrow" x1="156" y1="50" x2="200" y2="50" marker-end="url(#fd-arr)" />
  <rect class="gcd-window" x="212" y="24" width="180" height="52" rx="8" />
  <rect x="228" y="40" width="148" height="20" rx="4" fill="url(#fd-grad)" class="gcd-line" />
  <text class="gcd-chrome-label" x="302" y="90" text-anchor="middle">fade · duration_ms</text>
</svg>
</div>

Fades interpolate color on the target field area.

| Kind | Class | Role |
|------|-------|------|
| `"fade"` | `FadeEffect` | Fade foreground **to** a target |
| `"fade_from"` | `FadeFromEffect` | Fade foreground **from** a source |
| `"fade_to"` | `FadeToEffect` | Fade foreground and background **to** targets |
| `"fade_from_both"` | `FadeFromBothEffect` | Fade foreground and background **from** sources |

```python title="Fade kinds"
self.grid_effect(
    "fade",
    color="emerald-400",
    duration_ms=250,
    fields=["body"],
)

self.grid_effect(
    "fade_from",
    color="slate-700",
    duration_ms=250,
    fields=["body"],
)

self.grid_effect(
    "fade_to",
    color="white",
    background="slate-900",
    duration_ms=300,
    fields=["body"],
)

self.grid_effect(
    "fade_from_both",
    color="violet-400",
    background="black",
    duration_ms=300,
    fields=["body"],
)
```

Typed equivalents:

```python
from xnano.effects import (
    FadeEffect,
    FadeFromBothEffect,
    FadeFromEffect,
    FadeToEffect,
)

FadeEffect(color="emerald-400", duration_ms=250)
FadeFromEffect(color="slate-700", duration_ms=250)
FadeToEffect(color="white", background="slate-900", duration_ms=300)
FadeFromBothEffect(
    color="violet-400",
    background="black",
    duration_ms=300,
)
```

## Dissolve and typewriter coalesce

Cell-level transitions without a motion direction.

| Kind | Class | Role |
|------|-------|------|
| `"dissolve"` | `DissolveEffect` | Random pixel dissolve |
| `"coalesce"` | `CoalesceEffect` | Typewriter-style cell assembly |

```python title="Dissolve and coalesce"
self.grid_effect("dissolve", duration_ms=400, fields=["body"])
self.grid_effect("coalesce", duration_ms=500, fields=["body"])
```

```python
from xnano.effects import CoalesceEffect, DissolveEffect

DissolveEffect(duration_ms=400)
CoalesceEffect(duration_ms=500)
```

## Directional sweeps

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: a sweep reveals a field from left to right">
<svg viewBox="0 0 420 100" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="sw-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-window" x="40" y="22" width="340" height="56" rx="8" />
  <rect class="gcd-cell-highlight-strong" x="52" y="34" width="160" height="32" rx="4" />
  <rect class="gcd-z-base" x="212" y="34" width="152" height="32" rx="4" />
  <line class="gcd-arrow" x1="52" y1="50" x2="200" y2="50" marker-end="url(#sw-arr)" />
  <text class="gcd-chrome-label" x="210" y="92" text-anchor="middle">left_to_right · sweep_in</text>
</svg>
</div>

Directional sweeps reveal or hide content with a motion gradient.

| Kind | Class | Role |
|------|-------|------|
| `"sweep_in"` | `SweepInEffect` | Directional sweep **revealing** content |
| `"sweep_out"` | `SweepOutEffect` | Directional sweep **hiding** content |

`direction` is one of `"left_to_right"`, `"right_to_left"`, `"up_to_down"`,
`"down_to_up"`. Optional: `gradient_length` (cells), `randomness`, and
`color` (gradient accent).

```python title="Sweep in and out"
self.grid_effect(
    "sweep_in",
    direction="left_to_right",
    gradient_length=14,
    randomness=2,
    color="teal-400",
    duration_ms=400,
    fields=["body"],
)

self.grid_effect(
    "sweep_out",
    direction="up_to_down",
    duration_ms=350,
    fields=["body"],
)
```

```python
from xnano.effects import SweepInEffect, SweepOutEffect

SweepInEffect(
    direction="left_to_right",
    gradient_length=14,
    randomness=2,
    color="teal-400",
    duration_ms=400,
)
SweepOutEffect(direction="up_to_down", duration_ms=350)
```

## Directional slides

Directional slides, same motion parameters as sweeps.

| Kind | Class | Role |
|------|-------|------|
| `"slide_in"` | `SlideInEffect` | Directional slide **revealing** content |
| `"slide_out"` | `SlideOutEffect` | Directional slide **hiding** content |

```python title="Slide in and out"
self.grid_effect(
    "slide_in",
    direction="down_to_up",
    duration_ms=350,
    fields=["body"],
)

self.grid_effect(
    "slide_out",
    direction="right_to_left",
    color="sky-300",
    duration_ms=300,
    fields=["body"],
)
```

```python
from xnano.effects import SlideInEffect, SlideOutEffect

SlideInEffect(direction="down_to_up", duration_ms=350)
SlideOutEffect(
    direction="right_to_left",
    color="sky-300",
    duration_ms=300,
)
```

## Color paints

Paints set colors on the target area (as opposed to fading through them).

| Kind | Class | Role |
|------|-------|------|
| `"paint"` | `PaintEffect` | Paint foreground and background |
| `"paint_fg"` | `PaintForegroundEffect` | Paint foreground only |
| `"paint_bg"` | `PaintBackgroundEffect` | Paint background only |

```python title="Paint kinds"
self.grid_effect(
    "paint",
    color="white",
    background="slate-800",
    duration_ms=200,
    fields=["body"],
)

self.grid_effect(
    "paint_fg",
    color="amber-300",
    duration_ms=200,
    fields=["title"],
)

self.grid_effect(
    "paint_bg",
    background="slate-900",
    duration_ms=200,
    fields=["body"],
)
```

```python
from xnano.effects import (
    PaintBackgroundEffect,
    PaintEffect,
    PaintForegroundEffect,
)

PaintEffect(color="white", background="slate-800", duration_ms=200)
PaintForegroundEffect(color="amber-300", duration_ms=200)
PaintBackgroundEffect(background="slate-900", duration_ms=200)
```

## Delays and pauses

| Kind | Class | Role |
|------|-------|------|
| `"sleep"` | `SleepEffect` | Empty delay (useful inside sequences) |
| `"delay"` | `DelayEffect` | Wait, then run a `child` |

```python title="Sleep and delay"
from xnano.effects import DelayEffect, Effect, FadeEffect, SleepEffect

# Standalone pause for sequencing
SleepEffect(duration_ms=150)

# Wait, then fade
DelayEffect(
    duration_ms=200,
    child=FadeEffect(color="violet-400", duration_ms=250),
)

# Same idea via kind strings
self.grid_effect(
    "delay",
    duration_ms=200,
    child=Effect("fade", color="violet-400", duration_ms=250),
    fields=["body"],
)
```

## Combining effects

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: sequence runs effects one after another; parallel runs them together">
<svg viewBox="0 0 480 130" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="cm-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <text class="gcd-chrome-label" x="100" y="18" text-anchor="middle">sequence</text>
  <rect class="gcd-panel" x="24" y="28" width="72" height="36" rx="8" />
  <text class="gcd-chrome-label" x="60" y="50" text-anchor="middle">A</text>
  <line class="gcd-arrow" x1="96" y1="46" x2="120" y2="46" marker-end="url(#cm-arr)" />
  <rect class="gcd-panel" x="128" y="28" width="72" height="36" rx="8" />
  <text class="gcd-chrome-label" x="164" y="50" text-anchor="middle">B</text>
  <text class="gcd-chrome-label" x="340" y="18" text-anchor="middle">parallel</text>
  <rect class="gcd-panel gcd-panel-accent" x="280" y="28" width="72" height="36" rx="8" />
  <text class="gcd-chrome-label" x="316" y="50" text-anchor="middle">A</text>
  <rect class="gcd-panel gcd-panel-accent" x="280" y="76" width="72" height="36" rx="8" />
  <text class="gcd-chrome-label" x="316" y="98" text-anchor="middle">B</text>
  <path class="gcd-z-connector" d="M260 46 H 272" />
  <path class="gcd-z-connector" d="M260 94 H 272" />
  <text class="gcd-chrome-label" x="240" y="74" text-anchor="middle">together</text>
</svg>
</div>

| Kind | Class | Role |
|------|-------|------|
| `"sequence"` | `SequenceEffect` | Run children one after another (`effects=`) |
| `"parallel"` | `ParallelEffect` | Run children together (`effects=`) |
| `"repeat"` | `RepeatEffect` | Repeat a `child` `times` times (`None` = forever) |

```python title="Sequence, parallel, repeat"
from xnano.effects import Effect, ParallelEffect, RepeatEffect, SequenceEffect

self.grid_effect(
    "sequence",
    effects=(
        Effect("sweep_in", direction="up_to_down", duration_ms=350),
        Effect("fade", color="sky-300", duration_ms=200),
    ),
    fields=["body"],
)

self.grid_effect(
    "parallel",
    effects=(
        Effect("fade", color="emerald-400", duration_ms=300),
        Effect("paint_bg", background="slate-900", duration_ms=300),
    ),
    fields=["body"],
)

self.grid_effect(
    "repeat",
    child=Effect("fade", color="violet-400", duration_ms=200),
    times=3,
    fields=["title"],
)
```

Typed composition:

```python
intro = SequenceEffect(
    effects=(
        Effect("sweep_in", direction="left_to_right", duration_ms=400),
        Effect("fade", color="emerald-400", duration_ms=250),
    ),
)
pulse = RepeatEffect(
    child=Effect("fade", color="teal-400", duration_ms=180),
    times=2,
)
together = ParallelEffect(
    effects=(
        Effect("fade_to", color="white", background="black", duration_ms=300),
        Effect("coalesce", duration_ms=300),
    ),
)

self.grid_effect(intro, fields=["title", "body"])
```

## Duration, easing, and filters

Every effect instance carries these base attributes (from `AbstractEffect`):

| Attribute | Role |
|-----------|------|
| `duration_ms` | Length in milliseconds (default `300`) |
| `interpolation` | Easing curve (`"linear"`, `"smooth_step"`, `"sine_in_out"`, `"bounce_out"`, …) |
| `cell_filter` | Which cells participate (`"all"`, `"text"`, `"non_empty"`, `"background"`, `"background_only"`) |
| `key` | Optional id so replaying replaces an in-flight effect on that field |

Directional kinds (`sweep_*`, `slide_*`) also take:

| Attribute | Role |
|-----------|------|
| `direction` | `"left_to_right"`, `"right_to_left"`, `"up_to_down"`, `"down_to_up"` |
| `gradient_length` | Motion gradient length in cells (default `14`) |
| `randomness` | Randomness along the gradient (default `2`) |
| `color` | Accent color of the motion gradient |

Notes:

- `duration_ms`, `interpolation`, `color`, `background`, `direction`,
  `gradient_length`, `randomness`, `effects`, `child`, `times`, and `key` can
  be passed as kwargs on kind-string calls to `grid_effect` / `Effect(...)`.
- `cell_filter` is set on a typed instance (for example
  `FadeEffect(color="cyan", cell_filter="text")`), not as a kind-string kwarg.
- When `effect` is already an instance, set `key` on that instance; the
  `key=` kwarg on `grid_effect` is only used for kind strings.

## When effects run

Effects need an active runtime and a painted field geometry, so call
`grid_effect` from hooks, after the grid is attached to a live
`Terminal` / `Web` session, or from other runtime-bound code — not at module
import time.

```python title="Trigger from a hook"
from xnano import BaseGrid, Field, Terminal, on_keyboard, on_tick

class Banner(BaseGrid, direction="vertical"):
    label: str = Field(default="ready", height=1, border="rounded")
    _intro_done: bool = Field(default=False, state=True)

    @on_tick
    def play_intro_once(self) -> None:
        if self._intro_done:
            return
        self._intro_done = True
        self.grid_effect(
            "coalesce",
            duration_ms=450,
            fields=["label"],
        )

    @on_keyboard("r")
    def replay(self) -> None:
        self.grid_effect(
            "sweep_in",
            direction="left_to_right",
            duration_ms=350,
            fields=["label"],
            key="replay", # (1)!
        )

Terminal().run(Banner())
```

1. `key` de-duplicates: replaying with the same key on the same field replaces
   the in-flight effect instead of stacking another.

[`Runtime.play_effect`](../api/xnano/core/runtime.md){data-preview} is the
lower-level API. Grids wrap it as `grid_effect` so field names resolve
against that grid's layout after paint.

Effects are terminal-native in implementation detail (tachyonfx-backed under
xnano-core). On hosts without a live effect engine path, starting an effect may
no-op; the description API stays the same.

## Kind strings and typed builders

Two equivalent construction paths:

```python title="Effect factory vs typed classes"
from xnano.effects import Effect, FadeEffect, SweepInEffect

# Factory: kind string + kwargs
fade = Effect("fade", color="emerald-400", duration_ms=250)
sweep = Effect(
    "sweep_in",
    direction="left_to_right",
    duration_ms=400,
)

# Typed classes: same descriptions, explicit types
fade_too = FadeEffect(color="emerald-400", duration_ms=250)
sweep_too = SweepInEffect(direction="left_to_right", duration_ms=400)
```

Pass either form into `grid_effect`:

```python
self.grid_effect(fade, fields=["body"])
self.grid_effect("fade", color="emerald-400", fields=["body"])
```

Prefer kind strings at the call site for one-off triggers. Prefer typed classes
when you store, compose, or type-check effect values.

## Next

- [Grids](grids.md) — fields that effects target
- [Events & Hooks](events.md) — where you usually trigger them
- [Device & Cursor](device.md) — host chrome, not field animation

??? abstract "API"

    [`xnano.effects`](../api/xnano/effects.md){data-preview} ·
    [`BaseGrid.grid_effect`](../api/xnano/grids.md){data-preview} ·
    [`Runtime.play_effect`](../api/xnano/core/runtime.md){data-preview}

[effect]: ../api/xnano/effects.md
