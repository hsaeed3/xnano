"""
Benchmarks for xnano-core effects and animation, driven by a manual clock.
"""

from __future__ import annotations

from xnano_core._xnano_core import Buffer, Effect, Runtime, Style, Write


def effect_runtime(effect_count: int) -> tuple[Runtime, Buffer]:
    runtime = Runtime.offscreen(width=200, height=60)
    root = Buffer()
    runtime.mount(root, geometry='inherit')
    root.update(Write('\n'.join(['x' * 200] * 60), style=Style('white', 'black')))
    for index in range(effect_count):
        runtime.effects.start(
            Effect.fade_to('red', 'blue', duration_milliseconds=10_000_000),
            root,
            key=f'fade-{index}',
        )
    runtime.step()
    return runtime, root


def test_one_fade_frame(benchmark):
    runtime, _ = effect_runtime(1)

    def frame():
        runtime.advance_clock(16)
        runtime.step()

    benchmark(frame)
    assert runtime.effects.is_running('fade-0')
    runtime.close()


def test_ten_stacked_fades_frame(benchmark):
    runtime, _ = effect_runtime(10)

    def frame():
        runtime.advance_clock(16)
        runtime.step()

    benchmark(frame)
    assert runtime.effects.is_running('fade-9')
    runtime.close()


def test_dissolve_frame(benchmark):
    runtime = Runtime.offscreen(width=200, height=60)
    root = Buffer()
    runtime.mount(root, geometry='inherit')
    root.update(Write('\n'.join(['x' * 200] * 60)))
    runtime.effects.start(
        Effect.dissolve(duration_milliseconds=10_000_000), root, key='dissolve'
    )
    runtime.step()

    def frame():
        runtime.advance_clock(16)
        runtime.step()

    benchmark(frame)
    assert runtime.effects.is_running('dissolve')
    runtime.close()
