"""
xnano.demo

The feature demo: ``python -m xnano``. It opens with an animation, then fills the window with
live panels that each use a different part of xnano. It is written with the public API only,
so it doubles as a larger example.
"""

from __future__ import annotations

import collections
import datetime
import math
import pathlib

import xnano
from xnano.buffers import Buffer, Cell
from xnano.context import Context
from xnano.expressions import (
    Height,
    NumericValue,
    ParentHeight,
    ParentWidth,
    TimeElapsed,
    Width,
)
from xnano.placement import Placement
from xnano.styles import Style
from xnano.terminal import Terminal
from xnano.widgets import (
    Bar,
    BarChart,
    Block,
    Calendar,
    Figure,
    FigureCircle,
    FigurePoints,
    LineGauge,
    Paragraph,
    Sparkline,
    Table,
)

__all__ = ['main']

ASSETS = pathlib.Path(__file__).parent / 'assets'
WORDMARK = (
    '█   █   █   █  ███   █   █   ███ ',
    ' █ █    ██  █ █   █  ██  █  █   █',
    '  █     █ █ █ █████  █ █ █  █   █',
    ' █ █    █  ██ █   █  █  ██  █   █',
    '█   █   █   █ █   █  █   █   ███ ',
)
INK = '#f0e6dc'
MUTED = '#8f92c0'
NOTES = dict(
    zip('asdfghjk', ('C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'), strict=True)
)
INSTRUMENTS = ('piano', 'bell', 'marimba', 'synth', 'pluck', 'organ', 'strings', 'kick')
FEATURES = (
    ('formulas for positions', 'live'),
    ('typed state', 'ready'),
    ('tachyonfx effects', 'live'),
    ('pixels and art', 'live'),
    ('images and animations', 'live'),
    ('notes and melodies', 'live'),
    ('mouse and keyboard', 'live'),
)


def edge(fraction: float) -> NumericValue[int | float]:
    """A column of the window, as a formula of its width."""
    return (ParentWidth * fraction) // 1


def row(fraction: float) -> NumericValue[int | float]:
    """A row below the title, as a formula of the window's height."""
    return 1 + ((ParentHeight - 2) * fraction) // 1


