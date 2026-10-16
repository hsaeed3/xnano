"""
tests.test_error_messages

Each error raised by the hooks says what failed, what was expected and what to do next.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.errors import TerminalError
from xnano_core import Event


def hook_with(**arguments):
    with xnano.new(width=8, height=1) as canvas:
        canvas.hook(lambda context: None, **arguments)


def too_many_arguments():
    hook_with(on='tick', every=1, after=1)


def yields_a_value():
    with xnano.new(width=8, height=1) as canvas:

        @canvas.hook(on='key')
        def wait(context):
            yield 2.0

        canvas.push(Event.key_press('a'))
        canvas.deliver_events()


def returns_content():
    with xnano.new(width=8, height=1) as canvas:
        canvas.hook(lambda context: 'text', on='key')
        canvas.push(Event.key_press('a'))
        canvas.deliver_events()


def a_gate_that_is_off():
    with xnano.new(width=8, height=1) as canvas:
        canvas.hook(lambda context: None, on='scroll')
        canvas._gates_for_screen({'scroll': False})


def plays_an_unknown_name():
    xnano.note('C2', symbol='kick_drum')
    with xnano.new(width=8, height=1) as canvas:
        canvas.play('kik_drum')


def plays_a_pixel_name():
    xnano.Pixel('#', symbol='wall_cell')
    with xnano.new(width=8, height=1) as canvas:
        canvas.play('wall_cell')


def writes_bytes():
    with xnano.new(width=8, height=1) as canvas:
        canvas.write(b'abc')  # type: ignore[arg-type]


def writes_a_path():
    import pathlib

    with xnano.new(width=8, height=1) as canvas:
        canvas.write(pathlib.Path('picture.png'))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ('raiser', 'error', 'parts'),
    [
        (lambda: hook_with(every=1), ValueError, ['every=', 'on=', 'Nothing is guessed']),
        (
            too_many_arguments,
            ValueError,
            ['every=', 'after=', 'cannot be given together', 'Use every='],
        ),
        (
            lambda: hook_with(on='key', keys='escpae'),
            ValueError,
            ["'escpae'", "'escape'", 'KeyName'],
        ),
        (
            lambda: hook_with(on='click'),
            ValueError,
            ["on='click'", "mouse.kind == 'press'"],
        ),
        (
            lambda: hook_with(when=False),
            TypeError,
            ['when= received False', 'Keyboard.key == "q"'],
        ),
        (
            lambda: hook_with(when='banana'),
            ValueError,
            ["'banana'", 'column 0', 'The names are'],
        ),
        (lambda: hook_with(when='root.time > 3'), ValueError, ['no on=', 'on="tick"']),
        (
            lambda: hook_with(requires_deps=True),
            TerminalError,
            ['requires_deps=True', 'xnano.new(deps='],
        ),
        (
            yields_a_value,
            TerminalError,
            ['must yield nothing', 'context = yield', "on='tick'"],
        ),
        (returns_content, TerminalError, ['cannot return content', '@xnano.renderable']),
        (
            plays_an_unknown_name,
            ValueError,
            [
                "'kik_drum' is not a known sound symbol",
                "'kick_drum'",
                'an octave',
                "symbol='kik_drum'",
            ],
        ),
        (plays_a_pixel_name, TypeError, ['a Pixel symbol', 'Note or an Audio']),
        (
            lambda: xnano.note('H9'),
            ValueError,
            ["'H9' is not a note name", 'optional # or b'],
        ),
        (lambda: xnano.note('C4', beats=0), ValueError, ['beats must be', 'half a beat']),
        (
            lambda: xnano.note('C4', instrument='kazoo'),
            ValueError,
            ["'kazoo' is not an instrument", 'Use one of'],
        ),
        (
            lambda: xnano.note('C4', symbol='C4'),
            ValueError,
            ["'C4' reads as a note", 'Pick another name'],
        ),
        (writes_bytes, TypeError, ['raw bytes', 'xnano.from_image(data)']),
        (writes_a_path, TypeError, ['is a path', 'xnano.from_image(path)']),
        (
            a_gate_that_is_off,
            TerminalError,
            ['needs scroll=True', 'xnano.new(scroll=True)', 'scroll=False'],
        ),
    ],
)
def test_the_error_teaches_the_recovery(raiser, error, parts):
    with pytest.raises(error) as raised:
        raiser()
    text = str(raised.value)
    for part in parts:
        assert part in text, (part, text)
