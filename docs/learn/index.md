---
title: "Getting Started"
icon: "fontawesome/solid/bolt"
---

# Getting Started

## Install

```bash
pip install xnano                # the terminal, widgets, effects and events
pip install "xnano[audio]"       # adds notes, melodies and audio files
pip install "xnano[image]"       # adds images and animations
```

## Build values from the inside out

[`write`][xnano.write], [`draw`][xnano.draw], [`note`][xnano.note] and
[`box`][xnano.box] each make a small value. A value needs no screen and no sound
device, and the text and pixel ones render on their own:

```python
import xnano

card = xnano.write('Hello, world!', border='rounded', padding={'horizontal': 2})
heart = xnano.draw(
    """
    .RR.RR.
    RRRRRRR
    .RRRRR.
    ..RRR..
    ...R...
    """,
    'R=#e03040',
)
print(card.render())
print(heart.render(format='ansi'))
```

A [`Pixel`][xnano.Pixel] is one cell or dot:
`xnano.Pixel('diamond', foreground='red')`. A character the palette does not
name, such as `.`, is transparent. Pixel art keeps its color only in the `ansi`
format, so print it with `render(format='ansi')`.

## Put it on a canvas

[`new`][xnano.new] makes a [`Canvas`][xnano.Canvas]: a virtual terminal made of
devices, with hooks and state. Its [`screen`][xnano.devices.Screen] is where
things are written, its [`speaker`][xnano.devices.Speaker] plays,
[`keyboard`][xnano.devices.Keyboard] and [`mouse`][xnano.devices.Mouse] hear and
press keys and buttons, and its [`clock`][xnano.devices.Clock] keeps the time. A
canvas from `new()` has no real screen and its time moves only when you move it,
so the same program draws the same frames every run:

```python
import xnano

with xnano.new(width=40, height=6) as canvas:
    canvas.screen.write(xnano.write('Hello, world!', border='rounded'), x='center')
    for frame in canvas.iter(frames=3):
        pass
    print(canvas.screen.render())
```

[`canvas.iter()`][xnano.canvas.Canvas.iter] runs it one frame at a time,
[`canvas.clock.step()`][xnano.devices.Clock.step] moves one frame,
[`stop()`][xnano.devices.Clock.stop] freezes time and
[`resume()`][xnano.devices.Clock.resume] lets it run on. Positions take numbers,
percentages (`'50%'`), words (`'left'`, `'center'`, `'right'`, `'top'`,
`'bottom'`) or formulas.

## Put it on your screen

[`open`][xnano.open] is `new` on your screen: it returns the same canvas as a
[`Terminal`][xnano.Terminal]. `canvas.open()` puts a canvas you already built
there, with its time carried over.

```python
import xnano

with xnano.open(width=40, height=5) as terminal:
    terminal.screen.write('Hello, world!', x='center', y='center', border='rounded')
    terminal.run(quit_on='q')
```

## Run it one frame at a time

[`xnano.iter`][xnano.iter] takes the keywords of `open()`, opens the terminal and
runs it as a `for` loop: each frame has the terminal in `frame.canvas` and the
events that arrived since the previous frame in `frame.events`. Without `frames=`
or `seconds=` it runs until a key of `quit_on` is pressed, as `run()` does.

```python
import xnano

hero = None
for frame in xnano.iter(width=30, height=3, fps=30, quit_on='q'):
    if hero is None:
        hero = frame.canvas.screen.write('@', y=1)
    hero.x += frame.canvas.keyboard.axis('left', 'right')
    for event in frame.events:
        if event.key is not None and event.key.key == 'space':
            frame.canvas.speaker.play('C5')
```

## Make it move

A formula of time is evaluated again on every frame, so there is no loop to
write:

```python
import xnano
from xnano.expressions import ParentWidth, TimeElapsed, Width

with xnano.open(width=40, height=3) as terminal:
    ball = terminal.screen.write('●', y=1)
    ball.x = (ParentWidth - Width) * (TimeElapsed % 2 / 2)
    terminal.run(quit_on='q')
```

## React to the keyboard, the mouse and the clock

One [`hook`][xnano.canvas.Canvas.hook] reacts to everything, and `on=` says
what: `'key'`, `'mouse'`, `'scroll'`, `'drag'`, `'paste'`, `'tick'`, `'beat'`,
`'frame'`, `'resize'` or `'state'`.

