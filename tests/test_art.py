"""
tests.test_art

Pixel art written as text, and pixel worlds: children, a camera, collision and redraw-on-change.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.art import Art, Camera, draw
from xnano.image import TerminalImage


def red() -> Art:
    return draw(['R', 'R'], {'R': '#ff0000'})


def green() -> Art:
    return draw(['GGGG', 'GGGG'], {'G': '#00ff00'})


@pytest.fixture
def canvas():
    with xnano.new(width=8, height=4) as opened:
        yield opened


def world_on(canvas, width=8, height=8, background=None, **keywords):
    """A world written over the whole canvas, drawn on the next step, and its placement."""
    world = draw(None, width=width, height=height, background=background)
    view = canvas.write(world, width='100%', height='100%', **keywords)
    canvas.step()
    return world, view


def pixel(view, column, row):
    """The color of one pixel: a cell is two pixels, drawn as a half block or a plain space."""
    cell = view.core_buffer[column, row // 2]
    top, bottom = (
        (cell.foreground, cell.background)
        if cell.symbol == '▀'
        else (cell.background, cell.background)
        if cell.symbol == ' '
        else (cell.background, cell.foreground)
    )
    return (top if row % 2 == 0 else bottom).to_rgb()


class TestDraw:
    def test_text_rows_are_painted_with_a_palette(self):
        heart = draw(
            """
            .RR.RR.
            RRRRRRR
            .RRRRR.
            ..RRR..
            ...R...
            """,
            'R=#e03040',
        )
        assert (heart.width, heart.height) == (7, 5)

    def test_a_palette_is_a_mapping_or_a_string(self):
        by_mapping = draw(['AB'], {'A': 'red', 'B': (0, 0, 255)})
        by_text = draw(['AB'], 'A=red B=#0000ff')
        assert by_mapping.render(format='ansi') == by_text.render(format='ansi')

    def test_a_character_the_palette_does_not_name_is_transparent(self, canvas):
        view = canvas.write(draw(['.R'], {'R': '#ff0000'}))
        assert pixel(view, 0, 0) is None
        assert pixel(view, 1, 0) == (255, 0, 0)

    def test_a_list_is_rows_and_a_one_row_picture_is_a_list(self):
        assert (
            draw(['GG'], {'G': 'green'}).width,
            draw(['GG'], {'G': 'green'}).height,
        ) == (
            2,
            1,
        )

    def test_a_name_without_a_newline_is_a_symbol(self):
        registered = draw(['PP', 'PP'], {'P': 'blue'}, symbol='player')
        found = draw('player')
        assert (found.width, found.height) == (2, 2)
        assert found is not registered, 'a lookup returns a copy that can be moved alone'
        assert registered.symbol == 'player'
        assert xnano.symbols.lookup('player', kind=Art) is registered

    def test_an_unknown_symbol_lists_the_known_ones_and_says_how_to_draw_one_row(self):
        draw(['W'], {'W': 'white'}, symbol='wall')
        with pytest.raises(ValueError, match="'GG' is not a known Art symbol") as caught:
            draw('GG')
        message = str(caught.value)
        assert "'wall'" in message
        assert "draw(['GG'], palette)" in message

    def test_a_symbol_may_also_be_registered_by_a_lookup(self):
        draw(['W'], {'W': 'white'}, symbol='stone')
        again = draw('stone', symbol='boulder')
        assert xnano.symbols.lookup('boulder', kind=Art) is again

    def test_a_picture_is_copied(self):
        picture = TerminalImage.from_rgba(2, 1, bytes((255, 0, 0, 255, 0, 0, 255, 255)))
        art = draw(picture)
        assert (art.width, art.height) == (2, 1)
        image = xnano.Image(picture)
        assert draw(image).width == 2

    def test_bytes_need_a_size_that_matches(self):
        data = bytes((255, 0, 0, 255)) * 4
        assert draw(data, width=2, height=2).height == 2
        with pytest.raises(ValueError, match='need the size of the picture'):
            draw(data)
        with pytest.raises(ValueError, match='need 16 bytes'):
            draw(data[:8], width=2, height=2)

    def test_nothing_is_a_blank_world(self):
        world = draw(None, width=10, height=6, background='#336699')
        assert (world.width, world.height) == (10, 6)
        assert world.background == xnano.Color('#336699')
        with pytest.raises(ValueError, match='needs a size in pixels'):
            draw(None)

    def test_rows_must_match_and_a_palette_is_needed(self):
        with pytest.raises(ValueError, match='every row the same length'):
            draw(['AB', 'A'], {'A': 'red'})
        with pytest.raises(ValueError, match='need a palette'):
            draw(['AB'])
        with pytest.raises(ValueError, match='not a palette entry'):
            draw(['A'], 'A:red')

    def test_other_sources_are_explained(self):
        with pytest.raises(TypeError, match='cannot make art from a int'):
            draw(5)  # type: ignore[arg-type]

    def test_art_has_a_size(self):
        with pytest.raises(ValueError, match='at least 1 by 1'):
            Art(None, 0, 3)

    def test_effects_given_as_a_one_shot_iterable_are_kept(self):
        specification = {'kind': 'effect.dissolve'}
        art = draw(['G'], {'G': 'red'}, effects=(item for item in [specification]))
        assert art._effects == (specification,)
        registered = draw(['G'], {'G': 'red'}, symbol='one_shot_effects')
        again = draw('one_shot_effects', effects=(item for item in [specification]))
        assert again._effects == (specification,)
        assert registered._effects == ()

    def test_effects_run_on_every_placement_that_shows_the_art(self, canvas):
        art = draw(
            ['RR', 'RR'],
            {'R': 'red'},
            effects=[{'kind': 'effect.fade_to', 'duration_milliseconds': 500}],
        )
        assert len(canvas._effects) == 0
        first = canvas.write(art)
        assert first.width == 2
        assert len(canvas._effects) == 1
        canvas.write(art)
        assert len(canvas._effects) == 2


class TestDrawing:
    def test_children_are_drawn_where_the_camera_sees_them(self, canvas):
        world, view = world_on(canvas, background='black')
        world.add(green(), x=0, y=0)
        world.add(red(), x=3, y=2)
        canvas.step()
        assert pixel(view, 3, 2) == (255, 0, 0)
        assert pixel(view, 0, 0) == (0, 255, 0)
        assert pixel(view, 7, 7) == (0, 0, 0), (
            'the background shows where nothing is drawn'
        )

    def test_the_anchor_is_the_pixel_that_sits_at_the_position(self, canvas):
        world, view = world_on(canvas)
        world.add(red(), x=3, y=3, anchor=(0, 1))
        canvas.step()
        assert pixel(view, 3, 3) == (255, 0, 0)
        assert pixel(view, 3, 2) == (255, 0, 0)

    def test_higher_layers_are_drawn_over_lower_ones(self, canvas):
        world, view = world_on(canvas)
        world.add(red(), x=1, y=1, layer=1)
        world.add(green(), x=1, y=1, layer=0)
        canvas.step()
        assert pixel(view, 1, 1) == (255, 0, 0)

    def test_children_can_hold_children(self, canvas):
        world, view = world_on(canvas)
        body = world.add(green(), x=2, y=2)
        body.add(red(), x=1, y=0)
        canvas.step()
        assert pixel(view, 3, 2) == (255, 0, 0)

    def test_a_child_that_changes_is_drawn_again(self, canvas):
        world, view = world_on(canvas)
        child = world.add(red(), x=1, y=1)
        canvas.step()
        child.x = 5
        canvas.step()
        assert pixel(view, 1, 1) != (255, 0, 0)
        assert pixel(view, 5, 1) == (255, 0, 0)
        child.is_visible = False
        canvas.step()
        assert pixel(view, 5, 1) != (255, 0, 0)
        child.is_visible = True
        child.remove()
        canvas.step()
        assert pixel(view, 5, 1) != (255, 0, 0)

    def test_replace_swaps_the_pixels_and_keeps_the_place(self, canvas):
        world, view = world_on(canvas)
        child = world.add(draw(['R'], {'R': 'red'}), x=2, y=2, layer=3)
        canvas.step()
        child.replace(['B'], {'B': (0, 0, 255)})
        canvas.step()
        assert pixel(view, 2, 2) == (0, 0, 255)
        assert (child.x, child.y, child.layer) == (2, 2, 3)

    def test_a_world_that_did_not_change_is_not_drawn_again(self, canvas, mocker):
        world, view = world_on(canvas)
        world.add(red(), x=1, y=1)
        canvas.step()
        render = mocker.spy(Art, '__xnano_render__')
        canvas.step()
        canvas.step()
        assert render.call_count == 0
        world.add(red(), x=4, y=4)
        canvas.step()
        assert render.call_count == 1

    def test_a_composed_world_is_cached_until_it_changes(self, canvas):
        world, view = world_on(canvas)
        first = world._compose(8, 4)
        assert world._compose(8, 4) is first
        world.add(red())
        assert world._compose(8, 4) is not first

    def test_setting_an_attribute_to_its_current_value_changes_nothing(self, canvas):
        world, view = world_on(canvas)
        child = world.add(red(), x=1, y=1, layer=1, anchor=(0, 1))
        canvas.step()
        version = world._version
        child.x, child.y, child.layer = 1, 1, 1
        child.anchor, child.is_visible = (0, 1), True
        assert world._version == version
        child.anchor = (0, 0)
        assert world._version == version + 1

    def test_art_is_written_without_a_size_at_its_own_size(self, canvas):
        placement = canvas.write(
            draw(['AB', 'CD', 'EF'], 'A=red B=green C=blue D=white E=gray F=magenta')
        )
        assert (placement.width, placement.height) == (2, 2)

    def test_art_in_a_border_fits_inside_it(self, canvas):
        placement = canvas.write(draw(['AB'], 'A=red B=blue'), border='rounded')
        assert (placement.width, placement.height) == (4, 3)

    def test_art_draws_on_its_own(self):
        heart = draw(['R.R', 'RRR'], {'R': 'red'})
        assert heart.render() == ' ▄'
        assert '\x1b[' in heart.render(format='ansi')
        assert heart.render(width=4, height=2).count('\n') == 1

    def test_art_can_live_on_a_placement(self, canvas):
        view = canvas.write(' ', width=4, height=2)
        world = draw(None, width=4, height=4)
        inner = view.write(world, width='100%', height='100%')
        world.add(red(), x=1, y=1)
        canvas.step()
        assert pixel(inner, 1, 1) == (255, 0, 0)
        assert (inner.width, inner.height) == (4, 2)

    def test_art_follows_a_resize_of_its_placement(self):
        with xnano.new(width=8, height=4) as canvas:
            world = draw(None, width=40, height=40, background='black')
            placement = canvas.write(world, width=8, height=4)
            canvas.step()
            assert world._view_size() == (8, 8)
            placement.width = 4
            canvas.step()
            assert world._view_size() == (4, 8)


class TestCamera:
    def test_the_camera_follows_a_child_and_stays_inside_the_world(self, canvas):
        world, view = world_on(canvas, width=40, height=40)
        hero = world.add(red(), x=20, y=20)
        world.camera.follow(hero)
        assert world._view_size() == (8, 8)
        assert world._origin() == (16, 16)
        hero.x, hero.y = 0, 0
        assert world._origin() == (0, 0)
        hero.x, hero.y = 39, 39
        assert world._origin() == (32, 32)
        world.camera.follow(None)
        world.camera.x, world.camera.y = 100, -5
        assert world._origin() == (32, 0)

    def test_the_camera_follows_a_nested_child_by_its_world_position(self, canvas):
        world, view = world_on(canvas, width=40, height=40)
        carrier = world.add(red(), x=10, y=10)
        rider = carrier.add(red(), x=10, y=10)
        world.camera.follow(rider)
        assert world._origin() == (16, 16)

    def test_a_world_smaller_than_the_screen_is_centered(self, canvas):
        world, view = world_on(canvas, width=4, height=4)
        assert world._origin() == (-2, -2)

    def test_the_camera_object_is_per_art(self):
        assert isinstance(draw(None, width=2, height=2).camera, Camera)

    def test_a_cell_of_the_screen_is_a_world_pixel(self, canvas):
        world, view = world_on(canvas, width=40, height=40)
        hero = world.add(red(), x=20, y=20)
        world.camera.follow(hero)
        canvas.step()
        assert world.world_for_cell(0, 0) == (16, 17)
        assert world.world_for_cell(4, 2) == (20, 21)


class TestMovement:
    def solid_world(self):
        world = draw(None, width=8, height=8)
        solid = bytearray(64)
        for row in range(8):
            solid[row * 8 + 5] = 1  # a wall at column 5
        world.solid_map = solid
        return world

    def test_solid_ground_blocks_and_children_slide_along_it(self):
        world = self.solid_world()
        hero = world.add(red(), x=4, y=2)
        assert world.is_solid(5, 0)
        assert not world.is_solid(4, 0)
        assert world.is_solid(-1, 0) and world.is_solid(0, 8), (
            'outside the world is solid'
        )
        assert hero.move(2, 1) == (0.0, 1.0)
        assert (hero.x, hero.y) == (4, 3), 'it slides down the wall instead of stopping'
        assert hero.move(5, 0) == (0.0, 0.0), 'a head-on step is blocked'

    def test_replacing_the_pixels_keeps_the_solid_ground_of_the_same_size(self):
        world = self.solid_world()
        world.replace(None, width=8, height=8)
        assert world.is_solid(5, 0), 'the same size keeps the walls'
        world.replace(None, width=4, height=4)
        assert not world.is_solid(2, 0), 'a new size clears the walls'

    def test_the_four_verbs_move_and_say_how_far(self):
        world = draw(None, width=10, height=10)
        hero = world.add(red(), x=5, y=5)
        assert hero.right(2) == 2
        assert hero.down(3) == 3
        assert hero.left() == 1
        assert hero.up(0.5) == 0.5
        assert (hero.x, hero.y) == (6, 7.5)

    def test_the_verbs_report_a_block(self):
        world = self.solid_world()
        hero = world.add(red(), x=4, y=2)
        assert hero.right(3) == 0

    def test_a_loose_art_moves_freely(self):
        art = red()
        assert art.move(3, -2) == (3.0, -2.0)
        assert (art.x, art.y) == (3, -2)

    def test_a_solid_child_blocks_other_children_but_not_itself(self):
        world = draw(None, width=10, height=4)
        wall = world.add(draw(['W', 'W'], {'W': 'white'}), x=5, y=1, is_solid=True)
        hero = world.add(red(), x=3, y=1)
        assert world.is_solid(5, 1)
        assert hero.right(5) == 1, 'it stops in front of the wall'
        assert wall.right(1) == 1, 'the wall is not blocked by itself'

    def test_a_transparent_pixel_of_a_solid_child_does_not_block(self):
        world = draw(None, width=10, height=4)
        world.add(draw(['.W'], {'W': 'white'}), x=5, y=1, is_solid=True)
        assert not world.is_solid(5, 1)
        assert world.is_solid(6, 1)

    def test_fractional_steps_are_drawn_at_the_rounded_position(self, canvas):
        world, view = world_on(canvas)
        hero = world.add(red(), x=0, y=0)
        hero.move(0.4, 0)
        canvas.step()
        assert pixel(view, 0, 0) == (255, 0, 0)
        hero.move(0.4, 0)
        canvas.step()
        assert pixel(view, 1, 0) == (255, 0, 0)

    def test_the_solid_map_needs_one_byte_per_pixel(self):
        world = draw(None, width=4, height=4)
        with pytest.raises(ValueError, match='one byte for each of the 16 pixels'):
            world.solid_map = b'\x00' * 3


class TestComposition:
    def test_an_art_belongs_to_one_art(self):
        first = draw(None, width=4, height=4)
        second = draw(None, width=4, height=4)
        child = first.add(red())
        with pytest.raises(ValueError, match='already belongs to another art'):
            second.add(child)

    def test_an_art_cannot_hold_itself(self):
        world = draw(None, width=4, height=4)
        child = world.add(red())
        with pytest.raises(ValueError, match='cannot be added to itself'):
            world.add(world)
        with pytest.raises(ValueError, match='cannot be added to itself'):
            child.add(world)

    def test_only_art_can_be_added(self):
        with pytest.raises(TypeError, match='add\\(\\) takes an Art'):
            draw(None, width=4, height=4).add('x')  # type: ignore[arg-type]

    def test_removing_stops_the_camera_following(self):
        world = draw(None, width=40, height=40)
        hero = world.add(red())
        world.camera.follow(hero)
        hero.remove()
        hero.remove()
        assert world.camera.target is None

    def test_a_removed_art_can_be_added_elsewhere(self):
        first = draw(None, width=4, height=4)
        second = draw(None, width=4, height=4)
        child = first.add(red())
        child.remove()
        assert second.add(child) is child

    def test_a_copy_from_a_symbol_keeps_the_children(self):
        world = draw(None, width=6, height=6, background='black', symbol='arena')
        world.add(red(), x=2, y=2)
        copy = draw('arena')
        assert copy.render() == world.render()
        assert copy is not world
