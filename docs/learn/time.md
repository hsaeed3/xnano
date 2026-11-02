---
title: Time & Effects
icon: lucide/timer
---

# Time & Effects

Every canvas has a **clock**. The clock counts the time since the canvas
started, and it sets how many frames the canvas draws each second. You can also
pause it. Timers, values that change on each frame, and effects all follow the
clock.

## The clock

`terminal.clock.elapsed_seconds` is the time in seconds since the canvas
started. It does not include the time while the clock was paused. A canvas on
the screen draws at most 60 frames each second. To change this limit, give
`fps=` to `xnano.open()`.

```python
import xnano

with xnano.open(height=2, fps=30) as terminal:
    elapsed = terminal.screen.write('')

    @terminal.hook(on='frame')
    def show_time(context: xnano.Context):
        elapsed.text = f'{context.clock.elapsed_seconds:.1f}s'

    terminal.run(stop_on='q')
```

`on='frame'` runs a hook one time before each frame. Use it only for work that
must change on every frame. For work that runs less often, use a timer.

## Timers

`on='tick'` runs a hook on a timer. Give it one of these two arguments:

- `every=` runs the hook repeatedly, with that many seconds between two runs.
- `after=` runs the hook one time, that many seconds after you attach it.

<!-- @code-block name="learn-time-timers" type="gif" height=3
wait 4.5
-->
```python
import xnano

with xnano.open(height=3) as terminal:
    ticks = terminal.screen.write('tick 0')
    message = terminal.screen.write('')
    count = 0

    @terminal.hook(on='tick', every=1.0)
    def count_up(context: xnano.Context):
        global count
        count += 1
        ticks.text = f'tick {count}'

    @terminal.hook(on='tick', after=3.0)
    def say_hello(context: xnano.Context):
        message.text = 'three seconds have passed'

    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="learn-time-timers" -->

![learn-time-timers](../assets/examples/learn-time-timers-light.gif#only-light)
![learn-time-timers](../assets/examples/learn-time-timers-dark.gif#only-dark)

<!-- /@code-block-asset -->

Timers follow the clock, so they stop while the clock is paused.
`clock.pause()` stops the clock, and `clock.resume()` starts it again from the
same time. While the clock is paused, the canvas still draws and receives keys,
so a key hook can resume the clock. The
[focus timer](first-program.md#pause-with-a-key) uses both methods.

## Values that follow the clock

Arithmetic on the clock gives an **expression**. An expression is a value that
xnano calculates again on every frame. Assign an expression to a position, a
size or a number in a widget. The value then changes by itself, without a hook.

<!-- @code-block name="learn-time-expressions" type="gif" height=3
wait 4.0
-->
```python
import xnano
from xnano.expressions import ParentWidth

with xnano.open(height=3) as terminal:
    ball = terminal.screen.write('●', y=1, foreground='cyan')
    ball.x = (terminal.clock * 12) % ParentWidth  # >> [expression]
    terminal.screen.write('q quit', y='bottom', dim=True)
    terminal.run(stop_on='q')
```

<comments>
<tag name="expression" color="amber">
The ball moves 12 cells each second. At the right edge, it starts again at the
left edge. In arithmetic, `terminal.clock` is the elapsed seconds. `ParentWidth`
is the width of the screen that holds the ball, and it follows the window when
the user changes the window size.
</tag>
</comments>

<!-- @code-block-asset name="learn-time-expressions" -->

![learn-time-expressions](../assets/examples/learn-time-expressions-light.gif#only-light)
![learn-time-expressions](../assets/examples/learn-time-expressions-dark.gif#only-dark)

<!-- /@code-block-asset -->

A canvas with an expression on it draws every frame, because the time always
changes. A layout that only follows the size of the window does not need an
expression. For that layout, use percentages such as `width='50%'` and words
such as `x='center'`. xnano calculates these values again only when the size of
the window or the size of the content changes. The
[`xnano.expressions`][xnano.expressions] reference lists all of the expressions.

## Effects

An **effect** is a short animation of how content looks. For example, an effect
fades, dissolves, sweeps or slides the content, or it shifts the colors.

Each placement has an `fx` property, with one method for each effect. Call a
method to start its effect. `duration_milliseconds` sets the length of the
effect. Without it, most effects take 500 milliseconds.

<!-- @code-block name="learn-time-effects" type="gif" height=6
wait 1.2
press 1
wait 1.2
press 2
wait 1.2
press 3
wait 1.4
-->
```python
import xnano

with xnano.open(height=6) as terminal:
    card = terminal.screen.write(
        'xnano',
        border='rounded',
        padding={'horizontal': 4, 'vertical': 1},
        foreground='magenta',
    )
    terminal.screen.write('1 sweep · 2 coalesce · 3 fade · q quit', y='bottom', dim=True)
    card.fx.fade_from(foreground='black', duration_milliseconds=800)  # >> [start]

    @terminal.hook(on='key', keys='1')
    def sweep(context: xnano.Context):
        card.fx.sweep_in(color='cyan', duration_milliseconds=600)

    @terminal.hook(on='key', keys='2')
    def coalesce(context: xnano.Context):
        card.fx.coalesce(duration_milliseconds=600)

    @terminal.hook(on='key', keys='3')
    def fade(context: xnano.Context):
        card.fx.fade_from(foreground='yellow', duration_milliseconds=600)

    terminal.run(stop_on='q')
```

<comments>
<tag name="start" color="pink">
Fades the card in from black when the program starts.
</tag>
</comments>

<!-- @code-block-asset name="learn-time-effects" -->

![learn-time-effects](../assets/examples/learn-time-effects-light.gif#only-light)
![learn-time-effects](../assets/examples/learn-time-effects-dark.gif#only-dark)

<!-- /@code-block-asset -->

An effect method returns the running effect. To stop the effect early, call
`cancel()` on it. The canvas also has an `fx` property, for an effect on all of
the canvas.

This table gives some of the effects:

| Effects | What they do |
| --- | --- |
| `fade_from`, `fade_to` | Fade the colors in from a color, or out to a color. |
| `dissolve`, `coalesce` | Take the content apart cell by cell, or put it together cell by cell. |
| `sweep_in`, `sweep_out` | Show or hide the content behind a band of color that moves across it. |
| `slide_in`, `slide_out` | Move the content in or out, in a direction. |
| `hsl_shift`, `lighten`, `darken`, `saturate` | Change the hue, the lightness or the saturation of the colors. |
| `paint` | Paint a foreground color and a background color over the content. |
| `glitch` | Show a short glitch on some of the cells. |

The effects come from [tachyonfx](https://github.com/ratatui/tachyonfx), a Rust
library of terminal effects. The [`xnano.effects`][xnano.effects] reference
lists every effect and its settings.

Use an effect only when it has a purpose. A good effect confirms a change, or
shows the user where the change is. A bad effect makes the user wait for the
result. Keep an effect that answers a key press between 150 and 300
milliseconds. Longer effects are good for an entrance, or for a demonstration
like the example above.
