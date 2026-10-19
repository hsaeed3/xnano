# History

Release notes of every xnano package, newest first. This file is generated from the GitHub releases by `scripts/history.py` (run `make history`); do not edit it by hand.

## xnano

### 2.0.0

Published 2026-10-19. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v2.0.0).

#### xnano 2.0.0

xnano 2.0 is a ground-up rewrite of xnano. It shares the name, the goal (fun, fast terminal applications in Python) and the Rust foundations (`ratatui` and `tachyonfx`) with 1.2.3, and almost nothing else: the programming model, the package layout, the runtime and every public name are new. These notes describe the whole 2.0 API as it stands, set against what 1.2.3 offered. Code written for 1.2.3 does not run on 2.0, and the 1.2 documentation stays available on the [`v1` branch](https://github.com/hsaeed3/xnano/tree/v1) and under "Legacy v1" on the documentation site.

```sh
pip install xnano               # the terminal, widgets, effects, art and formulas
pip install "xnano[audio]"      # notes, melodies, sounds and the microphone
pip install "xnano[image]"      # PNG, JPEG, GIF, WebP and XNI images
pip install "xnano[monty]"      # running untrusted Python against a canvas
```

##### At a glance

In 1.2.3 an application was a class: a `BaseGrid` subclass that declared `Field` slots, decorated its methods with `@on_keyboard`, `@on_tick` and the other hooks, and was handed to `Terminal().run(...)`. In 2.0 an application is a canvas you write to. Writing returns a placement you can keep changing, and hooks are plain functions attached to whatever they belong to.

```python
import dataclasses

import xnano


@dataclasses.dataclass
class Counter:
    count: int = 0


with xnano.open(width=30, height=3, state=Counter()) as terminal:
    label = terminal.write('Count: 0', x='center', border='rounded')

    @terminal.hook(on='key', keys='up')
    def increment(context: xnano.Context) -> None:
        terminal.state.count += 1
        label.text = f'Count: {terminal.state.count}'

    terminal.run(quit_on='q')
```

| | 1.2.3 | 2.0.0 |
| --- | --- | --- |
| An application | a `BaseGrid` subclass with `Field` slots | a canvas from `xnano.open()` or `xnano.new()` that you `write()` to |
| Content on screen | a field value, re-rendered when assigned | a `Placement` returned by `write()`, changed through its properties |
| Layout | grid `direction`, `gap`, field `width`/`height` | `x`, `y`, `width`, `height` per placement (cells, percentages, words, formulas or ranges), `layer`, and `layout='column'`/`'row'` on a canvas |
| Behavior | twelve `@on_*` method decorators | one `hook(on=...)` for every kind of input, timer, beat and state change |
| Moving things | changing fields from hooks | formulas from `xnano.expressions` that are evaluated again on every frame |
| Effects | `grid_effect(...)` with effect classes | `xnano.effect(...)` values that are applied, edited live and cancelled |
| Media | an `Image` component (with Pillow) | pixel art, images, notes, melodies, sounds and a microphone |
| Testing | `Terminal.offscreen(...)` | `xnano.new()`: an offscreen canvas with a manual clock that you step, feed events to and read back |
| Errors | `XnanoError`, `ValidationError`, `HookError` | `TerminalError`, with a code and a labelled report for every failure |
| Python | 3.10 to 3.13 | 3.10 to 3.14 |

##### Canvases and terminals

A **canvas** is a rectangle of cells with its own clock, input, state and content. There are two ways to get one.

- **`xnano.open(content=None, *, title=None, width=None, height=None, fps=60.0, bpm=120.0, effects=(), deps=..., state=..., **settings)`** puts a `Terminal` on the screen. Without sizes it takes the whole window on the alternate screen; with a `height` (and optionally a `width`) it draws in a region below the cursor, which is erased when it closes unless `clear=False`. Sizes are cells or percentages such as `'50%'`. One terminal is open at a time; opening a second raises `TerminalAlreadyOpenError`.
- **`xnano.new(content=None, *, width=None, height=None, fps=None, bpm=None, realtime=False, ...)`** makes an offscreen `Canvas` (80 by 24 cells unless sized). Its clock is manual by default, so time moves only when you call `canvas.step()` or iterate `canvas.iter(count=..., seconds=...)`, and every run is repeatable. `realtime=True` runs it on the wall clock instead. `canvas.render()` returns what it shows as text (or ANSI with `format='ansi'`), and `canvas.open()` puts it on the screen with its time continuing.

`Terminal` is a `Canvas`, so everything below works on both. A terminal also has `capabilities`, `window` and `settings`, runs on its own thread, and shows writes immediately. `terminal.run(quit_on='q')` blocks until one of the quit keys is pressed (it takes a key, a sequence of keys or `None`); `quit()`, `stop()`, `resume()`, `close()`, `wait_for_key(*keys)` and `prompt(text, default='')` cover the rest of a terminal's life. Both are context managers that close on exit.

**Settings** are keywords on `open` and `new`: `mouse` (`True` or `'motion'`), `scroll`, `keyboard` (`True`, `'disambiguated'`, `'release_events'` or `False`), `paste`, `focus`, `interrupt` (Ctrl-C), `capture` (holding back printed text), `clear` and `alternate_screen`. A hook that needs mouse, scroll or paste input turns that input on by itself; a setting you set to `False` stays off, and the hook raises an error that names it.

**Nested canvases.** A canvas made with `new()` inside another canvas's `with` block belongs to it: it shares the outer clock and input, measures percentages against the outer canvas, and appears where you write it (`outer.write(inner, x=..., y=...)`). `canvas.new(...)` makes a child that is drawn at once. `xnano.active()` returns the innermost running canvas, and `xnano.iter(...)` steps it.

**Frame rate and tempo.** `canvas.fps` (the most frames drawn per second, and the step length of `iter()`) and `canvas.bpm` can be changed while the canvas runs. `canvas.time.fps` is the measured rate.

##### Writing content

`canvas.write(content, /, **options)` draws one piece of content and returns a `Placement`. Content can be a string or a list of lines, a widget, another canvas, an image, pixel art, a standalone region, a component, or nothing at all (an empty, styled box).

**Position and size.** `x`, `y`, `width` and `height` each take:

- a number of cells;
- a percentage of the parent, such as `'50%'`;
- a word: `'left'`, `'center'` or `'right'` for `x`, and `'top'`, `'center'` or `'bottom'` for `y`;
- a formula from `xnano.expressions`, evaluated again on every frame;
- a range `(low, high)`, which limits how far a position may travel or how small and large a size may get. Each end is any of the values above, or `None` for no limit.

`layer` sets the drawing order, and `lock=True` freezes the current position and size so later resizes leave it alone.

**Layout.** By default the content of a canvas overlaps freely (`layout='overlay'`). `layout='column'` stacks each write below the previous one, and `layout='row'` places them side by side. `edges` decides what content does at the canvas's edges: `'clip'` cuts it off (the default), `'stop'` keeps it inside, and `'wrap'` brings it back on the other side. Each write can override the canvas's `edges`.

**Placements.** A placement keeps working after it is drawn. Assigning `x`, `y`, `width`, `height`, `layer`, `is_visible`, `edges`, `text` or `style` redraws it; `move()`, `up()`, `down()`, `left()` and `right()` move it; `remove()` takes it away. `placement.write(...)` writes inside it, `placement.hook(...)` attaches a hook to it, and `placement.update(*operations)` (or `placement | operation`) applies operations such as effects.

##### Appearance

The look of text is set with keywords on `write`, `new` and `open`:

- **Colors:** `foreground` and `background`. A color is a name (`'red'`, `'light_blue'`, `'reset'`), a hex string (`'#ff8800'`), a palette index or an `(r, g, b)` tuple.
- **Text modifiers:** `bold`, `dim`, `italic`, `underline`, `blink`, `reverse`, `hidden` and `crossed_out`.
- **Box:** `border` (`'plain'`, `'rounded'`, `'double'`, `'thick'`, `True` or `False`), `border_style`, `title`, `padding` and `margin`. A spacing is a number of cells, a share of the content's size (`0.1` or `'10%'`), or a dictionary with `top`, `right`, `bottom`, `left`, `vertical` and `horizontal`. Padding alone draws the content in a box without a border.

Every canvas, placement and standalone region exposes the same settings as live properties: `.color.fg` and `.color.bg`, `.border`, `.padding`, `.margin` and the text modifiers. Assignments made together are drawn in one redraw.

`xnano.Color` parses and converts colors (`parse`, `from_rgb`, `from_hsl`, `from_hsv`, `from_tailwind`, `indexed`, `to_rgb`, `to_hex`, `to_hsl`, `to_hsv`), mixes them (`lerp`, `lighten`, `darken`, `saturate`, `inverse`), and picks them: `Color.random()` returns any color, and `Color.random(base='blue')` keeps the base's hue and saturation with a random lightness.

##### Formulas

`xnano.expressions` holds values that are evaluated again on every frame, such as `TimeElapsed`, `ParentWidth`, `Width`, `MousePosition`, `KeyboardKey` or `ScrollY`. They support Python arithmetic, and comparing them builds a condition. A formula can be used anywhere a number is accepted: positions, sizes, widget values and effect parameters.

```python
import xnano
from xnano.expressions import ParentWidth, TimeElapsed, Width

with xnano.open(width=40, height=3) as terminal:
    ball = terminal.write('●', y=1)
    ball.x = (ParentWidth - Width) * (TimeElapsed % 2 / 2)
    terminal.run(quit_on='q')
```

The names cover the placement's own geometry (`Width`, `Height`, `X`, `Y`, `Size`, `Position`), its parent and the screen (`ParentWidth`, `ParentHeight`, `ParentSize`, `TerminalWidth`, `TerminalHeight`, `ScreenBounds`), time (`TimeElapsed`, `TimeDelta`, `FPS` and their millisecond forms), the keyboard, mouse and scroll wheel, focus and visibility. `canvas.time / 2` and `canvas.audio.beat` are formulas too, and `canvas.inspect(formula)` reads a formula's current value.

##### Hooks

One function, `hook`, replaces 1.2.3's twelve `@on_*` decorators. `canvas.hook(...)` and `placement.hook(...)` attach a hook right away (also as a decorator) and return a `HookHandle` with `remove()`; `xnano.hook(...)` describes a hook once so it can be applied to several targets.

- **`on`** names what the hook hears: `'frame'`, `'tick'`, `'beat'`, `'key'`, `'mouse'`, `'scroll'`, `'drag'`, `'paste'`, `'focus'`, `'resize'`, `'state'` or `'custom'`. A hook without `on` hears every input event.
- **`keys`** narrows a key hook to key names and chords such as `'q'`, `'space'`, `'up'` or `'ctrl+s'`.
- **`every` and `after`** repeat or delay a hook, in seconds for `'tick'` and in beats for `'beat'`.
- **`when`** is a condition: a formula, a function of the context, or a string such as `"keyboard.key == 'q' and not mouse.is_down"`, which is parsed once.

A hook takes a `Context` or nothing. The context carries the event and the input that came with it (`keyboard`, `mouse`, `scroll`, `clipboard`), the target and its tree (`buffer`, `parent`, `root`), and the canvas's services (`time`, `audio`, `cursor`, `fx`, `region`, `size`, `state`, `deps`). A hook may return an operation, a style or an effect, which is applied to its target. A hook written as a generator (`HookResult`) follows an interaction over several events, such as a drag: `context = yield` waits for the next one.

Pointer hooks on a placement hear only the pointer inside it, so a placement handles its own clicks and drags.

##### State

`state=` on `open` or `new` takes a dataclass instance. Its fields become typed attributes of `canvas.state`; writes are checked against the field types, and `get(path)` and `push(path, value)` reach nested values by dotted path. Placements have their own `placement.state`, and each hook gets its own branch as `context.plugin.state`. A hook with `on='state'` runs again when a value it read changes, and the values a hook pushes are saved together when it returns. `deps=` carries anything else a hook needs, such as a database client, as `context.deps`.

##### Components

`@xnano.renderable` and `@xnano.playable` turn a function of `(context, **parameters)` into a component. Write a renderable component with `canvas.write(component(...))` and play a playable one with `canvas.play(...)`. A component runs again only when something it read has changed: the time, an event, its size, a state path or the input.

##### Effects

`xnano.effect(kind, **parameters)` builds an effect: a typed, editable value that is applied to a placement or canvas with `update`, with `|`, by returning it from a hook, or through `effects=[...]` on `write`, `new`, `open` and `draw`. Changing one of its fields while it runs changes the running effect, and `cancel()` stops it.

```python
title = terminal.write('xnano', x='center', y='center', border='rounded')
title.update(xnano.effect('effect.fade_from', foreground='black', duration_milliseconds=1500))
```

- **Visual effects:** `fade_to`, `fade_from`, `paint`, `saturate`, `lighten`, `darken`, `sweep_in`, `sweep_out`, `slide_in`, `slide_out`, `hsl_shift`, `dissolve`, `coalesce`, `glitch`, `sleep`, `evolve`, `evolve_into`, `evolve_from`, `expand`, `stretch` and `explode`, each as `'effect.<name>'`.
- **Audio effects:** `bit_crush`, `distortion`, `low_pass`, `high_pass`, `delay`, `reverb` and `tremolo`, each as `'audio.<name>'`.

Each kind has a parameters class in `xnano.effects` (`FadeToEffectParameters`, `ReverbAudioEffectParameters`, ...), and parameters such as colors, durations and an `interpolation` (`'linear'`, `'bounce_out'`, `'elastic_in_out'` and 31 more) accept formulas. The same effects are methods of `placement.fx`, `canvas.fx` and `canvas.audio.fx` (`placement.fx.fade_to(...)`), and `context.fx` starts effects that last as long as the hook.

##### Art and images

- **`xnano.draw(source, palette)`** paints pixel art from rows of characters and a palette such as `'R=#e03040 G=green'`; unmapped characters are transparent and a pixel is half a cell tall. The result, `Art`, is a value you write. Art can also be a world that holds other art, with a `Camera` that follows a target, and solid cells for collisions.
- **`Pixel`** is one cell or dot, from a character or one of 28 presets (`'block'`, `'shade_medium'`, `'braille'`, `'star'`, ...). `region[x, y]` reads and writes them.
- **`xnano.load_image(source, **options)`** loads a PNG, JPEG, GIF, WebP or XNI image as an `Image` that is written like any other content. `fit` is `'contain'`, `'cover'`, `'stretch'`, `'crop'` or `'smart'`, and animated images play on the canvas's clock. Images need the `image` extra.

##### Sound

With the `audio` extra, a canvas plays music on its own clock:

- **`Note(pitch, beats=1.0, instrument='piano', velocity=0.8)`** (or `xnano.note(...)`) is a note, a MIDI number or a chord. Creating notes needs no extra.
- **`Melody(text)`** reads a score such as `'C4 E4 G4:2 rest C5+E5+G5'`: `:n` sets beats, `+` builds a chord, `rest` or `-` is silence and `|` is a bar line.
- **`xnano.load_sound(source)`** (or `Sound(source)`) loads a WAV, MP3, FLAC, Ogg Vorbis or MP4/AAC file, from its path or its bytes, as a `Sound`.
- **`canvas.play(playable, **options)`** (or `xnano.play(...)`) plays any of them, a string, or a sequence, with `instrument`, `velocity`, `effects`, `volume`, `pan`, `at_beat` and `beats`. It returns a `PlayHandle`.
- **`canvas.audio`** reports `is_available`, follows the `beat`, and gives the `microphone` and its `level`. On an offscreen canvas with a manual clock, everything played is recorded, and `canvas.audio.render_sound()` renders it exactly.

##### Regions

A `Region` is a rectangle of a medium. On the screen it is measured in cells (with `half_blocks` and `braille` views for finer pixels); on the timeline it is measured in beats by semitones (with `ticks` and `milliseconds` views). Placements, canvases, notes, melodies and sounds all have a `region`, and `context.region` is the region of whatever a hook belongs to. `xnano.write(content, **options)` and `xnano.box(width, height, **appearance)` build standalone regions that are written later. `write` takes anything `canvas.write` shows (text, widgets, images, pixel art, components) with the same size and look keywords, and draws it as the active canvas sees it at that moment, or against the terminal window when no canvas is running. `box` takes no border unless given one, and its sizes can be relative and are measured again where the box is written.

##### Widgets

`xnano.widgets` holds the `ratatui` widgets: `Paragraph`, `Block`, `Gauge`, `LineGauge`, `Table`, `Tabs`, `ItemList`, `Scrollbar`, `Sparkline`, `BarChart`, `Chart`, `Calendar` and `Figure` (a drawing surface with lines, circles, rectangles, points, labels and maps). Their numbers and text accept formulas, so a gauge can follow a value without a hook.

##### Input, events and output

- **Input:** `canvas.input` reports held keys (`is_down(*keys)`), arrow-key `axis` and `direction()`, and the pointer. Release events are exact with `keyboard='release_events'` on terminals that support them.
- **Events:** `xnano.events.Event` builds key, mouse, paste, resize and custom events. `canvas.push(event)` followed by `canvas.deliver_events()` feeds them to an offscreen canvas, so hooks can be tested without a terminal.
- **Cursor:** `canvas.cursor` moves, shows, hides and follows a placement.
- **Output:** `canvas.output` reads the last drawn frame as `text` or `ansi`, with its `size`, the cursor, `lines()`, `snapshot()` and `to_cell_grid()`, without drawing a new one.
- **Time:** `canvas.time` gives `elapsed`, `delta`, `frame` and `fps`, can `stop()` and `resume()`, and freezes animations, effects, timers and the beat while input keeps arriving.

##### Errors

Every error xnano raises is a `TerminalError` with a `code` and a report in the style of a pydantic validation error: the number of problems, where each one happened, the message, the value that caused it and a hint for fixing it.

```text
1 error in canvas.write()
write.height
  height must be at most 65535 cells. [code=validation.bounds, input_value=70000, input_type=int]
    Pass a smaller height.
```

The codes are `validation.type`, `validation.value`, `validation.bounds`, `validation.keyword`, `canvas.closed`, `canvas.state`, `canvas.composition`, `canvas.thread`, `canvas.timeout`, `canvas.callback`, `screen.already_open` and `screen.unavailable`. Validation errors are also the matching `TypeError` or `ValueError`, so `except ValueError` keeps working, and `TerminalClosedError` and `TerminalAlreadyOpenError` name the two most common failures. An uncaught `TerminalError` is printed in color in a terminal, following `NO_COLOR` and `FORCE_COLOR`.

##### Readable values

Values print as the Python that builds them: `Note(pitch='C#4', beats=2, ...)`, `Color('#0000d4')`, operations, effects, formulas and regions all have readable `repr`s, and value types compare and hash by value.

##### Sandboxed Python

With the `monty` extra, `xnano.monty` runs untrusted or model-written Python in a [Monty](https://github.com/pydantic/monty) sandbox against a real canvas. `xnano.monty.run(code, canvas)` runs one program, and `xnano.monty.Sandbox(canvas)` keeps a session open across programs. Inside the sandbox, code writes, moves, styles and removes text, draws pixel art, steps an offscreen canvas and plays notes through a small typed API (`xnano.monty.SANDBOX_STUBS`), and every program is type-checked before it runs, within time and memory limits.

##### Packages and platforms

xnano is now a family of packages:

- **`xnano`** is the Python API described above. It depends only on `xnano-core`.
- **`xnano-core`** is the Rust engine under it, built on `ratatui`, `tachyonfx`, `crossterm` and `termprofile`.
- **`xnano-audio`** (the `audio` extra) synthesizes and plays notes, melodies and sounds, and reads the microphone.
- **`xnano-image`** (the `image` extra) decodes and draws images with `ratatui-image`.
- **`pydantic-monty`** (the `monty` extra) is the sandbox behind `xnano.monty`.

A feature whose extra is missing raises an error that names the extra to install. `python -m xnano` (or the `xnano` command) runs a demo of most of the library. Wheels are built for Linux (x86_64 and aarch64, glibc and musl), macOS (Intel and Apple silicon) and Windows (x86_64), one abi3 wheel per platform for Python 3.10 and later.

##### Not part of 2.0

These 1.2.3 features have no counterpart in 2.0:

- the `Web` host, which served a grid in a browser, and the experimental HTTP request hooks and `RequestServer`;
- the experimental `Command` command line framework;
- the Markdown runner (`xnano file.md`) and the `Markdown` component;
- the form components (`Input`, `Button`, `Dropdown`, `Select`, `Link`) and the `Loader`;
- Tailwind-style `Style` classes and Tailwind color strings such as `'violet-500'` (`Color.from_tailwind('violet', 500)` builds the same color);
- the `pydantic-core`, `markdown-it-py`, `pygments` and Pillow dependencies.

### 2.0.0-beta.3 (pre-release)

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v2.0.0-beta.3).

##### xnano 2.0.0-beta.3

A breaking ergonomics release of the v2 beta. It requires `xnano-core>=2.0.0b3`; `xnano-audio` and `xnano-image` (0.2.0) are unchanged. Pull request: #174.

###### Migration

| Before | Now |
| --- | --- |
| `xnano.img(path, ...)`, `Terminal.img(...)`, `ImageBuffer` | `xnano.Image(path, ...)`, shown with `terminal.write(image)` |
| `xnano.audio.Audio` (what `terminal.audio` returns) | `xnano.audio.AudioDevice` |
| none | `xnano.Audio(source)`, a sound that `terminal.audio.play(...)` accepts |
| none | `xnano.from_media(path or bytes)`, which returns an `Image` or an `Audio` |
| `terminal.loop.frames(...)` | `terminal.iter(...)` and `xnano.iter(...)` |
| `terminal.clock`, `context.clock`, `context.delta`, `context.elapsed_seconds` | `terminal.time`, `context.time` (a `xnano.time.Time`) |
| `terminal.pause()`, `terminal.resume()`, `terminal.is_paused` | `terminal.time.pause()`, `terminal.time.resume()`, `terminal.time.is_paused` |
| `open(clock='real')`, `open(clock='manual')` | `open(realtime=True)`, and the default |
| `mouse='buttons'`, `mouse='off'` | `mouse=True`, `mouse=False` (`'motion'` is unchanged) |
| `keyboard='basic'` | `keyboard=True` (`'disambiguated'` and `'release_events'` are unchanged; `False` ignores keys) |
| `interrupt='stop'`, `interrupt='event'` | `interrupt=True`, `interrupt=False` |
| none | `paste=` and `focus=` gates on `open` |
| `should_capture_output=` | `capture=` |
| `inline_height=`, `should_clear_on_close=` | `height=` for a region and `clear=` to erase it when the terminal closes |
| `should_use_alternate_screen=` | `alternate_screen=` |
| `fx('style' \| 'border' \| 'block' \| 'padding' \| 'margin' \| 'foreground' \| 'background', ...)` | the parameters of `write` and `new`, and the same names as properties of a placement or canvas |
| `terminal.fx(...)`, `placement.fx(...)`, `canvas.fx(...)` returning the target | they return the customization, which stays attached to the target |
| `terminal.pixels()`, `placement.pixels()`, `pixels(encoding='braille')` | `terminal.pixels`, `placement.pixels`, `pixels.braille` |
| `xnano.shade`, `xnano.draggable` | `xnano.operations.shade`, `xnano.operations.draggable` |

###### New

- **Appearance on `write` and `new`.** `padding` and `margin` join `foreground`, `background`, the text modifiers, `border`, `border_style` and `title`. A spacing is a number of cells, a float or percentage of the text's size (`0.1`, `'10%'`), or a dictionary with `top`, `right`, `bottom`, `left`, `vertical` and `horizontal`. Padding alone draws the text in a box with no border.
- **Appearance you can change afterwards.** On a text placement or a canvas made from a string, assigning `foreground`, `background`, any text modifier, `border`, `border_style`, `title`, `padding` or `margin` draws it again and resizes it to fit. `label.text = ...` keeps the look. A placement that does not show text raises a `TypeError` that says so.
- **`fx` returns a live handle.** `effect = placement.fx('effect.dissolve', ...)` returns the customization. Assigning one of its fields applies it again; a running effect is stopped and started again with the new values. On a canvas, edits before `build()` are picked up and edits afterwards change the built buffer. `fx` keeps `fill`, `write`, `layout`, `fuzz`, `pixels`, `raster`, and the `effect.*` and `audio.*` kinds.
- **`xnano.time.Time`** (`terminal.time`, `context.time`): `elapsed`, `elapsed_milliseconds`, `delta`, `frame`, `fps`, `is_paused`, `is_realtime`, `pause()`, `resume()`, and `seconds` and `milliseconds` as formulas. Used in arithmetic it is the formula for `seconds`, so `terminal.time / 2` follows the clock inside a formula. Inside a hook, read `context.time.elapsed` for the number.
- **`xnano.Image(source, ...)`** takes the path of an image file, its bytes or a `TerminalImage`, with the placement options that `xnano.img` had.
- **`xnano.Audio(source)` and `xnano.from_media(source)`.** `Audio` reads the path or bytes of a PCM WAV file, or takes a `TerminalSound`. `from_media` reads the extension, or the first bytes, and returns an `Image` or an `Audio`. Other sound formats raise a `ValueError` that says what is accepted.
- **Frames.** `terminal.iter(count=, duration_seconds=)` and `xnano.iter(...)`, which follows the active terminal, yield one `Frame` per tick.
- **Pixels.** `pixels[0:10, 2] = color` draws a block of pixels, `pixels[:, :] = color` fills all of them, and a `Color` object is a valid pixel color. `terminal.pixels.braille` gives the braille view.
- **`xnano.Color`** is exported. See the `xnano-core` notes for what `Color` gained.
- **Top-level names:** `Audio`, `Canvas`, `Color`, `Image`, `Terminal`, `active`, `from_media`, `fx`, `hook`, `iter`, `make`, `new` and `open`. `Spacing` and `SpacingDictionary` are in `xnano.types`.
- **`HISTORY.md` and `make history`** build the release history from the GitHub release notes with `scripts/history.py`.

###### Changed

- The input gates on `open` are booleans: `mouse`, `keyboard`, `paste`, `focus`, `interrupt` and `capture`. `clear` and `alternate_screen` replace the region and screen options, and `realtime` replaces the clock option for an offscreen terminal.
- The README note describes v2 as a beta.

###### Removed

- `xnano.img`, `Terminal.img` and `ImageBuffer`.
- `terminal.clock`, `context.clock`, `context.delta`, `context.elapsed_seconds`, `Terminal.pause`, `Terminal.resume` and `Terminal.is_paused`.
- The appearance kinds of `fx` (see the migration table).
- `shade` and `draggable` from the top level; they remain in `xnano.operations`.

###### Known gaps

- `lock` (keeping the terminal's size when the window is resized) is not an `open` option yet, and there is no separate clipboard gate beyond `paste`.
- `xnano.datetime` does not exist.
- `Audio` and `from_media` read PCM WAV files only.
- `make version-check` reports the v1 install pin (`xnano>=1.2.3,<2`) in `README.md` and `docs/`. The pin is intentional, and the check already reported it before this release.

### 2.0.0-beta.2 (pre-release)

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v2.0.0-beta.2).

### 2.0.0-beta.1 (pre-release)

Published 2026-10-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v2.0.0-beta.1).

