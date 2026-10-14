"""
A small playable world with an animated pixel-art character.

The terrain is baked once into an image and the hero is a four-direction sprite with a
walking cycle. Both live in a ``terminal.scene``: it draws them through a camera that follows the
hero, redraws only when something moved, and knows which pixels are solid, so ``sprite.move_by``
slides along water and trees. ``terminal.input`` answers "which keys are held?", and the
simulation runs on ``loop.on_update`` with a fixed time step so the hero walks at the same speed
on every machine.

Walk with ``wasd`` or the arrow keys, or hold the mouse button down and the hero walks toward
the pointer; a click walks to that spot. ``space`` stops time and starts it again. Water and
trees block the way. Press ``q`` to quit.
"""

import math
import random

import xnano
from xnano.context import Context, Update
from xnano.expressions import ParentHeight
from xnano.image import TerminalImage, from_art
from xnano.scene import Sprite

WORLD_WIDTH = 480
WORLD_HEIGHT = 288
SPEED = 36.0  # pixels per second
STRIDE = 3.0  # pixels walked per step of the walking cycle

# -- the hero: one character per pixel, as in a sprite sheet ------------------------------

PALETTE = {
    'H': (92, 56, 34),  # hair
    'S': (240, 196, 150),  # skin
    'E': (36, 30, 40),  # eyes
    'T': (60, 110, 200),  # tunic
    'A': (240, 196, 150),  # arms
    'U': (70, 70, 110),  # trousers
    'F': (50, 40, 40),  # boots
}
HEADS = {
    'front': ('..HHH..', '.HHHHH.', '.SESES.', '.SSSSS.'),
    'back': ('..HHH..', '.HHHHH.', '.HHHHH.', '.HHHHH.'),
    'side': ('..HHH..', '.HHHHH.', '.HSSES.', '..SSSS.'),
}
BODIES = {
    'front': ('.TTTTT.', 'ATTTTTA', '.TTTTT.'),
    'back': ('.TTTTT.', 'ATTTTTA', '.TTTTT.'),
    'side': ('..TTT..', '.TTATT.', '..TTT..'),
}
LEGS = {
    'front': {
        'idle': ('.UU.UU.', '.FF.FF.'),
        'stride': ('.UU.UU.', 'FF...FF'),
        'pass': ('..UUU..', '..FFF..'),
    },
    'side': {
        'idle': ('..UUU..', '..FFF..'),
        'stride': ('.UU.UU.', '.FF..FF'),
        'pass': ('..UUU..', '..FFF..'),
    },
}


def sprite(facing: str, gait: str) -> TerminalImage:
    """The hero facing ``'up'``, ``'down'``, ``'left'`` or ``'right'``, at one step of the walk."""
    view = (
        'side' if facing in ('left', 'right') else ('back' if facing == 'up' else 'front')
    )
    rows = (
        *HEADS[view],
        *BODIES[view],
        *LEGS['side' if view == 'side' else 'front'][gait],
    )
    if facing == 'left':
        rows = tuple(row[::-1] for row in rows)
    return from_art(rows, PALETTE)


SPRITES = {
    (facing, gait): sprite(facing, gait)
    for facing in ('up', 'down', 'left', 'right')
    for gait in ('idle', 'stride', 'pass')
}

# -- the terrain: smooth noise, baked into one picture ------------------------------------


def make_noise(generator: random.Random, cell: int):
    """A smooth random field: values at a grid of points, blended in between."""
    columns, rows = WORLD_WIDTH // cell + 2, WORLD_HEIGHT // cell + 2
    lattice = [[generator.random() for _ in range(columns)] for _ in range(rows)]

    def noise(x: int, y: int) -> float:
        fx, fy = x / cell, y / cell
        column, row = int(fx), int(fy)
        blend_x, blend_y = fx - column, fy - row
        top = lattice[row][column] * (1 - blend_x) + lattice[row][column + 1] * blend_x
        bottom = (
            lattice[row + 1][column] * (1 - blend_x)
            + lattice[row + 1][column + 1] * blend_x
        )
        return top * (1 - blend_y) + bottom * blend_y

    return noise


