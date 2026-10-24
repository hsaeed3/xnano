"""
tests.test_ai_art_finish

The pixel-art finishing of a flat drawing: the outline, the shading and the stray pixels.
"""

from __future__ import annotations

import pytest

pytest.importorskip('pydantic_ai')

from xnano.ai.models._art_finish import (  # noqa: E402
    finish,
    highlight_of,
    outline_of,
    shadow_of,
)

GOLD = {'y': ('base', '#ffcd75')}


def roles(finished, letters: str) -> set[str]:
    return {finished.palette[letter][0] for letter in letters if letter != '.'}


class TestOutline:
    def test_the_outline_runs_inside_the_silhouette(self):
        rows = ['........', *['.yyyyyy.'] * 8, '........']
        finished = finish(rows, GOLD)
        assert finished.rows[0] == '........'
        assert finished.rows[1] == '.oooooo.'
        assert finished.rows[2][1] == 'o' and finished.rows[2][6] == 'o'
        assert finished.palette['o'][0] == 'outline'
        assert finished.palette['o'][1] != '#000000'
        assert 'drew the outline' in ' '.join(finished.notes)

    def test_an_edge_on_the_canvas_edge_is_not_outlined(self):
        rows = ['yyyy', 'yyyy', 'yyyy', 'yyyy', 'yyyy', 'yyyy', 'yyyy', 'yyyy']
        finished = finish(rows, GOLD)
        assert 'o' not in finished.palette

    def test_a_diagonal_step_keeps_a_single_pixel_corner(self):
        rows = [
            '..........',
            '.yyyyy....',
            '.yyyyyy...',
            '.yyyyyyy..',
            '.yyyyyyyy.',
            '.yyyyyyyy.',
            '.yyyyyyyy.',
            '.yyyyyyyy.',
            '.yyyyyyyy.',
            '..........',
        ]
        finished = finish(rows, GOLD)
        # Along the slope, the ring steps one pixel at a time instead of doubling up.
        outline = [
            (x, y)
            for y, row in enumerate(finished.rows)
            for x, letter in enumerate(row)
            if letter == 'o'
        ]
        doubled = [
            (x, y)
            for x, y in outline
            if (x + 1, y) in outline
            and (x, y + 1) in outline
            and (x + 1, y + 1) in outline
        ]
        assert doubled == []
        assert finished.rows[4][8] == 'o' and finished.rows[1][5] == 'o'

    def test_a_drawing_with_its_own_outline_keeps_it(self):
        rows = ['oooo', 'oyyo', 'oyyo', 'oooo', 'oyyo', 'oyyo', 'oyyo', 'oooo']
        finished = finish(rows, {**GOLD, 'o': ('outline', '#101010')})
        assert finished.rows == tuple(rows)
        assert finished.palette['o'] == ('outline', '#101010')


class TestShading:
    def test_shadow_falls_lower_right_and_highlight_upper_left(self):
        rows = ['..........', *['.yyyyyyyy.'] * 8, '..........']
        finished = finish(rows, GOLD)
        inner = [row[2:8] for row in finished.rows[2:8]]
        letters = {letter for row in inner for letter in row}
        assert roles(finished, ''.join(letters)) == {'base', 'highlight', 'shadow'}
        highlight = next(
            letter for letter in letters if finished.palette[letter][0] == 'highlight'
        )
        shadow = next(
            letter for letter in letters if finished.palette[letter][0] == 'shadow'
        )
        assert inner[0][0] == highlight and inner[5][5] == shadow
        assert inner[0][5] == 'y' and inner[5][0] == 'y'

    def test_details_are_never_changed(self):
        rows = [
            '..........',
            *['.yyyyyyyy.'] * 3,
            '.yyyeeyyy.',
            *['.yyyyyyyy.'] * 4,
            '..........',
        ]
        finished = finish(rows, {**GOLD, 'e': ('detail', '#1a1c2c')})
        assert finished.rows[4][4:6] == 'ee'
        assert finished.palette['e'] == ('detail', '#1a1c2c')

    def test_a_drawing_with_its_own_shading_keeps_it(self):
        rows = ['..........', *['.yyyyyysy.'] * 8, '..........']
        finished = finish(rows, {**GOLD, 's': ('shadow', '#b86f50')})
        assert finished.rows[2][7] == 's'
        assert {role for role, _ in finished.palette.values()} == {
            'base',
            'shadow',
            'outline',
        }

    def test_small_art_is_left_alone(self):
        rows = ['yyyy', 'yyyy', 'yyyy', 'yyyy']
        finished = finish(rows, GOLD)
        assert finished.rows == tuple(rows)
        assert finished.notes == ()


class TestStrays:
    def test_a_lone_material_pixel_takes_the_colour_around_it(self):
        rows = ['........', '.yyyyyy.', '.yybyyy.', '.yyyyyy.', '.yyyyyy.', '........']
        finished = finish(rows, {**GOLD, 'b': ('base', '#38b764')})
        assert 'b' not in finished.palette
        assert finished.notes[0] == '1 stray pixel took the colour around it'

    def test_a_lone_detail_pixel_stays(self):
        rows = ['........', '.yyyyyy.', '.yyeyyy.', '.yyyyyy.', '.yyyyyy.', '........']
        finished = finish(rows, {**GOLD, 'e': ('detail', '#1a1c2c')})
        assert finished.rows[2][3] == 'e'


class TestColours:
    def test_shadows_darken_toward_blue_and_highlights_lighten_toward_yellow(self):
        import colorsys

        def hsv(color: str) -> tuple[float, float, float]:
            digits = color.lstrip('#')
            return colorsys.rgb_to_hsv(
                *(int(digits[index : index + 2], 16) / 255 for index in (0, 2, 4))
            )

        pink = '#e8739a'
        shadow, highlight, outline = shadow_of(pink), highlight_of(pink), outline_of(pink)
        assert hsv(shadow)[2] < hsv(pink)[2] < hsv(highlight)[2]
        assert hsv(outline)[2] < hsv(shadow)[2]
        assert hsv(shadow)[0] < hsv(pink)[0] or hsv(shadow)[0] > 0.9  # toward blue
        assert (
            hsv(highlight)[0] > hsv(pink)[0] or hsv(highlight)[0] < 0.2
        )  # toward yellow
        assert outline != '#000000'
