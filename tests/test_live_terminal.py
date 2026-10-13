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
    terminal.add('Hello, world!')
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
    terminal.add('HELLO-NOW', x=2)
    time.sleep(8)
"""
        )
        assert screen.wait_for('HELLO-NOW', timeout=4)
        assert screen.process.poll() is None
        assert screen.find('HELLO-NOW') == (2, 0)

    def test_a_persistent_region_stays_after_exit(self, run):
        screen = run(
            """
with xnano.open(inline_height=2) as terminal:
    terminal.add('stays')
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
    terminal.add('bottom')
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
    terminal.add('FULL SCREEN', x=3, y=2)
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
with xnano.open(should_use_alternate_screen=False) as terminal:
    terminal.add('MAIN SCREEN')
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
    terminal.add('press q')

    @terminal.hook(when=lambda context: context.keyboard is not None and context.keyboard.key == 'q')
    def quit(context):
        context.terminal.stop()

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
    terminal.add('waiting')
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
with xnano.open(height=3, mouse='buttons') as terminal:
    button = terminal.add('[ click ]', x=4, y=1)

    @button.hook(when=lambda context: context.mouse is not None and context.mouse.kind == 'press')
    def pressed(context):
        context.terminal.write('CLICKED', x=0, y=0)

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
with xnano.open(width=20, height=3, mouse='buttons') as terminal:
    button = terminal.add('[ click ]', x=4, y=1)

    @button.hook(when=lambda context: context.mouse is not None and context.mouse.kind == 'press')
    def pressed(context):
        context.terminal.write('CLICKED', x=0, y=0)

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
with xnano.open(height=3, width=30, mouse='buttons') as terminal:
    terminal.add('-' * 30, y=1)
    thumb = terminal.add('#', x=(0, 29), y=1, layer=1)
    thumb.make_draggable()
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
    terminal.add('paste here')

    @terminal.hook(when=lambda context: context.pasted is not None)
    def pasted(context):
        context.terminal.write('GOT:' + context.pasted, x=0, y=1)

    terminal.run()
"""
        )
        assert screen.wait_for('paste here')
        screen.paste('two words')
        assert screen.wait_for('GOT:two words')


class TestDrawing:
    def test_a_formula_moves_without_being_driven(self, run):
        screen = run(
            """
from xnano_core import TimeElapsed, ParentWidth, Width
with xnano.open(width=30, height=1) as terminal:
    ball = terminal.add('o')
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
    ball = terminal.add('o')
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
    pixels = terminal.pixels()
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
    terminal.add(image)
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
    placement = terminal.add('hello')
    placement.buffer.update(Effect.fade_to((255, 0, 0), duration_milliseconds=600))
    time.sleep(2)
"""
        )
        assert screen.wait_for('hello')
        assert screen.wait_until(lambda: screen.cell(0, 0).fg == 'ff0000', timeout=5)


class TestGraphicsProtocols:
    """The escape sequences of each protocol reach the terminal; the emulator cannot draw them."""

    SCRIPT = """
from xnano_image import TerminalGraphics, TerminalImage
image = TerminalImage.from_rgba(16, 16, bytes([255, 0, 0, 255]) * 256)
graphics = TerminalGraphics.from_capabilities(protocol={protocol!r}, cell_size_in_pixels=(8, 16))
grid = image.to_cell_grid(4, 2, graphics=graphics)
with xnano.open(width=10, height=3) as terminal:
    terminal.add(grid)
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
    terminal.add('field:')
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

    def test_a_hidden_cursor_stays_hidden(self, run):
        screen = run(
            """
with xnano.open(width=12, height=2) as terminal:
    terminal.add('no cursor')
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
    terminal.add('right', x='100%', y=0)
    terminal.add('middle', x='50%', y=1)
    terminal.run()
""",
            rows=8,
            columns=30,
        )
        assert screen.wait_for('middle')
        assert screen.find('middle') == (15, 1)
        screen.resize(8, 50)
        assert screen.wait_until(lambda: screen.find('middle') == (25, 1), timeout=5)


class TestOutputCapture:
    def test_prints_do_not_corrupt_the_screen_and_arrive_afterwards(self, run):
        screen = run(
            """
import sys
with xnano.open(height=2) as terminal:
    terminal.add('steady')
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
    terminal.add('steady')
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
with xnano.open(height=2, should_capture_output=False) as terminal:
    terminal.write('CAPTURED' if terminal.output.is_captured else 'OPEN')
    time.sleep(0.8)
"""
        )
        assert screen.wait_for('OPEN')


class TestMisuse:
    def test_a_second_live_terminal_is_refused_with_advice(self, run):
        screen = run(
            """
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
    terminal.add('about to fail')
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
    terminal.add('TITLE READY')
    terminal.run()
""")
    assert screen.wait_for('TITLE READY')
    assert screen.screen.title == 'Changed title'
    screen.press('ctrl+c')
    assert screen.finish() == 0
    assert b'Initial title' in screen.raw
    assert b'Changed title' in screen.raw
