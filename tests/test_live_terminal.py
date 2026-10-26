"""
tests.test_live_terminal

A live terminal, run for real on a pseudo-terminal and read from an emulated screen.

Nothing here fakes a terminal's answers: the emulator keeps the screen, and it is the
emulator that says where the cursor is when the program asks. What the tests assert on is
what a user would see.
"""

from __future__ import annotations

import re
import sys

import pytest

pytest.importorskip('pyte')
if sys.platform == 'win32':
    pytest.skip('needs a pseudo-terminal', allow_module_level=True)
from emulator import Screen  # noqa: E402

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='needs a pseudo-terminal')

PROMPT = """
print('user@host $ ls')
print('a.txt  b.txt')
print('user@host $ python app.py', flush=True)
"""


@pytest.fixture
def run():
    created: list[Screen] = []

    def start(body: str, **options: int) -> Screen:
        screen = Screen(body, **options)
        created.append(screen)
        return screen

    yield start
    for screen in created:
        screen.close()
        # Nothing the library leaves behind may reach a user's terminal as a warning.
        output = screen.raw.decode('utf-8', 'replace')
        assert 'unsendable' not in output
        assert 'Exception ignored' not in output
        assert 'RuntimeWarning' not in output


class TestInlineRegion:
    def test_the_region_is_drawn_below_the_prompt_and_erased_on_exit(self, run):
        screen = run(
            PROMPT
            + """
with xnano.open(width=14, height=2) as terminal:
    terminal.screen.write('Hello, world!')
    terminal.run()
print('DONE')
""",
            rows=12,
            columns=40,
        )
        assert screen.wait_for('Hello, world!')
        assert screen.lines()[:4] == [
            'user@host $ ls',
            'a.txt  b.txt',
            'user@host $ python app.py',
            'Hello, world!',
        ]
        screen.press('ctrl+c')
        assert screen.finish() == 0
        assert 'Hello' not in screen.text
        assert screen.lines()[3] == 'DONE'

    def test_it_is_drawn_while_the_program_is_still_busy(self, run):
        screen = run(
            """
with xnano.open(height=3) as terminal:
    terminal.screen.write('HELLO-NOW', x=2)
    time.sleep(8)
"""
        )
        assert screen.wait_for('HELLO-NOW', timeout=4)
        assert screen.process.poll() is None
        assert screen.find('HELLO-NOW') == (2, 0)

    def test_a_persistent_region_stays_after_exit(self, run):
        screen = run(
            """
with xnano.open(height=2, clears_on_close=False) as terminal:
    terminal.screen.write('stays')
    time.sleep(0.5)
print('after')
"""
        )
        assert screen.finish() == 0
        assert 'stays' in screen.text
        assert screen.lines().index('after') > screen.lines().index('stays')

    def test_the_region_is_drawn_at_the_bottom_of_a_full_screen(self, run):
        screen = run(
            """
for number in range(30):
    print('line', number)
with xnano.open(width=10, height=2) as terminal:
    terminal.screen.write('bottom')
    time.sleep(0.8)
""",
            rows=10,
            columns=30,
        )
        assert screen.wait_for('bottom')
        assert screen.find('bottom') is not None
        assert screen.find('bottom')[1] >= 7


class TestFullScreen:
    def test_it_uses_the_alternate_screen_and_gives_the_old_one_back(self, run):
        screen = run(
            PROMPT
            + """
with xnano.open() as terminal:
    terminal.screen.write('FULL SCREEN', x=3, y=2)
    time.sleep(1)
print('BACK')
""",
            rows=10,
            columns=40,
        )
        assert screen.wait_until(lambda: screen.is_alternate)
        assert screen.wait_for('FULL SCREEN')
        assert screen.find('FULL SCREEN') == (3, 2)
        assert 'user@host $ ls' not in screen.text, 'the shell history is not drawn over'
        assert screen.finish() == 0
        assert not screen.is_alternate
        assert 'FULL SCREEN' not in screen.text
        assert screen.lines()[:3] == [
            'user@host $ ls',
            'a.txt  b.txt',
            'user@host $ python app.py',
        ]
        assert 'BACK' in screen.text

    def test_it_can_stay_on_the_main_screen(self, run):
        screen = run(
            """
with xnano.open(alternate_screen=False) as terminal:
    terminal.screen.write('MAIN SCREEN')
    time.sleep(1)
"""
        )
        assert screen.wait_for('MAIN SCREEN')
        assert not screen.is_alternate


