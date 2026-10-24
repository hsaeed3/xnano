"""
tests.test_hook_triggers

The conditions of a hook: an expression, a function or a string, compiled once.
"""

from __future__ import annotations

import re
import typing

import pytest

import xnano
from xnano.devices import KeyName
from xnano.expressions import keyboard, mouse, parent, root, scroll
from xnano.hooks import Context
from xnano.hooks._triggers import (
    _MEMBERS,
    _PARTS,
    compile_when,
    normalize_binding,
    parse_when,
)
from xnano_core import Event, Expression


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=6, fps=10) as opened:
        yield opened


def push(canvas, event: Event) -> None:
    canvas.push(event)
    canvas.deliver_events()


# A condition that mentions an input hears only that input: these make a condition a key hook.
_HEARS = {'key': "keyboard.kind != 'release' and "}


def hook_heard(canvas, condition, *events: Event, placement=None, kind=None) -> int:
    """How many of the events made a hook with this condition run."""
    count = []
    target = canvas if placement is None else placement
    if kind is not None:
        condition = f'{_HEARS[kind]}({condition})'
    handle = target.hook(lambda context: count.append(1), on=condition)
    for event in events:
        push(canvas, event)
    handle.remove()
    return len(count)


class TestForms:
    def test_an_expression_is_checked_natively(self, canvas):
        assert (
            hook_heard(
                canvas,
                keyboard.key == 'q',
                Event.key_press('a'),
                Event.key_press('q'),
            )
            == 1
        )

    def test_expressions_combine_with_and_or_not(self, canvas):
        condition = (keyboard.key == 'a') | (
            (keyboard.key == 'b') & ~(keyboard.kind == 'repeat')
        )
        events = [Event.key_press(name) for name in 'abc']
        events.append(Event.key_press('b', kind='repeat'))
        assert hook_heard(canvas, condition, *events) == 2

    def test_a_function_is_called_with_the_context(self, canvas):
        seen: list[str | None] = []

        def only_q(context: Context) -> bool:
            seen.append(context.keyboard.key)
            return context.keyboard.key == 'q'

        assert hook_heard(canvas, only_q, Event.key_press('a'), Event.key_press('q')) == 1
        assert seen == ['a', 'q']

    def test_a_string_becomes_an_expression(self):
        compiled = compile_when("keyboard.key == 'q'")
        assert isinstance(compiled.expression, Expression)
        assert compiled.predicate is None
        assert compiled.reads == {'keyboard'}

    def test_a_string_is_parsed_once(self):
        first = parse_when(
            "keyboard.key == 'z' or mouse.is_down and mouse.position.x == 7"
        )
        info = parse_when.cache_info()
        second = parse_when(
            "keyboard.key == 'z' or mouse.is_down and mouse.position.x == 7"
        )
        assert second is first
        assert parse_when.cache_info().hits == info.hits + 1

    def test_a_plain_bool_is_refused_with_the_fix(self):
        with pytest.raises(TypeError, match=r'on= received False.*keyboard.key == "q"'):
            compile_when(False)

    def test_anything_else_is_refused(self):
        with pytest.raises(TypeError, match='condition expression, a function'):
            compile_when(3)

    def test_expressions_build_with_equality(self):
        assert isinstance(keyboard.key == 'q', Expression)
        assert hash(keyboard.key) == hash(keyboard.key)


