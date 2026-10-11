"""Notes, tempo maps and melodies: values, clock scheduling and rendering."""

from __future__ import annotations

import copy
import struct

import pytest

from xnano_audio import (
    TerminalAudioEffect,
    TerminalMelody,
    TerminalNote,
    TerminalScheduledNote,
    TerminalSound,
    TerminalStreamingAudioPlayer,
    TerminalTempoMap,
    TerminalTimeSignature,
    note_to_hertz,
)


def scale(beats_per_minute: float = 120.0) -> TerminalMelody:
    melody = TerminalMelody(tempo_map=TerminalTempoMap(beats_per_minute))
    for pitch in ('C4', 'D4', 'E4', 'F4'):
        melody = melody.appended_note(pitch)
    return melody


# ----------------------------------------------------------------- notes


def test_note_reads_names_and_numbers():
    assert TerminalNote('C4').pitch == 60
    assert TerminalNote(61).name == 'C#4'
    assert TerminalNote('Db5').pitch == 73
    assert TerminalNote('A').pitch == 69
    assert TerminalNote('A4').frequency_hertz == pytest.approx(note_to_hertz('A4'))


def test_note_properties_and_builders_return_new_notes():
    note = TerminalNote('C4', start_beats=1.0, duration_beats=0.5, velocity=0.6)
    assert (note.start_beats, note.duration_beats, note.end_beats) == (1.0, 0.5, 1.5)
    assert note.velocity == pytest.approx(0.6)
    assert note.with_pitch('D4').pitch == 62
    assert note.with_start_beats(2).start_beats == 2.0
    assert note.with_duration_beats(3).end_beats == 4.0
    assert note.with_velocity(1.0).velocity == 1.0
    assert note.transposed(12).pitch == 72
    assert note.pitch == 60


def test_note_equality_hash_copy_and_repr():
    first = TerminalNote('C4', duration_beats=2)
    second = TerminalNote(60, duration_beats=2)
    assert first == second and hash(first) == hash(second)
    assert first != first.with_velocity(0.1)
    assert len({first, second}) == 1
    assert copy.deepcopy(first) == first
    assert repr(first).startswith("TerminalNote('C4'")


@pytest.mark.parametrize(
    'arguments',
    [
        {'pitch': 128},
        {'pitch': -1},
        {'pitch': 'H4'},
        {'pitch': 'C#10'},
        {'pitch': 60, 'start_beats': -1.0},
        {'pitch': 60, 'duration_beats': 0.0},
        {'pitch': 60, 'duration_beats': float('nan')},
        {'pitch': 60, 'velocity': 1.5},
        {'pitch': 60, 'start_beats': float('inf')},
    ],
)
def test_note_rejects_bad_values_with_a_recovery_hint(arguments):
    with pytest.raises(ValueError, match=r'\S{8}'):
        TerminalNote(**arguments)


def test_note_rejects_wrong_pitch_types():
    for bad in (True, 60.5, None, b'C4'):
        with pytest.raises(TypeError):
            TerminalNote(bad)
    with pytest.raises(ValueError, match='MIDI'):
        TerminalNote(120).transposed(20)


# --------------------------------------------------- time signature, tempo


def test_time_signature_counts_bars():
    waltz = TerminalTimeSignature(3, 4)
    assert (waltz.numerator, waltz.denominator, waltz.bar_length_beats) == (3, 4, 3.0)
    assert waltz.bar_and_beat(7.5) == (2, 1.5)
    assert TerminalTimeSignature(6, 8).bar_length_beats == 3.0
    assert TerminalTimeSignature() == TerminalTimeSignature(4, 4)
    assert hash(TerminalTimeSignature()) == hash(TerminalTimeSignature(4, 4))
    with pytest.raises(ValueError):
        TerminalTimeSignature(4, 3)
    with pytest.raises(ValueError):
        TerminalTimeSignature(0, 4)
    with pytest.raises(ValueError):
        waltz.bar_and_beat(-1.0)


def test_tempo_map_converts_beats_and_seconds_across_changes():
    constant = TerminalTempoMap(120)
    assert constant.beats_to_seconds(4) == pytest.approx(2.0)
    assert constant.seconds_to_beats(2.0) == pytest.approx(4.0)
    changed = constant.with_change(4, 60)
    assert changed.changes == [(4.0, 60.0)]
    assert changed.beats_to_seconds(6) == pytest.approx(4.0)
    assert changed.seconds_to_beats(4.0) == pytest.approx(6.0)
    assert changed.beats_per_minute_at(3.5) == 120.0
    assert changed.beats_per_minute_at(4.0) == 60.0
    assert constant.changes == []
    for beat in (0.0, 1.0, 4.0, 5.5, 9.0):
        assert changed.seconds_to_beats(changed.beats_to_seconds(beat)) == pytest.approx(
            beat
        )


