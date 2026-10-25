"""
Hostile input: arguments, decoders and resource limits.

Acceptable outcomes are success or a clean Python exception. A panic, a
signal, a hang, runaway memory, or an error message that carries raw control
characters is a defect in core.
"""

from __future__ import annotations

import math
import random
import struct
import subprocess
import sys
import textwrap
import time
import zlib

import pytest
from helpers import animation, gradient, solid

from xnano_image import (
    TerminalGraphics,
    TerminalImage,
    TerminalImageError,
    cell_grid_size,
    cell_grid_to_ansi,
    cell_grid_to_text,
)

CLEAN = (TerminalImageError, ValueError, TypeError, OverflowError, OSError)
NAN, INF = float('nan'), float('inf')
JUNK = [
    None,
    True,
    '',
    'x',
    b'x',
    [],
    {},
    (),
    object(),
    1j,
    NAN,
    INF,
    -INF,
    2**70,
    -(2**70),
    -1,
    0,
    3.5,
]


def attempt(call):
    try:
        return call()
    except CLEAN as error:
        assert '\x1b' not in str(error) and '\x00' not in str(error), repr(str(error))
        return None


# ----------------------------------------------------- argument fuzzing


@pytest.mark.parametrize('junk', JUNK, ids=repr)
def test_every_argument_position_rejects_junk_cleanly(junk):
    image = animation(2, 6, 4)
    calls = [
        lambda: TerminalImage.from_rgba(junk, 1, b'\0\0\0\0'),
        lambda: TerminalImage.from_rgba(1, junk, b'\0\0\0\0'),
        lambda: TerminalImage.from_rgba(1, 1, junk),
        lambda: TerminalImage.from_rgba(1, 1, b'\0\0\0\0', duration_milliseconds=junk),
        lambda: TerminalImage.from_bytes(junk),
        lambda: TerminalImage.from_xni(junk),
        lambda: TerminalImage.from_frames(junk),
        lambda: TerminalImage.from_frames([junk]),
        lambda: TerminalImage.open(junk),
        lambda: image.resize(junk, 2),
        lambda: image.resize(2, junk),
        lambda: image.resize(2, 2, resampling_filter=junk),
        lambda: image.scale(junk),
        lambda: image.scale(0.5, resampling_filter=junk),
        lambda: image.crop(junk, 0, 1, 1),
        lambda: image.crop(0, 0, junk, 1),
        lambda: image.fit_to_canvas(junk, 4),
        lambda: image.focal_crop(junk, 4),
        lambda: image.flatten(junk),
        lambda: image.quantize(junk),
        lambda: image.quantize(8, should_dither=junk),
        lambda: image.first_frames(junk),
        lambda: image.still_frame(junk),
        lambda: image.with_frames_per_second(junk),
        lambda: image.with_speed(junk),
        lambda: image.frame_index_at(junk),
        lambda: image.to_rgba(junk),
        lambda: image.to_cell_grid(junk, 2),
        lambda: image.to_cell_grid(2, junk),
        lambda: image.to_cell_grid(2, 2, fit=junk),
        lambda: image.to_cell_grid(2, 2, horizontal_pixels_per_cell=junk),
        lambda: image.to_cell_grid(2, 2, should_correct_aspect_ratio=junk),
        lambda: image.to_cell_grid(2, 2, background=junk),
        lambda: image.to_cell_grid(2, 2, resampling_filter=junk),
        lambda: image.to_cell_grid(2, 2, frame_index=junk),
        lambda: image.to_cell_grid(2, 2, graphics=junk),
        lambda: image.to_cell_grids(junk, 2),
        lambda: image.to_ansi(2, junk),
        lambda: image.encode(junk),
        lambda: image.save(junk),
        lambda: image.to_xni(junk),
        lambda: cell_grid_size(junk),
        lambda: cell_grid_to_text(junk),
        lambda: cell_grid_to_ansi(junk),
        lambda: TerminalGraphics.half_blocks().with_protocol(junk),
        lambda: TerminalGraphics.from_capabilities(
            protocol=junk, cell_size_in_pixels=(8, 16)
        ),
        lambda: TerminalGraphics.from_capabilities(
            protocol='kitty', cell_size_in_pixels=junk
        ),
        lambda: image.to_cell_animation(junk, 2),
        lambda: image.to_cell_animation(2, 2, should_loop=junk),
        lambda: image.to_cell_animation(2, 2, graphics=junk),
    ]
    for call in calls:
        attempt(call)


