"""
tests.test_symbols

Names for values: registering, looking up, replacing and removing symbols.
"""

from __future__ import annotations

import pytest

import xnano
from xnano import symbols
from xnano._media import Audio


class TestRegistry:
    def test_a_registered_value_is_found_by_name(self):
        color = xnano.Color('#336699')
        symbols.register('accent', color)
        assert symbols.lookup('accent') is color
        assert symbols.lookup('accent', kind=xnano.Color) is color
        assert 'accent' in symbols.names()
        assert symbols.names(kind=xnano.Color) == ('accent',)
        assert symbols.names(kind=Audio) == ()

    def test_registering_again_replaces_a_value_of_the_same_kind(self):
        symbols.register('accent', xnano.Color('red'))
        symbols.register('accent', xnano.Color('blue'))
        assert symbols.lookup('accent') == xnano.Color('blue')

    def test_another_kind_under_a_taken_name_is_refused(self):
        symbols.register('kick', xnano.Color('red'))
        with pytest.raises(ValueError, match='already a Color') as caught:
            symbols.register('kick', 'not a color')
        assert "xnano.symbols.remove('kick')" in str(caught.value)
        assert symbols.lookup('kick') == xnano.Color('red')

    def test_removing_forgets_a_name_and_twice_is_harmless(self):
        symbols.register('accent', xnano.Color('red'))
        symbols.remove('accent')
        symbols.remove('accent')
        assert 'accent' not in symbols.names()

    def test_the_registry_is_reachable_from_the_package(self):
        assert xnano.symbols is symbols
        assert 'symbols' not in xnano.__all__


class TestNames:
    @pytest.mark.parametrize(
        ('name', 'text'),
        [
            ('w', 'too short'),
            ('my wall', 'has a space'),
            ('block', 'built-in pixel preset'),
            ('corner_top_left_rounded', 'built-in pixel preset'),
            ('C4', 'reads as a note'),
            ('f#3', 'reads as a note'),
            ('rest', 'reads as a note'),
            ('60', 'reads as a note, a rest or a MIDI number'),
        ],
    )
    def test_names_that_would_mean_something_else_are_refused(self, name, text):
        with pytest.raises(ValueError, match=text):
            symbols.register(name, xnano.Color('red'))

    def test_a_name_is_a_string(self):
        with pytest.raises(TypeError, match='is a string'):
            symbols.register(3, xnano.Color('red'))  # type: ignore[arg-type]


class TestUnknownNames:
    def test_an_unknown_name_lists_the_close_and_the_known_ones(self):
        symbols.register('wall', xnano.Color('gray'))
        symbols.register('water', xnano.Color('blue'))
        with pytest.raises(ValueError, match="Did you mean 'wall'") as caught:
            symbols.lookup('wal')
        message = str(caught.value)
        assert "Known symbols: 'wall', 'water'" in message
        assert "symbol='wal'" in message

    def test_a_name_of_another_kind_says_which_kind_it_is(self):
        symbols.register('wall', xnano.Color('gray'))
        with pytest.raises(ValueError, match='is a Color symbol, not an Audio symbol'):
            symbols.lookup('wall', kind=Audio)

    def test_an_empty_registry_says_so(self):
        with pytest.raises(ValueError, match='none yet'):
            symbols.lookup('anything', kind=Audio)

    def test_each_test_starts_with_the_registry_it_had(self):
        assert 'wall' not in symbols.names()
