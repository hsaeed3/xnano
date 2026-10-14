"""Events, key bindings, input routing, focus, hit areas and device state."""

from __future__ import annotations

import pytest

from xnano_core._xnano_core import (
    Buffer,
    Event,
    InputOptions,
    KeyBinding,
    Rectangle,
    Runtime,
    TerminalOptions,
    detect_terminal_capabilities,
    query_keyboard_capabilities,
)
from xnano_core._xnano_core._core_types import Propagate


def test_key_bindings_parse_and_match():
    event = Event.key_press('ctrl+shift+a')
    assert event.key.key == 'a' and event.key.modifiers == {'control', 'shift'}
    assert KeyBinding.parse('ctrl+shift+a').matches(event)
    assert not KeyBinding.parse('ctrl+a').matches(event)
    assert event.key.matches('Ctrl+Shift+A')
    assert KeyBinding.parse('A').matches(Event.key_press('A'))
    assert Event.key_press('q').key.text == 'q'
    assert Event.key_press('ctrl+c').key.text is None
    assert Event.key_press('space').key.text == ' '
    assert Event.key_press('ctrl++').key.key == '+'
    assert KeyBinding.parse('esc').matches(Event.key_press('escape'))
    assert Event.key_press('q', kind='release').key.kind == 'release'


def test_bad_bindings_say_what_is_valid():
    with pytest.raises(ValueError, match='not a modifier'):
        KeyBinding.parse('hyperdrive+x')
    with pytest.raises(ValueError, match='empty'):
        KeyBinding.parse('')
    with pytest.raises(ValueError, match='press, repeat or release'):
        Event.key_press('a', kind='tap')


def test_event_constructors():
    assert Event.paste('x').pasted_text == 'x'
    assert Event.resize(width=3, height=2).size.height == 2
    mouse = Event.mouse_event(column=4, row=2, kind='press', button='left')
    assert (mouse.mouse.column, mouse.mouse.row, mouse.mouse.button) == (4, 2, 'left')
    assert mouse.mouse.position.x == 4
    scroll = Event.mouse_event(column=0, row=0, kind='scroll', scroll_vertical=-1)
    assert scroll.mouse.scroll_vertical == -1
    assert Event.focus_gained().kind == 'focus_gained'
    with pytest.raises(ValueError, match='mouse button'):
        Event.mouse_event(column=0, row=0, kind='press', button='thumb')


def test_keys_route_to_the_focused_buffer_then_its_parents(runtime):
    parent = Buffer(width=10, height=3)
    child = Buffer(width=5, height=1)
    child.is_focusable = True
    parent.attach(child)
    runtime.mount(parent)
    seen = []
    parent.add_hook(lambda c: seen.append('parent'), events=('key',))
    runtime.router.focus(child)
    runtime.inject(Event.key_press('a'))
    runtime.step()
    assert seen == ['parent'], 'with no child hook, the key bubbles up'
    child.add_hook(lambda c: seen.append('child'), events=('key',))
    runtime.inject(Event.key_press('a'))
    runtime.step()
    assert seen == ['parent', 'child'], 'a handled key stops at the child'


def test_propagate_continues_to_the_parent(runtime):
    parent = Buffer(width=10, height=3)
    child = Buffer(width=5, height=1)
    child.is_focusable = True
    parent.attach(child)
    runtime.mount(parent)
    seen = []

    def handle(context):
        seen.append('child')
        raise Propagate

    child.add_hook(handle, events=('key',))
    parent.add_hook(lambda c: seen.append('parent'), events=('key',))
    runtime.router.focus(child)
    runtime.inject(Event.key_press('a'))
    runtime.step()
    assert seen == ['child', 'parent']


def test_consume_stops_every_other_hook(runtime):
    buffer = Buffer(width=4, height=1)
    runtime.mount(buffer)
    seen = []

    def first(context):
        seen.append('first')
        context.consume()

    buffer.add_hook(first, events=('key',), priority=1)
    buffer.add_hook(lambda c: seen.append('second'), events=('key',))
    runtime.inject(Event.key_press('a'))
    runtime.step()
    assert seen == ['first']


