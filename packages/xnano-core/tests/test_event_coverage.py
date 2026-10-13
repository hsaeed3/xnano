"""Every kind of input event can be built, injected and heard, including custom ones."""

from __future__ import annotations

import typing

import pytest

from xnano_core._xnano_core import Buffer, Event, Runtime, _core_types

BUILDERS = {
    'key': lambda: Event.key_press('ctrl+a'),
    'mouse': lambda: Event.mouse_event(column=1, row=0, kind='press', button='left'),
    'paste': lambda: Event.paste('pasted'),
    'resize': lambda: Event.resize(width=30, height=10),
    'focus_gained': lambda: Event.focus_gained(),
    'focus_lost': lambda: Event.focus_lost(),
    'tick': lambda: Event.tick(),
    'timer': lambda: Event.timer('blink'),
    'wake': lambda: Event.wake(),
    'exit_requested': lambda: Event.exit_requested(),
    'custom': lambda: Event.custom('volume_changed', data='40'),
}

# The runtime itself reports a frame; there is nothing to inject.
REPORTED_BY_THE_RUNTIME = ('frame',)


@pytest.fixture
def runtime():
    with Runtime.offscreen(width=12, height=3) as runtime:
        yield runtime


def test_every_kind_of_event_has_a_builder_or_is_reported_by_the_runtime():
    kinds = set(typing.get_args(_core_types.EventKind))
    assert kinds == set(BUILDERS) | set(REPORTED_BY_THE_RUNTIME)


def test_event_kinds_are_the_kinds_a_hook_can_listen_to():
    kinds = set(typing.get_args(_core_types.EventKind))
    assert kinds <= set(typing.get_args(_core_types.HookEventKind))


@pytest.mark.parametrize('kind', sorted(BUILDERS))
def test_an_injected_event_reaches_a_hook_on_its_kind(runtime, kind):
    event = BUILDERS[kind]()
    assert event.kind == kind
    buffer = Buffer(width=12, height=3)
    runtime.mount(buffer)
    heard = []
    buffer.add_hook(lambda context: heard.append(context.event.kind), events=(kind,))
    runtime.inject(event)
    runtime.step()
    assert heard == [kind]


@pytest.mark.parametrize('kind', sorted(BUILDERS))
def test_a_hook_only_hears_the_kinds_it_listens_to(runtime, kind):
    buffer = Buffer(width=12, height=3)
    runtime.mount(buffer)
    heard = []
    other = 'paste' if kind != 'paste' else 'key'
    buffer.add_hook(lambda context: heard.append(context.event.kind), events=(other,))
    runtime.inject(BUILDERS[kind]())
    runtime.step()
    assert heard == []


def test_a_custom_event_carries_its_name_and_data(runtime):
    buffer = Buffer(width=12, height=3)
    runtime.mount(buffer)
    heard = []
    buffer.add_hook(
        lambda context: heard.append(
            (context.event.custom_name, context.event.custom_data)
        ),
        events=('custom',),
    )
    runtime.inject(Event.custom('volume_changed', data='40'))
    runtime.inject(Event.custom('muted'))
    runtime.step()
    assert heard == [('volume_changed', '40'), ('muted', None)]


def test_a_custom_event_needs_a_name():
    with pytest.raises(ValueError, match='needs a name'):
        Event.custom('  ')


@pytest.mark.parametrize('kind', ['press', 'repeat', 'release'])
def test_every_key_event_kind_is_delivered(runtime, kind):
    buffer = Buffer(width=12, height=3)
    runtime.mount(buffer)
    heard = []
    buffer.add_hook(lambda context: heard.append(context.event.key.kind), events=('key',))
    runtime.inject(Event.key_press('a', kind=kind))
    runtime.step()
    assert heard == [kind]


@pytest.mark.parametrize('kind', ['press', 'release', 'drag', 'move', 'scroll'])
@pytest.mark.parametrize('button', ['left', 'right', 'middle', None])
def test_every_mouse_event_kind_and_button_is_delivered(runtime, kind, button):
    buffer = Buffer(width=12, height=3)
    runtime.mount(buffer)
    heard = []
    buffer.add_hook(
        lambda context: heard.append(
            (context.event.mouse.kind, context.event.mouse.button)
        ),
        events=('mouse',),
    )
    runtime.inject(Event.mouse_event(column=2, row=1, kind=kind, button=button))
    runtime.step()
    assert heard == [(kind, button)]


def test_the_values_an_event_was_built_with_can_be_read_back():
    assert Event.paste('x').pasted_text == 'x'
    assert Event.resize(width=7, height=5).size.width == 7
    assert Event.timer('blink').timer_key == 'blink'
    key = Event.key_press('shift+up').key
    assert key.key == 'up'
    scroll = Event.mouse_event(column=0, row=0, kind='scroll', scroll_vertical=-2).mouse
    assert scroll.scroll_vertical == -2
