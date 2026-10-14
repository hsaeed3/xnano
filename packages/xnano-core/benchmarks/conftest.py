"""benchmarks.conftest"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / 'scripts'))

import resource_logging


def pytest_addoption(parser, pluginmanager):
    """Make the ``--resource-log`` options available."""
    resource_logging.register(pluginmanager)