class _Demo:
    """The demo's panels, and what changes in them."""

    def __init__(self, terminal: Terminal[None, None]) -> None:
        """
        Prepare the panels' state.

        Args:
            terminal: The terminal the demo draws on.
        """
        self.terminal = terminal
        self.is_muted = False
        self.instrument = 0
        self.events: collections.deque[str] = collections.deque(maxlen=8)
        self.samples = [3] * 40
        self.intro: list[Placement[None, None]] = []
        self.log = Paragraph('', style=Style(INK))

    # -- the opening animation ----------------------------------------------------------

    def start(self) -> None:
        """Play the opening animation, then build the panels on the first key."""
        terminal = self.terminal
        clip = xnano.load_image(ASSETS / 'luffy.xni')
        self.intro.append(
            terminal.write(clip, x='center', y='center', width='100%', height='100%')
        )
        self.intro.append(terminal.write(wordmark(), x='center', y='center', layer=2))
        self.intro.append(
            terminal.write(
                'press any key',
                x='center',
                y=ParentHeight - 2,
                layer=2,
                style=Style('#b0a6c8'),
            )
        )

        @terminal.hook(on='key')
        def begin(context: Context) -> None:
            context.hook.remove()
            for placement in self.intro:
                placement.remove()
            self.build()

    # -- the panels ---------------------------------------------------------------------

    def panel(
        self, title: str, left: float, right: float, top: float, bottom: float
    ) -> None:
        """A titled border around a part of the window."""
        self.terminal.write(
            Block(title, border_type='rounded', border_style=Style(MUTED)),
            x=edge(left),
            y=row(top),
            width=edge(right) - edge(left),
            height=row(bottom) - row(top),
        )

    def build(self) -> None:
        """Fill the window with panels, each showing one part of xnano."""
        terminal = self.terminal
        terminal.write(' xnano 2 ', x=1, y=0, style=Style('black', INK, bold=True))
        terminal.write(
            'tab: instrument   a-k: notes   e: effect   space: stop time   m: mute   q: quit',
            x='right',
            y=0,
            style=Style(MUTED),
        )

        self.panel('expressions', 0.0, 0.27, 0.0, 0.3)
        self.panel('widgets', 0.0, 0.27, 0.3, 0.62)
        self.panel('features', 0.0, 0.27, 0.62, 1.0)
        self.panel('pixel art', 0.27, 0.73, 0.0, 0.6)
        self.panel('figure', 0.27, 0.73, 0.6, 1.0)
        self.panel('sound', 0.73, 1.0, 0.0, 0.34)
        self.panel('calendar', 0.73, 1.0, 0.34, 0.66)
        self.panel('events', 0.73, 1.0, 0.66, 1.0)

        self.build_expressions()
        self.build_widgets()
        self.build_features()
        self.build_art()
        self.build_figure()
        self.build_sound()
        self.build_calendar()
        self.build_events()

    def build_expressions(self) -> None:
        """Gauges and a ball whose positions are formulas of time: no loop moves them."""
        terminal = self.terminal
        inner = edge(0.27) - 4
        sweep = LineGauge(
            (TimeElapsed % 4) / 4, label='sweep', filled_style=Style('#d8b9a3')
        )
        terminal.write(sweep, x=2, y=row(0.0) + 1, width=inner, height=1, layer=1)
        self.wave = LineGauge(0.5, label='wave ', filled_style=Style('#c9a6b8'))
        terminal.write(self.wave, x=2, y=row(0.0) + 2, width=inner, height=1, layer=1)
        self.load = LineGauge(0.5, label='load ', filled_style=Style('#8f92c0'))
        terminal.write(self.load, x=2, y=row(0.0) + 3, width=inner, height=1, layer=1)
        ball = terminal.write('●', y=row(0.0) + 5, layer=1)
        ball.x = 2 + (edge(0.27) - 5) * (TimeElapsed % 3 / 3)

    def build_widgets(self) -> None:
        """A sparkline and a bar chart, refreshed from a timer."""
        terminal = self.terminal
        inner = edge(0.27) - 4
        self.spark = Sparkline(self.samples, maximum=8, style=Style('#8f92c0'))
        terminal.write(self.spark, x=2, y=row(0.3) + 1, width=inner, height=2, layer=1)
        self.bars = BarChart(
            [Bar(3, 'a'), Bar(5, 'b'), Bar(2, 'c'), Bar(6, 'd'), Bar(4, 'e')],
            bar_width=3,
            maximum=8,
            bar_style=Style('#d8b9a3'),
        )
        terminal.write(
            self.bars,
            x=2,
            y=row(0.3) + 3,
            width=inner,
            height=row(0.62) - row(0.3) - 4,
            layer=1,
        )

    def build_features(self) -> None:
        """A table of what xnano does."""
        table = Table(
            [[name, state] for name, state in FEATURES],
            header=['feature', ''],
            widths=[24, 6],
            style=Style(INK),
        )
        self.terminal.write(
            table,
            x=2,
            y=row(0.62) + 1,
            width=edge(0.27) - 4,
            height=row(1.0) - row(0.62) - 2,
            layer=1,
        )

    def build_art(self) -> None:
        """Pixel art that refits the window: it is sized by percentages, so it is unlocked."""
        art = self.terminal.write(
            xnano.Image(ASSETS / 'dusk.png', y=row(0.0) + 1, width='43%', layer=1)
        )
        # Centered in its panel by formulas of its own size, so a resize needs no code.
        art.x = edge(0.27) + (edge(0.73) - edge(0.27) - Width) // 2
        art.y = row(0.0) + (row(0.6) - row(0.0) - Height) // 2
        self.art = art

    def build_figure(self) -> None:
        """Shapes in coordinates of your own, redrawn on every frame."""
        terminal = self.terminal
        self.figure = Figure(x_bounds=(-10, 10), y_bounds=(-10, 10), marker='braille')
        terminal.write(
            self.figure,
            x=edge(0.27) + 1,
            y=row(0.6) + 1,
            width=edge(0.73) - edge(0.27) - 2,
            height=row(1.0) - row(0.6) - 2,
            layer=1,
        )
        orbit = [
            (8 * math.cos(angle / 36 * math.tau), 8 * math.sin(angle / 36 * math.tau))
            for angle in range(36)
        ]

        @terminal.hook(on='frame')
        def draw(context: Context) -> None:
            time = context.time.elapsed
            self.figure.clear_shapes()
            self.figure.extend_shapes(
                [
                    FigurePoints(orbit, 'gray'),
                    FigureCircle(0, 0, 2, 'yellow'),
                    FigureCircle(8 * math.cos(time), 8 * math.sin(time), 1, 'cyan'),
                    FigureCircle(
                        4 * math.cos(time * 2.2), 4 * math.sin(time * 2.2), 0.6, 'magenta'
                    ),
                ]
            )

    def build_sound(self) -> None:
        """The instruments, and a keyboard to play them; quiet when there is no sound card."""
        self.sound = self.terminal.write(
            '',
            x=edge(0.73) + 2,
            y=row(0.0) + 1,
            width=edge(1.0) - edge(0.73) - 4,
            height=row(0.34) - row(0.0) - 2,
            layer=1,
        )
        self.show_sound()

    def show_sound(self) -> None:
        """Say which instrument is chosen."""
        lines = []
        for index, name in enumerate(INSTRUMENTS):
            lines.append(('▶ ' if index == self.instrument else '  ') + name)
        status = 'muted' if self.is_muted else 'a-k to play'
        self.sound.text = '\n'.join([*lines[:7], status])

    def build_calendar(self) -> None:
        """Today, in a calendar widget."""
        today = datetime.date.today()
        calendar = Calendar(
            today.year,
            today.month,
            today.day,
            month_header_style=Style(INK, bold=True),
            weekdays_header_style=Style(MUTED),
        )
        self.terminal.write(
            calendar,
            x=edge(0.73) + 2,
            y=row(0.34) + 1,
            width=edge(1.0) - edge(0.73) - 4,
            height=row(0.66) - row(0.34) - 2,
            layer=1,
        )

    def build_events(self) -> None:
        """Every key and click, as they arrive: hooks hear them all."""
        terminal = self.terminal
        terminal.write(
            self.log,
            x=edge(0.73) + 2,
            y=row(0.66) + 1,
            width=edge(1.0) - edge(0.73) - 4,
            height=row(1.0) - row(0.66) - 2,
            layer=1,
        )
        self.remember('hover and click: the mouse is on')

        @terminal.hook(on='tick', every=0.12)
        def refresh(context: Context) -> None:
            elapsed = context.time.elapsed
            self.wave.ratio = 0.5 + 0.45 * math.sin(elapsed * 2)
            self.load.ratio = 0.55 + 0.3 * math.sin(elapsed * 0.7 + 1) * math.cos(
                elapsed * 1.9
            )
            self.samples.append(
                round(4 + 3.5 * math.sin(elapsed * 3) * math.sin(elapsed * 0.9))
            )
            del self.samples[0]
            self.spark.values = list(self.samples)
            self.bars.clear()
            for index, name in enumerate('abcde'):
                self.bars.append(
                    Bar(round(4 + 3.5 * math.sin(elapsed * 1.3 + index)), name)
                )

        @terminal.hook(on='key', keys='tab')
        def next_instrument(context: Context) -> None:
            self.instrument = (self.instrument + 1) % len(INSTRUMENTS)
            self.show_sound()
            self.remember(f'instrument: {INSTRUMENTS[self.instrument]}')

        @terminal.hook(on='key', keys=list(NOTES))
        def play(context: Context) -> None:
            if context.keyboard.key is None:
                return
            note = NOTES[context.keyboard.key]
            self.remember(f'note {note} on {INSTRUMENTS[self.instrument]}')
            if not self.is_muted and terminal.audio.is_available:
                terminal.play(
                    xnano.note(note, beats=0.5),
                    instrument=INSTRUMENTS[self.instrument],
                )

        @terminal.hook(on='key', keys='m')
        def mute(context: Context) -> None:
            self.is_muted = not self.is_muted
            self.show_sound()

        @terminal.hook(on='key', keys='e')
        def replay_effect(context: Context) -> None:
            self.art.update(xnano.effect('effect.coalesce', duration_milliseconds=1200))
            self.remember('effect: coalesce')

        @terminal.hook(on='key', keys='space')
        def toggle_time(context: Context) -> None:
            if terminal.time.is_stopped:
                terminal.time.resume()
            else:
                terminal.time.stop()
            self.remember(
                'time: ' + ('stopped' if terminal.time.is_stopped else 'running')
            )

        @terminal.hook(on='mouse', when="mouse.kind == 'press'")
        def click(context: Context) -> None:
            if context.mouse.position is not None:
                self.remember(
                    f'click at {context.mouse.position.x},{context.mouse.position.y}'
                )

    def remember(self, text: str) -> None:
        """Add a line to the event log."""
        self.events.append(text)
        self.log.text = '\n'.join(self.events)


def wordmark() -> Buffer:
    """The ``xnano`` block letters, with see-through gaps so the animation shows between them."""
    buffer = Buffer(width=max(len(line) for line in WORDMARK), height=len(WORDMARK))
    for y, line in enumerate(WORDMARK):
        for x in range(buffer.width):
            character = line[x] if x < len(line) else ' '
            if character == ' ':
                buffer[x, y] = Cell(' ', is_transparent=True)
            else:
                buffer[x, y] = Cell(character, style=Style(INK, bold=True))
    return buffer


def main() -> None:
    """Run the demo in the whole window."""
    with xnano.open(mouse=True, title='xnano', state=None) as terminal:
        _Demo(terminal).start()
        terminal.run(quit_on=('q', 'ctrl+c'))
