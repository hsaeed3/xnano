"""tests.beta.test_watch_hooks

---

Bare-name ``@on_state``/``@on_field`` hooks fire on mutation, while
expression forms keep firing every frame they are truthy.
"""

from __future__ import annotations

import dataclasses

from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid
from xnano.beta.hooks import on_field, on_state
from xnano.beta.terminal import Terminal


def test_on_field_bare_name_fires_once_per_mutation() -> None:
    fires: list[int] = []

    class App(BaseGrid):
        count: int = Field(default=0)

        @on_field("count")
        def _on_count(self) -> None:
            fires.append(self.count)

    app = App()
    terminal = Terminal.offscreen(cols=20, rows=3)
    try:
        terminal.render(app)  # baseline — no fire
        terminal.render(app)  # unchanged — no fire
        assert fires == []
        app.count = 5
        terminal.render(app)  # mutated — fire once
        terminal.render(app)  # unchanged — no fire
        assert fires == [5]
        app.count = 6
        terminal.render(app)
        assert fires == [5, 6]
    finally:
        terminal.close()


def test_on_state_bare_name_fires_once_per_mutation() -> None:
    fires: list[int] = []

    @dataclasses.dataclass
    class State:
        value: int = 0

    class App(BaseGrid):
        @on_state("value")
        def _on_value(self, ctx) -> None:
            fires.append(ctx.state.value)

    app = App()
    state = State()
    terminal = Terminal.offscreen(cols=20, rows=3, state=state)
    try:
        terminal.render(app)
        terminal.render(app)
        assert fires == []
        state.value = 9
        terminal.render(app)
        terminal.render(app)
        assert fires == [9]
    finally:
        terminal.close()


def test_on_state_bare_name_reads_dict_state_keys() -> None:
    fires: list[int] = []

    class App(BaseGrid):
        @on_state("value")
        def _on_value(self, ctx) -> None:
            fires.append(ctx.state["value"])

    app = App()
    state: dict[str, int] = {"value": 0}
    terminal = Terminal.offscreen(cols=20, rows=3, state=state)
    try:
        terminal.render(app)
        state["value"] = 3
        terminal.render(app)
        assert fires == [3]
    finally:
        terminal.close()


def test_expression_form_still_fires_every_truthy_frame() -> None:
    fires: list[int] = []

    class App(BaseGrid):
        count: int = Field(default=0)

        @on_field("count > 0")
        def _positive(self) -> None:
            fires.append(self.count)

    app = App()
    terminal = Terminal.offscreen(cols=20, rows=3)
    try:
        terminal.render(app)
        terminal.render(app)
        assert fires == []
        app.count = 2
        terminal.render(app)
        terminal.render(app)
        assert fires == [2, 2]
    finally:
        terminal.close()
