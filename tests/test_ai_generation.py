"""
tests.test_ai_generation

Models that generate: pixel art, components and melodies, the capabilities of an agent, and
replaying cases through a choice model.
"""

from __future__ import annotations

import pytest

pytest.importorskip('pydantic_ai')

from pydantic_ai import Agent  # noqa: E402

import xnano  # noqa: E402
from xnano.ai import GenerationError  # noqa: E402
from xnano.ai.capabilities import ArtCapability, CanvasCapability, MusicCapability  # noqa: E402
from xnano.ai.models.art import Animation, ArtModel, ArtText, PaletteColor  # noqa: E402
from xnano.ai.models.components import ComponentModel  # noqa: E402
from xnano.ai.models.decisions import ChoiceModel  # noqa: E402
from xnano.ai.models.music import MusicModel  # noqa: E402
from xnano.ai.testing import ScriptedDecisionModel, replay, scripted_model  # noqa: E402


def palette(*entries: tuple[str, str, str]) -> list[dict[str, str]]:
    return [
        {'letter': letter, 'role': role, 'color': color}
        for letter, role, color in entries
    ]


LAYOUT = 'Centred, filling the canvas.'
OUTLINE = ('o', 'outline', '#1a1c2c')
GOLD = ('y', 'base', '#ffcd75')


def coin_text() -> ArtText:
    return ArtText(
        rows=('.oo.', 'oyyo', 'oyyo', '.oo.'),
        palette={
            'o': PaletteColor('outline', '#1a1c2c'),
            'y': PaletteColor('base', '#ffcd75'),
        },
    )


def last_feedback(script) -> str:
    """The text the model was sent back with its last request."""
    for message in reversed(script.messages[-1]):
        for part in getattr(message, 'parts', []):
            content = getattr(part, 'content', None)
            if isinstance(content, str) and 'could not be used' in content:
                return content
    return ''


class TestArtText:
    def test_it_refuses_ragged_rows_and_unknown_letters(self):
        with pytest.raises(ValueError, match='Row 1 of the art has 3 pixels'):
            ArtText(('oooo', 'ooo'), {'o': PaletteColor('outline', '#000000')})
        with pytest.raises(ValueError, match="uses 'x'"):
            ArtText(('ox',), {'o': PaletteColor('outline', '#000000')})

    def test_the_changes_that_need_no_model(self):
        text = coin_text()
        assert text.flip_horizontal() == text
        assert text.shift(x=1).rows[1] == '.oyy'
        assert text.shift(y=-1).rows[-1] == '....'
        assert text.recolor({'y': '#ff0000'}).palette['y'] == PaletteColor(
            'base', '#ff0000'
        )
        assert text.scaled(2).width == 8
        assert text.labelled().splitlines()[0].strip() == '0123'

    def test_art_made_from_it_gives_back_its_letters(self):
        text = coin_text()
        assert ArtText.from_art(text.to_art()) is text

    def test_other_art_is_read_from_its_pixels(self):
        art = xnano.draw(['#.', '##'], {'#': '#102030'})
        read = ArtText.from_art(art)
        assert read.rows == ('a.', 'aa')
        assert read.palette['a'] == PaletteColor('outline', '#102030')


