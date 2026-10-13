"""
scripts.resource_logging

A pytest plugin that records the CPU time and memory every test or benchmark uses.

The test and benchmark suites import its hooks from their ``conftest.py``. Nothing is
measured unless ``--resource-log`` is passed, so ordinary runs pay no cost.

Wall time alone cannot tell a benchmark that is slow because it computes from one that is
slow because it waits, and Python's ``tracemalloc`` cannot see the memory the Rust
extensions allocate. Each record therefore holds:

* ``wall_seconds``: elapsed time of the test body.
* ``cpu_seconds``: CPU time of every thread of the process (user plus system). A ratio of
  ``cpu_seconds / wall_seconds`` above one means native threads ran in parallel; far below
  one means the test mostly waited.
* ``rss_start_bytes`` / ``rss_end_bytes`` / ``rss_growth_bytes``: resident memory of the
  whole process before and after the test, which includes Rust allocations.
* ``peak_rss_growth_bytes``: how far the process-wide peak resident memory rose.
* ``python_peak_bytes``: the peak Python-heap allocation, only with
  ``--resource-log-python-memory`` because tracing slows Python code down.

Examples:
    Print the table for a benchmark run and keep the data as JSON::

        pytest benchmarks --resource-log --resource-log-json resources.json
"""

from __future__ import annotations

import gc
import json
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

import pytest

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a development dependency
    psutil = None

try:
    import resource
except ImportError:  # pragma: no cover - the module does not exist on Windows
    resource = None

if TYPE_CHECKING:
    from collections.abc import Iterator

MEBIBYTE = 1024 * 1024
# A test that grows the process by more than this is flagged as a possible leak.
LEAK_THRESHOLD_BYTES = 8 * MEBIBYTE
# CPU time above this multiple of wall time means native threads ran in parallel.
PARALLEL_RATIO = 1.3
# CPU time below this fraction of wall time means the test mostly waited.
WAITING_RATIO = 0.5

RESOURCE_RECORDS = pytest.StashKey[list["ResourceRecord"]]()


@dataclass(frozen=True)
class ResourceRecord:
    """The CPU and memory one test used."""

    test: str
    wall_seconds: float
    cpu_seconds: float
    rss_start_bytes: int
    rss_end_bytes: int
    peak_rss_growth_bytes: int
    python_peak_bytes: int | None

    @property
    def rss_growth_bytes(self) -> int:
        """Resident memory gained (or lost, when negative) during the test."""
        return self.rss_end_bytes - self.rss_start_bytes

    @property
    def cpu_ratio(self) -> float:
        """CPU time divided by wall time."""
        return self.cpu_seconds / self.wall_seconds if self.wall_seconds else 0.0

    def get_flags(self) -> list[str]:
        """Return short notes about what the numbers suggest."""
        flags: list[str] = []
        if self.rss_growth_bytes > LEAK_THRESHOLD_BYTES:
            flags.append("memory growth")
        if self.cpu_ratio > PARALLEL_RATIO:
            flags.append("parallel")
        elif self.wall_seconds > 0.05 and self.cpu_ratio < WAITING_RATIO:
            flags.append("waiting")
        return flags


def get_resident_bytes() -> int:
    """Return the resident memory of this process, or ``0`` when it cannot be read."""
    if psutil is not None:
        return psutil.Process().memory_info().rss
    return get_peak_resident_bytes()


def get_peak_resident_bytes() -> int:
    """Return the highest resident memory this process has reached."""
    if resource is not None:
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS reports bytes, Linux reports kibibytes.
        return peak if sys.platform == "darwin" else peak * 1024
    if psutil is not None:  # pragma: no cover - Windows only
        return getattr(psutil.Process().memory_info(), "peak_wset", 0)
    return 0  # pragma: no cover


def get_cpu_seconds() -> float:
    """Return the CPU time (user plus system, all threads) this process has used."""
    return time.process_time()


