"""
tests.test_components

Renderable and playable components: protocols, decorators, what makes one run again, hooks on
components and dependencies.
"""

from __future__ import annotations

import dataclasses
import warnings

import pytest

import xnano
import xnano.audio
from xnano.components import (
    ComponentContext,
    ComponentHook,
    PlayableComponent,
    PlayableFunction,
    RenderableComponent,
    RenderableFunction,
)
from xnano.context import Context
from xnano.errors import TerminalError
from xnano_core import Buffer, Event, Fill


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=6, fps=10) as opened:
        yield opened


def push(canvas, *events: Event) -> None:
    for event in events:
        canvas.push(event)
    canvas.deliver_events()


def text_of(placement) -> str:
    return placement.core_buffer.text.rstrip('\n')


class TestDecorators:
    def test_the_decorated_function_is_the_component(self, canvas):
        @xnano.renderable
        def gauge(context: Context, ratio: float = 0.5) -> str:
            return '#' * round(ratio * 10)

        assert isinstance(gauge, RenderableFunction)
        assert text_of(canvas.write(gauge)) == '#####'
        bound = gauge(ratio=0.2)
        assert isinstance(bound, RenderableComponent)
        assert dict(bound.arguments) == {'ratio': 0.2}
        assert text_of(canvas.write(bound)) == '##'
        assert gauge.__name__ == 'gauge'

    def test_own_parameters_are_bound_positionally_or_by_name(self, canvas):
        @xnano.renderable
        def label(context: Context, text: str, repeat: int = 1) -> str:
            return text * repeat

        assert text_of(canvas.write(label('ab', 2))) == 'abab'
        assert text_of(canvas.write(label(text='x'))) == 'x'

    def test_a_component_needing_arguments_says_how_to_give_them(self, canvas):
        @xnano.renderable
        def label(context: Context, text: str) -> str:
            return text

        with pytest.raises(TypeError, match=r'canvas.write\(label\(\.\.\.\)\)'):
            canvas.write(label)
        with pytest.raises(TypeError, match='cannot be called with those arguments'):
            label()
        with pytest.raises(TypeError, match='cannot be called with those arguments'):
            label('a', colour='red')  # type: ignore[call-arg]

    def test_the_function_must_take_a_context(self):
        with pytest.raises(TypeError, match='first parameter is the context'):

            @xnano.renderable
            def nothing() -> str:  # type: ignore[misc]
                return ''

    def test_a_failed_first_run_leaves_nothing_on_the_canvas(self, canvas):
        @xnano.renderable
        def broken(context: Context) -> str:
            raise ValueError('no')

        with pytest.raises(ValueError, match='no'):
            canvas.write(broken)
        assert canvas._placements == []

    def test_playable_functions_mirror_renderable_ones(self, canvas):
        @xnano.playable
        def tune(context: Context, root: str = 'C4') -> xnano.Note:
            return xnano.note(root, beats=0.5)

        assert isinstance(tune, PlayableFunction)
        assert isinstance(tune(root='E4'), PlayableComponent)
        assert tune.__xnano_play__(None).pitch == 'C4'  # type: ignore[arg-type]


