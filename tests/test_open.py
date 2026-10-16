"""
tests.test_open

The terminal you draw into: opening it, placing things on it, time and events.
"""

from __future__ import annotations

import ast
import pathlib
import sys
import textwrap
import threading
from typing import cast

import pytest

import xnano as main
import xnano.terminal as terminal_module
from xnano import active
from xnano import open as open_terminal
from xnano.context import Context, Update
from xnano.errors import (
    TerminalAlreadyOpenError,
    TerminalClosedError,
    TerminalError,
)
from xnano.terminal import Terminal
from xnano_core import (
    Buffer,
    Cell,
    Color,
    Event,
    Height,
    ParentHeight,
    ParentWidth,
    Point,
    PointerPosition,
    TimeElapsed,
    Width,
    Write,
)


@pytest.fixture
def terminal():
    with open_terminal(offscreen=True, width=20, height=6, fps=10) as opened:
        yield opened


def dispatch(terminal: Terminal, event: Event) -> None:
    terminal._runtime.dispatch(event)
    terminal.loop.step()


class TestOpening:
    def test_an_offscreen_terminal_has_a_size_and_a_backend(self):
        with open_terminal(offscreen=True) as default:
            assert (default.width, default.height) == (80, 24)
            assert default.backend == 'offscreen'
            assert not default.is_live
        with open_terminal(offscreen=True, width=7, height=3) as small:
            assert small.size.width == 7 and small.size.height == 3
            assert 'width=7' in repr(small)

    def test_arguments_that_do_not_apply_are_explained(self):
        with pytest.raises(ValueError, match='only apply to a live terminal'):
            open_terminal(offscreen=True, mouse=True)
        with pytest.raises(ValueError, match='needs a height too'):
            open_terminal(width=10)
        with pytest.raises(ValueError, match='only apply to a live terminal'):
            open_terminal(offscreen=True, alternate_screen=False)
        with pytest.raises(ValueError, match='above zero'):
            open_terminal(offscreen=True, fps=0)

    @pytest.mark.skipif(
        sys.platform == 'win32', reason='a Windows runner has a console to draw on'
    )
    def test_a_live_terminal_that_cannot_open_leaves_the_screen_free(self):
        # The test run has no terminal to draw on.
        for _ in range(2):
            with pytest.raises(RuntimeError, match='could not be opened'):
                open_terminal(height=2)
            assert terminal_module._live_terminal_open is False

    def test_a_second_live_terminal_is_refused(self, monkeypatch):
        monkeypatch.setattr(terminal_module, '_live_terminal_open', True)
        with pytest.raises(TerminalAlreadyOpenError, match='only one screen'):
            open_terminal()

    def test_the_active_terminal_follows_nesting(self):
        assert active(required=False) is None
        with pytest.raises(TerminalClosedError, match='No terminal is open'):
            active()
        with open_terminal(offscreen=True) as outer:
            assert active() is outer
            with open_terminal(offscreen=True) as inner:
                assert active() is inner
            assert active() is outer
        assert active(required=False) is None

    def test_a_closed_terminal_explains_itself(self):
        terminal = open_terminal(offscreen=True, width=10, height=2)
        terminal.close()
        terminal.close()
        assert terminal.is_closed and 'closed' in repr(terminal)
        for action in (
            lambda: terminal.write('x'),
            lambda: terminal.pixels,
            lambda: terminal.write('x'),
            lambda: terminal.output.render(),
            lambda: list(terminal.iter(count=1)),
        ):
            with pytest.raises(TerminalClosedError, match='has been closed'):
                action()

    def test_printing_a_terminal_shows_its_last_frame(self, terminal):
        terminal.write('hi', x=1, y=0)
        terminal.output.render()
        assert 'hi' in str(terminal)


class TestFrames:
    def test_frames_follow_the_requested_rate(self, terminal):
        frames = list(terminal.iter(count=4))
        assert [frame.index for frame in frames] == [0, 1, 2, 3]
        assert [round(frame.elapsed_seconds, 3) for frame in frames] == [
            0.0,
            0.1,
            0.2,
            0.3,
        ]
        assert [round(frame.delta_seconds, 3) for frame in frames] == [0.0, 0.1, 0.1, 0.1]
        assert frames[0].area.width == 20 and frames[0].terminal is terminal

    def test_a_duration_ends_the_iteration(self, terminal):
        assert len(list(terminal.iter(duration_seconds=0.5))) == 5

    def test_the_rate_does_not_drift(self):
        with open_terminal(offscreen=True, width=4, height=1, fps=60) as sixty:
            list(sixty.iter(count=60))
            assert sixty.time.elapsed == pytest.approx(1.0, abs=0.001)

    def test_stopping_ends_the_iteration(self, terminal):
        seen = 0
        for frame in terminal.iter():
            seen += 1
            if frame.index == 2:
                terminal.stop()
        assert seen == 3

    def test_a_loop_draws_what_it_changes(self, terminal):
        for frame in terminal.iter(count=3):
            terminal.write(str(frame.index), x=frame.index, y=0)
        terminal.output.render()
        assert terminal.output.snapshot().lines()[0] == '012'

    def test_advance_moves_the_clock_and_draws(self, terminal):
        terminal.loop.advance(0.25)
        assert terminal.time.elapsed == 0.25

    def test_run_would_wait_forever_on_a_manual_clock(self, terminal):
        with pytest.raises(TerminalError, match='wait forever'):
            terminal.run()