class TestArtModel:
    def test_a_safe_repair_is_reported(self):
        answer = {
            'layout': LAYOUT,
            'palette': palette(('o', 'outline', '#f8c'), GOLD),
            'width': 4,
            'height': 4,
            'program': "ellipse(0, 0, W, H, 'o'); rect(1, 1, 2, 2, 'y')",
        }
        artist = ArtModel(scripted_model(answer).model, width=4, height=4)
        coin = artist.generate('a gold coin')
        assert (coin.width, coin.height) == (4, 4)
        report = artist.last_generation
        assert report.attempts == 1 and report.problems == ()
        assert any('#ff88cc' in note for note in report.notes)

    def test_the_error_quotes_the_last_answer(self):
        first = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 2,
            'height': 2,
            'program': "rect(0, 0, 2, 2, 'o'); undefined()",
        }
        last = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 2,
            'height': 2,
            'program': "rect(0, 0, 2, 2, 'o'); pixel(1, 1, 'x')",
        }
        script = scripted_model(first, last)
        artist = ArtModel(script.model, width=2, height=2, retries=1)
        with pytest.raises(GenerationError) as caught:
            artist.generate('a block')
        message = str(caught.value)
        assert "paints with 'x', which the palette does not name" in message
        assert 'the program failed' not in message
        assert len(caught.value.generation.problems) == 2

    def test_too_many_colours_and_a_wrong_size_are_sent_back(self):
        crowded = {
            'layout': LAYOUT,
            'palette': palette(*[(letter, 'detail', '#000000') for letter in 'abcdef']),
            'width': 6,
            'height': 1,
            'program': "rect(0, 0, W, H, 'a')",
        }
        script = scripted_model(crowded, repeat_last=True)
        artist = ArtModel(script.model, width=4, height=1, retries=1, max_colors=3)
        with pytest.raises(GenerationError) as caught:
            artist.generate('stripes')
        assert caught.value.code == 'ai.generation'
        problems = ' '.join(caught.value.generation.problems)
        assert 'at most 3 are allowed' in problems
        assert 'the size is 6 by 1; The art must be exactly 4 pixels wide' in problems

    def test_an_outline_surrounds_what_is_drawn(self):
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 4,
            'height': 4,
            'program': "rect(1, 1, 2, 2, 'y'); outline('o')",
        }
        artist = ArtModel(scripted_model(answer).model, width=4, height=4)
        rows = ArtText.from_art(artist.generate('a coin')).rows
        assert rows == ('.oo.', 'oyyo', 'oyyo', '.oo.')

    def test_the_renderer_outlines_and_shades_a_flat_drawing(self):
        answer = {
            'layout': LAYOUT,
            'palette': palette(GOLD, ('e', 'detail', '#1a1c2c')),
            'width': 10,
            'height': 10,
            'program': "ellipse(1, 1, 8, 8, 'y'); pixel(4, 4, 'e')",
        }
        artist = ArtModel(scripted_model(answer).model, width=10, height=10)
        text = ArtText.from_art(artist.generate('a coin'))
        roles = {letter: color.role for letter, color in text.palette.items()}
        assert set(roles.values()) == {'outline', 'base', 'highlight', 'shadow', 'detail'}
        outline = next(letter for letter, role in roles.items() if role == 'outline')
        assert text.rows[1].strip('.') == outline * len(text.rows[1].strip('.'))
        assert text.rows[0] == '.' * 10
        assert roles[text.rows[4][4]] == 'detail'
        highlight = next(letter for letter, role in roles.items() if role == 'highlight')
        shadow = next(letter for letter, role in roles.items() if role == 'shadow')
        assert highlight in text.rows[2] and shadow in text.rows[7]
        notes = ' '.join(artist.last_generation.notes)
        assert 'drew the outline' in notes and 'shaded 1 material' in notes

    def test_a_program_paints_the_letters(self):
        program = "rect(0, 0, 2, 2, 'o')\npixel(1, 1, 'y')\nmirror_x()"
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 4,
            'height': 2,
            'program': program,
        }
        artist = ArtModel(
            scripted_model(answer).model, strategy='program', width=4, height=2
        )
        assert ArtText.from_art(artist.generate('a cap')).rows == ('oooo', 'oyyo')

    def test_a_program_that_fails_is_sent_back(self):
        def answer(program: str) -> dict[str, object]:
            return {
                'layout': LAYOUT,
                'palette': palette(OUTLINE),
                'width': 1,
                'height': 1,
                'program': program,
            }

        script = scripted_model(answer('rect(0, 0, 1, 1)'), answer("pixel(0, 0, 'o')"))
        artist = ArtModel(script.model, strategy='program', width=1, height=1)
        artist.generate('a dot')
        feedback = last_feedback(script)
        assert 'the program failed' in feedback
        assert 'letter' in feedback

    def test_a_program_names_its_own_variables(self):
        program = "canvas = [[1]]\nfor x in range(W):\n    pixel(x, 0, 'o')"
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 3,
            'height': 1,
            'program': program,
        }
        artist = ArtModel(
            scripted_model(answer).model, strategy='program', width=3, height=1
        )
        assert ArtText.from_art(artist.generate('a bar')).rows == ('ooo',)

    def test_the_program_reference_draws_a_mushroom(self):
        from xnano.ai.models.art import _PROGRAM_REFERENCE

        program = _PROGRAM_REFERENCE.split('\n', 5)[5]
        answer = {
            'layout': LAYOUT,
            'palette': palette(
                OUTLINE,
                ('r', 'base', '#b13e53'),
                ('t', 'detail', '#e8d5b0'),
                ('w', 'highlight', '#f4f4f4'),
            ),
            'width': 8,
            'height': 10,
            'program': program,
        }
        artist = ArtModel(
            scripted_model(answer).model, strategy='program', width=8, height=10
        )
        rows = ArtText.from_art(artist.generate('a mushroom')).rows
        assert rows[2] == 'orwrrwro' and rows[7] == '..otto..'

    def test_a_large_piece_is_sketched_then_drawn_over_its_sketch(self):
        sketch = {
            'layout': LAYOUT,
            'palette': palette(GOLD),
            'width_in_blocks': 8,
            'height_in_blocks': 8,
            'program': "rect(2, 2, 4, 4, 'y')",
        }
        drawing = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 16,
            'height': 16,
            'program': "outline('o')",
        }
        script = scripted_model(sketch, drawing)
        artist = ArtModel(script.model, width=16, height=16)
        text = ArtText.from_art(artist.generate('a gold block'))
        rows = text.rows
        assert rows[3] == '....oooooooo....'
        assert rows[4][3] == 'o' and rows[4][12] == 'o'
        assert {text.palette[letter].role for letter in rows[4][4:12]} <= {
            'base',
            'highlight',
            'shadow',
        }
        report = artist.last_generation
        assert report.attempts == 2
        assert report.sketch == ('........', '........', '..yyyy..') + (
            '..yyyy..',
        ) * 3 + (
            '........',
            '........',
        )
        first_prompt = script.messages[0][0].parts[-1].content
        second_prompt = script.messages[1][-1].parts[-1].content
        assert isinstance(first_prompt, str) and first_prompt.startswith('Sketch: ')
        assert 'A reference:' not in first_prompt
        assert (
            isinstance(second_prompt, str)
            and 'Your sketch, 16 by 16 pixels' in second_prompt
        )
        assert 'already painted on the canvas' in second_prompt

    def test_a_drawing_that_leaves_its_sketch_goes_back(self):
        sketch = {
            'layout': LAYOUT,
            'palette': palette(GOLD),
            'width_in_blocks': 8,
            'height_in_blocks': 8,
            'program': "rect(2, 2, 4, 4, 'y')",
        }
        elsewhere = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 16,
            'height': 16,
            'program': "rect(0, 0, W, H, '.'); rect(0, 0, 2, 2, 'y')",
        }
        kept = {**elsewhere, 'program': "outline('o')"}
        script = scripted_model(sketch, elsewhere, kept)
        artist = ArtModel(script.model, width=16, height=16)
        artist.generate('a gold block')
        feedback = last_feedback(script)
        assert 'blocks inside the masses of the sketch are empty' in feedback
        assert 'abandoned its sketch' in feedback
        assert artist.last_generation.attempts == 3

    def test_a_sketch_that_fails_is_sent_back(self):
        broken = {
            'layout': LAYOUT,
            'palette': palette(GOLD),
            'width_in_blocks': 8,
            'height_in_blocks': 8,
            'program': 'undefined()',
        }
        sketch = {**broken, 'program': "rect(1, 1, 6, 6, 'y')"}
        drawing = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 16,
            'height': 16,
            'program': "outline('o')",
        }
        script = scripted_model(broken, sketch, drawing)
        artist = ArtModel(script.model, width=16, height=16)
        art = artist.generate('a gold block')
        assert (art.width, art.height) == (16, 16)
        assert 'the program failed' in artist.last_generation.problems[0]

    def test_a_sketch_in_the_wrong_number_of_blocks_is_sent_back(self):
        too_wide = {
            'layout': LAYOUT,
            'palette': palette(GOLD),
            'width_in_blocks': 20,
            'height_in_blocks': 8,
            'program': "rect(0, 0, W, H, 'y')",
        }
        sketch = {**too_wide, 'width_in_blocks': 8}
        drawing = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 16,
            'height': 16,
            'program': "outline('o')",
        }
        script = scripted_model(too_wide, sketch, drawing)
        artist = ArtModel(script.model, width=(8, 16), height=16)
        artist.generate('a gold block')
        feedback = [
            str(part.content)
            for message in script.messages[1]
            for part in message.parts
            if 'could not be used' in str(getattr(part, 'content', ''))
        ]
        assert (
            '20 blocks is 40 pixels wide; the sketch must be from 4 to 8 blocks wide'
            in feedback[0]
        )
        first_prompt = script.messages[0][0].parts[-1].content
        assert isinstance(first_prompt, str)
        assert 'exactly 8 blocks tall (16 pixels)' in first_prompt

    def test_an_svg_drawing_starts_from_its_sketch_as_rectangles(self):
        sketch = {
            'layout': LAYOUT,
            'palette': palette(GOLD),
            'width_in_blocks': 8,
            'height_in_blocks': 8,
            'program': "rect(2, 2, 4, 4, 'y')",
        }
        drawing = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 16,
            'height': 16,
            'svg': (
                '<svg viewBox="0 0 16 16"><rect x="4" y="4" width="8" height="8" fill="y" '
                'stroke="o" stroke-width="2" paint-order="stroke"/></svg>'
            ),
        }
        script = scripted_model(sketch, drawing)
        artist = ArtModel(script.model, strategy='svg', width=16, height=16)
        rows = ArtText.from_art(artist.generate('a gold block')).rows
        assert rows[3] == '...oooooooooo...'
        second_prompt = script.messages[1][-1].parts[-1].content
        assert isinstance(second_prompt, str)
        assert '<rect x="4" y="4" width="8" height="8" fill="y"/>' in second_prompt

    def test_small_art_is_drawn_in_one_step(self):
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 12,
            'height': 12,
            'program': "rect(0, 0, W, H, 'o')",
        }
        artist = ArtModel(scripted_model(answer).model, width=12, height=12)
        artist.generate('a block')
        assert artist.last_generation.attempts == 1
        assert artist.last_generation.sketch == ()

    def test_an_svg_is_sampled_at_pixel_centres(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 4">'
            '<circle cx="2" cy="2" r="2" fill="#1a1c2c"/>'
            '<rect x="1" y="1" width="2" height="2" fill="#ffcd75"/>'
            '</svg>'
        )
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 4,
            'height': 4,
            'svg': svg,
        }
        artist = ArtModel(scripted_model(answer).model, strategy='svg', width=4, height=4)
        rows = ArtText.from_art(artist.generate('a coin')).rows
        assert rows == ('.oo.', 'oyyo', 'oyyo', '.oo.')
        assert artist.last_generation.strategy == 'svg'

    def test_the_svg_reference_passes_its_own_checks(self):
        from xnano.ai.models.art import _SVG_REFERENCE

        answer = {
            'layout': LAYOUT,
            'palette': palette(
                OUTLINE,
                ('c', 'detail', '#8b5a3c'),
                ('g', 'base', '#a8d8ea'),
                ('p', 'accent', '#b13e53'),
                ('s', 'shadow', '#5d275d'),
                ('h', 'highlight', '#f4f4f4'),
            ),
            'width': 13,
            'height': 16,
            'svg': _SVG_REFERENCE[_SVG_REFERENCE.index('<svg') :],
        }
        sketch = {
            'layout': LAYOUT,
            'palette': palette(('g', 'base', '#a8d8ea')),
            'width_in_blocks': 7,
            'height_in_blocks': 8,
            'program': "rect(1, 0, 4, 3, 'g'); rect(0, 3, 6, 5, 'g')",
        }
        artist = ArtModel(
            scripted_model(sketch, answer).model, strategy='svg', width=13, height=16
        )
        rows = ArtText.from_art(artist.generate('a potion')).rows
        assert rows[1] == '...occccco...'
        assert rows[8] == '.oghgggggggo.'
        assert rows[12] == '.opppppppspo.'
        assert artist.last_generation.notes == ()

    def test_svg_faults_go_back_naming_the_element(self):
        faulty = (
            '<svg viewBox="0 0 4 4"><rect width="4" height="4" fill="#1a1c2c"/>'
            '<circle cx="9" cy="9" r="1" fill="#ffcd75"/>'
            '<rect x="1" y="1" width="2" height="2" fill="#ff0000"/></svg>'
        )
        fenced = (
            '```svg\n<svg viewBox="0 0 8 8">'
            '<rect width="8" height="8" fill="#1a1c2c"/></svg>\n```'
        )
        script = scripted_model(
            {
                'layout': LAYOUT,
                'palette': palette(OUTLINE, GOLD),
                'width': 4,
                'height': 4,
                'svg': faulty,
            },
            {
                'layout': LAYOUT,
                'palette': palette(OUTLINE),
                'width': 4,
                'height': 4,
                'svg': fenced,
            },
        )
        artist = ArtModel(script.model, strategy='svg', width=4, height=4)
        art = artist.generate('a block')
        feedback = last_feedback(script)
        assert '<circle cx=9 cy=9 r=1> lies outside the art' in feedback
        assert (
            '<rect x=1 y=1 width=2 height=2> paints #ff0000, which is not a colour of '
            'the palette'
        ) in feedback
        notes = artist.last_generation.notes
        assert any('code fence' in note for note in notes)
        assert any('scaled onto 4 by 4 pixels' in note for note in notes)
        assert ArtText.from_art(art).rows == ('oooo',) * 4

    def test_a_detail_smaller_than_a_pixel_keeps_one_pixel(self):
        svg = (
            '<svg viewBox="0 0 4 4"><rect width="4" height="4" fill="o"/>'
            '<circle cx="2.5" cy="1.5" r="0.3" fill="y"/></svg>'
        )
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, ('y', 'detail', '#ffcd75')),
            'width': 4,
            'height': 4,
            'svg': svg,
        }
        artist = ArtModel(scripted_model(answer).model, strategy='svg', width=4, height=4)
        rows = ArtText.from_art(artist.generate('a block with a spark')).rows
        assert rows == ('oooo', 'ooyo', 'oooo', 'oooo')
        notes = artist.last_generation.notes
        assert any('smaller than a pixel was kept as one pixel' in note for note in notes)

    def test_text_around_the_svg_is_removed(self):
        svg = '<![CDATA[\n<svg viewBox="0 0 2 2"><rect width="2" height="2" fill="o"/></svg>\n]]>'
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 2,
            'height': 2,
            'svg': svg,
        }
        artist = ArtModel(scripted_model(answer).model, strategy='svg', width=2, height=2)
        assert ArtText.from_art(artist.generate('a block')).rows == ('oo', 'oo')
        assert any('around the <svg>' in note for note in artist.last_generation.notes)

    def test_svg_that_cannot_be_drawn_goes_back(self):
        def answer(svg: str) -> dict[str, object]:
            return {
                'layout': LAYOUT,
                'palette': palette(OUTLINE),
                'width': 2,
                'height': 2,
                'svg': svg,
            }

        script = scripted_model(
            answer('<svg viewBox="0 0 2 2"><rect'),
            answer(
                '<svg viewBox="0 0 2 2"><text>hi</text>'
                '<rect width="2" height="2" fill="#1a1c2c"/></svg>'
            ),
        )
        artist = ArtModel(script.model, strategy='svg', width=2, height=2, retries=1)
        with pytest.raises(GenerationError) as caught:
            artist.generate('a block')
        first, second = caught.value.generation.problems
        assert 'not well-formed XML' in first
        assert '<text> is not supported' in second

    def test_references_are_shown_as_traced_svg(self):
        from xnano.ai._vector import read_svg
        from xnano.ai.models._art_references import REFERENCES
        from xnano.ai.models.art import _reference_text

        entry = REFERENCES[1]
        assert 'heart' in str(entry['subject'])
        heart = ArtText(
            tuple(entry['rows']),  # type: ignore[arg-type]
            {
                letter: PaletteColor(color['role'], color['color'])
                for letter, color in entry['palette'].items()  # type: ignore[union-attr]
            },
        )
        written = _reference_text(entry, 'svg')
        assert 'as SVG traced from its pixels' in written
        sampling = read_svg(written[written.index('<svg') :], default_size=(8, 8)).sample(
            8, 8
        )
        letters = {color.color: letter for letter, color in heart.palette.items()}
        rows = tuple(
            ''.join(letters[color] if color else '.' for color in row)
            for row in sampling.colors
        )
        assert rows == heart.rows

    def test_references_are_shown_as_programs_that_redraw_them(self):
        from xnano.ai.models._art_references import REFERENCES
        from xnano.ai.models.art import (
            _TRANSPARENT,
            _paint,
            _reference_text,
            _run_art_program,
        )

        for entry in REFERENCES:
            rows = [str(row) for row in entry['rows']]  # type: ignore[union-attr]
            written = _reference_text(entry, 'program')
            assert written.startswith(f'A reference: {entry["subject"]}, ')
            program = '\n'.join(
                line for line in written.splitlines()[1:] if line and ' = ' not in line
            )
            width, height = len(rows[0]), len(rows)
            grid = [[_TRANSPARENT] * width for _ in range(height)]
            for shape in _run_art_program(program, width, height):
                _paint(grid, shape)
            assert [''.join(row) for row in grid] == rows, entry['subject']

    def test_the_most_connected_candidate_is_kept(self):
        scattered = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 3,
            'height': 3,
            'program': "for x, y in [(0, 0), (2, 0), (0, 2), (2, 2)]:\\n    pixel(x, y, 'o')",
        }
        solid = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 3,
            'height': 3,
            'program': "rect(0, 0, 3, 3, 'o'); pixel(1, 1, '.')",
        }
        artist = ArtModel(scripted_model(scattered, solid).model, width=3, height=3)
        art = artist.generate('a ring', candidates=2)
        assert ArtText.from_art(art).rows == ('ooo', 'o.o', 'ooo')

    def test_a_size_can_be_a_share_of_the_canvas(self):
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 10,
            'height': 4,
            'program': "rect(0, 0, W, H, 'o')",
        }
        with xnano.new(width=20, height=4):
            artist = ArtModel(scripted_model(answer).model)
            art = artist.generate('a bar', width='50%', height='50%')
        assert (art.width, art.height) == (10, 4)

    def test_an_edit_is_a_patch_that_keeps_protected_pixels(self):
        coin = coin_text().to_art()
        touching = {'runs': [{'row': 1, 'column': 1, 'letters': 'oo'}], 'new_colors': []}
        sparing = {'runs': [{'row': 0, 'column': 0, 'letters': 'o'}], 'new_colors': []}
        script = scripted_model(('patch', touching), ('patch', sparing))
        artist = ArtModel(script.model)
        edited = artist.edit(coin, 'fill a corner', protect=['base'])
        assert 'protected pixels changed at (1, 1), (2, 1)' in last_feedback(script)
        assert ArtText.from_art(edited).rows[0] == 'ooo.'
        assert ArtText.from_art(coin).rows[0] == '.oo.'

    def test_new_colours_need_permission(self):
        coin = coin_text().to_art()
        painting = {
            'runs': [{'row': 1, 'column': 1, 'letters': 'rr'}],
            'new_colors': palette(('r', 'accent', '#ff0000')),
        }
        artist = ArtModel(
            scripted_model(('patch', painting), repeat_last=True).model, retries=0
        )
        with pytest.raises(GenerationError):
            artist.edit(coin, 'paint it red', mode='patch')
        allowed = ArtModel(scripted_model(('patch', painting)).model)
        edited = allowed.edit(coin, 'paint it red', allow_new_colors=True, mode='patch')
        assert ArtText.from_art(edited).palette['r'].role == 'accent'

    def test_protect_names_what_the_art_has(self):
        artist = ArtModel(scripted_model().model)
        with pytest.raises(ValueError, match='neither a role nor a letter'):
            artist.edit(coin_text().to_art(), 'x', protect=['skin'])

    def test_an_animation_is_one_patch_per_frame(self):
        frames = {'frames_runs': [[], [{'row': 0, 'column': 1, 'letters': '..'}]]}
        artist = ArtModel(scripted_model(('animation', frames)).model)
        animation = artist.animate(coin_text().to_art(), 'a blink', frames=2, fps=2)
        assert isinstance(animation, Animation)
        assert [ArtText.from_art(frame).rows[0] for frame in animation.frames] == [
            '.oo.',
            '....',
        ]
        with xnano.new(width=4, height=2) as canvas:
            canvas.screen.write(animation)
            first = canvas.screen.render()
            canvas.clock.step(delta_seconds=0.5)
            assert canvas.screen.render() != first

    def test_variants_edit_the_same_art(self):
        patch = {'runs': [{'row': 0, 'column': 0, 'letters': 'o'}], 'new_colors': []}
        artist = ArtModel(scripted_model(('patch', patch), repeat_last=True).model)
        variants = artist.variants(coin_text().to_art(), ['one', 'two'])
        assert len(variants) == 2

    def test_a_critique_round_redraws_and_keeps_the_better_piece(self):
        broken = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 4,
            'height': 4,
            'program': "for x, y in [(0, 0), (3, 0), (0, 3), (3, 3)]:\n    pixel(x, y, 'o')\nrect(1, 1, 2, 2, 'y')",
        }
        whole = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 4,
            'height': 4,
            'program': "ellipse(0, 0, W, H, 'o'); rect(1, 1, 2, 2, 'y')",
        }
        script = scripted_model(
            broken,
            ('critique', {'score': 4, 'problems': ['the outline is broken']}),
            whole,
            ('critique', {'score': 8, 'problems': []}),
        )
        artist = ArtModel(script.model, width=4, height=4, critique=1)
        art = artist.generate('a gold coin')
        assert ArtText.from_art(art).rows == ('.oo.', 'oyyo', 'oyyo', '.oo.')
        assert [critique.score for critique in artist.last_generation.critiques] == [4, 8]
        shown = []
        for message in script.messages[1]:
            for part in message.parts:
                content = getattr(part, 'content', None)
                if isinstance(content, list):
                    shown.extend(type(item).__name__ for item in content)
        assert shown == ['str', 'BinaryContent']

    def test_a_worse_revision_is_dropped(self):
        whole = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 4,
            'height': 4,
            'program': "ellipse(0, 0, W, H, 'o'); rect(1, 1, 2, 2, 'y')",
        }
        broken = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 4,
            'height': 4,
            'program': "for x, y in [(0, 0), (3, 0), (0, 3), (3, 3)]:\n    pixel(x, y, 'o')\nrect(1, 1, 2, 2, 'y')",
        }
        script = scripted_model(
            whole,
            ('critique', {'score': 7, 'problems': ['a highlight would help']}),
            broken,
            ('critique', {'score': 3, 'problems': ['the outline is broken']}),
        )
        artist = ArtModel(script.model, width=4, height=4)
        art = artist.generate('a gold coin', critique=1)
        assert ArtText.from_art(art).rows == ('.oo.', 'oyyo', 'oyyo', '.oo.')

    def test_nothing_to_fix_ends_the_rounds(self):
        whole = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE, GOLD),
            'width': 4,
            'height': 4,
            'program': "ellipse(0, 0, W, H, 'o'); rect(1, 1, 2, 2, 'y')",
        }
        script = scripted_model(whole, ('critique', {'score': 9, 'problems': []}))
        artist = ArtModel(script.model, width=4, height=4)
        artist.generate('a gold coin', critique=3)
        assert len(artist.last_generation.critiques) == 1

    def test_the_rounds_of_critique_are_bounded(self):
        with pytest.raises(ValueError, match='from 0 to 3'):
            ArtModel(scripted_model().model, critique=4)

    def test_the_critic_sees_a_png_of_the_piece(self):
        from xnano.ai.models.art import _png_of

        data = _png_of(coin_text())
        assert data.startswith(b'\x89PNG\r\n\x1a\n')
        assert int.from_bytes(data[16:20], 'big') == 4 * 64

    def test_installed_references_are_shown(self, tmp_path, monkeypatch):
        from xnano.ai import assets

        reference = {
            'subject': 'a gold coin',
            'tags': ['coin', 'treasure'],
            'width': 4,
            'height': 4,
            'palette': {'o': {'role': 'outline', 'color': '#000000'}},
            'rows': ['.oo.', 'o..o', 'o..o', '.oo.'],
        }
        monkeypatch.setattr(
            assets,
            '_entries',
            lambda name: (reference,) if name == 'art-references' else (),
        )
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 4,
            'height': 4,
            'program': "rect(0, 0, W, H, 'o')",
        }
        script = scripted_model(answer)
        ArtModel(script.model, width=4, height=4).generate('a silver coin')
        prompt = script.messages[0][0].parts[-1].content
        assert isinstance(prompt, str)
        assert 'A reference: a gold coin' in prompt