class TestProtocols:
    def test_a_plain_class_qualifies(self, canvas):
        class Greeting:
            def __xnano_render__(self, context: Context) -> str:
                return 'hello'

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            assert text_of(canvas.write(Greeting())) == 'hello'

    def test_a_frozen_dataclass_qualifies_and_gives_no_warning(self, canvas):
        @dataclasses.dataclass(frozen=True)
        class Badge:
            name: str

            def __xnano_render__(self, context: Context) -> str:
                return f'[{self.name}]'

        with warnings.catch_warnings():
            warnings.simplefilter('error')
            assert text_of(canvas.write(Badge('ok'))) == '[ok]'

    def test_a_class_that_can_change_warns_once_and_refresh_draws_it_again(self, canvas):
        @dataclasses.dataclass
        class Counter:
            count: int = 0

            def __xnano_render__(self, context: Context) -> str:
                return str(self.count)

        counter = Counter()
        with pytest.warns(UserWarning, match='Counter is drawn once') as caught:
            placement = canvas.write(counter)
        assert len(caught) == 1
        assert caught[0].filename == __file__, 'the warning points at the write() call'
        counter.count = 7
        canvas.step()
        assert text_of(placement) == '0', (
            'nothing it read changed, so it is not run again'
        )
        placement.refresh()
        canvas.step()
        assert text_of(placement) == '7'
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            canvas.write(Counter())

    def test_both_protocols_on_one_class(self, canvas):
        class Both:
            def __xnano_render__(self, context: Context) -> str:
                return 'show'

            def __xnano_play__(self, context: Context) -> xnano.Note:
                return xnano.note('C4', beats=0.5)

        both = Both()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            assert text_of(canvas.write(both)) == 'show'
        canvas.play(both)
        canvas.step(delta_seconds=0.25)
        assert canvas.audio.render_sound().peak > 0.0

    def test_a_return_value_that_cannot_be_shown_names_the_method(self, canvas):
        class Broken:
            def __xnano_render__(self, context: Context) -> int:
                return 1

        with pytest.raises(TypeError, match=r'Broken.__xnano_render__ returned int'):
            canvas.write(Broken())  # type: ignore[arg-type]

    def test_a_component_that_returns_itself_is_a_cycle(self, canvas):
        class Mirror:
            def __xnano_render__(self, context: Context) -> object:
                return self

        with pytest.raises(TerminalError, match='keeps returning something that renders'):
            canvas.write(Mirror())  # type: ignore[arg-type]

    def test_a_component_cannot_return_a_canvas(self, canvas):
        child = xnano.new(width=4, height=1)

        class Holder:
            def __xnano_render__(self, context: Context) -> object:
                return child

        with pytest.raises(TypeError, match=r'canvas.write\(child\) directly'):
            canvas.write(Holder())  # type: ignore[arg-type]
        child.close()

    def test_writing_something_that_only_plays_says_it_has_no_render_method(self, canvas):
        class OnlyPlay:
            def __xnano_play__(self, context: Context) -> xnano.Note:
                return xnano.note('C4')

        with pytest.raises(TypeError, match='no __xnano_render__ method') as caught:
            canvas.write(OnlyPlay())  # type: ignore[arg-type]
        assert type(caught.value) is TypeError

    def test_playing_something_that_only_renders_names_the_missing_method(self, canvas):
        class OnlyRender:
            def __xnano_render__(self, context: Context) -> str:
                return 'x'

        with pytest.raises(TypeError, match='no __xnano_play__ method') as caught:
            canvas.play(OnlyRender())  # type: ignore[arg-type]
        assert 'an object with __xnano_play__' in str(caught.value)

    def test_something_without_the_protocol_is_explained(self, canvas):
        with pytest.raises(TypeError, match='__xnano_render__'):
            canvas.write(object())  # type: ignore[arg-type]

    def test_the_old_buffer_protocol_is_gone(self, canvas):
        class Old:
            def __xnano_buffer__(self) -> Buffer:
                return Buffer.with_text('x')

        with pytest.raises(TypeError, match='Cannot show a Old'):
            canvas.write(Old())  # type: ignore[arg-type]

    def test_a_sequence_is_stacked_and_may_hold_components(self, canvas):
        @xnano.renderable
        def rule(context: Context) -> str:
            return '--'

        placement = canvas.write(['one', rule, xnano.write('end')])  # type: ignore[list-item]
        assert (placement.width, placement.height) == (3, 3)
        assert text_of(placement).splitlines() == ['one', '--', 'end']

    def test_a_pixel_and_a_region_still_write_directly(self, canvas):
        assert canvas.write(xnano.Pixel('star')).width == 1
        assert canvas.write(xnano.write('ab')).width == 2


