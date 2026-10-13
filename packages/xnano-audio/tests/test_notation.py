"""Notes and melodies are written with operators, and their names are checked by type aliases."""

from __future__ import annotations

import math
import typing

import pytest

import xnano_audio
from xnano_audio import (
    InstrumentName,
    NoteName,
    TerminalMelody,
    TerminalNote,
    instrument_names,
    note_to_hertz,
)

SEMITONES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def midi_of(name: str) -> int:
    letter, rest = name[0], name[1:]
    accidental = 1 if rest.startswith('#') else -1 if rest.startswith('b') else 0
    octave = int(rest.lstrip('#b'))
    return 12 * (octave + 1) + SEMITONES[letter] + accidental


class TestAliases:
    def test_every_note_name_is_a_real_pitch(self):
        names = typing.get_args(NoteName)
        assert len(names) == len(set(names)) > 100
        for name in names:
            expected = 440.0 * 2 ** ((midi_of(name) - 69) / 12)
            assert note_to_hertz(name) == pytest.approx(expected, rel=1e-4), name
            assert TerminalNote(name).pitch == midi_of(name), name

    def test_sharps_and_flats_name_the_same_note(self):
        assert TerminalNote('Db4') == TerminalNote('C#4')
        assert TerminalNote('Bb3').name == 'A#3'

    def test_a_notes_name_is_a_note_name(self):
        assert TerminalNote(61).name in typing.get_args(NoteName)

    def test_the_instrument_names_are_exactly_the_built_in_instruments(self):
        assert set(typing.get_args(InstrumentName)) == set(instrument_names())

    def test_the_aliases_are_exported(self):
        for name in ('NoteName', 'InstrumentName', 'Pitch'):
            assert name in xnano_audio.__all__


class TestNoteOperators:
    def test_adding_a_number_moves_the_pitch_up_in_semitones(self):
        assert TerminalNote('C4') + 1 == TerminalNote('C#4')
        assert (TerminalNote('C4') + 12).name == 'C5'
        assert (1 + TerminalNote('C4')).name == 'C#4'

    def test_subtracting_a_number_moves_the_pitch_down(self):
        assert (TerminalNote('C4') - 1).name == 'B3'

    def test_subtracting_a_note_measures_the_distance(self):
        assert TerminalNote('G4') - TerminalNote('C4') == 7
        assert TerminalNote('C4') - TerminalNote('G4') == -7

    def test_timing_and_strength_are_kept(self):
        note = TerminalNote('C4', start_beats=2.0, duration_beats=0.5, velocity=0.3)
        moved = note + 3
        assert (moved.start_beats, moved.duration_beats) == (2.0, 0.5)
        assert moved.velocity == pytest.approx(0.3)

    def test_leaving_the_midi_range_says_so(self):
        with pytest.raises(ValueError, match='MIDI'):
            TerminalNote(127) + 1
        with pytest.raises(ValueError, match='MIDI'):
            TerminalNote(0) - 1

    def test_notes_convert_to_their_midi_number(self):
        assert int(TerminalNote('C4')) == 60

    def test_notes_are_ordered_by_pitch_then_start(self):
        assert TerminalNote('C4') < TerminalNote('D4')
        assert TerminalNote('C4', start_beats=1) > TerminalNote('C4')
        assert min(TerminalNote('E4'), TerminalNote('C4')).name == 'C4'
        assert [
            note.name
            for note in sorted(
                [TerminalNote('E4'), TerminalNote('C4'), TerminalNote('D4')]
            )
        ] == ['C4', 'D4', 'E4']
        assert TerminalNote('C4') <= TerminalNote('C4')
        assert not TerminalNote('C4') < TerminalNote('C4')

    def test_a_bool_is_not_a_number_of_semitones(self):
        with pytest.raises(TypeError):
            TerminalNote('C4') + True  # type: ignore[operator]

    def test_a_note_does_not_add_to_text(self):
        with pytest.raises(TypeError):
            TerminalNote('C4') + 'x'  # type: ignore[operator]
        assert TerminalNote('C4') != 'C4'


class TestMelodyOperators:
    def test_adding_notes_makes_a_melody_that_plays_in_order(self):
        melody = TerminalNote('C4') + TerminalNote('E4') + TerminalNote('G4')
        assert isinstance(melody, TerminalMelody)
        assert [note.name for note in melody] == ['C4', 'E4', 'G4']
        assert [note.start_beats for note in melody] == [0.0, 1.0, 2.0]

    def test_the_or_operator_plays_together(self):
        chord = TerminalNote('C4') | TerminalNote('E4') | TerminalNote('G4')
        assert {note.start_beats for note in chord} == {0.0}
        assert len(chord) == 3

    def test_a_number_transposes_a_melody(self):
        melody = TerminalNote('C4') + TerminalNote('E4')
        assert [note.name for note in melody + 2] == ['D4', 'F#4']
        assert [note.name for note in 2 + melody] == ['D4', 'F#4']
        assert [note.name for note in melody - 1] == ['B3', 'D#4']

    def test_multiplying_repeats(self):
        melody = TerminalNote('C4') + TerminalNote('E4')
        assert len(melody * 3) == len(3 * melody) == 6
        assert (melody * 2).length_beats == 2 * melody.length_beats

    def test_shifting_moves_it_in_time(self):
        melody = TerminalNote('C4') + TerminalNote('E4')
        assert [note.start_beats for note in melody >> 2] == [2.0, 3.0]
        assert [note.start_beats for note in (melody >> 2) << 2] == [0.0, 1.0]

    def test_a_melody_and_a_note_combine(self):
        melody = TerminalNote('C4') + TerminalNote('E4')
        assert len(melody + TerminalNote('G4')) == 3
        assert len(TerminalNote('G4') + melody) == 3
        assert len(melody | TerminalNote('G4')) == 3

    def test_it_composes_like_ordinary_arithmetic(self):
        scale = TerminalNote('C4')
        phrase = scale + (scale + 4) + (scale + 7)
        assert [note.name for note in phrase] == ['C4', 'E4', 'G4']
        song = phrase * 2 + (phrase + 5) * 2
        assert len(song) == 12

    def test_the_result_still_renders_to_sound(self):
        melody = TerminalNote('C4') + TerminalNote('G4')
        sound = melody.render('piano')
        assert sound.duration_milliseconds > 0
        assert math.isfinite(sound.peak)

    def test_text_is_not_a_number_of_semitones(self):
        melody = TerminalNote('C4') + TerminalNote('E4')
        with pytest.raises(TypeError):
            melody + 'x'  # type: ignore[operator]
        with pytest.raises(TypeError):
            melody * 1.5  # type: ignore[operator]
