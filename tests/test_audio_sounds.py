"""
tests.test_audio_sounds

WAV files and samples become sounds.
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


class TestLoadSound:
    def test_a_wave_file_opens_as_a_sound(self, tmp_path):
        path = tmp_path / 'tone.wav'
        path.write_bytes(wave_bytes([0, 16384, -16384, 0], rate=8000))
        sound = xnano.load_sound(path)
        assert isinstance(sound, xnano.Sound)
        assert sound.samples.sample_rate == 8000
        assert len(sound.samples) == 4
        assert sound.samples.samples()[1] == pytest.approx(0.5)

    def test_stereo_is_mixed_down_to_mono(self):
        sound = xnano.load_sound(wave_bytes([16384, -16384, 8192, 8192], channels=2))
        assert sound.samples.samples() == pytest.approx([0.0, 0.25])

    def test_a_file_of_another_kind_says_what_is_accepted(self, tmp_path):
        path = tmp_path / 'notes.txt'
        path.write_text('hello, this is text')
        with pytest.raises(ValueError, match='not a PCM WAV file'):
            xnano.load_sound(path)

    def test_a_sound_can_be_played_from_the_canvas(self, canvas):
        pytest.importorskip('xnano_audio')
        sound = xnano.Sound(wave_bytes([0, 8000, -8000, 0], rate=8000))
        canvas.play(sound)
        canvas.step(delta_seconds=0.001)
        assert canvas.audio.render_sound().peak > 0.0


class TestSoundRegion:
    def test_a_sound_lasts_as_long_as_its_duration_on_the_timeline(self):
        terminal_sound = pytest.importorskip('xnano_audio').TerminalSound
        sound = xnano.Sound(terminal_sound.from_samples([0.0] * 22050, sample_rate=44100))
        region = sound.region
        assert region.resolution == 'beats'
        assert (region.x, region.y, region.height) == (0.0, 60, 1)
        assert region.width == pytest.approx(1.0)
        assert region.milliseconds.width == pytest.approx(
            sound.samples.duration_milliseconds
        )
        assert region.milliseconds.width == pytest.approx(500.0)

    def test_the_ticks_follow_the_duration_at_120_beats_per_minute(self):
        terminal_sound = pytest.importorskip('xnano_audio').TerminalSound
        sound = xnano.Sound(terminal_sound.from_samples([0.0] * 44100, sample_rate=44100))
        assert sound.region.width == pytest.approx(2.0)
        assert sound.region.ticks.width == pytest.approx(8.0)

    def test_a_sound_loaded_from_a_file_has_a_region_of_its_duration(self):
        sound = xnano.load_sound(wave_bytes([0] * 8000, rate=8000))
        assert sound.region.milliseconds.width == pytest.approx(1000.0)
        assert (sound.region.y, sound.region.height) == (60, 1)

    def test_the_row_of_a_sound_is_middle_c(self):
        from xnano.audio._sounds import SOUND_PITCH_ROW

        assert SOUND_PITCH_ROW == xnano.note('C4').region.y


class TestSoundValue:
    def test_sounds_from_equal_samples_are_equal_and_hash_equal(self):
        terminal_sound = pytest.importorskip('xnano_audio').TerminalSound
        first = xnano.Sound(terminal_sound.from_samples([0.0, 0.5, -0.5, 0.0]))
        second = xnano.Sound(terminal_sound.from_samples([0.0, 0.5, -0.5, 0.0]))
        assert first == second
        assert hash(first) == hash(second)
        assert len({first, second}) == 1

    def test_sounds_from_different_samples_are_unequal(self):
        terminal_sound = pytest.importorskip('xnano_audio').TerminalSound
        first = xnano.Sound(terminal_sound.from_samples([0.0, 0.5, -0.5, 0.0]))
        second = xnano.Sound(terminal_sound.from_samples([0.0, 0.25, -0.25, 0.0]))
        assert first != second
        assert len({first, second}) == 2


@pytest.mark.parametrize('name', ['Audio', 'from_audio'])
def test_the_old_names_are_gone(name):
    assert not hasattr(xnano, name)
