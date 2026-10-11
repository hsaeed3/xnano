"""Public checks for the opt-in v1 compatibility package."""

from __future__ import annotations

import subprocess
import sys

from xnano.v1 import Runtime
from xnano.v1.fields import Field
from xnano.v1.grids import BaseGrid


def test_importing_xnano_does_not_eagerly_load_v1() -> None:
    script = (
        'import sys, xnano; '
        "assert not any(name == 'xnano.v1' or name.startswith('xnano.v1.') "
        'for name in sys.modules)'
    )
    subprocess.run(
        [
            sys.executable,
            '-c',
            script,
        ],
        check=True,
    )


def test_fit_sizing_measures_sequence_content_and_spacing() -> None:
    class App(BaseGrid):
        items: list[str] = Field(
            default_factory=lambda: ['one', 'two', 'three'],
            width='fit',
            height='fit',
            direction='vertical',
            gap=1,
            border='double',
            padding=(1, 2),
        )

    runtime = Runtime.offscreen(32, 12)
    try:
        runtime.set_root(App())
        frame = runtime.render()
        assert all(value in frame.text for value in ('one', 'two', 'three'))
    finally:
        runtime.close()


def test_button_background_applies_to_block_and_focus_panel() -> None:
    from xnano.v1.components.button import Button
    from xnano.v1.core.content import Panel, TextBlock

    button = Button(
        label='Ok',
        focused_color='black',
        focused_background='yellow',
    )
    button._input_focused = True
    content = button.compose(None)  # pyright: ignore[reportArgumentType]
    assert isinstance(content, Panel)
    assert content.background == 'yellow'
    assert isinstance(content.child, TextBlock)
    assert content.child.background == 'yellow'
