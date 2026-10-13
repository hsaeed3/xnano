"""Every tachyonfx effect that can be described as data is an ``Effect`` that runs."""

from __future__ import annotations

import pytest

from xnano_core import Buffer, Effect, Rectangle, Runtime, Style, TimeElapsed

# Every public constructor in ``tachyonfx::fx`` (0.25), and how it is reached from Python.
UPSTREAM_EFFECTS = {
    'coalesce': 'Effect.coalesce()',
    'coalesce_from': 'Effect.coalesce(style=...)',
    'consume_tick': 'Effect.consume_tick()',
    'darken': 'Effect.darken()',
    'darken_fg': 'Effect.darken(foreground=...)',
    'delay': 'effect.delayed()',
    'dynamic_area': 'effect.with_area(expression)',
    'dissolve': 'Effect.dissolve()',
    'dissolve_to': 'Effect.dissolve(style=...)',
    'evolve': 'Effect.evolve()',
    'evolve_from': 'Effect.evolve_from()',
    'evolve_into': 'Effect.evolve_into()',
    'expand': 'Effect.expand()',
    'explode': 'Effect.explode()',
    'fade_from': 'Effect.fade_from()',
    'fade_from_fg': 'Effect.fade_from(foreground=...)',
    'fade_to': 'Effect.fade_to()',
    'fade_to_fg': 'Effect.fade_to(foreground=...)',
    'freeze_at': 'effect.freeze_at()',
    'hsl_shift': 'Effect.hsl_shift()',
    'hsl_shift_fg': 'Effect.hsl_shift(foreground=...)',
    'lighten': 'Effect.lighten()',
    'lighten_fg': 'Effect.lighten(foreground=...)',
    'never_complete': 'effect.never_complete()',
    'paint': 'Effect.paint()',
    'paint_bg': 'Effect.paint(background=...)',
    'paint_fg': 'Effect.paint(foreground=...)',
    'parallel': 'Effect.parallel()',
    'ping_pong': 'effect.ping_pong()',
    'prolong_end': 'effect.prolong_end()',
    'prolong_start': 'effect.prolong_start()',
    'remap_alpha': 'effect.remap_alpha()',
    'repeat': 'effect.repeated()',
    'repeating': 'effect.repeated()',
    'run_once': 'effect.run_once()',
    'saturate': 'Effect.saturate()',
    'saturate_fg': 'Effect.saturate(foreground=...)',
    'sequence': 'Effect.sequence()',
    'sleep': 'Effect.sleep()',
    'slide_in': 'Effect.slide_in()',
    'slide_out': 'Effect.slide_out()',
    'stretch': 'Effect.stretch()',
    'sweep_in': 'Effect.sweep_in()',
    'sweep_out': 'Effect.sweep_out()',
    'term256_colors': 'Effect.term256_colors()',
    'timed_never_complete': 'effect.timed_never_complete()',
    'translate': 'effect.translated()',
    'with_duration': 'effect.with_duration()',
}

# Upstream constructors that wrap a Rust closure, a shared Rust buffer or a Rust channel,
# which cannot be described as data. They have no Python counterpart.
NOT_DATA = (
    'dispatch_event',
    'effect_fn',
    'effect_fn_buf',
    'offscreen_buffer',
    'resize_area',
    'translate_buf',
)

SHORT = {'duration_milliseconds': 80}
RED = (255, 0, 0)
STYLE = Style(foreground=RED)

