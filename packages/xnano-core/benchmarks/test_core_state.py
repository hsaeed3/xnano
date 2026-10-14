"""
Benchmarks for xnano-core state, expressions and events.
"""

from __future__ import annotations

import itertools

from xnano_core._xnano_core import (
    Buffer,
    Event,
    Runtime,
    TerminalStatePatch,
    TerminalStateSchema,
    TerminalStateStore,
    _reference,
)

SCHEMA = TerminalStateSchema.compile(
    {
        'type': 'object',
        'properties': {
            'score': {'type': 'integer', 'minimum': 0},
            'items': {'type': 'array', 'items': {'type': 'string'}},
            'profile': {
                'type': 'object',
                'properties': {'name': {'type': 'string'}, 'level': {'type': 'integer'}},
            },
        },
    }
)


def new_store() -> TerminalStateStore:
    return TerminalStateStore(
        {'score': 0, 'items': ['a', 'b', 'c'], 'profile': {'name': 'x', 'level': 1}},
        schema=SCHEMA,
    )


def test_state_apply_patch(benchmark):
    store = new_store()
    patches = itertools.cycle(
        (
            TerminalStatePatch.from_value(
                [{'op': 'replace', 'path': '/score', 'value': 1}]
            ),
            TerminalStatePatch.from_value(
                [{'op': 'replace', 'path': '/score', 'value': 2}]
            ),
        )
    )
    benchmark(lambda: store.apply(next(patches)))
    assert store.snapshot().to_value()['score'] in (1, 2)


def test_state_apply_patch_with_subscribers(benchmark):
    store = new_store()
    notified = itertools.count()

    def count_notification(change) -> None:
        next(notified)

    for _ in range(20):
        store.subscribe([('score',)], count_notification)
    values = itertools.count(1)

    def apply_and_notify():
        store.apply(
            TerminalStatePatch.from_value(
                [{'op': 'replace', 'path': '/score', 'value': next(values)}]
            )
        )
        store.drain_notifications()

    benchmark(apply_and_notify)
    assert next(notified) >= 20


def test_state_snapshot_to_value(benchmark):
    store = new_store()
    store.apply(
        TerminalStatePatch.from_value(
            [
                {'op': 'add', 'path': '/items/-', 'value': f'item {index}'}
                for index in range(500)
            ]
        )
    )
    value = benchmark(lambda: store.snapshot().to_value())
    assert len(value['items']) == 503


def test_state_schema_rejects_invalid_patch(benchmark):
    store = new_store()
    patch = TerminalStatePatch.from_value(
        [{'op': 'replace', 'path': '/score', 'value': -1}]
    )

    def apply_invalid():
        try:
            store.apply(patch)
        except ValueError:
            return True
        return False

    assert benchmark(apply_invalid)


def test_expression_inspect_compound(benchmark):
    width = _reference('Width', 'numeric_property')
    height = _reference('Height', 'numeric_property')
    expression = ((width * 2 + height) % 7 > 2) & (width < 1000)
    buffer = Buffer(width=81, height=24)
    result = benchmark(buffer.inspect, expression)
    assert result is True  # (81 * 2 + 24) % 7 == 4, which is above 2, and 81 < 1000


def test_dispatch_keys_to_many_hooks(benchmark):
    runtime = Runtime.offscreen(width=80, height=24)
    root = Buffer()
    runtime.mount(root, geometry='inherit')
    counter = itertools.count()

    def count_call(context) -> None:
        next(counter)

    for _ in range(100):
        root.add_hook(count_call, events=['key'])
    event = Event.key_press('a')

    def dispatch():
        runtime.dispatch(event)
        runtime.step()

    benchmark(dispatch)
    assert next(counter) >= 100
    runtime.close()


def test_dispatch_mouse_over_many_buffers(benchmark):
    runtime = Runtime.offscreen(width=200, height=60)
    root = Buffer()
    runtime.mount(root, geometry='inherit')
    hits = itertools.count()

    def count_hit(context) -> None:
        next(hits)

    for index in range(100):
        child = Buffer(width=10, height=3, x=(index % 20) * 10, y=(index // 20) * 3)
        child.is_focusable = True
        root.attach(child)
        child.add_hook(count_hit, events=['mouse'])
    events = itertools.cycle(
        Event.mouse_event(column=column, row=row, kind='press', button='left')
        for column, row in ((5, 1), (95, 7), (190, 13))
    )

    def dispatch():
        runtime.dispatch(next(events))
        runtime.step()

    benchmark(dispatch)
    runtime.close()
