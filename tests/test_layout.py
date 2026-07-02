"""Tests for xnano.layout module - comprehensive layout functionality."""

import pytest
from xnano.layout import (
    Margin,
    Offset,
    Size,
    Position,
    Rectangle,
    Rect,
    Constraint,
    Layout,
    Direction,
    Alignment,
    Flex,
)


class TestMargin:
    """Tests for Margin class."""

    def test_margin_default(self):
        m = Margin()
        assert m.horizontal == 0
        assert m.vertical == 0

    def test_margin_custom(self):
        m = Margin(horizontal=5, vertical=10)
        assert m.horizontal == 5
        assert m.vertical == 10

    def test_margin_negative(self):
        m = Margin(horizontal=-1, vertical=-2)
        assert m.horizontal == -1
        assert m.vertical == -2

    def test_margin_to_core(self):
        m = Margin(horizontal=3, vertical=2)
        core_m = m._to_core()
        assert core_m is not None


class TestOffset:
    """Tests for Offset class."""

    def test_offset_default(self):
        o = Offset()
        assert o.x == 0
        assert o.y == 0

    def test_offset_positive(self):
        o = Offset(x=10, y=20)
        assert o.x == 10
        assert o.y == 20

    def test_offset_negative(self):
        o = Offset(x=-5, y=-10)
        assert o.x == -5
        assert o.y == -10

    def test_offset_to_core(self):
        o = Offset(x=3, y=4)
        core_o = o._to_core()
        assert core_o is not None

    def test_offset_get_core(self):
        o = Offset(x=3, y=4)
        core_o = o.get_core_offset()
        assert core_o is not None


class TestSize:
    """Tests for Size class."""

    def test_size_creation(self):
        s = Size(width=80, height=24)
        assert s.width == 80
        assert s.height == 24

    def test_size_to_core(self):
        s = Size(width=80, height=24)
        core_s = s._to_core()
        assert core_s is not None

    def test_size_get_core(self):
        s = Size(width=80, height=24)
        core_s = s.get_core_size()
        assert core_s is not None


class TestPosition:
    """Tests for Position class."""

    def test_position_origin(self):
        p = Position.origin()
        assert p.x == 0
        assert p.y == 0

    def test_position_custom(self):
        p = Position(x=10, y=20)
        assert p.x == 10
        assert p.y == 20

    def test_position_to_core(self):
        p = Position(x=10, y=20)
        core_p = p._to_core()
        assert core_p is not None

    def test_position_get_core(self):
        p = Position(x=10, y=20)
        core_p = p.get_core_position()
        assert core_p is not None


class TestRectangle:
    """Tests for Rectangle class."""

    def test_rectangle_zero(self):
        r = Rectangle.zero()
        assert r.x == 0
        assert r.y == 0
        assert r.width == 0
        assert r.height == 0

    def test_rectangle_custom(self):
        r = Rectangle(x=10, y=20, width=100, height=50)
        assert r.x == 10
        assert r.y == 20
        assert r.width == 100
        assert r.height == 50

    def test_rectangle_area(self):
        r = Rectangle(x=0, y=0, width=10, height=5)
        assert r.area() == 50

    def test_rectangle_area_zero(self):
        r = Rectangle.zero()
        assert r.area() == 0

    def test_rectangle_is_empty(self):
        r = Rectangle(x=0, y=0, width=10, height=5)
        assert not r.is_empty()
        r2 = Rectangle.zero()
        assert r2.is_empty()

    def test_rectangle_left(self):
        r = Rectangle(x=10, y=20, width=50, height=10)
        assert r.left() == 10

    def test_rectangle_right(self):
        r = Rectangle(x=10, y=20, width=50, height=10)
        assert r.right() == 60

    def test_rectangle_top(self):
        r = Rectangle(x=10, y=20, width=50, height=10)
        assert r.top() == 20

    def test_rectangle_bottom(self):
        r = Rectangle(x=10, y=20, width=50, height=10)
        assert r.bottom() == 30

    def test_rectangle_inner(self):
        r = Rectangle(x=0, y=0, width=20, height=10)
        m = Margin(horizontal=2, vertical=1)
        inner = r.inner(m)
        assert inner.x == 2
        assert inner.y == 1
        assert inner.width == 16
        assert inner.height == 8

    def test_rectangle_offset(self):
        r = Rectangle(x=10, y=20, width=50, height=10)
        o = Offset(x=5, y=-5)
        offset_r = r.offset(o)
        assert offset_r.x == 15
        assert offset_r.y == 15

    def test_rectangle_union(self):
        r1 = Rectangle(x=0, y=0, width=10, height=10)
        r2 = Rectangle(x=5, y=5, width=10, height=10)
        union = r1.union(r2)
        assert union is not None

    def test_rectangle_intersection(self):
        r1 = Rectangle(x=0, y=0, width=10, height=10)
        r2 = Rectangle(x=5, y=5, width=10, height=10)
        intersection = r1.intersection(r2)
        assert intersection is not None

    def test_rectangle_intersects_true(self):
        r1 = Rectangle(x=0, y=0, width=10, height=10)
        r2 = Rectangle(x=5, y=5, width=10, height=10)
        assert r1.intersects(r2)

    def test_rectangle_intersects_false(self):
        r1 = Rectangle(x=0, y=0, width=10, height=10)
        r2 = Rectangle(x=20, y=20, width=10, height=10)
        assert not r1.intersects(r2)

    def test_rectangle_contains_true(self):
        r = Rectangle(x=0, y=0, width=10, height=10)
        assert r.contains(5, 5)

    def test_rectangle_contains_false(self):
        r = Rectangle(x=0, y=0, width=10, height=10)
        assert not r.contains(15, 15)
        assert not r.contains(-1, 5)
        assert not r.contains(5, -1)

    def test_rectangle_to_core(self):
        r = Rectangle(x=10, y=20, width=100, height=50)
        core_r = r._to_core()
        assert core_r is not None

    def test_rectangle_get_core(self):
        r = Rectangle(x=10, y=20, width=100, height=50)
        core_r = r.get_core_rect()
        assert core_r is not None

    def test_rectangle_from_core(self):
        import xnano._core as core

        r = Rectangle._from_core(core.Rect(5, 10, 50, 25))
        assert r.x == 5
        assert r.y == 10
        assert r.width == 50
        assert r.height == 25


