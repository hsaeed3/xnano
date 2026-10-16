"""Events, key bindings, input routing, focus, hit areas and device state."""

from __future__ import annotations

import pytest

from xnano_core._xnano_core import (
    Buffer,
    Event,
    InputOptions,
    KeyBinding,
    KeyboardScope,
    MouseScope,
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
    scroll = Event.mouse_event(column=0, row=0, kind='scroll', scroll_y=-1)
    assert scroll.mouse.scroll_y == -1
    assert scroll.mouse.scroll_x == 0
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


def test_a_hook_hears_the_signed_scroll_steps_of_a_wheel_event(runtime):
    buffer = Buffer(width=12, height=3)
    runtime.mount(buffer)
    heard = []
    buffer.add_hook(
        lambda context: heard.append(
            (context.event.mouse.scroll_x, context.event.mouse.scroll_y)
        ),
        events=('mouse',),
    )
    runtime.inject(Event.mouse_event(column=2, row=1, kind='scroll', scroll_y=-1))
    runtime.inject(Event.mouse_event(column=2, row=1, kind='scroll', scroll_x=2))
    runtime.step()
    assert heard == [(0, -1), (2, 0)]


def test_the_scroll_gate_is_independent_and_the_keyboard_can_be_off():
    default = InputOptions()
    assert default.scroll is False and default.keyboard == 'basic'
    wheel_only = InputOptions(scroll=True, keyboard='off', interrupt='stop')
    assert wheel_only.scroll is True and wheel_only.mouse == 'off'
    assert wheel_only.keyboard == 'off' and wheel_only.interrupt == 'stop'
    with pytest.raises(ValueError, match='keyboard mode'):
        InputOptions(keyboard='none')
    assert TerminalOptions().input.scroll is False
    assert TerminalOptions(input=wheel_only).input.scroll is True


def test_input_options_print_and_compare_by_their_options():
    assert InputOptions(scroll=True) == InputOptions(scroll=True)
    assert InputOptions(scroll=True) != InputOptions(scroll=False)
    assert InputOptions() != 'off'
    assert repr(InputOptions(mouse='motion', scroll=True, interrupt='stop')) == (
        "InputOptions(mouse='motion', scroll=True, bracketed_paste=True, "
        "focus_reporting=True, keyboard='basic', capability_timeout_milliseconds=200, "
        "interrupt='stop')"
    )


def test_a_live_runtime_accepts_the_new_gates_without_opening_the_terminal():
    options = TerminalOptions(
        input=InputOptions(scroll=True, keyboard='off', interrupt='stop')
    )
    runtime = Runtime.live(options=options)
    assert runtime.device.backend == 'terminal'
    assert not runtime.device.is_mouse_capture_enabled
    runtime.close()


def test_the_latest_key_is_remembered_with_its_canonical_chord(runtime):
    runtime.mount(Buffer())
    state = runtime.input
    assert state.last_key is None and state.last_chord is None
    for binding, key, chord in (
        ('q', 'q', 'q'),
        ('ctrl+s', 's', 'ctrl+s'),
        ('shift+ctrl+a', 'a', 'ctrl+shift+a'),
        ('alt+shift+ctrl+left', 'left', 'ctrl+alt+shift+left'),
        ('A', 'a', 'shift+a'),
    ):
        runtime.inject(Event.key_press(binding))
        runtime.step()
        assert (state.last_key, state.last_chord) == (key, chord), binding
        assert state.last_key_kind == 'press'
    runtime.inject(Event.key_press('left', kind='release'))
    runtime.step()
    assert state.last_key_kind == 'release'
    assert KeyBinding.parse(state.last_chord).matches(Event.key_press('left'))


def test_mouse_buttons_are_held_from_press_to_release(runtime):
    runtime.mount(Buffer())
    state = runtime.input
    assert state.is_mouse_down is False
    runtime.inject(Event.mouse_event(column=3, row=1, kind='press', button='left'))
    runtime.step()
    assert state.is_mouse_down is True
    assert state.pressed_keys == {'mouse_left'}
    assert (state.last_mouse_button, state.last_mouse_kind) == ('left', 'press')
    assert state.last_mouse_position == (3, 1)
    runtime.inject(Event.mouse_event(column=5, row=2, kind='drag', button='left'))
    runtime.inject(Event.mouse_event(column=5, row=2, kind='press', button='right'))
    runtime.step()
    assert state.pressed_keys == {'mouse_left', 'mouse_right'}
    assert state.last_mouse_kind == 'press' and state.last_mouse_button == 'right'
    runtime.inject(Event.mouse_event(column=5, row=2, kind='release', button='left'))
    runtime.step()
    assert state.pressed_keys == {'mouse_right'} and state.is_mouse_down is True
    runtime.inject(Event.mouse_event(column=5, row=2, kind='release', button='right'))
    runtime.step()
    assert state.pressed_keys == frozenset() and state.is_mouse_down is False
    assert state.last_mouse_kind == 'release'
    runtime.inject(Event.mouse_event(column=1, row=1, kind='move'))
    runtime.step()
    assert state.last_mouse_kind == 'move' and state.last_mouse_button is None


def test_losing_focus_releases_the_held_mouse_buttons(runtime):
    runtime.mount(Buffer())
    runtime.inject(Event.mouse_event(column=3, row=1, kind='press', button='middle'))
    runtime.step()
    assert runtime.input.pressed_keys == {'mouse_middle'}
    runtime.inject(Event.focus_lost())
    runtime.step()
    assert runtime.input.pressed_keys == frozenset()
    assert runtime.input.is_mouse_down is False


def test_a_wheel_value_lives_for_one_step_and_belongs_to_the_wheel_only(runtime):
    runtime.mount(Buffer())
    state = runtime.input
    runtime.inject(Event.mouse_event(column=4, row=2, kind='press', button='left'))
    runtime.step()
    runtime.inject(Event.mouse_event(column=6, row=1, kind='scroll', scroll_y=-1))
    runtime.step()
    assert (state.scroll_x, state.scroll_y) == (0, -1)
    assert state.last_mouse_kind is None and state.last_mouse_button is None
    assert state.last_mouse_position is None
    assert state.pointer_cell == (6, 1), 'the wheel still moves the pointer'
    assert state.is_mouse_down is True, 'held state survives a wheel step'
    runtime.inject(Event.mouse_event(column=6, row=1, kind='scroll', scroll_x=2))
    runtime.step()
    assert (state.scroll_x, state.scroll_y) == (2, 0)
    runtime.step()
    assert (state.scroll_x, state.scroll_y) == (0, 0)


def test_a_step_with_several_wheel_reports_holds_the_latest_one(runtime):
    runtime.mount(Buffer())
    state = runtime.input
    for _ in range(3):
        runtime.inject(Event.mouse_event(column=1, row=1, kind='scroll', scroll_y=1))
    runtime.step()
    assert state.scroll_y == 1, 'wheel reports of one step do not add up'
    runtime.inject(Event.mouse_event(column=1, row=1, kind='scroll', scroll_y=1))
    runtime.inject(Event.mouse_event(column=2, row=1, kind='move'))
    runtime.step()
    assert state.scroll_y == 0, 'a motion report after the wheel clears it'


def test_pasted_text_is_remembered_until_other_input_arrives(runtime):
    runtime.mount(Buffer())
    state = runtime.input
    assert state.last_pasted_text is None
    runtime.inject(Event.key_press('x'))
    runtime.inject(Event.paste('hello'))
    runtime.step()
    assert state.last_pasted_text == 'hello'
    assert state.last_key is None and state.last_chord is None
    runtime.inject(Event.key_press('y'))
    runtime.step()
    assert state.last_pasted_text is None and state.last_key == 'y'


def test_each_kind_of_input_clears_the_latest_values_of_the_others(runtime):
    runtime.mount(Buffer())
    state = runtime.input
    runtime.inject(Event.key_press('q'))
    runtime.step()
    runtime.inject(Event.mouse_event(column=1, row=1, kind='move'))
    runtime.step()
    assert (
        state.last_key is None
        and state.last_key_kind is None
        and state.last_chord is None
    )
    assert state.last_mouse_position == (1, 1)
    runtime.inject(Event.key_press('w'))
    runtime.step()
    assert state.last_key == 'w'
    assert state.last_mouse_kind is None and state.last_mouse_position is None
    assert state.pointer_cell == (1, 1), 'the held pointer cell is not event scoped'


def test_a_key_scoped_condition_does_not_fire_on_a_later_mouse_event(runtime):
    buffer = Buffer(width=10, height=3)
    runtime.mount(buffer)
    heard = []
    buffer.add_hook(
        lambda context: heard.append(context.event.kind),
        events=('key', 'mouse', 'paste'),
        condition=KeyboardScope.key == 'q',
    )
    for event in (
        Event.key_press('w'),
        Event.key_press('q'),
        Event.mouse_event(column=1, row=1, kind='move'),
        Event.mouse_event(column=1, row=1, kind='scroll', scroll_y=1),
        Event.paste('q'),
    ):
        runtime.inject(event)
        runtime.step()
    assert heard == ['key']


def test_a_mouse_scoped_condition_does_not_fire_on_a_later_key_press(runtime):
    buffer = Buffer(width=10, height=3)
    runtime.mount(buffer)
    heard = []
    buffer.add_hook(
        lambda context: heard.append(context.event.kind),
        events=('key', 'mouse', 'paste'),
        condition=MouseScope.button == 'left',
    )
    for event in (
        Event.mouse_event(column=1, row=1, kind='press', button='left'),
        Event.key_press('a'),
        Event.paste('a'),
        Event.mouse_event(column=1, row=1, kind='scroll', scroll_y=1),
    ):
        runtime.inject(event)
        runtime.step()
    assert heard == ['mouse']
