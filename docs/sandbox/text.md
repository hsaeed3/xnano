---
title: "Text"
icon: "lucide/type"
---

# Text Sandbox

`Text` has one constructor for leaf text, inline spans, multi-line paragraphs,
and editable input. These examples cover every constructor option:
`content`, `color`, `background`, `modifiers`, `align`, `wrap`, `input`,
`placeholder`, `cursor`, `visible`, `z`, and `fit_content`.

## Every Content Shape

```pyodide install="xnano>=1.0.10" height="24"
from xnano import Terminal
from xnano.components.text import Text

leaf = Text("A leaf", color="cyan-300")

line = Text([
    Text("status: ", modifiers=("bold",)),
    Text("ready", color="emerald-400"),
    " · plain strings work too",
])

paragraph = Text([
    Text([Text("first ", color="amber-300"), Text("line", modifiers=("underline",))]),
    Text("second line", color="violet-300"),
    Text("third\nembedded newline", color="rose-300"),
])

Terminal(width=64, height=10).render(leaf, line, paragraph, gap=1)
```

`content` may be a string, another `Text`, or a list containing strings and
`Text` children. A list of leaves is one line; nested lines or embedded
newlines form a paragraph.

??? example "Every Content Shape"
    - `content`: `str | Text | list[str | Text]`; see [Text](../api/xnano/components/text.md#xnano.components.text.Text){data-preview}.

## Foreground, Background, and Modifiers

The outer component can style a complete block; children can carry independent
styles. The full modifier set is shown in the [Styling sandbox](styling.md).

```pyodide install="xnano>=1.0.10" height="15"
from xnano import render
from xnano.components.text import Text

render(Text(
    [
        Text("● ", color="emerald-400"),
        Text("healthy ", color="white", modifiers=("bold",)),
        Text("12ms", color="slate-300", modifiers=("italic", "underline")),
    ],
    background="slate-900",
))
```

??? example "Foreground, Background, and Modifiers"
    - `color`, `background`: [ColorLike](../api/xnano/color.md#xnano.color.ColorLike){data-preview} or `None`.
    - `modifiers`: a tuple of [CharacterModifier](../api/xnano/_types.md#xnano._types.CharacterModifier){data-preview} values; default `()`.

## Alignment and Wrapping

`align` is `left`, `center`, `right`, or `None`. `wrap=True` breaks text to fit
the available width; `False` keeps one logical line and clips at the boundary.

```pyodide install="xnano>=1.0.10" height="22"
from xnano import BaseGrid, Field, Terminal
from xnano.components.text import Text

long = "A long line demonstrates what happens at the right edge of a narrow field."

class TextLayout(BaseGrid, direction="vertical", gap=1, border="double", padding=1):
    left: Text = Field(default=Text("left", align="left"), height=1)
    center: Text = Field(default=Text("center", align="center"), height=1)
    right: Text = Field(default=Text("right", align="right"), height=1)
    wrapped: Text = Field(default=Text(long, wrap=True), height=3, border="plain", title="wrap=True")
    clipped: Text = Field(default=Text(long, wrap=False), height=3, border="plain", title="wrap=False")

Terminal(width=46, height=14).render(TextLayout())
```

??? example "Alignment and Wrapping"
    - `align`: [Alignment](../api/xnano/_types.md#xnano._types.Alignment){data-preview} (`"left"`, `"center"`, `"right"`) or `None`.
    - `wrap`: `bool`, default `True`; see [Text](../api/xnano/components/text.md#xnano.components.text.Text){data-preview}.

## Input, Placeholder, and Cursor

An input must be a leaf `Text`. `placeholder` accepts a string or styled
`Text`; `cursor=None` means the end, while an integer chooses a character
index. The offscreen terminal can focus fields and accept synthetic keyboard
actions, so this remains behavioral without `Terminal.run()`.

```pyodide install="xnano>=1.0.10" height="30"
from xnano import Action, BaseGrid, Field, Terminal
from xnano.components.text import Text

class Form(BaseGrid, direction="vertical", gap=1, border="rounded", title="input", padding=1):
    name: Text = Field(
        default=Text("Codex", input=True, cursor=2, color="cyan-200"),
        border="plain",
        title="integer cursor",
        height=3,
    )
    empty: Text = Field(
        default=Text(
            "",
            input=True,
            cursor=None,
            placeholder=Text("styled placeholder", color="amber-300", modifiers=("italic",)),
        ),
        border="plain",
        title="cursor=None + Text placeholder",
        height=3,
    )

form = Form()
terminal = Terminal.offscreen(cols=58, rows=10)
try:
    terminal.render(form)
    terminal.focus_field(form, "name")
    terminal.perform(Action.keyboard("!"))
    terminal.render(form)
    print(terminal.get_output_as_ansi())
    print("name value:", form.name.value, "cursor:", form.name.cursor)
finally:
    terminal.__exit__(None, None, None)
```

Try replacing the styled placeholder with a plain string, changing `cursor`,
or performing `left`, `right`, `home`, `end`, `backspace`, and `delete`
keyboard actions.

??? example "Input, Placeholder, and Cursor"
    - `input`: `bool`, default `False`; see [Text.input](../api/xnano/components/text.md#xnano.components.text.Text.input){data-preview}.
    - `placeholder`: `str | Text | None`; see [Text.placeholder](../api/xnano/components/text.md#xnano.components.text.Text.placeholder){data-preview}.
    - `cursor`: `int | None`; see [Text.cursor](../api/xnano/components/text.md#xnano.components.text.Text.cursor){data-preview}.

## Visibility, Stacking, and Intrinsic Size

All components inherit keyword-only `visible`, `z`, and `fit_content`.
`visible=False` suppresses painting. `z` determines sibling paint order when
areas overlap. `fit_content=True` lets `Text` measure to its content; `False`
lets its field/viewport supply the size.

```pyodide install="xnano>=1.0.10" height="18"
from xnano import Terminal
from xnano.components.text import Text

shown = Text("visible, z=2, intrinsic", color="green", visible=True, z=2, fit_content=True)
hidden = Text("hidden", color="red", visible=False, z=99, fit_content=True)
filling = Text("fit_content=False", color="cyan", visible=True, z=0, fit_content=False)

print("component flags:", shown.visible, shown.z, shown.fit_content)
Terminal(width=44, height=5).render(shown, hidden, filling, gap=1)
```

??? example "Visibility, Stacking, and Intrinsic Size"
    - `visible`: `bool`, default `True`.
    - `z`: `int`, default `0`.
    - `fit_content`: `bool`, default `True`.
    - Shared constructor: [AbstractComponent](../api/xnano/components/abstract.md#xnano.components.abstract.AbstractComponent){data-preview}.