```python
import xnano

with xnano.open(width=30, height=3) as terminal:
    terminal.screen.write('press space', y=1)
    elapsed = terminal.screen.write('  0.0s')

    @terminal.hook(on='key', keys='space')
    def toggle(context: xnano.Context) -> None:
        if context.clock.is_stopped:
            context.canvas.clock.resume()
        else:
            context.canvas.clock.stop()

    @terminal.hook(on='tick', every=1.0)
    def tick(context: xnano.Context) -> None:
        elapsed.text = f'{context.clock.elapsed:5.1f}s'

    terminal.run(quit_on='q')
```

`on=` also takes a condition: a string such as
`"mouse.position in buffer.region"`, an expression or a function. A hook on
`'drag'` is a generator: `context = yield` waits for the next movement.
`context.keyboard` (with `context.keyboard.pasted` for a paste), `context.mouse`
and `context.mouse.scroll` are the inputs, and `context.root.state.get(path)`
and `.push(path, value)` read and write state that
[`on='state'`][xnano.canvas.Canvas.hook] hooks follow.

## Components, art and sound

[`@xnano.writable`][xnano.writable] turns a function of
`(context, **parameters)` that returns content into a component that is written
again only when it read something that changes, such as the clock.
[`@xnano.playable`][xnano.playable] does the same for sound, and
[`@xnano.renderable`][xnano.renderable] gives a function a screen of its own: it
writes on `context.screen` and plays on `context.speaker` in one run, and each run
starts from an empty screen.

```python
import xnano


@xnano.renderable
def meter(context: xnano.Context, level: float = 0.5) -> None:
    context.screen.write('level', bold=True)
    context.screen.write('█' * round(level * 10))


with xnano.new(width=12, height=4) as canvas:
    canvas.screen.write(meter(level=0.3), border='rounded')
    print(canvas.screen.render())
```

`xnano.draw`
pixel art can hold other art and a camera, `xnano.play('C4 E4 G4:2')` plays a
melody written as text, and `canvas.screen.color`, `canvas.screen.border`, `canvas.screen.padding`
and `canvas.screen.margin` change how any canvas, placement or region looks. Run
`python -m xnano` to see the features working together; its source,
[`xnano.demo`][xnano.demo], is a larger example.

[`effect`][xnano.effect] builds an effect from a kind such as
`'effect.fade_from'` and its settings. Apply it to a placement with
`placement.update(...)` or `|`, or start one by name with
`placement.fx.fade_to(...)`:

```python
import xnano

with xnano.open(width=40, height=5) as terminal:
    title = terminal.screen.write('xnano', x='center', y='center', border='rounded')
    fade = xnano.effect(
        'effect.fade_from', foreground='black', duration_milliseconds=1500
    )
    title.update(fade)
    terminal.run(quit_on='q')
```

[`Image`][xnano.Image] and [`load_image`][xnano.load_image] show pictures
(the `image` extra). [`load_audio`][xnano.load_audio] loads WAV, MP3, FLAC,
Ogg Vorbis and AAC files as [`Audio`][xnano.Audio], which
[`Audio.from_samples`][xnano.Audio.from_samples] also makes from samples, and
[`Melody`][xnano.audio.Melody] is melody text parsed into notes (the `audio`
extra).

## Ask a model

`pip install "xnano[ai]"` adds [`xnano.ai`][xnano.ai]: task models that decide
what happens on a key press ([`ChoiceModel`][xnano.ai.models.decisions.ChoiceModel]),
judge what is on the screen, keep state, write text, and generate pixel art
([`ArtModel`][xnano.ai.models.art.ArtModel]), widgets
([`ComponentModel`][xnano.ai.models.components.ComponentModel]) and melodies
([`MusicModel`][xnano.ai.models.music.MusicModel]). Import them from
`xnano.ai` (`from xnano.ai import ArtModel`); each lives in a module of
[`xnano.ai.models`][xnano.ai.models] named for what it makes, such as
`xnano.ai.models.art`. [`xnano.ai.capabilities`][xnano.ai.capabilities]
gives any pydantic-ai agent the canvas, art and music as tools. `ArtModel` draws
with the language model in two steps, a sketch of the masses and then the piece,
and finishes the pixels itself; given an `image_model` such as
`'openrouter:google/gemini-2.5-flash-image'`, it has that model paint the piece
and reads the pixel art out of the picture. `generate(symmetrical=True)` mirrors
a left half, and `braille=True` or `borders=True` ask for the two looks only a
terminal has: braille dots, or box-drawing lines around colour. The generating
models work as they are, and read more examples from libraries you can install
the way spaCy installs a model:
`python -m xnano.ai.assets install art-references`.