class TestRectAlias:
    """Tests for Rect alias."""

    def test_rect_is_rectangle(self):
        assert Rect is Rectangle


class TestConstraint:
    """Tests for Constraint class."""

    def test_constraint_length(self):
        c = Constraint.length(10)
        assert c.apply(100) == 10

    def test_constraint_percentage(self):
        c = Constraint.percentage(50)
        assert c.apply(100) == 50

    def test_constraint_min(self):
        c = Constraint.min(10)
        assert c.apply(100) >= 10
        assert c.apply(5) >= 10  # Should give min

    def test_constraint_max(self):
        c = Constraint.max(50)
        assert c.apply(100) <= 50
        assert c.apply(25) == 25  # Should give actual value

    def test_constraint_ratio(self):
        c = Constraint.ratio(1, 3)
        assert c.apply(100) == 33  # 100/3 ≈ 33

    def test_constraint_fill(self):
        c = Constraint.fill(1)
        assert c.apply(100) == 1

    def test_constraint_fill_zero(self):
        c = Constraint.fill(0)
        assert c.apply(100) == 0

    def test_constraint_from_lengths(self):
        constraints = Constraint.from_lengths([10, 20, 30])
        assert len(constraints) == 3

    def test_constraint_from_percentages(self):
        constraints = Constraint.from_percentages([25, 50, 25])
        assert len(constraints) == 3

    def test_constraint_from_ratios(self):
        constraints = Constraint.from_ratios([(1, 2), (1, 2)])
        assert len(constraints) == 2

    def test_constraint_from_mins(self):
        constraints = Constraint.from_mins([10, 20])
        assert len(constraints) == 2

    def test_constraint_from_maxes(self):
        constraints = Constraint.from_maxes([50, 100])
        assert len(constraints) == 2

    def test_constraint_from_fills(self):
        constraints = Constraint.from_fills([1, 2, 3])
        assert len(constraints) == 3

    def test_constraint_invalid_instantiation(self):
        with pytest.raises(
            TypeError,
            match="Constraint instances are created via factory methods",
        ):
            Constraint()

    def test_constraint_to_core(self):
        c = Constraint.length(10)
        core_c = c._to_core()
        assert core_c is not None


