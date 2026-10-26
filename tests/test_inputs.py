"""
tests.test_inputs

The keyboard and the mouse of a canvas: what they read of the event a hook handles, what is held
down right now, and the program's own key presses, pastes, clicks, drags and turns of the wheel.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.devices import HeldButton, Keyboard, Mouse, Scroll
from xnano.hooks import Context
from xnano_core import Event, Point


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=6, fps=10) as opened:
        yield opened


def push(canvas, *events: Event) -> None:
    for event in events:
        canvas.push(event)
    canvas.deliver_events()


def record(canvas, on: str | None = None) -> list[Context]:
    contexts: list[Context] = []
    canvas.hook(contexts.append, on=on)
    return contexts


class TestKeyboard:
    def test_a_key_event(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.key_press('ctrl+s'))
        keyboard = contexts[0].keyboard
        assert isinstance(keyboard, Keyboard)
        assert keyboard.key == 's'
        assert keyboard.kind == 'press'
        assert keyboard.modifiers == {'control'}
        assert keyboard.text is None
        assert keyboard.binding == 'ctrl+s'
        assert keyboard.event is not None and keyboard.event.key == 's'

    def test_text_of_a_typed_key(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.key_press('a'))
        assert contexts[0].keyboard.text == 'a'

    def test_it_is_empty_for_other_events(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.paste('x'), Event.mouse_event(column=1, row=1, kind='move'))
        for context in contexts:
            assert context.keyboard.key is None
            assert context.keyboard.kind is None
            assert context.keyboard.modifiers == frozenset()
            assert context.keyboard.event is None

    def test_outside_a_hook_there_is_no_key_being_handled(self, canvas):
        assert canvas.keyboard.key is None
        assert canvas.keyboard.event is None

    def test_press_presses_a_key(self, canvas):
        contexts = record(canvas, on='key')
        canvas.hook(lambda context: context.keyboard.press('x'), on='tick', after=0.05)
        canvas.clock.step(delta_seconds=0.1)
        canvas.deliver_events()
        assert [context.keyboard.key for context in contexts] == ['x']

    def test_press_takes_a_key_binding_and_a_key_event(self, canvas):
        contexts = record(canvas, on='key')
        canvas.keyboard.press('ctrl+shift+q')
        canvas.keyboard.press(Event.key_press('alt+x', kind='repeat').key)
        canvas.deliver_events()
        assert [
            (context.keyboard.key, context.keyboard.kind) for context in contexts
        ] == [
            ('q', 'press'),
            ('x', 'repeat'),
        ]
        assert contexts[0].keyboard.modifiers == {'control', 'shift'}

    def test_press_explains_what_it_takes(self, canvas):
        with pytest.raises(TypeError, match=r'keyboard\.press\("q"\)'):
            canvas.keyboard.press(5)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match='not a key name'):
            canvas.keyboard.press('zzz')


class TestPaste:
    def test_pasted_text(self, canvas):
        contexts = record(canvas, on='paste')
        push(canvas, Event.paste('two words'))
        assert contexts[0].keyboard.pasted == 'two words'

    def test_it_is_empty_for_other_events(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.key_press('a'))
        assert contexts[0].keyboard.pasted is None

    def test_paste_pastes(self, canvas):
        contexts = record(canvas, on='paste')
        canvas.keyboard.paste('hello')
        canvas.deliver_events()
        assert contexts[0].keyboard.pasted == 'hello'

    def test_paste_needs_text(self, canvas):
        with pytest.raises(TypeError, match='Pass a str'):
            canvas.keyboard.paste(3)  # type: ignore[arg-type]


class TestMouse:
    def test_a_press(self, canvas):
        contexts = record(canvas, on='mouse')
        push(canvas, Event.mouse_event(column=3, row=2, kind='press', button='left'))
        mouse = contexts[0].mouse
        assert isinstance(mouse, Mouse)
        assert mouse.position == Point(3, 2)
        assert mouse.button == 'left'
        assert mouse.kind == 'press'
        assert mouse.is_down is True
        assert mouse.event is not None and mouse.event.column == 3

    def test_is_down_is_the_held_state(self, canvas):
        states: list[bool] = []
        canvas.hook(lambda context: states.append(context.mouse.is_down), on='mouse')
        push(canvas, Event.mouse_event(column=3, row=2, kind='press', button='left'))
        push(canvas, Event.mouse_event(column=4, row=2, kind='move'))
        push(canvas, Event.mouse_event(column=4, row=2, kind='release', button='left'))
        assert states == [True, True, False]

    def test_it_is_empty_for_other_events(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.key_press('a'))
        mouse = contexts[0].mouse
        assert (mouse.position, mouse.button, mouse.kind, mouse.event) == (None,) * 4
        assert mouse.is_down is False

    def test_the_wheel_is_not_a_pointer_event(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.mouse_event(column=3, row=2, kind='scroll', scroll_y=1))
        mouse = contexts[0].mouse
        assert (mouse.position, mouse.button, mouse.kind, mouse.event) == (None,) * 4

    def test_assigning_the_pointer_moves_it(self, canvas):
        contexts = record(canvas, on='mouse')
        canvas.mouse.pointer = (7, 3)
        canvas.deliver_events()
        assert contexts[0].mouse.position == Point(7, 3)
        assert contexts[0].mouse.kind == 'move'
        assert canvas.mouse.pointer == (7, 3)

    def test_click_presses_and_releases_at_a_cell(self, canvas):
        contexts = record(canvas, on='mouse')
        canvas.mouse.click('right', x=2, y=1)
        canvas.deliver_events()
        assert [(context.mouse.kind, context.mouse.button) for context in contexts] == [
            ('press', 'right'),
            ('release', 'right'),
        ]
        assert contexts[0].mouse.position == Point(2, 1)

    def test_a_held_button_drags_until_the_block_ends(self, canvas):
        contexts = record(canvas, on='mouse')
        with canvas.mouse.press('left', x=1, y=1) as button:
            assert isinstance(button, HeldButton)
            button.right(3).down()
        canvas.deliver_events()
        assert [context.mouse.kind for context in contexts] == [
            'press',
            'drag',
            'drag',
            'release',
        ]
        assert contexts[-1].mouse.position == Point(4, 2)
        assert button.is_released

    def test_a_held_button_shows_as_held_once_delivered(self, canvas):
        held = canvas.mouse.press('left', x=1, y=1)
        canvas.deliver_events()
        assert canvas.mouse.held_buttons == {'left'}
        assert canvas.mouse.is_down
        held.release()
        canvas.deliver_events()
        assert canvas.mouse.held_buttons == frozenset()

    def test_button_is_the_held_button_between_a_press_and_its_release(self, canvas):
        seen: list[str | None] = []
        canvas.hook(lambda context: seen.append(context.mouse.button), on='key')
        held = canvas.mouse.press('left', x=1, y=1)
        push(canvas, Event.key_press('a'))
        assert canvas.mouse.button == 'left'
        held.release()
        push(canvas, Event.key_press('b'))
        assert seen == ['left', None]
        assert canvas.mouse.button is None

    def test_a_hook_without_on_runs_on_every_frame_while_a_button_is_held(self, canvas):
        placement = canvas.screen.write('hello', x=2, y=1)
        heard: list[tuple[str, str | None]] = []
        pointer_kinds: list[str | None] = []

        @placement.hook
        def follow(context: Context) -> None:
            heard.append((type(context.event).__name__, context.mouse.button))

        placement.hook(
            lambda context: pointer_kinds.append(context.mouse.kind), on='mouse'
        )
        held = canvas.mouse.press('left', x=3, y=1)
        canvas.deliver_events()
        # The frame 0.1 seconds after the press is inside the delay before frames run.
        for _ in range(4):
            canvas.clock.step()
        held.release()
        canvas.deliver_events()
        for _ in range(3):
            canvas.clock.step()
        assert heard == [('Event', 'left'), *[('Frame', 'left')] * 3, ('Event', 'left')]
        assert pointer_kinds == ['press', 'release'], 'a mouse hook hears only events'

    def test_the_frames_stop_when_the_button_is_released_elsewhere(self, canvas):
        placement = canvas.screen.write('hello', x=2, y=1)
        frames: list[int] = []

        @placement.hook
        def follow(context: Context) -> None:
            if not isinstance(context.event, Event):
                frames.append(1)

        with canvas.mouse.press('left', x=3, y=1) as held:
            canvas.deliver_events()
            for _ in range(3):
                canvas.clock.step()
            held.move(x=10, y=3)
        canvas.deliver_events()
        count = len(frames)
        for _ in range(3):
            canvas.clock.step()
        assert count >= 1
        assert len(frames) == count

    def test_move_moves_by_cells_from_the_pointer(self, canvas):
        canvas.mouse.pointer = (5, 2)
        canvas.mouse.move(-2, 1)
        canvas.deliver_events()
        assert canvas.mouse.pointer == (3, 3)

    def test_a_button_name_is_checked(self, canvas):
        with pytest.raises(ValueError, match="'left', 'right' or 'middle'"):
            canvas.mouse.press('top')  # type: ignore[arg-type]


class TestScroll:
    def test_steps_are_signed(self, canvas):
        contexts = record(canvas, on='scroll')
        push(
            canvas,
            Event.mouse_event(column=3, row=2, kind='scroll', scroll_y=-1),
            Event.mouse_event(column=3, row=2, kind='scroll', scroll_x=2),
        )
        scroll = contexts[0].mouse.scroll
        assert isinstance(scroll, Scroll)
        assert (scroll.x, scroll.y) == (0, -1)
        assert (contexts[1].mouse.scroll.x, contexts[1].mouse.scroll.y) == (2, 0)
        assert scroll.event is not None and scroll.event.scroll_y == -1

    def test_it_is_zero_for_other_events(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.key_press('a'))
        scroll = contexts[0].mouse.scroll
        assert (scroll.x, scroll.y, scroll.event) == (0, 0, None)

    def test_turn_scrolls_at_the_pointer(self, canvas):
        contexts = record(canvas, on='scroll')
        canvas.mouse.pointer = (4, 1)
        canvas.deliver_events()
        canvas.mouse.scroll.turn(y=-1)
        canvas.deliver_events()
        assert contexts[0].mouse.scroll.y == -1
        assert contexts[0].event.mouse.position == Point(4, 1)

    def test_turn_scrolls_at_a_pointer_moved_before_the_next_step(self, canvas):
        contexts = record(canvas, on='scroll')
        canvas.mouse.pointer = (6, 2)
        canvas.mouse.scroll.turn(y=1)
        canvas.deliver_events()
        assert contexts[0].mouse.scroll.y == 1
        assert contexts[0].event.mouse.position == Point(6, 2)

    def test_turn_scrolls_at_the_seen_pointer_after_a_moved_pointer_was_delivered(
        self, canvas
    ):
        contexts = record(canvas, on='scroll')
        canvas.push(Event.mouse_event(column=1, row=1, kind='move'))
        canvas.deliver_events()
        canvas.mouse.pointer = (3, 3)
        canvas.deliver_events()
        canvas.push(Event.mouse_event(column=1, row=1, kind='move'))
        canvas.deliver_events()
        canvas.mouse.scroll.turn(y=1)
        canvas.deliver_events()
        assert contexts[0].event.mouse.position == Point(1, 1)


class TestHeldKeys:
    def test_a_misspelled_key_is_explained(self, canvas):
        with pytest.raises(ValueError, match=r"'entr' is not a key.*'enter'"):
            canvas.keyboard.is_down('entr')
        with pytest.raises(ValueError, match=r"'lefft' is not a key"):
            canvas.keyboard.axis('lefft', 'right')

    def test_a_mouse_button_points_to_the_mouse(self, canvas):
        with pytest.raises(ValueError, match='canvas.mouse.held_buttons'):
            canvas.keyboard.is_down('mouse_left')
        with pytest.raises(ValueError, match='canvas.mouse.held_buttons'):
            canvas.keyboard.is_down('left_mouse')

    def test_a_name_that_is_not_text_is_explained(self, canvas):
        for keys in (5, None, ['a', 5]):
            with pytest.raises(TypeError, match=r'The keyboard takes a key name'):
                canvas.keyboard.is_down(keys)
        with pytest.raises(TypeError, match=r'The keyboard takes a key name'):
            canvas.keyboard.direction(left=1)

    def test_an_alias_or_a_capital_matches_the_key_that_is_held(self, canvas):
        assert canvas.keyboard.held_keys == frozenset()
        push(canvas, Event.key_press('escape'))
        assert canvas.keyboard.is_down('Esc') is True
        push(canvas, Event.key_press('space'))
        assert canvas.keyboard.is_down('Space') is True
        assert canvas.keyboard.is_down('Enter') is False

    def test_a_key_hook_counts_its_own_key_and_not_the_one_before(self, canvas):
        directions = []
        canvas.hook(
            lambda context: directions.append(context.keyboard.direction()), on='key'
        )
        for key in ('left', 'left', 'right'):
            push(canvas, Event.key_press(key))
        # Without release reports, only the newest key held repeats.
        assert directions == [(-1, 0), (-1, 0), (1, 0)]
        assert canvas.keyboard.held_keys == {'right'}

    def test_a_key_binding_or_a_modifier_is_explained(self, canvas):
        with pytest.raises(
            ValueError, match=r"'ctrl\+s' is a modifier or a key binding.*hook\(keys="
        ):
            canvas.keyboard.is_down('ctrl+s')
        with pytest.raises(ValueError, match="'shift' is a modifier or a key binding"):
            canvas.keyboard.axis('shift', 'right')

    def test_held_buttons_are_not_held_keys(self, canvas):
        canvas.hook(lambda context: None, on='mouse')
        push(canvas, Event.mouse_event(column=1, row=1, kind='press', button='left'))
        assert canvas.mouse.held_buttons == {'left'}
        assert canvas.keyboard.held_keys == frozenset()


class TestCells:
    def test_a_cell_that_is_not_two_whole_numbers_is_explained(self, canvas):
        with pytest.raises(
            TypeError, match='mouse.pointer takes a pair of whole numbers'
        ):
            canvas.mouse.pointer = (1, 2, 3)  # type: ignore[assignment]
        with pytest.raises(TypeError, match='scroll.turn takes a pair of whole numbers'):
            canvas.mouse.scroll.turn(y=1.5)  # type: ignore[arg-type]

    def test_a_number_out_of_range_is_explained_and_changes_nothing(self, canvas):
        heard = record(canvas)
        with pytest.raises(ValueError, match='mouse.pointer takes whole numbers from'):
            canvas.mouse.pointer = (10**12, 5)
        with pytest.raises(ValueError, match='steps of the wheel'):
            canvas.mouse.scroll.turn(y=10**12)
        canvas.deliver_events()
        assert heard == []
