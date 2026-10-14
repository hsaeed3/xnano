"""
tests.test_actual_terminal

Observe xnano in a production terminal application, with no emulated responses.
"""

from __future__ import annotations

import os
import pathlib
import re
from collections.abc import Iterator
from typing import cast

import pytest
from actual_terminal import ActualTerminal, kitty_executable


@pytest.fixture
def actual_terminal(request: pytest.FixtureRequest) -> Iterator[ActualTerminal]:
    if not request.config.getoption('--actual-terminal'):
        pytest.skip('Native terminal tests are opt-in: make test-terminal')
    if kitty_executable() is None:
        pytest.fail(
            'Kitty is required for actual terminal tests. Run make install-terminal.'
        )
    program = getattr(request, 'param', '')
    terminal = ActualTerminal(program)
    try:
        yield terminal
    finally:
        directory = pathlib.Path(
            os.environ.get('XNANO_TERMINAL_ARTIFACTS', '.artifacts/terminal')
        ) / cast(str, request.node.originalname)
        try:
            terminal.save_artifacts(directory)
        finally:
            terminal.close()


@pytest.mark.parametrize(
    'actual_terminal',
    [
        """
with xnano.open(title='xnano native title') as terminal:
    terminal.write('NATIVE READY', x=3, y=2)
    terminal.run()
print('RESTORED', flush=True)
"""
    ],
    indirect=True,
)
def test_title_drawing_input_and_alternate_screen_restoration(actual_terminal):
    actual_terminal.wait_for('NATIVE READY')
    actual_terminal.wait_until(lambda: actual_terminal.title() == 'xnano native title')
    assert actual_terminal.text().splitlines()[2].startswith('   NATIVE READY')
    actual_terminal.press('ctrl+c')
    assert actual_terminal.finish() == 0
    actual_terminal.wait_for('RESTORED')
    assert 'NATIVE READY' not in actual_terminal.text()


@pytest.mark.parametrize(
    'actual_terminal',
    [
        """
print('shell prompt', flush=True)
with xnano.open(width=20, height=2) as terminal:
    terminal.write('INLINE READY')
    terminal.run()
print('REGION CLEARED', flush=True)
"""
    ],
    indirect=True,
)
def test_inline_region_stays_below_existing_output_and_clears(actual_terminal):
    actual_terminal.wait_for('INLINE READY')
    lines = actual_terminal.text().splitlines()
    assert lines.index('INLINE READY') > lines.index('shell prompt')
    actual_terminal.press('ctrl+c')
    assert actual_terminal.finish() == 0
    actual_terminal.wait_for('REGION CLEARED')
    assert 'INLINE READY' not in actual_terminal.text()
    assert 'shell prompt' in actual_terminal.text()


@pytest.mark.parametrize(
    'actual_terminal',
    [
        """
import xnano.styles
with xnano.open() as terminal:
    terminal.write('COLOR READY', style=xnano.styles.Style(foreground=(255, 0, 0)))
    print('CAPTURED OUTPUT', flush=True)
    terminal.run()
"""
    ],
    indirect=True,
)
def test_true_color_and_print_capture_reach_the_native_terminal(actual_terminal):
    actual_terminal.wait_for('COLOR READY')
    styled = actual_terminal.text(ansi=True)
    assert re.search(r'\x1b\[[0-9;:]*38[;:]2[;:]255[;:]0[;:]0', styled)
    assert 'CAPTURED OUTPUT' not in actual_terminal.text()
    actual_terminal.save_artifacts(
        pathlib.Path(os.environ.get('XNANO_TERMINAL_ARTIFACTS', '.artifacts/terminal'))
        / 'true-color-live'
    )
    actual_terminal.press('ctrl+c')
    assert actual_terminal.finish() == 0
    actual_terminal.wait_for('CAPTURED OUTPUT')


@pytest.mark.parametrize(
    'actual_terminal',
    [
        """
with xnano.open() as terminal:
    @terminal.hook
    def observe(context):
        if context.size_changed is not None:
            terminal.clear()
            terminal.write(f'RESIZED {terminal.width}x{terminal.height}')
    terminal.write('RESIZE READY')
    terminal.run()
"""
    ],
    indirect=True,
)
def test_native_window_resize_reaches_xnano(actual_terminal):
    actual_terminal.wait_for('RESIZE READY')
    actual_terminal.resize(columns=60, rows=18)
    actual_terminal.wait_for('RESIZED 60x18')
    actual_terminal.press('ctrl+c')
    assert actual_terminal.finish() == 0


@pytest.mark.parametrize(
    'actual_terminal',
    [
        """
with xnano.open() as terminal:
    @terminal.hook
    def observe(context):
        if context.pasted is not None:
            terminal.write(f'PASTED {context.pasted}', y=1)
        if context.keyboard is not None and context.keyboard.key == 'a':
            terminal.write('KEY RECEIVED', y=2)
    terminal.write('INPUT READY')
    terminal.run()
"""
    ],
    indirect=True,
)
def test_keyboard_and_bracketed_paste_use_the_native_terminal_encoder(actual_terminal):
    actual_terminal.wait_for('INPUT READY')
    actual_terminal.press('a')
    actual_terminal.wait_for('KEY RECEIVED')
    actual_terminal.paste('clipboard content')
    actual_terminal.wait_for('PASTED clipboard content')
    actual_terminal.press('ctrl+c')
    assert actual_terminal.finish() == 0


@pytest.mark.parametrize(
    'actual_terminal',
    [
        f"""
import runpy
runpy.run_path({str(pathlib.Path(__file__).resolve().parent.parent / 'examples' / '20_world.py')!r}, run_name='__main__')
"""
    ],
    indirect=True,
)
def test_world_fills_the_window(actual_terminal):
    actual_terminal.wait_for('hold the mouse')
    lines = actual_terminal.text().splitlines()
    assert 'hold the mouse' in lines[23], (
        'the status line is on the last row of the window'
    )
    actual_terminal.press('q')
    assert actual_terminal.finish() == 0