class TestWhenItRunsAgain:
    def counting(self, reads):
        calls = []

        @xnano.renderable
        def counter(context: Context) -> str:
            calls.append(1)
            reads(context)
            return str(len(calls))

        return counter, calls

    def test_a_component_that_read_nothing_runs_once(self, canvas):
        counter, calls = self.counting(lambda context: None)
        canvas.write(counter)
        canvas.step(delta_seconds=1.0)
        canvas.step(delta_seconds=1.0)
        assert len(calls) == 1

    def test_reading_the_time_runs_it_every_frame_until_removed(self, canvas):
        counter, calls = self.counting(lambda context: context.time.elapsed)
        placement = canvas.write(counter)
        canvas.step(delta_seconds=0.1)
        canvas.step(delta_seconds=0.1)
        assert len(calls) == 3
        assert text_of(placement) == '3'
        placement.remove()
        canvas.step(delta_seconds=0.1)
        assert len(calls) == 3
        assert canvas._frame_demand == 0

    @pytest.mark.parametrize('spelling', ['root', 'canvas'])
    def test_reading_the_time_through_the_canvas_runs_it_every_frame(
        self, canvas, spelling
    ):
        counter, calls = self.counting(
            lambda context: getattr(context, spelling).time.elapsed
        )
        placement = canvas.write(counter)
        canvas.step(delta_seconds=0.1)
        canvas.step(delta_seconds=0.1)
        assert len(calls) == 3
        assert text_of(placement) == '3'
        placement.remove()
        canvas.step(delta_seconds=0.1)
        assert len(calls) == 3
        assert canvas._frame_demand == 0

    def test_a_buffer_changed_in_place_shows_when_the_component_runs_again(self, canvas):
        shared = Buffer.with_text('aaaa')
        standalone = xnano.write('bbbb')

        @xnano.renderable
        def first(context: Context) -> Buffer:
            _ = context.time.elapsed
            return shared

        @xnano.renderable
        def second(context: Context) -> xnano.Region:
            _ = context.time.elapsed
            return standalone

        canvas.write(first)
        canvas.write(second, y=1)
        canvas.step(delta_seconds=0.1)
        shared.update(Fill('z'))
        standalone[0, 0] = xnano.Pixel('Q')
        canvas.step(delta_seconds=0.1)
        canvas.step(delta_seconds=0.1)
        rendered = canvas.render()
        assert 'zzzz' in rendered
        assert 'Qbbb' in rendered

    def test_a_frame_without_time_passing_does_not_run_it(self, canvas):
        counter, calls = self.counting(lambda context: context.time.elapsed)
        canvas.write(counter)
        canvas.deliver_events()
        canvas.deliver_events()
        assert len(calls) == 1

    def test_reading_state_runs_it_when_the_path_changes(self, canvas):
        counter, calls = self.counting(
            lambda context: context.root.state.get('score', default=0)
        )
        placement = canvas.write(counter)
        canvas.state.push('other', 1)
        canvas.deliver_events()
        assert len(calls) == 1, 'an unrelated path does not run it'
        canvas.state.push('score', 3)
        canvas.deliver_events()
        assert len(calls) == 2
        assert text_of(placement) == '2'

    def test_a_state_change_made_by_the_component_does_not_run_it_again(self, canvas):
        calls = []

        @xnano.renderable
        def tally(context: Context) -> str:
            calls.append(1)
            state = context.root.state
            state.push('seen', int(state.get('seen', default=0) or 0) + 1)
            return str(state.get('seen'))

        placement = canvas.write(tally)
        canvas.deliver_events()
        canvas.deliver_events()
        assert len(calls) == 1
        assert text_of(placement) == '1'
        assert canvas.state.get('seen') == 1

    def test_reading_an_input_runs_it_once_per_frame_however_many_events(self, canvas):
        counter, calls = self.counting(lambda context: context.keyboard.key)
        placement = canvas.write(counter)
        for letter in 'abc':
            canvas.push(Event.key_press(letter))
        canvas.deliver_events()
        assert len(calls) == 2, 'one evaluation for the burst of three keys'
        assert text_of(placement) == '2'
        canvas.deliver_events()
        assert len(calls) == 2

    def test_a_component_sees_the_key_that_woke_it(self, canvas):
        @xnano.renderable
        def last(context: Context) -> str:
            return context.keyboard.key or '-'

        placement = canvas.write(last)
        assert text_of(placement) == '-'
        push(canvas, Event.key_press('q'))
        assert text_of(placement) == 'q'

    def test_pointer_events_outside_the_placement_do_not_run_it(self, canvas):
        counter, calls = self.counting(lambda context: context.mouse.position)
        canvas.write(counter, x=10, y=2)
        push(canvas, Event.mouse_event(column=1, row=1, kind='move', button='left'))
        assert len(calls) == 1
        push(canvas, Event.mouse_event(column=10, row=2, kind='move', button='left'))
        assert len(calls) == 2

    def test_reading_the_size_runs_it_when_the_placement_size_changes(self, canvas):
        sizes = []

        @xnano.renderable
        def sized(context: Context) -> str:
            sizes.append(context.buffer.width)
            return 'x'

        placement = canvas.write(sized, width=5)
        placement.width = 9
        canvas.step()
        assert sizes[-1] == 9

    def test_reading_the_size_runs_it_on_a_resize_of_the_canvas(self, canvas):
        counter, calls = self.counting(lambda context: context.size)
        canvas.write(counter)
        push(canvas, Event.resize(width=30, height=6))
        assert len(calls) == 2

    def test_a_formula_resize_shows_the_component_at_the_new_width_in_the_same_frame(
        self, canvas
    ):
        @xnano.renderable
        def ruler(context: Context) -> str:
            return '#' * context.buffer.width

        parent = canvas.write('', width=10, height=1)
        child = parent.write(ruler, width='100%')
        canvas.step()
        assert text_of(child) == '#' * 10
        parent.width = 20
        canvas.step()
        assert text_of(child) == '#' * 20

    def test_reading_the_dependencies_alone_runs_it_once(self):
        with xnano.new(width=6, height=1, deps={'name': 'ada'}) as canvas:

            @xnano.renderable
            def greet(context: Context[dict[str, str]]) -> str:
                return context.deps['name']

            placement = canvas.write(greet)
            canvas.step(delta_seconds=1.0)
            assert text_of(placement) == 'ada'

    def test_refresh_draws_a_component_again_after_a_dependency_changed(self):
        dependencies = {'name': 'ada'}
        with xnano.new(width=6, height=1, deps=dependencies) as canvas:

            @xnano.renderable
            def greet(context: Context[dict[str, str]]) -> str:
                return context.deps['name']

            placement = canvas.write(greet)
            dependencies['name'] = 'bob'
            canvas.step()
            assert text_of(placement) == 'ada'
            placement.refresh()
            canvas.step()
            assert text_of(placement) == 'bob'

    def test_refresh_on_a_plain_placement_does_nothing(self, canvas):
        canvas.write('hi').refresh()

    def test_the_placement_follows_the_size_of_the_content(self, canvas):
        words = ['a', 'bcd']

        @xnano.renderable
        def word(context: Context) -> str:
            return words[int(context.time.elapsed)]

        placement = canvas.write(word)
        assert placement.width == 1
        canvas.step(delta_seconds=1.0)
        assert placement.width == 3

    def test_a_given_size_is_kept(self, canvas):
        @xnano.renderable
        def word(context: Context) -> str:
            return 'abcdefgh' if context.time.elapsed else 'a'

        placement = canvas.write(word, width=4)
        canvas.step(delta_seconds=1.0)
        assert placement.width == 4
        assert text_of(placement) == 'abcd'

    def test_the_look_given_to_write_applies_to_the_component(self, canvas):
        @xnano.renderable
        def word(context: Context) -> str:
            return 'hi'

        placement = canvas.write(word, border='rounded')
        assert (placement.width, placement.height) == (4, 3)
        assert '╭' in placement.render()

    def test_a_failing_later_run_stops_the_canvas_with_a_teaching_error(self):
        @xnano.renderable
        def fragile(context: Context) -> str:
            if context.time.elapsed > 0.5:
                raise ValueError('too late')
            return 'ok'

        with pytest.raises(TerminalError, match='The component fragile failed'):
            with xnano.new(width=6, height=1) as failing:
                failing.write(fragile)
                failing.step(delta_seconds=1.0)

    def test_removing_the_placement_closes_the_driver(self, canvas):
        counter, calls = self.counting(lambda context: context.keyboard.key)
        placement = canvas.write(counter)
        driver = placement._driver
        placement.remove()
        assert driver.is_closed
        push(canvas, Event.key_press('a'))
        assert len(calls) == 1

    def test_plugin_state_belongs_to_one_placement_of_the_component(self, canvas):
        @xnano.renderable
        def tally(context: Context) -> str:
            state = context.plugin.state
            state.push('runs', int(state.get('runs', default=0) or 0) + 1)
            return str(state.get('runs'))

        first = canvas.write(tally)
        second = canvas.write(tally)
        assert text_of(first) == text_of(second) == '1'
        first._driver.refresh()
        canvas.deliver_events()
        assert text_of(first) == '2'
        assert text_of(second) == '1'


