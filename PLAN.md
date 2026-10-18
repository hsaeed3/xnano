# Plan: restructuring the `xnano` package

Status: proposal for the `v2` line before 2.0.0 ships. Nothing in it is
implemented. Line counts and names are from the working tree on 2026-10-18 and
will drift.

The goal is a package whose layout reads the way a person thinks about a
terminal program: what is on the screen, what is heard, what reacts, how things
look, and the screen itself. No functionality is removed; things are renamed,
moved and in places split so that each public name sits where someone would look
for it. Because 2.0.0 has not shipped, nothing keeps a compatibility alias:
every move is a rename inside the unreleased line.

## Principles

1. **`xnano` is the opinionated layer.** `xnano_core`, `xnano_audio` and
   `xnano_image` are treated as upstream libraries with their own vocabulary
   (`TerminalImage`, `Device`, `TerminalMelody`, `Runtime`). `xnano` never
   re-exports an upstream class under its upstream name as the way users reach
   it. It names the concept the way a user says it, wraps or aliases the
   upstream class behind that name, and records the mapping in the docstring's
   `Maps to` line. The same holds inside `xnano`: a core class that leaks
   through a public signature is wrapped or aliased at the `xnano` level.
2. **No private scripts at the top of `xnano/`.** `xnano/_name.py` is not
   allowed. Private code lives in a private package (`xnano/_schema/`,
   `xnano/_internal/`, `xnano/_runtime/`) or inside a public package as a
   private module (`xnano/hooks/_triggers.py`). Public scripts
   (`xnano/canvas.py`) and public packages (`xnano/effects/`) are both fine.
3. **One concept, one name, one home.** A name that stands for the same thing in
   two media (a region of the screen, a region of the timeline) is one class,
   not two look-alikes.
4. **Re-export modules are lazy and self-documenting**, in the style of the
   rewritten `xnano/expressions.py`: a `TYPE_CHECKING` block names the upstream
   class, the module-level name carries its own docstring and example, and a
   module `__getattr__` imports on first use. This keeps `import xnano` fast and
   keeps the optional `xnano_audio` and `xnano_image` out of the import of
   `xnano` (as `CLAUDE.md` requires).
5. **The rules in `CLAUDE.md` stand**: full words, booleans as questions, no
   `Any`, every public attribute documented, docstrings for users only.

## The package today

