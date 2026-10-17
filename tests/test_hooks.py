"""
tests.test_hooks

One hook, one native registration, the events it hears and how generator hooks wait.
"""

from __future__ import annotations

import pytest

import xnano
from xnano._hooks import HookHandle
from xnano.context import Context
from xnano.errors import TerminalError
from xnano_core import Buffer, Event, Style


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=6, fps=10) as opened:
        yield opened


def push(canvas, *events: Event) -> None:
    for event in events:
        canvas.push(event)
    canvas.deliver_events()


def press(column: int, row: int, kind: str = 'press') -> Event:
    return Event.mouse_event(column=column, row=row, kind=kind, button='left')


class TestRegistration:
    def test_hook_always_returns_a_handle(self, canvas):
        assert isinstance(canvas.hook(lambda context: None), HookHandle)
        assert isinstance(
            canvas.hook(lambda context: None, on='tick', every=1), HookHandle
        )

        @canvas.hook(on='key')
        def decorated(context: Context) -> None:
            pass

        assert isinstance(decorated, HookHandle)
        assert decorated.on == 'key'
        assert decorated.function.__name__ == 'decorated'

    def test_each_handle_is_one_native_hook(self, canvas):
        first = canvas.hook(lambda context: None, on='key')
        second = canvas.hook(lambda context: None, on='key')
        assert first._core_hook is not None
        assert first._core_hook is not second._core_hook
        assert canvas._registrations == [first, second]

    def test_an_event_that_does_not_match_builds_no_context(self, canvas, monkeypatch):
        built: list[int] = []
        original = Context.__init__

        def spy(self, *arguments):
            built.append(1)
            original(self, *arguments)

        heard: list[str] = []
        canvas.hook(
            lambda context: heard.append(context.keyboard.key), on='key', keys='q'
        )
        monkeypatch.setattr(Context, '__init__', spy)
        push(canvas, Event.key_press('a'), Event.key_press('b'))
        assert built == []
        push(canvas, Event.key_press('q'))
        assert built == [1]
        assert heard == ['q']

    def test_removing_a_hook_stops_it_and_twice_is_harmless(self, canvas):
        heard: list[int] = []
        handle = canvas.hook(lambda context: heard.append(1), on='key')
        push(canvas, Event.key_press('a'))
        handle.remove()
        handle.remove()
        push(canvas, Event.key_press('a'))
        assert heard == [1]
        assert handle.is_removed
        assert handle not in canvas._registrations

    def test_a_hook_can_remove_itself(self, canvas):
        heard: list[int] = []

        def once(context: Context) -> None:
            heard.append(1)
            context.hook.remove()

        canvas.hook(once, on='key')
        push(canvas, Event.key_press('a'), Event.key_press('b'))
        assert heard == [1]

    def test_a_bare_hook_hears_input_but_not_state_changes(self, canvas):
        kinds: list[str] = []
        canvas.hook(lambda context: kinds.append(context.event.kind))
        push(
            canvas,
            Event.key_press('a'),
            Event.paste('x'),
            Event.custom('ping'),
            Event.resize(width=10, height=3),
            Event.focus_gained(),
            Event.mouse_event(column=1, row=1, kind='move'),
        )
        assert kinds == ['key', 'paste', 'custom', 'resize', 'focus_gained', 'mouse']

    def test_the_kinds_of_events(self, canvas):
        heard: dict[str, list[str]] = {name: [] for name in ('paste', 'focus', 'custom')}
        for name in heard:
            canvas.hook(
                lambda context, name=name: heard[name].append(context.event.kind), on=name
            )
        push(
            canvas,
            Event.paste('x'),
            Event.focus_lost(),
            Event.focus_gained(),
            Event.custom('ping'),
            Event.key_press('a'),
        )
        assert heard == {
            'paste': ['paste'],
            'focus': ['focus_lost', 'focus_gained'],
            'custom': ['custom'],
        }

    def test_resize_reaches_a_canvas_hook(self, canvas):
        sizes = []
        canvas.hook(lambda context: sizes.append(context.event.size.width), on='resize')
        push(canvas, Event.resize(width=33, height=4))
        assert sizes == [33]


