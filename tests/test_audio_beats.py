"""
tests.test_audio_beats

Sounds made once for repeated plays, and beat hooks on a canvas without a device.
"""

from __future__ import annotations

import pytest
from xnano_audio import TerminalSound

import xnano
from xnano.audio import _player


@pytest.fixture
def synthesis_count(monkeypatch) -> list[int]:
    """The number of notes rendered so far, in a list of one."""
    count = [0]
    real = _player.render_note

    def counting(*arguments, **keywords):
        count[0] += 1
        return real(*arguments, **keywords)

    monkeypatch.setattr(_player, 'render_note', counting)
    return count


def plan(canvas, source, **keywords):
    return _player._plan_call(
        source,
        bpm=canvas.bpm,
        instrument=keywords.pop('instrument', None),
        beats=keywords.pop('beats', None),
        velocity=keywords.pop('velocity', None),
        effects=keywords.pop('effects', None),
        volume=1.0,
        pan=0.0,
        at_beat=None,
    )


class TestSoundCache:
    def test_the_same_note_is_synthesized_once(self, synthesis_count):
        with xnano.new(width=8, height=1) as canvas:
            audio = canvas.audio
            first = audio._sound_for(plan(canvas, 'C4'))
            for _ in range(20):
                assert audio._sound_for(plan(canvas, 'C4')) is first
            assert synthesis_count[0] == 1

    def test_anything_that_changes_the_samples_is_a_new_sound(self, synthesis_count):
        with xnano.new(width=8, height=1) as canvas:
            audio = canvas.audio
            variants = [
                {},
                {'instrument': 'bell'},
                {'beats': 2.0},
                {'velocity': 0.3},
                {'effects': [{'kind': 'audio.reverb', 'mix': 0.4}]},
                {'effects': [{'kind': 'audio.reverb', 'mix': 0.9}]},
            ]
            sounds = [audio._sound_for(plan(canvas, 'C4', **v)) for v in variants]
            assert len({id(sound) for sound in sounds}) == len(variants)
            canvas.bpm = 90
            audio._sound_for(plan(canvas, 'C4'))
            assert synthesis_count[0] == len(variants) + 1

    def test_a_melody_text_and_a_chord_are_cached(self, synthesis_count):
        with xnano.new(width=8, height=1) as canvas:
            audio = canvas.audio
            for source in ('C4 E4 G4:2', 'C4+E4', ['C4', 'E4']):
                first = audio._sound_for(plan(canvas, source))
                count = synthesis_count[0]
                assert audio._sound_for(plan(canvas, source)) is first
                assert synthesis_count[0] == count

    def test_the_cache_is_bounded_by_count(self):
        with xnano.new(width=8, height=1) as canvas:
            audio = canvas.audio
            for midi in range(_player._MOST_MIXED_SOUNDS + 10):
                audio._sound_for(plan(canvas, midi % 100 + 10, beats=0.5 + midi * 0.001))
            assert len(audio._mixed) == _player._MOST_MIXED_SOUNDS

    def test_repeated_plans_are_faster_than_synthesizing(self):
        import time

        with xnano.new(width=8, height=1) as canvas:
            audio = canvas.audio
            started = time.perf_counter()
            audio._sound_for(plan(canvas, 'C4'))
            first = time.perf_counter() - started
            started = time.perf_counter()
            for _ in range(100):
                audio._sound_for(plan(canvas, 'C4'))
            repeated = (time.perf_counter() - started) / 100
            assert repeated < first

    def test_a_sound_is_cached_by_identity(self, synthesis_count):
        with xnano.new(width=8, height=1) as canvas:
            audio = canvas.audio
            one = TerminalSound.from_samples([0.0, 0.5, 0.0], sample_rate=44100)
            other = TerminalSound.from_samples([0.0, 0.5, 0.0], sample_rate=44100)
            assert audio._sound_for(plan(canvas, one)) is one
            assert audio._sound_for(plan(canvas, other)) is other


class TestBeatHooks:
    def test_an_offline_canvas_keeps_its_own_time(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.audio.start()
            canvas.bpm = 120
            beats = []
            canvas.hook(on='beat', every=1)(
                lambda context: beats.append(round(context.time.elapsed, 2))
            )
            for _ in range(16):
                canvas.step(delta_seconds=0.1)
            assert beats == pytest.approx([0.5, 1.0, 1.5], abs=0.11)