| Module | Lines | Role | Why it moves |
| --- | --- | --- | --- |
| `canvas.py` | 4638 | `Canvas`, `new`, `active`, `iter`, plus screen attachment, gates, slots, the frame loop | Holds terminal-device code (gates, window size, screen attach) that belongs to `terminal` |
| `_customize.py` | 2310 | `fx()`, 27 `XxxCustomization` dataclasses, 27 `XxxArguments` TypedDicts, kind literals, `effect_sequence`, `normalize_effect`, `apply_effects` | Private top-level script; mixes effects with fills, layouts and pixels |
| `components.py` | 1376 | `renderable`, `playable`, component classes | Stays |
| `placement.py` | 1254 | `Placement` | Stays |
| `appearance.py` | 1130 | `Colors`, `ColorSlot`, `BorderAppearance`, `Edges`, the `_Looked` and `_TextModifiers` mixins | Becomes a package with its private halves |
| `audio.py` | 1129 | `AudioDevice`, melody text parsing, and 12 re-exports of `xnano_audio` classes under upstream names | Upstream names leak; the user-facing `Audio` value lives elsewhere |
| `region.py` | 1123 | `Region`, `box`, `write` | Stays; `Region` gains the audio medium (below) |
| `_hooks.py` | 1068 | `HookHandle`, the `_Hooked` mixin, argument checking | Private top-level script |
| `art.py` | 1053 | `Art`, `Camera`, `draw` | Becomes a package that also holds pixels and images |
| `state.py` | 946 | `StateNamespace`, `StatePath`, `parse_path` | Stays |
| `_effect_controller.py` | 940 | `RenderableEffects`, `PlayableEffects`, `EffectController` | Private top-level script |
| `expressions.py` | 922 | Lazy re-exports | Stays; `DeviceWidth`/`DeviceHeight` renamed (below) |
| `_media.py` | 880 | `Image`, `Audio`, `from_image`, `from_audio`, image fitting, animation refresh | Private top-level script holding two public classes |
| `_when.py` | 819 | `compile_when`, `parse_when`, `CompiledWhen`, `normalize_chord` | Replaced by `hooks/_triggers.py` |
| `input.py` | 645 | `Input`, `KeyboardInput`, `MouseInput`, `ScrollInput`, `ClipboardInput` | Stays |
| `_axes.py` | 526 | Axis conversion and the `check_*` validators | Private top-level script |
| `_appearance.py` | 510 | The `Appearance` dataclass, spacing, border kinds | Private top-level script |
| `music.py` | 447 | `Note`, `note`, `play`, `PlayHandle` | Folds into the `audio` package |
| `_host.py` | 443 | `_Host`, `_InlineHost`, `_ThreadHost`, `_Registration` | Private top-level script |
| `context.py` | 431 | `Context`, `Frame`, `Update`, `Plugin`, `ReadLog` | Stays; gains `region` |
| `demo.py` | 408 | The feature demo | Stays |
| `types.py` | 405 | Public type index | Stays; re-exports from `_schema` |
| `operations.py` | 387 | Core operations, `ContextualOperation`, `hook`, `fx`, `Customization` | Loses `fx`, `hook` and the effect types |
| `cursor.py` | 341 | `Cursor` | Stays |
| `_values.py` | 323 | Type aliases and `TypeVar`s | Private top-level script |
| `terminal.py` | 306 | `Terminal`, `open`, screen claiming, live runtime creation | Becomes the `terminal` package |
| `errors.py` | 287 | `TerminalError` and codes | Stays |
| `_decoration.py` | 285 | Border, padding and margin painting | Private top-level script |
| `pixel.py` | 262 | `Pixel`, `PixelPreset` | Moves into `art` |
| `symbols.py` | 228 | The symbol registry | Stays |
| `time.py` | 220 | `Time` | Stays |
| `widgets.py` | 125 | 28 re-exports of `xnano_core` widgets | Stays; made lazy; `Canvas` renamed |
| `_attributes.py` | 95 | `_SealedAttributes`, `refuse_unknown_keywords` | Private top-level script |
| `output.py` | 79 | `Output` | Stays |
| `_optional.py` | 62 | The optional-extra loader | Private top-level script |
| `styles.py`, `geometry.py`, `events.py`, `buffers.py` | 44, 28, 23, 26 | Re-exports | Stay; made lazy; `buffers` drops `Image` |
| `effects.py` | 36 | 6 re-exports of core effect classes | **Already shadowed** by the new `effects/` package |
| `image.py` | 19 | 2 re-exports of `xnano_image` | Removed; its two classes get `xnano` homes |
| `hooks/`, `effects/` | 32 | The new packages with their notes | Filled in by this plan |

Twelve private top-level scripts (`_appearance`, `_attributes`, `_axes`,
`_customize`, `_decoration`, `_effect_controller`, `_hooks`, `_host`, `_media`,
`_optional`, `_values`, `_when`) must find a home. Three public scripts
(`image`, `music`, `effects`) dissolve into packages, and three (`art`, `audio`,
`terminal`) become packages.

Two things are broken on the working tree right now and are fixed by the first
phase:

- `xnano/effects/` (a package) and `xnano/effects.py` (a script) share a name,
  and Python imports the package, so `from xnano.effects import Effect` fails.
- `scripts/capture_examples.py` and `tests/test_canvas.py` still point at the
  deleted `examples/` directory.

## The package after

