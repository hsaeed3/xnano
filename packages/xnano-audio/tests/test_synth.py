"""Device-free tests: instruments, notes and effects render to plain samples."""

import math
from typing import Any, cast

import pytest

from xnano_audio import (
    TerminalAudioEffect,
    TerminalSound,
    instrument_names,
    is_percussive,
    note_to_hertz,
    render_note,
)

PERCUSSIVE = ('kick', 'snare', 'hihat', 'open_hat', 'clap', 'tom', 'cowbell')


def estimate_hz(sample: TerminalSound, expected: float, start_ms: int = 120) -> float:
    """Pitch from autocorrelation, searched near the expected period."""
    rate, window = sample.sample_rate, 4096
    start = int(rate * start_ms / 1000)
    data = sample.samples()[start : start + window]
    assert len(data) == window
    mean = sum(data) / window
    data = [v - mean for v in data]
    period = rate / expected
    lags = range(int(period * 0.97), int(period * 1.03) + 2)
    corr = {
        lag: sum(data[i] * data[i + lag] for i in range(window - lag - 1))
        for lag in range(lags.start - 1, lags.stop + 1)
    }
    best = max(lags, key=corr.__getitem__)
    c0, c1, c2 = corr[best - 1], corr[best], corr[best + 1]
    frac = 0.5 * (c0 - c2) / (c0 - 2 * c1 + c2)
    return rate / (best + frac)


def cents(actual: float, expected: float) -> float:
    return 1200 * math.log2(actual / expected)


# ----------------------------------------------------------------- catalog


def test_catalog_has_the_core_families():
    names = instrument_names()
    for expected in ('piano', 'guitar', 'synth', 'bass', 'bell', *PERCUSSIVE):
        assert expected in names
    assert len(names) == len(set(names))


def test_percussive_flags():
    for name in instrument_names():
        assert is_percussive(name) == (name in PERCUSSIVE)
    with pytest.raises(ValueError):
        is_percussive('kazoo')


@pytest.mark.parametrize('instrument', instrument_names())
def test_every_instrument_renders_a_sane_sound(instrument):
    sample = render_note(instrument, 'A3', duration_milliseconds=300)
    data = sample.samples()
    assert len(data) == len(sample) > 0
    assert all(math.isfinite(v) for v in data)
    assert 0.02 < sample.peak <= 0.951
    assert 0.0 < sample.root_mean_square < sample.peak
    assert sample.duration_milliseconds > 0
    # the end is faded, so sounds never stop with a click
    assert abs(data[-1]) < 0.05


@pytest.mark.parametrize('instrument', instrument_names())
def test_rendering_is_deterministic(instrument):
    first = render_note(instrument, 'D3', duration_milliseconds=200, velocity=0.7)
    second = render_note(instrument, 'D3', duration_milliseconds=200, velocity=0.7)
    assert first.to_bytes() == second.to_bytes()


def test_instrument_name_is_forgiving_and_errors_are_helpful():
    assert (
        render_note('Electric Piano', 'C4', duration_milliseconds=100).to_bytes()
        == render_note('electric_piano', 'C4', duration_milliseconds=100).to_bytes()
    )
    with pytest.raises(ValueError, match='piano') as info:
        render_note('kazoo')
    assert 'choose one of' in str(info.value)


# ------------------------------------------------------------------- notes


@pytest.mark.parametrize(
    ('note', 'hz'),
    [
        ('A4', 440.0),
        ('C4', 261.626),
        ('c#3', 138.591),
        ('Db5', 554.365),
        ('A', 440.0),
        ('69', 440.0),
        ('440hz', 440.0),
        (69, 440.0),
        (60, 261.626),
        (123.5, 123.5),
    ],
)
def test_note_to_hertz(note, hz):
    assert note_to_hertz(note) == pytest.approx(hz, rel=1e-3)


def test_enharmonic_names_agree():
    assert note_to_hertz('C#5') == pytest.approx(note_to_hertz('Db5'))


