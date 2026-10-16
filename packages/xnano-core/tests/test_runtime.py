"""The offscreen runtime: mounting, stepping, scheduling, hooks and frames."""

from __future__ import annotations

import pytest

from xnano_core._xnano_core import Buffer, Clock, Event, RenderError, Runtime, Write
from xnano_core._xnano_core._core_types import Invalidate, Skip, Stop


def test_offscreen_runtimes_use_manual_clocks_and_never_negotiate():
    runtime = Runtime.offscreen(width=10, height=3)
    assert runtime.clock.source == 'manual'
    assert runtime.device.backend == 'offscreen'
    assert runtime.device.size.width == 10
    assert runtime.device.capabilities.is_terminal is False
    assert runtime.device.keyboard.enhancement == 'unsupported'
    assert not runtime.is_closed and not runtime.is_running


def test_direct_construction_explains_how_to_create_one():
    with pytest.raises(TypeError, match='Runtime.live'):
        Runtime()


def test_mount_renders_the_first_frame_and_static_scenes_do_not_redraw(runtime):
    buffer = Buffer('hello')
    runtime.mount(buffer)
    first = runtime.step()
    assert first.did_render
    assert runtime.snapshot().lines()[0] == 'hello'
    second = runtime.step()
    assert not second.did_render and not runtime.needs_frame
    buffer.update(Write('J'))
    assert runtime.needs_frame
    assert runtime.step().did_render
    assert runtime.snapshot().lines()[0] == 'Jello'


def test_mounting_rules(runtime):
    buffer = Buffer('x')
    runtime.mount(buffer, key='main')
    with pytest.raises(ValueError, match='already mounted'):
        runtime.mount(buffer)
    with pytest.raises(ValueError, match='key "main"'):
        runtime.mount(Buffer('y'), key='main')
    child = Buffer('c')
    other = Buffer('p')
    other.attach(child)
    with pytest.raises(ValueError, match='attached to a parent'):
        runtime.mount(child)
    assert runtime.buffers == (buffer,)
    runtime.unmount(buffer)
    assert runtime.buffers == ()
    with pytest.raises(ValueError, match='not mounted'):
        runtime.unmount(buffer)


def test_inherit_geometry_fits_the_device(runtime):
    buffer = Buffer('x')
    runtime.mount(buffer, geometry='inherit')
    runtime.render()
    assert (buffer.width, buffer.height) == (40, 10)
    runtime.resize(width=12, height=4)
    runtime.step()
    assert (buffer.width, buffer.height) == (12, 4)
    assert runtime.snapshot().size.width == 12


def test_roots_composite_by_layer(runtime):
    low = Buffer('aaaa')
    high = Buffer('bb', layer=1) if False else Buffer('bb')
    high.layer = 1
    runtime.mount(high)
    runtime.mount(low)
    assert runtime.render().lines()[0] == 'bbaa'


def test_lifecycle_hooks_fire_on_mount_unmount_and_close():
    seen = []
    runtime = Runtime.offscreen(width=10, height=2)
    buffer = Buffer('x')
    buffer.add_hook(lambda context: seen.append('mount'), events=('mount',))
    buffer.add_hook(lambda context: seen.append('unmount'), events=('unmount',))
    runtime.mount(buffer)
    assert seen == ['mount']
    runtime.unmount(buffer)
    assert seen == ['mount', 'unmount']
    runtime.mount(buffer)
    runtime.close()
    assert seen == ['mount', 'unmount', 'mount', 'unmount']
    assert runtime.is_closed
    with pytest.raises(RuntimeError, match='closed'):
        runtime.step()
    runtime.close()


def test_children_attached_after_mounting_become_mounted(runtime):
    parent = Buffer(width=10, height=2)
    runtime.mount(parent)
    seen = []
    child = Buffer('c')
    child.add_hook(lambda context: seen.append('mounted'), events=('mount',))
    parent.attach(child)
    assert child in parent.children
    runtime.step()
    assert seen == ['mounted']
    parent.detach(child)
    runtime.step()


