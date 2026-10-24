"""
tests.test_canvas

A canvas is a virtual terminal: what ``new()`` creates, its time controls, the canvases written
into it, and how it ends.
"""

from __future__ import annotations

import dataclasses
import gc
import pathlib
import re
import threading
import weakref
from typing import cast

import pytest
from xnano_image import TerminalImage

import xnano
import xnano.terminal._screen
from xnano.canvas import Canvas
from xnano.errors import TerminalClosedError, TerminalError
from xnano.hooks import Frame
from xnano.terminal._settings import gates_for_screen, parse_open_settings
from xnano_core import Event, Point, TimeElapsed

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent


@dataclasses.dataclass
class Settings:
    volume: int = 40


class TestNew:
    def test_new_defaults(self):
        with xnano.new() as canvas:
            assert isinstance(canvas, Canvas)
            assert not isinstance(canvas, xnano.Terminal)
            assert (canvas.screen.width, canvas.screen.height) == (80, 24)
            assert canvas.clock.fps == 60
            assert canvas.clock.bpm == 120
            assert not canvas.clock.is_realtime
            assert canvas.deps is None
            assert canvas.is_running and not canvas.is_closed
            assert canvas.state.get('anything') is None

    def test_the_settings_are_kept(self):
        with xnano.new(
            width=12, height=3, fps=10, bpm=90, title='T', deps={'name': 'app'}
        ) as canvas:
            assert (
                canvas.screen.width,
                canvas.screen.height,
                canvas.clock.fps,
                canvas.clock.bpm,
            ) == (
                12,
                3,
                10,
                90,
            )
            assert canvas.screen.title == 'T'
            assert canvas.deps == {'name': 'app'}
        with xnano.new(width=8, height=1, state=Settings(volume=3)) as typed:
            assert typed.state.volume == 3

    def test_realtime_runs_on_the_wall_clock(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            assert canvas.clock.is_realtime
            assert not isinstance(canvas, xnano.Terminal)

    @pytest.mark.parametrize(
        ('keywords', 'error', 'text'),
        [
            ({'width': 0}, ValueError, 'width must be a whole number of cells'),
            ({'height': 2.5}, ValueError, 'height must be a whole number'),
            ({'fps': 0}, ValueError, 'fps must be a number above zero'),
            ({'bpm': 0}, ValueError, 'The tempo 0 is out of range'),
            ({'mosue': True}, TypeError, "Did you mean 'mouse'"),
            ({'mouse': 'yes'}, ValueError, "mouse must be True, False or 'motion'"),
            ({'scroll': 1}, ValueError, 'scroll must be True or False'),
            ({'offscreen': True}, TypeError, 'xnano.new'),
        ],
    )
    def test_bad_settings_are_explained(self, keywords, error, text):
        with pytest.raises(error, match=re.escape(text)):
            xnano.new(**keywords)

    def test_gates_are_stored_until_the_canvas_is_opened(self):
        with xnano.new(
            mouse='motion', scroll=True, keyboard=False, paste=False
        ) as canvas:
            assert canvas._gates == {
                'mouse': 'motion',
                'scroll': True,
                'keyboard': False,
                'paste': False,
            }
            screen = gates_for_screen(canvas, {**canvas._gates, 'scroll': False})
            assert screen['mouse'] == 'motion'
            assert screen['scroll'] is False, (
                'a gate given to open() replaces the stored one'
            )
            assert screen['keyboard'] is False and screen['paste'] is False
            assert screen['focus'] is True, 'a gate never given takes its default'

    def test_a_hook_turns_an_unset_gate_on_and_refuses_one_given_as_false(self):
        with xnano.new() as canvas:

            @canvas.hook(on="mouse.kind == 'press'")
            def click(context: xnano.hooks.Context) -> None:
                pass

            assert gates_for_screen(canvas, {})['mouse'] is True
            with pytest.raises(TerminalError, match='needs mouse=True'):
                gates_for_screen(canvas, {'mouse': False})

    def test_a_hook_on_a_canvas_that_runs_by_itself_turns_an_unset_gate_on(self):
        for _ in range(20):
            with xnano.new(realtime=True, width=8, height=1) as canvas:
                canvas.hook(lambda context: None, on="mouse.kind == 'press'")
                assert gates_for_screen(canvas, {})['mouse'] is True
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            canvas.hook(lambda context: None, on="mouse.kind == 'press'")
            with pytest.raises(TerminalError, match='needs mouse=True'):
                gates_for_screen(canvas, {'mouse': False})

    def test_the_gate_error_names_the_function_the_user_wrote(self):
        def on_press(context: xnano.hooks.Context) -> None:
            pass

        def on_drag(context: xnano.hooks.Context) -> None:
            pass

        def on_click(context: xnano.hooks.Context) -> None:
            pass

        with xnano.new() as canvas:
            canvas.screen.write('x').hook(on='mouse')(on_press)
            with pytest.raises(TerminalError, match='hook on_press needs mouse=True'):
                gates_for_screen(canvas, {'mouse': False})
        with xnano.new() as canvas:
            canvas.hook(on='drag')(on_drag)
            with pytest.raises(TerminalError, match='hook on_drag needs mouse=True'):
                gates_for_screen(canvas, {'mouse': False})
        with xnano.new() as canvas:
            canvas.hook(on_click, on="mouse.kind == 'press'")
            with pytest.raises(TerminalError, match='hook on_click needs mouse=True'):
                gates_for_screen(canvas, {'mouse': False})

    def test_gates_given_to_new_and_open_are_both_kept(self):
        with xnano.new(width=8, height=1, mouse=True) as canvas:
            settings = parse_open_settings(canvas, {'scroll': True})
            gates = {**canvas._gates, **cast('dict[str, object]', settings['gates'])}
            resolved = gates_for_screen(canvas, gates)
            assert resolved['mouse'] is True
            assert resolved['scroll'] is True

    def test_open_refuses_settings_that_belong_to_new(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(TypeError, match=r'open\(\) takes no realtime'):
                canvas.open(realtime=True)
            with pytest.raises(TypeError, match=r'open\(\) takes no realtime'):
                xnano.open(realtime=True)
        with xnano.new(width=8, height=1, deps={'name': 'app'}) as canvas:
            with pytest.raises(TypeError, match='deps was already given to xnano.new'):
                canvas.open(deps={'name': 'other'})
            assert not canvas.is_closed

    def test_padding_and_margin_draw_around_the_content_of_the_canvas(self):
        with xnano.new(width=8, height=5, border='plain', padding=1) as canvas:
            canvas.screen.write('hi')
            lines = canvas.screen.render().split('\n')
            assert lines[0] == '┌──────┐'
            assert lines[2] == '│ hi   │'
        with xnano.new(width=8, height=3, margin={'left': 2}) as canvas:
            canvas.screen.write('hi')
            assert canvas.screen.render().split('\n')[0] == '  hi'

    def test_appearance_with_content_names_the_function_that_was_called(self):
        with pytest.raises(TypeError, match=r'call open\(\) without content'):
            xnano.open('hello', border='rounded')
        with pytest.raises(TypeError, match=r'call new\(\) without content'):
            xnano.new('hello', border='rounded')

    def test_content_is_written_at_the_origin(self):
        with xnano.new('hello', width=8, height=2) as canvas:
            assert canvas.screen.render() == 'hello\n'
            placement = canvas._placements[0]
            assert (placement.x, placement.y) == (0, 0)

    def test_appearance_keywords_style_the_canvas_and_not_the_content(self):
        with pytest.raises(TypeError, match='not its content: border') as caught:
            xnano.new('hello', border='rounded')
        assert 'canvas.screen.write(content, border=...)' in str(caught.value)
        with xnano.new(width=6, height=3, border='rounded') as canvas:
            assert canvas.screen.render().split('\n')[0] == '╭────╮'

    def test_effects_apply_to_the_canvas_and_to_written_content(self):
        with xnano.new(
            width=6,
            height=1,
            effects=[{'kind': 'effect.fade_to', 'foreground': 'red'}],
        ) as canvas:
            assert len(canvas._effects) == 1
            label = canvas.screen.write(
                'hi', effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 50}]
            )
            assert len(canvas._effects) == 2
            canvas.clock.step(delta_seconds=1.0)
            label.remove()
            assert all(target is not label for _, target in canvas._effects)

    def test_an_effect_list_takes_dictionaries_of_visual_effects(self):
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(TypeError, match='effects= takes dictionaries'):
                canvas.screen.write('x', effects=[xnano.effect('effect.dissolve')])  # type: ignore[list-item]
            with pytest.raises(TypeError, match='is not a visual effect'):
                canvas.screen.write('x', effects=[{'kind': 'fill', 'cell': '.'}])

    def test_render_is_the_current_frame_as_text_or_ansi(self):
        with xnano.new(width=6, height=2) as canvas:
            canvas.screen.write('hi', y=1, foreground='red')
            text = canvas.screen.render()
            assert text == '\nhi'
            assert str(canvas) == text
            assert canvas.screen.render(format='ansi') == canvas.screen.output.ansi
            assert '\x1b[' in canvas.screen.render(format='ansi')
            with pytest.raises(ValueError, match="'text' or 'ansi'"):
                canvas.screen.render(format='html')  # type: ignore[arg-type]

    def test_a_canvas_sits_at_the_origin_and_cannot_be_moved(self):
        with xnano.new(width=6, height=2) as canvas:
            assert (canvas.screen.x, canvas.screen.y) == (0, 0)
            assert canvas.screen.local(Point(2, 1)) == Point(2, 1)
            with pytest.raises(TerminalError, match='sits at the origin'):
                canvas.screen.up()
            with pytest.raises(TerminalError, match=r'placement\.move'):
                canvas.screen.move(x=1)
            assert not hasattr(canvas, 'is_stopped')

    def test_the_root_and_parent_are_formula_scopes(self):
        with xnano.new(width=6, height=2) as canvas:
            assert canvas.screen.root.time is TimeElapsed
            assert canvas.inspect(canvas.screen.root.width) == 6

    def test_closing_twice_is_harmless(self):
        canvas = xnano.new(width=4, height=1)
        canvas.close()
        canvas.close()
        assert canvas.is_closed
        with pytest.raises(TerminalClosedError, match='has been closed'):
            canvas.screen.write('late')


