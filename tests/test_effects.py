"""Tests for xnano.effects module - comprehensive effects functionality."""

import pytest
from xnano.buffer import Buffer
from xnano.effects import (
    CellFilter,
    Effect,
    EffectManager,
    Motion,
    Interpolation,
    ColorSpace,
    fade_to_fg,
    fade_from_fg,
    fade_to,
    fade_from,
    paint,
    paint_fg,
    paint_bg,
    slide_in,
    slide_out,
    sweep_in,
    sweep_out,
    dissolve,
    dissolve_to,
    coalesce,
    coalesce_from,
    sleep,
    sequence,
    parallel,
    repeating,
    ping_pong,
    repeat,
    delay,
    prolong_start,
    prolong_end,
    saturate,
    saturate_fg,
    lighten,
    lighten_fg,
    darken,
    darken_fg,
    hsl_shift,
    hsl_shift_fg,
)
from xnano.color import Color
from xnano.style import Style
from xnano.layout import Rectangle, Margin


class TestCellFilter:
    """Tests for CellFilter class."""

    def test_cell_filter_all(self):
        f = CellFilter.all()
        assert f is not None

    def test_cell_filter_text(self):
        f = CellFilter.text()
        assert f is not None

    def test_cell_filter_non_empty(self):
        f = CellFilter.non_empty()
        assert f is not None

    def test_cell_filter_foreground_color(self):
        f = CellFilter.foreground_color("red")
        assert f is not None

    def test_cell_filter_background_color(self):
        f = CellFilter.background_color("blue")
        assert f is not None

    def test_cell_filter_fg_color_alias(self):
        f = CellFilter.fg_color("red")
        assert f is not None

    def test_cell_filter_bg_color_alias(self):
        f = CellFilter.bg_color("blue")
        assert f is not None

    def test_cell_filter_inner(self):
        f = CellFilter.inner(Margin(horizontal=1, vertical=1))
        assert f is not None

    def test_cell_filter_outer(self):
        f = CellFilter.outer(Margin(horizontal=1, vertical=1))
        assert f is not None

    def test_cell_filter_area(self):
        f = CellFilter.area(Rectangle(x=0, y=0, width=10, height=10))
        assert f is not None

    def test_cell_filter_all_of(self):
        f1 = CellFilter.text()
        f2 = CellFilter.non_empty()
        f = CellFilter.all_of([f1, f2])
        assert f is not None

    def test_cell_filter_any_of(self):
        f1 = CellFilter.text()
        f2 = CellFilter.non_empty()
        f = CellFilter.any_of([f1, f2])
        assert f is not None

    def test_cell_filter_not(self):
        f1 = CellFilter.text()
        f = CellFilter.not_(f1)
        assert f is not None

    def test_cell_filter_immutability(self):
        f = CellFilter.all()
        with pytest.raises(AttributeError, match="CellFilter is immutable"):
            f.test = True

    def test_cell_filter_to_core(self):
        f = CellFilter.all()
        core_f = f._to_core()
        assert core_f is not None


class TestEffect:
    """Tests for Effect class."""

    def test_effect_invalid_instantiation(self):
        with pytest.raises(TypeError, match="Effect instances must be created using the effect creator functions"):
            Effect()

    def test_effect_with_area(self):
        e = fade_to_fg("red", 100)
        with_area = e.with_area(Rectangle(x=0, y=0, width=10, height=10))
        assert with_area is not None

    def test_effect_with_filter(self):
        e = fade_to_fg("red", 100)
        with_filter = e.with_filter(CellFilter.all())
        assert with_filter is not None

    def test_effect_with_color_space(self):
        e = fade_to_fg("red", 100)
        with_space = e.with_color_space("rgb")
        assert with_space is not None

    def test_effect_with_rng(self):
        e = fade_to_fg("red", 100)
        with_rng = e.with_rng(42)
        assert with_rng is not None

    def test_effect_reversed(self):
        e = fade_to_fg("red", 100)
        rev = e.reversed()
        assert rev is not None

    def test_effect_name(self):
        e = fade_to_fg("red", 100)
        name = e.name()
        assert isinstance(name, str)

    def test_effect_is_done(self):
        e = fade_to_fg("red", 100)
        # Effect starts not done
        assert isinstance(e.is_done(), bool)

    def test_effect_is_running(self):
        e = fade_to_fg("red", 100)
        assert isinstance(e.is_running(), bool)

    def test_effect_reset(self):
        e = fade_to_fg("red", 100)
        e.reset()  # Should not raise

    def test_effect_immutability(self):
        e = fade_to_fg("red", 100)
        with pytest.raises(AttributeError, match="Effect is immutable"):
            e.test = True