def register(pluginmanager: pytest.PytestPluginManager) -> None:
    """
    Register this module as a plugin once, however many ``conftest.py`` files ask.

    Call it from a ``pytest_addoption`` hook in each suite's ``conftest.py``, so the
    options exist even when several suites run in one session.
    """
    if not pluginmanager.has_plugin("resource_logging"):
        pluginmanager.register(sys.modules[__name__], "resource_logging")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the resource logging options."""
    group = parser.getgroup("resource logging")
    group.addoption(
        "--resource-log",
        action="store_true",
        default=False,
        help="Record and print the CPU time and memory each test or benchmark uses.",
    )
    group.addoption(
        "--resource-log-json",
        metavar="PATH",
        default=None,
        help="Also write the resource records to this JSON file (implies --resource-log).",
    )
    group.addoption(
        "--resource-log-python-memory",
        action="store_true",
        default=False,
        help="Also trace the peak Python-heap allocation (slows Python code down).",
    )
    group.addoption(
        "--resource-log-top",
        type=int,
        default=0,
        metavar="COUNT",
        help="Only print the COUNT tests with the most CPU time (0 prints all).",
    )


def is_enabled(config: pytest.Config) -> bool:
    """Return whether resource logging was requested."""
    return bool(
        config.getoption("resource_log") or config.getoption("resource_log_json")
    )


def pytest_configure(config: pytest.Config) -> None:
    """Prepare the record list for the session."""
    config.stash[RESOURCE_RECORDS] = []


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Iterator[None]:
    """Measure the test body."""
    config = item.config
    if not is_enabled(config):
        return (yield)

    should_trace_python = bool(config.getoption("resource_log_python_memory"))
    # Collect first so garbage from earlier tests is not charged to this one.
    gc.collect()
    rss_start = get_resident_bytes()
    peak_start = get_peak_resident_bytes()
    if should_trace_python:
        tracemalloc.start()
    wall_start = time.perf_counter()
    cpu_start = get_cpu_seconds()
    try:
        return (yield)
    finally:
        cpu_seconds = get_cpu_seconds() - cpu_start
        wall_seconds = time.perf_counter() - wall_start
        python_peak = None
        if should_trace_python:
            python_peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
        config.stash[RESOURCE_RECORDS].append(
            ResourceRecord(
                test=item.nodeid,
                wall_seconds=wall_seconds,
                cpu_seconds=cpu_seconds,
                rss_start_bytes=rss_start,
                rss_end_bytes=get_resident_bytes(),
                peak_rss_growth_bytes=max(0, get_peak_resident_bytes() - peak_start),
                python_peak_bytes=python_peak,
            )
        )


def format_bytes(count: int) -> str:
    """Format a byte count, with a sign, in mebibytes."""
    return f"{count / MEBIBYTE:+.1f}"


def format_table(
    records: list[ResourceRecord], *, has_python_memory: bool
) -> list[str]:
    """Return the table lines for the terminal summary."""
    headers = ["test", "wall s", "cpu s", "cpu/wall", "rss MiB", "peak MiB", "notes"]
    if has_python_memory:
        headers.insert(-1, "py peak MiB")
    rows = []
    for record in records:
        row = [
            record.test,
            f"{record.wall_seconds:.3f}",
            f"{record.cpu_seconds:.3f}",
            f"{record.cpu_ratio:.2f}",
            format_bytes(record.rss_growth_bytes),
            format_bytes(record.peak_rss_growth_bytes),
            ", ".join(record.get_flags()),
        ]
        if has_python_memory:
            peak = record.python_peak_bytes or 0
            row.insert(-1, f"{peak / MEBIBYTE:.1f}")
        rows.append(row)
    widths = [
        max(len(headers[column]), *(len(row[column]) for row in rows))
        for column in range(len(headers))
    ]
    lines = []
    for row in [headers, *rows]:
        cells = [
            cell.ljust(widths[column])
            if column in (0, len(row) - 1)
            else cell.rjust(widths[column])
            for column, cell in enumerate(row)
        ]
        lines.append("  ".join(cells).rstrip())
    return lines


def pytest_terminal_summary(terminalreporter: Any, config: pytest.Config) -> None:
    """Print the resource table."""
    if not is_enabled(config):
        return
    records = config.stash[RESOURCE_RECORDS]
    if not records:
        return
    count = int(config.getoption("resource_log_top") or 0)
    shown = sorted(records, key=lambda record: record.cpu_seconds, reverse=True)
    if count > 0:
        shown = shown[:count]
    terminalreporter.section("resource usage (cpu and memory per test)")
    for line in format_table(
        shown, has_python_memory=bool(config.getoption("resource_log_python_memory"))
    ):
        terminalreporter.write_line(line)
    total_cpu = sum(record.cpu_seconds for record in records)
    total_wall = sum(record.wall_seconds for record in records)
    terminalreporter.write_line(
        f"{len(records)} tests: {total_cpu:.2f}s cpu in {total_wall:.2f}s wall; "
        f"peak resident memory {get_peak_resident_bytes() / MEBIBYTE:.1f} MiB"
    )
    if psutil is None:
        terminalreporter.write_line(
            "psutil is not installed: rss columns show the process peak, not the current size."
        )


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Write the JSON report."""
    config = session.config
    path = config.getoption("resource_log_json")
    if not path:
        return
    records = [
        {**asdict(record), "rss_growth_bytes": record.rss_growth_bytes}
        for record in config.stash[RESOURCE_RECORDS]
    ]
    with open(path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)
