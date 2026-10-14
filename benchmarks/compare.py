"""
benchmarks.compare

Compare xnano with other terminal libraries, one task at a time.

This is a report, not a test suite: it prints a table of how long each library takes for the
same job and how many times slower or faster xnano is. Run it with

    uv run python benchmarks/compare.py                 # everything
    uv run python benchmarks/compare.py table frame     # only cases whose name contains these
    uv run python benchmarks/compare.py --json out.json # also write the numbers
    uv run python benchmarks/compare.py --show          # watch each library draw each case

The competitors are `rich` (the standard for printing styled text), `urwid` (a retained widget
toolkit that renders to canvases) and `prompt_toolkit` (formatted text and layouts). Each case
does the same visible work in every library, at the same size, and every timed function returns
the rendered text so none of them can skip the work. Setup (building objects that a program
would keep between frames) is outside the timed part; building objects that a program would
create again is inside it, and each case says which it measures.

Install the competitors with `uv sync --group compare`.
"""
# pyright: reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

import argparse
import gc
import io
import json
import math
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from types import ModuleType

import xnano
import xnano.audio
import xnano.context
import xnano.effects
import xnano.events
import xnano.expressions
import xnano.image
import xnano.styles
import xnano.terminal
from xnano.buffers import Buffer
from xnano.styles import Style
from xnano.widgets import Block, Gauge, ItemList, Paragraph, Table

try:
    import rich
    import rich.box
    import rich.console
    import rich.layout
    import rich.panel
    import rich.progress_bar
    import rich.style
    import rich.table
    import rich.text
    import urwid
    from prompt_toolkit.data_structures import Size as ToolkitSize
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.output.vt100 import Vt100_Output
    from prompt_toolkit.shortcuts import print_formatted_text
except ImportError as error:  # pragma: no cover
    raise SystemExit(
        'This comparison needs rich, urwid and prompt_toolkit. '
        'Install them with: uv sync --group compare'
    ) from error

LIBRARIES = ('xnano', 'rich', 'urwid', 'prompt_toolkit')

LOREM = (
    'The quick brown fox jumps over the lazy dog while the five boxing wizards jump '
    'quickly, and pack my box with five dozen liquor jugs. '
) * 12  # about 2 KB
WORDS = [f'word{index}' for index in range(200)]


# ---------------------------------------------------------------------------------------
# A little timing harness
# ---------------------------------------------------------------------------------------


@dataclass
class Result:
    """Seconds per call for one library on one case."""

    median: float
    spread: float  # (slowest - fastest) / median over the repeats
    calls: int


@dataclass
class Case:
    """One job and how each library does it."""

    name: str
    group: str
    description: str
    builders: dict[str, Callable[[], Callable[[], object]]]
    results: dict[str, Result] = field(default_factory=dict)


def measure(
    function: Callable[[], object], *, budget: float = 0.25, repeats: int = 7
) -> Result:
    """Time ``function`` many times: the median of several runs of a calibrated loop."""
    assert function(), 'a benchmark must produce output'
    # Calibrate: enough calls for one repeat to take about budget / repeats seconds.
    calls = 1
    target = budget / repeats
    while True:
        start = time.perf_counter()
        for _ in range(calls):
            function()
        elapsed = time.perf_counter() - start
        if elapsed >= target or calls >= 1_000_000:
            break
        calls = max(calls * 2, int(calls * target / max(elapsed, 1e-9)))
    samples = []
    gc.collect()
    gc.disable()
    try:
        for _ in range(repeats):
            start = time.perf_counter()
            for _ in range(calls):
                function()
            samples.append((time.perf_counter() - start) / calls)
    finally:
        gc.enable()
    median = statistics.median(samples)
    return Result(median, (max(samples) - min(samples)) / median, calls)


def format_time(seconds: float) -> str:
    """Seconds with a sensible unit."""
    if seconds < 1e-6:
        return f'{seconds * 1e9:.0f} ns'
    if seconds < 1e-3:
        return f'{seconds * 1e6:.1f} µs'
    if seconds < 1:
        return f'{seconds * 1e3:.2f} ms'
    return f'{seconds:.2f} s'


# ---------------------------------------------------------------------------------------
# How each library renders to a string
# ---------------------------------------------------------------------------------------

WIDTH, HEIGHT = 80, 24


def rich_console(
    width: int = WIDTH, height: int = HEIGHT
) -> tuple[rich.console.Console, io.StringIO]:
    """A console that writes truecolor escape sequences into memory."""
    sink = io.StringIO()
    console = rich.console.Console(
        file=sink,
        width=width,
        height=height,
        force_terminal=True,
        color_system='truecolor',
        legacy_windows=False,
        _environ={},
    )
    return console, sink


def rich_render(
    renderable: object, width: int = WIDTH, height: int = HEIGHT
) -> Callable[[], str]:
    """Print a renderable to memory and return what was written."""
    console, sink = rich_console(width, height)

    def run() -> str:
        sink.seek(0)
        sink.truncate()
        console.print(renderable, end='')
        return sink.getvalue()

    return run


