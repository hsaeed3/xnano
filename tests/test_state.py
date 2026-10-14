"""
tests.test_state

Typed terminal state and references.
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
    with main.open(offscreen=True, width=8, height=2, state=Settings()) as terminal:

        @terminal.hook
        def remember(context: Context) -> None:
            if type(context.event).__name__ == 'TerminalStateChange':
                heard.append(context.state.volume)

        terminal._state_proxy.volume = 55
        terminal.loop.step()
        assert terminal._state_proxy.volume == 55
        assert heard == [55]
        with pytest.raises(TerminalError, match='volume'):
            terminal._state_proxy.volume = 'loud'


def test_a_reference_can_be_an_axis():
    with main.open(
        offscreen=True, width=20, height=2, state=Settings(volume=4)
    ) as terminal:
        thumb = terminal.write('#', x=terminal.ref(lambda state: state.volume))
        terminal.loop.advance(0)
        assert thumb.x == 4
        terminal._state_proxy.volume = 7
        terminal.loop.advance(0)
        assert thumb.x == 7


def test_an_unsupported_field_is_named():
    @dataclass
    class Broken:
        payload: bytes = b''

    with pytest.raises(TerminalError, match='payload'):
        main.open(offscreen=True, width=4, height=1, state=Broken())


def test_open_without_state_has_no_reference():
    with main.open(offscreen=True, width=4, height=1) as terminal:
        with pytest.raises(TerminalError, match='no state'):
            terminal.ref(lambda state: state.volume)


def test_an_expression_still_places_a_buffer():
    with main.open(offscreen=True, width=10, height=1) as terminal:
        placed = terminal.write('#', x=ParentWidth // 2)
        terminal.loop.advance(0)
        assert placed.x == 5
