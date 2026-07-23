"""tests.beta.test_terminal"""

from __future__ import annotations

from xnano.beta.components.text import Text
from xnano.beta.terminal import Terminal


def test_terminal_offscreen_render() -> None:
    terminal = Terminal.offscreen(cols=30, rows=8)
    terminal.render(Text("beta terminal"))
    assert "beta terminal" in terminal.get_output()
    assert terminal.surface == "offscreen"
    assert terminal.runtime is not None


def test_terminal_focus_aliases() -> None:
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid

    class Form(BaseGrid):
        name: Text = Field(
            default=Text("", input=True),
            group="name",
        )

    terminal = Terminal.offscreen(cols=30, rows=6)
    form = Form()
    terminal.attach_grid(form)
    terminal.render(form)
    assert terminal.focus("name") is True
    assert terminal.focused_group == "name"
    terminal.blur()
    assert terminal.focused_group is None


def test_terminal_run_polls_hooks_and_repaints_mutation(monkeypatch) -> None:
    from xnano.beta import hooks
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid

    class App(BaseGrid):
        label: str = Field(default="initial", border="rounded")
        ticks: int = Field(default=0, state=True)

        @hooks.on_tick
        def update(self, ctx) -> None:
            self.ticks += 1
            self.label = "updated"
            if self.ticks == 2:
                ctx.terminal.request_exit()

    terminal = Terminal.offscreen(cols=30, rows=6)
    app = App()
    frames = []
    render = terminal.runtime.render

    def capture_render(*args, **kwargs):
        frame = render(*args, **kwargs)
        frames.append(frame)
        return frame

    monkeypatch.setattr(terminal.runtime, "render", capture_render)
    terminal.run(app)
    assert app.ticks == 2
    assert any("updated" in frame.text for frame in frames)
    assert any("╭" in frame.text for frame in frames)