class TestInput:
    def test_a_key_stops_the_terminal(self, run):
        screen = run(
            """
with xnano.open(height=2) as terminal:
    terminal.screen.write('press q')

    @terminal.hook(on=lambda context: context.keyboard.key is not None and context.keyboard.key == 'q')
    def quit(context):
        context.canvas.stop()

    terminal.run()
print('LEFT')
"""
        )
        assert screen.wait_for('press q')
        screen.press('x')
        screen.settle(0.3)
        assert screen.process.poll() is None, 'another key does not stop it'
        screen.press('q')
        assert screen.finish() == 0
        assert screen.wait_for('LEFT', timeout=1)

    def test_ctrl_c_stops_run(self, run):
        screen = run(
            """
with xnano.open(height=2) as terminal:
    terminal.screen.write('waiting')
    terminal.run()
print('STOPPED')
"""
        )
        assert screen.wait_for('waiting')
        screen.press('ctrl+c')
        assert screen.finish() == 0
        assert screen.wait_for('STOPPED', timeout=1)

    def test_a_click_reaches_the_placement_under_it(self, run):
        screen = run(
            """
with xnano.open(height=3, mouse=True) as terminal:
    button = terminal.screen.write('[ click ]', x=4, y=1)

    @button.hook(on=lambda context: context.mouse.position is not None and context.mouse.kind == 'press')
    def pressed(context):
        context.canvas.screen.write('CLICKED', x=0, y=0)

    terminal.run()
"""
        )
        assert screen.wait_for('[ click ]')
        screen.click(0, 0)
        screen.settle(0.3)
        assert screen.find('CLICKED') is None, 'a click elsewhere is not heard'
        screen.click(6, 1)
        assert screen.wait_for('CLICKED')

    @pytest.mark.parametrize('decorator', ['@content.hook', "@content.hook(on='mouse')"])
    def test_a_click_changes_the_color_of_a_component_drawn_every_frame(
        self, run, decorator
    ):
        screen = run(
            f"""
@xnano.writable
def main(context: xnano.Context) -> str:
    return str(context.clock.elapsed_seconds)

with xnano.open(height=1, mouse=True) as terminal:
    content = terminal.screen.write(main)

    {decorator}
    def change_on_click(context: xnano.Context):
        if context.mouse.button == 'left':
            content.color.fg = content.color.fg.random()

    terminal.run(stop_on='q')
"""
        )
        assert screen.wait_until(lambda: screen.cell(0, 0).data.isdigit())
        assert screen.cell(0, 0).fg == 'default'
        screen.click(1, 0)
        assert screen.wait_until(lambda: screen.cell(0, 0).fg != 'default', timeout=5)
        screen.settle(0.3)
        assert screen.cell(0, 0).fg != 'default', 'the color stays while the text changes'
        screen.press('q')
        assert screen.finish() == 0

    def test_a_held_button_is_seen_on_every_frame_until_it_is_released(self, run):
        screen = run(
            """
from xnano.hooks import Frame

held_frames = []
held_seconds = []
pressed_seconds = []
frames_after_release = []
is_released = False

@xnano.writable
def main(context: xnano.Context) -> str:
    return str(context.clock.elapsed_seconds)

with xnano.open(height=2, mouse=True) as terminal:
    content = terminal.screen.write(main)
    log = terminal.screen.write('', y=1)

    @content.hook
    def change_while_held(context: xnano.Context):
        global is_released
        if context.mouse.kind == 'press':
            pressed_seconds.append(context.clock.elapsed_seconds)
        elif context.mouse.kind == 'release':
            is_released = True
        elif isinstance(context.event, Frame) and context.mouse.button == 'left':
            (frames_after_release if is_released else held_frames).append(context.event.index)
            held_seconds.append(context.event.elapsed_seconds)
        if context.mouse.button == 'left':
            content.color.fg = content.color.fg.random()
        log.text = f'HELD {len(held_frames)} RELEASED {is_released}'

    terminal.run(stop_on='q')
first = held_frames[0]
print('EVERY FRAME', held_frames == list(range(first, first + len(held_frames))))
print('DELAYED', held_seconds[0] - pressed_seconds[0] >= 0.15)
print('AFTER RELEASE', frames_after_release)
"""
        )

        def held_count() -> int:
            match = re.search(r'HELD (\d+)', screen.text)
            return int(match.group(1)) if match else 0

        assert screen.wait_until(lambda: screen.cell(0, 0).data.isdigit())
        screen.send('\x1b[<0;2;1M')
        assert screen.wait_until(lambda: held_count() >= 3, timeout=5)
        colors = set()
        for _ in range(10):
            screen.settle(0.05)
            colors.add(screen.cell(0, 0).fg)
        assert len(colors) >= 3, 'the color keeps changing while the button is held'
        assert screen.find('RELEASED False') is not None
        screen.send('\x1b[<0;2;1m')
        assert screen.wait_for('RELEASED True')
        count = held_count()
        color = screen.cell(0, 0).fg
        screen.settle(0.4)
        assert held_count() == count
        assert screen.cell(0, 0).fg == color, (
            'the color stays once the button is released'
        )
        screen.press('q')
        assert screen.finish() == 0
        assert 'EVERY FRAME True' in screen.text
        assert 'DELAYED True' in screen.text, 'the frames start after a short delay'
        assert 'AFTER RELEASE []' in screen.text

    def test_a_normal_click_runs_a_bare_hook_for_the_press_and_release_only(self, run):
        screen = run(
            """
from xnano.hooks import Frame

runs = []

@xnano.writable
def main(context: xnano.Context) -> str:
    return str(context.clock.elapsed_seconds)

with xnano.open(height=2, mouse=True) as terminal:
    content = terminal.screen.write(main)
    log = terminal.screen.write('', y=1)

    @content.hook
    def change_on_click(context: xnano.Context):
        if context.mouse.button == 'left':
            runs.append('frame' if isinstance(context.event, Frame) else context.mouse.kind)
            log.text = f'RUNS {len(runs)}'

    terminal.run(stop_on='q')
print('KINDS', runs)
"""
        )
        assert screen.wait_until(lambda: screen.cell(0, 0).data.isdigit())
        screen.send('\x1b[<0;2;1M')
        screen.settle(0.02)
        screen.send('\x1b[<0;2;1m')
        assert screen.wait_for('RUNS 2')
        screen.settle(0.3)
        screen.press('q')
        assert screen.finish() == 0
        assert "KINDS ['press', 'release']" in screen.text

    def test_a_click_in_a_region_below_the_prompt_lands_on_the_right_cell(self, run):
        screen = run(
            PROMPT
            + """
with xnano.open(width=20, height=3, mouse=True) as terminal:
    button = terminal.screen.write('[ click ]', x=4, y=1)

    @button.hook(on=lambda context: context.mouse.position is not None and context.mouse.kind == 'press')
    def pressed(context):
        context.canvas.screen.write('CLICKED', x=0, y=0)

    terminal.run()
""",
            rows=12,
            columns=40,
        )
        assert screen.wait_for('[ click ]')
        column, row = screen.find('[ click ]')
        assert row == 4, 'the region starts on the row below the prompt'
        screen.click(column + 2, row - 1)
        screen.settle(0.3)
        assert screen.find('CLICKED') is None, (
            'the row above the button is not the button'
        )
        screen.click(column + 2, row)
        assert screen.wait_for('CLICKED')

    def test_dragging_moves_a_slider_thumb(self, run):
        screen = run(
            """
import xnano
with xnano.open(height=3, width=30, mouse=True) as terminal:
    terminal.screen.write('-' * 30, y=1)
    thumb = terminal.screen.write('#', x=(0, 29), y=1, layer=1)

    @thumb.hook(on='drag')
    def slide(context):
        while context.mouse.is_down:
            thumb.x = context.parent.local(context.mouse.position).x
            context = yield

    terminal.run()
"""
        )
        assert screen.wait_for('#')
        start = screen.find('#')
        assert start == (0, 1)
        screen.drag((0, 1), (12, 1))
        assert screen.wait_until(lambda: screen.find('#') == (12, 1), timeout=5)

    def test_pasted_text_arrives_whole(self, run):
        screen = run(
            """
with xnano.open(height=2) as terminal:
    terminal.screen.write('paste here')

    @terminal.hook(on=lambda context: context.keyboard.pasted is not None)
    def pasted(context):
        context.canvas.screen.write('GOT:' + context.keyboard.pasted, x=0, y=1)

    terminal.run()
"""
        )
        assert screen.wait_for('paste here')
        screen.paste('two words')
        assert screen.wait_for('GOT:two words')


class TestState:
    def test_a_state_hook_draws_what_a_key_hook_pushed(self, run):
        screen = run(
            """
with xnano.open(height=2) as terminal:
    @terminal.hook(on='key', keys='a')
    def count(context):
        state = context.root.state
        state.set('count', state.get('count', default=0) + 1)

    @terminal.hook(on='state')
    def show(context):
        label.text = f"count: {context.root.state.get('count', default=0)}"

    # Written after the hooks, so a key pressed once it shows is heard by both.
    label = terminal.screen.write('count: 0')
    terminal.run()
"""
        )
        assert screen.wait_for('count: 0')
        screen.press('a')
        assert screen.wait_for('count: 1')
        screen.press('a')
        assert screen.wait_for('count: 2')
        screen.press('ctrl+c')
        assert screen.finish() == 0


