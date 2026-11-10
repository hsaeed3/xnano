"""
xnano.demo

The feature demo: ``python -m xnano``. It opens with an animation, then shows five pages that
each use a different part of xnano: live panels, the widgets, the effects, sound and input.
It is written with the public API only, so it doubles as a larger example.

The left and right arrows (or ``tab``) change the page, the up and down arrows move the
choice of a page, ``enter`` plays it again, and ``q`` quits. With the mouse, click a page name
or a line of a list.

Pictures need the ``image`` extra and sound needs the ``audio`` extra. Without one of them the
demo still runs: it draws its art from text, or stays silent, and names the extra to install.
"""

from __future__ import annotations

import collections
import datetime
import importlib.util
import math
import pathlib
from collections.abc import Callable

import xnano
from xnano.buffers import Buffer, Cell
from xnano.expressions import (
    Height,
    NumericValue,
    ParentHeight,
    ParentWidth,
    TimeElapsed,
    Width,
)
from xnano.hooks._context import Context
from xnano.layout._placement import Placement
from xnano.styles import Style
from xnano.terminal import Terminal
from xnano.widgets import (
    Bar,
    BarChart,
    Block,
    Calendar,
    Chart,
    ChartAxis,
    ChartDataset,
    Figure,
    FigureCircle,
    FigurePoints,
    Gauge,
    ItemList,
    LineGauge,
    Paragraph,
    Sparkline,
    Table,
    Tabs,
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
INK = '#f0e6dc'  # the wordmark over the opening animation, whose colors are fixed
ACCENT = 'cyan'  # the one accent: the chosen page, the chosen line and the live values
MINIMUM_WIDTH, MINIMUM_HEIGHT = 80, 24
PAGES = ('overview', 'widgets', 'effects', 'sound', 'input')
HINTS = {
    'overview': 'space pause time',
    'widgets': '↑ ↓ choose a widget',
    'effects': '↑ ↓ choose an effect · enter play again',
    'sound': 'a to k play · ↑ ↓ instrument · enter melody · m mute',
    'input': 'press a key · click anywhere',
}
NOTES = dict(
    zip('asdfghjk', ('C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'), strict=True)
)
INSTRUMENTS = ('piano', 'bell', 'marimba', 'synth', 'pluck', 'organ', 'strings', 'kick')
MELODY = 'C4 E4 G4 C5:2 G4 E4 C4:2'
EFFECTS = ('coalesce', 'fade in', 'sweep in', 'slide in', 'hue shift')
WIDGETS = (
    'bar chart',
    'calendar',
    'chart',
    'gauge',
    'line gauge',
    'paragraph',
    'sparkline',
    'table',
    'tabs',
)
SUNSET = (  # the art of the demo without the image extra: one character is one pixel
    'DDDDDDDDDDDDDDDDDDDDDDDD',
    'DDDDDDDDDDDDDDDDDDDDDDDD',
    'PPPPPPPPPPPPPPPPPPPPPPPP',
    'PPPPPPPPPPYYYYPPPPPPPPPP',
    'OOOOOOOOYYYYYYYYOOOOOOOO',
    'OOOOOOOYYYYYYYYYYOOOOOOO',
    'OOOOOOOYYYYYYYYYYOOOOOOO',
    'MMMMMMMMMMMMMMMMMMMMMMMM',
    'MMMMYYYYYYYYYYYYYYYYMMMM',
    'MMMMMMMMYYYYYYYYMMMMMMMM',
    'MMMMMMMMMMYYYYMMMMMMMMMM',
    'MMMMMMMMMMMMMMMMMMMMMMMM',
)
SUNSET_PALETTE = 'D=#3b3565 P=#8f5c8a O=#d98a6a Y=#f2cf8d M=#2a2748'
ABOUT = (
    'Each panel is one write() call. Its position and size are expressions of the '
    'window, so the layout follows a resize. The gauges, the ball and the orbit '
    'follow the clock.'
)

Number = NumericValue[int | float]


def edge(fraction: float) -> Number:
    """A column of the window, as an expression of its width."""
    return (ParentWidth * fraction) // 1


def row(fraction: float) -> Number:
    """A row between the page names and the hint line, as an expression of the height."""
    return 1 + ((ParentHeight - 2) * fraction) // 1


def has_extra(package: str) -> bool:
    """Whether the package behind an optional extra, such as ``'xnano_image'``, is installed."""
    return importlib.util.find_spec(package) is not None


class _Demo:
    """The pages of the demo, and what changes in them."""

    def __init__(self, terminal: Terminal[None, None]) -> None:
        """
        Prepare the state of the pages.

        Args:
            terminal: The terminal the demo draws on.
        """
        self.terminal = terminal
        self.page = 0
        self.is_muted = False
        self.has_images = has_extra('xnano_image')
        self.has_sound = False
        self.events: collections.deque[str] = collections.deque(maxlen=12)
        self.samples = [round(4 + 3.5 * math.sin(index / 3)) for index in range(60)]
        self.intro: list[Placement[None, None]] = []
        self.placements: dict[str, list[Placement[None, None]]] = {
            name: [] for name in PAGES
        }
        self.previews: list[Placement[None, None]] = []

    # -- the opening animation ----------------------------------------------------------

    def start(self) -> None:
        """Play the opening animation, then build the pages on the first key."""
        terminal = self.terminal
        if self.has_images:
            clip = xnano.load_image(ASSETS / 'luffy.xni')
            self.intro.append(
                terminal.screen.write(
                    clip, x='center', y='center', width='100%', height='100%'
                )
            )
        self.intro.append(
            terminal.screen.write(
                wordmark(INK if self.has_images else None),
                x='center',
                y='center',
                layer=2,
            )
        )
        self.intro.append(
            terminal.screen.write(
                'press any key',
                x='center',
                y=ParentHeight - 2,
                layer=2,
                style=Style('#b0a6c8') if self.has_images else Style(dim=True),
            )
        )

        @terminal.hook(on='key')
        def begin(context: Context) -> None:
            context.hook.remove()
            for placement in self.intro:
                placement.remove()
            self.build()

    # -- the frame around the pages -----------------------------------------------------

    def build(self) -> None:
        """Write the page names, the hint line and every page, then show the first page."""
        terminal = self.terminal
        screen = terminal.screen
        self.has_sound = has_extra('xnano_audio') and terminal.speaker.is_available
        screen.write(' xnano ', x=0, y=0, bold=True, reverse=True)
        self.tabs: list[Placement[None, None]] = []
        column = 9
        for index, name in enumerate(PAGES):
            tab = screen.write(f' {name} ', x=column, y=0)
            column += len(name) + 3
            self.tabs.append(tab)
            self.on_press(tab, lambda index=index: self.show_page(index))
        self.hint = screen.write('', x=1, y='bottom', dim=True)
        self.notice = screen.write(
            '', x='center', y='center', layer=3, border='rounded', padding=1
        )

        self.build_overview()
        self.build_widgets()
        self.build_effects()
        self.build_sound()
        self.build_input()
        self.listen()
        self.show_page(0)

    def on_press(
        self, placement: Placement[None, None], action: Callable[[], None]
    ) -> None:
        """Run ``action`` when the mouse is pressed on ``placement``."""

        @placement.hook(on='mouse')
        def press(context: Context) -> None:
            if context.mouse.kind == 'press':
                action()

    def panel(
        self,
        page: str,
        title: str,
        left: float,
        right: float,
        top: float,
        bottom: float,
    ) -> None:
        """A titled border around a part of ``page``."""
        self.add(
            page,
            Block(title, border_type='rounded', border_style=Style(dim=True)),
            left,
            right,
            top,
            bottom,
            is_border=True,
        )

    def add(
        self,
        page: str,
        content: object,
        left: float,
        right: float,
        top: float,
        bottom: float,
        *,
        is_border: bool = False,
    ) -> Placement[None, None]:
        """Write ``content`` on ``page``, inside the panel between the four fractions."""
        inset_x, inset_y = (0, 0) if is_border else (2, 1)
        placement = self.terminal.screen.write(
            content,  # type: ignore[arg-type]
            x=edge(left) + inset_x,
            y=row(top) + inset_y,
            width=edge(right) - edge(left) - 2 * inset_x,
            height=row(bottom) - row(top) - 2 * inset_y,
            layer=0 if is_border else 1,
        )
        return self.keep(page, placement)

    def keep(self, page: str, placement: Placement[None, None]) -> Placement[None, None]:
        """Make ``placement`` a part of ``page``: it shows only while that page does."""
        self.placements[page].append(placement)
        return placement

    def show_page(self, index: int) -> None:
        """Show the page at ``index`` and hide the others, or ask for a larger window."""
        self.page = index % len(PAGES)
        name = PAGES[self.page]
        screen = self.terminal.screen
        is_small = screen.width < MINIMUM_WIDTH or screen.height < MINIMUM_HEIGHT
        for page, placements in self.placements.items():
            for placement in placements:
                placement.is_visible = page == name and not is_small
        for preview_index, preview in enumerate(self.previews):
            preview.is_visible = (
                name == 'widgets' and not is_small and preview_index == self.widget
            )
        for tab_index, tab in enumerate(self.tabs):
            tab.reverse(tab_index == self.page).bold(tab_index == self.page)
        self.notice.is_visible = is_small
        if is_small:
            self.notice.text = (
                f'The demo needs {MINIMUM_WIDTH} by {MINIMUM_HEIGHT} cells.\n'
                f'This window has {screen.width} by {screen.height}.\n'
                f'Make the window larger, or press q to quit.'
            )
            self.hint.text = 'q quit'
            return
        self.hint.text = f'{HINTS[name]} · ← → page · q quit'
        if name == 'effects':
            self.play_effect()

    # -- overview: panels that follow the clock ------------------------------------------

    def build_overview(self) -> None:
        """Gauges, charts, a calendar and a figure, each in a panel of its own."""
        terminal = self.terminal
        page = 'overview'
        self.panel(page, 'time', 0.0, 0.34, 0.0, 0.45)
        self.panel(page, 'charts', 0.34, 0.67, 0.0, 0.45)
        self.panel(page, 'calendar', 0.67, 1.0, 0.0, 0.45)
        self.panel(page, 'figure', 0.0, 0.6, 0.45, 1.0)
        self.panel(page, 'how it is made', 0.6, 1.0, 0.45, 1.0)

        inner = edge(0.34) - 4
        screen = terminal.screen
        self.time = self.keep(page, screen.write('', x=2, y=row(0.0) + 1, layer=1))
        sweep = LineGauge(
            (TimeElapsed % 4) / 4, label='sweep', filled_style=Style(ACCENT)
        )
        self.wave = LineGauge(0.5, label='wave ', filled_style=Style(ACCENT))
        for line, gauge in enumerate((sweep, self.wave), 3):
            self.keep(
                page,
                screen.write(
                    gauge, x=2, y=row(0.0) + line, width=inner, height=1, layer=1
                ),
            )
        ball = self.keep(page, screen.write('●', y=row(0.0) + 6, layer=1))
        ball.x = 2 + (edge(0.34) - 5) * (TimeElapsed % 3 / 3)

        self.spark = Sparkline(self.samples, maximum=8, style=Style(ACCENT))
        self.keep(
            page,
            screen.write(
                self.spark,
                x=edge(0.34) + 2,
                y=row(0.0) + 1,
                width=edge(0.67) - edge(0.34) - 4,
                height=2,
                layer=1,
            ),
        )
        self.bars = BarChart([Bar(4, name) for name in 'abcde'], bar_width=3, maximum=8)
        self.keep(
            page,
            screen.write(
                self.bars,
                x=edge(0.34) + 2,
                y=row(0.0) + 4,
                width=edge(0.67) - edge(0.34) - 4,
                height=row(0.45) - row(0.0) - 5,
                layer=1,
            ),
        )

        today = datetime.date.today()
        calendar = Calendar(
            today.year,
            today.month,
            today.day,
            month_header_style=Style(bold=True),
            weekdays_header_style=Style(dim=True),
        )
        self.add(page, calendar, 0.67, 1.0, 0.0, 0.45)

        self.figure = Figure(x_bounds=(-10, 10), y_bounds=(-10, 10), marker='braille')
        self.add(page, self.figure, 0.0, 0.6, 0.45, 1.0)
        self.add(page, Paragraph(ABOUT, should_wrap=True), 0.6, 1.0, 0.45, 1.0)
        orbit = [
            (8 * math.cos(angle / 36 * math.tau), 8 * math.sin(angle / 36 * math.tau))
            for angle in range(36)
        ]

        @terminal.hook(on='frame')
        def turn(context: Context) -> None:
            if PAGES[self.page] != 'overview':
                return
            time = context.clock.elapsed_seconds
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

        @terminal.hook(on='tick', every=0.12)
        def refresh(context: Context) -> None:
            elapsed = context.clock.elapsed_seconds
            self.wave.ratio = 0.5 + 0.45 * math.sin(elapsed * 2)
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
            self.show_time()

        self.show_time()

    def show_time(self) -> None:
        """Say how long the clock has run, and whether it is paused."""
        clock = self.terminal.clock
        state = '‖ paused' if clock.is_paused else '▶ running'
        self.time.text = f'{state}  {clock.elapsed_seconds:6.1f} s'

    # -- widgets: a list, and the chosen widget beside it --------------------------------

    def build_widgets(self) -> None:
        """Every widget once, with a list to choose the one that shows."""
        page = 'widgets'
        self.widget = 0
        self.panel(page, 'widgets', 0.0, 0.3, 0.0, 1.0)
        self.panel(page, 'preview', 0.3, 1.0, 0.0, 1.0)
        self.widget_list = self.choice_list(page, WIDGETS, self.choose_widget)
        wave = [(step / 4, math.sin(step / 4)) for step in range(50)]
        widgets: tuple[object, ...] = (
            BarChart(
                [Bar(73, label='cpu'), Bar(41, label='memory'), Bar(18, label='network')],
                bar_width=8,
                bar_gap=3,
                bar_style=Style(ACCENT),
            ),
            Calendar(2026, 1, 1, month_header_style=Style(bold=True)),
            Chart(
                [
                    ChartDataset(
                        name='sin',
                        data=wave,
                        marker='braille',
                        graph_type='line',
                        style=Style(ACCENT),
                    )
                ],
                x_axis=ChartAxis(bounds=(0, 12), labels=['0', '6', '12']),
                y_axis=ChartAxis(bounds=(-1, 1), labels=['-1', '0', '1']),
            ),
            Gauge(0.6, label='60% of 512 GB', gauge_style=Style('green')),
            LineGauge(0.8, label='upload', filled_style=Style(ACCENT)),
            Paragraph(
                'A paragraph wraps its text at the width it is given, and can align it '
                'to the left, the center or the right.',
                should_wrap=True,
                alignment='center',
            ),
            Sparkline(
                [round(6 + 3 * math.sin(second / 4)) for second in range(60)],
                style=Style(ACCENT),
            ),
            Table(
                [
                    ['web', '● up', '41 ms'],
                    ['api', '● up', '12 ms'],
                    ['db', '× down', ''],
                ],
                header=['service', 'status', 'p95'],
                widths=[12, 10, 8],
            ),
            Tabs(
                ['overview', 'logs', 'settings'],
                selected=1,
                highlight_style=Style(ACCENT, bold=True),
            ),
        )
        short = {'gauge': 0.2, 'line gauge': 0.12, 'tabs': 0.12, 'sparkline': 0.3}
        for name, widget in zip(WIDGETS, widgets, strict=True):
            preview = self.add(page, widget, 0.3, 1.0, 0.0, short.get(name, 1.0))
            self.placements[page].remove(preview)
            self.previews.append(preview)

    def choose_widget(self, index: int) -> None:
        """Show the widget at ``index`` of the list in the preview."""
        self.widget = index % len(WIDGETS)
        self.widget_list.selected = self.widget
        self.show_page(self.page)

    def choice_list(
        self, page: str, names: tuple[str, ...], choose: Callable[[int], None]
    ) -> ItemList:
        """A list on the left of ``page``: a click on a line calls ``choose`` with its place."""
        choices = ItemList(
            list(names),
            selected=0,
            highlight_symbol='› ',
            highlight_style=Style(ACCENT, bold=True),
        )
        placement = self.add(page, choices, 0.0, 0.3, 0.0, 1.0)

        @placement.hook(on='mouse')
        def press(context: Context) -> None:
            position = context.mouse.position
            if context.mouse.kind == 'press' and position is not None:
                line = placement.local(position).y
                if 0 <= line < len(names):
                    choose(line)

        return choices

    # -- effects: a picture, and the effects that play on it -----------------------------

    def build_effects(self) -> None:
        """A picture in the middle of its panel, and a list of the effects to play on it."""
        page = 'effects'
        self.effect = 0
        self.panel(page, 'effects', 0.0, 0.3, 0.0, 1.0)
        self.panel(
            page, 'picture' if self.has_images else 'pixel art', 0.3, 1.0, 0.0, 1.0
        )
        self.effect_list = self.choice_list(page, EFFECTS, self.choose_effect)
        screen = self.terminal.screen
        if self.has_images:
            art = screen.write(xnano.Image(ASSETS / 'dusk.png', width='50%', layer=1))
        else:
            # each pixel of the art twice in both directions, so it fills more of its panel
            pixels = [
                ''.join(pixel * 2 for pixel in line) for line in SUNSET for _ in range(2)
            ]
            art = screen.write(xnano.pixel_art(pixels, SUNSET_PALETTE), layer=1)
            hint = self.keep(
                page,
                screen.write(
                    'pip install "xnano[image]" adds pictures', layer=1, dim=True
                ),
            )
            hint.x = edge(0.3) + (edge(1.0) - edge(0.3) - Width) // 2
            hint.y = row(1.0) - 2
        # Centered in its panel by expressions of its own size, so a resize needs no code.
        art.x = edge(0.3) + (edge(1.0) - edge(0.3) - Width) // 2
        art.y = row(0.0) + (row(1.0) - row(0.0) - Height) // 2
        self.art = self.keep(page, art)

    def choose_effect(self, index: int) -> None:
        """Choose the effect at ``index`` of the list, and play it."""
        self.effect = index % len(EFFECTS)
        self.effect_list.selected = self.effect
        self.play_effect()

    def play_effect(self) -> None:
        """Play the chosen effect on the picture."""
        art = self.art
        name = EFFECTS[self.effect]
        if name == 'coalesce':
            art.update(xnano.effect('effect.coalesce', duration_milliseconds=1200))
        elif name == 'fade in':
            art.fx.fade_from(
                foreground='black', background='black', duration_milliseconds=900
            )
        elif name == 'sweep in':
            art.fx.sweep_in(color=ACCENT, duration_milliseconds=800)
        elif name == 'slide in':
            art.fx.slide_in(direction='left_to_right', duration_milliseconds=800)
        else:
            art.fx.hsl_shift(
                foreground=(180, 0, 0), background=(180, 0, 0), duration_milliseconds=1200
            )

    # -- sound: instruments, and a row of keys to play them ------------------------------

    def build_sound(self) -> None:
        """A list of instruments, and the eight keys that play their notes."""
        page = 'sound'
        self.instrument = 0
        self.panel(page, 'instruments', 0.0, 0.3, 0.0, 1.0)
        self.panel(page, 'keys', 0.3, 1.0, 0.0, 1.0)
        self.instrument_list = self.choice_list(page, INSTRUMENTS, self.choose_instrument)
        screen = self.terminal.screen
        self.keys: dict[str, Placement[None, None]] = {}
        for index, (key, note) in enumerate(NOTES.items()):
            cap = screen.write(
                f'{key}\n{note}',
                x=edge(0.3) + 3 + index * 6,
                y=row(0.0) + 2,
                width=6,
                border='rounded',
                layer=1,
            )
            self.keys[key] = self.keep(page, cap)
            self.on_press(cap, lambda key=key: self.play_note(key))
        self.sound = self.keep(
            page, screen.write('', x=edge(0.3) + 3, y=row(0.0) + 7, layer=1)
        )
        self.show_sound()

    def choose_instrument(self, index: int) -> None:
        """Choose the instrument at ``index`` of the list."""
        self.instrument = index % len(INSTRUMENTS)
        self.instrument_list.selected = self.instrument
        self.show_sound()

    def show_sound(self) -> None:
        """Say which instrument plays, or why there is no sound."""
        if not has_extra('xnano_audio'):
            state = 'Sound needs an extra: pip install "xnano[audio]"'
        elif not self.has_sound:
            state = '× This computer has no sound output.'
        elif self.is_muted:
            state = '× muted: press m for sound'
        else:
            state = f'♪ {INSTRUMENTS[self.instrument]}'
        self.sound.text = state

    def play_note(self, key: str) -> None:
        """Mark the key that was pressed, and play its note on the chosen instrument."""
        cap = self.keys[key]
        cap.reverse(True)

        @self.terminal.hook(on='tick', after=0.15)
        def release(context: Context) -> None:
            cap.reverse(False)

        if self.has_sound and not self.is_muted:
            self.terminal.speaker.play(
                xnano.Note(NOTES[key], beats=0.5),
                instrument=INSTRUMENTS[self.instrument],
            )

    # -- input: what the keyboard and the mouse report -----------------------------------

    def build_input(self) -> None:
        """The newest key and click, a log of the ones before, and a mark where you click."""
        page = 'input'
        self.panel(page, 'newest', 0.0, 0.4, 0.0, 0.4)
        self.panel(page, 'log', 0.4, 1.0, 0.0, 1.0)
        self.panel(page, 'click here', 0.0, 0.4, 0.4, 1.0)
        self.newest = self.add(
            page, 'key    none yet\nmouse  none yet', 0.0, 0.4, 0.0, 0.4
        )
        self.log = Paragraph('')
        self.add(page, self.log, 0.4, 1.0, 0.0, 1.0)
        self.key_text, self.mouse_text = 'none yet', 'none yet'
        self.mark = self.keep(page, self.terminal.screen.write('●', layer=2))
        self.mark.color.fg = ACCENT
        self.mark.x = edge(0.2)
        self.mark.y = row(0.7)

    def remember(self, text: str) -> None:
        """Add a line to the log of the input page."""
        self.events.append(text)
        self.log.text = '\n'.join(self.events)
        self.newest.text = f'key    {self.key_text}\nmouse  {self.mouse_text}'

    # -- the keys and the mouse of every page --------------------------------------------

    def listen(self) -> None:
        """Hear the keys that change the page, move a choice and act on the page."""
        terminal = self.terminal

        @terminal.hook(on='key')
        def log_key(context: Context) -> None:
            key = context.keyboard.key
            if key is not None:
                self.key_text = key
                self.remember(f'key {key}')

        @terminal.hook(on='key', keys=['left', 'right', 'tab'])
        def change_page(context: Context) -> None:
            step = -1 if context.keyboard.key == 'left' else 1
            self.show_page(self.page + step)

        @terminal.hook(on='key', keys=['up', 'down'])
        def move_choice(context: Context) -> None:
            step = 1 if context.keyboard.key == 'down' else -1
            name = PAGES[self.page]
            if name == 'widgets':
                self.choose_widget(self.widget + step)
            elif name == 'effects':
                self.choose_effect(self.effect + step)
            elif name == 'sound':
                self.choose_instrument(self.instrument + step)

        @terminal.hook(on='key', keys='enter')
        def act(context: Context) -> None:
            name = PAGES[self.page]
            if name == 'effects':
                self.play_effect()
            elif name == 'sound' and self.has_sound and not self.is_muted:
                terminal.speaker.play(MELODY, instrument=INSTRUMENTS[self.instrument])

        @terminal.hook(on='key', keys='space')
        def toggle_time(context: Context) -> None:
            if PAGES[self.page] != 'overview':
                return
            if terminal.clock.is_paused:
                terminal.clock.resume()
            else:
                terminal.clock.pause()
            self.show_time()

        @terminal.hook(on='key', keys=list(NOTES))
        def play(context: Context) -> None:
            key = context.keyboard.key
            if key is not None and PAGES[self.page] == 'sound':
                self.play_note(key)

        @terminal.hook(on='key', keys='m')
        def mute(context: Context) -> None:
            if PAGES[self.page] == 'sound':
                self.is_muted = not self.is_muted
                self.show_sound()

        @terminal.hook(on="mouse.kind == 'press'")
        def click(context: Context) -> None:
            position = context.mouse.position
            if position is None:
                return
            self.mouse_text = f'column {position.x}, row {position.y}'
            self.remember(f'click at column {position.x}, row {position.y}')
            is_inside = 0 < position.y < terminal.screen.height - 1
            if PAGES[self.page] == 'input' and is_inside:
                self.mark.x, self.mark.y = position.x, position.y

        @terminal.hook(on='resize')
        def fit(context: Context) -> None:
            self.show_page(self.page)


def wordmark(color: str | None) -> Buffer:
    """
    The ``xnano`` block letters, with see-through gaps so the animation shows between them.

    Args:
        color: The color of the letters, or ``None`` for the terminal's own text color.
    """
    style = Style(color, bold=True) if color is not None else Style(bold=True)
    buffer = Buffer(width=max(len(line) for line in WORDMARK), height=len(WORDMARK))
    for y, line in enumerate(WORDMARK):
        for x in range(buffer.width):
            character = line[x] if x < len(line) else ' '
            if character == ' ':
                buffer[x, y] = Cell(' ', is_transparent=True)
            else:
                buffer[x, y] = Cell(character, style=style)
    return buffer


def main() -> None:
    """Run the demo in the whole window."""
    with xnano.open(mouse=True, title='xnano', state=None) as terminal:
        _Demo(terminal).start()
        terminal.run(stop_on=('q', 'ctrl+c'))
