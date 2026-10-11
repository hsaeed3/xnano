"""
Playback engine and microphone.

Needs an output (or input) device, so these skip where none exists (CI,
containers, SSH). Everything is played at volume 0.0 to stay silent while
still exercising the real mixer. Argument validation must happen *before*
anything reaches the mixer, so bad calls leave the engine usable.
"""

from __future__ import annotations

import math
import time

import pytest
from helpers import CLASSES, matches

from xnano_audio import (
    TerminalAudioEffect,
    TerminalAudioError,
    TerminalAudioPlayer,
    TerminalAudioUnavailableError,
    TerminalMicrophone,
    TerminalSound,
    detect_audio_capabilities,
    render_note,
)

NAN, INF = float('nan'), float('inf')

needs_output = pytest.mark.skipif(
    not TerminalAudioPlayer.is_available(), reason='no audio output device'
)
needs_input = pytest.mark.skipif(
    not TerminalMicrophone.is_available(), reason='no audio input device'
)


def test_probes_return_real_bools():
    assert type(TerminalAudioPlayer.is_available()) is bool
    assert type(TerminalMicrophone.is_available()) is bool


def test_error_is_a_runtime_error_with_a_helpful_type():
    assert issubclass(TerminalAudioError, RuntimeError)
    assert not issubclass(TerminalAudioError, ValueError)
    assert issubclass(TerminalAudioUnavailableError, TerminalAudioError)


@pytest.mark.skipif(TerminalAudioPlayer.is_available(), reason='a device exists')
def test_without_a_device_the_player_raises_unavailable():
    with pytest.raises(TerminalAudioUnavailableError) as caught:
        TerminalAudioPlayer()
    assert 'detect_audio_capabilities' in str(caught.value) or 'playback' in str(
        caught.value
    )


@pytest.mark.skipif(TerminalMicrophone.is_available(), reason='a device exists')
def test_without_a_microphone_construction_raises_unavailable():
    with pytest.raises(TerminalAudioUnavailableError):
        TerminalMicrophone()


def test_capability_detection_agrees_with_the_device_checks():
    capabilities = detect_audio_capabilities()
    assert capabilities.is_output_available == TerminalAudioPlayer.is_available()
    assert capabilities.is_input_available == TerminalMicrophone.is_available()


def test_bad_tempo_is_rejected_before_any_device_is_opened():
    with pytest.raises(ValueError, match='beats_per_minute'):
        TerminalAudioPlayer(beats_per_minute=0.0)


@pytest.fixture
def engine():
    return TerminalAudioPlayer()