class TestDrawing:
    def test_a_formula_moves_without_being_driven(self, run):
        screen = run(
            """
from xnano_core import TimeElapsed, ParentWidth, Width
with xnano.open(width=30, height=1) as terminal:
    ball = terminal.screen.write('o')
    ball.x = (ParentWidth - Width) * ((TimeElapsed / 2) % 1.0)
    time.sleep(6)
"""
        )
        assert screen.wait_for('o')
        first = screen.find('o')[0]
        assert screen.wait_until(lambda: (screen.find('o') or (first, 0))[0] > first + 5)

    def test_the_animation_keeps_going_while_the_program_is_busy(self, run):
        screen = run(
            """
from xnano_core import TimeElapsed, ParentWidth, Width
with xnano.open(width=30, height=1) as terminal:
    ball = terminal.screen.write('o')
    ball.x = (ParentWidth - Width) * ((TimeElapsed / 2) % 1.0)
    end = time.monotonic() + 6
    while time.monotonic() < end:
        sum(range(10000))  # the program is busy the whole time
"""
        )
        assert screen.wait_for('o')
        seen = set()
        deadline_samples = 12
        for _ in range(deadline_samples):
            screen.settle(0.2)
            position = screen.find('o')
            if position:
                seen.add(position[0])
        assert len(seen) >= 5

    def test_colors_reach_the_screen(self, run):
        screen = run(
            """
with xnano.open(width=8, height=2) as terminal:
    pixels = terminal.screen.region.half_blocks
    pixels[0, 0] = (255, 0, 0)
    pixels[0, 1] = (0, 0, 255)
    time.sleep(1.2)
"""
        )
        assert screen.wait_until(lambda: screen.cell(0, 0).data == '▀')
        cell = screen.cell(0, 0)
        assert (cell.fg, cell.bg) == ('ff0000', '0000ff')

    def test_an_image_is_drawn_in_its_colors(self, run):
        screen = run(
            """
from xnano_image import TerminalImage
image = TerminalImage.from_rgba(4, 2, bytes([0, 255, 0, 255]) * 8)
with xnano.open(width=10, height=2) as terminal:
    terminal.screen.write(xnano.Image(image))
    time.sleep(1.2)
"""
        )
        assert screen.wait_until(lambda: screen.cell(0, 0).data != ' ')
        assert '00ff00' in (screen.cell(0, 0).fg, screen.cell(0, 0).bg)

    def test_an_effect_changes_the_colors_over_time(self, run):
        screen = run(
            """
from xnano_core import Effect
with xnano.open(width=10, height=1) as terminal:
    placement = terminal.screen.write('hello')
    placement.core_buffer.update(Effect.fade_to((255, 0, 0), duration_milliseconds=600))
    time.sleep(2)
"""
        )
        assert screen.wait_for('hello')
        assert screen.wait_until(lambda: screen.cell(0, 0).fg == 'ff0000', timeout=5)

    def test_a_glitch_draws_only_printable_characters(self, run):
        # A glitch that moves `~` up by any amount passes the end of printable ASCII.
        screen = run(
            """
with xnano.open(width=40, height=1) as terminal:
    placement = terminal.screen.write('~' * 40)
    placement.fx.glitch(ratio=1.0, duration_milliseconds=1500)
    time.sleep(2)
"""
        )
        assert screen.wait_until(lambda: re.search('[!-}]', screen.lines()[0]), timeout=5)
        assert screen.finish() == 0
        output = screen.raw.decode('utf-8', 'replace')
        assert not re.search('[\x7f-\x9f]', output)

    def test_border_draws_around_art_and_widgets(self, run):
        screen = run(
            """
from xnano.widgets import Gauge
art = xnano.pixel_art(['RR', 'RR'], {'R': '#ff0000'})
with xnano.open(width=14, height=6) as terminal:
    terminal.screen.write(art, border='rounded')
    terminal.screen.write(Gauge(ratio=0.5, width=6, height=1), x=6, border='plain')
    time.sleep(1.5)
"""
        )
        assert screen.wait_for('╭')
        assert screen.wait_for('┌')
        assert screen.cell(1, 1).data in ('▀', ' ', '█')
        assert 'ff0000' in (screen.cell(1, 1).fg, screen.cell(1, 1).bg)

    def test_a_look_changed_before_opening_is_drawn_once_and_asks_for_no_frames(
        self, run
    ):
        screen = run(
            """
canvas = xnano.new(width=20, height=5)
canvas.screen.border = 'plain'
canvas.open()
time.sleep(0.3)
canvas.screen.write(f'dirty={len(canvas._dirty_looks)} demand={canvas._frame_demand}', x=1, y=1)
time.sleep(1.5)
"""
        )
        assert screen.wait_for('dirty=0 demand=0')

    def test_a_component_that_reads_the_time_keeps_drawing(self, run):
        screen = run(
            """
@xnano.writable
def clock(context):
    return str(int(context.clock.elapsed_seconds))

with xnano.open(width=6, height=1) as terminal:
    terminal.screen.write(clock)
    time.sleep(4)
"""
        )
        assert screen.wait_for('0')
        assert screen.wait_until(lambda: '2' in screen.text, timeout=6)

    def test_the_measured_frame_rate_stays_within_fps_while_input_arrives(self, run):
        screen = run(
            """
drawn = []

@xnano.writable
def elapsed(context):
    drawn.append(time.monotonic())
    return f'{context.clock.elapsed_seconds:.3f}'

readings = []
ratios = []
with xnano.open(width=30, height=2, fps=30, mouse=True) as terminal:
    terminal.screen.write(elapsed)
    keys = terminal.screen.write('keys 0', y=1)
    pressed = []

    @terminal.hook(on='key')
    def count(context):
        pressed.append(context.keyboard.key)
        keys.text = f'keys {len(pressed)}'

    @terminal.hook(on='tick', every=0.1)
    def measure(context):
        measured = context.clock.measured_fps
        readings.append(measured)
        # The frames drawn in the second before now, counted independently of the clock.
        now = time.monotonic()
        if now - drawn[0] > 1.0:
            counted = sum(1 for moment in drawn if moment > now - 1.0)
            ratios.append(measured / max(counted, 1))

    terminal.run(stop_on='q')
ratios.sort()
print('MOST', round(max(readings), 1))
print('RATIO', round(ratios[len(ratios) // 2], 2))
"""
        )
        assert screen.wait_until(lambda: screen.cell(0, 0).data.isdigit())
        for index in range(60):
            screen.press('x')
            screen.send(f'\x1b[<35;{index % 30 + 1};1M')
            screen.settle(0.02)
        assert screen.wait_for('keys 60')
        screen.settle(1.0)
        screen.press('q')
        assert screen.finish() == 0
        most = float(re.search(r'MOST ([\d.]+)', screen.text).group(1))
        ratio = float(re.search(r'RATIO ([\d.]+)', screen.text).group(1))
        assert most <= 30 * 1.05, f'measured {most} frames per second at fps=30'
        # A slow machine draws fewer frames, so the rate is compared with the frames that were
        # actually drawn rather than with a fixed floor. Stalls on a busy machine make a rate
        # smoothed over recent frames and a count over the last second disagree, so the median
        # of many readings only has to be the right size: a rate taken from runtime steps
        # reads hundreds of times too high.
        assert 1 / 3 <= ratio <= 3, (
            f'measured rates were typically {ratio} times the frames drawn each second'
        )

    def test_a_component_wakes_on_a_key(self, run):
        screen = run(
            """
@xnano.writable
def last(context):
    return context.keyboard.key or '-'

with xnano.open(width=6, height=1) as terminal:
    terminal.screen.write(last)
    terminal.run()
"""
        )
        assert screen.wait_for('-')
        screen.press('x')
        assert screen.wait_for('x')
        screen.press('ctrl+c')


class TestGraphicsProtocols:
    """The escape sequences of each protocol reach the terminal; the emulator cannot draw them."""

    SCRIPT = """
from xnano_core import Buffer
from xnano_image import TerminalGraphics, TerminalImage
image = TerminalImage.from_rgba(16, 16, bytes([255, 0, 0, 255]) * 256)
graphics = TerminalGraphics.from_capabilities(protocol={protocol!r}, cell_size_in_pixels=(8, 16))
grid = image.to_cell_grid(4, 2, graphics=graphics)
with xnano.open(width=10, height=3) as terminal:
    terminal.screen.write(Buffer.from_cell_grid(grid))
    time.sleep(1)
"""

    @pytest.mark.parametrize(
        ('protocol', 'marker'),
        [
            ('kitty', rb'\x1b_G[^\x1b]*a=T'),
            ('iterm2', rb'\x1b\]1337;File='),
            ('sixel', rb'\x1bP[0-9;]*q'),
        ],
    )
    def test_the_protocols_escape_sequence_is_sent(self, run, protocol, marker):
        screen = run(self.SCRIPT.format(protocol=protocol))
        assert screen.wait_until(
            lambda: re.search(marker, screen.raw) is not None, timeout=6
        ), screen.raw[-300:]


class TestCursor:
    def test_the_cursor_is_placed_inside_the_region_and_restored_after(self, run):
        screen = run(
            PROMPT
            + """
with xnano.open(width=12, height=3) as terminal:
    terminal.screen.write('field:')
    terminal.screen.cursor.position = (7, 1)
    terminal.screen.cursor.shape = 'bar'
    time.sleep(1.5)
print('DONE')
""",
            rows=12,
            columns=40,
        )
        assert screen.wait_for('field:')
        assert screen.wait_until(lambda: screen.cursor == (7, 4, True))
        assert screen.finish() == 0
        assert screen.cursor[2], 'the cursor is visible again'

    def test_the_cursor_moves_by_cells(self, run):
        screen = run(
            PROMPT
            + """
with xnano.open(width=12, height=4) as terminal:
    terminal.screen.write('moved')
    terminal.screen.cursor.home().right(5).down(2)
    time.sleep(1.5)
print('DONE')
""",
            rows=12,
            columns=40,
        )
        assert screen.wait_for('moved')
        assert screen.wait_until(lambda: screen.cursor == (5, 5, True))
        assert screen.finish() == 0

    def test_a_hidden_cursor_stays_hidden(self, run):
        screen = run(
            """
with xnano.open(width=12, height=2) as terminal:
    terminal.screen.write('no cursor')
    terminal.screen.cursor.is_visible = False
    time.sleep(1.2)
"""
        )
        assert screen.wait_for('no cursor')
        assert screen.wait_until(lambda: not screen.cursor[2])


