"""
tests.test_examples

Every example in ``examples/`` runs on a live terminal and shows what it promises.
"""

from __future__ import annotations

import pathlib
import re
import sys
import time

import pytest

pytest.importorskip('pyte')
if sys.platform == 'win32':
    pytest.skip('needs a pseudo-terminal', allow_module_level=True)
from emulator import Screen  # noqa: E402
from xnano_audio import TerminalAudioPlayer  # noqa: E402

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


def test_slider_follows_the_arrow_keys(example):
    screen = example('04_slider.py', rows=10, columns=60)
    assert screen.wait_for('volume   0%')
    screen.press('right')
    screen.press('right')
    assert screen.wait_until(lambda: screen.find('█') == (4, 1), timeout=5)
    screen.press('left')
    assert screen.wait_until(lambda: screen.find('█') == (2, 1), timeout=5)
    for _ in range(3):
        screen.press('left')
    assert screen.wait_until(lambda: screen.find('█') == (0, 1), timeout=5), (
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
        assert screen.wait_for(name), f'{name} is in the list of instruments'
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
    assert 'finished file 21' not in output, 'no timer runs after quit()'


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
    assert screen.wait_for('beat 2', timeout=15), 'the bars keep time'
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


def test_cursor(example):
    screen = example('25_cursor.py', rows=10, columns=60)
    assert screen.wait_for('arrows move the cursor')
    assert screen.wait_until(lambda: screen.cursor == (0, 2, True))
    screen.press('right')
    screen.press('right')
    screen.press('down')
    assert screen.wait_until(lambda: screen.cursor == (2, 3, True))
    assert screen.wait_for('column 2   row 3')
    screen.press('left')
    screen.press('left')
    screen.press('left')
    assert screen.wait_until(lambda: screen.cursor == (0, 3, True)), 'stops at the edge'
    screen.press('h')
    assert screen.wait_until(lambda: screen.cursor == (0, 0, True))
    screen.press('s')
    assert screen.wait_for('shape bar')
    assert b'\x1b[5 q' in screen.raw, 'a blinking bar'
    quit_with_q(screen)


def test_canvas_stops_resumes_and_steps_from_the_keyboard(example):
    pattern = re.compile(r'frame \d+ at ([\d.]+) seconds')

    def elapsed(screen: Screen) -> float:
        return float(pattern.findall(screen.text)[-1])

    screen = example('26_canvas.py', rows=12, columns=70)
    assert screen.wait_for('time runs')
    lines = screen.lines()
    assert lines[:3] == [
        'frame 0 at 0.0 seconds',
        'frame 1 at 0.1 seconds',
        'frame 2 at 0.2 seconds',
    ], 'the screenless part prints the same frames on every run'
    assert lines[3].startswith('this canvas runs by itself'), (
        'a canvas that runs by itself'
    )
    column, row = screen.find('this canvas runs by itself')
    assert screen.cell(column, row).fg == 'green', (
        'render(format="ansi") keeps the colors'
    )
    screen.press(' ')
    assert screen.wait_for('time stopped')
    screen.settle(0.3)
    frozen = elapsed(screen)
    screen.settle(0.6)
    assert elapsed(screen) == frozen, 'a stopped canvas keeps its time'
    screen.press('n')
    assert screen.wait_until(lambda: 0.05 < elapsed(screen) - frozen < 0.15)
    assert 'time stopped' in screen.text, 'a step leaves the canvas stopped'
    screen.press(' ')
    assert screen.wait_for('time runs')
    assert screen.wait_until(lambda: elapsed(screen) > frozen + 0.5)
    quit_with_q(screen)


def test_components_draw_from_the_clock_deps_and_hooks(example):
    screen = example('27_components.py', rows=10, columns=60)
    assert screen.wait_for('dashboard on xnano.local')
    assert screen.wait_for('cpu')

    def bars() -> tuple[str, ...]:
        return tuple(line for line in screen.lines() if '[' in line)

    first = bars()
    assert len(first) == 2
    assert screen.wait_until(lambda: bars() != first, timeout=5), (
        'gauges follow the clock'
    )
    screen.press('r')
    assert screen.wait_for('gauge heard r, 1 in all')
    screen.press('r')
    assert screen.wait_for('gauge heard r, 2 in all'), 'each placement counts for itself'
    screen.press('h')
    assert screen.wait_for('the dependencies name xnano.local')
    quit_with_q(screen)


def test_gestures_drag_scroll_and_conditions(example):
    screen = example('28_gestures.py', rows=14, columns=70)
    assert screen.wait_for('a box that hears gestures')
    assert screen.wait_for('zoom   0') and screen.wait_for('drag none')
    screen.send('\x1b[<0;5;5M')  # press inside the box
    screen.send('\x1b[<32;9;6M')  # drag
    assert screen.wait_for('drag 8,3'), 'the drag hook follows the pointer'
    assert screen.wait_for('left held'), 'the left button is held while dragging'
    assert screen.wait_for('moves 1'), 'the box keeps its own state'
    screen.send('\x1b[<0;9;6m')
    assert screen.wait_for('drag released')
    assert screen.wait_for('left free')
    screen.scroll(5, 4, direction='up')
    screen.scroll(5, 4, direction='up')
    assert screen.wait_for('zoom  -2')
    screen.scroll(60, 4, direction='up')
    screen.settle(0.3)
    assert screen.find('zoom  -2') is not None, 'a wheel outside the box is not heard'
    screen.press('z')
    assert screen.wait_for('zoom  -1'), 'a pushed scroll step reaches the box'
    screen.press('r')
    assert screen.wait_for('zoom   0') and screen.wait_for('drag none')
    quit_with_q(screen)


def test_art_walks_blocks_and_draws_cells(example):
    screen = example('29_art.py', rows=16, columns=62)
    assert screen.wait_for('arrows walk')
    assert screen.wait_until(lambda: screen.find('✓') is not None)
    top = screen.find('█ ◆ ★ ✓ ✗')
    assert top is not None, 'Pixel presets are single cells of a standalone box'
    assert screen.wait_for('cells, by value')
    assert screen.wait_until(lambda: screen.cell(top[0] - 1, top[1]).bg != 'default')
    assert any(
        screen.cell(column, row).bg == '9a7b4f' or screen.cell(column, row).fg == '9a7b4f'
        for column in range(14, 20)
        for row in range(3, 8)
    ), 'the wall registered as a symbol is in the world'
    assert screen.find('◆') is not None
    assert any(screen.cell(column, 10).bg != 'default' for column in range(36, 56)), (
        'region.draw_image paints the picture into the strip'
    )
    assert any('\u2800' < character <= '\u28ff' for character in screen.text), (
        'braille dots draw at the resolution of dots'
    )
    screen.press('right')
    assert screen.wait_for('walking')
    for _ in range(10):
        screen.press('right')
    assert screen.wait_for('blocked: a wall is in the way')
    screen.press('left')
    assert screen.wait_for('walking')
    quit_with_q(screen)


def test_notes_render_offline_and_play_by_name(example):
    has_sound_device = TerminalAudioPlayer.is_available()
    screen = example('30_notes.py', rows=8, columns=60)
    assert screen.wait_for('k kick')
    assert re.search(r'offline: 2\.0 seconds, peak 0\.\d\d', screen.text)
    if not has_sound_device:
        assert screen.wait_for('no sound device: rendered offline')
    sounds = [
        ('k', 'the kick by name'),
        ('c', 'the clip loaded with from_audio'),
        ('m', '4 notes at 120 bpm'),
        ('p', 'the arpeggio, a playable function'),
        ('f', 'a class that plays itself'),
    ]
    for key, what in sounds:
        screen.press(key)
        if has_sound_device:
            assert screen.wait_for(f'played {what}')
        else:
            assert screen.wait_for(f'no sound device: skipped {what}')
    quit_with_q(screen)


def test_appearance_changes_borders_colors_and_padding(example):
    screen = example('31_appearance.py', rows=14, columns=80)
    assert screen.wait_for('a card with a look')
    assert screen.wait_for('border rounded   padding 2')
    card = screen.find('a card with a look')
    assert card is not None
    before = screen.cell(card[0], card[1]).bg
    assert before == '335577'
    screen.press('t')
    assert screen.wait_until(lambda: '═' in screen.lines()[2])
    assert '│' in screen.text, 'only the top side changed'
    screen.press('b')
    assert screen.wait_for('border double')
    screen.press('c')
    assert screen.wait_for('text yellow')
    screen.press('p')
    assert screen.wait_for('padding 3')
    screen.press('d')
    assert screen.wait_until(lambda: screen.cell(card[0] - 1, card[1]).bg != before)
    screen.press('f')
    assert screen.wait_for('fade on')
    screen.press('f')
    assert screen.wait_for('fade off'), (
        'a second press clears the effect with context.fx.clear()'
    )
    quit_with_q(screen)


def test_effects_start_on_a_placement_from_a_key(example):
    screen = example('32_effects.py', rows=10, columns=70)
    assert screen.wait_until(lambda: screen.is_alternate)
    assert screen.wait_for('Press any key to change the color of this text')
    assert screen.wait_for('effects: none')
    text = screen.find('Press any key')
    assert text is not None
    assert text[1] == 4, 'the text is centered in the whole window'
    before = screen.cell(text[0], text[1]).fg
    screen.press('a')
    assert screen.wait_until(lambda: screen.cell(text[0], text[1]).fg != before)
    screen.press('e')
    assert screen.wait_for('effects: effect.fade_to')
    screen.press('g')
    assert screen.wait_for('effects: effect.fade_to, effect.glitch')
    screen.press('x')
    assert screen.wait_for('effects: none')
    screen.press('q')
    assert screen.finish() == 0


def test_layout_stacks_in_write_order_and_text_stops_at_the_edges(example):
    screen = example('33_layout.py', rows=14, columns=70)
    assert screen.wait_for('Press any key to change the color of this text')
    assert screen.wait_for('Use the arrow keys to move this text')
    top = screen.find('Press any key')
    movable = screen.find('Use the arrow keys')
    assert top is not None and movable is not None
    assert top[1] == 2, 'the text written first is centered in the top half'
    assert movable[1] == 7, 'the canvas written second takes the bottom half'
    for _ in range(6):
        screen.send('\x1b[A')
    for _ in range(30):
        screen.send('\x1b[D')
    assert screen.wait_until(lambda: screen.find('Use the arrow keys') == (1, 6))
    before = screen.cell(top[0], top[1]).fg
    screen.press('a')
    assert screen.wait_until(lambda: screen.cell(top[0], top[1]).fg != before)
    screen.press('q')
    assert screen.finish() == 0
