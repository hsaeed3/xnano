"""Symbolic expressions, predicates and composable operations."""

from __future__ import annotations

import pytest
from helpers import (
    Bounds,
    DeviceWidth,
    Focused,
    Frame,
    Height,
    Position,
    TimeElapsed,
    Width,
    X,
    Y,
)
from helpers import Size as SizeReference

from xnano_core._xnano_core import (
    Buffer,
    Conditional,
    Expression,
    Move,
    NumericValue,
    Operation,
    Place,
    Point,
    Predicate,
    Property,
    Resize,
    RuntimeRequiredError,
    SequenceOperation,
    SetValue,
    Size,
    UnsupportedOperationError,
    Write,
)
from xnano_core._xnano_core._core_types import EvaluationContext


class Extension:
    """A named registry extension, as ``Registry.install`` expects."""

    def __init__(self, name, register):
        self.name = name
        self.register = register


def test_references_read_geometry():
    buffer = Buffer(width=8, height=3, x=2, y=4)
    assert buffer.inspect(Width) == 8
    assert buffer.inspect(Height) == 3
    assert buffer.inspect(X) == 2 and buffer.inspect(Y) == 4
    assert buffer.inspect(Position) == Point(2, 4)
    assert buffer.inspect(SizeReference).width == 8
    assert buffer.inspect(Bounds).height == 3


def test_arithmetic_and_comparisons_build_expressions():
    buffer = Buffer(width=8, height=3)
    assert isinstance(Width > 4, Predicate)
    assert buffer.inspect(Width + 2) == 10
    assert buffer.inspect(Width / 2) == 4.0
    assert buffer.inspect(Width * Height) == 24
    assert buffer.inspect(10 - Width) == 2
    assert buffer.inspect(-Width) == -8
    assert buffer.inspect(Width % 3) == 2
    assert buffer.inspect((Width > 4) & (Height < 5)) is True
    assert buffer.inspect(~(Width > 4)) is False
    assert buffer.inspect((Width < 4) | (Height > 1)) is True
    assert buffer.inspect(Width.equals(8)) is True
    assert buffer.inspect(Width.not_equals(8)) is False
    assert buffer.inspect(Width == 8) is True
    assert buffer.inspect(Width != 8) is False
    assert isinstance(Width == 8, Predicate)


def test_expression_values_are_hashable_by_identity():
    assert len({Width, Height, Width}) == 2
    table = {Width: 'width'}
    assert table[Width] == 'width'
    assert Width in {Width}
    assert (Width == 8) is not (Width == 8)
    assert hash(Width) == hash(Width)


def test_comparing_an_expression_with_a_foreign_object_falls_back_to_identity():
    sentinel = object()
    assert (Width == sentinel) is False
    assert (Width != sentinel) is True
    assert (Width + 1 == sentinel) is False
    assert (Width + 1 != sentinel) is True
    assert sentinel not in [Width, Height]
    assert (Width == 8) is not False


def test_expressions_have_no_truth_value():
    with pytest.raises(TypeError, match='no truth value'):
        bool(Width > 4)
    with pytest.raises(TypeError, match='no truth value'):
        _ = (Width > 4) and (Height > 1)


def test_list_membership_of_expressions_explains_the_identity_lookup():
    items = [Width, Height]
    with pytest.raises(TypeError, match=r'==, using `in` or calling \.index\(\)'):
        _ = Height in items
    with pytest.raises(TypeError, match='identity'):
        items.index(Height)
    assert any(item is Height for item in items)
    assert Height in set(items)


def test_division_by_zero_and_type_errors_are_explained():
    buffer = Buffer(width=8, height=3)
    with pytest.raises(ZeroDivisionError, match='divisor'):
        buffer.inspect(Width / 0)
    with pytest.raises(TypeError, match='numbers'):
        buffer.inspect(Width + 'a')  # type: ignore[operator]


def test_properties_assign_when_called():
    buffer = Buffer(width=4, height=2)
    buffer.update(Width(10), X(3), Y(1))
    assert (buffer.width, buffer.x, buffer.y) == (10, 3, 1)
    buffer.update(Position(Point(7, 8)), Height(5))
    assert (buffer.x, buffer.y, buffer.height) == (7, 8, 5)
    buffer.update(SizeReference(Size(3, 2)))
    assert (buffer.width, buffer.height) == (3, 2)
    buffer.update(Width(Width + 1))
    assert buffer.width == 4
    with pytest.raises(TypeError, match='not callable'):
        TimeElapsed(1)  # type: ignore[operator]


