<!-- markdownlint-disable-next-line MD041 -->
> [!IMPORTANT]
> **v2!**
> `xnano` has been rewritten from the ground up, with a much faster and more
> flexible API. The rewrite is not backwards compatible with the previous
> version: the documentation of `xnano`'s original grid & field based API lives
> in the [`v1` branch](https://github.com/hsaeed3/xnano/tree/v1).

<div align="center">

# **xnano**

An _extremely nano_ terminal experience for Python, built on [`ratatui`](https://ratatui.rs/).

[![License](https://img.shields.io/github/license/hsaeed3/xnano)](./LICENSE)
[![Downloads](https://static.pepy.tech/badge/xnano/month)](https://pepy.tech/project/xnano)
[![Python Versions](https://img.shields.io/pypi/pyversions/xnano)](https://pypi.org/project/xnano)
[![CodSpeed](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://app.codspeed.io/hsaeed3/xnano?utm_source=badge)
[![Built With Ratatui](https://ratatui.rs/built-with-ratatui/badge.svg)](https://ratatui.rs/)

[Documentation](https://xnano.hammad.app) ·
[Learn](https://xnano.hammad.app/learn/) ·
[API Reference](https://xnano.hammad.app/api-reference/) ·
[Contribution Guide](./CONTRIBUTING.md)

</div>

---

`xnano` is a terminal framework for Python, with an API that is quick to learn and
flexible enough to grow with your program. With `xnano` you can:

- **Draw** text, widgets, pixel art and images anywhere in your terminal window.
- **React** to keys, the mouse and the clock with hooks.
- **Play** notes and melodies, and listen to the microphone, with
  [`xnano-audio`](https://github.com/hsaeed3/xnano/tree/main/packages/xnano-audio).
- **Build without a terminal**: a canvas from `xnano.new()` draws into memory,
  so you can print it, test it, and show it on the screen when you are ready.

## Requirements

- Python 3.10 to 3.14.
- Linux (x86_64 or aarch64, glibc or musl), macOS (Intel or Apple silicon) or Windows
  (x86_64). Each of these has pre-built wheels, so no Rust toolchain is needed.

## Installation

Install `xnano` from [PyPI](https://pypi.org/project/xnano):

```bash
pip install xnano
```

Images and sound are optional extras. When you use a feature whose extra is missing,
`xnano` tells you which one to install.

```bash
pip install "xnano[image]"  # pictures: .png, .jpg, .gif, .webp
pip install "xnano[audio]"  # sound: the speaker and the microphone
```

On Linux, playing sound on a device needs ALSA (`libasound`). Composing and rendering
sound work without a device everywhere.

## Quick Start

### Create it

Create a file `main.py` with:

<!-- @code-block name="hello-world" type="image" height=5 -->
```python
import xnano

with xnano.open() as terminal:
    terminal.write('Hello, world!', x='center', y='center')
    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="hello-world" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/hello-world-dark.png">
  <img alt="hello-world" src="docs/assets/readme/hello-world-light.png">
</picture>
<!-- /@code-block-asset -->

### Run it

```bash
python main.py
```

`Hello, world!` appears in the middle of your terminal window, and stays there
until you press `q`. You already have a program that:

- opens a live terminal with `xnano.open()`, which takes over the whole window
  (give it a `height` to draw in a region below your prompt instead),
- writes text with `terminal.write()`, at a position such as `'center'`,
- keeps running with `terminal.run()` until one of its `stop_on` keys is pressed.

### Example upgrade

Now make the text change color when you click it. Update `main.py`:

<!-- @code-block name="click-to-change-color" type="gif" height=5
wait 0.5
click 55 2
wait 0.5
click 55 2
wait 0.5
click 55 2
wait 0.5
click 55 2
wait 0.5
click 55 2
wait 0.5
click 55 2
wait 0.5
-->
```python
import xnano

# `mouse=True` turns on mouse events
with xnano.open(mouse=True) as terminal:
    greeting = terminal.write('Hello, world!', x='center', y='center')

    # a hook runs a function when something happens, and a hook on a placement only
    # hears the events inside its own cells
    @greeting.hook(on='mouse')
    def change_color(context: xnano.Context):
        # a click is a press and then a release: change the color once, on the press
        if context.mouse.kind == 'press':
            greeting.color.fg.random()

    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="click-to-change-color" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/click-to-change-color-dark.gif">
  <img alt="click-to-change-color" src="docs/assets/readme/click-to-change-color-light.gif">
</picture>
<!-- /@code-block-asset -->

Run `python main.py` again and click `Hello, world!`: every click gives it a new
color.

### Recap

- `xnano.open()` is a live terminal. `xnano.new()` makes a canvas in memory,
  which you can print, or show in a terminal later. Both have the same `screen`,
  `clock`, `keyboard`, `mouse` and `speaker`.
- `terminal.write()` and `canvas.write()` place text, widgets and images with a
  number of cells, a percentage or a word. Each is the same as `screen.write()`,
  and each returns a placement that you can change at any time.
- `hook(on=...)` runs a function when a key, the mouse or the clock does
  something, and the `context` it receives says what happened.

For a step-by-step introduction, see [Learn](https://xnano.hammad.app/learn/) in
the documentation.

## Core Features & Examples

Every example below is a complete program: copy it into a file and run it. Press
`q` to leave the live ones.

<details>
<summary>Composing Content</summary>

The `Canvas` is a stateful builder for a rectangular region of a terminal
screen, from a one-line header to a multi-window layout. A canvas from
`xnano.new()` draws into memory, so it can be printed without a live terminal.

<!-- @code-block name="composing-content" type="image" height=8 -->
```python
import xnano

# `layout='row'` gives everything written on the canvas an equal share of its width,
# and `x` and `y` place each piece inside its own share
with xnano.new(width='100%', height=7, layout='row') as canvas:
    canvas.write(
        'left panel', x='left', y='bottom', border='plain', foreground=(255, 0, 0)
    )
    canvas.write(
        'center panel',
        x='center',
        y='center',
        border='rounded',
        foreground='black',
        background='#f0f0f0',
    )
    canvas.write(
        'right panel', x='right', y='top', border='thick', foreground='blue'
    )

    # render one frame of the screen as colored text, and print it
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="composing-content" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/composing-content-dark.png">
  <img alt="composing-content" src="docs/assets/readme/composing-content-light.png">
</picture>
<!-- /@code-block-asset -->

</details>

<details>
<summary>Positioning & Sizing Content</summary>

Positions and sizes all take the same forms: a number of cells, a percentage of
the space around the content, or a word such as `'center'` or `'bottom'`.
Percentages and words are kept, not computed once, so content stays where you
put it when the window or the content changes. Positions can also be expressions
that change on every frame (see the **Clock** example) or ranges that limit how
far content can move (see the **Mouse** example).

<!-- @code-block name="positioning-and-sizing" type="image" height=8 -->
```python
import xnano

with xnano.new(width='100%', height=7) as canvas:
    # content written without a position goes on the next line, the way a terminal prints
    canvas.write('first line')
    canvas.write('second line')

    # a position or a size is a number of cells, a percentage or a word
    canvas.write('x=40', x=40, y=0)
    canvas.write("x='75%'", x='75%', y=1)
    canvas.write("x='right', y='bottom'", x='right', y='bottom')
    panel = canvas.write('panel', x='center', y='center', width='50%', border='rounded')

    # a placement takes new values at any time, and its words follow: it stays centered
    panel.width = '60%'
    canvas.write(
        f'the panel is {panel.width} cells wide, from column {panel.x}', y='bottom'
    )

    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="positioning-and-sizing" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/positioning-and-sizing-dark.png">
  <img alt="positioning-and-sizing" src="docs/assets/readme/positioning-and-sizing-light.png">
</picture>
<!-- /@code-block-asset -->

</details>

<details>
<summary>Styling Content</summary>

All of [`ratatui`'s styling](https://ratatui.rs/examples/style/) is available in
`xnano`, as keywords of `screen.write()` (`foreground`, `background`, `bold`,
`italic`, `border`, `title`, ...) and as attributes of what it returns
(`placement.color.fg`). This includes:

- [Background & foreground colors](https://ratatui.rs/examples/style/colors/):
  names such as `'red'`, `'#rrggbb'` strings, `(red, green, blue)` tuples, the
  256 ANSI colors (`xnano.Color.indexed(208)`) and Tailwind's palette
  (`xnano.Color.from_tailwind('sky', 500)`).
- [Text modifiers](https://ratatui.rs/examples/style/modifiers/): bold, dim, italic,
  underline, blink, reverse, hidden and crossed out.
- [Borders & border styling](https://ratatui.rs/recipes/widgets/block/):
  `'plain'`, `'rounded'`, `'double'` and `'thick'` borders, with a title and a
  style of their own.

</details>

<details>
<summary>Terminal and Terminal Devices</summary>

`xnano.open()` returns a `Terminal`: a canvas on your real screen that runs by
itself. Every canvas, live or not, has the same devices: `canvas.clock`,
`canvas.screen` and the others below (and `context.clock` and so on inside a
hook).

- `Clock`: the time of the canvas, its frame rate (`fps`) and tempo (`bpm`), and
  pausing and resuming everything that follows it.
- `Screen`: the cells the canvas draws, and `write()` to put content on them.
- `Keyboard` & `Mouse`: the key presses, pastes, clicks, drags and scrolls the canvas
  receives. They can also press keys and buttons for your program.
- `Speaker`: plays notes, melodies and sound files. <small>(Requires `xnano-audio`)</small>
- `Microphone`: the level of the sound coming in from the system's microphone.
  <small>(Requires `xnano-audio`)</small>

<details>
<summary><strong>Terminal</strong></summary>

<!-- @code-block name="terminal" type="gif" height=3
wait 0.5
press space
wait 0.2
press space
wait 2.0
press space
wait 1.3
press space
wait 5.1
press space
wait 1.0
-->
```python
import xnano

# give `xnano.open()` a `height` to draw in a region below your prompt, or leave it out
# to take over the whole window
with xnano.open(height=3, title='my app') as terminal:
    terminal.write('Welcome to xnano!', border='rounded')
    label = terminal.write('press space', x=22, y=1)

    # a hook on the terminal itself hears every event on the screen
    @terminal.hook(on='key', keys='space')
    def pressed(context: xnano.Context):
        label.text = f'space at {context.clock.elapsed_seconds:.1f}s'

    # `run()` keeps the terminal open until one of the `stop_on` keys is pressed
    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="terminal" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/terminal-dark.gif">
  <img alt="terminal" src="docs/assets/readme/terminal-light.gif">
</picture>
<!-- /@code-block-asset -->
</details>

<details>
<summary><strong>Clock</strong></summary>

<!-- @code-block name="clock" type="gif" height=3
wait 4.5
press space
wait 2.5
press space
wait 4.5
-->
```python
import xnano
from xnano.expressions import ParentWidth

with xnano.open(height=3) as terminal:
    label = terminal.write('')
    ball = terminal.write('●', y=1)

    # math with the clock makes an expression, which moves the ball on every frame;
    # `ParentWidth` is the screen's width, read again when the window is resized
    ball.x = (terminal.clock * 10) % ParentWidth

    # tick hooks run on a timer, measured in seconds of the clock
    @terminal.hook(on='tick', every=1.0)
    def show_time(context: xnano.Context):
        label.text = f'{context.clock.elapsed_seconds:.0f}s on the clock'

    # `pause()` freezes everything that follows the clock, and `resume()` lets it run on
    @terminal.hook(on='key', keys='space')
    def toggle(context: xnano.Context):
        if context.clock.is_paused:
            context.clock.resume()
        else:
            context.clock.pause()
            label.text = 'paused: press space to resume'

    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="clock" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/clock-dark.gif">
  <img alt="clock" src="docs/assets/readme/clock-light.gif">
</picture>
<!-- /@code-block-asset -->
</details>

<details>
<summary><strong>Screen</strong></summary>

<!-- @code-block name="screen" type="image" height=8 -->
```python
import xnano

# each service's response time, and its requests over the last 30 seconds
services = {
    'api': ('41 ms', '▂▃▃▅▃▂▃▅▆▅▃▂▃▅▆▅▃▂▂▃▅▃▂▃▅▆▅▃▂▃'),
    'web': ('870 ms', '▃▅▆▅▃▂▂▃▅▇██▇▇█▇▅▆▇██▇▆▇█▇▆▅▆▇'),
    'worker': ('12 ms', '▁▁▂▁▁▃▁▁▁▂▅▂▁▁▁▂▁▁▃▂▁▁▁▂▁▁▁▂▃▁'),
}

# a canvas from `xnano.new()` needs no live terminal: `width='100%'` fills the window
with xnano.new(width='100%', height=7) as canvas:
    screen = canvas.screen
    screen.write('services', bold=True)
    screen.write(f'{screen.width}×{screen.height} cells', x='right', y=0, dim=True)

    cards = {}
    for index, (name, (latency, graph)) in enumerate(services.items()):
        cards[name] = screen.write(
            ['● online', f'p95 {latency}', graph],
            x=f'{index * 34}%',
            y=1,
            width='32%',
            border='rounded',
            title=name,
            foreground='green',
        )

    # `write()` returns a live placement: its text and colors can change at any time
    cards['web'].text = cards['web'].text.replace('● online', '▲ slow responses')
    cards['web'].color.fg = 'yellow'

    # and they can be read back, like any other value
    healthy = sum(card.text.startswith('●') for card in cards.values())
    screen.write(f'{healthy} of {len(cards)} services healthy', y='bottom', dim=True)

    print(screen.render(format='ansi'))
```

<!-- @code-block-asset name="screen" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/screen-dark.png">
  <img alt="screen" src="docs/assets/readme/screen-light.png">
</picture>
<!-- /@code-block-asset -->
</details>

<details>
<summary><strong>Keyboard</strong></summary>

<!-- @code-block name="keyboard" type="gif" height=8
wait 0.8
press up
wait 0.08
press up
wait 0.08
press up
wait 0.08
press up
wait 0.08
wait 0.6
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
press right
wait 0.08
wait 0.6
press down
wait 0.08
press down
wait 0.08
press down
wait 0.08
wait 0.6
press left
wait 0.08
press left
wait 0.08
press left
wait 0.08
press left
wait 0.08
press left
wait 0.08
wait 0.6
press ctrl+r
wait 1.2
-->
```python
import xnano

# `edges='stop'` keeps content inside the terminal when it moves
with xnano.open(height=8, edges='stop') as terminal:
    player = terminal.write('@', x='center', y='center')
    terminal.write(
        'arrows or wasd to move · ctrl+r to reset · q to quit', y='bottom', dim=True
    )

    # `on='key'` hooks run on every key press, and again while a key repeats
    @terminal.hook(on='key')
    def move(context: xnano.Context):
        # `direction()` reads the arrow keys (or wasd) as one step along each axis
        step_x, step_y = context.keyboard.direction()
        player.move(step_x, step_y)

    # `keys=` narrows a hook to one key, or to a binding with modifiers
    @terminal.hook(on='key', keys='ctrl+r')
    def reset(context: xnano.Context):
        player.x, player.y = 'center', 'center'

    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="keyboard" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/keyboard-dark.gif">
  <img alt="keyboard" src="docs/assets/readme/keyboard-light.gif">
</picture>
<!-- /@code-block-asset -->
</details>

<details>
<summary><strong>Mouse</strong></summary>

<!-- @code-block name="mouse" type="gif" height=3
wait 0.8
drag 0 1 22 1
wait 1.2
drag 22 1 9 1
wait 1.5
-->
```python
import xnano

# `mouse=True` turns on mouse events
with xnano.open(height=3, mouse=True) as terminal:
    terminal.write('─' * 30, y=1)
    label = terminal.write('drag the ●', y=2)

    # a range keeps the thumb's `x` between two columns, however far it is dragged
    thumb = terminal.write('●', x=(0, 29), y=1)

    # a drag hook is a generator: each `yield` waits for the next movement of the pointer
    @thumb.hook(on='drag')
    def slide(context: xnano.Context):
        while context.mouse.is_down:
            thumb.x = context.parent.local(context.mouse.position).x
            context = yield
        label.text = f'dropped at {thumb.x}'

    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="mouse" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/mouse-dark.gif">
  <img alt="mouse" src="docs/assets/readme/mouse-light.gif">
</picture>
<!-- /@code-block-asset -->
</details>

<details>
<summary><strong>Speaker</strong></summary>

Notes and melodies are plain values. A live terminal plays them through its
speaker, and outside one, `xnano.play()` plays them through your computer's
sound output.

<!-- @code-block name="speaker" type="gif" height=3
wait 2.2
press 1
wait 0.5
press 3
wait 0.5
press 5
wait 0.5
press space
wait 1.8
-->
```python
import xnano

scale = ['C4', 'D4', 'E4', 'G4', 'A4']
chord = xnano.Note(('C4', 'E4', 'G4'), beats=2, instrument='electric_piano')

with xnano.open(height=2) as terminal:
    terminal.write('press 1-5 for a note, space for a chord')
    playing = terminal.write('', y=1, foreground='cyan')

    @terminal.hook(on='key')
    def play_note(context: xnano.Context):
        key = context.keyboard.key
        if key in ('1', '2', '3', '4', '5'):
            pitch = scale[int(key) - 1]
            playing.text = f'♪ {pitch}'
            note = xnano.Note(pitch, beats=0.5)
        elif key == 'space':
            playing.text = '♪ C4 E4 G4'
            note = chord
        else:
            return
        # a computer without a sound output device (over SSH, for example) only shows it
        if context.speaker.is_available:
            context.speaker.play(note)

    # a melody can also be written as text: a pitch, and its length in beats after a `:`
    if terminal.speaker.is_available:
        terminal.speaker.play('C4 E4 G4:2', instrument='piano')
    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="speaker" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/speaker-dark.gif">
  <img alt="speaker" src="docs/assets/readme/speaker-light.gif">
</picture>
<!-- /@code-block-asset -->
</details>

<details>
<summary><strong>Microphone</strong></summary>

<!-- @code-block name="microphone" type="image" height=3
wait 1.5
-->
```python
import xnano

with xnano.open(height=2) as terminal:
    terminal.write('speak into your microphone')

    # `level` is an expression from 0.0 to 1.0, so content can follow it on every frame
    # (the default input device opens the first time a frame reads it)
    level = terminal.microphone.level
    terminal.write('░' * 40, x=0, y=1, dim=True)
    terminal.write(
        '█' * 40, x=0, y=1, width=level * 40 + 1, foreground='green', layer=1
    )

    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="microphone" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/microphone-dark.png">
  <img alt="microphone" src="docs/assets/readme/microphone-light.png">
</picture>
<!-- /@code-block-asset -->
</details>

</details>

<details>
<summary>Terminal Widgets</summary>

All of [`ratatui`'s built-in widgets](https://ratatui.rs/concepts/widgets/) are
in `xnano.widgets`, where ratatui's `List` is `ItemList` and its `Canvas` is
`Figure`. A widget is written, sized and bordered like any other content:

<!-- @code-block name="widgets" type="image" height=13
wait 0.5
-->
```python
import math

import xnano
from xnano.styles import Style
from xnano.widgets import Bar, BarChart, Gauge, Sparkline, Table, TableCell, TableRow

# requests per second over the last 98 seconds
requests = [
    round(6 + 3 * math.sin(second / 5) + 2 * math.sin(second / 2)) for second in range(98)
]

with xnano.open(height=13) as terminal:
    terminal.write(
        Gauge(0.6, label='60% of 512 GB', gauge_style=Style(foreground='green')),
        width='100%',
        border='rounded',
        title='disk',
    )
    terminal.write(
        Sparkline(requests, style=Style(foreground='cyan')),
        width='100%',
        height=4,
        border='rounded',
        title='requests',
    )
    load = terminal.write(
        BarChart(
            [
                Bar(73, label='cpu'),
                Bar(41, label='memory'),
                Bar(18, label='network'),
                Bar(56, label='disk io'),
            ],
            bar_width=8,
            bar_gap=3,
            bar_style=Style(foreground='magenta'),
        ),
        width='48%',
        height=6,
        border='rounded',
        title='load',
    )
    # a placement's position can be read back, so the table lines up with the chart
    terminal.write(
        Table(
            [
                ['web', 'up', '41 ms'],
                ['api', 'up', '12 ms'],
                ['db', TableCell('down', style=Style(foreground='red')), '—'],
            ],
            header=TableRow(['service', 'status', 'p95'], style=Style(bold=True)),
        ),
        x='right',
        y=load.y,
        width='48%',
        height=6,
        border='rounded',
        title='services',
    )
    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="widgets" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/widgets-dark.png">
  <img alt="widgets" src="docs/assets/readme/widgets-light.png">
</picture>
<!-- /@code-block-asset -->

</details>

<details>
<summary>Images & Pixel Art</summary>

Pixel art is written as text in your code with `xnano.pixel_art()`. Pictures are
loaded from files with `xnano.load_image()`, from the `xnano-image` package
(built on [`ratatui-image`](https://github.com/ratatui/ratatui-image)).

### Pixel Art

<!-- @code-block name="pixel-art" type="image" height=6 -->
```python
import xnano

# each character is one pixel: the palette names the colors, and `.` is see-through
heart = xnano.pixel_art(
    """
    ..RR...RR..
    .RWWR.RRRR.
    RRWRRRRRRRR
    RRRRRRRRRRR
    .RRRRRRRRR.
    ..RRRRRRR..
    ...RRRRR...
    ....RRR....
    .....R.....
    """,
    'R=#e03040 W=#ffffff',
)

# two pixels fit in one cell, one above the other, so the heart takes 11 by 5 cells
print(xnano.region(heart).render(format='ansi'))
```

<!-- @code-block-asset name="pixel-art" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/pixel-art-dark.png">
  <img alt="pixel-art" src="docs/assets/readme/pixel-art-light.png">
</picture>
<!-- /@code-block-asset -->

### Images

Images need the `image` extra:

```bash
pip install "xnano[image]"
```

A picture can be loaded and printed without opening a live terminal:

<!-- @code-block name="images" type="image" height=31 -->
```python
import pathlib

import xnano

# this picture ships with xnano, so the example runs anywhere: use any path of your own
path = pathlib.Path(xnano.__file__).parent / 'assets' / 'dusk.png'

# `.png`, `.jpg`, `.webp` and animated `.gif` files load, sized in cells or a percentage
picture = xnano.load_image(path, width='100%')

# `xnano.region()` draws content into cells without a terminal, so it can be printed
print(xnano.region(picture).render(format='ansi'))
```

<!-- @code-block-asset name="images" -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/images-dark.png">
  <img alt="images" src="docs/assets/readme/images-light.png">
</picture>
<!-- /@code-block-asset -->

</details>

## Learn More

- [Documentation](https://xnano.hammad.app): the documentation site.
- [Learn](https://xnano.hammad.app/learn/): a step-by-step introduction.
- [API Reference](https://xnano.hammad.app/api-reference/): every public module,
  class and function.
- [Contribution Guide](./CONTRIBUTING.md): how to set up the development
  workspace, make changes and open a pull request.

`xnano` is released under the [MIT License](./LICENSE).