```text
xnano/
  __init__.py          new, open, active, iter, Canvas, Terminal, Context, Color, hook, effect,
                       write, box, draw, Pixel, Image, Sound, Note, note, play, renderable,
                       playable, symbols
  __main__.py
  demo.py              the feature demo (public, documented), with assets/
  assets/              dusk.png, luffy.xni (demo pictures; nothing else is packaged)

  canvas.py            Canvas, new, active, iter
  placement.py         Placement
  region.py            Region, box, write            (one Region for both media, see below)
  context.py           Context, Frame, Update, Plugin, ReadLog
  components.py        renderable, playable, the component classes
  state.py             StateNamespace, StatePath, parse_path
  time.py              Time
  cursor.py            Cursor
  input.py             Input, KeyboardInput, MouseInput, ScrollInput, ClipboardInput
  output.py            Output
  expressions.py       the expression vocabulary (lazy)
  operations.py        the core operations and ContextualOperation (lazy for core names)
  events.py, styles.py, geometry.py, buffers.py, widgets.py     lazy re-exports
  symbols.py
  errors.py
  types.py             the public type index: re-exports every TypedDict, Literal and alias

  hooks/               reacting: the hook decorator, handles and conditions
    __init__.py        hook, HookHandle, Hook, HookKind, HookGenerator, When
    _handles.py        from _hooks.py: HookHandle, _Hooked, argument checking
    _triggers.py       from _when.py: compile_when, parse_when, CompiledWhen, normalize_chord

  effects/             changing how content looks or sounds over time
    __init__.py        effect(), the EffectKind literals, RenderableEffectProperties,
                       PlayableEffectProperties, EffectController, the 28 parameter classes
    _properties.py     the dataclasses (XxxEffectParameters) and the two Properties classes
    _controller.py     from _effect_controller.py
    _registry.py       kind -> (parameters class, core customization); effect_sequence,
                       normalize_effect, apply_effects    (replaces the empty _schema.py)

  terminal/            the real screen: everything about the device a program runs in
    __init__.py        Terminal, open, TerminalSettings, capabilities(), graphics()
    _screen.py         from terminal.py: claiming the one screen, the live runtime, the
                       held-back-output warning, window size
    _settings.py       from canvas.py: gate names, defaults, inferred gates, validation,
                       the screen-attach and screenless-restore paths (_attach_screen,
                       _restore_screenless, _gates_for_screen, _parse_open_settings)
    _capabilities.py   wraps xnano_core.TerminalCapabilities, KeyboardCapabilities,
                       xnano_image.TerminalGraphics as xnano-level values

  art/                 what is seen: pictures made of cells, pixels and images
    __init__.py        Art, Camera, draw, Pixel, PixelPreset, Image, load_image (from_image)
    _pixels.py         from pixel.py
    _worlds.py         from art.py: Art, Camera, draw
    _images.py         from _media.py: Image, image fitting, ImageAnimation, ImageSource

  audio/               what is heard: sounds, notes, melodies and the canvas's player
    __init__.py        Sound, Note, note, Melody, play, PlayHandle, AudioDevice, Microphone,
                       instrument_names, Pitch, NoteName, InstrumentName, the audio errors
    _sounds.py         from _media.py: Sound (today's Audio), load_sound (from_audio), WAV decoding
    _notes.py          from music.py: Note, note, play, PlayHandle, the default player
    _melodies.py       from audio.py: melody text parsing, Melody
    _player.py         from audio.py: AudioDevice, recording on a manual clock, the beat clock
    _microphone.py     from audio.py: the level and level history

  appearance/          how things look: colors, borders, padding, margin, text modifiers
    __init__.py        Colors, ColorSlot, BorderAppearance, BorderSide, Edges, PaddingAppearance,
                       MarginAppearance
    _look.py           from _appearance.py: the Appearance dataclass, spacing, border kinds
    _decoration.py     from _decoration.py
    _owners.py         the _Looked and _TextModifiers mixins

  _schema/             every TypedDict, Literal and TypeAlias, by topic (no behavior)
    __init__.py
    _generics.py       DepsT, StateT, ValueT, WrittenDepsT, ... (from _values.py)
    _axes.py           Axis, Percentage, RangeBound, Bound, AxisName, HorizontalPosition, ...
    _layout.py         CanvasLayout, EdgeBehavior, Anchor, PixelEncoding, Interpolation, ...
    _content.py        Renderable, Playable, PlaySource, Content, SupportsRender, SupportsPlay
    _appearance.py     SpacingDictionary, Spacing, AppearanceArguments, CanvasAppearanceArguments
    _effects.py        the 28 XxxEffectParametersSchema TypedDicts, the kind literals, the
                       specification unions (from _customize.py)
    _hooks.py          Hook, HookGenerator, HookKind, When, KeyName, HeldMouseButtonName
    _terminal.py       GateSettings (-> TerminalSettings), CanvasSettings, OpenSettings
    _media.py          ImageFit, ResamplingFilter, PlayOptions

  _internal/           machinery shared by several public modules
    _attributes.py     from _attributes.py
    _axes.py           from _axes.py: conversion and the check_* validators
    _optional.py       from _optional.py
    _content.py        from _media.py: turning written content into a buffer

  _runtime/            the loop a canvas runs on
    _host.py           from _host.py
    _slots.py          from canvas.py: the slot buffers and the per-frame layout solve
```

The top-level `xnano/` then has 21 public scripts, 6 public packages, 3 private
packages and no private scripts.

