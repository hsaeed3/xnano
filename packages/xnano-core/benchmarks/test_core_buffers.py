"""
Benchmarks for xnano-core: laying out child buffers and writing text into them.
"""

from __future__ import annotations

from xnano._xnano_core import Buffer, Layout, SizeRule, Write


def layout_parent(child_count: int) -> tuple[Buffer, list[Buffer]]:
    parent = Buffer(width=120, height=40)
    children = [Buffer(width=1, height=1) for index in range(child_count)]
    for child in children:
        parent.attach(child, geometry='inherit')
    return parent, children


def test_layout_column_of_50_children(benchmark):
    parent, children = layout_parent(50)
    benchmark(parent.update, Layout('column'))
    assert sum(child.height for child in children) == parent.height
    assert all(child.width == parent.width for child in children)


def test_layout_row_with_size_rules(benchmark):
    parent, children = layout_parent(12)
    benchmark(parent.update, Layout('row', sizes=[SizeRule.cells(8)]))
    assert children[0].width == 8
    assert sum(child.width for child in children) == parent.width


def test_write_full_screen_text(benchmark):
    buffer = Buffer(width=200, height=60)
    line = 'x' * 200
    operation = Write('\n'.join([line] * 60))
    benchmark(buffer.update, operation)
    assert buffer.render(format='text') == '\n'.join([line] * 60)