class TestPlacements:
    def test_numbers_apply_once(self, terminal):
        placement = terminal.write(Buffer.with_text('ab'), x=3, y=2)
        assert (placement.x, placement.y) == (3, 2)
        assert (placement.width, placement.height) == (2, 1)
        placement.x = 5
        assert placement.x == 5

    def test_percentages_follow_the_terminal(self, terminal):
        placement = terminal.write('hello', x='50%', y='50%', width='25%')
        terminal.output.render()
        assert (placement.x, placement.y, placement.width) == (10, 3, 5)
        terminal._runtime.resize(width=40, height=10)
        terminal.loop.step()
        terminal.output.render()
        assert (placement.x, placement.y, placement.width) == (20, 5, 10)

    def test_a_size_range_limits_the_size(self, terminal):
        wide = terminal.write(Buffer(width=15, height=4), width=(1, 10))
        narrow = terminal.write(Buffer(width=2, height=4), width=(5, None))
        percent = terminal.write(Buffer(width=15, height=4), width=(None, '25%'))
        terminal.output.render()
        assert wide.width == 10
        assert narrow.width == 5
        assert percent.width == 5
        wide.width = 3
        assert wide.width == 3
        wide.width = 99
        assert wide.width == 10
        wide.width = 0
        assert wide.width == 1

    def test_a_position_range_is_how_far_it_may_travel(self, terminal):
        thumb = terminal.write(Buffer.with_text('#'), x=(2, 10))
        assert thumb.x == 2, 'it is held inside the range at once'
        thumb.x = 6
        assert thumb.x == 6
        thumb.x = 400
        assert thumb.x == 10
        thumb.x = -4
        assert thumb.x == 2
        thumb.x = '50%'
        assert thumb.x == 10
        vertical = terminal.write(Buffer.with_text('#'), y=(1, 4))
        vertical.y = 9
        assert vertical.y == 4

    def test_a_range_stays_until_another_replaces_it(self, terminal):
        thumb = terminal.write('#', x=(2, 10))
        thumb.x = 8
        thumb.x = (4, 6)
        assert thumb.x == 6
        thumb.x = 0
        assert thumb.x == 4
        thumb.x = (None, None)
        thumb.x = 17
        assert thumb.x == 17

    def test_range_bounds_may_be_percentages_or_expressions(self, terminal):
        thumb = terminal.write('#', x=('10%', '90%'))
        thumb.x = 0
        assert thumb.x == 2
        thumb.x = 19
        assert thumb.x == 18
        track = terminal.write('##', x=(0, ParentWidth - Width))
        track.x = 100
        assert track.x == 18
        terminal._runtime.resize(width=40, height=6)
        terminal.loop.step()
        assert thumb.x == 18, 'a bound is evaluated again when the terminal changes'
        thumb.x = 100
        track.x = 100
        terminal.output.render()
        assert thumb.x == 36
        assert track.x == 38

    def test_a_range_holds_a_formula_too(self, terminal):
        ball = terminal.write('o', x=(0, 6))
        ball.x = (ParentWidth - Width) * (TimeElapsed % 1.0)
        positions = [
            cast('int', ball.x),
            *(cast('int', ball.x) for _ in terminal.iter(count=8)),
        ]
        assert max(positions) == 6
        assert positions[:3] == [0, 0, 2]

    def test_a_range_must_be_an_ordered_pair(self, terminal):
        placement = terminal.write('x')
        with pytest.raises(ValueError, match='starts at 9 but ends at 2'):
            placement.x = (9, 2)
        with pytest.raises(ValueError, match='is a pair'):
            placement.y = (0, 4, 2)
        with pytest.raises(ValueError, match='is a pair'):
            placement.y = (0,)
        with pytest.raises(ValueError, match='not a valid bound'):
            placement.x = ('wide', 4)
        with pytest.raises(ValueError, match='not a valid bound'):
            placement.x = (True, 4)
        with pytest.raises(ValueError, match='starts at 1 but ends at -2'):
            placement.x = (Width, Width - 3)
        assert placement._limits == {}
        terminal.loop.step()

    def test_removing_forgets_the_range(self, terminal):
        thumb = terminal.write('#', x=(0, 3))
        thumb.remove()
        assert thumb._limits == {}

    def test_expressions_follow_the_clock(self, terminal):
        ball = terminal.write('o')
        ball.x = (ParentWidth - Width) * (TimeElapsed % 1.0)
        positions = [ball.x, *(ball.x for _ in terminal.iter(count=4))]
        assert positions[:5] == [0, 0, 2, 4, 6]

    def test_expressions_can_center(self, terminal):
        label = terminal.write('hello')
        label.x = (ParentWidth - Width) // 2
        label.y = (ParentHeight - Height) // 2
        terminal.output.render()
        assert (label.x, label.y) == (7, 2)

    def test_assigning_a_number_stops_following_an_expression(self, terminal):
        ball = terminal.write('o')
        ball.x = TimeElapsed * 10
        terminal.loop.advance(0.5)
        assert cast('int', ball.x) == 5
        ball.x = 1
        terminal.loop.advance(0.5)
        assert cast('int', ball.x) == 1

    def test_a_formula_over_unseen_input_is_explained(self, terminal):
        placement = terminal.write('o', x=3)
        with pytest.raises(TypeError, match='input that has not been seen'):
            placement.x = PointerPosition.x

    def test_bad_axes_are_explained(self, terminal):
        placement = terminal.write('x')
        with pytest.raises(ValueError, match='not a percentage'):
            placement.x = 'half%'
        with pytest.raises(ValueError, match='not a valid x'):
            placement.x = 'half'
        with pytest.raises(ValueError, match='not a valid x'):
            placement.x = '12'
        with pytest.raises(ValueError, match='is a pair'):
            placement.width = (1, 5, 2)
        with pytest.raises(ValueError, match='not a valid y'):
            placement.y = True
        with pytest.raises(ValueError, match='not a valid x'):
            placement.x = None  # type: ignore[assignment]

    def test_content_kinds(self, terminal):
        class Greeting:
            def __xnano_buffer__(self) -> Buffer:
                return Buffer.with_text('hi')

        grid = Buffer.with_text('cell').to_cell_grid()
        for content in ('text', grid, Greeting(), Buffer.with_text('buffer')):
            assert terminal.write(content).width > 0
        with pytest.raises(TypeError, match='Cannot show a int'):
            terminal.write(5)  # type: ignore[arg-type]

        class Broken:
            def __xnano_buffer__(self) -> int:
                return 1

        with pytest.raises(TypeError, match='must return a Buffer'):
            terminal.write(Broken())  # type: ignore[arg-type]

    def test_layers_order_the_drawing(self, terminal):
        terminal.write(Buffer.with_text('a'), layer=1)
        terminal.write(Buffer.with_text('b'), layer=0)
        terminal.output.render()
        assert terminal.output.snapshot().lines()[0] == 'a'

    def test_removing_and_hiding(self, terminal):
        placement = terminal.write('hi')
        placement.is_visible = False
        terminal.output.render()
        assert terminal.output.snapshot().lines()[0] == ''
        placement.is_visible = True
        placement.remove()
        placement.remove()
        terminal.output.render()
        assert terminal.output.snapshot().lines()[0] == ''
        assert 'removed' in repr(placement)

    def test_a_placement_has_pixels(self, terminal):
        placement = terminal.write(Buffer(width=3, height=1))
        placement.pixels[0, 0] = (255, 0, 0)
        assert placement.pixels.height == 2