class TestEnding:
    def test_quit_leaves_a_canvas_from_new_open(self):
        with xnano.new(width=12, height=1) as canvas:
            canvas.quit()
            assert not canvas.is_running
            assert not canvas.is_closed
            canvas.screen.write('still here')
            assert 'still here' in canvas.screen.render()
            assert list(canvas.iter(frames=3)) == [], 'the request to end is still set'

    def test_quit_ends_and_closes_a_canvas_that_runs_by_itself(self):
        canvas = xnano.new(realtime=True, width=8, height=1)
        try:
            canvas.quit()
            deadline = threading.Event()
            for _ in range(200):
                if canvas.is_closed:
                    break
                deadline.wait(0.01)
            assert canvas.is_closed
            with pytest.raises(TerminalClosedError):
                canvas.screen.write('late')
        finally:
            canvas.close()

    def test_run_needs_a_canvas_that_moves_by_itself(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(TerminalError, match='wait forever') as caught:
                canvas.run()
            assert 'realtime=True' in str(caught.value)


class TestActive:
    def test_the_innermost_running_canvas_is_active(self):
        assert xnano.active(is_required=False) is None
        outer = xnano.new(width=4, height=1)
        assert xnano.active() is outer
        with xnano.new(width=4, height=1) as inner:
            assert xnano.active() is inner
            inner.quit()
            assert xnano.active() is outer, 'a canvas that quit gives way'
        assert xnano.active() is outer
        outer.close()
        assert xnano.active(is_required=False) is None
        with pytest.raises(TerminalClosedError, match='No canvas is running'):
            xnano.active()

    def test_the_old_keyword_is_refused(self):
        with pytest.raises(TypeError):
            xnano.active(required=False)  # type: ignore[call-overload]


class TestTimeControls:
    def test_iter_counts_frames_and_steps_the_manual_clock(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            frames = list(canvas.iter(frames=3))
            assert [round(frame.elapsed_seconds, 3) for frame in frames] == [
                0.0,
                0.1,
                0.2,
            ]
            assert all(isinstance(frame, Frame) for frame in frames)
            assert round(canvas.clock.elapsed, 3) == 0.3

    def test_iter_ends_on_seconds_of_canvas_time(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            assert len(list(canvas.iter(seconds=0.5))) == 5

    def test_frames_and_seconds_end_on_the_first(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            assert len(list(canvas.iter(frames=2, seconds=10))) == 2
            assert len(list(canvas.iter(frames=50, seconds=0.3))) == 3

    def test_a_frame_carries_the_events_since_the_previous_one(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            seen = []
            for frame in canvas.iter(frames=4):
                seen.append([event.kind for event in frame.events])
                if frame.index == 1:
                    canvas.push(Event.key_press('a'))
                    canvas.push(Event.custom('ping'))
            assert seen == [[], [], ['key', 'custom'], []]

    def test_without_frames_or_seconds_it_runs_until_a_quit_key(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            yielded = 0
            for frame in canvas.iter(quit_on=('q', 'escape')):
                yielded += 1
                if frame.index == 6:
                    canvas.push(Event.key_press('escape'))
                assert yielded < 50
            assert (yielded, canvas.is_running) == (7, False)

    def test_the_quit_keys_last_as_long_as_the_iteration(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            before = len(canvas._hook_handles())
            for _ in canvas.iter(frames=2, quit_on='q'):
                assert canvas._quit_keys == ('q',)
            assert canvas._quit_keys == ()
            assert len(canvas._hook_handles()) == before
            for _ in canvas.iter(frames=2, quit_on=None):
                canvas.push(Event.key_press('ctrl+c'))
            assert canvas.is_running

    def test_an_unbounded_iter_ends_on_break_or_quit(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            for frame in canvas.iter():
                if frame.index >= 4:
                    break
            assert canvas.clock.frame == 4
            seen = 0
            for _ in canvas.iter():
                seen += 1
                if seen == 3:
                    canvas.quit()
            assert seen == 3

    def test_next_yields_the_current_frame_and_two_iterators_share_the_clock(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            first = canvas.iter()
            assert next(first).elapsed_seconds == 0.0
            second = canvas.iter()
            next(second)
            next(second)
            assert round(canvas.clock.elapsed, 3) == 0.1

    def test_a_step_moves_one_frame_and_returns_it(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            frame = canvas.clock.step()
            assert isinstance(frame, Frame)
            assert frame.elapsed_seconds == pytest.approx(0.1)
            assert frame.delta_seconds == pytest.approx(0.1)
            assert frame.index == canvas.clock.frame

    def test_a_canvas_that_runs_by_itself_is_stepped_only_while_stopped(self):
        canvas = xnano.new(realtime=True, width=4, height=1, fps=10)
        try:
            with pytest.raises(TerminalError, match='cannot be stepped by hand'):
                canvas.clock.step()
            canvas.clock.stop()
            before = canvas.clock.elapsed
            frame = canvas.clock.step()
            assert isinstance(frame, Frame)
            assert canvas.clock.elapsed == pytest.approx(before + 0.1, abs=1e-6)
            assert canvas.clock.is_stopped
        finally:
            canvas.close()

    def test_sixty_steps_at_sixty_frames_per_second_are_one_second(self):
        with xnano.new(width=4, height=1, fps=60) as canvas:
            for _ in range(60):
                canvas.clock.step()
            assert canvas.clock.elapsed == pytest.approx(1.0, abs=1e-9)
        with xnano.new(width=4, height=1, fps=60) as canvas:
            list(canvas.iter(frames=60))
            assert canvas.clock.elapsed == pytest.approx(1.0, abs=1e-9)
        with xnano.new(width=4, height=1, fps=60) as canvas:
            for _ in range(30):
                canvas.clock.step()
            list(canvas.iter(frames=30))
            assert canvas.clock.elapsed == pytest.approx(1.0, abs=1e-9)

    def test_a_step_takes_a_positive_delta_and_deliver_events_does_not_move_time(self):
        with xnano.new(width=4, height=1) as canvas:
            canvas.clock.step(delta_seconds=0.25)
            assert canvas.clock.elapsed == pytest.approx(0.25)
            with pytest.raises(ValueError, match='deliver_events'):
                canvas.clock.step(delta_seconds=0)
            with pytest.raises(ValueError, match='above zero'):
                canvas.clock.step(delta_seconds=-1)
            heard: list[str] = []
            canvas.hook(lambda context: heard.append(context.event.kind))
            canvas.push(Event.custom('ping'))
            canvas.deliver_events()
            assert heard == ['custom']
            assert canvas.clock.elapsed == pytest.approx(0.25)

    def test_stop_freezes_iter_while_step_moves_one_frame(self):
        with xnano.new(width=8, height=1, fps=10) as canvas:
            label = canvas.screen.write('-')
            canvas.clock.stop()
            assert canvas.clock.is_stopped
            texts = []
            for frame in canvas.iter(frames=3):
                label.text = str(frame.index)
                texts.append(frame.elapsed_seconds)
            assert texts == [0.0, 0.0, 0.0], 'a stopped canvas draws without moving time'
            assert '2' in canvas.screen.render()
            canvas.clock.step()
            assert canvas.clock.elapsed == pytest.approx(0.1)
            assert canvas.clock.is_stopped, 'a step leaves the canvas stopped'
            canvas.clock.resume()
            assert not canvas.clock.is_stopped

    def test_time_is_continuous_across_stop_and_resume(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            list(canvas.iter(frames=2))
            canvas.clock.stop()
            list(canvas.iter(frames=5))
            canvas.clock.resume()
            list(canvas.iter(frames=2))
            assert canvas.clock.elapsed == pytest.approx(0.4)

    def test_stopped_time_holds_formulas_and_timers_while_input_still_arrives(self):
        with xnano.new(width=20, height=1, fps=10) as canvas:
            ball = canvas.screen.write('o')
            ball.x = TimeElapsed * 10
            ticks: list[float] = []
            canvas.hook(on='tick', every=0.1)(
                lambda context: ticks.append(context.clock.elapsed)
            )
            pressed: list[str] = []
            canvas.hook(on='key')(lambda context: pressed.append(context.keyboard.key))
            canvas.clock.step(delta_seconds=0.5)
            before = (ball.x, len(ticks))
            canvas.clock.stop()
            for _ in canvas.iter(frames=3):
                pass
            canvas.push(Event.key_press('a'))
            canvas.deliver_events()
            assert (ball.x, len(ticks)) == before
            assert pressed == ['a']

    def test_seconds_on_a_stopped_canvas_is_refused(self):
        with xnano.new(width=4, height=1) as canvas:
            canvas.clock.stop()
            with pytest.raises(TerminalError, match='never reaches seconds=1'):
                canvas.iter(seconds=1)
            assert len(list(canvas.iter(frames=2, seconds=1))) == 2

    def test_iter_seconds_raises_when_stopped_inside_the_loop(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            with pytest.raises(TerminalError, match=r'canvas\.clock\.resume'):
                for frame in canvas.iter(seconds=1):
                    if frame.index == 1:
                        canvas.clock.stop()
            canvas.clock.resume()
            seen = 0
            for _ in canvas.iter(frames=3, seconds=10):
                seen += 1
                canvas.clock.stop()
            assert seen == 3

    def test_the_canvas_verbs_are_the_time_verbs(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            canvas.clock.stop()
            assert canvas.clock.is_stopped
            canvas.clock.resume()
            assert not canvas.clock.is_stopped
            canvas.clock.stop()
            frame = canvas.clock.step()
            assert frame.elapsed_seconds == pytest.approx(0.1)
            assert repr(canvas.clock) == 'Clock(elapsed=0.100, is_stopped=True)'


class TestChildCanvases:
    def test_a_canvas_written_into_another_draws_inside_it_on_its_time(self):
        with xnano.new(width=20, height=3, fps=10) as outer:
            inner = xnano.new(width=6, height=1)
            inner.screen.write('inside')
            placement = outer.screen.write(inner, x=2, y=1)
            assert (placement.x, placement.y, placement.width) == (2, 1, 6)
            assert outer.screen.render().split('\n')[1] == '  inside'
            outer.clock.step(delta_seconds=0.5)
            assert inner.clock is outer.clock
            assert inner.clock.elapsed == pytest.approx(0.5)
            assert xnano.active() is outer
            inner.screen.write('!', x=5, y=0)
            assert outer.screen.render().split('\n')[1] == '  insid!'
            inner.close()
            assert inner.is_closed
            assert outer.is_running
            assert outer.screen.render().split('\n')[1] == ''

    def test_changing_the_look_of_a_written_canvas_redraws_it(self):
        with xnano.new(width=14, height=6) as outer:
            inner = xnano.new(width=8, height=3, border='double')
            outer.screen.write(inner, x=1, y=1)
            outer.clock.step()
            assert outer.screen.render().split('\n')[1] == ' ╔══════╗'
            inner.screen.border = 'plain'
            outer.clock.step()
            assert outer.screen.render().split('\n')[1] == ' ┌──────┐'
            inner.screen.border = False
            outer.clock.step()
            assert outer.screen.render().strip() == ''

    def test_a_look_set_before_a_canvas_is_written_is_drawn_and_can_change(self):
        with xnano.new(width=12, height=6) as outer:
            inner = xnano.new(width=6, height=3)
            inner.screen.border = 'rounded'
            outer.screen.write(inner)
            outer.clock.step()
            assert (
                outer.screen.render().split('\n')[0]
                == '\u256d\u2500\u2500\u2500\u2500\u256e'
            )
            inner.screen.border = 'double'
            outer.clock.step()
            assert (
                outer.screen.render().split('\n')[0]
                == '\u2554\u2550\u2550\u2550\u2550\u2557'
            )

    def test_a_look_set_on_a_placement_before_its_canvas_is_written_is_drawn(self):
        with xnano.new(width=12, height=6) as outer:
            inner = xnano.new(width=10, height=4)
            placement = inner.screen.write('hi')
            placement.border = 'plain'
            outer.screen.write(inner)
            outer.clock.step()
            assert outer.screen.render().split('\n')[0] == '\u250c\u2500\u2500\u2510'
            placement.border = 'double'
            outer.clock.step()
            assert outer.screen.render().split('\n')[0] == '\u2554\u2550\u2550\u2557'

    def test_removing_a_look_larger_than_the_canvas_keeps_its_size(self):
        with xnano.new(width=12, height=6) as outer:
            inner = xnano.new(width=8, height=3)
            inner.screen.write('hi')
            placement = outer.screen.write(inner)
            inner.screen.margin = 2
            outer.clock.step()
            inner.screen.margin = 0
            outer.clock.step()
            assert (placement.width, placement.height) == (8, 3)
            assert (inner.screen.size.width, inner.screen.size.height) == (8, 3)

    def test_a_child_renders_its_own_cells_and_not_the_outer_frame(self):
        with xnano.new(width=20, height=3) as outer:
            inner = xnano.new(width=6, height=1)
            inner.screen.write('hi')
            outer.screen.write(inner, x=2, y=1)
            assert inner.screen.render() == 'hi'
            assert outer.screen.render().split('\n')[1] == '  hi'

    def test_the_formulas_and_hooks_of_a_child_move_to_the_outer_canvas(self):
        with xnano.new(width=20, height=2, fps=10) as outer:
            inner = xnano.new(width=10, height=1)
            ball = inner.screen.write('o')
            ball.x = TimeElapsed * 10
            ticks: list[float] = []
            inner.hook(on='tick', every=0.1)(
                lambda context: ticks.append(context.clock.elapsed)
            )
            outer.screen.write(inner)
            outer.clock.step(delta_seconds=0.5)
            assert ball.x == 5
            assert ticks

    @pytest.mark.parametrize(
        ('keywords', 'text'),
        [
            ({'state': Settings()}, 'Give state to the outermost canvas'),
            ({'deps': None}, 'Give deps to the outermost canvas'),
            ({'deps': {'name': 'app'}}, 'Give deps to the outermost canvas'),
        ],
    )
    def test_a_child_with_state_or_deps_is_refused(self, keywords, text):
        with xnano.new(width=8, height=2) as outer:
            with xnano.new(width=4, height=1, **keywords) as inner:
                with pytest.raises(TerminalError, match=text):
                    outer.screen.write(inner)

    def test_a_closed_canvas_itself_or_a_child_twice_is_refused(self):
        with xnano.new(width=8, height=2) as outer:
            closed = xnano.new(width=2, height=1)
            closed.close()
            with pytest.raises(TerminalError, match='has been closed'):
                outer.screen.write(closed)
            with pytest.raises(TerminalError, match='never into itself'):
                outer.screen.write(outer)
            inner = xnano.new(width=2, height=1)
            outer.screen.write(inner)
            with pytest.raises(TerminalError, match='once'):
                outer.screen.write(inner)
            with pytest.raises(TerminalError, match='part of it'):
                inner.screen.write(outer)
            with pytest.raises(TerminalError, match='Open the outer canvas'):
                inner.open()


class TestCanvasesCreatedInsideAnother:
    def test_its_size_and_clock_are_measured_in_the_canvas_around_it(self):
        with xnano.new(width=20, height=10, fps=10, bpm=90):
            with xnano.new(width='50%', height='30%') as inner:
                assert (inner.screen.width, inner.screen.height) == (10, 3)
                assert (inner.clock.fps, inner.clock.bpm) == (10, 90)
            with xnano.new() as filling:
                assert (filling.screen.width, filling.screen.height) == (20, 10)
            with xnano.new(width=4, height=2) as own:
                assert (own.screen.width, own.screen.height) == (4, 2)
            with xnano.new(width='50%', state=Settings()) as on_its_own:
                assert (
                    on_its_own.screen.width,
                    on_its_own.clock.fps,
                    on_its_own.clock.bpm,
                ) == (10, 10, 90)

    def test_it_is_not_drawn_until_it_is_written(self):
        with xnano.new(width=12, height=4) as outer:
            with xnano.new(height='50%') as inner:
                inner.screen.write('inside')
                assert xnano.active() is outer
            assert inner.clock is outer.clock
            assert outer.screen.render().strip() == ''
            outer.screen.write(inner, y=2)
            assert outer.screen.render().splitlines()[2] == 'inside'
            assert inner.screen.down() is inner.screen
            assert inner.screen.y == 3

    def test_it_outlives_its_own_block_and_closes_with_the_canvas_around_it(self):
        with xnano.new(width=12, height=4) as outer:
            with xnano.new(height='50%') as inner:
                pass
            assert not inner.is_closed
            heard: list[str] = []
            inner.hook(on='key')(lambda context: heard.append(context.keyboard.key))
            outer.screen.write(inner)
            outer.push(Event.key_press('a'))
            outer.deliver_events()
            assert heard == ['a']
            with xnano.new() as never_written:
                pass
        assert inner.is_closed
        assert never_written.is_closed

    def test_a_canvas_created_outside_any_block_closes_with_its_own(self):
        with xnano.new(width=4, height=1):
            pass
        with xnano.new(width=4, height=1) as later:
            pass
        assert later.is_closed

    def test_writing_on_the_outer_canvas_inside_its_block_lands_in_its_area(self):
        with xnano.new(width=12, height=4) as outer:
            with xnano.new(width=6, height='50%') as inner:
                outer.screen.write('abcdefgh', x='center', y='center')
                inner.screen.write('i')
            outer.screen.write('after', y=3)
            assert outer.screen.render().splitlines() == ['bcdefg', '', '', 'after']

    def test_the_area_follows_where_the_canvas_is_written(self):
        with xnano.new(width=12, height=4) as outer:
            inner = xnano.new(width=4, height=2)
            outer.screen.write(inner, x=6, y=2)
            with inner:
                outer.screen.write('ab', x='right', y='bottom')
            assert outer.screen.render().splitlines()[3] == '        ab'

    def test_a_canvas_that_is_not_written_refuses_to_move(self):
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(TerminalError, match='not written into another canvas'):
                canvas.screen.up()


class TestCanvasNew:
    def test_it_creates_a_canvas_drawn_here_at_once(self):
        with xnano.new(width=12, height=4, fps=10) as outer:
            panel = outer.screen.new('hi', height='50%')
            assert (panel.screen.width, panel.screen.height, panel.clock.fps) == (
                12,
                2,
                10,
            )
            assert panel._canvas is outer
            assert outer.screen.render().splitlines()[0] == 'hi'
            panel.screen.right(2)
            assert outer.screen.render().splitlines()[0] == '  hi'
        assert panel.is_closed

    def test_a_canvas_it_creates_takes_a_look(self):
        with xnano.new(width=6, height=3) as outer:
            outer.screen.new(border='plain')
            assert outer.screen.render().splitlines()[0] == '┌────┐'


class TestChangingTheFrameRate:
    def test_a_manual_canvas_steps_by_the_new_rate(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            assert round(canvas.clock.step().delta_seconds, 3) == 0.1
            canvas.clock.fps = 40
            assert canvas.clock.fps == 40
            assert round(canvas.clock.step().delta_seconds, 3) == 0.025
            frames = list(canvas.iter(frames=2))
            assert round(frames[-1].delta_seconds, 3) == 0.025

    def test_a_hook_can_change_the_rate(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            canvas.hook(on='key')(lambda context: setattr(context.clock, 'fps', 50))
            canvas.push(Event.key_press('a'))
            canvas.deliver_events()
            assert canvas.clock.fps == 50
            assert canvas._runtime.frame_interval_milliseconds == 20

    def test_a_written_canvas_changes_the_rate_of_the_one_it_is_written_into(self):
        with xnano.new(width=8, height=2, fps=10) as outer:
            inner = outer.screen.new(width=2, height=1)
            inner.clock.fps = 25
            assert outer.clock.fps == 25

    @pytest.mark.parametrize('rate', [0, -5, float('nan')])
    def test_a_rate_that_is_not_above_zero_is_refused(self, rate):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            with pytest.raises(ValueError, match='fps must be a number above zero'):
                canvas.clock.fps = rate
            assert canvas.clock.fps == 10

    def test_a_rate_that_is_not_a_number_is_refused(self):
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(TypeError, match='fps must be a number'):
                canvas.clock.fps = 'fast'  # type: ignore[assignment]


class TestRemovedNames:
    def test_the_removed_names_are_gone(self):
        for name in ('make', 'fx', 'loop'):
            assert not hasattr(xnano, name), name
        with xnano.new(width=4, height=1) as canvas:
            for name in (
                'loop',
                'is_live',
                'is_autonomous',
                'backend',
                'inject',
                'tempo',
            ):
                assert not hasattr(canvas, name), name

    def test_old_spellings_of_time_and_ending_are_not_used(self):
        patterns = re.compile(
            r'time\.pause\(|time\.is_paused|terminal\.stop\(|iter\(duration_seconds='
            r'|offscreen=True'
        )
        allowed = {
            pathlib.Path('tests/test_canvas.py'),
            pathlib.Path('tests/test_open.py'),
        }
        roots = [
            REPOSITORY / 'xnano',
            REPOSITORY / 'tests',
            REPOSITORY / 'docs' / 'learn',
        ]
        paths = [REPOSITORY / 'README.md']
        for root in roots:
            paths.extend(root.rglob('*.py'))
            paths.extend(root.rglob('*.md'))
        offenders = []
        for path in paths:
            relative = path.relative_to(REPOSITORY)
            if relative in allowed:
                continue
            for number, line in enumerate(
                path.read_text(encoding='utf-8').splitlines(), 1
            ):
                if patterns.search(line):
                    offenders.append(f'{relative}:{number}: {line.strip()}')
        assert offenders == []


class TestFrameDemand:
    """Python runs before a frame only while something needs it."""

    @pytest.fixture
    def frame_calls(self, monkeypatch):
        calls: list[int] = []
        original = Canvas._on_loop_frame

        def counting(self, core_context):
            calls.append(1)
            return original(self, core_context)

        monkeypatch.setattr(Canvas, '_on_loop_frame', counting)
        return calls

    def test_a_static_canvas_makes_no_frame_call(self, frame_calls):
        with xnano.new(width=20, height=2) as canvas:
            canvas.screen.write('still', x=2)
            canvas.screen.write('more', y=1, border=None)
            for _ in range(5):
                canvas.clock.step()
            list(canvas.iter(frames=5))
            assert canvas._frame_demand == 0
            assert frame_calls == []
            assert canvas.screen.render().startswith('  still')

    def test_a_fixed_image_makes_no_frame_call(self, frame_calls):
        image = xnano.Image(
            TerminalImage.from_rgba(2, 2, bytes([255, 0, 0, 255]) * 4), width=4
        )
        with xnano.new(width=20, height=4) as canvas:
            placement = canvas.screen.write(image)
            assert canvas._frame_demand == 0
            for _ in range(5):
                canvas.clock.step()
            assert frame_calls == []
            placement.remove()
            assert canvas._frame_demand == 0

    def test_an_image_that_follows_the_canvas_size_holds_frames_until_it_is_gone(
        self, frame_calls
    ):
        image = xnano.Image(TerminalImage.from_rgba(2, 2, bytes([255, 0, 0, 255]) * 4))
        with xnano.new(width=20, height=4) as canvas:
            placement = canvas.screen.write(image)
            assert canvas._frame_demand == 1
            canvas.clock.step()
            assert frame_calls
            placement.remove()
            assert canvas._frame_demand == 0

    def test_a_formula_holds_frames_until_it_is_gone(self, frame_calls):
        with xnano.new(width=20, height=1, fps=10) as canvas:
            ball = canvas.screen.write('o')
            ball.x = TimeElapsed * 10
            assert canvas._frame_demand == 1
            canvas.clock.step()
            canvas.clock.step()
            assert frame_calls
            assert ball.x == 2
            ball.remove()
            assert canvas._frame_demand == 0
            assert canvas._frame_registration is None
            frame_calls.clear()
            canvas.clock.step()
            assert frame_calls == []

    def test_a_frame_hook_holds_frames_until_its_placement_is_removed(self, frame_calls):
        with xnano.new(width=20, height=1) as canvas:
            label = canvas.screen.write('-')
            seen: list[int] = []

            @label.hook(on='frame')
            def count(context: xnano.hooks.Context) -> None:
                seen.append(context.clock.frame)

            canvas.clock.step()
            canvas.clock.step()
            assert len(seen) >= 2
            label.remove()
            canvas.clock.step()
            assert canvas._frame_demand == 0

    def test_leaving_the_runtime_releases_the_frames_of_finished_effects(
        self, monkeypatch
    ):
        monkeypatch.setattr(Canvas, '_follow_effects', lambda self, runtime: False)
        with xnano.new(width=8, height=1) as canvas:
            canvas.screen.write(
                'fade',
                effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 100}],
            )
            assert canvas._frame_demand == 1
            for _ in range(5):
                canvas.clock.step(delta_seconds=0.1)
            assert canvas._effects, 'the canvas has not noticed the effect ended'
            canvas._host.call(canvas._unbind_runtime)
            assert canvas._effects == []
            assert canvas._frame_demand == 0

    def test_timers_need_no_frame_calls(self, frame_calls):
        with xnano.new(width=8, height=1) as canvas:
            ticks: list[float] = []
            canvas.hook(on='beat', every=1)(
                lambda context: ticks.append(context.clock.elapsed)
            )
            for _ in range(20):
                canvas.clock.step(delta_seconds=0.1)
            assert len(ticks) >= 3
            assert frame_calls == []

    def test_a_finished_effect_releases_its_frames(self, frame_calls):
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.screen.write(
                'fade',
                effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 100}],
            )
            assert canvas._frame_demand == 1
            for _ in range(20):
                canvas.clock.step(delta_seconds=0.05)
            assert canvas._effects == []
            assert canvas._frame_demand == 0
            label.remove()

    def test_the_ledger_stays_bounded(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(on='beat', every=1)(lambda context: None)
            before = len(canvas._ledger)
            for _ in range(100):
                canvas.clock.step(delta_seconds=0.5)
            assert len(canvas._ledger) == before
            for number in range(50):
                label = canvas.screen.write(
                    str(number),
                    effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 20}],
                )
                canvas.clock.step(delta_seconds=0.05)
                canvas.clock.step(delta_seconds=0.05)
                label.remove()
            assert len(canvas._effects) <= 1


@pytest.mark.skipif(
    __import__('sys').platform == 'win32',
    reason='a Windows runner has a console to draw on',
)
class TestOpeningWithoutATerminal:
    """The test run has no terminal to draw on, so opening fails and changes nothing."""

    def test_opening_without_a_terminal_leaves_the_canvas_usable(self):
        with xnano.new(width=12, height=2, fps=10) as canvas:
            label = canvas.screen.write('kept')
            heard: list[str] = []
            canvas.hook(on='key')(lambda context: heard.append(context.keyboard.key))
            canvas.hook(on='tick', every=0.1)(lambda context: heard.append('tick'))
            canvas.clock.step(delta_seconds=0.5)
            for _ in range(2):
                with pytest.raises(RuntimeError, match='could not be opened'):
                    canvas.open(height=2)
                assert xnano.terminal._screen.is_screen_claimed is False
            assert not isinstance(canvas, xnano.Terminal)
            assert not canvas.clock.is_realtime
            assert canvas.clock.elapsed == pytest.approx(0.5)
            label.text = 'still kept'
            canvas.push(Event.key_press('z'))
            canvas.clock.step(delta_seconds=0.5)
            assert 'z' in heard and 'tick' in heard
            assert canvas.screen.render().startswith('still kept')

    def test_opening_from_another_thread_teaches_where_to_open(self):
        with xnano.new(width=12, height=2) as canvas:
            label = canvas.screen.write('kept')
            failures: list[BaseException] = []

            def attempt() -> None:
                try:
                    canvas.open(height=2)
                except BaseException as error:
                    failures.append(error)

            thread = threading.Thread(target=attempt)
            thread.start()
            thread.join()
            assert len(failures) == 1
            assert isinstance(failures[0], TerminalError)
            assert 'thread that called xnano.new()' in str(failures[0])
            assert xnano.terminal._screen.is_screen_claimed is False
            canvas.clock.step()
            assert canvas.screen.render().startswith(label.text)

    def test_xnano_open_without_a_terminal_closes_the_canvas_it_made(self):
        with pytest.raises(RuntimeError, match='could not be opened'):
            xnano.open('content', height=2)
        assert xnano.terminal._screen.is_screen_claimed is False
        assert xnano.active(is_required=False) is None


def test_the_timers_of_what_a_child_holds_move_to_the_outer_canvas():
    with xnano.new(width=20, height=2) as outer:
        inner = xnano.new(width=10, height=1)
        label = inner.screen.write('-')
        ticks: list[float] = []
        label.hook(on='tick', every=0.1)(
            lambda context: ticks.append(context.clock.elapsed)
        )
        inner.clock.step(delta_seconds=0.05)
        outer.screen.write(inner)
        outer.clock.step(delta_seconds=0.5)
        assert ticks


def test_the_hooks_of_a_child_canvas_hear_the_outer_canvas_and_stop_when_it_closes():
    with xnano.new(width=20, height=2) as outer:
        inner = xnano.new(width=10, height=1)
        heard: list[str] = []
        inner.hook(on='key')(lambda context: heard.append(context.keyboard.key))
        outer.screen.write(inner)
        outer.push(Event.key_press('a'))
        outer.deliver_events()
        assert heard == ['a']
        inner.close()
        outer.push(Event.key_press('b'))
        outer.deliver_events()
        assert heard == ['a']
        assert inner not in outer._children


class TestClosingAWrittenCanvas:
    def test_closing_a_canvas_closes_the_canvases_written_into_it(self):
        outer = xnano.new(width=10, height=4)
        middle = xnano.new(width=6, height=3)
        innermost = xnano.new(width=3, height=1)
        innermost.screen.write('b')
        middle.screen.write(innermost)
        outer.screen.write(middle)
        hits: list[int] = []
        innermost.hook(lambda context: hits.append(1), on='tick')
        outer.clock.step()
        middle.close()
        assert innermost.is_closed
        outer.clock.step()
        assert hits == [1]
        assert outer._children == []
        with pytest.raises(TerminalClosedError):
            innermost.screen.write('zz')
        outer.close()

    def test_a_closed_written_canvas_does_not_control_the_outer_canvas(self):
        outer = xnano.new(width=10, height=3)
        inner = xnano.new(width=4, height=1)
        outer.screen.write(inner)
        inner.close()
        frame = outer.clock.frame
        for call in (
            lambda: inner.clock.step(),
            inner.deliver_events,
            lambda: inner.clock.stop(),
            lambda: inner.clock.resume(),
            inner.quit,
        ):
            with pytest.raises(TerminalClosedError):
                call()
        assert outer.clock.frame == frame
        assert not outer.clock.is_stopped
        assert outer.is_running
        outer.close()

    def test_a_closed_written_canvas_refuses_every_other_call_too(self):
        outer = xnano.new(width=10, height=3)
        inner = xnano.new(width=4, height=1)
        outer.screen.write(inner)
        inner.close()
        for call in (
            lambda: inner.hook(lambda context: None, on='tick'),
            lambda: inner.push(Event.custom('late')),
            lambda: inner.speaker.play('C4'),
            lambda: inner.speaker,
            lambda: inner.keyboard,
            lambda: inner.mouse,
            lambda: inner.clock,
            lambda: inner.screen,
            lambda: inner.state,
            lambda: inner.screen.render(),
            lambda: inner.screen.region,
            lambda: inner.screen.cursor,
        ):
            with pytest.raises(TerminalClosedError):
                call()
        outer.close()

    def test_canvases_dropped_without_closing_are_collected(self):
        references = []

        def create_and_drop() -> None:
            canvas = xnano.new(width=8, height=2)
            canvas.screen.write('hello')
            canvas.screen.render()
            references.append(weakref.ref(canvas))

        for _ in range(50):
            create_and_drop()
        gc.collect()
        assert [reference for reference in references if reference() is not None] == []
        assert xnano.active(is_required=False) is None

    def test_a_canvas_dropped_without_closing_leaves_the_one_before_it(self):
        outer = xnano.new(width=4, height=1)
        inner = xnano.new(width=4, height=1)
        reference = weakref.ref(inner)
        del inner
        gc.collect()
        assert reference() is None
        assert xnano.active() is outer
        outer.close()

    def test_a_closed_written_canvas_cannot_iterate_or_read_the_time(self):
        outer = xnano.new(width=10, height=3)
        inner = xnano.new(width=4, height=1)
        outer.screen.write(inner)
        inner.close()
        frame = outer.clock.frame
        with pytest.raises(TerminalClosedError):
            list(inner.iter(frames=2))
        with pytest.raises(TerminalClosedError):
            _ = inner.clock
        assert outer.clock.frame == frame
        outer.close()

    def test_a_canvas_written_two_levels_deep_belongs_to_the_root(self):
        root = xnano.new(width=10, height=4)
        middle = xnano.new(width=6, height=3)
        innermost = xnano.new(width=3, height=1)
        innermost.screen.write('b')
        middle.screen.write(innermost)
        root.screen.write(middle)
        assert innermost._canvas is root
        assert innermost._root_canvas is root
        innermost.close()
        assert innermost not in root._children
        assert middle in root._children
        root.close()

    def test_quitting_a_canvas_written_two_levels_deep_ends_a_realtime_root(self):
        with xnano.new(width=10, height=4, realtime=True) as root:
            middle = xnano.new(width=6, height=3)
            innermost = xnano.new(width=3, height=1)
            middle.screen.write(innermost)
            root.screen.write(middle)
            innermost.quit()
            assert not root.is_running

    def test_pushing_something_that_is_not_an_event_leaves_a_realtime_canvas_running(
        self,
    ):
        with xnano.new(width=10, height=3, realtime=True) as canvas:
            with pytest.raises(TypeError, match=r'push\(\) takes an Event'):
                canvas.push(5)  # type: ignore[arg-type]
            canvas.screen.write('x')
            assert canvas.is_running


class TestRefusedSettings:
    def test_a_bad_border_kind_is_explained_before_anything_is_created(self):
        with pytest.raises(ValueError, match='"nonsense" is not a border kind|nonsense'):
            xnano.new(border='nonsense')  # type: ignore[arg-type]
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(ValueError, match='is not a border kind'):
                canvas.open(border='nonsense')  # type: ignore[arg-type]
            assert not isinstance(canvas, xnano.Terminal)
            assert xnano.terminal._screen.is_screen_claimed is False
            canvas.clock.step()

    @pytest.mark.parametrize(
        'settings',
        [
            {'margin': 'x'},
            {'padding': 'x'},
            {'foreground': 'nocolor'},
            {'background': 'nocolor'},
            {'bold': 'x'},
            {'border_style': 'nonsense'},
        ],
    )
    def test_a_bad_appearance_value_is_refused_by_open_before_the_screen_is_claimed(
        self, settings
    ):
        with xnano.new(width=8, height=1) as canvas:
            canvas.screen.write('hi')
            with pytest.raises((TypeError, ValueError)):
                canvas.open(**settings)  # type: ignore[arg-type]
            assert type(canvas) is xnano.Canvas
            assert not canvas.is_closed
            assert xnano.terminal._screen.is_screen_claimed is False
            canvas.clock.step()

    def test_a_bad_effect_is_refused_by_open_before_the_screen_is_claimed(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(TypeError, match="has no setting called 'color'"):
                canvas.open(effects=[{'kind': 'effect.dissolve', 'color': 'red'}])  # type: ignore[list-item]
            with pytest.raises(ValueError, match='is not a known visual effect'):
                canvas.open(effects=[{'kind': 'effect.bogus'}])  # type: ignore[list-item]
            assert not isinstance(canvas, xnano.Terminal)
            assert xnano.terminal._screen.is_screen_claimed is False

    def test_a_canvas_is_created_with_new_and_the_error_says_so(self):
        with pytest.raises(TypeError, match=r'xnano\.new\(\.\.\.\)'):
            xnano.Canvas()  # type: ignore[call-arg]

    def test_padding_and_margin_are_accepted_for_the_canvas_itself(self):
        with xnano.new(width=8, height=3, padding=1, margin=1) as canvas:
            assert canvas.screen.padding.top == 1 and canvas.screen.margin.left == 1


class TestManualCanvasThreads:
    def test_using_the_runtime_from_another_thread_is_explained(self):
        canvas = xnano.new(width=8, height=1)
        failures: list[BaseException] = []

        def attempt(action) -> None:
            try:
                action()
            except BaseException as error:
                failures.append(error)

        for action in (canvas.clock.step, canvas.screen.render, canvas.close):
            thread = threading.Thread(target=attempt, args=(action,))
            thread.start()
            thread.join()
        assert len(failures) == 3
        assert all(isinstance(error, TerminalError) for error in failures)
        assert 'thread that created it' in str(failures[2])
        assert all('realtime=True' in str(error) for error in failures)
        assert not canvas.is_closed
        canvas.close()
        assert canvas.is_closed

    def test_a_hook_refused_on_another_thread_is_not_left_registered(self):
        canvas = xnano.new(width=8, height=1)
        failures: list[BaseException] = []

        def attempt() -> None:
            try:
                canvas.hook(lambda context: None, on='tick')
            except BaseException as error:
                failures.append(error)

        thread = threading.Thread(target=attempt)
        thread.start()
        thread.join()
        assert len(failures) == 1 and 'realtime=True' in str(failures[0])
        assert canvas._registrations == []
        assert canvas._ledger == []
        canvas.close()

    def test_the_size_of_a_closed_canvas_is_the_size_it_had(self):
        canvas = xnano.new(width=10, height=2)
        canvas.screen.write('hi')
        canvas.clock.step()
        canvas.close()
        assert (canvas.screen.width, canvas.screen.height) == (10, 2)
        assert tuple(canvas.screen.size) == (10, 2)


class TestFailingHooks:
    def test_a_failing_hook_stops_a_canvas_that_you_step(self):
        calls: list[int] = []

        def explode(context) -> None:
            calls.append(1)
            raise ZeroDivisionError('nope')

        canvas = xnano.new(width=8, height=1)
        canvas.hook(explode, on='tick')
        with pytest.raises(TerminalError, match='explode.*ZeroDivisionError'):
            canvas.clock.step()
        assert canvas.is_closed and not canvas.is_running
        with pytest.raises(TerminalClosedError, match='ZeroDivisionError'):
            canvas.clock.step()
        assert calls == [1]
        canvas.close()

    def test_a_failing_hook_ends_iteration_with_the_error(self):
        canvas = xnano.new(width=8, height=1)
        canvas.hook(lambda context: 1 / 0, on='tick')
        with pytest.raises(TerminalError, match='ZeroDivisionError'):
            list(canvas.iter(frames=3))
        canvas.close()


class TestReleasedRuntime:
    def test_a_closed_canvas_with_callbacks_is_freed_by_the_garbage_collector(self):
        import gc
        import weakref

        references = []
        for _ in range(3):
            canvas = xnano.new(width=20, height=4)
            canvas.screen.write('x').hook(lambda context: None, on='key')
            canvas.hook(lambda context: None, on='tick')
            canvas.clock.step()
            canvas.close()
            references.append(weakref.ref(canvas))
            del canvas
        gc.collect()
        assert [reference() for reference in references] == [None, None, None]


class TestOpeningWithoutATerminalMessage:
    @pytest.mark.skipif(
        __import__('sys').platform == 'win32',
        reason='a Windows runner has a console to draw on',
    )
    def test_the_error_says_to_draw_into_a_canvas_instead(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(TerminalError) as caught:
                canvas.open(height=1)
            text = str(caught.value)
            assert 'xnano.new()' in text and 'canvas.screen.render()' in text
            assert 'Runtime.offscreen' not in text
            assert not isinstance(canvas, xnano.Terminal)

    @pytest.mark.skipif(
        __import__('sys').platform == 'win32',
        reason='a Windows runner has a console to draw on',
    )
    def test_a_failed_open_leaves_standard_output_untouched(self):
        import subprocess
        import sys

        result = subprocess.run(  # noqa: S603
            [sys.executable, '-c', 'import xnano\nxnano.open(height=3)'],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0
        assert result.stdout == b''


class TestPercentageSizes:
    @pytest.fixture
    def window(self, monkeypatch):
        import os

        size = os.terminal_size((120, 40))
        monkeypatch.setattr(xnano.terminal._screen, 'window_size', lambda: size)
        return size

    def test_a_percentage_is_a_share_of_the_window(self, window):
        with xnano.new(width='50%', height='25%') as canvas:
            assert (canvas.screen.width, canvas.screen.height) == (60, 10)

    def test_one_hundred_percent_is_the_whole_window(self, window):
        with xnano.new(width='100%', height='100%') as canvas:
            assert (canvas.screen.width, canvas.screen.height) == (120, 40)

    def test_any_percentage_works_and_rounds_to_cells(self, window):
        with xnano.new(width='33%', height='12.5%') as canvas:
            assert (canvas.screen.width, canvas.screen.height) == (40, 5)

    @pytest.mark.parametrize('value', ['0%', '150%', 'half', '%', '-5%', 'nan%'])
    def test_a_bad_percentage_is_refused(self, value):
        with pytest.raises(ValueError, match='or a percentage of the window'):
            xnano.new(width=value)

    def test_a_canvas_written_into_another_keeps_its_share_of_the_parent(self):
        with xnano.new(width=40, height=10) as outer:
            inner = xnano.new(width='50%', height='50%')
            placement = outer.screen.write(inner)
            assert (placement.width, placement.height) == (20, 5)
