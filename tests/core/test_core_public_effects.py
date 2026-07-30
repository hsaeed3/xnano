"""Tests for public effect descriptions lowered through the core engine."""

from __future__ import annotations

import pytest

from xnano.core.effects import build_native_effect, resolve_native_effect
from xnano.effects import (
    AbstractEffect,
    CoalesceEffect,
    DelayEffect,
    DissolveEffect,
    EffectCellFilter,
    FadeEffect,
    FadeFromBothEffect,
    FadeFromEffect,
    FadeToEffect,
    PaintBackgroundEffect,
    PaintEffect,
    PaintForegroundEffect,
    ParallelEffect,
    RepeatEffect,
    SequenceEffect,
    SleepEffect,
    SlideInEffect,
    SlideOutEffect,
    SweepInEffect,
    SweepOutEffect,
)


@pytest.mark.parametrize(
    "effect",
    (
        FadeEffect(color="cyan", interpolation="linear"),
        FadeFromEffect(color="blue", interpolation="smooth_step"),
        FadeToEffect(color="white", background="black"),
        FadeFromBothEffect(color="white", background="black"),
        DissolveEffect(),
        CoalesceEffect(),
        SweepInEffect(direction="up_to_down", color="green"),
        SweepOutEffect(direction="down_to_up", color="green"),
        SlideInEffect(direction="left_to_right", color="yellow"),
        SlideOutEffect(direction="right_to_left", color="yellow"),
        PaintEffect(color="white", background="blue"),
        PaintForegroundEffect(color="cyan"),
        PaintBackgroundEffect(background="black"),
        SleepEffect(duration_ms=10),
    ),
)
def test_transition_catalog_lowers_for_runtime_playback(
    effect: AbstractEffect,
) -> None:
    assert build_native_effect(effect) is not None


def test_nested_loading_transition_lowers_with_filters_and_repetition() -> None:
    transition = SequenceEffect(
        effects=(
            ParallelEffect(
                effects=(
                    FadeEffect(color="cyan", cell_filter="text"),
                    PaintBackgroundEffect(
                        background="black",
                        cell_filter="background_only",
                    ),
                )
            ),
            DelayEffect(
                duration_ms=20,
                child=RepeatEffect(
                    child=CoalesceEffect(cell_filter="non_empty"),
                    times=2,
                ),
            ),
        )
    )

    assert resolve_native_effect(transition) is not None
    assert resolve_native_effect(
        "repeat",
        child=SleepEffect(duration_ms=1),
        duration_ms=20,
    ) is not None
    assert build_native_effect(
        RepeatEffect(child=SleepEffect(duration_ms=1))
    ) is not None


@pytest.mark.parametrize(
    "cell_filter",
    ("all", "text", "non_empty", "background", "background_only"),
)
def test_transition_can_target_each_runtime_cell_group(
    cell_filter: EffectCellFilter,
) -> None:
    assert (
        resolve_native_effect(FadeEffect(color="cyan", cell_filter=cell_filter))
        is not None
    )


@pytest.mark.parametrize(
    ("effect", "message"),
    (
        (SequenceEffect(), "at least one child"),
        (ParallelEffect(), "at least one child"),
        (RepeatEffect(), "require a child"),
        (DelayEffect(), "require a child"),
        (FadeEffect(color="not-a-real-color"), "must resolve to a color"),
    ),
)
def test_invalid_transition_descriptions_explain_the_problem(
    effect: AbstractEffect,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_native_effect(effect)


def test_custom_unsupported_effect_fails_at_the_lowering_boundary() -> None:
    class CustomEffect(AbstractEffect):
        pass

    with pytest.raises(ValueError, match="unsupported effect type"):
        build_native_effect(CustomEffect())