### 1.2.3

Published 2026-08-05. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.3).

#### xnano v1.2.3

`v1.2.3` is the stable release of the 1.2.3 prerelease cycle. It brings the
ergonomics work from b1/b2 together with a clearer public API, vertical
alignment, non-blocking grid effects, a complete documentation refresh, and
faster construction of the small content values used throughout rendering.

##### Highlights

- **Grid effects are non-blocking and consistently named.** Use
  `self.grid_effect(...)` to start an effect and keep hooks, ticks, and
  rendering moving. The previous `grid_play_effect(...)` remains available as
  a deprecated alias. Effects are now covered end-to-end: tests verify that
  they paint, advance across frames, complete, cancel, and work from the
  supported hook paths. (#135)
- **Two-axis alignment.** `horizontal_align` replaces `align` for horizontal
  placement, and the new `vertical_align` supports `"top"`, `"middle"`, and
  `"bottom"` placement within a field. The old `align` spelling still works as
  a deprecated alias. The same explicit names are used by `Field`, `Text`,
  `TextBlock`, table columns, `Terminal`, and `render()`. (#139)
- **Clearer foreground naming.** APIs where `color` means a text/content
  foreground now expose `foreground`; `color` remains a deprecated,
  compatibility-preserving alias. Specific colors such as `border_color` and
  effect colors deliberately retain their existing names. (#136)
- **A current, runnable documentation site.** The Core Concepts section now
  covers the stable 1.2 API across grids, fields, state, actions, events,
  components, effects, terminal, web, requests, device controls, Markdown,
  and CLI. Runnable Pyodide examples are tested across all documentation pages,
  replacing the stale test that targeted the removed sandbox page. (#138)

##### Migration guide

###### Effects: `grid_effect()` is the canonical non-blocking API

```python
#### before (still works, deprecated)
self.grid_play_effect("fade", duration_ms=300, fields=["body"])

#### after
self.grid_effect("fade", duration_ms=300, fields=["body"])
self.status = "Animation started"  # runs immediately; hooks do not block
```

Use a handle when the calling scope owns the animation lifetime:

```python
with self.grid_effect("coalesce", duration_ms=450, fields=["body"]):
    self.status = "Animating"
```

###### Foreground and alignment names

```python
from xnano import BaseGrid, Field
from xnano.components.text import Text


class Status(BaseGrid):
    # before: color="cyan", align="center"
    label: Text = Field(
        default=Text("Ready", foreground="cyan"),
        horizontal_align="center",
        vertical_align="middle",
        height=5,
    )
```

The same migration applies to `render()`, `Terminal.render()`,
`TextBlock`, `Run`, table `Column`s, and field updates:

```python
#### before: grid_update_field("label", color="green", align="right")
self.grid_update_field(
    "label",
    foreground="green",
    horizontal_align="right",
)
```

`color` remains correct for values that name a specific thing, including
`border_color` and effects such as `FadeEffect(color="violet")`.

###### Grid helper namespace

```python
#### before (still works, deprecated)
self.set_background("slate-950")
self.schedule_update(refresh, field="body")

#### after
self.grid_set_background("slate-950")
self.grid_schedule_update(refresh, field="body")
```

###### Context event payloads

```python
from xnano.hooks import on_keyboard


@on_keyboard("ctrl+s")
def save(self, ctx):
    # before: ctx.keyboard
    if ctx.keyboard_event.matches("ctrl+s"):
        self.save_document()
```

`ctx.keyboard`, `ctx.mouse`, and `ctx.tick` still delegate to
`ctx.keyboard_event`, `ctx.mouse_event`, and `ctx.tick_event`, respectively,
but now emit a `DeprecationWarning`.

##### Grid API cleanup

`BaseGrid` now uses its public namespace consistently. Its supported helpers
are named `grid_*` (for example `grid_set_frame`, `grid_set_background`, and
`grid_schedule_update`), while internal markers use `__xnano_*__` / `_grid_*`.
Grids expose `__xnano_grid__`, allowing framework internals to recognize them
without importing `BaseGrid` and creating a circular dependency. The previous
unprefixed helper names remain deprecated aliases. (#141)

##### Rendering, content, and performance

- `Text` preserves authored indentation after newlines, including when text
  wraps.
- Multiple values passed to `render()` are measured and packed to their
  content, so `gap` is the literal number of cells between renderables rather
  than an accidental viewport-sized separation.
- `SizingLike` now gives editors useful literals for common widths/heights;
  `Sizing.parse("full")` resolves to `100%`.
- Geometry primitives now live in `xnano.area`: `Area`, `Size`, `Padding`,
  `align_area`, and the alignment aliases remain re-exported from
  `xnano.types` for compatibility.
- Hot `Run` and `TextBlock` construction keeps dataclass-generated
  initialization while retaining the deprecated `color`/`align` aliases. This
  removes the generic `*args`/`**kwargs` wrapper from rendering's high-volume
  content path; a local 200,000-`Run` construction check improved from 0.150s
  to 0.134s.

##### Context, state, and hosts

The stable host contract is the b2 contract: `state=` belongs on
`Terminal(...)`, `Terminal.offscreen(...)`, and `Web(...)`, preserving the
natural context-manager form:

```python
with Terminal(state=Notes()) as terminal:
    terminal.run(App())
```

`ctx.tick_event`, `ctx.keyboard_event`, and `ctx.mouse_event` are the
canonical event-payload accessors. The former `ctx.tick`, `ctx.keyboard`, and
`ctx.mouse` accessors remain available as deprecated aliases, so existing apps
continue to run while they migrate. Request dispatch now carries the request
through `Context.request` directly.

##### Skills and packaging

The repository now includes focused development skills for `xnano`,
documentation/examples, and `xnano-core`. The published package also includes
an application-facing `xnano` skill with references for grids, components,
hooks, hosts, and request servers; wheel verification confirms the skill files
ship under `xnano/.agents/skills`.

##### Documentation and migration

Examples, README snippets, generators, and API documentation use the stable
names: `foreground`, `horizontal_align`, `grid_effect`, and the current
`Context` event accessors. Top-level imports in the README reflect the public
`xnano` exports, while library code continues to prefer concrete internal
modules.

##### Deprecations

- `ctx.tick` → `ctx.tick_event`
- `ctx.keyboard` → `ctx.keyboard_event`
- `ctx.mouse` → `ctx.mouse_event`
- `color` → `foreground` where it represents content/text foreground
- `align` → `horizontal_align`
- `grid_play_effect(...)` → `grid_effect(...)`
- Unprefixed `BaseGrid` helpers such as `set_frame`, `set_background`, and
  `schedule_update` → their `grid_*` equivalents

All deprecated aliases continue to work and issue `DeprecationWarning`s; they
are intentionally compatibility bridges, not immediate breaks.

##### Changelog

* docs: rewrite core concepts & finalize docs for xnano 1.2 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/134
* chore: ruff/isort by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/137
* feat: improve grid ergonomics by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/142
* chore: add xnano skills by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/143
* perf: avoid deprecated alias wrapper overhead by @hsaeed3

### 1.2.3b2

Published 2026-07-31. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.3b2).

Adds deprecation to breaking changes for event accessors on `xnano.context.Context`, as well as reverting the `state` constructor change from `1.2.3b1`. The upside to passing `state=` is obvious, as it allows for the usage of the `with Terminal(state=...) as t:` context-manager pattern.

##### Hosts

**`Terminal(state=...)` and `Web(state=...)` are back on the constructor.** `1.2.3b1` moved `state` into `run()`/`render()`, which quietly broke the `with Terminal(state=...) as t:` context-manager pattern — the reason state lived at construction in the first place. Reverted: constructor state is first-class again on `Terminal`, `Terminal.offscreen`, and `Web`, exactly as in `1.2.2`.

##### Context

The event-payload accessor rename from `1.2.3b1` (`ctx.tick`/`keyboard`/`mouse` → `ctx.tick_event`/`keyboard_event`/`mouse_event`, matching `xnano.events.Event`) **stays, but is no longer a hard break.** The old names return as deprecated aliases: they delegate to the new accessors, emit a `DeprecationWarning` at runtime, and — via PEP 702 `@deprecated` — render with a strikethrough in editors. They won't be removed for several versions.

##### Docs

README examples now import everything the top-level `xnano` namespace re-exports (`BaseGrid`, `Field`, `Terminal`, `Context`, the `@on_*` hooks, `render`) straight from `xnano`, leaving `from xnano.components import Text/Component/TextBlock` to stand out as the deliberate special cases they are.

##### Deprecations

- `ctx.tick` → `ctx.tick_event`
- `ctx.keyboard` → `ctx.keyboard_event`
- `ctx.mouse` → `ctx.mouse_event`

Each still works and returns the same payload; migrate at your leisure.

##### Changelog

* release: xnano 1.2.3b2 — revert state move, deprecate event accessors by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/133

### 1.2.3b1

Published 2026-07-31. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.3b1).

#### xnano v1.2.3b1

First prerelease for the `v1.2.3` stable version.  Although this release carries no more than ergonomics upgrades and small bug fixes, it **does** contain 2 breaking changes and will remain as a beta release for the moment.

##### Rendering

- **`Text` keeps indentation after a newline.** Explicit indentation or spaces following a `\n` were dropped for any wrapping `Text` — the wrapping renderer trimmed leading whitespace off every line. Fixed in `xnano-core 0.0.17` (`trim: false`); authored indentation now lands as written. (#128)
- **`render()` packs multiple renderables by content.** Passing several top-level renderables gave each one an equal fill share of the viewport, so one-line items floated apart and any `gap` read as enormous whitespace. They now measure to their content size and pack from the top through the same layout path fields use, with `gap` as the literal number of cells between them. `gap=1` is one row, as it always should have been.

##### Sizing

Literal types for the common **`width`/`height`** values are now annotated. `SizingKeyword` (`"fit"`, `"fill"`, `"full"`, `"auto"`, the flex utilities, …) and `SizingPercentage` (`"0%"` – `"100%"`) fold into `SizingLike`, so editors autocomplete the values you reach for most while bare `str` stays in the union for open-ended forms like `"1fr"` or `"1/3"`. `Sizing.parse` also learned the `"full"` keyword (→ `100%`, matching the `w-full` rewrite) so every annotated literal actually resolves. (#102)

##### Context & hooks

- **Event payload accessors renamed** to match `xnano.events.Event`: `ctx.tick` / `ctx.keyboard` / `ctx.mouse` are now `ctx.tick_event` / `ctx.keyboard_event` / `ctx.mouse_event`. (#104)
- The internal `_beta_request` facade stash is gone — the HTTP request now rides on a real `Context.request` field instead of being `setattr`'d onto the runtime during dispatch. No user-facing change; `ctx.request` reads the same. (#105)

##### Hosts

**State moves off the constructor and into `run()` / `render()`.** `Terminal` and `Web` no longer take `state=` at construction; you pass it at paint time, and the constructors instead take a `state_type` for typing (à la `pydantic_ai.Agent`). `Web` is now generic over its state type. (#103)

##### Breaking changes

- `ctx.keyboard` / `ctx.mouse` / `ctx.tick` → `ctx.keyboard_event` / `ctx.mouse_event` / `ctx.tick_event`. (#104)
- `Terminal(state=...)` / `Web(state=...)` → pass `state=` to `run()` / `render()`:

  ```python
  # before
  Terminal(state=Notes()).run(App())
  # after
  Terminal().run(App(), state=Notes())
  ```
  (#103)

##### Changelog

* release: xnano 1.2.3b1 prerelease fixes by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/132

### 1.2.2

Published 2026-07-30. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.2).

#### xnano v1.2.2

A maintenance release on top of 1.2.1's ratatui 0.30 migration. No API breaks — this one hardens rendering, components, and validation, and opens up a browser story: **xnano now runs under Pyodide/WASM.** Everything below is bug fixes and coverage; upgrade in place.

##### Browser / WASM (Pyodide)

xnano can now render inside a Pyodide (WebAssembly) runtime. `device.py`'s ClearType capability lookup is guarded so it no longer blows up on wasm builds where the underlying terminal query is absent — the framework degrades instead of crashing on import. A new `docs/sandbox.md` walks through running xnano in the browser, and `scripts/set_version.py` now pins the sandbox alongside the rest of the release. WASM render + sandbox test suites were added to keep the path from regressing.

##### Rendering

`render()` now keeps styling from anything that carries its own — components, grids, and content primitives. Previously `styled` was driven only off the top-level kwargs, so `render(Text(...))`, `render(chart)`, and friends silently dropped their color/modifiers unless you also passed a style kwarg. A bare scalar with no style still stays plain text; anything richer keeps its paint. `lower_content` also now uses the live render area instead of a stale one, so component/content styling lands correctly.

##### Components

- **Options** windows long option lists instead of overflowing, and hover→index mapping is fixed so the dim hover indicator tracks the row your pointer is actually on. Dropdown coverage came along for the ride.
- **Chart** series were consolidated onto a single `schema.Series` (with marker support) — `chart.py` no longer carries its own parallel `Series` definition, so one type describes a series everywhere.

##### CLI & validation

- The CLI now renders help for `HelpException`, not only `HelpRequested` — invoking help through either path prints help instead of leaking an exception.
- TypedDict validation now honors `Required`/`NotRequired`.

##### Under the hood

CodSpeed continuous performance measurement added in CI, plus core/options benchmarks and runtime/options stress tests. Broad test-coverage expansion across components, the public core API, component base, entrypoint, and composition. Getting-started and zensical docs refreshed; Dependabot dependency bumps (GitHub Actions, Rust deps). `xnano-core` bumped to `0.0.16`.

##### Changelog

* chore(deps): bump actions/upload-artifact from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/98
* chore(deps): bump actions/checkout from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/99
* chore(deps): bump dorny/paths-filter from 3 to 4 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/100
* chore(deps): bump uvicorn from 0.51.0 to 0.52.0 in the python-dependencies group by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/101
* ci: add codspeed continuous performance measurement by @codspeed-hq[bot] in https://github.com/hsaeed3/xnano/pull/106
* chore: plus ultra by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/107
* fix(chart): consolidate Series onto schema.Series by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/108
* fix(options): scroll long lists with correct hover mapping by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/109
* fix(cli): handle HelpException in command dispatch by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/110
* fix(validation): respect Required/NotRequired qualifiers by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/111
* fix(device): lazy ClearType map for no-terminal-feature builds by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/112
* fix(render): preserve styling and pass live area to compose by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/113
* docs: refresh getting-started and zensical config by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/114
* test: expand coverage across components and framework by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/115
* chore(release): bump xnano to 1.2.2 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/116
* chore(release): bump xnano-core to 0.0.16 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/117
* docs(sandbox): add pyodide sandbox page by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/118
* test(pyodide): wasm render + sandbox coverage by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/119
* test(perf): benchmarks + stress suites by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/120
* test: core public API + framework coverage by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/121
* fix(tests): guard ComponentRenderContext subscript for Python 3.10 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/122
* fix(tests): skip ComponentRenderContext[Any] subscript on Python 3.10 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/123

##### New Contributors
* @codspeed-hq[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/106

### 1.2.1

Published 2026-07-29. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.1).

##### What's Changed
* chore(docs): enable instant navigation within `zensical.toml` for docs (#89) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/89
* chore(deps): add Dependabot config by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/90
* chore(deps): bump actions/download-artifact from 6 to 8 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/91
* chore(deps): bump actions/checkout from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/92
* chore(deps): bump softprops/action-gh-release from 2 to 3 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/93
* chore(deps): bump actions/setup-node from 6 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/94
* chore(deps): bump actions/setup-python from 6 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/95
* chore(deps): bump the rust-dependencies group in /xnano-core with 3 updates by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/96
* fix(xnano-core): migrate rust bindings to ratatui 0.30 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/97

##### New Contributors
* @dependabot[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/91

### 1.2.0

Published 2026-07-29. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.2.0).

##### xnano v1.2.0

This release promotes the former `xnano.beta` preview into the stable `xnano` namespace and retires the old framework surface entirely. The parallel `beta/` package is gone — its decoupled design *is* the framework now. Net effect: ~28,000 lines removed, one shared runtime under every host.

###### Rewritten public API

The old monolithic modules were replaced by a flat, modular DSL:

- `xnano/grid.py` (1,810 lines), `xnano/terminal/terminal.py` (1,182 lines), the full `xnano/web/*` HTML paint backenxnano/color.py`,`xnano/images.py`, and the entire private `_renderable` / `_styles` / `_types` /
`_tailwind_classes` / `_dispatcfunction_hooks` /`_core_bindings` layer are **removed**.
- In their place: `grids.py`, `ts.py`, `actions.py`,`colors.py`, `tailwind.py`, `effects.py`, `terminal.py`, `web.py`, plus `server/`, `cli/`,
`utils/`, `components/`, and a ime`, `Frame`, contentprimitives, controller, stage, dispatch).

Export changes:

- New top-level exports: `render()`, `Frame`, `Runtime`, `Component`, `Command`.
- The `Grid` alias and the bare use `BaseGrid` and the named`@on_*` hooks.
- `color=` is now `foreground=`s as a runtime alias).
- `Text` accepts plain string defaults; `grid_render(ctx)` supported.

###### One runtime for every host

Terminal, web, and the one-shot `render()` helper all run on the same offscreen `Runtime` /
`TerminalController` engine. WeHTML painter — it streams cellsfrom the same core path the terminal uses.

###### Fields, input & interaction

- `Field(z=)` threads z-order through a field's whole subtree (string, component, nested
grid) with additive global pain
- `Field(overlay=)` renders an out-of-flow centered popup that paints opaque over the panels
behind it.
- `Terminal(mouse_events=)` enables mouse capture; click-to-focus is no longer gated behind
arrow-nav.
- `Options` defaults to `searchable=False` (`Dropdown` overrides back to `True`) with a
distinct dim hover indicator separate from selection.
- Text/Options inputs no longer consume `ctrl`/`alt` chords as typed text, so app shortcuts (e.g. `ctrl+s`) reach hooks; thaced through the real terminal cursor each frame.

###### Rendering & performance

- Each live frame is drawn inside a crossterm synchronized update, so the emulator applies it
atomically — fixes row tearing se corruption that left garbledglyphs in other shells on exit.
- The showcase demo advances and adapts paint cadence toterminal size (~10–15fps), keeping full-screen truecolor motion smooth without pinning the CPU.

###### Also

- Scrollable markdown viewer and the `xnano PATH.md` runner.
- Terminal-restore fixes on exit and hangup.

### 1.1.7

Published 2026-07-28. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.7).

##### What's Changed
* beta: grid_render(ctx), color→foreground alias, str Text defaults (v1.1.7) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/77

### 1.1.6

Published 2026-07-28. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.6).

##### What's Changed
* docs/beta-context: update `README.md` to include context on `xnano.beta` API by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/75
* beta: showcase demo rewrite + render fixes (sync output, exit reset, transparent overlays) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/76

### 1.1.5

Published 2026-07-26. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.5).

##### What's Changed
* beta: ergonomics + bug-fix pass (fill, scroll, focus, threading, options) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/73
* chore: bump ``xnano`` to v1.1.5 for release by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/74

### 1.1.4

Published 2026-07-24. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.4).

##### What's Changed
* Beta ergonomics pass + stable-API deprecation cleanup by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/72

### 1.1.3

Published 2026-07-24. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.3).

##### What's Changed
* fix: make beta runtime updates reliable by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/71

### 1.1.2

Published 2026-07-23. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.2).

