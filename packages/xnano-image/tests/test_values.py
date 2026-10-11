"""Value semantics and text output for ``TerminalImage`` and ``TerminalGraphics``."""

from __future__ import annotations

import copy
import subprocess
import sys
from typing import Any, cast

import pytest
from helpers import animation, gradient, solid

from xnano_image import (
    TerminalGraphics,
    TerminalImage,
    TerminalImageError,
    TerminalQueryError,
)

BAD_TEXT = ('{', '}', '::', 'Some(', ' at 0x', '\x1b', '\n', '\x00')


def test_images_with_equal_pixels_are_equal_and_hash_alike():
    first, second = gradient(5, 4), gradient(5, 4)
    assert first is not second and first == second
    assert hash(first) == hash(second) and len({first, second}) == 1


@pytest.mark.parametrize(
    'other',
    [
        lambda: gradient(5, 5),
        lambda: gradient(4, 4),
        lambda: solid(5, 4, (1, 2, 3)),
        lambda: (
            gradient(5, 4)
            .flatten((9, 9, 9))
            .resize(5, 4, resampling_filter='nearest')
            .with_frames_per_second(3.0)
        ),
    ],
)
def test_images_that_differ_are_unequal(other):
    assert gradient(5, 4) != other()


def test_timing_and_frame_count_take_part_in_equality():
    base = animation(3)
    assert base != base.with_frames_per_second(4.0)
    assert base != base.first_frames(2)
    assert base == base.with_speed(1.0)


def test_pixel_difference_in_the_last_byte_is_noticed():
    pixels = bytearray(gradient(40, 40).to_rgba())
    pixels[-2] ^= 1
    changed = TerminalImage.from_rgba(40, 40, bytes(pixels))
    assert changed != gradient(40, 40)


def test_equal_images_built_different_ways_agree():
    assert TerminalImage.from_bytes(gradient(7, 5).encode('png')) == gradient(7, 5)
    assert TerminalImage.from_rgba(7, 5, gradient(7, 5).to_rgba()) == gradient(7, 5)


def test_never_equal_to_other_types():
    image = gradient(2, 2)
    assert image != 1 and image != 'x' and image != None and image != image.to_rgba()


def test_copy_and_deepcopy_are_equal():
    image = animation(3)
    assert copy.copy(image) == image == copy.deepcopy(image)
    assert copy.deepcopy([image, image])[1] == image


def test_operations_return_equal_but_independent_images():
    image = gradient(6, 6)
    assert image.first_frames(1) == image
    assert image.resize(6, 6, resampling_filter='nearest') == image


def test_images_work_as_dictionary_keys():
    table = {gradient(3, 3): 'a', solid(3, 3): 'b'}
    assert table[gradient(3, 3)] == 'a' and table[solid(3, 3)] == 'b'


@pytest.mark.parametrize(
    'image, expected',
    [
        (lambda: solid(4, 3), 'TerminalImage(4x3, 1 frame, 100 ms)'),
        (lambda: animation(3, 2, 2, 40), 'TerminalImage(2x2, 3 frames, 120 ms)'),
    ],
)
def test_image_repr(image, expected):
    assert repr(image()) == expected


def test_reprs_are_clean_text():
    for value in (solid(2, 2), animation(2), TerminalGraphics.half_blocks()):
        text = repr(value)
        for bad in BAD_TEXT:
            assert bad not in text, (bad, text)


# ----------------------------------------------------- terminal graphics


def test_terminal_graphics_are_immutable_values():
    graphics = TerminalGraphics.half_blocks()
    sixel = graphics.with_protocol('sixel')
    assert graphics.protocol == 'half_blocks' and sixel.protocol == 'sixel'
    assert graphics != sixel
    assert graphics == TerminalGraphics.half_blocks()
    assert copy.copy(sixel) is sixel and copy.deepcopy(sixel) is sixel
    with pytest.raises(AttributeError):
        cast(Any, graphics).protocol = 'kitty'


def test_terminal_graphics_are_hashable():
    first = TerminalGraphics.half_blocks()
    second = TerminalGraphics.half_blocks()
    assert hash(first) == hash(second) and len({first, second}) == 1
    assert len({first, first.with_protocol('kitty')}) == 2


def test_terminal_graphics_protocol_round_trips():
    graphics = TerminalGraphics.half_blocks()
    for name in ('sixel', 'kitty', 'iterm2', 'half_blocks'):
        changed = graphics.with_protocol(name)
        assert changed.protocol == name
        assert repr(changed) == (
            f"TerminalGraphics(protocol='{name}', cell_size_in_pixels=(10, 20))"
        )


def test_terminal_graphics_report_sane_geometry_and_identifier_capabilities():
    graphics = TerminalGraphics.half_blocks()
    width, height = graphics.cell_size_in_pixels
    assert 1 <= width <= 200 and 1 <= height <= 400
    assert all(name.isidentifier() for name in graphics.capabilities)


def test_from_capabilities_builds_known_capabilities():
    graphics = TerminalGraphics.from_capabilities(
        protocol='kitty', cell_size_in_pixels=(9, 18)
    )
    assert graphics.protocol == 'kitty'
    assert graphics.cell_size_in_pixels == (9, 18)
    assert graphics.capabilities == []


