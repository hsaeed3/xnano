"""
tests.test_readme_examples

Every Python block of the README and of the pages under ``docs/`` that teach the API runs.

The blocks open the screen and wait for a key, so the test swaps those calls (and ``xnano.iter``)
for a canvas without a screen that moves five frames, and runs the rest as written.
"""

from __future__ import annotations

import contextvars
import pathlib
import re

import pytest

import xnano
from xnano.canvas import Canvas

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
PAGES = (
    REPOSITORY / 'README.md',
    REPOSITORY / 'docs' / 'index.md',
)
BLOCK = re.compile(r'^```python\n(.*?)^```', re.MULTILINE | re.DOTALL)


def blocks() -> list[tuple[str, int, str]]:
    found = []
    for page in PAGES:
        text = page.read_text(encoding='utf-8')
        for number, match in enumerate(BLOCK.finditer(text), 1):
            found.append(
                (page.relative_to(REPOSITORY).as_posix(), number, match.group(1))
            )
    return found


CASES = blocks()


def test_the_readme_has_examples():
    assert 'README.md' in {name for name, _, _ in CASES}
    assert len(CASES) >= 9


@pytest.mark.parametrize(
    ('name', 'number', 'source'),
    CASES,
    ids=[f'{name}-{number}' for name, number, _ in CASES],
)
def test_a_block_runs(name, number, source, monkeypatch, capsys):
    def screenless(*arguments: object, **keywords: object) -> Canvas:
        return xnano.new(*arguments, **keywords)  # type: ignore[arg-type]

    def stay_on_the_canvas(self: Canvas, **settings: object) -> Canvas:
        return self

    def move_five_frames(self: Canvas, *, stop_on: object = None) -> None:
        for _ in self.iter(frames=5):
            pass

    def five_screenless_frames(
        *arguments: object,
        frames: object = None,
        seconds: object = None,
        stop_on: object = None,
        **keywords: object,
    ) -> object:
        with xnano.new(*arguments, **keywords) as canvas:  # type: ignore[arg-type]
            yield from canvas.iter(frames=5)

    monkeypatch.setattr(xnano, 'open', screenless)
    monkeypatch.setattr(xnano, 'iter', five_screenless_frames)
    monkeypatch.setattr(Canvas, 'open', stay_on_the_canvas)
    monkeypatch.setattr(Canvas, 'run', move_five_frames)
    # `xnano.new()` makes its canvas the active one until it is closed, so each block runs in a
    # context of its own: a canvas a block leaves open never reaches the tests after it.
    contextvars.copy_context().run(
        exec,
        compile(source, f'{name} block {number}', 'exec'),
        {'__name__': '__docs__'},
    )
    capsys.readouterr()