@pytest.mark.parametrize(
    'bad', ['H4', '', 'C#x', 'C10', 'B#9', '128', 128, 'hz', 400, 2.0]
)
def test_bad_notes_raise_value_error(bad):
    with pytest.raises(ValueError):
        note_to_hertz(bad)


@pytest.mark.parametrize('bad', [True, None, [60], object()])
def test_wrong_note_types_raise_type_error(bad):
    with pytest.raises(TypeError):
        note_to_hertz(bad)


@pytest.mark.parametrize(
    ('instrument', 'note'),
    [
        ('guitar', 'A2'),
        ('guitar', 'E4'),
        ('electric_guitar', 'A3'),
        ('pluck', 'A3'),
        ('pluck', 'A4'),
        ('sine', 'A3'),
        ('saw', 'A3'),
        ('electric_piano', 'A3'),
    ],
)
def test_pitched_instruments_are_in_tune(instrument, note):
    sample = render_note(instrument, note, duration_milliseconds=600)
    assert abs(cents(estimate_hz(sample, note_to_hertz(note)), note_to_hertz(note))) < 15


def test_bell_fundamental_is_the_note():
    # the bell is inharmonic, so look for its strongest low component instead
    note, rate = 'A3', 44100
    expected = note_to_hertz(note)
    data = render_note('bell', note, duration_milliseconds=400).samples()[2000:10000]

    def power(hz):
        w = 2 * math.pi * hz / rate
        coeff, s1, s2 = 2 * math.cos(w), 0.0, 0.0
        for v in data:
            s1, s2 = v + coeff * s1 - s2, s1
        return s2 * s2 + s1 * s1 - coeff * s1 * s2

    strongest = max((expected * (0.9 + 0.01 * i) for i in range(21)), key=power)
    assert strongest == pytest.approx(expected, rel=0.005)


# --------------------------------------------------------------- behaviour


def test_velocity_changes_loudness_and_brightness():
    soft, hard = (
        render_note('piano', 'C4', duration_milliseconds=300, velocity=0.2),
        render_note('piano', 'C4', duration_milliseconds=300, velocity=1.0),
    )
    assert hard.root_mean_square > soft.root_mean_square * 1.5
    assert hard.to_bytes() != soft.to_bytes()


@pytest.mark.parametrize('instrument', instrument_names())
def test_every_instrument_responds_to_velocity(instrument):
    note = 'A2' if instrument == 'tom' else 'A3'
    soft = render_note(instrument, note, duration_milliseconds=300, velocity=0.2)
    hard = render_note(instrument, note, duration_milliseconds=300, velocity=1.0)
    assert hard.root_mean_square > soft.root_mean_square * 2


def test_velocity_is_clamped():
    assert (
        render_note('sine', 'A3', duration_milliseconds=100, velocity=5.0).to_bytes()
        == render_note('sine', 'A3', duration_milliseconds=100, velocity=1.0).to_bytes()
    )


def test_duration_sets_length_of_pitched_but_not_percussive_notes():
    short, long = (
        render_note('synth', 'A3', duration_milliseconds=100),
        render_note('synth', 'A3', duration_milliseconds=900),
    )
    assert long.duration_milliseconds > short.duration_milliseconds + 700
    for drum in PERCUSSIVE:
        assert len(render_note(drum, 'A2', duration_milliseconds=50)) == len(
            render_note(drum, 'A2', duration_milliseconds=2000)
        )


def test_release_tail_extends_beyond_the_gate():
    assert (
        render_note('piano', 'C4', duration_milliseconds=300).duration_milliseconds > 300
    )
    assert (
        render_note('bell', 'C5', duration_milliseconds=100).duration_milliseconds > 1000
    )


def test_sample_rate_option():
    low = render_note('sine', 'A3', duration_milliseconds=200, sample_rate=22050)
    assert low.sample_rate == 22050
    assert low.duration_milliseconds == pytest.approx(
        render_note('sine', 'A3', duration_milliseconds=200).duration_milliseconds,
        rel=0.01,
    )