class TestKeys:
    def test_names_and_chords(self, canvas):
        heard: list[str] = []
        canvas.hook(
            lambda context: heard.append(context.keyboard.key),
            on='key',
            keys=['q', 'ctrl+s', 'escape'],
        )
        push(
            canvas,
            Event.key_press('q'),
            Event.key_press('s'),
            Event.key_press('ctrl+s'),
            Event.key_press('esc'),
        )
        assert heard == ['q', 's', 'escape']

    def test_a_single_key_name_is_accepted(self, canvas):
        heard: list[str] = []
        canvas.hook(lambda context: heard.append('x'), on='key', keys='enter')
        push(canvas, Event.key_press('return'))
        assert heard == ['x']

    def test_keys_hear_presses_and_repeats_but_not_releases(self, canvas):
        heard: list[str] = []
        canvas.hook(
            lambda context: heard.append(context.keyboard.kind), on='key', keys='a'
        )
        push(
            canvas,
            Event.key_press('a'),
            Event.key_press('a', kind='repeat'),
            Event.key_press('a', kind='release'),
        )
        assert heard == ['press', 'repeat']

    def test_releases_are_heard_by_testing_the_kind(self, canvas):
        heard: list[str] = []
        canvas.hook(
            lambda context: heard.append(context.keyboard.key),
            on='key',
            when="keyboard.kind == 'release'",
        )
        push(canvas, Event.key_press('a'), Event.key_press('b', kind='release'))
        assert heard == ['b']

    def test_a_misspelled_key_is_an_error_with_the_closest_names(self, canvas):
        with pytest.raises(ValueError, match=r"'escpae' is not a key name.*'escape'"):
            canvas.hook(lambda context: None, on='key', keys='escpae')

    def test_the_condition_and_the_keys_are_combined(self, canvas):
        heard: list[str] = []
        canvas.hook(
            lambda context: heard.append(context.keyboard.key),
            on='key',
            keys=['a', 'b'],
            when=lambda context: context.keyboard.key == 'b',
        )
        push(canvas, Event.key_press('a'), Event.key_press('b'))
        assert heard == ['b']


class TestArguments:
    @pytest.mark.parametrize(
        ('arguments', 'message'),
        [
            ({'every': 1}, r'every= needs an on= to say what it applies to'),
            ({'after': 1}, r'after= needs an on='),
            ({'keys': 'a'}, r'keys= needs an on='),
            (
                {'on': 'key', 'every': 1},
                r"every= is for on='tick' \(seconds\) or on='beat'",
            ),
            ({'on': 'tick', 'every': 1, 'after': 2}, 'cannot be given together'),
            ({'on': 'tick', 'keys': 'a'}, r"keys= is for on='key'"),
            ({'on': 'tick', 'every': 0}, 'must be a number above 0'),
            ({'on': 'tick', 'after': -1}, 'must be a number 0 or more'),
            ({'on': 'click'}, r"""on='mouse', when="mouse.kind == 'press'\""""),
            ({'on': 'immediate'}, r"on='tick', after=0.0"),
            ({'on': 'state_change'}, r"on='state'"),
            ({'on': 'kye'}, r"Did you mean 'key'"),
        ],
    )
    def test_a_bad_combination_names_the_fix(self, canvas, arguments, message):
        with pytest.raises(ValueError, match=message):
            canvas.hook(lambda context: None, **arguments)

    def test_resize_on_a_placement_says_to_use_the_canvas(self, canvas):
        placement = canvas.write('x')
        with pytest.raises(ValueError, match='register this hook on the canvas'):
            placement.hook(lambda context: None, on='resize')

    def test_requires_deps_says_how_to_give_them(self, canvas):
        with pytest.raises(TerminalError, match=r'xnano.new\(deps='):
            canvas.hook(lambda context: None, requires_deps=True)
        with xnano.new(width=4, height=1, deps={'name': 'x'}) as with_deps:
            handle = with_deps.hook(lambda context: None, requires_deps=True)
            assert isinstance(handle, HookHandle)

    def test_deps_are_on_the_context(self):
        seen = []
        with xnano.new(width=4, height=1, deps={'name': 'x'}) as canvas:
            canvas.hook(lambda context: seen.append(context.deps['name']), on='key')
            push(canvas, Event.key_press('a'))
        assert seen == ['x']

    def test_the_decorator_form_needs_no_function(self, canvas):
        assert callable(canvas.hook(on='key'))


