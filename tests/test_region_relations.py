"""
tests.test_region_relations

``in`` and ``overlaps`` between screen cells and areas (a region, a placement or a screen),
compared in screen cells, and the edge positions ``right_edge`` and ``bottom_edge``. A placement
is all the cells it takes, its border, padding and margin included, as its mouse hooks hear them.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.events import Event
from xnano.expressions import parent
from xnano_core import Point, TimeElapsed


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=8, fps=10) as opened:
        yield opened


class TestPoints:
    def test_a_screen_holds_its_cells(self, canvas):
        assert (0, 0) in canvas.screen and (19, 7) in canvas.screen
        assert Point(5, 3) in canvas.screen
        assert (20, 0) not in canvas.screen and (0, 8) not in canvas.screen
        assert (-1, 0) not in canvas.screen

    def test_a_placement_with_no_look_answers_like_its_region(self, canvas):
        button = canvas.screen.write('[ OK ]', x=2, y=1)
        for point in ((2, 1), (7, 1), Point(4, 1), (1, 1), (8, 1), (2, 0), (2, 2)):
            assert (point in button) == (point in button.region)
        assert (2, 1) in button and Point(7, 1) in button
        assert (8, 1) not in button and (2, 2) not in button

    def test_the_mouse_position_in_a_placement(self, canvas):
        button = canvas.screen.write('[ OK ]', x=2, y=1)
        hits: list[bool] = []

        @canvas.hook(on="mouse.kind == 'press'")
        def press(context):
            hits.append(context.mouse.position in button)

        for column in (2, 7, 8):
            canvas.push(
                Event.mouse_event(column=column, row=1, kind='press', button='left')
            )
            canvas.deliver_events()
        assert hits == [True, True, False]

    def test_a_value_that_is_not_a_cell_or_an_area_is_not_inside(self, canvas):
        button = canvas.screen.write('ok', x=0, y=0)
        for value in (
            None,
            'ab',
            (0,),
            (0, 0, 0),
            ('0', '0'),
            [0, 0],
            (True, False),
            canvas,
            xnano.Note('C4'),
        ):
            assert value not in button
            assert value not in button.region
            assert value not in canvas.screen


class TestAreas:
    def test_a_placement_inside_a_screen(self, canvas):
        label = canvas.screen.write('label', x=15, y=7)
        assert label in canvas.screen and label.region in canvas.screen
        label.x = 16
        assert label not in canvas.screen
        label.x = -1
        assert label not in canvas.screen

    def test_a_placement_inside_another_placement(self, canvas):
        frame = canvas.screen.write(xnano.box(10, 4), x=2, y=1)
        inside = canvas.screen.write('abc', x=3, y=2)
        across = canvas.screen.write('abc', x=10, y=2)
        assert inside in frame and inside.region in frame.region
        assert across not in frame and across.region not in frame
        assert frame not in inside
        assert frame in frame

    def test_a_screen_is_not_inside_a_smaller_placement(self, canvas):
        label = canvas.screen.write('abc', x=0, y=0)
        assert canvas.screen not in label
        assert canvas.screen in canvas.screen

    def test_a_child_placement_is_compared_in_screen_cells(self, canvas):
        frame = canvas.screen.write(xnano.box(10, 4), x=2, y=1)
        child = frame.write('hi', x=1, y=1)
        assert (child.x, child.y) == (1, 1)
        assert (child.region.x, child.region.y) == (3, 2)
        assert (3, 2) in child and (1, 1) not in child
        assert child in frame and child in canvas.screen

    def test_a_bordered_placement_includes_its_border(self, canvas):
        card = canvas.screen.write('card', x=2, y=1, border='plain')
        region = card.region
        assert (region.x, region.y, region.width, region.height) == (3, 2, 4, 1)
        assert (2, 1) in card and (7, 3) in card and (3, 2) in card
        assert (8, 1) not in card and (2, 4) not in card
        assert (2, 1) not in card.region
        corner = canvas.screen.write('x', x=2, y=1)
        assert corner in card and corner not in card.region
        assert card.overlaps(corner) and corner.overlaps(card)
        assert not card.region.overlaps(corner) and not corner.overlaps(card.region)
        assert card.region in card and card not in card.region
        assert card in canvas.screen

    def test_a_placement_includes_its_padding_and_margin(self, canvas):
        card = canvas.screen.write('ok', x=2, y=1, border='rounded', margin=1)
        assert (card.x, card.y, card.width, card.height) == (2, 1, 6, 5)
        assert (card.region.x, card.region.y) == (4, 3)
        assert (2, 1) in card and (7, 5) in card
        assert (8, 1) not in card and (2, 6) not in card
        padded = canvas.screen.write('ok', x=12, y=1, padding=1)
        assert (12, 1) in padded and (12, 1) not in padded.region

    def test_a_click_on_the_border_reaches_the_placement(self, canvas):
        button = canvas.screen.write('ok', x=2, y=1, border='rounded')
        canvas.clock.step()
        heard: list[tuple[int, int, bool]] = []

        @button.hook(on='mouse')
        def press(context):
            position = context.mouse.position
            heard.append((position.x, position.y, position in context.target))

        canvas.push(Event.mouse_event(column=2, row=1, kind='press', button='left'))
        canvas.deliver_events()
        assert heard == [(2, 1, True)]
        assert (2, 1) in button and (2, 1) not in button.region

    def test_a_placement_is_the_area_its_mouse_hooks_hear(self, canvas):
        card = canvas.screen.write(xnano.box(5, 3), x=2, y=1, border='plain', margin=1)
        canvas.clock.step()
        heard: list[tuple[int, int]] = []

        @card.hook(on="mouse.kind == 'press'")
        def press(context):
            heard.append((context.mouse.position.x, context.mouse.position.y))

        cells = [(column, row) for row in range(8) for column in range(12)]
        for column, row in cells:
            canvas.push(
                Event.mouse_event(column=column, row=row, kind='press', button='left')
            )
            canvas.deliver_events()
            canvas.push(
                Event.mouse_event(column=column, row=row, kind='release', button='left')
            )
            canvas.deliver_events()
        assert heard == [cell for cell in cells if cell in card]
        assert len(heard) == card.width * card.height

    def test_pixel_views_compare_in_cells(self, canvas):
        label = canvas.screen.write('abcd', x=2, y=1)
        dots = label.region.braille
        assert (dots.width, dots.height) == (8, 4)
        assert (5, 1) in dots and (6, 1) not in dots
        assert dots in label and label in dots
        assert label.region.half_blocks in canvas.screen
        assert dots.overlaps(label.region.half_blocks)


class TestNestedCanvas:
    def test_a_placement_on_a_written_canvas_is_compared_in_screen_cells(self, canvas):
        panel = xnano.new(width=8, height=3)
        canvas.screen.write(panel, x=5, y=2)
        child = panel.screen.write('ab', x=1, y=1)
        assert (child.region.x, child.region.y) == (6, 3)
        assert (6, 3) in child and (1, 1) not in child
        assert child in panel.screen and child in canvas.screen
        assert (5, 2) in panel.screen and (4, 2) not in panel.screen
        assert panel.screen in canvas.screen and canvas.screen not in panel.screen
        corner = canvas.screen.write('zz', x=0, y=0)
        assert corner not in panel.screen and not panel.screen.overlaps(corner)
        assert child.overlaps(panel.screen) and panel.screen.overlaps(child)


class TestEmptyAreas:
    def test_an_empty_area_is_inside_when_its_position_is_inside(self, canvas):
        empty = canvas.screen.write(None, x=4, y=3)
        assert (empty.width, empty.height) == (0, 0)
        assert empty in canvas.screen
        empty.x = 20
        assert empty not in canvas.screen

    def test_an_empty_area_overlaps_nothing(self, canvas):
        empty = canvas.screen.write(None, x=4, y=3)
        label = canvas.screen.write('abc', x=3, y=3)
        assert empty in label
        assert not label.overlaps(empty) and not empty.overlaps(label)
        assert not canvas.screen.overlaps(empty)

    def test_nothing_is_inside_an_empty_area(self, canvas):
        empty = canvas.screen.write(None, x=4, y=3)
        other = canvas.screen.write(None, x=4, y=3)
        label = canvas.screen.write('a', x=4, y=3)
        assert (4, 3) not in empty
        assert other not in empty and label not in empty


class TestTimeline:
    def test_a_region_on_the_timeline_keeps_its_beats_and_pitches(self, canvas):
        region = xnano.Note(('C4', 'G4'), beats=2).region
        assert (1, 60) in region and (1.5, 67) in region
        assert (2, 60) not in region and Point(1, 60) not in region
        assert region.overlaps((1, 60)) and not region.overlaps((3, 60))

    def test_no_area_is_inside_or_overlaps_a_region_on_the_timeline(self, canvas):
        region = xnano.Note(('C4', 'G4'), beats=2).region
        label = canvas.screen.write('a', x=0, y=0)
        assert label not in region and label.region not in region
        assert region not in canvas.screen and region not in label
        assert not region.overlaps(label) and not label.overlaps(region)

    def test_the_edges_of_a_region_on_the_timeline_are_its_end_and_the_pitch_above(self):
        region = xnano.Note(('C4', 'G4'), beats=2).region
        assert (region.right_edge, region.bottom_edge) == (2.0, 68)
        assert region.sixteenths.right_edge == 8.0


class TestOverlaps:
    def test_areas_that_share_a_cell_overlap(self, canvas):
        basket = canvas.screen.write('[___]', x=5, y=6)
        apple = canvas.screen.write('o', x=9, y=5)
        assert not basket.overlaps(apple) and not apple.overlaps(basket)
        apple.down()
        assert basket.overlaps(apple) and apple.overlaps(basket)
        assert basket.region.overlaps(apple.region)

    def test_areas_that_only_touch_do_not_overlap(self, canvas):
        left = canvas.screen.write('abc', x=0, y=0)
        right = canvas.screen.write('def', x=3, y=0)
        below = canvas.screen.write('ghi', x=0, y=1)
        assert left.right_edge == right.x and left.bottom_edge == below.y
        assert not left.overlaps(right) and not left.overlaps(below)
        right.left()
        assert left.overlaps(right)

    def test_a_cell_overlaps_when_it_is_inside(self, canvas):
        label = canvas.screen.write('abc', x=2, y=1)
        assert label.overlaps((2, 1)) and label.overlaps(Point(4, 1))
        assert not label.overlaps((5, 1)) and not label.overlaps(Point(1, 1))
        assert canvas.screen.overlaps((19, 7)) and not canvas.screen.overlaps((20, 7))

    def test_a_screen_overlaps_what_crosses_its_edge(self, canvas):
        across = canvas.screen.write('abcd', x=18, y=7)
        assert across not in canvas.screen
        assert canvas.screen.overlaps(across) and across.overlaps(canvas.screen)
        across.x = 20
        assert not canvas.screen.overlaps(across)

    @pytest.mark.parametrize(
        'value', [None, 'ab', [1, 2], (1, 2, 3), ('1', '2'), 3], ids=repr
    )
    def test_a_value_that_is_not_an_area_or_a_cell_is_refused(self, canvas, value):
        label = canvas.screen.write('abc')
        for owner in (label, label.region, canvas.screen):
            with pytest.raises(
                TypeError, match=r'overlaps\(\) takes an area or a screen cell'
            ) as caught:
                owner.overlaps(value)
            message = str(caught.value)
            assert f'but got {value!r}.' in message
            assert 'An area is a Region, a Placement or a Screen' in message
            assert 'Pass one of these' in message

    def test_the_refusal_of_a_canvas_names_its_screen(self, canvas):
        label = canvas.screen.write('abc')
        with pytest.raises(TypeError, match=r'such as canvas\.screen'):
            label.overlaps(canvas)


class TestEdges:
    def test_a_placement_edge_is_the_cell_after_it(self, canvas):
        label = canvas.screen.write('name', x=2, y=1)
        assert (label.right_edge, label.bottom_edge) == (6, 2)
        canvas.screen.write('→', x=label.right_edge + 1, y=label.y)
        canvas.clock.step()
        assert canvas.screen.render().splitlines()[1] == '  name →'

    def test_a_bordered_placement_edge_includes_its_border(self, canvas):
        card = canvas.screen.write('card', x=2, y=1, border='plain')
        assert (card.right_edge, card.bottom_edge) == (8, 4)
        assert (card.region.right_edge, card.region.bottom_edge) == (7, 3)

    def test_a_child_placement_edge_is_relative_to_its_parent(self, canvas):
        frame = canvas.screen.write(xnano.box(10, 4), x=2, y=1)
        child = frame.write('hi', x=1, y=1)
        assert (child.right_edge, child.bottom_edge) == (3, 2)
        assert (child.region.right_edge, child.region.bottom_edge) == (5, 3)

    def test_an_edge_reads_a_position_that_is_an_expression(self, canvas):
        end = canvas.screen.write('end', x=parent.width - 3, y=parent.height - 1)
        assert (end.right_edge, end.bottom_edge) == (20, 8)
        end.text = 'ending'
        assert end.right_edge == 17 + 6
        mover = canvas.screen.write('ab', x=TimeElapsed * 10, y=0)
        assert mover.right_edge == 2
        canvas.clock.step()
        assert (mover.x, mover.right_edge) == (1, 3)

    def test_a_region_edge_is_in_screen_cells_at_every_resolution(self, canvas):
        region = canvas.screen.write('abcd', x=2, y=1).region
        assert (region.right_edge, region.bottom_edge) == (6, 2)
        for view in (region.braille, region.half_blocks, region.cells):
            assert (view.right_edge, view.bottom_edge) == (6, 2)

    def test_a_standalone_region_edge_is_its_size(self):
        card = xnano.region('hi', border='plain')
        assert (card.right_edge, card.bottom_edge) == (4, 3)

    def test_a_screen_edge_is_its_size_and_follows_its_position(self, canvas):
        assert (canvas.screen.right_edge, canvas.screen.bottom_edge) == (20, 8)
        panel = canvas.screen.new('panel', width=6, height=2)
        panel.screen.move(x=3, y=4)
        assert (panel.screen.right_edge, panel.screen.bottom_edge) == (9, 6)
        assert (panel.screen.region.right_edge, panel.screen.region.bottom_edge) == (
            9,
            6,
        )