class TestWindow:
    def test_a_percentage_layout_follows_a_resize(self, run):
        screen = run(
            """
with xnano.open() as terminal:
    terminal.screen.write('right', x='100%', y=0)
    terminal.screen.write('middle', x='50%', y=1)
    terminal.run()
""",
            rows=8,
            columns=30,
        )
        assert screen.wait_for('middle')
        assert screen.find('middle') == (15, 1)
        screen.resize(8, 50)
        assert screen.wait_until(lambda: screen.find('middle') == (25, 1), timeout=5)

    def test_a_resize_hook_reads_the_new_size_and_region_of_the_window(self, run):
        screen = run(
            """
with xnano.open() as terminal:
    @terminal.hook(on='resize')
    def observe(context):
        terminal.screen.clear()
        region = context.region
        terminal.screen.write(
            f'RESIZED {context.size.width}x{context.size.height} '
            f'REGION {region.width}x{region.height}'
        )
    terminal.screen.write('RESIZE READY')
    terminal.run()
""",
            rows=8,
            columns=30,
        )
        assert screen.wait_for('RESIZE READY')
        screen.resize(18, 60)
        assert screen.wait_for('RESIZED 60x18 REGION 60x18')

    def test_a_resize_hook_of_a_bordered_window_reads_the_area_inside_the_border(
        self, run
    ):
        screen = run(
            """
with xnano.open() as terminal:
    terminal.screen.border = 'plain'

    @terminal.hook(on='resize')
    def observe(context):
        terminal.screen.write(
            f'INSIDE {context.size.width}x{context.size.height} '
            f'OUTSIDE {terminal.screen.size.width}x{terminal.screen.size.height}',
            x=1,
            y=2,
        )
    terminal.screen.write('RESIZE READY', x=1, y=1)
    terminal.run()
""",
            rows=8,
            columns=40,
        )
        assert screen.wait_for('RESIZE READY')
        screen.resize(18, 60)
        assert screen.wait_for('INSIDE 58x16 OUTSIDE 60x18')


class TestTerminalDetails:
    """What an open terminal says about its window, its settings and what it can do."""

    def test_the_window_is_larger_than_a_region_and_the_settings_are_resolved(self, run):
        screen = run(
            """
with xnano.open(height=2, mouse=True) as terminal:
    terminal.screen.write(
        f'W{terminal.screen.window.width}x{terminal.screen.window.height} '
        f'S{terminal.screen.width}x{terminal.screen.height} '
        f'M{terminal.settings["mouse"]}'
    )
    time.sleep(1)
""",
            rows=12,
            columns=60,
        )
        assert screen.wait_for('W60x12 S60x2 MTrue')

    def test_the_size_expressions_are_the_area_the_program_draws_on(self, run):
        screen = run(
            """
from xnano.expressions import TerminalHeight, TerminalWidth
with xnano.open(height=3) as terminal:
    terminal.screen.write(
        f'T{terminal.evaluate(TerminalWidth)}x{terminal.evaluate(TerminalHeight)} '
        f'W{terminal.screen.window.width}x{terminal.screen.window.height}'
    )
    time.sleep(1)
""",
            rows=12,
            columns=50,
        )
        assert screen.wait_for('T50x3 W50x12')

    def test_the_size_expressions_of_a_canvas_that_takes_the_window_are_the_window(
        self, run
    ):
        screen = run(
            """
from xnano.expressions import TerminalHeight, TerminalWidth
with xnano.open() as terminal:
    terminal.screen.write(
        f'T{terminal.evaluate(TerminalWidth)}x{terminal.evaluate(TerminalHeight)} '
        f'W{terminal.screen.window.width}x{terminal.screen.window.height}'
    )
    time.sleep(1)
""",
            rows=12,
            columns=50,
        )
        assert screen.wait_for('T50x12 W50x12')

    def test_the_terminal_reports_what_it_answered_when_it_was_opened(self, run):
        screen = run(
            """
with xnano.open(height=2) as terminal:
    terminal.screen.write(
        type(terminal.capabilities).__name__ + ' ' + terminal.capabilities.graphics.protocol
    )
    time.sleep(1)
"""
        )
        assert screen.wait_for('TerminalCapabilities')

    def test_the_function_does_not_ask_a_terminal_that_is_open(self, run):
        screen = run(
            """
import xnano.errors
with xnano.open(height=2) as terminal:
    try:
        xnano.terminal.capabilities()
    except xnano.errors.TerminalAlreadyOpenError:
        terminal.screen.write('REFUSED')
    time.sleep(0.8)
"""
        )
        assert screen.wait_for('REFUSED')


class TestPercentageSizes:
    def test_one_hundred_percent_fills_the_window(self, run):
        screen = run(
            PROMPT
            + """
with xnano.open(width='100%', height='100%') as terminal:
    terminal.screen.write('WHOLE', x='right', y='bottom')
    time.sleep(1)
""",
            rows=10,
            columns=40,
        )
        assert screen.wait_until(lambda: screen.is_alternate)
        assert screen.wait_for('WHOLE')
        assert screen.find('WHOLE') == (35, 9)
        assert screen.finish() == 0

    def test_a_percentage_height_is_a_share_of_the_window(self, run):
        screen = run(
            """
with xnano.open(height='50%') as terminal:
    terminal.screen.write('SIZE ' + repr((terminal.screen.width, terminal.screen.height)).replace(' ', ''))
    terminal.run()
""",
            rows=12,
            columns=60,
        )
        assert screen.wait_for('SIZE (60,6)')
        assert not screen.is_alternate
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_a_percentage_width_and_height_draw_a_region(self, run):
        screen = run(
            """
with xnano.open(width='25%', height='25%') as terminal:
    terminal.screen.write('SIZE ' + repr((terminal.screen.width, terminal.screen.height)).replace(' ', ''))
    terminal.run()
""",
            rows=12,
            columns=80,
        )
        assert screen.wait_for('SIZE (20,3)')
        screen.press('ctrl+c')
        assert screen.finish() == 0


class TestInlineResize:
    def test_a_resize_hook_sees_the_size_of_the_inline_region(self, run):
        screen = run(
            """
with xnano.open(height=4) as terminal:
    terminal.screen.write('region')
    sizes = []

    @terminal.hook(on='resize')
    def resized(context):
        sizes.append((terminal.screen.size.width, terminal.screen.size.height))
        terminal.screen.write('SIZES ' + repr(sizes[-1]).replace(' ', ''), y=1)

    terminal.run()
""",
            rows=12,
            columns=60,
        )
        assert screen.wait_for('region')
        screen.resize(12, 30)
        assert screen.wait_for('SIZES (30,4)')


class TestOutputCapture:
    def test_prints_do_not_corrupt_the_screen_and_arrive_afterwards(self, run):
        screen = run(
            """
import sys
with xnano.open(height=2) as terminal:
    terminal.screen.write('steady')
    print('A LOG LINE')
    sys.stderr.write('AN ERROR LINE\\n')
    time.sleep(1)
    assert 'A LOG LINE' in terminal.screen.output.take_captured()
print('AFTER')
"""
        )
        assert screen.wait_for('steady')
        screen.settle(0.8)
        assert 'LOG LINE' not in screen.text
        assert screen.finish() == 0
        assert 'AFTER' in screen.text

    def test_untaken_output_is_printed_when_the_terminal_closes(self, run):
        screen = run(
            """
with xnano.open(height=2) as terminal:
    terminal.screen.write('steady')
    print('PRINTED WHILE LIVE')
    time.sleep(0.8)
"""
        )
        assert screen.wait_for('steady')
        assert 'PRINTED WHILE LIVE' not in screen.text
        assert screen.finish() == 0
        assert 'PRINTED WHILE LIVE' in screen.text


class TestCaptureStatus:
    def test_a_live_terminal_reports_that_it_holds_output_back(self, run):
        screen = run(
            """
with xnano.open(height=2) as terminal:
    terminal.screen.write('CAPTURED' if terminal.screen.output.is_captured else 'OPEN')
    time.sleep(0.8)
"""
        )
        assert screen.wait_for('CAPTURED')

    def test_it_can_be_turned_off(self, run):
        screen = run(
            """
with xnano.open(height=2, capture=False) as terminal:
    terminal.screen.write('CAPTURED' if terminal.screen.output.is_captured else 'OPEN')
    time.sleep(0.8)
"""
        )
        assert screen.wait_for('OPEN')


class TestMisuse:
    def test_a_second_live_terminal_is_refused_with_advice(self, run):
        screen = run(
            """
import xnano.errors
with xnano.open(height=2) as terminal:
    try:
        xnano.open(height=2)
    except xnano.errors.TerminalAlreadyOpenError as error:
        terminal.screen.write('REFUSED', x=0, y=0)
    time.sleep(0.8)
"""
        )
        assert screen.wait_for('REFUSED')

    def test_an_error_in_the_program_restores_the_terminal(self, run):
        screen = run(
            """
with xnano.open(height=2) as terminal:
    terminal.screen.write('about to fail')
    time.sleep(0.4)
    raise RuntimeError('boom')
""",
            rows=12,
            columns=60,
        )
        assert screen.finish() == 1
        assert 'RuntimeError: boom' in screen.text
        assert screen.cursor[2], 'the cursor is visible again'


