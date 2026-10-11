"""Schema-validated drawings and their animations."""

from __future__ import annotations

import pytest
from helpers import rows

from xnano._xnano_core import (
    Buffer,
    Draw,
    Drawing,
    DrawingAnimation,
    DrawingFrame,
    TerminalStateSchema,
    TerminalStateValidationError,
    inspect_cell_animation,
    inspect_cell_grid,
)


def test_text_drawings_are_data():
    drawing = Drawing(['/\\', '\\/'])
    assert (drawing.kind, drawing.width, drawing.height) == ('text', 2, 2)
    assert drawing.rows == ('/\\', '\\/')
    assert Drawing.from_value(drawing.to_value()) == drawing
    assert '"rows"' in drawing.to_json()


def test_palette_drawings_map_symbols_to_colors_and_transparency():
    drawing = Drawing(['#.', '.#'], kind='palette', palette={'#': (255, 0, 0), '.': None})
    assert (drawing.width, drawing.height) == (2, 2)
    buffer = drawing.to_buffer()
    assert (buffer.width, buffer.height) == (2, 1)
    assert buffer[0, 0].foreground.to_rgb() == (255, 0, 0)
    assert buffer[1, 0].background.to_rgb() == (255, 0, 0) or buffer[
        1, 0
    ].foreground.to_rgb() == (255, 0, 0)
    assert Drawing.from_value(drawing.to_value()).palette == drawing.palette


def test_malformed_drawings_are_refused_with_recovery_hints():
    with pytest.raises(ValueError, match='same width'):
        Drawing(['ab', 'c'])
    with pytest.raises(ValueError, match='not in the palette'):
        Drawing(['x'], kind='palette', palette={'#': (0, 0, 0)})
    with pytest.raises(ValueError, match='exactly one character'):
        Drawing(['x'], kind='palette', palette={'ab': (0, 0, 0)})
    with pytest.raises(ValueError, match='no palette'):
        Drawing(['x'], palette={'x': None})
    with pytest.raises(ValueError, match='drawing kind'):
        Drawing([], kind='vector')


def test_wide_glyphs_count_display_columns():
    assert Drawing(['世界']).width == 4
    with pytest.raises(ValueError, match='same width'):
        Drawing(['世', 'ab', ''])


def test_draw_operation_paints_at_a_position():
    buffer = Buffer(width=6, height=2)
    buffer.update(Draw(Drawing(['ab', 'cd']), x=2, y=0))
    assert rows(buffer) == ['  ab', '  cd']
    sprite = Drawing(['#.#'], kind='palette', palette={'#': (9, 9, 9), '.': None})
    canvas = Buffer(width=3, height=1, style=None)
    canvas.update(Draw(sprite, encoding='braille'))
    assert 0x2800 <= ord(canvas[0, 0].symbol) <= 0x28FF


def drawing_schema(**rule):
    return TerminalStateSchema.compile(
        {
            'type': 'object',
            'properties': {
                'kind': {'enum': ['text']},
                'rows': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['kind', 'rows'],
            'x-xnano': {
                'rule': 'drawing',
                'kind': 'text',
                'maximum_width': 64,
                'maximum_height': 64,
                **rule,
            },
        }
    )


def test_drawing_rules_validate_semantics_natively():
    schema = drawing_schema(width=2, height=2, allowed_symbols=['#', '.'])
    schema.validate({'kind': 'text', 'rows': ['#.', '.#']})
    with pytest.raises(TerminalStateValidationError, match='width must be 2'):
        schema.validate({'kind': 'text', 'rows': ['#']})
    with pytest.raises(TerminalStateValidationError, match='allowed symbols'):
        schema.validate({'kind': 'text', 'rows': ['ab', 'cd']})
    with pytest.raises(TerminalStateValidationError, match='over the maximum'):
        drawing_schema(maximum_width=1).validate({'kind': 'text', 'rows': ['ab']})
    assert schema.to_json_schema()['x-xnano']['rule'] == 'drawing'


def test_animations_pack_into_cell_animations():
    frames = [
        DrawingFrame(Drawing(['a']), duration_milliseconds=50),
        DrawingFrame(Drawing(['bc']), duration_milliseconds=70),
    ]
    animation = DrawingAnimation(frames, should_loop=False)
    assert animation.should_loop is False and len(animation.frames) == 2
    packed = animation.to_cell_animation()
    info = inspect_cell_animation(packed)
    assert (info.frame_count, info.duration_milliseconds, info.columns) == (2, 120, 2)
    assert Buffer.from_cell_animation(packed, start_milliseconds=60).text == 'bc'
    with pytest.raises(ValueError, match='at least one frame'):
        DrawingAnimation([])
    with pytest.raises(ValueError, match='positive'):
        DrawingFrame(Drawing(['a']), duration_milliseconds=0)


def test_drawings_convert_to_cell_grids():
    packed = Drawing(['ab']).to_cell_grid()
    assert inspect_cell_grid(packed).columns == 2


def test_animating_a_drawing_needs_a_runtime(runtime):
    from xnano._xnano_core import AnimateDrawing, RuntimeRequiredError

    animation = DrawingAnimation(
        [
            DrawingFrame(Drawing(['a']), duration_milliseconds=100),
            DrawingFrame(Drawing(['b']), duration_milliseconds=100),
        ]
    )
    buffer = Buffer(width=4, height=1)
    with pytest.raises(RuntimeRequiredError):
        buffer.update(AnimateDrawing(animation))
    runtime.mount(buffer)
    buffer.update(AnimateDrawing(animation))
    runtime.step()
    assert runtime.snapshot().lines()[0] == 'a'
    runtime.advance_clock(100)
    runtime.step()
    assert runtime.snapshot().lines()[0] == 'b'
    runtime.advance_clock(100)
    runtime.step()
    assert runtime.snapshot().lines()[0] == 'a'
