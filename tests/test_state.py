"""
tests.test_state

Typed and dynamic state: namespaces, snapshots and transactions, and hooks that follow paths.
"""

import threading
from dataclasses import dataclass

import pytest
from typing_extensions import assert_type

import xnano as main
from xnano.context import Context
from xnano.errors import TerminalError
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
        thumb = canvas.write('#', x=canvas.ref(lambda state: state.volume))
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
            canvas.ref(lambda state: state.volume)


def test_an_expression_still_places_a_buffer():
    with main.new(width=10, height=1) as canvas:
        placed = canvas.write('#', x=ParentWidth // 2)
        canvas.deliver_events()
        assert placed.x == 5


@dataclass
class Typed:
    volume: float = 0.5
    muted: bool = False


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
            canvas.state.push('score', 3)
            assert canvas.state.get('score') == 3

    def test_pushing_a_deep_path_creates_the_objects_on_the_way(self):
        with main.new(width=8, height=1) as canvas:
            canvas.state.push('player.stats.score', 3)
            assert canvas.state.get('player') == {'stats': {'score': 3}}
            canvas.state.push('player.stats.level', 2)
            assert canvas.state.get('player.stats') == {'score': 3, 'level': 2}

    def test_a_list_is_addressed_by_index(self):
        with main.new(width=8, height=1) as canvas:
            canvas.state.push('items', [{'name': 'a'}, {'name': 'b'}])
            canvas.state.push('items.1.name', 'z')
            assert canvas.state.get('items.1.name') == 'z'
            assert canvas.state.get('items.5.name', default='none') == 'none'

    def test_the_root_hides_the_reserved_branch(self):
        with main.new(width=8, height=1) as canvas:
            canvas.state.push('score', 1)
            assert canvas.state.get('') == {'score': 1}
            with pytest.raises(ValueError, match="starts with 'xnano'"):
                canvas.state.push('xnano.buffers', 1)
            with pytest.raises(ValueError, match="starts with 'xnano'"):
                canvas.state.get('xnano')
            with pytest.raises(ValueError, match='whole root state'):
                canvas.state.push('', {'score': 2})

    def test_a_typed_root_has_get_push_and_its_attributes_at_run_time(self):
        with main.new(width=8, height=1, state=Typed()) as canvas:
            assert canvas.state.volume == 0.5
            canvas.state.volume = 0.75
            namespace: StateNamespace = canvas.state  # type: ignore[assignment]
            assert namespace.get('volume') == 0.75
            namespace.push('volume', 0.25)
            namespace.push('extra.count', 1)
            assert canvas.state.volume == 0.25
            assert namespace.get('extra.count') == 1

    def test_the_declared_type_of_the_accessor_follows_the_state_argument(self):
        with main.new(width=8, height=1, state=Typed()) as typed:
            assert_type(typed.state.volume, float)
        with main.new(width=8, height=1) as untyped:
            assert_type(untyped.state, StateNamespace)

    def test_an_attribute_that_is_not_a_field_says_what_to_use(self):
        with main.new(width=8, height=1, state=Typed()) as canvas:
            with pytest.raises(AttributeError, match=r"get\('loudness'\)"):
                _ = canvas.state.loudness  # type: ignore[attr-defined]
            with pytest.raises(TerminalError, match=r"push\('loudness', value\)"):
                canvas.state.loudness = 1  # type: ignore[attr-defined]

    @pytest.mark.parametrize('name', ['get', 'push', 'xnano'])
    def test_a_field_that_shadows_a_member_is_refused(self, name):
        Broken = dataclass(type('Broken', (), {'__annotations__': {name: int}, name: 1}))
        with pytest.raises(
            TerminalError, match=rf"field named '{name}'.*Rename the field"
        ):
            main.new(width=4, height=1, state=Broken())

    def test_a_value_the_field_refuses_names_the_path_and_the_fix(self):
        with main.new(width=8, height=1, state=Typed()) as canvas:
            with pytest.raises(TerminalError, match=r"push 'volume' to 'loud'.*accepts"):
                canvas.state.push('volume', 'loud')  # type: ignore[attr-defined]
            assert canvas.state.volume == 0.5

    def test_a_write_from_another_thread_is_saved_at_once(self):
        with main.new(width=8, height=1, realtime=True) as canvas:
            worker = threading.Thread(target=lambda: canvas.state.push('x', 9))
            worker.start()
            worker.join()
            assert canvas.state.get('x') == 9

    def test_a_replacing_store_keeps_the_free_paths_it_is_given(self):
        from xnano.state import prepare_state

        store = prepare_state(Typed(), {'earlier': 1, 'volume': 99})
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
                state.push('count', 1)
                state.push('count', number(state.get('count')) + 1)
                state.push('nested', {'a': 1})
                state.push('nested.b', 2)
                seen.append(
                    (state.get('count'), state.get('nested'), state.get('nested.b'))
                )
                state.push('nested', {'c': 3})
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
                state.push('a', 1)
                state.push('b', 2)
                state.push('c', 3)

            store = canvas._ensure_store()
            before = store.revision
            press(canvas)
            assert store.revision == before + 1
            assert [canvas.state.get(key) for key in 'abc'] == [1, 2, 3]

    def test_a_hook_that_raises_saves_nothing(self):
        canvas = main.new(width=8, height=1)

        @canvas.hook(on='key')
        def fail(context: Context) -> None:
            context.root.state.push('a', 1)
            raise RuntimeError('boom')

        canvas.push(Event.key_press('a'))
        canvas.deliver_events()
        assert canvas.state.get('a') is None
        with pytest.raises(TerminalError, match='boom'):
            canvas.close()

    def test_a_value_the_field_refuses_inside_a_hook_stops_the_canvas_with_the_fix(self):
        canvas = main.new(width=8, height=1, state=Typed())

        @canvas.hook(on='key')
        def wrong(context: Context[None, Typed]) -> None:
            context.root.state.volume = 'loud'  # type: ignore[assignment]

        canvas.push(Event.key_press('a'))
        with pytest.raises(TerminalError, match=r"push 'volume' to 'loud'"):
            canvas.deliver_events()
            canvas.close()

    def test_a_generator_hook_commits_at_each_resume(self):
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='key')
            def steps(context: Context):
                state = context.root.state
                state.push('step', 1)
                context = yield
                state.push('step', number(state.get('step')) + 1)
                context = yield
                state.push('step', number(state.get('step')) + 1)

            press(canvas)
            assert canvas.state.get('step') == 1
            press(canvas)
            assert canvas.state.get('step') == 2
            press(canvas)
            assert canvas.state.get('step') == 3

    def test_two_namespaces_of_the_same_name_do_not_meet(self):
        with main.new(width=20, height=2) as canvas:
            first = canvas.write('a')
            second = canvas.write('b', y=1)
            for placement in (first, second):

                @placement.hook(on='key')
                def count(context: Context) -> None:
                    state = context.buffer.state
                    state.push('count', number(state.get('count', default=0)) + 1)

            first.state.push('own', 'first')
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
                    state.push('presses', number(state.get('presses', default=0)) + 1)
                    context.root.state.push(name, state.get('presses'))

            make('first')
            make('second')
            press(canvas)
            press(canvas)
            press(canvas)
            assert canvas.state.get('first') == 3
            assert canvas.state.get('second') == 3

    def test_removing_a_placement_or_hook_deletes_its_branch(self):
        with main.new(width=8, height=1) as canvas:
            placement = canvas.write('a')
            placement.state.push('x', 1)

            @placement.hook(on='key')
            def keep(context: Context) -> None:
                context.plugin.state.push('y', 1)

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
                namespace.push('x', 2)
            assert namespace.get('x', default='gone') == 'gone'

    def test_a_large_namespace_is_still_saved(self):
        with main.new(width=8, height=1) as canvas:
            placement = canvas.write('a')
            for index in range(70):
                placement.state.push(f'key{index}', index)

            @placement.hook(on='key')
            def push_more(context: Context) -> None:
                context.buffer.state.push('key3', 'changed')
                context.buffer.state.push('extra', 1)

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

            canvas.state.push('other', 1)
            canvas.deliver_events()
            assert runs == [None]
            canvas.state.push('other', 2)
            canvas.deliver_events()
            assert runs == [None]
            canvas.state.push('watched', 5)
            canvas.deliver_events()
            assert runs == [None, 5]
            canvas.state.push('watched', 6)
            canvas.deliver_events()
            assert runs == [None, 5, 6]

    def test_a_state_hook_follows_a_path_below_and_above_what_it_read(self):
        runs: list[object] = []
        with main.new(width=8, height=1) as canvas:
            canvas.state.push('player', {'score': 0, 'name': 'Ada'})

            @canvas.hook(on='state')
            def follow(context: Context) -> None:
                runs.append(context.root.state.get('player.score'))

            canvas.state.push('player.name', 'Bo')
            canvas.deliver_events()
            assert runs == [0]
            canvas.state.push('player.name', 'Cy')
            canvas.deliver_events()
            assert runs == [0]
            canvas.state.push('player.score', 4)
            canvas.deliver_events()
            assert runs == [0, 4]
            canvas.state.push('player', {'score': 9, 'name': 'Di'})
            canvas.deliver_events()
            assert runs == [0, 4, 9]

    def test_a_state_hook_that_read_nothing_follows_every_change(self):
        heard: list[int] = []
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='state')
            def follow(context: Context) -> None:
                heard.append(len(context.event.paths))  # type: ignore[union-attr]

            canvas.state.push('a', 1)
            canvas.deliver_events()
            canvas.state.push('b', 1)
            canvas.deliver_events()
            assert heard == [1, 1]

    def test_the_context_event_is_the_state_change(self):
        events: list[object] = []
        with main.new(width=8, height=1) as canvas:
            canvas.hook(lambda context: events.append(context.event), on='state')
            canvas.state.push('a', 1)
            canvas.deliver_events()
            assert [type(event).__name__ for event in events] == ['TerminalStateChange']

    def test_a_state_hook_that_pushes_what_it_read_does_not_loop(self):
        runs: list[int] = []
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='state')
            def double(context: Context) -> None:
                state = context.root.state
                value = number(state.get('count', default=0))
                runs.append(value)
                state.push('count', value + 1)

            canvas.state.push('count', 10)
            canvas.deliver_events()
            assert runs == [10]
            assert canvas.state.get('count') == 11

    def test_a_cascade_of_state_hooks_settles_in_one_step(self):
        with main.new(width=8, height=1) as canvas:

            @canvas.hook(on='state')
            def first(context: Context) -> None:
                state = context.root.state
                state.push('b', number(state.get('a', default=0)) + 1)

            @canvas.hook(on='state')
            def second(context: Context) -> None:
                state = context.root.state
                state.push('c', number(state.get('b', default=0)) + 1)

            canvas.state.push('a', 1)
            canvas.deliver_events()
            assert (canvas.state.get('b'), canvas.state.get('c')) == (2, 3)

    def test_two_state_hooks_that_feed_each_other_stop_the_canvas_naming_both(self):
        canvas = main.new(width=8, height=1)

        @canvas.hook(on='state')
        def ping(context: Context) -> None:
            state = context.root.state
            state.push('ping', number(state.get('pong', default=0)) + 1)

        @canvas.hook(on='state')
        def pong(context: Context) -> None:
            state = context.root.state
            state.push('pong', number(state.get('ping', default=0)) + 1)

        canvas.state.push('ping', 1)
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
                state.push('count', number(state.get('count', default=0)) + 1)

            @canvas.hook(on='custom')
            def reset(context: Context) -> None:
                context.root.state.push('count', 0)

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
                state.push('count', number(state.get('count', default=0)) + 1)

            canvas.hook(increment, on='key')
            canvas.hook(increment, on='key')
            press(canvas)
            assert canvas.state.get('count') == 2

    def test_a_removed_state_hook_stops_following(self):
        runs: list[int] = []
        with main.new(width=8, height=1) as canvas:
            handle = canvas.hook(lambda context: runs.append(1), on='state')
            canvas.state.push('a', 1)
            canvas.deliver_events()
            handle.remove()
            canvas.deliver_events()
            canvas.state.push('a', 2)
            canvas.deliver_events()
            assert runs == [1]
            assert canvas._state_followers is not None
            assert not canvas._state_followers._everything

    def test_a_state_hook_on_a_placement_follows_the_state_it_read(self):
        runs: list[object] = []
        with main.new(width=8, height=1) as canvas:
            label = canvas.write('a')

            @label.hook(on='state')
            def follow(context: Context) -> None:
                runs.append(context.buffer.state.get('level'))

            label.state.push('level', 1)
            canvas.deliver_events()
            label.state.push('level', 2)
            canvas.deliver_events()
            canvas.state.push('level', 99)
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
