---
title: "Getting Started"
icon: "fontawesome/solid/bolt"
---

# Getting Started

## Install

```bash
pip install xnano                # the terminal, widgets, effects and events
pip install "xnano[audio]"       # adds notes, melodies and sounds
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

[`new`][xnano.new] makes a [`Canvas`][xnano.Canvas], a virtual terminal with a
size, a clock, hooks, a cursor, sound and state, and no screen. Its time moves
only when you move it, so the same program draws the same frames every run:

```python
import xnano

with xnano.new(width=40, height=6) as canvas:
    canvas.write(xnano.write('Hello, world!', border='rounded'), x='center')
    for frame in canvas.iter(count=3):
        pass
    print(canvas.render())
```

[`canvas.step()`][xnano.canvas.Canvas.step] moves one frame,
[`stop()`][xnano.canvas.Canvas.stop] freezes time and
[`resume()`][xnano.canvas.Canvas.resume] lets it run on. Positions take numbers,
percentages (`'50%'`), words (`'left'`, `'center'`, `'right'`, `'top'`,
`'bottom'`) or formulas.

## Put it on your screen

[`open`][xnano.open] is `new` on your screen: it returns the same canvas as a
[`Terminal`][xnano.Terminal]. `canvas.open()` puts a canvas you already built
there, with its time carried over.

```python
import xnano

with xnano.open(width=40, height=5) as terminal:
    terminal.write('Hello, world!', x='center', y='center', border='rounded')
    terminal.run(quit_on='q')
```

## Make it move

A formula of time is evaluated again on every frame, so there is no loop to
write:

```python
import xnano
from xnano.expressions import ParentWidth, TimeElapsed, Width

with xnano.open(width=40, height=3) as terminal:
    ball = terminal.write('●', y=1)
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
    terminal.write('press space', y=1)
    elapsed = terminal.write('  0.0s')

    @terminal.hook(on='key', keys='space')
    def toggle(context: xnano.Context) -> None:
        if context.time.is_stopped:
            context.canvas.resume()
        else:
            context.canvas.stop()

    @terminal.hook(on='tick', every=1.0)
    def tick(context: xnano.Context) -> None:
        elapsed.text = f'{context.time.elapsed:5.1f}s'

    terminal.run(quit_on='q')
```

`when=` narrows a hook with a string such as
`"mouse.position in buffer.region"`, an expression or a function. A hook on
`'drag'` is a generator: `context = yield` waits for the next movement.
`context.keyboard`, `context.mouse`, `context.scroll` and `context.clipboard`
are the inputs, and `context.root.state.get(path)` and `.push(path, value)` read
and write state that [`on='state'`][xnano.canvas.Canvas.hook] hooks follow.

## Components, art and sound

[`@xnano.renderable`][xnano.renderable] turns a function of
`(context, **parameters)` into a component that is drawn again only when it
read something that changes, such as the clock.
[`@xnano.playable`][xnano.playable] does the same for sound. `xnano.draw`
pixel art can hold other art and a camera, `xnano.play('C4 E4 G4:2')` plays a
melody written as text, and `canvas.color`, `canvas.border`, `canvas.padding`
and `canvas.margin` change how any canvas, placement or region looks. Run
`python -m xnano` to see the features working together; its source,
[`xnano.demo`][xnano.demo], is a larger example.

[`effect`][xnano.effect] builds an effect from a kind such as
`'effect.fade_from'` and its settings. Apply it to a placement with
`placement.update(...)` or `|`, or start one by name with
`placement.fx.fade_to(...)`:

```python
import xnano

with xnano.open(width=40, height=5) as terminal:
    title = terminal.write('xnano', x='center', y='center', border='rounded')
    fade = xnano.effect(
        'effect.fade_from', foreground='black', duration_milliseconds=1500
    )
    title.update(fade)
    terminal.run(quit_on='q')