class TestTime:
    def test_tick_every_runs_once_per_interval_in_one_step(self, canvas):
        ticks = []
        canvas.hook(
            lambda context: ticks.append(context.event.is_fixed_step),
            on='tick',
            every=0.1,
        )
        canvas.step(delta_seconds=2.0)
        assert len(ticks) == 20
        assert all(ticks)

    def test_tick_without_every_runs_each_step(self, canvas):
        ticks = []
        canvas.hook(lambda context: ticks.append(context.event.delta_seconds), on='tick')
        for _ in range(3):
            canvas.step(delta_seconds=0.1)
        assert len(ticks) == 3

    def test_tick_after_runs_once_with_no_event(self, canvas):
        seen = []
        canvas.hook(lambda context: seen.append(context.event), on='tick', after=0.25)
        for _ in range(5):
            canvas.step(delta_seconds=0.1)
        assert seen == [None]

    def test_frame_hooks_see_a_frame(self, canvas):
        frames = []
        canvas.hook(lambda context: frames.append(context.event.index), on='frame')
        for _ in canvas.iter(count=3):
            pass
        assert len(frames) >= 3
        assert frames == sorted(frames)

    def test_beat_every_follows_the_bpm_and_a_change_applies_from_the_next_beat(self):
        with xnano.new(width=8, height=1, bpm=120) as canvas:
            beats = []
            canvas.hook(
                lambda context: beats.append(round(context.time.elapsed, 2)), on='beat'
            )
            canvas.step(delta_seconds=0.5)
            canvas.step(delta_seconds=0.5)
            assert beats == [0.5, 1.0]
            canvas.bpm = 60
            for _ in range(4):
                canvas.step(delta_seconds=0.5)
            assert beats == [0.5, 1.0, 1.5, 2.5]

    def test_beat_every_n_and_after_n(self):
        with xnano.new(width=8, height=1, bpm=120) as canvas:
            every = []
            after = []
            canvas.hook(lambda context: every.append(1), on='beat', every=2)
            canvas.hook(lambda context: after.append(1), on='beat', after=1)
            for _ in range(8):
                canvas.step(delta_seconds=0.5)
            assert len(every) == 4
            assert after == [1]

    def test_a_manual_canvas_runs_every_beat_that_a_big_step_crossed(self):
        with xnano.new(width=8, height=1, bpm=120) as canvas:
            beats = []
            canvas.hook(lambda context: beats.append(1), on='beat')
            canvas.step(delta_seconds=3.0)
            assert len(beats) == 6

    def test_the_ledger_stays_small_over_many_beats(self):
        with xnano.new(width=8, height=1, bpm=600) as canvas:
            canvas.hook(lambda context: None, on='beat')
            canvas.step(delta_seconds=1.0)
            size = len(canvas._ledger)
            for _ in range(100):
                canvas.step(delta_seconds=1.0)
            assert len(canvas._ledger) == size

    def test_a_timer_does_not_run_after_removal(self, canvas):
        ticks = []
        handle = canvas.hook(lambda context: ticks.append(1), on='beat', after=1)
        handle.remove()
        canvas.step(delta_seconds=5.0)
        assert ticks == []

    def test_stopping_time_stops_timers(self, canvas):
        ticks = []
        canvas.hook(lambda context: ticks.append(1), on='tick', every=0.1)
        canvas.stop()
        canvas.deliver_events()
        assert ticks == []
        canvas.resume()
        canvas.step(delta_seconds=0.25)
        assert len(ticks) == 2

    def test_a_condition_gates_a_timed_hook(self, canvas):
        ticks = []
        canvas.hook(
            lambda context: ticks.append(1), on='tick', every=0.1, when='root.time > 0.5'
        )
        canvas.step(delta_seconds=0.4)
        assert ticks == []
        canvas.step(delta_seconds=0.4)
        assert len(ticks) == 4