def urwid_render(
    widget: object, width: int = WIDTH, height: int | None = None
) -> Callable[[], str]:
    """Render a widget to a canvas and join its text."""
    size = (width,) if height is None else (width, height)

    def run() -> str:
        canvas = widget.render(size)  # type: ignore[attr-defined]
        return '\n'.join(row.decode('utf-8', 'replace') for row in canvas.text)

    return run


def toolkit_render(fragments: object) -> Callable[[], str]:
    """Print formatted text through the vt100 output into memory."""
    sink = io.StringIO()
    output = Vt100_Output(
        sink, lambda: ToolkitSize(rows=HEIGHT, columns=WIDTH), term='xterm-256color'
    )

    def run() -> str:
        sink.seek(0)
        sink.truncate()
        print_formatted_text(fragments, output=output)
        output.flush()
        return sink.getvalue()

    return run


def xnano_widget(widget: Buffer) -> Callable[[], str]:
    """Render a widget to ANSI text."""
    return lambda: widget.render(format='ansi')


def xnano_frame(terminal: xnano.terminal.Terminal) -> Callable[[], str]:
    """Draw a frame of a terminal and return it as ANSI text."""
    return lambda: terminal.output.render().ansi


# ---------------------------------------------------------------------------------------
# The cases
# ---------------------------------------------------------------------------------------


