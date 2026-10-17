"""
tests.test_pixel

The Pixel value: presets, characters, symbols, equality and how a pixel is drawn.
"""

from __future__ import annotations

import dataclasses
import typing

import pytest

import xnano
from xnano import Color, Pixel
from xnano.pixel import _PRESET_CHARACTERS, PixelPreset


def test_the_preset_literal_and_the_glyph_table_agree():
    assert set(typing.get_args(PixelPreset)) == set(_PRESET_CHARACTERS)
    assert len(_PRESET_CHARACTERS) == 28


@pytest.mark.parametrize(
    ('name', 'character'),
    [
        ('block', '█'),
        ('half_top', '▀'),
        ('half_bottom', '▄'),
        ('shade_light', '░'),
        ('shade_medium', '▒'),
        ('shade_dark', '▓'),
        ('braille', '⠀'),
        ('circle', '●'),
        ('circle_outline', '○'),
        ('dot', '•'),
        ('diamond', '◆'),
        ('star', '★'),
        ('line_horizontal', '─'),
        ('line_vertical', '│'),
        ('corner_top_left_rounded', '╭'),
        ('corner_top_right_rounded', '╮'),
        ('corner_bottom_left_rounded', '╰'),
        ('corner_bottom_right_rounded', '╯'),
        ('corner_top_left_square', '┌'),
        ('corner_top_right_square', '┐'),
        ('corner_bottom_left_square', '└'),
        ('corner_bottom_right_square', '┘'),
        ('arrow_up', '↑'),
        ('arrow_down', '↓'),
        ('arrow_left', '←'),
        ('arrow_right', '→'),
        ('check', '✓'),
        ('cross', '✗'),
    ],
)
def test_each_preset_draws_its_glyph(name, character):
    assert Pixel(name).character == character


def test_a_pixel_defaults_to_a_block():
    assert Pixel().character == '█'


def test_one_character_is_drawn_as_it_is():
    assert Pixel('x').character == 'x'
    assert Pixel('█', foreground='red').foreground == 'red'


def test_a_pixel_is_a_value():
    first = Pixel('star', foreground=Color('red'))
    second = Pixel('star', foreground=Color('red'))
    assert first == second and hash(first) == hash(second)
    assert first != Pixel('star', foreground=Color('blue'))
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.character = 'x'  # type: ignore[misc]


def test_the_core_cell_is_built_once():
    pixel = Pixel('dot', foreground='red', background='blue')
    assert pixel.cell() is pixel.cell()
    cell = pixel.cell()
    assert cell.symbol == '•'
    assert cell.foreground == Color('red')
    assert cell.background == Color('blue')


def test_a_symbol_registers_the_pixel_and_resolves_by_name():
    wall = Pixel('block', foreground='red', symbol='wall')
    assert wall.symbol == 'wall'
    found = Pixel('wall')
    assert found.character == '█'
    assert found.foreground == 'red'
    assert found.symbol == 'wall'
    recolored = Pixel('wall', foreground='blue')
    assert recolored.foreground == 'blue'


def test_an_unknown_name_lists_close_names_presets_and_symbols():
    Pixel('block', symbol='brickwall')
    with pytest.raises(ValueError) as caught:
        Pixel('corner_top_left')
    message = str(caught.value)
    assert 'Did you mean' in message
    assert 'corner_top_left_rounded' in message
    assert 'Presets:' in message
    with pytest.raises(ValueError, match='brickwall'):
        Pixel('brickwal')


def test_an_empty_or_wrong_first_argument_is_explained():
    with pytest.raises(ValueError, match='preset name, a symbol name or one character'):
        Pixel('')
    with pytest.raises(ValueError, match='preset name'):
        Pixel(5)  # type: ignore[arg-type]


def test_a_pixel_draws_into_a_region_and_reads_back():
    with xnano.new(width=5, height=2) as canvas:
        canvas.region[1, 0] = Pixel('diamond', foreground='red', background='blue')
        found = canvas.region[1, 0]
        assert found.character == '◆'
        assert found.foreground == Color('red')
        assert found.background == Color('blue')


def test_a_pixel_can_be_written_as_content():
    with xnano.new(width=5, height=2) as canvas:
        canvas.write(Pixel('star'), x=2)
        assert canvas.render().split('\n')[0] == '  ★'


def test_a_pixel_prints_as_its_character():
    from xnano import Pixel

    assert str(Pixel('star')) == '\u2605'
    assert str(Pixel('x', foreground='red')) == 'x'


def test_a_pixel_names_a_bad_color_and_takes_options_by_keyword():
    with pytest.raises(ValueError, match='foreground of a pixel must be a color'):
        Pixel('block', foreground='nocolor')
    with pytest.raises(TypeError, match='background of a pixel must be a color'):
        Pixel('block', background=5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Pixel('block', 'red')  # type: ignore[misc]


def test_a_pixel_cannot_be_a_control_character():
    for character in ('\x1b', '\n'):
        with pytest.raises(ValueError, match='control character'):
            Pixel(character)