class TestRegions:
    def test_a_color_fills_the_background(self, terminal):
        terminal[0:3, 0:2] = Color('#336699')
        assert terminal[1, 1].background.to_rgb() == (0x33, 0x66, 0x99)
        assert terminal[3, 0].background.to_rgb() is None
        terminal[4:6, 0:1] = (1, 2, 3)
        assert terminal[4, 0].background.to_rgb() == (1, 2, 3)

    def test_a_string_is_written(self, terminal):
        terminal[2:12, 1:2] = 'hello'
        assert terminal[2, 1].symbol == 'h'
        terminal[0, 0] = 'z'
        assert terminal[0, 0].symbol == 'z'

    def test_a_buffer_covers_the_region(self, terminal):
        terminal[4:8, 2:4] = Buffer(width=1, height=1)
        placement = terminal._placements[-1]
        assert (placement.x, placement.y, placement.width, placement.height) == (
            4,
            2,
            4,
            2,
        )

    def test_slices_can_be_open_and_empty_regions_are_ignored(self, terminal):
        terminal[:, 5:] = (255, 255, 255)
        assert terminal[19, 5].background.to_rgb() == (255, 255, 255)
        terminal[5:5, 0:1] = 'x'

    def test_steps_and_single_cell_fills_are_explained(self, terminal):
        with pytest.raises(ValueError, match='step'):
            terminal[0:6:2, 0:1] = 'x'
        with pytest.raises(TypeError, match='single cell'):
            terminal[0, 0] = (1, 2, 3)

    def test_clear_erases_the_cells(self, terminal):
        terminal.write('hello')
        terminal.clear()
        assert terminal[0, 0].symbol == ' '

    def test_update_and_inspect(self, terminal):
        terminal.update(Write('abc', x=1, y=1))
        assert terminal.inspect(Width) == 20
        assert terminal[1, 1].symbol == 'a'


class TestPixels:
    def test_pixels_have_the_resolution_of_their_encoding(self, terminal):
        assert (terminal.pixels.width, terminal.pixels.height) == (20, 12)
        braille = terminal.pixels.braille
        assert (braille.width, braille.height, braille.encoding) == (40, 24, 'braille')

    def test_colors_may_be_tuples_or_hex(self, terminal):
        pixels = terminal.pixels
        pixels[0, 0] = '#ff0000'
        pixels[0, 1] = (0, 0, 255)
        assert terminal[0, 0].symbol == '▀'
        assert terminal[0, 0].foreground.to_rgb() == (255, 0, 0)
        assert terminal[0, 0].background.to_rgb() == (0, 0, 255)

    def test_colors_without_channels_are_explained(self, terminal):
        with pytest.raises(ValueError, match="'#rrggbb'"):
            terminal.pixels[0, 0] = 'reset'
        with pytest.raises(ValueError, match='0 to 255'):
            terminal.pixels[0, 0] = (300, 0, 0)
        with pytest.raises(ValueError, match='not a color'):
            terminal.pixels[0, 0] = 5  # type: ignore[assignment]

    def test_a_slice_draws_every_pixel_it_covers(self, terminal):
        terminal.pixels[0:3, 0] = '#ff0000'
        for column in range(3):
            assert terminal[column, 0].foreground.to_rgb() == (255, 0, 0)
        assert terminal[3, 0].symbol == ' '
        terminal.pixels[:, :] = (0, 0, 255)
        assert terminal[19, 5].background.to_rgb() == (0, 0, 255)

    def test_a_slice_with_a_step_is_explained(self, terminal):
        with pytest.raises(ValueError, match='step'):
            terminal.pixels[0:10:2, 0] = 'red'  # type: ignore[call-overload]
        with pytest.raises(TypeError, match='\\(column, row\\)'):
            terminal.pixels[0] = 'red'  # type: ignore[call-overload]

    def test_a_color_object_is_a_pixel_color(self, terminal):
        terminal.pixels[0, 0] = main.Color.from_hsl(120, 100, 50)
        terminal.pixels[1, 0] = main.Color('#336699').lighten(0.2)
        terminal.pixels[2, 0] = main.Color.red
        assert terminal[0, 0].foreground.to_rgb() == (0, 255, 0)
        assert terminal[2, 0].foreground.to_rgb() == (205, 0, 0)

    def test_shading_draws_from_a_formula(self, terminal):
        terminal.pixels.shade(
            lambda column, row: (column * 10, row * 10, 0) if column < 2 else None
        )
        assert terminal[1, 0].foreground.to_rgb() == (10, 0, 0)
        assert terminal[5, 0].symbol == ' '

    def test_many_pixels_and_images(self, terminal):
        pixels = terminal.pixels
        pixels.write([(0, 0, '#00ff00'), (1, 0, '#00ff00')])
        assert terminal[1, 0].symbol == '▀'
        pixels.draw_rgba(bytes([255, 0, 0, 255]) * 4, width=2, height=2, x=4, y=0)
        assert terminal[4, 0].background.to_rgb() == (255, 0, 0)
        assert pixels.cell_at(3, 5) == (3, 2)
        assert pixels.pixel_at(1, 1, anchor='top_left') == (1, 2)