class TestMembers:
    """One case per member of the table of string members."""

    def test_keyboard_key(self, canvas):
        assert hook_heard(canvas, "keyboard.key == 'q'", Event.key_press('q')) == 1

    def test_keyboard_key_as_a_bare_name(self, canvas):
        assert hook_heard(canvas, 'keyboard.key == escape', Event.key_press('esc')) == 1

    def test_keyboard_kind(self, canvas):
        events = [Event.key_press('a'), Event.key_press('a', kind='release')]
        assert hook_heard(canvas, "keyboard.kind == 'release'", *events) == 1

    def test_keyboard_binding(self, canvas):
        events = [Event.key_press('s'), Event.key_press('Ctrl+s')]
        assert hook_heard(canvas, "keyboard.binding == 'ctrl+s'", *events) == 1

    def test_mouse_position_in_the_region_of_the_buffer(self, canvas):
        placement = canvas.screen.write('....', x=5, y=2)
        events = [
            Event.mouse_event(column=6, row=2, kind='move'),
            Event.mouse_event(column=1, row=1, kind='move'),
        ]
        condition = 'mouse.position in target.region'
        assert hook_heard(canvas, condition, *events, placement=placement) == 1

    def test_mouse_button(self, canvas):
        events = [
            Event.mouse_event(column=1, row=1, kind='press', button=button)
            for button in ('left', 'right')
        ]
        assert hook_heard(canvas, "mouse.button == 'right'", *events) == 1

    def test_mouse_kind(self, canvas):
        events = [
            Event.mouse_event(column=1, row=1, kind=kind, button='left')
            for kind in ('press', 'drag', 'release')
        ]
        assert hook_heard(canvas, "mouse.kind in ('press', 'release')", *events) == 2

    def test_mouse_is_down(self, canvas):
        events = [
            Event.mouse_event(column=1, row=1, kind='press', button='left'),
            Event.mouse_event(column=2, row=1, kind='drag', button='left'),
            Event.mouse_event(column=2, row=1, kind='release', button='left'),
        ]
        assert hook_heard(canvas, 'mouse.is_down', *events) == 2

    def test_scroll_x_and_y(self, canvas):
        events = [
            Event.mouse_event(column=1, row=1, kind='scroll', scroll_y=-1),
            Event.mouse_event(column=1, row=1, kind='scroll', scroll_x=2),
        ]
        assert hook_heard(canvas, 'scroll.y < 0', *events) == 1
        assert hook_heard(canvas, 'scroll.x > 0', *events) == 1

    def test_buffer_geometry(self, canvas):
        placement = canvas.screen.write('abc', x=4, y=1)
        events = [Event.key_press('a')]
        for text in (
            'target.x == 4',
            'target.y == 1',
            'target.width == 3',
            'target.height == 1',
        ):
            assert (
                hook_heard(canvas, text, *events, placement=placement, kind='key') == 1
            ), text
        assert (
            hook_heard(
                canvas, 'target.width == 9', *events, placement=placement, kind='key'
            )
            == 0
        )

    def test_the_parts_of_a_position_a_size_and_a_region(self, canvas):
        placement = canvas.screen.write('abc', x=4, y=1)
        events = [Event.key_press('a')]
        kwargs = {'placement': placement, 'kind': 'key'}
        for text in (
            'target.position.x == 4',
            'target.size.width == 3',
            'target.region.right >= 7',
        ):
            assert hook_heard(canvas, text, *events, **kwargs) == 1, text

    def test_only_the_parts_that_exist_are_allowed(self, canvas):
        with pytest.raises(ValueError, match='not a member'):
            hook_heard(
                canvas, 'target.position.width == 4', Event.key_press('a'), kind='key'
            )

    def test_parent_and_root_geometry(self, canvas):
        placement = canvas.screen.write('abc')
        events = [Event.key_press('a')]
        for text in (
            'parent.width == 20',
            'parent.height == 6',
            'root.width == 20',
            'root.height == 6',
        ):
            assert (
                hook_heard(canvas, text, *events, placement=placement, kind='key') == 1
            ), text

    def test_root_time_delta_and_fps(self, canvas):
        ticks = []
        canvas.hook(lambda context: ticks.append(1), on='root.time > 0.25')
        canvas.hook(lambda context: ticks.append(2), on='time > 0.25')
        canvas.hook(lambda context: ticks.append(3), on='root.delta > 0.0')
        canvas.hook(lambda context: ticks.append(4), on='root.fps >= 0')
        for _ in range(4):
            canvas.clock.step(delta_seconds=0.1)
        assert ticks.count(1) == 2
        assert ticks.count(2) == 2
        assert ticks.count(3) == 4

    def test_deps_make_the_whole_string_a_python_condition(self):
        class Dependencies:
            limit = 2
            name = 'x'

        with xnano.new(width=8, height=1, deps=Dependencies()) as canvas:
            heard = []
            canvas.hook(
                lambda context: heard.append(context.keyboard.key),
                on="keyboard.key == 'a' and deps.limit == 2",
            )
            canvas.hook(
                lambda context: heard.append('never'),
                on='deps.limit > 5',
            )
            for name in 'ab':
                push(canvas, Event.key_press(name))
            assert heard == ['a']

    def test_deps_with_buffer_region_and_scroll(self):
        class Dependencies:
            name = 'x'

        with xnano.new(width=20, height=4, deps=Dependencies()) as canvas:
            placement = canvas.screen.write('abcd', x=2, y=1)
            heard = []
            placement.hook(
                lambda context: heard.append('inside'),
                on="mouse.position in target.region and deps.name == 'x'",
            )
            push(canvas, Event.mouse_event(column=3, row=1, kind='move'))
            assert heard == ['inside']


