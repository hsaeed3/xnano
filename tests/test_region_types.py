"""
tests.test_region_types

The type of a region follows its medium: ``Region[int]`` on the screen, whose ``x`` and ``width``
are whole numbers, and ``Region[float]`` on the timeline, whose are beats and can be fractions.

``make typecheck`` checks this file with the argument, index and call checks that the other tests
switch off, so a change that makes ``range(canvas.screen.region.width)`` stop type-checking fails there.
Every test also runs, so the types and the values cannot drift apart.
"""

# pyright: reportArgumentType=true, reportIndexIssue=true, reportCallIssue=true
# pyright: reportAttributeAccessIssue=true, reportUnnecessaryTypeIgnoreComment=true

from __future__ import annotations

import pytest
from typing_extensions import assert_type

import xnano
from xnano.layout import Region


def test_a_region_on_the_screen_has_whole_number_coordinates():
    with xnano.new(width=8, height=3) as canvas:
        region = canvas.screen.region
        assert_type(region, Region[int])
        assert_type(region.x, int)
        assert_type(region.y, int)
        assert_type(region.width, int)
        assert_type(region.height, int)

        for column in range(canvas.screen.region.width):
            region[column, 1] = 'o'
        region[region.width - 1, 0] = 'x'
        middle: int = region.x + region.width // 2

        assert canvas.screen.render().splitlines()[1] == 'oooooooo'
        assert region[7, 0].character == 'x'
        assert middle == 4


def test_every_view_and_maker_of_a_region_on_the_screen_keeps_it_whole():
    with xnano.new(width=8, height=3) as canvas:
        label = canvas.screen.write('ab')
        region = canvas.screen.region
        assert_type(label.region, Region[int])
        assert_type(region.cells, Region[int])
        assert_type(region.half_blocks, Region[int])
        assert_type(region.braille, Region[int])
        assert_type(region[0:2, 0:1], Region[int])
        assert_type(region.copy(), Region[int])
        assert len(range(region.braille.width)) == 16
    assert_type(xnano.region('a'), Region[int])
    assert_type(xnano.box(3, 3), Region[int])
    assert len(range(xnano.box(3, 3).width)) == 3


def test_a_region_on_the_timeline_has_fractional_coordinates():
    region = xnano.Note('C4', beats=1.5).region
    assert_type(region, Region[float])
    assert_type(region.x, float)
    assert_type(region.width, float)
    assert_type(region.y, int)
    assert_type(region.height, int)
    assert_type(region.beats, Region[float])
    assert_type(region.sixteenths, Region[float])
    assert_type(region.milliseconds, Region[float])

    assert region.width == 1.5
    with pytest.raises(TypeError):
        range(region.width)  # pyright: ignore[reportArgumentType]


def test_a_region_without_a_type_parameter_accepts_either_medium():
    def far_edge(region: Region) -> float:
        return region.x + region.width

    with xnano.new(width=8, height=3) as canvas:
        assert far_edge(canvas.screen.region) == 8
    assert far_edge(xnano.Note('C4', beats=2).region) == 2.0


def test_the_region_of_a_context_is_either_medium_and_its_buffer_is_on_the_screen():
    def read(context: xnano.Context) -> None:
        assert_type(context.region, Region[float])
        assert_type(context.target.region, Region[int])
        assert_type(context.size.width, int)

    assert callable(read)
