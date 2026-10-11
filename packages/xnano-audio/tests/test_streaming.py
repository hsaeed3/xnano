"""Buffered streaming: formats, file decoding, voices and deterministic null-backend playback."""

from __future__ import annotations

import array
import math
import struct
import wave

import pytest

from xnano_audio import (
    TerminalAudioError,
    TerminalAudioStream,
    TerminalPCMFormat,
    TerminalStreamingAudioPlayer,
    render_note,
)


def floats(data: bytes) -> list[float]:
    return list(struct.unpack(f'<{len(data) // 4}f', data))


def write_wave(path, *, rate=8000, seconds=0.5, channels=1, frequency=440.0):
    frames = int(rate * seconds)
    samples = array.array('h')
    for index in range(frames):
        value = int(12000 * math.sin(2 * math.pi * frequency * index / rate))
        samples.extend([value] * channels)
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.tobytes())
    return frames


class Constant:
    """A Python source that plays a fixed value for a number of frames."""

    def __init__(
        self, value: float, frames: int, format: TerminalPCMFormat | None = None
    ):
        self.format = format or TerminalPCMFormat(sample_rate=44100, channels=1)
        self.remaining = frames
        self.value = value
        self.closed = False

    def read(self, frames: int) -> bytes:
        count = min(frames, self.remaining)
        self.remaining -= count
        return struct.pack(f'<{count}f', *([self.value] * count))

    def close(self) -> None:
        self.closed = True


def test_formats_validate_and_describe_themselves():
    format = TerminalPCMFormat()
    assert (
        format.sample_rate,
        format.channels,
        format.sample_type,
        format.bytes_per_frame,
    ) == (44100, 2, 'f32le', 8)
    assert TerminalPCMFormat(channels=1, sample_type='s16le').bytes_per_frame == 2
    assert format == TerminalPCMFormat() and hash(format) == hash(TerminalPCMFormat())
    with pytest.raises(ValueError, match='sample_rate'):
        TerminalPCMFormat(sample_rate=10)
    with pytest.raises(ValueError, match='mono'):
        TerminalPCMFormat(channels=6)
    with pytest.raises(ValueError, match='sample type'):
        TerminalPCMFormat(sample_type='u8')


def test_null_backend_mixes_deterministically():
    with TerminalStreamingAudioPlayer(backend='null') as player:
        playback = player.play_stream(Constant(0.25, 100))
        data = player.advance(150)
        samples = floats(data)
        assert len(samples) == 300
        assert samples[0] == pytest.approx(0.25) and samples[1] == pytest.approx(0.25)
        assert samples[2 * 99] == pytest.approx(0.25) and samples[2 * 100] == 0.0
        assert player.sample_position == 150
        assert not playback.is_playing
        assert playback.position_frames == 100


def test_voices_sum_and_clip():
    with TerminalStreamingAudioPlayer(backend='null') as player:
        player.play_stream(Constant(0.75, 10))
        player.play_stream(Constant(0.75, 10))
        assert floats(player.advance(10))[0] == pytest.approx(1.0)


def test_pan_and_volume_scale_channels():
    with TerminalStreamingAudioPlayer(backend='null') as player:
        player.play_stream(Constant(0.5, 4), volume=0.5, pan=1.0)
        left, right = floats(player.advance(1))
        assert left == pytest.approx(0.0) and right == pytest.approx(0.25)


def test_playback_controls():
    with TerminalStreamingAudioPlayer(backend='null') as player:
        playback = player.play_stream(Constant(0.5, 1000))
        playback.pause()
        assert playback.is_paused and not playback.is_playing
        assert set(floats(player.advance(10))) == {0.0}
        playback.resume()
        assert playback.is_playing
        assert floats(player.advance(1))[0] == pytest.approx(0.5)
        playback.volume = 0.0
        player.advance(512)
        assert floats(player.advance(1))[0] == pytest.approx(0.0)
        playback.pan = -1.0
        assert playback.pan == -1.0
        with pytest.raises(ValueError, match='pan'):
            playback.pan = 3.0
        with pytest.raises(ValueError, match='finite'):
            playback.volume = float('nan')


def test_fades_and_stopping():
    with TerminalStreamingAudioPlayer(
        backend='null', format=TerminalPCMFormat(sample_rate=8000, channels=1)
    ) as player:
        source = Constant(1.0, 100000, TerminalPCMFormat(sample_rate=8000, channels=1))
        playback = player.play_stream(source)
        playback.fade_to(0.0, seconds=0.01)
        samples = floats(player.advance(100))
        assert samples[0] > samples[40] > samples[79]
        assert samples[85] == pytest.approx(0.0)
        playback.volume = 1.0
        player.advance(100)
        playback.stop(fade_seconds=0.005)
        player.advance(100)
        assert not playback.is_playing and source.closed
        again = player.play_stream(
            Constant(1.0, 100, TerminalPCMFormat(sample_rate=8000, channels=1))
        )
        again.stop()
        assert not again.is_playing


