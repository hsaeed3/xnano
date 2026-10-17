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
    terminal.write('Hello, world!')
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
    terminal.write('HELLO-NOW', x=2)
    time.sleep(8)
"""
        )
        assert screen.wait_for('HELLO-NOW', timeout=4)
        assert screen.process.poll() is None
        assert screen.find('HELLO-NOW') == (2, 0)

    def test_a_persistent_region_stays_after_exit(self, run):
        screen = run(
            """
with xnano.open(height=2, clear=False) as terminal:
    terminal.write('stays')
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
    terminal.write('bottom')
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
    terminal.write('FULL SCREEN', x=3, y=2)
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
    terminal.write('MAIN SCREEN')
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
    terminal.write('press q')

    @terminal.hook(when=lambda context: context.keyboard.key is not None and context.keyboard.key == 'q')
    def quit(context):
        context.canvas.quit()

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
    terminal.write('waiting')
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
    button = terminal.write('[ click ]', x=4, y=1)

    @button.hook(when=lambda context: context.mouse.position is not None and context.mouse.kind == 'press')
    def pressed(context):
        context.canvas.write('CLICKED', x=0, y=0)

    terminal.run()
"""
        )
        assert screen.wait_for('[ click ]')
        screen.click(0, 0)
        screen.settle(0.3)
        assert screen.find('CLICKED') is None, 'a click elsewhere is not heard'
        screen.click(6, 1)
        assert screen.wait_for('CLICKED')

    def test_a_click_in_a_region_below_the_prompt_lands_on_the_right_cell(self, run):
        screen = run(
            PROMPT
            + """
with xnano.open(width=20, height=3, mouse=True) as terminal:
    button = terminal.write('[ click ]', x=4, y=1)

    @button.hook(when=lambda context: context.mouse.position is not None and context.mouse.kind == 'press')
    def pressed(context):
        context.canvas.write('CLICKED', x=0, y=0)

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
    terminal.write('-' * 30, y=1)
    thumb = terminal.write('#', x=(0, 29), y=1, layer=1)

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
    terminal.write('paste here')

    @terminal.hook(when=lambda context: context.clipboard.text is not None)
    def pasted(context):
        context.canvas.write('GOT:' + context.clipboard.text, x=0, y=1)

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
    label = terminal.write('count: 0')

    @terminal.hook(on='key', keys='a')
    def count(context):
        state = context.root.state
        state.push('count', state.get('count', default=0) + 1)

    @terminal.hook(on='state')
    def show(context):
        label.text = f"count: {context.root.state.get('count', default=0)}"

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
    ball = terminal.write('o')
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
    ball = terminal.write('o')
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
    pixels = terminal.region.half_blocks
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
    terminal.write(xnano.Image(image))
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
    placement = terminal.write('hello')
    placement.core_buffer.update(Effect.fade_to((255, 0, 0), duration_milliseconds=600))
    time.sleep(2)
"""
        )
        assert screen.wait_for('hello')
        assert screen.wait_until(lambda: screen.cell(0, 0).fg == 'ff0000', timeout=5)

    def test_border_draws_around_art_and_widgets(self, run):
        screen = run(
            """
from xnano.widgets import Gauge
art = xnano.draw(['RR', 'RR'], {'R': '#ff0000'})
with xnano.open(width=14, height=6) as terminal:
    terminal.write(art, border='rounded')
    terminal.write(Gauge(ratio=0.5, width=6, height=1), x=6, border='plain')
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
canvas.border = 'plain'
canvas.open()
time.sleep(0.3)
canvas.write(f'dirty={len(canvas._dirty_looks)} demand={canvas._frame_demand}', x=1, y=1)
time.sleep(1.5)
"""
        )
        assert screen.wait_for('dirty=0 demand=0')

    def test_a_component_that_reads_the_time_keeps_drawing(self, run):
        screen = run(
            """
@xnano.renderable
def clock(context):
    return str(int(context.time.elapsed))