def test_tempo_map_replaces_and_scales():
    map_ = TerminalTempoMap(100).with_change(0, 90).with_change(4, 60).with_change(4, 80)
    assert map_.initial_beats_per_minute == 90.0
    assert map_.changes == [(4.0, 80.0)]
    doubled = map_.scaled(2)
    assert doubled.initial_beats_per_minute == 180.0 and doubled.changes == [(4.0, 160.0)]
    assert map_ == TerminalTempoMap(90).with_change(4, 80)
    assert hash(map_) == hash(TerminalTempoMap(90).with_change(4, 80))
    for bad in (0, -5, 1001, float('nan')):
        with pytest.raises(ValueError):
            TerminalTempoMap(bad)
    with pytest.raises(ValueError):
        map_.scaled(0)
    with pytest.raises(ValueError):
        map_.beats_to_seconds(-1)


# --------------------------------------------------------------- melodies


def test_melody_builds_chords_rests_and_exposes_its_timeline():
    melody = (
        TerminalMelody()
        .appended_note('C4')
        .appended_chord(['E4', 'G4', 67 + 5], duration_beats=2, velocity=0.5)
        .appended_rest(1)
    )
    assert len(melody) == 4
    assert [note.start_beats for note in melody] == [0.0, 1.0, 1.0, 1.0]
    assert melody.length_beats == 4.0
    assert melody.duration_seconds == pytest.approx(2.0)
    assert melody.notes[1].pitch == 64
    assert melody.tempo_map == TerminalTempoMap(120)
    assert melody.time_signature == TerminalTimeSignature(4, 4)
    assert repr(melody).startswith('TerminalMelody(notes=4')


def test_melody_sorts_notes_and_validates_construction():
    late = TerminalNote('C4', start_beats=3)
    early = TerminalNote('D4', start_beats=1)
    melody = TerminalMelody([late, early], length_beats=8)
    assert [note.pitch for note in melody.notes] == [62, 60]
    assert melody.length_beats == 8.0
    assert melody.with_length_beats(2).length_beats == 4.0
    with pytest.raises(ValueError):
        TerminalMelody(length_beats=-1)
    with pytest.raises(ValueError, match='at most'):
        TerminalMelody([TerminalNote(60)] * 100_001)


def test_melody_transforms_never_change_the_original():
    melody = scale()
    assert [n.pitch for n in melody.transposed(2)] == [62, 64, 66, 67]
    assert melody.shifted(1).notes[0].start_beats == 1.0
    assert melody.stretched(2).length_beats == 8.0
    assert melody.stretched(2).duration_seconds == pytest.approx(
        melody.duration_seconds * 2
    )
    assert melody.repeated(3).length_beats == 12.0 and len(melody.repeated(3)) == 12
    joined = melody.followed_by(melody.transposed(12))
    assert joined.length_beats == 8.0 and joined.notes[4].pitch == 72
    layered = melody.layered_with(melody.transposed(7))
    assert len(layered) == 8 and layered.length_beats == 4.0
    assert [n.pitch for n in melody] == [60, 62, 64, 65]
    with pytest.raises(ValueError):
        melody.transposed(100)
    with pytest.raises(ValueError):
        melody.shifted(-1)
    with pytest.raises(ValueError):
        melody.repeated(0)
    with pytest.raises(ValueError):
        melody.stretched(0)


def test_melody_swaps_tempo_map_and_signature():
    melody = (
        scale(120)
        .with_tempo_map(TerminalTempoMap(60))
        .with_time_signature(TerminalTimeSignature(3, 4))
    )
    assert melody.duration_seconds == pytest.approx(4.0)
    assert melody.time_signature.numerator == 3
    assert melody.with_notes([TerminalNote('C5', start_beats=4)]).length_beats == 5.0


def test_window_queries_use_half_open_ranges():
    melody = scale()
    assert [n.pitch for n in melody.notes_between_beats(1, 3)] == [62, 64]
    assert [n.pitch for n in melody.notes_between_beats(0, 1)] == [60]
    assert [n.pitch for n in melody.notes_between_seconds(0.5, 1.0)] == [62]
    assert melody.notes_between_beats(5, 9) == []
    slow = melody.with_tempo_map(TerminalTempoMap(60))
    assert [n.pitch for n in slow.notes_between_seconds(1, 3)] == [62, 64]


# ------------------------------------------------------ clock scheduling


def test_consecutive_windows_hear_every_note_once():
    melody = scale()
    heard = []
    previous = 0.0
    for step in range(1, 12):
        current = step * 0.23
        heard += [item.note.pitch for item in melody.scheduled_between(previous, current)]
        previous = current
    assert heard == [60, 62, 64, 65]


