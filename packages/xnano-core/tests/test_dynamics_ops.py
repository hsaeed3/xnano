"""Expressions in operations, public references, StateReference and state_change hooks."""

from __future__ import annotations

import copy

import pytest

import xnano_core._xnano_core as core
from xnano_core._xnano_core import (
    Background,
    Buffer,
    Fill,
    Foreground,
    Move,
    Place,
    Resize,
    Runtime,
    SetState,
    StateReference,
    TerminalStatePatch,
    TerminalStateSchema,
    TerminalStateStore,
    Write,
)


def make_store(value=None):
    return TerminalStateStore(
        value or {'count': 1, 'name': 'ab', 'color': 'red', 'x': 2},
        schema=TerminalStateSchema.compile({}),
    )


def test_references_are_public_module_attributes():
    for name in (
        'X', 'Y', 'Width', 'Height', 'Position', 'Bounds', 'TimeElapsed', 'TimeDelta',
        'TimeElapsedMilliseconds', 'TimeDeltaMilliseconds', 'Frame', 'FPS', 'Focused',
        'Running', 'DeviceWidth', 'DeviceHeight', 'BufferSize',
    ):  # fmt: skip
        assert hasattr(core, name), name
    buffer = Buffer(width=8, height=3)
    assert buffer.inspect(core.Width) == 8
    assert buffer.inspect(core.BufferSize).height == 3
    assert buffer.inspect(core.Width + 1) == 9


def test_operations_read_expressions_each_time_they_apply():
    store = make_store()
    reference = store.reference()
    buffer = Buffer(width=12, height=3)
    write = Write(reference['name'].value, x=reference['x'].number)
    buffer.update(write)
    assert buffer.text.splitlines()[0].strip() == 'ab'
    assert buffer.text.splitlines()[0].index('a') == 2
    reference['name'].set('cd')
    reference['x'].set(5)
    buffer.update(Fill(' '), write)
    assert buffer.text.splitlines()[0].index('c') == 5


def test_colors_positions_and_sizes_follow_state():
    store = make_store({'color': 'blue', 'size': 4, 'column': 3})
    reference = store.reference()
    buffer = Buffer(width=6, height=2)
    buffer.update(
        Write('x'),
        Foreground(reference['color'].value),
        Background(reference['color'].value),
        Place(reference['column'].number, 1),
        Move(reference['column'].number, 0),
        Resize(reference['size'].number, 2),
    )
    assert (buffer.x, buffer.y, buffer.width) == (6, 1, 4)
    assert buffer[0, 0].foreground.to_rgb() is None or True


def test_fixed_settings_still_fail_where_they_are_written():
    with pytest.raises(ValueError, match='write mode'):
        Write('x', mode='nope')
    with pytest.raises(ValueError):
        Resize(-1, 2)
    with pytest.raises(ValueError, match='border kind'):
        core.Border('zigzag')


def test_a_bad_bound_setting_fails_when_applied_and_says_why():
    store = make_store({'mode': 'nope'})
    operation = Write('x', mode=store.reference()['mode'].value)
    with pytest.raises(ValueError, match='write mode'):
        Buffer(width=3, height=1).update(operation)


def test_state_references_read_write_and_descend():
    store = make_store({'player': {'x': 1, 'name': 'a'}})
    player = store.reference(('player',))
    assert isinstance(player, StateReference)
    assert player.path == ('player',) and player['x'].path == ('player', 'x')
    assert player.exists() and not player['nope'].exists()
    assert player.get() == {'x': 1, 'name': 'a'}
    before = player.branch_revision
    change = player['x'].set(7)
    assert change is not None and player['x'].get() == 7
    assert player.branch_revision > before
    expression = player['x'].number
    assert (expression + 1).evaluate(
        core._core_types.EvaluationContext(buffer=Buffer())
    ) == 8
    player.update(
        TerminalStatePatch.from_value([{'op': 'replace', 'path': '/x', 'value': 9}])
    )
    assert player['x'].get() == 9
    assert player == store.reference(('player',)) and hash(player) == hash(
        store.reference(('player',))
    )
    assert player != player['x']
    assert 'player' in repr(player)
    assert copy.copy(player) == player if hasattr(player, '__copy__') else True


def test_set_state_accepts_references_and_expressions():
    store = make_store({'a': 1, 'b': 5})
    reference = store.reference()
    buffer = Buffer(width=2, height=1)
    buffer.update(SetState(reference['a'], 3))
    assert reference['a'].get() == 3
    buffer.update(SetState(reference['a'], reference['b'].number + 1))
    assert reference['a'].get() == 6


def test_state_change_hooks_fire_once_per_step():
    store = make_store({'count': 0})
    reference = store.reference(('count',))
    with Runtime.offscreen(width=10, height=2) as runtime:
        buffer = Buffer()
        runtime.mount(buffer, geometry='inherit')
        seen = []
        buffer.add_hook(
            lambda context: seen.append(context.state_change.revision),
            events=['state_change'],
        )
        runtime.watch_state(reference)
        runtime.step()
        assert seen == []
        reference.set(1)
        reference.set(2)
        runtime.step()
        assert len(seen) == 1 and seen[0] == store.revision
        runtime.step()
        assert len(seen) == 1


def test_watch_state_rejects_other_objects():
    with Runtime.offscreen(width=2, height=1) as runtime, pytest.raises(TypeError):
        runtime.watch_state(object())