with xnano.open(width=6, height=1) as terminal:
    terminal.write(clock)
    time.sleep(4)
"""
        )
        assert screen.wait_for('0')
        assert screen.wait_until(lambda: '2' in screen.text, timeout=6)

    def test_a_component_wakes_on_a_key(self, run):
        screen = run(
            """
@xnano.renderable
def last(context):
    return context.keyboard.key or '-'

with xnano.open(width=6, height=1) as terminal:
    terminal.write(last)
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
    terminal.write(Buffer.from_cell_grid(grid))
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
    terminal.write('field:')
    terminal.cursor.position = (7, 1)
    terminal.cursor.shape = 'bar'
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
    terminal.write('moved')
    terminal.cursor.home().right(5).down(2)
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
    terminal.write('no cursor')
    terminal.cursor.is_visible = False
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
    terminal.write('right', x='100%', y=0)
    terminal.write('middle', x='50%', y=1)
    terminal.run()
""",
            rows=8,
            columns=30,
        )
        assert screen.wait_for('middle')
        assert screen.find('middle') == (15, 1)
        screen.resize(8, 50)
        assert screen.wait_until(lambda: screen.find('middle') == (25, 1), timeout=5)


class TestInlineResize:
    def test_a_resize_hook_sees_the_size_of_the_inline_region(self, run):
        screen = run(
            """
with xnano.open(height=4) as terminal:
    terminal.write('region')
    sizes = []

    @terminal.hook(on='resize')
    def resized(context):
        sizes.append((terminal.size.width, terminal.size.height))
        terminal.write('SIZES ' + repr(sizes[-1]).replace(' ', ''), y=1)

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
    terminal.write('steady')
    print('A LOG LINE')
    sys.stderr.write('AN ERROR LINE\\n')
    time.sleep(1)
    assert 'A LOG LINE' in terminal.output.take_captured()
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
    terminal.write('steady')
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
    terminal.write('CAPTURED' if terminal.output.is_captured else 'OPEN')
    time.sleep(0.8)
"""
        )
        assert screen.wait_for('CAPTURED')

    def test_it_can_be_turned_off(self, run):
        screen = run(
            """
with xnano.open(height=2, capture=False) as terminal:
    terminal.write('CAPTURED' if terminal.output.is_captured else 'OPEN')
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
        terminal.write('REFUSED', x=0, y=0)
    time.sleep(0.8)
"""
        )
        assert screen.wait_for('REFUSED')

    def test_an_error_in_the_program_restores_the_terminal(self, run):
        screen = run(
            """
with xnano.open(height=2) as terminal:
    terminal.write('about to fail')
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
    terminal.title = 'Changed title'
    terminal.write('TITLE READY')
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
            "    terminal.write('alive')\n"
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
    terminal.write('ready')
    log = terminal.write('', y=1)
    heard = []

    @terminal.hook
    def listen(context):
        if context.mouse.kind is not None:
            heard.append(context.mouse.kind)
        if context.scroll.x or context.scroll.y:
            heard.append('scroll')
        if context.keyboard.key is not None:
            heard.append('key:' + str(context.keyboard.key))
        if context.clipboard.text is not None:
            heard.append('paste:' + context.clipboard.text)
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
    canvas.write('built off the screen')
    heard = canvas.write('', y=1)

    @canvas.hook(on='key', keys='k')
    def key(context):
        heard.text = 'KEY HEARD'

    canvas.step()
    terminal = canvas.open()
    assert terminal is canvas and isinstance(canvas, xnano.Terminal)
    canvas.write('OPENED', y=2)
    canvas.run(quit_on='q')
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
        canvas.write(f'FIRED AT {context.time.elapsed:.1f}', y=1)

    canvas.step(delta_seconds=5.0)
    canvas.open()
    canvas.write(f'OPENED AT {canvas.time.elapsed:.1f}')
    time.sleep(2)