def test_ticks_and_timers_follow_the_manual_clock(runtime):
    ticks, timers = [], []
    buffer = Buffer()
    buffer.add_hook(
        lambda context: ticks.append(round(context.clock.elapsed_seconds, 3)),
        events=('tick',),
    )
    buffer.add_hook(
        lambda context: timers.append(context.event.timer_key), events=('timer',)
    )
    runtime.mount(buffer)
    runtime.start_timer('t', interval_milliseconds=100)
    runtime.advance_clock(99)
    runtime.step()
    assert timers == []
    runtime.advance_clock(1)
    runtime.step()
    assert timers == ['t']
    assert runtime.stop_timer('t') and not runtime.stop_timer('t')
    runtime.advance_clock(500)
    runtime.step()
    assert timers == ['t']
    assert ticks == []


def test_tick_interval_produces_ticks():
    runtime = Runtime.offscreen(width=4, height=1, tick_interval_milliseconds=50)
    count = []
    buffer = Buffer()
    buffer.add_hook(lambda context: count.append(1), events=('tick',))
    with runtime:
        runtime.mount(buffer)
        for _ in range(4):
            runtime.advance_clock(50)
            runtime.step()
    assert len(count) == 4


def test_scheduled_calls_run_once_or_repeatedly(runtime):
    calls = []
    once = runtime.call_later(0.1, lambda: calls.append('once'))
    every = runtime.call_every(0.1, lambda: calls.append('every'))
    runtime.advance_clock(100)
    runtime.step()
    assert sorted(calls) == ['every', 'once']
    runtime.advance_clock(100)
    runtime.step()
    assert calls.count('every') == 2 and calls.count('once') == 1
    every.cancel()
    assert every.is_cancelled and not once.is_cancelled
    runtime.advance_clock(1000)
    runtime.step()
    assert calls.count('every') == 2
    with pytest.raises(ValueError, match='positive'):
        runtime.call_every(0, lambda: None)


def test_simulation_clock_delta_updates_when_sampled():
    parent = Clock.manual()
    simulation = parent.derive(rate=2.0)

    simulation.sample()
    parent.advance(100)
    simulation.sample()

    assert simulation.delta_seconds == pytest.approx(0.2)


def test_simulation_clocks_scale_scheduled_calls(runtime):
    simulation = runtime.clock.derive(rate=2.0)
    calls = []
    runtime.call_later(1.0, lambda: calls.append(1), clock=simulation)
    runtime.advance_clock(400)
    runtime.step()
    assert calls == []
    runtime.advance_clock(100)
    runtime.step()
    assert calls == [1]


def test_call_soon_threadsafe_and_waker(runtime):
    seen = []
    runtime.call_soon_threadsafe(lambda: seen.append('a'))
    runtime.waker().call_soon(seen.append, 'b')
    runtime.step()
    assert seen == ['a', 'b']
    wakes = []
    buffer = Buffer()
    buffer.add_hook(lambda context: wakes.append(1), events=('wake',))
    runtime.mount(buffer)
    runtime.waker().wake()
    runtime.step()
    assert wakes == [1]


def test_update_hooks_separate_simulation_from_frames(runtime):
    buffer = Buffer()
    runtime.mount(buffer)
    variable, fixed = [], []
    runtime.on_update(
        lambda c: variable.append(round(c.delta_seconds, 3)),
        target=buffer,
        maximum_delta_seconds=0.05,
    )
    runtime.on_update(
        lambda c: fixed.append((round(c.delta_seconds, 3), c.is_fixed_step)),
        target=buffer,
        fixed_step_seconds=0.1,
        maximum_catch_up_steps=2,
    )
    runtime.advance_clock(30)
    result = runtime.step()
    assert variable == [0.03] and fixed == [] and result.updates_processed == 1
    runtime.advance_clock(500)
    runtime.step()
    assert variable[-1] == 0.05, 'variable steps clamp the delta'
    assert fixed == [(0.1, True), (0.1, True)], (
        'fixed steps run at most maximum_catch_up_steps'
    )
    runtime.advance_clock(100)
    runtime.step()
    assert len(fixed) == 3, 'overflow was dropped, so only the new step ran'


def test_update_overflow_can_be_retained(runtime):
    buffer = Buffer()
    runtime.mount(buffer)
    fixed = []
    runtime.on_update(
        lambda c: fixed.append(1),
        target=buffer,
        fixed_step_seconds=0.1,
        maximum_catch_up_steps=1,
        overflow='retain',
    )
    runtime.advance_clock(300)
    runtime.step()
    runtime.step()
    runtime.advance_clock(1)
    runtime.step()
    assert len(fixed) >= 2
    with pytest.raises(ValueError, match='overflow'):
        runtime.on_update(lambda c: None, target=buffer, overflow='explode')


