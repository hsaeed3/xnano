"""
tests.test_audio

Sound, notes, melodies and the microphone, with the audio devices replaced.
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
def terminal():
    with xnano.open(offscreen=True, width=20, height=3) as terminal:
        yield terminal


def played(terminal) -> list:
    return FakePlayer.instances[-1].played if FakePlayer.instances else []


class TestPlay:
    def test_a_note_name_is_played_with_the_default_instrument(self, terminal):
        terminal.audio.play('C4')
        sound = played(terminal)[0][0]
        assert sound == render_note('piano', 'C4')

    def test_a_midi_number_is_a_pitch(self, terminal):
        terminal.audio.play(60, instrument='bell')
        assert played(terminal)[0][0] == render_note('bell', 60)

    def test_a_frequency_in_hertz_is_a_pitch(self, terminal):
        terminal.audio.play('440hz')
        assert played(terminal)[0][0] == render_note('piano', '440hz')

    def test_a_note_object_lasts_for_its_beats_at_the_tempo(self, terminal):
        terminal.audio.tempo = 60
        terminal.audio.play(TerminalNote('A4', duration_beats=2.0))
        sound = played(terminal)[0][0]
        assert sound.duration_milliseconds >= 2000

    def test_a_melody_is_rendered_and_played_once(self, terminal):
        melody = TerminalMelody([TerminalNote('C4'), TerminalNote('E4', start_beats=1)])
        terminal.audio.play(melody, instrument='piano')
        assert played(terminal)[0][0] == melody.render('piano')

    def test_a_sound_is_played_as_it_is_with_volume_and_pan(self, terminal):
        sound = render_note('bell', 'C6')
        terminal.audio.play(sound, volume=0.5, pan=-1.0)
        assert played(terminal)[0] == (sound, 0.5, -1.0, None)

    def test_effects_are_applied_to_a_sound(self, terminal):
        sound = render_note('bell', 'C6')
        effects = [TerminalAudioEffect.reverb()]
        terminal.audio.play(sound, effects=effects)
        assert played(terminal)[0][0] == sound.with_effects(effects)

    def test_scheduling_on_a_beat_starts_the_clock(self, terminal):
        terminal.audio.play('C4', at_beat=4)
        player = FakePlayer.instances[-1]
        assert player.is_clock_running
        assert player.played[0][3] == 4

    def test_playing_without_a_device_says_what_to_do(self, terminal):
        FakePlayer.available = False
        with pytest.raises(TerminalAudioUnavailableError, match='is_available'):
            terminal.audio.play('C4')

    def test_it_can_be_played_from_another_thread_on_a_running_terminal(self):
        import threading

        with xnano.open(offscreen=True, clock='real', width=8, height=1) as terminal:
            thread = threading.Thread(target=lambda: terminal.audio.play('C4'))
            thread.start()
            thread.join()
            terminal.output.render()
            assert len(played(terminal)) == 1

    def test_the_devices_are_released_when_the_terminal_closes(self):
        with xnano.open(offscreen=True, width=8, height=1) as terminal:
            terminal.audio.play('C4')
        assert FakePlayer.instances[-1].closed


class TestClock:
    def test_the_tempo_is_kept_and_applied(self, terminal):
        terminal.audio.play('C4')
        terminal.audio.tempo = 90
        assert terminal.audio.tempo == 90
        assert FakePlayer.instances[-1].tempo == 90

    @pytest.mark.parametrize('tempo', [0, -5, 600001])
    def test_a_tempo_out_of_range_is_refused(self, terminal, tempo):
        with pytest.raises(ValueError, match='out of range'):
            terminal.audio.tempo = tempo

    def test_the_clock_starts_pauses_and_stops(self, terminal):
        terminal.audio.start()
        player = FakePlayer.instances[-1]
        assert player.is_clock_running
        terminal.audio.pause()
        assert not player.is_clock_running


class TestExpressions:
    def test_the_microphone_level_is_an_expression(self, terminal):
        assert terminal.inspect(terminal.audio.level) == 0.25

    def test_the_level_drives_a_position(self, terminal):
        meter = terminal.write('#', y=1)
        meter.x = terminal.audio.level * 16
        terminal.loop.advance(0.1)
        assert meter.x == 4

    def test_the_level_combines_with_the_rest_of_the_language(self, terminal):
        assert terminal.inspect(terminal.audio.level * Width) == 5.0

    def test_the_beat_follows_the_player(self, terminal):
        assert terminal.inspect(terminal.audio.beat) == 0.0
        terminal.audio.start()
        FakePlayer.instances[-1].beat = 2.5
        assert terminal.inspect(terminal.audio.beat % 1) == 0.5

    def test_the_level_history_is_read_from_the_microphone(self, terminal):
        assert terminal.audio.level_history(3) == [0.1, 0.1, 0.1]

    def test_a_missing_microphone_reads_as_silence(self, monkeypatch, terminal):
        class Broken:
            def __init__(self) -> None:
                raise audio_module.TerminalAudioError('no input device')

        monkeypatch.setattr(audio_module, 'TerminalMicrophone', Broken)
        assert terminal.inspect(terminal.audio.level) == 0.0
        assert terminal.audio.level_history(2) == []


class TestInHooks:
    def test_a_hook_plays_a_note_on_a_key(self, terminal):
        @terminal.hook(when=lambda context: context.keyboard is not None)
        def press(context: xnano.context.Context) -> None:
            context.audio.play(context.keyboard.key)

        terminal.inject(Event.key_press('c'))
        terminal.loop.advance(0.05)
        assert len(played(terminal)) == 1


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

    def test_the_terminal_has_a_tempo_that_audio_shares(self):
        with xnano.open(offscreen=True, width=8, height=1) as terminal:
            terminal.tempo = 90
            assert terminal.audio.tempo == 90
            assert terminal.tempo == 90

    def test_every_beat_follows_the_tempo(self):
        with xnano.open(offscreen=True, width=8, height=1) as terminal:
            terminal.tempo = 120  # a beat is half a second
            beats = []

            @terminal.every(beats=1)
            def count(context):
                beats.append(round(context.clock.elapsed_seconds, 2))

            for _ in range(16):
                terminal.loop.advance(0.1)
            assert beats[:3] == pytest.approx([0.5, 1.0, 1.5], abs=0.11)
            assert len(beats) == 3

    def test_every_needs_exactly_one_unit(self):
        with xnano.open(offscreen=True, width=8, height=1) as terminal:
            with pytest.raises(ValueError, match='either seconds or beats'):
                terminal.every()
            with pytest.raises(ValueError, match='either seconds or beats'):
                terminal.every(1, beats=1)

    def test_play_and_note_need_a_sound_device_or_say_so(self):
        with xnano.open(offscreen=True, width=8, height=1) as terminal:
            if terminal.audio.is_available:
                terminal.play('C4 E4 G4:2')
                terminal.note('C5', beats=0.5)
            else:
                with pytest.raises(xnano.audio.TerminalAudioUnavailableError):
                    terminal.note('C5')
