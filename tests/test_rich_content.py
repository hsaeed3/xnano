"""
tests.test_rich_content

Text from other programs: ANSI text read with ``StyledText.from_ansi`` and written like a string,
and rich renderables drawn by ``xnano.from_rich`` at the size of their placement.
"""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING

import pytest

import xnano
from xnano.styles import RichContent, StyledText

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
    from rich.measure import Measurement


def test_ansi_text_is_written_with_its_colors():
    text = StyledText.from_ansi('\x1b[1;31merror:\x1b[0m disk full')
    with xnano.new(width=20, height=2) as canvas:
        canvas.screen.write(text)
        lines = canvas.screen.render(format='ansi').splitlines()
        assert lines[0].startswith('\x1b[0;1;31merror:\x1b[0m disk full')
    assert xnano.region(text).render().splitlines()[0] == 'error: disk full'


def test_a_rich_table_takes_its_natural_width():
    table = pytest.importorskip('rich.table').Table('service', 'status')
    table.add_row('web', 'up')
    with xnano.new(width=40, height=8) as canvas:
        placement = canvas.screen.write(xnano.from_rich(table))
        canvas.clock.step()
        assert (placement.width, placement.height) == (20, 5)
        assert '│ web     │ up     │' in canvas.screen.render()


def test_a_rich_panel_is_drawn_again_at_a_new_width():
    panel = pytest.importorskip('rich.panel').Panel('ready')
    with xnano.new(width=40, height=4) as canvas:
        placement = canvas.screen.write(xnano.from_rich(panel), width='100%')
        canvas.clock.step()
        assert canvas.screen.render().splitlines()[0] == '╭' + '─' * 38 + '╮'
        placement.width = 20
        canvas.clock.step()
        assert canvas.screen.render().splitlines()[0].rstrip() == '╭' + '─' * 18 + '╮'


def test_rich_colors_and_modifiers_keep_their_meaning():
    pytest.importorskip('rich')
    markup = (
        '[red]a[/][color(208)]b[/][#ff8800]c[/][bright_blue]d[/][on green]e[/]'
        '[underline2]f[/][strike]g[/][reverse]h[/][dim italic]i[/]'
    )
    with xnano.new(width=10, height=1) as canvas:
        canvas.screen.write(xnano.from_rich(markup))
        canvas.clock.step()
        rendered = canvas.screen.render(format='ansi')
    for expected in (
        '\x1b[0;31ma',
        '\x1b[0;38;5;208mb',
        '\x1b[0;38;2;255;136;0mc',
        '\x1b[0;94md',
        '\x1b[0;42me',
        '\x1b[0;4mf',
        '\x1b[0;9mg',
        '\x1b[0;7mh',
        '\x1b[0;2;3mi',
    ):
        assert expected in rendered


def test_rich_blinking_and_concealed_text_keep_their_modifiers():
    pytest.importorskip('rich')
    with xnano.new(width=4, height=1) as canvas:
        placement = canvas.screen.write(
            xnano.from_rich('[blink]a[/][blink2]b[/][conceal]c[/]')
        )
        canvas.clock.step()
        modifiers = [
            placement.core_buffer[column, 0].style.modifiers for column in range(3)
        ]
    assert modifiers == [{'blink'}, {'rapid_blink'}, {'hidden'}]


def test_refresh_draws_a_changed_renderable_again():
    table = pytest.importorskip('rich.table').Table('service')
    table.add_row('web')
    with xnano.new(width=20, height=8) as canvas:
        placement = canvas.screen.write(xnano.from_rich(table))
        canvas.clock.step()
        table.add_row('cache')
        placement.refresh()
        canvas.clock.step()
        assert 'cache' in canvas.screen.render()


def test_from_rich_explains_what_it_takes():
    pytest.importorskip('rich')
    with pytest.raises(
        TypeError, match=r'from_rich\(\) draws what rich can render, but got the int 42'
    ):
        xnano.from_rich(42)
    content = xnano.from_rich('[bold]ok[/bold]')
    assert isinstance(content, RichContent)
    assert content.renderable == '[bold]ok[/bold]'