def test_paused_clocks_pause_updates(runtime):
    buffer = Buffer()
    runtime.mount(buffer)
    calls = []
    simulation = runtime.clock.derive(rate=1.0)
    runtime.on_update(
        lambda c: calls.append(c.delta_seconds), target=buffer, clock=simulation
    )
    simulation.stop()
    runtime.advance_clock(100)
    runtime.step()
    assert calls == []
    simulation.resume()
    runtime.advance_clock(100)
    runtime.step()
    assert calls and abs(calls[0] - 0.1) < 1e-9


def test_frame_callbacks_see_the_authoritative_area(runtime):
    buffer = Buffer()
    runtime.mount(buffer)
    areas = []
    runtime.on_frame(lambda c: areas.append((c.area.width, c.area.height)), target=buffer)
    runtime.render()
    runtime.resize(width=7, height=3)
    runtime.step()
    assert areas == [(40, 10), (7, 3)]


def test_frame_context_reports_damage(runtime):
    buffer = Buffer(width=5, height=2)
    runtime.mount(buffer)
    damage = []
    runtime.on_frame(lambda c: damage.append(len(c.damaged_areas)), target=buffer)
    runtime.render()
    buffer.update(Write('x'))
    runtime.render()
    assert damage[-1] >= 1


def test_render_errors_are_recoverable_and_leave_the_last_frame(runtime):
    buffer = Buffer('ok')
    runtime.mount(buffer)
    runtime.render()
    failures = []
    hook = runtime.on_frame(lambda c: 1 / 0, target=buffer)
    buffer.update(Write('xx'))
    with pytest.raises(RenderError, match='previous frame') as caught:
        runtime.render()
    assert isinstance(caught.value.__cause__, ZeroDivisionError)
    assert runtime.snapshot().lines()[0] == 'ok'
    runtime.on_render_error(failures.append)
    runtime.render()
    assert len(failures) == 1 and isinstance(failures[0], RenderError)
    hook.cancel()
    runtime.render()
    assert runtime.snapshot().lines()[0] == 'xx'


def test_interrupts_still_propagate_from_frame_callbacks(runtime):
    buffer = Buffer('x')
    runtime.mount(buffer)
    runtime.on_render_error(lambda error: None)

    def interrupt(context):
        raise KeyboardInterrupt

    runtime.on_frame(interrupt, target=buffer)
    with pytest.raises(KeyboardInterrupt):
        runtime.render()


def test_hook_ordering_and_conditions(runtime):
    from helpers import Width

    order = []
    buffer = Buffer(width=10, height=1)
    runtime.mount(buffer)
    buffer.add_hook(lambda c: order.append('low'), events=('wake',), priority=0)
    buffer.add_hook(lambda c: order.append('high'), events=('wake',), priority=5)
    buffer.add_hook(lambda c: order.append('first'), events=('wake',), priority=0)
    buffer.add_hook(
        lambda c: order.append('narrow'), events=('wake',), condition=Width < 5
    )
    buffer.add_hook(
        lambda c: order.append('wide'), events=('wake',), condition=Width >= 5
    )
    runtime.waker().wake()
    runtime.step()
    assert order == ['high', 'low', 'first', 'wide']


def test_conditions_see_state_left_by_earlier_hooks(runtime):
    from helpers import Width

    buffer = Buffer(width=3, height=1)
    runtime.mount(buffer)
    seen = []
    buffer.add_hook(lambda c: c.buffer.update(Width(30)), events=('wake',), priority=10)
    buffer.add_hook(
        lambda c: seen.append('wide now'), events=('wake',), condition=Width > 20
    )
    runtime.waker().wake()
    runtime.step()
    assert seen == ['wide now']


def test_hook_controls(runtime):
    buffer = Buffer('x')
    runtime.mount(buffer)
    runtime.render()
    calls = []
    hook = buffer.add_hook(lambda c: calls.append('a'), events=('wake',), once=True)
    runtime.waker().wake()
    runtime.step()
    runtime.waker().wake()
    runtime.step()
    assert calls == ['a'] and hook.is_cancelled
    toggled = buffer.add_hook(lambda c: calls.append('b'), events=('wake',))
    toggled.enabled = False
    runtime.waker().wake()
    runtime.step()
    assert calls == ['a']
    toggled.enabled = True

    def invalidate(context):
        raise Invalidate

    buffer.add_hook(invalidate, events=('wake',))
    runtime.waker().wake()
    assert runtime.step().did_render


