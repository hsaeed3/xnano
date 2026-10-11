"""
Hostile input.

Every call must either succeed or raise a clean Python error
(``ValueError`` / ``TypeError`` / ``OverflowError``). A panic, a signal, a
hang, or -- worst -- a "successful" result containing NaN (which would poison
a mixer) is a defect.
"""

from __future__ import annotations

import math
import random
import subprocess
import sys
import textwrap
from typing import Any, cast

import pytest

from xnano_audio import (
    TerminalAudioEffect,
    TerminalSound,
    instrument_names,
    note_to_hertz,
    render_note,
)

CLEAN = (ValueError, TypeError, OverflowError)
NAN, INF = float('nan'), float('inf')
JUNK = [
    None,
    True,
    '',
    'x',
    b'x',
    [],
    {},
    (),
    object(),
    1j,
    NAN,
    INF,
    -INF,
    2**70,
    -(2**70),
    -1,
    0,
]


def finite(sample: TerminalSound) -> bool:
    return all(math.isfinite(x) for x in sample.samples())


def attempt(call):
    """Run ``call``; return its value, or None when it raised cleanly."""
    try:
        return call()
    except CLEAN:
        return None


# ------------------------------------------------------------ never poisons


@pytest.mark.parametrize('velocity', [NAN, INF, -INF, 1e300, -1e300, 0.0, -0.0])
def test_extreme_velocities_never_yield_non_finite_audio(velocity):
    sample = attempt(lambda: render_note('piano', velocity=velocity))
    if sample is not None:
        assert finite(sample) and sample.peak <= 1.0


@pytest.mark.parametrize('value', [NAN, INF, -INF, 1e300, -1e300])
def test_effect_constructors_reject_non_finite_or_absurd_numbers(value):
    builders = [
        lambda: TerminalAudioEffect.distortion(drive=value),
        lambda: TerminalAudioEffect.low_pass(cutoff=value),
        lambda: TerminalAudioEffect.low_pass(cutoff=1000.0, resonance=value),
        lambda: TerminalAudioEffect.high_pass(cutoff=value),
        lambda: TerminalAudioEffect.delay(time_milliseconds=value),
        lambda: TerminalAudioEffect.delay(time_milliseconds=100.0, feedback=value),
        lambda: TerminalAudioEffect.delay(
            time_milliseconds=100.0, feedback=0.3, mix=value
        ),
        lambda: TerminalAudioEffect.reverb(room=value),
        lambda: TerminalAudioEffect.reverb(room=0.5, damping=value),
        lambda: TerminalAudioEffect.reverb(room=0.5, damping=0.5, mix=value),
        lambda: TerminalAudioEffect.tremolo(rate_hertz=value),
        lambda: TerminalAudioEffect.tremolo(rate_hertz=5.0, depth=value),
    ]
    for build in builders:
        with pytest.raises(ValueError):
            build()


@pytest.mark.parametrize('bad', [NAN, INF, -INF])
def test_custom_samples_must_be_finite(bad):
    with pytest.raises(ValueError):
        TerminalSound.from_samples([0.0, bad])


def test_float_bytes_with_nan_or_inf_are_rejected():
    import struct

    for bad in (NAN, INF, -INF):
        with pytest.raises(ValueError):
            TerminalSound.from_bytes(struct.pack('<2f', 0.0, bad))


# ------------------------------------------------------- argument fuzzing


@pytest.mark.parametrize('junk', JUNK, ids=repr)
def test_every_argument_position_rejects_junk_cleanly(junk):
    calls = [
        lambda: render_note(junk),
        lambda: render_note('piano', junk),
        lambda: render_note('piano', 'C4', duration_milliseconds=junk),
        lambda: render_note('piano', 'C4', duration_milliseconds=50, velocity=junk),
        lambda: render_note(
            'piano', 'C4', duration_milliseconds=50, velocity=0.5, effects=junk
        ),
        lambda: render_note(
            'piano',
            'C4',
            duration_milliseconds=50,
            velocity=0.5,
            effects=None,
            sample_rate=junk,
        ),
        lambda: note_to_hertz(junk),
        lambda: TerminalSound.from_samples(junk),
        lambda: TerminalSound.from_samples([0.0], sample_rate=junk),
        lambda: TerminalSound.from_bytes(junk),
        lambda: TerminalSound.from_bytes(b'\x00\x00\x00\x00', sample_rate=junk),
        lambda: TerminalAudioEffect.bit_crush(bits=junk),
        lambda: TerminalAudioEffect.bit_crush(bits=8, downsample=junk),
        lambda: TerminalAudioEffect.distortion(drive=junk),
        lambda: TerminalAudioEffect.low_pass(cutoff=junk),
        lambda: TerminalAudioEffect.delay(time_milliseconds=junk),
        lambda: TerminalAudioEffect.reverb(room=junk),
        lambda: TerminalAudioEffect.tremolo(rate_hertz=junk),
        lambda: render_note('piano', effects=junk),
        lambda: render_note('piano', effects=[junk]),
        lambda: render_note('piano').with_effects(junk),
        lambda: render_note('piano').with_effects([junk]),
    ]
    for call in calls:
        result = attempt(call)
        if isinstance(result, TerminalSound):
            assert finite(result)