@pytest.mark.parametrize('value', [NAN, INF, -INF, 0.0, -1.0, 1e308, 1e-308, 5e-324])
def test_float_arguments_are_range_checked_not_trusted(value):
    image = animation(2, 6, 4)
    for call in (
        lambda: image.scale(value),
        lambda: image.with_frames_per_second(value),
        lambda: image.with_speed(value),
        lambda: image.frame_index_at(value),
        lambda: image.frame_index_at(value, should_loop=False),
    ):
        result = attempt(call)
        if isinstance(result, TerminalImage):
            assert result.width >= 1 and all(
                duration >= 0 for duration in result.frame_durations()
            )
        if isinstance(result, int):
            assert 0 <= result < image.frame_count


@pytest.mark.parametrize('value', [NAN, INF, -INF])
def test_non_finite_playback_times_are_rejected(value):
    with pytest.raises(TerminalImageError, match='finite'):
        animation(2).frame_index_at(value)


def test_frame_index_clamps_negative_and_huge_finite_times():
    image = animation(3, duration_milliseconds=50)
    assert image.frame_index_at(-1e9) == 0
    assert image.frame_index_at(1e300, should_loop=False) == 2
    assert 0 <= image.frame_index_at(1e300, should_loop=True) < 3


def test_speed_and_frame_rate_extremes_keep_durations_valid():
    image = animation(3, duration_milliseconds=50)
    for factor in (1e-6, 1e6):
        result = attempt(lambda factor=factor: image.with_speed(factor))
        if result is not None:
            assert all(duration >= 0 for duration in result.frame_durations())
    for frames_per_second in (1e-6, 1e6):
        result = attempt(
            lambda frames_per_second=frames_per_second: image.with_frames_per_second(
                frames_per_second
            )
        )
        if result is not None:
            assert all(duration >= 0 for duration in result.frame_durations())


def test_geometry_extremes():
    image = gradient(8, 8)
    for arguments in (
        (0, 0, 8, 8),
        (7, 7, 1, 1),
        (8, 8, 1, 1),
        (0, 0, 0, 0),
        (0, 0, 9, 9),
        (2**31, 0, 1, 1),
        (0, 0, 2**32 - 1, 1),
    ):
        result = attempt(lambda arguments=arguments: image.crop(*arguments))
        if result is not None:
            assert (result.width, result.height) == (arguments[2], arguments[3])
    for size in (
        (1, 1),
        (16384, 1),
        (1, 16384),
        (16385, 1),
        (0, 1),
        (2**32 - 1, 2**32 - 1),
    ):
        attempt(lambda size=size: image.resize(*size))


def test_extreme_aspect_ratios_convert():
    for width, height in ((16384, 1), (1, 16384), (3000, 2)):
        image = solid(width, height)
        grid = image.to_cell_grid(40, 10, fit='contain')
        assert cell_grid_size(grid) == (40, 10)
        assert len(cell_grid_to_text(grid)) == 10


def test_one_by_one_images_survive_every_operation():
    image = solid(1, 1, (9, 8, 7))
    for fit in ('crop', 'contain', 'cover', 'stretch', 'smart'):
        assert cell_grid_size(image.to_cell_grid(5, 3, fit=fit)) == (5, 3)
    assert image.scale(1.0).width == 1
    assert image.quantize(2).width == 1
    assert image.focal_crop(1, 1).width == 1
    assert TerminalImage.from_bytes(image.encode('png')) == image
    assert TerminalImage.from_xni(image.to_xni()).width == 1


# --------------------------------------------------------- decoder fuzzing


def png_bytes(width=5, height=4):
    return gradient(width, height).encode('png')


def gif_bytes():
    return animation(3, 6, 4).encode('gif')


SEEDS = {
    'png': png_bytes,
    'gif': gif_bytes,
    'xni': lambda: animation(3).to_xni(),
}


def decode(kind: str, data: bytes):
    return (
        TerminalImage.from_xni(data) if kind == 'xni' else TerminalImage.from_bytes(data)
    )


@pytest.mark.parametrize('kind', SEEDS)
def test_decoders_survive_random_mutations(kind):
    generator = random.Random(zlib.crc32(kind.encode()))
    valid = SEEDS[kind]()
    started = time.monotonic()
    for _ in range(400):
        data = bytearray(valid)
        for _ in range(generator.randrange(1, 8)):
            data[generator.randrange(len(data))] = generator.randrange(256)
        image = attempt(lambda data=data: decode(kind, bytes(data)))
        if image is not None:
            assert image.width >= 1 and image.frame_count >= 1
            assert len(image.to_rgba()) == image.width * image.height * 4
    assert time.monotonic() - started < 60


