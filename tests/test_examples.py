"""
tests.test_examples

Every example in ``examples/`` runs on a live terminal and shows what it promises.
"""

from __future__ import annotations

import pathlib
import sys
import time

import pytest

pytest.importorskip('pyte')
if sys.platform == 'win32':
    pytest.skip('needs a pseudo-terminal', allow_module_level=True)
from emulator import Screen  # noqa: E402

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='needs a pseudo-terminal')

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / 'examples'


@pytest.fixture
def example():
    created: list[Screen] = []

    def start(name: str, *, rows: int = 24, columns: int = 80, arguments=()) -> Screen:
        command = [sys.executable, str(EXAMPLES / name), *arguments]
        screen = Screen(command=command, rows=rows, columns=columns)
        created.append(screen)
        return screen

    yield start
    for screen in created:
        screen.close()
        output = screen.raw.decode('utf-8', 'replace')
        assert 'Traceback' not in output, output[-1500:]
        assert 'unsendable' not in output
        assert 'Warning' not in output


def quit_with_q(screen: Screen) -> None:
    screen.press('q')
    assert screen.finish() == 0


def test_every_example_has_a_test():
    names = sorted(path.name for path in EXAMPLES.glob('[0-9][0-9]_*.py'))
    source = pathlib.Path(__file__).read_text(encoding='utf-8')
    assert names
    assert [name for name in names if f"'{name}'" not in source] == []


def test_hello(example):
    screen = example('01_hello.py', rows=10, columns=50)
    assert screen.wait_for('Hello, world!')
    assert screen.find('press q to quit') is not None
    quit_with_q(screen)
    assert 'Hello' not in screen.text


def test_layout_follows_the_window(example):
    screen = example('02_layout.py', rows=20, columns=60)
    assert screen.wait_for('centered')
    assert screen.find('top left') == (0, 0)
    assert screen.find('top right') == (60 - len('top right'), 0)
    assert screen.find('bottom left')[1] == 19
    assert screen.find('centered')[0] == (60 - len('centered')) // 2
    top = next(line for line in screen.lines() if '╭' in line)
    assert top.rstrip().endswith('╮'), 'the border closes at the panel size'
    assert len(top.strip()) == 30
    screen.resize(20, 100)
    assert screen.wait_until(
        lambda: screen.find('top right') == (100 - len('top right'), 0), timeout=5
    )
    assert screen.find('centered')[0] == (100 - len('centered')) // 2
    assert screen.wait_until(
        lambda: len(next(line for line in screen.lines() if '╭' in line).strip()) == 50
    ), 'and follows the window'
    quit_with_q(screen)


def test_animation_moves_by_itself(example):
    screen = example('03_animation.py', rows=10, columns=70)
    assert screen.wait_for('frame ')
    first = {
        row: line.find('●') for row, line in enumerate(screen.lines()) if '●' in line
    }
    assert len(first) == 3
    assert screen.wait_until(
        lambda: any(
            line.find('●') not in (-1, first[row])
            for row, line in enumerate(screen.lines())
            if row in first
        )
    )
    frames = [int(line.split()[1]) for line in screen.lines() if line.startswith('frame')]
    assert frames and frames[0] >= 0
    quit_with_q(screen)


def test_slider_follows_the_mouse(example):
    screen = example('04_slider.py', rows=10, columns=60)
    assert screen.wait_for('volume   0%')
    assert screen.find('█') == (0, 1)
    screen.drag((0, 1), (19, 1))
    assert screen.wait_until(lambda: screen.find('█') == (19, 1), timeout=5)
    assert screen.wait_for('volume  49%')
    screen.drag((19, 1), (80 - 41, 1))
    assert screen.wait_until(lambda: screen.find('█') == (39, 1), timeout=5), (
        'held in its range'
    )
    quit_with_q(screen)


