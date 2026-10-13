"""
Snake: a game on a fixed time step.

``terminal.loop.on_update`` runs the simulation at a steady rate whatever the frame rate is, so
the snake moves at the same speed on every machine. The arrow keys steer, ``r`` restarts after
a crash, and ``q`` quits.
"""

import random

import xnano

WIDTH = 30
HEIGHT = 24  # in pixels: a cell holds two
DIRECTIONS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}


class Game:
    """The snake, the food and the score."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Start over with a short snake heading right."""
        self.body = [(5, 12), (4, 12), (3, 12)]
        self.direction = (1, 0)
        self.is_over = False
        self.food = self.new_food()

    def new_food(self) -> tuple[int, int]:
        """A free cell for the next piece of food."""
        free = [
            (column, row)
            for column in range(WIDTH)
            for row in range(HEIGHT)
            if (column, row) not in self.body
        ]
        return random.choice(free)

    def steer(self, direction: tuple[int, int]) -> None:
        """Turn, unless that would reverse into the snake's own neck."""
        if (direction[0] + self.direction[0], direction[1] + self.direction[1]) != (0, 0):
            self.direction = direction

    def step(self) -> None:
        """Move one cell, eat, or crash."""
        if self.is_over:
            return
        column, row = self.body[0]
        head = (column + self.direction[0], row + self.direction[1])
        is_eating = head == self.food
        # The tail moves away on a step that does not grow the snake, so its cell is free.
        occupied = self.body if is_eating else self.body[:-1]
        if not 0 <= head[0] < WIDTH or not 0 <= head[1] < HEIGHT or head in occupied:
            self.is_over = True
            return
        self.body.insert(0, head)
        if is_eating:
            self.food = self.new_food()
        else:
            self.body.pop()


def main() -> None:
    """Run the game until the player quits."""
    game = Game()
    with xnano.open(width=WIDTH, height=HEIGHT // 2 + 1) as terminal:
        pixels = terminal.pixels()

        def draw() -> None:
            terminal.clear()
            for column, row in game.body:
                pixels[column, row] = '#00c800'
            pixels[game.food[0], game.food[1]] = '#ff3030'
            status = (
                'crashed: r to restart' if game.is_over else f'score {len(game.body) - 3}'
            )
            terminal.write(status.ljust(WIDTH), y=HEIGHT // 2)

        @terminal.loop.on_update(fixed_step_seconds=0.12)
        def tick(update: xnano.Update) -> None:
            game.step()
            draw()

        @terminal.on_key(*DIRECTIONS)
        def steer(context: xnano.Context) -> None:
            if context.keyboard is not None:
                game.steer(DIRECTIONS[context.keyboard.key])

        @terminal.on_key('r')
        def restart(context: xnano.Context) -> None:
            game.reset()

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