def _every_member() -> list[str]:
    names = []
    for scope, members in _MEMBERS.items():
        for member in members:
            parts = _PARTS.get(member)
            if parts is None:
                names.append(f'{scope}.{member}')
            else:
                names.extend(f'{scope}.{member}.{part}' for part in parts)
    return names


class TestEveryMember:
    @pytest.mark.parametrize('member', _every_member())
    @pytest.mark.parametrize('suffix', ['', ' and deps.n == 1'])
    def test_each_member_is_readable_on_any_event(self, member, suffix):
        class Dependencies:
            n = 1

        with xnano.new(width=20, height=4, deps=Dependencies()) as canvas:
            placement = canvas.screen.write('abcd', x=2, y=1)
            count = []
            # The condition's own kind, a tick and a key hook each read the member.
            for timing in ({}, {'every': 0.1}, {'keys': 'ctrl+s'}):
                placement.hook(
                    lambda context: count.append(1),
                    on=f'({member} == {member}){suffix}',
                    **timing,
                )
            events = [
                Event.key_press('ctrl+s'),
                Event.mouse_event(column=3, row=1, kind='move'),
                Event.mouse_event(column=3, row=1, kind='scroll', scroll_y=1),
            ]
            for event in events:
                push(canvas, event)
            canvas.clock.step(delta_seconds=0.2)

    def test_binding_matches_in_both_paths(self, canvas):
        event = Event.key_press('ctrl+s')
        assert hook_heard(canvas, "keyboard.binding == 'ctrl+s'", event) == 1
        both = "(keyboard.binding == 'ctrl+s') and deps.n == 1"

        class Dependencies:
            n = 1

        with xnano.new(width=8, height=1, deps=Dependencies()) as other:
            assert hook_heard(other, both, event) == 1

    def test_a_part_of_a_missing_value_compares_false_with_deps(self):
        class Dependencies:
            n = 1

        with xnano.new(width=8, height=1, deps=Dependencies()) as canvas:
            events = [Event.key_press('a')]
            text = '(mouse.position.x == 0) and deps.n == 1'
            assert hook_heard(canvas, text, *events, kind='key') == 0
            text = '(mouse.position.x + 1 > 0) and deps.n == 1'
            assert hook_heard(canvas, text, *events, kind='key') == 0


