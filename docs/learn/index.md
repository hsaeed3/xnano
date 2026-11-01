---
title: Learn
icon: lucide/book-open
---

# Learn

These guides teach xnano from the first line to a finished program. Start with
[Installation](installation.md) and [Your First Program](first-program.md),
which builds a small focus timer from xnano's core ideas: a canvas, placements,
hooks on keys and time, a widget and a sound. The guides after it take one part
at a time and go deeper.

All you need is Python 3.10 to 3.14 and a terminal. Everything else is
explained as it comes up.

## The guides

| Guide | What you learn |
| --- | --- |
| [Installation](installation.md) | Install xnano and its optional image and audio extras |
| [Your First Program](first-program.md) | Draw on a terminal, then react to keys and time |
| [Writing Content](content.md) | Place, size and arrange anything on the screen |
| [Styling](styling.md) | Colors, text modifiers, borders and padding |
| [Hooks & Input](input.md) | React to the keyboard and the mouse |
| [Time & Effects](time.md) | Follow the clock, run timers and animate with effects |
| [Widgets](widgets.md) | Gauges, charts, tables and lists |
| [Images & Pixel Art](images.md) | Draw pixel art and load pictures |
| [Sound](sound.md) | Play notes and melodies, and listen to the microphone |

## Four ideas

Every guide builds on the same four ideas, so they are worth knowing before you
start.

- A **canvas** is a terminal you draw on. `xnano.open()` puts one on your
  screen, and `xnano.new()` makes one in memory, which is how you draw a single
  frame and print it.
- **Writing** something with `screen.write()` gives back a **placement**: a
  live handle on what you wrote. Change its text, color, position or size at any
  time, and the screen follows.
- A **hook** is a function that runs when something happens: a key press, a
  click, a tick of the clock.
- **Devices** are the parts of a terminal: its screen, keyboard, mouse, clock,
  speaker and microphone. A canvas has all of them, and so does every hook.

When you want every parameter of something, the [API
reference](../api-reference/index.md) lists it, generated from the source.
