"""
tests.test_random_choices

``random()`` on the inputs a hook can push to and on the border settings: valid choices only,
positions inside the canvas or placement the input belongs to, repeatable with ``random.seed``,
and delivered to hooks like any other pushed event.
"""

from __future__ import annotations

import random

import pytest
from typing_extensions import assert_type

import xnano
from xnano.devices import KeyName
from xnano.hooks._triggers import _KEY_NAMES

BORDER_KINDS = {'plain', 'rounded', 'double', 'thick'}


def _run_on_tick(canvas, owner, action, results):
    """Attach a tick hook to ``owner`` that records ``action(context)`` and run it once."""

    @owner.hook(on='tick', after=0.05)
    def act(context: xnano.Context) -> None:
        results.append(action(context))

    canvas.clock.step(delta_seconds=0.1)
    canvas.deliver_events()


def test_keyboard_random_presses_a_closed_key_and_returns_it():
    heard: list[str | None] = []
    pressed: list[KeyName] = []
    with xnano.new(width=8, height=1) as canvas:

        @canvas.hook(on='key')
        def listen(context: xnano.Context) -> None:
            assert context.keyboard.modifiers == frozenset()
            heard.append(context.keyboard.key)

        random.seed(11)
        for _ in range(60):
            canvas.clock.step(delta_seconds=0.01)
            _run_on_tick(canvas, canvas, lambda c: c.keyboard.random(), pressed)
    assert heard == pressed
    assert set(pressed) <= set(_KEY_NAMES)
    assert 'unknown' not in pressed and 'null' not in pressed
    assert len(set(pressed)) > 5


def test_keyboard_random_type():
    with xnano.new(width=8, height=1) as canvas:
        seen: list[KeyName] = []

        def action(context: xnano.Context) -> KeyName:
            name = context.keyboard.random()
            assert_type(name, KeyName)
            return name

        _run_on_tick(canvas, canvas, action, seen)
    assert len(seen) == 1


def _mouse_cells(canvas, owner, kind, count=40):
    kinds: list[tuple[str | None, tuple[int, int]]] = []

    @canvas.hook(on='mouse')
    def listen(context: xnano.Context) -> None:
        position = context.mouse.position
        kinds.append((context.mouse.kind, (position.x, position.y)))

    returned: list[tuple[int, int]] = []

    timing = {'after': 0.01} if count == 1 else {'every': 0.01}

    @owner.hook(on='tick', **timing)
    def act(context: xnano.Context) -> None:
        returned.append(context.mouse.random(kind))

    for _ in range(count):
        canvas.clock.step(delta_seconds=0.02)
    canvas.deliver_events()
    return kinds, returned


def test_mouse_random_clicks_inside_the_canvas():
    with xnano.new(width=12, height=5) as canvas:
        random.seed(1)
        kinds, returned = _mouse_cells(canvas, canvas, 'click')
    assert returned
    assert all(0 <= x < 12 and 0 <= y < 5 for x, y in returned)
    assert [kind for kind, _ in kinds[:2]] == ['press', 'release']
    assert [cell for _, cell in kinds[:2]] == [returned[0], returned[0]]


def test_mouse_random_stays_inside_a_placement():
    with xnano.new(width=30, height=12) as canvas:
        card = canvas.screen.write('hello', x=10, y=4, border='plain')
        random.seed(2)
        kinds, returned = _mouse_cells(canvas, card, 'click')
        left, top = card.x, card.y
        right, bottom = left + card.width, top + card.height
    assert returned
    assert all(left <= x < right and top <= y < bottom for x, y in returned)
    assert all(left <= x < right and top <= y < bottom for _, (x, y) in kinds)


def test_mouse_random_stays_inside_a_nested_placement():
    with xnano.new(width=40, height=16) as canvas:
        outer = canvas.screen.write(xnano.box(20, 8), x=6, y=3)
        inner = outer.write('hi', x=4, y=2, border='plain')
        bounds = inner._buffer._absolute_bounds
        left, top = bounds.x, bounds.y
        right, bottom = left + bounds.width, top + bounds.height
        assert (left, top) != (inner.x, inner.y)
        random.seed(3)
        _kinds, returned = _mouse_cells(canvas, inner, 'move')
    assert returned
    assert all(left <= x < right and top <= y < bottom for x, y in returned)


def test_mouse_random_drag_presses_drags_and_releases_inside_the_bounds():
    with xnano.new(width=30, height=12) as canvas:
        card = canvas.screen.write(xnano.box(10, 4), x=7, y=5)
        random.seed(4)
        kinds, returned = _mouse_cells(canvas, card, 'drag', count=1)
        left, top = card.x, card.y
        right, bottom = left + card.width, top + card.height
    assert [kind for kind, _ in kinds] == ['press', 'drag', 'release']
    assert all(left <= x < right and top <= y < bottom for _, (x, y) in kinds)
    assert kinds[2][1] == kinds[1][1] == returned[0]


