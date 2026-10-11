"""
Value semantics and text output.

``TerminalAudioEffect`` and ``TerminalSound`` are immutable values: equal by content,
hashable, copyable. ``repr`` must be clean Python text -- no Rust debug
syntax, no control characters -- and an effect's repr rebuilds it.
"""

from __future__ import annotations

import copy

import pytest

from xnano_audio import TerminalAudioEffect, TerminalSound, render_note

EFFECTS = {
    'bit_crush': lambda: TerminalAudioEffect.bit_crush(bits=5, downsample=3),
    'distortion': lambda: TerminalAudioEffect.distortion(drive=2.5),
    'low_pass': lambda: TerminalAudioEffect.low_pass(cutoff=900.0, resonance=1.5),
    'high_pass': lambda: TerminalAudioEffect.high_pass(cutoff=300.0, resonance=0.9),
    'delay': lambda: TerminalAudioEffect.delay(
        time_milliseconds=120.0, feedback=0.3, mix=0.4
    ),
    'reverb': lambda: TerminalAudioEffect.reverb(room=0.7, damping=0.2, mix=0.3),
    'tremolo': lambda: TerminalAudioEffect.tremolo(rate_hertz=7.0, depth=0.6),
}
#: a different instance of the same effect kind
OTHER = {
    'bit_crush': lambda: TerminalAudioEffect.bit_crush(bits=6, downsample=3),
    'distortion': lambda: TerminalAudioEffect.distortion(drive=2.6),
    'low_pass': lambda: TerminalAudioEffect.low_pass(cutoff=901.0, resonance=1.5),
    'high_pass': lambda: TerminalAudioEffect.high_pass(cutoff=300.0, resonance=0.8),
    'delay': lambda: TerminalAudioEffect.delay(
        time_milliseconds=120.0, feedback=0.3, mix=0.41
    ),
    'reverb': lambda: TerminalAudioEffect.reverb(room=0.7, damping=0.2, mix=0.31),
    'tremolo': lambda: TerminalAudioEffect.tremolo(rate_hertz=7.0, depth=0.61),
}
BAD_TEXT = ('{', '}', '::', 'Some(', 'None(', ' at 0x', '\x1b', '\n', '\x00')


@pytest.mark.parametrize('name', EFFECTS)
class TestEffect:
    def test_equal_by_value_not_identity(self, name):
        first, second = EFFECTS[name](), EFFECTS[name]()
        assert first is not second and first == second
        assert first == second

    def test_different_arguments_are_unequal(self, name):
        assert EFFECTS[name]() != OTHER[name]()

    def test_hash_agrees_with_equality(self, name):
        first, second = EFFECTS[name](), EFFECTS[name]()
        assert hash(first) == hash(second)
        assert len({first, second, OTHER[name]()}) == 2
        assert {first: 1}[second] == 1

    def test_copy_and_deepcopy_are_equal(self, name):
        effect = EFFECTS[name]()
        assert copy.copy(effect) == effect
        assert copy.deepcopy(effect) == effect
        assert copy.deepcopy([effect, effect])[0] == effect

    def test_repr_is_clean_python(self, name):
        text = repr(EFFECTS[name]())
        assert text.startswith(f'TerminalAudioEffect.{name}(') and text.endswith(')')
        for bad in BAD_TEXT:
            assert bad not in text, (bad, text)

    def test_repr_rebuilds_an_equal_effect(self, name):
        effect = EFFECTS[name]()
        assert eval(repr(effect), {'TerminalAudioEffect': TerminalAudioEffect}) == effect

    def test_never_equal_to_other_types(self, name):
        effect = EFFECTS[name]()
        assert effect != name and effect != 1 and effect != None
        assert effect != effect.name


def test_effects_of_different_kinds_are_unequal():
    built = [make() for make in EFFECTS.values()]
    assert len({hash(e) for e in built}) == len(built)
    for i, a in enumerate(built):
        for b in built[i + 1 :]:
            assert a != b


def test_default_effect_repr_shows_defaults():
    assert (
        repr(TerminalAudioEffect.bit_crush())
        == 'TerminalAudioEffect.bit_crush(bits=8, downsample=4)'
    )
    assert (
        repr(TerminalAudioEffect.reverb())
        == 'TerminalAudioEffect.reverb(room=0.5, damping=0.5, mix=0.25)'
    )


def test_negative_zero_equals_zero_and_hashes_alike():
    a, b = (
        TerminalAudioEffect.tremolo(rate_hertz=5.0, depth=0.0),
        TerminalAudioEffect.tremolo(rate_hertz=5.0, depth=-0.0),
    )
    assert a == b and hash(a) == hash(b)


def test_float_arguments_survive_the_repr_round_trip_exactly():
    for value in (20.1, 0.707 * 100, 1000 / 3, 1234.5678, 8000.0, 19999.0):
        effect = TerminalAudioEffect.low_pass(cutoff=value, resonance=0.1 + value / 2000)
        assert eval(repr(effect), {'TerminalAudioEffect': TerminalAudioEffect}) == effect


# ---------------------------------------------------------------- sample


def test_samples_with_same_content_are_equal_and_hash_alike():
    a = TerminalSound.from_samples([0.0, 0.25, -0.5], sample_rate=22050)
    b = TerminalSound.from_samples([0.0, 0.25, -0.5], sample_rate=22050)
    assert a == b and hash(a) == hash(b) and len({a, b}) == 1


def test_samples_differ_by_content_and_by_rate():
    base = TerminalSound.from_samples([0.0, 0.25])
    assert base != TerminalSound.from_samples([0.0, 0.26])
    assert base != TerminalSound.from_samples([0.0, 0.25], sample_rate=48000)
    assert base != TerminalSound.from_samples([0.0, 0.25, 0.0])
    assert base != 3 and base != 'x'


def test_rendered_notes_are_equal_across_renders():
    assert render_note('piano', 'A3', duration_milliseconds=80) == render_note(
        'piano', 'a3', duration_milliseconds=80
    )
    assert render_note('piano', 'A3', duration_milliseconds=80) != render_note(
        'piano', 'A4', duration_milliseconds=80
    )


def test_sample_copy_is_equal():
    sample = render_note('bell', 'C5', duration_milliseconds=60)
    assert copy.copy(sample) == sample == copy.deepcopy(sample)


def test_sample_with_no_effects_equals_the_original():
    sample = render_note('pluck', 'E3', duration_milliseconds=60)
    assert sample.with_effects([]) == sample


def test_negative_zero_samples_equal_zero_samples():
    assert TerminalSound.from_samples([-0.0]) == TerminalSound.from_samples([0.0])
    assert hash(TerminalSound.from_samples([-0.0])) == hash(
        TerminalSound.from_samples([0.0])
    )


def test_sample_repr_is_one_clean_line():
    text = repr(render_note('kick'))
    assert text.startswith('TerminalSound(') and 'ms @' in text and 'Hz' in text
    for bad in BAD_TEXT:
        assert bad not in text


def test_sample_bytes_and_floats_agree():
    import struct

    sample = render_note('synth', 'C3', duration_milliseconds=40)
    data = sample.to_bytes()
    assert len(data) == 4 * len(sample)
    assert list(struct.unpack(f'<{len(sample)}f', data)) == sample.samples()