class TestComponentHooks:
    def test_a_hook_receives_the_context_and_the_component_context(self, canvas):
        @xnano.renderable
        def label(context: Context, text: str = 'x') -> str:
            return text

        seen = []

        @label.hook(on='key', keys='a')
        def heard(context: Context, component: ComponentContext) -> None:
            seen.append(
                (context.keyboard.key, component.arguments['text'], component.placement)
            )

        placement = canvas.write(label(text='hi'))
        push(canvas, Event.key_press('a'))
        assert seen == [('a', 'hi', placement)]
        assert isinstance(heard, ComponentHook)

    def test_a_hook_on_the_function_reaches_present_and_future_placements(self, canvas):
        @xnano.renderable
        def label(context: Context, text: str = 'x') -> str:
            return text

        first = canvas.write(label(text='one'))
        heard = []
        hook = label.hook(
            lambda context, component: heard.append(component.arguments['text']),
            on='key',
            keys='a',
        )
        assert len(hook.handles) == 1
        canvas.write(label(text='two'))
        assert len(hook.handles) == 2
        push(canvas, Event.key_press('a'))
        assert sorted(heard) == ['one', 'two']
        hook.remove()
        assert hook.is_removed and hook.handles == ()
        heard.clear()
        push(canvas, Event.key_press('a'))
        assert heard == []
        first.remove()

    def test_a_hook_on_a_bound_component_reaches_only_its_placements(self, canvas):
        @xnano.renderable
        def label(context: Context, text: str = 'x') -> str:
            return text

        mine, other = label(text='mine'), label(text='other')
        heard = []
        mine.hook(lambda context, component: heard.append('mine'), on='key', keys='a')
        canvas.write(mine)
        canvas.write(other)
        push(canvas, Event.key_press('a'))
        assert heard == ['mine']

    def test_a_hook_added_before_any_placement_is_installed_on_placing(self, canvas):
        @xnano.renderable
        def label(context: Context) -> str:
            return 'x'

        heard = []
        hook = label.hook(lambda context, component: heard.append(1), on='key', keys='a')
        assert hook.handles == ()
        canvas.write(label)
        push(canvas, Event.key_press('a'))
        assert heard == [1]

    def test_removing_a_placement_removes_its_hooks(self, canvas):
        @xnano.renderable
        def label(context: Context) -> str:
            return 'x'

        hook = label.hook(lambda context, component: None, on='key')
        placement = canvas.write(label)
        assert len(hook.handles) == 1
        placement.remove()
        assert hook.handles == ()

    def test_a_pointer_hook_hears_only_the_pointer_inside_the_placement(self, canvas):
        @xnano.renderable
        def button(context: Context) -> str:
            return '[ok]'

        presses = []
        button.hook(
            lambda context, component: presses.append(context.mouse.position.x),
            on='mouse',
            when="mouse.kind == 'press'",
        )
        canvas.write(button, x=5, y=1)
        push(canvas, Event.mouse_event(column=1, row=0, kind='press', button='left'))
        push(canvas, Event.mouse_event(column=6, row=1, kind='press', button='left'))
        assert presses == [6]

    def test_a_generator_hook_receives_a_new_context_at_each_yield(self, canvas):
        @xnano.renderable
        def knob(context: Context) -> str:
            return '#'

        track = []

        @knob.hook(on='drag')
        def drag(context: Context, component: ComponentContext):
            while context.mouse.is_down:
                track.append(context.mouse.position.x)
                context = yield
            track.append('done')

        canvas.write(knob, x=3, y=1)
        for column, kind in ((3, 'press'), (4, 'drag'), (5, 'drag'), (5, 'release')):
            push(
                canvas, Event.mouse_event(column=column, row=1, kind=kind, button='left')
            )
        assert track == [4, 5, 'done']

    def test_a_hook_decorator_returns_the_component_hook(self, canvas):
        @xnano.renderable
        def label(context: Context) -> str:
            return 'x'

        decorator = label.hook(on='key')
        assert callable(decorator)
        assert isinstance(decorator(lambda context, component: None), ComponentHook)

    def test_bad_hook_arguments_are_explained_at_once(self):
        @xnano.renderable
        def label(context: Context) -> str:
            return 'x'

        with pytest.raises(ValueError, match='keys= is for'):
            label.hook(lambda context, component: None, on='mouse', keys='a')
        with pytest.raises(ValueError, match='resize events are reported to the canvas'):
            label.hook(lambda context, component: None, on='resize')
        with pytest.raises(ValueError, match='needs an on='):
            label.hook(lambda context, component: None, every=1)

    def test_a_hook_function_may_be_a_condition_string(self, canvas):
        @xnano.renderable
        def label(context: Context) -> str:
            return 'x'

        heard = []
        label.hook(
            lambda context, component: heard.append(context.keyboard.key),
            on='key',
            when="keyboard.key == 'b'",
        )
        canvas.write(label)
        push(canvas, Event.key_press('a'), Event.key_press('b'))
        assert heard == ['b']


