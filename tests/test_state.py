"""Tests for the convenience State wrapper."""

from __future__ import annotations

import pytest
from helpers import assign_attr
from pydantic_core import ValidationError

from xnano.state import State


def test_state_accepts_keyword_initialization() -> None:
    state = State(name="John", age=30)
    assert state.name == "John"
    assert state.age == 30


def test_state_allows_dynamic_attributes() -> None:
    state = State(name="John")
    state.address = "123 Main St"
    assert state.address == "123 Main St"


def test_state_subclass_validates_on_init() -> None:
    class MyState(State):
        name: str

    state = MyState(name="John")
    assert state.name == "John"

    with pytest.raises(ValidationError):
        MyState(name=123)


def test_state_subclass_validates_on_setattr() -> None:
    class MyState(State):
        count: int

    state = MyState(count=1)
    state.count = 2
    assert state.count == 2

    with pytest.raises(ValidationError):
        assign_attr(state, "count", "two")


def test_state_subclass_allows_unannotated_dynamic_attributes() -> None:
    class MyState(State):
        name: str

    state = MyState(name="John")
    state.note = "optional"
    assert state.note == "optional"


def test_state_repr_lists_public_attributes() -> None:
    state = State(name="John", age=30)
    assert repr(state) == "State(name='John', age=30)"