def test_window_title_is_written_while_stdout_is_captured(run):
    screen = run("""
with xnano.open(title='Initial title') as terminal:
    terminal.screen.title = 'Changed title'
    terminal.screen.write('TITLE READY')
    terminal.run()
""")
    assert screen.wait_for('TITLE READY')
    assert screen.screen.title == 'Changed title'
    screen.press('ctrl+c')
    assert screen.finish() == 0
    assert b'Initial title' in screen.raw
    assert b'Changed title' in screen.raw


def test_a_program_ends_when_its_terminal_window_closes():
    """Closing a window must not leave the program spinning on a terminal that is gone."""
    import os
    import subprocess

    screen = Screen(
        command=[
            sys.executable,
            '-c',
            'import xnano\n'
            'with xnano.open(width=20, height=2) as terminal:\n'
            "    terminal.screen.write('alive')\n"
            '    terminal.run()\n',
        ],
        rows=6,
        columns=30,
    )
    try:
        assert screen.wait_for('alive')
        process = screen.process
        os.close(screen.master)  # the window disappears under the program
        screen.master = os.open(os.devnull, os.O_RDWR)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pytest.fail('the program kept running after its terminal closed')
    finally:
        screen.close()


class TestGates:
    """Each input gate decides, on a real screen, which input reaches the canvas."""

    LISTENER = """
with xnano.open(width=40, height=3, {settings}) as terminal:
    terminal.screen.write('ready')
    log = terminal.screen.write('', y=1)
    heard = []

    @terminal.hook
    def listen(context):
        if context.mouse.kind is not None:
            heard.append(context.mouse.kind)
        if context.mouse.scroll.x or context.mouse.scroll.y:
            heard.append('scroll')
        if context.keyboard.key is not None:
            heard.append('key:' + str(context.keyboard.key))
        if context.keyboard.pasted is not None:
            heard.append('paste:' + context.keyboard.pasted)
        log.text = ' '.join(heard)

    terminal.run()
print('STOPPED')
"""

    def listener(self, run, settings: str):
        screen = run(self.LISTENER.format(settings=settings), rows=10, columns=50)
        assert screen.wait_for('ready')
        return screen

    def test_ctrl_c_stops_a_canvas_whose_keyboard_is_off(self, run):
        screen = self.listener(run, 'keyboard=False')
        screen.press('k')
        screen.settle(0.4)
        assert screen.find('key:') is None, 'device keys are dropped'
        assert screen.process.poll() is None
        screen.press('ctrl+c')
        assert screen.finish() == 0
        assert screen.wait_for('STOPPED', timeout=1)

    def test_a_canvas_whose_keyboard_is_on_hears_keys(self, run):
        screen = self.listener(run, 'keyboard=True')
        screen.press('k')
        assert screen.wait_for('key:k')
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_a_mouse_that_is_off_hears_neither_buttons_nor_the_wheel(self, run):
        screen = self.listener(run, 'mouse=False, scroll=False')
        screen.click(1, 0)
        screen.scroll(1, 0, direction='down')
        screen.settle(0.5)
        assert screen.find('press') is None
        assert screen.find('scroll') is None
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_buttons_arrive_without_the_wheel_when_scroll_is_off(self, run):
        screen = self.listener(run, 'mouse=True, scroll=False')
        screen.click(1, 0)
        assert screen.wait_for('press')
        screen.scroll(1, 0, direction='down')
        screen.settle(0.5)
        assert screen.find('scroll') is None
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_the_wheel_arrives_without_buttons_when_only_scroll_is_on(self, run):
        screen = self.listener(run, 'mouse=False, scroll=True')
        screen.click(1, 0)
        screen.settle(0.4)
        assert screen.find('press') is None
        screen.scroll(1, 0, direction='down')
        assert screen.wait_for('scroll')
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_the_paste_gate_decides_whether_the_terminal_brackets_pastes(self, run):
        screen = self.listener(run, 'paste=True')
        screen.paste('hello')
        assert screen.wait_for('paste:hello')
        assert b'\x1b[?2004h' in screen.raw
        screen.press('ctrl+c')
        assert screen.finish() == 0
        screen = self.listener(run, 'paste=False')
        assert b'\x1b[?2004h' not in screen.raw
        screen.press('ctrl+c')
        assert screen.finish() == 0