@pytest.mark.parametrize(
    'arguments, expected',
    [
        ({'protocol': 'halfblocks', 'cell_size_in_pixels': (9, 18)}, "'half_blocks'"),
        ({'protocol': 'kitty', 'cell_size_in_pixels': (0, 18)}, r'\(0, 18\)'),
        ({'protocol': 'kitty', 'cell_size_in_pixels': (9, 5000)}, '1000'),
    ],
)
def test_from_capabilities_rejects_invalid_values_with_the_choices(arguments, expected):
    with pytest.raises(TerminalImageError, match=expected):
        TerminalGraphics.from_capabilities(**arguments)


def test_detect_without_a_terminal_raises_a_query_error():
    script = (
        'from xnano_image import TerminalGraphics, TerminalQueryError\n'
        'try:\n'
        '    TerminalGraphics.detect()\n'
        'except TerminalQueryError as error:\n'
        '    print("QUERY-ERROR", error)\n'
        'else:\n'
        '    print("DETECTED")\n'
    )
    result = subprocess.run(
        [sys.executable, '-c', script],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-400:]
    assert 'QUERY-ERROR' in result.stdout, result.stdout
    assert 'from_capabilities' in result.stdout and 'half_blocks' in result.stdout


# ---------------------------------------------------------------- errors


def test_error_messages_are_single_clean_lines():
    cases = [
        lambda: TerminalImage.from_bytes(b'\x89PNG\r\n\x1a\n' + bytes(range(64))),
        lambda: TerminalImage.from_bytes(b'GIF89a' + b'\x00' * 40),
        lambda: TerminalImage.from_bytes(b'\xff\xd8\xff' + b'\x00' * 40),
        lambda: TerminalImage.from_bytes(b'RIFF\x00\x00\x00\x00WEBPVP8 ' + b'\x00' * 40),
        lambda: TerminalImage.from_xni(b'XNI1\x00\x01\x00\x01\x00\x01' + b'\x1b[31m'),
        lambda: solid(2, 2).to_cell_grid(2, 2, fit='\x1b[31mred'),
        lambda: solid(2, 2).resize(2, 2, resampling_filter='bad\nfilter\x00'),
        lambda: solid(2, 2).encode('\x1b]0;pwn\x07'),
        lambda: solid(2, 2).save('/nonexistent-dir-\x1b[2J/out.png'),
        lambda: TerminalGraphics.half_blocks().with_protocol(cast(Any, '\x1b[2J')),
    ]
    for call in cases:
        with pytest.raises((TerminalImageError, OSError)) as caught:
            call()
        message = str(caught.value)
        assert (
            '\x1b' not in message and '\x00' not in message and '\x07' not in message
        ), message
        assert len(message) <= 403, len(message)
        assert '\n' not in message


@pytest.mark.parametrize(
    'call, expected',
    [
        (
            lambda: solid(2, 2).to_cell_grid(fit='tile'),
            ["'tile'", "'contain'", "'smart'"],
        ),
        (
            lambda: solid(2, 2).resize(1, 1, resampling_filter='magic'),
            ["'magic'", "'nearest'", "'lanczos3'"],
        ),
        (lambda: solid(2, 2).encode('bmp'), ["'bmp'", "'png'", "'gif'"]),
        (lambda: solid(2, 2).to_cell_grid(columns=0), ['columns', '0', '1000']),
        (lambda: solid(2, 2).to_cell_grid(rows=5000), ['rows', '5000', '1000']),
        (
            lambda: solid(2, 2).to_cell_grid(horizontal_pixels_per_cell=3),
            ['horizontal_pixels_per_cell', '3', '1 or 2'],
        ),
        (lambda: animation(3).to_cell_grid(frame_index=7), ['7', '3 frames', '0 and 2']),
        (lambda: animation(3).still_frame(9), ['9', '0 and 2']),
        (lambda: solid(4, 4).crop(2, 2, 4, 4), ['4x4', '(2, 2)', '4x4 pixel image']),
        (lambda: solid(2, 2).quantize(1), ['1 colors', '2 and 256']),
        (lambda: solid(2, 2).scale(0.0), ['factor', '0.0', 'greater than zero']),
        (lambda: solid(2, 2).with_speed(-1.0), ['-1', 'greater than zero']),
        (lambda: solid(2, 2).with_frames_per_second(0.0), ['0', 'greater than zero']),
        (lambda: solid(2, 2).resize(0, 5), ['0x5', '1 and 16384']),
        (lambda: TerminalImage.from_rgba(2, 2, b'\x00' * 15), ['15 bytes', '16']),
        (lambda: TerminalImage.from_frames([]), ['at least one']),
        (lambda: TerminalImage.from_frames([solid(4, 4), solid(4, 5)]), ['4x5', '4x4']),
        (lambda: animation(2).frame_index_at(float('nan')), ['finite', 'nan']),
        (lambda: TerminalImage.from_bytes(b'not an image'), ['PNG', 'GIF']),
    ],
)
def test_error_messages_name_the_value_and_what_is_accepted(call, expected):
    with pytest.raises(TerminalImageError) as caught:
        call()
    message = str(caught.value)
    for fragment in expected:
        assert fragment in message, (fragment, message)
    assert message.rstrip().endswith('.'), message


def test_error_class_identity():
    assert TerminalImageError.__module__ == 'xnano_image._xnano_image'
    assert TerminalQueryError.__module__ == 'xnano_image._xnano_image'
    with pytest.raises(ValueError):
        TerminalImage.from_bytes(b'')