class TestDependencies:
    def test_requires_deps_names_the_hook_and_how_to_give_them(self, canvas):
        @xnano.renderable
        def label(context: Context) -> str:
            return 'x'

        placement = canvas.write(label)
        with pytest.raises(TerminalError, match=r'xnano\.new\(deps=') as caught:
            label.hook(lambda context, component: None, on='key', requires_deps=True)
        assert 'needs dependencies' in str(caught.value)
        assert placement is not None

    def test_requires_deps_is_checked_when_a_placement_is_made(self, canvas):
        @xnano.renderable
        def label(context: Context) -> str:
            return 'x'

        label.hook(lambda context, component: None, on='key', requires_deps=True)
        with pytest.raises(TerminalError, match='needs dependencies'):
            canvas.write(label)

    def test_a_canvas_with_dependencies_accepts_the_hook(self):
        with xnano.new(width=6, height=1, deps=object()) as canvas:

            @xnano.renderable
            def label(context: Context) -> str:
                return 'x'

            heard = []
            label.hook(
                lambda context, component: heard.append(context.deps is not None),
                on='key',
                requires_deps=True,
            )
            canvas.write(label)
            push(canvas, Event.key_press('a'))
            assert heard == [True]

    def test_context_deps_is_the_object_given_to_new(self):
        @dataclasses.dataclass
        class Services:
            name: str

        services = Services('db')
        with xnano.new(width=8, height=1, deps=services) as canvas:

            @xnano.renderable
            def label(context: Context[Services]) -> str:
                return context.deps.name

            assert text_of(canvas.write(label)) == 'db'


