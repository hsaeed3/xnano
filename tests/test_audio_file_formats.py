"""
tests.test_audio_file_formats

MP3, FLAC, Ogg Vorbis and MP4/AAC files become sounds like WAV files do.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

import xnano

pytest.importorskip('xnano_audio')

ENCODER = shutil.which('ffmpeg')
SONG = pathlib.Path(__file__).resolve().parent.parent / 'SILENT-SIREN.mp3'


@pytest.fixture(scope='module')
def tone_directory(tmp_path_factory):
    """A stereo half-second 440 Hz tone at 22050 Hz, encoded in each format."""
    if ENCODER is None:
        pytest.skip('ffmpeg is needed to encode the test files')
    directory = tmp_path_factory.mktemp('tones')
    for extension in ('wav', 'flac', 'ogg', 'mp3', 'm4a'):
        subprocess.run(
            [
                ENCODER, '-loglevel', 'error', '-f', 'lavfi', '-i',
                'sine=frequency=440:duration=0.5:sample_rate=22050',
                '-ac', '2', str(directory / f'tone.{extension}'),
            ],
            check=True,
        )  # fmt: skip
    return directory


@pytest.mark.parametrize('extension', ['wav', 'flac', 'ogg', 'mp3', 'm4a'])
class TestEveryFormat:
    def test_a_path_becomes_a_mono_sound(self, tone_directory, extension):
        sound = xnano.load_sound(tone_directory / f'tone.{extension}')
        # A WAV file keeps its own rate; the other formats are decoded at 44100 Hz.
        assert sound.samples.sample_rate == (22050 if extension == 'wav' else 44100)
        assert sound.samples.duration_milliseconds == pytest.approx(500, abs=60)
        assert sound.samples.peak > 0.05

    def test_bytes_become_the_same_sound(self, tone_directory, extension):
        path = tone_directory / f'tone.{extension}'
        from_path = xnano.Sound(str(path))
        from_bytes = xnano.Sound(path.read_bytes())
        assert from_bytes.samples.sample_rate == from_path.samples.sample_rate
        assert from_bytes.samples.duration_milliseconds == pytest.approx(
            from_path.samples.duration_milliseconds, abs=1
        )

    def test_the_extension_does_not_decide_the_format(self, tone_directory, extension):
        disguised = tone_directory / f'disguised-{extension}.bin'
        disguised.write_bytes((tone_directory / f'tone.{extension}').read_bytes())
        sound = xnano.load_sound(disguised)
        assert sound.samples.peak > 0.05


class TestFailures:
    def test_undecodable_bytes_say_what_is_accepted(self):
        with pytest.raises(ValueError, match='xnano accepts WAV, MP3, FLAC, Ogg'):
            xnano.Sound(b'definitely not audio' * 100)

    def test_empty_bytes_say_what_is_accepted(self):
        with pytest.raises(ValueError, match='xnano accepts WAV, MP3, FLAC, Ogg'):
            xnano.Sound(b'')

    def test_an_undecodable_file_names_the_path(self, tmp_path):
        path = tmp_path / 'broken.mp3'
        path.write_bytes(b'not an mp3' * 100)
        with pytest.raises(ValueError, match='broken.mp3'):
            xnano.load_sound(path)

    def test_the_temporary_file_of_bytes_is_removed(self, monkeypatch):
        import tempfile

        created = []
        real = tempfile.NamedTemporaryFile

        def recording(*arguments, **keywords):
            file = real(*arguments, **keywords)
            created.append(file.name)
            return file

        monkeypatch.setattr(tempfile, 'NamedTemporaryFile', recording)
        with pytest.raises(ValueError):
            xnano.Sound(b'not audio' * 100)
        assert created
        assert not any(pathlib.Path(name).exists() for name in created)


@pytest.mark.skipif(not SONG.is_file(), reason='SILENT-SIREN.mp3 is not present')
def test_a_whole_song_loads_and_plays():
    sound = xnano.load_sound(SONG)
    assert sound.samples.duration_milliseconds > 60_000
    with xnano.new(width=8, height=1) as canvas:
        canvas.play(sound)