"""
        )
        assert screen.wait_for('OPENED AT 5.')
        assert screen.wait_for('FIRED AT 5.')

    def test_a_stopped_canvas_stays_stopped_when_it_opens(self, run):
        screen = run(
            """
with xnano.new(width=40, height=3) as canvas:
    canvas.step(delta_seconds=2.0)
    canvas.stop()
    canvas.open()
    time.sleep(0.5)
    canvas.write(f'STOPPED {canvas.time.is_stopped} AT {canvas.time.elapsed:.2f}')
    canvas.step()
    canvas.write(f'STEPPED TO {canvas.time.elapsed:.3f}', y=1)
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
    @xnano.renderable
    def shown(context):
        return 'v=%s' % context.root.state.get('volume', 'none')

    heard = canvas.write('', y=2)

    @canvas.hook(on='state')
    def hear(context):
        heard.text = 'HEARD %s' % context.root.state.get('volume', 'none')

    canvas.write(shown)
    canvas.step(delta_seconds=0.2)
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
    canvas.write('faded')
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
    canvas.write('faded')
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
    canvas.write('hi')
    try:
        canvas.open(margin='x')
    except TypeError:
        print('REFUSED', type(canvas).__name__, canvas.is_closed)
    canvas.step()
"""
        )
        assert screen.wait_for('REFUSED Canvas False')
        assert screen.finish() == 0

    def test_open_draws_inline_at_the_size_given_to_new(self, run):
        screen = run(
            PROMPT
            + """
with xnano.new(width=12, height=2) as canvas:
    canvas.write('inline', x='right')
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
    canvas.write('everywhere', x='right', y='bottom')
    canvas.open()
    canvas.write(f'{canvas.width}x{canvas.height}')
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
    terminal.write(f'BPM {terminal.bpm:g} SAME {terminal is canvas}')
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
    field = canvas.write('name:', y=1)
    canvas.cursor.follow(field, x=6)
    canvas.cursor.shape = 'bar'
    canvas.open()
    canvas.write('READY')
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
    canvas.write('ready')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not canvas.input.held_keys:
        time.sleep(0.02)
    canvas.write(f'HELD {sorted(canvas.input.held_keys)}', y=1)
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
    canvas.write('start')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and canvas.width != 50:
        time.sleep(0.02)
    canvas.write(f'WIDTH {canvas.width}', y=1)
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

    placement = canvas.write('hi')
    placement.state.push('clicks', 3)
    canvas.step()
    canvas.open(state=Settings())
    canvas.state.push('volume', 5)
    time.sleep(0.5)
    canvas.write(f'SEEN {seen[-1]} CLICKS {placement.state.get("clicks")}', y=1)
    time.sleep(1)
"""
        )
        assert screen.wait_for('SEEN 5 CLICKS 3')

    def test_a_canvas_asked_to_quit_before_it_opens_runs_on_the_screen(self, run):
        screen = run(
            """
with xnano.new(width=40, height=2) as canvas:
    canvas.write('hi')
    canvas.quit()
    canvas.open()
    time.sleep(0.3)
    found = xnano.active(is_required=False) is canvas
    canvas.write(f'RUNNING {canvas.is_running} ACTIVE {found}', y=1)
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

    terminal.state.push('x', 1)
    time.sleep(0.5)
    terminal.write(f'SEEN {seen}', y=1)
    time.sleep(1)
"""
        )
        assert screen.wait_for('SEEN [1]')

    def test_a_child_canvas_with_a_mouse_hook_is_refused_by_a_screen_without_the_mouse(
        self, run
    ):
        screen = run(
            """
with xnano.open(width=30, height=3, mouse=False) as terminal:
    child = xnano.new(width=8, height=2)
    child.hook(on='mouse')(lambda context: None)
    try:
        terminal.write(child)
    except xnano.errors.TerminalError as error:
        terminal.write('REFUSED', y=1)
    time.sleep(1)
