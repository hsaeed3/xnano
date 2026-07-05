"""Effect builder and composition tests."""

from __future__ import annotations

from xnano_core.rust.native import (
    Color,
    Effect,
    fade_to_fg,
    parallel_effects,
    sequence_effects,
    sleep_effect,
)
from xnano_core.rust.engine import CoreRenderContent, CoreRenderNode, CoreSession


def test_effect_builder_returns_effect() -> None:
    effect = fade_to_fg(Color.RED, 120)
    assert isinstance(effect, Effect)
    assert effect.name()


def test_effect_with_area_and_filter() -> None:
    from xnano_core.rust.native import CellFilter, Rect

    effect = fade_to_fg(Color.BLUE, 80).with_area(Rect(0, 0, 10, 5))
    assert effect.get_area() is not None
    filtered = effect.with_filter(CellFilter.ALL)
    assert filtered.get_filter() is not None


def test_sequence_and_parallel_combinators() -> None:
    a = sleep_effect(50)
    b = sleep_effect(50)
    seq = sequence_effects([a, b])
    par = parallel_effects([a, b])
    assert isinstance(seq, Effect)
    assert isinstance(par, Effect)


def test_session_compose_and_process(
    offscreen_session: CoreSession, column_tree
) -> None:
    effect = sequence_effects(
        [fade_to_fg(Color.YELLOW, 100), sleep_effect(50)]
    )
    offscreen_session.add_effect(effect)
    offscreen_session.render(column_tree)
    assert offscreen_session.is_animating()
    offscreen_session.render(column_tree)