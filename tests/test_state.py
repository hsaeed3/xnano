"""
tests.test_state

Typed and dynamic state: namespaces, snapshots and transactions, and hooks that follow paths.
"""

import threading
from dataclasses import dataclass, field

import pytest
from typing_extensions import assert_type

import xnano as main
from xnano.errors import TerminalError
from xnano.hooks import Context
from xnano.state import StateNamespace, parse_path
from xnano_core import Event, JSONValue, ParentWidth


@dataclass
class Settings:
    volume: int = 40


@dataclass
class Nested:
    player: Settings


def test_a_state_write_is_validated_and_wakes_a_hook():
    heard: list[int] = []
    with main.new(width=8, height=2, state=Settings()) as canvas:

        @canvas.hook(on='state')
        def remember(context: Context) -> None:
            heard.append(context.root.state.volume)

        canvas.state.volume = 55
        canvas.deliver_events()
        assert canvas.state.volume == 55
        assert heard == [55]
        with pytest.raises(TerminalError, match='volume'):
            canvas.state.volume = 'loud'


def test_a_reference_can_be_an_axis():
    with main.new(width=20, height=2, state=Settings(volume=4)) as canvas:
        thumb = canvas.screen.write(
            '#', x=canvas.state_reference(lambda state: state.volume)
        )
        canvas.deliver_events()
        assert thumb.x == 4
        canvas.state.volume = 7
        canvas.deliver_events()
        assert thumb.x == 7


def test_an_unsupported_field_is_named():
    @dataclass
    class Broken:
        payload: bytes = b''

    with pytest.raises(TerminalError, match='payload'):
        main.new(width=4, height=1, state=Broken())


def test_open_without_state_has_no_reference():
    with main.new(width=4, height=1) as canvas:
        with pytest.raises(TerminalError, match='no state'):
            canvas.state_reference(lambda state: state.volume)