class TestPlayables:
    def test_a_component_cannot_play_without_a_canvas_and_the_error_says_so(self, canvas):
        @xnano.playable
        def tune(context: Context) -> xnano.Note:
            return xnano.note('C4')

        for play in (xnano.audio._plan_call, None):
            with pytest.raises(TypeError, match=r'needs a canvas to run in') as raised:
                if play is None:
                    canvas.audio.play(tune)
                else:
                    play(
                        tune,
                        bpm=120.0,
                        instrument=None,
                        beats=None,
                        velocity=None,
                        effects=None,
                        volume=1.0,
                        pan=0.0,
                        at_beat=None,
                    )
            assert 'canvas.play(component)' in str(raised.value)
            assert 'no __xnano_play__' not in str(raised.value)

    def test_a_playable_plays_once_when_it_read_nothing_that_changes(self, canvas):
        calls = []

        @xnano.playable
        def tune(context: Context) -> xnano.Note:
            calls.append(1)
            return xnano.note('C4', beats=0.5)

        handle = canvas.play(tune)
        canvas.step(delta_seconds=2.0)
        assert len(calls) == 1
        assert canvas.audio.render_sound().peak > 0.0
        assert handle.is_finished, 'the half beat note ended within the two seconds'
        handle.remove()
        assert handle.is_finished

    def test_a_playable_is_evaluated_on_beats_only(self, canvas):
        calls = []

        @xnano.playable
        def follow(context: Context) -> xnano.Note:
            calls.append(context.keyboard.key)
            return xnano.note('C4', beats=0.5)

        canvas.play(follow)
        assert calls == [None]
        push(canvas, Event.key_press('a'))
        assert calls == [None], 'a key only marks it; the next beat plays the new result'
        canvas.step(delta_seconds=0.5)
        assert calls == [None, 'a']
        canvas.step(delta_seconds=0.1)
        assert calls == [None, 'a']

    def test_reading_the_time_plays_it_again_every_beat(self, canvas):
        calls = []

        @xnano.playable
        def pulse(context: Context) -> xnano.Note:
            calls.append(context.time.elapsed)
            return xnano.note('C4', beats=0.25)

        handle = canvas.play(pulse)
        canvas.step(delta_seconds=1.0)
        assert len(calls) == 3, 'at bpm 120 a second holds two beats'
        assert not handle.is_finished
        handle.remove()
        canvas.step(delta_seconds=1.0)
        assert len(calls) == 3

    def test_a_playable_makes_the_sound_the_function_returns(self, canvas):
        @xnano.playable
        def chord(context: Context, root: str = 'C4') -> list[xnano.Note]:
            return [xnano.note(root, beats=0.5), xnano.note('G4', beats=0.5)]

        canvas.play(chord(root='E4'))
        canvas.step(delta_seconds=1.0)
        assert canvas.audio.render_sound().peak > 0.0

    def test_a_sequence_holding_components_is_resolved(self, canvas):
        @xnano.playable
        def blip(context: Context) -> xnano.Note:
            return xnano.note('A4', beats=0.5)

        handle = canvas.play([blip, 'C4'])
        canvas.step(delta_seconds=1.0)
        assert canvas.audio.render_sound().peak > 0.0
        handle.remove()

    def test_a_playable_hook_is_installed_on_the_canvas(self, canvas):
        @xnano.playable
        def blip(context: Context, name: str = 'a') -> xnano.Note:
            return xnano.note('A4', beats=0.5)

        heard = []
        hook = blip.hook(
            lambda context, component: heard.append(
                (component.placement, component.arguments['name'])
            ),
            on='key',
            keys='x',
        )
        handle = canvas.play(blip(name='b'))
        push(canvas, Event.key_press('x'))
        assert heard == [(None, 'b')]
        assert len(hook.handles) == 1
        handle.remove()
        assert hook.handles == ()

    def test_a_playable_that_fails_to_play_raises_to_the_caller(self, canvas):
        @xnano.playable
        def broken(context: Context) -> object:
            return 3.5j

        with pytest.raises(TypeError):
            canvas.play(broken)  # type: ignore[arg-type]

    def test_a_note_is_not_a_component(self, canvas):
        assert canvas.play(xnano.note('C4')) is not None


