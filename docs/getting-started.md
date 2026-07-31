---
title: "Getting Started"
icon: "lucide/book-open"
---

# Getting Started

## Installation

You can install [xnano]{data-preview} with your favorite package manager on python 3.10+ <small>(and lower than 3.14 for now)</small>.

!!! info "v1.2"

    The library has recently been rewritten from the ground up to provide a more stable & performant core compared to previous versions. Please ensure you are using a `v1.2.xx` or higher version of the library for the best experience.

??? abstract "Demo"

    [xnano]{data-preview} provides a built-in demo application you can run to get a quick feel for what the library is capable of. You can try it yourself by running the following command:

    === "pip"

        ```bash title="Run the demo"
        python -m xnano demo
        ```

    === "uv"

        ```bash title="Run the demo"
        uv run xnano demo
        ```

=== "pip"

    ```bash title="Install with pip"
    pip install "xnano>=1.2.3b2"
    ```

=== "uv"

    ```bash title="Install with uv"
    uv pip install "xnano>=1.2.3b2"

    # or add to your project's dependencies
    # uv add xnano
    ```

=== "poetry"

    ```bash title="Install with poetry"
    poetry install "xnano>=1.2.3b2"

    # or add to your project's dependencies
    # poetry add xnano
    ```

=== "conda"

    ```bash title="Install with conda"
    conda install "xnano>=1.2.3b2"
    ```

## Notetaking Application

The best way to begin understanding [xnano]{data-preview} is to actually build something with it. In this guide, we'll build a simple dashboard & to-do list application that we can write notes in.

### Prerequisites

This guide assumes you have a basic understanding of the following concepts:

- :material-checkbox-outline:{ .lg .middle } Type Hints
- :material-checkbox-outline:{ .lg .middle } Object Oriented Programming / Pydantic

## Grids

Grids are the centerpiece of the layout and rendering architecture within [xnano]{data-preview}, they represent a **resizable, focusable, renderable & rectangular area within the screen**.

Additionally, grids provide an easy way to scaffold the entire layout of your application before worrying about their individual content. Let's begin by creating the grid scaffold for our application.

```python title="Scaffolding the Application" hl_lines="15-32"
from xnano import BaseGrid, Field # (1)!

class Dashboard(BaseGrid):
    """Side/status panel that provides various information about the application and system.
    """

class Editor(BaseGrid):
    """The popup window that appears when creating or editing a note.
    """

class SavedNotes(BaseGrid):
    """The list of saved notes that the user can select from to read and edit.
    """

class NotesApp(BaseGrid, direction="horizontal"): # (2)!
    """The main application grid that houses all inner grids for the notetaking application.
    """
    saved_notes: SavedNotes = Field(
        default_factory=SavedNotes,
        width="25%", # (3)!
        height="100%",
    )
    dashboard: Dashboard = Field(
        default_factory=Dashboard,
        width="75%",
        height="100%",
    )
    editor: Editor = Field(
        default_factory=Editor,
        z=2, # (4)!
        visible=False # (5)!
    )
```

1. `xnano.BaseGrid` is a declarative class inspired by `pydantic.BaseModel` that allows you to define your grid's content and state in a field-based manner.
2. Grids can take in settings either directly as constructor arguments or using the `grid_settings` class attribute. <br/> In this case, we're setting the direction of the content of our grid to be horizontal.
3. Sizing in xnano is incredibly simple, we can use the `width` and `height` attributes to set the size of our content. <br/> These two parameters support absolute values such as `height=1` (one terminal row), relative values such as `width="50%"` and `height="fit"`.
4. The `z` attribute is a custom primtive within xnano that allows for the stacking of any content on top of each other.
5. We don't want to render the editor grid by default, so we set it with `visible=False`.

### Running the Application

xnano is designed to be **interface-agnostic** through the power of the [ratzilla] library. This means the same grid can be rendered to a terminal or the web browser.

We can now run our application by using the `Terminal` or `Web` classes.