##### What's Changed
* fix: complete beta runtime integration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/70

### 1.1.1

Published 2026-07-23. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.1).

##### What's Changed
* fix: exit terminal process on hangup by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/66
* chore: bump xnano to `v1.1.1` by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/67
* feat: ergonomics pass — container fields, scroll, group focus, web cursor/device parity by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/68
* feat: xnano.beta preview — decoupled framework, scrollable markdown viewer, terminal-restore fix by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/69

### 1.1.0

Published 2026-07-23. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.1.0).

##### What's Changed
* docs: remove data-preview annotations from index.md by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/57
* feat!: xnano 1.1.0 — big & better text update by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/63
* chore: remove .claude from tracked directories by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/64
* fix: include text editor in pyodide wheel by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/65

### 1.0.16

Published 2026-07-17. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.16).

##### What's Changed
* fix: update ``StateT | None`` removing optional None type to resolve "state might be None"  type checking errors when accessing state through context within hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/56

### 1.0.15

Published 2026-07-15. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.15).

##### What's Changed
* Bump xnano to 1.0.15, cap requires-python below 3.14 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/55

### 1.0.14

Published 2026-07-15. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.14).

##### What's Changed
* docs: cross-link xnano primitives across hooks and guide docs by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/53
* refactor: rename @on to @on_action, bump version to 1.0.14 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/54

