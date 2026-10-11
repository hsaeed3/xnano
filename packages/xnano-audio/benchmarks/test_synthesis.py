"""
Benchmarks for xnano-audio synthesis. None of them needs an audio device.
"""

from __future__ import annotations

import pytest

from xnano_audio import TerminalAudioEffect, TerminalSound, render_note


@pytest.fixture(scope='module')
def one_second() -> TerminalSound:
    return render_note('synth', 'A3', duration_milliseconds=900)


def test_render_piano_note(benchmark):
    benchmark(render_note, 'piano', 'C4', duration_milliseconds=500)


def test_render_bell_note(benchmark):
    benchmark(render_note, 'bell', 'C6', duration_milliseconds=200)


def test_render_kick(benchmark):
    benchmark(render_note, 'kick')


def test_low_pass(benchmark, one_second):
    effects = [TerminalAudioEffect.low_pass(cutoff=800.0)]
    benchmark(one_second.with_effects, effects)


def test_reverb(benchmark, one_second):
    effects = [TerminalAudioEffect.reverb()]
    benchmark(one_second.with_effects, effects)


def test_effect_chain(benchmark, one_second):
    effects = [
        TerminalAudioEffect.distortion(drive=2.0),
        TerminalAudioEffect.low_pass(cutoff=1500.0),
        TerminalAudioEffect.delay(),
        TerminalAudioEffect.reverb(),
    ]
    benchmark(one_second.with_effects, effects)


def test_envelope(benchmark, one_second):
    benchmark(one_second.envelope, 200)
