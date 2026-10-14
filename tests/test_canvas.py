"""
tests.test_canvas

Composing a buffer with make() and building it with make().
"""

from __future__ import annotations

import xnano
from xnano import iter as iter_terminal
from xnano.canvas import make
from xnano_core import Border, Buffer, Effect, Gauge, ParentWidth


def test_make_returns_a_buffer_and_does_not_open_a_terminal():
    card = make(width=12, height=3) | Border('rounded')
    buffer = card.build()
    assert isinstance(buffer, Buffer)
    assert card.build() is buffer
    assert '╭' in buffer.render(format='text')
    assert xnano.make is make


def test_attribute_operators_apply_when_the_buffer_is_built():
    thumb = make('#')
    thumb.x = 1
    thumb.x += 2
    buffer = thumb.build()
    assert buffer.render(format='text') == '#'
    assert buffer.x == 3
    thumb.x += 1
    assert buffer.x == 4


def test_an_expression_is_applied_when_the_buffer_is_placed():
    label = make('hi')
    label.x = ParentWidth // 2
    assert label.build().render(format='text') == 'hi'
    with iter_terminal(offscreen=True, width=10, height=1) as terminal:
        placed = terminal.write(label)
        assert placed.x == 5


def test_an_effect_is_applied_when_the_buffer_is_placed():
    gauge = make(Gauge, ratio=0.5, width=10, height=1)
    gauge.ratio = 0.75
    gauge |= Effect.fade_to('red', duration_milliseconds=100)
    assert gauge.build().ratio == 0.75
    with iter_terminal(offscreen=True, width=12, height=1) as terminal:
        terminal.write(gauge)
        terminal.loop.advance(0.05)
        assert gauge.build().ratio == 0.75


def test_a_child_is_attached_and_not_drawn_until_asked():
    group = make(width=8, height=1)
    group.write('thumb', x=1)
    text = group.build().render(format='text')
    assert text.startswith(' thumb') or text[1] == 't'


def test_adding_is_what_puts_a_composition_on_a_terminal():
    composition = make('slide')
    composition.build()
    with iter_terminal(offscreen=True, width=10, height=1) as terminal:
        assert 'slide' not in terminal.output.snapshot().lines()[0]
        terminal.write(composition)
        terminal.output.render()
        assert 'slide' in terminal.output.snapshot().lines()[0]
