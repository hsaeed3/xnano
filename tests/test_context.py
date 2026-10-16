"""
tests.test_context

What a hook receives: live views, input objects and the members that were removed.
"""

from __future__ import annotations

import pytest

import xnano
from xnano._effect_controller import EffectController
from xnano.context import Context, Frame, Plugin, Update
from xnano.expressions import Expression
from xnano.input import Input
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
    def test_in_a_canvas_hook_the_buffer_the_parent_and_the_root_are_the_canvas(
        self, canvas
    ):
        seen: list[Context] = []
        canvas.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        context = seen[0]
        assert context.canvas is canvas
        assert context.buffer is canvas
        assert context.parent is canvas
        assert context.root is canvas
        assert (context.buffer.x, context.buffer.y) == (0, 0)

    def test_in_a_placement_hook_the_views_have_concrete_values(self, canvas):
        box = canvas.write(Buffer(width=4, height=2), x=5, y=3)
        values: dict[str, object] = {}

        @box.hook(on='key')
        def look(context: Context) -> None:
            values['buffer'] = context.buffer
            values['parent'] = context.parent
            values['x'] = context.buffer.x
            values['parent_width'] = context.parent.width
            values['root_height'] = context.root.height

        push(canvas, Event.key_press('a'))
        assert values['buffer'] is box
        assert values['parent'] is canvas
        assert values['x'] == 5
        assert values['parent_width'] == 20
        assert values['root_height'] == 6

    def test_the_parent_of_a_nested_placement_is_its_placement(self, canvas):
        track = canvas.write(Buffer(width=10, height=1), y=2)
        thumb = track.write(Buffer(width=1, height=1), x=3)
        parents = []
        thumb.hook(lambda context: parents.append(context.parent), on='key')
        push(canvas, Event.key_press('a'))
        assert parents == [track]

    def test_buffer_has_the_verbs_of_a_placement(self, canvas):
        box = canvas.write(Buffer(width=2, height=1), x=1)

        @box.hook(on='key')
        def step_right(context: Context) -> None:
            context.buffer.right(2)

        push(canvas, Event.key_press('a'))
        assert box.x == 3

    def test_on_the_objects_themselves_parent_and_root_stay_formulas(self, canvas):
        box = canvas.write('x')
        assert isinstance(box.parent.width, Expression)
        assert isinstance(box.root.time, Expression)

    def test_local_turns_a_screen_cell_into_a_cell_of_the_buffer(self, canvas):
        box = canvas.write(Buffer(width=4, height=2), x=5, y=3)
        cells: list[Point] = []
        box.hook(lambda context: cells.append(context.local(Point(6, 4))), on='key')
        push(canvas, Event.key_press('a'))
        assert cells == [Point(1, 1)]


class TestMembers:
    def test_the_members_of_the_canvas(self, canvas):
        seen: list[Context] = []
        canvas.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        context = seen[0]
        assert context.time is canvas.time
        assert context.cursor is canvas.cursor
        assert context.size == Size(20, 6)
        assert isinstance(context.input, Input)
        assert context.deps is None
        assert isinstance(context.fx, EffectController)
        assert isinstance(context.plugin, Plugin)
        assert context.plugin.hook is context.hook
        assert context.event.kind == 'key'

    def test_audio_is_the_canvas_audio(self, canvas):
        pytest.importorskip('xnano_audio')
        seen: list[Context] = []
        canvas.hook(seen.append, on='key')
        push(canvas, Event.key_press('a'))
        assert seen[0].audio is canvas.audio

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
        canvas.step(delta_seconds=0.1)
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
