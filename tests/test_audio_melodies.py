"""
tests.test_audio_melodies

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
import xnano.audio._microphone as microphone_module
import xnano.audio._player as player_module
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
    sample_rate = 48000
    channels = 1
    is_open = True

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
    monkeypatch.setattr(player_module, 'TerminalAudioPlayer', FakePlayer)
    monkeypatch.setattr(microphone_module, 'TerminalMicrophone', FakeMicrophone)


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
    canvas.screen.output.render()
    return FakePlayer.instances[-1].played if FakePlayer.instances else []


class TestPlay:
    def test_a_note_name_is_played_with_the_default_instrument(self, canvas):
        canvas.speaker.play('C4')
        sound = played(canvas)[0][0]
        assert sound == render_note('piano', 'C4')

    def test_a_midi_number_is_a_pitch(self, canvas):
        canvas.speaker.play(60, instrument='bell')
        assert played(canvas)[0][0] == render_note('bell', 60)

    def test_a_frequency_in_hertz_is_a_pitch(self, canvas):
        canvas.speaker.play('440hz')
        assert played(canvas)[0][0] == render_note('piano', '440hz')

    def test_a_note_object_lasts_for_its_beats_at_the_tempo(self, canvas):
        canvas.clock.bpm = 60
        canvas.speaker.play(TerminalNote('A4', duration_beats=2.0))
        sound = played(canvas)[0][0]
        assert sound.duration_milliseconds >= 2000

    def test_a_melody_is_rendered_and_played_once(self, canvas):
        melody = TerminalMelody([TerminalNote('C4'), TerminalNote('E4', start_beats=1)])
        canvas.speaker.play(melody, instrument='piano')
        assert played(canvas)[0][0] == melody.render('piano')

    def test_a_sound_is_played_as_it_is_with_volume_and_pan(self, canvas):
        sound = render_note('bell', 'C6')
        canvas.speaker.play(sound, volume=0.5, pan=-1.0)
        assert played(canvas)[0] == (sound, 0.5, -1.0, None)

    def test_effects_are_applied_to_a_sound(self, canvas):
        sound = render_note('bell', 'C6')
        effects = [TerminalAudioEffect.reverb()]
        canvas.speaker.play(sound, effects=effects)
        assert played(canvas)[0][0] == sound.with_effects(effects)

    def test_scheduling_on_a_beat_starts_the_clock(self, canvas):
        canvas.speaker.play('C4', at_beat=4)
        played(canvas)
        player = FakePlayer.instances[-1]
        assert player.is_clock_running
        assert player.played[0][3] == 4

    def test_playing_without_a_device_says_what_to_do(self, canvas):
        FakePlayer.available = False
        assert not canvas.speaker.is_available
        with pytest.raises(TerminalAudioUnavailableError, match='is_available'):
            canvas.speaker.play('C4')

    def test_it_can_be_played_from_another_thread_on_a_running_canvas(self, canvas):
        import threading

        thread = threading.Thread(target=lambda: canvas.speaker.play('C4'))
        thread.start()
        thread.join()
        assert len(played(canvas)) == 1

    def test_the_devices_are_released_when_the_canvas_closes(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            canvas.speaker.play('C4')
            played(canvas)
        assert FakePlayer.instances[-1].closed


class TestClock:
    def test_the_tempo_is_kept_and_applied(self, canvas):
        canvas.speaker.play('C4')
        played(canvas)
        canvas.clock.bpm = 90
        assert canvas.clock.bpm == 90
        played(canvas)
        assert FakePlayer.instances[-1].tempo == 90

    @pytest.mark.parametrize('tempo', [0, -5, 600001])
    def test_a_tempo_out_of_range_is_refused(self, canvas, tempo):
        with pytest.raises(ValueError, match='out of range'):
            canvas.clock.bpm = tempo

    def test_the_clock_starts_pauses_and_stops(self, canvas):
        canvas.clock.beats.start()
        played(canvas)
        player = FakePlayer.instances[-1]
        assert player.is_clock_running
        canvas.clock.beats.pause()
        played(canvas)
        assert not player.is_clock_running

    def test_stopping_time_holds_the_musical_clock(self, canvas):
        canvas.clock.beats.start()
        played(canvas)
        player = FakePlayer.instances[-1]
        canvas.clock.pause()
        played(canvas)
        assert not player.is_clock_running
        canvas.clock.resume()
        played(canvas)
        assert player.is_clock_running


class TestExpressions:
    def test_the_microphone_level_is_an_expression(self, canvas):
        assert canvas.evaluate(canvas.microphone.level) == 0.25

    def test_the_level_drives_a_position(self, canvas):
        meter = canvas.screen.write('#', y=1)
        meter.x = canvas.microphone.level * 16
        assert canvas.screen.output.render() is not None
        import time

        deadline = time.monotonic() + 3
        while meter.x != 4 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert meter.x == 4

    def test_the_level_combines_with_the_rest_of_the_language(self, canvas):
        assert canvas.evaluate(canvas.microphone.level * Width) == 5.0

    def test_the_beat_follows_the_player(self, canvas):
        assert canvas.evaluate(canvas.clock.beats.position) == 0.0
        canvas.clock.beats.start()
        played(canvas)
        FakePlayer.instances[-1].beat = 2.5
        assert canvas.evaluate(canvas.clock.beats.position % 1) == 0.5

    def test_the_level_history_is_read_from_the_microphone(self, canvas):
        assert canvas.microphone.level_history(3) == [0.1, 0.1, 0.1]

    def test_a_missing_microphone_reads_as_silence(self, monkeypatch, canvas):
        class Broken:
            def __init__(self) -> None:
                raise microphone_module.TerminalAudioError('no input device')

        monkeypatch.setattr(microphone_module, 'TerminalMicrophone', Broken)
        assert canvas.evaluate(canvas.microphone.level) == 0.0
        assert canvas.microphone.level_history(2) == []


class TestInHooks:
    def test_a_hook_plays_a_note_on_a_key(self, canvas):
        @canvas.hook(on=lambda context: context.keyboard.key is not None)
        def press(context: xnano.hooks.Context) -> None:
            context.speaker.play(context.keyboard.key)

        canvas.push(Event.key_press('c'))
        import time

        deadline = time.monotonic() + 3
        while not played(canvas) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(played(canvas)) == 1


class TestRecording:
    """A canvas whose clock you move has no device: what is played is recorded."""

    def test_a_canvas_without_a_device_records_and_renders_each_step(self, manual):
        assert manual.speaker.is_offline
        assert manual.speaker.is_available
        manual.speaker.play('C4', instrument='bell')
        manual.clock.step()
        sound = manual.speaker.render()
        assert sound.duration_milliseconds == pytest.approx(100.0, abs=1.0)
        assert max(abs(sample) for sample in sound.samples()) > 0.0
        assert FakePlayer.instances == [], 'no device is opened'

    def test_playing_records_without_synthesizing(self, manual, monkeypatch):
        calls: list[str] = []
        real = player_module.render_note

        def counting(*arguments, **keywords):
            calls.append('render')
            return real(*arguments, **keywords)

        monkeypatch.setattr(player_module, 'render_note', counting)
        manual.speaker.play('C4')
        manual.speaker.play('E4')
        assert calls == []
        manual.clock.step()
        manual.speaker.render()
        assert len(calls) == 2

    def test_a_note_rings_on_into_the_next_window(self, manual):
        manual.speaker.play('C4', beats=0.6)
        manual.clock.step()
        first = manual.speaker.render()
        manual.clock.step()
        second = manual.speaker.render()
        assert max(abs(sample) for sample in first.samples()) > 0.0
        assert max(abs(sample) for sample in second.samples()) > 0.0

    def test_a_second_render_at_the_same_time_is_silent(self, manual):
        manual.speaker.play('C4')
        manual.clock.step()
        manual.speaker.render()
        again = manual.speaker.render()
        assert again.samples() == [0.0]

    def test_a_note_played_later_starts_later(self, manual):
        manual.clock.step()
        manual.speaker.render()
        manual.clock.step(delta_seconds=0.05)
        manual.speaker.play('C4')
        manual.clock.step(delta_seconds=0.05)
        sound = manual.speaker.render()
        samples = sound.samples()
        half = len(samples) // 2
        assert max(abs(sample) for sample in samples[: half - 50]) == 0.0
        assert max(abs(sample) for sample in samples[half:]) > 0.0

    def test_old_recordings_are_not_kept_for_ever(self, manual):
        manual.speaker.play('C4')
        manual.clock.step(delta_seconds=120.0)
        manual.speaker.play('E4')
        assert len(manual._audio_device()._recordings) == 1

    def test_arguments_are_checked_when_playing(self, manual):
        with pytest.raises(ValueError, match='not an instrument'):
            manual.speaker.play('C4', instrument='kazoo')  # type: ignore[arg-type]
        with pytest.raises(ValueError, match='is not a known sound symbol, a note name'):
            manual.speaker.play('X9')
        with pytest.raises(ValueError, match='velocity'):
            manual.speaker.play('C4', velocity=2.0)

    @pytest.mark.parametrize(
        ('arguments', 'error', 'message'),
        [
            ({'source': 'C4', 'pan': 5}, ValueError, 'pan must be between'),
            ({'source': 'C4', 'at_beat': -1}, ValueError, 'at_beat must be 0 or more'),
            (
                {'source': 'C4', 'at_beat': 'a'},
                TypeError,
                'at_beat must be a whole number',
            ),
            ({'source': 'C4', 'effects': [1]}, TypeError, 'effects= takes dictionaries'),
            ({'source': 300}, ValueError, 'MIDI pitch 300'),
            ({'source': -1}, ValueError, 'MIDI pitch -1'),
            ({'source': 0.5}, ValueError, 'frequency 0.5 Hz'),
            ({'source': 'abchz'}, ValueError, 'not a frequency'),
            ({'source': '5hz'}, ValueError, 'frequency 5.0 Hz'),
            ({'source': 'C4', 'beats': -5}, ValueError, 'beats must be a length'),
            ({'source': 'C4', 'beats': 0}, ValueError, 'beats must be a length'),
            ({'source': 'C4', 'beats': 2001}, ValueError, 'beats must be a length'),
            (
                {'source': 'C4', 'beats': float('nan')},
                ValueError,
                'beats must be a number',
            ),
            ({'source': 'C4', 'volume': 2.0}, ValueError, 'volume must be'),
        ],
    )
    def test_every_bad_argument_is_rejected_where_play_is_called(
        self, manual, arguments, error, message
    ):
        with pytest.raises(error, match=message):
            manual.speaker.play(arguments.pop('source'), **arguments)
        manual.clock.step(delta_seconds=1.0)
        assert max(abs(sample) for sample in manual.speaker.render().samples()) == 0.0, (
            'a rejected call records nothing'
        )

    def test_good_frequencies_are_recorded(self, manual):
        manual.speaker.play(60)
        manual.speaker.play(440.0)
        manual.speaker.play('440hz')
        manual.clock.step(delta_seconds=0.5)
        assert max(abs(sample) for sample in manual.speaker.render().samples()) > 0.0

    def test_a_canvas_on_a_device_does_not_record(self, canvas):
        with pytest.raises(xnano.errors.TerminalError, match=r'speaker\.render'):
            canvas.speaker.render()

    def test_the_beat_moves_with_the_manual_clock_and_the_tempo(self, manual):
        manual.clock.bpm = 120
        assert manual.evaluate(manual.clock.beats.position) == 0.0
        manual.clock.beats.start()
        manual.clock.step(delta_seconds=1.0)
        assert manual.evaluate(manual.clock.beats.position) == pytest.approx(2.0)
        manual.clock.bpm = 60
        assert manual.evaluate(manual.clock.beats.position) == pytest.approx(2.0), (
            'a change of tempo changes the rate, not the position'
        )
        manual.clock.step(delta_seconds=1.0)
        assert manual.evaluate(manual.clock.beats.position) == pytest.approx(3.0)

    def test_stopping_a_stopped_canvas_still_resumes_the_beat(self, manual):
        manual.clock.beats.start()
        manual.clock.step(delta_seconds=0.5)
        manual.clock.pause()
        manual.clock.pause()
        manual.clock.step(delta_seconds=0.5)
        manual.clock.resume()
        manual.clock.step(delta_seconds=0.5)
        assert manual.evaluate(manual.clock.beats.position) == pytest.approx(2.0)

    def test_a_formula_that_reads_the_beat_still_draws_in_the_outer_canvas(self):
        child = xnano.new(width=10, height=2)
        child.clock.beats.start()
        dot = child.screen.write('o')
        dot.x = child.clock.beats.position * 4
        child.clock.step(delta_seconds=0.5)
        with xnano.new(width=20, height=4) as outer:
            outer.screen.write(child)
            outer.clock.step(delta_seconds=0.5)
            assert dot.x == 0

    def test_stopping_time_and_the_audio_verbs_hold_the_beat(self, manual):
        manual.clock.beats.start()
        manual.clock.step(delta_seconds=0.5)
        manual.clock.beats.pause()
        manual.clock.step(delta_seconds=0.5)
        assert manual.evaluate(manual.clock.beats.position) == pytest.approx(1.0)
        manual.clock.beats.resume()
        manual.clock.step(delta_seconds=0.5)
        assert manual.evaluate(manual.clock.beats.position) == pytest.approx(2.0)
        manual.clock.beats.stop()
        assert manual.evaluate(manual.clock.beats.position) == 0.0

    def test_starting_the_clock_on_a_stopped_canvas_starts_it_held(self, manual):
        manual.clock.pause()
        manual.clock.beats.start()
        manual.clock.step(delta_seconds=0.5)
        manual.clock.step(delta_seconds=0.5)
        assert manual.evaluate(manual.clock.beats.position) == pytest.approx(0.0)
        manual.clock.resume()
        manual.clock.step(delta_seconds=0.5)
        assert manual.evaluate(manual.clock.beats.position) == pytest.approx(1.0)

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
            manual.speaker.play(TerminalNote(pitch, duration_beats=0.2))
            manual.clock.step(delta_seconds=2.0)
            counts[pitch].append(crossings(manual.speaker.render()))
        assert max(counts['C4']) < min(counts['C6']), (
            'every render has the pitch of the note that was played'
        )

    def test_the_same_melody_text_is_synthesized_once(self, manual):
        manual.speaker.play('C4 E4')
        manual.clock.step(delta_seconds=2.0)
        manual.speaker.render()
        manual.speaker.play('C4 E4')
        manual.clock.step(delta_seconds=2.0)
        manual.speaker.render()
        assert len(manual._audio_device()._synthesized) == 1

    def test_a_beat_in_the_future_starts_on_that_beat(self, manual):
        manual.speaker.play('C4', at_beat=1)
        recording = manual._audio_device()._recordings[-1]
        assert recording.start_seconds == pytest.approx(0.5)


class TestTerminalSoundShortcuts:
    def test_melody_text_reads_notes_lengths_chords_and_rests(self):
        melody = xnano.audio.Melody('C4 E4:0.5 rest G4+B4:2 - C5', bpm=120)
        assert [
            (note.name, note.start_beats, note.duration_beats)
            for note in melody.score.notes
        ] == [
            ('C4', 0.0, 1.0),
            ('E4', 1.0, 0.5),
            ('G4', 2.5, 2.0),
            ('B4', 2.5, 2.0),
            ('C5', 5.5, 1.0),
        ]

    def test_a_wrong_note_in_melody_text_is_explained(self):
        with pytest.raises(ValueError, match="'X9' is not a note in the melody"):
            xnano.audio.Melody('C4 X9')

    def test_the_canvas_keeps_the_tempo_that_audio_uses(self):
        with xnano.new(width=8, height=1, bpm=90) as canvas:
            assert canvas.clock.bpm == 90
            canvas.clock.bpm = 100
            assert canvas.clock.bpm == 100
            assert not hasattr(canvas.speaker, 'tempo')

    def test_every_beat_follows_the_tempo(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.clock.bpm = 120  # a beat is half a second
            beats = []

            @canvas.hook(on='beat', every=1)
            def count(context):
                beats.append(round(context.clock.elapsed_seconds, 2))

            for _ in range(16):
                canvas.clock.step(delta_seconds=0.1)
            assert beats[:3] == pytest.approx([0.5, 1.0, 1.5], abs=0.11)
            assert len(beats) == 3

    def test_every_and_after_have_one_unit_per_kind_of_hook(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(ValueError, match='needs an on='):
                canvas.hook(lambda context: None, every=1)
            with pytest.raises(ValueError, match='cannot be given together'):
                canvas.hook(lambda context: None, on='beat', every=1, after=2)
            with pytest.raises(ValueError, match="2 seconds for on='tick' and 2 beats"):
                canvas.hook(lambda context: None, on='key', every=2)

    def test_play_records_melody_text_on_a_canvas_without_a_device(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.speaker.play('C4 E4 G4:2')
            canvas.speaker.play(TerminalNote('C5', duration_beats=0.5), instrument='bell')
            canvas.clock.step(delta_seconds=0.5)
            assert canvas.speaker.render().duration_milliseconds == 500.0
            assert not hasattr(canvas, 'note')


class TestMelody:
    def test_it_knows_its_length(self):
        melody = xnano.audio.Melody('C4 E4 G4:2', bpm=120)
        assert melody.length_beats == 4.0
        assert melody.duration_seconds == 2.0
        assert xnano.audio.Melody('C4 C4', bpm=60).duration_seconds == 2.0

    def test_it_keeps_what_it_was_made_from(self):
        melody = xnano.audio.Melody('C4 E4', bpm=90, beats=0.5)
        assert (melody.text, melody.bpm, melody.beats, melody.symbol) == (
            'C4 E4',
            90.0,
            0.5,
            None,
        )
        assert [note.name for note in melody.score.notes] == ['C4', 'E4']
        assert melody.score.duration_seconds == pytest.approx(1.0 * 60.0 / 90.0, rel=1e-6)

    def test_a_note_without_a_length_lasts_the_default_beats(self):
        assert xnano.audio.Melody('C4 E4', beats=2.0).length_beats == 4.0

    def test_playing_a_melody_records_one_sound(self, manual):
        melody = xnano.audio.Melody('C4 E4 G4:2', bpm=120)
        manual.speaker.play(melody)
        assert len(manual._audio_device()._recordings) == 1
        manual.clock.step(delta_seconds=1.0)
        assert manual.speaker.render().peak > 0.0

    def test_it_plays_at_its_own_tempo_whatever_the_canvas_tempo(self, manual):
        melody = xnano.audio.Melody('C4 C4', bpm=60)
        manual.clock.bpm = 240
        manual.speaker.play(melody)
        recording = manual._audio_device()._recordings[-1]
        assert recording.end_seconds - recording.start_seconds >= 2.0

    def test_a_melody_is_not_synthesized_again_for_the_same_object(self, manual):
        melody = xnano.audio.Melody('C4 E4')
        for _ in range(2):
            manual.speaker.play(melody)
            manual.clock.step(delta_seconds=2.0)
            manual.speaker.render()
        assert len(manual._audio_device()._synthesized) == 1

    def test_it_is_played_by_the_device_of_a_running_canvas(self, canvas):
        melody = xnano.audio.Melody('C4 E4')
        canvas.speaker.play(melody)
        assert played(canvas)[0][0] == melody.score.render('piano')

    def test_a_symbol_names_a_melody_to_play(self, manual):
        melody = xnano.audio.Melody('C4 E4', symbol='melody_symbol')
        try:
            assert (
                xnano.symbols.lookup('melody_symbol', kind=xnano.audio.Melody) is melody
            )
            manual.speaker.play('melody_symbol')
            assert len(manual._audio_device()._recordings) == 1
        finally:
            xnano.symbols.remove('melody_symbol')

    def test_a_melody_in_a_sequence_plays_after_the_note_before_it(self, manual):
        melody = xnano.audio.Melody('C4 E4', bpm=120)
        manual.speaker.play([xnano.Note('C4'), melody])
        starts = sorted(item.start_seconds for item in manual._audio_device()._recordings)
        assert starts == pytest.approx([0.0, 0.5])

    def test_it_is_a_value_that_cannot_change(self):
        melody = xnano.audio.Melody('C4')
        with pytest.raises(AttributeError):
            melody.bpm = 90.0  # type: ignore[misc]

    def test_it_can_be_hashed_and_compared_by_what_it_was_made_from(self):
        melody = xnano.audio.Melody('C4 E4', bpm=90)
        same = xnano.audio.Melody('C4 E4', bpm=90)
        other = xnano.audio.Melody('C4 E4', bpm=100)
        assert melody == same
        assert hash(melody) == hash(same)
        assert melody != other
        assert len({melody, same, other}) == 2

    @pytest.mark.parametrize(
        ('arguments', 'message'),
        [
            ({'bpm': 0}, 'Use 120.0 for an ordinary tempo'),
            ({'bpm': -60}, 'bpm to be a finite number above 0'),
            ({'bpm': float('nan')}, 'bpm to be a finite number above 0'),
            ({'bpm': float('inf')}, 'bpm to be a finite number above 0'),
            ({'beats': -1}, 'beats to be a finite number above 0'),
            ({'beats': 0}, 'beats to be a finite number above 0'),
        ],
    )
    def test_a_tempo_or_length_that_is_not_above_zero_is_explained(
        self, arguments, message
    ):
        with pytest.raises(ValueError, match=message):
            xnano.audio.Melody('C4', **arguments)

    def test_it_needs_text(self):
        with pytest.raises(TypeError, match='Melody needs melody text'):
            xnano.audio.Melody(5)  # type: ignore[arg-type]


class TestMelodyRegion:
    def test_a_melody_with_a_chord_and_rests_spans_its_beats_and_pitches(self):
        region = xnano.audio.Melody('C4+E4+G4 rest:2 C5', bpm=120).region
        assert region.resolution == 'beats'
        assert (region.x, region.width) == (0.0, 4.0)
        assert (region.y, region.height) == (60, 13)

    def test_a_trailing_rest_counts_towards_the_length(self):
        region = xnano.audio.Melody('C4 E4 rest:2').region
        assert region.width == 4.0
        assert (region.y, region.height) == (60, 5)

    def test_a_melody_of_only_rests_spans_no_pitches(self):
        region = xnano.audio.Melody('rest rest:2').region
        assert (region.x, region.width) == (0.0, 3.0)
        assert region.height == 0
        assert (1.0, region.y) not in region

    def test_the_milliseconds_follow_the_tempo_of_the_melody(self):
        slow = xnano.audio.Melody('C4 E4', bpm=60).region
        assert slow.width == 2.0
        assert slow.milliseconds.width == 2000.0
        fast = xnano.audio.Melody('C4 E4', bpm=240).region
        assert fast.width == 2.0
        assert fast.milliseconds.width == 500.0
        one_beat = xnano.audio.Melody('C4', bpm=60).region
        assert (one_beat.width, one_beat.milliseconds.width) == (1.0, 1000.0)

    def test_the_ticks_are_sixteenth_notes(self):
        sixteenths = xnano.audio.Melody('C4 E4 G4:2', bpm=90).region.sixteenths
        assert (sixteenths.x, sixteenths.width) == (0.0, 16.0)
        assert (sixteenths.y, sixteenths.height) == (60, 8)

    def test_a_tempo_change_in_the_score_is_followed(self):
        # The melody text has no way to write a tempo change, so the score is given one.
        melody = xnano.audio.Melody('C4 E4 G4 C5', bpm=120)
        assert melody.region.milliseconds.width == pytest.approx(2000.0)
        tempo_map = melody.score.tempo_map.with_change(2.0, 60.0)
        object.__setattr__(melody, 'score', melody.score.with_tempo_map(tempo_map))
        # Two beats at 120 bpm last 1 s, then two beats at 60 bpm last 2 s.
        assert melody.region.milliseconds.width == pytest.approx(3000.0)


class TestPlayedRegion:
    """The handle of a played sound knows where the sound is on the timeline of the canvas."""

    def test_a_note_is_a_row_for_its_beats_without_the_ring_after_it(self, manual):
        region = manual.speaker.play(xnano.Note('E4', beats=2))._region
        assert region is not None
        assert region.resolution == 'beats'
        assert (region.x, region.width) == (0.0, 2.0)
        assert (region.y, region.height) == (64, 1)

    def test_it_starts_on_the_beat_the_canvas_has_reached(self, manual):
        manual.clock.step(delta_seconds=1.0)
        region = manual.speaker.play(xnano.Note('E4', beats=2))._region
        assert region is not None
        assert (region.x, region.width) == (2.0, 2.0), 'one second is two beats at 120'
        assert region.milliseconds.x == 1000.0

    def test_it_follows_the_tempo_of_the_canvas(self, manual):
        manual.clock.bpm = 60
        manual.clock.step(delta_seconds=1.0)
        region = manual.speaker.play(xnano.Note('E4', beats=2))._region
        assert region is not None
        assert (region.x, region.width) == (1.0, 2.0)
        assert region.milliseconds.width == 2000.0

    def test_a_beat_to_start_on_is_where_the_region_starts(self, manual):
        region = manual.speaker.play('C4', at_beat=4)._region
        assert region is not None
        assert region.x == 4.0

    def test_a_sequence_lasts_until_its_last_note_stops_and_spans_every_pitch(
        self, manual
    ):
        region = manual.speaker.play(
            [xnano.Note('C4'), xnano.Note(('G4', 'B4'), beats=2)]
        )._region
        assert region is not None
        assert (region.x, region.width) == (0.0, 3.0)
        assert (region.y, region.height) == (60, 12)

    def test_a_frequency_is_the_nearest_note(self, manual):
        for source, pitch in (('440hz', 69), ('261.63Hz', 60), (261.63, 60)):
            region = manual.speaker.play(source)._region
            assert region is not None
            assert (region.y, region.height) == (pitch, 1), source

    def test_a_frequency_out_of_the_midi_range_is_the_edge_of_it(self, manual):
        low = manual.speaker.play('8hz')._region
        high = manual.speaker.play('20000hz')._region
        assert low is not None
        assert high is not None
        assert (low.y, high.y) == (0, 127)

    def test_a_note_name_and_a_number_are_pitches(self, manual):
        region = manual.speaker.play([60, 'E4'])._region
        assert region is not None
        assert (region.y, region.height) == (60, 5)

    def test_a_melody_is_measured_in_beats_of_the_canvas(self, manual):
        melody = xnano.audio.Melody('C4 rest E4:2', bpm=60)
        region = manual.speaker.play(melody)._region
        assert region is not None
        assert (region.x, region.width) == (0.0, 8.0), (
            'four seconds are eight beats at 120'
        )
        assert (region.y, region.height) == (60, 5)

    def test_a_sound_has_one_row_and_lasts_its_duration(self, manual):
        sound = xnano.Audio.from_samples([0.0] * 44100)
        region = manual.speaker.play(sound)._region
        assert region is not None
        assert (region.x, region.width) == (0.0, 2.0)
        assert (region.y, region.height) == (60, 1)

    def test_a_canvas_with_a_device_reports_the_same_region(self, canvas):
        region = canvas.speaker.play(xnano.Note('E4', beats=2), at_beat=4)._region
        assert region is not None
        assert (region.x, region.width) == (4.0, 2.0)
        assert (region.y, region.height) == (64, 1)

    def test_a_device_region_starts_on_the_clock_of_the_canvas(self, canvas):
        region = canvas.speaker.play(xnano.Note('E4'))._region
        assert region is not None
        assert region.x == pytest.approx(canvas.clock.elapsed_seconds * 2.0, abs=0.5)


class TestMicrophone:
    def test_the_level_is_an_expression_on_the_microphone(self, canvas):
        assert canvas.evaluate(canvas.microphone.level) == 0.25

    def test_the_level_shortcut_is_the_same_expression(self, canvas):
        assert canvas.microphone.level is canvas.microphone.level
        assert canvas.evaluate(canvas.microphone.level) == canvas.evaluate(
            canvas.microphone.level
        )

    def test_the_level_history_is_read_from_the_input_device(self, canvas):
        assert canvas.microphone.level_history(2) == [0.1, 0.1]
        assert canvas.microphone.level_history(2) == canvas.microphone.level_history(2)

    def test_the_device_sample_rate_and_channels_are_read(self, canvas):
        microphone = canvas.microphone
        assert microphone.sample_rate == 48000
        assert microphone.channels == 1

    def test_it_is_open_only_after_something_opened_it(self, canvas):
        microphone = canvas.microphone
        assert not microphone.is_open
        assert not microphone.is_open, 'asking does not open the device'
        assert microphone.sample_rate == 48000
        assert microphone.is_open

    def test_it_is_closed_with_the_canvas(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            assert canvas.microphone.sample_rate == 48000
            device = canvas.microphone._device
        assert device is not None
        assert device.closed

    def test_a_canvas_without_a_device_has_a_silent_closed_microphone(self, manual):
        microphone = manual.microphone
        assert manual.evaluate(microphone.level) == 0.0
        assert microphone.level_history(3) == []
        assert not microphone.is_open
        assert microphone.sample_rate is None
        assert microphone.channels is None

    def test_a_missing_input_device_gives_none(self, monkeypatch, canvas):
        class Broken:
            def __init__(self) -> None:
                raise microphone_module.TerminalAudioError('no input device')

        monkeypatch.setattr(microphone_module, 'TerminalMicrophone', Broken)
        microphone = canvas.microphone
        assert microphone.sample_rate is None
        assert microphone.channels is None
        assert not microphone.is_open


class TestRenderingAfterALongGap:
    def test_a_canvas_not_asked_for_a_minute_returns_the_last_minute(self, manual):
        manual.speaker.play('C4')
        manual.clock.step(delta_seconds=200)
        assert manual.speaker.render().duration_milliseconds == pytest.approx(60000.0)

    def test_a_gap_beyond_the_longest_sound_still_renders(self, manual):
        assert manual.speaker.is_offline
        manual.clock.step(delta_seconds=5000)
        sound = manual.speaker.render()
        assert sound.duration_milliseconds == pytest.approx(60000.0)
        manual.speaker.play('C4')
        manual.clock.step()
        assert max(abs(sample) for sample in manual.speaker.render().samples()) > 0.0
