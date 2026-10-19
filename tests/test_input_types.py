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
import xnano.expressions
import xnano_core
from xnano.events import Event
from xnano.types import HeldMouseButtonName, KeyName


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
        held = canvas.input
        assert_type(held.held_keys, frozenset[KeyName | HeldMouseButtonName])
        assert_type(held.is_down('space'), bool)
        assert_type(held.is_down(('a', 'mouse_left')), bool)
        assert_type(held.direction(), tuple[int, int])
        assert held.is_down('space') is False


def test_the_deprecated_chord_property_warns_and_returns_the_binding():
    import warnings

    import pytest

    seen: list[object] = []

    with xnano.new(width=8, height=1) as canvas:

        @canvas.hook(on='key')
        def listen(context: xnano.Context) -> None:
            with pytest.warns(
                DeprecationWarning, match='removed in xnano 2.1.0.*binding'
            ):
                seen.append(context.keyboard.chord)
            seen.append(context.keyboard.binding)

        canvas.push(Event.key_press('ctrl+s'))
        canvas.deliver_events()

    assert seen == ['ctrl+s', 'ctrl+s']
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        assert xnano.expressions.KeyboardBinding is not None


def test_the_deprecated_chord_names_in_conditions_and_expressions_still_work():
    import pytest

    heard: list[str] = []
    with xnano.new(width=8, height=1) as canvas:
        with pytest.warns(DeprecationWarning, match='keyboard.binding'):
            canvas.hook(on='key', when="keyboard.chord == 'ctrl+s'")(
                lambda context: heard.append('old')
            )
        canvas.hook(on='key', when="keyboard.binding == 'ctrl+s'")(
            lambda context: heard.append('new')
        )
        canvas.push(Event.key_press('ctrl+s'))
        canvas.deliver_events()
    assert sorted(heard) == ['new', 'old']

    with pytest.warns(DeprecationWarning, match='KeyboardBinding'):
        old = xnano.expressions.KeyboardChord
    assert old is xnano.expressions.KeyboardBinding
