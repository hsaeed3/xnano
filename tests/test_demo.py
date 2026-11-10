"""
tests.test_demo

The feature demo (``python -m xnano``) on an emulated terminal, with and without the optional
``image`` and ``audio`` extras: it must run either way, because ``uvx xnano`` installs neither.
"""

from __future__ import annotations

import sys

import pytest

pytest.importorskip('pyte')
if sys.platform == 'win32':
    pytest.skip('needs a pseudo-terminal', allow_module_level=True)

from emulator import Screen  # noqa: E402

ROWS, COLUMNS = 24, 80
RUN_DEMO = 'from xnano.demo import main; main()'
WITHOUT_EXTRAS = (
    "import sys; sys.modules['xnano_image'] = None; sys.modules['xnano_audio'] = None; "
)


def painted_cells(screen: Screen) -> int:
    """How many cells of the screen hold a character or a background color."""
    return sum(
        screen.cell(column, row).bg != 'default'
        or screen.cell(column, row).data.strip() != ''
        for row in range(screen.rows)
        for column in range(screen.columns)
    )


@pytest.fixture
def demo():
    """Start the demo, with the extras blocked when asked, and close it after the test."""
    created: list[Screen] = []

    def start(*, extras: bool = True, rows: int = ROWS, columns: int = COLUMNS) -> Screen:
        source = RUN_DEMO if extras else WITHOUT_EXTRAS + RUN_DEMO
        screen = Screen(
            command=[sys.executable, '-c', source], rows=rows, columns=columns
        )
        created.append(screen)
        return screen

    yield start
    for screen in created:
        screen.close()
        assert 'Traceback' not in screen.raw.decode('utf-8', 'replace')


def open_pages(screen: Screen) -> None:
    """Leave the opening animation with a key, and wait for the first page."""
    assert screen.wait_for('press any key'), screen.text
    screen.press('x')
    assert screen.wait_for('q quit'), screen.text


def test_the_opening_animation_fills_the_window_when_images_are_installed(demo):
    pytest.importorskip('xnano_image')
    screen = demo()
    assert screen.wait_until(lambda: painted_cells(screen) > ROWS * COLUMNS * 0.9), (
        f'The opening animation did not fill the window:\n{screen.text}'
    )
    screen.press('x')
    assert screen.wait_for('╭time'), screen.text
    screen.press('q')
    assert screen.finish() == 0


def test_the_demo_runs_without_the_image_and_audio_extras(demo):
    screen = demo(extras=False)
    assert screen.wait_for('press any key'), screen.text
    assert '█   █   █' in screen.text
    screen.press('x')
    assert screen.wait_for('╭time'), screen.text
    screen.press('right')
    screen.press('right')
    assert screen.wait_for('pip install "xnano[image]" adds pictures'), screen.text
    screen.press('right')
    assert screen.wait_for('Sound needs an extra: pip install "xnano[audio]"'), (
        screen.text
    )
    screen.press('a')
    screen.press('enter')
    screen.press('q')
    assert screen.finish() == 0, screen.text


def test_the_arrows_change_the_page_and_the_hint_names_its_keys(demo):
    screen = demo()
    open_pages(screen)
    assert screen.wait_for('space pause time · ← → page · q quit'), screen.text
    for title, hint in (
        ('╭preview', '↑ ↓ choose a widget'),
        ('╭effects', '↑ ↓ choose an effect · enter play again'),
        ('╭instruments', 'enter melody · m mute'),
        ('╭log', 'press a key · click or drag anywhere'),
        ('╭time', 'space pause time'),
    ):
        screen.press('right')
        assert screen.wait_for(title), screen.text
        assert screen.wait_for(f'{hint} · ← → page · q quit'), screen.text
    screen.press('left')
    assert screen.wait_for('╭log'), screen.text
    screen.press('q')
    assert screen.finish() == 0


def test_the_name_of_the_page_on_screen_is_bold_and_in_reverse_video(demo):
    screen = demo()
    open_pages(screen)

    def is_marked(name: str) -> bool:
        column, row = screen.find(f' {name} ')
        cell = screen.cell(column + 1, row)
        return cell.reverse and cell.bold

    assert screen.wait_until(lambda: is_marked('overview')), screen.text
    assert not is_marked('widgets')
    screen.press('right')
    assert screen.wait_until(lambda: is_marked('widgets')), screen.text
    assert not is_marked('overview')
    screen.press('q')
    assert screen.finish() == 0


