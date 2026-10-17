"""
tests.test_canvas

A canvas is a virtual terminal: what ``new()`` creates, its time controls, the canvases written
into it, and how it ends.
"""

from __future__ import annotations

import dataclasses
import pathlib
import re
import threading
from typing import cast

import pytest
from xnano_image import TerminalImage

import xnano
from xnano.canvas import Canvas
from xnano.context import Frame
from xnano.errors import TerminalClosedError, TerminalError
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
            assert (canvas.width, canvas.height) == (80, 24)
            assert canvas.fps == 60
            assert canvas.bpm == 120
            assert not canvas.time.is_realtime
            assert canvas.deps is None
            assert canvas.is_running and not canvas.is_closed
            assert canvas.state.get('anything') is None

    def test_the_settings_are_kept(self):
        with xnano.new(
            width=12, height=3, fps=10, bpm=90, title='T', deps={'name': 'app'}
        ) as canvas:
            assert (canvas.width, canvas.height, canvas.fps, canvas.bpm) == (
                12,
                3,
                10,
                90,
            )
            assert canvas.title == 'T'
            assert canvas.deps == {'name': 'app'}
        with xnano.new(width=8, height=1, state=Settings(volume=3)) as typed:
            assert typed.state.volume == 3

    def test_realtime_runs_on_the_wall_clock(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            assert canvas.time.is_realtime
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
            screen = canvas._gates_for_screen({**canvas._gates, 'scroll': False})
            assert screen['mouse'] == 'motion'
            assert screen['scroll'] is False, (
                'a gate given to open() replaces the stored one'
            )
            assert screen['keyboard'] is False and screen['paste'] is False
            assert screen['focus'] is True, 'a gate never given takes its default'

    def test_a_hook_turns_an_unset_gate_on_and_refuses_one_given_as_false(self):
        with xnano.new() as canvas:

            @canvas.hook(on='mouse', when="mouse.kind == 'press'")
            def click(context: xnano.context.Context) -> None:
                pass

            assert canvas._gates_for_screen({})['mouse'] is True
            with pytest.raises(TerminalError, match='needs mouse=True'):
                canvas._gates_for_screen({'mouse': False})

    def test_a_hook_on_a_canvas_that_runs_by_itself_turns_an_unset_gate_on(self):
        for _ in range(20):
            with xnano.new(realtime=True, width=8, height=1) as canvas:
                canvas.hook(
                    lambda context: None, on='mouse', when="mouse.kind == 'press'"
                )
                assert canvas._gates_for_screen({})['mouse'] is True
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            canvas.hook(lambda context: None, on='mouse', when="mouse.kind == 'press'")
            with pytest.raises(TerminalError, match='needs mouse=True'):
                canvas._gates_for_screen({'mouse': False})

    def test_the_gate_error_names_the_function_the_user_wrote(self):
        def on_press(context: xnano.context.Context) -> None:
            pass

        def on_drag(context: xnano.context.Context) -> None:
            pass

        def on_click(context: xnano.context.Context) -> None:
            pass

        with xnano.new() as canvas:
            canvas.write('x').hook(on='mouse')(on_press)
            with pytest.raises(TerminalError, match='hook on_press needs mouse=True'):
                canvas._gates_for_screen({'mouse': False})
        with xnano.new() as canvas:
            canvas.hook(on='drag')(on_drag)
            with pytest.raises(TerminalError, match='hook on_drag needs mouse=True'):
                canvas._gates_for_screen({'mouse': False})
        with xnano.new() as canvas:
            canvas.hook(on_click, on='mouse', when="mouse.kind == 'press'")
            with pytest.raises(TerminalError, match='hook on_click needs mouse=True'):
                canvas._gates_for_screen({'mouse': False})

    def test_gates_given_to_new_and_open_are_both_kept(self):
        with xnano.new(width=8, height=1, mouse=True) as canvas:
            settings = canvas._parse_open_settings({'scroll': True})
            gates = {**canvas._gates, **cast('dict[str, object]', settings['gates'])}
            resolved = canvas._gates_for_screen(gates)
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
            canvas.write('hi')
            lines = canvas.render().split('\n')
            assert lines[0] == '┌──────┐'
            assert lines[2] == '│ hi   │'
        with xnano.new(width=8, height=3, margin={'left': 2}) as canvas:
            canvas.write('hi')
            assert canvas.render().split('\n')[0] == '  hi'

    def test_appearance_with_content_names_the_function_that_was_called(self):
        with pytest.raises(TypeError, match=r'call open\(\) without content'):
            xnano.open('hello', border='rounded')
        with pytest.raises(TypeError, match=r'call new\(\) without content'):
            xnano.new('hello', border='rounded')

    def test_content_is_written_at_the_origin(self):
        with xnano.new('hello', width=8, height=2) as canvas:
            assert canvas.render() == 'hello\n'
            placement = canvas._placements[0]
            assert (placement.x, placement.y) == (0, 0)

    def test_appearance_keywords_style_the_canvas_and_not_the_content(self):
        with pytest.raises(TypeError, match='not its content: border') as caught:
            xnano.new('hello', border='rounded')
        assert 'canvas.write(content, border=...)' in str(caught.value)
        with xnano.new(width=6, height=3, border='rounded') as canvas:
            assert canvas.render().split('\n')[0] == '╭────╮'

    def test_effects_apply_to_the_canvas_and_to_written_content(self):
        with xnano.new(
            width=6,
            height=1,
            effects=[{'kind': 'effect.fade_to', 'foreground': 'red'}],
        ) as canvas:
            assert len(canvas._effects) == 1
            label = canvas.write(
                'hi', effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 50}]
            )
            assert len(canvas._effects) == 2
            canvas.step(delta_seconds=1.0)
            label.remove()
            assert all(target is not label for _, target in canvas._effects)

    def test_an_effect_list_takes_dictionaries_of_visual_effects(self):
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(TypeError, match='effects= takes dictionaries'):
                canvas.write('x', effects=[xnano.operations.fx('effect.dissolve')])  # type: ignore[list-item]
            with pytest.raises(TypeError, match='is not a visual effect'):
                canvas.write('x', effects=[{'kind': 'fill', 'cell': '.'}])

    def test_render_is_the_current_frame_as_text_or_ansi(self):
        with xnano.new(width=6, height=2) as canvas:
            canvas.write('hi', y=1, foreground='red')
            text = canvas.render()
            assert text == '\nhi'
            assert str(canvas) == text
            assert canvas.render(format='ansi') == canvas.output.snapshot().ansi
            assert '\x1b[' in canvas.render(format='ansi')
            with pytest.raises(ValueError, match="'text' or 'ansi'"):
                canvas.render(format='html')  # type: ignore[arg-type]

    def test_a_canvas_sits_at_the_origin_and_cannot_be_moved(self):
        with xnano.new(width=6, height=2) as canvas:
            assert (canvas.x, canvas.y) == (0, 0)
            assert canvas.local(Point(2, 1)) == Point(2, 1)
            with pytest.raises(TerminalError, match='sits at the origin'):
                canvas.up()
            with pytest.raises(TerminalError, match=r'placement\.move'):
                canvas.move(x=1)
            assert not hasattr(canvas, 'is_stopped')

    def test_the_root_and_parent_are_formula_scopes(self):
        with xnano.new(width=6, height=2) as canvas:
            assert canvas.root.time is TimeElapsed
            assert canvas.inspect(canvas.root.width) == 6

    def test_closing_twice_is_harmless(self):
        canvas = xnano.new(width=4, height=1)
        canvas.close()
        canvas.close()
        assert canvas.is_closed
        with pytest.raises(TerminalClosedError, match='has been closed'):
            canvas.write('late')