def test_crossfade_swaps_voices():
    format = TerminalPCMFormat(sample_rate=8000, channels=1)
    with TerminalStreamingAudioPlayer(backend='null', format=format) as player:
        old = player.play_stream(Constant(0.5, 100000, format))
        new = player.play_stream(Constant(-0.5, 100000, format))
        player.crossfade(old, new, seconds=0.02)
        player.advance(8000 // 50 + 200)
        assert not old.is_playing and new.is_playing
        assert floats(player.advance(1))[0] == pytest.approx(-0.5, abs=0.01)


def test_underruns_are_counted_and_errors_stay_on_the_voice():
    class Slow:
        format = TerminalPCMFormat(sample_rate=44100, channels=1)

        def read(self, frames):
            return b''

        def close(self):
            pass

    class Broken(Slow):
        def read(self, frames):
            raise RuntimeError('disk on fire')

    with TerminalStreamingAudioPlayer(backend='null') as player:
        failing = player.play_stream(Broken())
        player.advance(10)
        assert 'disk on fire' in (failing.last_error or '')
        assert not failing.is_playing
        player.play_sound(render_note('sine', 'A4', duration_milliseconds=20))
        assert any(floats(player.advance(200)))


def test_sources_are_validated():
    with TerminalStreamingAudioPlayer(backend='null') as player:
        with pytest.raises(ValueError, match='read'):
            player.play_stream(object())
        with pytest.raises(ValueError, match='finite'):
            player.play_stream(Constant(0, 1), volume=float('inf'))


def test_decoding_files_lazily(tmp_path):
    path = tmp_path / 'tone.wav'
    frames = write_wave(path, rate=8000, seconds=0.25)
    with TerminalAudioStream.open(path) as stream:
        assert stream.format == TerminalPCMFormat(
            sample_rate=8000, channels=1, sample_type='f32le'
        )
        assert not stream.is_closed
        first = stream.read(100)
        assert len(first) == 100 * 4
        rest = b''
        while chunk := stream.read(500):
            rest += chunk
        assert len(first) + len(rest) == frames * 4
        stream.seek(0)
        assert stream.read(100) == first
    assert stream.is_closed
    with pytest.raises(TerminalAudioError, match='closed'):
        stream.read(1)


def test_decoding_resamples_and_converts(tmp_path):
    path = tmp_path / 'stereo.wav'
    write_wave(path, rate=8000, seconds=0.1, channels=2)
    target = TerminalPCMFormat(sample_rate=16000, channels=2, sample_type='s16le')
    with TerminalAudioStream.open(path, format=target) as stream:
        data = b''
        while chunk := stream.read(256):
            data += chunk
        assert abs(len(data) // 4 - 1600) <= 2
        assert stream.format == target


def test_unsupported_files_explain_themselves(tmp_path):
    bogus = tmp_path / 'notes.txt'
    bogus.write_text('not audio')
    with pytest.raises(TerminalAudioError, match='not a supported audio file'):
        TerminalAudioStream.open(bogus)
    with pytest.raises(TerminalAudioError, match='could not be opened'):
        TerminalAudioStream.open(tmp_path / 'missing.wav')


def test_streams_play_through_the_player(tmp_path):
    path = tmp_path / 'tone.wav'
    write_wave(path, rate=44100, seconds=0.05)
    with TerminalStreamingAudioPlayer(backend='null') as player:
        stream = TerminalAudioStream.open(path, format=player.format)
        playback = player.play_stream(stream)
        data = player.advance(4000)
        assert any(abs(value) > 0.1 for value in floats(data))
        assert not playback.is_playing
        assert stream.is_closed, 'the player closed the source when it ended'


def test_closing_is_idempotent_and_final():
    player = TerminalStreamingAudioPlayer(backend='null')
    source = Constant(0.5, 1000)
    player.play_stream(source)
    player.close()
    player.close()
    assert player.is_closed and source.closed
    with pytest.raises(TerminalAudioError, match='closed'):
        player.advance(1)
    with pytest.raises(TerminalAudioError, match='closed'):
        player.play_stream(Constant(0, 1))


def test_advance_needs_the_null_backend():
    try:
        player = TerminalStreamingAudioPlayer()
    except TerminalAudioError:
        pytest.skip('no output device on this machine')
    with player, pytest.raises(TerminalAudioError, match='backend="null"'):
        player.advance(1)


def test_backend_and_lookahead_are_validated():
    with pytest.raises(ValueError, match='backend'):
        TerminalStreamingAudioPlayer(backend='speakers')
    with pytest.raises(ValueError, match='lookahead_milliseconds'):
        TerminalStreamingAudioPlayer(backend='null', lookahead_milliseconds=1)
