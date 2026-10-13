"""The native state store: schemas, patches, transactions, subscriptions and observations."""

from __future__ import annotations

import pytest

from xnano_core._xnano_core import (
    TerminalStateAccessError,
    TerminalStateConflictError,
    TerminalStatePatch,
    TerminalStateSchema,
    TerminalStateStore,
    TerminalStateValidationError,
)

SCHEMA = {
    'type': 'object',
    'properties': {
        'player': {
            'type': 'object',
            'properties': {
                'x': {'type': 'integer', 'minimum': 0},
                'name': {'type': 'string'},
            },
            'required': ['x'],
        },
        'items': {'type': 'array', 'items': {'type': 'integer'}},
    },
    'required': ['player'],
}


def make_store() -> TerminalStateStore:
    return TerminalStateStore(
        {'player': {'x': 1, 'name': 'a'}, 'items': [1, 2]},
        schema=TerminalStateSchema.compile(SCHEMA),
    )


def replace(path: str, value) -> TerminalStatePatch:
    return TerminalStatePatch.from_value(
        [{'op': 'replace', 'path': path, 'value': value}]
    )


def test_snapshots_read_detached_values():
    store = make_store()
    snapshot = store.snapshot()
    assert snapshot.to_value()['player'] == {'x': 1, 'name': 'a'}
    assert snapshot.at(('player', 'x')).to_value() == 1
    assert snapshot.exists(('items', 1)) and not snapshot.exists(('items', 5))
    assert store.snapshot(('items',)).to_value() == [1, 2]


def test_patches_publish_validated_commits_with_revisions():
    store = make_store()
    before = store.revision
    change = store.apply(replace('/player/x', 5))
    assert change is not None
    assert change.before_revision == before and change.revision == store.revision
    assert change.paths == (('player', 'x'),)
    assert change.before.at(('player', 'x')).to_value() == 1
    assert change.after.at(('player', 'x')).to_value() == 5
    assert store.revision_at(('player', 'x')) == store.revision


def test_no_op_commits_publish_nothing():
    store = make_store()
    revision = store.revision
    assert store.apply(replace('/player/x', 1)) is None
    assert store.revision == revision


def test_invalid_commits_publish_nothing_and_name_the_problem():
    store = make_store()
    revision = store.revision
    with pytest.raises(TerminalStateValidationError) as caught:
        store.apply(replace('/player/x', -3))
    assert caught.value.issues and caught.value.issues[0].path == ('player', 'x')
    assert store.revision == revision
    assert store.snapshot(('player', 'x')).to_value() == 1


def test_expected_revisions_detect_conflicts():
    store = make_store()
    stale = store.revision
    store.apply(replace('/player/x', 2))
    with pytest.raises(TerminalStateConflictError) as caught:
        store.apply(replace('/player/x', 3), expected_revision=stale)
    assert caught.value.expected_revision == stale
    assert caught.value.actual_revision == store.revision


def test_transactions_are_atomic():
    store = make_store()
    with store.transaction() as transaction:
        transaction.set(('player', 'x'), 7)
        transaction.set(('items', 0), 9)
    assert store.snapshot().to_value()['items'] == [9, 2]
    revision = store.revision
    with pytest.raises(RuntimeError, match='boom'), store.transaction() as transaction:
        transaction.set(('player', 'x'), 8)
        raise RuntimeError('boom')
    assert store.revision == revision
    assert store.snapshot(('player', 'x')).to_value() == 7


def test_patches_round_trip_through_json():
    patch = TerminalStatePatch.from_value(
        [
            {'op': 'replace', 'path': '/player/x', 'value': 4},
            {'op': 'add', 'path': '/items/-', 'value': 3},
        ]
    )
    assert len(patch) == 2
    assert TerminalStatePatch.from_json(patch.to_json()).to_value() == patch.to_value()
    store = make_store()
    store.apply(patch)
    assert store.snapshot().to_value()['items'] == [1, 2, 3]


def test_subscriptions_queue_until_drained():
    store = make_store()
    seen = []
    subscription = store.subscribe([('player',)], seen.append)
    store.apply(replace('/player/x', 2))
    assert seen == []
    assert store.drain_notifications() == 1
    assert [change.paths for change in seen] == [(('player', 'x'),)]
    subscription.cancel()
    assert subscription.is_cancelled
    store.apply(replace('/player/x', 3))
    store.drain_notifications()
    assert len(seen) == 1


def test_wakers_signal_without_running_callbacks():
    store = make_store()
    wakes = []
    store.attach_waker(lambda: wakes.append(1))
    store.apply(replace('/player/x', 2))
    assert wakes


def test_callback_exceptions_reach_the_drainer():
    store = make_store()

    def fail(change):
        raise ValueError('callback failed')

    store.subscribe([()], fail)
    store.apply(replace('/player/x', 2))
    with pytest.raises(ValueError, match='callback failed'):
        store.drain_notifications()


def test_observations_enforce_grants_and_dependency_versions():
    store = make_store()
    observation = store.observe(read=[('player',)], write=[('player', 'x')])
    assert observation.read == (('player',),) and observation.write == (('player', 'x'),)
    store.apply_observed(replace('/player/x', 5), observation)
    with pytest.raises(TerminalStateAccessError):
        store.apply_observed(replace('/items/0', 5), observation)
    store.apply(replace('/player/name', 'b'))
    with pytest.raises(TerminalStateConflictError):
        store.apply_observed(replace('/player/x', 6), observation)


def test_schema_compilation_is_explicit():
    schema = TerminalStateSchema.compile(SCHEMA)
    schema.validate({'player': {'x': 0}})
    with pytest.raises(TerminalStateValidationError):
        schema.validate({'player': {}})
    assert schema.at(('player', 'x')).to_json_schema()['type'] == 'integer'
    with pytest.raises(ValueError):
        TerminalStateSchema.compile({'type': 'object', 'unsupportedKeyword': 1})


def test_values_must_be_finite_json():
    with pytest.raises((TypeError, ValueError)):
        TerminalStateStore({'x': float('nan')}, schema=TerminalStateSchema.compile({}))