EFFECTS = {
    'coalesce': lambda: Effect.coalesce(**SHORT),
    'coalesce_from': lambda: Effect.coalesce(style=STYLE, **SHORT),
    'consume_tick': lambda: Effect.consume_tick(),
    'darken': lambda: Effect.darken(0.5, 0.5, **SHORT),
    'darken_fg': lambda: Effect.darken(foreground=0.5, **SHORT),
    'delay': lambda: Effect.dissolve(**SHORT).delayed(20),
    'dynamic_area': lambda: Effect.dissolve(**SHORT).with_area(
        (TimeElapsed < 0.04).choose(Rectangle(0, 0, 3, 1), Rectangle(3, 0, 3, 1))
    ),
    'dissolve': lambda: Effect.dissolve(**SHORT),
    'dissolve_to': lambda: Effect.dissolve(style=STYLE, **SHORT),
    'evolve': lambda: Effect.evolve('shaded', **SHORT),
    'evolve_from': lambda: Effect.evolve_from('quadrants', **SHORT),
    'evolve_into': lambda: Effect.evolve_into('squares', style=STYLE, **SHORT),
    'expand': lambda: Effect.expand('vertical', style=STYLE, **SHORT),
    'explode': lambda: Effect.explode(force=4.0, **SHORT),
    'fade_from': lambda: Effect.fade_from(RED, 'blue', **SHORT),
    'fade_from_fg': lambda: Effect.fade_from(RED, **SHORT),
    'fade_to': lambda: Effect.fade_to(RED, 'blue', **SHORT),
    'fade_to_fg': lambda: Effect.fade_to(RED, **SHORT),
    'freeze_at': lambda: Effect.dissolve(**SHORT).freeze_at(0.5),
    'hsl_shift': lambda: Effect.hsl_shift((30.0, 0.0, 0.0), (0.0, 10.0, 0.0), **SHORT),
    'hsl_shift_fg': lambda: Effect.hsl_shift((30.0, 0.0, 0.0), **SHORT),
    'lighten': lambda: Effect.lighten(0.5, 0.5, **SHORT),
    'lighten_fg': lambda: Effect.lighten(foreground=0.5, **SHORT),
    'never_complete': lambda: Effect.dissolve(**SHORT).never_complete(),
    'paint': lambda: Effect.paint(RED, 'blue', **SHORT),
    'paint_bg': lambda: Effect.paint(background='blue', **SHORT),
    'paint_fg': lambda: Effect.paint(RED, **SHORT),
    'parallel': lambda: Effect.parallel(
        [Effect.dissolve(**SHORT), Effect.fade_to(RED, **SHORT)]
    ),
    'ping_pong': lambda: Effect.dissolve(**SHORT).ping_pong(),
    'prolong_end': lambda: Effect.dissolve(**SHORT).prolong_end(20),
    'prolong_start': lambda: Effect.dissolve(**SHORT).prolong_start(20),
    'remap_alpha': lambda: Effect.dissolve(**SHORT).remap_alpha(0.2, 0.8),
    'repeat': lambda: Effect.dissolve(**SHORT).repeated(2),
    'repeating': lambda: Effect.dissolve(**SHORT).repeated(),
    'run_once': lambda: Effect.dissolve(**SHORT).run_once(),
    'saturate': lambda: Effect.saturate(0.5, 0.5, **SHORT),
    'saturate_fg': lambda: Effect.saturate(foreground=0.5, **SHORT),
    'sequence': lambda: Effect.sequence(
        [Effect.dissolve(**SHORT), Effect.fade_to(RED, **SHORT)]
    ),
    'sleep': lambda: Effect.sleep(40),
    'slide_in': lambda: Effect.slide_in('left_to_right', **SHORT),
    'slide_out': lambda: Effect.slide_out('up_to_down', **SHORT),
    'stretch': lambda: Effect.stretch('right_to_left', style=STYLE, **SHORT),
    'sweep_in': lambda: Effect.sweep_in('down_to_up', **SHORT),
    'sweep_out': lambda: Effect.sweep_out('right_to_left', **SHORT),
    'term256_colors': lambda: Effect.term256_colors(),
    'timed_never_complete': lambda: Effect.dissolve(**SHORT).timed_never_complete(200),
    'translate': lambda: Effect.dissolve(**SHORT).translated(x=2, y=1, **SHORT),
    'with_duration': lambda: Effect.dissolve(**SHORT).with_duration(60),
}


