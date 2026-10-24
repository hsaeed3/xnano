"""
tests.test_audio

Audio files, samples and what a canvas played become audio.
"""

from __future__ import annotations

import pytest

import xnano


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=6) as canvas:
        yield canvas


def wave_bytes(samples, *, channels=1, width=2, rate=8000):
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(width)
        writer.setframerate(rate)
        writer.writeframes(
            b''.join(
                int(value).to_bytes(width, 'little', signed=True) for value in samples
            )
        )
    return buffer.getvalue()


class TestLoadAudio:
    def test_a_wave_file_opens_as_audio(self, tmp_path):
        path = tmp_path / 'tone.wav'
        path.write_bytes(wave_bytes([0, 16384, -16384, 0], rate=8000))
        audio = xnano.load_audio(path)
        assert isinstance(audio, xnano.Audio)
        assert audio.sample_rate == 8000
        assert len(audio.samples()) == 4
        assert audio.samples()[1] == pytest.approx(0.5)
        assert audio.peak == pytest.approx(0.5)

    def test_stereo_is_mixed_down_to_mono(self):
        audio = xnano.load_audio(wave_bytes([16384, -16384, 8192, 8192], channels=2))
        assert audio.samples() == pytest.approx([0.0, 0.25])

    def test_a_file_of_another_kind_says_what_is_read(self, tmp_path):
        path = tmp_path / 'notes.txt'
        path.write_text('hello, this is text')
        with pytest.raises(ValueError, match='xnano reads WAV, MP3, FLAC'):
            xnano.load_audio(path)

    def test_something_that_is_not_a_file_says_what_to_pass(self):
        with pytest.raises(
            TypeError, match=r'Audio\.from_samples\(\).*Audio\(terminal_sound\)'
        ):
            xnano.load_audio([0.0, 0.5])  # type: ignore[arg-type]

    def test_audio_can_be_played_from_the_canvas(self, canvas):
        audio = xnano.load_audio(wave_bytes([0, 8000, -8000, 0], rate=8000))
        canvas.speaker.play(audio)
        canvas.clock.step(delta_seconds=0.001)
        assert canvas.speaker.render().peak > 0.0


class TestAudioFromSamples:
    def test_samples_become_audio_at_the_rate_given(self):
        audio = xnano.Audio.from_samples([0.0, 0.5, -0.5, 0.0], sample_rate=8000)
        assert audio.sample_rate == 8000
        assert audio.duration_milliseconds == pytest.approx(0.5)
        assert audio.samples() == pytest.approx([0.0, 0.5, -0.5, 0.0])

    def test_a_symbol_plays_it_by_name(self, canvas):
        xnano.Audio.from_samples([0.0, 0.5, -0.5, 0.0] * 100, symbol='blip')
        canvas.speaker.play('blip')
        canvas.clock.step(delta_seconds=0.1)
        assert canvas.speaker.render().peak > 0.4

    def test_a_sound_of_xnano_audio_is_wrapped(self):
        terminal_sound = pytest.importorskip('xnano_audio').TerminalSound
        sound = terminal_sound.from_samples([0.0, 0.25])
        assert xnano.Audio(sound).terminal_sound is sound
        with pytest.raises(TypeError, match=r'load_audio\("song.mp3"\)'):
            xnano.Audio([0.0, 0.25])  # type: ignore[arg-type]

    def test_what_a_canvas_played_is_audio(self, canvas):
        canvas.speaker.play('C4')
        canvas.clock.step(delta_seconds=0.25)
        played = canvas.speaker.render()
        assert isinstance(played, xnano.Audio)
        assert played.duration_milliseconds == pytest.approx(250.0)


class TestAudioRegion:
    def test_audio_lasts_as_long_as_its_duration_on_the_timeline(self):
        audio = xnano.Audio.from_samples([0.0] * 22050, sample_rate=44100)
        region = audio.region
        assert region.resolution == 'beats'
        assert (region.x, region.y, region.height) == (0.0, 60, 1)
        assert region.width == pytest.approx(1.0)
        assert region.milliseconds.width == pytest.approx(audio.duration_milliseconds)
        assert region.milliseconds.width == pytest.approx(500.0)

    def test_the_ticks_follow_the_duration_at_120_beats_per_minute(self):
        audio = xnano.Audio.from_samples([0.0] * 44100, sample_rate=44100)
        assert audio.region.width == pytest.approx(2.0)
        assert audio.region.sixteenths.width == pytest.approx(8.0)

    def test_audio_loaded_from_a_file_has_a_region_of_its_duration(self):
        audio = xnano.load_audio(wave_bytes([0] * 8000, rate=8000))
        assert audio.region.milliseconds.width == pytest.approx(1000.0)
        assert (audio.region.y, audio.region.height) == (60, 1)

    def test_the_row_of_audio_is_middle_c(self):
        from xnano.audio._audio import AUDIO_PITCH_ROW

        assert AUDIO_PITCH_ROW == xnano.Note('C4').region.y


class TestAudioValue:
    def test_audio_from_equal_samples_is_equal_and_hashes_equal(self):
        first = xnano.Audio.from_samples([0.0, 0.5, -0.5, 0.0])
        second = xnano.Audio.from_samples([0.0, 0.5, -0.5, 0.0])
        assert first == second
        assert hash(first) == hash(second)
        assert len({first, second}) == 1

    def test_audio_from_different_samples_is_unequal(self):
        first = xnano.Audio.from_samples([0.0, 0.5, -0.5, 0.0])
        second = xnano.Audio.from_samples([0.0, 0.25, -0.25, 0.0])
        assert first != second
        assert len({first, second}) == 2


@pytest.mark.parametrize('name', ['Sound', 'load_sound', 'from_audio'])
def test_the_old_names_are_gone(name):
    assert not hasattr(xnano, name)