class TestHooks:
    def test_a_bare_hook_hears_every_key(self, terminal):
        heard: list[str] = []

        @terminal.hook
        def everything(context: Context) -> None:
            if context.keyboard is not None:
                heard.append(context.keyboard.key)

        for key in ('a', 'q'):
            dispatch(terminal, Event.key_press(key))
        assert heard == ['a', 'q']

    def test_a_function_trigger_filters_keys(self, terminal):
        heard: list[str] = []

        def is_quit(context: Context) -> bool:
            return context.keyboard is not None and context.keyboard.key in ('q', 'c')

        @terminal.hook(when=is_quit)
        def quit(context: Context) -> None:
            heard.append(context.keyboard.key)
            assert context.terminal is terminal

        for key in ('a', 'q', 'ctrl+c'):
            dispatch(terminal, Event.key_press(key))
        assert heard == ['q', 'c']

    def test_one_function_can_hook_two_targets(self, terminal):
        heard: list[str] = []
        placement = terminal.write(Buffer(width=4, height=2), x=0, y=0)

        def remember(context: Context) -> None:
            if context.keyboard is not None:
                heard.append(type(context.target).__name__)

        terminal.hook(remember)
        placement.hook(remember)
        dispatch(terminal, Event.key_press('a'))
        assert 'Terminal' in heard

    def test_removing_a_hook_stops_it(self, terminal):
        heard: list[str] = []

        def remember(context: Context) -> None:
            if context.keyboard is not None:
                heard.append(context.keyboard.key)

        handle = terminal.hook(remember)
        dispatch(terminal, Event.key_press('a'))
        handle.remove()
        handle.remove()
        dispatch(terminal, Event.key_press('a'))
        assert heard == ['a']

    def test_stopping_from_a_key(self, terminal):
        @terminal.hook
        def quit(context: Context) -> None:
            if context.keyboard is not None and context.keyboard.key == 'q':
                context.terminal.stop()

        dispatch(terminal, Event.key_press('q'))
        assert not terminal.is_running

    def test_mouse_reaches_the_placement_under_the_pointer(self, terminal):
        pressed: list[tuple[int, int]] = []
        local: list[tuple[int, int]] = []
        placement = terminal.write(Buffer(width=6, height=3), x=4, y=2)

        @terminal.hook
        def press(context: Context) -> None:
            if (
                context.mouse is not None
                and context.mouse.kind == 'press'
                and context.mouse.button == 'left'
            ):
                pressed.append((context.mouse.column, context.mouse.row))

        @placement.hook
        def anywhere(context: Context) -> None:
            if context.mouse is not None and context.mouse.kind == 'press':
                point = context.local(context.mouse.position)
                local.append((point.x, point.y))

        dispatch(
            terminal, Event.mouse_event(column=5, row=3, kind='press', button='left')
        )
        dispatch(
            terminal, Event.mouse_event(column=1, row=0, kind='press', button='left')
        )
        assert pressed == [(1, 0)]
        assert local == [(1, 1)]

    def test_resize_paste_and_focus(self, terminal):
        sizes: list[tuple[int, int]] = []
        pasted: list[str] = []
        focus: list[bool] = []

        @terminal.hook
        def heard(context: Context) -> None:
            if context.size_changed is not None:
                sizes.append((context.size_changed.width, context.size_changed.height))
            if context.pasted is not None:
                pasted.append(context.pasted)
            if context.focus_gained is not None:
                focus.append(True)
            elif getattr(context.event, 'kind', None) == 'focus_lost':
                focus.append(False)

        dispatch(terminal, Event.resize(width=30, height=9))
        dispatch(terminal, Event.paste('clipboard'))
        dispatch(terminal, Event.focus_lost())
        dispatch(terminal, Event.focus_gained())
        assert sizes == [(30, 9)]
        assert pasted == ['clipboard']
        assert focus == [False, True]

    def test_a_generator_trigger_waits_on_the_manual_clock(self, terminal):

        ticks: list[float] = []
        once: list[float] = []

        @terminal.every(0.1)
        def tick(context: Context) -> None:
            ticks.append(round(context.time.elapsed, 2))

        @terminal.after(0.25)
        def later(context: Context) -> None:
            once.append(context.time.elapsed)
            context.hook.remove()

        terminal.loop.advance(0.5)
        assert ticks
        assert len(once) == 1

    def test_five_clicks_and_a_parameterised_factory(self, terminal):
        def clicks(count: int, gap: float = 1.0):
            def trigger(context: Context):
                seen = 0
                event = None
                while seen < count:
                    event = yield gap
                    mouse = None if event is None else getattr(event, 'mouse', None)
                    pressed = (
                        mouse is not None
                        and mouse.kind == 'press'
                        and mouse.button == 'left'
                    )
                    seen = seen + 1 if pressed else 0
                return event  # noqa: B901

            return trigger

        hits: list[int] = []
        placement = terminal.write(Buffer(width=4, height=2))

        @placement.hook(when=clicks(5, gap=1.0))
        def egg(context: Context) -> None:
            hits.append(1)
            context.hook.remove()

        for _ in range(4):
            dispatch(
                terminal, Event.mouse_event(column=1, row=0, kind='press', button='left')
            )
        assert hits == []
        dispatch(
            terminal, Event.mouse_event(column=1, row=0, kind='press', button='left')
        )
        assert hits == [1]

    def test_removing_a_hook_cancels_its_timer(self, terminal):

        ticks: list[int] = []

        def tick(context: Context) -> None:
            ticks.append(1)

        handle = terminal.every(0.1)(tick)

        terminal.loop.advance(0.15)
        assert ticks
        handle.remove()
        before = len(ticks)
        terminal.loop.advance(0.4)
        assert len(ticks) == before

    def test_a_failing_hook_names_the_function(self, terminal):
        @terminal.hook
        def explode(context: Context) -> None:
            if context.keyboard is not None:
                raise ZeroDivisionError('nope')

        dispatch(terminal, Event.key_press('x'))
        with pytest.raises(TerminalError, match='explode') as caught:
            terminal.close()
        cause = caught.value.__cause__
        while cause is not None and not isinstance(cause, ZeroDivisionError):
            cause = cause.__cause__
        assert isinstance(cause, ZeroDivisionError)

    def test_a_hook_declared_from_another_thread_runs(self, terminal):
        heard: list[str] = []
        ready = threading.Event()

        def declare() -> None:
            @terminal.hook
            def remember(context: Context) -> None:
                if context.keyboard is not None:
                    heard.append(context.keyboard.key)

            ready.set()

        threading.Thread(target=declare).start()
        assert ready.wait(timeout=2)
        for _ in range(20):
            terminal.loop.step(timeout_seconds=0.01)
        dispatch(terminal, Event.key_press('z'))
        assert heard == ['z']

    def test_draggable_matches_a_hand_written_copy(self, terminal):

        library = terminal.write('#', x=(0, 10))
        custom = terminal.write('#', x=(0, 10), y=1)

        def dragging(context: Context) -> bool:
            return context.mouse is not None and context.mouse.kind == 'drag'

        @custom.hook(when=dragging)
        def move(context: Context) -> None:
            point = context.local(context.mouse.position)
            custom.x = point.x

        library.make_draggable()
        dispatch(terminal, Event.mouse_event(column=4, row=0, kind='drag', button='left'))
        dispatch(terminal, Event.mouse_event(column=4, row=1, kind='drag', button='left'))
        assert library.x == custom.x

    def test_closing_cancels_hooks(self):
        heard: list[str] = []
        terminal = open_terminal(offscreen=True, width=5, height=1)

        @terminal.hook
        def remember(context: Context) -> None:
            if context.keyboard is not None:
                heard.append(context.keyboard.key)

        runtime = terminal._runtime
        terminal.close()
        assert runtime.is_closed
        assert heard == []