### 1.0.13

Published 2026-07-15. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.13).

##### What's Changed
* docs: integrate context7 widget within documentation and style it a bit by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/51
* fix: initialize user Grid classes by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/52

### 1.0.11

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.11).

##### What's Changed
* docs: add interactive Pyodide sandbox by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/49
* feat: add optional terminal image rendering by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/50

### 1.0.10

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.10).

##### What's Changed
* docs: rewrite and restyle documentation by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/46
* docs: unify demo generation and refresh assets by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/47
* fix(tui): render grid roots through layout by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/48

### 1.0.9

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.9).

##### What's Changed
* fix(pyodide): preserve terminal output colors by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/45

### 1.0.8

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.8).

##### What's Changed
* release(xnano/v1.0.8) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/44

### 1.0.7

Published 2026-07-13. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.7).

##### What's Changed
* release(xnano/v1.0.7) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/43

### 1.0.6

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.6).

### 1.0.5

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.5).

### 1.0.4

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.4).

##### What's Changed
* docs: concepts rewrite and reference restructure by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/41
* feat: Pyodide/WebAssembly wheel support for xnano-core by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/42

### 1.0.3

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.3).

### 1.0.2

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.2).

##### What's Changed
* chore(ruff): update isort configuration for improved import spacing by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/40

