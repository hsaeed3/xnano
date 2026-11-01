---
title: Styling
icon: lucide/palette
---

# Styling

Every `write()` takes the same styling keywords: a `foreground` and a
`background` color, text modifiers such as `bold` and `dim`, and a border. This
guide covers each of them, how to change them later, and how to choose colors
that read well on any terminal.

## Colors

A color can be given three ways: by name, as a hex string, or as a
`(red, green, blue)` tuple.

<!-- @code-block name="learn-styling-colors" type="image" height=5 -->
```python
import xnano

with xnano.new(width=40, height=4) as canvas:
    canvas.screen.write('a named color', foreground='cyan')
    canvas.screen.write('a hex color', foreground='#e8768a')
    canvas.screen.write('a red, green, blue tuple', foreground=(148, 108, 230))
    canvas.screen.write(' on a background ', foreground='black', background='yellow')
    print(canvas.screen.render(format='ansi'))
```

<!-- @code-block-asset name="learn-styling-colors" -->

![learn-styling-colors](../assets/examples/learn-styling-colors-light.png#only-light)
![learn-styling-colors](../assets/examples/learn-styling-colors-dark.png#only-dark)

<!-- /@code-block-asset -->

The names are the 16 colors every terminal has: `black`, `red`, `green`,
`yellow`, `blue`, `magenta`, `cyan`, `white`, `gray` and their `light_` versions
such as `light_blue`.

## Text modifiers

`bold`, `dim`, `italic`, `underline`, `reverse` and `crossed_out` each take
`True`. They combine with each other and with colors.

<!-- @code-block name="learn-styling-modifiers" type="image" height=7 -->
```python
import xnano

with xnano.new(width=40, height=6) as canvas:
    canvas.screen.write('bold', bold=True)
    canvas.screen.write('dim', dim=True)
    canvas.screen.write('italic', italic=True)
    canvas.screen.write('underline', underline=True)
    canvas.screen.write('reverse', reverse=True)
    canvas.screen.write('crossed out', crossed_out=True)
    print(canvas.screen.render(format='ansi'))
```

<!-- @code-block-asset name="learn-styling-modifiers" -->

![learn-styling-modifiers](../assets/examples/learn-styling-modifiers-light.png#only-light)
![learn-styling-modifiers](../assets/examples/learn-styling-modifiers-dark.png#only-dark)

<!-- /@code-block-asset -->

Not every terminal draws every modifier: `italic` needs a font with an italic
face, and some terminals show `blink` as plain text.

## Changing styles later

A placement's colors live in its `color`: assign `color.fg` and `color.bg`. Each
modifier is a method, so `label.bold()` makes text bold and `label.bold(False)`
undoes it. The `is_bold` property (and `is_dim`, `is_italic`, and so on) reads
it back.

```python
import xnano

with xnano.new(width=30, height=1) as canvas:
    label = canvas.screen.write('status: ok', foreground='green')

    label.color.fg = 'yellow'
    label.color.bg = 'black'
    label.bold().underline()
    assert label.is_bold and label.is_underlined

    label.underline(False)
    print(canvas.screen.render(format='ansi'))
```

The methods return the placement, so they chain: `label.bold().underline()`.

## Reusing a style

A [`Style`][xnano.styles.Style] holds a color and modifiers together, so one
look can be given to many things. The keywords of `write()` apply on top of it.

<!-- @code-block name="learn-styling-style" type="image" height=4 -->
```python
import xnano
from xnano.styles import Style

heading = Style('magenta', bold=True)

with xnano.new(width=40, height=3) as canvas:
    canvas.screen.write('Overview', style=heading)
    canvas.screen.write('Details', style=heading, underline=True)
    canvas.screen.write('Plain text')
    print(canvas.screen.render(format='ansi'))
```

<!-- @code-block-asset name="learn-styling-style" -->

![learn-styling-style](../assets/examples/learn-styling-style-light.png#only-light)
![learn-styling-style](../assets/examples/learn-styling-style-dark.png#only-dark)

<!-- /@code-block-asset -->

## Several styles in one line

A line whose parts look different is a [`StyledText`][xnano.styles.StyledText]:
a list of spans, each with its own style. Write it inside a `Paragraph`.

<!-- @code-block name="learn-styling-spans" type="image" height=3 -->
```python
import xnano
from xnano.styles import Style, StyledText, TextSpan
from xnano.widgets import Paragraph

with xnano.new(width=40, height=2) as canvas:
    line = StyledText(
        [
            TextSpan('✓ ', style=Style('green', bold=True)),
            TextSpan('12 tests passed '),
            TextSpan('in 0.4s', style=Style(dim=True)),
        ]
    )
    canvas.screen.write(Paragraph(line), width='100%')
    print(canvas.screen.render(format='ansi'))
```

<!-- @code-block-asset name="learn-styling-spans" -->

![learn-styling-spans](../assets/examples/learn-styling-spans-light.png#only-light)
![learn-styling-spans](../assets/examples/learn-styling-spans-dark.png#only-dark)

<!-- /@code-block-asset -->

## Borders

`border` picks the kind of line, and `border_style` colors it separately from
the text inside.

<!-- @code-block name="learn-styling-borders" type="image" height=4 -->
```python
import xnano
from xnano.styles import Style

with xnano.new(width=40, height=3) as canvas:
    canvas.screen.write(
        'all systems normal',
        border='rounded',
        border_style=Style('green'),
        title='status',
        padding={'horizontal': 1},
    )
    print(canvas.screen.render(format='ansi'))
```

<!-- @code-block-asset name="learn-styling-borders" -->

![learn-styling-borders](../assets/examples/learn-styling-borders-light.png#only-light)
![learn-styling-borders](../assets/examples/learn-styling-borders-dark.png#only-dark)

<!-- /@code-block-asset -->

## Choosing colors

People run terminals with light themes and dark themes, and each theme picks its
own shade of every named color. A few habits keep a program readable on all of
them:

- **Prefer named colors and `dim`.** They follow the user's theme. A hex or
  tuple color is drawn exactly as written, so it can vanish against the other
  background. Keep exact colors for when the color itself is the content, such
  as art and gradients.
- **Give each color one meaning.** Green for success, yellow for a warning, red
  for an error, blue or cyan for information, and keep to it across the whole
  program.
- **Never let color carry a meaning alone.** Some people can't tell red from
  green, and some terminals show no color at all. Pair a color with a word or a
  symbol: `● online`, `▲ slow`.
- **Build hierarchy from weight, not size.** A terminal has one text size. Make
  titles and keys `bold`, leave content plain, and `dim` the hints.