def cases() -> list[Case]:
    """Every comparison."""
    found: list[Case] = []

    def add(
        name: str,
        group: str,
        description: str,
        **builders: Callable[[], Callable[[], object]],
    ) -> None:
        found.append(Case(name, group, description, builders))

    # -- static content, built and rendered each time ---------------------------------------

    add(
        'plain_text',
        'text',
        'wrap 2 KB of plain text to 80 columns and render it (object built each call)',
        xnano=lambda: (
            lambda: Paragraph(LOREM, should_wrap=True, width=WIDTH, height=30).render(
                format='ansi'
            )
        ),
        rich=lambda: lambda: rich_render(rich.text.Text(LOREM))(),
        urwid=lambda: lambda: urwid_render(urwid.Text(LOREM))(),
        prompt_toolkit=lambda: lambda: toolkit_render(FormattedText([('', LOREM)]))(),
    )

    add(
        'plain_text_kept',
        'text',
        'the same, with the object kept and only rendered again',
        xnano=lambda: xnano_widget(
            Paragraph(LOREM, should_wrap=True, width=WIDTH, height=30)
        ),
        rich=lambda: rich_render(rich.text.Text(LOREM)),
        urwid=lambda: urwid_render(urwid.Text(LOREM)),
        prompt_toolkit=lambda: toolkit_render(FormattedText([('', LOREM)])),
    )

    def styled_spans_xnano() -> Callable[[], object]:
        colors = [(index * 5 % 256, 120, 255 - index * 5 % 256) for index in range(200)]

        def run() -> str:
            spans = [
                xnano.styles.TextSpan(word + ' ', style=Style(foreground=color))
                for word, color in zip(WORDS, colors, strict=True)
            ]
            return Paragraph(
                xnano.styles.StyledText(spans), should_wrap=True, width=WIDTH, height=20
            ).render(format='ansi')

        return run

    def styled_spans_rich() -> Callable[[], object]:
        colors = [
            f'#{index * 5 % 256:02x}78{255 - index * 5 % 256:02x}' for index in range(200)
        ]

        def run() -> str:
            text = rich.text.Text()
            for word, color in zip(WORDS, colors, strict=True):
                text.append(word + ' ', style=color)
            return rich_render(text)()

        return run

    def styled_spans_urwid() -> Callable[[], object]:
        def run() -> str:
            markup = [
                (
                    urwid.AttrSpec(f'#{index % 16:x}{8:x}{15 - index % 16:x}', ''),
                    word + ' ',
                )
                for index, word in enumerate(WORDS)
            ]
            return urwid_render(urwid.Text(markup))()

        return run

    def styled_spans_toolkit() -> Callable[[], object]:
        def run() -> str:
            fragments = [
                (f'fg:#{index * 5 % 256:02x}78{255 - index * 5 % 256:02x}', word + ' ')
                for index, word in enumerate(WORDS)
            ]
            return toolkit_render(FormattedText(fragments))()

        return run

    add(
        'styled_spans',
        'text',
        '200 words, each with its own truecolor, wrapped to 80 columns (built each call)',
        xnano=styled_spans_xnano,
        rich=styled_spans_rich,
        urwid=styled_spans_urwid,
        prompt_toolkit=styled_spans_toolkit,
    )

    cjk = '日本語のテキスト、🚀 emoji and wide characters mixed with latin text. ' * 20
    add(
        'wide_characters',
        'text',
        'wrap text with double-width characters and emoji to 80 columns',
        xnano=lambda: xnano_widget(
            Paragraph(cjk, should_wrap=True, width=WIDTH, height=40)
        ),
        rich=lambda: rich_render(rich.text.Text(cjk)),
        urwid=lambda: urwid_render(urwid.Text(cjk)),
    )

    # -- structure --------------------------------------------------------------------------

    rows = [
        [
            f'row {index}',
            f'{index * 3.14159:.2f}',
            'active' if index % 2 else 'idle',
            f'node-{index % 7}',
            f'{index % 100}%',
        ]
        for index in range(40)
    ]

    def table_xnano() -> Callable[[], object]:
        def run() -> str:
            table = Table(
                rows,
                header=['name', 'value', 'state', 'node', 'load'],
                widths=[12, 10, 10, 10, 8],
                width=WIDTH,
                height=42,
            )
            return table.render(format='ansi')

        return run

    def table_rich() -> Callable[[], object]:
        def run() -> str:
            table = rich.table.Table(box=rich.box.SIMPLE)
            for column in ('name', 'value', 'state', 'node', 'load'):
                table.add_column(column)
            for row in rows:
                table.add_row(*row)
            return rich_render(table)()

        return run

    def table_urwid() -> Callable[[], object]:
        def run() -> str:
            lines = [urwid.Columns([urwid.Text(cell) for cell in row]) for row in rows]
            return urwid_render(urwid.Pile(lines))()

        return run

    add(
        'table',
        'structure',
        '40 rows by 5 columns with a header, built and rendered each call',
        xnano=table_xnano,
        rich=table_rich,
        urwid=table_urwid,
    )

    add(
        'bordered_panel',
        'structure',
        'a titled rounded border around wrapped text, built and rendered each call',
        xnano=lambda: lambda: _xnano_panel(),
        rich=lambda: (
            lambda: rich_render(
                rich.panel.Panel(
                    rich.text.Text(LOREM[:600]), title='title', box=rich.box.ROUNDED
                )
            )()
        ),
        urwid=lambda: (
            lambda: urwid_render(urwid.LineBox(urwid.Text(LOREM[:600]), title='title'))()
        ),
    )

    def columns_xnano() -> Callable[[], object]:
        terminal = xnano.open(offscreen=True, width=WIDTH, height=12)
        panel_width = WIDTH // 3
        for index in range(3):
            terminal.write(
                Block(f'panel {index}', border_type='rounded'),
                x=index * panel_width,
                width=panel_width,
                height=12,
            )
            terminal.write(
                Paragraph(
                    LOREM[:200], should_wrap=True, width=panel_width - 2, height=10
                ),
                x=index * panel_width + 1,
                y=1,
            )
        return xnano_frame(terminal)

    def columns_rich() -> Callable[[], object]:
        layout = rich.layout.Layout()
        layout.split_row(
            *(
                rich.layout.Layout(
                    rich.panel.Panel(
                        rich.text.Text(LOREM[:200]),
                        title=f'panel {index}',
                        box=rich.box.ROUNDED,
                    )
                )
                for index in range(3)
            )
        )
        return rich_render(layout, WIDTH, 12)

    def columns_urwid() -> Callable[[], object]:
        columns = urwid.Columns(
            [
                urwid.LineBox(
                    urwid.Filler(urwid.Text(LOREM[:200]), 'top'), title=f'panel {index}'
                )
                for index in range(3)
            ]
        )
        return urwid_render(columns, WIDTH, 12)

    add(
        'three_columns',
        'structure',
        'three bordered panels side by side, laid out and rendered (layout kept)',
        xnano=columns_xnano,
        rich=columns_rich,
        urwid=columns_urwid,
    )

    add(
        'progress_bar',
        'structure',
        'a 60% progress bar 60 cells wide, built and rendered each call',
        xnano=lambda: lambda: Gauge(0.6, width=60, height=1).render(format='ansi'),
        rich=lambda: (
            lambda: rich_render(
                rich.progress_bar.ProgressBar(total=100, completed=60, width=60)
            )()
        ),
        urwid=lambda: (
            lambda: urwid_render(
                urwid.ProgressBar('', 'done', current=60, done=100), 60
            )()
        ),
    )

    # -- many things ------------------------------------------------------------------------

    def many_xnano() -> Callable[[], object]:
        terminal = xnano.open(offscreen=True, width=WIDTH, height=HEIGHT)
        for index in range(500):
            terminal.write(f'item {index}', x=index % 60, y=index % HEIGHT)
        return xnano_frame(terminal)

    def scattered_lines() -> list[str]:
        """What the other libraries need: the same 500 items already placed into 24 lines."""
        grid = [[' '] * WIDTH for _ in range(HEIGHT)]
        for index in range(500):
            text, column, row = f'item {index}', index % 60, index % HEIGHT
            for offset, character in enumerate(text):
                if column + offset < WIDTH:
                    grid[row][column + offset] = character
        return [''.join(row) for row in grid]

    def many_rich() -> Callable[[], object]:
        return rich_render(
            rich.console.Group(
                *(rich.text.Text(line, no_wrap=True) for line in scattered_lines())
            )
        )

    def many_urwid() -> Callable[[], object]:
        return urwid_render(
            urwid.Pile([urwid.Text(line, wrap='clip') for line in scattered_lines()])
        )

    add(
        'many_small_items',
        'scale',
        '500 small items scattered over 80x24, one frame drawn (xnano keeps 500 placed objects; the others are given the 24 lines those items make, which a program would have to compose itself)',
        xnano=many_xnano,
        rich=many_rich,
        urwid=many_urwid,
    )

    def long_list_xnano() -> Callable[[], object]:
        items = ItemList(
            [f'item {index}' for index in range(10_000)], width=WIDTH, height=HEIGHT
        )
        position = [0]

        def run() -> str:
            position[0] = (position[0] + 1) % 9_900
            items.selected = position[0]
            return items.render(format='ansi')

        return run

    def long_list_rich() -> Callable[[], object]:
        lines = [f'item {index}' for index in range(10_000)]
        position = [0]
        console, sink = rich_console()

        def run() -> str:
            position[0] = (position[0] + 1) % 9_900
            sink.seek(0)
            sink.truncate()
            console.print(
                rich.console.Group(*lines[position[0] : position[0] + HEIGHT]), end=''
            )
            return sink.getvalue()

        return run

    def long_list_urwid() -> Callable[[], object]:
        walker = urwid.SimpleFocusListWalker(
            [urwid.Text(f'item {index}') for index in range(10_000)]
        )
        box = urwid.ListBox(walker)
        position = [0]

        def run() -> str:
            position[0] = (position[0] + 1) % 9_900
            walker.set_focus(position[0])
            canvas = box.render((WIDTH, HEIGHT), focus=True)
            return '\n'.join(row.decode('utf-8', 'replace') for row in canvas.text)

        return run

    add(
        'scroll_long_list',
        'scale',
        'scroll a list of 10,000 items one step and draw the 24 visible rows',
        xnano=long_list_xnano,
        rich=long_list_rich,
        urwid=long_list_urwid,
    )

    # -- animation: the same screen, changing -----------------------------------------------

    def frame_one_xnano(width: int, height: int) -> Callable[[], Callable[[], object]]:
        def build() -> Callable[[], object]:
            terminal = xnano.open(offscreen=True, width=width, height=height)
            for row in range(height):
                terminal.write(f'line {row:<4}' + 'x' * (width - 9), y=row)
            counter = [0]
            number = terminal.write('0', x=2, y=1, layer=1)

            def run() -> str:
                counter[0] += 1
                number.text = f'{counter[0] % 1000:<6}'
                return terminal.output.render().ansi

            return run

        return build

    def frame_one_rich(width: int, height: int) -> Callable[[], Callable[[], object]]:
        def build() -> Callable[[], object]:
            console, sink = rich_console(width, height)
            lines = [f'line {row:<4}' + 'x' * (width - 9) for row in range(height)]
            counter = [0]

            def run() -> str:
                counter[0] += 1
                lines[1] = lines[1][:2] + f'{counter[0] % 1000:<6}' + lines[1][8:]
                sink.seek(0)
                sink.truncate()
                console.print(
                    rich.console.Group(
                        *(rich.text.Text(line, no_wrap=True) for line in lines)
                    ),
                    end='',
                )
                return sink.getvalue()

            return run

        return build

    def frame_one_urwid(width: int, height: int) -> Callable[[], Callable[[], object]]:
        def build() -> Callable[[], object]:
            texts = [
                urwid.Text(f'line {row:<4}' + 'x' * (width - 9), wrap='clip')
                for row in range(height)
            ]
            pile = urwid.Pile(texts)
            counter = [0]

            def run() -> str:
                counter[0] += 1
                texts[1].set_text(
                    'line 1   ' + f'{counter[0] % 1000:<6}' + 'x' * (width - 15)
                )
                canvas = pile.render((width,))
                return '\n'.join(row.decode('utf-8', 'replace') for row in canvas.text)

            return run

        return build

    for width, height in ((80, 24), (200, 60)):
        add(
            f'frame_one_change_{width}x{height}',
            'frames',
            f'change one value on a {width}x{height} screen and draw the whole frame',
            xnano=frame_one_xnano(width, height),
            rich=frame_one_rich(width, height),
            urwid=frame_one_urwid(width, height),
        )

    def frame_all_xnano() -> Callable[[], object]:
        terminal = xnano.open(offscreen=True, width=WIDTH, height=HEIGHT)
        pixels = terminal.pixels
        tick = [0]

        def run() -> str:
            tick[0] += 1
            time_value = tick[0] / 10
            pixels.shade(
                lambda column, row: (
                    int(127 + 127 * math.sin(column / 7 + time_value)),
                    int(127 + 127 * math.sin(row / 5 - time_value)),
                    128,
                )
            )
            return terminal.output.render().ansi

        return run

    def frame_all_rich() -> Callable[[], object]:
        console, sink = rich_console()
        tick = [0]

        def run() -> str:
            tick[0] += 1
            time_value = tick[0] / 10
            lines = []
            for row in range(HEIGHT):
                line = rich.text.Text()
                for column in range(WIDTH):
                    top = (
                        int(127 + 127 * math.sin(column / 7 + time_value)),
                        int(127 + 127 * math.sin(2 * row / 5 - time_value)),
                        128,
                    )
                    bottom = (
                        int(127 + 127 * math.sin(column / 7 + time_value)),
                        int(127 + 127 * math.sin((2 * row + 1) / 5 - time_value)),
                        128,
                    )
                    line.append(
                        '▀',
                        style=f'rgb({top[0]},{top[1]},{top[2]}) on rgb({bottom[0]},{bottom[1]},{bottom[2]})',
                    )
                lines.append(line)
            sink.seek(0)
            sink.truncate()
            console.print(rich.console.Group(*lines), end='')
            return sink.getvalue()

        return run

    def frame_all_urwid() -> Callable[[], object]:
        tick = [0]
        spec_cache: dict[tuple[int, int, int], urwid.AttrSpec] = {}

        def run() -> str:
            tick[0] += 1
            time_value = tick[0] / 10
            rows = []
            for row in range(HEIGHT):
                markup = []
                for column in range(WIDTH):
                    red = int(127 + 127 * math.sin(column / 7 + time_value)) // 17
                    green = int(127 + 127 * math.sin(2 * row / 5 - time_value)) // 17
                    key = (red, green, 8)
                    spec = spec_cache.get(key)
                    if spec is None:
                        spec = spec_cache[key] = urwid.AttrSpec(
                            f'#{red:x}{green:x}8', f'#{green:x}{red:x}8'
                        )
                    markup.append((spec, '▀'))
                rows.append(urwid.Text(markup, wrap='clip'))
            return urwid_render(urwid.Pile(rows))()

        return run

    add(
        'frame_every_cell_changes',
        'frames',
        'a full-screen color animation: every cell of 80x24 changes each frame (two pixels per cell)',
        xnano=frame_all_xnano,
        rich=frame_all_rich,
        urwid=frame_all_urwid,
    )

    def formula_xnano() -> Callable[[], object]:
        terminal = xnano.open(offscreen=True, width=WIDTH, height=HEIGHT)
        for row in range(HEIGHT):
            ball = terminal.write('●', y=row)
            ball.x = (xnano.expressions.ParentWidth - xnano.expressions.Width) * (
                (xnano.expressions.TimeElapsed / (1 + row % 5)) % 1.0
            )
        counter = [0]

        def run() -> str:
            counter[0] += 1
            terminal.loop.advance(1 / 60)
            return terminal.output.snapshot().ansi

        return run

    def formula_rich() -> Callable[[], object]:
        console, sink = rich_console()
        counter = [0]

        def run() -> str:
            counter[0] += 1
            elapsed = counter[0] / 60
            lines = []
            for row in range(HEIGHT):
                position = int((WIDTH - 1) * ((elapsed / (1 + row % 5)) % 1.0))
                lines.append(' ' * position + '●')
            sink.seek(0)
            sink.truncate()
            console.print(rich.console.Group(*lines), end='')
            return sink.getvalue()

        return run

    add(
        'formula_animation',
        'frames',
        '24 balls moving by a formula of time: the library advances the clock and draws',
        xnano=formula_xnano,
        rich=formula_rich,
    )

    # -- the same jobs as rich's own benchmark suite (.workspace/rich/benchmarks) ------------

    snippets = rich_snippets()
    if snippets is not None and rich is not None:
        rich_text = rich.text.Text.from_markup(snippets.MARKUP)

        def spans_of(text: object) -> xnano.styles.StyledText:
            """The same styled runs, as xnano spans."""
            console, _ = rich_console()
            spans = []
            for segment in text.render(console):  # type: ignore[attr-defined]
                style = segment.style
                foreground = (
                    style.color.get_truecolor() if style and style.color else None
                )
                background = (
                    style.bgcolor.get_truecolor() if style and style.bgcolor else None
                )
                spans.append(
                    xnano.styles.TextSpan(
                        segment.text,
                        style=Style(
                            foreground=tuple(foreground) if foreground else None,
                            background=tuple(background) if background else None,
                        ),
                    )
                )
            return xnano.styles.StyledText(spans)

        marked = spans_of(rich_text)
        add(
            'wrap_markup_12',
            'rich_suite',
            'rich benchmark TextSuite.time_wrapping: styled text folded to 12 columns',
            xnano=lambda: xnano_widget(
                Paragraph(marked, should_wrap=True, width=12, height=400)
            ),
            rich=lambda: rich_render(rich_text, 12),
            urwid=lambda: urwid_render(urwid.Text(rich_text.plain), 12),
        )
        add(
            'wrap_unicode_12',
            'rich_suite',
            'TextSuite.time_wrapping_unicode_heavy: unicode-heavy text folded to 12 columns',
            xnano=lambda: xnano_widget(
                Paragraph(
                    snippets.UNICODE_HEAVY_TEXT, should_wrap=True, width=12, height=400
                )
            ),
            rich=lambda: rich_render(rich.text.Text(snippets.UNICODE_HEAVY_TEXT), 12),
            urwid=lambda: urwid_render(urwid.Text(snippets.UNICODE_HEAVY_TEXT), 12),
        )
        add(
            'fit_12',
            'rich_suite',
            'TextSuite.time_fit: lorem ipsum cut to 12 columns, no wrapping',
            xnano=lambda: xnano_widget(
                Paragraph(snippets.LOREM_IPSUM, should_wrap=False, width=12, height=20)
            ),
            rich=lambda: rich_render(
                rich.text.Text(snippets.LOREM_IPSUM, no_wrap=True, overflow='crop'), 12
            ),
            urwid=lambda: urwid_render(urwid.Text(snippets.LOREM_IPSUM, wrap='clip'), 12),
        )
        wide = len(snippets.LOREM_IPSUM) * 3
        add(
            'align_center',
            'rich_suite',
            'TextSuite.time_align_center: lorem ipsum centered in a line three times as wide',
            xnano=lambda: xnano_widget(
                Paragraph(
                    snippets.LOREM_IPSUM,
                    should_wrap=False,
                    alignment='center',
                    width=wide,
                    height=1,
                )
            ),
            rich=lambda: rich_render(
                rich.text.Text(snippets.LOREM_IPSUM, justify='center', no_wrap=True), wide
            ),
        )

        def star_wars_xnano(width: int) -> Callable[[], object]:
            rows = [
                ['Dec 20, 2019', 'Star Wars: The Rise of Skywalker', '$952,110,690'],
                ['May 25, 2018', 'Solo: A Star Wars Story', '$393,151,347'],
                ['Dec 15, 2017', 'Star Wars Ep. V111: The Last Jedi', '$1,332,539,889'],
                ['Dec 16, 2016', 'Rogue One: A Star Wars Story', '$1,332,439,889'],
            ]

            def run() -> str:
                table = Table(
                    rows,
                    header=['Released', 'Title', 'Box Office'],
                    widths=[12, max(width - 28, 6), 14],
                    width=width,
                    height=8,
                )
                return table.render(format='ansi')

            return run

        def star_wars_rich(width: int) -> Callable[[], object]:
            def run() -> str:
                table = rich.table.Table(title='Star Wars Movies')
                table.add_column('Released', justify='right', style='cyan', no_wrap=True)
                table.add_column('Title', style='magenta')
                table.add_column('Box Office', justify='right', style='green')
                table.add_row(
                    'Dec 20, 2019',
                    '[b]Star Wars[/]: The Rise of Skywalker',
                    '$952,110,690',
                )
                table.add_row(
                    'May 25, 2018',
                    'Solo: A [red][b]Star Wars[/] Story[/]',
                    '$393,151,347',
                )
                table.add_row(
                    'Dec 15, 2017',
                    '[b red]Star Wars[/] Ep. V111: The Last Jedi',
                    '$1,332,539,889',
                )
                table.add_row(
                    'Dec 16, 2016',
                    'Rogue One: A [blue]Star Wars[/] Story',
                    '$1,332,439,889',
                )
                return rich_render(table, width)()

            return run

        for label, width in (('no_wrapping', 100), ('heavy_wrapping', 30)):
            add(
                f'star_wars_table_{label}',
                'rich_suite',
                f'TableSuite: the Star Wars table at {width} columns, built and rendered each call',
                xnano=lambda width=width: star_wars_xnano(width),
                rich=lambda width=width: star_wars_rich(width),
            )

        add(
            'style_parse',
            'rich_suite',
            'StyleSuite.time_parse_*: make a style with foreground and background colors',
            xnano=lambda: lambda: repr(Style(foreground='#f0f0f0', background='#e2e28a')),
            rich=lambda: lambda: repr(rich.style.Style.parse('#f0f0f0 on #e2e28a')),
        )
        add(
            'style_add',
            'rich_suite',
            'StyleSuite.time_style_add: combine two styles',
            xnano=lambda: (lambda a, b: lambda: repr(a.patch(b)))(
                Style(foreground='blue', background='red'),
                Style(foreground='green', italic=True, bold=True),
            ),
            rich=lambda: (lambda a, b: lambda: repr(a + b))(
                rich.style.Style.parse('blue on red'),
                rich.style.Style.parse('green italic bold'),
            ),
        )

    # -- only xnano has these, so they show cost without a rival ----------------------------

    def effect_frame() -> Callable[[], object]:
        terminal = xnano.open(offscreen=True, width=WIDTH, height=HEIGHT)
        for row in range(HEIGHT):
            terminal.write('effects keep running ' * 3, y=row)
        terminal.root.update(
            xnano.effects.Effect.fade_to((255, 0, 0), duration_milliseconds=10_000_000)
        )

        def run() -> str:
            terminal.loop.advance(1 / 60)
            return terminal.output.snapshot().ansi

        return run

    add(
        'effect_frame',
        'only_xnano',
        'one frame while a fade effect runs over all of 80x24',
        xnano=effect_frame,
    )

    def key_round_trip() -> Callable[[], object]:
        terminal = xnano.open(offscreen=True, width=WIDTH, height=HEIGHT)
        seen = [0]
        digit = terminal.write('0')

        @terminal.hook(when=lambda context: context.keyboard is not None)
        def count(context: xnano.context.Context) -> None:
            seen[0] += 1
            digit.text = str(seen[0] % 10)

        event = xnano.events.Event.key_press('a')

        def run() -> str:
            terminal.inject(event)
            terminal.loop.advance(1 / 60)
            return str(seen[0])

        return run

    add(
        'key_to_frame',
        'only_xnano',
        'a key press reaches a hook, which writes, and a frame is drawn',
        xnano=key_round_trip,
    )

    @dataclass
    class Settings:
        volume: int = 0

    def state_to_frame() -> Callable[[], object]:
        terminal = xnano.open(
            offscreen=True, width=WIDTH, height=HEIGHT, state=Settings()
        )

        def volume(state: Settings) -> int:
            return state.volume

        reference = terminal.ref(volume)
        bar = terminal.write(Gauge(reference.number / 100, width=60, height=1))
        assert bar
        counter = [0]

        def run() -> str:
            counter[0] += 1
            terminal.state.volume = counter[0] % 100
            terminal.loop.advance(1 / 60)
            return terminal.output.snapshot().ansi

        return run

    add(
        'state_to_frame',
        'only_xnano',
        'a state write updates a gauge through an expression and a frame is drawn',
        xnano=state_to_frame,
    )

    def image_conversion() -> Callable[[], object]:
        image = xnano.image.TerminalImage.from_rgba(
            256, 256, bytes([40, 120, 220, 255]) * 65_536
        )
        return lambda: image.to_cell_grid(64, 32)

    add(
        'image_to_cells',
        'only_xnano',
        'convert a 256x256 image to a 64x32 cell grid (resampling included)',
        xnano=image_conversion,
    )

    def sound_render() -> Callable[[], object]:
        return lambda: xnano.audio.TerminalSound.__name__ and xnano_render_note()

    def xnano_render_note() -> str:
        from xnano_audio import render_note

        return str(len(render_note('piano', 'C4', duration_milliseconds=500).samples()))

    add(
        'render_note',
        'only_xnano',
        'synthesize half a second of piano (no device)',
        xnano=sound_render,
    )

    # -- fixed costs ------------------------------------------------------------------------

    def import_time(module: str) -> Callable[[], object]:
        def run() -> str:
            start = time.perf_counter()
            subprocess.run(
                [sys.executable, '-c', f'import {module}'],
                check=True,
                capture_output=True,
            )
            return f'{time.perf_counter() - start:.4f}'

        return run

    baseline = subprocess.run  # keep the name used above
    del baseline
    add(
        'import_time',
        'startup',
        'start a fresh interpreter and import the library (includes interpreter start-up)',
        xnano=lambda: import_time('xnano'),
        rich=lambda: import_time('rich.console, rich.table, rich.panel, rich.text'),
        urwid=lambda: import_time('urwid'),
        prompt_toolkit=lambda: import_time('prompt_toolkit.shortcuts'),
    )

    add(
        'open_and_close',
        'startup',
        'create a console or terminal, draw one line, and tear it down',
        xnano=lambda: _open_close_xnano,
        rich=lambda: _open_close_rich,
        urwid=lambda: _open_close_urwid,
    )

    return found