class TestComponentModel:
    def test_a_program_draws_the_component(self):
        answer = {
            'layout': 'One bold line.',
            'program': "canvas.screen.write('Ready', bold=True)",
        }
        badge = ComponentModel(scripted_model(answer).model).generate(
            'a badge', width=8, height=1
        )
        assert (badge.width, badge.height, badge.text) == (8, 1, 'Ready')
        with xnano.new(width=12, height=3) as canvas:
            canvas.screen.write(badge, border='rounded')
            assert canvas.screen.render().splitlines()[1] == '│Ready   │'

    def test_drawing_past_the_edge_goes_back_with_a_ruler(self):
        tall = {'layout': 'x', 'program': "canvas.screen.write(['one', 'two', 'three'])"}
        fitting = {'layout': 'x', 'program': "canvas.screen.write('short')"}
        script = scripted_model(tall, fitting)
        components = ComponentModel(script.model)
        components.generate('a line', width=10, height=1)
        feedback = last_feedback(script)
        assert 'past the bottom' in feedback and '0123456789' in feedback
        assert components.last_generation.attempts == 2

    def test_what_can_be_fixed_is_fixed_and_reported(self):
        program = (
            "canvas.screen.write('a line far too long for this card', border='round', "
            "foreground='lightblu', x=40, colour='red')"
        )
        components = ComponentModel(
            scripted_model({'layout': 'x', 'program': program}).model
        )
        card = components.generate('a card', width=16, height=3)
        assert card.text.splitlines() == [
            '╭──────────────╮',
            '│a line far too│',
            '╰──────────────╯',
        ]
        notes = ' '.join(components.last_generation.notes)
        for fixed in (
            "ignored 'colour'",
            "'round' was read as 'rounded'",
            "'lightblu' was read as 'light_blue'",
            'was cut to the 14',
            'x=40',
        ):
            assert fixed in notes
        assert components.last_generation.attempts == 1

    def test_what_cannot_be_fixed_goes_back(self):
        wrong = {'layout': 'x', 'program': "canvas.screen.writ('typo')"}
        right = {'layout': 'x', 'program': "canvas.screen.write('fixed')"}
        script = scripted_model(wrong, right)
        ComponentModel(script.model).generate('a word', width=8, height=1)
        assert 'the program failed' in last_feedback(script)

    def test_an_edit_keeps_the_size(self):
        first = {'layout': 'x', 'program': "canvas.screen.write('one')"}
        second = {'layout': 'x', 'program': "canvas.screen.write('two')"}
        components = ComponentModel(scripted_model(first, second).model)
        card = components.generate('a word', width=6, height=2)
        edited = components.edit(card, 'say two')
        assert (edited.width, edited.height, edited.text.splitlines()[0]) == (6, 2, 'two')
        assert card.text.splitlines()[0] == 'one'

    def test_a_size_beyond_the_most_is_refused(self):
        with pytest.raises(ValueError, match='from 1 to 48'):
            ComponentModel(scripted_model().model).generate('x', width=60)