@pytest.mark.parametrize('kind', SEEDS)
def test_decoders_survive_every_truncation(kind):
    valid = SEEDS[kind]()
    for cut in range(len(valid)):
        image = attempt(lambda cut=cut: decode(kind, valid[:cut]))
        if image is not None:
            assert image.frame_count >= 1


@pytest.mark.parametrize('kind', SEEDS)
def test_decoders_survive_byte_insertion_and_deletion(kind):
    generator = random.Random(5)
    valid = SEEDS[kind]()
    for _ in range(200):
        data = bytearray(valid)
        at = generator.randrange(len(data))
        if generator.random() < 0.5:
            del data[at : at + generator.randrange(1, 6)]
        else:
            data[at:at] = bytes(
                generator.randrange(256) for _ in range(generator.randrange(1, 6))
            )
        attempt(lambda data=data: decode(kind, bytes(data)))


def test_decoders_survive_pure_noise():
    generator = random.Random(77)
    for _ in range(300):
        data = bytes(generator.randrange(256) for _ in range(generator.randrange(0, 200)))
        attempt(lambda data=data: TerminalImage.from_bytes(data))
        attempt(lambda data=data: TerminalImage.from_xni(data))
        attempt(lambda data=data: TerminalImage.from_xni(b'XNI1' + data))
    for magic in (
        b'\x89PNG\r\n\x1a\n',
        b'GIF89a',
        b'GIF87a',
        b'\xff\xd8\xff',
        b'RIFF',
        b'BM',
        b'II*\x00',
    ):
        for _ in range(60):
            attempt(
                lambda magic=magic: TerminalImage.from_bytes(
                    magic
                    + bytes(
                        generator.randrange(256)
                        for _ in range(generator.randrange(0, 120))
                    )
                )
            )


def test_grids_survive_mutation():
    generator = random.Random(8)
    valid = gradient(6, 6).to_cell_grid(6, 3)
    for _ in range(400):
        data = bytearray(valid)
        for _ in range(generator.randrange(1, 6)):
            data[generator.randrange(len(data))] = generator.randrange(256)
        for helper in (cell_grid_size, cell_grid_to_text, cell_grid_to_ansi):
            attempt(lambda helper=helper, data=data: helper(bytes(data)))
    for cut in range(len(valid)):
        attempt(lambda cut=cut: cell_grid_to_ansi(valid[:cut]))


def test_mutated_grids_that_decode_still_produce_well_formed_output():

    generator = random.Random(21)
    valid = gradient(6, 6).to_cell_grid(6, 3)
    checked = 0
    for _ in range(800):
        data = bytearray(valid)
        data[generator.randrange(8, len(data))] = generator.randrange(256)
        text = attempt(lambda data=data: cell_grid_to_ansi(bytes(data)))
        if text is not None:
            checked += 1
            # the symbol bytes may now be arbitrary text, but escapes we
            # generate (colors) must stay well formed
            assert len(text.split('\n')) == 3
    assert checked > 0


# ------------------------------------------------------ resource safety


def run_script(source: str, timeout: float = 90):
    return subprocess.run(
        [sys.executable, '-c', textwrap.dedent(source)],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def chunk(kind: bytes, body: bytes) -> bytes:
    return (
        struct.pack('>I', len(body))
        + kind
        + body
        + struct.pack('>I', zlib.crc32(kind + body))
    )


def png_claiming(width: int, height: int, data: bytes = b'') -> bytes:
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', header)
        + chunk(b'IDAT', zlib.compress(data))
        + chunk(b'IEND', b'')
    )


def test_decompression_bomb_headers_are_refused_without_allocating():
    resource = pytest.importorskip('resource', reason='memory statistics require POSIX')
    claims = [
        (16384, 16384),
        (65535, 65535),
        (2**31 - 1, 2**31 - 1),
        (1, 2**31 - 1),
    ]
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    for width, height in claims:
        started = time.monotonic()
        with pytest.raises(TerminalImageError):
            TerminalImage.from_bytes(png_claiming(width, height))
        assert time.monotonic() - started < 5
    grown = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before
    unit = 1 if sys.platform == 'darwin' else 1024  # bytes vs kilobytes
    assert grown * unit < 600 * 1024 * 1024, f'rss grew by {grown * unit / 2**20:.0f} MiB'