def test_pixels_fill_every_cell_and_change(example):
    screen = example('05_pixels.py', rows=14, columns=64)
    assert screen.wait_until(
        lambda: sum(screen.cell(column, 11).data == '▀' for column in range(60)) >= 50
    ), 'the last row of pixels is drawn across the width'
    first = (screen.cell(10, 5).fg, screen.cell(10, 5).bg)
    assert screen.wait_until(
        lambda: (screen.cell(10, 5).fg, screen.cell(10, 5).bg) != first
    )
    quit_with_q(screen)


def test_images_can_be_panned_and_zoomed(example):
    screen = example('06_images.py', rows=24, columns=70)
    assert screen.wait_for('x 64 y 410 zoom 1x')
    assert screen.wait_until(
        lambda: screen.cell(0, 0).data != ' ' or screen.cell(0, 0).bg != 'default'
    )
    before = screen.text
    screen.press('right')
    assert screen.wait_for('x 72 y 410 zoom 1x')
    assert screen.text != before, 'panning shows other pixels'
    screen.press('up')
    assert screen.wait_for('x 72 y 402 zoom 1x')
    screen.press('+')
    assert screen.wait_for('zoom 2x')
    screen.press('-')
    screen.press('-')
    assert screen.wait_for('zoom 1x'), 'zooming out stops at one to one'
    for _ in range(80):
        screen.press('left')
    assert screen.wait_for('x 0 '), 'panning stops at the edge of the picture'
    quit_with_q(screen)


def test_images_can_come_from_a_file(example, tmp_path):
    from xnano_image import TerminalImage

    path = tmp_path / 'green.png'
    TerminalImage.from_rgba(80, 60, bytes([0, 255, 0, 255]) * 4800).save(path)
    screen = example('06_images.py', rows=24, columns=70, arguments=[str(path)])
    assert screen.wait_until(
        lambda: '00ff00' in (screen.cell(0, 0).fg, screen.cell(0, 0).bg)
    ), 'the file is shown in its colors'
    assert screen.wait_for('x 0 y 0 zoom 1x')
    quit_with_q(screen)


def test_effects_cycle(example):
    screen = example('07_effects.py', rows=10, columns=60)
    assert screen.wait_for('effect: fade_to')
    assert screen.wait_for('effect: dissolve', timeout=6)
    assert screen.wait_for('effect: coalesce', timeout=6)
    quit_with_q(screen)


def test_events_are_logged(example):
    screen = example('08_events.py', rows=14, columns=70)
    assert screen.wait_for('events (c: custom event')
    screen.press('x')
    assert screen.wait_for("key 'x' (press)")
    screen.click(5, 4)
    assert screen.wait_for('mouse press at 5,')
    screen.paste('some text')
    assert screen.wait_for("paste 'some text'")
    screen.press('c')
    assert screen.wait_for('custom hello from the example')
    screen.resize(14, 90)
    assert screen.wait_for('resize 90x')
    # A trigger that spans time: three quick taps fire it, slow ones do not.
    for _ in range(3):
        screen.press('t')
        time.sleep(0.15)
    assert screen.wait_for('triple tap of t')
    for _ in range(3):
        screen.press('t')
        time.sleep(1.0)
    screen.settle(0.3)
    assert sum('triple tap of t' in line for line in screen.lines()) == 1
    quit_with_q(screen)


def test_state_drives_the_gauge(example):
    screen = example('09_state.py', rows=8, columns=50)
    assert screen.wait_for('volume 40')
    assert screen.wait_until(lambda: screen.lines()[2].count('█') == 16)
    screen.press('up')
    assert screen.wait_for('volume 45')
    assert screen.wait_until(lambda: screen.lines()[2].count('█') == 17), (
        'the gauge follows'
    )
    for _ in range(4):
        screen.press('up')
    assert screen.wait_until(
        lambda: (screen.cell(17, 2).fg, screen.cell(17, 2).bg) == ('282828', '00c800')
    ), 'the label turns around the colors once the bar is under it'
    screen.press('m')
    assert screen.wait_for('muted')
    quit_with_q(screen)


