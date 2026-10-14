"""
tests.test_scene

A pixel world with a camera, sprites, collision and redraw-on-change.
"""

from __future__ import annotations

import pytest

import xnano
import xnano.pixels
from xnano.image import from_art

RED = from_art(['R', 'R'], {'R': '#ff0000'})
GREEN = from_art(['GGGG', 'GGGG'], {'G': '#00ff00'})


@pytest.fixture
def terminal():
    with xnano.iter(offscreen=True, width=8, height=4) as opened:
        yield opened


def pixel(terminal, column, row):
    """The color of one pixel: a cell is two pixels, drawn as a half block or a plain space."""
    cell = terminal[column, row // 2]
    top, bottom = (
        (cell.foreground, cell.background)
        if cell.symbol == '▀'
        else (cell.background, cell.background)
        if cell.symbol == ' '
        else (cell.background, cell.foreground)
    )
    return (top if row % 2 == 0 else bottom).to_rgb()


def test_sprites_are_drawn_where_the_camera_sees_them(terminal):
    scene = terminal.scene(world_width=8, world_height=8, background='black')
    scene.add(GREEN, x=0, y=0)
    scene.add(RED, x=3, y=2)
    terminal.loop.step()
    assert pixel(terminal, 3, 2) == (255, 0, 0)
    assert pixel(terminal, 0, 0) == (0, 255, 0)
    assert pixel(terminal, 7, 7) == (0, 0, 0), (
        'the background shows where nothing is drawn'
    )


def test_the_anchor_is_the_pixel_that_sits_at_the_position(terminal):
    scene = terminal.scene(world_width=8, world_height=8)
    scene.add(RED, x=3, y=3, anchor=(0, 1))
    terminal.loop.step()
    assert pixel(terminal, 3, 3) == (255, 0, 0)
    assert pixel(terminal, 3, 2) == (255, 0, 0)


def test_higher_layers_are_drawn_over_lower_ones(terminal):
    scene = terminal.scene(world_width=8, world_height=8)
    scene.add(RED, x=1, y=1, layer=1)
    scene.add(GREEN, x=1, y=1, layer=0)
    terminal.loop.step()
    assert pixel(terminal, 1, 1) == (255, 0, 0)


def test_a_sprite_that_changes_is_drawn_again(terminal):
    scene = terminal.scene(world_width=8, world_height=8)
    sprite = scene.add(RED, x=1, y=1)
    terminal.loop.step()
    sprite.x = 5
    terminal.loop.step()
    assert pixel(terminal, 1, 1) != (255, 0, 0)
    assert pixel(terminal, 5, 1) == (255, 0, 0)
    sprite.is_visible = False
    terminal.loop.step()
    assert pixel(terminal, 5, 1) != (255, 0, 0)
    sprite.is_visible = True
    sprite.remove()
    terminal.loop.step()
    assert pixel(terminal, 5, 1) != (255, 0, 0)


def test_a_scene_that_did_not_change_is_not_drawn_again(terminal, mocker):
    scene = terminal.scene(world_width=8, world_height=8)
    scene.add(RED, x=1, y=1)
    terminal.loop.step()
    draw = mocker.spy(xnano.pixels.Pixels, 'draw_rgba')
    terminal.loop.step()
    terminal.loop.step()
    assert draw.call_count == 0


def test_the_camera_follows_a_sprite_and_stays_inside_the_world(terminal):
    scene = terminal.scene(world_width=40, world_height=40)
    hero = scene.add(RED, x=20, y=20)
    scene.camera.follow(hero)
    assert scene.view_size == (8, 8)
    assert scene.origin == (16, 16)
    hero.x, hero.y = 0, 0
    assert scene.origin == (0, 0)
    hero.x, hero.y = 39, 39
    assert scene.origin == (32, 32)
    scene.camera.follow(None)
    scene.camera.x, scene.camera.y = 100, -5
    assert scene.origin == (32, 0)


def test_a_world_smaller_than_the_screen_is_centered(terminal):
    scene = terminal.scene(world_width=4, world_height=4)
    assert scene.origin == (-2, -2)


def test_solid_ground_blocks_and_sprites_slide_along_it(terminal):
    scene = terminal.scene(world_width=8, world_height=8)
    solid = bytearray(64)
    for row in range(8):
        solid[row * 8 + 5] = 1  # a wall at column 5
    scene.solid = solid
    hero = scene.add(RED, x=4, y=2)
    assert scene.is_solid(5, 0)
    assert not scene.is_solid(4, 0)
    assert scene.is_solid(-1, 0) and scene.is_solid(0, 8), 'outside the world is solid'
    moved = hero.move_by(2, 1)
    assert (hero.x, hero.y) == (4, 3), 'it slides down the wall instead of stopping'
    assert moved == 1
    assert hero.move_by(5, 0) == 0, 'a head-on step is blocked'


def test_a_cell_of_the_screen_is_a_world_pixel(terminal):
    scene = terminal.scene(world_width=40, world_height=40)
    hero = scene.add(RED, x=20, y=20)
    scene.camera.follow(hero)
    assert scene.world_at(0, 0) == (16, 17)
    assert scene.world_at(4, 2) == (20, 21)


def test_a_scene_needs_a_world(terminal):
    with pytest.raises(ValueError, match='world of at least 1 by 1'):
        terminal.scene(world_width=0, world_height=5)


def test_a_scene_can_live_on_a_placement(terminal):
    view = terminal.write(' ', width=4, height=2)
    scene = view.scene(world_width=4, world_height=4)
    scene.add(RED, x=1, y=1)
    terminal.loop.step()
    assert view.buffer[1, 0].background.to_rgb() == (255, 0, 0)


def test_setting_an_attribute_to_its_current_value_does_not_redraw(terminal):
    scene = terminal.scene(world_width=8, world_height=8)
    sprite = scene.add(RED, x=1, y=1, layer=1, anchor=(0, 1))
    terminal.loop.step()
    version = scene._version
    sprite.x, sprite.y, sprite.layer = 1, 1, 1
    sprite.anchor, sprite.image, sprite.is_visible = (0, 1), RED, True
    assert scene._version == version
    sprite.anchor = (0, 0)
    assert scene._version == version + 1