```python title="Running the Application"
from xnano import Terminal

Terminal().run(NotesApp())
```

## Adding Content

If you ran the following code above, you should see... **nothing**. No worries however, thats because we haven't added any content to our grids yet.

Let's now implement the functionality for writing and saving notes.

```python title="Implementing Note Writing" hl_lines="12-16"
from dataclasses import dataclass
from xnano import BaseGrid, Field

class Dashboard(BaseGrid):
    """Side/status panel that provides various information about the application and system.
    """

class Editor(BaseGrid):
    """The popup window that appears when creating or editing a note.
    """

@dataclass
class Note: # (1)
    """A single note that has been saved."""
    name: str
    content: str

class SavedNotes(BaseGrid):
    """The list of saved notes that the user can select from to read and edit.
    """

class NotesApp(BaseGrid, direction="horizontal"): # (2)!
    """The main application grid that houses all inner grids for the notetaking application.
    """
    saved_notes: SavedNotes = Field(
        default_factory=SavedNotes,
        width="25%", # (3)!
        height="100%",
    )
    dashboard: Dashboard = Field(
        default_factory=Dashboard,
        width="75%",
        height="100%",
    )
    editor: Editor = Field(
        default_factory=Editor,
        z=2, # (4)!
        visible=False # (5)!
    )
```

1. We'll define a simple dataclass to represent a saved note.

A `Note` gives us something to store, but a note has to live *somewhere* that every grid can reach. That shared place is the application's **state**.

## State

[xnano]{data-preview} gives you two kinds of state, and it's worth knowing which is which:

- **Grid state** — a `Field(state=True)` holds data on a *single* grid that never renders on its own (a counter, a flag). It behaves like a normal attribute, but assigning to it schedules a repaint.
- **Application state** — a single object shared by *every* grid and every event handler. This is where our list of notes belongs, since both the list and the editor need it.

Application state is any object you like — we'll use a `dataclass` — handed to the `Terminal` when you run.

```python title="Application State"
import dataclasses

@dataclasses.dataclass
class Notes: # (1)!
    """Application state shared with every grid's hooks."""
    saved: list[Note] = dataclasses.field(default_factory=list)
    editing: bool = False # (2)!
    current: int | None = None
```

1. A plain dataclass — no [xnano]{data-preview} base class required. Anything you pass to `Terminal(state=...)` becomes the shared state.
2. We track whether the editor is open (`editing`) and, when editing an existing note, its index (`current`). `None` means we're writing a brand-new note.

Every event handler receives a `Context`, and `ctx.state` *is* this object — the same instance, everywhere.

## Rendering Content

A field can hold a plain string, or one of [xnano]{data-preview}'s **components**. Components are the small, focused widgets your grids are built from — text, inputs, lists, tables, and so on.

The cleanest way to keep a field in sync with your state is `grid_render`, a method [xnano]{data-preview} calls on each grid **once per frame, right before layout**. Override it to refresh a field from the current state.

Let's give the `Dashboard` a status line:

```python title="A Live Status Panel"
from xnano import Context

class Dashboard(BaseGrid):
    stats: str = Field(default="") # (1)!

    def grid_render(self, ctx: Context[Notes]) -> None: # (2)!
        count = len(ctx.state.saved)
        self.stats = f"{count} note{'' if count == 1 else 's'} saved"
```

1. A field annotated as `str` renders its value as text — no component needed.
2. `grid_render` runs every frame. The `Context` parameter is optional; ask for it when you need `ctx.state`, `ctx.runtime`, or the triggering event. `Context[Notes]` just tells your type checker what `ctx.state` is.

The `SavedNotes` grid is a list the user browses, so it uses an `Options` component. We refresh its items from state the same way:

```python title="The Saved-Notes List"
from xnano.components import Options

class SavedNotes(BaseGrid):
    notes: Options = Field(
        default_factory=Options,
        border="rounded", # (1)!
        title="Saved Notes",
        padding=1,
    )

    def grid_render(self, ctx: Context[Notes]) -> None:
        self.notes.items = tuple(
            note.name for note in ctx.state.saved
        ) or ("no notes yet",)
```