class TestMusicModel:
    def test_melody_text_becomes_a_melody(self):
        pytest.importorskip('xnano_audio')
        composer = MusicModel(scripted_model({'text': 'C4 E4 G4:2 | F4 D4 C4:2'}).model)
        theme = composer.compose('a march', bars=2, bpm=100, symbol='march_theme')
        assert (theme.length_beats, theme.bpm) == (8.0, 100.0)
        assert xnano.symbols.lookup('march_theme') is theme

    def test_a_bar_of_the_wrong_length_goes_back(self):
        pytest.importorskip('xnano_audio')
        short = {'text': 'C4 E4 G4 | F4 D4 C4:2'}
        fixed = {'text': 'C4 E4 G4:2 | F4 D4 C4:2'}
        script = scripted_model(short, fixed)
        MusicModel(script.model).compose('x', bars=2, bpm=120)
        assert 'bar 1 holds 3 beats, but a bar of 4/4 holds 4' in last_feedback(script)

    def test_the_tempo_is_the_active_canvas_s(self):
        pytest.importorskip('xnano_audio')
        composer = MusicModel(scripted_model({'text': 'C4 D4 E4'}).model, meter='3/4')
        with xnano.new(width=4, height=1, bpm=90):
            theme = composer.compose('a waltz', bars=1)
        assert theme.bpm == 90.0

    def test_a_variation_keeps_the_bars_and_the_tempo(self):
        pytest.importorskip('xnano_audio')
        from xnano.audio import Melody

        theme = Melody('C4 E4 G4:2 | F4 D4 C4:2', bpm=140)
        variation = MusicModel(
            scripted_model({'text': 'E4 G4 C5:2 | D5 B4 C5:2'}).model
        ).vary(theme, 'higher')
        assert (variation.length_beats, variation.bpm) == (8.0, 140.0)


