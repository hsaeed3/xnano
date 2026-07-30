"""benchmarks.test_interaction

---

The latency-sensitive paths a user actually feels: a keystroke reaching the
focused component, arrow keys recomputing focus from live geometry, reactive
hooks firing on a state transition, a form being filled and submitted, and a
searchable list re-filtering on every character.

Each measured callable resets the state it mutates, because CodSpeed calls it
more than once per benchmark.
"""

from __future__ import annotations

from xnano import hooks
from xnano.actions import Action
from xnano.components.button import Button
from xnano.components.input import Input
from xnano.components.options import Options
from xnano.core import Runtime
from xnano.events import Event, KeyboardEventData
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.state import State

_TYPED = "hello xnano typing"

_OPTION_ITEMS = [
    f"item-{index}-{'alpha' if index % 2 else 'beta'}-name"
    for index in range(300)
]


class Editor(BaseGrid):
    """A single autofocused text input."""

    body: Input = Field(default_factory=Input, group="body", autofocus=True)


class Focusable(BaseGrid, direction="vertical"):
    """Three stacked focusable slots."""

    first: Input = Field(
        default_factory=Input, group="first", autofocus=True, height=1
    )
    second: Input = Field(default_factory=Input, group="second", height=1)
    third: Button = Field(
        default_factory=lambda: Button(label="Go"), group="third", height=1
    )


class Counter(State):
    """Shared session state driving an ``on_state`` hook."""

    ready: bool


class Reactive(BaseGrid):
    """A field expression hook and a state hook writing the same label."""

    count: int = Field(default=0, state=True)
    label: str = Field(default="idle")

    @hooks.on_field("count > 0")
    def _on_count(self) -> None:
        self.label = f"count={self.count}"

    @hooks.on_state("ready")
    def _on_ready(self) -> None:
        self.label = "ready"


class Form(BaseGrid, direction="vertical"):
    """Two inputs and a submit hook bound to enter."""

    name: Input = Field(
        default_factory=Input, group="name", autofocus=True, height=1
    )
    email: Input = Field(default_factory=Input, group="email", height=1)
    submitted: bool = Field(default=False, state=True)

    @hooks.on_keyboard("enter")
    def submit(self) -> None:
        self.submitted = True


class Picker(BaseGrid):
    """A searchable 300-item list."""

    picker: Options = Field(
        default_factory=lambda: Options(items=_OPTION_ITEMS, searchable=True),
        group="picker",
        autofocus=True,
    )


def _keyboard_actions(text: str) -> list[Action]:
    """Build one keyboard action per character of ``text``."""
    return [
        Action.keyboard("space" if character == " " else character)
        for character in text
    ]


def _offscreen(root: object, width: int, height: int) -> Runtime:
    """Open an offscreen runtime with ``root`` mounted and a frame drawn."""
    runtime = Runtime.offscreen(width, height)
    runtime.set_root(root)
    runtime.render()
    return runtime


def _type_text(
    runtime: Runtime, editor: Editor, actions: list[Action]
) -> None:
    """Replay a burst of keystrokes into the focused input."""
    editor.body.content = ""
    for action in actions:
        runtime.perform(action)


def _move_focus(runtime: Runtime, down: Event, up: Event) -> None:
    """Walk focus down twice and back up twice."""
    runtime.dispatch(down)
    runtime.dispatch(down)
    runtime.dispatch(up)
    runtime.dispatch(up)


def _drive_hooks(runtime: Runtime, app: Reactive, state: Counter) -> object:
    """Render once with hooks idle, then once across both transitions."""
    app.count = 0
    state.ready = False
    runtime.render()
    app.count = 7
    state.ready = True
    return runtime.render()


def _fill_form(
    runtime: Runtime,
    form: Form,
    keys: list[Action],
    tab: Action,
    enter: Action,
    shift_tab: Action,
) -> object:
    """Type, tab, type, submit, tab back and repaint."""
    form.name.content = ""
    form.email.content = ""
    form.submitted = False
    for action in keys:
        runtime.perform(action)
    runtime.perform(tab)
    for action in keys:
        runtime.perform(action)
    runtime.perform(enter)
    runtime.perform(shift_tab)
    return runtime.render()


def _search(runtime: Runtime, picker: Picker, keys: list[Action]) -> object:
    """Re-filter the list on every character of a query."""
    picker.picker.query = ""
    for action in keys:
        runtime.perform(action)
    return picker.picker.filtered


def test_typing_into_input(benchmark) -> None:
    """Per-keystroke dispatch down to the focused component."""
    editor = Editor()
    runtime = _offscreen(editor, 60, 10)
    actions = _keyboard_actions(_TYPED)
    try:
        benchmark(_type_text, runtime, editor, actions)
        assert editor.body.content == _TYPED
    finally:
        runtime.close()


def test_focus_navigation(benchmark) -> None:
    """Spatial focus resolution against live layout geometry."""
    app = Focusable()
    runtime = _offscreen(app, 40, 3)
    down = Event.from_data(KeyboardEventData.from_binding("down"))
    up = Event.from_data(KeyboardEventData.from_binding("up"))
    try:
        benchmark(_move_focus, runtime, down, up)
        assert runtime.focused_group == "first"
    finally:
        runtime.close()


def test_reactive_hooks(benchmark) -> None:
    """The safe expression evaluator behind ``on_field`` and ``on_state``."""
    state = Counter(ready=False)
    app = Reactive()
    runtime = Runtime.offscreen(40, 6, state=state)
    runtime.set_root(app)
    runtime.render()
    try:
        frame = benchmark(_drive_hooks, runtime, app, state)
        assert app.label == "ready"
        assert "ready" in frame.text
    finally:
        runtime.close()


def test_form_flow(benchmark) -> None:
    """A realistic form loop: typing, tab cycling, submit hook, repaint."""
    form = Form()
    runtime = _offscreen(form, 60, 6)
    keys = _keyboard_actions("alice")
    try:
        frame = benchmark(
            _fill_form,
            runtime,
            form,
            keys,
            Action.keyboard("tab"),
            Action.keyboard("enter"),
            Action.keyboard("shift+tab"),
        )
        assert form.submitted is True
        assert "alice" in frame.text
    finally:
        runtime.close()


def test_options_search(benchmark) -> None:
    """Worst realistic case: a full re-filter on each of six keystrokes."""
    picker = Picker()
    runtime = _offscreen(picker, 60, 20)
    keys = _keyboard_actions("itmalp")
    try:
        matched = benchmark(_search, runtime, picker, keys)
        assert 0 < len(matched) < len(_OPTION_ITEMS)
    finally:
        runtime.close()