def test_assigning_the_wrong_type_is_explained():
    buffer = Buffer(width=4, height=2)
    with pytest.raises(TypeError, match='whole number'):
        buffer.update(Width(1.5))
    with pytest.raises(TypeError, match='Point'):
        buffer.update(Position(3))


def test_operations_compose():
    buffer = Buffer(width=6, height=1)
    combined = Write('ab').then(Write('c', x=2)).then(Move(1, 0))
    assert isinstance(combined, SequenceOperation)
    buffer.update(combined)
    assert buffer.text == 'abc' and buffer.x == 1
    guarded = Place(0, 0).when(Width > 100)
    assert isinstance(guarded, Conditional)
    buffer.update(guarded)
    assert buffer.x == 1
    buffer.update(Conditional(Width > 1, Place(5, 5), otherwise=Place(9, 9)))
    assert (buffer.x, buffer.y) == (5, 5)
    buffer.update(Conditional(Width > 100, Place(5, 5), otherwise=Place(9, 9)))
    assert (buffer.x, buffer.y) == (9, 9)
    assert isinstance(SetValue(Width, 3), Operation)


def test_update_accepts_operations_only():
    buffer = Buffer(width=2, height=1)
    with pytest.raises(TypeError, match='operations only'):
        buffer.update(Width)
    with pytest.raises(TypeError, match='Operation'):
        buffer.update('write')


def test_runtime_references_need_a_runtime_offline():
    buffer = Buffer(width=2, height=1)
    for reference in (TimeElapsed, Frame, Focused, DeviceWidth):
        with pytest.raises(RuntimeRequiredError, match='needs a runtime'):
            buffer.inspect(reference)


def test_runtime_references_read_the_mounted_runtime(runtime):
    buffer = Buffer(width=2, height=1)
    runtime.mount(buffer)
    runtime.advance_clock(1500)
    runtime.step()
    assert buffer.inspect(TimeElapsed) == 1.5
    assert buffer.inspect(DeviceWidth) == 40
    assert buffer.inspect(Frame) >= 1
    assert buffer.inspect(Focused) is False


def test_expressions_evaluate_against_a_context():
    buffer = Buffer(width=5, height=1)
    context = EvaluationContext(buffer=buffer)
    assert (Width + 1).evaluate(context) == 6
    Write('hi').evaluate(context)
    assert buffer.text == 'hi'
    assert context.device is None and context.clock is None and context.runtime is None


def test_regions_are_their_own_targets_for_expressions():
    buffer = Buffer(width=6, height=3)
    region = buffer[1:4, 0:2]
    assert region.inspect(Width) == 3
    with pytest.raises(UnsupportedOperationError, match='region cannot be resized'):
        region.update(Resize(2, 2))


def test_bare_expressions_hold_nothing():
    with pytest.raises(TypeError, match='holds nothing'):
        Expression().evaluate(EvaluationContext(buffer=Buffer()))
    assert isinstance(Width, NumericValue) and isinstance(Position, Property)


def test_python_defined_operations_resolve_through_the_registry():
    from xnano_core._xnano_core._core_types import Registry

    class Shout(Operation):
        def __init__(self, text: str) -> None:
            self.text = text

    def apply(context, operation):
        context.target.update(Write(operation.text.upper()))

    plugin = Extension('shout', lambda registry: registry.register(Shout, apply))

    buffer = Buffer(width=8, height=1, registry=Registry())
    with pytest.raises(UnsupportedOperationError, match='cannot apply a Shout'):
        buffer.update(Shout('hi'))
    assert not buffer.supports(Shout)
    buffer.registry.install(plugin)
    assert buffer.supports(Shout)
    buffer.update(Shout('hi'))
    assert buffer.text == 'HI'
    buffer.registry.install(plugin)
    assert buffer.supports(Write)


def test_runtime_only_registrations_need_a_runtime(runtime):
    from xnano_core._xnano_core._core_types import Registry

    class Beep(Operation):
        pass

    calls = []
    plugin = Extension(
        'beep',
        lambda registry: registry.register(
            Beep,
            lambda context, operation: calls.append(context.runtime),
            requires_runtime=True,
        ),
    )
    registry = Registry()
    registry.install(plugin)
    offline = Buffer(width=2, height=1, registry=registry)
    with pytest.raises(RuntimeRequiredError, match='active runtime'):
        offline.update(Beep())
    mounted = Buffer(width=2, height=1, registry=registry)
    runtime.mount(mounted)
    mounted.update(Beep())
    assert calls == [runtime]