def bake_world(seed: int) -> tuple[TerminalImage, bytearray]:
    """The whole world as an image, and a mask that says which pixels cannot be walked on."""
    generator = random.Random(seed)
    height = make_noise(generator, 64)
    detail = make_noise(generator, 8)
    forest = make_noise(generator, 32)
    picture = bytearray(WORLD_WIDTH * WORLD_HEIGHT * 4)
    solid = bytearray(WORLD_WIDTH * WORLD_HEIGHT)
    for y in range(WORLD_HEIGHT):
        for x in range(WORLD_WIDTH):
            elevation = height(x, y) * 0.8 + detail(x, y) * 0.2
            shade = int(detail(x, y) * 14)
            if elevation < 0.38:
                color, blocked = (50 + shade, 110 + shade, 190 + shade), 1
            elif elevation < 0.43:
                color, blocked = (222 - shade, 205 - shade, 140 - shade), 0
            else:
                color, blocked = (76 + shade, 158 + shade, 78 - shade // 2), 0
            index = y * WORLD_WIDTH + x
            picture[index * 4 : index * 4 + 4] = bytes((*color, 255))
            solid[index] = blocked
    for _ in range(3600):  # trees and flowers on the grass
        x, y = (
            generator.randrange(3, WORLD_WIDTH - 3),
            generator.randrange(6, WORLD_HEIGHT - 2),
        )
        index = y * WORLD_WIDTH + x
        if solid[index] or picture[index * 4 + 1] < 140:
            continue
        if forest(x, y) > 0.55 and generator.random() < 0.5:
            plant_tree(picture, solid, x, y)
        elif generator.random() < 0.3:
            flower = generator.choice([(250, 230, 90), (240, 120, 160), (250, 250, 250)])
            picture[index * 4 : index * 4 + 4] = bytes((*flower, 255))
    return TerminalImage.from_rgba(WORLD_WIDTH, WORLD_HEIGHT, bytes(picture)), solid


def plant_tree(picture: bytearray, solid: bytearray, x: int, y: int) -> None:
    """A tree whose trunk stands at ``(x, y)``: a crown of three rows over a trunk pixel."""
    for row, half_width in ((-5, 1), (-4, 2), (-3, 2), (-2, 1)):
        for column in range(-half_width, half_width + 1):
            start = ((y + row) * WORLD_WIDTH + x + column) * 4
            picture[start : start + 4] = bytes((28, 100 + 10 * (row + 5), 52, 255))
    for row in (-1, 0):
        start = ((y + row) * WORLD_WIDTH + x) * 4
        picture[start : start + 4] = bytes((100, 66, 40, 255))
    solid[y * WORLD_WIDTH + x] = 1


# -- the game -----------------------------------------------------------------------------


class Hero:
    """The hero's sprite, where it is walking to, and how it looks while doing so."""

    def __init__(self, sprite: Sprite) -> None:
        self.sprite = sprite
        self.target: tuple[float, float] | None = None
        self.facing = 'down'
        self.walked = 0.0

    def step(self, seconds: float, direction: tuple[int, int]) -> None:
        """
        Walk for ``seconds``: along ``direction`` while keys are held, otherwise toward the
        target. The sprite slides along obstacles instead of stopping at them.
        """
        sprite = self.sprite
        if direction != (0, 0):
            self.target = None
            delta_x, delta_y = float(direction[0]), float(direction[1])
        elif self.target is not None:
            delta_x, delta_y = self.target[0] - sprite.x, self.target[1] - sprite.y
        else:
            self.show('idle')
            return
        distance = math.hypot(delta_x, delta_y)
        if distance < 0.5:
            self.target = None
            self.show('idle')
            return
        length = (
            SPEED * seconds if direction != (0, 0) else min(distance, SPEED * seconds)
        )
        walked = sprite.move_by(delta_x / distance * length, delta_y / distance * length)
        if walked == 0:
            self.target = None  # blocked
            self.show('idle')
            return
        self.walked += walked
        if abs(delta_x) > abs(delta_y):
            self.facing = 'right' if delta_x > 0 else 'left'
        else:
            self.facing = 'down' if delta_y > 0 else 'up'
        self.show(('stride', 'pass')[int(self.walked // STRIDE) % 2])

    def show(self, gait: str) -> None:
        """Show the hero facing the way it walks, at one step of the walking cycle."""
        self.sprite.image = SPRITES[self.facing, gait]
        self.sprite.anchor = (
            3,
            9 if gait == 'pass' else 8,
        )  # the legs-together step lifts a pixel


def find_grass(solid: bytes | bytearray) -> tuple[int, int]:
    """The walkable pixel nearest the middle of the world."""
    for radius in range(60):
        for angle in range(0, 360, 15):
            x = WORLD_WIDTH // 2 + round(radius * math.cos(math.radians(angle)))
            y = WORLD_HEIGHT // 2 + round(radius * math.sin(math.radians(angle)))
            if not solid[y * WORLD_WIDTH + x]:
                return x, y
    return WORLD_WIDTH // 2, WORLD_HEIGHT // 2


def main() -> None:
    """Open the world and let the player walk around in it."""
    picture, solid = bake_world(seed=7)
    with xnano.open(
        mouse='buttons', keyboard='release_events', title='world'
    ) as terminal:
        # Everything but the last row is the world; the last row says where the hero is.
        view = terminal.write(' ', width='100%', height=ParentHeight - 1)
        scene = view.scene(WORLD_WIDTH, WORLD_HEIGHT, background='black')
        scene.solid = solid
        scene.add(picture)
        start_x, start_y = find_grass(solid)
        hero = Hero(
            scene.add(
                SPRITES['down', 'idle'], x=start_x, y=start_y, anchor=(3, 8), layer=1
            )
        )
        scene.camera.follow(hero.sprite)

        status_line = terminal.write('', y='bottom', layer=1)

        def show_status() -> None:
            state = (
                'paused (space)' if terminal.is_paused else 'wasd or hold the mouse: walk'
            )
            status = f'x {round(hero.sprite.x):>3} y {round(hero.sprite.y):>3}   {state}   q: quit'
            status_line.text = status

        @terminal.loop.on_update(fixed_step_seconds=1 / 60)
        def simulate(update: Update) -> None:
            hero.step(1 / 60, terminal.input.direction())
            show_status()

        @terminal.on_key('space')
        def toggle_time(context: Context) -> None:
            if terminal.is_paused:
                terminal.resume()
            else:
                terminal.pause()
            show_status()  # updates wait while time is stopped

        def walk_toward_pointer(context: Context) -> None:
            mouse = context.mouse
            if mouse is not None and mouse.position.y < terminal.height - 1:
                world_x, world_y = scene.world_at(mouse.position.x, mouse.position.y)
                hero.target = (float(world_x), float(world_y))

        terminal.on_click(walk_toward_pointer)
        terminal.on_drag(walk_toward_pointer)
        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