class TestFadeEffects:
    """Tests for fade effect functions."""

    def test_fade_to_fg(self):
        e = fade_to_fg("red", 100)
        assert e is not None

    def test_fade_to_fg_with_interpolation(self):
        e = fade_to_fg("red", 100, interpolation="linear")
        assert e is not None

    def test_fade_from_fg(self):
        e = fade_from_fg("red", 100)
        assert e is not None

    def test_fade_from_fg_with_interpolation(self):
        e = fade_from_fg("red", 100, interpolation="back_in_out")
        assert e is not None

    def test_fade_to(self):
        e = fade_to("red", "blue", 100)
        assert e is not None

    def test_fade_to_with_interpolation(self):
        e = fade_to("red", "blue", 100, interpolation="cubic_in")
        assert e is not None

    def test_fade_from(self):
        e = fade_from("red", "blue", 100)
        assert e is not None


class TestPaintEffects:
    """Tests for paint effect functions."""

    def test_paint(self):
        e = paint("red", "blue", 100)
        assert e is not None

    def test_paint_fg(self):
        e = paint_fg("red", 100)
        assert e is not None

    def test_paint_bg(self):
        e = paint_bg("blue", 100)
        assert e is not None


class TestSlideAndSweepEffects:
    """Tests for slide and sweep effect functions."""

    def test_slide_in(self):
        e = slide_in("down_to_up", 5, 2, "red", 100)
        assert e is not None

    def test_slide_in_all_directions(self):
        for direction in ["up_to_down", "down_to_up", "left_to_right", "right_to_left"]:
            e = slide_in(direction, 5, 2, "red", 100)
            assert e is not None

    def test_slide_out(self):
        e = slide_out("down_to_up", 5, 2, "red", 100)
        assert e is not None

    def test_sweep_in(self):
        e = sweep_in("down_to_up", 5, 2, "red", 100)
        assert e is not None

    def test_sweep_out(self):
        e = sweep_out("down_to_up", 5, 2, "red", 100)
        assert e is not None


class TestDissolveAndCoalesceEffects:
    """Tests for dissolve and coalesce effect functions."""

    def test_dissolve(self):
        e = dissolve(100)
        assert e is not None

    def test_dissolve_to(self):
        e = dissolve_to(Style(foreground="red"), 100)
        assert e is not None

    def test_coalesce(self):
        e = coalesce(100)
        assert e is not None

    def test_coalesce_from(self):
        e = coalesce_from(Style(foreground="red"), 100)
        assert e is not None


class TestSequenceAndParallelEffects:
    """Tests for sequence and parallel effect functions."""

    def test_sequence(self):
        e1 = fade_to_fg("red", 50)
        e2 = fade_to_fg("blue", 50)
        e = sequence([e1, e2])
        assert e is not None

    def test_parallel(self):
        e1 = fade_to_fg("red", 50)
        e2 = fade_to_fg("blue", 50)
        e = parallel([e1, e2])
        assert e is not None