class TestOpeningACanvas:
    """A canvas from ``xnano.new()`` is put on the screen with ``open()``."""

    def test_a_screenless_canvas_opens_on_the_screen(self, run):
        screen = run(
            """
with xnano.new(width=30, height=3) as canvas:
    canvas.screen.write('built off the screen')
    heard = canvas.screen.write('', y=1)

    @canvas.hook(on='key', keys='k')
    def key(context):
        heard.text = 'KEY HEARD'

    canvas.clock.step()
    terminal = canvas.open()
    assert terminal is canvas and isinstance(canvas, xnano.Terminal)
    canvas.screen.write('OPENED', y=2)
    canvas.run(stop_on='q')
print('ENDED')
"""
        )
        assert screen.wait_for('OPENED')
        assert screen.find('built off the screen') == (0, 0)
        screen.press('k')
        assert screen.wait_for('KEY HEARD')
        screen.press('q')
        assert screen.finish() == 0
        assert screen.wait_for('ENDED', timeout=1)

    def test_a_canvas_keeps_its_time_and_timers_when_it_opens(self, run):
        screen = run(
            """
with xnano.new(width=40, height=3, fps=10) as canvas:
    @canvas.hook(on='tick', after=5.4)
    def later(context):
        canvas.screen.write(f'FIRED AT {context.clock.elapsed_seconds:.1f}', y=1)

    canvas.clock.step(delta_seconds=5.0)
    canvas.open()
    canvas.screen.write(f'OPENED AT {canvas.clock.elapsed_seconds:.1f}')
    time.sleep(3)
"""
        )
        assert screen.wait_for('OPENED AT 5.')
        assert screen.wait_for('FIRED AT ', timeout=10)
        screen.settle(0.3)
        fired = re.findall(r'FIRED AT (\d+(?:\.\d+)?)', screen.text)
        assert len(fired) == 1, 'the timer fires exactly once'
        assert 5.4 <= float(fired[0]) < 9, 'the timer fires once time passes 5.4'

    def test_a_stopped_canvas_stays_stopped_when_it_opens(self, run):
        screen = run(
            """
with xnano.new(width=40, height=3) as canvas:
    canvas.clock.step(delta_seconds=2.0)
    canvas.clock.pause()
    canvas.open()
    time.sleep(0.5)
    canvas.screen.write(f'STOPPED {canvas.clock.is_paused} AT {canvas.clock.elapsed_seconds:.2f}')
    canvas.clock.step()
    canvas.screen.write(f'STEPPED TO {canvas.clock.elapsed_seconds:.3f}', y=1)
    time.sleep(1)
"""
        )
        assert screen.wait_for('STOPPED True AT 2.00')
        assert screen.wait_for('STEPPED TO 2.01')

    def test_state_given_to_open_reaches_what_follows_it(self, run):
        screen = run(
            """
import dataclasses

@dataclasses.dataclass
class Settings:
    volume: int = 3

with xnano.new(width=30, height=3) as canvas:
    @xnano.writable
    def shown(context):
        return 'v=%s' % context.root.state.get('volume', 'none')

    heard = canvas.screen.write('', y=2)

    @canvas.hook(on='state')
    def hear(context):
        heard.text = 'HEARD %s' % context.root.state.get('volume', 'none')

    canvas.screen.write(shown)
    canvas.clock.step(delta_seconds=0.2)
    canvas.open(state=Settings(volume=7))
    time.sleep(2)
"""
        )
        assert screen.wait_for('v=7')
        assert screen.wait_for('HEARD 7')

    def test_effects_given_to_open_start_on_the_screen(self, run):
        screen = run(
            """
fade = [{'kind': 'effect.fade_to', 'foreground': 'red', 'duration_milliseconds': 300}]
with xnano.new(width=12, height=2) as canvas:
    canvas.screen.write('faded')
    canvas.open(effects=fade)
    time.sleep(2)
"""
        )
        assert screen.wait_for('faded')
        assert screen.wait_until(
            lambda: screen.cell(0, 0).fg in ('cd0000', 'ff0000'), timeout=5
        )

    def test_effects_given_to_xnano_open_with_a_canvas_start_on_the_screen(self, run):
        screen = run(
            """
fade = [{'kind': 'effect.fade_to', 'foreground': 'red', 'duration_milliseconds': 300}]
with xnano.new(width=12, height=2) as canvas:
    canvas.screen.write('faded')
    xnano.open(canvas, effects=fade)
    time.sleep(2)
"""
        )
        assert screen.wait_for('faded')
        assert screen.wait_until(
            lambda: screen.cell(0, 0).fg in ('cd0000', 'ff0000'), timeout=5
        )

    def test_a_bad_appearance_value_leaves_the_canvas_usable_and_leaks_nothing(self, run):
        screen = run(
            """
with xnano.new(width=20, height=3) as canvas:
    canvas.screen.write('hi')
    try:
        canvas.open(margin='x')
    except TypeError:
        print('REFUSED', type(canvas).__name__, canvas.is_closed)
    canvas.clock.step()
"""
        )
        assert screen.wait_for('REFUSED Canvas False')
        assert screen.finish() == 0

    def test_open_draws_inline_at_the_size_given_to_new(self, run):
        screen = run(
            PROMPT
            + """
with xnano.new(width=12, height=2) as canvas:
    canvas.screen.write('inline', x='right')
    canvas.open()
    time.sleep(1)
print('DONE')
""",
            rows=12,
            columns=40,
        )
        assert screen.wait_for('inline')
        assert screen.find('inline') == (6, 3), 'drawn 12 wide below the prompt'
        assert not screen.is_alternate
        assert screen.finish() == 0

    def test_open_fills_the_window_for_a_canvas_created_without_a_size(self, run):
        screen = run(
            """
with xnano.new() as canvas:
    canvas.screen.write('everywhere', x='right', y='bottom')
    canvas.open()
    canvas.screen.write(f'{canvas.screen.width}x{canvas.screen.height}')
    time.sleep(1)
""",
            rows=10,
            columns=30,
        )
        assert screen.wait_until(lambda: screen.is_alternate)
        assert screen.wait_for('30x10')
        assert screen.find('everywhere') == (20, 9)

    def test_xnano_open_takes_a_canvas_and_its_settings(self, run):
        screen = run(
            """
canvas = xnano.new(width=30, height=3, bpm=90)
with xnano.open(canvas, height=2, bpm=150, title='opened') as terminal:
    terminal.screen.write(f'BPM {terminal.clock.bpm:g} SAME {terminal is canvas}')
    terminal.run()
"""
        )
        assert screen.wait_for('BPM 150 SAME True')
        assert screen.screen.title == 'opened'
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_the_cursor_and_title_are_carried_when_a_canvas_opens(self, run):
        screen = run(
            PROMPT
            + """
with xnano.new(width=20, height=3, title='carried') as canvas:
    field = canvas.screen.write('name:', y=1)
    canvas.screen.cursor.follow(field, x=6)
    canvas.screen.cursor.shape = 'bar'
    canvas.open()
    canvas.screen.write('READY')
    time.sleep(1.5)
""",
            rows=12,
            columns=40,
        )
        assert screen.wait_for('READY')
        assert screen.wait_until(lambda: screen.cursor == (6, 4, True))
        assert screen.screen.title == 'carried'

    def test_input_works_after_open_from_the_callers_thread(self, run):
        screen = run(
            """
with xnano.new(width=30, height=2) as canvas:
    canvas.open(keyboard='release_events')
    canvas.screen.write('ready')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not canvas.keyboard.held_keys:
        time.sleep(0.02)
    canvas.screen.write(f'HELD {sorted(canvas.keyboard.held_keys)}', y=1)
    time.sleep(1)
"""
        )
        assert screen.wait_for('ready')
        screen.press('a')
        assert screen.wait_for("HELD ['a']")

    def test_a_resize_updates_the_size_of_a_canvas_with_no_hooks(self, run):
        screen = run(
            """
with xnano.new() as canvas:
    canvas.open()
    canvas.screen.write('start')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and canvas.screen.width != 50:
        time.sleep(0.02)
    canvas.screen.write(f'WIDTH {canvas.screen.width}', y=1)
    time.sleep(1)
""",
            rows=8,
            columns=30,
        )
        assert screen.wait_for('start')
        screen.resize(8, 50)
        assert screen.wait_for('WIDTH 50')

    def test_state_given_to_open_keeps_what_already_followed_the_state(self, run):
        screen = run(
            """
from dataclasses import dataclass

@dataclass
class Settings:
    volume: int = 1

seen = []
with xnano.new(width=40, height=3) as canvas:
    @canvas.hook(on='state')
    def watch(context):
        seen.append(context.root.state.get('volume'))

    placement = canvas.screen.write('hi')
    placement.state.set('clicks', 3)
    canvas.clock.step()
    canvas.open(state=Settings())
    canvas.state.set('volume', 5)
    time.sleep(0.5)
    canvas.screen.write(f'SEEN {seen[-1]} CLICKS {placement.state.get("clicks")}', y=1)
    time.sleep(1)
"""
        )
        assert screen.wait_for('SEEN 5 CLICKS 3')

    def test_a_canvas_asked_to_quit_before_it_opens_runs_on_the_screen(self, run):
        screen = run(
            """
with xnano.new(width=40, height=2) as canvas:
    canvas.screen.write('hi')
    canvas.stop()
    canvas.open()
    time.sleep(0.3)
    found = xnano.active(is_required=False) is canvas
    canvas.screen.write(f'RUNNING {canvas.is_running} ACTIVE {found}', y=1)
    time.sleep(1)
"""
        )
        assert screen.wait_for('RUNNING True ACTIVE True')

    def test_a_hook_for_state_hears_a_push_made_right_after_it_is_declared(self, run):
        screen = run(
            """
with xnano.open(width=40, height=2) as terminal:
    seen = []

    @terminal.hook(on='state')
    def watch(context):
        seen.append(context.root.state.get('x'))

    terminal.state.set('x', 1)
    time.sleep(0.5)
    terminal.screen.write(f'SEEN {seen}', y=1)
    time.sleep(1)
"""
        )
        assert screen.wait_for('SEEN [1]')

    def test_a_child_canvas_with_a_mouse_hook_is_written_into_a_screen_without_the_mouse(
        self, run
    ):
        screen = run(
            """
heard = []
child = xnano.new(width=8, height=2)
child.hook(on='mouse')(lambda context: heard.append(context.mouse.kind))
child.screen.write('WRITTEN')
with xnano.open(width=30, height=3, mouse=False) as terminal:
    terminal.screen.write(child)
    terminal.run(stop_on='q')
print('HEARD', heard)
"""
        )
        assert screen.wait_for('WRITTEN')
        screen.click(1, 0)
        screen.settle(0.4)
        screen.press('q')
        assert screen.finish() == 0
        assert 'HEARD []' in screen.text

    def test_a_canvas_created_in_the_terminal_block_hears_keys_and_shows_once_written(
        self, run
    ):
        screen = run(
            """
with xnano.open(width=30, height=4) as terminal:
    with xnano.new(height='50%') as canvas:
        canvas.screen.write('arrows')
    terminal.screen.write('HIDDEN' if 'arrows' in terminal.screen.render() else 'NOT YET', y=3)
    terminal.screen.write(canvas)

    @canvas.hook(on='key')
    def move(context):
        if context.keyboard.key == 'down':
            canvas.screen.down()
            terminal.screen.write('MOVED', x=10, y=3)

    terminal.run(stop_on='q')
"""
        )
        assert screen.wait_for('NOT YET')
        assert screen.wait_for('arrows')
        before = screen.find('arrows')
        assert before is not None
        screen.send('\x1b[B')
        assert screen.wait_for('MOVED')
        assert screen.wait_until(
            lambda: screen.find('arrows') == (before[0], before[1] + 1)
        )
        screen.send('q')
        assert screen.finish() == 0

    def test_terminal_content_written_in_a_canvas_block_moves_by_its_hooks(self, run):
        screen = run(
            """
with xnano.open(width=30, height=6) as terminal:
    terminal.screen.write('footer', y=5)
    with xnano.new(height='50%') as canvas:
        movable = terminal.screen.write('arrows', y='center')

    @canvas.hook(on='key')
    def move(context):
        if context.keyboard.key == 'down':
            movable.down()
            terminal.screen.write('MOVED', x=10, y=5)

    # Written last, so the hook is listening once it shows.
    terminal.screen.write('ready', x=25, y=0)
    terminal.run(stop_on='q')
"""
        )
        assert screen.wait_for('ready')
        before = screen.find('arrows')
        assert before is not None
        screen.send('\x1b[B')
        assert screen.wait_for('MOVED')
        assert screen.wait_until(
            lambda: screen.find('arrows') == (before[0], before[1] + 1)
        )
        screen.send('q')
        assert screen.finish() == 0

    def test_a_hook_changes_the_frame_rate_of_a_running_terminal(self, run):
        screen = run(
            """
with xnano.open(width=30, height=2, fps=60) as terminal:
    label = terminal.screen.write('fps 60')

    @terminal.hook(on='key', keys='s')
    def slow_down(context):
        context.canvas.clock.fps = 5
        label.text = f'fps {context.canvas.clock.fps:g}'

    terminal.run(stop_on='q')
"""
        )
        assert screen.wait_for('fps 60')
        screen.send('s')
        assert screen.wait_for('fps 5')
        screen.send('q')
        assert screen.finish() == 0

    def test_a_child_canvas_draws_inside_its_parent(self, run):
        screen = run(
            """
with xnano.open(width=30, height=3) as terminal:
    inner = xnano.new(width=10, height=1)
    inner.screen.write('inner')
    terminal.screen.write(inner, x=5, y=1)
    inner.screen.write('!', x=5, y=0)
    terminal.run()
"""
        )
        assert screen.wait_for('inner!')
        assert screen.find('inner!') == (5, 1)
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_a_hook_turns_on_the_mouse_gate_it_needs(self, run):
        screen = run(
            """
with xnano.new(width=30, height=2) as canvas:
    button = canvas.screen.write('[ click ]')

    @button.hook( on="mouse.kind == 'press'")
    def pressed(context):
        canvas.screen.write('CLICKED', y=1)

    canvas.open()
    canvas.run()
"""
        )
        assert screen.wait_for('[ click ]')
        screen.click(2, 0)
        assert screen.wait_for('CLICKED')
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_a_scroll_hook_registered_before_open_turns_the_wheel_on(self, run):
        screen = run(
            """
with xnano.new(width=40, height=3) as canvas:
    box = canvas.screen.write('wheel here', x=10, y=0)
    log = canvas.screen.write('', y=2)

    @box.hook(on='scroll')
    def wheel(context):
        log.text = f'wheel {context.mouse.scroll.y}'

    canvas.open()
    canvas.run()
"""
        )
        assert screen.wait_for('wheel here')
        column, row = screen.find('wheel here')
        screen.scroll(1, row, direction='down')
        screen.settle(0.4)
        assert screen.find('wheel 1') is None, 'the wheel outside the box is not heard'
        screen.scroll(column + 2, row, direction='down')
        assert screen.wait_for('wheel 1')
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_timer_hooks_registered_before_open_keep_running_on_the_screen(self, run):
        screen = run(
            """
with xnano.new(width=40, height=4, bpm=240) as canvas:
    log = canvas.screen.write('', y=1)
    beats = []
    ticks = []

    @canvas.hook(on='beat')
    def beat(context):
        beats.append(1)
        log.text = f'beats {len(beats)} ticks {len(ticks)}'

    @canvas.hook(on='tick', every=0.1)
    def tick(context):
        ticks.append(1)

    @canvas.hook(on='tick', after=0.3)
    def once(context):
        canvas.screen.write('ONCE', y=3)

    canvas.open()
    canvas.run()
"""
        )
        assert screen.wait_for('ONCE')
        assert screen.wait_for('beats 4')
        assert screen.find('ONCE') is not None
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_a_release_hook_needs_the_release_gate(self, run):
        screen = run(
            """
import xnano.errors
with xnano.new(width=40, height=3) as canvas:
    canvas.hook(lambda context: None,  on="keyboard.kind == 'release'")
    try:
        canvas.open()
    except xnano.errors.TerminalError as error:
        print('REFUSED:', "keyboard='release_events'" in str(error), isinstance(canvas, xnano.Terminal))
    canvas.open(keyboard='release_events')
    print('OPENED:', isinstance(canvas, xnano.Terminal))
"""
        )
        assert screen.wait_for('REFUSED: True False')
        assert screen.wait_for('OPENED: True')

    def test_a_scroll_hook_added_after_open_with_scroll_off_is_attached_and_never_runs(
        self, run
    ):
        screen = run(
            """
heard = []
with xnano.open(width=60, height=3, scroll=False) as terminal:
    terminal.hook(lambda context: heard.append('scroll'), on='scroll')
    terminal.screen.write('ATTACHED')
    terminal.run(stop_on='q')
print('HEARD', heard)
"""
        )
        assert screen.wait_for('ATTACHED')
        screen.scroll(1, 0, direction='down')
        screen.settle(0.4)
        screen.press('q')
        assert screen.finish() == 0
        assert 'HEARD []' in screen.text

    def test_a_gate_given_as_false_refuses_a_hook_at_open_but_not_after_it(self, run):
        screen = run(
            """
import xnano.errors
with xnano.new(width=60, height=3, mouse=False) as canvas:
    canvas.hook(lambda context: None, on='mouse')
    try:
        canvas.open()
    except xnano.errors.TerminalError as error:
        print('AT OPEN:', 'needs mouse=True' in str(error), isinstance(canvas, xnano.Terminal))
with xnano.open(width=60, height=3, mouse=False) as terminal:
    handle = terminal.hook(lambda context: None, on='mouse')
    terminal.screen.write('AFTER OPEN: ' + str(not handle.is_removed))
    time.sleep(1)
"""
        )
        assert screen.wait_for('AFTER OPEN: True')
        assert screen.finish() == 0
        assert 'AT OPEN: True False' in screen.text

    def test_a_second_screen_is_refused_and_the_canvas_stays_usable(self, run):
        screen = run(
            """
import xnano.errors
with xnano.new(width=10, height=1) as other, xnano.open(width=40, height=3) as terminal:
    other.screen.write('kept')
    try:
        other.open()
    except xnano.errors.TerminalAlreadyOpenError:
        terminal.screen.write('REFUSED ' + other.screen.render())
    time.sleep(1)
"""
        )
        assert screen.wait_for('REFUSED kept')

    def test_xnano_iter_opens_a_terminal_and_runs_it_frame_by_frame(self, run):
        screen = run(
            """
label = None
for frame in xnano.iter(height=2, fps=30, stop_on='q'):
    if label is None:
        label = frame.canvas.screen.write('READY')
    for event in frame.events:
        if event.key is not None and event.key.key == 'a':
            label.text = 'GOT A'
print('ENDED', frame.canvas.is_closed)
"""
        )
        assert screen.wait_for('READY')
        screen.press('a')
        assert screen.wait_for('GOT A')
        screen.press('q')
        assert screen.finish() == 0
        assert 'ENDED True' in screen.text

    def test_quit_ends_run_and_closes_the_canvas(self, run):
        screen = run(
            """
with xnano.new(width=30, height=2) as canvas:
    canvas.open()

    @canvas.hook(on='tick', after=0.3)
    def finish(context):
        canvas.stop()

    canvas.run(stop_on=None)
    print('CLOSED', canvas.is_closed)
"""
        )
        assert screen.finish() == 0
        assert 'CLOSED True' in screen.text

    def test_output_capture_holds_back_printed_text_after_an_attach(self, run):
        screen = run(
            """
with xnano.new(width=20, height=2) as canvas:
    canvas.open()
    canvas.screen.write('steady')
    print('HELD BACK')
    time.sleep(0.8)
    assert 'HELD BACK' in canvas.screen.output.take_captured()
print('AFTER')
"""
        )
        assert screen.wait_for('steady')
        assert 'HELD BACK' not in screen.text
        assert screen.finish() == 0
        assert 'AFTER' in screen.text

    def test_a_canvas_that_runs_by_itself_opens_on_the_screen(self, run):
        screen = run(
            """
with xnano.new(realtime=True, width=30, height=2) as canvas:
    canvas.screen.write('realtime first')
    ticks = []
    canvas.hook(on='tick', every=0.05)(lambda context: ticks.append(1))
    time.sleep(0.3)
    before = len(ticks)
    canvas.open()
    time.sleep(0.5)
    canvas.screen.write(f'TICKING {len(ticks) > before}', y=1)
    time.sleep(1)
"""
        )
        assert screen.wait_for('realtime first')
        assert screen.wait_for('TICKING True')
        assert screen.finish() == 0

    def test_keys_can_stop_resume_and_step_time(self, run):
        screen = run(
            """
with xnano.open(width=40, height=2, fps=10) as canvas:
    shown = canvas.screen.write('')

    @canvas.hook(on='key', keys='s')
    def stop(context):
        canvas.clock.pause()
        shown.text = f'STOPPED AT {round(canvas.clock.elapsed_seconds * 10)}'

    @canvas.hook(on='key', keys='n')
    def step(context):
        before = round(canvas.clock.elapsed_seconds * 10)
        canvas.clock.step()
        shown.text = f'STEPPED {round(canvas.clock.elapsed_seconds * 10) - before}'

    @canvas.hook(on='key', keys='r')
    def resume(context):
        canvas.clock.resume()
        shown.text = f'RESUMED {canvas.clock.is_paused}'

    canvas.run()
"""
        )
        assert screen.wait_until(lambda: screen.process.poll() is None and screen.lines())
        screen.settle(0.3)
        screen.press('s')
        assert screen.wait_for('STOPPED AT')
        screen.press('n')
        assert screen.wait_for('STEPPED 1')
        screen.press('r')
        assert screen.wait_for('RESUMED False')
        screen.press('ctrl+c')
        assert screen.finish() == 0