### 1.0.1

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.1).

##### What's Changed
* [ImgBot] Optimize images by @imgbot[bot] in https://github.com/hsaeed3/xnano/pull/31
* feat: Tailwind CSS class_name support for grid fields by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/32
* refactor: finalize module layout and interface-neutral core by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/33
* test: update suite for module layout and BaseGrid by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/34
* chore: retarget examples and scripts to the new package layout by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/35
* refactor: polish package docs, Actions tests, and type fixes by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/36
* docs: retarget site, README, and nav for the new package layout by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/37
* docs: retarget AGENTS.md and CLAUDE.md for the new package layout by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/38
* refactor: optimize runtime dispatch and enforce imports by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/39

### 1.0.0

Published 2026-07-10. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0).

##### What's Changed
* refactor: migrate xnano.beta into the stable xnano namespace by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/16
* docs: update API reference for the xnano namespace migration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/17
* chore: update examples and dev scripts for the xnano namespace migration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/18
* perf: optimize core rendering and framework hot paths by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/19
* docs: reorganize guides and expand documentation site by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/21
* [ImgBot] Optimize images by @imgbot[bot] in https://github.com/hsaeed3/xnano/pull/22
* Harden terminal teardown and add background cell-filter effects by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/23
* Add xnano feature showcase demo app by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/24
* docs: add title/feature-tour demo GIFs and VHS tooling by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/25
* refactor(core): sound BufferMutView borrows and unicode IR measure by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/26
* refactor(arch): fix hook registration, layout measure, and event cache by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/27
* feat(beta): web UI host, htmx controller, and request hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/28
* feat(beta): add Command CLI class by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/29
* docs(beta): Web UI, request hooks, and Commands preview docs by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/30