def test_effect_lists_must_contain_only_effects():
    for bad in (
        'reverb',
        [TerminalAudioEffect.reverb(), 'reverb'],
        [render_note('kick')],
        5,
    ):
        with pytest.raises(TypeError):
            cast(Any, render_note)('piano', effects=bad)


def test_unknown_instrument_error_lists_the_valid_names():
    with pytest.raises(ValueError) as caught:
        render_note('kazoo')
    message = str(caught.value)
    assert 'kazoo' in message
    assert all(name in message for name in instrument_names())


def test_instrument_names_with_control_characters_are_reported_safely():
    with pytest.raises(ValueError) as caught:
        render_note('pi\x1b[31mano\n')
    assert (
        '\x1b' not in str(caught.value)
        and '\n' not in str(caught.value).split('choose')[0]
    )


@pytest.mark.parametrize(
    'note',
    [
        'C' * 10_000,
        '\x00',
        '\U0001f600',
        'c#' * 500,
        ' ',
        '-1',
        '1e999',
        'nan',
        'inf',
        '0x40',
    ],
)
def test_weird_note_strings_never_crash(note):
    attempt(lambda: note_to_hertz(note))
    attempt(lambda: render_note('piano', note, duration_milliseconds=20))


def test_huge_integers_for_every_numeric_parameter():
    for value in (2**31, 2**32, 2**63, 2**64, -(2**63)):
        attempt(lambda value=value: render_note('piano', duration_milliseconds=value))
        attempt(lambda value=value: render_note('piano', sample_rate=value))
        attempt(lambda value=value: render_note('piano', value))
        attempt(
            lambda value=value: TerminalAudioEffect.bit_crush(bits=value, downsample=1)
        )
        attempt(
            lambda value=value: TerminalAudioEffect.bit_crush(bits=8, downsample=value)
        )


def test_integer_parameters_reject_fractions_and_bools_are_not_special():
    with pytest.raises(TypeError):
        cast(Any, render_note)('piano', duration_milliseconds=10.5)
    with pytest.raises(TypeError):
        cast(Any, TerminalAudioEffect.bit_crush)(8.0, 1)


# ---------------------------------------------------------- from_bytes fuzz


def test_from_bytes_survives_random_data():
    rng = random.Random(1234)
    for _ in range(300):
        length = rng.randrange(0, 64)
        data = bytes(rng.randrange(256) for _ in range(length))
        sample = attempt(lambda data=data: TerminalSound.from_bytes(data))
        if sample is not None:
            assert finite(sample) and len(sample) == length // 4


def test_from_bytes_survives_mutated_valid_data():
    rng = random.Random(99)
    valid = bytearray(render_note('bell', 'C5', duration_milliseconds=30).to_bytes())
    for _ in range(300):
        data = bytearray(valid)
        for _ in range(rng.randrange(1, 6)):
            data[rng.randrange(len(data))] = rng.randrange(256)
        sample = attempt(lambda data=data: TerminalSound.from_bytes(bytes(data)))
        if sample is not None:
            assert finite(sample)


def test_bytes_round_trip_is_exact_for_every_instrument():
    for name in instrument_names():
        sample = render_note(name, 'C4', duration_milliseconds=30)
        assert (
            TerminalSound.from_bytes(sample.to_bytes(), sample_rate=sample.sample_rate)
            == sample
        )


# ------------------------------------------------------- property sweep


def test_random_valid_renders_are_finite_bounded_deterministic_and_composable():
    rng = random.Random(2024)
    names = instrument_names()
    builders = [
        lambda: TerminalAudioEffect.bit_crush(
            bits=rng.randrange(1, 17), downsample=rng.randrange(1, 40)
        ),
        lambda: TerminalAudioEffect.distortion(drive=rng.uniform(0.1, 20.0)),
        lambda: TerminalAudioEffect.low_pass(
            cutoff=rng.uniform(20.0, 18000.0), resonance=rng.uniform(0.1, 10.0)
        ),
        lambda: TerminalAudioEffect.high_pass(
            cutoff=rng.uniform(20.0, 18000.0), resonance=rng.uniform(0.1, 10.0)
        ),
        lambda: TerminalAudioEffect.delay(
            time_milliseconds=rng.uniform(1.0, 1000.0),
            feedback=rng.uniform(0.0, 0.95),
            mix=rng.uniform(0.0, 1.0),
        ),
        lambda: TerminalAudioEffect.reverb(
            room=rng.random(), damping=rng.random(), mix=rng.random()
        ),
        lambda: TerminalAudioEffect.tremolo(
            rate_hertz=rng.uniform(0.1, 30.0), depth=rng.random()
        ),
    ]
    for _ in range(120):
        effects = [rng.choice(builders)() for _ in range(rng.randrange(0, 4))]
        args = {
            'instrument': rng.choice(names),
            'note': rng.choice(
                [rng.randrange(24, 108), rng.uniform(40.0, 4000.0), 'F#3']
            ),
            'duration_milliseconds': rng.randrange(1, 400),
            'velocity': rng.random(),
            'sample_rate': rng.choice([8000, 22050, 44100, 48000, 96000]),
        }
        one = render_note(**args, effects=effects)
        two = render_note(**args, effects=effects)
        assert one == two, 'rendering is not deterministic'
        assert finite(one) and len(one) > 0
        assert one.peak <= 1.0, (args, effects, one.peak)
        assert (
            one == cast(Any, render_note)(**args).with_effects(effects) or effects == []
        )


