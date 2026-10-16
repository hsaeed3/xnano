"""
tests.test_state

Typed canvas state and references.
"""

from dataclasses import dataclass

import pytest

import xnano as main
from xnano.context import Context
from xnano.errors import TerminalError
from xnano_core import ParentWidth


@dataclass
class Settings:
    volume: int = 40


@dataclass
class Nested:
    player: Settings


def test_a_state_write_is_validated_and_wakes_a_hook():
    heard: list[int] = []
    with main.new(width=8, height=2, state=Settings()) as canvas:

        @canvas.hook(on='state')
        def remember(context: Context) -> None:
            heard.append(context.root.state.volume)

        canvas.state.volume = 55
        canvas.deliver_events()
        assert canvas.state.volume == 55
        assert heard == [55]
        with pytest.raises(TerminalError, match='volume'):
            canvas.state.volume = 'loud'


def test_a_reference_can_be_an_axis():
    with main.new(width=20, height=2, state=Settings(volume=4)) as canvas:
        thumb = canvas.write('#', x=canvas.ref(lambda state: state.volume))
        canvas.deliver_events()
        assert thumb.x == 4
        canvas.state.volume = 7
        canvas.deliver_events()
        assert thumb.x == 7


def test_an_unsupported_field_is_named():
    @dataclass
    class Broken:
        payload: bytes = b''

    with pytest.raises(TerminalError, match='payload'):
        main.new(width=4, height=1, state=Broken())


def test_open_without_state_has_no_reference():
    with main.new(width=4, height=1) as canvas:
        with pytest.raises(TerminalError, match='no state'):
            canvas.ref(lambda state: state.volume)


def test_an_expression_still_places_a_buffer():
    with main.new(width=10, height=1) as canvas:
        placed = canvas.write('#', x=ParentWidth // 2)
        canvas.deliver_events()
        assert placed.x == 5