@pytest.mark.parametrize(
    'kwargs',
    [
        {'duration_milliseconds': 0},
        {'duration_milliseconds': 60_001},
        {'sample_rate': 100},
        {'sample_rate': 500_000},
    ],
)
def test_out_of_range_arguments(kwargs):
    with pytest.raises(ValueError):
        render_note('sine', 'A3', **kwargs)


def test_sample_views():
    sample = render_note('sine', 'A3', duration_milliseconds=100)
    assert len(sample.to_bytes()) == 4 * len(sample)
    assert len(sample.samples()) == len(sample)
    assert 'TerminalSound' in repr(sample)


# ----------------------------------------------------------------- effects


def sine() -> TerminalSound:
    return render_note('sine', 'A3', duration_milliseconds=300)


def test_lowpass_removes_highs_and_highpass_removes_lows():
    base = sine()
    assert (
        base.with_effects([TerminalAudioEffect.high_pass(cutoff=2000)]).root_mean_square
        < base.root_mean_square / 10
    )
    hissy = render_note('hihat', velocity=1.0)
    assert (
        hissy.with_effects([TerminalAudioEffect.low_pass(cutoff=300)]).root_mean_square
        < hissy.root_mean_square / 5
    )


def test_bitcrush_limits_levels_and_holds_samples():
    crushed = sine().with_effects([TerminalAudioEffect.bit_crush(bits=3, downsample=1)])
    assert len({round(v, 5) for v in crushed.samples()}) <= 8
    held = (
        sine()
        .with_effects([TerminalAudioEffect.bit_crush(bits=16, downsample=8)])
        .samples()
    )
    assert all(held[i] == held[i + 1] for i in range(0, 400, 8))


def test_distortion_adds_energy():
    quiet = render_note('sine', 'A3', duration_milliseconds=300, velocity=0.3)
    assert (
        quiet.with_effects([TerminalAudioEffect.distortion(drive=8.0)]).root_mean_square
        > quiet.root_mean_square * 1.5
    )


def test_delay_and_reverb_extend_the_sound():
    base = sine()
    assert (
        base.with_effects(
            [TerminalAudioEffect.delay(time_milliseconds=200, feedback=0.5)]
        ).duration_milliseconds
        > base.duration_milliseconds + 1000
    )
    assert (
        base.with_effects([TerminalAudioEffect.reverb(room=0.8)]).duration_milliseconds
        > base.duration_milliseconds + 1500
    )
    # a dry reverb or zero-feedback delay still never shortens the sound
    assert (
        base.with_effects(
            [TerminalAudioEffect.reverb(room=0.0, mix=0.0)]
        ).duration_milliseconds
        >= base.duration_milliseconds
    )


def test_tremolo_modulates_amplitude():
    steady = render_note('sine', 'A3', duration_milliseconds=1000)
    wobbled = steady.with_effects(
        [TerminalAudioEffect.tremolo(rate_hertz=4.0, depth=1.0)]
    )
    data = wobbled.samples()
    assert min(abs(v) for v in data[8000:30000]) < 0.1 * steady.peak
    assert wobbled.peak > 0.8 * steady.peak


def test_effects_are_ordered_reusable_and_do_not_mutate():
    base = sine()
    before = base.to_bytes()
    chain = [TerminalAudioEffect.distortion(drive=3.0), TerminalAudioEffect.reverb()]
    first, second = base.with_effects(chain), base.with_effects(chain)
    assert first.to_bytes() == second.to_bytes()
    assert base.to_bytes() == before
    reversed_chain = base.with_effects(chain[::-1])
    assert reversed_chain.to_bytes() != first.to_bytes()


def test_effects_in_render_note_match_with_effects():
    chain = [
        TerminalAudioEffect.bit_crush(bits=6, downsample=2),
        TerminalAudioEffect.low_pass(cutoff=3000),
    ]
    direct = render_note('synth', 'C3', duration_milliseconds=200, effects=chain)
    later = render_note('synth', 'C3', duration_milliseconds=200).with_effects(chain)
    assert direct.to_bytes() == later.to_bytes()


