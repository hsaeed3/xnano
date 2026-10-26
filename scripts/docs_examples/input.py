"""
A tiny farm on a floating island: walk around, harvest what is ripe and water what grows.

The arrow keys (or ``wasd``) walk the farmer one tile at a time and ``space`` works the
tile they face: a ripe crop is harvested and replanted, and a seed or sprout is watered
and grows back to ripe. The island is a pixel world: every sprite is written as rows of
characters (one pixel each, ``.`` for none), and the farmer, the crops and the water are
art inside the world that moves and changes. Run it with ``python input.py`` and press
``q`` to quit.
"""

import dataclasses
import math

import xnano
from xnano.art import Art

PALETTE = (
    "G=#7cba62 g=#609e4e l=#a0d276 f=#f096be y=#f4cc6e o=#faf6ec "  # grass and flowers
    "S=#ac7a50 s=#8e6240 M=#785238 m=#62422e P=#e4d0a4 p=#c6b084 "  # soil, wet soil, path
    "W=#6ea8e8 w=#badcf8 b=#5080c4 D=#966846 d=#765036 k=#563a28 "  # water, the cliff
    "T=#d2a46e t=#946a44 e=#604630 V=#68ba58 v=#468e40 "  # fence, seeds and leaves
    "A=#f0c870 a=#e876aa C=#f6ceaa E=#302438 K=#784e32 B=#6098ec U=#7c60b4 O=#60402c"
)  # the farmer: hat, hat band, skin, eyes, hair, shirt, trousers and boots
FRUIT_COLORS = {  # each column of the field grows its own crop, colored R with a shade r
    2: " R=#ec80b2 r=#c45c8c",  # turnips
    3: " R=#ecaa48 r=#c88030",  # pumpkins
    4: " R=#6aa0ee r=#4670c8",  # blueberries
    5: " R=#966ee6 r=#6e4cbe",  # eggplants
}
TILES = {  # eight by eight pixels, row after row
    "G": "GGGGGGGG GGgGGGGG GgGGGGlG GGGGGGGG GGGGgGGG GlGGGgGG GGGGGGGG GGGgGGGG",
    "F": "GGGGGGGG GfGGGGGG fyfGGoGG GfGGoyoG GGGGGoGG GGGGGGGG GGyGGGgG GGGGGGGG",
    "S": "SSSSSSSS SsSSSsSS ssssssss SSSSSSSS SSSsSSSs ssssssss SSSSSSSS SSSSSSSS",
    "P": "PPPPPPPP PPPpPPPP PPPPPPpP PpPPPPPP PPPPPPPP PPPPpPPP PPPPPPPP PPpPPPPP",
}
TILES["W"] = TILES["G"]  # the pond lies on grass
TILES["M"] = TILES["S"].replace("S", "M").replace("s", "m")  # soil that was watered
# the tiles of the farm, row after row from the back: flowers, grass, water, soil, path
FARM = ("FGGGGGGWW", "GGSSSSGWW", "GFSSSSGGF", "PPPPPPPPG")
CLIFF = (  # the earth under the island, a third of its width
    "DDDDDDDDDDDDDDDDDDDDDDDD DdDDDDDDkDDDDDdDDDDDDkDD DDDkDDdDDDDDDDDDDkDDDDdD "
    "kddkdddkkdddkddkddddkddk .kk..kkk...k...kk.k..kk."
)
FENCE = ".tt..... .TT..... TTTTTTTT tTTttttt .TT..... TTTTTTTT tTTttttt .tt....."
POND = (
    "....bbbbbbbb.... ..bbWWWWWWWWbb.. .bWWWWWWWWWWWWb. .bWWWWWWWWWWWWb. "
    + "bWWWWWWWWWWWWWWb " * 8
    + ".bWWWWWWWWWWWWb. .bWWWWWWWWWWWWb. ..bbWWWWWWWWbb.. ....bbbbbbbb...."
)
RIPPLES = [(4, 3), (11, 4), (6, 6), (3, 9), (10, 10), (7, 13)]  # light on the water
CROP_STAGES = (  # a seed, a sprout, a young plant and a ripe one
    "........ ........ ........ ..e..e.. ........ ...e..e. ........ ........",
    "........ ........ ........ ..VV.VV. ...VvV.. ....v... ....v... ........",
    "........ ..V..V.. .VVV.VV. ..VVvVV. ...VvV.. ....v... ...vvv.. ........",
    "..V..V.. .VVVvVV. ..VvVV.. ..RRRR.. .RRRRRr. .RRRRrr. ..Rrrr.. ........",
)
RIPE = len(CROP_STAGES) - 1
FRUIT = "..V.. .RRR. RRRRr RRRrr .rrr."
DROPS = "..w...w. ........ .W...W.. ....w... ..W..... ......W. .w..W..."
FARMER = {  # the head and body; facing right is facing left, mirrored
    "down": "..AAA.. .AaaaA. AAAAAAA .CECEC. .CCCCC. CBBBBBC .BBBBB.",
    "up": "..AAA.. .AaaaA. AAAAAAA .KKKKK. .KKKKK. CBBBBBC .BBBBB.",
    "left": "..AAA.. .AaaaA. AAAAAAA .CECKK. .CCCKK. .BBBBC. .BBBBB.",
}
LEGS = (".UU.UU. .OO.OO.", "..UUU.. ..OOO..")  # standing, and mid-stride
STEPS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
WALK_KEYS = {"left": "left", "right": "right", "up": "up", "down": "down"}
WALK_KEYS |= {"a": "left", "d": "right", "w": "up", "s": "down"}
# the pixel where the first tile of the farm starts, and how large a tile is
LEFT, TOP, TILE = 4, 6, 8
STEP_SECONDS, GROW_SECONDS = 0.18, 0.7