def test_audio_keys(example):
    screen = example('10_audio.py', rows=14, columns=70)
    assert screen.wait_for('up/down: instrument')
    for name in ('piano', 'bell', 'kick', 'cowbell', 'electric_guitar'):
        assert screen.find(name) is not None, f'{name} is in the list of instruments'
    assert screen.wait_until(
        lambda: screen.cell(2, 2).bg != 'default' or screen.cell(2, 2).fg == 'default'
    )
    screen.press('a')
    assert screen.wait_for('C4   on piano')
    screen.press('down')
    assert screen.wait_for('instrument: electric_piano')
    screen.press('right')
    assert screen.wait_for('instrument: ')
    screen.press('left')
    assert screen.wait_for('instrument: electric_piano')
    screen.press('k')
    assert screen.wait_for('C5   on electric_piano')
    screen.press('d')
    assert screen.wait_for('E4   on electric_piano'), (
        'the third key is a major third above the root'
    )
    screen.press(' ')
    assert screen.wait_for('chord C4 E4 G4 on electric_piano')
    screen.press('m')
    assert screen.wait_for('tune of 7 notes on electric_piano')
    quit_with_q(screen)


def test_text_field(example):
    screen = example('11_text_field.py', rows=10, columns=60)
    assert screen.wait_for('Your name:')
    for letter in 'Adx':
        screen.press(letter)
    screen.send(b'\x7f')
    screen.press('a')
    assert screen.wait_for('Your name: Ada')
    assert screen.wait_until(lambda: screen.cursor == (len('Your name: ') + 3, 0, True))
    assert b'\x1b[5 q' in screen.raw, 'the cursor is a blinking bar'
    screen.press('enter')
    assert screen.wait_for('Hello, Ada!')
    assert screen.wait_for('press escape to leave')
    screen.press('escape')
    assert screen.finish() == 0


def test_widgets(example):
    screen = example('12_widgets.py', rows=12, columns=60)
    assert screen.wait_for('history')
    assert screen.find('╭') is not None
    assert screen.find('╮') is not None, 'the border closes at the block size'
    first = screen.text
    assert screen.wait_until(lambda: screen.text != first, timeout=5)
    quit_with_q(screen)


def test_menu(example):
    screen = example('13_menu.py', rows=10, columns=40)
    assert screen.wait_for('> New game')
    screen.press('down')
    assert screen.wait_for('> Continue')
    screen.press('enter')
    assert screen.wait_for('chose Continue')
    screen.press('up')
    screen.press('up')
    assert screen.wait_for('> New game'), 'the highlight stops at the first choice'
    for _ in range(5):
        screen.press('down')
    assert screen.wait_for('> Quit'), 'the highlight stops at the last choice'
    screen.press('enter')
    assert screen.finish() == 0


def test_dashboard(example):
    screen = example('14_dashboard.py', rows=20, columns=64)
    assert screen.wait_for('requests')
    assert screen.wait_for('services')
    assert screen.wait_for('latency')
    first = screen.text
    assert screen.wait_until(lambda: screen.text != first, timeout=5), (
        'the charts and the table follow the timer'
    )
    quit_with_q(screen)


def test_canvas(example):
    screen = example('15_canvas.py', rows=18, columns=54)
    assert screen.wait_for('orbit')
    assert screen.wait_for('sun')
    first = screen.text
    assert screen.wait_until(lambda: screen.text != first, timeout=5), 'the planet moves'
    quit_with_q(screen)


def test_snake(example):
    screen = example('16_snake.py', rows=14, columns=40)
    assert screen.wait_for('score ')
    assert screen.wait_for('crashed: r to restart', timeout=40), (
        'a snake that is not steered runs into the wall'
    )
    screen.press('r')
    assert screen.wait_for('score ')
    quit_with_q(screen)


def test_tabs(example):
    screen = example('17_tabs.py', rows=14, columns=50)
    assert screen.wait_for('xnano draws on a terminal')
    screen.press('right')
    assert screen.wait_for('October 2026')
    assert screen.find('xnano draws') is None, 'only the selected page shows'
    screen.press('right')
    assert screen.wait_for('ratatui')
    screen.press('right')
    assert screen.wait_for('xnano draws on a terminal'), 'the tabs wrap around'
    quit_with_q(screen)