def test_effect_output_never_clips():
    loud = render_note('kick', velocity=1.0)
    for effect in (
        TerminalAudioEffect.distortion(drive=50),
        TerminalAudioEffect.reverb(room=1.0, mix=1.0),
        TerminalAudioEffect.delay(time_milliseconds=50, feedback=0.9, mix=1.0),
    ):
        assert loud.with_effects([effect]).peak <= 0.981


def test_effect_identity_and_names():
    assert TerminalAudioEffect.reverb(room=0.3) == TerminalAudioEffect.reverb(room=0.3)
    assert TerminalAudioEffect.reverb(room=0.3) != TerminalAudioEffect.reverb(room=0.4)
    assert [
        e.name for e in (TerminalAudioEffect.bit_crush(), TerminalAudioEffect.tremolo())
    ] == [
        'bit_crush',
        'tremolo',
    ]
    assert 'TerminalAudioEffect' in repr(TerminalAudioEffect.delay())


@pytest.mark.parametrize(
    'build',
    [
        lambda: TerminalAudioEffect.bit_crush(bits=0),
        lambda: TerminalAudioEffect.bit_crush(bits=17),
        lambda: TerminalAudioEffect.bit_crush(bits=8, downsample=0),
        lambda: TerminalAudioEffect.distortion(drive=0.0),
        lambda: TerminalAudioEffect.low_pass(cutoff=5),
        lambda: TerminalAudioEffect.high_pass(cutoff=30_000),
        lambda: TerminalAudioEffect.low_pass(cutoff=1000, resonance=0.0),
        lambda: TerminalAudioEffect.delay(time_milliseconds=0),
        lambda: TerminalAudioEffect.delay(time_milliseconds=100, feedback=1.0),
        lambda: TerminalAudioEffect.delay(time_milliseconds=100, mix=1.5),
        lambda: TerminalAudioEffect.reverb(room=2.0),
        lambda: TerminalAudioEffect.reverb(damping=-0.1),
        lambda: TerminalAudioEffect.tremolo(rate_hertz=0.0),
        lambda: TerminalAudioEffect.tremolo(depth=1.1),
    ],
)
def test_effect_arguments_are_validated(build):
    with pytest.raises(ValueError):
        build()


# ---------------------------------------------------------------- loudness


def test_instruments_are_loudness_matched():
    """Gains in the instrument table keep every sound at a similar level."""
    levels = {}
    for name in instrument_names():
        note = 'A2' if name == 'tom' else 'A3'
        levels[name] = render_note(
            name, note, duration_milliseconds=500, velocity=0.8
        ).root_mean_square
        # nothing may clip at full velocity, and nothing may vanish
        assert (
            render_note(name, note, duration_milliseconds=500, velocity=1.0).peak <= 0.951
        ), name
        assert levels[name] > 0.02, name
    matched = [n for n, rms in levels.items() if 0.09 <= rms <= 0.15]
    # transient-heavy sounds (hats, cowbell, plucks) are capped by their
    # peaks instead, but the large majority sit at the common level
    assert len(matched) >= 17, levels
    assert max(levels.values()) < 0.15


# ---------------------------------------------------- custom samples (DIY)


def test_sample_from_samples_round_trips_and_plays_through_effects():
    wave = [math.sin(2 * math.pi * 330 * i / 44100) * 0.5 for i in range(4410)]
    sample = TerminalSound.from_samples(wave)
    assert len(sample) == 4410
    assert sample.sample_rate == 44100
    assert sample.peak == pytest.approx(0.5, abs=1e-3)
    assert estimate_hz(
        TerminalSound.from_samples(wave * 2), 330.0, start_ms=0
    ) == pytest.approx(330, rel=0.01)
    assert (
        sample.with_effects([TerminalAudioEffect.reverb()]).duration_milliseconds
        > sample.duration_milliseconds
    )