1. Any field can carry its own chrome — a `border`, a `title`, and `padding` — without wrapping it in another grid.

!!! tip "Components are opt-in, not one-size-fits-all"

    An `Options` list is *not* a search box by default — it browses with the arrow keys and lets every other key through to your app. Pass `Options(searchable=True)` when you actually want type-to-filter.

Finally, the `Editor` holds two text `Input`s — a single-line title and a multiline body:

```python title="The Editor's Inputs"
from xnano.components import Input

class Editor(BaseGrid):
    title: Input = Field(
        default_factory=lambda: Input(placeholder="Title"),
        group="title", # (1)!
        height=1,
    )
    body: Input = Field(
        default_factory=lambda: Input(
            placeholder="Write your note…", multiline=True # (2)!
        ),
        group="body",
    )
```

1. A `group` names a field so it can hold **focus** — the target of the keyboard. We'll move focus to `"body"` when the editor opens.
2. `multiline=True` turns the input into a small text editor with its own caret; the default is a single line.

## Reacting to the Keyboard

Nothing types itself — we need to *handle events*. [xnano]{data-preview} exposes a family of `@on_*` decorators; the one we need most is `@on_keyboard`. A handler is just a method on a grid, and it runs whenever its key is pressed.

We'll put every command on `NotesApp`, since it owns the whole application:

```python title="Commands" hl_lines="6 12 20"
from xnano import on_keyboard

class NotesApp(BaseGrid, direction="horizontal"):
    # ...fields as before...

    def grid_render(self, ctx: Context[Notes]) -> None:
        self.grid_set_field("editor", visible=ctx.state.editing) # (1)!

    @on_keyboard("n")
    def new_note(self, ctx: Context[Notes]) -> None:
        self.editor.title.value = ""
        self.editor.body.value = ""
        ctx.state.editing = True
        ctx.runtime.focus("body") # (2)!

    @on_keyboard("ctrl+s")
    def save_note(self, ctx: Context[Notes]) -> None:
        if not ctx.state.editing:
            return
        name = self.editor.title.value.strip() or "Untitled"
        ctx.state.saved.append(Note(name, self.editor.body.value))
        ctx.state.editing = False
        ctx.runtime.blur() # (3)!

    @on_keyboard("esc")
    def cancel(self, ctx: Context[Notes]) -> None:
        ctx.state.editing = False
        ctx.runtime.blur()
```

1. `grid_set_field` changes a field's metadata at runtime — here we show or hide the editor to match `state.editing`. Because it runs in `grid_render`, the editor's visibility always tracks the state.
2. `ctx.runtime.focus(group)` sends the keyboard to a field by its `group`, so typing lands in the note body.
3. `ctx.runtime.blur()` releases focus when we close the editor, so the next `[n]`, `[↑]`, or `[↓]` reaches our commands again instead of being typed into a hidden input.

!!! info "Modifier keys stay yours"

    A focused input types the keys you'd expect, but passes modifier chords like `ctrl+s` straight through to your handlers — so app shortcuts keep working even while the user is typing.

## Turning the Editor into a Popup

Right now the `editor` is an ordinary field, so it claims its own slice of the layout and pushes the panels aside. A popup should *float above* the content instead. That's exactly what `overlay` is for:

```python title="A Floating Editor" hl_lines="3 4"
    editor: Editor = Field(
        default_factory=Editor,
        overlay=True, # (1)!
        z=2, # (2)!
        visible=False,
        border="rounded",
        background="black", # (3)!
        title=" Editor ",
        padding=1,
        width="60%", # (4)!
        height="60%",
    )
```

1. An `overlay` field is taken *out of the flow*: it no longer takes a column, and is instead centered on top of the grid's content.
2. Remember `z` from the scaffold — it lifts the whole editor (border, inputs, and all) onto a layer above the panels behind it.
3. An overlay clears the cells it covers, so a `background` gives you a solid, opaque popup rather than one you can see through.
4. `width` and `height` size the floating box; unset, it would fill the whole area.