def sprite_art(rows: str, palette: str = PALETTE) -> Art:
    """Pixel art from rows of characters separated by spaces."""
    return xnano.pixel_art(rows.split(), palette)


def tile_corner(column: int, row: int) -> tuple[int, int]:
    """The pixel at the top-left corner of a tile."""
    return LEFT + column * TILE, TOP + row * TILE


@dataclasses.dataclass
class Plot:
    """A tile of soil: how it looks when wet, its crop and how far the crop has grown."""

    column: int
    wet_soil: Art
    crop: Art
    stage: int
    grows_at: float | None = None  # when it grows next, while it is watered

    def show(self) -> None:
        """Draw the crop at its stage."""
        self.crop.replace(
            CROP_STAGES[self.stage].split(), PALETTE + FRUIT_COLORS[self.column]
        )


@dataclasses.dataclass
class Farmer:
    """Where the farmer stands and faces, and when they last stepped, harvested and watered."""

    column: int = 1
    row: int = 3
    facing: str = "down"
    step_from: tuple[int, int] = tile_corner(1, 3)
    stepped_at: float = -9.0
    harvested_at: float = -9.0
    watered_at: float = -9.0
    watered_tile: tuple[int, int] = (0, 0)


world = xnano.pixel_art(None, width=80, height=46)  # no background: the island floats
ground = [
    "".join(TILES[tile].split()[line] for tile in tiles)
    for tiles in FARM
    for line in range(TILE)
]
cliff = [row * 3 for row in CLIFF.split()]
world.add(xnano.pixel_art(ground + cliff, PALETTE), x=LEFT, y=TOP)
fence = [row * len(FARM[0]) for row in FENCE.split()]
world.add(xnano.pixel_art(fence, PALETTE), x=LEFT, y=TOP - 4, layer=1)
pond_x, pond_y = tile_corner(7, 0)
world.add(sprite_art(POND), x=pond_x, y=pond_y, layer=1)
ripple_rows = ["." * 16] * 16
for x, y in RIPPLES:
    ripple_rows[y] = ripple_rows[y][:x] + "ww" + ripple_rows[y][x + 2 :]
ripples = world.add(xnano.pixel_art(ripple_rows, PALETTE), x=pond_x, y=pond_y, layer=2)
plots: dict[tuple[int, int], Plot] = {}
for row, tiles in enumerate(FARM):
    for column in [column for column, tile in enumerate(tiles) if tile == "S"]:
        x, y = tile_corner(column, row)
        wet_soil = world.add(sprite_art(TILES["M"]), x=x, y=y, layer=1)
        wet_soil.is_visible = False
        crop = world.add(sprite_art(CROP_STAGES[0]), x=x, y=y, layer=2)
        stage = {(3, 1): 2, (5, 1): 1}.get((column, row), RIPE)  # two are still growing
        plots[column, row] = Plot(column, wet_soil, crop, stage)
        plots[column, row].show()