"""
        )
        assert screen.wait_for('REFUSED')

    def test_a_child_canvas_draws_inside_its_parent(self, run):
        screen = run(
            """
with xnano.open(width=30, height=3) as terminal:
    inner = xnano.new(width=10, height=1)
    inner.write('inner')
    terminal.write(inner, x=5, y=1)
    inner.write('!', x=5)
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
    button = canvas.write('[ click ]')

    @button.hook(on='mouse', when="mouse.kind == 'press'")
    def pressed(context):
        canvas.write('CLICKED', y=1)

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
    box = canvas.write('wheel here', x=10, y=0)
    log = canvas.write('', y=2)

    @box.hook(on='scroll')
    def wheel(context):
        log.text = f'wheel {context.scroll.y}'

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
    log = canvas.write('', y=1)
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
        canvas.write('ONCE', y=3)

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
    canvas.hook(lambda context: None, on='key', when="keyboard.kind == 'release'")
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

    def test_a_scroll_hook_added_after_open_with_scroll_off_is_refused(self, run):
        screen = run(
            """
import xnano.errors
with xnano.open(width=60, height=3, scroll=False) as terminal:
    try:
        terminal.hook(lambda context: None, on='scroll')
    except xnano.errors.TerminalError as error:
        terminal.write('AFTER OPEN: ' + str('scroll=True' in str(error)))
    time.sleep(1)
"""
        )
        assert screen.wait_for('AFTER OPEN: True')

    def test_a_hook_for_a_gate_that_is_off_raises_a_teaching_error(self, run):
        screen = run(
            """
import xnano.errors
with xnano.new(width=60, height=3, mouse=False) as canvas:
    canvas.hook(lambda context: None, on='mouse')
    try:
        canvas.open()
    except xnano.errors.TerminalError as error:
        print('AT OPEN:', 'needs mouse=True' in str(error), isinstance(canvas, xnano.Terminal))
with xnano.open(width=60, height=3) as terminal:
    try:
        terminal.hook(lambda context: None, on='mouse')
    except xnano.errors.TerminalError as error:
        terminal.write('AFTER OPEN: ' + str('mouse=True' in str(error)))
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
with xnano.open(width=40, height=3) as terminal:
    with xnano.new(width=10, height=1) as other:
        other.write('kept')
        try:
            other.open()
        except xnano.errors.TerminalAlreadyOpenError:
            terminal.write('REFUSED ' + other.render())
    time.sleep(1)
"""
        )
        assert screen.wait_for('REFUSED kept')

    def test_quit_ends_run_and_closes_the_canvas(self, run):
        screen = run(
            """
with xnano.new(width=30, height=2) as canvas:
    canvas.open()

    @canvas.hook(on='tick', after=0.3)
    def finish(context):
        canvas.quit()

    canvas.run(quit_on=None)
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
    canvas.write('steady')
    print('HELD BACK')
    time.sleep(0.8)
    assert 'HELD BACK' in canvas.output.take_captured()
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
    canvas.write('realtime first')
    ticks = []
    canvas.hook(on='tick', every=0.05)(lambda context: ticks.append(1))
    time.sleep(0.3)
    before = len(ticks)
    canvas.open()
    time.sleep(0.5)
    canvas.write(f'TICKING {len(ticks) > before}', y=1)
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
    shown = canvas.write('')

    @canvas.hook(on='key', keys='s')
    def stop(context):
        canvas.stop()
        shown.text = f'STOPPED AT {round(canvas.time.elapsed * 10)}'

    @canvas.hook(on='key', keys='n')
    def step(context):
        before = round(canvas.time.elapsed * 10)
        canvas.step()
        shown.text = f'STEPPED {round(canvas.time.elapsed * 10) - before}'

    @canvas.hook(on='key', keys='r')
    def resume(context):
        canvas.resume()
        shown.text = f'RESUMED {canvas.time.is_stopped}'

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