class TestFlow:
    def test_unpositioned_writes_stack_as_lines_on_the_screen(self, run):
        screen = run(
            """
with xnano.open() as terminal:
    terminal.screen.write('FIRST LINE')
    terminal.screen.write('SECOND LINE')
    terminal.screen.write('THIRD LINE')
    terminal.run()
""",
            rows=8,
            columns=30,
        )
        assert screen.wait_for('THIRD LINE')
        assert screen.find('FIRST LINE') == (0, 0)
        assert screen.find('SECOND LINE') == (0, 1)
        assert screen.find('THIRD LINE') == (0, 2)
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_a_line_below_a_panel_follows_the_window_when_the_panel_does(self, run):
        screen = run(
            """
with xnano.open() as terminal:
    terminal.screen.write(xnano.box('100%', '50%', border='plain'))
    terminal.screen.write('BELOW THE PANEL')
    terminal.run()
""",
            rows=10,
            columns=40,
        )
        assert screen.wait_for('BELOW THE PANEL')
        assert screen.find('BELOW THE PANEL') == (0, 5)
        screen.resize(16, 40)
        assert screen.wait_until(
            lambda: screen.find('BELOW THE PANEL') == (0, 8), timeout=5
        )
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_a_line_that_grows_while_running_moves_the_lines_after_it(self, run):
        screen = run(
            """
with xnano.open() as terminal:
    log = terminal.screen.write('LOG 1')
    terminal.screen.write('FOOTER')

    @terminal.hook(on='key', keys='g')
    def grow(context):
        log.text = 'LOG 1\\nLOG 2\\nLOG 3'

    terminal.run()
""",
            rows=8,
            columns=30,
        )
        assert screen.wait_for('FOOTER')
        assert screen.find('FOOTER') == (0, 1)
        screen.press('g')
        assert screen.wait_until(lambda: screen.find('FOOTER') == (0, 3), timeout=5)
        assert screen.find('LOG 3') == (0, 2)
        screen.press('ctrl+c')
        assert screen.finish() == 0