class TestGenerators:
    def test_each_resume_receives_a_new_context(self, canvas):
        seen: list[Context] = []

        @canvas.hook(on='key')
        def spell(context: Context):
            while True:
                seen.append(context)
                context = yield

        for name in 'abc':
            push(canvas, Event.key_press(name))
        assert [context.keyboard.key for context in seen] == ['a', 'b', 'c']
        assert seen[0] is not seen[1] is not seen[2]

    def test_a_finished_generator_starts_again_on_the_next_event(self, canvas):
        runs: list[str] = []

        @canvas.hook(on='key')
        def two(context: Context):
            runs.append(f'start {context.keyboard.key}')
            context = yield
            runs.append(f'second {context.keyboard.key}')

        for name in 'abcd':
            push(canvas, Event.key_press(name))
        assert runs == ['start a', 'second b', 'start c', 'second d']

    def test_yielding_a_value_teaches_the_bare_yield(self):
        with pytest.raises(TerminalError, match=r"'context = yield'") as error:
            with xnano.new(width=8, height=1) as canvas:

                @canvas.hook(on='key')
                def wait(context: Context):
                    yield 1.5

                push(canvas, Event.key_press('a'))
        assert 'hook(on=' in str(error.value)
        assert ').. ' not in str(error.value)
        assert 'open()..' not in str(error.value)

    def test_a_condition_that_reads_only_deps_needs_an_event_kind(self, canvas):
        with pytest.raises(ValueError, match='no on='):
            canvas.hook(lambda context: None, when='deps.x == 1')

    def test_removing_closes_the_generator(self, canvas):
        closed: list[bool] = []

        def watch(context: Context):
            try:
                while True:
                    yield
            finally:
                closed.append(True)

        handle = canvas.hook(watch, on='key')
        push(canvas, Event.key_press('a'))
        handle.remove()
        assert closed == [True]

    def test_a_drag_loop_ends_with_the_release(self, canvas):
        track = canvas.write(' ' * 10, y=1)
        thumb = track.write('#', x=(0, 9))
        finished: list[int] = []

        @thumb.hook(on='drag')
        def slide(context: Context):
            while context.mouse.is_down:
                thumb.x = context.parent.local(context.mouse.position).x
                context = yield
            finished.append(thumb.x)

        push(canvas, press(0, 1), press(4, 1, 'drag'), press(6, 1, 'drag'))
        assert thumb.x == 6
        assert finished == []
        push(canvas, press(6, 1, 'release'))
        assert finished == [6]

    def test_a_press_alone_runs_nothing_on_a_drag_hook(self, canvas):
        placement = canvas.write('#')
        heard = []
        placement.hook(lambda context: heard.append(context.mouse.kind), on='drag')
        push(canvas, press(0, 0), press(0, 0, 'release'))
        assert heard == []
        push(canvas, press(0, 0), press(1, 0, 'drag'), press(1, 0, 'release'))
        assert heard == ['drag']


class TestRegions:
    def test_a_mouse_hook_hears_only_the_pointer_inside_its_placement(self, canvas):
        box = canvas.write(Buffer(width=4, height=2), x=5, y=2)
        heard = []
        box.hook(lambda context: heard.append(context.mouse.position.x), on='mouse')
        push(
            canvas,
            Event.mouse_event(column=1, row=0, kind='move'),
            Event.mouse_event(column=6, row=3, kind='move'),
            Event.mouse_event(column=9, row=3, kind='move'),
        )
        assert heard == [6]

    def test_a_scroll_hook_hears_only_the_wheel_inside_its_placement(self, canvas):
        box = canvas.write(Buffer(width=4, height=2), x=5, y=2)
        heard = []
        box.hook(lambda context: heard.append(context.scroll.y), on='scroll')
        push(
            canvas,
            Event.mouse_event(column=1, row=0, kind='scroll', scroll_y=-1),
            Event.mouse_event(column=6, row=3, kind='scroll', scroll_y=1),
            Event.mouse_event(column=6, row=3, kind='move'),
        )
        assert heard == [1]

    def test_the_wheel_is_not_a_mouse_event(self, canvas):
        kinds = []
        canvas.hook(lambda context: kinds.append('mouse'), on='mouse')
        canvas.hook(lambda context: kinds.append('scroll'), on='scroll')
        push(canvas, Event.mouse_event(column=1, row=1, kind='scroll', scroll_y=-1))
        push(canvas, Event.mouse_event(column=1, row=1, kind='move'))
        assert kinds == ['scroll', 'mouse']

    def test_a_press_captures_the_pointer_until_the_release(self, canvas):
        box = canvas.write(Buffer(width=3, height=1), x=2, y=2)
        heard = []
        box.hook(lambda context: heard.append(context.mouse.kind), on='mouse')
        push(
            canvas,
            press(3, 2),
            press(15, 5, 'drag'),
            press(15, 5, 'release'),
            press(15, 5, 'drag'),
        )
        assert heard == ['press', 'drag', 'release']

    def test_a_matching_hook_consumes_the_event_for_ancestors(self, canvas):
        box = canvas.write(Buffer(width=4, height=2), x=0, y=0)
        heard = []
        canvas.hook(lambda context: heard.append('canvas'), on='mouse')
        box.hook(lambda context: heard.append('box'), on='mouse')
        push(canvas, Event.mouse_event(column=1, row=1, kind='move'))
        assert heard == ['box']

    def test_a_hook_that_does_not_match_lets_the_event_through(self, canvas):
        box = canvas.write(Buffer(width=4, height=2), x=0, y=0)
        heard = []
        canvas.hook(lambda context: heard.append('canvas'), on='mouse')
        box.hook(
            lambda context: heard.append('box'), on='mouse', when="mouse.kind == 'press'"
        )
        push(canvas, Event.mouse_event(column=1, row=1, kind='move'))
        assert heard == ['canvas']

    def test_a_key_reaches_every_buffer_while_nothing_has_focus(self, canvas):
        first = canvas.write('x')
        second = canvas.write('y', y=1)
        heard = []
        first.hook(lambda context: heard.append('first'), on='key')
        second.hook(lambda context: heard.append('second'), on='key')
        canvas.hook(lambda context: heard.append('canvas'), on='key')
        push(canvas, Event.key_press('r'))
        assert sorted(heard) == ['canvas', 'first', 'second']

    def test_two_hooks_on_one_buffer_both_run(self, canvas):
        heard = []
        canvas.hook(lambda context: heard.append(1), on='key')
        canvas.hook(lambda context: heard.append(2), on='key')
        push(canvas, Event.key_press('a'))
        assert heard == [1, 2]


