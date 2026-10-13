"""Private v1 value and builder adapters backed by the current native core."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from xnano_core import _xnano_core as core

RatatuiRectangle = core.Rectangle


def _names(**values):
    return SimpleNamespace(**values)


RatatuiMarker = _names(
    Dot='dot', Block='block', Bar='bar', Braille='braille', HalfBlock='half_block'
)
RatatuiGraphType = _names(Scatter='scatter', Line='line', Bar='bar')
RatatuiLegendPosition = _names(
    **{
        ''.join(part.title() for part in value.split('_')): value
        for value in (
            'top',
            'top_right',
            'top_left',
            'left',
            'right',
            'bottom',
            'bottom_right',
            'bottom_left',
        )
    }
)
RatatuiBorderType = _names(
    **{
        ''.join(part.title() for part in value.split('_')): value
        for value in (
            'plain',
            'rounded',
            'double',
            'thick',
            'quadrant_inside',
            'quadrant_outside',
        )
    }
)
RatatuiBorders = _names(NONE=0, TOP=1, RIGHT=2, BOTTOM=4, LEFT=8, ALL=15)
RatatuiAlignment = _names(Left='left', Center='center', Right='right')
RatatuiDirection = _names(Horizontal='horizontal', Vertical='vertical')
RatatuiScrollbarOrientation = _names(
    VerticalRight='vertical_right',
    VerticalLeft='vertical_left',
    HorizontalBottom='horizontal_bottom',
    HorizontalTop='horizontal_top',
)
RatatuiModifier = _names(
    **{
        name.upper(): name
        for name in (
            'bold',
            'dim',
            'italic',
            'slow_blink',
            'rapid_blink',
            'reversed',
            'hidden',
            'crossed_out',
        )
    },
    UNDERLINED='underline',
)


class RatatuiColor:
    rgb = staticmethod(core.Color.from_rgb)


def CoreStyle(foreground=None, background=None, modifiers=()):
    names = {'slow_blink': 'blink', 'reversed': 'reverse'}
    flags = {names.get(name, name): True for name in modifiers}
    return core.Style(foreground=foreground, background=background, **flags)


class RatatuiStyle:
    def __init__(self, foreground=None, background=None, modifiers=()):
        self.foreground_value = foreground
        self.background_value = background
        self.modifiers = modifiers

    @classmethod
    def default(cls):
        return cls()

    def foreground(self, value):
        return type(self)(value, self.background_value, self.modifiers)

    def background(self, value):
        return type(self)(self.foreground_value, value, self.modifiers)

    def add_modifier(self, value):
        return type(self)(
            self.foreground_value, self.background_value, (*self.modifiers, value)
        )

    def native(self):
        return CoreStyle(self.foreground_value, self.background_value, self.modifiers)


def native_style(value):
    return value.native() if isinstance(value, RatatuiStyle) else value


class RatatuiSpan:
    @staticmethod
    def styled(text, style):
        return core.TextSpan(text, style=native_style(style))


class RatatuiLine:
    @staticmethod
    def from_spans(spans):
        return core.StyledText(spans)

    @staticmethod
    def raw(text):
        return core.StyledText([core.TextSpan(text)])

    @staticmethod
    def styled(text, style):
        return core.StyledText([RatatuiSpan.styled(text, style)])


@dataclass(frozen=True)
class RatatuiPadding:
    left: int
    right: int
    top: int
    bottom: int

    @classmethod
    def new(cls, left, right, top, bottom):
        return cls(left, right, top, bottom)


class _Builder:
    def __init__(self, **values):
        self.values = values

    @classmethod
    def default(cls):
        return cls()

    def __getattr__(self, name):
        def set_value(value):
            return type(self)(**{**self.values, name: value})

        return set_value


class RatatuiAxis(_Builder):
    def native(self):
        return core.ChartAxis(
            **{
                key: native_style(value) if key == 'style' else value
                for key, value in self.values.items()
            }
        )


class RatatuiDataset(_Builder):
    def native(self):
        return core.ChartDataset(
            **{
                key: native_style(value) if key == 'style' else value
                for key, value in self.values.items()
            }
        )


class RatatuiChart(_Builder):
    @classmethod
    def new(cls, datasets):
        return cls(datasets=datasets)

    def native(self, width, height):
        values = {
            key: value.native()
            if key in ('x_axis', 'y_axis')
            else native_style(value)
            if key == 'style'
            else value
            for key, value in self.values.items()
        }
        values['datasets'] = [value.native() for value in values.get('datasets', [])]
        return core.Chart(width=width, height=height, **values)


class RatatuiBlock(_Builder):
    def native(self, width, height):
        values = dict(self.values)
        sides = values.pop('borders', 0)
        values['borders'] = [
            name
            for bit, name in ((1, 'top'), (2, 'right'), (4, 'bottom'), (8, 'left'))
            if sides & bit
        ]
        title = values.pop('title_top', None)
        if title is not None:
            values['title'] = title
        title = values.pop('title_bottom', None)
        if title is not None:
            values['title'] = core.BlockTitle(title, position='bottom')
        for key in ('style', 'border_style'):
            if key in values:
                values[key] = native_style(values[key])
        return core.Block(width=width, height=height, **values)


class RatatuiConstraint:
    length = staticmethod(lambda value: ('length', value, 1))
    percentage = staticmethod(lambda value: ('percentage', value, 1))
    ratio = staticmethod(lambda value, denominator: ('ratio', value, denominator))
    minimum = staticmethod(lambda value: ('minimum', value, 1))
    maximum = staticmethod(lambda value: ('maximum', value, 1))
    fill = staticmethod(lambda value: ('fill', value, 1))


class RatatuiLayout:
    def __init__(self, direction, constraints, gap=0):
        self.direction, self.constraints, self.gap = direction, constraints, gap

    @classmethod
    def new(cls, direction, constraints):
        return cls(direction, constraints)

    def spacing(self, gap):
        return type(self)(self.direction, self.constraints, gap)

    def split(self, area):
        return core.Layout.split(
            area,
            arrangement='row' if self.direction == 'horizontal' else 'column',
            constraints=self.constraints,
            spacing=self.gap,
        )


def ratatui_tailwind_color(palette, shade):
    return core.Color.from_tailwind(palette, shade)