def test_effect_chain_length_is_capped_everywhere():
    sample = render_note('kick', duration_milliseconds=10)
    for count, ok in ((32, True), (33, False)):
        chain = [TerminalAudioEffect.tremolo()] * count
        if ok:
            render_note('kick', effects=chain)
            sample.with_effects(chain)
        else:
            with pytest.raises(ValueError, match='at most 32'):
                render_note('kick', effects=chain)
            with pytest.raises(ValueError, match='at most 32'):
                sample.with_effects(chain)


def test_long_effect_chains_stay_bounded():
    chain = [
        TerminalAudioEffect.reverb(room=1.0, damping=0.0, mix=1.0),
        TerminalAudioEffect.delay(time_milliseconds=300.0, feedback=0.95, mix=1.0),
    ] * 6
    sample = render_note('piano', duration_milliseconds=200, effects=chain)
    assert finite(sample) and sample.peak <= 1.0
    assert sample.duration_milliseconds < 60_000, 'tails must be capped'


def test_extreme_but_valid_effect_settings():
    for effect in (
        TerminalAudioEffect.bit_crush(bits=1, downsample=1),
        TerminalAudioEffect.bit_crush(bits=16, downsample=1),
        TerminalAudioEffect.distortion(drive=0.1),
        TerminalAudioEffect.low_pass(cutoff=20.0, resonance=0.1),
        TerminalAudioEffect.high_pass(cutoff=19000.0, resonance=20.0),
        TerminalAudioEffect.delay(time_milliseconds=1.0, feedback=0.0, mix=0.0),
        TerminalAudioEffect.reverb(room=0.0, damping=0.0, mix=0.0),
        TerminalAudioEffect.reverb(room=1.0, damping=1.0, mix=1.0),
        TerminalAudioEffect.tremolo(rate_hertz=0.1, depth=1.0),
    ):
        sample = render_note('synth', 'A2', duration_milliseconds=80, effects=[effect])
        assert finite(sample) and sample.peak <= 1.0, effect


def test_minimum_and_maximum_sizes():
    shortest = render_note('kick', duration_milliseconds=1, sample_rate=8000)
    longest = render_note('pad', 'C2', duration_milliseconds=60_000, sample_rate=8000)
    assert len(shortest) > 0 and finite(shortest)
    assert finite(longest) and longest.duration_milliseconds >= 60_000


def test_single_sample_buffers_work_with_every_effect():
    one = TerminalSound.from_samples([0.5])
    for make in (
        TerminalAudioEffect.bit_crush,
        TerminalAudioEffect.distortion,
        TerminalAudioEffect.low_pass,
        TerminalAudioEffect.high_pass,
        TerminalAudioEffect.delay,
        TerminalAudioEffect.reverb,
        TerminalAudioEffect.tremolo,
    ):
        out = one.with_effects([make()])
        assert finite(out) and len(out) >= 1


def test_empty_samples_are_refused():
    with pytest.raises(ValueError):
        TerminalSound.from_samples([])
    with pytest.raises(ValueError):
        TerminalSound.from_bytes(b'')


# ------------------------------------------------- process-level safety


def test_concurrent_rendering_from_threads():
    import concurrent.futures

    def work(i):
        return render_note(
            instrument_names()[i % len(instrument_names())],
            48 + i % 24,
            duration_milliseconds=60,
        )

    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(work, range(64)))
    assert all(finite(r) for r in results)
    assert results[3] == work(3)


def test_deeply_nested_and_huge_argument_lists_do_not_crash_the_interpreter():
    script = textwrap.dedent(
        """
        from xnano_audio import *
        try:
            render_note("piano", effects=[TerminalAudioEffect.reverb()] * 20000)
            print("NOT REFUSED")
        except Exception as error:
            print("RAISED", type(error).__name__)
        else:
            print("OK")
        try:
            TerminalSound.from_samples([0.0] * 5_000_000)
        except Exception as error:
            print("RAISED", type(error).__name__)
        else:
            print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-400:]
    assert result.stdout.split()[:2] == ['RAISED', 'ValueError'], (
        'long chains must be refused'
    )
    assert 'NOT REFUSED' not in result.stdout
