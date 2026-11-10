---
title: Reading Files
icon: lucide/book-open
---

# Reading Files

xnano reads a file and shows it in the way that suits its kind. You use it from
the command line, or from a program.

## Read a file from the command line

Give the `xnano` command the path of a file.

```bash
xnano README.md
```

On a terminal, the file opens in a viewer. In a pipe or in a file, xnano prints
the document as plain text.

```bash
xnano data.json | head
```

| Kind of file | What you see |
| --- | --- |
| Markdown | Headings, lists, quotes, code, tables, links and images, laid out. |
| JSON | Indented data, with a color for each kind of value. |
| `.csv` and `.tsv` | A table. Its header stays in view while you scroll. |
| PDF | The text of each page. This needs `pip install "xnano[pdf]"`. |
| A picture | The picture. This needs `pip install "xnano[image]"`. |
| A sound | Its length and format, and `space` plays it. This needs `pip install "xnano[audio]"`. |
| Other text | The text with line numbers. |
| Other data | The bytes, 16 in each line. |

If xnano cannot show an image or play a sound, it names the image or the sound
in text. The rest of the document stays readable.

These options change what the command does:

| Option | What it does |
| --- | --- |
| `-p`, `--print` | Prints the document and leaves, also on a terminal. |
| `-w CELLS`, `--width CELLS` | Sets the width of the printed document. |
| `-t NAME`, `--theme NAME` | Chooses the colors. See [Themes](#themes). |

## Use the viewer

The last line of the viewer shows its keys. Each key on that line is also a
button for the mouse.

| Key | What it does |
| --- | --- |
| `↑` `↓`, `j` `k` | Scroll one line. |
| `space`, `page down`, `b`, `page up` | Scroll one page. |
| `g`, `G` | Go to the start or the end. |
| `/` | Find text. `n` and `N` go to the next and the previous match. |
| `o` | List the headings. `enter` goes to the chosen heading. |
| `r` | Show the source of the document, or the laid out document. |
| `backspace` | Go back to the file that you came from. |
| `q` | Leave. |

The wheel scrolls, and a drag on the document or on the bar at the right edge
scrolls too. A click on a link to a heading goes to the heading. A click on a
link to another file opens that file.

## Read a file from a program

`xnano.view()` does what the command does.

```python
import xnano

xnano.view('README.md', theme='xnano-night')
```

When the program has no terminal, `view()` prints the document. To print on a
terminal too, pass `interactive=False`.

## Write Markdown on a canvas

`xnano.from_markdown()` lays Markdown out as styled text. Write it on a canvas
like any other text.

```python
import xnano

with xnano.new(width=40, height=6) as canvas:
    canvas.write(xnano.from_markdown('# Notes\n\nA **bold** word.', width=40))
    print(canvas.render())
```

## Themes

A theme sets the colors of the document. Without a theme, the document uses the
colors of your terminal, so it follows the theme that you chose there. A theme
draws its own colors.

The same names work for any canvas: `xnano.open(theme='dracula')` colors the
text, the borders and the widgets of a program. See [Styling](styling.md#themes).

| Theme | Colors by |
| --- | --- |
| `xnano-day`, `xnano-night` | xnano. Birch and dark oak wood, with a warm key light and a cool fill light after [Complementary Shaders](https://www.complementary.dev/) by EminGT. |
| `zed-dark`, `zed-light` | [Zed Industries](https://github.com/zed-industries/zed/tree/main/assets/themes/one): One Dark and One Light of the Zed editor. |
| `one-dark-pro` | [Binaryify](https://github.com/Binaryify/OneDark-Pro): One Dark Pro. |
| `one-dark`, `one-light` | GitHub: [One Dark](https://github.com/atom/one-dark-syntax) and [One Light](https://github.com/atom/one-light-syntax) of the Atom editor. |
| `dracula` | [Zeno Rocha and the Dracula Theme contributors](https://github.com/dracula/dracula-theme). |
| `monokai` | [Wimer Hazenberg](https://github.com/textmate/monokai.tmbundle). |
| `github-dark`, `github-light` | [GitHub](https://github.com/primer/github-vscode-theme): GitHub Dark Default and GitHub Light Default. |
| `anthropic-dark`, `anthropic-light` | The brand colors of [Anthropic](https://github.com/anthropics/skills/tree/main/skills/brand-guidelines). |
| `openai-dark`, `openai-light` | The colors of [OpenAI's Apps SDK UI](https://github.com/openai/apps-sdk-ui). |

The names and the colors of these themes belong to their authors. xnano is not
affiliated with any of them.