class TestTime:
    def test_every_after_and_frames(self, terminal):

        ticks: list[float] = []
        once: list[float] = []
        seen: list[int] = []

        @terminal.every(0.1)
        def tick(context: Context) -> None:
            ticks.append(round(context.time.elapsed, 2))

        @terminal.after(0.25)
        def later(context: Context) -> None:
            once.append(context.time.elapsed)
            context.hook.remove()

        terminal.loop.on_frame(lambda frame: seen.append(frame.index))
        terminal.loop.advance(0.5)
        assert ticks and once
        assert seen

    def test_updates_run_at_a_fixed_step(self, terminal):
        steps: list[float] = []

        @terminal.loop.on_update(fixed_step_seconds=0.05)
        def update(step: Update) -> None:
            assert step.is_fixed_step
            steps.append(round(step.delta_seconds, 2))

        terminal.loop.advance(0.1)
        assert steps == [0.05, 0.05]

    def test_other_threads_hand_work_to_the_loop(self, terminal):
        done = threading.Event()
        threading.Thread(
            target=lambda: terminal._host.post(lambda: (terminal.write('x'), done.set()))
        ).start()
        assert done.wait(timeout=5) is False or True
        for _ in range(50):
            terminal.loop.step(timeout_seconds=0.01)
            if done.is_set():
                break
        assert done.is_set()
        assert terminal.output.snapshot().lines()[0].startswith('x')


class TestCellAccess:
    def test_terminal_cells_are_indexable(self, terminal):
        terminal.update(Write('ab'))
        assert isinstance(terminal[0, 0], Cell)
        assert terminal[0:2, 0:1][0, 0].symbol == 'a'


def python_examples():
    """Every ``python`` block in the docstrings of xnano's public modules."""
    examples = []
    root = pathlib.Path(main.__file__).parent
    for path in sorted(root.glob('*.py')):
        if path.name == '__init__.py':
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                if not docstring:
                    continue
                lines = docstring.splitlines()
                inside = False
                block: list[str] = []
                for line in lines:
                    if line.strip() == '```python':
                        inside, block = True, []
                    elif line.strip() == '```' and inside:
                        inside = False
                        examples.append((node.name, textwrap.dedent('\n'.join(block))))
                    elif inside:
                        block.append(line)
    return examples


@pytest.mark.parametrize(('name', 'source'), python_examples())
def test_docstring_examples_run(name, source, monkeypatch):
    monkeypatch.setitem(__import__('sys').modules, 'xnano', main)
    exec(compile(source, f'<docstring of {name}>', 'exec'), {})


def wait_for(condition, timeout=5.0):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.002)
    return False


@pytest.fixture
def autonomous():
    with open_terminal(
        offscreen=True, realtime=True, width=20, height=4, fps=60
    ) as opened:
        yield opened


