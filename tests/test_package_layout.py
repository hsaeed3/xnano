"""
tests.test_package_layout

Where the modules of the ``xnano`` package live.
"""

from __future__ import annotations

import pathlib

import xnano

PACKAGE = pathlib.Path(xnano.__file__).parent


def test_no_private_script_sits_at_the_top_of_the_package():
    private_scripts = sorted(
        path.name
        for path in PACKAGE.glob('_*.py')
        if not (path.stem.startswith('__') and path.stem.endswith('__'))
    )
    assert private_scripts == []