@needs_output
class TestEngine:
    def test_clock_starts_at_zero_and_reports_a_float(self, engine):
        beat = engine.beat
        assert type(beat) is float and beat == 0.0
        return_type = CLASSES['TerminalAudioPlayer'].methods['beat'].returns
        assert return_type is not None
        assert matches(beat, return_type)
        assert engine.tempo == 120.0
        assert engine.is_clock_running is False

    def test_clock_runs_pauses_and_resets(self, engine):
        engine.set_tempo(6000.0)  # 100 beats per second
        engine.start_clock()
        time.sleep(0.3)
        assert engine.beat > 5
        assert engine.clock_position_milliseconds > 50
        engine.pause_clock()
        time.sleep(0.05)  # clock commands apply on the next audio buffer
        paused = engine.beat
        time.sleep(0.1)
        assert engine.beat == paused
        engine.stop_clock()
        time.sleep(0.05)
        assert engine.beat == 0.0

    def test_sounds_and_notes_play_on_the_clock(self, engine):
        engine.set_tempo(6000.0)
        engine.start_clock()
        engine.play_note('piano', 'C4', duration_milliseconds=50, volume=0.0)
        engine.play_note('kick', effects=[TerminalAudioEffect.reverb()], volume=0.0)
        engine.play_sound(
            render_note('bell', 'C6', duration_milliseconds=50), volume=0.0, at_beat=5
        )
        time.sleep(0.2)
        assert engine.beat > 5

    def test_play_calls_return_none(self, engine):
        assert engine.play_note('hihat', volume=0.0) is None
        assert (
            engine.play_sound(TerminalSound.from_samples([0.0] * 441), volume=0.0) is None
        )

    @pytest.mark.parametrize('pan', [-1.0, 0.0, 1.0, 0.25])
    def test_valid_pans(self, engine, pan):
        engine.play_note('hihat', volume=0.0, pan=pan)
        engine.play_sound(TerminalSound.from_samples([0.0] * 441), volume=0.0, pan=pan)

    @pytest.mark.parametrize('pan', [-1.01, 1.5, NAN, INF, -INF])
    def test_bad_pans_are_rejected_everywhere(self, engine, pan):
        silent = TerminalSound.from_samples([0.0] * 441)
        with pytest.raises(ValueError):
            engine.play_sound(silent, pan=pan)
        with pytest.raises(ValueError):
            engine.play_note('piano', pan=pan)

    @pytest.mark.parametrize('volume', [NAN, INF, -INF])
    def test_non_finite_volume_is_rejected_not_sent_to_the_mixer(self, engine, volume):
        silent = TerminalSound.from_samples([0.0] * 441)
        with pytest.raises(ValueError, match='volume'):
            engine.play_sound(silent, volume=volume)
        with pytest.raises(ValueError, match='volume'):
            engine.play_note('piano', volume=volume)

    def test_out_of_range_volume_is_clamped(self, engine):
        silent = TerminalSound.from_samples([0.0] * 441)
        engine.play_sound(silent, volume=-5.0)
        engine.play_sound(silent, volume=50.0)

    @pytest.mark.parametrize('speed', [0.0, -60.0, NAN, INF, -INF, 1e12])
    def test_bad_tempos_are_rejected(self, engine, speed):
        with pytest.raises(ValueError, match='beats_per_minute'):
            engine.set_tempo(speed)
        engine.set_tempo(120.0)  # still usable afterwards

    def test_bad_arguments_leave_the_engine_usable(self, engine):
        for call in (
            lambda: engine.play_note('kazoo'),
            lambda: engine.play_note('piano', 'H9'),
            lambda: engine.play_note('piano', duration_milliseconds=0),
            lambda: engine.play_note('piano', velocity=NAN),
            lambda: engine.play_note(
                'piano', effects=[TerminalAudioEffect.tremolo()] * 33
            ),
        ):
            with pytest.raises(ValueError):
                call()
        engine.play_note('piano', volume=0.0)

    def test_wrong_types_raise_type_error(self, engine):
        with pytest.raises(TypeError):
            engine.play_sound('not a sample')
        with pytest.raises(TypeError):
            engine.play_note('piano', note=[60])
        with pytest.raises(TypeError):
            engine.play_note('piano', effects='reverb')

    @pytest.mark.parametrize('beat', [-1, 2**64])
    def test_at_beat_must_fit_an_unsigned_64_bit_integer(self, engine, beat):
        with pytest.raises(OverflowError):
            engine.play_note('piano', volume=0.0, at_beat=beat)

    def test_huge_future_beats_are_accepted_and_never_fire(self, engine):
        engine.play_note('piano', volume=0.0, at_beat=2**63)

    def test_many_sounds_do_not_exhaust_the_mixer_silently(self, engine):
        silent = TerminalSound.from_samples([0.0] * 441)
        try:
            for _ in range(300):
                engine.play_sound(silent, volume=0.0)
        except TerminalAudioError as error:
            assert str(error)  # running out of voices must say so

    def test_two_engines_in_one_process_fail_cleanly_or_work(self, engine):
        try:
            other = TerminalAudioPlayer()
        except TerminalAudioError as error:
            assert str(error)
        else:
            other.play_note('hihat', volume=0.0)

    def test_every_instrument_plays(self, engine):
        from xnano_audio import instrument_names

        for name in instrument_names():
            engine.play_note(name, duration_milliseconds=20, volume=0.0)

    def test_engine_is_bound_to_its_thread(self, engine):
        """
        Documented limitation (``unsendable``): use from the creating
        thread. A worker thread is refused loudly, and the owner is unharmed.
        """
        import threading

        failures = []

        def other():
            try:
                engine.beat  # noqa: B018 - reading the property is the test
            except BaseException as error:  # noqa: BLE001 - PanicException
                failures.append(error)

        thread = threading.Thread(target=other)
        thread.start()
        thread.join()
        assert failures and 'unsendable' in str(failures[0])
        assert engine.beat >= 0
        engine.play_note('hihat', volume=0.0)


@needs_input
class TestMicrophone:
    @pytest.fixture
    def microphone(self):
        try:
            return TerminalMicrophone()
        except TerminalAudioError as error:
            pytest.skip(f'input device could not be opened: {error}')

    def test_lifecycle(self, microphone):
        with microphone as opened:
            assert opened is microphone
            assert microphone.is_open
            assert microphone.sample_rate > 0
            assert microphone.channels > 0
        assert not microphone.is_open

    def test_level_is_a_unit_float(self, microphone):
        with microphone:
            time.sleep(0.1)
            level = microphone.level
            assert type(level) is float and 0.0 <= level <= 1.0
            assert not math.isnan(level)

    def test_level_history_and_peak(self, microphone):
        with microphone:
            time.sleep(0.2)
            history = microphone.level_history(10)
            assert len(history) <= 10
            assert all(0.0 <= level <= 1.0 for level in history)
            assert microphone.peak_level >= max(history, default=0.0)
            microphone.reset_peak_level()
            with pytest.raises(ValueError, match='count'):
                microphone.level_history(5000)

    def test_close_is_idempotent_and_level_after_close_is_safe(self, microphone):
        microphone.close()
        microphone.close()
        assert not microphone.is_open
        assert microphone.level == 0.0

    def test_properties_have_stub_types(self, microphone):
        stub = CLASSES['TerminalMicrophone'].methods
        sample_rate_type = stub['sample_rate'].returns
        channels_type = stub['channels'].returns
        assert sample_rate_type is not None and channels_type is not None
        assert matches(microphone.sample_rate, sample_rate_type)
        assert matches(microphone.channels, channels_type)
        microphone.close()

    def test_exceptions_inside_the_with_block_still_close(self, microphone):
        with pytest.raises(KeyError), microphone:
            raise KeyError('boom')
        assert not microphone.is_open
