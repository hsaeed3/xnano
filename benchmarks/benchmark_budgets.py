"""
benchmarks.benchmark_budgets

Time budgets for the benchmarks in this directory. A budget is a wall-clock limit, so it is
checked only when ``XNANO_CHECK_BUDGETS=1`` is set (``make benchmark-xnano`` sets it), the
extension is an optimized build, and the run is not measured by CodSpeed. Every benchmark still
runs and asserts on its result in any other case.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import pytest

import xnano_core


def budgets_are_checked() -> bool:
    """Whether this run compares measured times with their budgets."""
    return (
        os.environ.get('XNANO_CHECK_BUDGETS') == '1'
        and not os.environ.get('CODSPEED_ENV')
        and xnano_core.is_optimized_build
    )


def check_budget(
    measure: Callable[[], float], budget: float, what: str, *, unit: str = 'us'
) -> None:
    """Fail when ``measure()`` is above ``budget``; do nothing when budgets are not checked."""
    if budgets_are_checked():
        assert_within_budget(measure(), budget, what, unit=unit)


def assert_within_budget(
    measured: float, budget: float, what: str, *, unit: str = 'us'
) -> None:
    """Fail when ``measured`` is above ``budget``."""
    assert measured <= budget, (
        f'{what} took {measured:.2f} {unit}; the budget is {budget:.2f} {unit}'
    )


def skip_unless_budgets_are_checked() -> None:
    """Skip a test whose only purpose is a budget."""
    if not budgets_are_checked():
        pytest.skip(
            'Time budgets are checked only on an optimized build with XNANO_CHECK_BUDGETS=1 '
            'outside CodSpeed. Run make benchmark-xnano to check them.'
        )
