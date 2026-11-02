---
title: Styling
icon: lucide/palette
---

# Styling

Each `write()` call accepts the same style keywords:

- `foreground` and `background` set the colors.
- Text modifiers, such as `bold` and `dim`, change how the text looks.
- `border` and `border_style` put a box around the content and set its color.

This guide shows each of them. It also shows how to change a style after you
write the content, and how to choose colors that show clearly in all terminal
themes.

## Colors

You can give a color in three forms:

- A name, such as `'cyan'`.
- A hex string, such as `'#e8768a'`.
- A `(red, green, blue)` tuple, with each value from 0 to 255.

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

The names are the 16 colors that every terminal has. Each of the eight normal
colors has a light version:

| Normal color | Light version |
| --- | --- |
| `black` | `dark_gray` |
| `red` | `light_red` |
| `green` | `light_green` |
| `yellow` | `light_yellow` |
| `blue` | `light_blue` |
| `magenta` | `light_magenta` |
| `cyan` | `light_cyan` |
| `gray` | `white` |

The spelling `grey` and the prefix `bright_`, as in `bright_red`, also work.
`'reset'` gives the default color of the terminal. If xnano does not know a
color, `write()` raises a `ValueError`, and the message shows the forms that
work.

## Text modifiers

A text modifier changes how text looks. Each modifier is a keyword of `write()`
that takes `True` or `False`, and the default is `False`. You can use more than
one modifier at the same time, and you can use modifiers with colors.

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

| Modifier | What it does |
| --- | --- |
| `bold` | Makes the text bold. |
| `dim` | Makes the text less bright. |
| `italic` | Makes the text italic. |
| `underline` | Puts a line below the text. |
| `reverse` | Swaps the foreground color and the background color. |
| `crossed_out` | Puts a line through the text. |
| `blink` | Makes the text blink. |
| `hidden` | Hides the text, but keeps the cells that it uses. |

Some terminals do not show all modifiers. For example, `italic` needs a font
with italic letters, and some terminals show `blink` text without the blink.

## Change a style later

After you write content, you can change its style through its placement. Each
modifier has a method with the same name, such as `bold()` or `underline()`.

```python
import xnano

with xnano.new(width=30, height=1) as canvas:
    label = canvas.screen.write('status: ok', foreground='green')

    label.color.fg = 'yellow'  # >> [color]
    label.color.bg = 'black'  # >> [color]
    label.bold().underline()  # >> [chain]
    assert label.is_bold and label.is_underlined  # >> [read]

    label.underline(False)  # >> [off]
    print(canvas.screen.render(format='ansi'))
```

<comments>
<tag name="color" color="blue">
`color.fg` is the text color, and `color.bg` is the background color. They
accept the same forms as `foreground` and `background`. `'reset'` removes the
color.
</tag>

<tag name="chain" color="green">
A modifier method turns the modifier on. Each method returns the placement, so
you can chain the calls.
</tag>

<tag name="read" color="amber">
A property such as `is_bold` tells you if a modifier is on. You can also set the
property, for example `label.is_bold = False`.
</tag>

<tag name="off" color="pink">
Give `False` to turn a modifier off.
</tag>
</comments>

The properties are `is_bold`, `is_dim`, `is_italic`, `is_underlined`,
`is_reversed`, `is_crossed_out`, `is_blinking` and `is_hidden`.

## Reuse a style

A [`Style`][xnano.styles.Style] keeps colors and modifiers together. Make the
style one time, then give it to each `write()` call with `style=`. The first
argument of `Style` is the foreground color, and the second argument is the
background color. If you also give style keywords to `write()`, they apply over
the style.

<!-- @code-block name="learn-styling-style" type="image" height=4 -->
```python
import xnano
from xnano.styles import Style

heading = Style('magenta', bold=True)

with xnano.new(width=40, height=3) as canvas:
    canvas.screen.write('Overview', style=heading)
    canvas.screen.write('Details', style=heading, underline=True)  # >> [over]
    canvas.screen.write('Plain text')
    print(canvas.screen.render(format='ansi'))
```

<comments>
<tag name="over" color="blue">
`underline=True` applies over the style, so `Details` is magenta, bold and
underlined.
</tag>
</comments>

<!-- @code-block-asset name="learn-styling-style" -->

![learn-styling-style](../assets/examples/learn-styling-style-light.png#only-light)
![learn-styling-style](../assets/examples/learn-styling-style-dark.png#only-dark)

<!-- /@code-block-asset -->

## Several styles in one line

To give different styles to parts of one line, use a
[`StyledText`][xnano.styles.StyledText]. A `StyledText` is a list of
[`TextSpan`][xnano.styles.TextSpan] items, and each span has its own text and
style. A span without a style keeps the default style. `write()` does not accept
a `StyledText` directly, so write it in a
[`Paragraph`][xnano.widgets.Paragraph] widget.

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

`border` sets the kind of line. `border_style` takes a `Style` for the border
only, so the border can have a color that is different from the text.
[Writing Content](content.md#boxes) shows the kinds of line, `title` and
`padding`.

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

## Choose colors for all themes

People use terminals with light themes and with dark themes, and each theme has
its own shade for each named color. These rules keep a program easy to read in
all themes:

- **Use named colors and `dim` first.** Named colors follow the theme of the
  user. xnano sends a hex color or a tuple color as it is, so it can be almost
  invisible on a light or a dark background. Use exact colors only when the
  color is the content, for example in art and gradients.
- **Give one meaning to each color.** Use green for success, yellow for a
  warning, red for an error, and blue or cyan for information. Use the same
  meanings everywhere in the program.
- **Do not use color as the only sign of a meaning.** Some people cannot see
  the difference between red and green, and some terminals show no color. Put a
  word or a symbol with the color, for example `● online` or `▲ slow`.
- **Show importance with weight, not with size.** A terminal has one text size.
  Make titles and keys `bold`, keep content plain, and make hints `dim`.