def test_every_upstream_effect_has_a_python_counterpart_or_a_stated_reason():
    assert set(EFFECTS) == set(UPSTREAM_EFFECTS)
    assert not set(NOT_DATA) & set(UPSTREAM_EFFECTS)


@pytest.mark.parametrize('name', sorted(EFFECTS))
def test_the_effect_runs_on_a_mounted_buffer(name):
    effect = EFFECTS[name]()
    assert isinstance(effect, Effect)
    with Runtime.offscreen(width=12, height=3) as runtime:
        buffer = Buffer.with_text('hello world')
        runtime.mount(buffer)
        runtime.step()
        buffer.update(effect)
        for _ in range(8):
            runtime.advance_clock(30)
            runtime.step()
        assert runtime.snapshot().lines()


@pytest.mark.parametrize(
    'name', ['evolve', 'evolve_into', 'evolve_from', 'expand', 'explode', 'stretch']
)
def test_the_new_effects_report_their_kind(name):
    assert EFFECTS[name]().kind == name


def test_evolve_steps_cells_through_its_symbols():
    with Runtime.offscreen(width=6, height=1) as runtime:
        buffer = Buffer.with_text('xxxxxx')
        runtime.mount(buffer)
        runtime.step()
        buffer.update(Effect.evolve('shaded', duration_milliseconds=100))
        runtime.step()
        runtime.advance_clock(40)
        runtime.step()
        middle = runtime.snapshot().lines()[0]
        assert any(symbol in middle for symbol in '░▒▓█ ')


def test_translate_moves_what_an_effect_draws():
    effect = Effect.dissolve(duration_milliseconds=50).translated(
        x=3, duration_milliseconds=50
    )
    assert effect.kind == 'translate'
    assert len(effect.children) == 1


@pytest.mark.parametrize(
    ('call', 'message'),
    [
        (lambda: Effect.evolve('nope'), 'not a symbol set'),
        (lambda: Effect.expand('diagonal'), 'not an expand direction'),
        (lambda: Effect.stretch('sideways'), 'not a motion direction'),
    ],
)
def test_new_effects_reject_unknown_names_at_once(call, message):
    with pytest.raises(ValueError, match=message):
        call()


def test_an_effect_that_cannot_run_says_so_instead_of_failing_silently():
    from xnano_core._xnano_core import RenderError

    with Runtime.offscreen(width=6, height=1) as runtime:
        buffer = Buffer.with_text('xxxxxx')
        runtime.mount(buffer)
        runtime.step()
        buffer.update(Effect.hsl_shift(duration_milliseconds=50))
        runtime.advance_clock(10)
        with pytest.raises(RenderError, match='hsl_shift effect could not run'):
            runtime.step()
        # The broken effect is gone and the runtime carries on.
        runtime.advance_clock(10)
        runtime.step()
        assert runtime.snapshot().lines()[0] == 'xxxxxx'


def test_dynamic_area_moves_without_restarting_the_effect():
    area = (TimeElapsed < 0.05).choose(Rectangle(0, 0, 2, 1), Rectangle(3, 0, 2, 1))
    with Runtime.offscreen(width=6, height=1) as runtime:
        buffer = Buffer.with_text('xxxxxx')
        runtime.mount(buffer)
        runtime.step()
        buffer.update(
            Effect.paint(foreground='red', duration_milliseconds=100).with_area(area)
        )
        runtime.step()
        runtime.advance_clock(60)
        runtime.step()
        cells = Buffer.from_cell_grid(runtime.snapshot().to_cell_grid())
        assert cells[0, 0].foreground != cells[3, 0].foreground
        assert runtime.effects.running()[0].elapsed_milliseconds == 60


def test_effect_area_rejects_non_rectangles():
    with pytest.raises(TypeError, match='Expected a Rectangle'):
        Effect.dissolve().with_area(3)