def test_stop_signals_end_the_runtime(runtime):
    buffer = Buffer()
    runtime.mount(buffer)

    def stop(context):
        raise Stop

    buffer.add_hook(stop, events=('wake',))
    runtime.waker().wake()
    result = runtime.step()
    assert not result.is_running and not runtime.is_running


def test_skip_continues_with_later_hooks(runtime):
    buffer = Buffer()
    runtime.mount(buffer)
    calls = []

    def skip(context):
        calls.append('skip')
        raise Skip

    buffer.add_hook(skip, events=('wake',), priority=1)
    buffer.add_hook(lambda c: calls.append('after'), events=('wake',))
    runtime.waker().wake()
    runtime.step()
    assert calls == ['skip', 'after']


def test_hook_registration_validates_its_arguments(runtime):
    buffer = Buffer()
    with pytest.raises(TypeError, match='callable'):
        buffer.add_hook('nope')
    with pytest.raises(ValueError, match='mount, unmount'):
        buffer.add_hook(lambda c: None, events=('explode',))


def test_exceptions_in_event_hooks_propagate(runtime):
    buffer = Buffer()
    runtime.mount(buffer)
    buffer.add_hook(lambda c: 1 / 0, events=('wake',))
    runtime.waker().wake()
    with pytest.raises(ZeroDivisionError):
        runtime.step()


def test_change_hooks_are_coalesced_per_step(runtime):
    buffer = Buffer(width=4, height=1)
    runtime.mount(buffer)
    runtime.step()
    count = []
    buffer.add_hook(lambda c: count.append(1), events=('change',))
    buffer.update(Write('a'), Write('b', x=1), Write('c', x=2))
    runtime.step()
    assert count == [1]


def test_before_and_after_render_hooks(runtime):
    buffer = Buffer('x')
    runtime.mount(buffer)
    phases = []
    buffer.add_hook(lambda c: phases.append('before'), events=('before_render',))
    buffer.add_hook(lambda c: phases.append('after'), events=('after_render',))
    runtime.render()
    assert phases == ['before', 'after']


def test_event_streams_yield_dispatched_events(runtime):
    stream = runtime.events()
    runtime.inject(Event.key_press('a'))
    runtime.inject(Event.paste('hi'))
    kinds = [event.kind for event in stream]
    assert kinds == ['key', 'paste']


def test_frame_metrics_count_frames(runtime):
    buffer = Buffer('x')
    runtime.mount(buffer)
    runtime.render()
    runtime.render()
    metrics = runtime.frame_metrics
    assert metrics.frames == 2
    assert (
        metrics.last_frame_microseconds >= 0 and metrics.average_frame_microseconds >= 0
    )


def test_snapshots_expose_text_ansi_and_cells(runtime):
    runtime.mount(Buffer('hi'))
    snapshot = runtime.render()
    assert snapshot.text.startswith('hi')
    assert '\x1b[' in snapshot.ansi
    assert snapshot.revision == 1
    assert snapshot.cursor_position is None and snapshot.is_cursor_visible is False
    assert Buffer.from_cell_grid(snapshot.to_cell_grid()).text.startswith('hi')


def test_custom_manual_clocks_are_shared():
    clock = Clock.manual(elapsed_seconds=5.0)
    runtime = Runtime.offscreen(width=2, height=1, clock=clock)
    assert runtime.clock.elapsed_seconds == 5.0
    runtime.advance_clock(1000)
    assert clock.elapsed_seconds == 6.0
    with pytest.raises(ValueError, match='manual clock'):
        Runtime.offscreen(width=1, height=1, clock=Clock.monotonic()).advance_clock(1)


def test_run_returns_when_stopped_by_a_hook(runtime):
    buffer = Buffer()
    runtime.mount(buffer)
    runtime.call_soon_threadsafe(runtime.stop)
    runtime.run()
    assert runtime.is_closed is False


def test_context_helpers(runtime):
    buffer = Buffer(width=6, height=2, x=3, y=1)
    buffer.is_focusable = True
    captured = []
    runtime.mount(buffer)
    buffer.add_hook(
        lambda c: captured.append(
            (c.bounds.x, c.bounds.y, c.is_focused, c.focus(), c.is_focused)
        ),
        events=('wake',),
    )
    runtime.waker().wake()
    runtime.step()
    assert captured == [(3, 1, False, True, True)]


