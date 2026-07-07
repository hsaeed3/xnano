"""Tests for keyboard binding resolution."""

from __future__ import annotations

import dataclasses
from typing import cast

from xnano_core.rust import native

from xnano.beta.utils.events import (
    get_keyboard_binding_tuple_from_native_event,
)


@dataclasses.dataclass
class _StubModifiers:
    _control: bool = False
    _shift: bool = False
    _alt: bool = False

    def control(self) -> bool:
        return self._control

    def shift(self) -> bool:
        return self._shift

    def alt(self) -> bool:
        return self._alt


@dataclasses.dataclass
class _StubCodeName:
    value: int

    def __int__(self) -> int:
        return self.value


@dataclasses.dataclass
class _StubKeyEvent:
    code_name: _StubCodeName
    modifiers: _StubModifiers
    _char: str | None = None
    _function_number: int | None = None

    def char(self) -> str | None:
        return self._char

    def char_value(self) -> str | None:
        return self._char

    def function_number(self) -> int | None:
        return self._function_number

    def is_enter(self) -> bool:
        return False

    def is_esc(self) -> bool:
        return False

    def is_backspace(self) -> bool:
        return False

    def is_back_tab(self) -> bool:
        return False

    def is_tab(self) -> bool:
        return False

    def is_up(self) -> bool:
        return False

    def is_down(self) -> bool:
        return False

    def is_left(self) -> bool:
        return False

    def is_right(self) -> bool:
        return False

    def is_home(self) -> bool:
        return False

    def is_end(self) -> bool:
        return False

    def is_page_up(self) -> bool:
        return False

    def is_page_down(self) -> bool:
        return False

    def is_insert(self) -> bool:
        return False

    def is_delete(self) -> bool:
        return False

    def is_null(self) -> bool:
        return False

    def is_caps_lock(self) -> bool:
        return False

    def is_scroll_lock(self) -> bool:
        return False

    def is_num_lock(self) -> bool:
        return False

    def is_function_key(self) -> bool:
        return False


def test_ctrl_c_control_character_resolves_to_binding() -> None:
    event = _StubKeyEvent(
        code_name=_StubCodeName(1),
        modifiers=_StubModifiers(),
        _char="\x03",
    )
    modifiers, key = get_keyboard_binding_tuple_from_native_event(
        cast(native.KeyEvent, event)
    )
    assert modifiers == ["ctrl"]
    assert key == "c"


def test_ctrl_c_with_modifier_and_letter_resolves_to_binding() -> None:
    event = _StubKeyEvent(
        code_name=_StubCodeName(2),
        modifiers=_StubModifiers(_control=True),
        _char="c",
    )
    modifiers, key = get_keyboard_binding_tuple_from_native_event(
        cast(native.KeyEvent, event)
    )
    assert modifiers == ["ctrl"]
    assert key == "c"
