"""
tests.test_context

What a hook receives: live views, input objects and the members that were removed.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.devices import Keyboard, Mouse
from xnano.effects import EffectController
from xnano.errors import TerminalError
from xnano.expressions import Expression
from xnano.hooks import Context, Frame, Plugin, Update
from xnano.layout import Region
from xnano_core import Buffer, Event, Point, Size


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=6, fps=10) as opened:
        yield opened


def push(canvas, *events: Event) -> None:
    for event in events:
        canvas.push(event)
    canvas.deliver_events()


class TestLiveViews:
    def test_in_a_canvas_hook_the_buffer_and_the_root_are_the_canvas_and_the_parent_its_screen(
        self, canvas
    ):
        seen: list[Context] = []
        canvas.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        context = seen[0]
        assert context.canvas is canvas
        assert context.buffer is canvas
        assert context.parent is canvas.screen
        assert context.root is canvas
        assert (context.buffer.screen.x, context.buffer.screen.y) == (0, 0)

    def test_in_a_placement_hook_the_views_have_concrete_values(self, canvas):
        box = canvas.screen.write(Buffer(width=4, height=2), x=5, y=3)
        values: dict[str, object] = {}

        @box.hook(on='key')
        def look(context: Context) -> None:
            values['buffer'] = context.buffer
            values['parent'] = context.parent
            values['x'] = context.buffer.x
            values['parent_width'] = context.parent.width
            values['root_height'] = context.root.screen.height

        push(canvas, Event.key_press('a'))
        assert values['buffer'] is box
        assert values['parent'] is canvas.screen
        assert values['x'] == 5
        assert values['parent_width'] == 20
        assert values['root_height'] == 6

    def test_the_parent_of_a_nested_placement_is_its_placement(self, canvas):
        track = canvas.screen.write(Buffer(width=10, height=1), y=2)
        thumb = track.write(Buffer(width=1, height=1), x=3)
        parents = []
        thumb.hook(lambda context: parents.append(context.parent), on='key')
        push(canvas, Event.key_press('a'))
        assert parents == [track]

    def test_buffer_has_the_verbs_of_a_placement(self, canvas):
        box = canvas.screen.write(Buffer(width=2, height=1), x=1)

        @box.hook(on='key')
        def step_right(context: Context) -> None:
            context.buffer.right(2)

        push(canvas, Event.key_press('a'))
        assert box.x == 3

    def test_on_the_objects_themselves_parent_and_root_stay_formulas(self, canvas):
        box = canvas.screen.write('x')
        assert isinstance(box.parent.width, Expression)
        assert isinstance(box.root.time, Expression)

    def test_local_turns_a_screen_cell_into_a_cell_of_the_buffer(self, canvas):
        box = canvas.screen.write(Buffer(width=4, height=2), x=5, y=3)
        cells: list[Point] = []
        box.hook(lambda context: cells.append(context.local(Point(6, 4))), on='key')
        push(canvas, Event.key_press('a'))
        assert cells == [Point(1, 1)]


class TestRegion:
    def test_the_region_of_a_canvas_hook_is_the_cells_of_the_canvas(self, canvas):
        seen: list[Context] = []
        canvas.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        region = seen[0].region
        assert region.resolution == 'cells'
        assert region.size == Size(20, 6)
        assert seen[0].size == region.size

    def test_the_region_of_a_placement_hook_is_where_the_placement_is_drawn(self, canvas):
        box = canvas.screen.write(Buffer(width=4, height=2), x=5, y=3)
        seen: list[Context] = []
        box.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        region = seen[0].region
        assert (region.x, region.y) == (5, 3)
        assert (region.width, region.height) == (4, 2)
        assert seen[0].size == Size(4, 2), 'the size is the shortcut for region.size'

    def test_inside_a_border_the_region_is_the_area_inside_it(self, canvas):
        card = canvas.screen.write('hi', x=2, y=1, border='plain')
        seen: list[Context] = []
        card.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        region = seen[0].region
        assert (region.x, region.y, region.width, region.height) == (3, 2, 2, 1)
        assert seen[0].size == Size(2, 1)

    def test_the_size_is_the_size_of_the_region_inside_every_border_and_padding(self):
        with xnano.new(width=10, height=4, border='plain') as bordered:
            seen: dict[str, Context] = {}
            card = bordered.screen.write(
                Buffer(width=4, height=2), x=2, y=1, border='plain', padding=1
            )
            label = bordered.screen.write('hi', x=1, y=1, border='rounded')
            for name, owner in (('canvas', bordered), ('card', card), ('label', label)):
                owner.hook(
                    lambda context, name=name: seen.__setitem__(name, context), on='key'
                )
            push(bordered, Event.key_press('a'))
            assert set(seen) == {'canvas', 'card', 'label'}
            for context in seen.values():
                assert context.size == context.region.size
            assert seen['canvas'].size == Size(8, 2)
            assert seen['card'].size == Size(4, 2)
            assert seen['label'].size == Size(2, 1)
            assert seen['canvas'].canvas.screen.size == Size(10, 4), (
                'the window is canvas.screen.size'
            )

    def test_reading_the_size_makes_no_region(self, canvas, monkeypatch):
        sizes: dict[str, Size] = {}
        box = canvas.screen.write(Buffer(width=4, height=2), x=5, y=3)
        for name, owner in (('canvas', canvas), ('box', box)):
            owner.hook(
                lambda context, name=name: sizes.__setitem__(name, context.size),
                on='key',
            )

        def forbidden(*arguments, **keywords):
            raise AssertionError('context.size made a Region')

        monkeypatch.setattr(Region, '__init__', forbidden)
        push(canvas, Event.key_press('a'))
        assert sizes == {'canvas': Size(20, 6), 'box': Size(4, 2)}

    def test_the_region_of_a_hook_is_on_the_screen_and_refuses_the_timeline(self, canvas):
        seen: list[Context] = []
        canvas.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        with pytest.raises(TerminalError, match='timeline') as raised:
            _ = seen[0].region.beats
        assert raised.value.code == 'canvas.state'

    def test_a_generator_hook_reads_the_region_of_each_event(self, canvas):
        box = canvas.screen.write(Buffer(width=4, height=2), x=5, y=3)
        widths: list[int] = []

        @box.hook(on='key')
        def watch(context: Context):
            while True:
                widths.append(context.region.width)
                context = yield

        push(canvas, Event.key_press('a'))
        box.width = 6
        push(canvas, Event.key_press('b'))
        assert widths == [4, 6]


class TestMembers:
    def test_the_members_of_the_canvas(self, canvas):
        seen: list[Context] = []
        canvas.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        context = seen[0]
        assert context.clock is canvas.clock
        assert context.screen.cursor is canvas.screen.cursor
        assert context.size == Size(20, 6)
        assert isinstance(context.keyboard, Keyboard)
        assert isinstance(context.mouse, Mouse)
        assert context.deps is None
        assert isinstance(context.fx, EffectController)
        assert isinstance(context.plugin, Plugin)
        assert context.plugin.hook is context.hook
        assert context.event.kind == 'key'

    def test_the_speaker_plays_on_the_canvas(self, canvas):
        pytest.importorskip('xnano_audio')
        seen: list[Context] = []
        canvas.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        seen[0].speaker.play('C4')
        assert len(canvas._audio_device()._recordings) == 1

    def test_the_state_is_read_from_the_root(self):
        import dataclasses

        @dataclasses.dataclass
        class Settings:
            volume: int = 3

        with xnano.new(width=8, height=1, state=Settings()) as canvas:
            seen: list[int] = []
            canvas.hook(lambda context: seen.append(context.root.state.volume), on='key')
            push(canvas, Event.key_press('a'))
        assert seen == [3]

    def test_frames_and_updates_are_events(self, canvas):
        events = []
        canvas.hook(lambda context: events.append(context.event), on='frame')
        canvas.hook(lambda context: events.append(context.event), on='tick')
        canvas.clock.step(delta_seconds=0.1)
        assert any(isinstance(event, Frame) for event in events)
        assert any(isinstance(event, Update) for event in events)

    @pytest.mark.parametrize(
        'name',
        [
            'terminal',
            'target',
            'pasted',
            'size_changed',
            'focus_gained',
            'bounds',
            'x',
            'y',
            'width',
            'height',
            'core',
            'state',
        ],
    )
    def test_the_removed_members_are_gone(self, canvas, name):
        seen: list[Context] = []
        canvas.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        assert not hasattr(seen[0], name)