##### New Contributors
* @imgbot[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/22

### 1.0.0b4

Published 2026-07-10. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0b4).

##### What's Changed
* feat: field focus, editable text input, and on_focus/on_field/on_poll hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/14
* feat: add Table, Chart, and Progress declarative components by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/15

### 1.0.0b3

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0b3).

##### What's Changed
* fix(render_ir): push field background onto spans rather than flood-filling slot by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/8
* fix(frame): restrict Field background to text cells; add TailwindColorBinding and VHS utils by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/9
* docs: add showcase, restructure nav, add concept demos, and VHS scripts by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/10
* docs(readme): replace demo GIFs with concept dark GIFs; add render and styled-text examples by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/11
* fix(render_tree): clamp absolute rect to buffer bounds on terminal resize by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/12
* feat(demo): add python -m xnano interactive showcase by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/13

### 1.0.0b2

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0b2).

##### What's Changed
* feat(standardized-sizing) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/7

### 1.0.0b1

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v1.0.0b1).

##### What's Changed
* refactor(demos): streamline demo steps and improve function formatting by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/5
* feat(render): update `render(..)` call compatibility and functionality by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/6

### 0.99.7

Published 2026-07-07. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v0.99.7).

### 0.99.6

Published 2026-07-07. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano/v0.99.6).

##### What's Changed
* refactor(tui) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/3
* refactor(beta) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/4

##### New Contributors
* @hsaeed3 made their first contribution in https://github.com/hsaeed3/xnano/pull/3

## xnano-core

### 2.0.0

Published 2026-10-19. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v2.0.0).

#### xnano-core 2.0.0

xnano-core 2.0 is the Rust engine under xnano 2.0, rewritten alongside it. In the 1.2 line (xnano-core 0.0.17) the package was an internal render-session engine: its public module exported four event names, and xnano drove it through a private render tree. In 2.0 it is a complete, documented terminal runtime of its own, with one flat `xnano_core` namespace of typed classes, a docstring with runnable examples on each, and stubs that editors and type checkers read. Most applications use it through `xnano`; `xnano_core` is for building on the engine directly.

```sh
pip install xnano-core
```

##### What it is built on

`ratatui` 0.30 for layout, cells and widgets, `tachyonfx` 0.25 for effects, `crossterm` 0.29 for the live terminal, and `termprofile` for color support detection, compiled with PyO3 into one abi3 wheel per platform for Python 3.10 and later.

##### The runtime

- **`Runtime`** owns a canvas's buffers, clock, input, state and hooks, and draws frames on the screen or offscreen. `Frame`, `FrameMetrics` and `FrameSnapshot` describe what was drawn.
- **`Clock`, `SimulationClock` and `FPS`** run time on the wall clock or step it by hand, so an offscreen runtime renders the same frames every time.
- **`TerminalOptions`** set the screen, input and capture behavior; **`TerminalCapabilities`** (from `detect_terminal_capabilities()`) report the color profile, graphics protocols and keyboard support of the terminal in use.
- **`Cursor`** and **`CursorShape`** control the cursor.

##### Content and output

- **`Buffer`**, **`Cell`** and **`Layer`** hold what is drawn, cell by cell and in drawing order.
- **`TextContent`**, **`TextLine`**, **`TextSpan`** and **`StyledText`** describe styled text; `layout_text()` wraps it and `display_width()` measures it.
- **`Pixels`** and **`Raster`** draw at sub-cell resolution with half blocks or braille.
- **`Rendering`** reads a buffer back as text or ANSI, and the `cell_grid_*` functions read, validate and convert whole cell grids and cell animations.
- **`TextEditor`** is a multi-line text editor.

##### Operations

Everything that changes a buffer is an **`Operation`**: `Write`, `Fill`, `Place`, `Move`, `Resize`, `ApplyStyle`, `Draw`, `AnimateDrawing`, `SetState`, `ApplyStatePatch`, `Conditional` and more. Operations chain into sequences, are dispatched through a `Registry`, and print as the Python call that builds them.