## Per-area plans

### `xnano.hooks`

- `hook()` moves from `operations.py` to `hooks/__init__.py`. It keeps its two
  forms: the decorator form that returns a reusable `ContextualOperation`, and
  `canvas.hook(...)`, `placement.hook(...)` and `component.hook(...)` as
  methods. `ContextualOperation` itself stays in `operations.py` (it is an
  operation).
- `_hooks.py` becomes `hooks/_handles.py` with no code changes beyond imports.
  The decision to move it rather than leave it is principle 2 plus the fact that
  `HookHandle` is a public type (`xnano.types.HookHandle`), so its home should
  be the hooks package.
- `_when.py` becomes `hooks/_triggers.py`, as the note in that file says. The
  public vocabulary for the `when=` argument is unchanged: an expression, a
  function or the string syntax. `When` (the alias) moves to `_schema/_hooks.py`
  and is re-exported from `xnano.hooks` and `xnano.types`.
- `test_when.py` is renamed `test_hook_triggers.py`; `test_hooks.py` keeps its
  name.

### `xnano.effects`

This is the largest move. Today `_customize.py` holds 27 kinds under one
`Customization` base, 21 visual, 7 audio, plus six that are not effects at all
(`fill`, `write`, `layout`, `fuzz`, `pixels`, `raster`: operations whose
settings may follow expressions).

- **`effect()`** replaces `fx()` as the overloaded module function. It takes the
  visual kinds (`'effect.fade_to'`, ...) and the audio kinds (`'audio.reverb'`,
  ...), exactly as `fx` does today, with one `@overload` per kind over its
  `ParametersSchema` TypedDict, and returns that kind's `Parameters` dataclass.
  The returned object still applies with `|`, `canvas.update(...)`,
  `placement.update(...)`, can be returned from a hook, and can be listed in
  `effects=[...]`. The kind strings keep their `effect.` and `audio.` prefixes
  so every `effects=[{'kind': ...}]` list keeps working.
- **The six non-effect customizations** move to `xnano.operations` as
  `DynamicFill`, `DynamicWrite`, `DynamicLayout`, `DynamicFuzz`, `DynamicPixels`
  and `DynamicRaster`: the expression-following forms of the plain `Fill`,
  `Write`, `Layout`, `Fuzz`, `Pixels` and `Raster` operations. They are built by
  their class, not by `effect()`, so a layout is never called an effect. Their
  TypedDicts move to `_schema/_operations.py`.
- **Naming.** `XxxCustomization` becomes `XxxEffectParameters` and
  `XxxEffectArguments` becomes `XxxEffectParametersSchema`; `Customization`
  becomes `EffectParameters` (the base dataclass); `EffectCustomization` becomes
  `EffectSpecification`... see decision D1 for the `Parameters` spelling.
  `RenderableEffects` becomes `RenderableEffectProperties` and `PlayableEffects`
  becomes `PlayableEffectProperties`, as the note in `_properties.py` asks;
  `EffectController` keeps its name. The `.fx` attributes on `Canvas`,
  `Placement`, `Context` and `AudioDevice` keep their name, which `CLAUDE.md`
  lists as an accepted short form.
- **Files.** `_properties.py` holds the dataclasses and the two Properties
  classes. `_controller.py` holds what `_effect_controller.py` holds.
  `_registry.py` (replacing the empty `_schema.py`) holds the kind-to-class map
  and `effect_sequence`, `normalize_effect` and `apply_effects`. The TypedDicts
  live in `_schema/_effects.py`, which is what the note about
  `xnano._schema._effects.py` asks for.
- **`xnano/effects.py` is deleted.** Its six core names (`Effect`, `Fade`,
  `Dissolve`, `Glitch`, `Fuzz`, `CancelEffect`) are the upstream operation
  classes; `Effect` and `CancelEffect` are re-exported from `xnano.operations`
  (they are operations), and the method-style constructors
  (`Effect.fade_to(...)`) are documented as the operation form of
  `effect('effect.fade_to', ...)`. `Fuzz` is already in `operations`.
- `test_fx.py` becomes `test_effects.py`.

### `xnano.terminal`

Everything about the real device gathers here, and the word "device" stops
appearing in public `xnano` names.

- `terminal.py` becomes `terminal/__init__.py` plus `_screen.py`, holding
  `Terminal`, `open`, the one-screen claim, the live runtime creation and the
  held-back-output warning.