class TestResults:
    def test_a_returned_style_is_applied_to_the_target(self, canvas):
        label = canvas.write('hi')

        @label.hook(on='key')
        def tint(context: Context):
            return Style(foreground='red')

        push(canvas, Event.key_press('a'))
        assert str(label.core_buffer[0, 0].foreground) == "Color('red')"

    def test_returning_a_buffer_or_text_teaches_the_renderable_decorator(self):
        with pytest.raises(TerminalError, match=r'@xnano.renderable'):
            with xnano.new(width=8, height=1) as canvas:
                canvas.hook(lambda context: 'text', on='key')
                push(canvas, Event.key_press('a'))

    def test_an_error_in_a_hook_names_the_function(self):
        def explode(context: Context) -> None:
            raise ZeroDivisionError('nope')

        with pytest.raises(
            TerminalError, match=r'The hook explode failed.*ZeroDivisionError'
        ):
            with xnano.new(width=8, height=1) as canvas:
                canvas.hook(explode, on='key')
                push(canvas, Event.key_press('a'))


class TestGates:
    """Gates are inferred, or refused with the fix, when a canvas is attached to a screen."""

    def test_an_unset_gate_is_turned_on_by_a_hook(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: None, on='scroll')
            canvas.hook(lambda context: None, on='mouse')
            resolved = canvas._gates_for_screen({})
            assert resolved['scroll'] is True
            assert resolved['mouse'] is True

    def test_a_hook_that_needs_nothing_leaves_the_gates_alone(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: None, on='key')
            resolved = canvas._gates_for_screen({})
            assert resolved['scroll'] is False
            assert resolved['mouse'] is False

    def test_a_bare_hook_that_reads_the_mouse_turns_it_on(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: None, when='mouse.is_down')
            assert canvas._gates_for_screen({})['mouse'] is True

    @pytest.mark.parametrize(
        ('on', 'gate'),
        [('scroll', 'scroll'), ('mouse', 'mouse'), ('drag', 'mouse'), ('paste', 'paste')],
    )
    def test_an_explicit_false_stays_off_and_the_hook_is_refused(self, on, gate):
        with xnano.new(width=8, height=1) as canvas:

            def listener(context: Context) -> None:
                pass

            canvas.hook(listener, on=on)
            with pytest.raises(TerminalError, match=rf'hook listener needs {gate}=True'):
                canvas._gates_for_screen({gate: False})

    def test_the_keyboard_gate_when_off(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: None, on='key')
            with pytest.raises(TerminalError, match='needs keyboard=True'):
                canvas._gates_for_screen({'keyboard': False})

    def test_focus_hooks_need_the_focus_gate(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: None, on='focus')
            with pytest.raises(TerminalError, match='needs focus=True'):
                canvas._gates_for_screen({'focus': False})

    def test_a_release_test_needs_the_release_gate(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: None, on='key', when="keyboard.kind == 'release'")
            with pytest.raises(TerminalError, match="needs keyboard='release_events'"):
                canvas._gates_for_screen({})
            assert canvas._gates_for_screen({'keyboard': 'release_events'})[
                'keyboard'
            ] == ('release_events')

    def test_not_equal_to_release_does_not_need_the_gate(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: None, on='key', when="keyboard.kind != 'release'")
            assert canvas._gates_for_screen({})['keyboard'] is True

    def test_the_error_says_how_to_turn_the_gate_on(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: None, on='scroll')
            with pytest.raises(TerminalError) as error:
                canvas._gates_for_screen({'scroll': False})
            text = str(error.value)
            assert 'xnano.new(scroll=True)' in text
            assert 'canvas.open(scroll=True)' in text
            assert 'scroll=False' in text
