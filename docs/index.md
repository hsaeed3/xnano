---
title: "xnano"
icon: "fontawesome/solid/x"
---

# xnano

<!-- The homepage's runnable example, shown after the features: the homepage
     template places what is between the two markers. It needs no files, so it
     runs as written in a terminal and in the browser with Pyodide. Until a
     visitor runs it, the page shows the output saved in
     docs/assets/home/hero-example.ansi, which tests/test_readme_examples.py
     keeps in step with the code. -->
<!-- xn-hero-example -->

```pyodide install="xnano"
import xnano
from xnano.styles import Style
from xnano.widgets import Gauge, Sparkline

requests = [3, 4, 6, 5, 7, 9, 8, 6, 7, 9, 10, 8, 6, 7] * 3
sparkline = Sparkline(requests, style=Style('cyan'))
gauge = Gauge(0.62, label='62% of 512 GB', gauge_style=Style('green'))

# a canvas draws in memory, so this runs in a terminal and in a browser
with xnano.new(width=44, height=7) as canvas:
    screen = canvas.screen
    screen.write('xnano', bold=True, foreground='magenta')
    screen.write('● online', x='right', y=0, foreground='green')
    screen.write(
        sparkline, width='100%', height=4, border='rounded', title='requests'
    )
    screen.write(gauge, width='100%', y='bottom')
    print(screen.render(format='ansi'))
```

<!-- /xn-hero-example -->

<!-- The homepage's examples, in the order they appear. Each one's text is
     markdown; figure="left" or "right" puts its animation on that side, and
     light and dark name the files shown in each color scheme. -->
<!-- markdownlint-disable MD013 -->
<features>
<feature title="Composable" figure="right" light="assets/home/widgets-light.gif" dark="assets/home/widgets-dark.gif" alt="A git client with a commit graph, branch tree and menus, drawn with xnano widgets">
    xnano is built on [`ratatui`'s](https://ratatui.rs/) layout and widget system, and provides an expressive API for composing the content displayed to the terminal.
</feature>

<feature title="Reactive" figure="left" light="assets/home/input-light.gif" dark="assets/home/input-dark.gif" alt="A small farming game running in the terminal with xnano">
    Create reactive components that respond to user input, time, and other factors at the speed you can think of them.
</feature>

<feature title="Audio Support" figure="right" light="assets/home/sound-light.gif" dark="assets/home/sound-dark.gif" alt="Pixel piano keys pressed as xnano plays their notes">
    xnano treats audio content as a first-class citizen, with the ability to synthesize music with MIDI patterns, play back audio files, and capture microphone input. It can even generate sound effects in real time.
</feature>

<feature title="Effects" figure="left" light="assets/home/effects-light.gif" dark="assets/home/effects-dark.gif" alt="Eight gradient cards in a grid, each playing in turn the tachyonfx effects named under it: dissolve and coalesce, sweeps, a hue shift, evolving symbols, slides, fades, paint and lighten">
    Anything on screen can dissolve, sweep, slide, fade or shift its colors with [`tachyonfx`](https://github.com/ratatui/tachyonfx)'s effects, each started by name with `placement.fx`. Sounds take [effects](api-reference/xnano/effects.md) such as reverb and delay the same way.
</feature>

<feature title="AI Native" figure="right" light="assets/home/ai-light.gif" dark="assets/home/ai-dark.gif" alt="A request for a now playing card typed into an xnano program, the program a model wrote for it shown beside the card it draws in the sandbox, then a second request that turns the card pink">
    [`xnano.ai`](api-reference/xnano/ai.md) lets models read the canvas and answer in xnano values: choices, verdicts, text, pixel art, widgets and melodies, and gives any pydantic-ai agent tools to see and change it. Code a model writes runs in a [sandbox](api-reference/xnano/sandbox.md) that can draw on the canvas but cannot reach files, the network or the rest of your program.
</feature>
</features>
<!-- markdownlint-enable MD013 -->