farmer = Farmer()
farmer_sprite = world.add(sprite_art(FARMER["down"] + " " + LEGS[0]), layer=3)
held_fruit = world.add(sprite_art(FRUIT, PALETTE + FRUIT_COLORS[2]), layer=4)
drops = world.add(sprite_art(DROPS), layer=4)
held_fruit.is_visible = drops.is_visible = False


def is_walkable(column: int, row: int) -> bool:
    """Whether a tile is on the island and is grass or path."""
    is_on_island = 0 <= row < len(FARM) and 0 <= column < len(FARM[0])
    return is_on_island and FARM[row][column] in "GFP"


def work_tile(now: float) -> None:
    """Harvest the crop the farmer faces if it is ripe, or else water it."""
    step_x, step_y = STEPS[farmer.facing]
    column, row = farmer.column + step_x, farmer.row + step_y
    plot = plots.get((column, row))
    if plot is not None and plot.stage == RIPE:
        plot.stage = 0  # harvested, and a seed goes back in
        plot.show()
        held_fruit.replace(FRUIT.split(), PALETTE + FRUIT_COLORS[plot.column])
        farmer.harvested_at = now
    elif plot is not None and plot.grows_at is None:
        plot.grows_at = now + GROW_SECONDS
        plot.wet_soil.is_visible = True
        farmer.watered_at, farmer.watered_tile = now, tile_corner(column, row)


def draw_farmer(now: float) -> None:
    """Move the farmer's sprite along their step, facing their way, legs mid-stride."""
    progress = min(1.0, (now - farmer.stepped_at) / STEP_SECONDS)
    from_x, from_y = farmer.step_from
    to_x, to_y = tile_corner(farmer.column, farmer.row)
    farmer_sprite.x = round(from_x + (to_x - from_x) * progress)
    # one pixel up, so the hat pokes above the tile
    farmer_sprite.y = round(from_y + (to_y - from_y) * progress) - 1
    body = FARMER["left" if farmer.facing == "right" else farmer.facing]
    rows = (body + " " + LEGS[1 if 0.2 < progress < 0.8 else 0]).split()
    if farmer.facing == "right":
        rows = [row[::-1] for row in rows]
    farmer_sprite.replace(rows, PALETTE)


with xnano.open(title="farm") as terminal:
    terminal.screen.write(world, x="center", y=0)
    hint = "← ↑ → ↓ walk  ·  space harvest or water"
    terminal.screen.write(hint, x="center", y="bottom", dim=True)

    @terminal.hook(on="key")
    def work(context: xnano.Context) -> None:
        """Walk a tile (or turn toward one that cannot be walked on), or work a tile."""
        now = context.clock.elapsed_seconds
        facing = WALK_KEYS.get(context.keyboard.key or "")
        if facing is not None and now - farmer.stepped_at >= STEP_SECONDS:
            farmer.facing = facing
            step_x, step_y = STEPS[facing]
            if is_walkable(farmer.column + step_x, farmer.row + step_y):
                farmer.step_from = tile_corner(farmer.column, farmer.row)
                farmer.column, farmer.row = farmer.column + step_x, farmer.row + step_y
                farmer.stepped_at = now
        elif context.keyboard.key == "space":
            work_tile(now)

    @terminal.hook(on="tick", every=1 / 30)
    def animate(context: xnano.Context) -> None:
        """Move the farmer, grow what is watered and play the harvest and water effects."""
        now = context.clock.elapsed_seconds
        draw_farmer(now)
        for plot in plots.values():
            if plot.grows_at is not None and now >= plot.grows_at:
                plot.stage += 1
                plot.show()
                is_growing = plot.stage < RIPE
                plot.grows_at = plot.grows_at + GROW_SECONDS if is_growing else None
                plot.wet_soil.is_visible = is_growing
        held_fruit.is_visible = now - farmer.harvested_at < 0.6
        held_fruit.x = farmer_sprite.x + 1
        held_fruit.y = farmer_sprite.y - 6 - round((now - farmer.harvested_at) * 4)
        drops.is_visible = now - farmer.watered_at < 0.5
        drops.x, drops.y = farmer.watered_tile
        drops.y += int((now - farmer.watered_at) * 8) % 2  # the drops fall
        ripples.x = pond_x + round(math.sin(now * math.pi))

    terminal.run(stop_on="q")