##### Layout and geometry

`SizeRule` sizes content in cells, percentages, fills, fits, minimums and maximums. `Point`, `Size`, `Rectangle`, `Position`, `Offset`, `Margin`, `Bounds` and `HitArea` describe geometry, and `Width`, `Height`, `X`, `Y` and the `Parent*` values are expressions that follow it.

##### Styles and colors

`Style` and `Modifier` style cells, and `Color` parses names, hex strings and palette indexes, builds colors from RGB, HSL, HSV and Tailwind values (`Color.from_tailwind('violet', 500)`), converts between them, mixes them (`lerp`, `lighten`, `darken`, `saturate`, `inverse`), and picks them with `Color.random(base=None)`.

##### Expressions

`Expression`, `ScalarExpression` and `Predicate` are values that are evaluated against the runtime on every frame. They cover geometry, time (`TimeElapsed`, `TimeDelta`), the keyboard, mouse and scroll wheel, focus and visibility, combine with Python arithmetic and comparisons, and print as the Python that builds them.

##### Hooks, events and input

- **`Hook`** runs a callback on frames, ticks, events and state changes, with a context (`FrameContext`, `EventContext`, `UpdateContext`) for each.
- **`Event`**, **`KeyEvent`** and **`MouseEvent`** describe input; **`KeyBinding`** parses key names and chords.
- **`InputRouter`** and **`InputState`** route events to the content under the pointer and track held keys and buttons.

##### State

`TerminalStateStore` is a typed store with a JSON schema, snapshots, patches, transactions, subscriptions and selections. Writes are checked against the schema, and conflicts and access outside a store's scope raise their own errors.

##### Effects

`Effect` and its kinds (`Fade`, `Dissolve`, `Glitch`, `Fuzz`, `EvolveSymbolSet` and the rest of `tachyonfx`) are operations, run by an `EffectManager` on the runtime's clock, with `CellFilter` and `Interpolation` to choose which cells change and how.

##### Widgets

The `ratatui` widgets, ready to draw: `Paragraph`, `Block`, `Gauge`, `LineGauge`, `Table`, `Tabs`, `ItemList`, `Scrollbar`, `Sparkline`, `BarChart`, `Chart`, `Calendar` and `Canvas` with its shapes. Their values and text accept expressions.

##### Errors

`ErrorDetail`, `ErrorReport` and `ReportedError` give errors labelled reports in the style of pydantic-core: each detail has a code, a message, a location, a hint and the value that caused it, and a report prints them with a count heading. `ReportedError` is meant to be subclassed; xnano's `TerminalError` is built on it. Engine failures raise `RenderError`, `UnsupportedOperationError`, `RuntimeRequiredError`, `InvalidRegionError` and `CellGridError`.

##### Readable values

Every class has a `repr` that shows the Python that builds it, and value types (colors, styles, geometry, events and the rest) compare and hash by value.

##### Platforms

Wheels are built for Linux (x86_64 and aarch64, glibc and musl), macOS (Intel and Apple silicon) and Windows (x86_64). A WebAssembly wheel is built and tested in Pyodide, where a runtime renders offscreen; the live terminal is not part of the WebAssembly build.

### 2.0.0-beta.4 (pre-release)

Published 2026-10-17. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v2.0.0-beta.4).

#### xnano-core 2.0.0-beta.4

Engine (`xnano-terminal-runtime`):

- Clocks can be stepped by hand while stopped: a manual clock steps at any time, and a monotonic clock steps only
  while it is stopped. A monotonic clock can start at a given elapsed time and frame, which is how a canvas keeps
  its time when it is opened on the screen.
- The live input reader delivers only what the gates allow: with the keyboard off no key events arrive except
  `Ctrl-C` while the interrupt is kept, and wheel reports arrive only when `scroll` is on, independently of
  `mouse`. Turning on `scroll` alone asks the terminal for button reports and passes only the wheel through.
- `Move` operations and mouse events use `x` and `y`.
- Expressions: a comparison with a value that has not been seen yet (`None`) is false, never an error, and so
  is `contains` with one.

Bindings (`xnano_core`):

- `Color.darken(amount, *, color_space='hsl')` (an amount from 0.0 to 1.0) and `Color.inverse()`, which raises a
  `ValueError` for `Color.reset`.
- `Move(x, y)` and `Rectangle.translate(x, y)` replace `horizontal` and `vertical`; `MouseEvent.scroll_x` and
  `scroll_y`, and `Event.mouse_event(scroll_x=, scroll_y=)`, replace `scroll_horizontal` and `scroll_vertical`.
- `Clock.stop()`, `Clock.resume()` and `Clock.is_stopped` replace `pause`, `resume` and `is_paused`;
  `Clock.step(milliseconds)` replaces `advance`; `Clock.monotonic(*, elapsed_seconds=0.0, frame=0)`;
  `SimulationClock.stop()`, `is_stopped` and `derive(is_stopped=)` replace `pause`, `paused` and
  `derive(paused=)`.
- `Runtime.live(..., clock=None)` runs a live runtime on a given clock.
- `InputOptions(scroll=False)` and `InputOptions(keyboard='off')`; `InputOptions` has a `repr`, compares by value
  and is not hashable.
- `InputState` remembers the latest input: `last_key`, `last_key_kind`, `last_chord`, `last_mouse_button`,
  `last_mouse_kind`, `last_mouse_position`, `scroll_x`, `scroll_y`, `is_mouse_down` and `last_pasted_text`, and
  `pressed_keys` holds `mouse_left`, `mouse_right` and `mouse_middle` while a button is held.
- A live runtime drawing in an inline region reports the region's size, not the window's, to resize hooks.
- Expression scopes `KeyboardScope`, `MouseScope` and `ScrollScope` (classes `KeyboardExpressionScope`,
  `MouseExpressionScope`, `ScrollExpressionScope`), the values `KeyboardKey`, `KeyboardKind`, `KeyboardChord`,
  `MouseButtonValue`, `MouseKind`, `MousePosition`, `MouseIsDown`, `ScrollX` and `ScrollY`, and `BufferRegion`
  (`BufferExpressionScope.region`), the buffer's rectangle on the screen.
- `Value.contains(point)`. `==` and `!=` on a `Value` build predicates, and `Value.eq` and `Value.ne` are now
  `Value.equals` and `Value.not_equals`.
- `xnano_core.Pixel` (the `(column, row, (red, green, blue))` tuple alias) is `xnano_core.PixelEntry`.
- `Surface.set_background_colors(colors, *, width, x=0, y=0)` and `Surface.set_foreground_colors(...)` set the
  colors of a block of cells in one call; `None` leaves a cell alone.
- A build instrumented for coverage counts as not optimized, so the speed budgets skip it.

### 2.0.0-beta.3 (pre-release)

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v2.0.0-beta.3).

##### xnano-core 2.0.0-beta.3

A small release of the Rust engine bindings. It ships with `xnano` 2.0.0-beta.3, which requires it (`xnano-core>=2.0.0b3`). `xnano-audio` (0.2.0) and `xnano-image` (0.2.0) are unchanged.

###### New

- **`Color.to_hex()`** returns a true color as a `'#rrggbb'` string. Named and indexed colors are chosen by the terminal's theme and have no fixed value, so, like `to_rgb()`, they raise a `ValueError` that says what to pass instead (a `'#rrggbb'` string or an `(r, g, b)` tuple).

###### Documented

`Color` already had these members in the compiled module; the type stubs and docs now describe them, each with a runnable example:

