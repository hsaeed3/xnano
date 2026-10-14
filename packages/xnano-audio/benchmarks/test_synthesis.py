"""
Benchmarks for xnano-audio synthesis. None of them needs an audio device.

Every benchmark checks the sound it produced. Durations are the interesting figure: a
benchmark that renders ``N`` seconds of audio in ``T`` seconds runs ``N / T`` times faster
than real time, which is what decides whether synthesis can keep up with playback.
"""

from __future__ import annotations

import pytest

from xnano_audio import (
    TerminalAudioEffect,
    TerminalMelody,
    TerminalNote,
    TerminalSound,
    TerminalTempoMap,
    instrument_names,
    render_note,
)

SAMPLE_RATE = 44100


@pytest.fixture(scope='module')
def held_note() -> TerminalSound:
    """A synth note held for one second (its release is added on top)."""
    sound = render_note('synth', 'A3', duration_milliseconds=1000)
    assert sound.duration_milliseconds >= 1000
    return sound


@pytest.fixture(scope='module')
def melody() -> TerminalMelody:
    """Thirty-two notes over eight bars, with a chord on every beat of the second bar."""
    notes = [
        TerminalNote(
            pitch=48 + (index * 5) % 24, start_beats=index * 0.5, duration_beats=0.5
        )
        for index in range(32)
    ]
    notes += [
        TerminalNote(pitch=pitch, start_beats=4.0 + beat, duration_beats=1.0)
        for beat in range(4)
        for pitch in (60, 64, 67)
    ]
    return TerminalMelody(notes, tempo_map=TerminalTempoMap(140.0))


def test_render_piano_note(benchmark):
    sound = benchmark(render_note, 'piano', 'C4', duration_milliseconds=500)
    assert sound.duration_milliseconds >= 500
    assert 0.0 < sound.peak <= 1.0


def test_render_bell_note(benchmark):
    sound = benchmark(render_note, 'bell', 'C6', duration_milliseconds=200)
    assert sound.peak > 0.0


def test_render_kick(benchmark):
    sound = benchmark(render_note, 'kick')
    assert sound.peak > 0.0


def test_render_long_note(benchmark):
    sound = benchmark(render_note, 'pad', 'C3', duration_milliseconds=8000)
    assert sound.duration_milliseconds >= 8000


def test_render_at_48_kilohertz(benchmark):
    sound = benchmark(
        render_note, 'piano', 'C4', duration_milliseconds=500, sample_rate=48000
    )
    assert sound.sample_rate == 48000


@pytest.mark.parametrize('instrument', instrument_names())
def test_render_every_instrument(benchmark, instrument):
    sound = benchmark(render_note, instrument, 'C4', duration_milliseconds=300)
    assert sound.duration_milliseconds > 0
    assert sound.peak > 0.0


def test_low_pass(benchmark, held_note):
    filtered = benchmark(
        held_note.with_effects, [TerminalAudioEffect.low_pass(cutoff=800.0)]
    )
    assert filtered.duration_milliseconds == held_note.duration_milliseconds
    assert filtered.root_mean_square < held_note.root_mean_square


def test_reverb(benchmark, held_note):
    reverberant = benchmark(held_note.with_effects, [TerminalAudioEffect.reverb()])
    assert reverberant.duration_milliseconds >= held_note.duration_milliseconds


def test_delay(benchmark, held_note):
    delayed = benchmark(held_note.with_effects, [TerminalAudioEffect.delay()])
    assert delayed.duration_milliseconds > held_note.duration_milliseconds


def test_effect_chain(benchmark, held_note):
    effects = [
        TerminalAudioEffect.distortion(drive=2.0),
        TerminalAudioEffect.low_pass(cutoff=1500.0),
        TerminalAudioEffect.delay(),
        TerminalAudioEffect.reverb(),
    ]
    processed = benchmark(held_note.with_effects, effects)
    assert processed.peak <= 1.0


def test_melody_render(benchmark, melody):
    sound = benchmark(melody.render, 'piano')
    assert sound.duration_milliseconds >= melody.duration_seconds * 1000
    assert sound.peak <= 1.0


def test_melody_render_with_effects(benchmark, melody):
    effects = [TerminalAudioEffect.reverb()]
    sound = benchmark(lambda: melody.render('piano', effects=effects))
    assert sound.peak <= 1.0


def test_melody_edit_and_schedule(benchmark, melody):
    """Pure bookkeeping: transposing, repeating and scheduling a melody."""

    def edit() -> int:
        edited = melody.transposed(2).repeated(4).stretched(0.5)
        return len(edited.scheduled_between(0.0, 30.0))

    assert benchmark(edit) > 0


def test_envelope(benchmark, held_note):
    envelope = benchmark(held_note.envelope, 200)
    assert len(envelope) == 200


def test_samples_round_trip(benchmark, held_note):
    def round_trip() -> TerminalSound:
        return TerminalSound.from_samples(
            held_note.samples(), sample_rate=held_note.sample_rate
        )

    sound = benchmark(round_trip)
    assert sound.duration_milliseconds == held_note.duration_milliseconds


def test_bytes_round_trip(benchmark, held_note):
    def round_trip() -> TerminalSound:
        return TerminalSound.from_bytes(
            held_note.to_bytes(), sample_rate=held_note.sample_rate
        )

    sound = benchmark(round_trip)
    assert sound.duration_milliseconds == held_note.duration_milliseconds
