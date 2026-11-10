---
title: Learn
icon: lucide/book-open
---

# Learn

These guides teach xnano, from the first line of code to a finished program.
Start with [Installation](installation.md). Then read
[Your First Program](first-program.md), where we build a small focus timer. The
timer uses the main ideas of xnano: a canvas, placements, hooks for keys and
time, a widget and a sound. Each guide after it explains one part in more
detail.

You need Python 3.10 to 3.14 and a terminal. The guides explain everything else
when you need it.

## The guides

| Guide | What you learn |
| --- | --- |
| [Installation](installation.md) | Install xnano and the optional extras for images and sound |
| [Your First Program](first-program.md) | Write text on a terminal, then make it react to keys and time |
| [Writing Content](content.md) | Set the position, size, box and layer of content |
| [Styling](styling.md) | Use colors, text modifiers, styles and borders |
| [Hooks & Input](input.md) | React to the keyboard and the mouse |
| [Time & Effects](time.md) | Use the clock and timers, and animate content with effects |
| [Widgets](widgets.md) | Show gauges, charts, tables and lists |
| [Images & Pixel Art](images.md) | Draw pixel art and load pictures |
| [Sound](sound.md) | Play notes and melodies, and listen to the microphone |
| [Testing](testing.md) | Test a program without a terminal: its screen, its keys and its time |

## Four ideas

All the guides use the same four ideas. Learn them before you start.

- A **canvas** is the area that you draw on. `xnano.new()` makes a canvas in
  memory, which you can use to draw one frame and print it. `xnano.open()`
  shows a canvas in your terminal window and returns it as a **terminal**.
- The **screen** of a canvas, `canvas.screen`, holds its cells. You **write**
  content on it with `canvas.write()`, which is the same as
  `canvas.screen.write()`. The call returns a **placement**, a live handle on
  the content that you wrote. When you change the text, color, position or size
  of a placement, the screen changes too.
- A **hook** is a function that xnano calls when something happens, for example
  a key press, a mouse click or a tick of the clock. xnano gives each hook a
  **context**, which holds the event and the devices.
- A **device** is one part of a terminal: the screen, the keyboard, the mouse,
  the clock, the speaker or the microphone. Each canvas has all six devices,
  and each context has them too.

## Words in these guides

| Word | Meaning |
| --- | --- |
| cell | One character position on the screen. Positions and sizes are in cells. |
| frame | One drawing of the screen. |
| widget | Ready-made content, such as a gauge, a chart, a table or a list. |
| expression | A value that xnano calculates again on each frame, such as `terminal.clock / 60`. |
| effect | An animation on content, such as a fade or a sweep. |
| layer | A level of content. Content on a higher layer covers content on a lower layer. |
| extra | An optional part of xnano that you install separately, such as `xnano[image]`. |

## After the guides

- Run the demo with `python -m xnano`. It shows the widgets, the effects, sound
  and input in one program, and its source is `xnano/demo.py`.
- Read the programs in the
  [`examples/`](https://github.com/hsaeed3/xnano/tree/main/examples) directory:
  four games, a dashboard, a form, a file picker and a log viewer.
- The [API reference](../api-reference/index.md) gives every function, class
  and parameter.