def test_a_clock_stops_resumes_and_does_not_count_the_stopped_time():
    clock = Clock.manual()
    clock.advance(1000)
    clock.stop()
    assert clock.is_stopped
    clock.advance(5000)
    assert clock.elapsed_seconds == 1.0
    clock.resume()
    assert not clock.is_stopped
    assert clock.elapsed_seconds == 1.0
    clock.advance(500)
    assert clock.elapsed_seconds == 1.5


def test_clocks_no_longer_use_the_pause_names():
    clock = Clock.manual()
    assert not hasattr(clock, 'pause') and not hasattr(clock, 'is_paused')
    simulation = clock.derive()
    assert not hasattr(simulation, 'pause') and not hasattr(simulation, 'paused')
    with pytest.raises(TypeError):
        clock.derive(paused=True)


def test_simulation_clocks_stop_and_resume():
    simulation = Clock.manual().derive(is_stopped=True)
    assert simulation.is_stopped
    simulation.resume()
    assert not simulation.is_stopped
    simulation.stop()
    assert simulation.is_stopped
    simulation.is_stopped = False
    assert not simulation.is_stopped
    assert 'is_stopped=False' in repr(simulation)


def test_a_manual_clock_steps_by_hand_and_a_step_reaches_the_delta():
    clock = Clock.manual()
    clock.step(250)
    assert clock.elapsed_milliseconds == 250.0
    runtime = Runtime.offscreen(width=2, height=1, clock=clock)
    runtime.step()
    clock.step(100)
    runtime.step()
    assert clock.delta_seconds == pytest.approx(0.1)
    assert clock.frame == 2
    runtime.close()


def test_a_stopped_monotonic_clock_steps_by_hand_and_resumes_without_a_jump():
    clock = Clock.monotonic()
    clock.stop()
    before = clock.elapsed_seconds
    clock.step(2000)
    assert clock.elapsed_seconds == pytest.approx(before + 2.0)
    assert clock.is_stopped
    clock.resume()
    assert 2.0 <= clock.elapsed_seconds < 3.0


def test_a_running_monotonic_clock_refuses_to_be_stepped_and_says_what_to_do():
    clock = Clock.monotonic()
    with pytest.raises(ValueError, match=r'running wall clock.*stop\(\) first'):
        clock.step(10)
    with pytest.raises(ValueError, match=r'Clock\.step cannot move time backwards'):
        Clock.manual().step(-1)


def test_a_monotonic_clock_refuses_a_negative_frame_count():
    with pytest.raises(ValueError, match='frame of zero or more'):
        Clock.monotonic(frame=-1)


def test_the_delta_after_a_step_on_a_stopped_clock_is_the_step():
    clock = Clock.monotonic()
    clock.stop()
    clock.step(0)
    clock.step(40)
    runtime = Runtime.offscreen(width=2, height=1, clock=clock)
    runtime.step()
    clock.step(40)
    runtime.step()
    assert clock.delta_seconds == pytest.approx(0.04, abs=1e-6)
    runtime.close()


def test_a_monotonic_clock_can_start_at_an_elapsed_time_and_frame():
    clock = Clock.monotonic(elapsed_seconds=2.0, frame=120)
    assert clock.source == 'monotonic'
    assert 2.0 <= clock.elapsed_seconds < 3.0
    assert clock.frame == 120
    default = Clock.monotonic()
    assert default.frame == 0 and default.elapsed_seconds < 1.0
    for bad in (-1.0, float('inf'), float('nan')):
        with pytest.raises(ValueError, match='elapsed_seconds'):
            Clock.monotonic(elapsed_seconds=bad)
        with pytest.raises(ValueError, match='elapsed_seconds'):
            Clock.manual(elapsed_seconds=bad)


def test_a_live_runtime_accepts_the_clock_of_an_earlier_runtime():
    import inspect

    parameters = inspect.signature(Runtime.live).parameters
    assert parameters['clock'].default is None
    assert parameters['clock'].kind is inspect.Parameter.KEYWORD_ONLY
    clock = Clock.monotonic(elapsed_seconds=5.0, frame=7)
    runtime = Runtime.live(clock=clock)
    try:
        assert runtime.clock.elapsed_seconds >= 5.0
        assert runtime.clock.frame == 7
    finally:
        runtime.close()
    with pytest.raises(TypeError):
        Runtime.live(clock=object())