def test_from_rich_names_the_install_command_without_rich(monkeypatch):
    monkeypatch.setitem(sys.modules, 'rich.protocol', None)
    with pytest.raises(ImportError, match='pip install rich'):
        xnano.from_rich('[bold]ok[/bold]')


def test_a_component_draws_live_data_with_rich():
    table_module = pytest.importorskip('rich.table')

    @xnano.writable
    def uptime(context: xnano.Context) -> RichContent:
        table = table_module.Table('uptime')
        table.add_row(f'{context.clock.elapsed_seconds:.0f} s')
        return xnano.from_rich(table)

    with xnano.new(width=20, height=6) as canvas:
        canvas.screen.write(uptime)
        canvas.clock.step(delta_seconds=1.0)
        assert '│ 1 s    │' in canvas.screen.render()
        canvas.clock.step(delta_seconds=2.0)
        assert '│ 3 s    │' in canvas.screen.render()


def test_rich_content_follows_expressions_and_prints_without_a_canvas():
    table = pytest.importorskip('rich.table').Table('name')
    table.add_row('web')
    with xnano.new(width=40, height=6) as canvas:
        placement = canvas.screen.write(
            xnano.from_rich(table), x=canvas.clock * 10, border='rounded'
        )
        canvas.clock.step(delta_seconds=1.0)
        assert placement.x == 10
    assert '│ web  │' in xnano.region(xnano.from_rich(table)).render()


class _MixedResults:
    """Yields each kind of result that ``__rich_console__`` can yield."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        from rich.panel import Panel
        from rich.segment import Segment
        from rich.text import Text

        yield Segment('segment')
        yield Segment.line()
        yield Text('text', style='bold')
        yield '[red]markup[/red]'
        yield Panel('inner', expand=False)


class _CastToMarkup:
    """Has only ``__rich__``, which returns rich markup."""

    def __rich__(self) -> str:
        return '[green]cast[/green]'


class _CastToPanel:
    """Has only ``__rich__``, which returns another renderable."""

    def __rich__(self) -> RenderableType:
        from rich.panel import Panel

        return Panel('panel', expand=False)


class _MeasuredFill:
    """Fills the width that it gets, and measures six cells at most."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        from rich.segment import Segment

        yield Segment('=' * options.max_width)

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        from rich.measure import Measurement

        return Measurement(4, 6)


class _OptionsReport:
    """Writes the width, the height and the largest height that rich gives it."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        from rich.text import Text

        yield Text(f'{options.max_width} {options.height} {options.max_height}')


class _ControlCodes:
    """Moves the cursor and rings the bell between two letters, as rich.live does."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        from rich.control import Control
        from rich.segment import Segment

        yield Control.move_to(5, 2)
        yield Segment('a')
        yield Control.bell()
        yield Segment('b')


class _CountedRenderable:
    """Counts how many times rich draws it."""

    def __init__(self) -> None:
        self.draw_count = 0

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        self.draw_count += 1
        yield 'still'


