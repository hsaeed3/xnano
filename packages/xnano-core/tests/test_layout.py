"""Layout rules over inherited children: never zero-sized by accident."""

from __future__ import annotations

import pytest
from helpers import rows

from xnano._xnano_core import Buffer, Layout, Resize, SizeRule, Write


def make(count: int, **options) -> tuple[Buffer, list[Buffer]]:
    parent = Buffer(width=12, height=6)
    children = [Buffer(width=1, height=1) for _ in range(count)]
    for child in children:
        parent.attach(child, geometry='inherit', **options)
    return parent, children


def sizes(children: list[Buffer]) -> list[tuple[int, int, int, int]]:
    return [(child.x, child.y, child.width, child.height) for child in children]


def test_inherited_children_fill_the_parent_by_default():
    _, children = make(2)
    assert sizes(children) == [(0, 0, 12, 6), (0, 0, 12, 6)]


def test_columns_and_rows_share_space_equally_without_rules():
    parent, children = make(3)
    parent.update(Layout('column'))
    assert [child.height for child in children] == [2, 2, 2]
    assert all(child.width == 12 for child in children)
    parent.update(Layout('row'))
    assert [child.width for child in children] == [4, 4, 4]


@pytest.mark.parametrize('child_count', [40, 50, 100])
@pytest.mark.parametrize('arrangement', ['column', 'row'])
@pytest.mark.parametrize('spacing', [0, 1])
def test_large_fill_layouts_share_the_available_space(child_count, arrangement, spacing):
    parent = Buffer(width=240, height=200)
    children = [Buffer(width=1, height=1) for index in range(child_count)]
    for child in children:
        parent.attach(child, geometry='inherit')
    parent.update(Layout(arrangement, spacing=spacing, padding=2))
    if arrangement == 'row':
        lengths = [child.width for child in children]
        assert children[0].x == 2
        assert children[-1].x + children[-1].width == parent.width - 2
        assert all(
            child.y == 2 and child.height == parent.height - 4 for child in children
        )
        available = parent.width - 4
    else:
        lengths = [child.height for child in children]
        assert children[0].y == 2
        assert children[-1].y + children[-1].height == parent.height - 2
        assert all(child.x == 2 and child.width == parent.width - 4 for child in children)
        available = parent.height - 4
    assert sum(lengths) + spacing * (child_count - 1) == available
    assert max(lengths) - min(lengths) <= 1


def test_a_missing_rule_never_means_a_zero_sized_child():
    parent, children = make(3)
    parent.update(Layout('column', sizes=[SizeRule.cells(2)]))
    assert [child.height for child in children] == [2, 2, 2]
    assert all(child.width > 0 for child in children)


def test_size_rules():
    parent, children = make(4)
    parent.update(
        Layout(
            'row',
            sizes=[
                SizeRule.cells(2),
                SizeRule.percent(25),
                SizeRule.fill(1),
                SizeRule.fill(2),
            ],
        )
    )
    widths = [child.width for child in children]
    assert widths[0] == 2 and widths[1] == 3
    assert widths[2] * 2 == pytest.approx(widths[3], abs=1) and sum(widths) == 12


def test_fit_uses_the_childs_own_size():
    parent = Buffer(width=10, height=4)
    label = Buffer('abcd')
    filler = Buffer()
    parent.attach(label, geometry='inherit')
    parent.attach(filler, geometry='inherit')
    parent.update(Layout('row', sizes=[SizeRule.fit(), SizeRule.fill()]))
    assert label.width == 4 and filler.width == 6
    assert label.height == 4


def test_spacing_and_padding():
    parent, children = make(2)
    parent.update(Layout('row', spacing=2, padding=1))
    assert children[0].x == 1 and children[0].y == 1 and children[0].height == 4
    assert children[1].x == children[0].x + children[0].width + 2
    assert children[1].x + children[1].width == 11


def test_overlay_children_share_the_content_area():
    parent, children = make(2)
    parent.update(Layout('overlay', padding=1))
    assert sizes(children) == [(1, 1, 10, 4), (1, 1, 10, 4)]


def test_explicit_children_are_left_alone():
    parent = Buffer(width=12, height=6)
    floating = Buffer(width=3, height=2, x=5, y=1)
    laid = Buffer()
    parent.attach(floating)
    parent.attach(laid, geometry='inherit')
    parent.update(Layout('column'))
    assert (floating.x, floating.y, floating.width) == (5, 1, 3)
    assert laid.height == 6


def test_resizing_the_parent_relays_children_out_and_clips_output():
    parent, children = make(2)
    parent.update(Layout('column'))
    parent.update(Resize(8, 4))
    assert [child.height for child in children] == [2, 2]
    assert all(child.width == 8 for child in children)
    children[0].update(Write('top'))
    children[1].update(Write('bottom'))
    assert rows(parent)[0] == 'top' and rows(parent)[2] == 'bottom'


def test_nested_layouts_resolve_recursively():
    root = Buffer(width=10, height=4)
    left, right = Buffer(), Buffer()
    root.attach(left, geometry='inherit')
    root.attach(right, geometry='inherit')
    root.update(Layout('row'))
    inner_a, inner_b = Buffer(), Buffer()
    left.attach(inner_a, geometry='inherit')
    left.attach(inner_b, geometry='inherit')
    left.update(Layout('column'))
    assert (inner_a.width, inner_a.height, inner_b.height) == (5, 2, 2)
    root.update(Resize(20, 8))
    assert (inner_a.width, inner_a.height) == (10, 4)


def test_invalid_rules_explain_themselves():
    with pytest.raises(ValueError, match='arrangement'):
        Layout('diagonal')
    with pytest.raises(ValueError, match='0 to 100'):
        SizeRule.percent(120)
    with pytest.raises(ValueError, match='at least 1'):
        SizeRule.fill(0)
    with pytest.raises(ValueError, match='65535'):
        SizeRule.cells(-1)
    assert repr(SizeRule.fit()) == 'SizeRule.fit()'
    assert SizeRule.cells(3) == SizeRule.cells(3)


def test_layout_cannot_target_a_region():
    parent = Buffer(width=4, height=4)
    with pytest.raises(Exception, match='arranged'):
        parent[0:2, 0:2].update(Layout('row'))


def test_a_stack_of_inherit_children_paints_everywhere():
    """Children with inherited geometry are never invisible for lack of size."""
    parent = Buffer(width=6, height=2)
    child = Buffer('hello')
    parent.attach(child, geometry='inherit')
    assert (child.width, child.height) == (6, 2)
    assert rows(parent)[0] == 'hello'
