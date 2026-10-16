"""
Stub-driven contract tests.

The ``.pyi`` is the documented surface. These tests check the compiled module
against it: every name exists both ways, every device-free call returns the
type its annotation promises, and every public item is documented.
"""

from __future__ import annotations

import inspect
import re
from typing import Any, cast

import pytest
from helpers import CLASSES, FUNCTIONS, matches

import xnano_audio
import xnano_audio._xnano_audio as native
from xnano_audio import (
    TerminalAudioEffect,
    TerminalSound,
    instrument_names,
    is_percussive,
    note_to_hertz,
    render_note,
)

DEVICE_CLASSES = {
    'TerminalAudioPlayer',
    'TerminalMicrophone',
    'TerminalStreamingAudioPlayer',
}
# Protocols describe what a Python object must provide; they have no native implementation.
PROTOCOLS = {'TerminalAudioSource', 'SupportsAudioEffect'}


def test_every_stubbed_name_exists_at_runtime():
    for name in (*CLASSES, *FUNCTIONS):
        if name not in PROTOCOLS:
            assert hasattr(native, name), name
    for name, cls in CLASSES.items():
        if name in PROTOCOLS:
            continue
        for method in cls.methods:
            if method.startswith('__') and method not in ('__init__',):
                continue
            assert hasattr(getattr(native, name), method), f'{name}.{method}'


def test_every_runtime_name_is_stubbed():
    stubbed = {*CLASSES, *FUNCTIONS}
    for name in dir(native):
        if name.startswith('_'):
            continue
        value = getattr(native, name)
        if inspect.isclass(value) or inspect.isroutine(value):
            assert name in stubbed, f'{name} has no stub'
    for name, cls in CLASSES.items():
        if name in PROTOCOLS:
            continue
        runtime = getattr(native, name)
        if name in ('TerminalAudioError', 'TerminalAudioUnavailableError'):
            continue
        for method in vars(runtime):
            if method.startswith('_'):
                continue
            assert method in cls.methods, f'{name}.{method} has no stub'


def test_package_exports_match_the_stub():
    aliases = {'InstrumentName', 'NoteName', 'Pitch', 'is_optimized_build'}
    expected = {*CLASSES, *FUNCTIONS, '__version__'}
    assert set(xnano_audio.__all__) == expected | aliases
    for name in expected - PROTOCOLS:
        assert getattr(xnano_audio, name) is getattr(native, name)


def test_version_is_a_dotted_string():
    assert isinstance(xnano_audio.__version__, str)
    assert all(part.isdigit() for part in xnano_audio.__version__.split('.'))


def test_classes_report_the_public_module():
    for name in CLASSES.keys() - PROTOCOLS:
        assert getattr(native, name).__module__ == 'xnano_audio._xnano_audio'


def test_every_public_item_is_documented():
    missing = []
    for name, cls in CLASSES.items():
        if not cls.doc:
            missing.append(name)
        for method in cls.methods.values():
            if not method.name.startswith('__') and not method.doc:
                missing.append(f'{name}.{method.name}')
    missing += [name for name, fn in FUNCTIONS.items() if not fn.doc]
    assert missing == []


def test_documented_exceptions_are_real_classes():
    assert issubclass(native.TerminalAudioError, RuntimeError)
    assert issubclass(native.TerminalAudioUnavailableError, native.TerminalAudioError)
    for error in (native.TerminalAudioError, native.TerminalAudioUnavailableError):
        assert error.__module__ == 'xnano_audio._xnano_audio'


def test_capabilities_are_detected_without_opening_a_device():
    capabilities = native.detect_audio_capabilities()
    check(capabilities, 'detect_audio_capabilities')
    for name in ('has_device_support', 'is_output_available', 'is_input_available'):
        check(getattr(capabilities, name), name, 'TerminalAudioCapabilities')
    for name in ('output_unavailable_reason', 'input_unavailable_reason'):
        check(getattr(capabilities, name), name, 'TerminalAudioCapabilities')
    if capabilities.is_output_available:
        assert capabilities.output_unavailable_reason is None
    else:
        assert capabilities.output_unavailable_reason
    if not capabilities.has_device_support:
        assert not capabilities.is_output_available
        assert not capabilities.is_input_available
    assert capabilities == native.detect_audio_capabilities()
    assert repr(capabilities).startswith('TerminalAudioCapabilities(')


# ------------------------------------------------- return types vs. the stub


def check(value, stub_name: str, owner: str | None = None):
    stub = CLASSES[owner].methods[stub_name] if owner else FUNCTIONS[stub_name]
    assert stub.returns is not None, f'{owner}.{stub_name} has no return annotation'
    assert matches(value, stub.returns), (
        f'{owner or "module"}.{stub_name} returned {value!r} '
        f'({type(value).__name__}), stub says {stub.returns}'
    )


@pytest.fixture(scope='module')
def sample():
    return render_note('piano', 'C4', duration_milliseconds=120)


def test_module_functions_return_their_annotated_types():
    check(instrument_names(), 'instrument_names')
    check(is_percussive('kick'), 'is_percussive')
    for note in ('C4', 60, 440.0, '440hz', 'c#3'):
        check(note_to_hertz(note), 'note_to_hertz')
    check(render_note('bell'), 'render_note')