def test_sample_bytes_round_trip():
    original = render_note('marimba', 'C5', duration_milliseconds=200)
    rebuilt = TerminalSound.from_bytes(
        original.to_bytes(), sample_rate=original.sample_rate
    )
    assert rebuilt.to_bytes() == original.to_bytes()
    assert rebuilt.sample_rate == original.sample_rate


@pytest.mark.parametrize(
    'build',
    [
        lambda: TerminalSound.from_samples([]),
        lambda: TerminalSound.from_samples([0.0, float('nan')]),
        lambda: TerminalSound.from_samples([0.0, float('inf')]),
        lambda: TerminalSound.from_samples([0.0], sample_rate=100),
        lambda: TerminalSound.from_bytes(b'\x00\x00\x00'),
        lambda: TerminalSound.from_bytes(b''),
    ],
)
def test_custom_samples_are_validated(build):
    with pytest.raises(ValueError):
        build()


# --------------------------------------------------------------------- mix


def tone(value: float, samples: int, sample_rate: int = 44100) -> TerminalSound:
    return TerminalSound.from_samples([value] * samples, sample_rate=sample_rate)


def test_mix_places_each_layer_at_its_offset():
    rate = 8000
    mixed = TerminalSound.mix(
        [(tone(0.25, 4000, rate), 0.0, 1.0), (tone(0.5, 2000, rate), 0.25, 1.0)],
        duration_seconds=1.0,
        sample_rate=rate,
    )
    data = mixed.samples()
    assert len(data) == rate and mixed.sample_rate == rate
    assert data[0] == pytest.approx(0.25) and data[1999] == pytest.approx(0.25)
    assert data[2000] == pytest.approx(0.75) and data[3999] == pytest.approx(0.75)
    assert data[4000] == 0.0 and data[-1] == 0.0


def test_mix_applies_gain_and_limits_the_sum():
    rate = 8000
    loud = tone(0.9, 800, rate)
    mixed = TerminalSound.mix(
        [(loud, 0.0, 1.0), (loud, 0.0, 1.0), (loud, 0.0, 0.5)],
        duration_seconds=0.1,
        sample_rate=rate,
    )
    assert max(mixed.samples()) == 1.0 and mixed.peak == 1.0
    negative = TerminalSound.mix(
        [(tone(-0.9, 800, rate), 0.0, 2.0)], duration_seconds=0.1, sample_rate=rate
    )
    assert min(negative.samples()) == -1.0
    silent = TerminalSound.mix([(loud, 0.0, 0.0)], duration_seconds=0.1, sample_rate=rate)
    assert silent.peak == 0.0


def test_mix_cuts_layers_at_the_edges_of_the_window():
    rate = 8000
    ramp = TerminalSound.from_samples(
        [index / 8000 for index in range(8000)], sample_rate=rate
    )
    window = TerminalSound.mix(
        [(ramp, 0.0, 1.0)], duration_seconds=0.25, start_seconds=0.5, sample_rate=rate
    )
    data = window.samples()
    assert len(data) == 2000
    assert data[0] == pytest.approx(0.5) and data[-1] == pytest.approx(5999 / 8000)
    early = TerminalSound.mix(
        [(ramp, 0.5, 1.0)], duration_seconds=0.25, start_seconds=0.0, sample_rate=rate
    )
    assert early.peak == 0.0, 'a layer that starts after the window adds nothing'
    ended = TerminalSound.mix(
        [(ramp, -2.0, 1.0)], duration_seconds=0.25, start_seconds=0.0, sample_rate=rate
    )
    assert ended.peak == 0.0, 'a layer that ended before the window adds nothing'
    running = TerminalSound.mix(
        [(ramp, -0.5, 1.0)], duration_seconds=0.25, start_seconds=0.0, sample_rate=rate
    )
    assert running.samples()[0] == pytest.approx(0.5)


