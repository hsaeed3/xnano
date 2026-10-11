"""Private bridge from the v1 scene model to the current retained core."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from xnano import _xnano_core as core

from . import _ratatui as ratatui

CoreEvent = core.Event
CoreKeyBinding = core.KeyBinding


class _CallableText(str):
    def __call__(self):
        return str(self)


class CoreTextEditor:
    def __init__(self, text=''):
        self._editor = core.TextEditor(text)
        self._placeholder_text = None

    def __getattr__(self, name):
        if name == 'text':
            return _CallableText(self._editor.text)
        return getattr(self._editor, name)

    def __setattr__(self, name, value):
        if name in {'_editor', '_placeholder_text'}:
            object.__setattr__(self, name, value)
        elif name == 'placeholder_text':
            object.__setattr__(self, '_placeholder_text', value)
        else:
            setattr(self._editor, name, value)

    @property
    def placeholder_text(self):
        return self._placeholder_text

    @property
    def cursor_location(self):
        prefix = self._editor.text[: self._editor.cursor_offset]
        return prefix.count('\n'), len(prefix.rsplit('\n', 1)[-1])


@dataclass
class CoreRenderNode:
    content: Any = None
    children: list[CoreRenderNode] = field(default_factory=list)
    key: str | None = None
    position: Any = None
    layer: int = 0
    arrangement: str = 'overlay'
    spacing: int = 0
    padding: Any = None
    size: Any = None
    is_visible: bool = True

    @classmethod
    def overlay(cls, nodes):
        return cls(children=list(nodes))

    @classmethod
    def row(cls, nodes, spacing=0):
        return cls(children=list(nodes), arrangement='row', spacing=spacing)

    @classmethod
    def column(cls, nodes, spacing=0):
        return cls(children=list(nodes), arrangement='column', spacing=spacing)


class CoreRenderContent:
    @staticmethod
    def ratatui_widget(widget):
        return CoreWidget(widget.native)


class CoreNodeSize:
    fill = staticmethod(ratatui.RatatuiConstraint.fill)
    percent = staticmethod(ratatui.RatatuiConstraint.percentage)
    ratio = staticmethod(ratatui.RatatuiConstraint.ratio)
    minimum = staticmethod(ratatui.RatatuiConstraint.minimum)


class CoreWidget:
    def __init__(self, factory):
        self.factory = factory

    def native(self, width, height):
        return self.factory(width, height)

    @staticmethod
    def style(foreground=None, background=None, modifiers=()):
        names = {'slow_blink': 'blink', 'reversed': 'reverse'}
        flags = {names.get(name, name): True for name in modifiers}
        return core.Style(foreground=foreground, background=background, **flags)

    @classmethod
    def text(
        cls,
        text,
        *,
        foreground=None,
        background=None,
        modifiers=(),
        alignment=None,
        should_wrap=True,
    ):
        if isinstance(text, list):
            parts = []
            for index, line in enumerate(text):
                if index:
                    parts.append(core.TextSpan('\n'))
                parts.extend(line.spans if isinstance(line, core.StyledText) else [line])
            text = core.StyledText(parts)
        elif isinstance(text, core.TextSpan):
            text = core.StyledText([text])
        return cls(
            lambda width, height: core.Paragraph(
                text,
                style=cls.style(foreground, background, modifiers),
                alignment=alignment,
                should_wrap=should_wrap,
                width=width,
                height=height,
            )
        )

    @classmethod
    def gauge(cls, ratio, *, label=None, foreground=None, background=None):
        return cls(
            lambda width, height: core.Gauge(
                ratio,
                label=label,
                gauge_style=cls.style(foreground, background),
                width=width,
                height=height,
            )
        )

    @classmethod
    def line_gauge(
        cls,
        ratio,
        *,
        label=None,
        foreground=None,
        background=None,
        filled_foreground=None,
        unfilled_foreground=None,
    ):
        return cls(
            lambda width, height: core.LineGauge(
                ratio,
                label=label,
                style=cls.style(foreground, background),
                filled_style=cls.style(filled_foreground),
                unfilled_style=cls.style(unfilled_foreground),
                width=width,
                height=height,
            )
        )

    @classmethod
    def bar_chart(
        cls,
        data,
        *,
        bar_width=1,
        bar_gap=1,
        group_gap=1,
        maximum_value=None,
        direction='vertical',
        foreground=None,
        value_foreground=None,
        label_foreground=None,
    ):
        return cls(
            lambda width, height: core.BarChart(
                data,
                bar_width=bar_width,
                bar_gap=bar_gap,
                group_gap=group_gap,
                maximum=maximum_value,
                direction=direction,
                bar_style=cls.style(foreground),
                value_style=cls.style(value_foreground),
                label_style=cls.style(label_foreground),
                width=width,
                height=height,
            )
        )

    @classmethod
    def sparkline(
        cls,
        data,
        *,
        maximum_value=None,
        foreground=None,
        background=None,
        absent_value_foreground=None,
        absent_value_symbol=None,
    ):
        return cls(
            lambda width, height: core.Sparkline(
                data,
                maximum=maximum_value,
                style=cls.style(foreground, background),
                absent_value_style=cls.style(absent_value_foreground),
                absent_value_symbol=absent_value_symbol,
                width=width,
                height=height,
            )
        )

    @classmethod
    def item_list(
        cls,
        items,
        *,
        selected_index=None,
        foreground=None,
        background=None,
        highlight_foreground=None,
        highlight_background=None,
        highlight_symbol=None,
    ):
        return cls(
            lambda width, height: core.ItemList(
                [core.ListItem(item) for item in items],
                selected=selected_index,
                style=cls.style(foreground, background),
                highlight_style=cls.style(highlight_foreground, highlight_background),
                highlight_symbol=highlight_symbol,
                width=width,
                height=height,
            )
        )

    @classmethod
    def table(
        cls,
        rows,
        *,
        header=None,
        footer=None,
        column_widths=None,
        column_spacing=1,
        selected_row=None,
        selected_column=None,
        highlight_foreground=None,
        highlight_background=None,
        highlight_symbol=None,
    ):
        rules = [
            core.SizeRule.cells(value) if isinstance(value, int) else _size_rule(value)
            for value in column_widths or []
        ]
        return cls(
            lambda width, height: core.Table(
                rows,
                header=header,
                footer=footer,
                widths=rules,
                column_spacing=column_spacing,
                selected_row=selected_row,
                selected_column=selected_column,
                row_highlight_style=cls.style(highlight_foreground, highlight_background),
                highlight_symbol=highlight_symbol,
                width=width,
                height=height,
            )
        )

    @classmethod
    def scrollbar(
        cls,
        *,
        content_length,
        position,
        viewport_length=None,
        orientation='vertical_right',
        foreground=None,
        thumb_foreground=None,
        track_foreground=None,
        begin_symbol=None,
        end_symbol=None,
    ):
        return cls(
            lambda width, height: core.Scrollbar(
                content_length,
                position,
                viewport_content_length=viewport_length,
                orientation=orientation,
                style=cls.style(foreground),
                thumb_style=cls.style(thumb_foreground),
                track_style=cls.style(track_foreground),
                begin_symbol=begin_symbol,
                end_symbol=end_symbol,
                has_begin=begin_symbol is not None,
                has_end=end_symbol is not None,
                width=width,
                height=height,
            )
        )

    @classmethod
    def clear(cls):
        return cls(lambda width, height: core.Clear(width=width, height=height))

    @classmethod
    def canvas(cls, shapes, *, x_bounds, y_bounds, background=None, marker='braille'):
        return cls(
            lambda width, height: core.Canvas(
                x_bounds,
                y_bounds,
                background_color=background,
                marker=marker,
                shapes=shapes,
                width=width,
                height=height,
            )
        )


def CoreBar(
    value, label=None, *, text_value=None, foreground=None, value_foreground=None
):
    return core.Bar(
        value,
        label,
        text_value=text_value,
        style=CoreWidget.style(foreground),
        value_style=CoreWidget.style(value_foreground),
    )


CoreBarGroup = core.BarGroup


def CoreTableCell(content, *, foreground=None, background=None, modifiers=()):
    return core.TableCell(
        content, style=CoreWidget.style(foreground, background, modifiers)
    )


def CoreTableRow(cells, *, foreground=None, background=None, height=1):
    return core.TableRow(
        cells, style=CoreWidget.style(foreground, background), height=height
    )


class CoreCanvasShape:
    line = staticmethod(
        lambda x1, y1, x2, y2, color=None: core.CanvasLine(x1, y1, x2, y2, color=color)
    )
    points = staticmethod(
        lambda points, color=None: core.CanvasPoints(points, color=color)
    )
    rectangle = staticmethod(
        lambda x, y, width, height, color=None: core.CanvasRectangle(
            x, y, width, height, color=color
        )
    )
    circle = staticmethod(
        lambda x, y, radius, color=None: core.CanvasCircle(x, y, radius, color=color)
    )
    text = staticmethod(
        lambda x, y, text, color=None: core.CanvasLabel(
            x, y, text, style=CoreWidget.style(foreground=color)
        )
    )


def _size_rule(value):
    kind, amount, denominator = value
    return (
        core.SizeRule.percent(amount)
        if kind == 'percentage'
        else core.SizeRule.cells(amount)
        if kind == 'length'
        else core.SizeRule.minimum(amount)
        if kind == 'minimum'
        else core.SizeRule.maximum(amount)
        if kind == 'maximum'
        else core.SizeRule.fill(amount)
        if kind == 'fill'
        else core.SizeRule.percent(round(amount * 100 / denominator))
    )


class _Snapshot:
    def __init__(self, snapshot):
        self.text = snapshot.text
        self.ansi = snapshot.ansi

    def to_string_lines(self):
        return self.text.split('\n')

    def to_ansi_lines(self):
        return self.ansi.split('\n')


class _Waker:
    def __init__(self, runtime):
        self.waker = runtime.waker()

    def call_soon(self, callback, *args):
        self.waker.call_soon(callback, *args)


class CoreSession:
    def __init__(self, runtime):
        self.runtime = runtime
        self.runtime.__enter__()
        self.root = core.Buffer(
            width=runtime.device.size.width, height=runtime.device.size.height
        )
        self.runtime.mount(self.root, geometry='inherit')
        self.areas = {}
        self.stream = runtime.events()
        self.is_live = runtime.clock.source != 'manual'
        self._saved_termios = None

    @classmethod
    def offscreen(cls, width, height):
        return cls(core.Runtime.offscreen(width=width, height=height))

    @classmethod
    def live(cls, **options):
        return cls(core.Runtime.live(**options))

    def enter(self):
        return self

    def restore(self):
        self.runtime.close()

    @property
    def size(self):
        return self.runtime.device.size

    @property
    def clock_milliseconds(self):
        return self.runtime.clock.elapsed_milliseconds

    def advance_clock(self, milliseconds):
        self.runtime.advance_clock(max(0, round(milliseconds)))

    def waker(self):
        return _Waker(self.runtime)

    def render(self, node):
        for child in self.root.children:
            self.root.detach(child)
        self.root.resize(self.size.width, self.size.height)
        self.root.fill(' ')
        self.areas.clear()
        self._attach(
            node, self.root, core.Rectangle(0, 0, self.root.width, self.root.height), 0, 0
        )
        self.runtime.render()

    def _attach(self, node, parent, area, absolute_x, absolute_y):
        if not node.is_visible:
            return
        if node.position is not None:
            area = node.position
        padding = node.padding
        if padding is not None:
            area = core.Rectangle(
                area.x + padding.left,
                area.y + padding.top,
                max(0, area.width - padding.left - padding.right),
                max(0, area.height - padding.top - padding.bottom),
            )
        wrapper = core.Buffer(width=area.width, height=area.height, x=area.x, y=area.y)
        _mark_blank_cells_transparent(wrapper)
        wrapper.layer = node.layer
        parent.attach(wrapper, mode='transparent')
        if node.key is not None:
            self.areas[node.key] = core.Rectangle(
                absolute_x + area.x, absolute_y + area.y, area.width, area.height
            )
        if node.content is not None:
            widget = (
                node.content.native(area.width, area.height)
                if hasattr(node.content, 'native')
                else node.content
            )
            if isinstance(widget, core.Buffer):
                _mark_blank_cells_transparent(widget)
                wrapper.attach(widget, geometry='inherit', mode='transparent')
            else:
                raise TypeError('Native content must be a current core Buffer or Widget')
        child_areas = [core.Rectangle(0, 0, area.width, area.height)] * len(node.children)
        if node.arrangement != 'overlay' and node.children:
            constraints = [
                ratatui.RatatuiConstraint.length(child.size)
                if isinstance(child.size, int)
                else child.size or ratatui.RatatuiConstraint.fill(1)
                for child in node.children
            ]
            child_areas = core.Layout.split(
                child_areas[0],
                arrangement=node.arrangement,
                constraints=constraints,
                spacing=node.spacing,
            )
        for child, child_area in zip(node.children, child_areas):
            self._attach(
                child, wrapper, child_area, absolute_x + area.x, absolute_y + area.y
            )

    def snapshot_buffer(self):
        return _Snapshot(self.runtime.snapshot())

    def poll_event(self, *, timeout_milliseconds=0):
        event = self.stream._poll()
        if event is None:
            self.runtime.step(timeout_milliseconds=timeout_milliseconds)
            event = self.stream._poll()
        return event

    def area_for(self, key):
        return self.areas.get(key)

    def add_effect(self, effect, *, key=None, area_key=None):
        return self.runtime.effects.start(
            effect,
            self.root,
            key=key,
            area=self.areas.get(area_key) if area_key else None,
        )

    def cancel_effect(self, key):
        self.runtime.effects.cancel(key)

    @property
    def has_running_effects(self):
        return len(self.runtime.effects) > 0

    @staticmethod
    def is_live_terminal_available():
        import sys

        return sys.stdin.isatty() and sys.stdout.isatty()

    def resize(self, width, height):
        self.runtime.resize(width, height)

    def _emit(self, value):
        if self.is_live:
            from ._terminal import emit

            emit(value)

    def enable_raw_mode(self):
        import sys

        if sys.platform == 'win32':
            raise OSError('runtime raw mode is managed by the native Windows backend')
        import termios
        import tty

        if self._saved_termios is None:
            self._saved_termios = termios.tcgetattr(sys.stdin.fileno())
        tty.setraw(sys.stdin.fileno())

    def disable_raw_mode(self):
        if self._saved_termios is not None:
            import sys
            import termios

            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._saved_termios)
            self._saved_termios = None

    def enter_alternate_screen(self):
        self._emit('\x1b[?1049h')

    def leave_alternate_screen(self):
        self._emit('\x1b[?1049l')

    def enable_mouse_capture(self):
        self._emit('\x1b[?1000h\x1b[?1002h\x1b[?1006h')

    def disable_mouse_capture(self):
        self._emit('\x1b[?1000l\x1b[?1002l\x1b[?1006l')

    def enable_bracketed_paste(self):
        self._emit('\x1b[?2004h')

    def disable_bracketed_paste(self):
        self._emit('\x1b[?2004l')

    def enable_focus_reporting(self):
        self._emit('\x1b[?1004h')

    def disable_focus_reporting(self):
        self._emit('\x1b[?1004l')

    def begin_synchronized_update(self):
        self._emit('\x1b[?2026h')

    def end_synchronized_update(self):
        self._emit('\x1b[?2026l')

    def show_cursor(self):
        self._emit('\x1b[?25h')

    def hide_cursor(self):
        self._emit('\x1b[?25l')

    def set_cursor_style(self, style):
        self._emit(f'\x1b[{style} q')

    def move_cursor_to(self, x, y):
        self._emit(f'\x1b[{y + 1};{x + 1}H')

    def set_title(self, title):
        title = title.replace('\x1b', '').replace('\x07', '')
        self._emit(f'\x1b]0;{title}\x07')

    def clear_screen(self):
        self._emit('\x1b[2J\x1b[H')


def _mark_blank_cells_transparent(buffer):
    reset = core.Color('reset')
    for row in range(buffer.height):
        for column in range(buffer.width):
            cell = buffer[column, row]
            if cell.symbol == ' ' and cell.background == reset:
                buffer[column, row] = core.Cell(
                    ' ', style=cell.style, is_transparent=True
                )