class TestCapabilities:
    def test_an_agent_writes_a_component_and_sees_the_canvas(self):
        script = scripted_model(
            (
                'write_component',
                {
                    'program': "canvas.screen.write('hello')",
                    'width': 8,
                    'height': 1,
                    'name': 'greeting',
                },
            ),
            ('observe', {}),
            'Done.',
        )
        with xnano.new(width=20, height=3) as canvas:
            capability = CanvasCapability(canvas)
            agent = Agent(script.model, capabilities=[capability])
            assert agent.run_sync('Say hello.').output == 'Done.'
            assert canvas.screen.render().splitlines()[0] == 'hello'
            assert 'greeting' in capability.components

    def test_an_agent_shows_art_drawn_by_a_program(self):
        script = scripted_model(
            (
                'show_art',
                {
                    'name': 'ink_dot',
                    'palette': palette(OUTLINE),
                    'width': 2,
                    'height': 2,
                    'program': "rect(0, 0, W, H, 'o')",
                },
            ),
            'Done.',
        )
        with xnano.new(width=20, height=3) as canvas:
            agent = Agent(script.model, capabilities=[CanvasCapability(canvas)])
            assert agent.run_sync('Draw a dot.').output == 'Done.'
            assert '\x1b[' in canvas.screen.render(format='ansi').splitlines()[0]
        art = xnano.symbols.lookup('ink_dot')
        assert (art.width, art.height) == (2, 2)

    def test_the_keys_that_end_the_program_are_refused(self):
        script = scripted_model(
            ('press_key', {'key': 'ctrl+c'}), ('press_key', {'key': 'a'}), 'Done.'
        )
        with xnano.new(width=20, height=3) as canvas:
            heard = []
            canvas.hook(lambda context: heard.append(context.keyboard.key), on='key')
            agent = Agent(
                script.model, capabilities=[CanvasCapability(canvas, keyboard=True)]
            )
            agent.run_sync('go')
            assert heard == ['a']
        tools = [tool.name for tool in script.calls[0].function_tools]
        assert 'press_key' in tools and 'click' not in tools

    def test_the_mouse_acts_at_cells_inside_the_canvas(self):
        script = scripted_model(
            ('click', {'x': 50, 'y': 0}),
            ('drag', {'from_x': 0, 'from_y': 0, 'to_x': 3, 'to_y': 0}),
            'Done.',
        )
        with xnano.new(width=20, height=3) as canvas:
            heard = []
            canvas.hook(lambda context: heard.append(context.mouse.kind), on='mouse')
            agent = Agent(
                script.model, capabilities=[CanvasCapability(canvas, mouse=True)]
            )
            agent.run_sync('go')
            assert heard == ['press', 'drag', 'release']

    def test_art_and_melodies_are_kept_by_name(self):
        pytest.importorskip('xnano_audio')
        script = scripted_model(
            (
                'draw_art',
                {
                    'name': 'gem_piece',
                    'palette': palette(('g', 'base', '#00ff00')),
                    'width': 2,
                    'height': 2,
                    'program': "pixel(0, 0, 'g'); pixel(1, 1, 'g')",
                },
            ),
            (
                'edit_art',
                {
                    'name': 'gem_piece',
                    'runs': [{'row': 0, 'column': 1, 'letters': 'g'}],
                    'new_colors': [],
                },
            ),
            ('compose_melody', {'name': 'gem_tune', 'text': 'C4 E4 G4:2'}),
            'Done.',
        )
        agent = Agent(script.model, capabilities=[ArtCapability(), MusicCapability()])
        agent.run_sync('go')
        assert xnano.symbols.lookup('gem_piece').pixel(1, 0) == (0, 255, 0, 255)
        assert xnano.symbols.lookup('gem_tune').length_beats == 4.0


