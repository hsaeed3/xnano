"""Animated effects run on mounted targets; Fuzz is immediate."""

from __future__ import annotations

import pytest

from xnano_core._xnano_core import (
    Buffer,
    CancelEffect,
    Color,
    Dissolve,
    Effect,
    Fade,
    Fuzz,
    Glitch,
    Runtime,
    RuntimeRequiredError,
)


def test_animated_effects_need_a_mounted_runtime():
    buffer = Buffer('hello')
    for effect in (
        Fade(foreground='red'),
        Dissolve(),
        Glitch(),
        CancelEffect('x'),
        Effect(),
    ):
        with pytest.raises(
            RuntimeRequiredError, match='mounted target and an active runtime'
        ):
            buffer.update(effect)


def test_fade_moves_colors_toward_the_target(runtime):
    buffer = Buffer('hello')
    runtime.mount(buffer)
    runtime.step()
    buffer.update(Fade(foreground=(255, 0, 0), duration_milliseconds=200, key='fade'))
    runtime.step()
    start = runtime.snapshot().to_cell_grid()
    runtime.advance_clock(100)
    runtime.step()
    middle = Buffer.from_cell_grid(runtime.snapshot().to_cell_grid())
    runtime.advance_clock(200)
    runtime.step()
    end = Buffer.from_cell_grid(runtime.snapshot().to_cell_grid())
    assert end[0, 0].foreground.to_rgb() == (255, 0, 0)
    assert middle[0, 0].foreground != end[0, 0].foreground
    assert start


def test_effects_finish_and_stop_requesting_frames(runtime):
    buffer = Buffer('hello')
    runtime.mount(buffer)
    runtime.step()
    buffer.update(Fade(foreground='blue', duration_milliseconds=50))
    assert runtime.needs_frame
    runtime.advance_clock(60)
    runtime.step()
    runtime.advance_clock(60)
    runtime.step()
    runtime.step()
    assert not runtime.needs_frame


def test_dissolve_blanks_cells_over_time(runtime):
    buffer = Buffer('xxxxxxxxxx')
    runtime.mount(buffer)
    runtime.step()
    buffer.update(Dissolve(duration_milliseconds=100, seed=3))
    runtime.step()
    runtime.advance_clock(110)
    runtime.step()
    assert runtime.snapshot().lines()[0].strip() == ''


def test_keyed_effects_replace_and_cancel(runtime):
    buffer = Buffer('hello')
    runtime.mount(buffer)
    runtime.step()
    buffer.update(Fade(foreground='red', duration_milliseconds=1000, key='k'))
    buffer.update(Fade(foreground='blue', duration_milliseconds=1000, key='k'))
    runtime.step()
    buffer.update(CancelEffect('k'))
    runtime.advance_clock(10)
    runtime.step()
    runtime.step()
    assert not runtime.needs_frame


def test_effect_modifiers_return_effects(runtime):
    fade = Fade(foreground='red', duration_milliseconds=100)
    for modified in (fade.repeat(times=2), fade.reversed(), fade.delayed(50)):
        assert isinstance(modified, Effect)
    buffer = Buffer('hello')
    runtime.mount(buffer)
    runtime.step()
    buffer.update(fade.delayed(100))
    runtime.step()
    runtime.advance_clock(50)
    runtime.step()
    assert Buffer.from_cell_grid(runtime.snapshot().to_cell_grid())[
        0, 0
    ].foreground != Color('red')


def test_effects_validate_their_arguments():
    with pytest.raises(ValueError, match='positive'):
        Fade(duration_milliseconds=0)
    with pytest.raises(ValueError, match='interpolation'):
        Fade(interpolation='bouncy')
    with pytest.raises(ValueError, match='0.0 to 1.0'):
        Glitch(intensity=2.0)
    with pytest.raises(ValueError, match='0 to 100'):
        Fuzz(500)


def test_fuzz_corrupts_glyphs_once_and_deterministically():
    first = Buffer('abcdefghijklmnopqrstuvwxyz' * 4)
    second = first.copy()
    first.update(Fuzz(50, seed=7))
    second.update(Fuzz(50, seed=7))
    assert first.text == second.text
    assert first.text != 'abcdefghijklmnopqrstuvwxyz' * 4
    blank = Buffer(width=5, height=1)
    blank.update(Fuzz(100, seed=1))
    assert blank.text == ''


def test_effects_apply_to_a_regions_target_area_only(runtime):
    buffer = Buffer('aaaaaaaa')
    runtime.mount(buffer)
    runtime.step()
    buffer[0:4, 0:1].update(Dissolve(duration_milliseconds=50, seed=1))
    runtime.step()
    runtime.advance_clock(60)
    runtime.step()
    line = runtime.snapshot().lines()[0]
    assert line[:4].strip() == '' and line[4:] == 'aaaa'


def test_glitch_seed_reproduces_frames():
    def render_frames():
        runtime = Runtime.offscreen(width=40, height=1)
        buffer = Buffer('abcdefghijklmnopqrstuvwxyz0123456789ABCD')
        runtime.mount(buffer)
        runtime.step()
        buffer.update(Glitch(intensity=1.0, duration_milliseconds=500, seed=1))
        frames = []
        for _ in range(10):
            runtime.advance_clock(20)
            runtime.step()
            frames.append(runtime.snapshot().lines())
        runtime.close()
        return frames

    expected_frames = render_frames()
    assert any(frame != expected_frames[0] for frame in expected_frames[1:])
    for _ in range(5):
        assert render_frames() == expected_frames
