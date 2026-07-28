"""tests.beta.test_grid_render_ctx

---

``grid_render`` may optionally take a ``Context``, dispatched by arity like
``grid_post_init`` — both the zero-arg and one-arg forms must render without
a ``TypeError``.
"""

from __future__ import annotations

from xnano.beta.context import Context
from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid
from xnano.beta.terminal import Terminal


def test_grid_render_receives_ctx_and_state() -> None:
    seen: list[object] = []

    class App(BaseGrid):
        label: str = Field(default="")

        def grid_render(  # ty: ignore[invalid-method-override]
            self, ctx: Context
        ) -> None:
            seen.append(ctx.state)
            self.label = f"model: {ctx.state['model']}"

    grid = App()
    state = {"model": "opus"}
    terminal = Terminal.offscreen(cols=40, rows=4, state=state)
    terminal.attach_grid(grid)
    terminal.render()
    terminal.close()

    assert seen and seen[0] == state
    assert grid.label == "model: opus"


def test_grid_render_zero_arg_form_still_works() -> None:
    calls: list[str] = []

    class App(BaseGrid):
        label: str = Field(default="")

        def grid_render(self) -> None:
            calls.append("called")

    grid = App()
    terminal = Terminal.offscreen(cols=40, rows=4)
    terminal.attach_grid(grid)
    terminal.render()
    terminal.close()

    assert calls