## Mouse Support

[xnano]{data-preview} apps are keyboard-first, but a click or a hover is often the most natural thing to reach for. Mouse input is **opt-in** — turn it on when you run:

```python title="Enabling the Mouse"
Terminal(state=Notes(), mouse_events=True).run(NotesApp())
```

With mouse events on, two behaviors come for free:

- **Click to focus** — clicking the title or body input moves the keyboard to it, so you can point at the field you want to edit.
- **Hover to preview** — moving the pointer over the saved-notes list marks the row under the cursor with a dim indicator, kept distinct from the arrow-key selection. Move the selection with `[↑/↓]` and press `[enter]` (or wire up `@on_click`) to open a note.

## A Persistent Footer

A good TUI keeps its controls in sight. We'll add a footer bar that stays visible even while the editor floats on top. That means one small restructure: the two side-by-side panels move into their own grid, and `NotesApp` stacks that row above a footer.

```python title="Panels + Footer"
class Panels(BaseGrid, direction="horizontal"): # (1)!
    saved_notes: SavedNotes = Field(default_factory=SavedNotes, width="25%")
    dashboard: Dashboard = Field(default_factory=Dashboard, width="75%")

class NotesApp(BaseGrid, direction="vertical"): # (2)!
    panels: Panels = Field(default_factory=Panels, height="1fr") # (3)!
    editor: Editor = Field(default_factory=Editor, overlay=True, z=2, visible=False, ...)
    footer: str = Field(
        default="[n] new   [↑/↓] browse   [enter] open   [ctrl+s] save   [esc] cancel   [q] quit",
        height=1,
        background="dimgray",
        align="center",
    )
```

1. Grids nest freely — a grid is just another kind of content. Pulling the panels into `Panels` keeps `NotesApp` free to lay out its children top-to-bottom.
2. `NotesApp` is now `vertical`: the panels sit above the footer.
3. `height="1fr"` gives the panels every row the footer doesn't take. Because the editor floats *over the panels' area* and is centered at 60% height, it never covers the footer.

## The Complete Application

Put together, the whole notetaking app is well under a hundred lines:

