"""Tests for xnano.effects."""

from __future__ import annotations

from xnano_core.rust import native

from xnano.effects import (
    CoalesceEffect,
    DissolveEffect,
    Effect,
    FadeEffect,
    SweepInEffect,
)
from xnano.tui.effects import (
    build_native_effect,
    resolve_native_effect,
)


def test_effect_factory_builds_dissolve() -> None:
    effect = Effect("dissolve", duration_ms=250)
    native_effect = build_native_effect(effect)
    assert isinstance(native_effect, native.Effect)


def test_effect_factory_builds_fade_with_color() -> None:
    effect = Effect("fade", color="#ff00aa", duration_ms=400)
    assert isinstance(effect, FadeEffect)
    native_effect = build_native_effect(effect)
    assert isinstance(native_effect, native.Effect)


def test_effect_factory_builds_sweep_in() -> None:
    effect = Effect(
        "sweep_in",
        direction="left_to_right",
        color="teal",
        gradient_length=10,
        randomness=1,
        duration_ms=500,
    )
    assert isinstance(effect, SweepInEffect)
    native_effect = build_native_effect(effect)
    assert isinstance(native_effect, native.Effect)


def test_resolve_native_effect_accepts_subclass() -> None:
    effect = CoalesceEffect(duration_ms=120)
    native_effect = resolve_native_effect(effect)
    assert isinstance(native_effect, native.Effect)


def test_effect_cell_filter_is_lowered() -> None:
    effect = CoalesceEffect(
        duration_ms=120,
        cell_filter="background_only",
    )
    native_effect = resolve_native_effect(effect)
    assert native_effect.get_filter() is not None


def test_resolve_native_effect_accepts_kind_string() -> None:
    native_effect = resolve_native_effect("dissolve", duration_ms=180)
    assert isinstance(native_effect, native.Effect)


def test_custom_subclass_round_trip() -> None:
    effect = DissolveEffect(duration_ms=220, interpolation="cubic_out")
    assert effect.interpolation == "cubic_out"
    native_effect = build_native_effect(effect)
    assert isinstance(native_effect, native.Effect)


def test_resolve_native_effect_inline_kind_kwargs() -> None:
    native_effect = resolve_native_effect(
        "sweep_in",
        duration_ms=350,
        direction="right_to_left",
        color="#00ffcc",
        gradient_length=8,
        randomness=3,
        interpolation="smooth_step",
    )
    assert isinstance(native_effect, native.Effect)