## Where everything lives

The top-level `xnano` holds the main API. Everything else is in a module named
for what it holds:

| Module | What it holds |
| --- | --- |
| [`xnano`][xnano] | The main API: `new`, `open`, `iter`, `iter_async`, `active`, `Canvas`, `Terminal`, `Context`, `Color`, `hook`, `effect`, `write`, `box`, `draw`, `Pixel`, `Image`, `load_image`, `Audio`, `load_audio`, `Note`, `note`, `play`, `writable`, `renderable`, `playable` and the `symbols` module. |
| [`xnano.canvas`][xnano.canvas] | The canvas: `Canvas`, `new`, `active`, and its settings. |
| [`xnano.terminal`][xnano.terminal] | The real screen: `Terminal`, `open`, `iter`, `TerminalSettings`, `capabilities` and what it reports. |
| [`xnano.devices`][xnano.devices] | The devices a canvas is made of: `Screen`, `Speaker`, `Microphone`, `Keyboard`, `Mouse`, `Clock`, with the screen's `Cursor` and `Output`, and the key names. |
| [`xnano.layout`][xnano.layout] | Where things are written and how much room they take: `Placement`, `Region`, `box`, `write`, positions and sizes, `Point`, `Size`, `Rectangle`. |
| [`xnano.styles`][xnano.styles] | How things look: `Style`, `Color`, styled text, and `Colors`, `BorderAppearance`, `PaddingAppearance`, `MarginAppearance`. |
| [`xnano.hooks`][xnano.hooks] | Reacting to events: `hook`, `HookHandle`, `HookKind`, `When`, and what a hook is called with: `Context`, `Frame`, `Update`. |
| [`xnano.events`][xnano.events] | The events of the keyboard, the mouse and everything else: `Event`, `KeyEvent`, `MouseEvent`. |
| [`xnano.components`][xnano.components] | Components: `writable`, `renderable`, `playable`, the component classes, and what can be written and played (`Writable`, `Playable`). |
| [`xnano.effects`][xnano.effects] | Effects: `effect`, the effect kinds, the `<Kind>EffectParameters` classes such as `FadeToEffectParameters`, and the dictionaries an `effects=[...]` list takes. |
| [`xnano.art`][xnano.art] | What is seen: `Art`, `Camera`, `draw`, `Pixel`, `PixelPreset`, `Image`, `load_image` (images need the `image` extra). |
| [`xnano.audio`][xnano.audio] | What is heard: `Note`, `note`, `play`, `PlayHandle`, `Melody`, `Audio`, `load_audio`, `Microphone` and the instrument names (the `audio` extra). |
| [`xnano.expressions`][xnano.expressions] | Formulas such as `TerminalWidth`, `ParentWidth` and `TimeElapsed`. |
| [`xnano.operations`][xnano.operations] | Operations, including `Effect`, `CancelEffect`, `ContextualOperation` and the `Dynamic...` operations. |
| [`xnano.state`][xnano.state] | State: `StateNamespace`, `StatePath`. |
| [`xnano.widgets`][xnano.widgets], [`xnano.buffers`][xnano.buffers] | The core's widgets, such as `Figure`, `Table` and `Gauge`, and its buffers of cells. |
| [`xnano.sandbox`][xnano.sandbox] | Running untrusted Python that draws on a canvas (the `monty` extra). |
| [`xnano.ai`][xnano.ai] | Language and decision models on a canvas (the `ai` extra): the task models in `xnano.ai.models` (`decisions`, `state`, `text`, `art`, `components`, `music`), plugins, agent capabilities, `xnano.ai.assets` for the libraries of examples and `xnano.ai.testing` for models that answer from a script. |
| [`xnano.symbols`][xnano.symbols] | The registry of names for values. |
| [`xnano.errors`][xnano.errors] | `TerminalError` and the other errors a canvas raises. |

Images need the optional `image` extra and sound the `audio` extra.