- `Color.from_hsl(hue, saturation, lightness)` and `Color.from_hsv(hue, saturation, value)` (hue in degrees, the others as percentages).
- `Color.to_hsl()` and `Color.to_hsv()`.
- `Color.lerp(other, ratio, color_space=...)`, `Color.lighten(amount, color_space=...)` and `Color.saturate(factor, color_space=...)`, where `color_space` is `'rgb'`, `'hsl'` (the default) or `'hsv'`.
- `Color.is_reset`.
- The named colors as class attributes: `Color.black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `gray`, `dark_gray`, `light_red`, `light_green`, `light_yellow`, `light_blue`, `light_magenta`, `light_cyan`, `white` and `reset`.

###### Packaging

- `xnano-core` and `xnano` share the workspace version, now 2.0.0-beta.3 (Python `2.0.0b3`).

### 2.0.0-beta.2 (pre-release)

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v2.0.0-beta.2).

### 2.0.0-beta.1 (pre-release)

Published 2026-10-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v2.0.0-beta.1).

### 0.0.17

Published 2026-07-31. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.17).

#### xnano-core v0.0.17

Silly little layout bug fixes.

##### Text wrapping

Wrapped paragraphs now **preserve authored leading whitespace**. The native paragraph widget wrapped with ratatui's `Wrap { trim: true }`, which strips leading whitespace from every laid-out line — so any indentation after a `\n` silently vanished the moment a paragraph wrapped (which is the default). Switched to `trim: false`, so indentation the caller wrote survives to the buffer. This is the native half of xnano's `Text` indentation fix (see xnano #128); markdown, tables, and every other paragraph-backed surface inherit the corrected behavior.

### 0.0.16

Published 2026-07-30. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.16).

##### What's Changed
* chore(deps): bump actions/upload-artifact from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/98
* chore(deps): bump actions/checkout from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/99
* chore(deps): bump dorny/paths-filter from 3 to 4 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/100
* chore(deps): bump uvicorn from 0.51.0 to 0.52.0 in the python-dependencies group by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/101
* ci: add codspeed continuous performance measurement by @codspeed-hq[bot] in https://github.com/hsaeed3/xnano/pull/106
* chore: plus ultra by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/107
* fix(chart): consolidate Series onto schema.Series by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/108
* fix(options): scroll long lists with correct hover mapping by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/109
* fix(cli): handle HelpException in command dispatch by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/110
* fix(validation): respect Required/NotRequired qualifiers by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/111
* fix(device): lazy ClearType map for no-terminal-feature builds by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/112
* fix(render): preserve styling and pass live area to compose by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/113
* docs: refresh getting-started and zensical config by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/114
* test: expand coverage across components and framework by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/115
* chore(release): bump xnano to 1.2.2 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/116
* chore(release): bump xnano-core to 0.0.16 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/117
* docs(sandbox): add pyodide sandbox page by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/118
* test(pyodide): wasm render + sandbox coverage by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/119
* test(perf): benchmarks + stress suites by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/120
* test: core public API + framework coverage by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/121
* fix(tests): guard ComponentRenderContext subscript for Python 3.10 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/122

##### New Contributors
* @codspeed-hq[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/106

### 0.0.15

Published 2026-07-29. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.15).

##### What's Changed
* chore(docs): enable instant navigation within `zensical.toml` for docs (#89) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/89
* chore(deps): add Dependabot config by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/90
* chore(deps): bump actions/download-artifact from 6 to 8 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/91
* chore(deps): bump actions/checkout from 5 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/92
* chore(deps): bump softprops/action-gh-release from 2 to 3 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/93
* chore(deps): bump actions/setup-node from 6 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/94
* chore(deps): bump actions/setup-python from 6 to 7 by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/95
* chore(deps): bump the rust-dependencies group in /xnano-core with 3 updates by @dependabot[bot] in https://github.com/hsaeed3/xnano/pull/96
* fix(xnano-core): migrate rust bindings to ratatui 0.30 by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/97

##### New Contributors
* @dependabot[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/91

### 0.0.14

Published 2026-07-29. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.14).

##### What's Changed
* docs(chore): add pointer for `uv run xnano` demo within README.md by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/78
* beta: field z/overlay, mouse events, input & Options ergonomics (#82) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/83
* Migrate xnano.beta into the stable namespace + terminal/demo perf by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/84
* release(xnano-core): bump `xnano-core` to `v1.0.14` for release by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/85

### 0.0.13

Published 2026-07-28. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.13).

##### What's Changed
* docs/beta-context: update `README.md` to include context on `xnano.beta` API by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/75
* beta: showcase demo rewrite + render fixes (sync output, exit reset, transparent overlays) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/76

### 0.0.12

Published 2026-07-23. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.12).

##### What's Changed
* docs: remove data-preview annotations from index.md by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/57
* feat!: xnano 1.1.0 — big & better text update by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/63
* chore: remove .claude from tracked directories by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/64
* fix: include text editor in pyodide wheel by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/65

### 0.0.11

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.11).

### 0.0.10

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.10).

##### What's Changed
* docs: concepts rewrite and reference restructure by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/41
* feat: Pyodide/WebAssembly wheel support for xnano-core by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/42

### 0.0.9

Published 2026-07-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.9).

### 0.0.8

Published 2026-07-10. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.8).

##### What's Changed
* refactor: migrate xnano.beta into the stable xnano namespace by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/16
* docs: update API reference for the xnano namespace migration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/17
* chore: update examples and dev scripts for the xnano namespace migration by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/18
* perf: optimize core rendering and framework hot paths by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/19
* docs: reorganize guides and expand documentation site by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/21
* [ImgBot] Optimize images by @imgbot[bot] in https://github.com/hsaeed3/xnano/pull/22
* Harden terminal teardown and add background cell-filter effects by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/23
* Add xnano feature showcase demo app by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/24
* docs: add title/feature-tour demo GIFs and VHS tooling by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/25
* refactor(core): sound BufferMutView borrows and unicode IR measure by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/26
* refactor(arch): fix hook registration, layout measure, and event cache by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/27
* feat(beta): web UI host, htmx controller, and request hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/28
* feat(beta): add Command CLI class by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/29
* docs(beta): Web UI, request hooks, and Commands preview docs by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/30

##### New Contributors
* @imgbot[bot] made their first contribution in https://github.com/hsaeed3/xnano/pull/22

### 0.0.7

Published 2026-07-10. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.7).

##### What's Changed
* feat: field focus, editable text input, and on_focus/on_field/on_poll hooks by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/14
* feat: add Table, Chart, and Progress declarative components by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/15

### 0.0.6

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.6).

##### What's Changed
* fix(render_ir): push field background onto spans rather than flood-filling slot by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/8
* fix(frame): restrict Field background to text cells; add TailwindColorBinding and VHS utils by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/9
* docs: add showcase, restructure nav, add concept demos, and VHS scripts by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/10
* docs(readme): replace demo GIFs with concept dark GIFs; add render and styled-text examples by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/11
* fix(render_tree): clamp absolute rect to buffer bounds on terminal resize by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/12
* feat(demo): add python -m xnano interactive showcase by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/13

### 0.0.5

Published 2026-07-08. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.5).

##### What's Changed
* feat(standardized-sizing) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/7

### 0.0.4

Published 2026-07-07. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-core/v0.0.4).

##### What's Changed
* refactor(tui) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/3
* refactor(beta) by @hsaeed3 in https://github.com/hsaeed3/xnano/pull/4

##### New Contributors
* @hsaeed3 made their first contribution in https://github.com/hsaeed3/xnano/pull/3

## xnano-audio

### 0.4.0

Published 2026-10-19. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-audio/v0.4.0).

#### xnano-audio 0.4.0

- **Readable values.** `TerminalAudioPlayer` (its `tempo`, `beat` and `is_clock_running`), `TerminalMicrophone` (`sample_rate`, `channels` and `is_open`), `TerminalAudioStream` (`format` and `is_closed`), `TerminalPlayback` (`is_playing`, `is_paused`, `volume` and `pan`) and `TerminalStreamingAudioPlayer` (`format`, `sample_position` and `is_closed`) print their state, so every public class of `xnano_audio` now has a readable `repr`.
- The package README names `xnano.load_sound` as the way to load a sound through xnano.
- **Lighter playback.** A sound played without panning shares one stereo copy of its samples across plays, and its volume is applied by the audio engine instead of a copy of the samples for every play.
- **Tempo changes take effect at once.** `TerminalAudioPlayer.set_tempo` changes the musical clock immediately instead of over a short ramp.

### 0.3.0

Published 2026-10-17. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-audio/v0.3.0).

#### xnano-audio 0.3.0

- `TerminalSound.mix(layers, *, duration_seconds, start_seconds=0.0, sample_rate=44100)` mixes sounds placed on a
  timeline into one sound. Each layer is a `(sound, offset_seconds, gain)` tuple; the result is the part of the
  timeline from `start_seconds` for `duration_seconds` (above 0 and at most 3600), summed and limited to -1.0 to
  1.0. Every layer must have been rendered at `sample_rate` (8000 to 192000). A malformed layer, a negative or
  non-finite gain, or a mismatched sample rate raises an error that names the layer and what to pass. The GIL is
  released while mixing. `xnano` uses it for `canvas.audio.render_sound()`.
- The instrument inventory is unchanged and is now checked against the Rust instrument table, so
  `instrument_names()` lists exactly the 23 built-in instruments: `piano`, `electric_piano`, `organ`, `bell`,
  `marimba`, `guitar`, `electric_guitar`, `pluck`, `bass`, `synth`, `pad`, `strings`, `sine`, `square`, `saw`,
  `triangle`, `kick`, `snare`, `hihat`, `open_hat`, `clap`, `tom` and `cowbell`. `xnano` accepts every one of them
  (`xnano_audio.InstrumentName`), and an unknown name raises a `ValueError` that lists them.
- The README describes mixing and the `xnano` entry points `xnano.note`, `xnano.play`, `xnano.from_audio`,
  `canvas.audio`, `canvas.play` and `canvas.bpm`.

#### Compatibility

- `xnano` 2.0.0b4 requires `xnano-core>=2.0.0b4`.
- The `audio` extra requires `xnano-audio>=0.3.0,<0.4`.
- The `image` extra requires `xnano-image>=0.2.0,<0.3`; `xnano-image` 0.2.0 is unchanged.
- `xnano` and `xnano-core` move from 2.0.0-beta.3 (`2.0.0b3`) to 2.0.0-beta.4 (`2.0.0b4`) together, and
  `xnano-audio` moves from 0.2.0 to 0.3.0.
- Python 3.10 to 3.14.
- The previous major version: `pip install "xnano>=1.2.3,<2"`.

### 0.2.0

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-audio/v0.2.0).

### 0.1.0

Published 2026-10-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-audio/v0.1.0).

## xnano-image

### 0.2.0

Published 2026-10-14. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-image/v0.2.0).

### 0.1.0

Published 2026-10-12. [Release page](https://github.com/hsaeed3/xnano/releases/tag/xnano-image/v0.1.0).