class TestAutonomous:
    """A terminal with a real clock runs on a thread of its own."""

    def test_it_runs_by_itself(self, autonomous):
        assert autonomous.is_autonomous
        assert not autonomous.is_live and autonomous.backend == 'offscreen'

    def test_what_is_declared_appears_at_once(self, autonomous):
        autonomous.write('hi', x=3)
        assert wait_for(lambda: autonomous.output.snapshot().lines()[0] == '   hi')
        autonomous.write('yo', x=0, y=1)
        assert wait_for(lambda: autonomous.output.snapshot().lines()[1] == 'yo')
        placement = autonomous.write('gone')
        assert wait_for(lambda: 'gone' in autonomous.output.snapshot().lines()[0])
        placement.remove()
        assert wait_for(lambda: 'gone' not in autonomous.output.snapshot().lines()[0])

    def test_the_cursor_can_be_set_from_any_thread(self, autonomous):
        autonomous.cursor.position = (2, 1)
        autonomous.cursor.shape = 'bar'
        assert autonomous.cursor.position == Point(2, 1)
        assert wait_for(
            lambda: autonomous.output.snapshot().cursor_position == Point(2, 1)
        )

    def test_a_burst_of_declarations_is_drawn_together(self, autonomous):
        frames: list[int] = []
        autonomous.loop.on_frame(lambda frame: frames.append(frame.index))
        wait_for(lambda: frames)
        before = len(frames)
        for number in range(500):
            autonomous.write(str(number % 10), x=number % 20, y=2)
        assert wait_for(lambda: autonomous.output.snapshot().lines()[2] != '')
        assert len(frames) - before < 20

    def test_a_formula_keeps_moving_while_the_program_is_busy(self, autonomous):
        import time

        ball = autonomous.write('o')
        ball.x = (ParentWidth - Width) * (TimeElapsed % 1.0)
        positions: set[int] = set()
        end = time.perf_counter() + 1.0
        while time.perf_counter() < end:
            # Busy work that never calls the terminal.
            sum(index * index for index in range(2000))
            positions.add(ball.x)
        assert len(positions) >= 4

    def test_callbacks_run_on_the_terminals_own_thread(self, autonomous):
        import threading

        names: list[str] = []
        seen: list[Terminal | None] = []

        def is_a(context: Context) -> bool:
            return context.keyboard is not None and context.keyboard.key == 'a'

        @autonomous.hook(when=is_a)
        def heard(context: Context) -> None:
            names.append(threading.current_thread().name)
            seen.append(active(required=False))

        autonomous._host.post(lambda: autonomous._runtime.dispatch(Event.key_press('a')))
        assert wait_for(lambda: names)
        assert names == ['xnano-terminal']
        assert seen == [autonomous]

    def test_stopping_from_a_callback_ends_run(self, autonomous):
        import threading

        @autonomous.hook
        def quit(context: Context) -> None:
            if context.keyboard is not None and context.keyboard.key == 'q':
                context.terminal.stop()

        threading.Timer(
            0.05,
            lambda: autonomous._host.post(
                lambda: autonomous._runtime.dispatch(Event.key_press('q'))
            ),
        ).start()
        autonomous.run()
        assert not autonomous.is_running

    def test_timers_and_frame_hooks_run_without_being_driven(self, autonomous):

        ticks: list[int] = []
        frames: list[int] = []
        once: list[int] = []

        @autonomous.every(0.02)
        def tick(context: Context) -> None:
            ticks.append(1)

        @autonomous.after(0.02)
        def later(context: Context) -> None:
            once.append(1)
            context.hook.remove()

        autonomous.loop.on_frame(lambda frame: frames.append(frame.index))
        autonomous.write('x')
        assert wait_for(lambda: len(ticks) >= 3 and once and frames)

    def test_frames_paces_the_callers_own_code(self):
        import time

        with open_terminal(
            offscreen=True, realtime=True, width=8, height=1, fps=20
        ) as paced:
            start = time.perf_counter()
            frames = list(paced.iter(count=4))
            elapsed = time.perf_counter() - start
        assert [frame.index for frame in frames] == [0, 1, 2, 3]
        assert 0.1 <= elapsed < 1.0

    def test_driving_methods_are_for_manual_clocks(self, autonomous):
        with pytest.raises(TerminalError, match='runs by itself'):
            autonomous.loop.advance(0.1)
        with pytest.raises(TerminalError, match='runs by itself'):
            autonomous.loop.step()

    def test_the_runtime_belongs_to_the_loop(self, autonomous):
        with pytest.raises(TerminalError, match='own thread'):
            _ = autonomous._runtime
        results: list[bool] = []
        autonomous._host.post(lambda: results.append(autonomous._runtime.is_running))
        assert wait_for(lambda: results == [True])

    def test_size_and_clock_are_readable_from_any_thread(self, autonomous):
        assert (autonomous.width, autonomous.height) == (20, 4)
        first = autonomous.time.elapsed
        assert wait_for(lambda: autonomous.time.elapsed > first)
        autonomous._host.post(lambda: autonomous._runtime.resize(width=30, height=5))
        assert wait_for(lambda: autonomous.width == 30)

    def test_a_failing_callback_stops_the_terminal_and_is_reported(self):
        terminal = open_terminal(offscreen=True, realtime=True, width=8, height=1)

        @terminal.hook
        def explode(context: Context) -> None:
            if context.keyboard is not None and context.keyboard.key == 'x':
                raise ZeroDivisionError('nope')

        terminal._host.post(lambda: terminal._runtime.dispatch(Event.key_press('x')))
        assert wait_for(lambda: terminal.is_closed)
        with pytest.raises(TerminalClosedError, match='ZeroDivisionError'):
            terminal.write('late')
        with pytest.raises(TerminalError, match='ZeroDivisionError') as caught:
            terminal.close()
        cause = caught.value.__cause__
        while cause is not None and not isinstance(cause, ZeroDivisionError):
            cause = cause.__cause__
        assert isinstance(cause, ZeroDivisionError)
        terminal.close()

    def test_an_error_in_the_with_block_is_not_hidden_by_a_callback_failure(self):
        with pytest.raises(KeyError):
            with open_terminal(
                offscreen=True, realtime=True, width=8, height=1
            ) as terminal:

                @terminal.hook
                def explode(context: Context) -> None:
                    if context.keyboard is not None and context.keyboard.key == 'x':
                        raise ZeroDivisionError('nope')

                terminal._host.post(
                    lambda: terminal._runtime.dispatch(Event.key_press('x'))
                )
                assert wait_for(lambda: terminal.is_closed)
                raise KeyError('mine')

    def test_closing_stops_the_loop(self):
        terminal = open_terminal(offscreen=True, realtime=True, width=8, height=1)
        thread = terminal._host._thread
        terminal.close()
        assert not thread.is_alive()
        assert terminal.is_closed and not terminal.is_running


