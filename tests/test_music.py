"""
tests.test_music

Notes, chords and sequences: defining them without a device, playing them on a canvas or on
the sound output, and finding sounds by symbol name.
"""

from __future__ import annotations

import sys
import threading
import typing

import pytest
from xnano_audio import (
    TerminalAudioEffect,
    TerminalAudioUnavailableError,
    TerminalNote,
    TerminalSound,
    instrument_names,
    render_note,
)

import xnano
import xnano.audio as audio_module
import xnano.music as music_module
import xnano.types
from xnano import symbols
from xnano_core import Event


@pytest.fixture
def canvas():
    """A canvas whose clock you move, so what is played is recorded."""
    with xnano.new(width=20, height=3, fps=10) as canvas:
        yield canvas


def peak_after(canvas, seconds: float) -> float:
    canvas.step(delta_seconds=seconds)
    return max(abs(sample) for sample in canvas.audio.render_sound().samples())


def crossings(sound: TerminalSound) -> int:
    samples = sound.samples()
    return sum(
        1
        for previous, current in zip(samples, samples[1:], strict=False)
        if (previous < 0.0) != (current < 0.0)
    )


class TestNote:
    def test_a_note_is_a_value_with_defaults(self):
        note = xnano.note('C4')
        assert note == xnano.Note('C4')
        assert (note.beats, note.instrument, note.velocity) == (1.0, 'piano', 0.8)
        assert note.effects == ()
        assert note.symbol is None

    def test_a_chord_is_a_tuple_of_pitches(self):
        assert xnano.note(['C4', 'E4', 64]).pitch == ('C4', 'E4', 64)
        assert xnano.note(('C4', 'E4')).pitch == ('C4', 'E4')

    def test_a_note_is_frozen(self):
        with pytest.raises(AttributeError):
            xnano.note('C4').beats = 2.0  # type: ignore[misc]

    def test_a_note_is_playable_by_itself(self):
        note = xnano.note('C4')
        assert note.__xnano_play__(None) is note  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ('keywords', 'error', 'message'),
        [
            ({'pitch': 'X9'}, ValueError, "'X9' is not a note name"),
            ({'pitch': 128}, ValueError, 'MIDI pitch 128'),
            ({'pitch': -1}, ValueError, 'MIDI pitch -1'),
            ({'pitch': 4.5}, TypeError, 'A pitch is a note name'),
            ({'pitch': True}, TypeError, 'A pitch is a note name'),
            ({'pitch': ()}, ValueError, 'at least one pitch'),
            ({'pitch': 'C4', 'beats': 0}, ValueError, 'beats must be a number above 0'),
            ({'pitch': 'C4', 'beats': -1}, ValueError, 'beats must be a number above 0'),
            ({'pitch': 'C4', 'velocity': 1.5}, ValueError, 'velocity must be from'),
            ({'pitch': 'C4', 'instrument': 'kazoo'}, ValueError, 'not an instrument'),
            ({'pitch': 'C4', 'effects': [3]}, TypeError, 'dictionaries such as'),
        ],
    )
    def test_a_wrong_value_is_explained_where_the_note_is_made(
        self, keywords, error, message
    ):
        with pytest.raises(error, match=message):
            xnano.Note(**keywords)

    def test_a_note_needs_no_device_and_no_canvas(self):
        assert xnano.active(is_required=False) is None
        xnano.note('C4', instrument='bell', effects=[{'kind': 'audio.reverb'}])

    def test_every_instrument_can_be_a_note(self, canvas):
        assert len(instrument_names()) == 23
        for name in instrument_names():
            canvas.play(xnano.note('C3', instrument=name, beats=0.2))
            assert peak_after(canvas, 0.5) > 0.0, name

    def test_a_note_works_without_the_audio_package(self):
        import subprocess
        import textwrap

        code = textwrap.dedent(
            """
            import sys
            sys.modules['xnano_audio'] = None
            import xnano
            note = xnano.note(['C4', 'Eb4'], beats=2, instrument='anything')
            assert note.pitch == ('C4', 'Eb4')
            try:
                xnano.note('H9')
            except ValueError as error:
                print(error)
            """
        )
        result = subprocess.run(
            [sys.executable, '-c', code], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr
        assert "'H9' is not a note name" in result.stdout


class TestPlaying:
    def test_a_note_lasts_for_its_beats_at_the_tempo(self):
        with xnano.new(width=8, height=1, bpm=60) as canvas:
            canvas.play(xnano.note('A4', beats=2.0))
            canvas.step(delta_seconds=1.0)
            first = canvas.audio.render_sound()
            canvas.step(delta_seconds=1.5)
            second = canvas.audio.render_sound()
            assert max(first.samples()) > 0.1
            assert max(second.samples()) > 0.1, 'still held after one beat at 60 bpm'

    def test_a_chord_sounds_all_its_pitches(self, canvas):
        canvas.play(xnano.note('C4', instrument='sine', beats=0.4))
        single = crossings_of(canvas)
        canvas.play(xnano.note(('C4', 'G5'), instrument='sine', beats=0.4))
        chord = crossings_of(canvas)
        assert chord > single * 2

    def test_a_sequence_plays_one_note_after_another(self, canvas):
        canvas.play(
            [
                xnano.note('C4', instrument='sine', beats=0.5),
                xnano.note('C6', instrument='sine', beats=0.5),
            ]
        )
        canvas.step(delta_seconds=0.25)
        first = crossings(canvas.audio.render_sound())
        canvas.step(delta_seconds=0.25)
        second = crossings(canvas.audio.render_sound())
        assert second > first * 2, 'the second half is the higher note'

    def test_the_recording_of_a_sequence_starts_each_note_after_the_previous(
        self, canvas
    ):
        canvas.play([xnano.note('C4', beats=1.0), xnano.note('E4', beats=2.0), 'G4'])
        starts = [recording.start_seconds for recording in canvas.audio._recordings]
        assert starts == pytest.approx([0.0, 0.5, 1.5])

    def test_an_empty_sequence_is_refused(self, canvas):
        with pytest.raises(ValueError, match='empty sequence'):
            canvas.play([])

    def test_an_option_replaces_the_value_on_a_note(self, canvas):
        calls: list[tuple[str, float, int]] = []
        real = audio_module.render_note

        def spy(instrument, pitch, *, duration_milliseconds, velocity, effects):
            calls.append((instrument, velocity, duration_milliseconds))
            return real(
                instrument,
                pitch,
                duration_milliseconds=duration_milliseconds,
                velocity=velocity,
                effects=effects,
            )

        audio_module.render_note = spy
        try:
            canvas.play(xnano.note('C4', instrument='bell', velocity=0.3, beats=1.0))
            canvas.play(
                xnano.note('E4', instrument='bell', velocity=0.3, beats=1.0),
                instrument='marimba',
                velocity=0.9,
                beats=0.5,
            )
            canvas.step(delta_seconds=1.0)
            canvas.audio.render_sound()
        finally:
            audio_module.render_note = real
        assert sorted(calls) == [('bell', 0.3, 500), ('marimba', 0.9, 250)]

    def test_beats_set_the_length_of_a_note_name_and_of_melody_text(self, canvas):
        canvas.play('C4 E4', beats=0.5)
        canvas.play(60, beats=2.0)
        lengths = sorted(
            round(recording.end_seconds - recording.start_seconds - 1.0, 3)
            for recording in canvas.audio._recordings
        )
        assert lengths == [0.5, 1.0]

    def test_effects_of_a_note_change_the_sound(self, canvas):
        plain = render_note('bell', 'C5')
        reverb = render_note('bell', 'C5', effects=[TerminalAudioEffect.reverb()])
        canvas.play(
            xnano.note('C5', instrument='bell', effects=[{'kind': 'audio.reverb'}])
        )
        canvas.step(delta_seconds=1.0)
        heard = canvas.audio.render_sound().samples()
        assert heard[:1000] != plain.samples()[:1000]
        assert heard[:1000] == pytest.approx(reverb.samples()[:1000], abs=1e-6)

    def test_a_visual_effect_in_a_sound_is_refused(self, canvas):
        with pytest.raises(TypeError, match='visual effect; pass it to write'):
            canvas.play('C4', effects=[{'kind': 'effect.fade_to'}])

    def test_a_handle_tells_when_the_sound_is_over(self, canvas):
        handle = canvas.play(xnano.note('C4', beats=0.2))
        assert not handle.is_finished
        canvas.step(delta_seconds=3.0)
        assert handle.is_finished

    def test_removing_a_handle_silences_what_was_not_heard_yet(self, canvas):
        handle = canvas.play(xnano.note('C4', beats=1.0))
        handle.remove()
        handle.remove()
        assert handle.is_finished
        assert peak_after(canvas, 1.0) == 0.0

    def test_play_returns_a_handle_everywhere(self, canvas):
        assert isinstance(canvas.play('C4'), xnano.music.PlayHandle)
        assert isinstance(canvas.audio.play('C4'), xnano.music.PlayHandle)
        assert isinstance(xnano.play('C4'), xnano.music.PlayHandle)

    def test_a_thing_that_cannot_be_played_says_what_can(self, canvas):
        with pytest.raises(TypeError, match='Cannot play a object.*Note'):
            canvas.play(object())  # type: ignore[arg-type]


def crossings_of(canvas) -> int:
    canvas.step(delta_seconds=0.5)
    return crossings(canvas.audio.render_sound())


class TestPlayOnTheActiveCanvas:
    def test_play_on_a_manual_canvas_is_recorded_not_sounded(self, canvas, monkeypatch):
        monkeypatch.setattr(music_module, '_default', None)
        xnano.play(xnano.note('C4'))
        assert music_module._default is None, 'no sound output was opened'
        assert peak_after(canvas, 0.5) > 0.0

    def test_play_goes_to_the_innermost_canvas(self):
        with xnano.new(width=4, height=1) as outer, xnano.new(width=4, height=1) as inner:
            xnano.play('C4')
            assert len(inner.audio._recordings) == 1
            assert outer.audio._recordings == []


class FakePlayer:
    instances: list[FakePlayer] = []
    is_open = True

    def __init__(self, *, beats_per_minute: float = 120.0) -> None:
        if not FakePlayer.is_open:
            raise audio_module.TerminalAudioError('no device')
        self.tempo = beats_per_minute
        self.played: list[tuple[TerminalSound, float, float, int | None]] = []
        self.is_clock_running = False
        self.closed = False
        FakePlayer.instances.append(self)

    def play_sound(self, sound, *, volume=1.0, pan=0.0, at_beat=None) -> None:
        self.played.append((sound, volume, pan, at_beat))

    def start_clock(self) -> None:
        self.is_clock_running = True

    def close(self) -> None:
        self.closed = True


class TestPlayWithoutACanvas:
    @pytest.fixture(autouse=True)
    def fake_output(self, monkeypatch):
        FakePlayer.instances = []
        FakePlayer.is_open = True
        monkeypatch.setattr(audio_module, 'TerminalAudioPlayer', FakePlayer)
        monkeypatch.setattr(music_module, '_default', None)
        monkeypatch.setattr('atexit.register', lambda function: None)

    def test_the_sound_goes_to_a_default_output(self):
        handle = xnano.play(xnano.note('C4', instrument='bell'), volume=0.5)
        (player,) = FakePlayer.instances
        sound, volume, pan, at_beat = player.played[0]
        assert sound == render_note('bell', 'C4', duration_milliseconds=500)
        assert (volume, pan, at_beat) == (0.5, 0.0, None)
        assert not handle.is_finished

    def test_one_output_serves_every_call(self):
        xnano.play('C4')
        xnano.play('E4')
        assert len(FakePlayer.instances) == 1
        assert len(FakePlayer.instances[0].played) == 2

    def test_a_sequence_is_mixed_into_one_sound(self):
        xnano.play([xnano.note('C4', beats=1.0), xnano.note('E4', beats=1.0)])
        ((sound, *_),) = FakePlayer.instances[0].played
        assert sound.duration_milliseconds >= 1000
        assert sound.peak <= 1.0

    def test_a_beat_starts_the_clock(self):
        xnano.play('C4', at_beat=2)
        player = FakePlayer.instances[0]
        assert player.is_clock_running
        assert player.played[0][3] == 2

    def test_no_device_says_how_to_play_anyway(self):
        FakePlayer.is_open = False
        with pytest.raises(
            TerminalAudioUnavailableError, match='xnano.play needs a sound'
        ):
            xnano.play('C4')

    def test_the_output_is_closed_on_request(self):
        xnano.play('C4')
        music_module._default_player().close()
        assert FakePlayer.instances[0].closed

    def test_calls_from_two_threads_share_the_output(self):
        threads = [threading.Thread(target=lambda: xnano.play('C4')) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert len(FakePlayer.instances) == 1
        assert len(FakePlayer.instances[0].played) == 4


class TestSymbols:
    def test_a_registered_note_plays_by_name(self, canvas):
        xnano.note('C2', instrument='kick', symbol='kick_drum')
        assert symbols.lookup('kick_drum', kind=xnano.Note).instrument == 'kick'
        canvas.play('kick_drum')
        assert peak_after(canvas, 0.5) > 0.0

    def test_a_registered_sound_plays_by_name(self, canvas):
        sound = TerminalSound.from_samples([0.0, 0.5, -0.5, 0.0] * 100, sample_rate=44100)
        xnano.from_audio(sound, symbol='blip')
        canvas.play('blip')
        assert peak_after(canvas, 0.1) > 0.4

    def test_a_symbol_is_found_inside_a_sequence_and_takes_options(self, canvas):
        xnano.note('C4', beats=1.0, symbol='low_tone')
        canvas.play(['low_tone', 'low_tone'], beats=0.25)
        starts = [recording.start_seconds for recording in canvas.audio._recordings]
        assert starts == pytest.approx([0.0, 0.125])

    def test_a_symbol_of_another_kind_is_not_a_sound(self, canvas):
        xnano.Pixel('#', symbol='wall_pixel')
        with pytest.raises(TypeError, match="'wall_pixel' is a Pixel symbol"):
            canvas.play('wall_pixel')

    def test_an_unknown_name_lists_the_symbols_and_the_grammar(self, canvas):
        xnano.note('C2', symbol='kick_drum')
        xnano.note('C3', symbol='snare_drum')
        with pytest.raises(ValueError) as caught:
            canvas.play('kik_drum')
        message = str(caught.value)
        assert (
            "'kik_drum' is not a known sound symbol, a note name or melody text"
            in message
        )
        assert "'kick_drum', 'snare_drum'" in message
        assert 'letter, an optional # or b, and an octave' in message
        assert "symbol='kik_drum'" in message

    def test_a_note_name_is_never_a_symbol(self):
        with pytest.raises(ValueError, match='reads as a note'):
            xnano.note('C2', symbol='C4')

    def test_registering_a_note_again_replaces_it(self, canvas):
        xnano.note('C4', symbol='tone_again')
        xnano.note('E4', symbol='tone_again')
        assert symbols.lookup('tone_again').pitch == 'E4'

    def test_a_different_kind_under_a_taken_name_is_refused(self):
        xnano.note('C4', symbol='tone_taken')
        with pytest.raises(ValueError, match='already a Note'):
            xnano.Pixel('#', symbol='tone_taken')


class TestRawForms:
    """What the canvas has always played still plays, with ``beats`` for the length."""

    def test_a_terminal_note_melody_and_sound_play(self, canvas):
        from xnano_audio import TerminalMelody

        canvas.play(TerminalNote('C4', duration_beats=0.5))
        canvas.play(TerminalMelody([TerminalNote('E4')]))
        canvas.play(render_note('bell', 'C6'))
        assert len(canvas.audio._recordings) == 3

    def test_a_midi_number_and_a_frequency_play(self, canvas):
        canvas.play(60)
        canvas.play(440.0)
        canvas.play('440hz')
        assert peak_after(canvas, 1.0) > 0.0

    def test_a_sound_of_another_sample_rate_is_mixed_at_the_standard_rate(self, canvas):
        slow = TerminalSound.from_samples([0.5, -0.5] * 400, sample_rate=8000)
        canvas.play(slow)
        canvas.play('C4')
        assert peak_after(canvas, 0.2) > 0.0


class TestSoundEffectLists:
    @pytest.mark.parametrize(
        ('effects', 'message'),
        [
            ([{'kind': 'effect.fade_to'}], "'effect.fade_to' is a visual effect"),
            ([{'kind': 'fill'}], "'fill' is not a sound effect"),
            ([{'kind': 'audio.nope'}], "'audio.nope' is not a known customization"),
        ],
    )
    def test_a_note_refuses_what_is_not_a_sound_effect(self, effects, message):
        error = ValueError if 'known customization' in message else TypeError
        with pytest.raises(error, match=message):
            xnano.note('C4', effects=effects)

    def test_a_note_checks_the_keywords_of_its_effects(self):
        with pytest.raises(TypeError):
            xnano.note('C4', effects=[{'kind': 'audio.reverb', 'wetness': 1}])

    def test_an_fx_object_is_not_a_sound_effect_entry(self, canvas):
        reverb = xnano.operations.fx('audio.reverb')
        with pytest.raises(TypeError, match='write the effect as a dictionary'):
            canvas.play('C4', effects=[reverb])  # type: ignore[list-item]
        with pytest.raises(TypeError, match='write the effect as a dictionary'):
            xnano.note('C4', effects=[reverb])  # type: ignore[list-item]

    def test_every_sound_kind_plays(self, canvas):
        for kind in typing.get_args(xnano.types.PlayableEffectKind):
            canvas.play(xnano.note('C4', beats=0.2, effects=[{'kind': kind}]))
        assert peak_after(canvas, 1.0) > 0.0


class TestHookSoundEffects:
    @staticmethod
    def hear(canvas, *, press_keys=('a',)):
        for key in press_keys:
            canvas.push(Event.key_press(key))
            canvas.deliver_events()
        canvas.step(delta_seconds=1.0)
        return canvas.audio.render_sound().samples()

    def test_a_sound_effect_of_a_hook_is_added_to_what_the_hook_plays(self, canvas):
        @canvas.hook(on='key')
        def ring(context):
            context.fx('audio.reverb')
            context.audio.play(xnano.note('C5', instrument='bell'))

        heard = self.hear(canvas)
        reverb = render_note('bell', 'C5', effects=[TerminalAudioEffect.reverb()])
        plain = render_note('bell', 'C5')
        assert heard[:1000] == pytest.approx(reverb.samples()[:1000], abs=1e-6)
        assert heard[:1000] != plain.samples()[:1000]

    def test_the_effect_applies_to_every_form_of_sound(self, canvas):
        @canvas.hook(on='key')
        def ring(context):
            context.fx('audio.distortion')
            context.canvas.play('C4')
            context.audio.play('C4 E4')
            context.canvas.play(render_note('bell', 'C6'))

        canvas.push(Event.key_press('a'))
        canvas.deliver_events()
        recordings = canvas.audio._recordings
        assert len(recordings) == 3
        for recording in recordings:
            assert 'distortion' in repr(recording.key).lower()

    def test_a_note_keeps_its_own_effects_and_gains_the_hooks(self, canvas):
        @canvas.hook(on='key')
        def ring(context):
            context.fx('audio.tremolo')
            context.audio.play(
                xnano.note('C5', instrument='bell', effects=[{'kind': 'audio.reverb'}])
            )

        heard = self.hear(canvas)
        expected = render_note(
            'bell',
            'C5',
            effects=[TerminalAudioEffect.reverb(), TerminalAudioEffect.tremolo()],
        )
        assert heard[:1000] == pytest.approx(expected.samples()[:1000], abs=1e-6)

    def test_sound_played_outside_the_hook_is_not_changed(self, canvas):
        @canvas.hook(on='key')
        def set_effect(context):
            context.fx('audio.reverb')

        canvas.push(Event.key_press('a'))
        canvas.deliver_events()
        canvas.play(xnano.note('C5', instrument='bell'))
        canvas.step(delta_seconds=1.0)
        heard = canvas.audio.render_sound().samples()
        plain = render_note('bell', 'C5')
        assert heard[:1000] == pytest.approx(plain.samples()[:1000], abs=1e-6)

    def test_the_effect_stays_for_later_runs_of_the_hook(self, canvas):
        @canvas.hook(on='key')
        def ring(context):
            if context.keyboard.key == 'a':
                context.fx('audio.reverb')
            else:
                context.audio.play(xnano.note('C5', instrument='bell'))

        heard = self.hear(canvas, press_keys=('a', 'b'))
        reverb = render_note('bell', 'C5', effects=[TerminalAudioEffect.reverb()])
        assert heard[:1000] == pytest.approx(reverb.samples()[:1000], abs=1e-6)

    def test_clear_stops_adding_the_effect(self, canvas):
        @canvas.hook(on='key')
        def ring(context):
            context.fx('audio.reverb')
            context.fx.clear()
            context.audio.play(xnano.note('C5', instrument='bell'))

        heard = self.hear(canvas)
        plain = render_note('bell', 'C5')
        assert heard[:1000] == pytest.approx(plain.samples()[:1000], abs=1e-6)

    def test_removing_the_hook_stops_adding_the_effect(self, canvas):
        @canvas.hook(on='key')
        def ring(context: xnano.context.Context) -> None:
            context.fx('audio.reverb')

        canvas.push(Event.key_press('a'))
        canvas.deliver_events()
        (handle,) = canvas._registrations
        assert handle._effect_state is not None
        handle.remove()
        assert handle._effect_state is None
        assert audio_module.hook_effects(canvas) == ()

    def test_another_hook_is_not_affected(self, canvas):
        @canvas.hook(on='key', keys='a')
        def first(context):
            context.fx('audio.reverb')

        @canvas.hook(on='key', keys='b')
        def second(context):
            context.audio.play(xnano.note('C5', instrument='bell'))

        heard = self.hear(canvas, press_keys=('a', 'b'))
        plain = render_note('bell', 'C5')
        assert heard[:1000] == pytest.approx(plain.samples()[:1000], abs=1e-6)

    def test_a_thread_that_is_not_the_hook_gets_no_effects(self, canvas):
        outcome: list[tuple[object, ...]] = []

        @canvas.hook(on='key')
        def ring(context):
            context.fx('audio.reverb')
            worker = threading.Thread(
                target=lambda: outcome.append(audio_module.hook_effects(canvas))
            )
            worker.start()
            worker.join()
            outcome.append(audio_module.hook_effects(canvas))

        canvas.push(Event.key_press('a'))
        canvas.deliver_events()
        assert outcome[0] == ()
        assert len(outcome[1]) == 1
        assert audio_module.hook_effects(canvas) == ()

    def test_a_visual_effect_does_not_reach_the_sound(self, canvas):
        @canvas.hook(on='key')
        def ring(context):
            context.fx('effect.fade_to', foreground='red', duration_milliseconds=100)
            context.audio.play('C4')
            assert audio_module.hook_effects(canvas) == ()

        canvas.push(Event.key_press('a'))
        canvas.deliver_events()