class TestReplay:
    CASES = [
        {'evidence': {'wall': 'right'}, 'options': ['left', 'right'], 'expected': 'left'},
        {'evidence': {'wall': 'left'}, 'options': ['left', 'right'], 'expected': 'right'},
        {'evidence': {'wall': 'right'}, 'options': ['left', 'right'], 'expected': 'left'},
    ]

    def test_the_figures_come_from_one_answer_per_case(self):
        model = ScriptedDecisionModel({'response': {'left': 0.8, 'right': 0.2}})
        report = replay(ChoiceModel(model), self.CASES, should_check_order=False)
        # The third case is the first one again, whose saved answer is reused.
        assert len(model.requests) == 2
        assert report.accuracy == pytest.approx(2 / 3)
        assert report.majority_baseline == pytest.approx(2 / 3)
        assert report.calibration_error == pytest.approx(abs(2 / 3 - 0.8))
        assert report.order_sensitivity is None
        assert report.at_threshold(0.9).coverage == 0.0

    def test_reversing_the_options_measures_order_sensitivity(self):
        def first_listed(name, question, request):
            return next(iter(question.criteria))

        report = replay(ChoiceModel(ScriptedDecisionModel(first_listed)), self.CASES)
        assert report.order_sensitivity == 1.0

    def test_a_file_of_cases_is_read(self, tmp_path):
        import json

        path = tmp_path / 'cases.jsonl'
        path.write_text(''.join(json.dumps(case) + '\n' for case in self.CASES))
        model = ScriptedDecisionModel({'response': 'left'})
        assert replay(
            ChoiceModel(model), path, should_check_order=False
        ).accuracy == pytest.approx(2 / 3)

    def test_a_case_expecting_a_missing_option_is_refused(self):
        with pytest.raises(ValueError, match='not one of its options'):
            replay(
                ChoiceModel(ScriptedDecisionModel()),
                [{'evidence': {}, 'options': ['a', 'b'], 'expected': 'c'}],
            )


