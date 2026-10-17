"""
tests.test_readme_examples

Every Python block of the README and of the pages under ``docs/`` that teach the API runs.

The blocks open the screen and wait for a key, so the test swaps those two calls for a canvas
without a screen that moves five frames, and runs the rest as written.
"""

from __future__ import annotations

import pathlib
import re

import pytest

import xnano
from xnano.canvas import Canvas

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
PAGES = (
    REPOSITORY / 'README.md',
    REPOSITORY / 'docs' / 'index.md',
    REPOSITORY / 'docs' / 'learn' / 'index.md',
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


def test_the_pages_have_examples():
    assert {name for name, _, _ in CASES} == {
        'README.md',
        'docs/index.md',
        'docs/learn/index.md',
    }
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

    def move_five_frames(self: Canvas, *, quit_on: object = None) -> None:
        for _ in self.iter(count=5):
            pass

    monkeypatch.setattr(xnano, 'open', screenless)
    monkeypatch.setattr(Canvas, 'open', stay_on_the_canvas)
    monkeypatch.setattr(Canvas, 'run', move_five_frames)
    exec(compile(source, f'{name} block {number}', 'exec'), {'__name__': '__docs__'})  # noqa: S102
    capsys.readouterr()