def test_an_expression_still_places_a_buffer():
    with main.new(width=10, height=1) as canvas:
        placed = canvas.screen.write('#', x=ParentWidth // 2)
        canvas.deliver_events()
        assert placed.x == 5


@dataclass
class Typed:
    volume: float = 0.5
    muted: bool = False


@dataclass
class Inner:
    depth: float = 1.0


@dataclass
class NestedSettings:
    inner: Inner = field(default_factory=Inner)
    volume: float = 0.5


def number(value: JSONValue) -> int:
    assert isinstance(value, int)
    return value


def press(canvas, key: str = 'a') -> None:
    canvas.push(Event.key_press(key))
    canvas.deliver_events()


class TestPaths:
    def test_a_path_is_split_into_keys_and_indexes(self):
        assert parse_path('player.items.0.name') == ('player', 'items', 0, 'name')
        assert parse_path('') == ()

    @pytest.mark.parametrize('path', ['a..b', '.a', 'a.'])
    def test_an_empty_part_is_refused_with_the_fix(self, path):
        with pytest.raises(ValueError, match='empty part'):
            parse_path(path)

    def test_a_path_must_be_a_string(self):
        with pytest.raises(ValueError, match='must be a string'):
            parse_path(3)  # type: ignore[arg-type]


class TestRootNamespace:
    def test_a_canvas_without_a_dataclass_has_get_and_push(self):
        with main.new(width=8, height=1) as canvas:
            assert isinstance(canvas.state, StateNamespace)
            assert canvas.state.get('score') is None
            assert canvas.state.get('score', default=0) == 0
            canvas.state.set('score', 3)
            assert canvas.state.get('score') == 3

    def test_a_namespace_that_is_not_filled_in_yet_has_no_attributes(self):
        blank = StateNamespace.__new__(StateNamespace)
        assert not hasattr(blank, '__setstate__')
        assert not hasattr(blank, 'volume')

    def test_a_namespace_can_be_copied(self):
        import copy

        with main.new(width=8, height=1) as canvas:
            canvas.state.set('score', 3)
            duplicate = copy.copy(canvas.state)
            assert duplicate.get('score') == 3
            duplicate.set('score', 4)
            assert canvas.state.get('score') == 4
            placement_state = copy.copy(canvas.screen.write('a').state)
            assert repr(placement_state).startswith('StateNamespace(')

    def test_pushing_a_deep_path_creates_the_objects_on_the_way(self):
        with main.new(width=8, height=1) as canvas:
            canvas.state.set('player.stats.score', 3)
            assert canvas.state.get('player') == {'stats': {'score': 3}}
            canvas.state.set('player.stats.level', 2)
            assert canvas.state.get('player.stats') == {'score': 3, 'level': 2}

    def test_a_list_is_addressed_by_index(self):
        with main.new(width=8, height=1) as canvas:
            canvas.state.set('items', [{'name': 'a'}, {'name': 'b'}])
            canvas.state.set('items.1.name', 'z')
            assert canvas.state.get('items.1.name') == 'z'
            assert canvas.state.get('items.5.name', default='none') == 'none'

    def test_the_root_hides_the_reserved_branch(self):
        with main.new(width=8, height=1) as canvas:
            canvas.state.set('score', 1)
            assert canvas.state.get('') == {'score': 1}
            with pytest.raises(ValueError, match="starts with 'xnano'"):
                canvas.state.set('xnano.buffers', 1)
            with pytest.raises(ValueError, match="starts with 'xnano'"):
                canvas.state.get('xnano')
            with pytest.raises(ValueError, match='whole root state'):
                canvas.state.set('', {'score': 2})

    def test_a_typed_root_has_get_push_and_its_attributes_at_run_time(self):
        with main.new(width=8, height=1, state=Typed()) as canvas:
            assert canvas.state.volume == 0.5
            canvas.state.volume = 0.75
            namespace: StateNamespace = canvas.state  # type: ignore[assignment]
            assert namespace.get('volume') == 0.75
            namespace.set('volume', 0.25)
            namespace.set('extra.count', 1)
            assert canvas.state.volume == 0.25
            assert namespace.get('extra.count') == 1

    def test_a_nested_dataclass_field_is_read_as_its_declared_type(self):
        with main.new(width=8, height=1, state=NestedSettings()) as canvas:
            assert canvas.state.inner == Inner(depth=1.0)
            canvas.state.set('inner.depth', 4)
            assert canvas.state.inner.depth == 4.0
            canvas.state.inner = Inner(depth=7)
            assert canvas.state.inner == Inner(depth=7.0)
            canvas.state.set('inner', {'depth': 9})
            assert canvas.state.inner == Inner(depth=9.0)

    def test_a_whole_number_written_to_a_float_field_is_a_float(self):
        with main.new(width=8, height=1, state=NestedSettings()) as canvas:
            canvas.state.set('volume', 2)
            assert isinstance(canvas.state.volume, float)
            canvas.state.volume = 3  # type: ignore[assignment]
            assert canvas.state.volume == 3.0
            assert isinstance(canvas.state.inner.depth, float)

    def test_the_declared_type_of_the_accessor_follows_the_state_argument(self):
        with main.new(width=8, height=1, state=Typed()) as typed:
            assert_type(typed.state.volume, float)
        with main.new(width=8, height=1) as untyped:
            assert_type(untyped.state, StateNamespace)

    def test_an_attribute_that_is_not_a_field_says_what_to_use(self):
        with main.new(width=8, height=1, state=Typed()) as canvas:
            with pytest.raises(AttributeError, match=r"get\('loudness'\)"):
                _ = canvas.state.loudness  # type: ignore[attr-defined]
            with pytest.raises(TerminalError, match=r"set\('loudness', value\)"):
                canvas.state.loudness = 1  # type: ignore[attr-defined]

    @pytest.mark.parametrize('name', ['get', 'set', 'xnano'])
    def test_a_field_that_shadows_a_member_is_refused(self, name):
        Broken = dataclass(type('Broken', (), {'__annotations__': {name: int}, name: 1}))
        with pytest.raises(
            TerminalError, match=rf"field named '{name}'.*Rename the field"
        ):
            main.new(width=4, height=1, state=Broken())

    def test_a_value_the_field_refuses_names_the_path_and_the_fix(self):
        with main.new(width=8, height=1, state=Typed()) as canvas:
            with pytest.raises(
                TerminalError, match=r"set 'volume' to 'loud'.*the field declares"
            ):
                canvas.state.set('volume', 'loud')  # type: ignore[attr-defined]
            assert canvas.state.volume == 0.5

    def test_a_write_from_another_thread_is_saved_at_once(self):
        with main.new(width=8, height=1, realtime=True) as canvas:
            worker = threading.Thread(target=lambda: canvas.state.set('x', 9))
            worker.start()
            worker.join()
            assert canvas.state.get('x') == 9

    def test_a_replacing_store_keeps_the_free_paths_it_is_given(self):
        from xnano.state import _prepare_state

        store = _prepare_state(Typed(), {'earlier': 1, 'volume': 99})
        value = store.snapshot().to_value()
        assert value['earlier'] == 1
        assert value['volume'] == 0.5


class TestHookRuns:
    def test_a_hook_reads_its_own_pushes(self):
        seen: list[object] = []
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='key')
            def count(context: Context) -> None:
                state = context.root.state
                state.set('count', 1)
                state.set('count', number(state.get('count')) + 1)
                state.set('nested', {'a': 1})
                state.set('nested.b', 2)
                seen.append(
                    (state.get('count'), state.get('nested'), state.get('nested.b'))
                )
                state.set('nested', {'c': 3})
                seen.append(state.get('nested'))

            press(canvas)
            assert seen == [(2, {'a': 1, 'b': 2}, 2), {'c': 3}]
            assert canvas.state.get('count') == 2
            assert canvas.state.get('nested') == {'c': 3}

    def test_a_typed_field_can_be_incremented_twice_in_one_hook(self):
        with main.new(width=8, height=1, state=Counter()) as canvas:

            @canvas.hook(on='key')
            def twice(context: Context[None, Counter]) -> None:
                context.root.state.count += 1
                context.root.state.count += 1

            press(canvas)
            assert canvas.state.count == 2

    def test_a_hook_commits_all_its_pushes_in_one_transaction(self):
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='key')
            def push_three(context: Context) -> None:
                state = context.root.state
                state.set('a', 1)
                state.set('b', 2)
                state.set('c', 3)

            store = canvas._ensure_store()
            before = store.revision
            press(canvas)
            assert store.revision == before + 1
            assert [canvas.state.get(key) for key in 'abc'] == [1, 2, 3]

    def test_a_hook_that_raises_saves_nothing(self):
        canvas = main.new(width=8, height=1)

        @canvas.hook(on='key')
        def fail(context: Context) -> None:
            context.root.state.set('a', 1)
            raise RuntimeError('boom')

        canvas.push(Event.key_press('a'))
        with pytest.raises(TerminalError, match='boom'):
            canvas.deliver_events()
        assert canvas.state.get('a') is None
        canvas.close()

    def test_a_value_the_field_refuses_inside_a_hook_stops_the_canvas_with_the_fix(self):
        canvas = main.new(width=8, height=1, state=Typed())

        @canvas.hook(on='key')
        def wrong(context: Context[None, Typed]) -> None:
            context.root.state.volume = 'loud'  # type: ignore[assignment]

        canvas.push(Event.key_press('a'))
        with pytest.raises(TerminalError, match=r"set 'volume' to 'loud'"):
            canvas.deliver_events()
            canvas.close()

    def test_a_generator_hook_commits_at_each_resume(self):
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='key')
            def steps(context: Context):
                state = context.root.state
                state.set('step', 1)
                context = yield
                state.set('step', number(state.get('step')) + 1)
                context = yield
                state.set('step', number(state.get('step')) + 1)

            press(canvas)
            assert canvas.state.get('step') == 1
            press(canvas)
            assert canvas.state.get('step') == 2
            press(canvas)
            assert canvas.state.get('step') == 3

    def test_two_namespaces_of_the_same_name_do_not_meet(self):
        with main.new(width=20, height=2) as canvas:
            first = canvas.screen.write('a')
            second = canvas.screen.write('b', y=1)
            for placement in (first, second):

                @placement.hook(on='key')
                def count(context: Context) -> None:
                    state = context.target.state
                    state.set('count', number(state.get('count', default=0)) + 1)

            first.state.set('own', 'first')
            press(canvas)
            press(canvas)
            assert first.state.get('count') == 2
            assert second.state.get('count') == 2
            assert first.state.get('own') == 'first'
            assert second.state.get('own') is None
            assert canvas.state.get('count') is None

    def test_a_plugin_namespace_belongs_to_one_hook(self):
        with main.new(width=8, height=1) as canvas:

            def make(name: str) -> None:
                @canvas.hook(on='key')
                def keep(context: Context) -> None:
                    state = context.plugin.state
                    state.set('presses', number(state.get('presses', default=0)) + 1)
                    context.root.state.set(name, state.get('presses'))

            make('first')
            make('second')
            press(canvas)
            press(canvas)
            press(canvas)
            assert canvas.state.get('first') == 3
            assert canvas.state.get('second') == 3

    def test_removing_a_placement_or_hook_deletes_its_branch(self):
        with main.new(width=8, height=1) as canvas:
            placement = canvas.screen.write('a')
            placement.state.set('x', 1)

            @placement.hook(on='key')
            def keep(context: Context) -> None:
                context.plugin.state.set('y', 1)

            press(canvas)
            store = canvas._ensure_store()
            tree = store.snapshot().to_value()['xnano']
            assert len(tree['buffers']) == 1 and len(tree['plugins']) == 1
            namespace = placement.state
            placement.remove()
            canvas.deliver_events()
            tree = store.snapshot().to_value()['xnano']
            assert tree == {'buffers': {}, 'plugins': {}}
            with pytest.raises(TerminalError, match='was removed'):
                namespace.set('x', 2)
            assert namespace.get('x', default='gone') == 'gone'

    def test_a_large_namespace_is_still_saved(self):
        with main.new(width=8, height=1) as canvas:
            placement = canvas.screen.write('a')
            for index in range(70):
                placement.state.set(f'key{index}', index)

            @placement.hook(on='key')
            def push_more(context: Context) -> None:
                context.target.state.set('key3', 'changed')
                context.target.state.set('extra', 1)

            press(canvas)
            assert placement.state.get('key3') == 'changed'
            assert placement.state.get('extra') == 1
            assert placement.state.get('key69') == 69


