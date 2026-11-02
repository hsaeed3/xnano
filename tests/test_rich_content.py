"""
tests.test_rich_content

Text from other programs: ANSI text read with ``StyledText.from_ansi`` and written like a string,
and rich renderables drawn by ``xnano.from_rich`` at the width of their placement.
"""

from __future__ import annotations

import sys

import pytest

import xnano
from xnano.styles import RichContent, StyledText


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