class TestNestedCanvases:
    def test_a_component_of_a_canvas_written_into_another_keeps_running(self):
        calls = []

        @xnano.renderable
        def ticker(context: Context) -> str:
            calls.append(context.time.elapsed)
            return str(len(calls))

        with xnano.new(width=20, height=4) as outer:
            inner = xnano.new(width=6, height=1)
            inner.write(ticker)
            outer.write(inner)
            outer.step(delta_seconds=1.0)
            outer.step(delta_seconds=1.0)
            assert len(calls) >= 3
            assert '3' in outer.render()

    def test_a_component_is_removed_with_its_nested_placement(self):
        @xnano.renderable
        def label(context: Context) -> str:
            return context.keyboard.key or 'x'

        with xnano.new(width=20, height=4) as canvas:
            outer = canvas.write('', width=10, height=3)
            inner = outer.write(label)
            inner.remove()
            assert inner._driver is None or inner._driver.is_closed


class TestEffectsInComponents:
    def test_a_renderable_can_set_an_effect_through_the_context(self):
        seen = []

        @xnano.renderable
        def fancy(context: Context) -> str:
            effect = context.fx.fade_to(foreground='red', duration_milliseconds=200)
            seen.append((effect, context.fx.active))
            return 'hello'

        with xnano.new(width=10, height=1) as canvas:
            placement = canvas.write(fancy)
            canvas.step(delta_seconds=0.1)
            assert seen and seen[0][1] == (seen[0][0],)
            assert 'hello' in canvas.render()
            placement.remove()

    def test_a_component_context_can_clear_effects_and_remove_itself(self):
        @xnano.renderable
        def once(context: Context) -> str:
            context.fx.clear()
            context.hook.remove()
            return 'once'

        with xnano.new(width=10, height=1) as canvas:
            canvas.write(once)
            canvas.step()
            assert canvas.render().startswith('once')