def test_paint(example):
    screen = example('18_paint.py', rows=16, columns=54)
    assert screen.wait_for('drag to paint')
    screen.drag((5, 4), (15, 4))
    assert screen.wait_until(
        lambda: {screen.cell(10, 4).fg, screen.cell(10, 4).bg} & {'ff3030'}
    ), 'the drag paints the first color'
    screen.press('3')
    screen.drag((5, 8), (15, 8))
    assert screen.wait_until(
        lambda: {screen.cell(10, 8).fg, screen.cell(10, 8).bg} & {'00c800'}
    ), 'the color keys change the brush'
    screen.press('c')
    assert screen.wait_until(
        lambda: 'ff3030' not in {screen.cell(10, 4).fg, screen.cell(10, 4).bg}
    ), 'c clears the painting'
    quit_with_q(screen)


def test_progress(example):
    screen = example('19_progress.py', rows=6, columns=50)
    assert screen.wait_for('Processing files')
    assert screen.finish() == 0, 'the job ends by itself'
    output = screen.raw.decode('utf-8', 'replace')
    assert 'xnano job: 100%' in output, 'the window title follows the progress'
    assert 'finished file 20 of 20' in output, (
        'printed text appears when the screen closes'
    )
    assert 'stopped after 20 of 20 files' in output


def hero_position(screen: Screen) -> tuple[int, int]:
    import re

    match = re.search(r'x\s+(\d+) y\s+(\d+)', screen.text)
    assert match, screen.text
    return int(match.group(1)), int(match.group(2))


def test_world(example):
    screen = example('20_world.py', rows=25, columns=80)
    assert screen.wait_for('hold the mouse')
    assert screen.wait_until(lambda: screen.cell(10, 5).bg != 'default'), (
        'the terrain is drawn'
    )
    start = hero_position(screen)
    before = screen.text
    screen.settle(0.5)
    written = len(screen.raw)
    screen.settle(1.0)
    assert len(screen.raw) == written, 'a screen that does not change writes nothing'
    for _ in range(6):
        screen.press('right')
        screen.settle(0.05)
    assert screen.wait_until(lambda: hero_position(screen)[0] > start[0]), (
        'holding a key walks the hero'
    )
    screen.settle(0.8)  # a terminal without key releases guesses the key is still held
    walked = hero_position(screen)
    assert walked[1] == start[1]
    screen.click(10, 3)

    def arrived() -> bool:
        before_wait = hero_position(screen)
        screen.settle(0.5)
        return hero_position(screen) == before_wait

    assert screen.wait_until(arrived, timeout=15), 'the hero stops at its target'
    assert hero_position(screen)[0] < walked[0], 'a click walks the hero toward that spot'
    assert screen.text != before
    held_from = hero_position(screen)
    screen.drag((40, 3), (70, 3))
    assert screen.wait_until(
        lambda: hero_position(screen)[0] > held_from[0] + 5, timeout=10
    ), 'holding the mouse button walks the hero toward the pointer'
    screen.press(' ')
    assert screen.wait_for('paused')
    frozen = hero_position(screen)
    screen.drag((5, 3), (6, 3))
    screen.settle(1.0)
    assert hero_position(screen) == frozen, 'while time is stopped the hero stands still'
    screen.press(' ')
    assert screen.wait_until(
        lambda: 'paused' not in screen.text and hero_position(screen) != frozen,
        timeout=10,
    ), 'and walks on once time runs again'
    quit_with_q(screen)


def test_world_fits_a_resized_window(example):
    screen = example('20_world.py', rows=25, columns=80)
    assert screen.wait_for('hold the mouse')
    screen.resize(31, 100)
    assert screen.wait_until(
        lambda: len(screen.lines()) > 30 and 'hold the mouse' in screen.lines()[30],
        timeout=10,
    ), 'the status line moves to the last row of the larger window'
    assert screen.cell(99, 29).bg != 'default', 'the terrain reaches the right edge'
    quit_with_q(screen)