class TestEnding:
    def test_quit_leaves_a_canvas_from_new_open(self):
        with xnano.new(width=12, height=1) as canvas:
            canvas.quit()
            assert not canvas.is_running
            assert not canvas.is_closed
            canvas.write('still here')
            assert 'still here' in canvas.render()
            assert list(canvas.iter(count=3)) == [], 'the request to end is still set'

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
                canvas.write('late')
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
        with xnano.new(width=4, height=1) as outer:
            assert xnano.active() is outer
            with xnano.new(width=4, height=1) as inner:
                assert xnano.active() is inner
                inner.quit()
                assert xnano.active() is outer, 'a canvas that quit gives way'
            assert xnano.active() is outer
        assert xnano.active(is_required=False) is None
        with pytest.raises(TerminalClosedError, match='No canvas is running'):
            xnano.active()

    def test_the_old_keyword_is_refused(self):
        with pytest.raises(TypeError):
            xnano.active(required=False)  # type: ignore[call-overload]


class TestTimeControls:
    def test_iter_counts_frames_and_steps_the_manual_clock(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            frames = list(canvas.iter(count=3))
            assert [round(frame.elapsed_seconds, 3) for frame in frames] == [
                0.0,
                0.1,
                0.2,
            ]
            assert all(isinstance(frame, Frame) for frame in frames)
            assert round(canvas.time.elapsed, 3) == 0.3

    def test_iter_ends_on_seconds_of_canvas_time(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            assert len(list(canvas.iter(seconds=0.5))) == 5

    def test_count_and_seconds_end_on_the_first(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            assert len(list(canvas.iter(count=2, seconds=10))) == 2
            assert len(list(canvas.iter(count=50, seconds=0.3))) == 3

    def test_an_unbounded_iter_ends_on_break_or_quit(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            for frame in canvas.iter():
                if frame.index >= 4:
                    break
            assert canvas.time.frame == 4
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
            assert round(canvas.time.elapsed, 3) == 0.1

    def test_a_step_moves_one_frame_and_returns_it(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            frame = canvas.step()
            assert isinstance(frame, Frame)
            assert frame.elapsed_seconds == pytest.approx(0.1)
            assert frame.delta_seconds == pytest.approx(0.1)
            assert frame.index == canvas.time.frame

    def test_a_canvas_that_runs_by_itself_is_stepped_only_while_stopped(self):
        canvas = xnano.new(realtime=True, width=4, height=1, fps=10)
        try:
            with pytest.raises(TerminalError, match='cannot be stepped by hand'):
                canvas.step()
            canvas.stop()
            before = canvas.time.elapsed
            frame = canvas.step()
            assert isinstance(frame, Frame)
            assert canvas.time.elapsed == pytest.approx(before + 0.1, abs=1e-6)
            assert canvas.time.is_stopped
        finally:
            canvas.close()

    def test_sixty_steps_at_sixty_frames_per_second_are_one_second(self):
        with xnano.new(width=4, height=1, fps=60) as canvas:
            for _ in range(60):
                canvas.step()
            assert canvas.time.elapsed == pytest.approx(1.0, abs=1e-9)
        with xnano.new(width=4, height=1, fps=60) as canvas:
            list(canvas.iter(count=60))
            assert canvas.time.elapsed == pytest.approx(1.0, abs=1e-9)
        with xnano.new(width=4, height=1, fps=60) as canvas:
            for _ in range(30):
                canvas.step()
            list(canvas.iter(count=30))
            assert canvas.time.elapsed == pytest.approx(1.0, abs=1e-9)

    def test_a_step_takes_a_positive_delta_and_deliver_events_does_not_move_time(self):
        with xnano.new(width=4, height=1) as canvas:
            canvas.step(delta_seconds=0.25)
            assert canvas.time.elapsed == pytest.approx(0.25)
            with pytest.raises(ValueError, match='deliver_events'):
                canvas.step(delta_seconds=0)
            with pytest.raises(ValueError, match='above zero'):
                canvas.step(delta_seconds=-1)
            heard: list[str] = []
            canvas.hook(lambda context: heard.append(context.event.kind))
            canvas.push(Event.custom('ping'))
            canvas.deliver_events()
            assert heard == ['custom']
            assert canvas.time.elapsed == pytest.approx(0.25)

    def test_stop_freezes_iter_while_step_moves_one_frame(self):
        with xnano.new(width=8, height=1, fps=10) as canvas:
            label = canvas.write('-')
            canvas.stop()
            assert canvas.time.is_stopped
            texts = []
            for frame in canvas.iter(count=3):
                label.text = str(frame.index)
                texts.append(frame.elapsed_seconds)
            assert texts == [0.0, 0.0, 0.0], 'a stopped canvas draws without moving time'
            assert '2' in canvas.render()
            canvas.step()
            assert canvas.time.elapsed == pytest.approx(0.1)
            assert canvas.time.is_stopped, 'a step leaves the canvas stopped'
            canvas.resume()
            assert not canvas.time.is_stopped

    def test_time_is_continuous_across_stop_and_resume(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            list(canvas.iter(count=2))
            canvas.stop()
            list(canvas.iter(count=5))
            canvas.resume()
            list(canvas.iter(count=2))
            assert canvas.time.elapsed == pytest.approx(0.4)

    def test_stopped_time_holds_formulas_and_timers_while_input_still_arrives(self):
        with xnano.new(width=20, height=1, fps=10) as canvas:
            ball = canvas.write('o')
            ball.x = TimeElapsed * 10
            ticks: list[float] = []
            canvas.hook(on='tick', every=0.1)(
                lambda context: ticks.append(context.time.elapsed)
            )
            pressed: list[str] = []
            canvas.hook(on='key')(lambda context: pressed.append(context.keyboard.key))
            canvas.step(delta_seconds=0.5)
            before = (ball.x, len(ticks))
            canvas.stop()
            for _ in canvas.iter(count=3):
                pass
            canvas.push(Event.key_press('a'))
            canvas.deliver_events()
            assert (ball.x, len(ticks)) == before
            assert pressed == ['a']

    def test_seconds_on_a_stopped_canvas_is_refused(self):
        with xnano.new(width=4, height=1) as canvas:
            canvas.stop()
            with pytest.raises(TerminalError, match='never reaches seconds=1'):
                canvas.iter(seconds=1)
            assert len(list(canvas.iter(count=2, seconds=1))) == 2

    def test_iter_seconds_raises_when_stopped_inside_the_loop(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            with pytest.raises(TerminalError, match='canvas.resume'):
                for frame in canvas.iter(seconds=1):
                    if frame.index == 1:
                        canvas.stop()
            canvas.resume()
            seen = 0
            for _ in canvas.iter(count=3, seconds=10):
                seen += 1
                canvas.stop()
            assert seen == 3

    def test_the_canvas_verbs_are_the_time_verbs(self):
        with xnano.new(width=4, height=1, fps=10) as canvas:
            canvas.time.stop()
            assert canvas.time.is_stopped
            canvas.resume()
            assert not canvas.time.is_stopped
            canvas.stop()
            frame = canvas.time.step()
            assert frame.elapsed_seconds == pytest.approx(0.1)
            assert repr(canvas.time) == 'Time(elapsed=0.100, is_stopped=True)'


class TestChildCanvases:
    def test_a_canvas_written_into_another_draws_inside_it_on_its_time(self):
        with xnano.new(width=20, height=3, fps=10) as outer:
            inner = xnano.new(width=6, height=1)
            inner.write('inside')
            placement = outer.write(inner, x=2, y=1)
            assert (placement.x, placement.y, placement.width) == (2, 1, 6)
            assert outer.render().split('\n')[1] == '  inside'
            outer.step(delta_seconds=0.5)
            assert inner.time is outer.time
            assert inner.time.elapsed == pytest.approx(0.5)
            assert xnano.active() is outer
            inner.write('!', x=5)
            assert outer.render().split('\n')[1] == '  insid!'
            inner.close()
            assert inner.is_closed
            assert outer.is_running
            assert outer.render().split('\n')[1] == ''

    def test_a_child_renders_its_own_cells_and_not_the_outer_frame(self):
        with xnano.new(width=20, height=3) as outer:
            inner = xnano.new(width=6, height=1)
            inner.write('hi')
            outer.write(inner, x=2, y=1)
            assert inner.render() == 'hi'
            assert outer.render().split('\n')[1] == '  hi'

    def test_the_formulas_and_hooks_of_a_child_move_to_the_outer_canvas(self):
        with xnano.new(width=20, height=2, fps=10) as outer:
            inner = xnano.new(width=10, height=1)
            ball = inner.write('o')
            ball.x = TimeElapsed * 10
            ticks: list[float] = []
            inner.hook(on='tick', every=0.1)(
                lambda context: ticks.append(context.time.elapsed)
            )
            outer.write(inner)
            outer.step(delta_seconds=0.5)
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
                    outer.write(inner)

    def test_a_closed_canvas_itself_or_a_child_twice_is_refused(self):
        with xnano.new(width=8, height=2) as outer:
            closed = xnano.new(width=2, height=1)
            closed.close()
            with pytest.raises(TerminalError, match='has been closed'):
                outer.write(closed)
            with pytest.raises(TerminalError, match='never into itself'):
                outer.write(outer)
            inner = xnano.new(width=2, height=1)
            outer.write(inner)
            with pytest.raises(TerminalError, match='once'):
                outer.write(inner)
            with pytest.raises(TerminalError, match='part of it'):
                inner.write(outer)
            with pytest.raises(TerminalError, match='Open the outer canvas'):
                inner.open()


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
            REPOSITORY / 'examples',
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
            canvas.write('still', x=2)
            canvas.write('more', y=1, border=None)
            for _ in range(5):
                canvas.step()
            list(canvas.iter(count=5))
            assert canvas._frame_demand == 0
            assert frame_calls == []
            assert canvas.render().startswith('  still')

    def test_a_fixed_image_makes_no_frame_call(self, frame_calls):
        image = xnano.Image(
            TerminalImage.from_rgba(2, 2, bytes([255, 0, 0, 255]) * 4), width=4
        )
        with xnano.new(width=20, height=4) as canvas:
            placement = canvas.write(image)
            assert canvas._frame_demand == 0
            for _ in range(5):
                canvas.step()
            assert frame_calls == []
            placement.remove()
            assert canvas._frame_demand == 0

    def test_an_image_that_follows_the_canvas_size_holds_frames_until_it_is_gone(
        self, frame_calls
    ):
        image = xnano.Image(TerminalImage.from_rgba(2, 2, bytes([255, 0, 0, 255]) * 4))
        with xnano.new(width=20, height=4) as canvas:
            placement = canvas.write(image)
            assert canvas._frame_demand == 1
            canvas.step()
            assert frame_calls
            placement.remove()
            assert canvas._frame_demand == 0

    def test_a_formula_holds_frames_until_it_is_gone(self, frame_calls):
        with xnano.new(width=20, height=1, fps=10) as canvas:
            ball = canvas.write('o')
            ball.x = TimeElapsed * 10
            assert canvas._frame_demand == 1
            canvas.step()
            canvas.step()
            assert frame_calls
            assert ball.x == 2
            ball.remove()
            assert canvas._frame_demand == 0
            assert canvas._frame_registration is None
            frame_calls.clear()
            canvas.step()
            assert frame_calls == []

    def test_a_frame_hook_holds_frames_until_its_placement_is_removed(self, frame_calls):
        with xnano.new(width=20, height=1) as canvas:
            label = canvas.write('-')
            seen: list[int] = []

            @label.hook(on='frame')
            def count(context: xnano.context.Context) -> None:
                seen.append(context.time.frame)

            canvas.step()
            canvas.step()
            assert len(seen) >= 2
            label.remove()
            canvas.step()
            assert canvas._frame_demand == 0

    def test_leaving_the_runtime_releases_the_frames_of_finished_effects(
        self, monkeypatch
    ):
        monkeypatch.setattr(Canvas, '_follow_effects', lambda self, runtime: False)
        with xnano.new(width=8, height=1) as canvas:
            canvas.write(
                'fade',
                effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 100}],
            )
            assert canvas._frame_demand == 1
            for _ in range(5):
                canvas.step(delta_seconds=0.1)
            assert canvas._effects, 'the canvas has not noticed the effect ended'
            canvas._host.call(canvas._unbind_runtime)
            assert canvas._effects == []
            assert canvas._frame_demand == 0

    def test_timers_need_no_frame_calls(self, frame_calls):
        with xnano.new(width=8, height=1) as canvas:
            ticks: list[float] = []
            canvas.hook(on='beat', every=1)(
                lambda context: ticks.append(context.time.elapsed)
            )
            for _ in range(20):
                canvas.step(delta_seconds=0.1)
            assert len(ticks) >= 3
            assert frame_calls == []

    def test_a_finished_effect_releases_its_frames(self, frame_calls):
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.write(
                'fade',
                effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 100}],
            )
            assert canvas._frame_demand == 1
            for _ in range(20):
                canvas.step(delta_seconds=0.05)
            assert canvas._effects == []
            assert canvas._frame_demand == 0
            label.remove()

    def test_the_ledger_stays_bounded(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.hook(on='beat', every=1)(lambda context: None)
            before = len(canvas._ledger)
            for _ in range(100):
                canvas.step(delta_seconds=0.5)
            assert len(canvas._ledger) == before
            for number in range(50):
                label = canvas.write(
                    str(number),
                    effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 20}],
                )
                canvas.step(delta_seconds=0.05)
                canvas.step(delta_seconds=0.05)
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
            label = canvas.write('kept')
            heard: list[str] = []
            canvas.hook(on='key')(lambda context: heard.append(context.keyboard.key))
            canvas.hook(on='tick', every=0.1)(lambda context: heard.append('tick'))
            canvas.step(delta_seconds=0.5)
            for _ in range(2):
                with pytest.raises(RuntimeError, match='could not be opened'):
                    canvas.open(height=2)
                assert xnano.terminal._live_terminal_open is False
            assert not isinstance(canvas, xnano.Terminal)
            assert not canvas.time.is_realtime
            assert canvas.time.elapsed == pytest.approx(0.5)
            label.text = 'still kept'
            canvas.push(Event.key_press('z'))
            canvas.step(delta_seconds=0.5)
            assert 'z' in heard and 'tick' in heard
            assert canvas.render().startswith('still kept')

    def test_opening_from_another_thread_teaches_where_to_open(self):
        with xnano.new(width=12, height=2) as canvas:
            label = canvas.write('kept')
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
            assert xnano.terminal._live_terminal_open is False
            canvas.step()
            assert canvas.render().startswith(label.text)

    def test_xnano_open_without_a_terminal_closes_the_canvas_it_made(self):
        with pytest.raises(RuntimeError, match='could not be opened'):
            xnano.open('content', height=2)
        assert xnano.terminal._live_terminal_open is False
        assert xnano.active(is_required=False) is None


def test_the_timers_of_what_a_child_holds_move_to_the_outer_canvas():
    with xnano.new(width=20, height=2) as outer:
        inner = xnano.new(width=10, height=1)
        label = inner.write('-')
        ticks: list[float] = []
        label.hook(on='tick', every=0.1)(
            lambda context: ticks.append(context.time.elapsed)
        )
        inner.step(delta_seconds=0.05)
        outer.write(inner)
        outer.step(delta_seconds=0.5)
        assert ticks


def test_the_hooks_of_a_child_canvas_hear_the_outer_canvas_and_stop_when_it_closes():
    with xnano.new(width=20, height=2) as outer:
        inner = xnano.new(width=10, height=1)
        heard: list[str] = []
        inner.hook(on='key')(lambda context: heard.append(context.keyboard.key))
        outer.write(inner)
        outer.push(Event.key_press('a'))
        outer.deliver_events()
        assert heard == ['a']
        inner.close()
        outer.push(Event.key_press('b'))
        outer.deliver_events()
        assert heard == ['a']
        assert inner not in outer._children


class TestRefusedSettings:
    def test_a_bad_border_kind_is_explained_before_anything_is_created(self):
        with pytest.raises(ValueError, match='"nonsense" is not a border kind|nonsense'):
            xnano.new(border='nonsense')  # type: ignore[arg-type]
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(ValueError, match='is not a border kind'):
                canvas.open(border='nonsense')  # type: ignore[arg-type]
            assert not isinstance(canvas, xnano.Terminal)
            assert xnano.terminal._live_terminal_open is False
            canvas.step()

    @pytest.mark.parametrize(
        'settings',
        [
            {'margin': 'x'},
            {'padding': 'x'},
            {'foreground': 'nocolor'},
            {'background': 'nocolor'},
            {'is_bold': 'x'},
            {'border_style': 'nonsense'},
        ],
    )
    def test_a_bad_appearance_value_is_refused_by_open_before_the_screen_is_claimed(
        self, settings
    ):
        with xnano.new(width=8, height=1) as canvas:
            canvas.write('hi')
            with pytest.raises((TypeError, ValueError)):
                canvas.open(**settings)  # type: ignore[arg-type]
            assert type(canvas) is xnano.Canvas
            assert not canvas.is_closed
            assert xnano.terminal._live_terminal_open is False
            canvas.step()

    def test_a_bad_effect_is_refused_by_open_before_the_screen_is_claimed(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(TypeError, match="has no setting called 'color'"):
                canvas.open(effects=[{'kind': 'effect.dissolve', 'color': 'red'}])  # type: ignore[list-item]
            with pytest.raises(ValueError, match='is not a known visual effect'):
                canvas.open(effects=[{'kind': 'effect.bogus'}])  # type: ignore[list-item]
            assert not isinstance(canvas, xnano.Terminal)
            assert xnano.terminal._live_terminal_open is False

    def test_a_canvas_is_created_with_new_and_the_error_says_so(self):
        with pytest.raises(TypeError, match=r'xnano\.new\(\.\.\.\)'):
            xnano.Canvas()  # type: ignore[call-arg]

    def test_padding_and_margin_are_accepted_for_the_canvas_itself(self):
        with xnano.new(width=8, height=3, padding=1, margin=1) as canvas:
            assert canvas.padding.top == 1 and canvas.margin.left == 1


class TestManualCanvasThreads:
    def test_using_the_runtime_from_another_thread_is_explained(self):
        canvas = xnano.new(width=8, height=1)
        failures: list[BaseException] = []

        def attempt(action) -> None:
            try:
                action()
            except BaseException as error:
                failures.append(error)

        for action in (canvas.step, canvas.render, canvas.close):
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
        canvas.write('hi')
        canvas.step()
        canvas.close()
        assert (canvas.width, canvas.height) == (10, 2)
        assert tuple(canvas.size) == (10, 2)


class TestFailingHooks:
    def test_a_failing_hook_stops_a_canvas_that_you_step(self):
        calls: list[int] = []

        def explode(context) -> None:
            calls.append(1)
            raise ZeroDivisionError('nope')

        canvas = xnano.new(width=8, height=1)
        canvas.hook(explode, on='tick')
        with pytest.raises(TerminalError, match='explode.*ZeroDivisionError'):
            canvas.step()
        assert canvas.is_closed and not canvas.is_running
        with pytest.raises(TerminalClosedError, match='ZeroDivisionError'):
            canvas.step()
        assert calls == [1]
        canvas.close()

    def test_a_failing_hook_ends_iteration_with_the_error(self):
        canvas = xnano.new(width=8, height=1)
        canvas.hook(lambda context: 1 / 0, on='tick')
        with pytest.raises(TerminalError, match='ZeroDivisionError'):
            list(canvas.iter(count=3))
        canvas.close()


class TestReleasedRuntime:
    def test_a_closed_canvas_with_callbacks_is_freed_by_the_garbage_collector(self):
        import gc
        import weakref

        references = []
        for _ in range(3):
            canvas = xnano.new(width=20, height=4)
            canvas.write('x').hook(lambda context: None, on='key')
            canvas.hook(lambda context: None, on='tick')
            canvas.step()
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
            assert 'xnano.new()' in text and 'canvas.render()' in text
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