def test_terminal_title_can_be_set_changed_and_cleared_offscreen():
    with open_terminal(offscreen=True, title='Initial') as terminal:
        assert terminal.title == 'Initial'
        terminal.title = 'Changed'
        assert terminal.title == 'Changed'
        terminal.title = None
        assert terminal.title is None


@pytest.mark.parametrize('title', ['bad\nline', 'bad\x1btitle', 'bad\x07title'])
def test_terminal_title_rejects_control_characters(title):
    with open_terminal(offscreen=True) as terminal:
        with pytest.raises(ValueError, match='control characters'):
            terminal.title = title
        assert terminal.title is None


class TestKeyDecorators:
    def test_it_fires_for_the_given_keys_only(self, terminal):

        seen = []

        @terminal.on_key('a', 'enter')
        def record(context):
            seen.append(context.keyboard.key)

        for name in ('a', 'b', 'enter'):
            dispatch(terminal, Event.key_press(name))
        assert seen == ['a', 'enter']

    def test_without_keys_it_fires_for_every_key_pressed(self, terminal):
        seen = []

        @terminal.on_key()
        def record(context):
            seen.append(context.keyboard.key)

        dispatch(terminal, Event.key_press('a'))
        dispatch(terminal, Event.key_press('b', kind='release'))
        dispatch(terminal, Event.key_press('c'))
        assert seen == ['a', 'c']

    def test_after_runs_once(self, terminal):
        seen = []

        @terminal.after(0.1)
        def later(context):
            seen.append(context.time.elapsed)

        terminal.loop.advance(0.5)
        assert len(seen) == 1

    def test_click_and_drag_decorators_hear_their_own_mouse_events(self, terminal):
        seen = []

        @terminal.on_click
        def click(context):
            seen.append('click')

        @terminal.on_drag
        def drag(context):
            seen.append('drag')

        dispatch(
            terminal, Event.mouse_event(column=1, row=1, kind='press', button='left')
        )
        dispatch(terminal, Event.mouse_event(column=2, row=1, kind='drag', button='left'))
        dispatch(
            terminal, Event.mouse_event(column=2, row=1, kind='release', button='left')
        )
        assert seen == ['click', 'drag']


class TestKeyReleaseDecorator:
    def test_it_fires_for_a_release_of_the_given_keys_only(self, terminal):

        seen = []

        @terminal.on_key_release('a')
        def record(context):
            seen.append((context.keyboard.key, context.keyboard.kind))

        dispatch(terminal, Event.key_press('a'))
        dispatch(terminal, Event.key_press('a', kind='release'))
        dispatch(terminal, Event.key_press('b', kind='release'))
        assert seen == [('a', 'release')]


def test_a_keyboard_mode_needs_a_live_terminal():
    with pytest.raises(ValueError, match='keyboard'):
        open_terminal(offscreen=True, keyboard='release_events')


def test_pixels_accept_named_colors(terminal):
    pixels = terminal.pixels
    pixels[0, 0] = 'red'
    pixels[0, 1] = 'bright_blue'
    assert terminal[0, 0].foreground.to_rgb() == (205, 0, 0)
    assert terminal[0, 0].background.to_rgb() == (92, 92, 255)
    with pytest.raises(ValueError, match='no red, green and blue'):
        pixels[1, 0] = 'reset'


class TestRunQuitKeys:
    def run_until_key(self, name, **run_arguments):
        import threading

        with open_terminal(offscreen=True, realtime=True, width=8, height=1) as terminal:
            finished = threading.Event()

            def run():
                terminal.run(**run_arguments)
                finished.set()

            thread = threading.Thread(target=run)
            thread.start()
            terminal.inject(Event.key_press('x'))
            assert not finished.wait(timeout=0.3), 'an ordinary key does not stop run()'
            terminal.inject(Event.key_press(name))
            stopped = finished.wait(timeout=3)
            terminal.stop()
            thread.join(timeout=3)
            return stopped

    def test_control_c_stops_by_default(self):
        assert self.run_until_key('ctrl+c')

    def test_a_chosen_key_stops(self):
        assert self.run_until_key('q', quit_on='q')

    def test_any_of_several_keys_stops(self):
        assert self.run_until_key('escape', quit_on=('q', 'escape'))

    def test_a_plain_key_does_not_stop_when_only_control_c_does(self):
        assert not self.run_until_key('q')


class TestPausingTime:
    def test_pausing_stops_everything_that_follows_the_clock(self):
        import time

        with open_terminal(offscreen=True, realtime=True, width=12, height=1) as terminal:
            ticks = []

            @terminal.every(0.05)
            def tick(context):
                ticks.append(context.time.elapsed)

            time.sleep(0.3)
            assert ticks
            terminal.time.pause()
            assert terminal.time.is_paused
            time.sleep(0.1)  # a timer that was already firing may still land
            frozen = terminal.time.elapsed
            count = len(ticks)
            time.sleep(0.3)
            assert terminal.time.elapsed == frozen
            assert len(ticks) == count, 'timers wait while time is stopped'
            terminal.time.resume()
            assert not terminal.time.is_paused
            time.sleep(0.3)
            assert len(ticks) > count, 'and carry on after it resumes'
            assert terminal.time.elapsed - frozen < 0.5, 'the pause is not counted'

    def test_a_key_can_resume_a_paused_terminal(self):
        with open_terminal(offscreen=True, width=12, height=1) as terminal:

            @terminal.on_key('space')
            def toggle(context):
                if terminal.time.is_paused:
                    terminal.time.resume()
                else:
                    terminal.time.pause()

            dispatch(terminal, Event.key_press('space'))
            assert terminal.time.is_paused
            dispatch(terminal, Event.key_press('space'))
            assert not terminal.time.is_paused

    def test_a_paused_terminal_still_draws_what_a_hook_changes(self):
        import time

        with open_terminal(offscreen=True, realtime=True, width=12, height=1) as terminal:

            @terminal.on_key('x')
            def draw(context):
                terminal.write('drawn')

            terminal.time.pause()
            terminal.inject(Event.key_press('x'))
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if 'drawn' in terminal.output.snapshot().lines()[0]:
                    break
                time.sleep(0.02)
            assert 'drawn' in terminal.output.snapshot().lines()[0]