def test_mix_drops_layers_that_land_far_outside_the_window():
    rate = 8000
    note = TerminalSound.from_samples([0.5] * 800, sample_rate=rate)
    far_before = TerminalSound.mix(
        [(note, -1e15, 1.0)], duration_seconds=0.25, sample_rate=rate
    )
    assert len(far_before) == 2000 and far_before.peak == 0.0
    far_after = TerminalSound.mix(
        [(note, 0.0, 1.0)], duration_seconds=0.25, start_seconds=1e300, sample_rate=rate
    )
    assert far_after.peak == 0.0
    far_ahead = TerminalSound.mix(
        [(note, 1e15, 1.0)], duration_seconds=0.25, sample_rate=rate
    )
    assert far_ahead.peak == 0.0


def test_mix_of_no_layers_is_silence_of_the_requested_length():
    silence = TerminalSound.mix([], duration_seconds=0.5)
    assert len(silence) == 22050 and silence.peak == 0.0
    assert silence.sample_rate == 44100


def test_mix_matches_a_note_rendered_alone():
    note = render_note('piano', 'C4', duration_milliseconds=300)
    alone = TerminalSound.mix(
        [(note, 0.0, 1.0)], duration_seconds=note.duration_milliseconds / 1000
    )
    assert alone.samples() == pytest.approx(note.samples())


@pytest.mark.parametrize(
    ('layers', 'keywords', 'message'),
    [
        ([], {'duration_seconds': 0.0}, 'duration_seconds'),
        ([], {'duration_seconds': -1.0}, 'duration_seconds'),
        ([], {'duration_seconds': float('nan')}, 'duration_seconds'),
        ([], {'duration_seconds': 4000.0}, 'at most 3600'),
        ([], {'duration_seconds': 1e-9}, 'shorter than one sample'),
        ([], {'duration_seconds': 1.0, 'sample_rate': 100}, 'sample_rate'),
        ([], {'duration_seconds': 1.0, 'start_seconds': float('inf')}, 'start_seconds'),
        ([(tone(0.1, 10, 8000), 0.0, 1.0)], {'duration_seconds': 1.0}, 'Hz'),
        (
            [(tone(0.1, 10), float('nan'), 1.0)],
            {'duration_seconds': 1.0},
            'offset_seconds',
        ),
        ([(tone(0.1, 10), 0.0, -1.0)], {'duration_seconds': 1.0}, 'gain'),
        ([(tone(0.1, 10), 0.0, float('inf'))], {'duration_seconds': 1.0}, 'gain'),
    ],
)
def test_mix_refuses_bad_arguments_and_says_what_to_pass(layers, keywords, message):
    with pytest.raises(ValueError, match=message):
        TerminalSound.mix(layers, **keywords)


def test_mix_takes_its_window_by_keyword_and_layers_as_tuples():
    with pytest.raises(TypeError):
        cast(Any, TerminalSound.mix)([], 1.0)
    with pytest.raises(
        TypeError, match=r'layer 0 is a TerminalSound on its own.*\(sound, 0\.0, 1\.0\)'
    ):
        TerminalSound.mix([tone(0.1, 10)], duration_seconds=1.0)  # type: ignore[list-item]
    with pytest.raises(ValueError, match=r'layer 0 has 2 values.*offset_seconds, gain'):
        TerminalSound.mix([(tone(0.1, 10), 0.0)], duration_seconds=1.0)  # type: ignore[list-item]
    with pytest.raises(TypeError, match=r'first value of layer 0 is a str'):
        TerminalSound.mix([('x', 0.0, 1.0)], duration_seconds=1.0)  # type: ignore[list-item]
    with pytest.raises(TypeError, match=r'offset_seconds of layer 0 must be a number'):
        TerminalSound.mix([(tone(0.1, 10), 'soon', 1.0)], duration_seconds=1.0)  # type: ignore[list-item]
    with pytest.raises(TypeError, match=r'sequence of \(sound, offset_seconds, gain\)'):
        TerminalSound.mix(5, duration_seconds=1.0)  # type: ignore[arg-type]
