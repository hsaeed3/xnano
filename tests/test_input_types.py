"""
tests.test_input_types

The values a hook reads from ``context.keyboard``, ``context.mouse`` and ``context.input`` are
typed with the names they can take, so an editor suggests ``'enter'`` and a type checker catches
``'enterr'``. ``make typecheck`` checks this file with the argument and call checks that the other
tests switch off; every test also runs, so the types and the values cannot drift apart.
"""

# pyright: reportArgumentType=true, reportIndexIssue=true, reportCallIssue=true
# pyright: reportAttributeAccessIssue=true, reportUnnecessaryTypeIgnoreComment=true

from __future__ import annotations

from typing_extensions import assert_type

import xnano
import xnano_core
from xnano.devices import KeyName
from xnano.events import Event


def test_the_keyboard_reports_typed_names():
    heard: list[tuple[KeyName | None, xnano_core.KeyEventKind | None]] = []

    with xnano.new(width=8, height=1) as canvas:

        @canvas.hook(on='key')
        def listen(context: xnano.Context) -> None:
            keyboard = context.keyboard
            assert_type(keyboard.key, KeyName | None)
            assert_type(keyboard.kind, xnano_core.KeyEventKind | None)
            assert_type(keyboard.modifiers, frozenset[xnano_core.KeyModifier])
            assert_type(keyboard.binding, 'xnano_core.KeyBindingText | None')
            heard.append((keyboard.key, keyboard.kind))

        canvas.push(Event.key_press('enter'))
        canvas.deliver_events()

    assert heard == [('enter', 'press')]


def test_the_mouse_reports_typed_buttons():
    seen: list[xnano_core.MouseButton | None] = []

    with xnano.new(width=8, height=1) as canvas:

        @canvas.hook(on='mouse')
        def listen(context: xnano.Context) -> None:
            mouse = context.mouse
            assert_type(mouse.button, xnano_core.MouseButton | None)
            seen.append(mouse.button)

        canvas.push(Event.mouse_event(column=1, row=0, kind='press', button='left'))
        canvas.deliver_events()

    assert seen == ['left']


def test_held_input_takes_and_reports_typed_names():
    with xnano.new(width=8, height=1) as canvas:
        keyboard = canvas.keyboard
        assert_type(keyboard.held_keys, frozenset[KeyName])
        assert_type(keyboard.is_down('space'), bool)
        assert_type(keyboard.is_down(('a', 'left')), bool)
        assert_type(keyboard.direction(), tuple[int, int])
        assert keyboard.is_down('space') is False
        assert_type(canvas.mouse.held_buttons, frozenset[xnano_core.MouseButton])
        assert canvas.mouse.held_buttons == frozenset()


def test_a_binding_reads_the_same_as_a_string_and_as_an_expression():
    import pytest

    from xnano.expressions import keyboard

    heard: list[str] = []
    with xnano.new(width=8, height=1) as canvas:
        canvas.hook(on="keyboard.binding == 'ctrl+s'")(
            lambda context: heard.append('string')
        )
        canvas.hook(on=keyboard.binding == 'ctrl+s')(
            lambda context: heard.append('expression')
        )
        canvas.push(Event.key_press('ctrl+s'))
        canvas.deliver_events()
        with pytest.raises(
            ValueError, match='members of keyboard are key, kind, binding'
        ):
            canvas.hook(on="keyboard.chord == 'ctrl+s'")
    assert sorted(heard) == ['expression', 'string']
