"""
tests.test_audio

Sound, notes, melodies and the microphone: recorded on a canvas whose clock you move, and
played on a device (replaced here) by a canvas that runs by itself.
"""

from __future__ import annotations

import pytest
from xnano_audio import (
    TerminalAudioEffect,
    TerminalAudioUnavailableError,
    TerminalMelody,
    TerminalNote,
    TerminalSound,
    render_note,
)

import xnano
import xnano.audio as audio_module
from xnano_core import Event, Width


class FakePlayer:
    available = True
    instances: list[FakePlayer] = []

    def __init__(self, *, beats_per_minute: float = 120.0) -> None:
        self.tempo = beats_per_minute
        self.played: list[tuple[TerminalSound, float, float, int | None]] = []
        self.is_clock_running = False
        self.beat = 0.0
        self.closed = False
        FakePlayer.instances.append(self)

    @staticmethod
    def is_available() -> bool:
        return FakePlayer.available

    def play_sound(self, sound, *, volume=1.0, pan=0.0, at_beat=None) -> None:
        self.played.append((sound, volume, pan, at_beat))

    def start_clock(self) -> None:
        self.is_clock_running = True

    def pause_clock(self) -> None:
        self.is_clock_running = False

    def stop_clock(self) -> None:
        self.is_clock_running = False
        self.beat = 0.0

    def set_tempo(self, beats_per_minute: float) -> None:
        self.tempo = beats_per_minute

    def close(self) -> None:
        self.closed = True


class FakeMicrophone:
    level = 0.25

    def __init__(self) -> None:
        self.closed = False

    def level_history(self, count: int) -> list[float]:
        return [0.1] * count

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def fake_devices(monkeypatch):
    FakePlayer.available = True
    FakePlayer.instances = []
    monkeypatch.setattr(audio_module, 'TerminalAudioPlayer', FakePlayer)
    monkeypatch.setattr(audio_module, 'TerminalMicrophone', FakeMicrophone)


@pytest.fixture
def canvas():
    """A canvas that runs by itself, so it plays on the (replaced) device."""
    with xnano.new(realtime=True, width=20, height=3) as canvas:
        yield canvas


@pytest.fixture
def manual():
    """A canvas whose clock you move, which records what is played."""
    with xnano.new(width=20, height=3, fps=10) as canvas:
        yield canvas


def played(canvas) -> list:
    """What reached the device, once the canvas's loop handled everything handed to it."""
    canvas.output.render()
    return FakePlayer.instances[-1].played if FakePlayer.instances else []