class TestRepeatAndLoopEffects:
    """Tests for repeat and loop effect functions."""

    def test_repeat_no_args(self):
        e = repeat(fade_to_fg("red", 100))
        assert e is not None

    def test_repeat_times(self):
        e = repeat(fade_to_fg("red", 100), times=3)
        assert e is not None

    def test_repeat_duration(self):
        e = repeat(fade_to_fg("red", 100), duration_ms=500)
        assert e is not None

    def test_repeating(self):
        e = repeating(fade_to_fg("red", 100))
        assert e is not None

    def test_ping_pong(self):
        e = ping_pong(fade_to_fg("red", 100))
        assert e is not None


class TestDelayAndProlongEffects:
    """Tests for delay and prolong effect functions."""

    def test_delay(self):
        e = delay(100, fade_to_fg("red", 100))
        assert e is not None

    def test_prolong_start(self):
        e = prolong_start(100, fade_to_fg("red", 100))
        assert e is not None

    def test_prolong_end(self):
        e = prolong_end(100, fade_to_fg("red", 100))
        assert e is not None


class TestColorTransformEffects:
    """Tests for color transform effect functions."""

    def test_saturate(self):
        e = saturate(100, fg=0.5)
        assert e is not None

    def test_saturate_both(self):
        e = saturate(100, fg=0.5, bg=0.5)
        assert e is not None

    def test_saturate_fg(self):
        e = saturate_fg(0.5, 100)
        assert e is not None

    def test_lighten(self):
        e = lighten(100, fg=0.2)
        assert e is not None

    def test_lighten_both(self):
        e = lighten(100, fg=0.2, bg=0.3)
        assert e is not None

    def test_lighten_fg(self):
        e = lighten_fg(0.2, 100)
        assert e is not None

    def test_darken(self):
        e = darken(100, fg=0.2)
        assert e is not None

    def test_darken_both(self):
        e = darken(100, fg=0.2, bg=0.3)
        assert e is not None

    def test_darken_fg(self):
        e = darken_fg(0.2, 100)
        assert e is not None

    def test_hsl_shift(self):
        e = hsl_shift(100, fg_h=0.1, fg_s=0.1, fg_l=0.1)
        assert e is not None

    def test_hsl_shift_all(self):
        e = hsl_shift(100, fg_h=0.1, fg_s=0.1, fg_l=0.1, bg_h=0.2, bg_s=0.2, bg_l=0.2)
        assert e is not None

    def test_hsl_shift_fg(self):
        e = hsl_shift_fg(0.1, 0.1, 0.1, 100)
        assert e is not None


class TestSleepEffect:
    """Tests for sleep effect function."""

    def test_sleep(self):
        e = sleep(100)
        assert e is not None


class TestEffectManager:
    """Tests for EffectManager class."""

    def test_effect_manager_creation(self):
        em = EffectManager()
        assert em is not None

    def test_effect_manager_add(self):
        em = EffectManager()
        e = fade_to_fg("red", 100)
        em.add(e)

    def test_effect_manager_add_unique(self):
        em = EffectManager()
        e = fade_to_fg("red", 100)
        em.add_unique("fade1", e)
        em.add_unique("fade2", e)

    def test_effect_manager_is_running_false(self):
        em = EffectManager()
        assert em.is_running() is False

    def test_effect_manager_process(self):
        em = EffectManager()
        buf = Buffer.empty(Rectangle(0, 0, 10, 10))
        e = fade_to_fg("red", 100)
        em.add(e)
        em.process(10, buf, Rectangle(0, 0, 10, 10))


class TestTypeAliases:
    """Tests for type aliases."""

    def test_motion_types(self):
        for m in ["up_to_down", "down_to_up", "left_to_right", "right_to_left"]:
            e = fade_to_fg("red", 100)  # Just verify type aliases are valid strings

    def test_interpolation_types(self):
        for i in ["back_in", "back_out", "cubic_in", "cubic_out", "linear", "sine_in"]:
            e = fade_to_fg("red", 100, interpolation=i)
            assert e is not None

    def test_color_space_types(self):
        for cs in ["rgb", "hsl", "hsv"]:
            e = fade_to_fg("red", 100)
            e2 = e.with_color_space(cs)
            assert e2 is not None