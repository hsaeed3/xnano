"""
tests.test_audio_player

Audio on the real output device. Skipped on computers without one (such as CI).
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable

import pytest
from xnano_audio import TerminalAudioPlayer, TerminalMelody, TerminalNote

import xnano

pytestmark = pytest.mark.skipif(
    not TerminalAudioPlayer.is_available(), reason='no sound output device'
)


def wait_until(
    condition: Callable[[], bool],
    *,
    timeout_seconds: float = 5.0,
    interval_seconds: float = 0.02,
) -> bool:
    """Check the condition until it holds or the timeout passes, and return the last result."""
    deadline = time.monotonic() + timeout_seconds
    holds = condition()
    while not holds and time.monotonic() < deadline:
        time.sleep(interval_seconds)
        holds = condition()
    return holds


def test_a_note_plays_on_the_real_device_and_the_clock_runs():
    with xnano.new(realtime=True, width=8, height=1) as canvas:
        canvas.clock.bpm = 240
        canvas.speaker.play('C4', volume=0.0)
        canvas.clock.beats.start()
        assert wait_until(lambda: canvas.evaluate(canvas.clock.beats.position) > 0.5), (
            f'the clock stayed at beat {canvas.evaluate(canvas.clock.beats.position)}'
        )


def test_a_melody_is_scheduled_on_a_beat_of_the_real_clock():
    melody = TerminalMelody([TerminalNote('C4'), TerminalNote('E4', start_beats=1)])
    with xnano.new(realtime=True, width=8, height=1) as canvas:
        canvas.speaker.play(melody, volume=0.0, at_beat=1)
        # Playing on a beat starts the clock.
        assert wait_until(lambda: canvas.evaluate(canvas.clock.beats.position) > 0), (
            f'the clock stayed at beat {canvas.evaluate(canvas.clock.beats.position)}'
        )


def test_a_note_played_on_the_real_device_has_its_region_on_the_timeline():
    with xnano.new(realtime=True, width=8, height=1) as canvas:
        region = canvas.speaker.play(
            xnano.Note('E4', beats=2), volume=0.0, at_beat=4
        )._region
        assert region is not None
        assert (region.x, region.width) == (4.0, 2.0)
        assert (region.y, region.height) == (64, 1)


@pytest.mark.skipif(
    os.environ.get('XNANO_TEST_MICROPHONE') != '1',
    reason='opening the microphone can ask for permission; set XNANO_TEST_MICROPHONE=1',
)
def test_the_microphone_level_is_a_number_between_zero_and_one():
    with xnano.new(realtime=True, width=8, height=1) as canvas:
        time.sleep(0.3)
        level = canvas.evaluate(canvas.microphone.level)
        assert 0.0 <= level <= 1.0
