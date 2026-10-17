"""
benchmarks.test_hooks

Benchmarks for the cost of hearing an event: a key that reaches one hook, a key among ten hooks,
and a key that no hook wants.

Each call pushes 100 key events and delivers them in one step, so the cost of an event is the
time of the call divided by 100.

Measured on an optimized build (Apple M-series, Python 3.11): 7.57 us per event with one
registered hook and 42.07 us with ten; a natively filtered hook costs 0.16 us per event.

The budgets are asserted only when ``XNANO_CHECK_BUDGETS=1`` is set on an optimized build
outside CodSpeed (``make benchmark-xnano`` does it): a debug build is several times slower and
says nothing about the code's speed.
"""

from __future__ import annotations

import time

from benchmark_budgets import check_budget

import xnano
from xnano.context import Context
from xnano_core import Event

EVENTS = 100

ONE_HOOK_BUDGET_MICROSECONDS = 10.0
"""One matching no-op hook costs at most this much per event."""

TEN_HOOKS_BUDGET_MICROSECONDS = 60.0
"""Ten registered hooks of which one matches cost at most this much per event."""

FILTERED_BUDGET_MICROSECONDS = 1.0
"""An event that no hook wants never reaches Python, so it costs about the runtime's routing."""


def minimum_microseconds(function, *, rounds: int = 30) -> float:
    """The fastest of several calls, in microseconds per event."""
    results = []
    for _ in range(rounds):
        start = time.perf_counter()
        function()
        results.append((time.perf_counter() - start) / EVENTS * 1e6)
    return min(results)


def deliver(canvas, event: Event) -> None:
    for _ in range(EVENTS):
        canvas.push(event)
    canvas.deliver_events()


def test_one_matching_hook(benchmark):
    heard: list[int] = []

    def hook(context: Context) -> None:
        heard.append(1)

    with xnano.new(width=80, height=24) as canvas:
        canvas.hook(hook, on='key', keys='a')
        event = Event.key_press('a')
        deliver(canvas, event)
        assert len(heard) == EVENTS
        benchmark.pedantic(lambda: deliver(canvas, event), rounds=30, iterations=1)
        assert len(heard) > EVENTS
        assert len(heard) % EVENTS == 0
        check_budget(
            lambda: minimum_microseconds(lambda: deliver(canvas, event)),
            ONE_HOOK_BUDGET_MICROSECONDS,
            'one matching hook',
        )


def test_ten_hooks_of_which_one_matches(benchmark):
    heard: list[int] = []

    def hook(context: Context) -> None:
        heard.append(1)

    with xnano.new(width=80, height=24) as canvas:
        for key in 'bcdefghij':
            canvas.hook(hook, on='key', keys=key)
        canvas.hook(hook, on='key', keys='a')
        event = Event.key_press('a')
        deliver(canvas, event)
        assert len(heard) == EVENTS
        benchmark.pedantic(lambda: deliver(canvas, event), rounds=30, iterations=1)
        assert len(heard) > EVENTS
        assert len(heard) % EVENTS == 0
        check_budget(
            lambda: minimum_microseconds(lambda: deliver(canvas, event)),
            TEN_HOOKS_BUDGET_MICROSECONDS,
            'ten hooks, one matching',
        )


def test_a_key_that_no_hook_wants(benchmark):
    built: list[int] = []

    def hook(context: Context) -> None:
        built.append(1)

    with xnano.new(width=80, height=24) as canvas:
        canvas.hook(hook, on='key', keys='a')
        event = Event.key_press('z')
        benchmark.pedantic(lambda: deliver(canvas, event), rounds=30, iterations=1)
        assert built == []
        check_budget(
            lambda: minimum_microseconds(lambda: deliver(canvas, event)),
            FILTERED_BUDGET_MICROSECONDS,
            'a filtered key',
        )