def test_unfocused_input_reaches_every_mounted_buffer(runtime):
    a, b = Buffer(width=2, height=1), Buffer(width=2, height=1)
    seen = []
    a.add_hook(lambda c: seen.append('a'), events=('key',))
    b.add_hook(lambda c: seen.append('b'), events=('key',))
    runtime.mount(a)
    runtime.mount(b)
    runtime.inject(Event.key_press('x'))
    runtime.step()
    assert sorted(seen) == ['a', 'b']


def test_router_bindings_filter_keys(runtime):
    buffer = Buffer(width=4, height=1)
    runtime.mount(buffer)
    seen = []
    hook = runtime.router.on(
        lambda c: seen.append(c.event.key.key), target=buffer, binding='ctrl+s'
    )
    runtime.inject(Event.key_press('s'))
    runtime.inject(Event.key_press('ctrl+s'))
    runtime.step()
    assert seen == ['s']
    hook.cancel()
    runtime.inject(Event.key_press('ctrl+s'))
    runtime.step()
    assert seen == ['s']


def test_mouse_routes_to_the_topmost_buffer_and_reports_local_pointer(runtime):
    base = Buffer(width=20, height=5)
    top = Buffer(width=4, height=2, x=5, y=1)
    base.attach(top)
    runtime.mount(base)
    seen = []
    base.add_hook(lambda c: seen.append(('base', c.local_pointer)), events=('mouse',))
    top.add_hook(lambda c: seen.append(('top', c.local_pointer)), events=('mouse',))
    runtime.inject(Event.mouse_event(column=6, row=2, kind='press', button='left'))
    runtime.inject(Event.mouse_event(column=15, row=3, kind='move'))
    runtime.step()
    assert seen == [('top', (1, 1)), ('base', (15, 3))]
    assert runtime.input.pointer_cell == (15, 3)


def test_clicking_focuses_the_nearest_focusable_buffer(runtime):
    base = Buffer(width=20, height=5)
    base.is_focusable = True
    top = Buffer(width=4, height=2, x=5, y=1)
    base.attach(top)
    runtime.mount(base)
    runtime.inject(Event.mouse_event(column=6, row=2, kind='press', button='left'))
    runtime.step()
    assert runtime.router.focus(base) is True


def test_pointer_capture_follows_drags(runtime):
    base = Buffer(width=20, height=5)
    top = Buffer(width=4, height=2, x=5, y=1)
    base.attach(top)
    runtime.mount(base)
    seen = []
    top.add_hook(
        lambda c: (
            seen.append(c.event.mouse.kind),
            c.capture_pointer() if c.event.mouse.kind == 'press' else None,
        ),
        events=('mouse',),
    )
    runtime.inject(Event.mouse_event(column=6, row=2, kind='press', button='left'))
    runtime.inject(Event.mouse_event(column=18, row=4, kind='drag', button='left'))
    runtime.inject(Event.mouse_event(column=18, row=4, kind='release', button='left'))
    runtime.inject(Event.mouse_event(column=18, row=4, kind='move'))
    runtime.step()
    assert seen == ['press', 'drag', 'release']


def test_hit_areas_register_geometry_without_painted_glyphs(runtime):
    buffer = Buffer(width=20, height=5, x=2, y=1)
    runtime.mount(buffer)
    area = runtime.router.hit_area(
        'button', target=buffer, bounds=Rectangle(3, 1, 4, 2), layer=1
    )
    assert area.key == 'button'
    assert runtime.router.hit_test(5, 3)[0].key == 'button'
    assert runtime.router.hit_test(0, 0) == ()
    area.bounds = Rectangle(0, 0, 2, 2)
    assert runtime.router.hit_test(5, 3) == ()
    assert runtime.router.hit_test(2, 1)[0] is not None
    area.remove()
    assert runtime.router.hit_test(2, 1) == ()


def test_modal_scopes_confine_input(runtime):
    page = Buffer(width=20, height=5)
    dialog = Buffer(width=6, height=3)
    page.attach(dialog)
    runtime.mount(page)
    seen = []
    page.add_hook(lambda c: seen.append('page'), events=('key',))
    dialog.add_hook(lambda c: seen.append('dialog'), events=('key',))
    with runtime.router.scope(dialog, modal=True) as scope:
        assert scope.is_active
        runtime.inject(Event.key_press('a'))
        runtime.step()
    assert not scope.is_active
    assert seen == ['dialog']
    runtime.inject(Event.key_press('a'))
    runtime.step()
    assert 'page' in seen


