"""tests.test_types"""

from __future__ import annotations

import typing

from xnano.types import Sizing, SizingKeyword, SizingPercentage


def test_sizing_literal_members_all_parse() -> None:
    """Every declared sizing literal resolves through ``Sizing.parse`` so the
    autocomplete surface can never drift from the runtime parser (#102).
    """
    for token in typing.get_args(SizingKeyword):
        assert Sizing.parse(token) is not None, token
    for token in typing.get_args(SizingPercentage):
        assert Sizing.parse(token) is not None, token


def test_sizing_percentage_covers_0_to_100() -> None:
    assert set(typing.get_args(SizingPercentage)) == {
        f"{index}%" for index in range(101)
    }
