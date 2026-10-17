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


@xnano.renderable
def label_with_text(context, text):
    return text


class _OnlyRenders:
    def __xnano_render__(self, context):
        return 'x'


class _OnlyPlays:
    def __xnano_play__(self, context):
        return xnano.note('C4')


class _ReturnsANumber:
    def __xnano_render__(self, context):
        return 1


class _RendersItself:
    def __xnano_render__(self, context):
        return self


def writes_a_component_that_needs_arguments():
    with xnano.new(width=8, height=1) as canvas:
        canvas.write(label_with_text)


def declares_a_component_without_a_context():
    @xnano.renderable
    def nothing():
        return ''


def writes_something_that_only_plays():
    with xnano.new(width=8, height=1) as canvas:
        canvas.write(_OnlyPlays())


def plays_something_that_only_renders():
    with xnano.new(width=8, height=1) as canvas:
        canvas.play(_OnlyRenders())


def writes_a_component_that_returns_a_number():
    with xnano.new(width=8, height=1) as canvas:
        canvas.write(_ReturnsANumber())


def writes_a_component_that_renders_itself():
    with xnano.new(width=8, height=1) as canvas:
        canvas.write(_RendersItself())


def writes_a_component_that_returns_a_canvas():
    child = xnano.new(width=4, height=1)

    class Holder:
        def __xnano_render__(self, context):
            return child

    try:
        with xnano.new(width=8, height=1) as canvas:
            canvas.write(Holder())
    finally:
        child.close()


def a_component_gate_that_is_off():
    @xnano.renderable
    def wheel(context):
        return str(context.scroll.y)

    with xnano.new(width=8, height=1) as canvas:
        canvas.write(wheel)
        canvas._gates_for_screen({'scroll': False})


def a_component_hook_that_needs_dependencies():
    @xnano.renderable
    def label(context):
        return 'x'

    label.hook(lambda context, component: None, on='key', requires_deps=True)
    with xnano.new(width=8, height=1) as canvas:
        canvas.write(label)


def draws_rows_of_different_lengths():
    xnano.draw(['A', 'BB'], {'A': 'red', 'B': 'blue'})


def draws_an_unknown_symbol():
    xnano.draw('unknown_art_symbol')


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


def reads_the_reserved_key():
    with xnano.new(width=8, height=1) as canvas:
        canvas.state.get('xnano.buffers')


def pushes_the_whole_root():
    with xnano.new(width=8, height=1) as canvas:
        canvas.state.push('', {'a': 1})


def pushes_a_wrong_type():
    import dataclasses

    @dataclasses.dataclass
    class Settings:
        volume: int = 1

    with xnano.new(width=8, height=1, state=Settings()) as canvas:
        canvas.state.push('volume', 'loud')


def pushes_to_a_removed_placement():
    with xnano.new(width=8, height=1) as canvas:
        placement = canvas.write('a')
        namespace = placement.state
        placement.remove()
        namespace.push('x', 1)


def reads_an_attribute_that_is_not_a_field():
    import dataclasses

    @dataclasses.dataclass
    class Settings:
        volume: int = 1

    with xnano.new(width=8, height=1, state=Settings()) as canvas:
        canvas.state.loudness  # type: ignore[attr-defined]  # noqa: B018


def names_a_field_get():
    import dataclasses

    @dataclasses.dataclass
    class Settings:
        get: int = 1

    with xnano.new(width=8, height=1, state=Settings()):
        pass


def hooks_that_feed_each_other():
    canvas = xnano.new(width=8, height=1)

    @canvas.hook(on='state')
    def ping(context):
        state = context.root.state
        state.push('ping', state.get('pong', default=0) + 1)

    @canvas.hook(on='state')
    def pong(context):
        state = context.root.state
        state.push('pong', state.get('ping', default=0) + 1)

    canvas.state.push('ping', 1)
    canvas.deliver_events()
    canvas.close()


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
        (
            writes_a_component_that_needs_arguments,
            TypeError,
            ['needs arguments', 'canvas.write(label_with_text(...))'],
        ),
        (
            declares_a_component_without_a_context,
            TypeError,
            ['first parameter is the context', 'def nothing(context'],
        ),
        (
            writes_something_that_only_plays,
            TypeError,
            ['no __xnano_render__ method', 'canvas.play()', 'Use a string'],
        ),
        (
            plays_something_that_only_renders,
            TypeError,
            [
                'no __xnano_play__ method',
                'canvas.write()',
                'an object with __xnano_play__',
            ],
        ),
        (
            writes_a_component_that_returns_a_number,
            TypeError,
            ['_ReturnsANumber.__xnano_render__ returned int', 'must return something'],
        ),
        (
            writes_a_component_that_renders_itself,
            TerminalError,
            ['keeps returning something that renders', 'Return text'],
        ),
        (
            writes_a_component_that_returns_a_canvas,
            TypeError,
            ['canvas.write(child) directly'],
        ),
        (
            a_component_gate_that_is_off,
            TerminalError,
            ['The component wheel needs scroll=True', 'xnano.new(scroll=True)'],
        ),
        (
            a_component_hook_that_needs_dependencies,
            TerminalError,
            ['needs dependencies', 'xnano.new(deps='],
        ),
        (
            draws_rows_of_different_lengths,
            ValueError,
            ['every row the same length', 'Pad the short rows'],
        ),
        (
            draws_an_unknown_symbol,
            ValueError,
            ["'unknown_art_symbol' is not a known Art symbol", 'symbol='],
        ),
        (writes_bytes, TypeError, ['raw bytes', 'xnano.from_image(data)']),
        (writes_a_path, TypeError, ['is a path', 'xnano.from_image(path)']),
        (
            a_gate_that_is_off,
            TerminalError,
            ['needs scroll=True', 'xnano.new(scroll=True)', 'scroll=False'],
        ),
        (
            lambda: xnano.state.parse_path('player..score'),
            ValueError,
            ["'player..score'", 'empty part', "'player.score'"],
        ),
        (
            reads_the_reserved_key,
            ValueError,
            ["'xnano.buffers'", "starts with 'xnano'", 'another name'],
        ),
        (
            pushes_the_whole_root,
            ValueError,
            ['whole root state', "push('score', 1)"],
        ),
        (
            pushes_a_wrong_type,
            TerminalError,
            ["push 'volume' to 'loud'", 'Use a value the field accepts'],
        ),
        (
            pushes_to_a_removed_placement,
            TerminalError,
            ["Could not push 'x'", 'was removed', 'still on the canvas'],
        ),
        (
            reads_an_attribute_that_is_not_a_field,
            AttributeError,
            ['loudness is not a field', "get('loudness')"],
        ),
        (
            names_a_field_get,
            TerminalError,
            ["field named 'get'", 'Rename the field'],
        ),
        (
            hooks_that_feed_each_other,
            TerminalError,
            [
                "hooks 'ping' and 'pong' keep changing",
                'stop writing it',
                'only when the value differs',
            ],
        ),
    ],
)
def test_the_error_teaches_the_recovery(raiser, error, parts):
    with pytest.raises(error) as raised:
        raiser()
    text = str(raised.value)
    for part in parts:
        assert part in text, (part, text)