class TestPlay:
    def test_a_note_name_is_played_with_the_default_instrument(self, canvas):
        canvas.audio.play('C4')
        sound = played(canvas)[0][0]
        assert sound == render_note('piano', 'C4')

    def test_a_midi_number_is_a_pitch(self, canvas):
        canvas.audio.play(60, instrument='bell')
        assert played(canvas)[0][0] == render_note('bell', 60)

    def test_a_frequency_in_hertz_is_a_pitch(self, canvas):
        canvas.audio.play('440hz')
        assert played(canvas)[0][0] == render_note('piano', '440hz')

    def test_a_note_object_lasts_for_its_beats_at_the_tempo(self, canvas):
        canvas.bpm = 60
        canvas.audio.play(TerminalNote('A4', duration_beats=2.0))
        sound = played(canvas)[0][0]
        assert sound.duration_milliseconds >= 2000

    def test_a_melody_is_rendered_and_played_once(self, canvas):
        melody = TerminalMelody([TerminalNote('C4'), TerminalNote('E4', start_beats=1)])
        canvas.audio.play(melody, instrument='piano')
        assert played(canvas)[0][0] == melody.render('piano')

    def test_a_sound_is_played_as_it_is_with_volume_and_pan(self, canvas):
        sound = render_note('bell', 'C6')
        canvas.audio.play(sound, volume=0.5, pan=-1.0)
        assert played(canvas)[0] == (sound, 0.5, -1.0, None)

    def test_effects_are_applied_to_a_sound(self, canvas):
        sound = render_note('bell', 'C6')
        effects = [TerminalAudioEffect.reverb()]
        canvas.audio.play(sound, effects=effects)
        assert played(canvas)[0][0] == sound.with_effects(effects)

    def test_scheduling_on_a_beat_starts_the_clock(self, canvas):
        canvas.audio.play('C4', at_beat=4)
        played(canvas)
        player = FakePlayer.instances[-1]
        assert player.is_clock_running
        assert player.played[0][3] == 4

    def test_playing_without_a_device_says_what_to_do(self, canvas):
        FakePlayer.available = False
        assert not canvas.audio.is_available
        with pytest.raises(TerminalAudioUnavailableError, match='is_available'):
            canvas.audio.play('C4')

    def test_it_can_be_played_from_another_thread_on_a_running_canvas(self, canvas):
        import threading

        thread = threading.Thread(target=lambda: canvas.audio.play('C4'))
        thread.start()
        thread.join()
        assert len(played(canvas)) == 1

    def test_the_devices_are_released_when_the_canvas_closes(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            canvas.audio.play('C4')
            played(canvas)
        assert FakePlayer.instances[-1].closed


class TestClock:
    def test_the_tempo_is_kept_and_applied(self, canvas):
        canvas.audio.play('C4')
        played(canvas)
        canvas.bpm = 90
        assert canvas.bpm == 90
        played(canvas)
        assert FakePlayer.instances[-1].tempo == 90

    @pytest.mark.parametrize('tempo', [0, -5, 600001])
    def test_a_tempo_out_of_range_is_refused(self, canvas, tempo):
        with pytest.raises(ValueError, match='out of range'):
            canvas.bpm = tempo

    def test_the_clock_starts_pauses_and_stops(self, canvas):
        canvas.audio.start()
        played(canvas)
        player = FakePlayer.instances[-1]
        assert player.is_clock_running
        canvas.audio.pause()
        played(canvas)
        assert not player.is_clock_running

    def test_stopping_time_holds_the_musical_clock(self, canvas):
        canvas.audio.start()
        played(canvas)
        player = FakePlayer.instances[-1]
        canvas.stop()
        played(canvas)
        assert not player.is_clock_running
        canvas.resume()
        played(canvas)
        assert player.is_clock_running


class TestExpressions:
    def test_the_microphone_level_is_an_expression(self, canvas):
        assert canvas.inspect(canvas.audio.level) == 0.25

    def test_the_level_drives_a_position(self, canvas):
        meter = canvas.write('#', y=1)
        meter.x = canvas.audio.level * 16
        assert canvas.output.render() is not None
        import time

        deadline = time.monotonic() + 3
        while meter.x != 4 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert meter.x == 4

    def test_the_level_combines_with_the_rest_of_the_language(self, canvas):
        assert canvas.inspect(canvas.audio.level * Width) == 5.0

    def test_the_beat_follows_the_player(self, canvas):
        assert canvas.inspect(canvas.audio.beat) == 0.0
        canvas.audio.start()
        played(canvas)
        FakePlayer.instances[-1].beat = 2.5
        assert canvas.inspect(canvas.audio.beat % 1) == 0.5

    def test_the_level_history_is_read_from_the_microphone(self, canvas):
        assert canvas.audio.level_history(3) == [0.1, 0.1, 0.1]

    def test_a_missing_microphone_reads_as_silence(self, monkeypatch, canvas):
        class Broken:
            def __init__(self) -> None:
                raise audio_module.TerminalAudioError('no input device')

        monkeypatch.setattr(audio_module, 'TerminalMicrophone', Broken)
        assert canvas.inspect(canvas.audio.level) == 0.0
        assert canvas.audio.level_history(2) == []


class TestInHooks:
    def test_a_hook_plays_a_note_on_a_key(self, canvas):
        @canvas.hook(when=lambda context: context.keyboard is not None)
        def press(context: xnano.context.Context) -> None:
            context.audio.play(context.keyboard.key)

        canvas.push(Event.key_press('c'))
        import time

        deadline = time.monotonic() + 3
        while not played(canvas) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(played(canvas)) == 1


class TestRecording:
    """A canvas whose clock you move has no device: what is played is recorded."""

    def test_a_canvas_without_a_device_records_and_renders_each_step(self, manual):
        assert manual.audio.is_offline
        assert manual.audio.is_available
        manual.audio.play('C4', instrument='bell')
        manual.step()
        sound = manual.audio.render_sound()
        assert sound.duration_milliseconds == pytest.approx(100.0, abs=1.0)
        assert max(abs(sample) for sample in sound.samples()) > 0.0
        assert FakePlayer.instances == [], 'no device is opened'

    def test_playing_records_without_synthesizing(self, manual, monkeypatch):
        calls: list[str] = []
        real = audio_module.render_note

        def counting(*arguments, **keywords):
            calls.append('render')
            return real(*arguments, **keywords)

        monkeypatch.setattr(audio_module, 'render_note', counting)
        manual.audio.play('C4')
        manual.audio.play('E4')
        assert calls == []
        manual.step()
        manual.audio.render_sound()
        assert len(calls) == 2

    def test_a_note_rings_on_into_the_next_window(self, manual):
        manual.audio.play('C4', duration_milliseconds=300)
        manual.step()
        first = manual.audio.render_sound()
        manual.step()
        second = manual.audio.render_sound()
        assert max(abs(sample) for sample in first.samples()) > 0.0
        assert max(abs(sample) for sample in second.samples()) > 0.0

    def test_a_second_render_at_the_same_time_is_silent(self, manual):
        manual.audio.play('C4')
        manual.step()
        manual.audio.render_sound()
        again = manual.audio.render_sound()
        assert again.samples() == [0.0]

    def test_a_note_played_later_starts_later(self, manual):
        manual.step()
        manual.audio.render_sound()
        manual.step(delta_seconds=0.05)
        manual.audio.play('C4')
        manual.step(delta_seconds=0.05)
        sound = manual.audio.render_sound()
        samples = sound.samples()
        half = len(samples) // 2
        assert max(abs(sample) for sample in samples[: half - 50]) == 0.0
        assert max(abs(sample) for sample in samples[half:]) > 0.0

    def test_old_recordings_are_not_kept_for_ever(self, manual):
        manual.audio.play('C4')
        manual.step(delta_seconds=120.0)
        manual.audio.play('E4')
        assert len(manual.audio._recordings) == 1

    def test_arguments_are_checked_when_playing(self, manual):
        with pytest.raises(ValueError, match='not an instrument'):
            manual.audio.play('C4', instrument='kazoo')  # type: ignore[arg-type]
        with pytest.raises(ValueError, match='unrecognized pitch'):
            manual.audio.play('X9')
        with pytest.raises(ValueError, match='velocity'):
            manual.audio.play('C4', velocity=2.0)

    @pytest.mark.parametrize(
        ('arguments', 'error', 'message'),
        [
            ({'source': 'C4', 'pan': 5}, ValueError, 'pan must be between'),
            ({'source': 'C4', 'at_beat': -1}, ValueError, 'at_beat must be 0 or more'),
            ({'source': 'C4', 'effects': [1]}, TypeError, 'effects must hold audio'),
            ({'source': 300}, ValueError, 'MIDI pitch 300'),
            ({'source': -1}, ValueError, 'MIDI pitch -1'),
            ({'source': 0.5}, ValueError, 'frequency 0.5 Hz'),
            ({'source': 'abchz'}, ValueError, 'not a frequency'),
            ({'source': '5hz'}, ValueError, 'frequency 5.0 Hz'),
            ({'source': 'C4', 'duration_milliseconds': -5}, ValueError, 'between 1 and'),
            (
                {'source': 'C4', 'duration_milliseconds': 60001},
                ValueError,
                'between 1 and',
            ),
        ],
    )
    def test_every_bad_argument_is_rejected_where_play_is_called(
        self, manual, arguments, error, message
    ):
        with pytest.raises(error, match=message):
            manual.audio.play(**arguments)
        manual.step(delta_seconds=1.0)
        assert (
            max(abs(sample) for sample in manual.audio.render_sound().samples()) == 0.0
        ), 'a rejected call records nothing'

    def test_good_frequencies_are_recorded(self, manual):
        manual.audio.play(60)
        manual.audio.play(440.0)
        manual.audio.play('440hz')
        manual.step(delta_seconds=0.5)
        assert max(abs(sample) for sample in manual.audio.render_sound().samples()) > 0.0

    def test_a_canvas_on_a_device_does_not_record(self, canvas):
        with pytest.raises(xnano.errors.TerminalError, match='render_sound'):
            canvas.audio.render_sound()

    def test_the_beat_moves_with_the_manual_clock_and_the_tempo(self, manual):
        manual.bpm = 120
        assert manual.inspect(manual.audio.beat) == 0.0
        manual.audio.start()
        manual.step(delta_seconds=1.0)
        assert manual.inspect(manual.audio.beat) == pytest.approx(2.0)
        manual.bpm = 60
        assert manual.inspect(manual.audio.beat) == pytest.approx(2.0), (
            'a change of tempo changes the rate, not the position'
        )
        manual.step(delta_seconds=1.0)
        assert manual.inspect(manual.audio.beat) == pytest.approx(3.0)

    def test_stopping_time_and_the_audio_verbs_hold_the_beat(self, manual):
        manual.audio.start()
        manual.step(delta_seconds=0.5)
        manual.audio.pause()
        manual.step(delta_seconds=0.5)
        assert manual.inspect(manual.audio.beat) == pytest.approx(1.0)
        manual.audio.resume()
        manual.step(delta_seconds=0.5)
        assert manual.inspect(manual.audio.beat) == pytest.approx(2.0)
        manual.audio.stop()
        assert manual.inspect(manual.audio.beat) == 0.0

    def test_a_new_note_object_is_never_heard_as_an_earlier_one(self, manual):
        def crossings(sound: TerminalSound) -> int:
            samples = sound.samples()
            return sum(
                1
                for previous, current in zip(samples, samples[1:], strict=False)
                if (previous < 0.0) != (current < 0.0)
            )

        counts: dict[str, list[int]] = {'C4': [], 'C6': []}
        for index in range(200):
            pitch = 'C4' if index % 2 == 0 else 'C6'
            manual.audio.play(TerminalNote(pitch, duration_beats=0.2))
            manual.step(delta_seconds=2.0)
            counts[pitch].append(crossings(manual.audio.render_sound()))
        assert max(counts['C4']) < min(counts['C6']), (
            'every render has the pitch of the note that was played'
        )

    def test_the_same_melody_text_is_synthesized_once(self, manual):
        manual.audio.play('C4 E4')
        manual.step(delta_seconds=2.0)
        manual.audio.render_sound()
        manual.audio.play('C4 E4')
        manual.step(delta_seconds=2.0)
        manual.audio.render_sound()
        assert len(manual.audio._synthesized) == 1

    def test_a_beat_in_the_future_starts_on_that_beat(self, manual):
        manual.audio.play('C4', at_beat=1)
        recording = manual.audio._recordings[-1]
        assert recording.start_seconds == pytest.approx(0.5)


class TestTerminalSoundShortcuts:
    def test_melody_text_reads_notes_lengths_chords_and_rests(self):
        from xnano.audio import _parse_melody

        melody = _parse_melody('C4 E4:0.5 rest G4+B4:2 - C5', 120)
        assert [
            (note.name, note.start_beats, note.duration_beats) for note in melody.notes
        ] == [
            ('C4', 0.0, 1.0),
            ('E4', 1.0, 0.5),
            ('G4', 2.5, 2.0),
            ('B4', 2.5, 2.0),
            ('C5', 5.5, 1.0),
        ]

    def test_a_wrong_note_in_melody_text_is_explained(self):
        from xnano.audio import _parse_melody

        with pytest.raises(ValueError, match="'X9' is not a note in the melody"):
            _parse_melody('C4 X9', 120)

    def test_the_canvas_keeps_the_tempo_that_audio_uses(self):
        with xnano.new(width=8, height=1, bpm=90) as canvas:
            assert canvas.bpm == 90
            canvas.bpm = 100
            assert canvas.bpm == 100
            assert not hasattr(canvas.audio, 'tempo')

    def test_every_beat_follows_the_tempo(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.bpm = 120  # a beat is half a second
            beats = []

            @canvas.every(beats=1)
            def count(context):
                beats.append(round(context.time.elapsed, 2))

            for _ in range(16):
                canvas.step(delta_seconds=0.1)
            assert beats[:3] == pytest.approx([0.5, 1.0, 1.5], abs=0.11)
            assert len(beats) == 3

    def test_every_needs_exactly_one_unit(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(ValueError, match='either seconds or beats'):
                canvas.every()
            with pytest.raises(ValueError, match='either seconds or beats'):
                canvas.every(1, beats=1)

    def test_play_records_melody_text_on_a_canvas_without_a_device(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.play('C4 E4 G4:2')
            canvas.play(TerminalNote('C5', duration_beats=0.5), instrument='bell')
            canvas.step(delta_seconds=0.5)
            assert canvas.audio.render_sound().duration_milliseconds == 500.0
            assert not hasattr(canvas, 'note')