@dataclass
class Counter:
    count: int = 0


class TestFollowingPaths:
    def test_a_state_hook_runs_again_only_when_a_path_it_read_changes(self):
        runs: list[object] = []
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='state')
            def follow(context: Context) -> None:
                runs.append(context.root.state.get('watched'))

            canvas.state.set('other', 1)
            canvas.deliver_events()
            assert runs == [None]
            canvas.state.set('other', 2)
            canvas.deliver_events()
            assert runs == [None]
            canvas.state.set('watched', 5)
            canvas.deliver_events()
            assert runs == [None, 5]
            canvas.state.set('watched', 6)
            canvas.deliver_events()
            assert runs == [None, 5, 6]

    def test_a_state_hook_follows_a_path_below_and_above_what_it_read(self):
        runs: list[object] = []
        with main.new(width=8, height=1) as canvas:
            canvas.state.set('player', {'score': 0, 'name': 'Ada'})

            @canvas.hook(on='state')
            def follow(context: Context) -> None:
                runs.append(context.root.state.get('player.score'))

            canvas.state.set('player.name', 'Bo')
            canvas.deliver_events()
            assert runs == [0]
            canvas.state.set('player.name', 'Cy')
            canvas.deliver_events()
            assert runs == [0]
            canvas.state.set('player.score', 4)
            canvas.deliver_events()
            assert runs == [0, 4]
            canvas.state.set('player', {'score': 9, 'name': 'Di'})
            canvas.deliver_events()
            assert runs == [0, 4, 9]

    def test_a_state_hook_that_read_nothing_follows_every_change(self):
        heard: list[int] = []
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='state')
            def follow(context: Context) -> None:
                heard.append(len(context.event.paths))  # type: ignore[union-attr]

            canvas.state.set('a', 1)
            canvas.deliver_events()
            canvas.state.set('b', 1)
            canvas.deliver_events()
            assert heard == [1, 1]

    def test_the_context_event_is_the_state_change(self):
        events: list[object] = []
        with main.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: events.append(context.event), on='state')
            canvas.state.set('a', 1)
            canvas.deliver_events()
            assert [type(event).__name__ for event in events] == ['TerminalStateChange']

    def test_a_replaced_store_is_described_by_a_real_state_change(self):
        import xnano_core
        from xnano.state import _prepare_state, _replaced_state

        earlier = _prepare_state(None, {'a': 1, 'b': 2})
        replacement = _prepare_state(None, {'a': 5, 'c': 3})
        change = _replaced_state(earlier.snapshot(), replacement)
        assert isinstance(change, xnano_core.TerminalStateChange)
        assert set(change.paths) >= {('a',), ('b',), ('c',)}
        assert change.after.to_value()['a'] == 5
        assert _replaced_state(earlier.snapshot(), earlier) is None

    def test_a_state_hook_that_pushes_what_it_read_does_not_loop(self):
        runs: list[int] = []
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='state')
            def double(context: Context) -> None:
                state = context.root.state
                value = number(state.get('count', default=0))
                runs.append(value)
                state.set('count', value + 1)

            canvas.state.set('count', 10)
            canvas.deliver_events()
            assert runs == [10]
            assert canvas.state.get('count') == 11

    def test_a_cascade_of_state_hooks_settles_in_one_step(self):
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='state')
            def first(context: Context) -> None:
                state = context.root.state
                state.set('b', number(state.get('a', default=0)) + 1)

            @canvas.hook(on='state')
            def second(context: Context) -> None:
                state = context.root.state
                state.set('c', number(state.get('b', default=0)) + 1)

            canvas.state.set('a', 1)
            canvas.deliver_events()
            assert (canvas.state.get('b'), canvas.state.get('c')) == (2, 3)

    def test_two_state_hooks_that_feed_each_other_stop_the_canvas_naming_both(self):
        canvas = main.new(width=8, height=1)

        @canvas.hook(on='state')
        def ping(context: Context) -> None:
            state = context.root.state
            state.set('ping', number(state.get('pong', default=0)) + 1)

        @canvas.hook(on='state')
        def pong(context: Context) -> None:
            state = context.root.state
            state.set('pong', number(state.get('ping', default=0)) + 1)

        canvas.state.set('ping', 1)
        with pytest.raises(TerminalError, match=r"hooks 'ping' and 'pong' keep changing"):
            canvas.deliver_events()
            canvas.close()

    def test_event_hooks_do_not_follow_reads(self):
        runs: list[object] = []
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='key')
            def count(context: Context) -> None:
                state = context.root.state
                runs.append(state.get('count', default=0))
                state.set('count', number(state.get('count', default=0)) + 1)

            @canvas.hook(on='custom')
            def reset(context: Context) -> None:
                context.root.state.set('count', 0)

            press(canvas)
            assert runs == [0]
            canvas.push(Event.custom('reset'))
            canvas.deliver_events()
            assert runs == [0]
            assert canvas.state.get('count') == 0

    def test_two_key_hooks_that_increment_one_path_add_two_and_do_not_repeat(self):
        with main.new(width=8, height=1) as canvas:

            def increment(context: Context) -> None:
                state = context.root.state
                state.set('count', number(state.get('count', default=0)) + 1)

            canvas.hook(increment, on='key')
            canvas.hook(increment, on='key')
            press(canvas)
            assert canvas.state.get('count') == 2

    def test_a_removed_state_hook_stops_following(self):
        runs: list[int] = []
        with main.new(width=8, height=1) as canvas:
            handle = canvas.hook(lambda context: runs.append(1), on='state')
            canvas.state.set('a', 1)
            canvas.deliver_events()
            handle.remove()
            canvas.deliver_events()
            canvas.state.set('a', 2)
            canvas.deliver_events()
            assert runs == [1]
            assert canvas._state_followers is not None
            assert not canvas._state_followers._everything

    def test_a_state_hook_on_a_placement_follows_the_state_it_read(self):
        runs: list[object] = []
        with main.new(width=8, height=1) as canvas:
            label = canvas.screen.write('a')

            @label.hook(on='state')
            def follow(context: Context) -> None:
                runs.append(context.target.state.get('level'))

            label.state.set('level', 1)
            canvas.deliver_events()
            label.state.set('level', 2)
            canvas.deliver_events()
            canvas.state.set('level', 99)
            canvas.deliver_events()
            assert runs == [1, 2]