- The gate machinery leaves `canvas.py`: `_GATE_NAMES`, `_DEFAULT_GATES`,
  `_INFERRED_GATES`, `_validate_gate_values`, `_split_settings`,
  `_parse_open_settings`, `_gates_for_screen`, `_check_gates`, `_attach_screen`,
  `_restore_screenless`, `_restore_carried` and `_window_size` move to
  `terminal/_settings.py` and `terminal/_screen.py`. `Canvas.open` stays a
  method, delegating to them. `canvas.py` shrinks by roughly 700 lines.
- `GateSettings` is renamed **`TerminalSettings`** (the keywords are what the
  terminal is asked to report), defined in `_schema/_terminal.py` and
  re-exported from `xnano.terminal` and `xnano.types`. `OpenSettings` and
  `CanvasSettings` keep their names.
- **Capabilities.** `xnano_core.TerminalCapabilities`, `KeyboardCapabilities`,
  `detect_terminal_capabilities`, `query_keyboard_capabilities`, `ColorProfile`,
  `GraphicsProtocol` and `xnano_image.TerminalGraphics` are reached as
  `xnano.terminal.capabilities()` (one call, one `TerminalCapabilities` value
  with `.colors`, `.keyboard`, `.graphics` and `.is_available` fields) and as
  `Terminal.capabilities` on an open terminal. `Terminal` also gains `window`
  (the window size in cells, today read through `runtime.device.size`) and
  `settings` (the resolved `TerminalSettings`). `xnano/image.py` goes away with
  this: `TerminalGraphics` was its only reason to exist besides `TerminalImage`,
  which moves to `art`.
- **Expressions.** `DeviceWidth` and `DeviceHeight` are exposed from
  `xnano.expressions` as **`TerminalWidth`** and **`TerminalHeight`** (the core
  names stay as the `Maps to` line); `Root` keeps its meaning (the root canvas,
  which on the screen is the terminal).
- `Output` stays in `xnano/output.py`: drawn frames exist on an offscreen canvas
  too. Its `is_captured`/`take_captured` members are documented as having a
  value only on a `Terminal`.
- `TerminalError` and its codes keep their names; "terminal" there is the
  established vocabulary for the whole error family, not the device.

### `xnano.art`

Pictures of every kind live together: text art, pixels and decoded images.

- `art.py` becomes `art/_worlds.py` (`Art`, `Camera`, `draw`), `pixel.py`
  becomes `art/_pixels.py`, and the image half of `_media.py` becomes
  `art/_images.py`.
- `xnano.Image` stays the user-facing image: a decoded picture plus how it is
  shown. The upstream `xnano_image.TerminalImage` is reached as `Image.decoded`
  and is never a public `xnano` name; `from_image` is renamed **`load_image`**
  (it reads a path, bytes or a decoded image into an `Image`) and lives in
  `xnano.art` with a top-level alias.
- `Region.draw_image`, `Region.half_blocks`, `Region.braille`, `pixel_for_cell`
  and `cell_for_pixel` stay on `Region` (a region is where pixels land); `art`
  documents them as the way to paint into a region.
- `xnano/buffers.py` drops its `Image` re-export (a buffer is cells; an image is
  art).
- `test_media.py` splits into `test_art_images.py` and `test_audio_sounds.py`;
  `test_pixel.py` and `test_art.py` keep their names.

### `xnano.audio`

Everything that is heard, in `xnano`'s own words. The upstream `xnano_audio`
names (`TerminalSound`, `TerminalMelody`, `TerminalNote`, `TerminalMicrophone`,
...) disappear from `xnano`'s public surface and are reached through the `xnano`
classes that wrap them.

- **`Sound`** replaces today's `xnano.Audio` value class: rendered samples you
  can play. `from_audio` becomes **`load_sound`**. `Sound.samples` is the
  upstream `TerminalSound`.
- **`Note`**, `note()`, `play()` and `PlayHandle` move from `music.py` into
  `audio/_notes.py`; `xnano/music.py` is deleted. `Note` is the only
  upstream-free value (it needs no extra), which stays true.
- **`Melody`** is new at the `xnano` level: the parsed form of melody text (`'C4
  E4 G4:2 rest C5+E5+G5'`), with the notes, the tempo map and the time signature
  the upstream `TerminalMelody` carries. `play()` keeps accepting melody text
  directly; `Melody` is what you get when you want to inspect or reuse one.