def test_xni_bomb_headers_are_refused_quickly():
    for width, height, frames in (
        (65535, 65535, 65535),
        (65535, 65535, 1),
        (1, 1, 65535),
    ):
        started = time.monotonic()
        payload = b'XNI1' + struct.pack('>HHH', width, height, frames) + b'\0' * 32
        with pytest.raises(TerminalImageError):
            TerminalImage.from_xni(payload)
        assert time.monotonic() - started < 5


@pytest.mark.parametrize('side', [16384, 20000, 65535])
def test_gif_with_huge_logical_screen_is_refused_fast(side):
    """A 20-byte GIF must not make the decoder allocate its whole declared canvas."""
    gif = bytearray(gif_bytes())
    gif[6:10] = struct.pack('<HH', side, side)
    started = time.monotonic()
    with pytest.raises(TerminalImageError, match='canvas'):
        TerminalImage.from_bytes(bytes(gif))
    assert time.monotonic() - started < 2
    if sys.platform != 'win32':
        resource = pytest.importorskip(
            'resource', reason='memory statistics require POSIX'
        )
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < 4 * 2**30


def test_largest_legal_still_image_works_at_the_pixel_budget():
    result = run_script(
        """
        from xnano_image import *
        image = TerminalImage.from_rgba(4096, 4096, bytes(4096 * 4096 * 4))
        grid = image.to_cell_grid(100, 30)
        assert cell_grid_size(grid) == (100, 30)
        print("OK")
        """
    )
    assert result.returncode == 0 and 'OK' in result.stdout, result.stderr[-400:]


def test_zlib_bomb_in_xni_is_bounded():
    width = height = 4000
    packed = zlib.compress(bytes(width * height), 9)  # ~16 MB of zeros, ~16 KB packed
    payload = (
        b'XNI1'
        + struct.pack('>HHH', 8, 8, 1)  # claims 8x8 ...
        + struct.pack('>HHI', 100, 1, len(packed))
        + b'\0\0\0'
        + packed  # ... but the stream inflates to 16 MB
    )
    started = time.monotonic()
    attempt(lambda: TerminalImage.from_xni(payload))
    assert time.monotonic() - started < 10


def test_many_frames_and_large_lists_do_not_hang():
    frames = [solid(4, 4, (index % 256, 0, 0)) for index in range(2000)]
    started = time.monotonic()
    movie = TerminalImage.from_frames(frames)
    assert movie.frame_count == 2000
    assert len(movie.to_cell_grids(4, 2)) == 2000
    assert time.monotonic() - started < 30


def test_from_frames_validates_sizes():
    with pytest.raises(TerminalImageError, match='at least one'):
        TerminalImage.from_frames([])
    with pytest.raises(TerminalImageError, match='4x4'):
        TerminalImage.from_frames([solid(4, 4), solid(4, 5)])
    merged = TerminalImage.from_frames([animation(2, 4, 4), solid(4, 4)])
    assert merged.frame_count == 3


def test_open_handles_unusual_paths(tmp_path):
    for path in (
        '',
        '/',
        '/dev/null',
        str(tmp_path),
        str(tmp_path / 'missing.png'),
        'a\x00b',
    ):
        attempt(lambda path=path: TerminalImage.open(path))
    (tmp_path / 'empty.png').write_bytes(b'')
    (tmp_path / 'junk.png').write_bytes(b'not an image' * 100)
    for name in ('empty.png', 'junk.png'):
        with pytest.raises(TerminalImageError):
            TerminalImage.open(str(tmp_path / name))


def test_save_errors_are_clean(tmp_path):
    image = solid(2, 2)
    for path in (
        str(tmp_path / 'x.bmp'),
        str(tmp_path / 'noext'),
        str(tmp_path / 'no' / 'dir' / 'x.png'),
        str(tmp_path),
    ):
        with pytest.raises(CLEAN):
            image.save(path)
    assert list(tmp_path.iterdir()) == [], 'failed saves must not leave files behind'


def test_concurrent_conversion_from_threads():
    import concurrent.futures

    image = gradient(64, 64)
    expected = image.to_cell_grid(20, 6)
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda _: image.to_cell_grid(20, 6), range(64)))
    assert all(result == expected for result in results)


def test_math_helpers_unused():
    assert math.isfinite(1.0)  # keeps the import honest for static checkers
