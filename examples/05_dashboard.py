"""
Dashboard: three services, each with its response time and a graph of the last 24 seconds.

Every second each service gets a new response time. A service that answers slowly turns
yellow and one that stops answering turns red, with a symbol and a word beside the color.
``space`` pauses the updates, and ``q`` quits.
"""

import random

import xnano

BLOCKS = '▁▂▃▄▅▆▇█'  # one character for each height of the graph, lowest first
SLOW_MILLISECONDS, DOWN_MILLISECONDS = 400, 900
STATUS = {  # the symbol and word of each status, and its color
    'online': ('● online', 'green'),
    'slow': ('▲ slow', 'yellow'),
    'down': ('× down', 'red'),
}
# each service's usual response time in milliseconds, and how far it strays from it
SERVICES = {'api': (60, 30), 'web': (380, 260), 'worker': (20, 10)}
generator = random.Random(7)  # seeded, so every run draws the same graphs


def measure_one(usual: int, spread: int) -> int:
    """One response time of a service, which now and then does not answer at all."""
    if generator.random() < 0.05:
        return DOWN_MILLISECONDS + generator.randrange(400)
    return max(1, round(generator.gauss(usual, spread)))


history = {
    name: [measure_one(usual, spread) for _ in range(24)]
    for name, (usual, spread) in SERVICES.items()
}


def status_of(milliseconds: int) -> str:
    """The status of a service that answered in ``milliseconds``."""
    if milliseconds >= DOWN_MILLISECONDS:
        return 'down'
    return 'slow' if milliseconds >= SLOW_MILLISECONDS else 'online'


def graph_of(samples: list[int]) -> str:
    """The samples as a row of blocks, the tallest block for the slowest answer."""
    highest = max(max(samples), 1)
    return ''.join(BLOCKS[min(7, sample * 8 // (highest + 1))] for sample in samples)


def card_lines(name: str) -> list[str]:
    """The three lines inside the card of the service ``name``."""
    samples = history[name]
    word, _ = STATUS[status_of(samples[-1])]
    return [word, f'{samples[-1]} ms', graph_of(samples)]


with xnano.open(title='dashboard') as terminal:
    terminal.write('services', bold=True)
    summary = terminal.write('', x='right', y=0, dim=True)
    cards = {}
    for index, name in enumerate(SERVICES):
        cards[name] = terminal.write(
            card_lines(name),
            x=f'{index * 34}%',
            y=2,
            width='32%',
            border='rounded',
            title=name,
            foreground='green',
        )
    terminal.write('space pause · q quit', y='bottom', dim=True)

    def show() -> None:
        """Draw every card and the summary from the newest samples."""
        healthy = 0
        for name, card in cards.items():
            card.text = '\n'.join(card_lines(name))
            status = status_of(history[name][-1])
            card.color.fg = STATUS[status][1]
            healthy += status == 'online'
        summary.text = f'{healthy} of {len(cards)} online'

    @terminal.hook(on='tick', every=1.0)
    def measure(context: xnano.Context) -> None:
        """Give every service a new response time, once a second."""
        for name, (usual, spread) in SERVICES.items():
            history[name] = [*history[name][1:], measure_one(usual, spread)]
        show()

    @terminal.hook(on='key', keys='space')
    def pause(context: xnano.Context) -> None:
        """Pause the clock, and the updates with it, or resume it."""
        if context.clock.is_paused:
            context.clock.resume()
        else:
            context.clock.pause()

    show()
    terminal.run(stop_on='q')