- **`AudioDevice`** keeps its name and its members (`play`, `render_sound`,
  `beat`, `start`, `pause`, `resume`, `stop`, `level`, `fx`); it moves to
  `audio/_player.py`. "Device" here is the sound output, not the terminal, so it
  is outside the terminal naming rule (decision D5 offers a rename if wanted).
- **`Microphone`** wraps `TerminalMicrophone` behind `canvas.audio.microphone`
  with `level`, `level_history`, `is_open`, `sample_rate` and `channels`;
  today's `level` and `level_history` on `AudioDevice` stay as shortcuts.
- `instrument_names`, `Pitch`, `NoteName`, `InstrumentName` and the two audio
  errors are re-exported lazily under their current names, which are already
  full words.
- `test_music.py`, `test_audio.py` and `test_audio_device.py` are kept and
  renamed `test_audio_notes.py`, `test_audio_melodies.py` and
  `test_audio_player.py`.

### `Region` across both media

Today `Region` is a rectangle of cells with three resolutions (`cells`,
`half_blocks`, `braille`) and `context.buffer`/`context.size` tell a hook where
it is on the screen. A playable hook has nothing equivalent. The unification:

- A `Region` is a rectangle in a medium's grid: `x`, `y`, `width`, `height`, a
  `resolution` that names the grid, `local()`, `contains()`, and the medium's
  views.
  - On the screen the grid is cells, as today: `region.cells`,
    `region.half_blocks`, `region.braille`.
  - On the timeline the grid is **beats by semitones**, a piano roll: `x` is the
    beat the sound starts on, `width` how many beats it lasts, `y` the lowest
    pitch as a MIDI number, `height` how many semitones it spans (a chord spans
    several, a drum one). Its finer views are `region.beats`, `region.ticks`
    (sixteenths) and `region.milliseconds` (through the tempo map).
- `Note.region`, `Melody.region` and `Sound.region` (a sound spans its length
  and the pitch row it is played at) give the timeline region of a playable;
  `placement.region` and `canvas.region` give the screen region of a renderable,
  as today.
- **`context.region`** is the dynamic one: for a hook on a renderable it is the
  buffer's screen region; for a hook or component on a playable it is the
  timeline region of what is playing. `context.size` becomes
  `context.region.size` (kept as a shortcut).
