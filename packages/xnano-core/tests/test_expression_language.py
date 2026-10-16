"""The expression language: numeric functions, choices, components and new references."""

from __future__ import annotations

import math

import pytest

from xnano_core._xnano_core import (
    Bounds,
    Buffer,
    BufferRegion,
    BufferScope,
    Event,
    Expression,
    Height,
    IsVisible,
    KeyboardChord,
    KeyboardKey,
    KeyboardKind,
    KeyboardScope,
    Layer,
    MouseButtonValue,
    MouseIsDown,
    MouseKind,
    MousePosition,
    MouseScope,
    NumericValue,
    ParentHeight,
    ParentSize,
    ParentWidth,
    Place,
    Point,
    PointerPosition,
    Position,
    Predicate,
    Rectangle,
    RuntimeRequiredError,
    ScreenBounds,
    ScreenPosition,
    ScrollScope,
    ScrollX,
    ScrollY,
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


def mounted_buffer(runtime, **keywords):
    buffer = Buffer(**keywords)
    runtime.mount(buffer)
    return buffer


def send(runtime, *events):
    for event in events:
        runtime.inject(event)
        runtime.step()


def test_input_references_are_null_until_the_input_was_seen(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2)
    assert buffer.inspect(KeyboardKey) is None
    assert buffer.inspect(KeyboardKind) is None
    assert buffer.inspect(KeyboardChord) is None
    assert buffer.inspect(MouseButtonValue) is None
    assert buffer.inspect(MouseKind) is None
    assert buffer.inspect(MousePosition) is None
    assert buffer.inspect(MouseIsDown) is False
    assert buffer.inspect(ScrollX) == 0 and buffer.inspect(ScrollY) == 0
    assert buffer.inspect(BufferRegion) == Rectangle(0, 0, 4, 2)


def test_input_references_read_the_latest_event(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2)
    send(runtime, Event.key_press('ctrl+s'))
    assert buffer.inspect(KeyboardKey) == 's'
    assert buffer.inspect(KeyboardKind) == 'press'
    assert buffer.inspect(KeyboardChord) == 'ctrl+s'
    send(runtime, Event.mouse_event(column=7, row=2, kind='press', button='right'))
    assert buffer.inspect(KeyboardKey) is None
    assert buffer.inspect(MouseButtonValue) == 'right'
    assert buffer.inspect(MouseKind) == 'press'
    assert buffer.inspect(MousePosition) == Point(7, 2)
    assert buffer.inspect(MouseIsDown) is True
    send(
        runtime,
        Event.mouse_event(column=7, row=2, kind='scroll', scroll_x=1, scroll_y=-1),
    )
    assert buffer.inspect(ScrollX) == 1 and buffer.inspect(ScrollY) == -1
    assert buffer.inspect(MousePosition) is None, 'a wheel report has no button cell'
    assert buffer.inspect(MouseIsDown) is True
    runtime.step()
    assert buffer.inspect(ScrollY) == 0


def test_the_region_is_the_buffer_on_the_screen(runtime):
    parent = Buffer(width=20, height=6, x=3, y=1)
    child = Buffer(width=4, height=2, x=2, y=1)
    parent.attach(child)
    runtime.mount(parent)
    assert (
        child.inspect(BufferRegion)
        == child.inspect(ScreenBounds)
        == Rectangle(5, 2, 4, 2)
    )
    assert child.inspect(BufferRegion) != child.inspect(Bounds)
    assert BufferScope.region is BufferRegion


def test_comparing_input_that_was_never_seen_is_false_not_an_error(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2)
    for condition in (
        KeyboardKey == 'q',
        KeyboardKey != 'q',
        MouseKind == 'press',
        MouseKind != 'press',
        MousePosition == Point(0, 0),
        MousePosition.x > 0,
        MousePosition.x <= 100,
        MousePosition.x + 1 > 0,
        -MousePosition.x > -5,
    ):
        assert buffer.inspect(condition) is False, condition
    assert buffer.inspect(MousePosition.x) is None
    assert buffer.inspect(MousePosition.x * 2) is None


def test_values_that_were_seen_compare_normally(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2)
    send(runtime, Event.key_press('q'))
    assert buffer.inspect(KeyboardKey == 'q') is True
    assert buffer.inspect(KeyboardKey != 'q') is False
    assert buffer.inspect(KeyboardKey != 'w') is True
    assert buffer.inspect(KeyboardKey.equals('q')) is True
    assert buffer.inspect(KeyboardKey.not_equals('q')) is False
    assert buffer.inspect((KeyboardKey == 'q') & (KeyboardKind == 'press')) is True


def test_a_rectangle_contains_a_point_and_nothing_seen_is_not_contained(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2, x=1, y=1)
    inside = BufferRegion.contains(MousePosition)
    assert isinstance(inside, Expression)
    assert buffer.inspect(inside) is False, 'no pointer has been seen'
    send(runtime, Event.mouse_event(column=1, row=1, kind='move'))
    assert buffer.inspect(inside) is True
    send(runtime, Event.mouse_event(column=5, row=1, kind='move'))
    assert buffer.inspect(inside) is False, 'the right edge is outside'
    send(runtime, Event.mouse_event(column=4, row=2, kind='move'))
    assert buffer.inspect(inside) is True
    assert buffer.inspect(BufferRegion.contains(Point(2, 2))) is True
    assert buffer.inspect(Bounds.contains(Point(9, 9))) is False
    with pytest.raises(TypeError, match='contain'):
        buffer.inspect(BufferRegion.contains(3))


def test_the_event_position_is_null_on_a_key_press_but_the_pointer_is_held(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2, x=1, y=1)
    heard = []
    buffer.add_hook(
        lambda context: heard.append(context.event.kind),
        events=('key', 'mouse'),
        condition=BufferRegion.contains(MousePosition),
    )
    send(runtime, Event.mouse_event(column=2, row=2, kind='move'))
    assert heard == ['mouse']
    send(runtime, Event.key_press('a'))
    assert heard == ['mouse'], (
        'the pointer rests inside, but the key is not a mouse event'
    )
    assert buffer.inspect(PointerPosition) == Point(2, 2)
    assert buffer.inspect(BufferRegion.contains(PointerPosition)) is True
    assert buffer.inspect(BufferRegion.contains(MousePosition)) is False
    send(runtime, Event.mouse_event(column=8, row=2, kind='move'))
    assert heard == ['mouse']


def test_comparing_a_condition_with_a_bool_builds_a_condition(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2)
    assert isinstance(MouseIsDown == True, Predicate)
    assert isinstance(MouseScope.is_down != False, Predicate)
    assert buffer.inspect(MouseIsDown == False) is True
    assert buffer.inspect(MouseIsDown == True) is False
    assert buffer.inspect(MouseIsDown != True) is True
    send(runtime, Event.mouse_event(column=1, row=1, kind='press', button='left'))
    assert buffer.inspect(MouseIsDown == True) is True
    assert buffer.inspect(MouseIsDown != False) is True
    assert hash(MouseIsDown) == hash(MouseIsDown)
    assert len({MouseIsDown, MouseScope.is_down}) == 1


def test_comparing_an_expression_with_none_explains_that_it_never_holds(runtime):
    mounted_buffer(runtime, width=4, height=2)
    with pytest.raises(TypeError, match='always false'):
        _ = KeyboardKey == None
    with pytest.raises(TypeError, match='on='):
        _ = KeyboardKey != None
    with pytest.raises(TypeError, match='always false'):
        _ = MouseIsDown == None


def test_asking_a_value_that_is_not_a_rectangle_names_both_types(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2)
    with pytest.raises(TypeError, match='whether an int contains a Point'):
        buffer.inspect(Width.contains(Point(1, 1)))
    with pytest.raises(TypeError, match='whether a Rectangle contains an int'):
        buffer.inspect(BufferRegion.contains(3))


def test_mouse_is_down_combines_with_other_conditions(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2, x=1, y=1)
    assert isinstance(MouseIsDown, Predicate)
    assert isinstance(MouseScope.is_down, Predicate)
    pressed_inside = MouseScope.is_down & BufferRegion.contains(MousePosition)
    released = ~MouseScope.is_down
    either = MouseScope.is_down | (KeyboardKey == 'q')
    assert buffer.inspect(pressed_inside) is False
    assert buffer.inspect(released) is True
    assert buffer.inspect(either) is False
    send(runtime, Event.mouse_event(column=2, row=1, kind='press', button='left'))
    assert buffer.inspect(pressed_inside) is True
    assert buffer.inspect(released) is False
    assert buffer.inspect(either) is True
    send(runtime, Event.mouse_event(column=9, row=1, kind='drag', button='left'))
    assert buffer.inspect(pressed_inside) is False
    send(runtime, Event.mouse_event(column=2, row=1, kind='release', button='left'))
    assert buffer.inspect(released) is True


def test_a_hook_condition_can_combine_the_held_button_with_the_region(runtime):
    buffer = mounted_buffer(runtime, width=4, height=2, x=1, y=1)
    drags = []
    moves = []
    buffer.add_hook(
        lambda context: drags.append(context.event.mouse.position),
        events=('mouse',),
        condition=MouseScope.is_down & BufferRegion.contains(MousePosition),
    )
    buffer.add_hook(
        lambda context: moves.append(context.event.mouse.position),
        events=('mouse',),
        condition=~MouseScope.is_down,
    )
    send(runtime, Event.mouse_event(column=2, row=1, kind='move'))
    assert drags == [] and moves == [Point(2, 1)]
    send(runtime, Event.mouse_event(column=2, row=1, kind='press', button='left'))
    send(runtime, Event.mouse_event(column=3, row=2, kind='drag', button='left'))
    send(runtime, Event.mouse_event(column=9, row=2, kind='drag', button='left'))
    assert drags == [Point(2, 1), Point(3, 2)]
    send(runtime, Event.mouse_event(column=3, row=2, kind='release', button='left'))
    assert len(moves) == 2


def test_scopes_provide_the_new_references():
    assert KeyboardScope.key is KeyboardKey
    assert KeyboardScope.kind is KeyboardKind
    assert KeyboardScope.chord is KeyboardChord
    assert MouseScope.position is MousePosition
    assert MouseScope.button is MouseButtonValue
    assert MouseScope.kind is MouseKind
    assert MouseScope.is_down is MouseIsDown
    assert ScrollScope.x is ScrollX and ScrollScope.y is ScrollY
    with pytest.raises(AttributeError, match='chord'):
        KeyboardScope.letter  # noqa: B018
    with pytest.raises(AttributeError, match='is_down'):
        MouseScope.held  # noqa: B018
    with pytest.raises(AttributeError, match='y'):
        ScrollScope.z  # noqa: B018


def test_an_input_condition_with_a_wheel_hook_filters_natively(runtime):
    buffer = mounted_buffer(runtime, width=10, height=3)
    steps = []
    buffer.add_hook(
        lambda context: steps.append(context.event.mouse.scroll_y),
        events=('mouse',),
        condition=ScrollScope.y < 0,
    )
    send(
        runtime,
        Event.mouse_event(column=1, row=1, kind='scroll', scroll_y=1),
        Event.mouse_event(column=1, row=1, kind='scroll', scroll_y=-1),
        Event.mouse_event(column=1, row=1, kind='move'),
    )
    assert steps == [-1]