class TestFittedRegion:
    def test_a_region_that_fits_grows_below_the_prompt_with_its_lines(self, run):
        screen = run(
            PROMPT
            + """
with xnano.open(height='fit') as terminal:
    terminal.screen.write('LINE ONE')

    @terminal.hook(on='key', keys='g')
    def grow(context):
        terminal.screen.write('LINE TWO')
        terminal.screen.write('LINE THREE')

    terminal.run()
""",
            rows=12,
            columns=40,
        )
        assert screen.wait_for('LINE ONE')
        assert not screen.is_alternate
        top = screen.find('LINE ONE')[1]
        assert top == 3, 'drawn on the line below the prompt'
        screen.press('g')
        assert screen.wait_for('LINE THREE')
        assert screen.find('LINE TWO') == (0, top + 1)
        assert screen.find('LINE THREE') == (0, top + 2)
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_a_region_that_fits_scrolls_the_window_when_it_reaches_the_bottom(self, run):
        screen = run(
            PROMPT
            + """
with xnano.open(height='fit') as terminal:
    for index in range(10):
        terminal.screen.write(f'ROW {index}')
    terminal.run()
""",
            rows=8,
            columns=40,
        )
        assert screen.wait_for('ROW 7')
        assert screen.find('ROW 7') == (0, 7)
        screen.press('ctrl+c')
        assert screen.finish() == 0

    def test_no_size_still_fills_the_window(self, run):
        screen = run(
            """
with xnano.open() as terminal:
    terminal.screen.write('CENTER', width='100%', x='center', y='center')
    terminal.run()
""",
            rows=10,
            columns=40,
        )
        assert screen.wait_until(lambda: screen.is_alternate)
        assert screen.wait_for('CENTER')
        assert screen.find('CENTER') == (17, 4)
        screen.press('ctrl+c')
        assert screen.finish() == 0


class TestOpenAsync:
    def test_an_async_program_draws_and_hears_keys_while_its_loop_runs(self, run):
        screen = run(
            PROMPT
            + """
import asyncio


async def main():
    opening = xnano.open_async(height=3)
    async with opening as terminal:
        assert (await opening) is terminal
        label = terminal.screen.write('WAITING')
        ticks = [0]

        async def count():
            while True:
                ticks[0] += 1
                await asyncio.sleep(0.01)

        counter = asyncio.ensure_future(count())
        key = await terminal.keyboard.wait_async('g')
        label.text = f'GOT {key} {ticks[0] > 0}'
        await terminal.run_async(stop_on='q')
        counter.cancel()
    print('CLOSED', terminal.is_closed)


asyncio.run(main())
""",
            rows=10,
            columns=40,
        )
        assert screen.wait_for('WAITING')
        assert not screen.is_alternate
        screen.press('g')
        assert screen.wait_for('GOT g True')
        screen.press('q')
        assert screen.wait_for('CLOSED True')
        assert screen.finish() == 0

    def test_an_async_hook_answers_a_key_while_the_screen_keeps_drawing(self, run):
        screen = run(
            PROMPT
            + """
import asyncio


async def main():
    async with xnano.open_async(height=3) as terminal:
        label = terminal.screen.write('ASK')

        @terminal.hook(on='key', keys='a')
        async def answer(context):
            label.text = 'THINKING'
            await asyncio.sleep(0.05)
            label.text = 'ANSWERED'

        await terminal.run_async(stop_on='q')


asyncio.run(main())
""",
            rows=10,
            columns=40,
        )
        assert screen.wait_for('ASK')
        screen.press('a')
        assert screen.wait_for('ANSWERED')
        screen.press('q')
        assert screen.finish() == 0


class TestStoppingTime:
    def test_stopping_and_resuming_time_keeps_the_terminal_open(self, run):
        screen = run(
            """
with xnano.open() as terminal:
    terminal.screen.write('hello', x='center', y='center')
    terminal.screen.write('world')
    time.sleep(0.5)
    terminal.clock.pause()
    terminal.screen.write('STOPPED', y=2)
    time.sleep(0.5)
    terminal.clock.resume()
    terminal.screen.write('RESUMED', y=3)
    time.sleep(0.5)
print('CLOSED')
""",
            rows=10,
            columns=40,
        )
        assert screen.wait_for('STOPPED')
        assert screen.is_alternate
        assert screen.wait_for('RESUMED')
        assert screen.is_alternate
        assert screen.wait_for('CLOSED')
        assert screen.finish() == 0