- Implementation: `region.py` keeps one `Region` class whose `_source` is either
  a buffer view (today's code) or a timeline span; the three screen views and
  the three timeline views are properties that raise a `TerminalError`
  (`'canvas.state'`) naming the other medium when read on the wrong kind. No
  second class, no `AudioRegion`.
- Decision D7 asks whether this lands with the audio package or as a phase of
  its own.

### `xnano.appearance`

`appearance.py`, `_appearance.py` and `_decoration.py` are one topic split by
visibility. They become the `appearance/` package: `__init__.py` with today's
public classes, `_look.py` (the `Appearance` dataclass, spacing, border kinds,
the modifier keyword mapping), `_decoration.py` (unchanged) and `_owners.py`
(the `_Looked` and `_TextModifiers` mixins that `Canvas`, `Placement` and
`Region` inherit).

### `xnano._schema`, `xnano._internal`, `xnano._runtime`

- `_schema/` holds every TypedDict, Literal and TypeAlias with no behavior,
  split by topic as the tree shows. `xnano/types.py` becomes the public index
  that lazily re-exports them (today it already re-exports from `_values`,
  `_customize`, `_appearance`, `_hooks` and `_effect_controller`). Nothing
  imports `_schema` except `types.py` and the modules that define behavior for
  those types.
  An alias made from runtime classes stays next to those classes: `_schema`
  never imports a class that has behavior. `RenderableEffect`, `PlayableEffect`
  and `EffectSpecification` are unions of the effect parameter dataclasses, so
  they live in `effects/_properties.py` beside those dataclasses, while the
  unions of the TypedDicts live in `_schema/_effects.py`.
- `_internal/` holds the three small helpers that several public modules share
  and that belong to no one topic: sealed attributes, axis conversion and
  validation, and the optional-extra loader.
- `_runtime/` holds the loop (`_host.py`) and the slot machinery that the
  `layout` setting added to `canvas.py` (`_open_slot`, `_close_slot`,
  `_mark_layout_pending`, `_apply_pending_layouts`, `_apply_layout`,
  `_slot_rule`). `Canvas` keeps the public `layout` and `edges` properties and
  calls into it.

### Thin re-export modules

`styles.py`, `geometry.py`, `events.py`, `buffers.py`, `widgets.py` and the core
half of `operations.py` switch to the lazy pattern of `expressions.py`, each
name with its own docstring and example. Two renames come with it:

- `xnano.widgets.Canvas` (ratatui's shape-drawing widget) is renamed
  **`Figure`**, with `FigureCircle`, `FigureLine`, `FigureMap`, `FigurePoints`,
  `FigureRectangle` and `FigureLabel`, so that `Canvas` means one thing in
  `xnano`.
- `BufferSize` is an expression, so it lives only in `xnano.expressions`.
  `xnano.buffers` re-exports only `Buffer` and `Cell`.

### The top level

`xnano/__init__.py` exports: `new`, `open`, `active`, `iter`, `Canvas`,
`Terminal`, `Context`, `Color`, `hook`, `effect`, `write`, `box`, `draw`,
`Pixel`, `Image`, `load_image`, `Sound`, `load_sound`, `Note`, `note`, `play`,
`renderable`, `playable` and the `symbols` module. Compared with today: `Audio`
becomes `Sound`, `from_image` and `from_audio` become `load_image` and
`load_sound`, and `effect` is added.

## Name changes

| Today | After | Why |
| --- | --- | --- |
| `xnano.operations.fx()` | `xnano.effects.effect()` | Builds effects only; full word |
| `Customization` | `EffectParameters` | Says what it holds |
| `XxxCustomization` | `XxxEffectParameters` | Same |
| `XxxEffectArguments` (TypedDict) | `XxxEffectParametersSchema` | The schema of the parameters |
| `RenderableEffects`, `PlayableEffects` | `RenderableEffectProperties`, `PlayableEffectProperties` | As the note asks |
| `EffectCustomization` | `EffectSpecification` | A spec, not a customization |
| `FillCustomization` ... `RasterCustomization` | `operations.DynamicFill` ... `DynamicRaster` | Not effects |
| `xnano.Audio`, `from_audio` | `xnano.Sound`, `load_sound` | "Audio" is the medium, a sound is the value |
| `from_image` | `load_image` | A verb that says it reads a file |
| `xnano.music.*` | `xnano.audio.*` | One home for what is heard |
| `xnano.image.TerminalImage` | `Image.decoded` (no public name) | Upstream class behind the `xnano` one |
| `xnano.image.TerminalGraphics` | `xnano.terminal.capabilities().graphics` | A device capability |
| `GateSettings` | `TerminalSettings` | What the terminal is asked for |
| `DeviceWidth`, `DeviceHeight` | `TerminalWidth`, `TerminalHeight` | Terminal, not device, at the `xnano` level |
| `widgets.Canvas` and `CanvasXxx` | `widgets.Figure` and `FigureXxx` | `Canvas` means one thing |
| `context.size` | `context.region.size` (shortcut kept) | One region concept |
| `_when` | `hooks._triggers` | As the note asks |
| `HookGenerator` | `HookResult` | What a hook returns (maintainer decision) |

Core, audio and image package names (`xnano_core.Device`,
`xnano_audio.TerminalSound`, `xnano_image.TerminalImage`, ...) do not change;
the plan is entirely in `xnano/`.

## Decisions for the maintainer

- **D1 `Parameters` or `Params`.** The note in `effects/_properties.py` writes
  `EffectParams` and `EffectParamsSchema`; `CLAUDE.md` names `Parameters` as the
  required spelling and says no short form is added without a maintainer
  decision. This plan uses `EffectParameters` and `EffectParametersSchema`.
  Choosing `Params` means adding it to the accepted list in `CLAUDE.md`.
- **D2 The builder's name.** `effect()` as proposed, or keep `fx()` as a module
  function too. The `.fx` attributes stay either way.
- **D3 Non-effect customizations.** `DynamicFill` and friends in `operations`,
  as proposed, or keep them reachable from `effect()` under their old kind
  strings.
- **D4 `xnano.music`.** Fold into `xnano.audio` as proposed, or keep `music` as
  the composition side (`Note`, `Melody`, `note`) with `audio` as playback.
- **D5 `AudioDevice`.** Keep the name (proposed), or rename to avoid the word
  "device" everywhere: `Speaker`, `Player` or `Audio` (the last one is free once
  the value class is `Sound`).
- **D6 `hooks/_handles.py`.** Move `_hooks.py` into the package (proposed), or
  leave the handle machinery under `_internal/`.
- **D7 `Region` for audio.** Land it with the audio package, or as its own phase
  after the moves; and whether `context.size` keeps working as a shortcut.
- **D8 `canvas.py`.** Keep it one script after the terminal and runtime code
  leaves (roughly 3,500 lines), or split it into a `canvas/` package in a later
  phase.
- **D9 `widgets.Canvas`.** `Figure` as proposed, or another word.

## Phases

Each phase is one pull request on `v2`, passes `make format-all`, `make check`
and `make test`, and regenerates the API reference (`uv run python
scripts/docs/autogenerate_api_references.py`, which already turns a package into
a page and skips private modules). The order keeps every intermediate state
importable.

1. **Unblock.** Delete `xnano/effects.py` (moving its six names to
   `operations`), point `scripts/capture_examples.py` and `tests/test_canvas.py`
   away from the deleted `examples/`, and add a test that no `xnano/_*.py`
   script exists (it fails until phase 7 and documents the goal).
2. **`_schema`, `_internal`, `_runtime`.** Move `_values.py`, the TypedDicts of
   `_customize.py` and `_appearance.py`, `_attributes.py`, `_axes.py`,
   `_optional.py` and `_host.py`. Pure moves plus import rewrites; `types.py`
   re-exports from `_schema`.
3. **`hooks`.** `hook()`, `_hooks.py` and `_when.py` move in; `test_when.py` is
   renamed.
   A repair step (3.1) follows it: the hook aliases keep their runtime type
   parameters, and `HookGenerator` is renamed `HookResult`.
4. **`effects`.** The rename and split of `_customize.py` and
   `_effect_controller.py`; `effect()` replaces `fx()`; the six dynamic
   operations move to `operations`; `test_fx.py` is renamed.
5. **`terminal`.** The package, the gate machinery out of `canvas.py`,
   `TerminalSettings`, `capabilities()`, `TerminalWidth`/`TerminalHeight`, and
   the deletion of `image.py`'s graphics half.
6. **`art` and `audio`.** The two packages, `Sound`/`load_sound`/`load_image`,
   `Melody`, `Microphone`, the deletion of `image.py` and `music.py`, and the
   split of `_media.py` and `test_media.py`.
7. **`appearance`** becomes a package; the no-private-scripts test from phase 1
   passes.
8. **`Region` across media** and `context.region`.
9. **Lazy re-exports and widget renames.** `styles`, `geometry`, `events`,
   `buffers`, `widgets`, `operations`; `Figure`.
10. **Docs.** `docs/learn/index.md` ("Where everything lives"), `docs/index.md`,
    the README and the `Maps to` lines are brought in line with the final
    layout; the demo is updated to the new names.
    The README gets a dedicated step: the supported platforms from the wheel
    build matrix in place of the `@TODO`, a Quick Start of short runnable
    examples for the main concepts in the final API, `scripts/readme_images.py`
    photographing them, and the strict README check in
    `tests/test_readme_examples.py` restored. The sdist excludes `docs/`, so
    no README picture ships in a package.

11. **`box`** (maintainer request). `xnano.box` draws no border unless asked
    (`border='plain'`, `True` or another kind), and its `width` and `height`
    take the same values as every other size: cells, percentages and
    formulas. A relative box is measured where it is written and refits when
    its parent resizes; before that, in the active canvas or the window.
12. **`Output` conveniences** (maintainer request). `canvas.output` exposes
    the last drawn frame directly: `text`, `ansi`, `size`, `revision`,
    `cursor_position`, `is_cursor_visible`, `lines()` and `to_cell_grid()`,
    with the meanings of `xnano_core.FrameSnapshot`.

## What this touches outside `xnano/`

- `tests/test_terminal_api.py` asserts the structure (`xnano._hooks.HookHandle`,
  `xnano._effect_controller.EffectController`, the top-level `__all__`, the
  removed-modules check); it is updated in each phase.
- `zensical.toml` navigation is regenerated by the API reference script.
- `scripts/capture_examples.py` is retired or repointed (phase 1).
- The `packages/` stubs do not change. Where a `Maps to` line in `xnano` names
  an upstream class, it keeps naming it.

## Out of scope

- Splitting `canvas.py` and `placement.py` further (D8).
- Any change to the Rust crates or to `xnano_core`'s public surface.
- Compatibility aliases for the old names: 2.0.0 has not shipped.
