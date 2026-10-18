"""
tests.test_error_messages

Each error raised by the hooks says what failed, what was expected and what to do next.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.errors import TerminalError
from xnano.hooks._triggers import parse_when
from xnano.terminal._settings import gates_for_screen
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
        gates_for_screen(canvas, {'scroll': False})


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
    def nothing(*, context):  # type: ignore[misc]
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
        gates_for_screen(canvas, {'scroll': False})


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
        (plays_a_pixel_name, TypeError, ['a Pixel symbol', 'Melody or a Sound']),
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
        (writes_bytes, TypeError, ['raw bytes', 'xnano.load_image(data)']),
        (writes_a_path, TypeError, ['is a path', 'xnano.load_image(path)']),
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
            ["set 'volume' to 'loud'", 'the type the field declares'],
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


@pytest.mark.parametrize(
    ('raiser', 'error', 'parts'),
    [
        (
            lambda canvas: xnano.new(width=10**20, height=3),
            ValueError,
            ['from 1 to 65535'],
        ),
        (
            lambda canvas: xnano.new(width=3, height=10**20),
            ValueError,
            ['from 1 to 65535'],
        ),
        (lambda canvas: xnano.box(10**20, 3), TerminalError, ['65535']),
        (lambda canvas: canvas.write('a', layer=10**20), ValueError, ['layer must be']),
        (lambda canvas: canvas.write('a', padding=10**20), ValueError, ['at most 65535']),
        (lambda canvas: canvas.write('a', margin=10**20), ValueError, ['at most 65535']),
        (
            lambda canvas: xnano.draw(['ab'], palette=5),
            TypeError,
            ['mapping', "'#=white"],
        ),
        (
            lambda canvas: canvas.cursor.follow(canvas.write('a'), x=1.5),
            TypeError,
            ['whole'],
        ),
        (
            lambda canvas: canvas.cursor.follow(canvas.write('a'), x=10**20),
            ValueError,
            ['2147483647'],
        ),
        (
            lambda canvas: setattr(canvas.cursor, 'position', (10**12, 2)),
            ValueError,
            ['whole numbers from'],
        ),
        (
            lambda canvas: setattr(canvas.write('a'), 'layer', 10**20),
            ValueError,
            ['layer must be a whole number from'],
        ),
    ],
)
def test_a_number_out_of_range_says_what_to_pass(raiser, error, parts):
    with xnano.new(width=10, height=3) as canvas, pytest.raises(error) as raised:
        raiser(canvas)
    for part in parts:
        assert part in str(raised.value), (part, str(raised.value))


def test_a_placement_size_above_the_most_cells_says_what_to_pass():
    with xnano.new(width=10, height=3) as canvas:
        placement = canvas.write('a')
        for value in (70000, 10**20):
            with pytest.raises(
                ValueError, match='width must be a whole number of cells from 0 to 65535'
            ):
                placement.width = value
            with pytest.raises(
                ValueError, match='height must be a whole number of cells from 0 to 65535'
            ):
                canvas.write('a', height=value)
        with pytest.raises(
            ValueError, match='write\\(\\) shows content of at most 65535'
        ):
            canvas.write('a' * 10**6)


def test_draw_refuses_a_row_longer_than_a_buffer_holds():
    with pytest.raises(ValueError, match='rows of at most 65535 characters'):
        xnano.draw(['a' * 70000], {'a': 'red'})


def _draw_with_effects(value):
    xnano.draw(['a'], {'a': 'red'}, effects=value)


def _write_with_effects(value):
    with xnano.new(width=4, height=1) as canvas:
        canvas.write('a', effects=value)


def _new_with_effects(value):
    xnano.new(effects=value)


def _note_with_effects(value):
    xnano.note('C4', effects=value)


@pytest.mark.parametrize('value', ['fade', {'kind': 'effect.fade_to'}, 5])
@pytest.mark.parametrize(
    'call',
    [_draw_with_effects, _write_with_effects, _new_with_effects, _note_with_effects],
)
def test_effects_given_as_one_value_are_reported_whole(call, value):
    with pytest.raises(
        TypeError, match='effects= takes a list of dictionaries'
    ) as raised:
        call(value)
    assert repr(value) in str(raised.value)


@pytest.mark.parametrize('width', ['-50%', '1000000000%'])
def test_a_percentage_that_is_not_a_size_says_what_to_pass(width):
    with xnano.new(width=10, height=3) as canvas:
        with pytest.raises(
            ValueError, match='width must be a whole number of cells from 0 to 65535'
        ):
            canvas.write('a', width=width)
        placement = canvas.write('a')
        with pytest.raises(ValueError, match="share such as width='50%'"):
            placement.width = width


@pytest.mark.parametrize(
    ('condition', 'message'),
    [
        ('keyboard.key < "b"', r'< cannot compare keyboard\.key'),
        ('keyboard.key > 1', r'> cannot compare keyboard\.key'),
        ('-keyboard.key', r'- cannot be applied to keyboard\.key'),
        ('keyboard.key and 3', r'and joins comparisons'),
    ],
)
def test_operators_a_condition_cannot_use_are_explained(condition, message):
    with pytest.raises(ValueError, match=message) as raised:
        parse_when(condition).native()
    assert 'xnano_core' not in str(raised.value)
    assert '^' in str(raised.value)


@pytest.mark.parametrize('shown', ['keyboard.key', 'keyboard.chord', 'mouse.button'])
def test_the_suggestion_after_not_is_the_same_condition(shown):
    with pytest.raises(ValueError, match='or write') as raised:
        parse_when(f'not {shown}').native()
    message = str(raised.value)
    assert ' in [' not in message
    assert ' or ' not in message.split('or write', 1)[1]


def test_not_on_a_value_with_no_obvious_comparison_gives_no_wrong_example():
    with pytest.raises(ValueError, match='Compare it with == or !=') as raised:
        parse_when('not mouse.position').native()
    assert '<= 2' not in str(raised.value)


def test_pushing_a_key_is_taught_with_names_that_exist():
    with xnano.new(width=4, height=1) as canvas:
        with pytest.raises(TypeError, match='xnano_core.Event.key_press') as raised:
            canvas.push(5)
        assert 'canvas.input.keyboard' not in str(raised.value)
        assert hasattr(Event, 'key_press')
        assert not hasattr(canvas.input, 'keyboard')


@pytest.mark.parametrize('value', [5, ['key', 5], ('key', 'mouse')])
def test_a_hook_kind_that_is_not_one_name_is_explained(value):
    with xnano.new(width=8, height=1) as canvas:
        with pytest.raises(TypeError, match='takes one kind of hook as text'):
            canvas.hook(lambda context: None, on=value)


@pytest.mark.parametrize('value', ['no', 5, None])
def test_realtime_must_be_true_or_false(value):
    with pytest.raises(ValueError, match='realtime must be True or False'):
        xnano.new(realtime=value)


def test_resizing_a_slice_of_a_region_does_not_talk_about_a_canvas():
    box = xnano.box(6, 4)
    with pytest.raises(TerminalError, match='slice of a region is a window onto it'):
        box[0:2, 0:2].resize(1, 1)
    with xnano.new(width=4, height=2) as canvas:
        with pytest.raises(TerminalError, match='size of a canvas follows'):
            canvas.region.resize(5, 5)


def test_an_unknown_attribute_cannot_be_assigned():
    with xnano.new(width=8, height=2) as canvas:
        placement = canvas.write('a')
        for target, name in (
            (canvas.cursor, 'is_visble'),
            (canvas, 'titel'),
            (placement, 'is_bld'),
            (xnano.box(3, 3), 'border_colour'),
        ):
            with pytest.raises(AttributeError, match=f'no attribute called {name!r}'):
                setattr(target, name, True)
        canvas.cursor.is_visible = True
        placement.is_bold = True
        canvas.title = 'ok'


def test_an_unknown_keyword_of_write_lists_the_settings():
    with xnano.new(width=8, height=2) as canvas:
        with pytest.raises(TypeError, match='Canvas.write\\(\\) has no setting called'):
            canvas.write('a', anchor='middle')
        with pytest.raises(
            TypeError, match='Placement.write\\(\\) has no setting called'
        ):
            canvas.write('a').write('b', bogus=1)