def test_focus_rules(runtime):
    a, b = Buffer(width=2, height=1), Buffer(width=2, height=1)
    runtime.mount(a)
    assert runtime.router.focus(a) is False, 'buffers are not focusable until marked'
    a.is_focusable = True
    assert runtime.router.focus(a) is True
    assert runtime.router.focus(b) is False
    runtime.router.clear_focus()
    assert runtime.router.focus(a) is True


def test_unmounting_releases_focus_and_hit_areas(runtime):
    buffer = Buffer(width=4, height=2)
    buffer.is_focusable = True
    runtime.mount(buffer)
    runtime.router.focus(buffer)
    area = runtime.router.hit_area('x', target=buffer, bounds=Rectangle(0, 0, 2, 2))
    runtime.unmount(buffer)
    assert runtime.router.hit_test(0, 0) == ()
    assert area.key == 'x'
    assert runtime.router.focus(buffer) is False


def test_pressed_keys_need_release_reporting(runtime):
    runtime.mount(Buffer())
    runtime.inject(Event.key_press('a'))
    runtime.step()
    assert runtime.input.held_keys_available is False
    assert runtime.input.pressed_keys == frozenset()


def test_estimated_holds_are_separate_and_opt_in(runtime):
    runtime.mount(Buffer())
    with pytest.raises(ValueError, match='positive'):
        runtime.input.estimate_holds(timeout_seconds=0)
    runtime.input.estimate_holds(timeout_seconds=0.5)
    runtime.inject(Event.key_press('left'))
    runtime.step()
    assert runtime.input.estimated_pressed_keys == {'left'}
    assert runtime.input.pressed_keys == frozenset()
    runtime.advance_clock(600)
    assert runtime.input.estimated_pressed_keys == frozenset()
    runtime.input.estimate_holds()
    assert runtime.input.estimated_pressed_keys == frozenset()


def test_focus_loss_clears_estimates(runtime):
    runtime.mount(Buffer())
    runtime.input.estimate_holds(timeout_seconds=5)
    runtime.inject(Event.key_press('a'))
    runtime.inject(Event.focus_lost())
    runtime.step()
    assert runtime.input.estimated_pressed_keys == frozenset()
    assert runtime.device.is_focused is False
    runtime.inject(Event.focus_gained())
    runtime.step()
    assert runtime.device.is_focused is True


def test_options_are_validated():
    assert InputOptions().mouse == 'off'
    with pytest.raises(ValueError, match='mouse mode'):
        InputOptions(mouse='all')
    with pytest.raises(ValueError, match='keyboard mode'):
        InputOptions(keyboard='kitty')
    with pytest.raises(ValueError, match='interrupt mode'):
        InputOptions(interrupt='die')
    options = TerminalOptions(input=InputOptions(mouse='motion'), alternate_screen=False)
    assert options.input.mouse == 'motion' and not options.alternate_screen
    assert options.raw_mode and options.drain_timeout_milliseconds == 250


def test_capability_queries_never_raise_without_a_terminal():
    capabilities = detect_terminal_capabilities(timeout_milliseconds=10)
    assert capabilities.graphics_protocol in ('half_blocks', 'kitty', 'sixel', 'iterm2')
    assert capabilities.synchronized_output in ('supported', 'unsupported', 'unknown')
    keyboard = query_keyboard_capabilities(timeout_milliseconds=10)
    assert keyboard.enhancement in ('supported', 'unsupported', 'unknown')
    assert keyboard.enabled_features == frozenset()
    if keyboard.enhancement != 'supported':
        assert keyboard.unavailable_reason


def test_live_runtimes_are_lazy():
    runtime = Runtime.live()
    assert runtime.device.backend == 'terminal'
    assert not runtime.device.is_raw_mode_enabled
    assert runtime.clock.source == 'monotonic'
    runtime.close()
