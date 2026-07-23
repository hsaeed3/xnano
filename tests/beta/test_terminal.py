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