def test_melody(example):
    screen = example('21_melody.py', rows=6, columns=60)
    assert screen.wait_for('120 beats per minute')
    assert screen.wait_for('beat 2', timeout=5), (
        'a beat is half a second at 120 beats per minute'
    )
    screen.press('up')
    assert screen.wait_for('130 beats per minute')
    screen.press('m')
    screen.press(' ')
    assert screen.wait_for('paused')
    stopped = screen.text
    screen.settle(1.2)
    assert screen.text == stopped, 'the beat waits while time is stopped'
    screen.press(' ')
    assert screen.wait_for('playing')
    quit_with_q(screen)


def test_song(example):
    screen = example('22_song.py', rows=9, columns=70)
    assert screen.wait_for('A song written as text')
    assert screen.wait_for('beat 2', timeout=6), 'the bars keep time'
    screen.press(' ')
    stopped = screen.text
    screen.settle(1.0)
    assert screen.text == stopped, 'the song waits while time is stopped'
    screen.press(' ')
    assert screen.wait_until(lambda: screen.text != stopped, timeout=6)
    quit_with_q(screen)


def test_sprites(example):
    screen = example('23_sprites.py', rows=13, columns=84)
    assert screen.wait_for('pixel art, written as text')
    for name in ('heart', 'star', 'mushroom', 'slime'):
        assert screen.wait_for(name)
    first = (screen.cell(70, 4).fg, screen.cell(70, 4).bg)
    assert screen.wait_until(
        lambda: (screen.cell(70, 4).fg, screen.cell(70, 4).bg) != first, timeout=6
    ), 'the slime animates'
    assert screen.cell(6, 4).bg != 'default', 'the heart is drawn'
    quit_with_q(screen)


def test_dusk_refits_when_the_window_is_resized(example):
    screen = example('24_dusk.py', rows=30, columns=100)
    assert screen.wait_for('resize the window')

    def colored() -> int:
        return sum(
            1
            for row in range(screen.rows)
            for column in range(screen.columns)
            if screen.cell(column, row).bg != 'default'
        )

    assert screen.wait_until(lambda: colored() > screen.rows * screen.columns * 0.9)
    thumbnail = screen.find('resize')[0]
    screen.resize(44, 140)
    assert screen.wait_until(lambda: screen.rows == 44 and colored() > 44 * 140 * 0.9), (
        'unlocked art fills the larger window'
    )
    assert screen.find('resize') is not None
    assert screen.wait_until(lambda: screen.cell(135, 40).bg != 'default')
    assert thumbnail != screen.find('resize')[0], 'the caption stays centered'
    quit_with_q(screen)


def test_the_demo_opens_with_the_animation_and_then_fills_the_window():
    screen = Screen(command=[sys.executable, '-m', 'xnano'], rows=40, columns=140)
    try:
        assert screen.wait_for('press any key')
        assert screen.find('█') is not None, 'the wordmark is drawn over the animation'

        def look() -> tuple[tuple[str, str], ...]:
            return tuple(
                (screen.cell(column, row).fg, screen.cell(column, row).bg)
                for column in range(0, 140, 7)
                for row in range(0, 40, 3)
            )

        first = look()
        assert screen.wait_until(lambda: look() != first, timeout=6), (
            'the animation plays'
        )
        screen.press('x')
        for title in (
            'expressions',
            'widgets',
            'features',
            'pixel art',
            'canvas',
            'sound',
        ):
            assert screen.wait_for(title), f'the {title} panel is shown'
        assert screen.wait_for('calendar') and screen.wait_for('events')
        screen.press('tab')
        assert screen.wait_for('instrument: bell')
        screen.press('e')
        assert screen.wait_for('effect: coalesce')
        screen.resize(30, 100)
        assert screen.wait_until(
            lambda: screen.rows == 30 and screen.find('events') is not None, timeout=10
        ), 'the panels follow the window'
        screen.press('q')
        assert screen.finish() == 0
    finally:
        screen.close()
        assert 'Traceback' not in screen.raw.decode('utf-8', 'replace')