```python title="notes.py"
import dataclasses

from xnano import BaseGrid, Context, Field, Terminal, on_keyboard
from xnano.components import Input, Options

KEYS = (
    "[n] new   [↑/↓] browse   [enter] open   "
    "[ctrl+s] save   [esc] cancel   [q] quit"
)

@dataclasses.dataclass
class Note:
    name: str
    content: str

@dataclasses.dataclass
class Notes:
    saved: list[Note] = dataclasses.field(default_factory=list)
    editing: bool = False
    current: int | None = None

class Dashboard(BaseGrid):
    stats: str = Field(default="")

    def grid_render(self, ctx: Context[Notes]) -> None:
        count = len(ctx.state.saved)
        self.stats = (
            f"{count} note{'' if count == 1 else 's'} saved\n\n"
            "Pick a note on the left, or press [n] to write a new one."
        )

class SavedNotes(BaseGrid):
    notes: Options = Field(
        default_factory=Options, border="rounded", title="Saved Notes", padding=1
    )

    def grid_render(self, ctx: Context[Notes]) -> None:
        self.notes.items = tuple(n.name for n in ctx.state.saved) or ("no notes yet",)

class Editor(BaseGrid):
    title: Input = Field(
        default_factory=lambda: Input(placeholder="Title"), group="title", height=1
    )
    body: Input = Field(
        default_factory=lambda: Input(placeholder="Write your note…", multiline=True),
        group="body",
    )

class Panels(BaseGrid, direction="horizontal"):
    saved_notes: SavedNotes = Field(default_factory=SavedNotes, width="25%")
    dashboard: Dashboard = Field(default_factory=Dashboard, width="75%")

class NotesApp(BaseGrid, direction="vertical"):
    panels: Panels = Field(default_factory=Panels, height="1fr")
    editor: Editor = Field(
        default_factory=Editor,
        overlay=True,
        z=2,
        visible=False,
        border="rounded",
        background="black",
        title=" Editor ",
        padding=1,
        width="60%",
        height="60%",
    )
    footer: str = Field(default=KEYS, height=1, background="dimgray", align="center")

    def grid_render(self, ctx: Context[Notes]) -> None:
        self.grid_set_field("editor", visible=ctx.state.editing)

    def _open(self, ctx: Context[Notes], note: Note | None) -> None:
        self.editor.title.value = "" if note is None else note.name
        self.editor.body.value = "" if note is None else note.content
        ctx.state.editing = True
        ctx.runtime.focus("body")

    @on_keyboard("n")
    def new_note(self, ctx: Context[Notes]) -> None:
        ctx.state.current = None
        self._open(ctx, None)

    @on_keyboard("enter")
    def open_selected(self, ctx: Context[Notes]) -> None:
        if not ctx.state.saved:
            return
        index = self.panels.saved_notes.notes.selected
        ctx.state.current = index
        self._open(ctx, ctx.state.saved[index])

    @on_keyboard("up")
    def select_previous(self) -> None:
        self.panels.saved_notes.notes.move(-1)

    @on_keyboard("down")
    def select_next(self) -> None:
        self.panels.saved_notes.notes.move(1)

    @on_keyboard("ctrl+s")
    def save_note(self, ctx: Context[Notes]) -> None:
        if not ctx.state.editing:
            return
        name = self.editor.title.value.strip() or f"Note {len(ctx.state.saved) + 1}"
        note = Note(name, self.editor.body.value)
        if ctx.state.current is None:
            ctx.state.saved.append(note)
        else:
            ctx.state.saved[ctx.state.current] = note
        self._close(ctx)

    @on_keyboard("esc")
    def cancel(self, ctx: Context[Notes]) -> None:
        self._close(ctx)

    def _close(self, ctx: Context[Notes]) -> None:
        ctx.state.editing = False
        ctx.state.current = None
        ctx.runtime.blur()

    @on_keyboard("q")
    def quit(self, ctx: Context[Notes]) -> None:
        ctx.runtime.request_exit()

if __name__ == "__main__":
    Terminal(state=Notes(), mouse_events=True).run(NotesApp())
```

Run it with `python notes.py`, and you have a complete little application: browse your notes on the left, watch the count on the right, pop open the editor to write or edit, and every keybind in reach along the bottom.

From here, the same grids, fields, and hooks scale up — swap `Terminal` for `Web` to serve it in a browser, add a `Table` or a `Chart` component, or wire `@on_click` onto the notes list to open a note with a tap. The pieces don't change; you just compose more of them.


*[TUI]: A text-based user interface (your terminal applications).
*[Pydantic]: A library for data validation and settings management using Python type hints. <br/>The patterns and design choices for the user API within xnano are directly inspired by Pydantic.
*[Pydantic-core]: The core validation engine for Pydantic.
*[ratatui]: A rust crate for building terminal user interfaces.
*[ratzilla]: A rust crate that provides native ratatui support within the web browser.
*[tachyonfx]: A rust crate that provides terminal effects for ratatui.
*[Type Hints]: Python’s way of specifying the expected data type of variables, function arguments, and return values (for example, `str`, `int`, `float`, `bool`), which helps with code clarity, editor support, and early catching of type-related errors.
*[Object Oriented Programming]: A programming paradigm based on the concept of "objects", which can contain data and code to manipulate that data.
[xnano]: index.md
[Pydantic]: https://docs.pydantic.dev/latest/
[pydantic-core]: https://github.com/pydantic/pydantic-core
[ratatui]: https://ratatui.rs/
[ratzilla]: https://github.com/ratatui/ratzilla
[tachyonfx]: https://github.com/ratatui/tachyonfx
