"""
tests.test_inputs

The inputs of a hook's context as properties, and their ``get`` and ``push`` methods.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.context import Context
from xnano.input import ClipboardInput, KeyboardInput, MouseInput, ScrollInput
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
        assert isinstance(keyboard, KeyboardInput)
        assert keyboard.key == 's'
        assert keyboard.kind == 'press'
        assert keyboard.modifiers == {'control'}
        assert keyboard.text is None
        assert keyboard.get().key == 's'

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
            assert context.keyboard.get() is None

    def test_push_presses_a_key(self, canvas):
        contexts = record(canvas, on='key')
        canvas.hook(lambda context: context.keyboard.push('x'), on='tick', after=0.05)
        canvas.step(delta_seconds=0.1)
        canvas.deliver_events()
        assert [context.keyboard.key for context in contexts] == ['x']

    def test_push_accepts_a_chord_and_a_key_event(self, canvas):
        contexts = record(canvas, on='key')
        keyboard = KeyboardInput(canvas, None)
        keyboard.push('ctrl+shift+q')
        keyboard.push(Event.key_press('alt+x', kind='repeat').key)
        canvas.deliver_events()
        assert [(c.keyboard.key, c.keyboard.kind) for c in contexts] == [
            ('q', 'press'),
            ('x', 'repeat'),
        ]
        assert contexts[0].keyboard.modifiers == {'control', 'shift'}


class TestMouse:
    def test_a_press(self, canvas):
        contexts = record(canvas, on='mouse')
        push(canvas, Event.mouse_event(column=3, row=2, kind='press', button='left'))
        mouse = contexts[0].mouse
        assert isinstance(mouse, MouseInput)
        assert mouse.position == Point(3, 2)
        assert mouse.button == 'left'
        assert mouse.kind == 'press'
        assert mouse.is_down is True
        assert mouse.get().column == 3

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
        assert mouse.position is None
        assert mouse.button is None
        assert mouse.kind is None
        assert mouse.is_down is False
        assert mouse.get() is None

    def test_the_wheel_is_not_a_mouse_event(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.mouse_event(column=3, row=2, kind='scroll', scroll_y=1))
        mouse = contexts[0].mouse
        assert (mouse.position, mouse.button, mouse.kind, mouse.get()) == (None,) * 4

    def test_push_moves_the_pointer(self, canvas):
        contexts = record(canvas, on='mouse')
        MouseInput(canvas, None).push((7, 3))
        canvas.deliver_events()
        assert contexts[0].mouse.position == Point(7, 3)
        assert contexts[0].mouse.kind == 'move'

    def test_push_accepts_a_mouse_event(self, canvas):
        contexts = record(canvas, on='mouse')
        event = Event.mouse_event(column=2, row=1, kind='press', button='right')
        MouseInput(canvas, None).push(event.mouse)
        canvas.deliver_events()
        assert (contexts[0].mouse.kind, contexts[0].mouse.button) == ('press', 'right')

    def test_push_refuses_the_wheel_and_names_scroll(self, canvas):
        wheel = Event.mouse_event(column=2, row=1, kind='scroll', scroll_y=1).mouse
        with pytest.raises(TypeError, match=r'scroll.push\(\(x, y\)\)'):
            MouseInput(canvas, None).push(wheel)


class TestScroll:
    def test_steps_are_signed(self, canvas):
        contexts = record(canvas, on='scroll')
        push(
            canvas,
            Event.mouse_event(column=3, row=2, kind='scroll', scroll_y=-1),
            Event.mouse_event(column=3, row=2, kind='scroll', scroll_x=2),
        )
        scroll = contexts[0].scroll
        assert isinstance(scroll, ScrollInput)
        assert (scroll.x, scroll.y) == (0, -1)
        assert (contexts[1].scroll.x, contexts[1].scroll.y) == (2, 0)
        assert scroll.get().scroll_y == -1

    def test_it_is_zero_for_other_events(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.key_press('a'))
        scroll = contexts[0].scroll
        assert (scroll.x, scroll.y, scroll.get()) == (0, 0, None)

    def test_push_scrolls_at_the_pointer(self, canvas):
        contexts = record(canvas, on='scroll')
        MouseInput(canvas, None).push((4, 1))
        canvas.deliver_events()
        ScrollInput(canvas, None).push((0, -1))
        canvas.deliver_events()
        assert contexts[0].scroll.y == -1
        assert contexts[0].event.mouse.position == Point(4, 1)

    def test_push_scrolls_at_a_pointer_pushed_before_the_next_step(self, canvas):
        contexts = record(canvas, on='scroll')
        MouseInput(canvas, None).push((6, 2))
        ScrollInput(canvas, None).push((0, 1))
        canvas.deliver_events()
        assert contexts[0].scroll.y == 1
        assert contexts[0].event.mouse.position == Point(6, 2)

    def test_push_scrolls_at_the_seen_pointer_after_a_pushed_move_was_delivered(
        self, canvas
    ):
        contexts = record(canvas, on='scroll')
        canvas.push(Event.mouse_event(column=1, row=1, kind='move'))
        canvas.deliver_events()
        MouseInput(canvas, None).push((3, 3))
        canvas.deliver_events()
        canvas.push(Event.mouse_event(column=1, row=1, kind='move'))
        canvas.deliver_events()
        ScrollInput(canvas, None).push((0, 1))
        canvas.deliver_events()
        assert contexts[0].event.mouse.position == Point(1, 1)

    def test_push_accepts_a_wheel_event(self, canvas):
        contexts = record(canvas, on='scroll')
        wheel = Event.mouse_event(column=2, row=2, kind='scroll', scroll_x=3).mouse
        ScrollInput(canvas, None).push(wheel)
        canvas.deliver_events()
        assert contexts[0].scroll.x == 3

    def test_push_refuses_other_mouse_events_and_names_mouse(self, canvas):
        press = Event.mouse_event(column=2, row=1, kind='press', button='left').mouse
        with pytest.raises(TypeError, match=r'context.mouse.push\(event\)'):
            ScrollInput(canvas, None).push(press)


class TestClipboard:
    def test_pasted_text(self, canvas):
        contexts = record(canvas, on='paste')
        push(canvas, Event.paste('two words'))
        clipboard = contexts[0].clipboard
        assert isinstance(clipboard, ClipboardInput)
        assert clipboard.text == 'two words'
        assert clipboard.get() == 'two words'

    def test_it_is_empty_for_other_events(self, canvas):
        contexts = record(canvas)
        push(canvas, Event.key_press('a'))
        assert contexts[0].clipboard.text is None

    def test_push_pastes(self, canvas):
        contexts = record(canvas, on='paste')
        ClipboardInput(canvas, None).push('hello')
        canvas.deliver_events()
        assert contexts[0].clipboard.text == 'hello'

    def test_push_needs_text(self, canvas):
        with pytest.raises(TypeError, match='Pass a str'):
            ClipboardInput(canvas, None).push(3)  # type: ignore[arg-type]


class TestHeldNamesAreChecked:
    def test_a_misspelled_key_or_button_is_explained(self, canvas):
        with pytest.raises(
            ValueError, match=r"'entr' is not a key or a mouse button.*'enter'"
        ):
            canvas.input.is_down('entr')
        with pytest.raises(ValueError, match=r"'left_mouse'.*one of 'mouse_left'"):
            canvas.input.is_down('left_mouse')
        with pytest.raises(ValueError, match=r"'lefft' is not a key or a mouse button"):
            canvas.input.axis('lefft', 'right')
        with pytest.raises(ValueError) as caught:
            canvas.input.is_down('left_mouse')
        assert 'chord' not in str(caught.value)

    def test_a_name_that_is_not_text_is_explained(self, canvas):
        for keys in (5, None, ['a', 5]):
            with pytest.raises(TypeError, match=r'Held input takes a key name'):
                canvas.input.is_down(keys)
        with pytest.raises(TypeError, match=r'Held input takes a key name'):
            canvas.input.direction(left=1)


class TestHeldNamesMatchTheHeldKeys:
    def test_an_alias_or_a_capital_matches_the_key_that_is_held(self, canvas):
        canvas.input  # noqa: B018
        push(canvas, Event.key_press('escape'))
        push(canvas, Event.key_press('space'))
        assert canvas.input.is_down('Esc') is True
        assert canvas.input.is_down('Space') is True
        assert canvas.input.is_down('Enter') is False

    def test_a_chord_or_a_modifier_is_explained(self, canvas):
        with pytest.raises(
            ValueError, match=r"'ctrl\+s' is a modifier or a chord.*hook\(keys="
        ):
            canvas.input.is_down('ctrl+s')
        with pytest.raises(ValueError, match="'shift' is a modifier or a chord"):
            canvas.input.axis('shift', 'right')


class TestHeldMouseButtons:
    def test_the_buttons_are_in_the_held_input_vocabulary(self, canvas):
        canvas.hook(lambda context: None, on='mouse')
        assert canvas.input.is_down('mouse_left') is False
        push(canvas, Event.mouse_event(column=1, row=1, kind='press', button='left'))
        assert canvas.input.is_down('mouse_left') is True
        assert canvas.input.is_down(('mouse_right', 'mouse_left')) is True
        assert canvas.input.is_down('mouse_middle') is False
        assert 'mouse_left' in canvas.input.held_keys
        push(canvas, Event.mouse_event(column=1, row=1, kind='release', button='left'))
        assert canvas.input.is_down('mouse_left') is False


class TestMousePush:
    def test_a_mouse_event_inside_an_event_is_unwrapped(self, canvas):
        heard = record(canvas, 'mouse')
        canvas.hook(
            lambda context: context.mouse.push(
                Event.mouse_event(column=2, row=1, kind='move')
            ),
            on='key',
        )
        push(canvas, Event.key_press('a'))
        assert [item.mouse.kind for item in heard] == ['move']

    def test_values_that_are_not_mouse_input_are_explained(self, canvas):
        errors = []

        def try_push(context: Context, value: object) -> None:
            try:
                context.mouse.push(value)  # type: ignore[arg-type]
            except TypeError as error:
                errors.append(str(error))

        def attempt(context: Context) -> None:
            try_push(context, Event.key_press('b'))
            try_push(context, 'move')

        canvas.hook(attempt, on='key')
        push(canvas, Event.key_press('a'))
        assert 'takes a mouse event' in errors[0]
        assert 'MouseEvent or an (x, y) pair' in errors[1]


class TestPushedPairs:
    def test_a_pair_that_is_not_two_whole_numbers_is_explained(self, canvas):
        errors = []

        def try_push(context: Context, call: str, value: object) -> None:
            try:
                getattr(context, call).push(value)
            except TypeError as error:
                errors.append(str(error))

        def attempt(context: Context) -> None:
            try_push(context, 'mouse', (1, 2, 3))
            try_push(context, 'scroll', (1,))
            try_push(context, 'scroll', 5)

        canvas.hook(attempt, on='key')
        push(canvas, Event.key_press('a'))
        assert 'mouse.push takes a pair of whole numbers' in errors[0]
        assert 'scroll.push takes a pair of whole numbers' in errors[1]
        assert 'scroll.push takes a MouseEvent' in errors[2]

    def test_a_number_out_of_range_is_explained_and_changes_nothing(self, canvas):
        errors = []

        def try_push(context: Context, call: str, value: object) -> None:
            try:
                getattr(context, call).push(value)
            except ValueError as error:
                errors.append(str(error))

        def attempt(context: Context) -> None:
            try_push(context, 'mouse', (10**12, 5))
            try_push(context, 'scroll', (0, 10**12))
            try_push(context, 'scroll', (0, 1))

        canvas.hook(attempt, on='key')
        push(canvas, Event.key_press('a'))
        assert len(errors) == 2
        assert 'mouse.push takes whole numbers from' in errors[0]
        assert 'scroll.push takes whole numbers from' in errors[1]
        assert 'steps of the wheel' in errors[1]
        assert 'a cell on the screen' in errors[0]