class TestDecoratorArguments:
    @pytest.mark.parametrize('decorator', ['renderable', 'playable'])
    @pytest.mark.parametrize('value', [5, None, 'text'])
    def test_something_that_is_not_a_function_is_explained(self, decorator, value):
        with pytest.raises(TypeError, match=rf'@xnano\.{decorator} decorates a function'):
            getattr(xnano, decorator)(value)

    def test_a_class_is_pointed_at_the_protocol_method(self):
        class Gauge:
            pass

        with pytest.raises(TypeError, match=r'__xnano_render__\(self, context\)'):
            xnano.renderable(Gauge)

    def test_a_play_method_without_a_context_says_what_it_returns(self):
        class Chime:
            def __xnano_play__(self):
                return 'C4'

        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(TypeError, match=r'return what it plays, such as a Note'):
                canvas.play(Chime())

    def test_the_example_of_the_refusal_fits_the_decorator(self):
        with pytest.raises(TypeError, match=r'def gauge\(context\)'):
            xnano.renderable(None)
        with pytest.raises(TypeError, match=r'def chime\(context\)'):
            xnano.playable(None)

    def test_the_context_check_inspects_a_method_once(self, monkeypatch):
        import inspect

        calls = []
        real = inspect.signature

        def counting(function, *arguments, **keywords):
            calls.append(function)
            return real(function, *arguments, **keywords)

        class Gauge:
            def __xnano_render__(self, context):
                return 'x'

        monkeypatch.setattr(inspect, 'signature', counting)
        from xnano._media import check_context_method

        for _ in range(5):
            check_context_method(Gauge(), '__xnano_render__')
        assert len(calls) == 1

    def test_a_render_method_without_a_context_is_explained(self):
        class Gauge:
            def __xnano_render__(self):
                return 'x'

        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(
                TypeError, match=r'Gauge\.__xnano_render__ must take the context'
            ):
                canvas.write(Gauge())
