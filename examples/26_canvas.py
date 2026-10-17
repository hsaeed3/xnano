"""
A canvas without a screen, then the same canvas on the screen.

``xnano.new()`` makes a canvas that draws into memory. Its clock moves only when you move it:
``iter(count=3)`` yields three frames and ``render()`` returns what was drawn, so the first
part of this program prints plain text that is the same on every run. ``open()`` then puts the
same canvas on the screen, with its time carried over. There, ``space`` stops and resumes
time, ``n`` moves a stopped canvas one frame with ``step()``, and ``q`` quits.

``xnano.new(realtime=True)`` is the other screenless canvas: it runs by itself on the wall
clock, on a thread of its own, so you write to it from your thread and a timer hook ends the
wait. ``render(format='ansi')`` returns its frame with the colors as escape codes.
"""

import xnano
from xnano.context import Context
from xnano.events import Event

canvas = xnano.new(width=52, height=3, fps=10)
counter = canvas.write('frame 0 at 0.0 seconds')
status = canvas.write('time runs   space stop/resume   n step   q quit', y=2)

for frame in canvas.iter(count=3):
    counter.text = f'frame {frame.index} at {frame.elapsed_seconds:.1f} seconds'
    print(canvas.render().splitlines()[0])  # noqa: T201

with xnano.new(width=52, height=1, realtime=True) as running:
    running.write('this canvas runs by itself', foreground='green')

    @running.hook(on='tick', after=0.05)
    def finish(context: Context) -> None:
        running.push(Event.key_press('enter'))

    running.wait_for_key('enter')
    print(running.render(format='ansi').splitlines()[0])  # noqa: T201


@canvas.hook(on='frame')
def show_frame(context: Context) -> None:
    index = context.time.frame
    counter.text = f'frame {index} at {context.time.elapsed:.1f} seconds'
    status.text = (
        'time stopped   space resume   n step   q quit'
        if context.time.is_stopped
        else 'time runs   space stop   n step   q quit'
    )


@canvas.hook(on='key', keys='space')
def toggle(context: Context) -> None:
    if context.time.is_stopped:
        context.canvas.resume()
    else:
        context.canvas.stop()


@canvas.hook(on='key', keys='n')
def step_once(context: Context) -> None:
    if context.time.is_stopped:
        context.canvas.step()


with canvas.open():
    canvas.run(quit_on='q')
