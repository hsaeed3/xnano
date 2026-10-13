"""The Canvas widget: shapes, dynamic settings and value semantics."""

from __future__ import annotations

import copy

import pytest

from xnano_core._xnano_core import (
    Block,
    Buffer,
    Canvas,
    CanvasCircle,
    CanvasLabel,
    CanvasLayer,
    CanvasLine,
    CanvasMap,
    CanvasMarker,
    CanvasPoints,
    CanvasRectangle,
    TerminalStatePatch,
    TerminalStateSchema,
    TerminalStateStore,
    _state_expression,
)


def text(canvas) -> str:
    return canvas.render(format='text')


def test_a_canvas_draws_shapes_in_order():
    canvas = Canvas(
        (0, 10),
        (0, 10),
        marker='block',
        shapes=[CanvasRectangle(0, 0, 10, 10, 'red')],
        width=10,
        height=5,
    )
    assert '█' in text(canvas)
    assert len(canvas.shapes) == 1 and isinstance(canvas.shapes[0], CanvasRectangle)


@pytest.mark.parametrize(
    'shape',
    [
        CanvasLine(0, 0, 10, 10, 'green'),
        CanvasLine(0, 0, 10, 10, 'green', fill_to_y=0),
        CanvasCircle(5, 5, 4, 'blue'),
        CanvasPoints([(1, 1), (5, 5), (9, 9)], 'yellow'),
        CanvasMap('low', 'white'),
    ],
)
def test_every_shape_paints_cells(shape):
    canvas = Canvas((0, 10), (0, 10), marker='block', shapes=[shape], width=10, height=5)
    if isinstance(shape, CanvasMap):
        canvas.x_bounds = (-180, 180)
        canvas.y_bounds = (-90, 90)
    assert '█' in text(canvas)


def test_labels_print_on_top_and_layers_and_markers_are_accepted():
    canvas = Canvas(
        (0, 10),
        (0, 10),
        shapes=[
            CanvasMarker('block'),
            CanvasRectangle(0, 0, 10, 10),
            CanvasLayer(),
            CanvasLabel(1, 5, 'hi'),
        ],
        width=10,
        height=5,
    )
    assert 'hi' in text(canvas)


def test_shapes_can_be_added_replaced_and_cleared():
    canvas = Canvas((0, 10), (0, 10), marker='block', width=10, height=5)
    assert '█' not in text(canvas)
    shape = CanvasRectangle(0, 0, 10, 10)
    canvas.add_shape(shape)
    assert '█' in text(canvas)
    canvas.clear_shapes()
    assert canvas.shapes == [] and '█' not in text(canvas)
    canvas.extend_shapes([shape, CanvasCircle(5, 5, 2)])
    assert len(canvas.shapes) == 2
    canvas.shapes = [CanvasLabel(0, 0, 'x')]
    assert len(canvas.shapes) == 1
    with pytest.raises(TypeError, match='CanvasLine'):
        canvas.add_shape('nope')


def test_editing_a_shape_repaints_its_canvas_immediately():
    shape = CanvasPoints([(1, 1)])
    canvas = Canvas((0, 10), (0, 10), marker='block', shapes=[shape], width=10, height=5)
    before = text(canvas)
    shape.coordinates = [(1, 1), (9, 9)]
    assert text(canvas) != before
    shape.color = 'red'
    assert text(canvas)


def test_bounds_marker_and_background_are_settable():
    canvas = Canvas((0, 1), (0, 1), width=6, height=3)
    canvas.x_bounds = (0, 100)
    canvas.y_bounds = (0, 50)
    assert canvas.x_bounds == (0.0, 100.0) and canvas.y_bounds == (0.0, 50.0)
    canvas.marker = 'dot'
    assert canvas.marker == 'dot'
    canvas.background_color = 'blue'
    assert canvas.background_color is not None
    canvas.background_color = None
    assert canvas.background_color is None
    canvas.marker = '#'
    assert canvas.marker == '#'


def test_settings_follow_state_live():
    store = TerminalStateStore({'size': 4.0}, schema=TerminalStateSchema.compile({}))
    size = _state_expression(store, ('size',), True)
    circle = CanvasCircle(5, 5, size, 'red')
    canvas = Canvas(
        (0, 10), (0, 10), marker='block', shapes=[circle], width=20, height=10
    )
    small = text(canvas)
    store.apply(
        TerminalStatePatch.from_value([{'op': 'replace', 'path': '/size', 'value': 1.0}])
    )
    assert text(canvas) != small
    assert text(canvas).count('█') < small.count('█')
    canvas.x_bounds = (0, size)
    assert canvas.x_bounds[1] is not None


def test_block_frames_the_canvas_and_follows_edits():
    block = Block('map', width=12, height=5)
    canvas = Canvas((0, 1), (0, 1), block=block, width=12, height=5)
    assert canvas.block is block and 'map' in text(canvas)
    block.border_type = 'double'
    assert '╔' in text(canvas)
    canvas.block = None
    assert 'map' not in text(canvas)


def test_invalid_input_explains_the_fix():
    with pytest.raises(ValueError, match='marker'):
        Canvas(marker='huge')
    with pytest.raises(ValueError, match='two numbers'):
        Canvas((1, 2, 3))
    with pytest.raises(ValueError, match='low'):
        CanvasMap('medium')
    with pytest.raises(ValueError, match='finite'):
        CanvasPoints([(float('nan'), 1)])
    canvas = Canvas((0, 1), (0, 1), width=4, height=2)
    canvas.x_bounds = (0, float('inf'))
    with pytest.raises(Exception, match='finite'):
        text(canvas)


@pytest.mark.parametrize(
    'factory',
    [
        lambda: CanvasLine(0, 0, 1, 1, 'red'),
        lambda: CanvasRectangle(0, 0, 1, 1),
        lambda: CanvasCircle(0, 0, 1),
        lambda: CanvasPoints([(0, 0)]),
        lambda: CanvasMap(),
        lambda: CanvasLabel(0, 0, 'a'),
        lambda: CanvasMarker('dot'),
    ],
)
def test_shapes_compare_by_value_copy_and_are_not_hashable(factory):
    first, second = factory(), factory()
    assert first == second and first != object()
    assert repr(first).startswith('Canvas')
    for clone in (copy.copy(first), copy.deepcopy(first)):
        assert clone == first and clone is not first
    with pytest.raises(TypeError):
        hash(first)


def test_a_layer_marker_is_a_hashable_value():
    assert CanvasLayer() == CanvasLayer() and hash(CanvasLayer()) == hash(CanvasLayer())
    assert repr(CanvasLayer()) == 'CanvasLayer()'


def test_a_canvas_is_a_buffer_widget():
    canvas = Canvas((0, 1), (0, 1), width=6, height=3, x=2, y=1)
    assert isinstance(canvas, Buffer) and (canvas.x, canvas.y) == (2, 1)
    assert 'Canvas' in repr(canvas)
