"""
tests.test_examples

Every program in ``examples/`` runs on an emulated terminal of 80 by 24 cells, the size the
homepage records them at: it draws its game, shows the keys it listens to, and leaves with
``q`` without an error.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

pytest.importorskip('pyte')
if sys.platform == 'win32':
    pytest.skip('needs a pseudo-terminal', allow_module_level=True)

from emulator import Screen  # noqa: E402

EXAMPLES = sorted((pathlib.Path(__file__).resolve().parent.parent / 'examples').glob('*.py'))


def test_there_are_examples():
    assert EXAMPLES, 'examples/ has no programs to run.'


@pytest.mark.parametrize('program', EXAMPLES, ids=[program.stem for program in EXAMPLES])
def test_an_example_draws_and_quits(program):
    screen = Screen(command=[sys.executable, str(program)], rows=24, columns=80)
    try:
        assert screen.wait_for('q quit'), (
            f'{program.name} did not show its "q quit" hint within 10 seconds. '
            f'The screen showed:\n{screen.text}'
        )
        screen.settle(1.0)
        drawn = [line for line in screen.lines() if line.strip()]
        assert len(drawn) >= 3, f'{program.name} drew almost nothing:\n{screen.text}'
        screen.press('q')
        assert screen.finish() == 0, f'{program.name} did not exit cleanly:\n{screen.text}'
        output = screen.raw.decode('utf-8', 'replace')
        assert 'Traceback' not in output
    finally:
        screen.close()
