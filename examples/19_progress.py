"""
A long job: a progress bar, the window title and output printed along the way.

The title of the terminal window reports the progress, so it is visible even when the window is
in the background. Text that ``print`` writes while the terminal is open is held back and shows
up below the screen when the terminal closes, so it never tears the picture. The job finishes
by itself, or press ``q`` to stop early.
"""

import xnano
from xnano.widgets import LineGauge

STEPS = 20
SECONDS_PER_STEP = 0.1


class Job:
    """How far the job has come."""

    def __init__(self) -> None:
        self.done = 0


def main() -> None:
    """Run the job and report it."""
    job = Job()
    with xnano.open(width=40, height=3, title='xnano job: starting') as terminal:
        terminal.add('Processing files', y=0)
        bar = LineGauge(0.0, label='0%')
        terminal.add(bar, y=1, width=40, height=1)

        @terminal.every(SECONDS_PER_STEP)
        def work(context: xnano.Context) -> None:
            job.done += 1
            percent = job.done * 100 // STEPS
            bar.ratio = job.done / STEPS
            bar.label = f'{percent}%'
            context.terminal.title = f'xnano job: {percent}%'
            print(f'finished file {job.done} of {STEPS}')  # noqa: T201
            if job.done == STEPS:
                context.terminal.stop()

        terminal.run(quit_on='q')
    print(f'stopped after {job.done} of {STEPS} files')  # noqa: T201


if __name__ == '__main__':
    main()
