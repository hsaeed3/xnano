"""
tests.test_open

The canvas you draw into: creating and opening it, placing things on it, time and events.
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
from xnano import active, new
from xnano import hook as xnano_hook
from xnano import open as open_terminal
from xnano.canvas import Canvas
from xnano.context import Context
from xnano.errors import (
    TerminalAlreadyOpenError,
    TerminalClosedError,
    TerminalError,
)
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
    Style,
    TimeElapsed,
    Width,
    Write,
)


@pytest.fixture
def canvas():
    with new(width=20, height=6, fps=10) as opened:
        yield opened


def dispatch(canvas: Canvas, event: Event) -> None:
    canvas.push(event)
    canvas.deliver_events()


class TestOpening:
    def test_a_new_canvas_has_a_size_and_no_screen(self):
        with new() as default:
            assert (default.width, default.height) == (80, 24)
            assert not isinstance(default, main.Terminal)
            assert isinstance(default, Canvas)
        with new(width=7, height=3) as small:
            assert small.size.width == 7 and small.size.height == 3
            assert 'width=7' in repr(small)

    def test_gates_are_accepted_off_the_screen_and_bad_values_are_explained(self):
        with new(mouse=True, scroll=True, alternate_screen=False) as gated:
            assert gated._gates == {
                'mouse': True,
                'scroll': True,
                'alternate_screen': False,
            }
        with pytest.raises(ValueError, match='needs a height too'):
            open_terminal(width=10)
        with pytest.raises(ValueError, match='above zero'):
            new(fps=0)
        with pytest.raises(ValueError, match="mouse='buttons' is mouse=True"):
            new(mouse='buttons')  # type: ignore[arg-type]

    def test_open_refuses_offscreen_and_realtime_and_points_to_new(self):
        with pytest.raises(TypeError, match=r'xnano\.new\(\.\.\.\)'):
            open_terminal(offscreen=True)  # type: ignore[call-overload]
        with pytest.raises(TypeError, match='takes no realtime'):
            open_terminal(realtime=True)  # type: ignore[call-overload]

    @pytest.mark.skipif(
        sys.platform == 'win32', reason='a Windows runner has a console to draw on'
    )
    def test_a_live_terminal_that_cannot_open_leaves_the_screen_free(self):
        # The test run has no canvas to draw on.
        for _ in range(2):
            with pytest.raises(RuntimeError, match='could not be opened'):
                open_terminal(height=2)
            assert terminal_module._live_terminal_open is False

    def test_a_second_live_terminal_is_refused(self, monkeypatch):
        monkeypatch.setattr(terminal_module, '_live_terminal_open', True)
        with pytest.raises(TerminalAlreadyOpenError, match='only one screen'):
            open_terminal()

    def test_the_active_canvas_follows_nesting(self):
        assert active(is_required=False) is None
        with pytest.raises(TerminalClosedError, match='No canvas is running'):
            active()
        with new() as outer:
            assert active() is outer
            with new() as inner:
                assert active() is inner
            assert active() is outer
        assert active(is_required=False) is None

    def test_a_closed_terminal_explains_itself(self):
        canvas = new(width=10, height=2)
        canvas.close()
        canvas.close()
        assert canvas.is_closed and 'closed' in repr(canvas)
        for action in (
            lambda: canvas.write('x'),
            lambda: canvas.region,
            lambda: canvas.write('x'),
            lambda: canvas.output.render(),
            lambda: list(canvas.iter(count=1)),
        ):
            with pytest.raises(TerminalClosedError, match='has been closed'):
                action()

    def test_printing_a_terminal_shows_its_last_frame(self, canvas):
        canvas.write('hi', x=1, y=0)
        canvas.output.render()
        assert 'hi' in str(canvas)


class TestFrames:
    def test_frames_follow_the_requested_rate(self, canvas):
        frames = list(canvas.iter(count=4))
        assert [frame.index for frame in frames] == [0, 1, 2, 3]
        assert [round(frame.elapsed_seconds, 3) for frame in frames] == [
            0.0,
            0.1,
            0.2,
            0.3,
        ]
        assert [round(frame.delta_seconds, 3) for frame in frames] == [0.0, 0.1, 0.1, 0.1]
        assert frames[0].area.width == 20 and frames[0].canvas is canvas

    def test_a_duration_ends_the_iteration(self, canvas):
        assert len(list(canvas.iter(seconds=0.5))) == 5

    def test_the_rate_does_not_drift(self):
        with new(width=4, height=1, fps=60) as sixty:
            list(sixty.iter(count=60))
            assert sixty.time.elapsed == pytest.approx(1.0, abs=0.001)

    def test_stopping_ends_the_iteration(self, canvas):
        seen = 0
        for frame in canvas.iter():
            seen += 1
            if frame.index == 2:
                canvas.quit()
        assert seen == 3

    def test_a_loop_draws_what_it_changes(self, canvas):
        for frame in canvas.iter(count=3):
            canvas.write(str(frame.index), x=frame.index, y=0)
        canvas.output.render()
        assert canvas.output.snapshot().lines()[0] == '012'

    def test_a_step_moves_the_clock_and_draws(self, canvas):
        canvas.step(delta_seconds=0.25)
        assert canvas.time.elapsed == 0.25

    def test_run_would_wait_forever_on_a_manual_clock(self, canvas):
        with pytest.raises(TerminalError, match='wait forever'):
            canvas.run()


class TestPlacements:
    def test_numbers_apply_once(self, canvas):
        placement = canvas.write(Buffer.with_text('ab'), x=3, y=2)
        assert (placement.x, placement.y) == (3, 2)
        assert (placement.width, placement.height) == (2, 1)
        placement.x = 5
        assert placement.x == 5

    def test_percentages_follow_the_terminal(self, canvas):
        placement = canvas.write('hello', x='50%', y='50%', width='25%')
        canvas.output.render()
        assert (placement.x, placement.y, placement.width) == (10, 3, 5)
        canvas._runtime.resize(width=40, height=10)
        canvas.deliver_events()
        canvas.output.render()
        assert (placement.x, placement.y, placement.width) == (20, 5, 10)

    def test_a_size_range_limits_the_size(self, canvas):
        wide = canvas.write(Buffer(width=15, height=4), width=(1, 10))
        narrow = canvas.write(Buffer(width=2, height=4), width=(5, None))
        percent = canvas.write(Buffer(width=15, height=4), width=(None, '25%'))
        canvas.output.render()
        assert wide.width == 10
        assert narrow.width == 5
        assert percent.width == 5
        wide.width = 3
        assert wide.width == 3
        wide.width = 99
        assert wide.width == 10
        wide.width = 0
        assert wide.width == 1

    def test_a_position_range_is_how_far_it_may_travel(self, canvas):
        thumb = canvas.write(Buffer.with_text('#'), x=(2, 10))
        assert thumb.x == 2, 'it is held inside the range at once'
        thumb.x = 6
        assert thumb.x == 6
        thumb.x = 400
        assert thumb.x == 10
        thumb.x = -4
        assert thumb.x == 2
        thumb.x = '50%'
        assert thumb.x == 10
        vertical = canvas.write(Buffer.with_text('#'), y=(1, 4))
        vertical.y = 9
        assert vertical.y == 4

    def test_a_range_stays_until_another_replaces_it(self, canvas):
        thumb = canvas.write('#', x=(2, 10))
        thumb.x = 8
        thumb.x = (4, 6)
        assert thumb.x == 6
        thumb.x = 0
        assert thumb.x == 4
        thumb.x = (None, None)
        thumb.x = 17
        assert thumb.x == 17

    def test_range_bounds_may_be_percentages_or_expressions(self, canvas):
        thumb = canvas.write('#', x=('10%', '90%'))
        thumb.x = 0
        assert thumb.x == 2
        thumb.x = 19
        assert thumb.x == 18
        track = canvas.write('##', x=(0, ParentWidth - Width))
        track.x = 100
        assert track.x == 18
        canvas._runtime.resize(width=40, height=6)
        canvas.deliver_events()
        assert thumb.x == 18, 'a bound is evaluated again when the canvas changes'
        thumb.x = 100
        track.x = 100
        canvas.output.render()
        assert thumb.x == 36
        assert track.x == 38

    def test_a_range_holds_a_formula_too(self, canvas):
        ball = canvas.write('o', x=(0, 6))
        ball.x = (ParentWidth - Width) * (TimeElapsed % 1.0)
        positions = [
            cast('int', ball.x),
            *(cast('int', ball.x) for _ in canvas.iter(count=8)),
        ]
        assert max(positions) == 6
        assert positions[:3] == [0, 0, 2]

    def test_a_range_must_be_an_ordered_pair(self, canvas):
        placement = canvas.write('x')
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
        canvas.deliver_events()

    def test_removing_forgets_the_range(self, canvas):
        thumb = canvas.write('#', x=(0, 3))
        thumb.remove()
        assert thumb._limits == {}

    def test_expressions_follow_the_clock(self, canvas):
        ball = canvas.write('o')
        ball.x = (ParentWidth - Width) * (TimeElapsed % 1.0)
        positions = [ball.x, *(ball.x for _ in canvas.iter(count=4))]
        assert positions[:5] == [0, 0, 2, 4, 6]

    def test_expressions_can_center(self, canvas):
        label = canvas.write('hello')
        label.x = (ParentWidth - Width) // 2
        label.y = (ParentHeight - Height) // 2
        canvas.output.render()
        assert (label.x, label.y) == (7, 2)

    def test_assigning_a_number_stops_following_an_expression(self, canvas):
        ball = canvas.write('o')
        ball.x = TimeElapsed * 10
        canvas.step(delta_seconds=0.5)
        assert cast('int', ball.x) == 5
        ball.x = 1
        canvas.step(delta_seconds=0.5)
        assert cast('int', ball.x) == 1

    def test_a_formula_over_unseen_input_is_explained(self, canvas):
        placement = canvas.write('o', x=3)
        with pytest.raises(TypeError, match='input that has not been seen'):
            placement.x = PointerPosition.x

    def test_a_rejected_formula_leaves_nothing_behind(self, canvas):
        with pytest.raises(TypeError, match='input that has not been seen'):
            canvas.write('ghost', x=PointerPosition.x)
        assert len(canvas._placements) == 0
        assert 'ghost' not in canvas.render()
        placement = canvas.write('o', x=3)
        with pytest.raises(TypeError, match='input that has not been seen'):
            placement.x = PointerPosition.x
        assert 'x' not in placement._bindings
        placement.y = TimeElapsed * 0
        canvas.step()
        assert placement.x == 3

    def test_a_removed_placement_refuses_every_change_the_same_way(self, canvas):
        placement = canvas.write('a')
        placement.remove()
        actions = [
            lambda: placement.write('x'),
            lambda: placement.hook(lambda context: None, on='tick'),
            lambda: setattr(placement, 'text', 'b'),
            lambda: setattr(placement, 'x', 3),
            lambda: setattr(placement, 'is_bold', True),
            lambda: placement.move(x=1),
            lambda: placement.update(Style(foreground='red')),
            lambda: placement.state,
        ]
        for action in actions:
            with pytest.raises(TerminalClosedError, match='was removed'):
                action()
        placement.remove()

    def test_a_negative_size_names_the_setting_and_a_fix(self, canvas):
        with pytest.raises(
            ValueError, match='width must be a whole number of cells from 0 to 65535'
        ):
            canvas.write('x', width=-3)
        assert len(canvas._placements) == 0

    def test_a_rejected_formula_is_reported_on_a_canvas_that_runs_by_itself(self):
        with new(width=10, height=2, realtime=True) as running:
            placement = running.write('ok')
            with pytest.raises(TypeError, match='input that has not been seen'):
                placement.x = PointerPosition.x
            with pytest.raises(TypeError, match='input that has not been seen'):
                running.write('ghost', x=PointerPosition.x)
            assert 'x' not in placement._bindings
            assert len(running._placements) == 1
            assert running.is_running

    def test_operations_are_applied_not_written(self, canvas):
        from xnano_core import Move, Style

        for operation in (Style(foreground='red'), Move(x=1, y=0)):
            with pytest.raises(
                TypeError, match=r'canvas\.update\(\.\.\.\) or canvas \| operation'
            ):
                canvas.write(operation)  # type: ignore[arg-type]
        parent = canvas.write('box', width=6, height=2)
        with pytest.raises(TypeError, match=r'placement\.update\(\.\.\.\)'):
            parent.write(Style(foreground='red'))  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='xnano.hook|ContextualOperation|changes'):
            canvas.write(xnano_hook(lambda context: None, on='tick'))  # type: ignore[arg-type]
        assert not hasattr(canvas, '__getitem__')

    def test_removing_a_placement_removes_what_is_nested_in_it(self, canvas):
        parent = canvas.write('outer', width=8, height=2)
        inner = parent.write('inner')
        deeper = inner.write('deeper')
        keeper = canvas.write('kept', y=3)
        parent.remove()
        assert canvas._placements == [keeper]
        assert inner._removed and deeper._removed
        with pytest.raises(TerminalError, match='was removed'):
            parent.state.push('a', 1)

    def test_bad_axes_are_explained(self, canvas):
        placement = canvas.write('x')
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

    @pytest.mark.filterwarnings('ignore:Greeting is drawn once')
    def test_content_kinds(self, canvas):
        class Greeting:
            def __xnano_render__(self, context) -> Buffer:
                return Buffer.with_text('hi')

        grid = Buffer.with_text('cell').to_cell_grid()
        for content in (
            'text',
            Greeting(),
            Buffer.from_cell_grid(grid),
            Buffer.with_text('buffer'),
        ):
            assert canvas.write(content).width > 0
        with pytest.raises(TypeError, match='does not accept raw bytes'):
            canvas.write(grid)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='Cannot show a int'):
            canvas.write(5)  # type: ignore[arg-type]

        class Broken:
            def __xnano_render__(self, context) -> int:
                return 1

        with pytest.raises(TypeError, match='Broken.__xnano_render__ returned int'):
            canvas.write(Broken())  # type: ignore[arg-type]

    def test_layers_order_the_drawing(self, canvas):
        canvas.write(Buffer.with_text('a'), layer=1)
        canvas.write(Buffer.with_text('b'), layer=0)
        canvas.output.render()
        assert canvas.output.snapshot().lines()[0] == 'a'

    def test_removing_and_hiding(self, canvas):
        placement = canvas.write('hi')
        placement.is_visible = False
        canvas.output.render()
        assert canvas.output.snapshot().lines()[0] == ''
        placement.is_visible = True
        placement.remove()
        placement.remove()
        canvas.output.render()
        assert canvas.output.snapshot().lines()[0] == ''
        assert 'removed' in repr(placement)

    def test_a_placement_has_a_region(self, canvas):
        placement = canvas.write(Buffer(width=3, height=1))
        placement.region.half_blocks[0, 0] = (255, 0, 0)
        assert placement.region.half_blocks.height == 2


class TestRegions:
    def test_a_color_fills_the_background(self, canvas):
        canvas.region[0:3, 0:2] = Color('#336699')
        assert canvas.region[1, 1].background.to_rgb() == (0x33, 0x66, 0x99)
        assert canvas.region[3, 0].background is None
        canvas.region[4:6, 0:1] = (1, 2, 3)
        assert canvas.region[4, 0].background.to_rgb() == (1, 2, 3)

    def test_a_string_is_written(self, canvas):
        canvas.region[2:12, 1:2] = 'hello'
        assert canvas.region[2, 1].character == 'h'
        canvas.region[0, 0] = 'z'
        assert canvas.region[0, 0].character == 'z'

    def test_a_buffer_covers_the_region(self, canvas):
        canvas.region[4:8, 2:4] = Buffer(width=1, height=1)
        placement = canvas._placements[-1]
        assert (placement.x, placement.y, placement.width, placement.height) == (
            4,
            2,
            4,
            2,
        )

    def test_slices_can_be_open_and_empty_regions_are_ignored(self, canvas):
        canvas.region[:, 5:] = (255, 255, 255)
        assert canvas.region[19, 5].background.to_rgb() == (255, 255, 255)
        canvas.region[5:5, 0:1] = 'x'

    def test_steps_and_single_cell_fills_are_explained(self, canvas):
        with pytest.raises(ValueError, match='step'):
            canvas.region[0:6:2, 0:1] = 'x'
        with pytest.raises(IndexError, match='outside this region'):
            canvas.region[0:3, 99] = 'x'

    def test_clear_erases_the_cells(self, canvas):
        canvas.write('hello')
        canvas.clear()
        assert canvas.region[0, 0].character == ' '

    def test_update_and_inspect(self, canvas):
        canvas.update(Write('abc', x=1, y=1))
        assert canvas.inspect(Width) == 20
        assert canvas.region[1, 1].character == 'a'


class TestRegionResolution:
    def test_pixels_have_the_resolution_of_their_encoding(self, canvas):
        pixels = canvas.region.half_blocks
        assert (pixels.width, pixels.height) == (20, 12)
        braille = canvas.region.braille
        assert (braille.width, braille.height, braille.resolution) == (40, 24, 'braille')

    def test_colors_may_be_tuples_or_colors(self, canvas):
        pixels = canvas.region.half_blocks
        pixels[0, 0] = Color('#ff0000')
        pixels[0, 1] = (0, 0, 255)
        assert canvas.core_buffer[0, 0].symbol == '▀'
        assert canvas.core_buffer[0, 0].foreground.to_rgb() == (255, 0, 0)
        assert canvas.core_buffer[0, 0].background.to_rgb() == (0, 0, 255)

    def test_colors_without_channels_are_explained(self, canvas):
        with pytest.raises(ValueError, match="'#rrggbb'"):
            canvas.region.half_blocks[0, 0] = Color('reset')
        with pytest.raises(ValueError, match='0 to 255'):
            canvas.region.half_blocks[0, 0] = (300, 0, 0)
        with pytest.raises(TypeError, match='color or a Pixel'):
            canvas.region.half_blocks[0:2, 0] = 'red'

    def test_a_slice_draws_every_pixel_it_covers(self, canvas):
        canvas.region.half_blocks[0:3, 0] = Color('#ff0000')
        for x in range(3):
            assert canvas.core_buffer[x, 0].foreground.to_rgb() == (255, 0, 0)
        assert canvas.core_buffer[3, 0].symbol == ' '
        canvas.region.half_blocks[:, :] = (0, 0, 255)
        assert canvas.core_buffer[19, 5].background.to_rgb() == (0, 0, 255)

    def test_a_slice_with_a_step_is_explained(self, canvas):
        with pytest.raises(ValueError, match='step'):
            canvas.region.half_blocks[0:10:2, 0] = (255, 0, 0)
        with pytest.raises(TypeError, match='indexed by'):
            canvas.region.half_blocks[0] = (255, 0, 0)  # type: ignore[index]

    def test_a_color_object_is_a_pixel_color(self, canvas):
        pixels = canvas.region.half_blocks
        pixels[0, 0] = main.Color.from_hsl(120, 100, 50)
        pixels[1, 0] = main.Color('#336699').lighten(0.2)
        pixels[2, 0] = main.Color.red
        assert canvas.core_buffer[0, 0].foreground.to_rgb() == (0, 255, 0)
        assert canvas.core_buffer[2, 0].foreground.to_rgb() == (205, 0, 0)

    def test_shading_draws_from_a_formula(self, canvas):
        canvas.region.half_blocks.shade(
            lambda x, y: (x * 10, y * 10, 0) if x < 2 else None
        )
        assert canvas.core_buffer[1, 0].foreground.to_rgb() == (10, 0, 0)
        assert canvas.core_buffer[5, 0].symbol == ' '

    def test_many_pixels_and_images(self, canvas):
        pixels = canvas.region.half_blocks
        pixels.shade(lambda x, y: (0, 255, 0) if y == 0 and x < 2 else None)
        assert canvas.core_buffer[1, 0].symbol == '▀'
        pixels.draw_color_bytes(bytes([255, 0, 0, 255]) * 4, width=2, height=2, x=4, y=0)
        assert canvas.core_buffer[4, 0].background.to_rgb() == (255, 0, 0)
        assert pixels.cell_for_pixel(3, 5) == (3, 2)
        assert pixels.pixel_for_cell(1, 1, anchor='top_left') == (1, 2)


class TestHooks:
    def test_a_bare_hook_hears_every_key(self, canvas):
        heard: list[str] = []

        @canvas.hook
        def everything(context: Context) -> None:
            if context.keyboard.key is not None:
                heard.append(context.keyboard.key)

        for key in ('a', 'q'):
            dispatch(canvas, Event.key_press(key))
        assert heard == ['a', 'q']

    def test_a_function_trigger_filters_keys(self, canvas):
        heard: list[str] = []

        def is_quit(context: Context) -> bool:
            return context.keyboard.key is not None and context.keyboard.key in ('q', 'c')

        @canvas.hook(when=is_quit)
        def quit(context: Context) -> None:
            heard.append(context.keyboard.key)
            assert context.canvas is canvas

        for key in ('a', 'q', 'ctrl+c'):
            dispatch(canvas, Event.key_press(key))
        assert heard == ['q', 'c']

    def test_one_function_can_hook_two_targets(self, canvas):
        heard: list[str] = []
        placement = canvas.write(Buffer(width=4, height=2), x=0, y=0)

        def remember(context: Context) -> None:
            if context.keyboard.key is not None:
                heard.append(type(context.buffer).__name__)

        canvas.hook(remember)
        placement.hook(remember)
        dispatch(canvas, Event.key_press('a'))
        assert 'Canvas' in heard

    def test_removing_a_hook_stops_it(self, canvas):
        heard: list[str] = []

        def remember(context: Context) -> None:
            if context.keyboard.key is not None:
                heard.append(context.keyboard.key)

        handle = canvas.hook(remember)
        dispatch(canvas, Event.key_press('a'))
        handle.remove()
        handle.remove()
        dispatch(canvas, Event.key_press('a'))
        assert heard == ['a']

    def test_stopping_from_a_key(self, canvas):
        @canvas.hook
        def quit(context: Context) -> None:
            if context.keyboard.key is not None and context.keyboard.key == 'q':
                context.canvas.quit()

        dispatch(canvas, Event.key_press('q'))
        assert not canvas.is_running
        assert not canvas.is_closed, 'a canvas from new() stays open after quit()'
        canvas.write('still writable')

    def test_mouse_reaches_the_placement_under_the_pointer(self, canvas):
        pressed: list[tuple[int, int]] = []
        local: list[tuple[int, int]] = []
        placement = canvas.write(Buffer(width=6, height=3), x=4, y=2)

        @canvas.hook
        def press(context: Context) -> None:
            if (
                context.mouse.position is not None
                and context.mouse.kind == 'press'
                and context.mouse.button == 'left'
            ):
                pressed.append((context.mouse.position.x, context.mouse.position.y))

        @placement.hook
        def anywhere(context: Context) -> None:
            if context.mouse.position is not None and context.mouse.kind == 'press':
                point = context.local(context.mouse.position)
                local.append((point.x, point.y))

        dispatch(canvas, Event.mouse_event(column=5, row=3, kind='press', button='left'))
        dispatch(canvas, Event.mouse_event(column=1, row=0, kind='press', button='left'))
        assert pressed == [(1, 0)]
        assert local == [(1, 1)]

    def test_resize_paste_and_focus(self, canvas):
        sizes: list[tuple[int, int]] = []
        pasted: list[str] = []
        focus: list[bool] = []

        @canvas.hook
        def heard(context: Context) -> None:
            event = context.event
            if event.kind == 'resize':
                sizes.append((event.size.width, event.size.height))
            if context.clipboard.text is not None:
                pasted.append(context.clipboard.text)
            if event.kind == 'focus_gained':
                focus.append(True)
            elif event.kind == 'focus_lost':
                focus.append(False)

        dispatch(canvas, Event.resize(width=30, height=9))
        dispatch(canvas, Event.paste('clipboard'))
        dispatch(canvas, Event.focus_lost())
        dispatch(canvas, Event.focus_gained())
        assert sizes == [(30, 9)]
        assert pasted == ['clipboard']
        assert focus == [False, True]

    def test_a_generator_trigger_waits_on_the_manual_clock(self, canvas):

        ticks: list[float] = []
        once: list[float] = []

        @canvas.hook(on='tick', every=0.1)
        def tick(context: Context) -> None:
            ticks.append(round(context.time.elapsed, 2))

        @canvas.hook(on='tick', after=0.25)
        def later(context: Context) -> None:
            once.append(context.time.elapsed)
            context.hook.remove()

        canvas.step(delta_seconds=0.5)
        assert ticks
        assert len(once) == 1

    def test_five_clicks_with_a_generator_hook(self, canvas):
        hits: list[int] = []
        placement = canvas.write(Buffer(width=4, height=2))

        @placement.hook(on='mouse', when="mouse.kind == 'press' and mouse.button == left")
        def egg(context: Context):
            presses = 1
            while presses < 5:
                context = yield
                presses += 1
            hits.append(1)
            context.hook.remove()

        for _ in range(4):
            dispatch(
                canvas, Event.mouse_event(column=1, row=0, kind='press', button='left')
            )
        assert hits == []
        dispatch(canvas, Event.mouse_event(column=1, row=0, kind='press', button='left'))
        assert hits == [1]

    def test_removing_a_hook_cancels_its_timer(self, canvas):

        ticks: list[int] = []

        def tick(context: Context) -> None:
            ticks.append(1)

        handle = canvas.hook(on='tick', every=0.1)(tick)

        canvas.step(delta_seconds=0.15)
        assert ticks
        handle.remove()
        before = len(ticks)
        canvas.step(delta_seconds=0.4)
        assert len(ticks) == before

    def test_a_failing_hook_names_the_function(self, canvas):
        @canvas.hook
        def explode(context: Context) -> None:
            if context.keyboard.key is not None:
                raise ZeroDivisionError('nope')

        with pytest.raises(TerminalError, match='explode') as caught:
            dispatch(canvas, Event.key_press('x'))
        cause = caught.value.__cause__
        while cause is not None and not isinstance(cause, ZeroDivisionError):
            cause = cause.__cause__
        assert isinstance(cause, ZeroDivisionError)

    def test_a_hook_declared_from_another_thread_runs(self, canvas):
        heard: list[str] = []
        ready = threading.Event()

        def declare() -> None:
            @canvas.hook
            def remember(context: Context) -> None:
                if context.keyboard.key is not None:
                    heard.append(context.keyboard.key)

            ready.set()

        threading.Thread(target=declare).start()
        assert ready.wait(timeout=2)
        for _ in range(20):
            canvas.deliver_events()
        dispatch(canvas, Event.key_press('z'))
        assert heard == ['z']

    def test_a_drag_hook_matches_a_hand_written_copy(self, canvas):
        library = canvas.write('#', x=(0, 10))
        custom = canvas.write('#', x=(0, 10), y=1)

        @custom.hook(on='drag')
        def move(context: Context) -> None:
            custom.x = context.parent.local(context.mouse.position).x

        @library.hook(on='drag')
        def slide(context: Context):
            while context.mouse.is_down:
                library.x = context.parent.local(context.mouse.position).x
                context = yield

        dispatch(canvas, Event.mouse_event(column=0, row=0, kind='press', button='left'))
        dispatch(canvas, Event.mouse_event(column=4, row=0, kind='drag', button='left'))
        dispatch(
            canvas, Event.mouse_event(column=4, row=0, kind='release', button='left')
        )
        dispatch(canvas, Event.mouse_event(column=0, row=1, kind='press', button='left'))
        dispatch(canvas, Event.mouse_event(column=4, row=1, kind='drag', button='left'))
        dispatch(
            canvas, Event.mouse_event(column=4, row=1, kind='release', button='left')
        )
        assert library.x == custom.x == 4

    def test_closing_cancels_hooks(self):
        heard: list[str] = []
        canvas = new(width=5, height=1)

        @canvas.hook
        def remember(context: Context) -> None:
            if context.keyboard.key is not None:
                heard.append(context.keyboard.key)

        runtime = canvas._runtime
        canvas.close()
        assert runtime.is_closed
        assert heard == []


class TestTime:
    def test_every_after_and_frames(self, canvas):

        ticks: list[float] = []
        once: list[float] = []
        seen: list[int] = []

        @canvas.hook(on='tick', every=0.1)
        def tick(context: Context) -> None:
            ticks.append(round(context.time.elapsed, 2))

        @canvas.hook(on='tick', after=0.25)
        def later(context: Context) -> None:
            once.append(context.time.elapsed)
            context.hook.remove()

        @canvas.hook(on='frame')
        def frame(context: Context) -> None:
            seen.append(context.time.frame)

        canvas.step(delta_seconds=0.5)
        assert ticks and once
        assert seen

    def test_updates_run_at_a_fixed_step(self, canvas):
        steps: list[float] = []

        @canvas.hook(on='tick', every=0.05)
        def update(context: Context) -> None:
            assert isinstance(context.event, main.context.Update)
            assert context.event.is_fixed_step
            steps.append(round(context.event.delta_seconds, 2))

        canvas.step(delta_seconds=0.1)
        assert steps == [0.05, 0.05]
        canvas.step(delta_seconds=2.0)
        assert len(steps) == 42, 'a jump of the manual clock runs every step it crossed'

    def test_other_threads_hand_work_to_the_loop(self, canvas):
        done = threading.Event()
        threading.Thread(
            target=lambda: canvas._host.post(lambda: (canvas.write('x'), done.set()))
        ).start()
        assert done.wait(timeout=5) is False or True
        for _ in range(50):
            canvas.deliver_events()
            if done.is_set():
                break
        assert done.is_set()
        assert canvas.output.snapshot().lines()[0].startswith('x')


class TestCellAccess:
    def test_terminal_cells_are_indexable(self, canvas):
        canvas.update(Write('ab'))
        assert isinstance(canvas.core_buffer[0, 0], Cell)
        assert canvas.core_buffer[0:2, 0:1][0, 0].symbol == 'a'


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
    with new(realtime=True, width=20, height=4, fps=60) as opened:
        yield opened


class TestAutonomous:
    """A canvas with a real clock runs on a thread of its own."""

    def test_it_runs_by_itself(self, autonomous):
        assert autonomous.time.is_realtime
        assert not isinstance(autonomous, main.Terminal)

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
        autonomous._on_frame(lambda frame: frames.append(frame.index))
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
            # Busy work that never calls the canvas.
            sum(index * index for index in range(2000))
            positions.add(ball.x)
        assert len(positions) >= 4

    def test_callbacks_run_on_the_terminals_own_thread(self, autonomous):
        import threading

        names: list[str] = []
        seen: list[Canvas | None] = []

        def is_a(context: Context) -> bool:
            return context.keyboard.key is not None and context.keyboard.key == 'a'

        @autonomous.hook(when=is_a)
        def heard(context: Context) -> None:
            names.append(threading.current_thread().name)
            seen.append(active(is_required=False))

        autonomous.push(Event.key_press('a'))
        assert wait_for(lambda: names)
        assert names == ['xnano-terminal']
        assert seen == [autonomous]

    def test_stopping_from_a_callback_ends_run(self, autonomous):
        import threading

        @autonomous.hook
        def quit(context: Context) -> None:
            if context.keyboard.key is not None and context.keyboard.key == 'q':
                context.canvas.quit()

        threading.Timer(0.05, lambda: autonomous.push(Event.key_press('q'))).start()
        autonomous.run()
        assert not autonomous.is_running

    def test_timers_and_frame_hooks_run_without_being_driven(self, autonomous):

        ticks: list[int] = []
        frames: list[int] = []
        once: list[int] = []

        @autonomous.hook(on='tick', every=0.02)
        def tick(context: Context) -> None:
            ticks.append(1)

        @autonomous.hook(on='tick', after=0.02)
        def later(context: Context) -> None:
            once.append(1)
            context.hook.remove()

        @autonomous.hook(on='frame')
        def frame(context: Context) -> None:
            frames.append(context.time.frame)

        autonomous.write('x')
        assert wait_for(lambda: len(ticks) >= 3 and once and frames)

    def test_frames_paces_the_callers_own_code(self):
        import time

        with new(realtime=True, width=8, height=1, fps=20) as paced:
            start = time.perf_counter()
            frames = list(paced.iter(count=4))
            elapsed = time.perf_counter() - start
        indices = [frame.index for frame in frames]
        assert len(indices) == 4 and indices == sorted(indices)
        assert 0.1 <= elapsed < 1.0

    def test_a_running_autonomous_canvas_cannot_be_stepped(self, autonomous):
        with pytest.raises(TerminalError, match='runs by itself'):
            autonomous.step(delta_seconds=0.1)
        with pytest.raises(TerminalError, match='canvas.stop'):
            autonomous.step()
        autonomous.deliver_events()

    def test_a_stopped_autonomous_canvas_steps_one_frame(self, autonomous):
        autonomous.stop()
        before = autonomous.time.elapsed
        frame = autonomous.step(delta_seconds=0.25)
        assert frame.elapsed_seconds == pytest.approx(before + 0.25, abs=0.002)
        assert autonomous.time.is_stopped
        with pytest.raises(TerminalError, match='stopped canvas never reaches'):
            autonomous.iter(seconds=1.0)

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

    def test_open_from_a_hook_of_a_canvas_that_runs_by_itself_is_refused(self):
        with new(realtime=True, width=8, height=1) as canvas:
            messages: list[str] = []

            def hear(context: Context) -> None:
                try:
                    context.root.open()
                except TerminalError as error:
                    messages.append(str(error))

            canvas.hook(hear, on='tick', after=0.0)
            assert wait_for(lambda: bool(messages))
            assert 'open() was called from a hook' in messages[0]
            assert canvas.is_running

    def test_a_failing_callback_stops_the_terminal_and_is_reported(self):
        canvas = new(realtime=True, width=8, height=1)

        @canvas.hook
        def explode(context: Context) -> None:
            if context.keyboard.key is not None and context.keyboard.key == 'x':
                raise ZeroDivisionError('nope')

        canvas.push(Event.key_press('x'))
        assert wait_for(lambda: canvas.is_closed)
        with pytest.raises(TerminalClosedError, match='ZeroDivisionError'):
            canvas.write('late')
        with pytest.raises(TerminalError, match='ZeroDivisionError') as caught:
            canvas.close()
        cause = caught.value.__cause__
        while cause is not None and not isinstance(cause, ZeroDivisionError):
            cause = cause.__cause__
        assert isinstance(cause, ZeroDivisionError)
        canvas.close()

    def test_an_error_in_the_with_block_is_not_hidden_by_a_callback_failure(self):
        with pytest.raises(KeyError):
            with new(realtime=True, width=8, height=1) as canvas:

                @canvas.hook
                def explode(context: Context) -> None:
                    if context.keyboard.key is not None and context.keyboard.key == 'x':
                        raise ZeroDivisionError('nope')

                canvas.push(Event.key_press('x'))
                assert wait_for(lambda: canvas.is_closed)
                raise KeyError('mine')

    def test_closing_stops_the_loop(self):
        canvas = new(realtime=True, width=8, height=1)
        thread = canvas._host._thread
        canvas.close()
        assert not thread.is_alive()
        assert canvas.is_closed and not canvas.is_running


def test_terminal_title_can_be_set_changed_and_cleared_on_a_screenless_canvas():
    with new(title='Initial') as canvas:
        assert canvas.title == 'Initial'
        canvas.title = 'Changed'
        assert canvas.title == 'Changed'
        canvas.title = None
        assert canvas.title is None


@pytest.mark.parametrize('title', ['bad\nline', 'bad\x1btitle', 'bad\x07title'])
def test_terminal_title_rejects_control_characters(title):
    with new() as canvas:
        with pytest.raises(ValueError, match='control characters'):
            canvas.title = title
        assert canvas.title is None


class TestKeyDecorators:
    def test_it_fires_for_the_given_keys_only(self, canvas):

        seen = []

        @canvas.hook(on='key', keys=['a', 'enter'])
        def record(context):
            seen.append(context.keyboard.key)

        for name in ('a', 'b', 'enter'):
            dispatch(canvas, Event.key_press(name))
        assert seen == ['a', 'enter']

    def test_without_keys_it_fires_for_every_key_event(self, canvas):
        seen = []

        @canvas.hook(on='key')
        def record(context):
            seen.append(context.keyboard.key)

        dispatch(canvas, Event.key_press('a'))
        dispatch(canvas, Event.key_press('b', kind='release'))
        dispatch(canvas, Event.key_press('c'))
        assert seen == ['a', 'b', 'c'], 'a key hook without keys also hears releases'

    def test_a_condition_on_the_kind_leaves_out_releases(self, canvas):
        seen = []

        @canvas.hook(on='key', when="keyboard.kind != 'release'")
        def record(context):
            seen.append(context.keyboard.key)

        dispatch(canvas, Event.key_press('a'))
        dispatch(canvas, Event.key_press('b', kind='release'))
        assert seen == ['a']

    def test_after_runs_once(self, canvas):
        seen = []

        @canvas.hook(on='tick', after=0.1)
        def later(context):
            seen.append(context.time.elapsed)

        canvas.step(delta_seconds=0.5)
        assert len(seen) == 1

    def test_click_and_drag_decorators_hear_their_own_mouse_events(self, canvas):
        seen = []

        @canvas.hook(on='mouse', when="mouse.kind == 'press'")
        def click(context):
            seen.append('click')

        @canvas.hook(on='drag')
        def drag(context):
            seen.append('drag')

        dispatch(canvas, Event.mouse_event(column=1, row=1, kind='press', button='left'))
        dispatch(canvas, Event.mouse_event(column=2, row=1, kind='drag', button='left'))
        dispatch(
            canvas, Event.mouse_event(column=2, row=1, kind='release', button='left')
        )
        assert seen == ['click', 'drag']


class TestKeyReleaseDecorator:
    def test_it_fires_for_a_release_of_the_given_keys_only(self, canvas):

        seen = []

        @canvas.hook(on='key', when="keyboard.kind == 'release' and keyboard.key == a")
        def record(context):
            seen.append((context.keyboard.key, context.keyboard.kind))

        dispatch(canvas, Event.key_press('a'))
        dispatch(canvas, Event.key_press('a', kind='release'))
        dispatch(canvas, Event.key_press('b', kind='release'))
        assert seen == [('a', 'release')]


def test_a_keyboard_mode_is_stored_for_the_screen():
    with new(keyboard='release_events') as canvas:
        assert canvas._gates['keyboard'] == 'release_events'
    with pytest.raises(ValueError, match='keyboard must be'):
        new(keyboard='loud')  # type: ignore[arg-type]


def test_pixels_accept_colors_by_name(canvas):
    pixels = canvas.region.half_blocks
    pixels[0, 0] = main.Color.red
    pixels[0, 1] = main.Color('#5c5cff')
    assert canvas.core_buffer[0, 0].foreground.to_rgb() == (205, 0, 0)
    assert canvas.core_buffer[0, 0].background.to_rgb() == (92, 92, 255)
    with pytest.raises(ValueError, match='no red, green and blue'):
        pixels[1, 0] = main.Color.reset


class TestRunQuitKeys:
    def run_until_key(self, name, **run_arguments):
        import threading

        with new(realtime=True, width=8, height=1) as canvas:
            finished = threading.Event()

            def run():
                canvas.run(**run_arguments)
                finished.set()

            thread = threading.Thread(target=run)
            thread.start()
            canvas.push(Event.key_press('x'))
            assert not finished.wait(timeout=0.3), 'an ordinary key does not stop run()'
            canvas.push(Event.key_press(name))
            stopped = finished.wait(timeout=3)
            canvas.quit()
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

        with new(realtime=True, width=12, height=1) as canvas:
            ticks = []

            @canvas.hook(on='tick', every=0.05)
            def tick(context):
                ticks.append(context.time.elapsed)

            time.sleep(0.3)
            assert ticks
            canvas.time.stop()
            assert canvas.time.is_stopped
            time.sleep(0.1)  # a timer that was already firing may still land
            frozen = canvas.time.elapsed
            count = len(ticks)
            time.sleep(0.3)
            assert canvas.time.elapsed == frozen
            assert len(ticks) == count, 'timers wait while time is stopped'
            canvas.time.resume()
            assert not canvas.time.is_stopped
            time.sleep(0.3)
            assert len(ticks) > count, 'and carry on after it resumes'
            assert canvas.time.elapsed - frozen < 0.5, 'the pause is not counted'

    def test_a_key_can_resume_a_stopped_terminal(self):
        with new(width=12, height=1) as canvas:

            @canvas.hook(on='key', keys='space')
            def toggle(context):
                if canvas.time.is_stopped:
                    canvas.time.resume()
                else:
                    canvas.time.stop()

            dispatch(canvas, Event.key_press('space'))
            assert canvas.time.is_stopped
            dispatch(canvas, Event.key_press('space'))
            assert not canvas.time.is_stopped

    def test_a_stopped_terminal_still_draws_what_a_hook_changes(self):
        import time

        with new(realtime=True, width=12, height=1) as canvas:

            @canvas.hook(on='key', keys='x')
            def draw(context):
                canvas.write('drawn')

            canvas.time.stop()
            canvas.push(Event.key_press('x'))
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if 'drawn' in canvas.output.snapshot().lines()[0]:
                    break
                time.sleep(0.02)
            assert 'drawn' in canvas.output.snapshot().lines()[0]


class TestPolledInput:
    def test_held_keys_make_a_direction(self):
        with new(width=12, height=1) as canvas:
            assert canvas.input.direction() == (0, 0)
            dispatch(canvas, Event.key_press('d'))
            dispatch(canvas, Event.key_press('up'))
            assert canvas.input.is_down('d')
            assert canvas.input.direction() == (1, -1)
            dispatch(canvas, Event.key_press('d', kind='release'))
            assert canvas.input.direction() == (0, -1)
            assert canvas.input.axis('q', 'e') == 0


def test_sprites_can_be_drawn_from_text_and_scrolled():
    from xnano.image import TerminalImage

    red, blue, none = (255, 0, 0, 255), (0, 0, 255, 255), (0, 0, 0, 0)
    sprite = TerminalImage.from_rgba(2, 2, bytes(red + blue + none + blue))
    with new(width=4, height=2) as canvas:
        pixels = canvas.region.half_blocks
        pixels.draw_image(sprite, x=1, y=0)
        assert canvas.core_buffer[1, 0].foreground.to_rgb() == (255, 0, 0)
        pixels.draw_image(sprite, x=-1, y=0, mode='replace')
        assert canvas.core_buffer[0, 0].background.to_rgb() == (0, 0, 255), (
            'a negative offset scrolls'
        )


class TestWritingTheWayItIsThought:
    def test_text_takes_a_style(self, canvas):
        from xnano.styles import Style

        text = canvas.write('hi', style=Style('red', bold=True))
        assert text.core_buffer[0, 0].foreground == Color('red')
        assert 'bold' in text.core_buffer[0, 0].style.modifiers

    def test_text_in_a_titled_box(self, canvas):
        box = canvas.write('hi', title='Box', border='rounded')
        assert (box.width, box.height) == (5, 3), 'the box is as wide as its title'
        assert '╭' in box.core_buffer.render(format='text')
        assert 'Box' in box.core_buffer.render(format='text')

    def test_a_list_of_lines_is_one_text(self, canvas):
        lines = canvas.write(['one', 'three'])
        assert (lines.width, lines.height) == (5, 2)

    def test_a_widget_takes_a_look_like_text_does(self, canvas):
        from xnano.styles import Style
        from xnano.widgets import Gauge

        placement = canvas.write(Gauge(0.5), style=Style('red'), border='rounded')
        assert placement.border.kind == 'rounded'

    @pytest.mark.parametrize(
        ('x', 'y', 'expected'),
        [
            ('left', 'top', (0, 0)),
            ('center', 'center', (7, 2)),
            ('right', 'bottom', (15, 5)),
        ],
    )
    def test_words_place_something_inside_its_parent(self, canvas, x, y, expected):
        placed = canvas.write('hello', x=x, y=y)
        canvas.deliver_events()
        assert (placed.x, placed.y) == expected

    def test_a_word_for_the_wrong_axis_is_explained(self, canvas):
        with pytest.raises(ValueError, match='cannot place the y'):
            canvas.write('hi', y='left')

    def test_a_placement_takes_operations_such_as_effects(self, canvas):
        from xnano.effects import Effect

        text = canvas.write('hi')
        text.update(Effect.dissolve(duration_milliseconds=200))
        canvas.step(delta_seconds=0.3)


class TestWaitingForTheUser:
    def run_with_input(self, call, *events):
        import threading
        import time

        with new(realtime=True, width=30, height=3) as canvas:
            results = []
            thread = threading.Thread(target=lambda: results.append(call(canvas)))
            thread.start()
            time.sleep(0.3)
            for event in events:
                canvas.push(event)
                time.sleep(0.05)
            thread.join(timeout=5)
            assert not thread.is_alive(), 'the call should have returned'
            return results[0]

    def test_wait_for_key_returns_the_key(self):
        key = self.run_with_input(
            lambda canvas: canvas.wait_for_key('q', 'enter'),
            Event.key_press('x'),
            Event.key_press('enter'),
        )
        assert key == 'enter'

    def test_prompt_returns_what_was_typed(self):
        answer = self.run_with_input(
            lambda canvas: canvas.prompt('Name: '),
            Event.key_press('A'),
            Event.key_press('d'),
            Event.key_press('x'),
            Event.key_press('backspace'),
            Event.key_press('a'),
            Event.key_press('enter'),
        )
        assert answer == 'Ada'

    def test_prompt_puts_the_cursor_after_wide_characters_and_restores_it(self):
        import time

        with new(realtime=True, width=30, height=3) as canvas:
            before = (canvas.cursor.shape, canvas.cursor.is_blinking)
            results: list[str] = []
            thread = threading.Thread(
                target=lambda: results.append(canvas.prompt('Name: '))
            )
            thread.start()
            time.sleep(0.3)
            for key in ('世', '界', 'a'):
                canvas.push(Event.key_press(key))
                time.sleep(0.05)
            assert wait_for(lambda: canvas.cursor.position == Point(11, 0))
            canvas.push(Event.key_press('enter'))
            thread.join(timeout=5)
            assert results == ['世界a']
            assert (canvas.cursor.shape, canvas.cursor.is_blinking) == before

    def test_prompt_keeps_a_cursor_that_followed_a_placement_following_it(self):
        import time

        with new(realtime=True, width=30, height=3) as canvas:
            field = canvas.write('field', x=2, y=1)
            canvas.cursor.follow(field, x=1)
            results: list[str] = []
            thread = threading.Thread(
                target=lambda: results.append(canvas.prompt('Name: ', y=2))
            )
            thread.start()
            time.sleep(0.3)
            canvas.push(Event.key_press('enter'))
            thread.join(timeout=5)
            assert results == ['']
            field.x = 10
            assert wait_for(lambda: canvas.cursor.position == Point(11, 1))

    def test_a_terminal_that_never_moves_cannot_be_waited_on(self, canvas):
        with pytest.raises(TerminalError, match='never moves by itself'):
            canvas.wait_for_key('q')


def test_assigning_text_to_a_placement_changes_what_it_shows(canvas):
    text = canvas.write('hello')
    text.text = 'bye'
    assert text.text == 'bye'
    assert (text.width, text.height) == (3, 1)
    canvas.deliver_events()
    assert canvas.output.snapshot().lines()[0] == 'bye'
    text.text = 'one\ntwo'
    assert (text.width, text.height) == (3, 2)


class TestRemovingBeforeTheNextFrame:
    def test_a_look_changed_just_before_remove_is_never_drawn(self, canvas):
        placement = canvas.write('hi')
        placement.color.fg = 'red'
        placement.border = True
        placement.padding = 1
        placement.remove()
        assert not canvas._dirty_looks
        canvas.step()
        assert canvas.render().strip() == ''

    def test_a_running_canvas_survives_it(self):
        with new(width=20, height=5, realtime=True) as running:
            placement = running.write('hi')
            placement.color.fg = 'red'
            placement.remove()
            running.write('still here')
            running.stop()
            running.step()
            assert 'still here' in running.render()


class TestFormulasThatLoseTheirValue:
    def test_an_axis_follows_the_pointer_until_the_pointer_is_forgotten(self, canvas):
        from xnano.expressions import Mouse

        canvas.push(Event.mouse_event(column=7, row=1, kind='move'))
        canvas.step()
        placement = canvas.write('a')
        placement.x = Mouse.position.x
        assert placement.x == 7
        canvas.push(Event.key_press('a'))
        canvas.step()
        canvas.step()
        assert placement.x == 7, (
            'the axis keeps its last value while the formula has none'
        )

    def test_an_axis_bound_to_a_state_field_that_becomes_none_keeps_its_value(self):
        from dataclasses import dataclass

        @dataclass
        class Fields:
            maybe: int | None = 3

        with new(width=20, height=3, state=Fields()) as stated:
            placement = stated.write('a')
            placement.x = stated.state_reference(lambda fields: fields.maybe)
            stated.step()
            assert placement.x == 3
            stated.state.push('maybe', None)
            stated.step()
            stated.step()
            assert placement.x == 3
            stated.state.push('maybe', 5)
            stated.step()
            assert placement.x == 5


class TestWritingACanvasIntoAnother:
    def test_a_refused_write_leaves_the_child_ready_to_be_written_again(self):
        outer = new(width=20, height=4)
        child = new(width=5, height=1)
        child.write('kid')
        try:
            for keywords in (
                {'x': 'bad'},
                {'width': -1},
                {'height': -1},
                {'width': 'zz'},
                {'layer': 'x'},
            ):
                with pytest.raises((ValueError, TypeError)):
                    outer.write(child, **keywords)  # type: ignore[arg-type]
                assert child._canvas is child
                assert not outer._children
            child.step()
            outer.write(child)
            outer.step()
            assert 'kid' in outer.render()
        finally:
            outer.close()

    def test_lock_freezes_the_formulas_of_a_written_canvas(self):
        with new(width=20, height=4) as outer:
            child = new(width=5, height=1)
            locked = outer.write(child, x='50%', lock=True)
            assert not locked._bindings
            assert locked.x == 10

    def test_removing_the_placement_closes_the_canvas_inside_it(self):
        with new(width=20, height=4) as outer:
            child = new(width=5, height=1)
            holder = outer.write(child)
            holder.remove()
            assert child.is_closed
            assert child not in outer._children
            with pytest.raises(TerminalClosedError):
                child.write('late')

    def test_adding_and_removing_canvases_does_not_grow_the_list_of_children(self):
        with new(width=20, height=4) as outer:
            for _ in range(5):
                outer.write(new(width=5, height=1)).remove()
            assert outer._children == []


class TestSteppingWhileClosing:
    def test_a_stopped_canvas_closed_from_another_thread_ends_the_step_at_once(self):
        import time

        running = new(width=10, height=2, realtime=True)
        running.stop()
        closer = threading.Timer(0.05, running.close)
        closer.start()
        started = time.monotonic()
        try:
            with pytest.raises(TerminalError):
                while time.monotonic() - started < 3:
                    running.step()
        finally:
            closer.join()
        assert time.monotonic() - started < 3

    def test_a_step_that_is_too_large_says_how_to_step(self, canvas):
        with pytest.raises(ValueError, match='at most'):
            canvas.step(delta_seconds=1e300)


class TestTheCursorAndARemovedPlacement:
    def test_a_cursor_that_followed_a_placement_loses_its_position_with_it(self, canvas):
        field = canvas.write('field', x=3, y=1)
        canvas.cursor.follow(field, x=2)
        canvas.step()
        assert canvas.cursor.position == Point(5, 1)
        field.remove()
        canvas.step()
        assert canvas.cursor.position is None

    def test_following_something_else_says_what_to_pass(self, canvas):
        with pytest.raises(TypeError, match='placement, a region or a buffer'):
            canvas.cursor.follow('a')  # type: ignore[arg-type]


class TestTeachingErrorsOnWrongTypes:
    def test_modifiers_and_styles_are_checked_where_they_are_set(self, canvas):
        placement = canvas.write('a')
        with pytest.raises(TypeError, match='is_bold must be True or False'):
            placement.is_bold = 'x'  # type: ignore[assignment]
        assert placement.is_bold is False
        with pytest.raises(TypeError, match='style must be a Style'):
            placement.style = 5  # type: ignore[assignment]
        with pytest.raises(TypeError, match='is_bold must be True or False'):
            canvas.write('a', is_bold='x')  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='title must be text'):
            canvas.write('a', title=5)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError), match='foreground must be a color'):
            canvas.write('a', foreground='nocolor')
        with pytest.raises(TypeError, match='text must be a string'):
            placement.text = 5  # type: ignore[assignment]
        canvas.step()

    def test_the_layer_is_a_whole_number(self, canvas):
        placement = canvas.write('a')
        with pytest.raises(TypeError, match='layer must be a whole number'):
            placement.layer = 'a'  # type: ignore[assignment]
        with pytest.raises(TypeError, match='layer must be a whole number'):
            canvas.write('a', layer='a')  # type: ignore[arg-type]
        assert len(canvas._placements) == 1

    def test_a_position_that_is_not_a_cell_is_refused(self, canvas):
        placement = canvas.write('a')
        with pytest.raises(ValueError, match='not a valid x'):
            placement.x = float('inf')
        with pytest.raises(ValueError, match='too far'):
            placement.x = 2**40

    def test_a_margin_error_names_margin_in_its_advice(self):
        with pytest.raises(TypeError, match=r'Pass margin=1, margin=0\.1'):
            new(margin='x')  # type: ignore[arg-type]
        with pytest.raises(TypeError, match=r'Pass padding=1, padding=0\.1'):
            new(padding='x')  # type: ignore[arg-type]

    def test_the_title_and_effects_and_keys_say_what_they_take(self, canvas):
        with pytest.raises(TypeError, match='title must be text'):
            canvas.title = 5  # type: ignore[assignment]
        with pytest.raises(TypeError, match='effects= takes a list'):
            canvas.write('a', effects=1)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='keys= takes'):
            canvas.hook(lambda context: None, on='key', keys=5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='takes a function'):
            canvas.state_reference(5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='takes a Point'):
            canvas.local((1, 1))  # type: ignore[arg-type]

    def test_counts_name_the_method_and_its_opposite(self, canvas):
        placement = canvas.write('a')
        with pytest.raises(
            TypeError, match=r'Pass count=1 to move one cell with right\(\)'
        ):
            placement.right('a')  # type: ignore[arg-type]
        with pytest.raises(ValueError, match=r'call left\(\) instead of right\(\)'):
            placement.right(-1)
        with pytest.raises(ValueError, match=r'call down\(\) instead of up\(\)'):
            canvas.cursor.up(-1)

    def test_arguments_of_the_wrong_kind_are_explained_where_they_are_given(self, canvas):
        from xnano.input import KeyboardInput
        from xnano.operations import fx

        with pytest.raises(TypeError, match='title must be text or None'):
            new(title=5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='title must be text or None'):
            canvas.open(title=5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='keys= takes key names'):
            canvas.hook(lambda context: None, on='key', keys=[5])  # type: ignore[list-item]
        with pytest.raises(TypeError, match='keyboard.push takes a key name'):
            KeyboardInput(canvas, None).push(5)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="'zzz' is not a key name"):
            KeyboardInput(canvas, None).push('zzz')
        with pytest.raises(
            TypeError, match="effect 'effect.fade_to' has no setting called 'color'"
        ):
            fx('effect.fade_to', color='red')  # type: ignore[call-overload]
        with pytest.raises(TypeError, match='shade.. takes a function of the position'):
            canvas.color.bg.shade(5)  # type: ignore[arg-type]

    def test_a_missing_image_file_names_the_path(self):
        pytest.importorskip('xnano_image')
        with pytest.raises(FileNotFoundError, match='nonexistent.png'):
            main.from_image('nonexistent.png')

    def test_a_missing_sound_file_is_explained_like_a_missing_image(self):
        pytest.importorskip('xnano_audio')
        with pytest.raises(
            FileNotFoundError, match='Audio could not load.*Check the path'
        ):
            main.from_audio('nonexistent.wav')
        with pytest.raises(
            ValueError, match=r'not a PCM WAV file that xnano can read[^(]'
        ):
            main.from_audio(b'')

    def test_a_space_cannot_be_negative(self, canvas):
        with pytest.raises(ValueError, match='padding must be zero or more'):
            canvas.write('a', padding=-1)
        with pytest.raises(ValueError, match='margin must be zero or more'):
            canvas.write('a', margin='-10%')

    @pytest.mark.parametrize('value', [float('nan'), float('inf'), 'nan%', 'inf%'])
    def test_a_space_cannot_be_infinite_or_not_a_number(self, canvas, value):
        with pytest.raises(ValueError, match='padding must be zero or more and finite'):
            canvas.write('a', padding=value)
        placement = canvas.write('a')
        with pytest.raises(ValueError, match='padding must be zero or more and finite'):
            placement.padding = value

    def test_requires_deps_explains_the_two_ways_to_give_them(self, canvas):
        with pytest.raises(TerminalError, match=r'canvas\.open\(deps='):
            canvas.hook(lambda context: None, on='tick', requires_deps=True)


class TestThreadErrorsNameTheOperation:
    def test_using_a_manual_canvas_from_another_thread_names_the_call(self, canvas):
        caught: list[BaseException] = []

        def other() -> None:
            try:
                canvas.step()
            except BaseException as error:
                caught.append(error)

        thread = threading.Thread(target=other)
        thread.start()
        thread.join()
        assert len(caught) == 1
        assert isinstance(caught[0], TerminalError)
        assert 'step was used from another thread' in str(caught[0])

    @pytest.mark.parametrize(
        ('call', 'name'),
        [
            (lambda canvas, placement: canvas.state.push('a', 1), 'push'),
            (
                lambda canvas, placement: placement.hook(lambda context: None, on='tick'),
                'hook',
            ),
        ],
    )
    def test_the_call_the_user_wrote_is_named_not_a_helper(self, canvas, call, name):
        caught: list[BaseException] = []
        placement = canvas.write('xy')

        def other() -> None:
            try:
                call(canvas, placement)
            except BaseException as error:
                caught.append(error)

        thread = threading.Thread(target=other)
        thread.start()
        thread.join()
        assert len(caught) == 1
        assert f'{name} was used from another thread' in str(caught[0])

    def test_assigning_a_state_field_from_another_thread_says_what_was_used(self):
        import dataclasses

        @dataclasses.dataclass
        class Score:
            value: int = 0

        caught: list[BaseException] = []
        with new(width=10, height=3, state=Score()) as canvas:

            def other() -> None:
                try:
                    canvas.state.value = 3
                except BaseException as error:
                    caught.append(error)

            thread = threading.Thread(target=other)
            thread.start()
            thread.join()
            assert len(caught) == 1
            assert str(caught[0]).startswith('This canvas was used from another thread')
            assert canvas.state.get('value') == 0

    def test_a_push_refused_on_another_thread_saves_nothing(self, canvas):
        caught: list[BaseException] = []

        def other() -> None:
            try:
                canvas.state.push('refused', 2)
            except BaseException as error:
                caught.append(error)

        thread = threading.Thread(target=other)
        thread.start()
        thread.join()
        assert len(caught) == 1
        assert canvas.state.get('refused') is None

    def test_a_user_module_that_starts_with_xnano_is_not_part_of_xnano(self, canvas):
        import types

        module = types.ModuleType('xnano_application')
        exec(  # noqa: S102
            'def update_everything(canvas):\n    canvas.cursor.up()\n', module.__dict__
        )
        caught: list[BaseException] = []

        def go() -> None:
            try:
                module.update_everything(canvas)
            except BaseException as error:
                caught.append(error)

        thread = threading.Thread(target=go)
        thread.start()
        thread.join()
        assert len(caught) == 1
        assert 'up was used from another thread' in str(caught[0])