class TestOperators:
    def test_not_in_and_comparisons(self, canvas):
        events = [Event.key_press(name) for name in 'abc']
        assert hook_heard(canvas, "keyboard.key not in ('a', 'b')", *events) == 1
        assert hook_heard(canvas, "keyboard.key != 'a'", *events) == 2

    def test_negation_holds_for_an_event_without_the_input(self, canvas):
        events = [Event.key_press('q'), Event.paste('x')]
        both = ' and not mouse.is_down'
        assert hook_heard(canvas, "keyboard.key != 'q'" + both, *events) == 0
        assert hook_heard(canvas, "not keyboard.key == 'q'" + both, *events) == 1
        assert hook_heard(canvas, "keyboard.key not in ('q',)" + both, *events) == 1
        assert hook_heard(canvas, ~(keyboard.key == 'q'), *events) == 1

    def test_a_string_that_reads_one_input_hears_only_that_input(self, canvas):
        events = [Event.key_press('q'), Event.paste('x')]
        assert hook_heard(canvas, "not keyboard.key == 'q'", *events) == 0

    def test_arithmetic_and_negation(self, canvas):
        placement = canvas.screen.write('abc')
        events = [Event.key_press('a')]
        kwargs = {'placement': placement, 'kind': 'key'}
        assert hook_heard(canvas, 'parent.width / 2 + 1 == 11', *events, **kwargs) == 1
        assert hook_heard(canvas, 'not parent.width - 20 == 0', *events, **kwargs) == 0
        assert hook_heard(canvas, '-parent.width < 0', *events, **kwargs) == 1

    def test_chained_comparison(self, canvas):
        placement = canvas.screen.write('abc')
        events = [Event.key_press('a')]
        kwargs = {'placement': placement, 'kind': 'key'}
        assert hook_heard(canvas, '10 < parent.width < 30', *events, **kwargs) == 1
        assert hook_heard(canvas, '10 < parent.width < 15', *events, **kwargs) == 0

    def test_a_missing_value_compares_false(self, canvas):
        assert hook_heard(canvas, "mouse.button == 'left'", Event.key_press('a')) == 0

    def test_the_scopes_are_exported_from_the_expressions_module(self):
        assert isinstance(parent.width > 1, Expression)
        assert isinstance(root.time > 1, Expression)
        assert isinstance(mouse.button == 'left', Expression)
        assert isinstance(scroll.y < 0, Expression)


class TestKeys:
    def test_normalizing_matches_the_runtime(self, canvas):
        names = list(typing.get_args(typing.get_args(KeyName)[0]))
        chords = [
            'ctrl+s',
            'Ctrl+Shift+S',
            'alt+ctrl+x',
            'shift+tab',
            'esc',
            'S',
            ' ',
            'cmd+x',
        ]
        for name in [*names, *chords]:
            heard = []
            handle = canvas.hook(
                lambda context, heard=heard: heard.append(1), on='key', keys=name
            )
            push(canvas, Event.key_press(name))
            handle.remove()
            assert heard == [1], name
            assert isinstance(normalize_binding(name), str)

    def test_chords_are_written_in_one_order(self):
        assert normalize_binding('shift+ctrl+alt+x') == 'ctrl+alt+shift+x'
        assert normalize_binding('Esc') == 'escape'
        assert normalize_binding('Q') == 'shift+q'

    def test_an_unknown_key_names_the_closest(self):
        with pytest.raises(ValueError, match=r"'escpae' is not a key name.*'escape'"):
            normalize_binding('escpae')

    def test_a_key_with_modifiers_in_keyboard_key_points_to_the_chord(self):
        with pytest.raises(ValueError, match=re.escape("keyboard.binding == 'ctrl+s'")):
            parse_when("keyboard.key == 'ctrl+s'")


