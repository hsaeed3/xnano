"""Tests for the unified ``Sizing`` vocabulary."""

from __future__ import annotations

import pytest

from xnano.beta.sizing import Sizing


# ---------------------------------------------------------------------------
# constructors
# ---------------------------------------------------------------------------


def test_cells() -> None:
    sizing = Sizing.cells(10)
    assert sizing.kind == "cells"
    assert sizing.value == 10


def test_percent_from_percentage() -> None:
    assert Sizing.percent(50).value == 50


def test_percent_from_fraction() -> None:
    # Values in 0..=1 are treated as fractions.
    assert Sizing.percent(0.25).value == 25


def test_percent_clamps_to_100() -> None:
    assert Sizing.percent(150).value == 100


def test_ratio() -> None:
    sizing = Sizing.ratio(1, 3)
    assert sizing.kind == "ratio"
    assert sizing.value == 1
    assert sizing.denominator == 3


def test_fraction() -> None:
    sizing = Sizing.fraction(2)
    assert sizing.kind == "fraction"
    assert sizing.value == 2
    assert sizing.is_fill


def test_fit_with_bounds() -> None:
    sizing = Sizing.fit(minimum=2, maximum=8)
    assert sizing.is_fit
    assert sizing.minimum == 2
    assert sizing.maximum == 8


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


def test_parse_none() -> None:
    assert Sizing.parse(None) is None


def test_parse_sizing_passthrough() -> None:
    sizing = Sizing.cells(3)
    assert Sizing.parse(sizing) is sizing


def test_parse_int_is_cells() -> None:
    assert Sizing.parse(12) == Sizing.cells(12)


def test_parse_float_fraction_is_percent() -> None:
    assert Sizing.parse(0.5) == Sizing.percent(50)


def test_parse_percent_string() -> None:
    assert Sizing.parse("75%") == Sizing.percent(75)


def test_parse_fr_string() -> None:
    assert Sizing.parse("3fr") == Sizing.fraction(3)


def test_parse_bare_fr_is_one() -> None:
    assert Sizing.parse("fr") == Sizing.fraction(1)


def test_parse_fit_aliases() -> None:
    for token in ("fit", "auto", "content"):
        parsed = Sizing.parse(token)
        assert parsed is not None and parsed.is_fit


def test_parse_fill_aliases() -> None:
    assert Sizing.parse("fill") == Sizing.fraction(1)
    assert Sizing.parse("grow") == Sizing.fraction(1)


def test_parse_tailwind_flex_class() -> None:
    assert Sizing.parse("flex-1") == Sizing.fraction(1)
    assert Sizing.parse("grow-0") == Sizing.fraction(0)


def test_parse_ratio_string() -> None:
    assert Sizing.parse("2/5") == Sizing.ratio(2, 5)


def test_parse_decimal_string_is_cells() -> None:
    assert Sizing.parse("8") == Sizing.cells(8)


def test_parse_invalid_string_raises() -> None:
    with pytest.raises(ValueError):
        Sizing.parse("wide")


def test_parse_bool_raises() -> None:
    with pytest.raises(TypeError):
        Sizing.parse(True)


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------


def test_resolve_cells() -> None:
    assert Sizing.cells(10).resolve(80) == 10


def test_resolve_percent() -> None:
    assert Sizing.percent(50).resolve(80) == 40


def test_resolve_ratio() -> None:
    assert Sizing.ratio(1, 4).resolve(80) == 20


def test_resolve_fit_uses_content() -> None:
    assert Sizing.fit().resolve(80, content=12) == 12


def test_resolve_fraction_fills_available() -> None:
    assert Sizing.fraction(1).resolve(80) == 80


def test_resolve_applies_minimum() -> None:
    assert Sizing.fit(minimum=5).resolve(80, content=2) == 5


def test_resolve_applies_maximum() -> None:
    assert Sizing.fit(maximum=6).resolve(80, content=20) == 6