def test_scheduled_notes_carry_clock_times():
    melody = scale().with_tempo_map(TerminalTempoMap(60).with_change(2, 120))
    items = melody.scheduled_between(10.0, 20.0, start_seconds=10.0)
    assert all(isinstance(item, TerminalScheduledNote) for item in items)
    assert [item.start_seconds for item in items] == pytest.approx(
        [10.0, 11.0, 12.0, 12.5]
    )
    assert [item.duration_seconds for item in items] == pytest.approx(
        [1.0, 1.0, 0.5, 0.5]
    )
    assert items[0].end_seconds == pytest.approx(11.0)
    assert items[0].note.pitch == 60 and items[0].iteration == 0
    assert repr(items[0]).startswith("TerminalScheduledNote('C4'")


def test_windows_before_the_start_or_after_the_end_are_empty():
    melody = scale()
    assert melody.scheduled_between(0.0, 5.0, start_seconds=6.0) == []
    assert melody.scheduled_between(3.0, 4.0) == []
    assert melody.scheduled_between(1.0, 1.0) == []
    assert TerminalMelody().scheduled_between(0.0, 10.0, should_loop=True) == []


def test_looping_restarts_at_the_melody_length():
    melody = scale()
    items = melody.scheduled_between(1.9, 4.1, should_loop=True)
    assert [(item.note.pitch, item.iteration) for item in items] == [
        (60, 1),
        (62, 1),
        (64, 1),
        (65, 1),
        (60, 2),
    ]
    assert [item.start_seconds for item in items] == pytest.approx(
        [2.0, 2.5, 3.0, 3.5, 4.0]
    )
    previous, heard = 0.0, []
    for step in range(1, 40):
        current = step * 0.17
        heard += [
            (item.iteration, item.note.pitch)
            for item in melody.scheduled_between(previous, current, should_loop=True)
        ]
        previous = current
    assert heard[:5] == [(0, 60), (0, 62), (0, 64), (0, 65), (1, 60)]
    assert len(heard) == len(set(heard))


def test_scheduling_rejects_backwards_or_non_finite_windows():
    melody = scale()
    with pytest.raises(ValueError, match='earlier'):
        melody.scheduled_between(2.0, 1.0)
    with pytest.raises(ValueError):
        melody.scheduled_between(0.0, float('inf'))
    with pytest.raises(ValueError):
        melody.scheduled_between(0.0, 1.0, start_seconds=float('nan'))


# -------------------------------------------------------------- rendering


def test_render_places_notes_at_the_tempo_and_is_deterministic():
    melody = TerminalMelody([TerminalNote('A4', start_beats=1, duration_beats=0.5)])
    sound = melody.render('sine', sample_rate=8000)
    assert isinstance(sound, TerminalSound) and sound.sample_rate == 8000
    samples = sound.samples()
    assert all(value == 0.0 for value in samples[:4000])
    assert max(abs(value) for value in samples[4000:]) > 0.05
    assert sound == melody.render('sine', sample_rate=8000)
    slower = melody.with_tempo_map(TerminalTempoMap(60)).render('sine', sample_rate=8000)
    assert all(value == 0.0 for value in slower.samples()[:8000])


def test_render_mixes_chords_without_clipping():
    chord = TerminalMelody().appended_chord(['C4', 'E4', 'G4', 'C5'], velocity=1.0)
    sound = chord.render('saw')
    assert 0.0 < sound.peak <= 0.95 + 1e-6


def test_render_windows_and_effects():
    melody = scale()
    window = melody.render('piano', sample_rate=8000, from_seconds=1.0, to_seconds=2.0)
    assert window.sample_rate == 8000
    assert max(abs(v) for v in window.samples()[:800]) > 0.0
    plain = melody.render('sine', sample_rate=8000, to_seconds=1.0)
    echoed = melody.render(
        'sine', sample_rate=8000, to_seconds=1.0, effects=[TerminalAudioEffect.reverb()]
    )
    assert len(echoed) > len(plain)


def test_render_reports_actionable_errors():
    melody = scale()
    with pytest.raises(ValueError, match='instrument_names'):
        melody.render('kazoo')
    with pytest.raises(ValueError, match='sample_rate'):
        melody.render('sine', sample_rate=10)
    with pytest.raises(ValueError, match='600'):
        melody.with_length_beats(5000).render('sine', to_seconds=2000.0)
    with pytest.raises(ValueError):
        melody.render('sine', from_seconds=float('nan'))


def test_rendered_melody_plays_through_the_null_backend():
    melody = scale()
    sound = melody.render('sine', to_seconds=1.0)
    with TerminalStreamingAudioPlayer(backend='null') as player:
        player.play_sound(sound)
        data = player.advance(4410)
    values = struct.unpack(f'<{len(data) // 4}f', data)
    assert max(abs(value) for value in values) > 0.01