class TestSvgReading:
    def sampled(self, svg: str, width: int, height: int | None = None) -> list[str]:
        from xnano.ai._vector import read_svg

        height = width if height is None else height
        sampling = read_svg(svg, default_size=(width, height)).sample(width, height)
        return [
            ''.join('#' if color else '.' for color in row) for row in sampling.colors
        ]

    def test_transforms_compose_left_to_right(self):
        svg = (
            '<svg viewBox="0 0 4 4"><g transform="translate(2 0) scale(2 1)">'
            '<rect width="1" height="2" fill="#000"/></g></svg>'
        )
        assert self.sampled(svg, 4) == ['..##', '..##', '....', '....']

    def test_an_even_odd_path_leaves_a_hole(self):
        svg = (
            '<svg viewBox="0 0 3 3"><path fill-rule="evenodd" fill="#000" '
            'd="M0 0H3V3H0Z M1 1H2V2H1Z"/></svg>'
        )
        assert self.sampled(svg, 3) == ['###', '#.#', '###']

    def test_a_stroke_covers_the_pixels_along_a_line(self):
        svg = (
            '<svg viewBox="0 0 3 3"><line x1="0" y1="1.5" x2="3" y2="1.5" '
            'stroke="#000" stroke-width="1"/></svg>'
        )
        assert self.sampled(svg, 3) == ['...', '###', '...']

    def test_an_arc_draws_a_half_disc(self):
        svg = '<svg viewBox="0 0 4 4"><path d="M0 2 A2 2 0 0 1 4 2 Z" fill="#000"/></svg>'
        assert self.sampled(svg, 4) == ['.##.', '####', '....', '....']

    def test_a_line_ends_where_it_is_drawn_unless_its_cap_says(self):
        def line(cap: str) -> str:
            return (
                '<svg viewBox="0 0 5 3"><line x1="1" y1="1.5" x2="4" y2="1.5" '
                f'stroke="#000" stroke-linecap="{cap}"/></svg>'
            )

        assert self.sampled(line('butt'), 5, 3)[1] == '.###.'
        assert self.sampled(line('square'), 5, 3)[1] == '#####'

    def test_each_pixel_takes_the_colour_covering_most_of_it(self):
        svg = '<svg viewBox="0 0 4 1"><rect x="0.7" width="2.6" height="1" fill="#000"/></svg>'
        assert self.sampled(svg, 4, 1) == ['.##.']

    def test_a_stroke_under_the_fill_is_an_outside_outline(self):
        svg = (
            '<svg viewBox="0 0 6 4"><rect x="2" y="1" width="2" height="2" fill="#f00" '
            'stroke="#000" stroke-width="2" paint-order="stroke"/></svg>'
        )
        from xnano.ai._vector import read_svg

        sampling = read_svg(svg, default_size=(6, 4)).sample(6, 4)
        drawn = [
            ''.join({'#ff0000': 'r', '#000000': 'o', None: '.'}[color] for color in row)
            for row in sampling.colors
        ]
        assert drawn == ['.oooo.', '.orro.', '.orro.', '.oooo.']

    def test_unreadable_svg_names_each_problem(self):
        from xnano.ai._vector import SvgError, read_svg

        with pytest.raises(SvgError) as caught:
            read_svg(
                '<svg viewBox="0 0 2 2"><circle r="0"/><path d="L1 1"/>'
                '<rect fill="url(#g)" width="1" height="1"/></svg>',
                default_size=(2, 2),
            )
        problems = caught.value.problems
        assert problems[0] == '<circle cx=0 cy=0 r=0> has no radius'
        assert 'must start with M, but starts with L' in problems[1]
        assert 'not a gradient or pattern' in problems[2]

    def test_entities_are_refused(self):
        from xnano.ai._vector import SvgError, read_svg

        with pytest.raises(SvgError, match='declares entities'):
            read_svg(
                '<!DOCTYPE svg [<!ENTITY a "x">]><svg viewBox="0 0 1 1"/>',
                default_size=(1, 1),
            )