def test_mouse_random_move_moves_the_pointer():
    with xnano.new(width=12, height=5) as canvas:
        random.seed(5)
        kinds, returned = _mouse_cells(canvas, canvas, 'move', count=1)
    assert kinds == [('move', returned[0])]


def test_mouse_random_rejects_an_unknown_kind():
    with xnano.new(width=12, height=5) as canvas:
        results: list[object] = []
        with pytest.raises(Exception, match="'click', 'drag' or 'move'"):
            _run_on_tick(canvas, canvas, lambda c: c.mouse.random('hover'), results)


def test_scroll_random_turns_the_wheel_inside_the_bounds():
    turned: list[tuple[int, int, int, int]] = []
    pushed: list[tuple[int, int]] = []
    with xnano.new(width=30, height=12) as canvas:
        card = canvas.screen.write(xnano.box(10, 4), x=7, y=5)

        @canvas.hook(on='scroll')
        def listen(context: xnano.Context) -> None:
            event = context.mouse.scroll.event
            assert event is not None
            turned.append(
                (event.column, event.row, context.mouse.scroll.x, context.mouse.scroll.y)
            )

        @card.hook(on='tick', every=0.01)
        def act(context: xnano.Context) -> None:
            pushed.append(context.mouse.scroll.random())

        random.seed(6)
        for _ in range(40):
            canvas.clock.step(delta_seconds=0.02)
        canvas.deliver_events()
        left, top = card.x, card.y
        right, bottom = left + card.width, top + card.height
    assert pushed and [(x, y) for _, _, x, y in turned] == pushed
    for column, row, steps_x, steps_y in turned:
        assert left <= column < right and top <= row < bottom
        assert (steps_x == 0) != (steps_y == 0)
        assert 1 <= abs(steps_x + steps_y) <= 3


def test_random_is_repeatable_with_a_seed():
    def play() -> list[object]:
        outcomes: list[object] = []
        with xnano.new(width=30, height=12) as canvas:
            card = canvas.screen.write('x', x=3, y=3, border='plain')

            def action(context: xnano.Context) -> object:
                return (
                    context.keyboard.random(),
                    context.mouse.random(),
                    context.mouse.scroll.random(),
                    card.border.random(),
                    card.border.left.random(),
                )

            random.seed(99)
            _run_on_tick(canvas, card, action, outcomes)
        return outcomes

    assert play() == play()


def test_random_needs_a_cell_on_the_screen():
    with xnano.new(width=10, height=4) as canvas:
        away = canvas.screen.write('x', x=50, y=50)
        results: list[object] = []
        with pytest.raises(Exception, match='covers no cell on the screen'):
            _run_on_tick(canvas, away, lambda c: c.mouse.random(), results)


def test_border_random_sets_a_valid_kind_on_every_side():
    with xnano.new(width=12, height=5) as canvas:
        card = canvas.screen.write('hi')
        seen = set()
        for seed in range(40):
            random.seed(seed)
            kind = card.border.random()
            assert kind in BORDER_KINDS
            assert card.border.kind == kind
            assert {card.border.top.kind, card.border.left.kind} == {kind}
            seen.add(kind)
        assert seen == BORDER_KINDS
        assert 'hi' in canvas.screen.render()


def test_border_random_draws_immediately():
    with xnano.new(width=12, height=5) as canvas:
        card = canvas.screen.write('hi')
        random.seed(0)
        kind = card.border.random()
        glyph = {'plain': '┌', 'rounded': '╭', 'double': '╔', 'thick': '┏'}[kind]
        assert glyph in canvas.screen.render()


def test_border_side_random_changes_only_that_side():
    with xnano.new(width=12, height=5) as canvas:
        card = canvas.screen.write('hi', border='plain')
        seen = set()
        for seed in range(40):
            random.seed(seed)
            kind = card.border.top.random()
            assert kind in BORDER_KINDS and card.border.top.kind == kind
            assert card.border.bottom.kind == 'plain'
            seen.add(kind)
        assert seen == BORDER_KINDS


def test_border_side_random_draws_a_side_that_was_off():
    with xnano.new(width=12, height=5) as canvas:
        card = canvas.screen.write('hi', border='plain')
        card.border.left = False
        assert card.border.left.kind is None
        assert card.border.left.random() in BORDER_KINDS
        assert card.border.left.kind is not None