class TestLayout:
    """Tests for Layout class."""

    def test_layout_default(self):
        layout = Layout()
        assert layout is not None

    def test_layout_vertical(self):
        r = Rectangle(x=0, y=0, width=100, height=100)
        layout = Layout(
            direction="vertical",
            constraints=[Constraint.length(10), Constraint.fill(1)],
        )
        splits = layout.split(r)
        assert len(splits) == 2
        assert splits[0].height == 10
        assert splits[1].height == 90

    def test_layout_horizontal(self):
        r = Rectangle(x=0, y=0, width=100, height=100)
        layout = Layout(
            direction="horizontal",
            constraints=[Constraint.percentage(30), Constraint.fill(1)],
        )
        splits = layout.split(r)
        assert len(splits) == 2
        assert splits[0].width == 30
        assert splits[1].width == 70

    def test_layout_with_margin(self):
        r = Rectangle(x=10, y=10, width=100, height=50)
        layout = Layout(
            direction="vertical",
            constraints=[Constraint.length(10)],
            margin=Margin(horizontal=2, vertical=2),
        )
        splits = layout.split(r)
        assert splits[0].x == 12
        assert splits[0].y == 12

    def test_layout_with_margin_int(self):
        r = Rectangle(x=0, y=0, width=100, height=100)
        layout = Layout(
            direction="vertical",
            constraints=[Constraint.length(10)],
            margin=2,
        )
        splits = layout.split(r)
        assert len(splits) == 1

    def test_layout_with_spacing(self):
        r = Rectangle(x=0, y=0, width=100, height=100)
        layout = Layout(
            direction="vertical",
            constraints=[Constraint.length(10), Constraint.length(10)],
            spacing=5,
        )
        splits = layout.split(r)
        assert len(splits) == 2

    def test_layout_with_flex(self):
        r = Rectangle(x=0, y=0, width=100, height=100)
        layout = Layout(
            direction="vertical",
            constraints=[Constraint.fill(1)],
            flex="start",
        )
        splits = layout.split(r)
        assert len(splits) == 1

    def test_layout_all_flex_modes(self):
        r = Rectangle(x=0, y=0, width=100, height=100)
        for mode in [
            "legacy",
            "start",
            "end",
            "center",
            "space_between",
            "space_around",
        ]:
            layout = Layout(
                direction="vertical",
                constraints=[Constraint.fill(1)],
                flex=mode,
            )
            splits = layout.split(r)
            assert splits is not None

    def test_layout_to_core(self):
        layout = Layout(
            direction="vertical", constraints=[Constraint.length(10)]
        )
        core_layout = layout._to_core()
        assert core_layout is not None

    def test_layout_get_core(self):
        layout = Layout(
            direction="vertical", constraints=[Constraint.length(10)]
        )
        core_layout = layout.get_core_layout()
        assert core_layout is not None

    def test_layout_shorthand_constraints(self):
        # Test ConstraintLike inputs in Layout constructor:
        # - integer -> length
        # - float -> percentage
        # - string '%' -> percentage
        # - string 'fill' / '*' -> fill(1)
        # - string '3*' -> fill(3)
        # - string digits -> length
        l = Layout(
            direction="vertical",
            constraints=[10, 0.25, "50%", "fill", "*", "3*", "15"],
        )
        assert l is not None

        # Test invalid constraint type
        with pytest.raises(TypeError, match="Invalid constraint"):
            Layout(constraints=[(1, 2, 3)])  # type: ignore

    def test_layout_split_with_tuple_area(self):
        l = Layout(direction="vertical", constraints=[10])
        # Pass a 4-tuple area instead of Rectangle
        splits = l.split((0, 0, 100, 100))
        assert len(splits) == 1
        assert splits[0].width == 100
        assert splits[0].height == 10

        # Test invalid rectangle type
        with pytest.raises(TypeError, match="expected Rectangle or 4-tuple"):
            l.split(123)  # type: ignore

    def test_layout_map(self):
        l = Layout(direction="vertical", constraints=[10, 20])
        widgets = ["header", "body"]
        states = ["h_state", "b_state"]

        from typing import cast, Any

        # Map widgets and states to 4-tuple area
        mapping = l.map((0, 0, 100, 100), widgets, states)
        assert len(mapping) == 2
        item0 = cast(tuple[Any, Any, Any], mapping[0])
        assert item0[0] == "header"
        assert item0[1].height == 10
        assert item0[2] == "h_state"

        # Map widgets without states
        mapping2 = l.map((0, 0, 100, 100), widgets)
        assert len(mapping2) == 2
        assert len(mapping2[0]) == 2
        assert mapping2[0][0] == "header"

        # Test ValueError when more widgets than splits
        with pytest.raises(ValueError, match="More widgets"):
            l.map((0, 0, 100, 100), ["w1", "w2", "w3"])

    def test_layout_named_constraints(self):
        from typing import cast, Any

        # 1. Named constraints in split
        l = Layout(
            direction="vertical",
            constraints={"header": 3, "body": "fill", "footer": 3},
        )
        splits = l.split((0, 0, 100, 100))
        assert isinstance(splits, dict)
        assert len(splits) == 3
        assert splits["header"].height == 3
        assert splits["body"].height == 94
        assert splits["footer"].height == 3

        # 2. Named constraints in map
        mapping = l.map(
            (0, 0, 100, 100),
            widgets={"header": "header_widget", "body": "body_widget"},
            states={"body": "body_state"},
        )
        assert len(mapping) == 2
        item0 = cast(tuple[Any, Any, Any], mapping[0])
        assert item0[0] == "header_widget"
        assert item0[1].height == 3
        # body mapping (with state):
        item1 = cast(tuple[Any, Any, Any], mapping[1])
        assert item1[0] == "body_widget"
        assert item1[1].height == 94
        assert item1[2] == "body_state"

        # 3. TypeErrors in map: passing list widgets to dict layout, or dict widgets to list layout
        with pytest.raises(TypeError, match="widgets must be a dict"):
            l.map((0, 0, 100, 100), ["w1", "w2"])

        l_list = Layout(direction="vertical", constraints=[3, 10])
        with pytest.raises(TypeError, match="widgets must be a list/sequence"):
            l_list.map((0, 0, 100, 100), {"a": "w1"})

        # 4. KeyError when widget name doesn't match split name
        with pytest.raises(KeyError, match="No split area named"):
            l.map((0, 0, 100, 100), {"invalid_key": "widget"})