class TestErrors:
    @pytest.mark.parametrize(
        ('text', 'message'),
        [
            ('keyboard.modifiers == 1', 'not a member'),
            ('time.delta > 0', 'time is a number'),
            ('keyboard == 1', 'needs a member'),
            ('banana == 1', 'is not a name'),
            ("keyboard.key == 'escpae'", "Did you mean 'escape'"),
            ("mouse.button == 'center'", "The choices are 'left', 'right', 'middle'"),
            ("keyboard.kind == 'push'", 'is not a keyboard kind'),
            ('len(deps) > 1', 'Call is not allowed'),
            ('keyboard.key ==', 'is not valid'),
            ("[x for x in 'ab']", 'ListComp is not allowed'),
            ('mouse.position == None', 'cannot be built'),
            ('not keyboard.key', 'not needs a comparison, but keyboard.key is a value'),
        ],
    )
    def test_a_bad_string_says_what_is_wrong(self, text, message):
        with pytest.raises(ValueError, match=message):
            parse_when(text)

    def test_the_suggestion_after_not_fits_the_value(self):
        with pytest.raises(ValueError, match=r'such as not root.time > 2'):
            parse_when('not root.time')
        with pytest.raises(ValueError, match=r"such as not mouse.button == 'left'"):
            parse_when('not mouse.button')
        with pytest.raises(ValueError, match=r"such as not keyboard.key == 'q'"):
            parse_when('not keyboard.key')

    def test_not_applies_to_a_constant_as_in_python(self):
        with pytest.raises(
            ValueError, match="'not True' is False, which is not a condition"
        ):
            parse_when('not True')
        with pytest.raises(
            ValueError, match="'not False' is True, which is not a condition"
        ):
            parse_when('not False')

    def test_the_message_shows_the_column(self):
        with pytest.raises(ValueError, match=r'at column 16') as error:
            parse_when('keyboard.key == banana.x == 3')
        assert 'keyboard.key == banana.x == 3' in str(error.value)

    def test_the_message_suggests_the_nearest_member(self):
        with pytest.raises(ValueError, match=r'Did you mean mouse.position'):
            parse_when('mouse.posiiton.x == 1')


class TestInputlessConditions:
    def test_a_string_that_reads_no_input_is_checked_at_each_step(self, canvas):
        ticks = []
        canvas.hook(lambda context: ticks.append(1), on='root.time > 0.15')
        for _ in range(4):
            canvas.clock.step(delta_seconds=0.1)
        assert ticks == [1, 1, 1]

    def test_every_and_after_make_a_condition_a_timed_hook(self, canvas):
        ticks = []
        canvas.hook(lambda context: ticks.append(1), on=root.time > 0.15, every=0.1)
        for _ in range(4):
            canvas.clock.step(delta_seconds=0.1)
        assert ticks

    def test_an_expression_and_a_function_hear_every_input_event(self, canvas):
        events = [Event.key_press('a'), Event.paste('x')]
        assert hook_heard(canvas, root.time >= 0, *events) == 2
        assert hook_heard(canvas, lambda context: True, *events) == 2

    def test_reading_an_input_and_time_hears_that_input(self, canvas):
        events = [Event.key_press('a'), Event.paste('x')]
        assert hook_heard(canvas, "keyboard.key == 'a' and root.time >= 0", *events) == 1


class TestUnseenValues:
    def test_not_equal_is_false_for_a_value_the_event_did_not_carry(self):
        native: list[str] = []
        python: list[str] = []
        with xnano.new(width=8, height=1, deps=1) as canvas:
            canvas.hook(
                lambda context: native.append(context.event.kind),
                on="keyboard.key != 'q'",
            )
            canvas.hook(
                lambda context: python.append(context.event.kind),
                on="keyboard.key != 'q' and deps",
            )
            canvas.push(Event.mouse_event(column=1, row=1, kind='move'))
            canvas.push(Event.key_press('r'))
            canvas.deliver_events()
        assert native == ['key']
        assert python == native

    def test_the_hyper_modifier_is_part_of_a_chord(self, canvas):
        assert normalize_binding('hyper+a') == 'hyper+a'
        heard: list[str] = []
        canvas.hook(
            lambda context: heard.append(context.keyboard.binding),
            on='key',
            keys=['hyper+a'],
        )
        canvas.push(Event.key_press('hyper+a'))
        canvas.push(Event.key_press('a'))
        canvas.deliver_events()
        assert heard == ['hyper+a']


class TestArithmeticErrors:
    def test_arithmetic_on_a_name_says_which_operands_are_not_numbers(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(
                ValueError, match=r'\+ cannot be applied to keyboard\.key and 1'
            ):
                canvas.hook(lambda context: None, on='keyboard.key + 1')