class TestSymmetrical:
    def test_the_model_draws_the_left_half_and_it_is_mirrored(self):
        answer = {
            'layout': LAYOUT,
            'palette': palette(GOLD, ('e', 'detail', '#1a1c2c')),
            'width': 4,
            'height': 8,
            'program': "rect(0, 0, W, H, 'y'); pixel(3, 2, 'e')",
        }
        script = scripted_model(answer)
        artist = ArtModel(script.model, width=8, height=8)
        text = ArtText.from_art(artist.generate('a face', symmetrical=True))
        assert (text.width, text.height) == (8, 8)
        assert text.rows[2][3:5] == 'ee'
        assert all(row == row[::-1] for row in text.rows)
        prompt = script.messages[0][0].parts[-1].content
        assert isinstance(prompt, str)
        assert 'draw only its left half' in prompt
        assert 'exactly 4 pixels wide' in prompt

    def test_an_odd_width_shares_its_middle_column(self):
        answer = {
            'layout': LAYOUT,
            'palette': palette(OUTLINE),
            'width': 4,
            'height': 3,
            'program': "rect(0, 0, W, H, 'o'); pixel(3, 1, '.')",
        }
        artist = ArtModel(scripted_model(answer).model, width=7, height=3)
        text = ArtText.from_art(artist.generate('a bar', symmetrical=True))
        assert text.rows == ('ooooooo', 'ooo.ooo', 'ooooooo')

    def test_a_large_symmetrical_piece_is_sketched_at_half_width(self):
        sketch = {
            'layout': LAYOUT,
            'palette': palette(GOLD),
            'width_in_blocks': 4,
            'height_in_blocks': 8,
            'program': "rect(1, 1, 3, 6, 'y')",
        }
        drawing = {
            'layout': LAYOUT,
            'palette': palette(GOLD),
            'width': 8,
            'height': 16,
            'program': "pixel(7, 2, 'y')",
        }
        script = scripted_model(sketch, drawing)
        artist = ArtModel(script.model, width=16, height=16)
        text = ArtText.from_art(artist.generate('a vase', symmetrical=True))
        assert (text.width, text.height) == (16, 16)
        # The silhouette is symmetric; the shading is not, since the light stays top left.
        silhouette = [''.join('#' if c != '.' else '.' for c in row) for row in text.rows]
        assert all(row == row[::-1] for row in silhouette)
        assert silhouette[2] == '..############..'
        first_prompt = script.messages[0][0].parts[-1].content
        assert isinstance(first_prompt, str)
        assert 'exactly 4 blocks wide (8 pixels)' in first_prompt
        assert 'draw only its left half' in first_prompt

    def test_a_half_that_does_not_reach_the_middle_goes_back(self):
        centred = {
            'layout': LAYOUT,
            'palette': palette(GOLD),
            'width': 4,
            'height': 8,
            'program': "rect(1, 1, 2, 6, 'y')",
        }
        reaching = {**centred, 'program': "rect(1, 1, 3, 6, 'y')"}
        script = scripted_model(centred, reaching)
        artist = ArtModel(script.model, width=8, height=8)
        text = ArtText.from_art(artist.generate('a vase', symmetrical=True))
        assert text.width == 8
        assert 'reach the right edge of the canvas' in last_feedback(script)
        assert artist.last_generation.attempts == 2

    def test_symmetrical_must_be_a_boolean(self):
        artist = ArtModel(scripted_model().model, width=8, height=8)
        with pytest.raises(ValueError, match='symmetrical must be True or False'):
            artist.generate('a face', symmetrical='yes')  # type: ignore[arg-type]


class TestLooks:
    def answer(self, program: str = "rect(0, 0, W, H, 'y'); pixel(2, 2, 'e')") -> dict:
        return {
            'layout': LAYOUT,
            'palette': palette(GOLD, ('e', 'detail', '#1a1c2c')),
            'width': 8,
            'height': 8,
            'program': program,
        }

    def test_braille_art_is_packed_two_by_four_and_the_model_is_told(self):
        script = scripted_model(self.answer())
        artist = ArtModel(script.model, width=8, height=8)
        art = artist.generate('a coin', braille=True)
        assert art.encoding == 'braille'
        assert len(art.render().split('\n')) == 2
        # flat colours, dotted: the edges solid, the inside one dot in four
        text = ArtText.from_art(art)
        assert text.rows[0] == 'yyyyyyyy' and text.rows[7] == 'yyyyyyyy'
        assert text.rows[5][0] == 'y' and text.rows[5][7] == 'y'
        assert text.rows[5][1] == '.' and text.rows[4][2] == 'y'
        assert text.rows[2][2] == 'e'
        assert all(
            'drew the outline' not in note for note in artist.last_generation.notes
        )
        prompt = script.messages[0][0].parts[-1].content
        assert isinstance(prompt, str) and 'braille dots' in prompt

    def test_bordered_art_shows_its_edge_in_box_drawing_and_the_model_is_told(self):
        script = scripted_model(self.answer("rect(0, 0, W, H, 'y')"))
        artist = ArtModel(script.model, width=8, height=8)
        art = artist.generate('a coin', borders=True)
        assert art.borders is True
        assert art.render().split('\n')[0] == '┌──────┐'
        assert all(
            'drew the outline' not in note for note in artist.last_generation.notes
        )
        assert all(
            'drew the outline' not in note for note in artist.last_generation.notes
        )
        prompt = script.messages[0][0].parts[-1].content
        assert isinstance(prompt, str) and 'box-drawing characters' in prompt

    def test_the_looks_must_be_booleans(self):
        artist = ArtModel(scripted_model().model, width=8, height=8)
        with pytest.raises(ValueError, match='braille must be True or False'):
            artist.generate('a coin', braille='yes')  # type: ignore[arg-type]
        with pytest.raises(ValueError, match='borders must be True or False'):
            artist.generate('a coin', borders=1)  # type: ignore[arg-type]