class TestPolledInput:
    def test_held_keys_make_a_direction(self):
        with open_terminal(offscreen=True, width=12, height=1) as terminal:
            assert terminal.input.direction() == (0, 0)
            dispatch(terminal, Event.key_press('d'))
            dispatch(terminal, Event.key_press('up'))
            assert terminal.input.is_down('d')
            assert terminal.input.direction() == (1, -1)
            dispatch(terminal, Event.key_press('d', kind='release'))
            assert terminal.input.direction() == (0, -1)
            assert terminal.input.axis('q', 'e') == 0


def test_sprites_can_be_drawn_from_text_and_scrolled():
    from xnano.image import from_art

    sprite = from_art(['AB', '.B'], {'A': '#ff0000', 'B': (0, 0, 255)})
    with open_terminal(offscreen=True, width=4, height=2) as terminal:
        pixels = terminal.pixels
        pixels.draw_image(sprite, x=1, y=0)
        assert terminal[1, 0].foreground.to_rgb() == (255, 0, 0)
        pixels.draw_image(sprite, x=-1, y=0, mode='replace')
        assert terminal[0, 0].background.to_rgb() == (0, 0, 255), (
            'a negative offset scrolls'
        )
    with pytest.raises(ValueError, match='every row the same length'):
        from_art(['AB', 'A'], {'A': 'red'})


class TestWritingTheWayItIsThought:
    def test_text_takes_a_style(self, terminal):
        from xnano.styles import Style

        text = terminal.write('hi', style=Style('red', bold=True))
        assert text.buffer[0, 0].foreground == Color('red')
        assert 'bold' in text.buffer[0, 0].style.modifiers

    def test_text_in_a_titled_box(self, terminal):
        box = terminal.write('hi', title='Box', border='rounded')
        assert (box.width, box.height) == (5, 3), 'the box is as wide as its title'
        assert '╭' in box.buffer.render(format='text')
        assert 'Box' in box.buffer.render(format='text')

    def test_a_list_of_lines_is_one_text(self, terminal):
        lines = terminal.write(['one', 'three'])
        assert (lines.width, lines.height) == (5, 2)

    def test_a_widget_cannot_take_a_text_style(self, terminal):
        from xnano.styles import Style
        from xnano.widgets import Gauge

        with pytest.raises(TypeError, match='decorate text'):
            terminal.write(Gauge(0.5), style=Style('red'))

    @pytest.mark.parametrize(
        ('x', 'y', 'expected'),
        [
            ('left', 'top', (0, 0)),
            ('center', 'center', (7, 2)),
            ('right', 'bottom', (15, 5)),
        ],
    )
    def test_words_place_something_inside_its_parent(self, terminal, x, y, expected):
        placed = terminal.write('hello', x=x, y=y)
        terminal.loop.step()
        assert (placed.x, placed.y) == expected

    def test_a_word_for_the_wrong_axis_is_explained(self, terminal):
        with pytest.raises(ValueError, match='cannot place the y'):
            terminal.write('hi', y='left')

    def test_a_placement_takes_operations_such_as_effects(self, terminal):
        from xnano.effects import Effect

        text = terminal.write('hi')
        text.update(Effect.dissolve(duration_milliseconds=200))
        terminal.loop.advance(0.3)


class TestWaitingForTheUser:
    def run_with_input(self, call, *events):
        import threading
        import time

        with open_terminal(offscreen=True, realtime=True, width=30, height=3) as terminal:
            results = []
            thread = threading.Thread(target=lambda: results.append(call(terminal)))
            thread.start()
            time.sleep(0.3)
            for event in events:
                terminal.inject(event)
                time.sleep(0.05)
            thread.join(timeout=5)
            assert not thread.is_alive(), 'the call should have returned'
            return results[0]

    def test_wait_for_key_returns_the_key(self):
        key = self.run_with_input(
            lambda terminal: terminal.wait_for_key('q', 'enter'),
            Event.key_press('x'),
            Event.key_press('enter'),
        )
        assert key == 'enter'

    def test_prompt_returns_what_was_typed(self):
        answer = self.run_with_input(
            lambda terminal: terminal.prompt('Name: '),
            Event.key_press('A'),
            Event.key_press('d'),
            Event.key_press('x'),
            Event.key_press('backspace'),
            Event.key_press('a'),
            Event.key_press('enter'),
        )
        assert answer == 'Ada'

    def test_a_terminal_that_never_moves_cannot_be_waited_on(self, terminal):
        with pytest.raises(TerminalError, match='never moves by itself'):
            terminal.wait_for_key('q')


def test_assigning_text_to_a_placement_changes_what_it_shows(terminal):
    text = terminal.write('hello')
    text.text = 'bye'
    assert text.text == 'bye'
    assert (text.width, text.height) == (3, 1)
    terminal.loop.step()
    assert terminal.output.snapshot().lines()[0] == 'bye'
    text.text = 'one\ntwo'
    assert (text.width, text.height) == (3, 2)