```

[`Image`][xnano.Image] and [`load_image`][xnano.load_image] show pictures
(the `image` extra). [`Sound`][xnano.Sound] and
[`load_sound`][xnano.load_sound] are WAV sounds, and
[`Melody`][xnano.audio.Melody] is melody text parsed into notes (the `audio`
extra).

## Where everything lives

The top-level `xnano` holds the main API. Everything else is in a module named
for what it holds:

| Module | What it holds |
| --- | --- |
| [`xnano`][xnano] | The main API: `new`, `open`, `active`, `iter`, `Canvas`, `Terminal`, `Context`, `Color`, `hook`, `effect`, `write`, `box`, `draw`, `Pixel`, `Image`, `load_image`, `Sound`, `load_sound`, `Note`, `note`, `play`, `renderable`, `playable` and the `symbols` module. |
| [`xnano.canvas`][xnano.canvas] | The canvas: `Canvas`, `new`, `active`, `iter`. |
| [`xnano.terminal`][xnano.terminal] | The real screen: `Terminal`, `open`, `TerminalSettings`, `capabilities`, `TerminalCapabilities`, `KeyboardCapabilities`, `GraphicsCapabilities`. |
| [`xnano.placement`][xnano.placement] | A buffer placed on a canvas: `Placement`. |
| [`xnano.region`][xnano.region] | A rectangle of a canvas: `Region`, `box`, `write`, `Resolution`, `PixelAnchor`. |
| [`xnano.context`][xnano.context] | What a hook is called with: `Context`, `Frame`, `Update`, `Plugin`, `ReadLog`. |
| [`xnano.components`][xnano.components] | Components that draw or play themselves: `renderable`, `playable` and the component classes. |
| [`xnano.hooks`][xnano.hooks] | Reacting to events: `hook`, `HookHandle`, `Hook`, `HookKind`, `HookResult`, `When`. |
| [`xnano.effects`][xnano.effects] | Effects: `effect`, the effect kinds, the `<Kind>EffectParameters` classes such as `FadeToEffectParameters`, `EffectController`. |
| [`xnano.art`][xnano.art] | What is seen: `Art`, `Camera`, `draw`, `Pixel`, `PixelPreset`, `Image`, `load_image` (images need the `image` extra). |
| [`xnano.audio`][xnano.audio] | What is heard: `Note`, `note`, `play`, `PlayHandle`, `Melody`, `Sound`, `load_sound`, `AudioDevice`, `Microphone` and the instrument names (the `audio` extra). |
| [`xnano.appearance`][xnano.appearance] | How things look: `Colors`, `ColorSlot`, `BorderAppearance`, `BorderSide`, `Edges`, `PaddingAppearance`, `MarginAppearance`. |
| [`xnano.state`][xnano.state] | State: `StateNamespace`, `StatePath`. |
| [`xnano.time`][xnano.time] | The clock: `Time`. |
| [`xnano.cursor`][xnano.cursor] | The cursor: `Cursor`. |
| [`xnano.input`][xnano.input] | What a hook reads: `KeyboardInput`, `MouseInput`, `ScrollInput`, `ClipboardInput`. |
| [`xnano.output`][xnano.output] | What a canvas has drawn: `Output`. |
| [`xnano.expressions`][xnano.expressions] | Formulas such as `TerminalWidth`, `TerminalHeight`, `ParentWidth` and `TimeElapsed`. |
| [`xnano.operations`][xnano.operations] | Operations, including `Effect`, `CancelEffect`, `ContextualOperation` and the `Dynamic...` operations. |
| [`xnano.widgets`][xnano.widgets], [`xnano.styles`][xnano.styles], [`xnano.geometry`][xnano.geometry], [`xnano.events`][xnano.events], [`xnano.buffers`][xnano.buffers] | Re-exports of the core: widgets such as `Figure`, `Table` and `Gauge`, styles, geometry, events and buffers. |
| [`xnano.symbols`][xnano.symbols] | The registry of names for values. |
| [`xnano.errors`][xnano.errors] | `TerminalError` and the other errors a canvas raises. |
| [`xnano.types`][xnano.types] | The index of public types. |

Images need the optional `image` extra and sound the `audio` extra.
