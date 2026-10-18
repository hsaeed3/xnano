"""
benchmarks.test_state

Benchmarks for dynamic state: a hook that pushes three values, a typed field read, and a commit
on a canvas with a thousand hooks that follow state.

Each call pushes 100 key events and delivers them in one step, so the cost of one hook call is the
time of the call divided by 100. Three pushes are measured on each namespace (the root of the
canvas, a placement and a hook) because the state store's cost grows with the depth of a path.

The budgets are asserted only when ``XNANO_CHECK_BUDGETS=1`` is set on an optimized build
outside CodSpeed (``make benchmark-xnano`` does it): a debug build is several times slower and
says nothing about the code's speed.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable

import pytest
from benchmark_budgets import assert_within_budget, budgets_are_checked

import xnano
from xnano._schema._generics import DepsT, StateT
from xnano.canvas import Canvas
from xnano.context import Context
from xnano_core import Event

EVENTS = 100
ROUNDS = 200

THREE_PUSHES_BUDGET_MICROSECONDS = 15.0
"""A hook that pushes three values costs at most this much more than a hook that does nothing."""

WARM_READ_BUDGET_MICROSECONDS = 1.0
"""A typed field read, after the hook's first read, costs at most this much."""

FIRST_READ_BUDGET_MICROSECONDS = 1.3
"""The first typed field read of a hook call costs at most this much more than no read."""

READERS = 1000
READERS_BUDGET_RATIO = 2.0
"""A commit with a thousand followers costs at most this many times a commit with none."""


@dataclasses.dataclass
class Settings:
    volume: int = 40
    brightness: int = 7
    contrast: int = 3


def deliver(canvas: Canvas[DepsT, StateT], event: Event) -> None:
    for _ in range(EVENTS):
        canvas.push(event)
    canvas.deliver_events()


def minimum_microseconds(function: Callable[[], None], *, rounds: int = ROUNDS) -> float:
    """The fastest of several calls, in microseconds per event."""
    for _ in range(20):
        function()
    results = []
    for _ in range(rounds):
        start = time.perf_counter()
        function()
        results.append((time.perf_counter() - start) / EVENTS * 1e6)
    return min(results)


def no_op(context: Context) -> None:
    return None


def make_push_three(namespace: str) -> tuple[Callable[[Context], None], list[int]]:
    counter = [0]

    def push_root(context: Context) -> None:
        counter[0] += 1
        state = context.root.state
        state.push('a', counter[0])
        state.push('b', counter[0])
        state.push('c', counter[0])

    def push_buffer(context: Context) -> None:
        counter[0] += 1
        state = context.buffer.state
        state.push('a', counter[0])
        state.push('b', counter[0])
        state.push('c', counter[0])

    def push_plugin(context: Context) -> None:
        counter[0] += 1
        state = context.plugin.state
        state.push('a', counter[0])
        state.push('b', counter[0])
        state.push('c', counter[0])

    functions = {'root': push_root, 'buffer': push_buffer, 'plugin': push_plugin}
    return functions[namespace], counter


def _read_state(canvas: Canvas, namespace: str) -> dict[str, object]:
    if namespace == 'root':
        return {key: canvas.state.get(key) for key in 'abc'}
    placement = canvas._placements[0]
    if namespace == 'buffer':
        return {key: placement.state.get(key) for key in 'abc'}
    handle = placement._registrations[0]
    return {key: handle._state_namespace().get(key) for key in 'abc'}


@pytest.mark.parametrize('namespace', ['root', 'buffer', 'plugin'])
def test_three_pushes(benchmark, namespace: str) -> None:
    event = Event.key_press('a')
    push_three, counter = make_push_three(namespace)
    with xnano.new(width=80, height=24) as canvas:
        label = canvas.write('x')
        label.hook(push_three, on='key')
        benchmark.pedantic(
            lambda: deliver(canvas, event), rounds=ROUNDS, warmup_rounds=20, iterations=1
        )
        last = counter[0]
        assert _read_state(canvas, namespace) == {'a': last, 'b': last, 'c': last}
        measured = (
            minimum_microseconds(lambda: deliver(canvas, event))
            if budgets_are_checked()
            else 0.0
        )
    if budgets_are_checked():
        with xnano.new(width=80, height=24) as baseline:
            label = baseline.write('x')
            label.hook(no_op, on='key')
            empty = minimum_microseconds(lambda: deliver(baseline, event))
        assert_within_budget(
            measured - empty,
            THREE_PUSHES_BUDGET_MICROSECONDS,
            f'three pushes ({namespace})',
        )


def test_typed_read(benchmark) -> None:
    event = Event.key_press('a')
    heard: list[int] = []

    def read_none(context: Context[None, Settings]) -> None:
        return None

    def read_one(context: Context[None, Settings]) -> None:
        heard.append(context.root.state.volume)

    def read_three(context: Context[None, Settings]) -> None:
        state = context.root.state
        heard.append(state.volume + state.brightness + state.contrast)

    results = {}
    for name, function in (('none', read_none), ('one', read_one), ('three', read_three)):
        with xnano.new(width=80, height=24, state=Settings()) as canvas:
            canvas.hook(function, on='key')
            if name == 'one':
                benchmark.pedantic(
                    lambda: deliver(canvas, event),
                    rounds=ROUNDS,
                    warmup_rounds=20,
                    iterations=1,
                )
                assert heard and heard[-1] == 40
            if budgets_are_checked():
                results[name] = minimum_microseconds(lambda: deliver(canvas, event))
    if budgets_are_checked():
        first = results['one'] - results['none']
        warm = (results['three'] - results['one']) / 2
        assert_within_budget(
            first, FIRST_READ_BUDGET_MICROSECONDS, 'the first typed read of a hook call'
        )
        assert_within_budget(
            warm, WARM_READ_BUDGET_MICROSECONDS, 'a later typed read of a hook call'
        )


def test_many_readers(benchmark) -> None:
    counter = [0]

    def commit(canvas: Canvas) -> None:
        for _ in range(EVENTS):
            counter[0] += 1
            canvas.state.push('unrelated', counter[0])
            canvas.deliver_events()

    def build(readers: int) -> Canvas:
        canvas = xnano.new(width=80, height=24)
        for index in range(readers):
            path = f'reader_{index}'

            def follow(context: Context, path: str = path) -> None:
                context.root.state.get(path)

            canvas.hook(follow, on='state')
        canvas.state.push('warmup', 1)
        canvas.deliver_events()
        return canvas

    alone = build(0)
    crowded = build(READERS)
    try:
        assert crowded._state_followers is not None
        assert not crowded._state_followers._everything
        benchmark.pedantic(
            lambda: commit(crowded), rounds=30, warmup_rounds=3, iterations=1
        )
        if budgets_are_checked():
            zero = minimum_microseconds(lambda: commit(alone), rounds=30)
            many = minimum_microseconds(lambda: commit(crowded), rounds=30)
            assert_within_budget(
                many / zero,
                READERS_BUDGET_RATIO,
                'a commit with a thousand followers (ratio)',
                unit='times',
            )
    finally:
        alone.close()
        crowded.close()
