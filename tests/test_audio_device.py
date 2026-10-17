"""
tests.test_audio_device

Audio on the real output device. Skipped on computers without one (such as CI).
"""

from __future__ import annotations

import os
import time

import pytest
from xnano_audio import TerminalAudioPlayer, TerminalMelody, TerminalNote

import xnano

pytestmark = pytest.mark.skipif(
    not TerminalAudioPlayer.is_available(), reason='no sound output device'
)


def test_a_note_plays_on_the_real_device_and_the_clock_runs():
    with xnano.new(realtime=True, width=8, height=1) as canvas:
        canvas.bpm = 240
        canvas.audio.play('C4', volume=0.0)
        canvas.audio.start()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if canvas.inspect(canvas.audio.beat) > 0.5:
                break
            time.sleep(0.05)
        assert canvas.inspect(canvas.audio.beat) > 0.5


def test_a_melody_is_scheduled_on_a_beat_of_the_real_clock():
    melody = TerminalMelody([TerminalNote('C4'), TerminalNote('E4', start_beats=1)])
    with xnano.new(realtime=True, width=8, height=1) as canvas:
        canvas.audio.play(melody, volume=0.0, at_beat=1)
        # Playing on a beat starts the clock.
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and canvas.inspect(canvas.audio.beat) <= 0:
            time.sleep(0.05)
        assert canvas.inspect(canvas.audio.beat) > 0


@pytest.mark.skipif(
    os.environ.get('XNANO_TEST_MICROPHONE') != '1',
    reason='opening the microphone can ask for permission; set XNANO_TEST_MICROPHONE=1',
)
def test_the_microphone_level_is_a_number_between_zero_and_one():
    with xnano.new(realtime=True, width=8, height=1) as canvas:
        time.sleep(0.3)
        level = canvas.inspect(canvas.audio.level)
        assert 0.0 <= level <= 1.0
