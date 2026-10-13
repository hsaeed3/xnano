"""
Benchmarks for xnano-core buffers: laying out child buffers, writing text and moving
cells between buffers.

Every timed call must do the work it names. Applying the same ``Layout`` twice in a row
takes a fast path that costs a fraction of a real layout, so the layout benchmarks cycle
between two layouts that give different results. Benchmarks whose first call is
faster than the rest set their rounds explicitly. Setup that is not part of the
measurement runs outside the timed call.
"""

from __future__ import annotations

import itertools

from xnano_core._xnano_core import Buffer, Layout, Rectangle, SizeRule, Write


def layout_parent(child_count: int) -> tuple[Buffer, list[Buffer]]:
    parent = Buffer(width=120, height=40)
    children = [Buffer(width=1, height=1) for index in range(child_count)]
    for child in children:
        parent.attach(child, geometry='inherit')
    return parent, children


def test_layout_column_of_50_children(benchmark):
    parent, children = layout_parent(50)
    layouts = itertools.cycle((Layout('column'), Layout('column', spacing=0, padding=1)))
    benchmark(lambda: parent.update(next(layouts)))
    assert all(child.width in (parent.width, parent.width - 2) for child in children)


def test_layout_row_with_size_rules(benchmark):
    parent, children = layout_parent(12)
    layouts = itertools.cycle(
        (
            Layout('row', sizes=[SizeRule.cells(8)]),
            Layout('row', sizes=[SizeRule.cells(9)]),
        )
    )
    benchmark(lambda: parent.update(next(layouts)))
    assert children[0].width in (8, 9)
    assert sum(child.width for child in children) == parent.width


def test_layout_nested_columns_and_rows(benchmark):
    """A three level tree: 6 columns of 6 rows of 6 cells."""
    root = Buffer(width=120, height=40)
    leaves = []
    for _column in range(6):
        column = Buffer()
        root.attach(column, geometry='inherit')
        for _row in range(6):
            row = Buffer()
            column.attach(row, geometry='inherit')
            for _cell in range(6):
                leaf = Buffer()
                row.attach(leaf, geometry='inherit')
                leaves.append(leaf)
            row.update(Layout('row'))
        column.update(Layout('column'))
    layouts = itertools.cycle((Layout('row'), Layout('row', spacing=1)))
    benchmark(lambda: root.update(next(layouts)))
    assert all(leaf.width >= 1 for leaf in leaves)


def test_write_full_screen_text(benchmark):
    buffer = Buffer(width=200, height=60)
    line = 'x' * 200
    operation = Write('\n'.join([line] * 60))
    benchmark(buffer.update, operation)
    assert buffer.render(format='text') == '\n'.join([line] * 60)


def test_write_single_line(benchmark):
    buffer = Buffer(width=200, height=60)
    operations = itertools.cycle((Write('a' * 80, x=10, y=5), Write('b' * 80, x=10, y=5)))
    benchmark(lambda: buffer.update(next(operations)))
    assert buffer[10, 5].symbol in ('a', 'b')


def test_direct_cell_writes(benchmark):
    """One thousand single-cell assignments through ``buffer[x, y] = symbol``."""
    buffer = Buffer(width=200, height=60)
    symbols = itertools.cycle(('a', 'b'))

    def write_cells():
        symbol = next(symbols)
        for index in range(1000):
            buffer[index % 200, index // 200] = symbol

    benchmark(write_cells)
    assert buffer[999 % 200, 999 // 200].symbol in ('a', 'b')


def test_paste_large_sprite(benchmark):
    canvas = Buffer(width=200, height=60)
    sprite = Buffer(width=100, height=30)
    sprite.update(Write('\n'.join(['#' * 100] * 30)))
    offsets = itertools.cycle((0, 1))
    benchmark(lambda: canvas.paste(sprite, x=next(offsets), y=0))
    assert canvas[50, 10].symbol == '#'


def test_region_copy(benchmark):
    buffer = Buffer(width=200, height=60)
    buffer.update(Write('\n'.join(['x' * 200] * 60)))
    region = buffer.region(Rectangle(10, 10, 100, 40))
    copy = benchmark(region.copy)
    assert (copy.width, copy.height) == (100, 40)


def test_attach_and_detach_children(benchmark):
    parent = Buffer(width=120, height=40)
    children = [Buffer(width=1, height=1) for _ in range(100)]

    def attach_and_detach():
        for child in children:
            parent.attach(child)
        for child in children:
            parent.detach(child)

    benchmark(attach_and_detach)
    assert parent.children == ()


def test_resize_with_children(benchmark):
    parent, children = layout_parent(50)
    heights = itertools.cycle((41, 40))
    # Every child inherits the parent's full size, so one resize reallocates 50 grids.
    # The first call after a resize is the slow one, so the rounds are set explicitly
    # instead of being calibrated from a single fast measurement.
    benchmark.pedantic(
        lambda: parent.resize(120, next(heights)),
        rounds=300,
        iterations=1,
        warmup_rounds=4,
    )
    assert all(child.height == parent.height for child in children)