def test_the_up_and_down_arrows_move_the_choice_of_a_page(demo):
    screen = demo()
    open_pages(screen)
    screen.press('tab')
    assert screen.wait_for('› bar chart'), screen.text
    screen.press('down')
    assert screen.wait_for('› calendar'), screen.text
    assert 'January 2026' in screen.text
    screen.press('up')
    screen.press('up')
    assert screen.wait_for('› tabs'), screen.text
    screen.press('q')
    assert screen.finish() == 0


def test_space_pauses_the_clock_of_the_overview(demo):
    screen = demo()
    open_pages(screen)
    assert screen.wait_for('▶ running'), screen.text
    screen.press(' ')
    assert screen.wait_for('‖ paused'), screen.text
    screen.press(' ')
    assert screen.wait_for('▶ running'), screen.text
    screen.press('q')
    assert screen.finish() == 0


def test_the_mouse_chooses_a_page_and_a_line_and_marks_a_click(demo):
    screen = demo()
    open_pages(screen)
    column, row = screen.find('widgets')
    screen.click(column + 1, row)
    assert screen.wait_for('› bar chart'), screen.text
    column, row = screen.find('gauge')
    screen.click(column, row)
    assert screen.wait_for('› gauge'), screen.text
    column, row = screen.find('input')
    screen.click(column + 1, row)
    assert screen.wait_for('╭click or drag here'), screen.text
    screen.click(10, 15)
    assert screen.wait_for('click at column 10, row 15'), screen.text
    assert screen.lines()[15][10] == '●'
    screen.drag((10, 15), (20, 18))
    assert screen.wait_until(lambda: screen.lines()[18][20] == '●'), screen.text
    assert screen.lines()[15][10] != '●'
    assert 'mouse  column 20, row 18' in screen.text
    screen.press('q')
    assert screen.finish() == 0


def test_a_small_window_asks_for_a_larger_one_and_a_resize_brings_the_page_back(demo):
    screen = demo(rows=20, columns=60)
    assert screen.wait_for('press any key'), screen.text
    screen.press('x')
    assert screen.wait_for('The demo needs 80 by 24 cells.'), screen.text
    assert 'This window has 60 by 20.' in screen.text
    assert '╭time' not in screen.text
    screen.resize(30, 100)
    assert screen.wait_for('╭time'), screen.text
    assert 'The demo needs' not in screen.text
    screen.press('q')
    assert screen.finish() == 0


@pytest.mark.parametrize(('rows', 'columns'), [(14, 60), (6, 34), (2, 10)])
def test_a_window_of_any_size_opens_the_pages_without_an_error(demo, rows, columns):
    screen = demo(rows=rows, columns=columns)
    screen.settle(1.5)
    screen.press('x')
    # The notice covers the hint line of a window this small, so wait for the notice.
    if rows >= 5:
        assert screen.wait_for('demo needs 80 by 24'), screen.text
    else:
        screen.settle(1.0)
    screen.resize(30, 100)
    assert screen.wait_for('╭time'), screen.text
    for key in ('right', 'down', 'right', 'right', 'right'):
        screen.press(key)
    assert screen.wait_for('╭log'), screen.text
    screen.resize(3, 12)
    screen.settle(0.5)
    screen.press('q')
    assert screen.finish() == 0, screen.raw.decode('utf-8', 'replace')[-800:]


def test_every_widget_of_the_widgets_page_draws_something_in_its_preview(demo):
    screen = demo()
    open_pages(screen)
    screen.press('tab')
    assert screen.wait_for('› bar chart'), screen.text
    column, _ = screen.find('╭preview')
    shown = {
        'bar chart': 'memory',
        'calendar': 'January 2026',
        'chart': '└──',
        'gauge': '60% of 512 GB',
        'line gauge': 'upload',
        'paragraph': 'A paragraph wraps',
        'sparkline': '▁',
        'table': 'service',
        'tabs': 'settings',
    }
    for name, text in shown.items():
        assert screen.wait_for(f'› {name}'), screen.text
        preview = '\n'.join(line[column:] for line in screen.lines())
        assert screen.wait_until(
            lambda text=text: text in '\n'.join(line[column:] for line in screen.lines())
        ), f'The preview of {name} does not show {text!r}:\n{preview}'
        screen.press('down')
    screen.press('q')
    assert screen.finish() == 0
