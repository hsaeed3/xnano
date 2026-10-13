"""Paragraph, Clear, CustomWidget and Live: live settings, bindings and value semantics."""

from __future__ import annotations

import copy

import pytest

from xnano_core._xnano_core import (
    Block,
    Border,
    Buffer,
    Clear,
    CustomWidget,
    Live,
    Paragraph,
    RenderError,
    Runtime,
    TerminalStatePatch,
    TerminalStateSchema,
    TerminalStateStore,
    Write,
    _state_expression,
)


def text(widget) -> list[str]:
    return widget.render(format='text').split('\n')


def make_store(value):
    return TerminalStateStore({'v': value}, schema=TerminalStateSchema.compile({}))


def replace(store, value):
    store.apply(
        TerminalStatePatch.from_value([{'op': 'replace', 'path': '/v', 'value': value}])
    )


def test_paragraph_wraps_aligns_and_scrolls():
    paragraph = Paragraph('hello brave new world', width=10, height=3, should_wrap=True)
    assert text(paragraph) == ['hello', 'brave new', 'world']
    paragraph.alignment = 'right'
    assert text(paragraph)[0] == '     hello'
    paragraph.scroll_row = 1
    assert text(paragraph)[0] == ' brave new'
    assert paragraph.line_count() == 3 and paragraph.line_width() == 21


def test_paragraph_text_follows_state_and_settings_round_trip():
    store = make_store('abc')
    paragraph = Paragraph(_state_expression(store, ('v',), False), width=6, height=1)
    assert text(paragraph) == ['abc']
    replace(store, 'xyz!')
    assert text(paragraph) == ['xyz!']
    paragraph.text = 'plain'
    assert paragraph.text == 'plain' and text(paragraph) == ['plain']
    with pytest.raises(ValueError, match='not an alignment'):
        paragraph.alignment = 'middle'


def test_paragraph_takes_a_block_and_copies_independently():
    block = Block('T', width=10, height=3)
    paragraph = Paragraph('hi', width=10, height=3, block=block)
    assert text(paragraph)[1].startswith('│hi')
    clone = copy.deepcopy(paragraph)
    clone.text = 'other'
    assert paragraph.text == 'hi' and 'Paragraph(' in repr(clone)


def test_clear_fills_with_its_symbol():
    clear = Clear(symbol='.', width=4, height=1)
    assert text(clear) == ['....']
    clear.symbol = '#'
    assert text(clear) == ['####']
    with pytest.raises(Exception, match='single character'):
        Clear(symbol='ab', width=2, height=1)


def test_custom_widget_redraws_on_invalidate_and_watched_changes():
    store = make_store(1)
    calls = []

    def draw(context, region):
        calls.append(1)
        region.update(Write('hi', x=1))

    widget = CustomWidget(
        draw, width=5, height=1, watch=[_state_expression(store, ('v',), True)]
    )
    assert text(widget) == [' hi'] and len(calls) == 1
    text(widget)
    assert len(calls) == 1
    widget.invalidate()
    text(widget)
    assert len(calls) == 2
    replace(store, 2)
    text(widget)
    assert len(calls) == 3
    with pytest.raises(ValueError, match='redraw policy'):
        widget.redraw = 'sometimes'


def test_custom_widget_redraws_every_frame_when_asked():
    calls = []
    with Runtime.offscreen(width=8, height=2) as runtime:
        widget = CustomWidget(
            lambda context, region: calls.append(1), redraw='always', width=4, height=1
        )
        runtime.mount(widget, geometry='explicit')
        runtime.step()
        runtime.step()
    assert len(calls) >= 2


def test_custom_widget_errors_are_render_errors_with_the_cause():
    def broken(context, region):
        raise ValueError('nope')

    widget = CustomWidget(broken, width=3, height=1)
    with pytest.raises(RenderError) as caught:
        text(widget)
    assert isinstance(caught.value.__cause__, ValueError)


def test_live_reapplies_operations_when_they_change():
    live = Live(Write('a'), width=4, height=1)
    assert text(live) == ['a']
    live.operations = [Write('b'), Write('c', x=1)]
    assert text(live) == ['bc']
    framed = Live(Border('plain'), width=4, height=3)
    assert text(framed)[0] == '┌──┐'
    with pytest.raises(TypeError):
        Live('not an operation')


@pytest.mark.parametrize(
    'make',
    [
        lambda: Paragraph('x', width=3, height=1),
        lambda: Clear(width=3, height=1),
        lambda: CustomWidget(lambda context, region: None, width=3, height=1),
        lambda: Live(Write('x'), width=3, height=1),
    ],
)
def test_widgets_have_repr_and_independent_copies(make):
    widget = make()
    clone = copy.copy(widget)
    assert type(clone) is type(widget) and repr(clone) == repr(widget)
    assert clone is not widget and isinstance(widget, Buffer)