class TestFollowerIndex:
    def test_the_index_finds_followers_by_read_path(self):
        from xnano.state import _StateFollowers

        class Follower:
            pass

        near, far, anything = Follower(), Follower(), Follower()
        index = _StateFollowers()
        index.follow(near, frozenset({('a', 'b')}))
        index.follow(far, frozenset({('c',)}))
        index.follow(anything, None)
        assert index.affected([('a', 'b', 'x')]) == {near, anything}
        assert index.affected([('a',)]) == {near, anything}
        assert index.affected([('c', 'd')]) == {far, anything}
        assert index.affected([('z',)]) == {anything}
        index.unfollow(near)
        index.unfollow(anything)
        assert index.affected([('a', 'b')]) == set()
        assert index.affected([('c',)]) == {far}


class TestStateAcrossOpen:
    def test_the_state_of_the_placements_survives_a_replaced_store(self):
        with main.new(width=8, height=1) as canvas:
            placement = canvas.screen.write('hi')
            placement.state.set('clicks', 3)
            canvas.state.set('free', 1)
            replacement = main.state._prepare_state(
                Settings(), canvas._state_store.snapshot().to_value()
            )
            assert replacement.snapshot(('free',)).to_value() == 1
            assert replacement.snapshot().to_value()['xnano']['buffers']

    def test_a_non_root_namespace_says_it_has_no_declared_fields(self):
        with main.new(width=8, height=1, state=Settings()) as canvas:
            placement = canvas.screen.write('hi')
            with pytest.raises(AttributeError, match='only the canvas.s own state does'):
                placement.state.volume  # noqa: B018
            with pytest.raises(TerminalError, match='no declared fields'):
                placement.state.volume = 3
            with pytest.raises(AttributeError, match="this canvas's state"):
                canvas.state.nothing  # noqa: B018

    def test_a_hook_on_the_state_of_a_realtime_canvas_hears_the_next_push(self):
        import time

        heard = []
        with main.new(realtime=True, width=8, height=1) as canvas:

            @canvas.hook(on='state')
            def watch(context: Context) -> None:
                heard.append(context.root.state.get('x'))

            canvas.state.set('x', 1)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and 1 not in heard:
                time.sleep(0.01)
        assert 1 in heard

    def test_the_active_run_belongs_to_each_thread(self):
        import threading

        with main.new(width=8, height=1) as canvas:
            marker = object()
            canvas._active_run = marker  # type: ignore[assignment]
            seen = []
            thread = threading.Thread(target=lambda: seen.append(canvas._active_run))
            thread.start()
            thread.join()
            assert seen == [None]
            assert canvas._active_run is marker
            canvas._active_run = None


class TestLocalStateTypes:
    def test_a_state_defined_inside_a_function_says_where_to_define_it(self):
        source = """
from __future__ import annotations
from dataclasses import dataclass, field

def make():
    @dataclass
    class Inner:
        value: int = 1

    @dataclass
    class Outer:
        inner: Inner = field(default_factory=Inner)

    return Outer()
"""
        namespace: dict[str, object] = {}
        exec(source, namespace)  # noqa: S102
        with pytest.raises(TerminalError, match='top level of a module'):
            main.new(state=namespace['make']())  # type: ignore[operator]
