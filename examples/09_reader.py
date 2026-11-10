"""
Reader: Markdown laid out on the terminal, with a theme to choose.

``xnano.from_markdown`` turns Markdown into styled text that any canvas can write. ``t``
changes the theme, and ``q`` quits. To read a file of your
own with images, tables and links, run ``xnano FILE`` or call ``xnano.view``.
"""

import xnano

NOTES = """# Field notes

A short document with **bold** and *italic* words, `inline code`,
~~struck text~~ and a [link](https://xnano.hammad.app/).

## Tasks

- [x] Write the notes
- [ ] Read them on a terminal
- Share them

## Code

```python
import xnano

xnano.view('README.md')
```

> A quote keeps its mark on every line that it wraps to.
"""
THEMES = [
    None,
    'xnano-night',
    'xnano-day',
    'dracula',
    'github-light',
]  # None: the terminal's
theme = 0

with xnano.open(title='reader') as terminal:
    title = terminal.write('', bold=True)
    page = terminal.write('', y=2, width='100%')
    terminal.write('t theme · q quit', y='bottom', dim=True)

    def show() -> None:
        """Lay the notes out for the width of the window, in the chosen theme."""
        page.text = xnano.from_markdown(
            NOTES, width=terminal.screen.width, theme=THEMES[theme]
        )
        title.text = f'reader · {THEMES[theme] or "the colors of the terminal"}'

    @terminal.hook(on='key', keys='t')
    def change_theme(context: xnano.Context) -> None:
        """Show the notes in the next theme."""
        global theme
        theme = (theme + 1) % len(THEMES)
        show()

    @terminal.hook(on='resize')
    def lay_out_again(context: xnano.Context) -> None:
        """Wrap the notes at the new width of the window."""
        show()

    show()
    terminal.run(stop_on='q')