class _BrokenRenderable:
    """Raises an error when rich draws it."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        raise ValueError('the data is missing')


def _first_lines(canvas: xnano.Canvas, count: int) -> list[str]:
    """The first ``count`` lines of the screen, without spaces at their end."""
    return [line.rstrip() for line in canvas.screen.render().splitlines()[:count]]


def test_a_custom_renderable_yields_segments_text_markup_and_renderables():
    pytest.importorskip('rich')
    with xnano.new(width=40, height=8) as canvas:
        placement = canvas.screen.write(xnano.from_rich(_MixedResults()))
        assert (placement.width, placement.height) == (9, 6)
        assert _first_lines(canvas, 6) == [
            'segment',
            'text',
            'markup',
            '╭───────╮',
            '│ inner │',
            '╰───────╯',
        ]
        assert placement.core_buffer[0, 1].style.modifiers == {'bold'}
        assert '\x1b[0;31mmarkup' in canvas.screen.render(format='ansi')


def test_a_renderable_with_only_rich_cast_is_drawn():
    pytest.importorskip('rich')
    with xnano.new(width=20, height=4) as canvas:
        canvas.screen.write(xnano.from_rich(_CastToMarkup()))
        canvas.screen.write(xnano.from_rich(_CastToPanel()), y=1)
        assert _first_lines(canvas, 4) == ['cast', '╭───────╮', '│ panel │', '╰───────╯']
        assert '\x1b[0;32mcast' in canvas.screen.render(format='ansi')


def test_the_natural_width_comes_from_rich_measure():
    pytest.importorskip('rich')
    with xnano.new(width=20, height=2) as canvas:
        natural = canvas.screen.write(xnano.from_rich(_MeasuredFill()))
        given = canvas.screen.write(xnano.from_rich(_MeasuredFill()), y=1, width=10)
        assert (natural.width, given.width) == (6, 10)
        assert _first_lines(canvas, 2) == ['======', '==========']


def test_a_renderable_is_drawn_again_at_the_new_width_of_its_placement():
    pytest.importorskip('rich')
    with xnano.new(width=30, height=1) as canvas:
        placement = canvas.screen.write(xnano.from_rich(_OptionsReport()), width='100%')
        assert _first_lines(canvas, 1) == ['30 None 1']
        placement.width = 12
        canvas.clock.step()
        assert _first_lines(canvas, 1) == ['12 None 1']


def test_a_renderable_gets_the_height_of_its_placement():
    pytest.importorskip('rich')
    with xnano.new(width=30, height=6) as canvas:
        canvas.screen.write(xnano.from_rich(_OptionsReport()), height=2)
        canvas.screen.write(xnano.from_rich(_OptionsReport()), y=3)
        lines = _first_lines(canvas, 4)
    assert (lines[0], lines[3]) == ('30 2 2', '30 None 6')


def test_rich_control_codes_are_not_drawn():
    pytest.importorskip('rich')
    with xnano.new(width=8, height=3) as canvas:
        placement = canvas.screen.write(xnano.from_rich(_ControlCodes()))
        assert (placement.width, placement.height) == (2, 1)
        rendered = canvas.screen.render(format='ansi')
    assert rendered.startswith('\x1b[0mab ')
    assert '\x07' not in rendered


def test_a_table_in_a_component_takes_its_new_size_on_each_run():
    table_module = pytest.importorskip('rich.table')

    @xnano.writable
    def jobs(context: xnano.Context) -> RichContent:
        table = table_module.Table('job')
        for index in range(int(context.clock.elapsed_seconds) + 1):
            table.add_row(f'job {index}' + '!' * index)
        return xnano.from_rich(table)

    with xnano.new(width=30, height=10) as canvas:
        placement = canvas.screen.write(jobs)
        assert (placement.width, placement.height) == (9, 5)
        canvas.clock.step(delta_seconds=2.0)
        assert (placement.width, placement.height) == (11, 7)
        assert '│ job 2!! │' in canvas.screen.render()


def test_a_rich_spinner_moves_with_the_canvas_clock():
    spinner_module = pytest.importorskip('rich.spinner')
    with xnano.new(width=20, height=1) as canvas:
        placement = canvas.screen.write(
            xnano.from_rich(spinner_module.Spinner('line', 'working'))
        )
        frames = _first_lines(canvas, 1)
        for _ in range(3):
            canvas.clock.step(delta_seconds=0.2)
            frames += _first_lines(canvas, 1)
        placement.refresh()
        canvas.deliver_events()
        assert _first_lines(canvas, 1) == frames[-1:]
    assert frames == ['- working', '\\ working', '/ working', '- working']


def test_a_still_renderable_is_not_drawn_on_each_frame():
    pytest.importorskip('rich')
    counted = _CountedRenderable()
    with xnano.new(width=10, height=1) as canvas:
        canvas.screen.write(xnano.from_rich(counted))
        for _ in range(3):
            canvas.clock.step()
    assert counted.draw_count == 1


def test_a_rich_progress_follows_the_canvas_clock_that_it_is_given():
    progress_module = pytest.importorskip('rich.progress')
    with xnano.new(width=40, height=1) as canvas:
        progress = progress_module.Progress(
            progress_module.TextColumn('{task.description}'),
            progress_module.BarColumn(bar_width=10),
            progress_module.TimeElapsedColumn(),
            get_time=lambda: canvas.clock.elapsed_seconds,
        )
        task = progress.add_task('build', total=4)

        @xnano.writable
        def build(context: xnano.Context) -> RichContent:
            progress.update(task, completed=context.clock.elapsed_seconds)
            return xnano.from_rich(progress)

        canvas.screen.write(build)
        canvas.clock.step(delta_seconds=2.0)
        assert _first_lines(canvas, 1) == ['build ━━━━━╺━━━━ 0:00:02']


def _built_in_renderable(name: str) -> RenderableType:
    """A built-in rich renderable, made after the test checks that rich is installed."""
    from rich.align import Align
    from rich.columns import Columns
    from rich.console import Group
    from rich.markdown import Markdown
    from rich.padding import Padding
    from rich.panel import Panel
    from rich.pretty import Pretty
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich.text import Text
    from rich.tree import Tree

    tree = Tree('root')
    tree.add('leaf').add('deep')
    tree.add('other')
    renderables: dict[str, RenderableType] = {
        'markup text': '[bold]bold[/] 42 :smile: "quoted"',
        'cropped text': Text(
            'a long line that does not fit', no_wrap=True, overflow='ellipsis'
        ),
        'justified text': Group(
            Text('left'), Text('middle', justify='center'), Text('right', justify='right')
        ),
        'syntax': Syntax(
            'def double(value):\n    return value * 2\n', 'python', line_numbers=True
        ),
        'markdown': Markdown('# Title\n\nSome *text* with `code`.\n\n- one\n- two'),
        'tree': tree,
        'columns': Columns(['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta']),
        'group': Group('first', Rule(), Panel('second')),
        'panel': Panel('hello', title='title'),
        'padding': Padding('padded', (1, 4)),
        'align': Align.center('middle'),
        'pretty': Pretty({'name': 'web', 'ports': [80, 443], 'is_up': True}),
    }
    return renderables[name]


@pytest.mark.parametrize(
    'name',
    [
        'markup text',
        'cropped text',
        'justified text',
        'syntax',
        'markdown',
        'tree',
        'columns',
        'group',
        'panel',
        'padding',
        'align',
        'pretty',
    ],
)
def test_a_built_in_renderable_shows_the_text_that_rich_print_shows(name: str):
    console_module = pytest.importorskip('rich.console')
    renderable = _built_in_renderable(name)
    output = io.StringIO()
    # The adapter draws without the legacy Windows console mode, which on Windows would
    # use square box corners and one column less. The reference does the same.
    console = console_module.Console(
        file=output,
        width=30,
        height=12,
        force_terminal=True,
        color_system=None,
        legacy_windows=False,
    )
    console.print(renderable)
    expected = '\n'.join(line.rstrip() for line in output.getvalue().splitlines())
    with xnano.new(width=30, height=12) as canvas:
        canvas.screen.write(xnano.from_rich(renderable), width='100%')
        drawn = '\n'.join(_first_lines(canvas, 12))
    assert drawn.rstrip('\n') == expected.rstrip('\n')


def test_rich_text_keeps_its_spans_and_its_justification():
    text_module = pytest.importorskip('rich.text')
    text = text_module.Text.assemble(
        ('error', 'bold red'), ': disk full', justify='right'
    )
    with xnano.new(width=20, height=1) as canvas:
        placement = canvas.screen.write(xnano.from_rich(text), width=20)
        assert _first_lines(canvas, 1) == ['    error: disk full']
        first = placement.core_buffer[4, 0].style
        last = placement.core_buffer[19, 0].style
    assert (first.modifiers, last.modifiers) == ({'bold'}, frozenset())
    assert first.foreground is not None and last.foreground is None


def test_a_rich_background_fills_the_width_of_its_placement():
    panel_module = pytest.importorskip('rich.panel')
    syntax_module = pytest.importorskip('rich.syntax')
    with xnano.new(width=24, height=6) as canvas:
        panel = canvas.screen.write(
            xnano.from_rich(panel_module.Panel('note', style='on blue')), width=20
        )
        syntax = canvas.screen.write(
            xnano.from_rich(
                syntax_module.Syntax('width = 1\nheight = 2', 'python', theme='monokai')
            ),
            y=3,
            width=20,
        )
        for placement in (panel, syntax):
            buffer = placement.core_buffer
            assert all(
                buffer[column, row].style.background is not None
                for row in range(placement.height)
                for column in range(20)
            )


def test_a_rich_layout_fills_the_height_that_it_gets():
    layout_module = pytest.importorskip('rich.layout')
    layout = layout_module.Layout()
    layout.split_column(
        layout_module.Layout(name='top'), layout_module.Layout(name='bottom')
    )
    with xnano.new(width=30, height=8) as canvas:
        filled = canvas.screen.write(xnano.from_rich(layout))
        given = canvas.screen.write(xnano.from_rich(layout), width=20, height=4)
        assert (filled.width, filled.height) == (30, 8)
        assert (given.width, given.height) == (20, 4)


def test_rich_uses_the_size_of_the_canvas_and_not_of_the_terminal(monkeypatch):
    layout_module = pytest.importorskip('rich.layout')
    monkeypatch.setenv('COLUMNS', '200')
    monkeypatch.setenv('LINES', '50')
    monkeypatch.setenv('TERM', 'dumb')
    with xnano.new(width=30, height=8) as canvas:
        placement = canvas.screen.write(xnano.from_rich(layout_module.Layout()))
        assert (placement.width, placement.height) == (30, 8)


def test_text_is_drawn_as_rich_print_draws_it():
    text_module = pytest.importorskip('rich.text')
    with xnano.new(width=20, height=2) as canvas:
        canvas.screen.write(xnano.from_rich('[bold]ok[/bold] 42 :smile:'))
        canvas.screen.write(xnano.from_rich(text_module.Text('[bold]ok[/bold] 42')), y=1)
        assert _first_lines(canvas, 2) == ['ok 42 😄', '[bold]ok[/bold] 42']
        rendered = canvas.screen.render(format='ansi').splitlines()
    assert '\x1b[0;1;36m42' in rendered[0]
    assert '\x1b[0;1;36m' not in rendered[1]


def test_a_rich_link_keeps_its_text_and_loses_its_address():
    pytest.importorskip('rich')
    with xnano.new(width=10, height=1) as canvas:
        canvas.screen.write(xnano.from_rich('[link=https://example.com]docs[/link]'))
        assert _first_lines(canvas, 1) == ['docs']
        assert '\x1b]8' not in canvas.screen.render(format='ansi')


def test_frames_circles_and_overlines_draw_as_plain_text():
    pytest.importorskip('rich')
    with xnano.new(width=4, height=1) as canvas:
        placement = canvas.screen.write(
            xnano.from_rich('[frame]a[/][encircle]b[/][overline]c[/]')
        )
        styles = [placement.core_buffer[column, 0].style for column in range(3)]
    assert [
        (style.foreground, style.background, style.modifiers) for style in styles
    ] == [(None, None, frozenset())] * 3


def test_the_default_color_of_rich_is_no_color():
    pytest.importorskip('rich')
    with xnano.new(width=4, height=1) as canvas:
        placement = canvas.screen.write(
            xnano.from_rich('[red on blue]a[default on default]b[/][/]')
        )
        styles = [placement.core_buffer[column, 0].style for column in range(2)]
    assert styles[0].foreground is not None and styles[0].background is not None
    assert (styles[1].foreground, styles[1].background) == (None, None)


def test_an_error_while_rich_draws_goes_through_with_a_note():
    pytest.importorskip('rich')
    with xnano.new(width=20, height=2) as canvas:
        with pytest.raises(ValueError, match='the data is missing') as raised:
            canvas.screen.write(xnano.from_rich(_BrokenRenderable()))
    if sys.version_info >= (3, 11):
        assert raised.value.__notes__ == [
            'from_rich() could not draw the _BrokenRenderable renderable. The error above '
            'occurred when rich drew it. To find the cause, print the renderable with '
            'rich.print().'
        ]