def _xnano_panel() -> str:
    panel = Block('title', border_type='rounded', width=WIDTH, height=12)
    text = Paragraph(LOREM[:600], should_wrap=True, width=WIDTH - 2, height=10, x=1, y=1)
    panel.attach(text)
    return panel.render(format='ansi')


def _open_close_xnano() -> str:
    with xnano.open(offscreen=True, width=WIDTH, height=HEIGHT) as terminal:
        terminal.write('hello')
        return terminal.output.render().ansi


def _open_close_rich() -> str:
    console, sink = rich_console()
    console.print('hello', end='')
    return sink.getvalue()


def _open_close_urwid() -> str:
    return urwid_render(urwid.Text('hello'))()


# ---------------------------------------------------------------------------------------
# Running and reporting
# ---------------------------------------------------------------------------------------


def rich_snippets() -> ModuleType | None:
    """The inputs rich's own benchmarks use, when its repository is checked out in .workspace."""
    import importlib.util
    import pathlib

    path = (
        pathlib.Path(__file__).resolve().parent.parent
        / '.workspace'
        / 'rich'
        / 'benchmarks'
        / 'snippets.py'
    )
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location('rich_benchmark_snippets', path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def run(selected: list[str], *, libraries: tuple[str, ...]) -> list[Case]:
    """Time every case whose name contains one of ``selected`` (all when empty)."""
    chosen = []
    for case in cases():
        if selected and not any(
            word in case.name or word in case.group for word in selected
        ):
            continue
        for library in libraries:
            builder = case.builders.get(library)
            if builder is None:
                continue
            try:
                function = builder()
                case.results[library] = measure(
                    function,
                    budget=1.0 if case.name == 'import_time' else 0.25,
                    repeats=3 if case.name == 'import_time' else 7,
                )
            except Exception as error:  # report it and carry on
                print(
                    f'  ! {case.name} / {library}: {type(error).__name__}: {error}',
                    file=sys.stderr,
                )
        chosen.append(case)
    return chosen


def report(chosen: list[Case], libraries: tuple[str, ...]) -> None:
    """Print a table, one row per case, with xnano's speed relative to each other library."""
    others = [library for library in libraries if library != 'xnano']
    header = (
        f'{"case":<30}{"xnano":>12}'
        + ''.join(f'{library:>16}' for library in others)
        + '   verdict'
    )
    print(header)
    print('-' * len(header))
    group = ''
    for case in chosen:
        if case.group != group:
            group = case.group
            print(f'[{group}]')
        ours = case.results.get('xnano')
        cells = [
            f'{case.name:<30}',
            f'{format_time(ours.median):>12}' if ours else f'{"-":>12}',
        ]
        slower_than = []
        for library in others:
            theirs = case.results.get(library)
            if ours is None or theirs is None:
                cells.append(f'{"-":>16}')
                continue
            ratio = theirs.median / ours.median
            cells.append(f'{format_time(theirs.median):>9} {ratio:>5.1f}x')
            if ratio < 1.0:
                slower_than.append(library)
        compared = [library for library in others if library in case.results]
        if not compared:
            verdict = ''
        elif slower_than:
            verdict = 'SLOWER than ' + ', '.join(slower_than)
        else:
            verdict = 'faster than all'
        print(''.join(cells) + '   ' + verdict)
    print()
    print(
        "Each column after xnano shows that library's time and, in the second figure, how many"
    )
    print('times as long it takes as xnano (above 1.0x means xnano is faster).')


def show(
    names: list[str], libraries: tuple[str, ...], seconds: float, fps: float
) -> None:
    """
    Draw every case in every library, one after the other, in this terminal.

    Each library's output is redrawn in place for ``seconds`` at ``fps``, so an
    animation moves and a static case simply stays, and the screen shows what each library's
    format actually looks like. Press ``Ctrl-C`` to stop. (urwid's canvases are shown without
    color, because it reports colors through its own attribute tables.)
    """
    interval = 1.0 / fps
    try:
        for case in cases():
            if names and not any(
                word in case.name or word in case.group for word in names
            ):
                continue
            if case.name in ('import_time', 'open_and_close'):
                continue
            for library in libraries:
                builder = case.builders.get(library)
                if builder is None:
                    continue
                try:
                    function = builder()
                except Exception as error:
                    print(f'{case.name} / {library}: {type(error).__name__}: {error}')
                    continue
                deadline = time.perf_counter() + seconds
                count = 0
                while time.perf_counter() < deadline:
                    started = time.perf_counter()
                    output = str(function())
                    lines = output.split('\n')[:30]
                    header = f'\x1b[0m\x1b[1m{case.name}  ·  {library}\x1b[0m   {case.description}'
                    sys.stdout.write(
                        '\x1b[H\x1b[2J' + header + '\n\n' + '\n'.join(lines) + '\x1b[0m\n'
                    )
                    sys.stdout.flush()
                    count += 1
                    time.sleep(max(0.0, interval - (time.perf_counter() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\x1b[0m\x1b[?25h\n')


def refuse_debug_build(*, allowed: bool) -> None:
    """Stop before timing an unoptimized extension, which is several times slower."""
    import importlib
    import importlib.util

    debug = [
        name
        for name in ('xnano_core', 'xnano_audio', 'xnano_image')
        if importlib.util.find_spec(name) is not None
        and not importlib.import_module(name).is_optimized_build
    ]
    if not debug or allowed:
        return
    sys.exit(
        f'The xnano extensions {", ".join(debug)} in this environment are debug builds, which run several times '
        'slower than a release build, so timing it would be unfair to xnano.\n'
        'Build the optimized extensions first with `make compare` (it does that and then runs '
        'this), or pass --allow-debug to time it anyway.'
    )


def main() -> None:
    """Parse arguments, run the cases and print the table."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'names',
        nargs='*',
        help='only cases whose name or group contains one of these words',
    )
    parser.add_argument('--json', help='also write the numbers to this file')
    parser.add_argument('--libraries', nargs='*', default=list(LIBRARIES))
    parser.add_argument(
        '--allow-debug', action='store_true', help='time a debug build anyway'
    )
    parser.add_argument(
        '--show', action='store_true', help='draw every case live instead of timing'
    )
    parser.add_argument(
        '--seconds',
        type=float,
        default=2.0,
        help='how long --show draws each case in each library',
    )
    parser.add_argument(
        '--fps', type=float, default=20.0, help='redraws per second in --show'
    )
    arguments = parser.parse_args()
    libraries = tuple(arguments.libraries)
    if not arguments.show:
        refuse_debug_build(allowed=arguments.allow_debug)
    if arguments.show:
        show(arguments.names, libraries, arguments.seconds, arguments.fps)
        return
    chosen = run(arguments.names, libraries=libraries)
    report(chosen, libraries)
    if arguments.json:
        payload = {
            case.name: {
                library: result.median for library, result in case.results.items()
            }
            for case in chosen
        }
        with open(arguments.json, 'w', encoding='utf-8') as file:
            json.dump(payload, file, indent=2)


if __name__ == '__main__':
    main()