@pytest.mark.parametrize('instrument', instrument_names())
def test_is_percussive_is_a_real_bool(instrument):
    assert type(is_percussive(instrument)) is bool


def test_note_to_hertz_is_always_a_float_even_for_int_input():
    assert type(note_to_hertz(60)) is float
    assert type(note_to_hertz(440.0)) is float


def test_sample_members_return_their_annotated_types(sample):
    check(sample.sample_rate, 'sample_rate', 'TerminalSound')
    check(sample.duration_milliseconds, 'duration_milliseconds', 'TerminalSound')
    check(sample.peak, 'peak', 'TerminalSound')
    check(sample.root_mean_square, 'root_mean_square', 'TerminalSound')
    check(sample.to_bytes(), 'to_bytes', 'TerminalSound')
    check(sample.samples(), 'samples', 'TerminalSound')
    check(sample.envelope(16), 'envelope', 'TerminalSound')
    check(
        sample.with_effects([TerminalAudioEffect.reverb()]),
        'with_effects',
        'TerminalSound',
    )
    check(len(sample), '__len__', 'TerminalSound')
    check(repr(sample), '__repr__', 'TerminalSound')


def test_sample_constructors_return_samples(sample):
    check(TerminalSound.from_samples([0.0, 0.5]), 'from_samples', 'TerminalSound')
    check(TerminalSound.from_bytes(sample.to_bytes()), 'from_bytes', 'TerminalSound')


EFFECT_BUILDERS = {
    'bit_crush': TerminalAudioEffect.bit_crush,
    'distortion': TerminalAudioEffect.distortion,
    'low_pass': TerminalAudioEffect.low_pass,
    'high_pass': TerminalAudioEffect.high_pass,
    'delay': TerminalAudioEffect.delay,
    'reverb': TerminalAudioEffect.reverb,
    'tremolo': TerminalAudioEffect.tremolo,
}


def test_every_stubbed_effect_constructor_is_covered_here():
    stubbed = {
        name
        for name, m in CLASSES['TerminalAudioEffect'].methods.items()
        if not name.startswith('__') and name != 'name'
    }
    assert stubbed == set(EFFECT_BUILDERS)


@pytest.mark.parametrize('name', EFFECT_BUILDERS)
def test_effect_constructors_and_members(name):
    effect = EFFECT_BUILDERS[name]()
    check(effect, name, 'TerminalAudioEffect')
    check(effect.name, 'name', 'TerminalAudioEffect')
    assert effect.name == name
    check(repr(effect), '__repr__', 'TerminalAudioEffect')


def test_instrument_names_are_unique_lowercase_identifiers():
    names = instrument_names()
    assert len(names) == len(set(names)) > 10
    for name in names:
        assert name == name.lower() and name.replace('_', '').isalnum(), name


def test_signatures_match_the_stub():
    """Argument names in the stub are accepted as keywords at runtime."""
    render_note(
        instrument='piano',
        note='C4',
        duration_milliseconds=50,
        velocity=0.5,
        effects=None,
        sample_rate=22050,
    )
    TerminalSound.from_samples(samples=[0.0], sample_rate=8000)
    TerminalAudioEffect.bit_crush(bits=4, downsample=2)
    TerminalAudioEffect.distortion(drive=2.0)
    TerminalAudioEffect.low_pass(cutoff=500.0, resonance=1.0)
    TerminalAudioEffect.high_pass(cutoff=500.0, resonance=1.0)
    TerminalAudioEffect.delay(time_milliseconds=100.0, feedback=0.2, mix=0.2)
    TerminalAudioEffect.reverb(room=0.3, damping=0.3, mix=0.3)
    TerminalAudioEffect.tremolo(rate_hertz=3.0, depth=0.3)
    note_to_hertz(note='A4')


def test_device_free_calls_are_keyword_only_after_the_subject():
    with pytest.raises(TypeError):
        cast(Any, render_note)('piano', 'C4', 50)
    with pytest.raises(TypeError):
        cast(Any, TerminalAudioEffect.low_pass)(500.0)
    with pytest.raises(TypeError):
        cast(Any, TerminalSound.from_samples)([0.0], 8000)


def test_envelope_traces_the_loudness_of_a_sound():
    sound = TerminalSound.from_samples([0.0] * 100 + [0.5] * 100 + [-1.0] * 100)
    assert sound.envelope(3) == [0.0, 0.5, 1.0]
    assert len(sound.envelope(1000)) == 1000
    assert max(sound.envelope(1)) == 1.0
    for points in (0, 100_001):
        with pytest.raises(ValueError, match='points'):
            sound.envelope(points)


def test_the_stub_table_lists_every_instrument():
    from helpers import STUB

    text = STUB.read_text(encoding='utf-8')
    module_doc = text.split('"""', 2)[1]
    table = module_doc.split('Built-in instruments:', 1)[1].split(
        'Percussive instruments ring', 1
    )[0]
    listed = set(re.findall(r'``([a-z_]+)``', table))
    listed -= {'duration_milliseconds', 'note'}
    assert listed == set(instrument_names())
