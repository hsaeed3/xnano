"""The expression language: numeric functions, choices, components and new references."""

from __future__ import annotations

import math

import pytest

from xnano_core._xnano_core import (
    Bounds,
    Buffer,
    Event,
    Height,
    IsVisible,
    Layer,
    NumericValue,
    ParentHeight,
    ParentSize,
    ParentWidth,
    Place,
    Point,
    PointerPosition,
    Position,
    Rectangle,
    RuntimeRequiredError,
    ScreenBounds,
    ScreenPosition,
    Size,
    TerminalStateSchema,
    TerminalStateStore,
    Width,
    X,
    Y,
)


def evaluate(expression, buffer=None):
    return (buffer or Buffer(width=7, height=3, x=2, y=1)).inspect(expression)


def test_floor_division_follows_python():
    for numerator in (7, -7, 0):
        for divisor in (2, -2, 3, -3):
            buffer = Buffer(width=1, height=1, x=numerator)
            assert buffer.inspect(X // divisor) == numerator // divisor
    assert Buffer(width=4, height=1).inspect(-9 // Width) == -9 // 4


def test_floor_division_of_floats_and_by_zero():
    assert evaluate(Width // 2.0) == 3.0
    with pytest.raises(ZeroDivisionError):
        evaluate(Width // 0)


def test_power_keeps_integers_and_falls_back_to_floats():
    assert evaluate(Width**2) == 49
    assert evaluate(2**Height) == 8
    assert evaluate(Width**-1) == pytest.approx(1 / 7)
    assert evaluate(Width**0.5) == pytest.approx(math.sqrt(7))
    with pytest.raises(TypeError, match='modulo'):
        pow(Width, 2, 5)


def test_reflected_division_and_remainder():
    assert evaluate(21 / Width) == 3.0
    assert evaluate(10 % Height) == 1


def test_rounding_functions():
    assert evaluate(abs(-Width)) == 7
    assert evaluate(math.floor(Width / 2)) == 3
    assert evaluate(math.ceil(Width / 2)) == 4
    assert evaluate(round(Width / 2)) == 4
    assert evaluate(round(Width - 4.5)) == 3
    with pytest.raises(TypeError, match='digits'):
        round(Width, 2)


def test_minimum_maximum_and_clamp():
    assert evaluate(Width.minimum(3)) == 3
    assert evaluate(Width.maximum(30)) == 30
    assert evaluate(Width.clamp(0, 5)) == 5
    assert evaluate(Width.clamp(10, 20)) == 10
    assert evaluate(Width.clamp(0.5, 8.5)) == 7
    assert evaluate(Width.minimum(Height)) == 3
    with pytest.raises(TypeError, match='lowest'):
        evaluate(Width.clamp(9, 1))


def test_functions_only_take_numbers():
    with pytest.raises(TypeError, match='numbers'):
        evaluate(Width.minimum(Position))


def test_choose_selects_a_branch_and_stays_numeric():
    condition = Width > 5
    choice = condition.choose(10, 20)
    assert isinstance(choice, NumericValue)
    assert evaluate(choice + 1) == 11
    assert evaluate((Width < 5).choose(Width, Height)) == 3
    assert evaluate((Width > 5).choose('wide', 'narrow')) == 'wide'


def test_choose_follows_the_buffer():
    expression = (Width > 0).choose(1, 2)
    assert Buffer(width=1, height=1).inspect(expression) == 1
    assert Buffer(width=0, height=1).inspect(expression) == 2


def test_components_of_points_sizes_and_rectangles():
    buffer = Buffer(width=7, height=3, x=2, y=1)
    assert buffer.inspect(Position.x) == 2
    assert buffer.inspect(Position.y) == 1
    assert buffer.inspect(Bounds.width) == 7
    assert buffer.inspect(Bounds.height) == 3
    assert buffer.inspect(Bounds.right) == 9
    assert buffer.inspect(Bounds.bottom) == 4
    assert buffer.inspect(Bounds.x + Bounds.right) == 11


def test_components_reject_other_values():
    with pytest.raises(TypeError, match='has no'):
        evaluate(Position.width)
    with pytest.raises(TypeError, match='has no'):
        evaluate(Bounds.x.x)


def test_parent_references_read_the_parent():
    parent = Buffer(width=30, height=10)
    child = Buffer(width=4, height=2, x=3, y=1)
    parent.attach(child)
    assert child.inspect(ParentWidth) == 30
    assert child.inspect(ParentHeight) == 10
    assert child.inspect(ParentSize) == Size(30, 10)
    parent.resize(40, 12)
    assert child.inspect(ParentHeight) == 12


def test_parent_references_explain_a_missing_parent():
    with pytest.raises(TypeError, match='parent buffer'):
        Buffer(width=2, height=2).inspect(ParentWidth)


def test_a_region_is_inside_its_buffer():
    buffer = Buffer(width=20, height=8)
    region = buffer[2:6, 1:3]
    assert region.inspect(ParentSize) == Size(20, 8)


def test_screen_references_add_every_parent_offset():
    root = Buffer(width=40, height=20, x=5, y=2)
    middle = Buffer(width=20, height=10, x=3, y=1)
    leaf = Buffer(width=4, height=2, x=1, y=1)
    root.attach(middle)
    middle.attach(leaf)
    assert leaf.inspect(ScreenPosition) == Point(9, 4)
    assert leaf.inspect(ScreenBounds) == Rectangle(9, 4, 4, 2)
    region = leaf[1:3, 0:1]
    assert region.inspect(ScreenPosition) == Point(10, 4)
    assert region.inspect(ScreenBounds) == Rectangle(10, 4, 2, 1)


def test_layer_and_visibility_read_and_assign():
    parent = Buffer(width=4, height=2)
    child = Buffer(width=2, height=1)
    parent.attach(child)
    assert child.inspect(Layer) == 0
    assert child.inspect(IsVisible) is True
    child.update(Layer(3), IsVisible(False))
    assert child.layer == 3 and child.is_visible is False
    assert child.inspect(Layer + 1) == 4
    with pytest.raises(TypeError, match='not callable'):
        ParentWidth(3)
    with pytest.raises(TypeError, match='bool'):
        child.update(IsVisible(1))


def test_pointer_position_needs_a_runtime_and_follows_the_mouse(runtime):
    with pytest.raises(RuntimeRequiredError, match='runtime'):
        Buffer(width=2, height=2).inspect(PointerPosition)
    buffer = Buffer()
    runtime.mount(buffer, geometry='inherit')
    assert buffer.inspect(PointerPosition) is None
    runtime.dispatch(Event.mouse_event(column=6, row=3, kind='move'))
    runtime.step()
    assert buffer.inspect(PointerPosition) == Point(6, 3)
    assert buffer.inspect(PointerPosition.x * 2) == 12


def test_a_slider_thumb_follows_a_state_value_using_only_expressions():
    """The thumb's row is a function of a number and the track it sits in."""
    store = TerminalStateStore({'volume': 50}, schema=TerminalStateSchema.compile({}))
    volume = store.reference()['volume'].number
    track = Buffer(width=3, height=11)
    thumb = Buffer('███')
    track.attach(thumb)
    free_rows = ParentHeight - Height
    thumb_row = round((100 - volume.clamp(0, 100)) / 100 * free_rows)
    thumb.update(Place(0, 0))
    assert thumb.inspect(thumb_row) == 5
    reference = store.reference()['volume']
    for value, row in ((0, 10), (100, 0), (25, 8), (250, 0)):
        reference.set(value)
        assert thumb.inspect(thumb_row) == row


def test_the_slider_thumb_can_be_moved_by_an_assignment():
    track = Buffer(width=3, height=11)
    thumb = Buffer('███')
    track.attach(thumb)
    thumb.update(Y(ParentHeight - Height))
    assert thumb.y == 10
    thumb.update(Y((ParentHeight - Height) // 2))
    assert thumb.y == 5


def test_a_runtime_provides_a_named_external_value():
    from xnano_core._xnano_core import Buffer, Runtime, _external

    level = _external('test.level', True)
    with Runtime.offscreen(width=4, height=1) as runtime:
        buffer = Buffer.with_text('x')
        runtime.mount(buffer)
        runtime.provide('test.level', lambda: 3)
        assert buffer.inspect(level + 1) == 4
